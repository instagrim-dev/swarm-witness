"""Evidence-sufficiency audit: identical receipts, distinct hidden grant state.

Worlds A (grant still valid) and B (grant revoked) can share the same old
receipt while current authority is unobserved. Without a discriminating
observation, a reliable evaluator cannot justify a permission claim. Supplying
current grant state distinguishes the worlds; an irrelevant observation must
not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

WorldId = Literal["A", "B"]
GrantState = Literal["active", "revoked"]
AssessmentKind = Literal[
    "unsupported",
    "permission_justified",
    "permission_refuted",
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
    # When include_current_grant is True, the observed value (may be wrong if
    # misbound — used by adversarial controls).
    observed_grant: GrantState | None = None
    irrelevant_fact: str | None = None


WORLDS: dict[str, World] = {
    "A": World(world_id="A", grant_current="active"),
    "B": World(world_id="B", grant_current="revoked"),
}


def assess_permission(
    world: World,
    observations: ObservationSet,
    *,
    visible_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess 'current permission is justified' under a partial observation set.

    The old receipt alone never justifies current permission. Current grant
    state is the discriminating observation. Irrelevant facts do not qualify.
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
        "decision": None,
        "assessment": "unsupported",
        "justified_permission_claim": False,
        "reason": "",
    }

    if not observations.include_current_grant or observations.observed_grant is None:
        out["reason"] = (
            "old receipt available but current grant state unobserved; "
            "permission claim unsupported (Worlds A and B indistinguishable "
            "from this evidence)"
        )
        if observations.include_irrelevant:
            out["reason"] += (
                f"; irrelevant fact {observations.irrelevant_fact!r} does not "
                "discriminate"
            )
        return out

    observed = observations.observed_grant
    if observed == "active":
        out["decision"] = "allow"
        out["assessment"] = "permission_justified"
        out["justified_permission_claim"] = True
        out["reason"] = "current grant observed active; permission claim supported"
        return out

    out["decision"] = "deny"
    out["assessment"] = "permission_refuted"
    out["justified_permission_claim"] = False
    out["reason"] = "current grant observed revoked; permission claim refuted"
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
    """Execute the declared evidence-sufficiency cases."""
    cases: list[dict[str, Any]] = []

    # Blind worlds: identical visible evidence → identical unsupported assessments.
    for wid in ("A", "B"):
        world = WORLDS[wid]
        result = assess_permission(world, blind_observation())
        cases.append(
            {
                "case_id": f"blind_world_{wid.lower()}",
                "name": f"World {wid} without current grant observation",
                "role": "indistinguishability",
                "expected_assessment": "unsupported",
                "result": result,
            }
        )

    # Negative control: irrelevant fact must not upgrade unsupported → justified.
    for wid in ("A", "B"):
        world = WORLDS[wid]
        result = assess_permission(world, blind_observation(irrelevant=True))
        cases.append(
            {
                "case_id": f"irrelevant_blind_{wid.lower()}",
                "name": f"World {wid} blind + irrelevant observation",
                "role": "negative_control",
                "expected_assessment": "unsupported",
                "result": result,
            }
        )

    # Discriminating observation supplied.
    for wid, expected in (("A", "permission_justified"), ("B", "permission_refuted")):
        world = WORLDS[wid]
        result = assess_permission(world, true_observation(world))
        cases.append(
            {
                "case_id": f"discriminated_world_{wid.lower()}",
                "name": f"World {wid} with current grant observed",
                "role": "discriminator",
                "expected_assessment": expected,
                "result": result,
            }
        )

    # Valid authorization proceeds when necessary evidence is present (World A).
    world_a = WORLDS["A"]
    result = assess_permission(world_a, true_observation(world_a))
    cases.append(
        {
            "case_id": "valid_with_evidence",
            "name": "Legitimate allow when current grant observed active",
            "role": "valid_control",
            "expected_assessment": "permission_justified",
            "result": result,
        }
    )

    # Adversarial misbinding: observed grant flipped vs ground truth.
    for wid in ("A", "B"):
        world = WORLDS[wid]
        result = assess_permission(world, misbound_observation(world))
        # Assessment follows *observed* value; protocol records mismatch separately.
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
                "ground_truth_mismatch": True,
                "result": result,
            }
        )

    return cases


def evaluate_method_success(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Score whether the audit kit's assessments match the protocol expectations."""
    errors: list[str] = []
    for case in cases:
        got = case["result"]["assessment"]
        want = case["expected_assessment"]
        if got != want:
            errors.append(f"{case['case_id']}: got {got!r} want {want!r}")

    blind_a = next(c for c in cases if c["case_id"] == "blind_world_a")
    blind_b = next(c for c in cases if c["case_id"] == "blind_world_b")
    indistinguish = (
        blind_a["result"]["assessment"] == blind_b["result"]["assessment"] == "unsupported"
        and blind_a["result"]["decision"] == blind_b["result"]["decision"]
        and blind_a["result"]["visible_receipt"] == blind_b["result"]["visible_receipt"]
    )
    if not indistinguish:
        errors.append("blind worlds are distinguishable or not both unsupported")

    disc_a = next(c for c in cases if c["case_id"] == "discriminated_world_a")
    disc_b = next(c for c in cases if c["case_id"] == "discriminated_world_b")
    if disc_a["result"]["decision"] == disc_b["result"]["decision"]:
        errors.append("discriminator failed: A and B decisions still equal")

    for case in cases:
        if case["role"] == "negative_control" and case["result"]["assessment"] != "unsupported":
            errors.append(f"{case['case_id']}: irrelevant fact upgraded assessment")

    # Misbound cases: assessment follows observation, but must flag mismatch.
    for case in cases:
        if case.get("ground_truth_mismatch"):
            obs = case["result"]["observations"]["observed_grant"]
            truth = case["result"]["ground_truth_grant"]
            if obs == truth:
                errors.append(f"{case['case_id']}: misbind did not flip observation")
            case["result"]["misbound_detected"] = obs != truth

    return {
        "passed": not errors,
        "errors": errors,
        "indistinguishable_when_blind": indistinguish,
        "discriminator_separates_worlds": disc_a["result"]["decision"]
        != disc_b["result"]["decision"],
        "case_count": len(cases),
        "unsupported_blind_count": sum(
            1
            for c in cases
            if c["role"] in {"indistinguishability", "negative_control"}
            and c["result"]["assessment"] == "unsupported"
        ),
    }
