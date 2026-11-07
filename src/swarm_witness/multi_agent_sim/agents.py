"""Per-agent local observation mailboxes (independent of the authoritative ledger)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from swarm_witness.multi_agent_sim.events import AgentId, LocalKnowledge, SIM_AGENTS


@dataclass
class AgentMailbox:
    """Locally delivered observations for one principal."""

    agent: AgentId
    grant_observations: dict[str, dict[str, Any]] = field(default_factory=dict)
    # grant_id -> latest delivered grant observation payload
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    irrelevant_facts: list[str] = field(default_factory=list)
    observation_ids: list[str] = field(default_factory=list)

    def deliver_grant_observation(
        self,
        *,
        observation_id: str,
        grant: dict[str, Any],
        source_event_id: str,
        freshness: str = "current",
    ) -> None:
        payload = dict(grant)
        payload["source_event_id"] = source_event_id
        payload["observation_id"] = observation_id
        # Delivery label. Decision-time freshness is rechecked against the
        # authoritative grant version and may differ from this value.
        payload["delivered_freshness"] = freshness
        payload["observation_freshness"] = freshness
        self.grant_observations[grant["grant_id"]] = payload
        self.observation_ids.append(observation_id)

    def deliver_receipt(
        self,
        *,
        observation_id: str,
        receipt: dict[str, Any],
        source_event_id: str,
    ) -> None:
        payload = dict(receipt)
        payload["source_event_id"] = source_event_id
        payload["observation_id"] = observation_id
        self.receipts[receipt["receipt_id"]] = payload
        self.observation_ids.append(observation_id)

    def deliver_irrelevant(self, *, observation_id: str, fact: str) -> None:
        self.irrelevant_facts.append(fact)
        self.observation_ids.append(observation_id)

    def knowledge(self) -> LocalKnowledge:
        return LocalKnowledge(
            agent=self.agent,
            grant_observations=tuple(
                dict(v) for _, v in sorted(self.grant_observations.items())
            ),
            receipts=tuple(dict(v) for _, v in sorted(self.receipts.items())),
            irrelevant_facts=tuple(self.irrelevant_facts),
            observation_ids=tuple(self.observation_ids),
        )

    def observed_grant(self, grant_id: str) -> dict[str, Any] | None:
        g = self.grant_observations.get(grant_id)
        return None if g is None else dict(g)


@dataclass
class AgentStore:
    mailboxes: dict[AgentId, AgentMailbox] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.mailboxes:
            self.mailboxes = {a: AgentMailbox(agent=a) for a in SIM_AGENTS}

    def get(self, agent: AgentId) -> AgentMailbox:
        return self.mailboxes[agent]
