"""Synthetic coordination controls. These graphs are not incident records."""

from __future__ import annotations

import copy
from typing import Any

from swarm_witness.coordination import (
    attribute_stream,
    attribute_synthetic_scale,
    coordination_added_value,
    qualify_case,
)
from swarm_witness.provenance import (
    content_sha256,
    make_claim,
    make_event,
    make_extraction,
    make_source,
    validate_graph,
)

INCIDENT_CLAIMS = (
    "prov_tool_call_spoof",
    "prov_message_board",
    "prov_hf_effect",
)


def _pinned(sid: str, text: str, group: str | None = None) -> dict[str, Any]:
    nbytes = len(text.encode("utf-8"))
    return make_source(
        id=sid,
        canonical_url=f"fixture://{sid}",
        publisher="synthetic-control",
        observation_origin="synthetic_control",
        independence_group=group or f"group:{sid}",
        access_level="public_bytes",
        collection_boundary="synthetic control bytes, not an incident record",
        custody="intact",
        redaction="none",
        locally_held=True,
        public_bytes=text,
        content_digest=content_sha256(text),
        byte_offset={"start": 0, "end": nbytes},
        retrieved_document_offset={"start": 0, "end": nbytes},
    )


def _log(eid: str, sid: str, actor: str, kind: str = "independent_service_log", **overrides: Any) -> dict[str, Any]:
    event = make_event(
        id=eid,
        necessary_source_ids=[sid],
        event_kind=kind,
        statement=f"synthetic {kind} for {actor}",
        polarity="supports",
        actor_binding="bound",
        actor_ref=actor,
        event_time="2026-01-02T00:00:00Z",
        observed_time="2026-01-02T00:00:01Z",
        time_basis="source_stated",
        authenticity="not_checked",
        verification_method="independent_log_digest",
    )
    event.update(overrides)
    return event


def _graph(gid: str, sources: list[dict], events: list[dict], claims: list[dict]) -> dict:
    extractions = []
    built = []
    for event in events:
        ext = f"ext-{event['id']}"
        extractions.append(
            make_extraction(
                id=ext,
                analyst_id="synthetic-control",
                analysis_origin="human",
                source_ids=list(event["necessary_source_ids"]),
            )
        )
        event = dict(event)
        event["extraction_ids"] = [ext]
        built.append(event)
    graph = {
        "id": gid,
        "source_records": sources,
        "extractions": extractions,
        "observed_events": built,
        "claims": claims,
    }
    validate_graph(graph)
    return graph


def _claim(cid: str, **overrides: Any) -> dict[str, Any]:
    claim = make_claim(
        id=cid,
        proposition="synthetic distinction",
        world_claim=False,
        required_event_kinds=["independent_service_log"],
        insufficient_event_kinds=["narrative_report"],
        event_ids=[],
        evidence_slots=[],
    )
    claim.update(overrides)
    return claim


def _agent(aid: str, status: str, actor: str | None, event: str, source: str) -> dict[str, Any]:
    return {
        "id": aid,
        "actor_ref": actor,
        "identifier_status": status,
        "provenance_event_ids": [event],
        "provenance_source_ids": [source],
    }


def _message(mid: str, speaker: str | None, relation: str, event: str, source: str) -> dict[str, Any]:
    return {
        "id": mid,
        "artifact_ref": source,
        "speaker_agent_id": speaker,
        "relation_to_content": relation,
        "provenance_event_ids": [event],
        "provenance_source_ids": [source],
    }


def _finish(case: dict[str, Any]) -> dict[str, Any]:
    events: list[str] = []
    sources: list[str] = []

    def add(items: list[str], bucket: list[str]) -> None:
        for item in items:
            if item not in bucket:
                bucket.append(item)

    for key in (
        "agent_instances",
        "tasks",
        "messages",
        "delegations",
        "adoptions",
        "effects",
        "edges",
    ):
        for record in case[key]:
            add(record["provenance_event_ids"], events)
            add(record["provenance_source_ids"], sources)
    for population in case["populations"]:
        if population["count_label"] == "investigator_reported":
            add([population["provenance_source_id"]], sources)
    case["observed_times"] = [
        {"id": f"ot-{event_id}", "provenance_event_id": event_id} for event_id in events
    ]
    case["source_citations"] = [
        {"id": f"cite-{source_id}", "provenance_source_id": source_id} for source_id in sources
    ]
    by_source = {row["provenance_source_id"]: row["id"] for row in case["source_citations"]}
    for edge in case["edges"]:
        edge["source_citation_ids"] = [by_source[source_id] for source_id in edge["provenance_source_ids"]]
    return case


def _blank(cid: str, kind: str, proposition: str, claim_id: str | None) -> dict[str, Any]:
    return {
        "id": cid,
        "proposition": proposition,
        "proposition_kind": kind,
        "provenance_claim_id": claim_id,
        "populations": [],
        "agent_instances": [],
        "tasks": [],
        "messages": [],
        "delegations": [],
        "adoptions": [],
        "effects": [],
        "edges": [],
    }


def forged_case() -> tuple[dict, dict]:
    source = _pinned("src-real", "deliver note from syn-real")
    event = _log("ev-real", "src-real", "syn-real")
    claim = _claim("claim-forged", event_ids=["ev-real"], required_event_kinds=["independent_service_log"], insufficient_event_kinds=["narrative_report"])
    graph = _graph("g-forged", [source], [event], [claim])
    case = _blank("ctrl-forged", "negative_control", "A copied or forged actor is not the bound speaker.", "claim-forged")
    case["agent_instances"] = [
        _agent("ag-real", "lineage", "syn-real", "ev-real", "src-real"),
        _agent("ag-copy", "copied", "syn-real", "ev-real", "src-real"),
        _agent("ag-forged", "forged", "syn-forged", "ev-real", "src-real"),
    ]
    case["tasks"] = [
        {
            "id": "task-note",
            "statement": "synthetic note",
            "provenance_event_ids": ["ev-real"],
            "provenance_source_ids": ["src-real"],
        }
    ]
    case["messages"] = [
        _message("msg-real", "ag-real", "original", "ev-real", "src-real"),
        _message("msg-copy", "ag-copy", "original", "ev-real", "src-real"),
        _message("msg-forged", "ag-forged", "original", "ev-real", "src-real"),
    ]
    for name in ("real", "copy", "forged"):
        case["edges"].append(
            {
                "id": f"edge-{name}",
                "kind": "communication",
                "from_id": f"msg-{name}",
                "to_id": "task-note",
                "provenance_event_ids": ["ev-real"],
                "provenance_source_ids": ["src-real"],
            }
        )
    return graph, _finish(case)


def relay_case() -> tuple[dict, dict]:
    source = _pinned("src-a", "deliver msg-1 from syn-a")
    event = _log("ev-a", "src-a", "syn-a")
    claim = _claim("claim-relay", event_ids=["ev-a"])
    graph = _graph("g-relay", [source], [event], [claim])
    case = _blank("ctrl-relay", "negative_control", "Relaying someone else's message is not authorship.", "claim-relay")
    case["agent_instances"] = [
        _agent("ag-a", "lineage", "syn-a", "ev-a", "src-a"),
        _agent("ag-b", "unknown", None, "ev-a", "src-a"),
    ]
    case["tasks"] = [{
        "id": "task-a",
        "statement": "synthetic",
        "provenance_event_ids": ["ev-a"],
        "provenance_source_ids": ["src-a"],
    }]
    case["messages"] = [
        _message("msg-a", "ag-a", "original", "ev-a", "src-a"),
        _message("msg-b", "ag-b", "relay", "ev-a", "src-a"),
    ]
    case["effects"] = [{
        "id": "eff-a",
        "statement": "no committed effect is cited",
        "provenance_event_ids": ["ev-a"],
        "provenance_source_ids": ["src-a"],
    }]
    case["edges"] = [
        {
            "id": "edge-a",
            "kind": "communication",
            "from_id": "msg-a",
            "to_id": "task-a",
            "provenance_event_ids": ["ev-a"],
            "provenance_source_ids": ["src-a"],
        },
        {
            "id": "edge-relay",
            "kind": "relay",
            "from_id": "msg-b",
            "to_id": "msg-a",
            "provenance_event_ids": ["ev-a"],
            "provenance_source_ids": ["src-a"],
        },
        {
            "id": "edge-contrib",
            "kind": "contribution",
            "from_id": "msg-b",
            "to_id": "eff-a",
            "provenance_event_ids": ["ev-a"],
            "provenance_source_ids": ["src-a"],
        },
    ]
    return graph, _finish(case)


def reused_file_case() -> tuple[dict, dict]:
    src_a = _pinned("src-a", "read file F by syn-a", "group:file")
    src_b = _pinned("src-b", "read file F by syn-b", "group:file-b")
    src_e = _pinned("src-e", "effect bytes", "group:effect")
    events = [
        _log("ev-a", "src-a", "syn-a"),
        _log("ev-b", "src-b", "syn-b"),
        _log("ev-e", "src-e", "syn-a", kind="committed_effect"),
    ]
    claim = _claim(
        "claim-file",
        required_event_kinds=["committed_effect"],
        insufficient_event_kinds=["independent_service_log", "narrative_report"],
        event_ids=["ev-e"],
        requires_bound_actor=True,
        requires_event_time=True,
        world_claim=True,
        evidence_slots=[{
            "id": "slot-e",
            "source_id": "src-e",
            "blocks_upgrade": True,
            "role": "effect",
        }],
    )
    graph = _graph("g-file", [src_a, src_b, src_e], events, [claim])
    case = _blank("ctrl-file", "negative_control", "Two agents on one file are not a handoff.", "claim-file")
    case["agent_instances"] = [
        _agent("ag-a", "lineage", "syn-a", "ev-a", "src-a"),
        _agent("ag-b", "lineage", "syn-b", "ev-b", "src-b"),
    ]
    case["messages"] = [
        _message("msg-a", "ag-a", "reused_file", "ev-a", "src-a"),
        _message("msg-b", "ag-b", "reused_file", "ev-b", "src-b"),
    ]
    case["effects"] = [{
        "id": "eff-e",
        "statement": "an effect exists without a handoff",
        "provenance_event_ids": ["ev-e"],
        "provenance_source_ids": ["src-e"],
    }]
    case["edges"] = [
        {
            "id": "edge-file",
            "kind": "reused_file",
            "from_id": "msg-a",
            "to_id": "msg-b",
            "provenance_event_ids": ["ev-a", "ev-b"],
            "provenance_source_ids": ["src-a", "src-b"],
        },
        {
            "id": "edge-contrib",
            "kind": "contribution",
            "from_id": "msg-a",
            "to_id": "eff-e",
            "provenance_event_ids": ["ev-e"],
            "provenance_source_ids": ["src-e"],
        },
    ]
    return graph, _finish(case)


def _delegation_parts(timed: bool) -> tuple[list[dict], list[dict]]:
    src_a = _pinned("src-a", "handoff from syn-a")
    src_b = _pinned("src-b", "receipt by syn-b")
    time = {
        "time_basis": "source_stated",
        "event_time": "2026-01-02T00:00:00Z",
        "observed_time": "2026-01-02T00:00:01Z",
    }
    if not timed:
        time = {"time_basis": "missing", "event_time": None, "observed_time": None}
    events = [
        _log("ev-a", "src-a", "syn-a", **time),
        _log("ev-b", "src-b", "syn-b", **time),
    ]
    return [src_a, src_b], events


def _delegation_case(cid: str, kind: str, proposition: str, claim_id: str, timed: bool) -> tuple[dict, dict]:
    sources, events = _delegation_parts(timed)
    claim = _claim(claim_id, event_ids=["ev-a", "ev-b"])
    graph = _graph(f"g-{cid}", sources, events, [claim])
    case = _blank(cid, kind, proposition, claim_id)
    case["agent_instances"] = [
        _agent("ag-a", "lineage", "syn-a", "ev-a", "src-a"),
        _agent("ag-b", "lineage", "syn-b", "ev-b", "src-b"),
    ]
    case["tasks"] = [{
        "id": "task-t",
        "statement": "synthetic task",
        "provenance_event_ids": ["ev-a"],
        "provenance_source_ids": ["src-a"],
    }]
    case["messages"] = [_message("msg-a", "ag-a", "original", "ev-a", "src-a")]
    case["delegations"] = [{
        "id": "del-ab",
        "from_agent_id": "ag-a",
        "to_agent_id": "ag-b",
        "task_id": "task-t",
        "message_id": "msg-a",
        "provenance_event_ids": ["ev-a", "ev-b"],
        "provenance_source_ids": ["src-a", "src-b"],
    }]
    case["edges"] = [{
        "id": "edge-del",
        "kind": "delegation",
        "from_id": "del-ab",
        "to_id": "task-t",
        "provenance_event_ids": ["ev-a", "ev-b"],
        "provenance_source_ids": ["src-a", "src-b"],
    }]
    return graph, _finish(case)


def incomplete_timeline_case() -> tuple[dict, dict]:
    return _delegation_case(
        "ctrl-time",
        "negative_control",
        "A handoff with no source-stated time is not a coordination chronology.",
        "claim-time",
        False,
    )


def delegation_case() -> tuple[dict, dict]:
    return _delegation_case(
        "ctrl-delegation",
        "synthetic_distinction",
        "A traced handoff with bound logs and source-stated times is delegation_evidenced.",
        "claim-delegation",
        True,
    )


def duplicate_report_case() -> tuple[dict, dict]:
    original = _pinned("src-a", "the same sentence", "group:dup")
    copy_source = make_source(
        id="src-b",
        canonical_url=None,
        publisher="synthetic-control",
        observation_origin="reused_transcript_dump",
        independence_group="group:dup",
        duplicate_of="src-a",
        access_level="withheld",
        collection_boundary="second handle for the same synthetic sentence",
        custody="unknown",
        redaction="withheld_original",
        locally_held=False,
        public_bytes=None,
    )
    first = make_event(
        id="ev-a",
        necessary_source_ids=["src-a"],
        event_kind="narrative_report",
        statement="synthetic duplicate sentence",
        polarity="reports",
        actor_binding="not_applicable",
        verification_method="excerpt_sha256",
        time_basis="missing",
    )
    second = make_event(
        id="ev-b",
        necessary_source_ids=["src-b"],
        event_kind="narrative_report",
        statement="second handle, not a second observation",
        polarity="reports",
        actor_binding="not_applicable",
        verification_method="excerpt_sha256",
        time_basis="missing",
    )
    claim = _claim(
        "claim-dup",
        required_event_kinds=["committed_effect"],
        insufficient_event_kinds=["narrative_report"],
        minimum_independent_groups=2,
        event_ids=["ev-a", "ev-b"],
    )
    graph = _graph("g-dup", [original, copy_source], [first, second], [claim])
    case = _blank("ctrl-dup", "negative_control", "A duplicate report is not a second observation.", "claim-dup")
    case["messages"] = [
        _message("msg-a", None, "investigator_aggregate", "ev-a", "src-a"),
        _message("msg-b", None, "investigator_aggregate", "ev-b", "src-b"),
    ]
    case["edges"] = [{
        "id": "edge-dup",
        "kind": "duplicate_report",
        "from_id": "msg-a",
        "to_id": "msg-b",
        "provenance_event_ids": ["ev-a", "ev-b"],
        "provenance_source_ids": ["src-a", "src-b"],
    }]
    return graph, _finish(case)


def possession_case() -> tuple[dict, dict]:
    source = _pinned("src-a", "board line held by syn-a")
    event = _log("ev-a", "src-a", "syn-a")
    claim = _claim("claim-poss", event_ids=["ev-a"])
    graph = _graph("g-poss", [source], [event], [claim])
    case = _blank(
        "ctrl-poss",
        "negative_control",
        "Repeating board content is not authorship or causal contribution.",
        "claim-poss",
    )
    case["agent_instances"] = [
        _agent("ag-a", "lineage", "syn-a", "ev-a", "src-a"),
        _agent("ag-b", "unknown", None, "ev-a", "src-a"),
    ]
    case["tasks"] = [{
        "id": "task-a",
        "statement": "synthetic",
        "provenance_event_ids": ["ev-a"],
        "provenance_source_ids": ["src-a"],
    }]
    case["messages"] = [
        _message("msg-a", "ag-a", "original", "ev-a", "src-a"),
        _message("msg-b", "ag-b", "repetition", "ev-a", "src-a"),
    ]
    case["effects"] = [{
        "id": "eff-a",
        "statement": "repetition does not reach an effect",
        "provenance_event_ids": ["ev-a"],
        "provenance_source_ids": ["src-a"],
    }]
    case["edges"] = [
        {
            "id": "edge-a",
            "kind": "communication",
            "from_id": "msg-a",
            "to_id": "task-a",
            "provenance_event_ids": ["ev-a"],
            "provenance_source_ids": ["src-a"],
        },
        {
            "id": "edge-poss",
            "kind": "possession",
            "from_id": "msg-b",
            "to_id": "msg-a",
            "provenance_event_ids": ["ev-a"],
            "provenance_source_ids": ["src-a"],
        },
        {
            "id": "edge-contrib",
            "kind": "contribution",
            "from_id": "msg-b",
            "to_id": "eff-a",
            "provenance_event_ids": ["ev-a"],
            "provenance_source_ids": ["src-a"],
        },
    ]
    return graph, _finish(case)


def adoption_case() -> tuple[dict, dict]:
    source = _pinned("src-n", "the report says a goal was shared")
    event = make_event(
        id="ev-n",
        necessary_source_ids=["src-n"],
        event_kind="narrative_report",
        statement="synthetic narrative of a shared goal",
        polarity="reports",
        actor_binding="not_applicable",
        verification_method="excerpt_sha256",
        time_basis="missing",
    )
    claim = _claim(
        "claim-adopt",
        required_event_kinds=["committed_effect"],
        insufficient_event_kinds=["narrative_report"],
        event_ids=["ev-n"],
    )
    graph = _graph("g-adopt", [source], [event], [claim])
    case = _blank(
        "ctrl-adopt",
        "synthetic_distinction",
        "Goal adoption inferred from a narrative is not causal contribution or intent.",
        "claim-adopt",
    )
    case["agent_instances"] = [_agent("ag-c", "unknown", None, "ev-n", "src-n")]
    case["tasks"] = [{
        "id": "task-g",
        "statement": "synthetic shared wording",
        "provenance_event_ids": ["ev-n"],
        "provenance_source_ids": ["src-n"],
    }]
    case["adoptions"] = [{
        "id": "ad-c",
        "agent_id": "ag-c",
        "task_id": "task-g",
        "provenance_event_ids": ["ev-n"],
        "provenance_source_ids": ["src-n"],
    }]
    case["effects"] = [{
        "id": "eff-g",
        "statement": "narrative is not an effect",
        "provenance_event_ids": ["ev-n"],
        "provenance_source_ids": ["src-n"],
    }]
    case["edges"] = [
        {
            "id": "edge-adopt",
            "kind": "adoption",
            "from_id": "ad-c",
            "to_id": "task-g",
            "provenance_event_ids": ["ev-n"],
            "provenance_source_ids": ["src-n"],
        },
        {
            "id": "edge-vocab",
            "kind": "shared_vocabulary",
            "from_id": "ad-c",
            "to_id": "task-g",
            "provenance_event_ids": ["ev-n"],
            "provenance_source_ids": ["src-n"],
        },
        {
            "id": "edge-contrib",
            "kind": "contribution",
            "from_id": "ad-c",
            "to_id": "eff-g",
            "provenance_event_ids": ["ev-n"],
            "provenance_source_ids": ["src-n"],
        },
    ]
    return graph, _finish(case)


def _effect_bundle(on_claim: bool) -> tuple[dict, dict]:
    src_a = _pinned("src-a", "handoff from syn-a")
    src_b = _pinned("src-b", "receipt by syn-b")
    src_e = _pinned("src-e", "committed effect bytes")
    events = [
        _log("ev-a", "src-a", "syn-a"),
        _log("ev-b", "src-b", "syn-b"),
        _log("ev-e", "src-e", "syn-a", kind="committed_effect"),
    ]
    claim = _claim(
        "claim-effect",
        proposition="synthetic effect",
        world_claim=True,
        required_event_kinds=["committed_effect"],
        insufficient_event_kinds=["independent_service_log", "narrative_report"],
        requires_bound_actor=True,
        requires_event_time=True,
        event_ids=["ev-e"] if on_claim else [],
        evidence_slots=[{
            "id": "slot-e",
            "source_id": "src-e",
            "blocks_upgrade": True,
            "role": "effect log",
        }],
    )
    graph = _graph("g-effect", [src_a, src_b, src_e], events, [claim])
    case = _blank(
        "ctrl-effect" if on_claim else "ctrl-added",
        "collective_causal_impact",
        "Synthetic traced handoff to a verified effect. Not an incident record.",
        "claim-effect",
    )
    case["agent_instances"] = [
        _agent("ag-a", "lineage", "syn-a", "ev-a", "src-a"),
        _agent("ag-b", "lineage", "syn-b", "ev-b", "src-b"),
    ]
    case["tasks"] = [{
        "id": "task-t",
        "statement": "synthetic task",
        "provenance_event_ids": ["ev-a"],
        "provenance_source_ids": ["src-a"],
    }]
    case["messages"] = [_message("msg-a", "ag-a", "original", "ev-a", "src-a")]
    case["delegations"] = [{
        "id": "del-ab",
        "from_agent_id": "ag-a",
        "to_agent_id": "ag-b",
        "task_id": "task-t",
        "message_id": "msg-a",
        "provenance_event_ids": ["ev-a", "ev-b"],
        "provenance_source_ids": ["src-a", "src-b"],
    }]
    case["effects"] = [{
        "id": "eff-e",
        "statement": "synthetic committed effect",
        "provenance_event_ids": ["ev-e"],
        "provenance_source_ids": ["src-e"],
    }]
    case["edges"] = [
        {
            "id": "edge-del",
            "kind": "delegation",
            "from_id": "del-ab",
            "to_id": "task-t",
            "provenance_event_ids": ["ev-a", "ev-b"],
            "provenance_source_ids": ["src-a", "src-b"],
        },
        {
            "id": "edge-contrib",
            "kind": "contribution",
            "from_id": "del-ab",
            "to_id": "eff-e",
            "provenance_event_ids": ["ev-e"],
            "provenance_source_ids": ["src-e"],
        },
    ]
    return graph, _finish(case)


def traced_handoff_case() -> tuple[dict, dict]:
    return _effect_bundle(True)


def added_value_case() -> tuple[dict, dict]:
    return _effect_bundle(False)


def _append_log(graph: dict, sid: str, kind: str, statement: str) -> str:
    source = _pinned(sid, f"log-bytes:{sid}", group=f"group:{sid}")
    graph["source_records"].append(source)
    graph["extractions"].append(
        make_extraction(
            id=f"ext-{sid}",
            analyst_id="synthetic-control",
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
            actor_ref="syn-foreign",
            verification_method="independent_log_digest",
            time_basis="source_stated",
            event_time="2026-07-11T10:10:00Z",
            observed_time="2026-07-11T10:11:00Z",
        )
    )
    return f"ev-{sid}"


def foreign_log_does_not_upgrade(incident: dict) -> dict[str, Any]:
    """A verified log from another source must not support a blocked incident claim."""
    effect = copy.deepcopy(incident)
    effect_event = _append_log(
        effect,
        "src-foreign-effect",
        "committed_effect",
        "Bytes from a log that is not the Hugging Face platform log.",
    )
    effect_value = coordination_added_value(effect, "prov_hf_effect", [effect_event])

    spoof = copy.deepcopy(incident)
    for event in spoof["observed_events"]:
        event["conflicts_with"] = []
        if event["polarity"] == "contradicts":
            event["polarity"] = "reports"
    spoof_event = _append_log(
        spoof,
        "src-foreign-exec",
        "independent_service_log",
        "An execution log that is not the withheld transcript.",
    )
    spoof_value = coordination_added_value(spoof, "prov_tool_call_spoof", [spoof_event])
    return {"effect": effect_value, "spoof": spoof_value}


def _qualify(builder: Any) -> dict:
    graph, case = builder()
    return qualify_case(case, graph)


def _edge(result: dict, edge_id: str) -> dict:
    return next(edge for edge in result["edges"] if edge["id"] == edge_id)


def _flags_clear(result: dict) -> None:
    if result["real_world_authenticity_certified"] is not False:
        raise RuntimeError("real-world authenticity was certified")
    if result["incident_detection_claimed"] is not False:
        raise RuntimeError("incident detection was claimed")
    if result["incident_prevention_claimed"] is not False:
        raise RuntimeError("incident prevention was claimed")
    if result["supported_while_blocked"] is not False:
        raise RuntimeError("supported while a blocker remained")
    if result["intent_inferred"] is not False or result["goal_contagion_claimed"] is not False:
        raise RuntimeError("intent or goal contagion was claimed")


def check_controls() -> dict[str, Any]:
    """Run the synthetic controls. Raise if a distinction collapses."""
    forged = _qualify(forged_case)
    if "communication_observed" not in _edge(forged, "edge-real")["labels"]:
        raise RuntimeError("bound speaker was not communication_observed")
    for name in ("copy", "forged"):
        edge = _edge(forged, f"edge-{name}")
        if edge["authorship_supported"] or "communication_observed" in edge["labels"]:
            raise RuntimeError(f"{name} actor was treated as the speaker")
    if "forged_or_copied_actor" not in forged["unsupported_seams"]:
        raise RuntimeError("forged control missing seam")

    relay = _qualify(relay_case)
    if "communication_observed" not in _edge(relay, "edge-a")["labels"]:
        raise RuntimeError("original sender was not observed")
    relay_edge = _edge(relay, "edge-relay")
    if relay_edge["authorship_supported"] or relay_edge["link_class"] != "relay":
        raise RuntimeError("relay was treated as authorship")
    if "causal_contribution_unresolved" not in _edge(relay, "edge-contrib")["labels"]:
        raise RuntimeError("relay contribution was resolved")

    reused = _qualify(reused_file_case)
    if _edge(reused, "edge-file")["link_class"] != "reused_file":
        raise RuntimeError("reused file was not distinguished")
    if _edge(reused, "edge-contrib")["causal_link_supported"]:
        raise RuntimeError("file reuse was treated as a traced handoff")
    if "delegation_evidenced" in reused["labels"]:
        raise RuntimeError("file reuse was delegation")

    timeline = _qualify(incomplete_timeline_case)
    timed = _edge(timeline, "edge-del")
    if "delegation_evidenced" in timed["labels"] or timed["event_time"] is not None:
        raise RuntimeError("missing time became a chronology")
    if timed["link_class"] != "incomplete_timeline":
        raise RuntimeError("incomplete timeline link class")

    delegated = _qualify(delegation_case)
    if "delegation_evidenced" not in _edge(delegated, "edge-del")["labels"]:
        raise RuntimeError("traced handoff was not delegation_evidenced")
    if _edge(delegated, "edge-del")["time_basis"] != "source_stated":
        raise RuntimeError("source-stated time was dropped")

    duplicate = _qualify(duplicate_report_case)
    if duplicate["independent_observation_count"] != 1:
        raise RuntimeError("duplicate report counted as two observations")
    if "duplicate_report" not in duplicate["unsupported_seams"]:
        raise RuntimeError("duplicate seam missing")

    possessed = _qualify(possession_case)
    if _edge(possessed, "edge-poss")["authorship_supported"]:
        raise RuntimeError("repetition was authorship")
    if possessed["independent_observation_count"] != 1:
        raise RuntimeError("repetition created an independence group")
    if "causal_contribution_unresolved" not in _edge(possessed, "edge-contrib")["labels"]:
        raise RuntimeError("repetition became contribution")
    if "communication_observed" not in _edge(possessed, "edge-a")["labels"]:
        raise RuntimeError("original possession case lost communication_observed")

    adopted = _qualify(adoption_case)
    if "goal_adoption_inferred" not in adopted["labels"]:
        raise RuntimeError("narrative adoption was not labeled as inference")
    if adopted["intent_inferred"] or any(edge["causal_link_supported"] for edge in adopted["edges"]):
        raise RuntimeError("goal inference became intent or causation")
    if "causal_contribution_unresolved" not in _edge(adopted, "edge-contrib")["labels"]:
        raise RuntimeError("inferred goal resolved contribution")

    handoff = _qualify(traced_handoff_case)
    contrib = _edge(handoff, "edge-contrib")
    if not contrib["causal_link_supported"] or contrib["link_class"] != "traced_handoff":
        raise RuntimeError("synthetic traced handoff did not link")
    if "causal_contribution_unresolved" in contrib["labels"]:
        raise RuntimeError("cleared synthetic effect stayed unresolved")
    if handoff["added_claim_qualification_value"]:
        raise RuntimeError("already-qualified effect was counted as added value")
    if handoff["traced_causal_actor_count"] != 1:
        raise RuntimeError("traced actor count")
    if handoff["primary_upgrade_blocker"] is not None:
        raise RuntimeError("cleared synthetic blocker remained")

    added = _qualify(added_value_case)
    if not added["added_claim_qualification_value"]:
        raise RuntimeError("withheld effect event did not change the verdict once cited")
    if added["qualification_value"]["augmented_finding_label"] != "reproduced":
        raise RuntimeError("blocking source itself did not satisfy the internal rule")
    if added["real_world_authenticity_certified"] or added["incident_detection_claimed"]:
        raise RuntimeError("internal rule certified the real world")

    for result in (
        forged, relay, reused, timeline, delegated, duplicate, possessed, adopted, handoff, added
    ):
        _flags_clear(result)

    scale = attribute_synthetic_scale()
    if scale["records_visited"] != scale["n_messages"] or scale["pairs_considered"] != scale["n_handoffs"]:
        raise RuntimeError("scale attribution was not one explicit edge per handoff")
    if not scale["pairs_considered"] * 100 < scale["all_pairs"]:
        raise RuntimeError("scale attribution approached all pairs")
    if scale["agent_pair_matrix_allocated"] or scale["incident_records_invented"] or not scale["synthetic"]:
        raise RuntimeError("scale fixture was not synthetic")
    try:
        attribute_stream([
            {
                "record_label": "synthetic",
                "incident_record": False,
                "message_id": "ev-metr-board",
                "kind": "message",
            }
        ])
    except ValueError:
        pass
    else:
        raise RuntimeError("incident id was accepted in the synthetic stream")

    return {
        "negative_controls": 6,
        "negative_controls_passed": True,
        "distinctions_passed": 4,
        "synthetic_added_value_detected": True,
        "scale_messages": scale["n_messages"],
        "scale_pairs_considered": scale["pairs_considered"],
        "scale_all_pairs": scale["all_pairs"],
        "scale_agent_pair_matrix_allocated": False,
        "controls_detection_claimed": False,
        "controls_prevention_claimed": False,
    }


def check_incident_blockers(incident: dict, qualified: dict[str, dict]) -> None:
    foreign = foreign_log_does_not_upgrade(incident)
    for name, expected in (
        ("effect", "src-hf-platform-logs"),
        ("spoof", "src-transcript-dump"),
    ):
        value = foreign[name]
        if value["added"] or value["augmented_finding_label"] != "unresolved":
            raise RuntimeError(f"{name} upgraded past its blocker")
        if value["primary_upgrade_blocker"] != expected:
            raise RuntimeError(f"{name} blocker changed to {value['primary_upgrade_blocker']}")
        if value["refused_blocked_support"]:
            raise RuntimeError(f"{name} provenance returned supported while blocked")
        if any(row["source_id"] == expected for row in value["upgrade_blocked_by"]) is False:
            raise RuntimeError(f"{name} lost {expected}")

    board = qualified["coord_board_participation"]
    work = qualified["coord_delegated_workstream"]
    impact = qualified["coord_collective_impact"]
    for result in (board, work, impact):
        _flags_clear(result)
        if result["finding_label"] != "unresolved" or result["conclusion_class"] != "missing_evidence":
            raise RuntimeError(f"{result['case_id']} was supported")
        if result["added_claim_qualification_value"]:
            raise RuntimeError(f"{result['case_id']} added qualification value")
        if result["traced_causal_actor_count"] != 0:
            raise RuntimeError("reported population was traced")
        if result["investigator_reported_agents_are_traced_actors"]:
            raise RuntimeError("reported agents were marked traced")
    if board["primary_upgrade_blocker"] != "src-board-dump":
        raise RuntimeError("board blocker moved")
    if board["independent_observation_count"] != 1:
        raise RuntimeError("board publications counted as independent")
    if "communication_observed" in board["labels"]:
        raise RuntimeError("board narrative became communication_observed")
    if impact["primary_upgrade_blocker"] != "src-hf-platform-logs":
        raise RuntimeError("effect blocker moved")
    if "causal_contribution_unresolved" not in impact["labels"]:
        raise RuntimeError("collective impact resolved contribution")
    if any(edge["event_time"] for edge in impact["edges"]):
        raise RuntimeError("narrative window was promoted onto coordination time")
    if "delegation_evidenced" in work["labels"]:
        raise RuntimeError("outline became a handoff")
    unavailable = {row["source_id"] for row in work["unavailable_telemetry"]}
    if "src-transcript-dump" not in unavailable:
        raise RuntimeError("withheld transcript was not explicit")
