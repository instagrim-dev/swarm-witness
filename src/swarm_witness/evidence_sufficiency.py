"""Evidence-sufficiency and three-way conclusion audit.

Worlds A (grant still valid) and B (grant revoked) can share the same old
receipt while current authority is unobserved. Without a discriminating
observation, conclusions stay ``missing_evidence``. With current grant state,
a correct gate yields ``supported`` (allow or deny as required). A broken gate
that allows under a revoked grant yields ``failed_enforcement``. Irrelevant
facts must not upgrade ``missing_evidence``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from swarm_witness.conclusion_classes import (
    classify_conclusion,
    required_permission_decision,
)

WorldId = Literal["A", "B"]
GrantState = Literal["active", "revoked"]
GateBehavior = Literal[
    "correct",
    "broken_allow_when_revoked",
    "broken_deny_when_active",
]
AssessmentKind = Literal[
    "unsupported",
    "permission_justified",
    "permission_refuted",
    "enforcement_failed",
]


OLD_RECEIPT = {
    "receipt_id": "receipt-prior-1",
    "call_id": "call-prior-1",
    "attestation": "ordinary-retry-first-edit/v1:synthetic-prior",
    "observed_at": "prior_episode",
}


@dataclass(frozen=True)
class World:
    world_id: WorldId
    grant_current: GrantState


@dataclass(frozen=True)
class ObservationSet:
    """What the auditor is allowed to see beyond the shared old receipt."""

    include_current_grant: bool = False
    include_irrelevant: bool = False
    observed_grant: GrantState | None = None
    irrelevant_fact: str | None = None


WORLDS: dict[str, World] = {
    "A": World(world_id="A", grant_current="active"),
    "B": World(world_id="B", grant_current="revoked"),
}


def _gate_decide(observed_grant: GrantState, *, behavior: GateBehavior) -> str:
    required = required_permission_decision(observed_grant)
    if behavior == "correct":
        return required
    if behavior == "broken_allow_when_revoked":
        # Defective enforcement: still allows after revocation.
        if observed_grant == "revoked":
            return "allow"
        return required
    if behavior == "broken_deny_when_active":
        # Defective enforcement: denies a still-valid grant.
        if observed_grant == "active":
            return "deny"
        return required
    raise ValueError(f"unknown gate behavior: {behavior!r}")


def assess_permission(
    world: World,
    observations: ObservationSet,
    *,
    visible_receipt: dict[str, Any] | None = None,
    gate_behavior: GateBehavior = "correct",
) -> dict[str, Any]:
    """Assess current-permission under a partial observation set and a gate.

    Returns both a legacy ``assessment`` string and a three-way
    ``conclusion_class`` (missing_evidence / failed_enforcement / supported).
    """
    receipt = dict(visible_receipt or OLD_RECEIPT)
    out: dict[str, Any] = {
        "world_id": world.world_id,
        "ground_truth_grant": world.grant_current,
        "visible_receipt": receipt,
        "observations": {
            "include_current_grant": observations.include_current_grant,
            "include_irrelevant": observations.include_irrelevant,
            "observed_grant": observations.observed_grant,
            "irrelevant_fact": observations.irrelevant_fact,
        },
        "gate_behavior": gate_behavior,
        "decision": None,
        "required_decision": None,
        "assessment": "unsupported",
        "justified_permission_claim": False,
        "conclusion_class": "missing_evidence",
        "finding_label": "unresolved",
        "property_holds": None,
        "reason": "",
    }

    if not observations.include_current_grant or observations.observed_grant is None:
        classified = classify_conclusion(
            evidence_complete=False, property_holds=None
        )
        out.update(
            {
                "conclusion_class": classified["conclusion_class"],
                "finding_label": classified["finding_label"],
                "property_holds": None,
                "reason": (
                    "old receipt available but current grant state unobserved; "
                    "permission claim is missing_evidence (Worlds A and B "
                    "indistinguishable from this evidence)"
                ),
            }
        )
        if observations.include_irrelevant:
            out["reason"] += (
                f"; irrelevant fact {observations.irrelevant_fact!r} does not "
                "discriminate"
            )
        return out

    observed = observations.observed_grant
    required = required_permission_decision(observed)
    decision = _gate_decide(observed, behavior=gate_behavior)
    holds = decision == required
    classified = classify_conclusion(
        evidence_complete=True, property_holds=holds
    )

    out["decision"] = decision
    out["required_decision"] = required
    out["conclusion_class"] = classified["conclusion_class"]
    out["finding_label"] = classified["finding_label"]
    out["property_holds"] = holds
    out["justified_permission_claim"] = decision == "allow" and holds

    if not holds:
        out["assessment"] = "enforcement_failed"
        out["reason"] = (
            f"evidence complete (grant={observed}); gate decided {decision!r} "
            f"but required {required!r} — failed_enforcement"
        )
        return out

    if decision == "allow":
        out["assessment"] = "permission_justified"
        out["reason"] = (
            "current grant observed active; correct allow — supported"
        )
    else:
        out["assessment"] = "permission_refuted"
        out["reason"] = (
            "current grant observed revoked; correct deny — supported "
            "(enforcement held; permission claim refuted)"
        )
    return out


def true_observation(world: World, *, irrelevant: bool = False) -> ObservationSet:
    return ObservationSet(
        include_current_grant=True,
        observed_grant=world.grant_current,
        include_irrelevant=irrelevant,
        irrelevant_fact="receipt_print_color=blue" if irrelevant else None,
    )


def blind_observation(*, irrelevant: bool = False) -> ObservationSet:
    return ObservationSet(
        include_current_grant=False,
        observed_grant=None,
        include_irrelevant=irrelevant,
        irrelevant_fact="receipt_print_color=blue" if irrelevant else None,
    )


def misbound_observation(world: World) -> ObservationSet:
    """Adversarial: report the opposite grant state as if observed."""
    flipped: GrantState = "revoked" if world.grant_current == "active" else "active"
    return ObservationSet(
        include_current_grant=True,
        observed_grant=flipped,
        include_irrelevant=False,
        irrelevant_fact=None,
    )


def run_protocol_cases() -> list[dict[str, Any]]:
    """Execute evidence-sufficiency + three-way conclusion cases."""
    cases: list[dict[str, Any]] = []

    # --- missing_evidence ---
    for wid in ("A", "B"):
        world = WORLDS[wid]
        result = assess_permission(world, blind_observation())
        cases.append(
            {
                "case_id": f"blind_world_{wid.lower()}",
                "name": f"World {wid} without current grant observation",
                "role": "indistinguishability",
                "expected_assessment": "unsupported",
                "expected_conclusion_class": "missing_evidence",
                "result": result,
            }
        )

    for wid in ("A", "B"):
        world = WORLDS[wid]
        result = assess_permission(world, blind_observation(irrelevant=True))
        cases.append(
            {
                "case_id": f"irrelevant_blind_{wid.lower()}",
                "name": f"World {wid} blind + irrelevant observation",
                "role": "negative_control",
                "expected_assessment": "unsupported",
                "expected_conclusion_class": "missing_evidence",
                "result": result,
            }
        )

    # --- supported (correct gate, complete evidence) ---
    for wid, expected in (("A", "permission_justified"), ("B", "permission_refuted")):
        world = WORLDS[wid]
        result = assess_permission(world, true_observation(world))
        cases.append(
            {
                "case_id": f"discriminated_world_{wid.lower()}",
                "name": f"World {wid} with current grant observed (correct gate)",
                "role": "discriminator",
                "expected_assessment": expected,
                "expected_conclusion_class": "supported",
                "result": result,
            }
        )

    world_a = WORLDS["A"]
    result = assess_permission(world_a, true_observation(world_a))
    cases.append(
        {
            "case_id": "valid_with_evidence",
            "name": "Legitimate allow when current grant observed active",
            "role": "valid_control",
            "expected_assessment": "permission_justified",
            "expected_conclusion_class": "supported",
            "result": result,
        }
    )

    # --- failed_enforcement (broken gates under complete evidence) ---
    world_b = WORLDS["B"]
    result = assess_permission(
        world_b,
        true_observation(world_b),
        gate_behavior="broken_allow_when_revoked",
    )
    cases.append(
        {
            "case_id": "failed_enforcement_revoked_still_allows",
            "name": "World B: revoked grant observed but gate still allows",
            "role": "failed_enforcement",
            "expected_assessment": "enforcement_failed",
            "expected_conclusion_class": "failed_enforcement",
            "result": result,
        }
    )

    world_a = WORLDS["A"]
    result = assess_permission(
        world_a,
        true_observation(world_a),
        gate_behavior="broken_deny_when_active",
    )
    cases.append(
        {
            "case_id": "failed_enforcement_active_still_denies",
            "name": "World A: active grant observed but gate still denies",
            "role": "failed_enforcement",
            "expected_assessment": "enforcement_failed",
            "expected_conclusion_class": "failed_enforcement",
            "result": result,
        }
    )

    # Contrasts: correct gates on the same evidence remain supported.
    result_ok = assess_permission(world_b, true_observation(world_b))
    cases.append(
        {
            "case_id": "enforcement_held_revoked_deny",
            "name": "World B: revoked grant + correct deny (contrast)",
            "role": "enforcement_contrast",
            "expected_assessment": "permission_refuted",
            "expected_conclusion_class": "supported",
            "result": result_ok,
        }
    )
    result_ok_a = assess_permission(world_a, true_observation(world_a))
    cases.append(
        {
            "case_id": "enforcement_held_active_allow",
            "name": "World A: active grant + correct allow (contrast)",
            "role": "enforcement_contrast",
            "expected_assessment": "permission_justified",
            "expected_conclusion_class": "supported",
            "result": result_ok_a,
        }
    )

    # Misbound observations (adversarial evidence quality — still complete,
    # so classification follows observed grant vs gate decision).
    for wid in ("A", "B"):
        world = WORLDS[wid]
        result = assess_permission(world, misbound_observation(world))
        expected = (
            "permission_refuted"
            if world.grant_current == "active"
            else "permission_justified"
        )
        cases.append(
            {
                "case_id": f"misbound_world_{wid.lower()}",
                "name": f"World {wid} with flipped grant observation",
                "role": "adversarial_misbind",
                "expected_assessment": expected,
                "expected_conclusion_class": "supported",
                "ground_truth_mismatch": True,
                "result": result,
            }
        )

    return cases


def evaluate_method_success(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Score whether assessments and three-way classes match expectations."""
    errors: list[str] = []
    for case in cases:
        got = case["result"]["assessment"]
        want = case["expected_assessment"]
        if got != want:
            errors.append(f"{case['case_id']}: assessment got {got!r} want {want!r}")
        got_c = case["result"]["conclusion_class"]
        want_c = case["expected_conclusion_class"]
        if got_c != want_c:
            errors.append(
                f"{case['case_id']}: conclusion_class got {got_c!r} want {want_c!r}"
            )

    blind_a = next(c for c in cases if c["case_id"] == "blind_world_a")
    blind_b = next(c for c in cases if c["case_id"] == "blind_world_b")
    indistinguish = (
        blind_a["result"]["assessment"] == blind_b["result"]["assessment"] == "unsupported"
        and blind_a["result"]["conclusion_class"]
        == blind_b["result"]["conclusion_class"]
        == "missing_evidence"
        and blind_a["result"]["decision"] == blind_b["result"]["decision"]
        and blind_a["result"]["visible_receipt"] == blind_b["result"]["visible_receipt"]
    )
    if not indistinguish:
        errors.append("blind worlds are distinguishable or not both missing_evidence")

    disc_a = next(c for c in cases if c["case_id"] == "discriminated_world_a")
    disc_b = next(c for c in cases if c["case_id"] == "discriminated_world_b")
    if disc_a["result"]["decision"] == disc_b["result"]["decision"]:
        errors.append("discriminator failed: A and B decisions still equal")

    for case in cases:
        if (
            case["role"] == "negative_control"
            and case["result"]["conclusion_class"] != "missing_evidence"
        ):
            errors.append(f"{case['case_id']}: irrelevant fact upgraded conclusion")

    for fail_id in (
        "failed_enforcement_revoked_still_allows",
        "failed_enforcement_active_still_denies",
    ):
        fail = next(c for c in cases if c["case_id"] == fail_id)
        if fail["result"]["conclusion_class"] != "failed_enforcement":
            errors.append(f"{fail_id}: not classified as failed_enforcement")
        if fail["result"]["finding_label"] != "contradicted_in_scope":
            errors.append(f"{fail_id}: did not map to contradicted_in_scope")
        if fail["result"]["finding_label"] == "reproduced":
            errors.append(f"{fail_id}: incorrectly mapped to reproduced")

    for held_id in (
        "enforcement_held_revoked_deny",
        "enforcement_held_active_allow",
    ):
        held = next(c for c in cases if c["case_id"] == held_id)
        if held["result"]["conclusion_class"] != "supported":
            errors.append(f"{held_id}: correct gate was not classified as supported")

    for case in cases:
        if case.get("ground_truth_mismatch"):
            obs = case["result"]["observations"]["observed_grant"]
            truth = case["result"]["ground_truth_grant"]
            if obs == truth:
                errors.append(f"{case['case_id']}: misbind did not flip observation")
            case["result"]["misbound_detected"] = obs != truth

    classes_seen = {c["result"]["conclusion_class"] for c in cases}
    three_way = classes_seen == {
        "missing_evidence",
        "failed_enforcement",
        "supported",
    }
    if not three_way:
        errors.append(f"protocol did not exercise all three classes: {sorted(classes_seen)}")

    return {
        "passed": not errors,
        "errors": errors,
        "indistinguishable_when_blind": indistinguish,
        "discriminator_separates_worlds": disc_a["result"]["decision"]
        != disc_b["result"]["decision"],
        "three_way_classes_exercised": three_way,
        "case_count": len(cases),
        "unsupported_blind_count": sum(
            1
            for c in cases
            if c["role"] in {"indistinguishability", "negative_control"}
            and c["result"]["assessment"] == "unsupported"
        ),
        "missing_evidence_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "missing_evidence"
        ),
        "failed_enforcement_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "failed_enforcement"
        ),
        "supported_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "supported"
        ),
    }
