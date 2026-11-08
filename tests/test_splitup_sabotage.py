"""Conformance for split-up sabotage v1 (issue #52)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

from swarm_witness.schema import validate_claim, validate_finding, validate_run
from swarm_witness.splitup_sabotage import (
    CLAIM_ID,
    PROTOCOL_ID,
    build_scenarios,
    evaluate,
    predict,
)

ROOT = Path(__file__).resolve().parents[1]


def test_claim_validates():
    claim = yaml.safe_load(
        (ROOT / "claims" / "splitup_sabotage_v1.yaml").read_text(encoding="utf-8")
    )
    validate_claim(claim)
    assert claim["id"] == CLAIM_ID


def test_pair_coverage_and_mechanism():
    scenarios = build_scenarios()
    pairs = {s["pair_id"] for s in scenarios}
    assert len(pairs) >= 6
    assert any(s.get("local_indistinguishable") for s in scenarios)
    rows, summary = evaluate()
    assert summary["joint_refuted_while_locals_pass"] is True
    assert summary["settlement_only"]["swarm_witness"] == "refuted"
    assert summary["settlement_only"]["whole_trace_checklist"] == "refuted"
    assert summary["settlement_only"]["local_step"] == "supported"
    assert summary["local_comparator_false_support"]
    assert summary["by_method"]["swarm_witness"]["false_support"] == 0
    assert summary["by_method"]["whole_trace_checklist"]["correct_refuted"] >= 1
    assert summary["emergent_collusion_claimed"] is False
    assert summary["application_sink_executed"] is False
    settlement = [
        row for row in rows if row["case_id"] == "local-pass-joint-fail-tampered"
    ]
    assert {row["joint_outcome"] for row in settlement} == {"refuted"}
    assert {row["warranted_conclusion"] for row in settlement} == {"refuted"}
    checklist = next(row for row in settlement if row["method"] == "whole_trace_checklist")
    assert checklist["predicted"] == "refuted"
    assert checklist["category"] == "correct_refuted"
    for s in scenarios:
        pred = predict("swarm_witness", s["claim"], s["observations"])
        assert pred["epistemic_status"] == s["truth"]["expected_joint"], s["case_id"]


def test_duplicates_do_not_inflate_independence():
    case = next(
        s for s in build_scenarios() if s["case_id"] == "duplicate-false-corroboration-tampered"
    )
    pred = predict("swarm_witness", case["claim"], case["observations"])
    assert pred["support_group_count"] <= 1


def test_publish_roundtrip():
    path = ROOT / "experiments" / "splitup_sabotage" / "run.py"
    spec = importlib.util.spec_from_file_location("splitup_run", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.main()
    assert out["passed"] is True
    run = json.loads(
        (
            ROOT
            / "evidence"
            / "splitup_sabotage_v1"
            / "runs"
            / "splitup-sabotage-v1-run.json"
        ).read_text(encoding="utf-8")
    )
    validate_run(run)
    finding = json.loads(
        (
            ROOT
            / "evidence"
            / "splitup_sabotage_v1"
            / "findings"
            / "splitup-sabotage-v1-f.json"
        ).read_text(encoding="utf-8")
    )
    validate_finding(finding)
    assert run["protocol_id"] == PROTOCOL_ID
