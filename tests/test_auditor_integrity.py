"""Conformance for auditor-integrity v1 (issue #51)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
import yaml

from swarm_witness.auditor_integrity import (
    CLAIM_ID,
    METHODS,
    PROTOCOL_ID,
    build_cases,
    evaluate_from_disk,
    load_packet,
    load_truth,
    negative_mutations,
    predict,
    score_case,
    summarize,
    validate_freeze,
    write_split_fixtures,
)
from swarm_witness.schema import validate_claim, validate_finding, validate_run

ROOT = Path(__file__).resolve().parents[1]


def test_claim_file_validates():
    claim = yaml.safe_load(
        (ROOT / "claims" / "auditor_integrity_v1.yaml").read_text(encoding="utf-8")
    )
    validate_claim(claim)
    assert claim["id"] == CLAIM_ID


def test_freeze_rejects_empty_and_requires_controls():
    with pytest.raises(ValueError, match="cases=\\[\\]"):
        validate_freeze([])
    cases = build_cases()
    freeze = validate_freeze(cases)
    assert freeze["case_count"] >= 12
    assert freeze["positive"] >= 2
    assert freeze["negative"] >= 2
    assert freeze["unknown"] >= 2
    assert "evaluator_source_leakage" in freeze["mechanisms"]
    assert "source_laundering" in freeze["mechanisms"]
    assert "property_laundering" in freeze["mechanisms"]


def test_packet_truth_split_and_disk_eval(tmp_path: Path):
    # Use repo paths; write_split_fixtures always targets experiments/.
    digests = write_split_fixtures(ROOT)
    assert digests
    man = json.loads(
        (ROOT / "experiments" / "auditor_integrity" / "freeze_manifest.json").read_text()
    )
    case_id = man["case_ids"][0]
    packet = load_packet(ROOT, case_id)
    truth = load_truth(ROOT, case_id)
    assert "truth" not in packet
    assert "expected_epistemic" in truth
    rows, totals = evaluate_from_disk(ROOT)
    assert len(rows) == len(man["case_ids"]) * len(METHODS)
    assert totals["case_count"] == len(man["case_ids"])


def test_classifiers_do_not_import_truth_paths():
    src = (ROOT / "src" / "swarm_witness" / "auditor_integrity.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "predict",
            "naive_pass_verdict",
            "score_case",
        }:
            body = ast.dump(node)
            assert "truth/" not in body
            assert "load_truth" not in body or node.name == "score_case"


def test_swarm_zero_false_support_and_retains_positives():
    write_split_fixtures(ROOT)
    rows, totals = evaluate_from_disk(ROOT)
    swarm = totals["by_method"]["swarm_witness"]
    assert swarm["false_support"] == 0
    assert swarm["correct_supported"] >= 2
    assert swarm["correct_unresolved"] >= 2
    # Naive should over-support at least once on a contamination/divergence case.
    naive = totals["by_method"]["naive_pass"]
    assert naive["false_support"] >= 1


def test_contaminated_grader_exposure_not_supported_by_swarm():
    case = next(c for c in build_cases() if c["case_id"] == "eval-contaminated-before")
    swarm = predict("swarm_witness", case["claim"], case["observations"])
    naive = predict("naive_pass", case["claim"], case["observations"])
    assert swarm["epistemic_status"] == "refuted"
    assert naive["epistemic_status"] == "supported"


def test_posthoc_docs_do_not_contaminate_earlier_success():
    case = next(c for c in build_cases() if c["case_id"] == "eval-posthoc-docs-only")
    swarm = predict("swarm_witness", case["claim"], case["observations"])
    assert swarm["epistemic_status"] == "supported"


def test_property_laundering_url_not_system():
    case = next(c for c in build_cases() if c["case_id"] == "prop-url-not-system")
    swarm = predict("swarm_witness", case["claim"], case["observations"])
    assert swarm["epistemic_status"] == "refuted"


def test_duplicate_origin_does_not_inflate_groups():
    case = next(c for c in build_cases() if c["case_id"] == "src-duplicate-origin")
    swarm = predict("swarm_witness", case["claim"], case["observations"])
    assert swarm["support_group_count"] <= 1


def test_negative_mutations_pass():
    results = negative_mutations()
    counted = [item for item in results if item.get("counted", True)]
    assert counted
    assert all(item.get("passed") for item in counted)
    assert all(not item.get("false_supported") for item in results)
    hidden = next(item for item in results if item["mutation"] == "hidden_label_not_readable")
    assert hidden["counted"] is False
    assert hidden["executed"] is False
    assert hidden["passed"] is None


def test_attribution_has_its_own_denominator():
    write_split_fixtures(ROOT)
    _rows, totals = evaluate_from_disk(ROOT)
    swarm = totals["by_method"]["swarm_witness"]
    assert swarm["unique_origin_cases"] >= 2
    assert swarm["correct_concrete_origin"] == swarm["unique_origin_cases"]
    assert swarm["unsupported_attribution"] == 0
    assert swarm["correct_attribution_coverage"] == 1


def test_published_evidence_roundtrip():
    from experiments.auditor_integrity import run as runner

    # Import via path execution pattern used by other tests.
    import importlib.util

    path = ROOT / "experiments" / "auditor_integrity" / "run.py"
    spec = importlib.util.spec_from_file_location("auditor_integrity_run", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.main()
    assert out["passed"] is True
    run = json.loads(
        (
            ROOT
            / "evidence"
            / "auditor_integrity_v1"
            / "runs"
            / "auditor-integrity-v1-run.json"
        ).read_text(encoding="utf-8")
    )
    validate_run(run)
    finding = json.loads(
        (
            ROOT
            / "evidence"
            / "auditor_integrity_v1"
            / "findings"
            / "auditor-integrity-v1-f.json"
        ).read_text(encoding="utf-8")
    )
    validate_finding(finding)
    assert run["protocol_id"] == PROTOCOL_ID


def test_each_case_has_expected_status_for_swarm():
    for case in build_cases():
        rows = score_case(case)
        swarm_row = next(r for r in rows if r["method"] == "swarm_witness")
        assert swarm_row["predicted"] == case["truth"]["expected_epistemic"], case[
            "case_id"
        ]
