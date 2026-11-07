"""Scenario generation for the multi-agent simulator.

Scenario specs are data: schedules and expected properties live here; policy
and oracle implementations live elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from swarm_witness.multi_agent_sim.scheduler import Schedule, ScheduleStep

Role = Literal[
    "interleaving",
    "revocation_late_observation",
    "reference_vs_mutant",
    "paired_world",
    "negative_control",
]


@dataclass(frozen=True)
class ScenarioSpec:
    case_id: str
    name: str
    role: Role
    schedule: Schedule
    policy_id: str
    # Expected properties checked by the protocol scorer (not by the policy).
    expected: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "role": self.role,
            "policy_id": self.policy_id,
            "schedule": self.schedule.to_dict(),
            "expected": dict(self.expected),
        }


GRANT = "grant-shared"


def _seed_shared_grant_steps(*, owner: str = "A") -> list[ScheduleStep]:
    return [
        ScheduleStep(
            kind="grant_issue",
            actor=owner,  # type: ignore[arg-type]
            grant_id=GRANT,
            note="issue shared one-use grant",
        ),
        ScheduleStep(
            kind="delegation",
            actor="ledger",
            grant_id=GRANT,
            target="B",
            note="assign B",
        ),
        ScheduleStep(
            kind="delegation",
            actor="ledger",
            grant_id=GRANT,
            target="C",
            note="assign C",
        ),
    ]


def interleaving_a_first(seed: int = 101) -> ScenarioSpec:
    """Competing claims: A observes+claims before B."""
    steps = _seed_shared_grant_steps()
    steps.extend(
        [
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="A",
                note="A receives current grant",
            ),
            ScheduleStep(
                kind="claim",
                actor="A",
                grant_id=GRANT,
                call_id="a-claim",
                note="A claims first",
            ),
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="B",
                note="B receives post-spend grant",
            ),
            ScheduleStep(
                kind="claim",
                actor="B",
                grant_id=GRANT,
                call_id="b-claim",
                note="B claims after A spent",
            ),
        ]
    )
    return ScenarioSpec(
        case_id="interleave_a_first_reference",
        name="Shared grant contention: A-first interleaving (reference)",
        role="interleaving",
        schedule=Schedule(
            schedule_id="sched-a-first",
            seed=seed,
            steps=tuple(steps),
            description="A observes and claims before B; one-use safety holds",
        ),
        policy_id="reference",
        expected={
            "winners": ["A"],
            "claim_decisions": {"a-claim": "allow", "b-claim": "deny"},
            "committed_effects": {"a-claim": True, "b-claim": False},
            "one_use_ok": True,
            "claim_conclusions": {
                "a-claim": "supported",
                "b-claim": "supported",
            },
        },
    )


def interleaving_b_first(seed: int = 202) -> ScenarioSpec:
    """Competing claims: B observes+claims before A — materially different winner."""
    steps = _seed_shared_grant_steps()
    steps.extend(
        [
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="B",
                note="B receives current grant first",
            ),
            ScheduleStep(
                kind="claim",
                actor="B",
                grant_id=GRANT,
                call_id="b-claim",
                note="B claims first",
            ),
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="A",
                note="A receives post-spend grant",
            ),
            ScheduleStep(
                kind="claim",
                actor="A",
                grant_id=GRANT,
                call_id="a-claim",
                note="A claims after B spent",
            ),
        ]
    )
    return ScenarioSpec(
        case_id="interleave_b_first_reference",
        name="Shared grant contention: B-first interleaving (reference)",
        role="interleaving",
        schedule=Schedule(
            schedule_id="sched-b-first",
            seed=seed,
            steps=tuple(steps),
            description="B observes and claims before A; winner differs from A-first",
        ),
        policy_id="reference",
        expected={
            "winners": ["B"],
            "claim_decisions": {"b-claim": "allow", "a-claim": "deny"},
            "committed_effects": {"b-claim": True, "a-claim": False},
            "one_use_ok": True,
            "claim_conclusions": {
                "b-claim": "supported",
                "a-claim": "supported",
            },
        },
    )


def _toctou_contention_steps() -> list[ScheduleStep]:
    """Both assignees observe active state before either claims (classic race)."""
    steps = _seed_shared_grant_steps()
    steps.extend(
        [
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="A",
                note="A observes active grant",
            ),
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="B",
                note="B observes active grant before either claim",
            ),
            ScheduleStep(
                kind="claim",
                actor="A",
                grant_id=GRANT,
                call_id="a-claim",
                note="A claims with active local observation",
            ),
            ScheduleStep(
                kind="claim",
                actor="B",
                grant_id=GRANT,
                call_id="b-claim",
                note="B claims with stale-active local observation (no refresh)",
            ),
        ]
    )
    return steps


def revocation_late_observation(seed: int = 303) -> ScenarioSpec:
    """Revoke then late/stale active observation; fresh view still denies.

    Schedule: issue → observe-to-C (active) → revoke → deliver stale active to B →
    B claims (local allow; authoritative ledger refuses commit under reference) →
    C receives fresh revoked observation and denies.
    """
    steps = _seed_shared_grant_steps()
    steps.extend(
        [
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="C",
                note="C observes active grant before revoke",
            ),
            ScheduleStep(
                kind="revocation",
                actor="ledger",
                grant_id=GRANT,
                note="owner revokes grant",
            ),
            # Late/stale observation: B is told the grant is still active.
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="B",
                stale_grant={
                    "grant_id": GRANT,
                    "owner": "A",
                    "state": "active",
                    "epoch": "epoch-1",
                    "owner_version": 1,
                    "assignees": ["A", "B", "C"],
                    "spent": False,
                },
                note="late stale active observation delivered to B",
            ),
            ScheduleStep(
                kind="claim",
                actor="B",
                grant_id=GRANT,
                call_id="b-late",
                note="B claims on stale active observation after revoke",
            ),
            # Fresh observation to C after revoke (discriminating).
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="C",
                note="C receives post-revoke observation",
            ),
            ScheduleStep(
                kind="claim",
                actor="C",
                grant_id=GRANT,
                call_id="c-fresh",
                note="C claims with fresh revoked observation",
            ),
        ]
    )
    return ScenarioSpec(
        case_id="revocation_late_observation_reference",
        name="Revocation with late/stale observation (reference)",
        role="revocation_late_observation",
        schedule=Schedule(
            schedule_id="sched-revoke-late",
            seed=seed,
            steps=tuple(steps),
            description=(
                "After revoke, B acts on stale active observation (local allow "
                "vs authoritative deny); C acts on fresh revoked observation"
            ),
        ),
        policy_id="reference",
        expected={
            # Local allow on stale active diverges from authoritative deny, but
            # the enforcing ledger refuses settlement — bad decision ≠ commit.
            "claim_decisions": {"b-late": "allow", "c-fresh": "deny"},
            "committed_effects": {"b-late": False, "c-fresh": False},
            "effect_settlements": {"b-late": "refused", "c-fresh": "not_attempted"},
            "claim_conclusions": {
                "b-late": "failed_enforcement",  # decision != authoritative required
                "c-fresh": "supported",
            },
            "authoritative_final_state": "revoked",
        },
    )


def reference_contention_arm(seed: int = 404) -> ScenarioSpec:
    """Reference on TOCTOU contention: first commit allowed; second effect refused."""
    steps = _toctou_contention_steps()
    return ScenarioSpec(
        case_id="reference_contention_one_use",
        name="Reference monitor: TOCTOU contention preserves one-use via effect boundary",
        role="reference_vs_mutant",
        schedule=Schedule(
            schedule_id="sched-toctou-contend",
            seed=seed,
            steps=tuple(steps),
            description=(
                "Both A and B observe active before either claims; reference "
                "commits A and refuses B at the authoritative effect boundary"
            ),
        ),
        policy_id="reference",
        expected={
            # Local views are both active at claim time, so both *decisions* allow;
            # only the first effect commits under the enforcing ledger.
            "claim_decisions": {"a-claim": "allow", "b-claim": "allow"},
            "committed_effects": {"a-claim": True, "b-claim": False},
            "effect_settlements": {"a-claim": "committed", "b-claim": "refused"},
            "one_use_ok": True,
            "claim_conclusions": {
                "a-claim": "supported",
                "b-claim": "failed_enforcement",
            },
        },
    )


def mutant_contention_arm(seed: int = 404) -> ScenarioSpec:
    """Identical TOCTOU schedule; mutant bypasses effect boundary → double commit."""
    steps = _toctou_contention_steps()
    return ScenarioSpec(
        case_id="mutant_ignore_spend_contention",
        name="Mutant ignore-spend on identical TOCTOU schedule (counterexample)",
        role="reference_vs_mutant",
        schedule=Schedule(
            schedule_id="sched-toctou-contend",
            seed=seed,
            steps=tuple(steps),
            description=(
                "Same TOCTOU schedule/seed as reference contention; mutant "
                "disables effect-boundary enforcement and double-commits"
            ),
        ),
        policy_id="mutant_ignore_spend",
        expected={
            "claim_decisions": {"a-claim": "allow", "b-claim": "allow"},
            "committed_effects": {"a-claim": True, "b-claim": True},
            "effect_settlements": {"a-claim": "committed", "b-claim": "committed"},
            "one_use_ok": False,
            "claim_conclusions": {
                "a-claim": "supported",
                "b-claim": "failed_enforcement",
            },
            "counterexample": True,
        },
    )


def paired_world_blind(world: Literal["active", "revoked"], seed: int = 505) -> ScenarioSpec:
    """Paired worlds with identical agent-visible evidence until discrimination."""
    steps: list[ScheduleStep] = [
        ScheduleStep(
            kind="grant_issue",
            actor="A",
            grant_id=GRANT,
            note="issue grant",
        ),
        ScheduleStep(
            kind="delegation",
            actor="ledger",
            grant_id=GRANT,
            target="B",
        ),
    ]
    if world == "revoked":
        steps.append(
            ScheduleStep(kind="revocation", actor="ledger", grant_id=GRANT, note="world B revoke")
        )
    # Agent B claims without any grant observation — worlds indistinguishable.
    steps.append(
        ScheduleStep(
            kind="claim",
            actor="B",
            grant_id=GRANT,
            call_id="b-blind",
            note="blind claim; worlds share empty local evidence",
        )
    )
    return ScenarioSpec(
        case_id=f"paired_world_{world}_blind",
        name=f"Paired world ({world}) blind claim — missing_evidence",
        role="paired_world",
        schedule=Schedule(
            schedule_id=f"sched-pair-{world}-blind",
            seed=seed,
            steps=tuple(steps),
            description="No current grant observation delivered before claim",
        ),
        policy_id="reference",
        expected={
            "claim_conclusions": {"b-blind": "missing_evidence"},
            "committed_effects": {"b-blind": False},
            "indistinguishable_agent_view": True,
        },
    )


def paired_world_irrelevant(world: Literal["active", "revoked"], seed: int = 506) -> ScenarioSpec:
    """Irrelevant observation must not upgrade missing_evidence."""
    steps: list[ScheduleStep] = [
        ScheduleStep(kind="grant_issue", actor="A", grant_id=GRANT),
        ScheduleStep(kind="delegation", actor="ledger", grant_id=GRANT, target="B"),
    ]
    if world == "revoked":
        steps.append(ScheduleStep(kind="revocation", actor="ledger", grant_id=GRANT))
    steps.extend(
        [
            ScheduleStep(
                kind="irrelevant_deliver",
                actor="scheduler",
                target="B",
                irrelevant_fact="receipt_print_color=blue",
                note="irrelevant fact only",
            ),
            ScheduleStep(
                kind="claim",
                actor="B",
                grant_id=GRANT,
                call_id="b-irr",
                note="irrelevant observation does not discriminate",
            ),
        ]
    )
    return ScenarioSpec(
        case_id=f"paired_world_{world}_irrelevant",
        name=f"Paired world ({world}) + irrelevant observation stays missing_evidence",
        role="negative_control",
        schedule=Schedule(
            schedule_id=f"sched-pair-{world}-irr",
            seed=seed,
            steps=tuple(steps),
            description="Irrelevant fact must not upgrade conclusion",
        ),
        policy_id="reference",
        expected={
            "claim_conclusions": {"b-irr": "missing_evidence"},
            "committed_effects": {"b-irr": False},
        },
    )


def paired_world_distinguished(
    world: Literal["active", "revoked"], seed: int = 507
) -> ScenarioSpec:
    """Distinguishing observation makes worlds separable."""
    steps: list[ScheduleStep] = [
        ScheduleStep(kind="grant_issue", actor="A", grant_id=GRANT),
        ScheduleStep(kind="delegation", actor="ledger", grant_id=GRANT, target="B"),
    ]
    if world == "revoked":
        steps.append(ScheduleStep(kind="revocation", actor="ledger", grant_id=GRANT))
    steps.extend(
        [
            ScheduleStep(
                kind="observation_deliver",
                actor="scheduler",
                grant_id=GRANT,
                target="B",
                note="discriminating current grant observation",
            ),
            ScheduleStep(
                kind="claim",
                actor="B",
                grant_id=GRANT,
                call_id="b-disc",
                note="claim after discriminating observation",
            ),
        ]
    )
    decision = "allow" if world == "active" else "deny"
    return ScenarioSpec(
        case_id=f"paired_world_{world}_distinguished",
        name=f"Paired world ({world}) with discriminating observation",
        role="paired_world",
        schedule=Schedule(
            schedule_id=f"sched-pair-{world}-disc",
            seed=seed,
            steps=tuple(steps),
            description="Independently delivered distinguishing observation",
        ),
        policy_id="reference",
        expected={
            "claim_decisions": {"b-disc": decision},
            "committed_effects": {"b-disc": world == "active"},
            "claim_conclusions": {"b-disc": "supported"},
        },
    )


def all_scenario_specs() -> list[ScenarioSpec]:
    return [
        interleaving_a_first(),
        interleaving_b_first(),
        revocation_late_observation(),
        reference_contention_arm(),
        mutant_contention_arm(),
        paired_world_blind("active"),
        paired_world_blind("revoked"),
        paired_world_irrelevant("active"),
        paired_world_irrelevant("revoked"),
        paired_world_distinguished("active"),
        paired_world_distinguished("revoked"),
    ]
