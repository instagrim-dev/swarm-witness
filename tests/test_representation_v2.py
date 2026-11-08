"""Frozen-slice representation study: same 70 packets, four arms, no label leakage."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "experiments" / "external_calibration" / "representation_v2.py"
PROTOCOL = ROOT / "experiments" / "external_calibration" / "representation_v2.yaml"
HELDOUT = ROOT / "evidence" / "external_calibration_v1" / "heldout_v1" / "result.json"


def _runner():
    spec = importlib.util.spec_from_file_location("representation_v2", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_membership_preserves_the_seventy_case_slice():
    module = _runner()
    before = HELDOUT.read_bytes()
    packets = module.eligible_packets(ROOT)
    retained = json.loads(HELDOUT.read_text(encoding="utf-8"))
    assert [packet["claim"]["id"] for packet in packets] == [
        row["claim_id"] for row in retained["rows"]
    ]
    assert len(packets) == 70
    protocol = PROTOCOL.read_text(encoding="utf-8")
    assert packets[0]["claim"]["id"] not in protocol
    assert "frozen-slice representation study" in protocol
    assert HELDOUT.read_bytes() == before


def test_truth_or_scoring_label_changes_do_not_change_predictions():
    module = _runner()
    packet = module.eligible_packets(ROOT)[0]
    original = module.predict_arms(packet)
    mutated = copy.deepcopy(packet)
    mutated["factual_outcome"] = {"proposition_holds": False}
    mutated["warranted_conclusion"] = {"status": "refuted"}
    assert module.predict_arms(mutated, scoring_label="refuted") == original
    assert set(original) == {
        "raw_strong",
        "raw_qualifier",
        "composed_strong",
        "composed_qualifier",
    }


def test_projection_is_not_counted_as_an_independent_source(tmp_path: Path):
    document = _runner().run_representation_study(ROOT, tmp_path)
    assert document["transfer_claim"] is False
    assert document["superiority_claim"] is False
    assert document["independent_jury"] is False
    assert document["study_kind"] == "frozen_slice_representation"
    assert document["built_corpus_count"] == 130
    assert document["overlap_with_130_packet_corpus"] == 70
    assert document["errors"] == []
    assert document["qualified_disagreements"]["composed_versus_assessor"] == []
    assert len(document["qualified_disagreements"]["composed_versus_warrant"]) == 10
    for arm in ("composed_strong", "composed_qualifier"):
        demand = document["arms"][arm]["source_demand"]
        assert demand["supplied_records"] == 332
        assert demand["derived_records"] == 36
        assert demand["additional_source_requests"] == 0
        assert demand["independent_source_records"] == 332
    assert document["arms"]["raw_strong"]["assessor"]["decisive_coverage"] == "0/36"
    assert document["arms"]["composed_qualifier"]["assessor"]["decisive_coverage"] == "36/36"
    assert document["arms"]["composed_strong"]["warrant"]["unsupported_support"] == 10
    assert (tmp_path / "manifest.json").is_file()
    assert (tmp_path / "result.json").is_file()


def test_controls_preserve_historical_nominee_and_record_actual_status(tmp_path: Path):
    document = _runner().run_representation_study(ROOT, tmp_path)
    nominee = document["controls"]["historical_refutation_nominee"]
    assert nominee["selection_rule"] == "lexicographically first eligible fabricated_execution claim"
    assert nominee["visible_evidence_label"] == "unresolved"
    assert nominee["blind_validation"] is False
    supplementary = document["controls"]["supplementary_refuted_representative"]
    assert supplementary["role"] == "inspected_representative"
    assert supplementary["blind_validation"] is False
    assert supplementary["visible_evidence_label"] == "refuted"
    assert "lexicographically first assessor-refuted" in supplementary["selection_rule"]
    interventions = document["interventions"]
    assert interventions["removed"]["assessor_label"] == "unresolved"
    assert interventions["duplicated"]["assessor_label"] == interventions["baseline"]["assessor_label"]
    assert interventions["irrelevant"]["assessor_label"] == interventions["baseline"]["assessor_label"]
    assert interventions["removed"]["predictions"]["raw_qualifier"] == "unresolved"
    assert interventions["baseline"]["supplied_record_ids"]
    assert "derived_records" in interventions["removed"]
