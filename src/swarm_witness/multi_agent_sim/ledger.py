"""Authoritative grant/effect ledger (separate from per-agent local views)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from swarm_witness.multi_agent_sim.events import AgentId, GrantSnapshot


@dataclass
class AuthoritativeLedger:
    """Ground-truth grant ownership, spend, and committed effects."""

    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    committed_effects: list[dict[str, Any]] = field(default_factory=list)
    owner_version: int = 0
    # grant_id -> owner_version -> snapshot at that version. Used to tell a
    # faithful older observation from a fabricated payload.
    grant_history: dict[str, dict[int, dict[str, Any]]] = field(default_factory=dict)

    def issue_grant(
        self,
        grant_id: str,
        *,
        owner: AgentId,
        epoch: str = "epoch-1",
    ) -> GrantSnapshot:
        self.owner_version += 1
        self.grants[grant_id] = {
            "owner": owner,
            "state": "active",
            "epoch": epoch,
            "owner_version": self.owner_version,
            "assignees": {owner},
            "spent": False,
        }
        self._remember(grant_id)
        return self.snapshot(grant_id)

    def delegate(self, grant_id: str, delegate: AgentId) -> GrantSnapshot:
        g = self.grants[grant_id]
        g["assignees"] = set(g["assignees"]) | {delegate}
        self.owner_version += 1
        g["owner_version"] = self.owner_version
        self._remember(grant_id)
        return self.snapshot(grant_id)

    def revoke(self, grant_id: str) -> GrantSnapshot:
        g = self.grants[grant_id]
        if g["state"] != "spent":
            g["state"] = "revoked"
        self.owner_version += 1
        g["owner_version"] = self.owner_version
        self._remember(grant_id)
        return self.snapshot(grant_id)

    def snapshot(self, grant_id: str) -> GrantSnapshot:
        g = self.grants[grant_id]
        state = "spent" if g["spent"] else g["state"]
        return GrantSnapshot(
            grant_id=grant_id,
            owner=g["owner"],
            state=state,
            epoch=g["epoch"],
            owner_version=int(g["owner_version"]),
            assignees=tuple(sorted(g["assignees"])),
            spent=bool(g["spent"]),
        )

    def commit_effect(
        self,
        *,
        grant_id: str,
        agent: AgentId,
        call_id: str,
        decision_event_id: str,
        enforce: bool = True,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Attempt to settle an effect.

        Returns ``(effect, None)`` on commit, or ``(None, refusal_reason)`` when
        the authoritative boundary refuses.

        When ``enforce`` is True (reference arm), refuse spent/revoked grants and
        non-assignees so a bad *decision* is not silently turned into an
        unauthorized committed effect. Mutant arms may pass ``enforce=False`` to
        produce a concrete counterexample at the effect boundary.
        """
        g = self.grants[grant_id]
        if enforce:
            if bool(g["spent"]) or g["state"] in {"revoked", "spent"}:
                return None, "authoritative_spent_or_revoked"
            if agent not in g["assignees"]:
                return None, "agent_not_assignee"
        g["spent"] = True
        g["state"] = "spent"
        self.owner_version += 1
        g["owner_version"] = self.owner_version
        self._remember(grant_id)
        receipt_id = f"receipt-{call_id}"
        receipt = {
            "receipt_id": receipt_id,
            "agent": agent,
            "grant_id": grant_id,
            "call_id": call_id,
            "decision_event_id": decision_event_id,
        }
        self.receipts[receipt_id] = receipt
        effect = {
            "effect_id": f"effect-{call_id}",
            "grant_id": grant_id,
            "agent": agent,
            "call_id": call_id,
            "decision_event_id": decision_event_id,
            "owner_version_at_commit": g["owner_version"],
        }
        self.committed_effects.append(effect)
        return effect, None

    def owner_state_projection(self, grant_id: str) -> dict[str, Any]:
        snap = self.snapshot(grant_id)
        return {
            "grant": snap.to_dict(),
            "committed_effect_count": sum(
                1 for e in self.committed_effects if e["grant_id"] == grant_id
            ),
            "committed_effects": [
                dict(e) for e in self.committed_effects if e["grant_id"] == grant_id
            ],
            "ledger_owner_version": self.owner_version,
        }

    def _remember(self, grant_id: str) -> None:
        snap = self.snapshot(grant_id).to_dict()
        self.grant_history.setdefault(grant_id, {})[int(snap["owner_version"])] = snap

    @staticmethod
    def _projection(raw: dict[str, Any]) -> dict[str, Any]:
        """Grant body, ignoring observation-delivery metadata."""
        version = raw.get("owner_version")
        try:
            version_n = None if version is None else int(version)
        except (TypeError, ValueError):
            version_n = None
        return {
            "grant_id": raw.get("grant_id"),
            "owner": raw.get("owner"),
            "state": raw.get("state"),
            "epoch": raw.get("epoch"),
            "owner_version": version_n,
            "assignees": tuple(sorted(raw.get("assignees") or [])),
            "spent": bool(raw.get("spent")),
        }

    @staticmethod
    def _binding(raw: dict[str, Any]) -> dict[str, Any]:
        """Who the grant is bound to. State drift is freshness, not integrity."""
        return {
            "grant_id": raw.get("grant_id"),
            "owner": raw.get("owner"),
            "assignees": tuple(sorted(raw.get("assignees") or [])),
        }

    def evidence_integrity(
        self, observation: dict[str, Any] | None, grant_id: str
    ) -> str:
        """Integrity of one local observation, separate from freshness.

        ``authentic`` — the payload matches the authoritative snapshot at the
        version it claims, or its owner/assignee binding still matches the
        grant. A faithful older snapshot stays authentic; state or version
        drift is freshness, not a fabricated binding.

        ``misbound`` — the payload matches neither that historical snapshot
        nor the current binding (fabricated assignee list, wrong owner).

        ``missing`` — no observation.
        """
        if observation is None:
            return "missing"
        if observation.get("grant_id") not in (None, grant_id):
            return "misbound"
        claimed = observation.get("owner_version")
        historical: dict[str, Any] | None = None
        if claimed is not None:
            try:
                historical = self.grant_history.get(grant_id, {}).get(int(claimed))
            except (TypeError, ValueError):
                historical = None
        if historical is not None and self._projection(observation) == self._projection(
            historical
        ):
            return "authentic"
        current = self.snapshot(grant_id).to_dict()
        if self._binding(observation) == self._binding(current):
            return "authentic"
        return "misbound"
