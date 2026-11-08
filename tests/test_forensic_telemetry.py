"""Forensic telemetry: one reproduction record, and originals that are not gates."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from swarm_witness.provenance import source_unavailable, validate_graph
from swarm_witness.telemetry import (
    UnsupportedAttachment,
    adapt_agent_tool_records,
    adapt_service_effect_logs,
    comparator_packet,
    probe_held_source_gate,
    read_rows,
    reconcile_events,
    verify_digest,
)

ROOT = Path(__file__).resolve().parents[1]


def _qualify():
    spec = importlib.util.spec_from_file_location(
        "telemetry_qualify", ROOT / "experiments" / "telemetry" / "qualify.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bundle():
    return _qualify().build_bundle()


def test_post_and_appendix_are_one_record(bundle):
    claim = bundle["qualified"]["claims"]["tel_reproduction_record"]
    assert claim["finding_label"] == "reproduced"
    assert claim["independent_observation_count"] == 1
    assert claim["effect_status"] == "unobserved"
    assert claim["primary_upgrade_blocker"] is None
    assert claim["real_world_authenticity_certified"] is False
    assert claim["incident_detection_claimed"] is False
    assert claim["incident_prevention_claimed"] is False
    keys = {item["corroboration_key"] for item in claim["lineage"]}
    assert len(keys) == 1
    assert "ev-lw-appendix" in claim["duplicated_report_ids"]
    assert all(item["digest_certifies_assertion"] is False for item in claim["lineage"])
    unavailable = {item["source_id"] for item in claim["unavailable_sources"]}
    assert {"src-transcript-dump", "src-hf-platform-logs"} <= unavailable


def test_original_logs_stay_unresolved_without_a_gate(bundle):
    claim = bundle["qualified"]["claims"]["tel_original_logs"]
    assert claim["finding_label"] == "unresolved"
    assert claim["effect_status"] == "unobserved"
    assert claim["primary_upgrade_blocker"] is None
    assert claim["absence_of_sink_is_no_effect"] is False
    assert claim["real_world_authenticity_certified"] is False
    assert claim["verified_event_ids"] == []
    for slot in bundle["graph"]["claims"]:
        for evidence in slot["evidence_slots"]:
            assert evidence["blocks_upgrade"] is False


def test_unavailable_source_cannot_be_a_gate(bundle):
    graph = copy.deepcopy(bundle["graph"])
    graph["claims"][1]["evidence_slots"][0]["blocks_upgrade"] = True
    source = next(item for item in graph["source_records"] if item["id"] == "src-hf-platform-logs")
    assert source_unavailable(source)
    with pytest.raises(ValueError, match="cannot be an upgrade gate"):
        validate_graph(graph)


def test_held_source_gate_still_blocks(bundle):
    probed = probe_held_source_gate(
        bundle["graph"], "tel_reproduction_record", "src-metr-command"
    )
    assert probed["finding_label"] != "reproduced"
    assert probed["primary_upgrade_blocker"] == "src-metr-command"
    assert "src-unrelated-probe-log" not in {item["id"] for item in bundle["graph"]["source_records"]}
    with pytest.raises(ValueError, match="cannot be an upgrade gate"):
        probe_held_source_gate(
            bundle["graph"], "tel_reproduction_record", "src-hf-platform-logs"
        )


def test_postmortem_sentences_are_reports_not_effects(bundle):
    by_id = {event["id"]: event for event in bundle["events"]}
    for record_id in ("pub-metr-command", "pub-hf-correlation"):
        event = by_id[record_id]
        assert event["event_kind"] == "narrative_report"
        assert event["polarity"] == "reports"
        assert event["event_time"] is None
        assert event["actor_ref"] is None
        assert event["synthetic"] is False
        assert verify_digest(event)
    offered = set()
    for claim in bundle["graph"]["claims"]:
        offered.update(claim["event_ids"])
    assert "ev-pub-metr-command" not in offered
    assert "ev-pub-hf-correlation" not in offered


def test_synthetic_reconciliation_confirms_no_effect(bundle):
    links = bundle["reconciliation"]["links"]
    assert all(link["confirmed_effect"] is False for link in links)
    by_id = {link["id"]: link for link in links}

    def link(left, right):
        ordered = tuple(sorted((left, right)))
        return by_id[f"link:{ordered[0]}:{ordered[1]}"]

    span = link("syn-span-api", "syn-span-log")
    assert span["status"] == "confirmed"
    assert "service_corroboration" in span["flags"]
    assert any("one_to_many" in item["flags"] for item in links)
    assert any("many_to_one" in item["flags"] for item in links)
    assert any("ambiguous_actor" in item["flags"] for item in links)
    disagreed = link("syn-time-api", "syn-time-tool")
    assert disagreed["status"] == "conflicting"
    assert "timestamp_disagreement" in disagreed["flags"]
    reused = link("syn-token-a", "syn-token-b")
    assert reused["status"] == "unlinked"
    assert "token_only" in reused["flags"]
    spoof = by_id["link:syn-spoof-call:-"]
    assert spoof["status"] == "spoof_suspected"
    assert "absent_effect" in spoof["flags"]
    orphan = by_id["link:syn-orphan-service:-"]
    assert orphan["status"] == "unlinked"
    assert "missing_transcript" in orphan["flags"]
    events = {event["id"]: event for event in bundle["events"]}
    assert events["syn-orphan-service"]["event_kind"] == "independent_service_log"
    assert events["syn-spoof-call"]["event_kind"] == "tool_call_arguments"
    assert "super-secret-token" not in json.dumps(bundle["events"])
    assert events["syn-redacted"]["actor_ref"] is None
    assert events["syn-redacted"]["credential_ref"].startswith("redacted:")
    assert events["syn-token-a"]["actor_binding"] == "unverified_binding"
    provenance = {event["id"]: event for event in bundle["graph"]["observed_events"]}
    assert provenance["ev-syn-spoof-call"]["event_time"] is None
    assert provenance["ev-syn-spoof-call"]["observed_time"] is None


def test_replay_is_stable_and_bytes_matter(bundle):
    again = comparator_packet(bundle["events"])
    assert again == comparator_packet(bundle["events"])
    changed = copy.deepcopy(bundle["events"][0])
    changed["public_bytes"] = changed["public_bytes"] + " "
    assert verify_digest(changed) is False


def test_redacted_credential_is_not_a_new_actor():
    boundary = "synthetic readback, not an incident log and not a LessWrong transcript"
    rows = []
    for record_id in ("redact-a", "redact-b"):
        rows.append(
            {
                "record_id": record_id,
                "surface": "service_log",
                "origin": "synthetic_control",
                "synthetic": True,
                "independence_group": "synthetic:readback",
                "publisher": "fixture",
                "credential": "[REDACTED]",
                "call_id": record_id,
                "action": "observe",
                "result": "hidden",
                "object": "sandbox",
                "event_time": None,
                "time_basis": "missing",
                "collection_boundary": boundary,
                "access_level": "redacted",
                "redaction": "partial",
                "locally_held": False,
                "custody": "unknown",
                "canonical_url": f"fixture://telemetry/{record_id}",
                "source_id": f"src-{record_id}",
            }
        )
    events = adapt_service_effect_logs(rows, salt="forensic-telemetry-v1")
    assert events[0]["credential_ref"] == events[1]["credential_ref"]
    assert events[0]["actor_ref"] is None
    assert events[1]["actor_ref"] is None


def test_unsupported_attachment_and_forbidden_fields(tmp_path):
    attachment = tmp_path / "notes.txt"
    attachment.write_text("not a log", encoding="utf-8")
    with pytest.raises(UnsupportedAttachment):
        read_rows(attachment, kind="agent")
    with pytest.raises(ValueError, match="privileged"):
        adapt_agent_tool_records(
            [
                {
                    "record_id": "hidden",
                    "surface": "requested_command",
                    "origin": "synthetic_control",
                    "synthetic": True,
                    "ground_truth": True,
                }
            ],
            salt="forensic-telemetry-v1",
        )


def test_csv_adapter_does_not_invent_a_time(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text(
        "record_id,surface,origin,synthetic,independence_group,publisher,raw,"
        "collection_boundary,canonical_url,event_time,ingest_time\n"
        "csv-command,requested_command,synthetic_control,true,synthetic:readback,"
        "fixture,synthetic csv command,synthetic readback,fixture://telemetry/csv-command,,\n",
        encoding="utf-8",
    )
    events = adapt_agent_tool_records(
        read_rows(path, kind="agent"), salt="forensic-telemetry-v1"
    )
    assert len(events) == 1
    assert events[0]["event_time"] is None
    assert events[0]["event_kind"] == "transcript_visible_command"
    assert events[0]["actor_ref"] is None


def test_same_packet_for_both_comparators(bundle):
    left = comparator_packet(bundle["events"])
    right = comparator_packet(bundle["events"])
    assert left == right
    assert bundle["naive_agent_row_count"] > 0
    assert all(link["confirmed_effect"] is False for link in reconcile_events(bundle["events"])["links"])


def test_evidence_matches_the_bundle():
    module = _qualify()
    artifacts = module.build_artifacts()
    evidence = ROOT / "evidence" / "telemetry"
    method = json.loads(
        (evidence / "runs" / "forensic-telemetry-v1-run.json").read_text(encoding="utf-8")
    )
    assert method["observations"]["reproduction_finding_label"] == "reproduced"
    assert method["observations"]["independent_observation_count"] == 1
    assert method["observations"]["original_finding_label"] == "unresolved"
    assert method["observations"]["confirmed_effect_count"] == 0
    assert method["observations"]["real_world_authenticity_certified"] is False
    assert artifacts["method_run"]["observations"]["reproduction_finding_label"] == "reproduced"
