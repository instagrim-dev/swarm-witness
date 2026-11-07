"""Independent conclusion evaluator.

The evaluator learns from the simulation trace *after* decisions, using
authoritative owner state and committed effects. It does not reuse the policy
predicate to invent expected outcomes.
"""

from __future__ import annotations

from typing import Any

from swarm_witness.audit_diagnosis import diagnosis
from swarm_witness.conclusion_classes import classify_conclusion
from swarm_witness.multi_agent_sim.events import decision_time_observation_freshness
from swarm_witness.multi_agent_sim.scheduler import ClaimOutcome, SimulationResult


def _freshness(obs: dict[str, Any], claim: ClaimOutcome) -> str:
    """Recheck the relevant observation against the pre-decision grant version."""
    return decision_time_observation_freshness(
        obs,
        authoritative_version=claim.authoritative_grant_version_at_decision,
        relevant_grant_id=claim.grant_id,
    )


def _observation_denominator(claim: ClaimOutcome) -> dict[str, Any]:
    """Explicit observation denominators retained for auditability.

    Counts use decision-time freshness, not the label assigned at delivery.
    """
    knowledge = claim.local_knowledge
    grant_obs = knowledge.get("grant_observations") or []
    fresh = [_freshness(obs, claim) for obs in grant_obs]
    present: list[str] = []
    for freshness in fresh:
        label = (
            "stale_grant_observation"
            if freshness == "stale"
            else "current_grant_observation"
        )
        if label not in present:
            present.append(label)
    return {
        "required_discriminators": ["current_grant_observation"],
        "required_count": 1,
        "present_discriminators": present,
        "present_count": len(present),
        "current_grant_observation_count": sum(1 for f in fresh if f == "current"),
        "stale_grant_observation_count": sum(1 for f in fresh if f == "stale"),
        "authoritative_grant_version_at_decision": (
            claim.authoritative_grant_version_at_decision
        ),
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
        return _evaluated(
            claim,
            denominators,
            assessment="unsupported",
            classified=classified,
            property_holds=None,
            diag=diag,
            reason=(
                "agent lacked current grant observation at decision; "
                "evaluator later inspected authoritative owner state without "
                "upgrading the agent-visible missing_evidence conclusion"
            ),
        )

    holds = claim.decision == claim.required_decision
    unauthorized_commit = bool(
        claim.committed_effect and claim.required_decision == "deny"
    )
    # Integrity is an input to evaluation, not implied by a populated mailbox.
    if claim.evidence_integrity != "authentic":
        if unauthorized_commit:
            # Fabricated evidence can still produce an independent effect-boundary
            # outcome when the ledger actually commits the unauthorized effect.
            failure_origin = "effect_boundary"
            effect_status = "committed"
            decision_status = "incorrect"
            classified = classify_conclusion(
                evidence_complete=True, property_holds=False
            )
            assessment = "enforcement_failed"
            property_holds: bool | None = False
        elif not holds:
            failure_origin = "evidence"
            effect_status = "committed" if claim.committed_effect else "prevented"
            decision_status = "incorrect"
            classified = classify_conclusion(
                evidence_complete=True, property_holds=False
            )
            assessment = "enforcement_failed"
            property_holds = False
        else:
            # Misbound evidence that happens to match the required decision
            # is not an authentic supported conclusion.
            failure_origin = "evidence"
            effect_status = "committed" if claim.committed_effect else "prevented"
            decision_status = "unknown"
            classified = classify_conclusion(
                evidence_complete=False, property_holds=None
            )
            assessment = "unsupported"
            property_holds = None
        diag = diagnosis(
            evidence_status="misbound",
            decision_status=decision_status,  # type: ignore[arg-type]
            effect_status=effect_status,  # type: ignore[arg-type]
            failure_origin=failure_origin,  # type: ignore[arg-type]
        )
        return _evaluated(
            claim,
            denominators,
            assessment=assessment,
            classified=classified,
            property_holds=property_holds,
            diag=diag,
            reason=(
                "grant observation is misbound; evidence integrity is separate "
                f"from freshness and completeness; "
                f"evidence_integrity={claim.evidence_integrity}; "
                f"decision={claim.decision} required={claim.required_decision} "
                f"committed_effect={claim.committed_effect} "
                f"effect_settlement={claim.effect_settlement} "
                f"effect_refusal_reason={claim.effect_refusal_reason}"
            ),
        )

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
    if unauthorized_commit:
        failure_origin = "effect_boundary"
        effect_status = "committed"
    elif claim.committed_effect:
        effect_status = "committed"
    else:
        effect_status = "prevented"
        # Wrong local allow that the ledger refused remains a decision-policy
        # failure with a prevented effect — not an executed unauthorized effect.
        if (
            claim.decision == "allow"
            and claim.required_decision == "deny"
            and claim.effect_settlement == "refused"
        ):
            failure_origin = "decision_policy"

    diag = diagnosis(
        evidence_status="authentic",
        decision_status=decision_status,  # type: ignore[arg-type]
        effect_status=effect_status,  # type: ignore[arg-type]
        failure_origin=failure_origin,  # type: ignore[arg-type]
    )
    return _evaluated(
        claim,
        denominators,
        assessment=assessment,
        classified=classified,
        property_holds=holds,
        diag=diag,
        reason=classified["reason"]
        + (
            f"; evidence_integrity={claim.evidence_integrity}; "
            f"decision={claim.decision} required={claim.required_decision} "
            f"committed_effect={claim.committed_effect} "
            f"effect_settlement={claim.effect_settlement}"
        ),
    )


def _evaluated(
    claim: ClaimOutcome,
    denominators: dict[str, Any],
    *,
    assessment: str,
    classified: dict[str, Any],
    property_holds: bool | None,
    diag: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "call_id": claim.call_id,
        "agent": claim.agent,
        "grant_id": claim.grant_id,
        "decision": claim.decision,
        "committed_effect": claim.committed_effect,
        "effect_settlement": claim.effect_settlement,
        "effect_refusal_reason": claim.effect_refusal_reason,
        "effect_boundary_enforced": claim.effect_boundary_enforced,
        "evidence_integrity": claim.evidence_integrity,
        "authoritative_grant_version_at_decision": (
            claim.authoritative_grant_version_at_decision
        ),
        "authoritative_owner_state": claim.authoritative_owner_state,
        "required_decision": claim.required_decision,
        "local_knowledge_at_decision": claim.local_knowledge,
        "evaluator_learned_afterward": {
            "authoritative_owner_state": claim.authoritative_owner_state,
            "committed_effect": claim.committed_effect,
            "effect_settlement": claim.effect_settlement,
            "required_decision": claim.required_decision,
            "evidence_integrity": claim.evidence_integrity,
            "authoritative_grant_version_at_decision": (
                claim.authoritative_grant_version_at_decision
            ),
            "one_use_effect_count": claim.authoritative_owner_state.get(
                "committed_effect_count"
            ),
        },
        "observation_denominators": denominators,
        "assessment": assessment,
        "conclusion_class": classified["conclusion_class"],
        "finding_label": classified["finding_label"],
        "property_holds": property_holds,
        "diagnosis": diag,
        "reason": reason,
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
