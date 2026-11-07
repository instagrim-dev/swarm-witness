"""Protocol runner: scenarios → traces → independent evaluation → score."""

from __future__ import annotations

from typing import Any

from swarm_witness.multi_agent_sim.evaluate import evaluate_simulation
from swarm_witness.multi_agent_sim.policy import get_policy
from swarm_witness.multi_agent_sim.scenarios import ScenarioSpec, all_scenario_specs
from swarm_witness.multi_agent_sim.scheduler import run_schedule

PROTOCOL_ID = "multi-agent-sim-v1"
SOURCE_PIN = "swarm-witness-multi-agent-sim-v1"
CLAIM_ID = "multi_agent_sim"


def run_scenario(spec: ScenarioSpec) -> dict[str, Any]:
    policy = get_policy(spec.policy_id)  # type: ignore[arg-type]
    sim = run_schedule(spec.schedule, policy)
    evaluation = evaluate_simulation(sim)
    claims_by_id = {c["call_id"]: c for c in evaluation["claims"]}

    return {
        "case_id": spec.case_id,
        "name": spec.name,
        "role": spec.role,
        "policy_id": spec.policy_id,
        "expected": dict(spec.expected),
        "manifest": spec.to_dict(),
        "trace": sim.relevant_trace(),
        "evaluation": evaluation,
        "claims_by_id": claims_by_id,
        "agents": ["A", "B", "C"],
    }


def _check_expected(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    exp = case["expected"]
    claims = case["claims_by_id"]
    evaluation = case["evaluation"]

    if "claim_decisions" in exp:
        for call_id, want in exp["claim_decisions"].items():
            got = claims[call_id]["decision"]
            if got != want:
                errors.append(
                    f"{case['case_id']}:{call_id}: decision {got!r} want {want!r}"
                )

    if "committed_effects" in exp:
        for call_id, want in exp["committed_effects"].items():
            got = claims[call_id]["committed_effect"]
            if got != want:
                errors.append(
                    f"{case['case_id']}:{call_id}: committed_effect {got!r} want {want!r}"
                )

    if "claim_conclusions" in exp:
        for call_id, want in exp["claim_conclusions"].items():
            got = claims[call_id]["conclusion_class"]
            if got != want:
                errors.append(
                    f"{case['case_id']}:{call_id}: conclusion {got!r} want {want!r}"
                )

    if "one_use_ok" in exp and evaluation["one_use_ok"] != exp["one_use_ok"]:
        errors.append(
            f"{case['case_id']}: one_use_ok {evaluation['one_use_ok']!r} "
            f"want {exp['one_use_ok']!r}"
        )

    if "winners" in exp:
        winners = [
            c["agent"]
            for c in evaluation["claims"]
            if c["committed_effect"] and c["decision"] == "allow"
        ]
        if winners != list(exp["winners"]):
            errors.append(
                f"{case['case_id']}: winners {winners!r} want {exp['winners']!r}"
            )

    # Distinguishing observation fields must be present on every claim eval.
    for call_id, ceval in claims.items():
        for key in (
            "decision",
            "committed_effect",
            "authoritative_owner_state",
            "conclusion_class",
            "local_knowledge_at_decision",
            "evaluator_learned_afterward",
            "observation_denominators",
        ):
            if key not in ceval:
                errors.append(f"{case['case_id']}:{call_id}: missing field {key}")

        # Bad decision must not be silently equated to committed effect.
        if ceval["decision"] == "allow" and ceval["committed_effect"] is not True:
            # allow without commit is allowed only if settlement refused — our
            # model commits on allow; flag inconsistency.
            errors.append(
                f"{case['case_id']}:{call_id}: allow without committed_effect"
            )
        if ceval["decision"] == "deny" and ceval["committed_effect"]:
            errors.append(
                f"{case['case_id']}:{call_id}: deny incorrectly recorded as committed"
            )

    return errors


def run_protocol_cases() -> list[dict[str, Any]]:
    return [run_scenario(spec) for spec in all_scenario_specs()]


def evaluate_protocol_success(cases: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    for case in cases:
        errors.extend(_check_expected(case))

    by_id = {c["case_id"]: c for c in cases}

    # --- Acceptance: ≥2 materially different interleavings, same grant ---
    a_first = by_id.get("interleave_a_first_reference")
    b_first = by_id.get("interleave_b_first_reference")
    if a_first and b_first:
        a_winners = [
            c["agent"]
            for c in a_first["evaluation"]["claims"]
            if c["committed_effect"]
        ]
        b_winners = [
            c["agent"]
            for c in b_first["evaluation"]["claims"]
            if c["committed_effect"]
        ]
        if a_winners == b_winners:
            errors.append(
                "interleavings are not materially different: "
                f"both winners={a_winners!r}"
            )
        if a_winners != ["A"] or b_winners != ["B"]:
            errors.append(
                f"expected A-first→[A] and B-first→[B]; got {a_winners}/{b_winners}"
            )
    else:
        errors.append("missing interleaving cases")

    # --- Revocation / late observation present ---
    if "revocation_late_observation_reference" not in by_id:
        errors.append("missing revocation_late_observation case")

    # --- Reference vs mutant on identical step shape ---
    ref = by_id.get("reference_contention_one_use")
    mut = by_id.get("mutant_ignore_spend_contention")
    if ref and mut:
        if ref["manifest"]["schedule"]["steps"] != mut["manifest"]["schedule"]["steps"]:
            errors.append("reference/mutant schedules differ (must be identical inputs)")
        if ref["evaluation"]["one_use_ok"] is not True:
            errors.append("reference arm failed one-use safety")
        if mut["evaluation"]["one_use_ok"] is not False:
            errors.append("mutant arm did not violate one-use (no counterexample)")
        # Concrete counterexample: second committed effect under mutant.
        mut_commits = [
            c["call_id"]
            for c in mut["evaluation"]["claims"]
            if c["committed_effect"]
        ]
        if len(mut_commits) < 2:
            errors.append(f"mutant counterexample weak: commits={mut_commits}")
    else:
        errors.append("missing reference/mutant paired arms")

    # --- Paired worlds: indistinguishable until distinguishing observation ---
    blind_a = by_id.get("paired_world_active_blind")
    blind_r = by_id.get("paired_world_revoked_blind")
    if blind_a and blind_r:
        ka = blind_a["claims_by_id"]["b-blind"]["local_knowledge_at_decision"]
        kr = blind_r["claims_by_id"]["b-blind"]["local_knowledge_at_decision"]
        # Compare agent-visible projection (ignore agent id field equality already).
        vis_a = {
            "grant_observations": ka["grant_observations"],
            "receipts": ka["receipts"],
            "irrelevant_facts": ka["irrelevant_facts"],
        }
        vis_r = {
            "grant_observations": kr["grant_observations"],
            "receipts": kr["receipts"],
            "irrelevant_facts": kr["irrelevant_facts"],
        }
        if vis_a != vis_r:
            errors.append("paired blind worlds not agent-indistinguishable")
        if (
            blind_a["claims_by_id"]["b-blind"]["conclusion_class"] != "missing_evidence"
            or blind_r["claims_by_id"]["b-blind"]["conclusion_class"]
            != "missing_evidence"
        ):
            errors.append("paired blind worlds must stay missing_evidence")
    else:
        errors.append("missing paired blind world cases")

    # Irrelevant must not upgrade.
    for wid in ("active", "revoked"):
        case = by_id.get(f"paired_world_{wid}_irrelevant")
        if not case:
            errors.append(f"missing paired_world_{wid}_irrelevant")
            continue
        got = case["claims_by_id"]["b-irr"]["conclusion_class"]
        if got != "missing_evidence":
            errors.append(
                f"irrelevant observation upgraded conclusion to {got!r} ({wid})"
            )

    # Distinguishing observation separates worlds.
    disc_a = by_id.get("paired_world_active_distinguished")
    disc_r = by_id.get("paired_world_revoked_distinguished")
    if disc_a and disc_r:
        if disc_a["claims_by_id"]["b-disc"]["decision"] == disc_r["claims_by_id"][
            "b-disc"
        ]["decision"]:
            errors.append("distinguished paired worlds unexpectedly agree on decision")
    else:
        errors.append("missing distinguished paired world cases")

    # Replay stability checked separately via hash of relevant_trace; record pins.
    classes = {
        c["conclusion_class"]
        for case in cases
        for c in case["evaluation"]["claims"]
    }
    three_way = classes >= {
        "missing_evidence",
        "failed_enforcement",
        "supported",
    }
    if not three_way:
        errors.append(f"did not exercise all three conclusion classes: {sorted(classes)}")

    return {
        "passed": not errors,
        "errors": errors,
        "case_count": len(cases),
        "protocol_id": PROTOCOL_ID,
        "source_pin": SOURCE_PIN,
        "three_way_classes_exercised": three_way,
        "missing_evidence_count": sum(
            1
            for case in cases
            for c in case["evaluation"]["claims"]
            if c["conclusion_class"] == "missing_evidence"
        ),
        "failed_enforcement_count": sum(
            1
            for case in cases
            for c in case["evaluation"]["claims"]
            if c["conclusion_class"] == "failed_enforcement"
        ),
        "supported_count": sum(
            1
            for case in cases
            for c in case["evaluation"]["claims"]
            if c["conclusion_class"] == "supported"
        ),
        "all_checks_pass": not errors,
    }


def replay_traces_match(seed_schedule_policy: tuple[str, int, str] | None = None) -> bool:
    """Fresh-run verification: same seed/schedule/policy → identical relevant trace."""
    from swarm_witness.multi_agent_sim.scenarios import interleaving_a_first

    spec = interleaving_a_first()
    if seed_schedule_policy:
        # reserved for future parameterization
        _ = seed_schedule_policy
    first = run_scenario(spec)["trace"]
    second = run_scenario(spec)["trace"]
    return first == second
