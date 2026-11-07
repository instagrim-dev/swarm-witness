"""Incident detection latency is an absence read from forensic telemetry."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from swarm_witness.latency_evidence import (
    INCIDENT_UNAVAILABLE_SOURCES,
    REPRODUCTION_SOURCE_IDS,
    incident_detection_latency,
    latency_from_held_events,
    load_telemetry_bundle,
    trustworthy_event_time,
)
from swarm_witness.provenance import source_unavailable

ROOT = Path(__file__).resolve().parents[1]


def _source(source_id: str, **overrides) -> dict:
    source = {
        "id": source_id,
        "access_level": "public_bytes",
        "locally_held": True,
        "redaction": "none",
    }
    source.update(overrides)
    return source


def _event(source_id: str, event_time, **overrides) -> dict:
    event = {
        "id": source_id,
        "source_id": source_id,
        "event_time": event_time,
        "time_basis": "source_stated" if event_time else "missing",
        "synthetic": True,
        "ingest_time": "2026-11-07T00:00:00Z",
    }
    event.update(overrides)
    return event


def test_missing_clock_does_not_emit_a_duration():
    sources = {
        "start": _source("start"),
        "end": _source("end"),
    }
    start = _event("start", None)
    end = _event("end", "2026-01-03T01:00:00Z")
    result = latency_from_held_events(
        start, end, sources, claim_id="gap", corpus_label="synthetic_control"
    )
    assert result["status"] == "absent"
    assert result["seconds"] is None
    assert start["ingest_time"] not in json.dumps(result)


def test_reconstructed_and_unheld_times_are_not_latency():
    reconstructed = _event("held", "2026-01-03T00:00:00Z", time_basis="reconstructed")
    later = _event("held", "2026-01-03T01:00:00Z")
    sources = {"held": _source("held"), "withheld": _source("withheld", access_level="withheld", locally_held=False)}
    assert trustworthy_event_time(reconstructed, sources["held"], allow_synthetic=True) is None
    withheld_event = _event(
        "withheld", "2026-01-03T00:00:00Z", synthetic=False
    )
    assert source_unavailable(sources["withheld"])
    assert trustworthy_event_time(withheld_event, sources["withheld"], allow_synthetic=False) is None
    result = latency_from_held_events(
        reconstructed,
        later,
        sources,
        claim_id="gap",
        corpus_label="synthetic_control",
    )
    assert result["seconds"] is None


def test_held_source_stated_times_publish_a_duration():
    sources = {"start": _source("start"), "end": _source("end")}
    result = latency_from_held_events(
        _event("start", "2026-01-03T00:00:00Z"),
        _event("end", "2026-01-03T01:00:00Z"),
        sources,
        claim_id="synthetic_gap",
        corpus_label="synthetic_control",
    )
    assert result["status"] == "published"
    assert result["seconds"] == 3600
    assert result["corpus_label"] == "synthetic_control"


def test_synthetic_times_are_not_an_incident_clock():
    sources = {"start": _source("start"), "end": _source("end")}
    result = latency_from_held_events(
        _event("start", "2026-01-03T00:00:00Z", synthetic=True),
        _event("end", "2026-01-03T01:00:00Z", synthetic=True),
        sources,
        claim_id="incident_detection_latency",
        corpus_label="historical_replay",
    )
    assert result["status"] == "absent"
    assert result["seconds"] is None


def test_executed_incident_latency_is_absent():
    bundle = load_telemetry_bundle(ROOT)
    before = {source["id"] for source in bundle["graph"]["source_records"]}
    incident = incident_detection_latency(bundle)
    after = {source["id"] for source in bundle["graph"]["source_records"]}
    assert before == after
    assert incident["status"] == "absent"
    assert incident["seconds"] is None
    assert incident["reason"] == "no_trustworthy_event_time_on_held_evidence"
    assert incident["trustworthy_event_time_count"] == 0
    assert incident["detector_alert_at"] is None
    assert incident["effect_commit_at"] is None
    assert incident["contract_errors"] == []
    assert incident["incident_detection_claimed"] is False
    assert incident["incident_prevention_claimed"] is False
    assert incident["real_world_authenticity_certified"] is False

    record = incident["reproduction_record"]
    assert record["one_public_record"] is True
    assert record["independent_observation_count"] == 1
    assert record["source_ids"] == list(REPRODUCTION_SOURCE_IDS)
    assert record["effect_status"] == "unobserved"
    assert record["event_time"] is None
    assert record["time_basis"] == "missing"
    assert record["chronology_event_time"] is None
    assert all(row["trustworthy_event_time"] is None for row in record["events"])

    original = incident["original_logs"]
    assert original["finding_label"] == "unresolved"
    assert original["effect_status"] == "unobserved"
    assert original["event_time"] is None
    assert original["primary_upgrade_blocker"] is None
    assert original["absence_of_sink_is_no_effect"] is False
    assert original["verified_event_count"] == 0

    assert [row["source_id"] for row in incident["unavailable_records"]] == [
        source_id for source_id, _role in INCIDENT_UNAVAILABLE_SOURCES
    ]
    for row in incident["unavailable_records"]:
        assert row["row_count"] == 0
        assert row["graph_event_count"] == 0
        assert row["effect_time"] is None
        assert row["blocks_upgrade"] is False
        assert row["upgrade_gate"] is False
        assert row["unavailable"] is True

    gate = incident["held_source_gate"]
    assert gate["source_id"] == "src-metr-command"
    assert gate["held"] is True
    assert gate["prevents_supported"] is True
    assert gate["primary_upgrade_blocker"] == "src-metr-command"
    assert gate["conclusion_class"] != "supported"
    assert incident["unavailable_gate_rejected"] is True

    # A copied blocks_upgrade on an unavailable source is not how the absence is produced.
    graph = copy.deepcopy(bundle["graph"])
    for claim in graph["claims"]:
        for slot in claim["evidence_slots"]:
            if slot["source_id"] == "src-hf-platform-logs":
                slot["blocks_upgrade"] = True
    from swarm_witness.provenance import validate_graph

    try:
        validate_graph(graph)
    except ValueError as exc:
        assert "cannot be an upgrade gate" in str(exc)
    else:
        raise AssertionError("unavailable blocks_upgrade was accepted")
