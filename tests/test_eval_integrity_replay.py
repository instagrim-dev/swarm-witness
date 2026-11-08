"""Conformance for eval-integrity replay v1 (issue #50)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

from swarm_witness.eval_integrity_replay import (
    CLAIM_ID,
    ENVSRC_JUDGE_SHA256,
    FROZEN_CASES,
    PROTOCOL_ID,
    build_cases,
    causal_interventions,
    corpus_manifest,
    evaluate,
    predict,
    write_fixtures,
)
from swarm_witness.schema import validate_claim, validate_finding, validate_run

ROOT = Path(__file__).resolve().parents[1]


def test_claim_validates():
    claim = yaml.safe_load(
        (ROOT / "claims" / "eval_integrity_replay_v1.yaml").read_text(encoding="utf-8")
    )
    validate_claim(claim)
    assert claim["id"] == CLAIM_ID


def test_manifest_pins_and_unavailable_originals():
    man = corpus_manifest(retrieved_at="2026-11-08T00:00:00Z")
    assert man["sources"]
    assert any(s["id"] == "original_incident_logs" and s["available"] is False for s in man["sources"])
    assert any(s.get("sha256") == ENVSRC_JUDGE_SHA256 for s in man["sources"])
    assert man["denominator"]["frozen_scored_cases"] == len(FROZEN_CASES)
    assert man["transfer_claim"] is False


def test_sample_has_clean_and_contaminated():
    controls = {c["control"] for c in FROZEN_CASES}
    assert "positive" in controls and "negative" in controls and "unknown" in controls
    assert any(c["gets_source"] for c in FROZEN_CASES)
    assert any(not c["gets_source"] and c["control"] == "positive" for c in FROZEN_CASES)


def test_author_tags_not_in_observations():
    for case in build_cases():
        blob = json.dumps(case["observations"])
        assert "study_may_exclude" not in blob
        assert "author_exclusion_tag" not in blob


def test_swarm_matches_expected_label_replay():
    rows, totals, interventions = evaluate()
    swarm = totals["by_method"]["swarm_witness"]
    assert swarm["false_support"] == 0
    assert all(i["passed"] for i in interventions)
    for case in build_cases():
        pred = predict("swarm_witness", case["claim"], case["observations"])
        assert pred["epistemic_status"] == case["truth"]["expected_epistemic"], case[
            "case_id"
        ]
        blob = json.dumps(case["observations"])
        assert "grader_exposure_before_scored_behavior" not in blob
        assert "visible task progress" not in blob


def test_contaminated_source_access_does_not_decide_order():
    case = next(c for c in build_cases() if c["case_id"] == "envsrc-contam-scoring-py")
    assert case["truth"]["ordering_relative_to_scored_behavior"] == "unknown"
    assert case["truth"]["target_behavior_independently_verified"] is False
    for method in ("swarm_witness", "strong_checklist", "naive_pass"):
        assert (
            predict(method, case["claim"], case["observations"])["epistemic_status"]
            == "unresolved"
        )


def test_posthoc_docs_unresolved():
    case = next(
        c for c in build_cases() if c["case_id"] == "envsrc-posthoc-narration-only"
    )
    assert predict("swarm_witness", case["claim"], case["observations"])[
        "epistemic_status"
    ] == "unresolved"


def test_publish_roundtrip():
    path = ROOT / "experiments" / "eval_integrity_replay" / "run.py"
    spec = importlib.util.spec_from_file_location("eval_integrity_run", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.main()
    assert out["passed"] is True
    assert out["headline_eligible"] is False
    assert out["retained_valid_success"] is False
    assert out["study_kind"] == "label_replay"
    run = json.loads(
        (
            ROOT
            / "evidence"
            / "eval_integrity_replay_v1"
            / "runs"
            / "eval-integrity-replay-v1-run.json"
        ).read_text(encoding="utf-8")
    )
    validate_run(run)
    finding = json.loads(
        (
            ROOT
            / "evidence"
            / "eval_integrity_replay_v1"
            / "findings"
            / "eval-integrity-replay-v1-f.json"
        ).read_text(encoding="utf-8")
    )
    validate_finding(finding)
    assert run["protocol_id"] == PROTOCOL_ID
    assert (ROOT / "experiments" / "eval_integrity_replay" / "corpus_manifest.json").exists()
    write_fixtures(ROOT)  # idempotent
    assert causal_interventions()
