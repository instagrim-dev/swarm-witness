"""Independent conclusion evaluator.

The evaluator learns from the simulation trace *after* decisions, using
authoritative owner state and committed effects. It does not reuse the policy
predicate to invent expected outcomes.
"""

from __future__ import annotations

from typing import Any

from swarm_witness.audit_diagnosis import diagnosis
from swarm_witness.conclusion_classes import classify_conclusion
from swarm_witness.multi_agent_sim.scheduler import ClaimOutcome, SimulationResult


def _observation_denominator(claim: ClaimOutcome) -> dict[str, Any]:
    """Explicit observation denominators retained for auditability."""
    knowledge = claim.local_knowledge
    grant_obs = knowledge.get("grant_observations") or []
    return {
        "required_discriminators": ["current_grant_observation"],
        "required_count": 1,
        "present_discriminators": (
            ["current_grant_observation"] if claim.local_evidence_complete else []
        ),
        "present_count": 1 if claim.local_evidence_complete else 0,
        "irrelevant_count": len(knowledge.get("irrelevant_facts") or []),
        "receipt_count": len(knowledge.get("receipts") or []),
        "grant_observation_count": len(grant_obs),
        "observation_id_count": len(knowledge.get("observation_ids") or []),
    }


def evaluate_claim(claim: ClaimOutcome) -> dict[str, Any]:
    """Classify one claim using post-hoc evaluator knowledge."""
    denominators = _observation_denominator(claim)

    if not claim.local_evidence_complete:
        classified = classify_conclusion(
            evidence_complete=False, property_holds=None
        )
        diag = diagnosis(
            evidence_status="missing",
            decision_status="unknown",
            effect_status="prevented" if not claim.committed_effect else "committed",
            failure_origin="evidence",
        )
        return {
            "call_id": claim.call_id,
            "agent": claim.agent,
            "grant_id": claim.grant_id,
            "decision": claim.decision,
            "committed_effect": claim.committed_effect,
            "authoritative_owner_state": claim.authoritative_owner_state,
            "required_decision": claim.required_decision,
            "local_knowledge_at_decision": claim.local_knowledge,
            "evaluator_learned_afterward": {
                "authoritative_owner_state": claim.authoritative_owner_state,
                "committed_effect": claim.committed_effect,
                "required_decision": claim.required_decision,
            },
            "observation_denominators": denominators,
            "assessment": "unsupported",
            "conclusion_class": classified["conclusion_class"],
            "finding_label": classified["finding_label"],
            "property_holds": None,
            "diagnosis": diag,
            "reason": (
                "agent lacked current grant observation at decision; "
                "evaluator later inspected authoritative owner state without "
                "upgrading the agent-visible missing_evidence conclusion"
            ),
        }

    holds = claim.decision == claim.required_decision
    classified = classify_conclusion(evidence_complete=True, property_holds=holds)
    if holds:
        assessment = (
            "permission_justified"
            if claim.decision == "allow"
            else "permission_refuted"
        )
        decision_status = "correct"
        failure_origin = "none"
    else:
        assessment = "enforcement_failed"
        decision_status = "incorrect"
        failure_origin = "decision_policy"

    # Unauthorized committed effect is recorded separately from the decision.
    if claim.committed_effect and claim.required_decision == "deny":
        failure_origin = "effect_boundary"
        effect_status = "committed"
    elif claim.committed_effect:
        effect_status = "committed"
    else:
        effect_status = "prevented"

    diag = diagnosis(
        evidence_status="authentic",
        decision_status=decision_status,  # type: ignore[arg-type]
        effect_status=effect_status,  # type: ignore[arg-type]
        failure_origin=failure_origin,  # type: ignore[arg-type]
    )
    return {
        "call_id": claim.call_id,
        "agent": claim.agent,
        "grant_id": claim.grant_id,
        "decision": claim.decision,
        "committed_effect": claim.committed_effect,
        "authoritative_owner_state": claim.authoritative_owner_state,
        "required_decision": claim.required_decision,
        "local_knowledge_at_decision": claim.local_knowledge,
        "evaluator_learned_afterward": {
            "authoritative_owner_state": claim.authoritative_owner_state,
            "committed_effect": claim.committed_effect,
            "required_decision": claim.required_decision,
            "one_use_effect_count": claim.authoritative_owner_state.get(
                "committed_effect_count"
            ),
        },
        "observation_denominators": denominators,
        "assessment": assessment,
        "conclusion_class": classified["conclusion_class"],
        "finding_label": classified["finding_label"],
        "property_holds": holds,
        "diagnosis": diag,
        "reason": classified["reason"]
        + (
            f"; decision={claim.decision} required={claim.required_decision} "
            f"committed_effect={claim.committed_effect}"
        ),
    }


def evaluate_simulation(result: SimulationResult) -> dict[str, Any]:
    claim_evals = [evaluate_claim(c) for c in result.claims]
    one_use_ok = all(result.one_use_holds.values()) if result.one_use_holds else True
    return {
        "schedule_id": result.schedule.schedule_id,
        "seed": result.schedule.seed,
        "policy_id": result.policy_id,
        "claims": claim_evals,
        "one_use_holds": dict(result.one_use_holds),
        "one_use_ok": one_use_ok,
        "final_owner_state": result.final_owner_state,
        "event_count": len(result.events),
        "claim_count": len(result.claims),
    }
