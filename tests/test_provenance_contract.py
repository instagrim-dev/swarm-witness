"""Provenance contract: independence, spoofed transcripts, and absent telemetry."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from swarm_witness.conclusion_classes import classify_conclusion
from swarm_witness.provenance import (
    CONTRACT_VERSION,
    content_sha256,
    make_claim,
    make_event,
    make_extraction,
    make_source,
    normalize_lineage,
    qualify_graph,
    validate_graph,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "experiments" / "provenance" / "incident_lineage.yaml"


def _load_qualify():
    spec = importlib.util.spec_from_file_location(
        "provenance_qualify", ROOT / "experiments" / "provenance" / "qualify.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _incident():
    payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    return payload["graphs"][0]


def _graph(gid, sources, extractions, events, claims):
    return {
        "id": gid,
        "source_records": sources,
        "extractions": extractions,
        "observed_events": events,
        "claims": claims,
    }


def _pinned(sid, text, **overrides):
    nbytes = len(text.encode("utf-8"))
    node = make_source(
        id=sid,
        canonical_url=f"fixture://{sid}",
        publisher="fixture",
        collection_boundary="synthetic pinned bytes",
        public_bytes=text,
        content_digest=content_sha256(text),
        byte_offset={"start": 0, "end": nbytes},
        retrieved_document_offset={"start": 0, "end": nbytes},
        access_level="public_bytes",
        custody="intact",
        redaction="none",
        locally_held=True,
        observation_origin="synthetic_control",
        independence_group=f"group:{sid}",
    )
    node.update(overrides)
    return node


def _one_claim_graph(source, event, claim):
    extraction = make_extraction(
        id="ext", analyst_id="analyst", analysis_origin="human", source_ids=[source["id"]]
    )
    event = make_event(**event)
    event["extraction_ids"] = ["ext"]
    event["necessary_source_ids"] = [source["id"]]
    claim = make_claim(**claim)
    claim["event_ids"] = [event["id"]]
    return _graph("g", [source], [extraction], [event], [claim])


def test_contract_version_and_fixture_load():
    graph = _incident()
    validate_graph(graph)
    qualified = qualify_graph(graph)
    assert qualified["contract_version"] == CONTRACT_VERSION
    assert qualified["real_world_authenticity_certified"] is False
    assert qualified["incident_detection_claimed"] is False
    assert qualified["incident_prevention_claimed"] is False
    assert set(qualified["claims"]) == {
        "prov_tool_call_spoof",
        "prov_message_board",
        "prov_hf_effect",
        "prov_reproduction_transcripts",
    }


def test_validation_rejects_cycle_duplicate_dangling_and_fabricated_time():
    left = make_source(id="left", independence_group="g", depends_on=["right"])
    right = make_source(id="right", independence_group="g", depends_on=["left"])
    with pytest.raises(ValueError, match="cycle"):
        validate_graph(_graph("cycle", [left, right], [], [], []))

    with pytest.raises(ValueError, match="duplicate node"):
        validate_graph(
            _graph("dup", [make_source(id="same"), make_source(id="same")], [], [], [])
        )

    pinned = _pinned("bytes", "same-text", canonical_url="fixture://same")
    other = _pinned("other", "same-text", canonical_url="fixture://same")
    with pytest.raises(ValueError, match="duplicate content"):
        validate_graph(_graph("content", [pinned, other], [], [], []))

    dangling = make_event(id="ev", extraction_ids=["missing"], necessary_source_ids=[])
    with pytest.raises(ValueError, match="dangling reference"):
        validate_graph(
            _graph(
                "dangling",
                [make_source(id="s")],
                [],
                [dangling],
                [],
            )
        )

    forged_time = make_event(
        id="ev",
        extraction_ids=["ext"],
        necessary_source_ids=["s"],
        time_basis="missing",
        event_time="2026-07-08T23:00:00Z",
    )
    with pytest.raises(ValueError, match="fabricated chronology"):
        validate_graph(
            _graph(
                "time",
                [make_source(id="s")],
                [make_extraction(id="ext", source_ids=["s"])],
                [forged_time],
                [],
            )
        )

    graph = _graph("cert", [make_source(id="s")], [], [], [])
    graph["certify_real_world"] = True
    with pytest.raises(ValueError, match="certification flags"):
        validate_graph(graph)


def test_two_reports_of_one_dump_are_one_observation():
    qualified = qualify_graph(_incident())["claims"]
    spoof = qualified["prov_tool_call_spoof"]
    board = qualified["prov_message_board"]
    assert spoof["publication_surface_count"] >= 2
    assert spoof["verified_narrative_group_count"] == 1
    assert spoof["cited_independence_groups"] == ["openai-supplied-transcript-dump"]
    assert spoof["independent_observation_count"] == 0
    assert board["publication_surface_count"] == 2
    assert board["verified_narrative_group_count"] == 1
    assert board["independent_observation_count"] == 0
    assert board["cited_independence_groups"] == [
        "openai-artifactory-message-board-dump"
    ]


def test_distinct_analysts_do_not_split_one_source_group():
    dump = make_source(
        id="dump",
        observation_origin="unavailable_private_original",
        independence_group="shared-dump",
        access_level="withheld",
        redaction="withheld_original",
    )
    left = _pinned(
        "left-report",
        "report A",
        observation_origin="correlated_analysis_of_single_dataset",
        independence_group="shared-dump",
        depends_on=["dump"],
    )
    right = _pinned(
        "right-report",
        "report B",
        observation_origin="correlated_analysis_of_single_dataset",
        independence_group="shared-dump",
        depends_on=["dump"],
    )
    graph = _graph(
        "analysts",
        [dump, left, right],
        [
            make_extraction(
                id="ext-a", analyst_id="analyst-a", analysis_origin="human", source_ids=["left-report", "dump"]
            ),
            make_extraction(
                id="ext-b", analyst_id="analyst-b", analysis_origin="delegated_model", source_ids=["right-report", "dump"]
            ),
        ],
        [
            make_event(
                id="ev-a",
                extraction_ids=["ext-a"],
                necessary_source_ids=["left-report"],
                event_kind="narrative_report",
                verification_method="excerpt_sha256",
                statement="Analyst A narrates the same dump.",
            ),
            make_event(
                id="ev-b",
                extraction_ids=["ext-b"],
                necessary_source_ids=["right-report"],
                event_kind="narrative_report",
                verification_method="excerpt_sha256",
                statement="Analyst B narrates the same dump.",
            ),
        ],
        [
            make_claim(
                id="claim",
                proposition="The shared dump was independently observed twice.",
                required_event_kinds=["message_board_record"],
                insufficient_event_kinds=["narrative_report"],
                event_ids=["ev-a", "ev-b"],
                evidence_slots=[
                    {
                        "id": "slot-dump",
                        "source_id": "dump",
                        "blocks_upgrade": False,
                        "role": "original",
                    }
                ],
            )
        ],
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    assert claim["investigator_count"] == 2
    assert claim["verified_narrative_group_count"] == 1
    assert claim["independent_observation_count"] == 0
    assert claim["finding_label"] == "unresolved"


def test_forged_tool_call_does_not_establish_execution():
    source = _pinned(
        "forged-call",
        "echo REAL; sleep",
        observation_origin="synthetic_control",
        independence_group="forged-group",
    )
    graph = _one_claim_graph(
        source,
        {
            "id": "ev",
            "event_kind": "actual_tool_response",
            "statement": "A modified tool-call representation.",
            "authenticity": "forged",
            "verification_method": "independent_log_digest",
            "polarity": "supports",
            "actor_binding": "bound",
            "time_basis": "source_stated",
            "event_time": "2026-07-11T00:00:00Z",
        },
        {
            "id": "claim",
            "proposition": "The forged representation establishes the displayed command executed.",
            "required_event_kinds": ["actual_tool_response"],
            "insufficient_event_kinds": ["transcript_visible_command"],
            "requires_bound_actor": True,
            "requires_event_time": True,
        },
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    assert claim["evidence_status"] == "misbound"
    assert claim["conclusion_class"] == "missing_evidence"
    assert claim["effect_status"] == "unobserved"
    assert claim["independent_observation_count"] == 0
    assert claim["kind_rejections"][0]["reason"] == (
        "forged representation cannot establish the event"
    )
    assert claim["real_world_authenticity_certified"] is False


def test_missing_timestamp_is_not_a_fabricated_chronology():
    source = make_source(
        id="src",
        observation_origin="unknown",
        access_level="unobserved",
        independence_group="no-time",
    )
    graph = _one_claim_graph(
        source,
        {
            "id": "ev",
            "event_kind": "committed_effect",
            "statement": "No time was recorded.",
            "time_basis": "missing",
            "event_time": None,
            "observed_time": None,
        },
        {
            "id": "claim",
            "proposition": "The effect has a known event time.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["narrative_report"],
            "requires_event_time": True,
        },
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    assert claim["chronology"] == {
        "event_time": None,
        "observed_time": None,
        "time_basis": "missing",
        "fabricated": False,
    }
    assert claim["rejected_times"][0]["reason"] == "missing timestamp is not a chronology"
    assert claim["finding_label"] == "unresolved"

    reconstructed = _pinned("clock", "clock")
    rebuilt = _one_claim_graph(
        reconstructed,
        {
            "id": "ev",
            "event_kind": "committed_effect",
            "statement": "A reconstructed clock.",
            "time_basis": "reconstructed",
            "event_time": "2026-07-08T23:00:00Z",
            "verification_method": "independent_log_digest",
            "polarity": "supports",
            "actor_binding": "bound",
        },
        {
            "id": "claim",
            "proposition": "The reconstructed clock is the event time.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["narrative_report"],
            "requires_event_time": True,
            "requires_bound_actor": True,
        },
    )
    # excerpt/log method cannot verify this origin-kind pair through reconstructed time
    rebuilt["source_records"][0]["observation_origin"] = "synthetic_control"
    claim = qualify_graph(rebuilt)["claims"]["claim"]
    assert claim["chronology"]["event_time"] is None
    assert claim["chronology"]["fabricated"] is False
    assert claim["rejected_times"][0]["event_time"] == "2026-07-08T23:00:00Z"
    assert claim["rejected_times"][0]["time_basis"] == "reconstructed"
    assert claim["finding_label"] == "unresolved"


def test_kind_ladder_conflict_and_unverified_binding():
    kinds = [
        "transcript_visible_command",
        "tool_call_arguments",
        "actual_tool_response",
        "independent_service_log",
        "committed_effect",
    ]
    sources = [
        _pinned(f"src-{kind}", kind, independence_group="one-transcript")
        for kind in kinds
    ]
    extractions = [
        make_extraction(
            id=f"ext-{kind}",
            analyst_id="analyst",
            analysis_origin="human",
            source_ids=[f"src-{kind}"],
        )
        for kind in kinds
    ]
    events = []
    for kind in kinds:
        event = make_event(
            id=f"ev-{kind}",
            extraction_ids=[f"ext-{kind}"],
            necessary_source_ids=[f"src-{kind}"],
            event_kind=kind,
            statement=kind,
            verification_method="excerpt_sha256",
            polarity="supports",
            actor_binding="bound",
        )
        events.append(event)
    events[0]["actor_binding"] = "unverified_binding"
    events[2]["polarity"] = "contradicts"
    events[2]["conflicts_with"] = ["ev-transcript_visible_command"]
    claim = make_claim(
        id="effect",
        proposition="A committed effect occurred.",
        required_event_kinds=["committed_effect"],
        insufficient_event_kinds=[
            "transcript_visible_command",
            "tool_call_arguments",
            "actual_tool_response",
            "independent_service_log",
            "narrative_report",
        ],
        event_ids=[event["id"] for event in events],
    )
    qualified = qualify_graph(_graph("kinds", sources, extractions, events, [claim]))
    result = qualified["claims"]["effect"]
    assert result["kinds_present"] == sorted(kinds)
    assert result["independent_observation_count"] == 0
    assert result["source_conflict"] is True
    assert result["unverified_binding"] is True
    assert result["effect_status"] == "unobserved"
    reasons = {item["event_kind"]: item["reason"] for item in result["kind_rejections"]}
    assert reasons["transcript_visible_command"] == (
        "excerpt digest verifies publication bytes, not this event kind"
    )
    assert reasons["actual_tool_response"] == reasons["transcript_visible_command"]
    assert reasons["independent_service_log"] == reasons["committed_effect"]
    assert "committed_effect" in reasons
    assert result["finding_label"] == "unresolved"


def test_self_reported_and_metadata_do_not_certify():
    source = _pinned(
        "pretty",
        "log-line",
        observation_origin="independent_provider_telemetry",
        independence_group="provider-logs",
    )
    graph = _one_claim_graph(
        source,
        {
            "id": "ev",
            "event_kind": "committed_effect",
            "statement": "The record asserts its own authenticity.",
            "authenticity": "asserted",
            "verification_method": "self_report",
            "polarity": "supports",
            "actor_binding": "bound",
            "actor_ref": "agent-1",
            "time_basis": "source_stated",
            "event_time": "2026-07-11T10:10:00Z",
            "observed_time": "2026-07-11T10:11:00Z",
        },
        {
            "id": "claim",
            "proposition": "Metadata establishes the committed effect.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["narrative_report"],
            "requires_bound_actor": True,
            "requires_event_time": True,
        },
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    assert claim["conclusion_class"] == "missing_evidence"
    assert claim["independent_observation_count"] == 0
    assert claim["real_world_authenticity_certified"] is False
    assert claim["kind_rejections"][0]["reason"] == (
        "self-reported authenticity is not verification"
    )

    incident = copy.deepcopy(_incident())
    for event in incident["observed_events"]:
        event["authenticity"] = "asserted"
        event["actor_binding"] = "bound"
    flipped = qualify_graph(incident)
    assert flipped["real_world_authenticity_certified"] is False
    for claim_id in (
        "prov_tool_call_spoof",
        "prov_message_board",
        "prov_hf_effect",
    ):
        assert flipped["claims"][claim_id]["finding_label"] == "unresolved"
        assert flipped["claims"][claim_id]["independent_observation_count"] == 0


def test_fixture_log_bytes_do_not_certify_the_real_world():
    source = _pinned(
        "supplied-log",
        "service-log:effect-1",
        observation_origin="independent_provider_telemetry",
        independence_group="supplied-provider-log",
    )
    graph = _one_claim_graph(
        source,
        {
            "id": "ev",
            "event_kind": "committed_effect",
            "statement": "Bytes supplied inside the fixture.",
            "authenticity": "unknown",
            "verification_method": "independent_log_digest",
            "polarity": "supports",
            "actor_binding": "bound",
            "time_basis": "source_stated",
            "event_time": "2026-07-11T10:10:00Z",
            "observed_time": "2026-07-11T10:11:00Z",
        },
        {
            "id": "claim",
            "proposition": "The supplied log shows a committed effect.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["independent_service_log", "narrative_report"],
            "requires_bound_actor": True,
            "requires_event_time": True,
            "evidence_slots": [
                {
                    "id": "slot",
                    "source_id": "supplied-log",
                    "blocks_upgrade": True,
                    "role": "log",
                }
            ],
        },
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    expected = classify_conclusion(evidence_complete=True, property_holds=True)
    assert claim["conclusion_class"] == expected["conclusion_class"] == "supported"
    assert claim["finding_label"] == "reproduced"
    assert claim["effect_status"] == "committed"
    assert claim["evidence_status"] == "authentic"
    assert claim["chronology"]["event_time"] == "2026-07-11T10:10:00Z"
    assert claim["real_world_authenticity_certified"] is False
    assert claim["incident_detection_claimed"] is False
    assert claim["incident_prevention_claimed"] is False
    assert claim["primary_upgrade_blocker"] is None


def _verified_log(graph, *, sid, group, kind, statement):
    source = _pinned(
        sid,
        f"log-bytes:{sid}",
        observation_origin="independent_provider_telemetry",
        independence_group=group,
    )
    graph["source_records"].append(source)
    graph["extractions"].append(
        make_extraction(
            id=f"ext-{sid}",
            analyst_id="fixture-analyst",
            analysis_origin="human",
            source_ids=[sid],
        )
    )
    graph["observed_events"].append(
        make_event(
            id=f"ev-{sid}",
            extraction_ids=[f"ext-{sid}"],
            necessary_source_ids=[sid],
            event_kind=kind,
            statement=statement,
            polarity="supports",
            actor_binding="bound",
            verification_method="independent_log_digest",
            time_basis="source_stated",
            event_time="2026-07-11T10:10:00Z",
            observed_time="2026-07-11T10:11:00Z",
        )
    )
    return f"ev-{sid}"


def test_unavailable_platform_log_does_not_block_a_verified_effect():
    graph = copy.deepcopy(_incident())
    event_id = _verified_log(
        graph,
        sid="supplied-log",
        group="supplied-provider-log",
        kind="committed_effect",
        statement="Bytes from a log that is not the Hugging Face platform log.",
    )
    for claim in graph["claims"]:
        if claim["id"] == "prov_hf_effect":
            claim["event_ids"].append(event_id)
    claim = qualify_graph(graph)["claims"]["prov_hf_effect"]
    assert event_id in claim["verified_event_ids"]
    assert claim["conclusion_class"] == "supported"
    assert claim["finding_label"] == "reproduced"
    assert claim["effect_status"] == "committed"
    assert claim["primary_upgrade_blocker"] is None
    assert claim["upgrade_blocked_by"] == []
    unavailable = {item["source_id"] for item in claim["unavailable_sources"]}
    assert "src-hf-platform-logs" in unavailable
    assert "src-hf-indicators" in unavailable
    assert "src-launchpad-logs" in unavailable
    assert claim["coverage"]["unobserved"] >= 1
    assert claim["real_world_authenticity_certified"] is False
    assert claim["incident_detection_claimed"] is False
    assert claim["incident_prevention_claimed"] is False


def test_withheld_transcript_does_not_block_another_admissible_log():
    graph = copy.deepcopy(_incident())
    for event in graph["observed_events"]:
        event["conflicts_with"] = []
        if event["polarity"] == "contradicts":
            event["polarity"] = "reports"
    event_id = _verified_log(
        graph,
        sid="other-exec-log",
        group="other-exec-log",
        kind="independent_service_log",
        statement="An execution log that is not the withheld transcript.",
    )
    for claim in graph["claims"]:
        if claim["id"] == "prov_tool_call_spoof":
            claim["event_ids"].append(event_id)
    claim = qualify_graph(graph)["claims"]["prov_tool_call_spoof"]
    assert claim["source_conflict"] is False
    assert event_id in claim["verified_event_ids"]
    assert claim["conclusion_class"] == "supported"
    assert claim["finding_label"] == "reproduced"
    assert claim["primary_upgrade_blocker"] is None
    assert claim["upgrade_blocked_by"] == []
    withheld = next(
        item for item in claim["unavailable_sources"] if item["source_id"] == "src-transcript-dump"
    )
    assert withheld["coverage_status"] == "withheld"
    assert withheld["reason"] == "recorded unavailable; not an upgrade gate"
    assert "src-execution-log" in {item["source_id"] for item in claim["unavailable_sources"]}
    assert claim["real_world_authenticity_certified"] is False


def test_incident_claims_keep_unavailable_telemetry_explicit():
    claims = qualify_graph(_incident())["claims"]
    spoof = claims["prov_tool_call_spoof"]
    board = claims["prov_message_board"]
    effect = claims["prov_hf_effect"]

    assert spoof["kinds_present"] == [
        "actual_tool_response",
        "narrative_report",
        "tool_call_arguments",
        "transcript_visible_command",
    ]
    assert "committed_effect" not in spoof["kinds_present"]
    assert spoof["source_conflict"] is True
    assert spoof["unverified_binding"] is True
    assert spoof["primary_upgrade_blocker"] is None
    assert spoof["upgrade_blocked_by"] == []
    assert "src-transcript-dump" in {item["source_id"] for item in spoof["unavailable_sources"]}
    assert "src-execution-log" in {item["source_id"] for item in spoof["unavailable_sources"]}
    assert spoof["chronology"]["event_time"] is None
    assert spoof["chronology"]["fabricated"] is False
    assert spoof["reported_counts"]["held_by_audit"] is False
    assert spoof["reported_counts"]["transcripts"] == 1300

    assert board["reported_counts"]["held_by_audit"] is False
    assert board["reported_counts"]["messages_and_files"] == 70000
    assert board["coverage"]["denominator"] not in {70000, 1300, 1200}
    assert board["primary_upgrade_blocker"] is None
    assert "src-board-dump" in {item["source_id"] for item in board["unavailable_sources"]}
    assert "message_board_record" not in board["kinds_present"]

    assert effect["effect_status"] == "unobserved"
    assert effect["primary_upgrade_blocker"] is None
    assert effect["upgrade_blocked_by"] == []
    assert {item["source_id"] for item in effect["unavailable_sources"]} == {
        "src-hf-platform-logs",
        "src-hf-indicators",
        "src-launchpad-logs",
    }
    assert effect["chronology"]["event_time"] is None
    narrative_times = [
        item["event_time"]
        for item in effect["rejected_times"]
        if item["event_time"] is not None
    ]
    assert "2026-07-09T02:28:00Z/2026-07-13T14:14:00Z" in narrative_times
    assert "huggingface-platform-telemetry-2026-07" in effect["cited_independence_groups"]
    assert "openai-supplied-transcript-dump" not in effect["cited_independence_groups"]

    for claim in (spoof, board, effect):
        assert claim["conclusion_class"] == "missing_evidence"
        assert claim["finding_label"] == "unresolved"
        assert claim["property_holds"] is None
        assert claim["decision_status"] == "unknown"
        assert claim["failure_origin"] == "evidence"
        assert claim["real_world_authenticity_certified"] is False
        assert claim["incident_detection_claimed"] is False
        assert claim["incident_prevention_claimed"] is False
        counts = claim["coverage"]
        assert (
            counts["available"]
            + counts["withheld"]
            + counts["redacted"]
            + counts["unobserved"]
            == counts["denominator"]
        )
        expected = classify_conclusion(evidence_complete=False, property_holds=None)
        assert claim["conclusion_class"] == expected["conclusion_class"]
        assert claim["finding_label"] == expected["finding_label"]
        assert claim["diagnosis"]["evidence_status"] == claim["evidence_status"]


def test_four_source_situations_are_not_equivalent():
    graph = _incident()
    by_origin: dict[str, list] = {}
    for source in graph["source_records"]:
        by_origin.setdefault(source["observation_origin"], []).append(source)
    for origin in (
        "reused_transcript_dump",
        "correlated_analysis_of_single_dataset",
        "independent_provider_telemetry",
        "unavailable_private_original",
    ):
        assert by_origin[origin], origin

    dump = next(s for s in graph["source_records"] if s["id"] == "src-transcript-dump")
    copy_handle = next(
        s for s in graph["source_records"] if s["id"] == "src-transcript-dump-copy"
    )
    redwood = next(s for s in graph["source_records"] if s["id"] == "src-redwood-command")
    metr = next(s for s in graph["source_records"] if s["id"] == "src-metr-command")
    logs = next(s for s in graph["source_records"] if s["id"] == "src-hf-platform-logs")
    blog = next(s for s in graph["source_records"] if s["id"] == "src-openai-blog")

    assert copy_handle["duplicate_of"] == dump["id"]
    assert copy_handle["independence_group"] == dump["independence_group"]
    assert redwood["observation_origin"] == "reused_transcript_dump"
    assert metr["observation_origin"] == "correlated_analysis_of_single_dataset"
    assert redwood["independence_group"] == metr["independence_group"] == dump["independence_group"]
    assert logs["observation_origin"] == "independent_provider_telemetry"
    assert logs["access_level"] == "unobserved"
    assert logs["independence_group"] != dump["independence_group"]
    assert dump["access_level"] == "withheld"
    assert blog["retrieval"]["http_status"] == 403
    assert blog["public_bytes"] is None
    assert blog["access_level"] == "unknown"

    claims = qualify_graph(graph)["claims"]
    assert claims["prov_tool_call_spoof"]["independent_observation_count"] == 0
    assert claims["prov_hf_effect"]["independent_observation_count"] == 0
    assert claims["prov_message_board"]["coverage"]["withheld"] >= 1
    assert claims["prov_hf_effect"]["coverage"]["unobserved"] >= 1
    assert claims["prov_hf_effect"]["coverage"]["redacted"] >= 1


def test_verified_contradiction_uses_existing_verdict_scale():
    source = _pinned(
        "counter-log",
        "executed-command:other",
        observation_origin="synthetic_control",
        independence_group="counter-log",
    )
    graph = _one_claim_graph(
        source,
        {
            "id": "ev",
            "event_kind": "committed_effect",
            "statement": "The log records a different command.",
            "authenticity": "unknown",
            "verification_method": "independent_log_digest",
            "polarity": "contradicts",
            "actor_binding": "bound",
            "time_basis": "source_stated",
            "event_time": "2026-07-11T00:00:00Z",
        },
        {
            "id": "claim",
            "proposition": "The displayed command was the committed effect.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["transcript_visible_command"],
            "requires_bound_actor": True,
        },
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    expected = classify_conclusion(evidence_complete=True, property_holds=False)
    assert claim["conclusion_class"] == expected["conclusion_class"] == "failed_enforcement"
    assert claim["finding_label"] == "contradicted_in_scope"
    assert claim["failure_origin"] == "evidence"
    assert claim["effect_status"] == "unobserved"
    assert claim["real_world_authenticity_certified"] is False


def test_regenerated_artifacts_match_the_fixture():
    module = _load_qualify()
    artifacts = module.build_artifacts()
    for claim_id, run in artifacts["runs"].items():
        on_disk = json.loads(
            (ROOT / "evidence" / "provenance" / "runs" / f"{run['id']}.json").read_text()
        )
        assert on_disk == run
        finding = artifacts["findings"][claim_id]
        stored = json.loads(
            (
                ROOT / "evidence" / "provenance" / "findings" / f"{finding['id']}.json"
            ).read_text()
        )
        assert stored == finding
        if claim_id == "prov_reproduction_transcripts":
            assert stored["label"] == "reproduced"
            assert run["observations"]["primary_upgrade_blocker"] is None
        else:
            assert stored["label"] == "unresolved"
            assert run["observations"]["underlying_telemetry"] == "unavailable"
    method = json.loads(
        (ROOT / "evidence" / "provenance" / "runs" / "provenance-contract-v1-run.json").read_text()
    )
    assert method == artifacts["method_run"]
    assert method["observations"]["incident_unresolved"] == 3
    assert method["observations"]["incident_detection_claimed"] is False
    assert method["observations"]["unavailable_originals_are_upgrade_gates"] is False


def test_reproduction_transcripts_qualify_without_the_missing_originals():
    claim = qualify_graph(_incident())["claims"]["prov_reproduction_transcripts"]
    assert claim["conclusion_class"] == "supported"
    assert claim["finding_label"] == "reproduced"
    assert claim["independent_observation_count"] == 1
    assert claim["publication_surface_count"] == 2
    assert "ev-lw-appendix" in claim["duplicated_report_ids"]
    unavailable = {item["source_id"] for item in claim["unavailable_sources"]}
    assert unavailable == {"src-transcript-dump", "src-hf-platform-logs"}
    assert claim["primary_upgrade_blocker"] is None
    assert claim["upgrade_blocked_by"] == []
    assert claim["coverage_assumption"]["declared"] is True
    assert claim["coverage_assumption"]["completeness"] == "partial"
    assert claim["real_world_authenticity_certified"] is False
    kinds = {item["evidence_type"] for item in claim["lineage"]}
    assert kinds == {"public_report_assertion"}
    assert all(item["digest_certifies_assertion"] is False for item in claim["lineage"])


def test_held_blocks_upgrade_slot_still_prevents_supported():
    held = _pinned(
        "held-log",
        "service-log:held",
        observation_origin="independent_provider_telemetry",
        independence_group="held-log",
    )
    other = _pinned(
        "other-log",
        "service-log:other",
        observation_origin="independent_provider_telemetry",
        independence_group="other-log",
    )
    graph = _graph(
        "gate",
        [held, other],
        [
            make_extraction(id="ext-held", analyst_id="a", analysis_origin="human", source_ids=["held-log"]),
            make_extraction(id="ext-other", analyst_id="b", analysis_origin="human", source_ids=["other-log"]),
        ],
        [
            make_event(
                id="ev-other",
                extraction_ids=["ext-other"],
                necessary_source_ids=["other-log"],
                event_kind="committed_effect",
                statement="A different held log.",
                polarity="supports",
                actor_binding="bound",
                verification_method="independent_log_digest",
                time_basis="source_stated",
                event_time="2026-07-11T10:10:00Z",
            )
        ],
        [
            make_claim(
                id="claim",
                proposition="The held log was used.",
                required_event_kinds=["committed_effect"],
                insufficient_event_kinds=["narrative_report"],
                requires_bound_actor=True,
                requires_event_time=True,
                event_ids=["ev-other"],
                evidence_slots=[
                    {"id": "slot-held", "source_id": "held-log", "blocks_upgrade": True, "role": "required-log"},
                    {"id": "slot-other", "source_id": "other-log", "blocks_upgrade": False, "role": "other-log"},
                ],
            )
        ],
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    assert claim["conclusion_class"] == "missing_evidence"
    assert claim["primary_upgrade_blocker"] == "held-log"
    assert claim["real_world_authenticity_certified"] is False


def test_unavailable_source_cannot_be_declared_as_a_gate():
    source = make_source(
        id="dump",
        observation_origin="unavailable_private_original",
        independence_group="dump",
        access_level="withheld",
        redaction="withheld_original",
    )
    graph = _graph(
        "gate",
        [source],
        [],
        [],
        [
            make_claim(
                id="claim",
                evidence_slots=[
                    {
                        "id": "slot",
                        "source_id": "dump",
                        "blocks_upgrade": True,
                        "role": "original",
                    }
                ],
            )
        ],
    )
    with pytest.raises(ValueError, match="cannot be an upgrade gate"):
        validate_graph(graph)


def test_blocks_upgrade_on_unheld_evidence_cannot_prevent_supported():
    """A public narrative the audit did not pin is not a gate."""
    narrative = make_source(
        id="narr",
        observation_origin="correlated_analysis_of_single_dataset",
        independence_group="narr-group",
        access_level="public_narrative",
        redaction="none",
        custody="intact",
        locally_held=False,
        collection_boundary="A public page this audit did not pin.",
    )
    held = _pinned(
        "held-log",
        "service-log:held",
        observation_origin="independent_provider_telemetry",
        independence_group="held-log",
    )
    event = make_event(
        id="ev",
        extraction_ids=["ext"],
        necessary_source_ids=["held-log"],
        event_kind="committed_effect",
        statement="A log this audit holds.",
        polarity="supports",
        actor_binding="bound",
        verification_method="independent_log_digest",
        time_basis="source_stated",
        event_time="2026-07-11T10:10:00Z",
    )
    claim = make_claim(
        id="claim",
        proposition="The held log shows a committed effect.",
        required_event_kinds=["committed_effect"],
        insufficient_event_kinds=["narrative_report"],
        requires_bound_actor=True,
        requires_event_time=True,
        event_ids=["ev"],
        evidence_slots=[
            {"id": "slot-narr", "source_id": "narr", "blocks_upgrade": True, "role": "unpinned-narrative"},
            {"id": "slot-held", "source_id": "held-log", "blocks_upgrade": False, "role": "log"},
        ],
    )
    graph = _graph(
        "unheld-gate",
        [narrative, held],
        [make_extraction(id="ext", analyst_id="a", analysis_origin="human", source_ids=["held-log"])],
        [event],
        [claim],
    )
    with pytest.raises(ValueError, match="requires evidence this audit holds"):
        validate_graph(copy.deepcopy(graph))

    duplicate = _pinned(
        "dup-log",
        "service-log:duplicate",
        observation_origin="independent_provider_telemetry",
        independence_group="held-log",
        duplicate_of="held-log",
    )
    dup_graph = _graph(
        "dup-gate",
        [held, duplicate],
        [make_extraction(id="ext", analyst_id="a", analysis_origin="human", source_ids=["held-log"])],
        [event],
        [
            make_claim(
                id="claim",
                proposition="A duplicate handle blocks the claim.",
                required_event_kinds=["committed_effect"],
                insufficient_event_kinds=["narrative_report"],
                event_ids=["ev"],
                evidence_slots=[
                    {"id": "slot-dup", "source_id": "dup-log", "blocks_upgrade": True, "role": "duplicate"},
                ],
            )
        ],
    )
    with pytest.raises(ValueError, match="requires evidence this audit holds"):
        validate_graph(dup_graph)

    broken = _pinned(
        "broken-log",
        "service-log:broken",
        observation_origin="independent_provider_telemetry",
        independence_group="broken-log",
        custody="unknown",
    )
    broken_graph = _one_claim_graph(
        broken,
        {
            "id": "ev-broken",
            "event_kind": "committed_effect",
            "statement": "Bytes with unknown custody.",
            "verification_method": "independent_log_digest",
            "polarity": "supports",
            "actor_binding": "bound",
            "time_basis": "source_stated",
            "event_time": "2026-07-11T10:10:00Z",
        },
        {
            "id": "claim",
            "proposition": "Unknown custody is a gate.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["narrative_report"],
            "evidence_slots": [
                {"id": "slot-broken", "source_id": "broken-log", "blocks_upgrade": True, "role": "broken"},
            ],
        },
    )
    with pytest.raises(ValueError, match="requires evidence this audit holds"):
        validate_graph(broken_graph)

    graph["claims"][0]["evidence_slots"][0]["blocks_upgrade"] = False
    qualified = qualify_graph(graph)["claims"]["claim"]
    assert qualified["conclusion_class"] == "supported"
    assert qualified["primary_upgrade_blocker"] is None
    assert qualified["upgrade_blocked_by"] == []
    assert qualified["real_world_authenticity_certified"] is False
    assert qualified["incident_detection_claimed"] is False
    assert qualified["incident_prevention_claimed"] is False


def test_same_origin_excerpts_do_not_satisfy_two_groups():
    left = _pinned(
        "excerpt-a",
        "excerpt-a-bytes",
        canonical_url="fixture://excerpt-a",
        observation_origin="synthetic_control",
        independence_group="same-corpus",
    )
    right = _pinned(
        "excerpt-b",
        "excerpt-b-bytes",
        canonical_url="fixture://excerpt-b",
        observation_origin="synthetic_control",
        independence_group="same-corpus",
    )
    graph = _graph(
        "same-corpus",
        [left, right],
        [
            make_extraction(
                id="ext-a", analyst_id="a", analysis_origin="human", source_ids=["excerpt-a"]
            ),
            make_extraction(
                id="ext-b", analyst_id="b", analysis_origin="human", source_ids=["excerpt-b"]
            ),
        ],
        [
            make_event(
                id="ev-a",
                extraction_ids=["ext-a"],
                necessary_source_ids=["excerpt-a"],
                event_kind="committed_effect",
                statement="First excerpt of the same corpus.",
                polarity="supports",
                actor_binding="bound",
                verification_method="independent_log_digest",
                time_basis="source_stated",
                event_time="2026-07-11T10:10:00Z",
            ),
            make_event(
                id="ev-b",
                extraction_ids=["ext-b"],
                necessary_source_ids=["excerpt-b"],
                event_kind="committed_effect",
                statement="Second excerpt of the same corpus.",
                polarity="supports",
                actor_binding="bound",
                verification_method="independent_log_digest",
                time_basis="source_stated",
                event_time="2026-07-11T10:10:00Z",
            ),
        ],
        [
            make_claim(
                id="claim",
                proposition="Two excerpts from one corpus are two origins.",
                required_event_kinds=["committed_effect"],
                insufficient_event_kinds=["narrative_report"],
                minimum_independent_groups=2,
                requires_bound_actor=True,
                requires_event_time=True,
                event_ids=["ev-a", "ev-b"],
            )
        ],
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    assert claim["cited_independence_groups"] == ["same-corpus"]
    assert claim["independent_observation_count"] == 1
    assert claim["conclusion_class"] == "missing_evidence"
    assert not (
        claim["conclusion_class"] == "supported"
        and claim["independent_observation_count"] == 2
        and claim["cited_independence_groups"] == ["same-corpus"]
    )


def test_untimed_observation_does_not_refute_a_claim_that_requires_event_time():
    source = _pinned(
        "log",
        "log-bytes",
        observation_origin="synthetic_control",
        independence_group="log",
    )
    graph = _one_claim_graph(
        source,
        {
            "id": "ev",
            "event_kind": "committed_effect",
            "statement": "An effect with no time.",
            "polarity": "contradicts",
            "actor_binding": "bound",
            "verification_method": "independent_log_digest",
            "time_basis": "missing",
            "event_time": None,
        },
        {
            "id": "claim",
            "proposition": "The effect happened at a stated time.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["narrative_report"],
            "requires_event_time": True,
        },
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    assert claim["conclusion_class"] == "missing_evidence"
    assert claim["property_holds"] is None
    assert claim["conclusion_class"] != "failed_enforcement"
    assert any(
        item["event_id"] == "ev" and item["time_basis"] == "missing"
        for item in claim["rejected_times"]
    )


def test_duplicate_reports_do_not_corroborate_and_irrelevant_records_do_not_move_the_verdict():
    text = "same-log-bytes"
    first = _pinned(
        "log-a",
        text,
        canonical_url="fixture://log-a",
        observation_origin="independent_provider_telemetry",
        independence_group="group-a",
    )
    copy_log = _pinned(
        "log-b",
        text,
        canonical_url="fixture://log-b",
        observation_origin="independent_provider_telemetry",
        independence_group="group-b",
    )
    graph = _graph(
        "dup",
        [first, copy_log],
        [
            make_extraction(id="ext-a", analyst_id="a", analysis_origin="human", source_ids=["log-a"]),
            make_extraction(id="ext-b", analyst_id="b", analysis_origin="delegated_model", source_ids=["log-b"]),
        ],
        [
            make_event(
                id="ev-a",
                extraction_ids=["ext-a"],
                necessary_source_ids=["log-a"],
                event_kind="committed_effect",
                statement="One log.",
                polarity="supports",
                actor_binding="bound",
                verification_method="independent_log_digest",
                time_basis="source_stated",
                event_time="2026-07-11T10:10:00Z",
            ),
            make_event(
                id="ev-b",
                extraction_ids=["ext-b"],
                necessary_source_ids=["log-b"],
                event_kind="committed_effect",
                statement="The same log again.",
                polarity="supports",
                actor_binding="bound",
                verification_method="independent_log_digest",
                time_basis="source_stated",
                event_time="2026-07-11T10:10:00Z",
            ),
        ],
        [
            make_claim(
                id="claim",
                proposition="Two copies are two observations.",
                required_event_kinds=["committed_effect"],
                insufficient_event_kinds=["narrative_report"],
                minimum_independent_groups=2,
                requires_bound_actor=True,
                requires_event_time=True,
                event_ids=["ev-a", "ev-b"],
            )
        ],
    )
    claim = qualify_graph(graph)["claims"]["claim"]
    assert claim["independent_observation_count"] == 1
    assert claim["investigator_count"] == 2
    assert "ev-b" in claim["duplicated_report_ids"]
    assert claim["conclusion_class"] == "missing_evidence"
    before = (
        claim["conclusion_class"],
        claim["independent_observation_count"],
        claim["finding_label"],
    )
    graph["extractions"].append(
        make_extraction(id="ext-noise", analyst_id="c", analysis_origin="human", source_ids=["log-a"])
    )
    graph["observed_events"].append(
        make_event(
            id="ev-noise",
            extraction_ids=["ext-noise"],
            necessary_source_ids=["log-a"],
            event_kind="narrative_report",
            statement="An irrelevant narration.",
            polarity="supports",
            subject="unrelated-subject",
        )
    )
    graph["claims"][0]["event_ids"].append("ev-noise")
    again = qualify_graph(graph)["claims"]["claim"]
    assert (
        again["conclusion_class"],
        again["independent_observation_count"],
        again["finding_label"],
    ) == before


def test_altered_stale_and_misbound_records_stay_unresolved():
    source = _pinned(
        "log",
        "log-bytes",
        observation_origin="synthetic_control",
        independence_group="log",
    )
    base_event = {
        "id": "ev",
        "event_kind": "committed_effect",
        "statement": "A log row.",
        "polarity": "supports",
        "actor_binding": "bound",
        "verification_method": "independent_log_digest",
        "time_basis": "source_stated",
        "event_time": "2026-07-11T10:10:00Z",
    }
    altered = _one_claim_graph(
        source,
        {**base_event, "authenticity": "disputed"},
        {
            "id": "claim",
            "proposition": "An altered log establishes the effect.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["narrative_report"],
            "requires_bound_actor": True,
            "requires_event_time": True,
        },
    )
    altered_claim = qualify_graph(altered)["claims"]["claim"]
    assert altered_claim["conclusion_class"] == "missing_evidence"
    assert any(item["requirement"] == "altered_record" for item in altered_claim["invalid_requirements"])

    stale = _one_claim_graph(
        source,
        {**base_event, "temporal_applicability": "stale"},
        {
            "id": "claim",
            "proposition": "A stale log establishes the effect.",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["narrative_report"],
            "requires_bound_actor": True,
            "requires_event_time": True,
        },
    )
    stale_claim = qualify_graph(stale)["claims"]["claim"]
    assert stale_claim["conclusion_class"] == "missing_evidence"
    assert stale_claim["dimensions"]["temporal_applicability"] == "stale"
    assert any(item["requirement"] == "stale_record" for item in stale_claim["invalid_requirements"])

    misbound = _one_claim_graph(
        source,
        {**base_event, "subject": "other-actor"},
        {
            "id": "claim",
            "proposition": "A misbound log establishes the effect.",
            "subject": "expected-actor",
            "required_event_kinds": ["committed_effect"],
            "insufficient_event_kinds": ["narrative_report"],
            "requires_bound_actor": True,
            "requires_event_time": True,
        },
    )
    misbound_claim = qualify_graph(misbound)["claims"]["claim"]
    assert misbound_claim["conclusion_class"] == "missing_evidence"
    assert misbound_claim["unverified_binding"] is True
    assert any(item["requirement"] == "misbound_record" for item in misbound_claim["invalid_requirements"])


def test_missing_records_need_a_coverage_assumption_and_absence_needs_complete_coverage():
    empty = _pinned(
        "sink",
        "sink-export:\n",
        observation_origin="independent_provider_telemetry",
        independence_group="sink",
        evidence_type="application_readback",
    )
    withheld = make_source(
        id="original",
        observation_origin="unavailable_private_original",
        independence_group="openai-supplied-transcript-dump",
        access_level="withheld",
        redaction="withheld_original",
    )
    graph = _graph(
        "coverage",
        [empty, withheld],
        [],
        [],
        [
            make_claim(
                id="claim",
                proposition="No effect row was written.",
                required_event_kinds=["committed_effect"],
                insufficient_event_kinds=["narrative_report"],
                evidence_slots=[
                    {"id": "slot-sink", "source_id": "sink", "blocks_upgrade": False, "role": "sink"},
                    {"id": "slot-original", "source_id": "original", "blocks_upgrade": False, "role": "unavailable"},
                ],
            )
        ],
    )
    missing = qualify_graph(graph)["claims"]["claim"]
    assert missing["conclusion_class"] == "missing_evidence"
    assert missing["absence_of_sink_is_no_effect"] is False
    assert any(item["requirement"] == "coverage_assumption" for item in missing["missing_requirements"])
    assert "original" in missing["missing_requirements"][0]["source_ids"]

    graph["claims"][0]["coverage_assumption"] = {
        "operation": "sink.write",
        "interval": {"start": "2026-07-09T00:00:00Z", "end": "2026-07-14T00:00:00Z"},
        "completeness": "complete",
    }
    invalid = qualify_graph(graph)["claims"]["claim"]
    assert invalid["absence_of_sink_is_no_effect"] is False
    assert invalid["conclusion_class"] == "missing_evidence"
    assert any(item["status"] == "invalid" for item in invalid["invalid_requirements"])

    graph["source_records"] = [empty]
    graph["claims"][0]["evidence_slots"] = [
        {"id": "slot-sink", "source_id": "sink", "blocks_upgrade": False, "role": "sink"}
    ]
    covered = qualify_graph(graph)["claims"]["claim"]
    assert covered["coverage_established"] is True
    assert covered["absence_of_sink_is_no_effect"] is True
    # Covered absence refutes effect-existence; it is not an enforcement failure.
    assert covered["conclusion_class"] == "refuted"
    assert covered["conclusion_class"] != "supported"
    assert covered["conclusion_class"] != "failed_enforcement"
    assert covered["real_world_authenticity_certified"] is False


def test_evidence_types_stay_distinct_through_normalization():
    kinds = (
        ("public", "public_report_assertion", "correlated_analysis_of_single_dataset"),
        ("synthetic", "synthetic_model_record", "synthetic_control"),
        ("readback", "application_readback", "independent_provider_telemetry"),
    )
    sources = []
    extractions = []
    events = []
    for sid, evidence_type, origin in kinds:
        sources.append(
            _pinned(
                sid,
                f"bytes:{sid}",
                observation_origin=origin,
                independence_group=f"group:{sid}",
                evidence_type=evidence_type,
            )
        )
        extractions.append(
            make_extraction(
                id=f"ext-{sid}",
                analyst_id="analyst",
                analysis_origin="human",
                source_ids=[sid],
            )
        )
        events.append(
            make_event(
                id=f"ev-{sid}",
                extraction_ids=[f"ext-{sid}"],
                necessary_source_ids=[sid],
                event_kind="narrative_report",
                statement=sid,
                evidence_type=evidence_type,
                verification_method="excerpt_sha256",
            )
        )
    graph = _graph(
        "types",
        sources,
        extractions,
        events,
        [make_claim(id="claim", event_ids=[event["id"] for event in events], required_event_kinds=["narrative_report"], insufficient_event_kinds=["committed_effect"])],
    )
    normalized = normalize_lineage(graph)
    found = [item["evidence_type"] for item in normalized["observations"]]
    assert found == [
        "public_report_assertion",
        "synthetic_model_record",
        "application_readback",
    ]
    assert normalized["evidence_type_counts"]["public_report_assertion"] == 1
    assert normalized["evidence_type_counts"]["synthetic_model_record"] == 1
    assert normalized["evidence_type_counts"]["application_readback"] == 1
