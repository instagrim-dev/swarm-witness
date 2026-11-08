"""Detection-latency replay: synthetic measures publish, incident latency does not."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from swarm_witness.conclusion_classes import assert_label_matches_conclusion
from swarm_witness.detection_latency import (
    ALERT_BUDGET,
    LOCAL_RULE,
    PROTOCOL_ID,
    RULES,
    TIMESTAMP_FIELDS,
    WITHHELD_LATENCY_CLAIMS,
    TimestampError,
    latency_seconds,
    parse_timestamp,
    render_report,
    run_replay,
)
from swarm_witness.latency_evidence import bind_incident_latency, load_telemetry_bundle

ROOT = Path(__file__).resolve().parents[1]


def _load_dataset_module():
    path = ROOT / "experiments" / "detection_latency" / "dataset.py"
    spec = importlib.util.spec_from_file_location("detection_latency_dataset", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


DATASET = _load_dataset_module()


def _score():
    replay = run_replay(DATASET.build_dataset(), DATASET.build_sources())
    return bind_incident_latency(replay, load_telemetry_bundle(ROOT))


@pytest.fixture(scope="module")
def score():
    return _score()


def _stage(score, case_id, stage_id):
    for stage in score["stages"]:
        if stage["case_id"] == case_id and stage["stage_id"] == stage_id:
            return stage
    raise AssertionError(f"missing {case_id}/{stage_id}")


def _audit(score, case_id, stage_id, detector="evidence_qualified_audit"):
    return _stage(score, case_id, stage_id)["detectors"][detector]


def test_absent_timestamp_requires_a_reason():
    with pytest.raises(TimestampError):
        parse_timestamp("enforcement_at", {"value": None, "confidence": "unavailable"})


def test_imputed_timestamp_is_rejected():
    with pytest.raises(TimestampError):
        parse_timestamp(
            "enforcement_at",
            {
                "value": "2026-01-15T03:00:00Z",
                "precision": "exact",
                "confidence": "authored",
                "source_id": PROTOCOL_ID,
                "locator": "test",
                "unavailable_reason": None,
                "copied_from": "event_time",
            },
        )


def test_reconstructed_bounds_do_not_publish_a_duration():
    sources = DATASET.build_sources()
    bounds = {item["id"]: item for item in sources["stated_bounds"]}
    start = parse_timestamp(
        "event_time",
        {
            "value": bounds["hf-window-start"]["stated_value"],
            "precision": "exact",
            "confidence": "reconstructed",
            "source_id": "hf-technical-timeline",
            "locator": "forensic reconstruction window",
            "unavailable_reason": None,
        },
    )
    end = parse_timestamp(
        "event_time",
        {
            "value": bounds["hf-window-end"]["stated_value"],
            "precision": "exact",
            "confidence": "reconstructed",
            "source_id": "hf-technical-timeline",
            "locator": "forensic reconstruction window",
            "unavailable_reason": None,
        },
    )
    for corpus in ("historical_replay", "synthetic_control"):
        result = latency_seconds(
            start,
            end,
            corpus_label=corpus,
            claim_id="hugging_face_narrative_window_duration",
        )
        assert result["status"] == "withheld"
        assert result["seconds"] is None


def test_day_precision_is_not_subtracted():
    day = parse_timestamp(
        "observation_available_at",
        {
            "value": "2026-07-27",
            "precision": "day",
            "confidence": "publication",
            "source_id": "hf-technical-timeline",
            "locator": "Published July 27, 2026",
            "unavailable_reason": None,
        },
    )
    exact = parse_timestamp(
        "detector_alert_at",
        {
            "value": "2026-07-28T00:00:00Z",
            "precision": "exact",
            "confidence": "authored",
            "source_id": PROTOCOL_ID,
            "locator": "test",
            "unavailable_reason": None,
        },
    )
    result = latency_seconds(
        day,
        exact,
        corpus_label="synthetic_control",
        claim_id="time_to_first_warranted_alert",
    )
    assert result["seconds"] is None
    assert result["status"] == "withheld"


def test_replay_passes_and_withholds_historical_latency(score):
    assert score["errors"] == []
    metrics = score["metrics"]
    assert metrics["passed"] is True
    assert metrics["seed"] == 32
    assert metrics["seed_draws"] == 0
    assert metrics["alert_budget"] == ALERT_BUDGET
    assert metrics["historical_latency_result_count"] == 0
    assert metrics["incident_detection_claimed"] is False
    assert metrics["incident_prevention_claimed"] is False
    assert metrics["withheld_latency_claim_count"] == len(WITHHELD_LATENCY_CLAIMS)
    assert [item["claim_id"] for item in score["withheld_latency_claims"]] == list(
        WITHHELD_LATENCY_CLAIMS
    )
    assert all(item["seconds"] is None for item in score["withheld_latency_claims"])
    assert score["narrative_window"]["window"]["seconds"] is None
    assert score["narrative_window"]["enforcement_at"] is None
    assert score["may_signal"]["seconds"] is None
    incident = score["incident_latency"]
    assert incident["status"] == "absent"
    assert incident["seconds"] is None
    assert metrics["incident_latency_status"] == "absent"
    assert metrics["incident_detection_latency_emitted"] is False
    assert metrics["incident_detection_latency_seconds"] is None
    assert metrics["incident_trustworthy_event_time_count"] == 0
    assert metrics["reproduction_one_public_record"] is True
    assert metrics["unavailable_row_count"] == 0
    assert metrics["unavailable_effect_time_count"] == 0
    assert metrics["unavailable_records_are_gates"] is False
    assert metrics["held_source_gate_prevents_supported"] is True


def test_required_shapes_and_corpus_labels(score):
    cases = {case["id"]: case for case in DATASET.build_dataset()["cases"]}
    assert cases["syn-comms-incomplete-actors"]["shape"] == (
        "unauthorized_shared_communications_incomplete_actors"
    )
    assert cases["syn-transcript-mismatch"]["shape"] == "valid_transcript_mismatched_effect"
    assert cases["syn-local-ok-downstream"]["shape"] == (
        "local_control_ok_downstream_unauthorized"
    )
    labels = {stage["corpus_label"] for stage in score["stages"]}
    assert labels == {"historical_replay", "synthetic_control"}
    historical = cases["hist-public-milestones"]
    for field in TIMESTAMP_FIELDS:
        assert historical["endpoints"][field]["value"] is None
        assert historical["endpoints"][field]["unavailable_reason"] == (
            "event_telemetry_unavailable"
        )


def test_incomplete_actors_and_hindsight_document(score):
    partial = _audit(score, "syn-comms-incomplete-actors", "partial")
    assert partial["decision"] == "abstain"
    assert partial["emitted_count"] == 0
    observed = _audit(score, "syn-comms-incomplete-actors", "actors-observed")
    assert observed["decision"] == "alert"
    assert observed["emitted_rule_ids"] == ["unsanctioned_cross_agent"]
    document = _stage(score, "syn-comms-incomplete-actors", "hindsight-document-only")
    assert "comms-actors-telemetry" in document["excluded_event_ids"]
    assert "comms-actor-document" in document["visible_event_ids"]
    assert document["detectors"]["evidence_qualified_audit"]["decision"] == "abstain"
    assert document["detectors"]["rule_baseline"]["decision"] == "abstain"
    assert score["metrics"]["hindsight_document_qualified_alert_count"] == 0
    weak = document["detectors"]["weak_indicator_baseline"]
    assert weak["decision"] == "alert"
    assert weak["measures"][0]["warranted"] is False


def test_transcript_alone_does_not_alert_and_mismatch_does(score):
    early = _stage(score, "syn-transcript-mismatch", "transcript-only")
    assert "effect-write" in early["excluded_event_ids"]
    assert early["detectors"]["evidence_qualified_audit"]["decision"] == "abstain"
    assert early["detectors"]["rule_baseline"]["decision"] == "abstain"
    late = _audit(score, "syn-transcript-mismatch", "effect-observed")
    assert late["decision"] == "alert"
    assert late["emitted_rule_ids"] == ["anomalous_effect_mismatch"]
    measure = late["measures"][0]
    assert measure["time_to_first_warranted_alert"]["seconds"] == 0
    assert measure["time_to_first_warranted_alert"]["corpus_label"] == "synthetic_control"
    assert measure["detection_to_intervention_gap"]["seconds"] is None
    assert measure["effect_before_alert"] == "effect_before_alert"


def test_local_success_stays_separate_from_downstream_failure(score):
    audit = _audit(score, "syn-local-ok-downstream", "effect-observed")
    assert audit["decision"] == "alert"
    assert audit["emitted_rule_ids"] == ["downstream_unauthorized"]
    judgments = {item["property_id"]: item for item in audit["judgments"]}
    assert judgments["local_control_correct"]["conclusion_class"] == "supported"
    assert judgments["local_control_correct"]["property_holds"] is True
    assert judgments["downstream_effect_authorized"]["conclusion_class"] == "failed_enforcement"
    assert judgments["command_matches_effect"]["property_holds"] is True
    rule = _audit(score, "syn-local-ok-downstream", "effect-observed", "rule_baseline")
    assert rule["decision"] == "miss"
    measure = audit["measures"][0]
    assert measure["detector_alert_at"] == "2026-01-15T02:00:00Z"
    assert measure["detection_to_intervention_gap"]["seconds"] == 3600
    assert measure["effect_before_alert"] == "effect_before_alert"
    endpoints = next(
        case["endpoints"]
        for case in DATASET.build_dataset()["cases"]
        if case["id"] == "syn-local-ok-downstream"
    )
    assert endpoints["effect_commit_at"]["value"] == "2026-01-15T01:00:00Z"
    assert endpoints["responder_ack_at"]["value"] == "2026-01-15T02:30:00Z"
    assert endpoints["enforcement_at"]["value"] == "2026-01-15T03:00:00Z"
    assert measure["detector_alert_at"] != endpoints["enforcement_at"]["value"]
    assert measure["detector_alert_at"] != endpoints["effect_commit_at"]["value"]


def test_negative_controls_do_not_alert(score):
    for case_id, stage_id in (
        ("syn-sanctioned-comms", "complete"),
        ("syn-authorized-downstream", "complete"),
    ):
        stage = _stage(score, case_id, stage_id)
        for detector in stage["detectors"].values():
            assert detector["decision"] == "no_alert"
            assert detector["emitted_count"] == 0


def test_same_observations_and_budget(score):
    for stage in score["stages"]:
        fingerprints = {
            detector["observation_fingerprint"] for detector in stage["detectors"].values()
        }
        budgets = {detector["alert_budget"] for detector in stage["detectors"].values()}
        assert len(fingerprints) == 1
        assert budgets == {ALERT_BUDGET}


def test_threshold_sensitivity_preserves_tie_and_failure(score):
    metrics = score["metrics"]
    assert metrics["detectable_case_denominator"] == 5
    assert metrics["audit_true_alert_count"] == 5
    assert metrics["audit_false_alert_count"] == 0
    assert metrics["rule_baseline_true_alert_count"] == 3
    assert metrics["rule_baseline_miss_count"] == 2
    assert metrics["higher_threshold_2_true_alert_count"] == 1
    assert metrics["higher_threshold_2_miss_count"] == 4
    assert metrics["higher_threshold_1_true_alert_count"] == 4
    assert metrics["higher_threshold_1_false_alert_count"] == 0
    assert metrics["weak_threshold_false_alert_count"] == 2
    assert metrics["tie_count"] == 6
    assert metrics["failure_count"] == 4
    assert metrics["budget_suppressed_count"] == 3
    failures = {(item["case_id"], item["stage_id"]) for item in score["failures"]}
    assert ("syn-local-ok-downstream", "effect-observed") in failures
    assert ("syn-comms-incomplete-actors", "actors-observed") in failures
    ties = {(item["case_id"], item["stage_id"]) for item in score["ties"]}
    assert ("syn-stacked-signals", "both-observed") in ties
    stacked = _audit(score, "syn-stacked-signals", "both-observed")
    assert stacked["emitted_count"] == 1
    assert stacked["suppressed_count"] == 1
    assert stacked["alert_budget"] == 1


def test_publication_ablation_hides_later_sources(score):
    early = _stage(score, "hist-public-milestones", "scope-start")
    narrative = _stage(score, "hist-public-milestones", "narrative-date")
    after_hf = _stage(score, "hist-public-milestones", "after-hf-publication")
    after_metr = _stage(score, "hist-public-milestones", "after-metr-publication")
    assert early["visible_event_ids"] == []
    assert narrative["visible_event_ids"] == []
    assert after_hf["visible_event_ids"] == ["doc-hf-timeline"]
    assert after_metr["visible_event_ids"] == ["doc-hf-timeline", "doc-metr"]
    for stage in (early, narrative, after_hf, after_metr):
        for detector in stage["detectors"].values():
            assert detector["decision"] == "abstain"
            assert detector["measures"][0]["detector_alert_at"] is None
            assert detector["measures"][0]["effect_before_alert"] == "unknown_missing_timestamp"
            for key in ("time_to_first_warranted_alert", "detection_to_intervention_gap"):
                assert detector["measures"][0][key]["seconds"] is None
                assert detector["measures"][0][key]["status"] == "withheld"


def test_openai_pages_contribute_no_timestamps():
    sources = {item["id"]: item for item in DATASET.build_sources()["sources"]}
    for source_id in ("openai-index", "openai-misalignment"):
        assert sources[source_id]["http_status"] == 403
        assert sources[source_id]["article_available"] is False
        assert sources[source_id]["operational_timestamps_admitted"] == 0
    assert all(bound["latency_eligible"] is False for bound in DATASET.build_sources()["stated_bounds"])
    assert all(bound["promoted_to_field"] is None for bound in DATASET.build_sources()["stated_bounds"])


def test_every_rule_declares_its_contract():
    cases = {case["id"] for case in DATASET.build_dataset()["cases"]}
    required = {
        "signal",
        "evidence_requirements",
        "false_positive_cases",
        "false_negative_cases",
        "actionability",
        "source_availability",
    }
    for rule in (*RULES.values(), LOCAL_RULE):
        assert required <= set(rule)
        assert set(rule["false_positive_cases"]) <= cases
        assert set(rule["false_negative_cases"]) <= cases
        assert rule["evidence_requirements"]
        assert rule["actionability"]
        assert rule["source_availability"]


def test_report_has_no_incident_result_language(score):
    report = render_report(score)
    lowered = report.lower()
    for phrase in (
        "detected the incident",
        "prevented the incident",
        "could have prevented",
        "would have prevented",
        "was deployed",
        "real-time prevention",
        "measured private",
    ):
        assert phrase not in lowered
    assert "synthetic_control" in report
    assert "withheld" in report
    assert "seconds = null" in report
    assert "one public record" in report
    assert "Incident detection latency: absent, seconds = null." in report


def test_rerun_is_deterministic(score):
    again = _score()
    assert again == score


def test_committed_artifacts_match_the_replay(score):
    committed = json.loads(
        (ROOT / "evidence" / "detection_latency" / "runs" / "detection-latency-score.json").read_text()
    )
    assert committed["observations"]["passed"] is True
    assert committed["observations"]["historical_latency_result_count"] == 0
    for key, value in score["metrics"].items():
        assert committed["observations"][key] == value
    report = (ROOT / "docs" / "detection_latency_replay_v1.md").read_text()
    assert report == render_report(score)
    finding = json.loads(
        (
            ROOT
            / "evidence"
            / "detection_latency"
            / "findings"
            / "detection-latency-f-protocol.json"
        ).read_text()
    )
    assert finding["label"] == "reproduced"
    assert finding["conclusion_class"] == "supported"
    assert_label_matches_conclusion(finding["label"], finding["conclusion_class"])
    committed_dataset = json.loads(
        (ROOT / "experiments" / "detection_latency" / "dataset.json").read_text()
    )
    committed_sources = json.loads(
        (ROOT / "experiments" / "detection_latency" / "sources.json").read_text()
    )
    assert committed_dataset == DATASET.build_dataset()
    assert committed_sources == DATASET.build_sources()
