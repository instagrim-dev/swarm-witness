"""R5-v3 wider-coverage protocol tests (issue #11).

The historical claims/r5_v2.yaml causal matrix is a different protocol and
must remain registered under that id.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.schema import validate_claim, validate_finding, validate_run  # noqa: E402
from swarm_witness.swarm_audit_v3 import (  # noqa: E402
    SIM_PIN_SOURCE_COMMIT,
    SwarmStateV2,
    compare_boundaries_to_v1,
    coverage_report,
    evaluate_r5_v2_success,
    gate_policy_decision,
    gate_policy_ignore_scope,
    held_out_binding_errors,
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
    assert (ROOT / "experiments" / "swarm_r5_v3" / "case_expectations.yaml").is_file()
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
        assert result["fixture_valid"] is True
        assert result["fixture_binding_errors"] == []
        assert result["reference_source"] == "held_out_trusted_ground_truth"
        expected = result.get("fixture_expected")
        assert expected
        assert result["conclusion_class"] == expected["conclusion_class"]
        agent = str(result["agent"]).lower()
        assert result["required_decision"] == result["trusted_ground_truth"][
            f"required_decision_for_{agent}"
        ]
        assert str(case["evidence_source"]).startswith("held_out:")
    wired = [
        c
        for c in run_r5_v2_protocol_cases()
        if str(c.get("evidence_source", "")).startswith("held_out:")
    ]
    assert wired and all(c.get("expected") for c in wired)


def test_contradictory_scope_fixture_is_invalid(tmp_path: Path):
    """A substituted scope truth must not pass as deny/supported."""
    source = json.loads(
        (
            ROOT
            / "experiments"
            / "swarm_r5_v3"
            / "held_out"
            / "scope_attenuated_out_of_task.json"
        ).read_text(encoding="utf-8")
    )
    source["trusted_ground_truth"]["assignee_c_scope"] = "task-*"
    source["trusted_ground_truth"]["required_decision_for_c"] = "allow"
    source["trusted_ground_truth"]["effect_may_commit"] = True
    (tmp_path / "scope_attenuated_out_of_task.json").write_text(
        json.dumps(source), encoding="utf-8"
    )
    loaded = load_held_out_cases(tmp_path)
    assert len(loaded) == 1
    result = loaded[0]["result"]
    # The setup still denies; the declaration does not rewrite that execution.
    assert result["decision"] == "deny"
    assert result["conclusion_class"] == "supported"
    assert result["effect_committed"] is False
    assert result["fixture_valid"] is False
    assert result["reference_source"] == "rejected_held_out_ground_truth"
    assert any("assignee_c_scope" in msg for msg in result["fixture_binding_errors"])
    assert any("required_decision_for_c" in msg for msg in result["fixture_binding_errors"])
    assert any("effect_may_commit" in msg for msg in result["fixture_binding_errors"])

    cases = [
        c
        for c in run_r5_v2_protocol_cases()
        if not str(c.get("evidence_source", "")).startswith("held_out:")
    ]
    cases.extend(loaded)
    score = evaluate_r5_v2_success(cases)
    assert score["passed"] is False
    assert any("invalidated" in err for err in score["errors"])

    # The shipped fixture's own binding helper accepts the unsubstitued file.
    shipped = json.loads(
        (
            ROOT
            / "experiments"
            / "swarm_r5_v3"
            / "held_out"
            / "scope_attenuated_out_of_task.json"
        ).read_text(encoding="utf-8")
    )
    state = SwarmStateV2()
    state.seed_shared_grant("g-held-3", owner="A", task_scope="task-*")
    state.assign_delegate("g-held-3", by="A", delegate="B", task_scope="task-edit-*")
    state.assign_delegate(
        "g-held-3", by="B", delegate="C", task_scope="task-edit-doc"
    )
    assert held_out_binding_errors(shipped, state, result) == []


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
    loser = next(
        c
        for c in sim_cases
        if c["case_id"].endswith("reference_contention_one_use__b-claim")
    )
    assert loser["result"]["has_current_grant_observation"] is False
    assert loser["result"]["observation_freshness"] == "stale"
    assert loser["result"]["effect_settlement"] == "refused"
    assert loser["result"]["effect_committed"] is False
    late = next(
        c
        for c in sim_cases
        if c["case_id"].endswith("revocation_late_observation_reference__b-late")
    )
    assert late["result"]["decision"] == "allow"
    assert late["result"]["effect_committed"] is False
    assert late["result"]["effect_settlement"] == "refused"
    assert late["result"]["failure_origin"] == "decision_policy"
    forged = next(
        c
        for c in sim_cases
        if c["case_id"].endswith("reference_forged_assignee_boundary__b-forge")
    )
    assert forged["result"]["evidence_status"] == "misbound"
    assert forged["result"]["failure_origin"] == "evidence"
    assert forged["result"]["effect_status"] == "prevented"
    assert forged["result"]["effect_committed"] is False


def test_pinned_trace_digests_match_provenance():
    errors = verify_pinned_concurrency_digests()
    assert not errors, errors
    digests = pinned_concurrency_trace_digests()
    assert len(digests) == 7
    prov = (
        ROOT
        / "experiments"
        / "swarm_r5_v3"
        / "concurrency_traces"
        / "PROVENANCE.md"
    ).read_text(encoding="utf-8")
    assert f"source commit `{SIM_PIN_SOURCE_COMMIT}`" in prov
    assert "490d0bd5c6bbb4159b9e002e7a3ce4a22ca7e38e" not in prov.split("Superseded")[0]
    assert "c23f2954660e22ea5dace762197107c604f13bb8" not in prov.split("Superseded")[0]


def test_mismatched_pin_digest_and_missing_trace_fail_explicitly(tmp_path):
    """A wrong digest or a named pin that is absent is an error, not a skipped row."""
    digest_errors = verify_pinned_concurrency_digests(
        expected={"mas-reference_contention_one_use.json": "0" * 64}
    )
    assert any(item.startswith("pin digest mismatch ") for item in digest_errors)
    assert any("mas-reference_contention_one_use.json" in item for item in digest_errors)
    missing_errors = verify_pinned_concurrency_digests(
        expected={"mas-does-not-exist.json": "ab" * 32},
        trace_dir=tmp_path,
    )
    assert any(item.startswith("missing pinned trace ") for item in missing_errors)
    assert any("mas-does-not-exist.json" in item for item in missing_errors)


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
    # The correct gate and its one-rule mutant do not call the oracle.
    for fn in (gate_policy_decision, gate_policy_ignore_scope):
        assert "oracle_required_decision" not in fn.__code__.co_names
    observed = {
        "state": "active",
        "spent": False,
        "assignees": {"A", "B", "C"},
        "task_scopes": {
            "A": "task-*",
            "B": "task-edit-*",
            "C": "task-edit-doc",
        },
    }
    assert (
        oracle_required_decision(
            agent="C", authoritative_grant=observed, task_id="task-admin"
        )
        == "deny"
    )
    assert (
        gate_policy_decision(
            agent="C", observed_grant=observed, task_id="task-admin"
        )
        == "deny"
    )
    assert (
        gate_policy_ignore_scope(
            agent="C", observed_grant=observed, task_id="task-admin"
        )
        == "allow"
    )
    revoked = {**observed, "state": "revoked"}
    assert (
        gate_policy_ignore_scope(
            agent="C", observed_grant=revoked, task_id="task-admin"
        )
        == "deny"
    )
    cases = {c["case_id"]: c for c in run_r5_v2_protocol_cases()}
    mutant = cases["v2_deleg_scope_mutant_ignore_scope"]
    assert mutant["result"]["decision"] == "allow"
    assert mutant["result"]["required_decision"] == "deny"
    assert mutant["result"]["conclusion_class"] == "failed_enforcement"
    assert mutant["result"]["failure_origin"] == "decision_policy"
    assert mutant["result"]["effect_committed"] is False
    correct = cases["v2_deleg_scope_rule_correct_deny"]["result"]
    assert correct["decision"] == "deny"
    assert correct["conclusion_class"] == "supported"
    hidden = dict(mutant)
    hidden["result"] = {
        **mutant["result"],
        "decision": "deny",
        "property_holds": True,
        "conclusion_class": "supported",
        "failure_origin": "none",
        "decision_status": "correct",
        "effect_status": "not_applicable",
        "assessment": "permission_refuted",
    }
    hidden["expected"] = {
        **mutant["expected"],
        "conclusion_class": "supported",
        "decision": "deny",
        "decision_status": "correct",
        "effect_status": "not_applicable",
        "failure_origin": "none",
        "assessment": "permission_refuted",
    }
    missed = [
        hidden if c["case_id"] == mutant["case_id"] else c
        for c in cases.values()
    ]
    score = evaluate_r5_v2_success(missed)
    assert score["passed"] is False
    assert any("was not detected" in err for err in score["errors"])


def test_runner_writes_valid_evidence(tmp_path: Path):
    spec = importlib.util.spec_from_file_location(
        "r5v2_run", ROOT / "experiments" / "swarm_r5_v3" / "run.py"
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
            (ROOT / "claims" / "r5_v3.yaml").read_text(encoding="utf-8")
        )
    )
    assert claim.id == "r5_v3"
    assert claim.source_version == "swarm-witness-r5-v3"


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
    historical = yaml.safe_load(
        (ROOT / "claims" / "r5_v2.yaml").read_text(encoding="utf-8")
    )
    assert historical["id"] == "r5_v2"
    assert historical["source_version"] == "r5-v2-causal-matrix"
    historical_summary = json.loads(
        (ROOT / "evidence" / "r5_v2" / "summary.json").read_text(encoding="utf-8")
    )
    # Retained #33 summary identifies the protocol in-file; claim_id stays on the claim and result.yaml.
    assert "claim_id" not in historical_summary
    assert historical_summary["protocol"] == "r5-v2-causal-matrix"
    assert historical_summary["scenario_count"] == 14
    assert historical_summary["arm_count"] == 28
    historical_result = yaml.safe_load(
        (ROOT / "evidence" / "r5_v2" / "result.yaml").read_text(encoding="utf-8")
    )
    assert historical_result["claim_id"] == "r5_v2"
