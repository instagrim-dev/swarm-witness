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
