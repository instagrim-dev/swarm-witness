"""The held-out protocol is frozen before its labels, and the result keeps them separate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "external_calibration" / "heldout_v1.yaml"
RESULT = ROOT / "evidence" / "external_calibration_v1" / "heldout_v1" / "result.json"
RUNNER = ROOT / "experiments" / "external_calibration" / "heldout_v1.py"


def _runner():
    spec = importlib.util.spec_from_file_location("heldout_v1_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_protocol_does_not_contain_heldout_outcomes():
    text = PROTOCOL.read_text(encoding="utf-8")
    protocol = yaml.safe_load(text)
    assert protocol["independent_jury"] is False
    assert protocol["superiority_claim"] is False
    assert protocol["transfer_claim"] is False
    assert "claim_id" not in text
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    for row in result["rows"]:
        assert row["claim_id"] not in text


def test_retained_heldout_result_matches_a_fresh_run():
    retained = json.loads(RESULT.read_text(encoding="utf-8"))
    fresh = _runner().run()
    assert retained["independent_jury"] is False
    assert retained["controlled_truth_is_the_label"] is False
    assert retained["agreement_is_not_the_label"] is True
    assert retained["transfer_claim"] is False
    assert retained["superiority_claim"] is False
    assert retained["source_demand"]["additional_source_requests"] == 0
    assert retained["eligibility_count"] == len(retained["rows"])
    controls = retained["controls"]
    assert controls["successful"]["visible_evidence_label"] == "supported"
    assert controls["unresolved"]["visible_evidence_label"] == "unresolved"
    assert controls["refutation"]["visible_evidence_label"] == "refuted"
    removed = retained["discriminating_record"]["interventions"]["removed"]
    duplicated = retained["discriminating_record"]["interventions"]["duplicated"]
    irrelevant = retained["discriminating_record"]["interventions"]["irrelevant"]
    assert removed["visible_evidence_label"] == "unresolved"
    assert duplicated["visible_evidence_label"] == controls["successful"]["visible_evidence_label"]
    assert irrelevant["visible_evidence_label"] == controls["successful"]["visible_evidence_label"]
    for key in ("rows", "label_counts", "disagreements", "controls", "discriminating_record"):
        assert fresh[key] == retained[key]
