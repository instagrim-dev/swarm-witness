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
        return self.snapshot(grant_id)

    def delegate(self, grant_id: str, delegate: AgentId) -> GrantSnapshot:
        g = self.grants[grant_id]
        g["assignees"] = set(g["assignees"]) | {delegate}
        self.owner_version += 1
        g["owner_version"] = self.owner_version
        return self.snapshot(grant_id)

    def revoke(self, grant_id: str) -> GrantSnapshot:
        g = self.grants[grant_id]
        if g["state"] != "spent":
            g["state"] = "revoked"
        self.owner_version += 1
        g["owner_version"] = self.owner_version
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
