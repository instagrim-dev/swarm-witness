"""Typed simulation events for the multi-agent causal interleaving harness.

A simulated interleaving is not a live distributed-system deployment. Events
record actor, identity, causal predecessor, epoch/owner version, and observed
source so traces remain machine-readable and replayable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AgentId = Literal["A", "B", "C"]
ActorId = AgentId | Literal["ledger", "scheduler", "evaluator"]

EventKind = Literal[
    "grant_issue",
    "observation_deliver",
    "delegation",
    "revocation",
    "claim",
    "receipt_deliver",
    "receipt_replay",
    "effect_attempt",
    "effect_settle",
]

SIM_AGENTS: tuple[AgentId, ...] = ("A", "B", "C")


@dataclass(frozen=True)
class SimEvent:
    """One recorded simulation event."""

    event_id: str
    kind: EventKind
    actor: ActorId
    causal_predecessor: str | None
    epoch: str
    owner_version: int
    observed_source: str | None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GrantSnapshot:
    """Authoritative or locally observed grant projection."""

    grant_id: str
    owner: AgentId
    state: Literal["active", "revoked", "spent"]
    epoch: str
    owner_version: int
    assignees: tuple[AgentId, ...]
    spent: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "owner": self.owner,
            "state": self.state,
            "epoch": self.epoch,
            "owner_version": self.owner_version,
            "assignees": list(self.assignees),
            "spent": self.spent,
        }


@dataclass(frozen=True)
class LocalKnowledge:
    """What one actor knew at a decision point."""

    agent: AgentId
    grant_observations: tuple[dict[str, Any], ...]
    receipts: tuple[dict[str, Any], ...]
    irrelevant_facts: tuple[str, ...]
    observation_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        current = [
            g
            for g in self.grant_observations
            if g.get("observation_freshness", "current") == "current"
        ]
        stale = [
            g
            for g in self.grant_observations
            if g.get("observation_freshness") == "stale"
        ]
        return {
            "agent": self.agent,
            "grant_observations": [dict(g) for g in self.grant_observations],
            "receipts": [dict(r) for r in self.receipts],
            "irrelevant_facts": list(self.irrelevant_facts),
            "observation_ids": list(self.observation_ids),
            "has_current_grant_observation": bool(current),
            "has_stale_grant_observation": bool(stale),
        }


def decision_time_observation_freshness(
    obs: dict[str, Any],
    *,
    authoritative_version: int | None,
    relevant_grant_id: str | None = None,
) -> str:
    """Freshness of one grant observation at a decision point.

    Delivery-time labels are not the audit's freshness. An explicit stale
    delivery stays stale. A live delivery is current only when its
    ``owner_version`` equals the authoritative grant version retained
    immediately before the decision. When ``relevant_grant_id`` is set, only
    that grant's observation is version-checked.
    """
    delivered = obs.get("delivered_freshness", obs.get("observation_freshness", "current"))
    if delivered == "stale":
        return "stale"
    if relevant_grant_id is not None and obs.get("grant_id") != relevant_grant_id:
        return "current"
    if authoritative_version is None:
        return "stale"
    observed = obs.get("owner_version")
    if observed is None:
        return "stale"
    try:
        if int(observed) != int(authoritative_version):
            return "stale"
    except (TypeError, ValueError):
        return "stale"
    return "current"


def annotate_decision_freshness(
    knowledge: dict[str, Any],
    *,
    grant_id: str,
    authoritative_version: int,
) -> dict[str, Any]:
    """Copy local knowledge with freshness judged at the decision point."""
    observations: list[dict[str, Any]] = []
    current = 0
    stale = 0
    for raw in knowledge.get("grant_observations") or []:
        obs = dict(raw)
        if "delivered_freshness" not in obs:
            obs["delivered_freshness"] = obs.get("observation_freshness", "current")
        fresh = decision_time_observation_freshness(
            obs,
            authoritative_version=authoritative_version,
            relevant_grant_id=grant_id,
        )
        obs["observation_freshness"] = fresh
        observations.append(obs)
        if fresh == "stale":
            stale += 1
        else:
            current += 1
    updated = dict(knowledge)
    updated["grant_observations"] = observations
    updated["has_current_grant_observation"] = current > 0
    updated["has_stale_grant_observation"] = stale > 0
    updated["authoritative_grant_version_at_decision"] = authoritative_version
    return updated
