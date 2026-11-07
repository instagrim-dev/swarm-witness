"""Issue #29: boundary properties do not collapse into a URL-policy pass."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "theory"))

from check_taxonomy import FULL, verdict  # noqa: E402
from swarm_witness.incident_property_graph import (  # noqa: E402
    CHILDREN,
    DIAGNOSIS_TYPES,
    GRAPH_FIELDS,
    SYSTEM,
    conjoin,
    evaluate_manifest,
    finite_conjunction_check,
    load_inputs,
    mask_verdict,
)

FORBIDDEN_FRAGMENTS = (
    "cycler.__init__",
    "__builtins__",
    "b64decode",
    "169.254.169.254",
    "/proc/self",
    "sqlite3_initialize",
    "gzip.decompress",
    "__globals__",
)


@pytest.fixture(scope="module")
def bundle():
    graph, fixtures, postmortem = load_inputs(ROOT)
    summary = evaluate_manifest(graph=graph, fixtures=fixtures, postmortem=postmortem)
    by_id = {row["case_id"]: row for row in summary["results"]}
    return graph, fixtures, postmortem, summary, by_id


def test_graph_maps_every_property(bundle):
    graph, *_ = bundle
    assert graph["schema_version"] == "incident_property_graph_v1"
    assert graph["conjunction"]["children"] == list(CHILDREN)
    for name, node in graph["properties"].items():
        for field in GRAPH_FIELDS:
            assert node[field], name
    for field in GRAPH_FIELDS:
        assert graph["conjunction"][field]
    assert graph["conjunction"]["control"] == "no_single_control"


def test_mask_verdict_matches_theory_checker():
    for property_mask in range(FULL + 1):
        for evidence in range(FULL + 1):
            assert mask_verdict(property_mask, evidence) == verdict(property_mask, evidence)
            assert mask_verdict(property_mask, evidence, verified=False) == "unresolved"


def test_supported_url_does_not_support_system_when_children_fail():
    verdicts = {
        "P_url": "supported",
        "P_file_read": "refuted",
        "P_exec": "refuted",
        "P_identity": "supported",
        "P_effect": "supported",
    }
    assert conjoin(verdicts) == "refuted"
    assert verdicts["P_file_read"] == "refuted"
    assert verdicts["P_exec"] == "refuted"
    # A refuted child still refutes the conjunction when another child is unknown.
    partial = dict(verdicts)
    partial["P_identity"] = "unresolved"
    assert conjoin(partial) == "refuted"
    assert partial["P_identity"] == "unresolved"


def test_finite_conjunction_is_support_sound():
    report = finite_conjunction_check()
    assert report["passed"], report["violations"]
    assert report["checks"] > 4000
    assert report["conservative_unresolved_gap"] is True


def test_url_hold_with_worker_local_read_is_a_broader_failure(bundle):
    _, _, _, summary, by_id = bundle
    row = by_id["url_held_worker_local_read"]
    assert row["child_verdicts"]["P_url"] == "supported"
    assert row["child_verdicts"]["P_file_read"] == "refuted"
    assert row["child_verdicts"]["P_exec"] == "supported"
    assert row["system_verdict"] == "refuted"
    assert row["baseline_system"] == "supported"
    assert row["baseline_false_system_support"] is True
    assert row["graph_false_system_support"] is False
    assert row["refuted_child_hidden"] is False
    assert set(row["child_verdicts"]) == set(CHILDREN)
    layers = {item["event_id"]: item for item in row["layers"]}
    assert layers["url-1"]["decision"] == "deny"
    assert layers["url-1"]["settlement"] == "prevented"
    assert layers["url-1"]["broader_safety_property"] is None
    assert layers["read-1"]["settlement"] == "committed"
    assert layers["read-1"]["local_evidence"]["subject_class"] == "worker_local"
    diagnosis = row["diagnosis"]
    assert diagnosis["types"] == ["control_held", "effect_boundary"]
    assert diagnosis["control_held"]["remote_url_allowlist"] is True
    assert diagnosis["control_held"]["file_boundary"] is False
    assert diagnosis["decision_policy"] == "correct"
    assert "decision_policy" not in diagnosis["types"]
    assert summary["graph_false_system_supports"] == 0


def test_file_read_and_exec_fail_independently(bundle):
    _, _, _, _, by_id = bundle
    file_case = by_id["url_held_worker_local_read"]["child_verdicts"]
    exec_case = by_id["url_held_config_exec"]["child_verdicts"]
    identity_case = by_id["url_held_unscoped_credential"]["child_verdicts"]
    assert file_case["P_file_read"] == "refuted" and file_case["P_exec"] == "supported"
    assert exec_case["P_exec"] == "refuted" and exec_case["P_file_read"] == "supported"
    assert identity_case["P_identity"] == "refuted" and identity_case["P_url"] == "supported"
    for case_id in (
        "url_held_worker_local_read",
        "url_held_config_exec",
        "url_held_unscoped_credential",
    ):
        row = by_id[case_id]
        assert row["system_verdict"] == "refuted"
        assert row["baseline_false_system_support"] is True


def test_negative_controls_keep_diagnosis_axes_apart(bundle):
    _, _, _, _, by_id = bundle
    denied = by_id["denied_then_unauthorized_effect"]
    assert denied["child_verdicts"]["P_url"] == "supported"
    assert denied["child_verdicts"]["P_effect"] == "refuted"
    assert denied["system_verdict"] == "refuted"
    assert denied["diagnosis"]["decision_policy"] == "correct"
    assert denied["diagnosis"]["effect_boundary"] == "violated"
    assert denied["diagnosis"]["types"] == ["control_held", "effect_boundary"]
    assert denied["deny_with_committed_effect"] == 1
    assert denied["decision_used_as_effect_proof_count"] == 0
    assert denied["baseline_false_system_support"] is True
    bad = {item["event_id"]: item for item in denied["layers"]}["eff-bad"]
    assert bad["decision"] == "deny" and bad["settlement"] == "committed"

    same_boundary = by_id["url_deny_ledger_commits"]
    assert same_boundary["child_verdicts"]["P_url"] == "refuted"
    assert same_boundary["diagnosis"]["decision_policy"] == "correct"
    assert same_boundary["diagnosis"]["types"] == ["control_held", "effect_boundary"]
    assert same_boundary["baseline_system"] == "supported"
    url = {item["event_id"]: item for item in same_boundary["layers"]}["url-1"]
    assert url["decision"] == "deny" and url["settlement"] == "committed"

    blocked = by_id["wrong_allow_blocked_at_settlement"]
    assert blocked["child_verdicts"]["P_url"] == "supported"
    assert blocked["system_verdict"] == "supported"
    assert blocked["diagnosis"]["decision_policy"] == "incorrect"
    assert blocked["diagnosis"]["effect_boundary"] == "held"
    assert blocked["diagnosis"]["control_held"]["remote_url_allowlist"] is False
    assert blocked["diagnosis"]["types"] == [
        "control_held",
        "decision_policy",
        "effect_boundary",
    ]
    assert blocked["baseline_system"] == "refuted"
    assert blocked["baseline_false_system_reject"] is True
    assert blocked["graph_false_system_support"] is False
    allowed = {item["event_id"]: item for item in blocked["layers"]}["url-1"]
    assert allowed["decision"] == "allow" and allowed["settlement"] == "prevented"

    valid = by_id["valid_local_read"]
    assert valid["child_verdicts"]["P_file_read"] == "supported"
    assert valid["child_verdicts"]["P_effect"] == "supported"
    assert valid["system_verdict"] == "unresolved"
    assert valid["diagnosis"]["types"] == ["control_held"]
    assert valid["diagnosis"]["effect_boundary"] == "held"
    assert valid["diagnosis"]["scope_mismatch"] is False
    assert all(item["settlement"] != "committed" or item["channel"] != "local_read"
               or item["local_evidence"]["subject_class"] == "sandbox_local"
               for item in valid["layers"])

    narrative = by_id["narrative_only_effect"]
    assert set(narrative["child_verdicts"].values()) == {"unresolved"}
    assert narrative["system_verdict"] == "unresolved"
    assert narrative["diagnosis"]["types"] == ["unverified_source"]
    assert narrative["diagnosis"]["effect_boundary"] == "unobserved"
    assert narrative["diagnosis"]["decision_policy"] == "unknown"
    assert "effect_boundary" not in narrative["diagnosis"]["types"]
    assert "decision_policy" not in narrative["diagnosis"]["types"]

    scope = by_id["url_only_system_claim"]
    assert scope["child_verdicts"]["P_url"] == "supported"
    assert scope["system_verdict"] == "unresolved"
    assert scope["diagnosis"]["types"] == ["control_held", "scope_mismatch"]
    assert scope["baseline_false_system_support"] is True
    assert "decision_policy" not in scope["diagnosis"]["types"]


def test_diagnosis_types_are_not_a_single_forced_label(bundle):
    _, _, _, _, by_id = bundle
    for row in by_id.values():
        types = row["diagnosis"]["types"]
        assert types == [name for name in DIAGNOSIS_TYPES if name in types]
        assert "exclusive_label" not in row["diagnosis"]
    # The five type names each occur, and at least one case carries two.
    seen = {name for row in by_id.values() for name in row["diagnosis"]["types"]}
    assert seen == set(DIAGNOSIS_TYPES)
    assert any(len(row["diagnosis"]["types"]) >= 2 for row in by_id.values())


def test_baseline_counterexamples_are_counted(bundle):
    _, _, _, summary, by_id = bundle
    assert summary["passed"] is True
    assert summary["baseline_false_system_supports"] == 6
    assert summary["baseline_false_system_rejects"] == 1
    assert summary["graph_false_system_supports"] == 0
    assert summary["decision_used_as_effect_proof_count"] == 0
    assert summary["deny_with_committed_effect"] == 2
    assert summary["incident_detection_claimed"] is False
    assert summary["incident_prevention_claimed"] is False
    false_supports = [
        row["case_id"] for row in by_id.values() if row["baseline_false_system_support"]
    ]
    assert false_supports == [
        "url_held_worker_local_read",
        "url_held_config_exec",
        "url_held_unscoped_credential",
        "denied_then_unauthorized_effect",
        "url_deny_ledger_commits",
        "url_only_system_claim",
    ]


def test_postmortem_stays_unresolved_and_names_telemetry(bundle):
    _, _, _, summary, _ = bundle
    score = summary["postmortem"]
    assert score["independent_supported"] == 0
    assert score["independent_refuted"] == 0
    assert score["independent_unresolved"] == 5
    assert set(score["independent_verdicts"].values()) == {"unresolved"}
    assert score["system_independent_verdict"] == "unresolved"
    assert score["url_support_implies_system"] is False
    assert score["narrative_conditional_system_supported"] is False
    assert score["narrative_reports"]["P_url"] == "control_reported_held"
    assert score["narrative_reports"]["P_file_read"] == "failure_reported"
    assert score["narrative_reports"]["P_exec"] == "failure_reported"
    mistaken = score["if_narrative_were_mistaken_for_verified_verdicts"]
    assert mistaken["adopted_as_case_verdict"] is False
    assert mistaken["system_verdict"] == "refuted"
    assert score["incident_detection_claimed"] is False
    assert score["incident_prevention_claimed"] is False
    assert score["diagnosis_types"] == ["unverified_source", "scope_mismatch"]
    properties = {item["property"] for item in score["telemetry_required"]}
    assert set(CHILDREN) <= properties
    assert "cross_source" in properties
    for item in score["telemetry_required"]:
        assert item["observation"] and item["why_insufficient"] and item["qualifying_source"]


def test_records_do_not_carry_exploit_payloads():
    paths = [
        ROOT / "src" / "swarm_witness" / "incident_property_graph.py",
        ROOT / "experiments" / "incident_properties" / "graph.yaml",
        ROOT / "experiments" / "incident_properties" / "fixtures.json",
        ROOT / "experiments" / "incident_properties" / "postmortem.yaml",
        ROOT / "experiments" / "incident_properties" / "run.py",
        ROOT / "experiments" / "incident_properties" / "README.md",
        ROOT / "docs" / "incident_property_decomposition.md",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for fragment in FORBIDDEN_FRAGMENTS:
            assert fragment not in text, f"{fragment} in {path.name}"


def test_committed_evidence_matches_fresh_evaluation():
    graph, fixtures, postmortem = load_inputs(ROOT)
    summary = evaluate_manifest(graph=graph, fixtures=fixtures, postmortem=postmortem)
    run = json.loads(
        (ROOT / "evidence" / "incident_property_graph" / "runs" / "incident-property-graph-meta.json").read_text()
    )
    for key, value in run["observations"].items():
        assert summary[key] == value
    assert run["observations"]["url_held_local_read_p_system"] == "refuted"
    assert summary["postmortem"]["case_id"] == postmortem["case_id"]
    assert SYSTEM == "P_system"
