"""The pipeline comparison uses the frozen 70 labels and keeps false exclusivity."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "evidence" / "external_calibration_v1" / "heldout_v1" / "pipeline_v1.json"
LABELS = ROOT / "evidence" / "external_calibration_v1" / "heldout_v1" / "result.json"
RUNNER = ROOT / "experiments" / "external_calibration" / "heldout_pipeline_v1.py"


def _runner():
    spec = importlib.util.spec_from_file_location("heldout_pipeline_v1_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pipeline_recovers_assessor_labels_and_keeps_false_exclusivity():
    retained = json.loads(RESULT.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    fresh = _runner().run()
    assert retained["packet_count"] == 70
    assert retained["assessor_decisive"] == 36
    assert retained["superiority_claim"] is False
    assert retained["transfer_claim"] is False
    assert retained["independent_jury"] is False
    assert [row["claim_id"] for row in retained["rows"]] == [
        row["claim_id"] for row in labels["rows"]
    ]
    assert [row["assessor_label"] for row in retained["rows"]] == [
        row["visible_evidence_label"] for row in labels["rows"]
    ]
    raw = retained["methods"]["raw_swarm_witness"]
    raw_strong = retained["methods"]["raw_strong_invariant"]
    adapted = retained["methods"]["adapted_swarm_witness"]
    adapted_strong = retained["methods"]["adapted_strong_invariant"]
    assert raw["decisive_coverage"] == raw_strong["decisive_coverage"] == "0/36"
    assert raw["abstention"] == raw_strong["abstention"] == 70
    assert raw["unsupported_support"] == raw_strong["unsupported_support"] == 0
    assert adapted["decisive_coverage"] == adapted_strong["decisive_coverage"] == "36/36"
    assert adapted["unsupported_support"] == adapted_strong["unsupported_support"] == 0
    assert adapted["unsupported_refutation"] == adapted_strong["unsupported_refutation"] == 0
    assert adapted["abstention"] == adapted_strong["abstention"] == 34
    assert adapted["source_demand"]["supplied_records"] == 332
    assert adapted["source_demand"]["derived_records"] == 36
    assert adapted["source_demand"]["additional_source_requests"] == 0
    assert raw["source_demand"]["additional_source_requests"] == 0
    false_rows = [row for row in retained["rows"] if row["scenario"] == "false_exclusivity"]
    assert len(false_rows) == 13
    known = [
        row
        for row in false_rows
        if row["assessor_label"] == "supported" and row["warranted_conclusion"] == "unresolved"
    ]
    assert len(known) == 10
    assert all(row["raw_swarm_witness"] == "unresolved" for row in known)
    assert all(row["raw_strong_invariant"] == "unresolved" for row in known)
    assert all(row["adapted_swarm_witness"] == "supported" for row in known)
    assert all(row["adapted_strong_invariant"] == "supported" for row in known)
    assert retained["adapted_arms_agree"] is True
    assert retained["adapter_matches_adapted_arms"] is True
    assert retained["warrant_decisive"] == 26
    warrant = retained["warrant"]
    assert warrant["raw_swarm_witness"]["decisive_coverage"] == "0/26"
    assert warrant["raw_strong_invariant"]["decisive_coverage"] == "0/26"
    assert warrant["raw_swarm_witness"]["abstention"] == 70
    assert warrant["raw_swarm_witness"]["unsupported_support"] == 0
    for arm in ("adapted_swarm_witness", "adapted_strong_invariant"):
        assert warrant[arm]["decisive_coverage"] == "26/26"
        assert warrant[arm]["unsupported_support"] == 10
        assert warrant[arm]["unsupported_refutation"] == 0
        assert warrant[arm]["abstention"] == 34
    assert all(
        row["adapter_verdict"] == row["adapted_swarm_witness"] == row["adapted_strong_invariant"]
        for row in retained["rows"]
    )
    assert fresh["warrant"] == retained["warrant"]
    assert fresh["warrant_decisive"] == retained["warrant_decisive"]
    assert fresh["adapter_matches_adapted_arms"] == retained["adapter_matches_adapted_arms"]
    assert fresh["methods"] == retained["methods"]
    assert fresh["false_exclusivity"] == retained["false_exclusivity"]
    assert [{key: row[key] for key in row if key != "processing_seconds"} for row in fresh["rows"]] == [
        {key: row[key] for key in row if key != "processing_seconds"} for row in retained["rows"]
    ]
