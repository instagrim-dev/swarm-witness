"""R5-v2 wider-coverage protocol tests (issue #11)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.schema import validate_claim, validate_finding, validate_run  # noqa: E402
from swarm_witness.swarm_audit_v2 import (  # noqa: E402
    compare_boundaries_to_v1,
    coverage_report,
    evaluate_r5_v2_success,
    load_case_expectations,
    load_concurrency_trace_cases,
    load_held_out_cases,
    oracle_required_decision,
    pinned_concurrency_trace_digests,
    run_r5_v2_protocol_cases,
    run_sequential_family_cases,
    verify_pinned_concurrency_digests,
)


def test_r5_v2_method_success_and_coverage():
    cases = run_r5_v2_protocol_cases()
    score = evaluate_r5_v2_success(cases)
    assert score["passed"] is True, score["errors"]
    assert score["agent_count"] == 3
    assert score["three_way_classes_exercised"] is True
    assert score["held_out_count"] >= 1
    assert score["concurrency_row_count"] >= 4
    assert score["effect_boundary_count"] >= 1
    assert score["decision_policy_count"] >= 1
    assert score["unknown_coerced_count"] == 0
    assert score["pin_digest_ok"] is True
    assert set(score["major_families_with_paired_arms"]) >= {
        "authority_observation",
        "delegation_scope",
        "receipt_provenance",
        "observation_delivery",
        "concurrency_interleaving",
    }

    coverage = coverage_report(cases)
    assert coverage["dimension_count"] >= 6
    assert not coverage["unbound_tested_seams"], coverage["unbound_tested_seams"]
    for dim in coverage["dimensions"]:
        assert dim["tested_seams"], dim["id"]
        assert "untested_seams" in dim
        assert dim["bound_case_count"] >= 1, dim["id"]
        assert not dim["unbound_tested_seams"], dim


def test_correct_and_faulty_arms_share_inputs():
    cases = run_sequential_family_cases()
    by_pair: dict[str, set[str]] = {}
    for case in cases:
        pid = case.get("paired_input_id")
        if not pid:
            continue
        by_pair.setdefault(pid, set()).add(case["mechanism_arm"])
    paired = [
        pid
        for pid, arms in by_pair.items()
        if "correct" in arms
        and any(a.startswith("broken") for a in arms)
    ]
    assert "auth_active_b" in paired  # correct allow + broken_deny
    assert "obs_partial_b" in paired  # correct + broken_allow on partial
    assert paired, "expected at least one correct+faulty pair on same inputs"
    modes = {c["result"]["gate_mode"] for c in cases}
    assert "broken_deny" in modes
    assert "broken_allow" in modes
    # Misnamed revoke-after-hops broken_deny must not exist.
    assert not any(
        c["case_id"] == "v2_deleg_revoked_after_hops_broken_deny" for c in cases
    )


def test_unknown_not_coerced_and_diagnoses_distinct():
    cases = {c["case_id"]: c for c in run_r5_v2_protocol_cases()}
    missing = cases["v2_auth_missing_observation"]["result"]
    assert missing["conclusion_class"] == "missing_evidence"
    assert missing["decision"] is None
    assert missing["decision_status"] == "unknown"

    # Faulty arm on partial inputs still cannot coerce unknown → allow.
    partial_broken = cases["v2_obs_partial_broken_allow"]["result"]
    assert partial_broken["conclusion_class"] == "missing_evidence"
    assert partial_broken["decision"] is None
    assert partial_broken["gate_mode"] == "broken_allow"

    prevented = cases["v2_auth_revoked_broken_allow_prevented"]["result"]
    assert prevented["decision"] == "allow"
    assert prevented["effect_committed"] is False
    assert prevented["failure_origin"] == "decision_policy"
    assert prevented["effect_status"] == "prevented"

    committed = cases["v2_auth_spent_broken_commit"]["result"]
    assert committed["decision"] == "allow"
    assert committed["effect_committed"] is True
    assert committed["failure_origin"] == "effect_boundary"
    assert committed["effect_status"] == "committed"

    misbound = cases["v2_auth_misbound_active_when_revoked"]["result"]
    assert misbound["evidence_status"] == "misbound"
    assert misbound["failure_origin"] == "evidence"
    assert misbound["effect_committed"] is False

    own_bound = cases["v2_rx_own_bound_after_spend_deny"]["result"]
    assert own_bound["receipt_kind"] == "own_bound"
    assert own_bound["decision"] == "deny"
    assert own_bound["conclusion_class"] == "supported"


def test_expectations_are_external_not_classifier_authored():
    expectations = load_case_expectations()
    assert "v2_auth_valid_active_allow" in expectations
    assert "v2_auth_active_broken_deny" in expectations
    assert "v2_rx_own_bound_after_spend_deny" in expectations
    assert "v2_deleg_revoked_after_hops_broken_deny" not in expectations
    assert (ROOT / "experiments" / "swarm_r5_v2" / "case_expectations.yaml").is_file()
    cases = run_r5_v2_protocol_cases()
    for case in cases:
        if case["case_id"] == "v2_auth_valid_active_allow":
            case["expected"] = {
                **case["expected"],
                "conclusion_class": "missing_evidence",
            }
            break
    bad = evaluate_r5_v2_success(cases)
    assert bad["passed"] is False


def test_held_out_fixtures_bind_ground_truth():
    held = load_held_out_cases()
    assert held
    for case in held:
        result = case["result"]
        assert result.get("trusted_ground_truth")
        assert result.get("held_out_artifact")
        expected = result.get("fixture_expected")
        assert expected
        assert result["conclusion_class"] == expected["conclusion_class"]
        assert str(case["evidence_source"]).startswith("held_out:")
    wired = [
        c
        for c in run_r5_v2_protocol_cases()
        if str(c.get("evidence_source", "")).startswith("held_out:")
    ]
    assert wired and all(c.get("expected") for c in wired)


def test_concurrency_rows_cite_simulator_not_live_swarm():
    sim_cases = load_concurrency_trace_cases()
    assert len(sim_cases) >= 4
    for case in sim_cases:
        assert "multi-agent-sim" in (case.get("evidence_source") or "")
        assert case["result"].get("sim_protocol_id") == "multi-agent-sim-v1"
        excl = case["result"].get("sim_exclusions") or []
        assert "live_bmo_mesh_equivalence" in excl
        assert "production_concurrency_guarantees" in excl
    # Shared paired_input_id for reference vs mutant contention (same seed).
    contention = [
        c
        for c in sim_cases
        if c.get("paired_input_id") == "sim:contention_one_use_seed404"
    ]
    arms = {c["mechanism_arm"] for c in contention}
    assert "reference" in arms and any(a.startswith("mutant") for a in arms)
    mutant = next(
        c
        for c in sim_cases
        if c["case_id"].endswith("mutant_ignore_spend_contention__b-claim")
    )
    assert mutant["result"]["effect_committed"] is True
    assert mutant["result"]["failure_origin"] == "effect_boundary"
    assert mutant["result"]["conclusion_class"] == "failed_enforcement"


def test_pinned_trace_digests_match_provenance():
    errors = verify_pinned_concurrency_digests()
    assert not errors, errors
    digests = pinned_concurrency_trace_digests()
    assert len(digests) == 5


def test_boundary_comparison_retains_v1():
    boundaries = compare_boundaries_to_v1()
    assert boundaries["v1_retained"] is True
    assert boundaries["v1_passed"] is True
    assert boundaries["boundary_changes"]["v1_finding_unchanged"] is True
    assert boundaries["boundary_changes"]["new_concurrency_derived_rows"] is True
    assert boundaries["falsifying_counterexamples"]


def test_oracle_separated_from_gate():
    required = oracle_required_decision(
        agent="C",
        authoritative_grant={
            "state": "active",
            "spent": False,
            "assignees": {"A", "B"},
            "task_scopes": {"A": "task-*", "B": "task-*"},
        },
    )
    assert required == "deny"


def test_runner_writes_valid_evidence(tmp_path: Path):
    spec = importlib.util.spec_from_file_location(
        "r5v2_run", ROOT / "experiments" / "swarm_r5_v2" / "run.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["r5v2_run"] = mod
    spec.loader.exec_module(mod)
    cases = mod.run_r5_v2_protocol_cases()
    score = mod.evaluate_r5_v2_success(cases)
    coverage = mod.coverage_report(cases)
    boundaries = mod.compare_boundaries_to_v1(cases)
    out = mod.write_evidence(tmp_path, cases, score, coverage, boundaries)
    assert out["finding"]["label"] == "reproduced"
    validate_finding(
        {k: v for k, v in out["finding"].items() if k not in {"conclusion_class", "evaluation_method"}}
    )
    for path in (tmp_path / "runs").glob("*.json"):
        validate_run(json.loads(path.read_text(encoding="utf-8")))
    claim = validate_claim(
        yaml.safe_load(
            (ROOT / "claims" / "r5_v2_swarm_audit.yaml").read_text(encoding="utf-8")
        )
    )
    assert claim.id == "r5_v2"


def test_v1_artifacts_untouched():
    v1_finding = json.loads(
        (ROOT / "evidence" / "r5" / "findings" / "r5-f-swarm-audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert v1_finding["claim_id"] == "r5"
    assert v1_finding["label"] == "reproduced"
    v1_claim = yaml.safe_load(
        (ROOT / "claims" / "r5_swarm_audit.yaml").read_text(encoding="utf-8")
    )
    assert v1_claim["source_version"] == "swarm-witness-r5-v1"
