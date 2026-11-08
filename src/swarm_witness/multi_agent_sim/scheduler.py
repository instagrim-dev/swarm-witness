"""Deterministic, replayable scheduler for controllable causal interleavings.

Delays, missing/reordered observations, and contended claims are schedule
artifacts — not live multihost concurrency guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from swarm_witness.multi_agent_sim.agents import AgentStore
from swarm_witness.multi_agent_sim.events import (
    AgentId,
    SimEvent,
    annotate_decision_freshness,
)
from swarm_witness.multi_agent_sim.ledger import AuthoritativeLedger
from swarm_witness.multi_agent_sim.oracle import (
    authoritative_required_decision,
    oracle_one_use_holds,
)
from swarm_witness.multi_agent_sim.policy import Policy, decision_record

StepKind = Literal[
    "grant_issue",
    "observation_deliver",
    "irrelevant_deliver",
    "delegation",
    "revocation",
    "claim",
    "receipt_deliver",
    "receipt_replay",
]


@dataclass(frozen=True)
class ScheduleStep:
    """One scheduled action in a deterministic interleaving."""

    kind: StepKind
    actor: AgentId | Literal["ledger", "scheduler"]
    grant_id: str | None = None
    target: AgentId | None = None  # observation/receipt recipient or delegate
    call_id: str | None = None
    use_foreign_receipt: bool = False
    foreign_receipt_from: AgentId | None = None
    irrelevant_fact: str | None = None
    # Optional stale observation payload override (adversarial / late delivery).
    stale_grant: dict[str, Any] | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "actor": self.actor,
            "grant_id": self.grant_id,
            "target": self.target,
            "call_id": self.call_id,
            "use_foreign_receipt": self.use_foreign_receipt,
            "foreign_receipt_from": self.foreign_receipt_from,
            "irrelevant_fact": self.irrelevant_fact,
            "stale_grant": None if self.stale_grant is None else dict(self.stale_grant),
            "note": self.note,
        }


@dataclass(frozen=True)
class Schedule:
    schedule_id: str
    seed: int
    steps: tuple[ScheduleStep, ...]
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "seed": self.seed,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class ClaimOutcome:
    call_id: str
    agent: AgentId
    grant_id: str
    decision: str
    required_decision: str
    committed_effect: bool
    effect: dict[str, Any] | None
    local_knowledge: dict[str, Any]
    authoritative_owner_state: dict[str, Any]
    decision_event_id: str
    policy_id: str
    local_evidence_complete: bool
    use_foreign_receipt: bool
    # Grant version captured immediately before this decision (pre-commit).
    authoritative_grant_version_at_decision: int
    # authentic | misbound | missing. Independent of freshness and completeness.
    evidence_integrity: str
    effect_settlement: str = "not_attempted"
    effect_refusal_reason: str | None = None
    effect_boundary_enforced: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "agent": self.agent,
            "grant_id": self.grant_id,
            "decision": self.decision,
            "required_decision": self.required_decision,
            "committed_effect": self.committed_effect,
            "effect": None if self.effect is None else dict(self.effect),
            "local_knowledge_at_decision": self.local_knowledge,
            "authoritative_owner_state": self.authoritative_owner_state,
            "decision_event_id": self.decision_event_id,
            "policy_id": self.policy_id,
            "local_evidence_complete": self.local_evidence_complete,
            "use_foreign_receipt": self.use_foreign_receipt,
            "authoritative_grant_version_at_decision": (
                self.authoritative_grant_version_at_decision
            ),
            "evidence_integrity": self.evidence_integrity,
            "effect_settlement": self.effect_settlement,
            "effect_refusal_reason": self.effect_refusal_reason,
            "effect_boundary_enforced": self.effect_boundary_enforced,
        }


@dataclass
class SimulationResult:
    schedule: Schedule
    policy_id: str
    events: list[SimEvent] = field(default_factory=list)
    claims: list[ClaimOutcome] = field(default_factory=list)
    final_owner_state: dict[str, Any] = field(default_factory=dict)
    one_use_holds: dict[str, bool] = field(default_factory=dict)

    def relevant_trace(self) -> dict[str, Any]:
        """Stable projection used for replay equality checks."""
        return {
            "schedule_id": self.schedule.schedule_id,
            "seed": self.schedule.seed,
            "policy_id": self.policy_id,
            "events": [
                {
                    "event_id": e.event_id,
                    "kind": e.kind,
                    "actor": e.actor,
                    "causal_predecessor": e.causal_predecessor,
                    "epoch": e.epoch,
                    "owner_version": e.owner_version,
                    "observed_source": e.observed_source,
                    "payload": e.payload,
                }
                for e in self.events
            ],
            "claims": [c.to_dict() for c in self.claims],
            "one_use_holds": dict(self.one_use_holds),
            "final_owner_state": dict(self.final_owner_state),
        }


class Simulator:
    """Execute a schedule under a chosen policy against an authoritative ledger."""

    def __init__(self, schedule: Schedule, policy: Policy) -> None:
        self.schedule = schedule
        self.policy = policy
        self.ledger = AuthoritativeLedger()
        self.agents = AgentStore()
        self.events: list[SimEvent] = []
        self.claims: list[ClaimOutcome] = []
        self._seq = 0
        self._last_event_id: str | None = None
        self._epoch = "epoch-1"

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        # Seed is mixed into ids so different schedules cannot collide on identity.
        return f"{prefix}-{self.schedule.seed}-{self._seq:04d}"

    def _record(
        self,
        kind: str,
        actor: str,
        *,
        payload: dict[str, Any],
        observed_source: str | None = None,
        owner_version: int | None = None,
    ) -> SimEvent:
        event = SimEvent(
            event_id=self._next_id("evt"),
            kind=kind,  # type: ignore[arg-type]
            actor=actor,  # type: ignore[arg-type]
            causal_predecessor=self._last_event_id,
            epoch=self._epoch,
            owner_version=(
                self.ledger.owner_version if owner_version is None else owner_version
            ),
            observed_source=observed_source,
            payload=payload,
        )
        self.events.append(event)
        self._last_event_id = event.event_id
        return event

    def run(self) -> SimulationResult:
        grant_ids: set[str] = set()
        for step in self.schedule.steps:
            if step.grant_id:
                grant_ids.add(step.grant_id)
            self._apply_step(step)

        final_state = {
            gid: self.ledger.owner_state_projection(gid) for gid in sorted(grant_ids)
        }
        one_use = {gid: oracle_one_use_holds(self.ledger, gid) for gid in sorted(grant_ids)}
        return SimulationResult(
            schedule=self.schedule,
            policy_id=self.policy.policy_id,
            events=list(self.events),
            claims=list(self.claims),
            final_owner_state=final_state,
            one_use_holds=one_use,
        )

    def _apply_step(self, step: ScheduleStep) -> None:
        if step.kind == "grant_issue":
            assert step.grant_id and step.actor in {"A", "B", "C"}
            snap = self.ledger.issue_grant(
                step.grant_id, owner=step.actor, epoch=self._epoch  # type: ignore[arg-type]
            )
            self._record(
                "grant_issue",
                "ledger",
                payload={"grant": snap.to_dict(), "note": step.note},
            )
            return

        if step.kind == "delegation":
            assert step.grant_id and step.target
            snap = self.ledger.delegate(step.grant_id, step.target)
            self._record(
                "delegation",
                "ledger",
                payload={
                    "grant_id": step.grant_id,
                    "delegate": step.target,
                    "grant": snap.to_dict(),
                    "note": step.note,
                },
            )
            return

        if step.kind == "revocation":
            assert step.grant_id
            snap = self.ledger.revoke(step.grant_id)
            self._record(
                "revocation",
                "ledger",
                payload={"grant": snap.to_dict(), "note": step.note},
            )
            return

        if step.kind == "observation_deliver":
            assert step.grant_id and step.target
            if step.stale_grant is not None:
                grant_payload = dict(step.stale_grant)
                freshness = "stale"
            else:
                grant_payload = self.ledger.snapshot(step.grant_id).to_dict()
                freshness = "current"
            obs_id = self._next_id("obs")
            source = self._record(
                "observation_deliver",
                "scheduler",
                payload={
                    "target": step.target,
                    "grant": grant_payload,
                    "observation_id": obs_id,
                    "stale": freshness == "stale",
                    "observation_freshness": freshness,
                    "note": step.note,
                },
                observed_source="authoritative_ledger"
                if freshness == "current"
                else "stale_or_adversarial",
            )
            self.agents.get(step.target).deliver_grant_observation(
                observation_id=obs_id,
                grant=grant_payload,
                source_event_id=source.event_id,
                freshness=freshness,
            )
            return

        if step.kind == "irrelevant_deliver":
            assert step.target and step.irrelevant_fact
            obs_id = self._next_id("irr")
            self._record(
                "observation_deliver",
                "scheduler",
                payload={
                    "target": step.target,
                    "irrelevant_fact": step.irrelevant_fact,
                    "observation_id": obs_id,
                    "kind_detail": "irrelevant",
                    "note": step.note,
                },
                observed_source="irrelevant",
            )
            self.agents.get(step.target).deliver_irrelevant(
                observation_id=obs_id, fact=step.irrelevant_fact
            )
            return

        if step.kind == "receipt_deliver" or step.kind == "receipt_replay":
            assert step.target and step.call_id
            receipt_id = f"receipt-{step.call_id}"
            receipt = self.ledger.receipts.get(receipt_id)
            if receipt is None:
                # Allow delivering a synthetic foreign receipt template.
                receipt = {
                    "receipt_id": receipt_id,
                    "agent": step.foreign_receipt_from or step.actor,
                    "grant_id": step.grant_id,
                    "call_id": step.call_id,
                }
            obs_id = self._next_id("rcpt")
            kind = "receipt_deliver" if step.kind == "receipt_deliver" else "receipt_replay"
            source = self._record(
                kind,
                "scheduler",
                payload={
                    "target": step.target,
                    "receipt": dict(receipt),
                    "observation_id": obs_id,
                    "note": step.note,
                },
                observed_source="receipt",
            )
            self.agents.get(step.target).deliver_receipt(
                observation_id=obs_id,
                receipt=dict(receipt),
                source_event_id=source.event_id,
            )
            return

        if step.kind == "claim":
            self._apply_claim(step)
            return

        raise ValueError(f"unknown schedule step kind: {step.kind!r}")

    def _apply_claim(self, step: ScheduleStep) -> None:
        assert step.grant_id and step.call_id and step.actor in {"A", "B", "C"}
        agent: AgentId = step.actor  # type: ignore[assignment]
        mailbox = self.agents.get(agent)
        # Retain authority before the decision and before any commit bumps it.
        authoritative_version = self.ledger.snapshot(step.grant_id).owner_version
        observed = mailbox.observed_grant(step.grant_id)
        evidence_integrity = self.ledger.evidence_integrity(observed, step.grant_id)
        knowledge = annotate_decision_freshness(
            mailbox.knowledge().to_dict(),
            grant_id=step.grant_id,
            authoritative_version=authoritative_version,
        )
        rec = decision_record(
            self.policy,
            mailbox,
            agent=agent,
            grant_id=step.grant_id,
            use_foreign_receipt=step.use_foreign_receipt,
        )
        required = authoritative_required_decision(
            self.ledger,
            agent=agent,
            grant_id=step.grant_id,
            use_foreign_receipt=step.use_foreign_receipt,
        )
        decision = rec["decision"]
        decision_evt = self._record(
            "claim",
            agent,
            payload={
                "call_id": step.call_id,
                "grant_id": step.grant_id,
                "decision": decision,
                "required_decision": required,
                "policy_id": self.policy.policy_id,
                "local_evidence_complete": rec["local_evidence_complete"],
                "use_foreign_receipt": step.use_foreign_receipt,
                "authoritative_grant_version_at_decision": authoritative_version,
                "evidence_integrity": evidence_integrity,
                "local_knowledge_at_decision": knowledge,
                "note": step.note,
            },
            observed_source="local_mailbox",
        )

        # Effect attempt is always recorded separately from the decision.
        self._record(
            "effect_attempt",
            agent,
            payload={
                "call_id": step.call_id,
                "grant_id": step.grant_id,
                "decision": decision,
                "decision_event_id": decision_evt.event_id,
            },
        )

        committed = False
        effect: dict[str, Any] | None = None
        enforce = bool(getattr(self.policy, "enforce_effect_boundary", True))
        settlement = "not_attempted"
        refusal_reason: str | None = None
        # Settlement rule: only an allow decision may attempt commit. Reference
        # arms enforce the authoritative spent/revoked boundary so a bad
        # decision is not automatically an unauthorized committed effect.
        # Mutant arms may disable enforcement to surface concrete double-commit
        # counterexamples — still recorded as separate decision vs effect fields.
        if decision == "allow":
            effect, refusal_reason = self.ledger.commit_effect(
                grant_id=step.grant_id,
                agent=agent,
                call_id=step.call_id,
                decision_event_id=decision_evt.event_id,
                enforce=enforce,
            )
            if effect is not None:
                committed = True
                settlement = "committed"
                refusal_reason = None
                self._record(
                    "effect_settle",
                    "ledger",
                    payload={
                        "effect": dict(effect),
                        "committed_effect": True,
                        "effect_settlement": settlement,
                        "effect_boundary_enforced": enforce,
                        "decision_event_id": decision_evt.event_id,
                    },
                )
            else:
                settlement = "refused"
                self._record(
                    "effect_settle",
                    "ledger",
                    payload={
                        "call_id": step.call_id,
                        "grant_id": step.grant_id,
                        "committed_effect": False,
                        "effect_settlement": settlement,
                        "effect_refusal_reason": refusal_reason,
                        "effect_boundary_enforced": enforce,
                        "decision_event_id": decision_evt.event_id,
                    },
                )
        else:
            settlement = "not_attempted"
            refusal_reason = "decision_denied"
            self._record(
                "effect_settle",
                "ledger",
                payload={
                    "call_id": step.call_id,
                    "grant_id": step.grant_id,
                    "committed_effect": False,
                    "effect_settlement": settlement,
                    "effect_refusal_reason": refusal_reason,
                    "effect_boundary_enforced": enforce,
                    "decision_event_id": decision_evt.event_id,
                    "reason": "decision_denied",
                },
            )

        self.claims.append(
            ClaimOutcome(
                call_id=step.call_id,
                agent=agent,
                grant_id=step.grant_id,
                decision=decision,
                required_decision=required,
                committed_effect=committed,
                effect=effect,
                local_knowledge=knowledge,
                authoritative_owner_state=self.ledger.owner_state_projection(step.grant_id),
                decision_event_id=decision_evt.event_id,
                policy_id=self.policy.policy_id,
                local_evidence_complete=bool(rec["local_evidence_complete"]),
                use_foreign_receipt=step.use_foreign_receipt,
                authoritative_grant_version_at_decision=authoritative_version,
                evidence_integrity=evidence_integrity,
                effect_settlement=settlement,
                effect_refusal_reason=refusal_reason,
                effect_boundary_enforced=enforce,
            )
        )


def run_schedule(schedule: Schedule, policy: Policy) -> SimulationResult:
    return Simulator(schedule, policy).run()
