"""Evidence-provenance contract (evidence-provenance-v1).

Normative statement: ``protocol/evidence_provenance_v1.md``.

The graph is ``source_record → extraction → observed_event → claim``.
Source ``independence_group`` is not investigator identity. A field that
asserts authenticity does not verify an event. ``supported`` inside a
fixture means the fixture met the rule; it does not certify a real-world
event, and it does not claim that Swarm Witness detected or prevented
anything.

Verdicts reuse ``classify_conclusion`` and ``audit_diagnosis``. This module
does not add a second confidence scale.
"""

from __future__ import annotations

import hashlib
from typing import Any

from swarm_witness.audit_diagnosis import (
    DecisionStatus,
    EffectStatus,
    EvidenceStatus,
    FailureOrigin,
    diagnosis,
)
from swarm_witness.conclusion_classes import classify_conclusion

CONTRACT_VERSION = "evidence-provenance-v1"

OBSERVATION_ORIGINS = frozenset(
    {
        "reused_transcript_dump",
        "correlated_analysis_of_single_dataset",
        "independent_provider_telemetry",
        "unavailable_private_original",
        "released_reproduction",
        "synthetic_control",
        "unknown",
    }
)
ACCESS_LEVELS = frozenset(
    {
        "public_bytes",
        "public_narrative",
        "withheld",
        "redacted",
        "private_original",
        "unobserved",
        "unknown",
    }
)
CUSTODY_VALUES = frozenset({"intact", "break", "unknown", "not_applicable"})
REDACTION_VALUES = frozenset({"none", "partial", "withheld_original", "unknown"})
ANALYSIS_ORIGINS = frozenset({"human", "delegated_model", "mixed", "unknown"})
EVENT_KINDS = frozenset(
    {
        "transcript_visible_command",
        "tool_call_arguments",
        "actual_tool_response",
        "independent_service_log",
        "committed_effect",
        "narrative_report",
        "message_board_record",
        "unknown",
    }
)
ACTOR_BINDINGS = frozenset(
    {"bound", "unverified_binding", "conflicting", "unknown", "not_applicable"}
)
AUTHENTICITY_VALUES = frozenset(
    {"asserted", "disputed", "forged", "unknown", "not_checked"}
)
TIME_BASES = frozenset({"source_stated", "reconstructed", "missing", "unknown"})
VERIFICATION_METHODS = frozenset(
    {"none", "self_report", "excerpt_sha256", "independent_log_digest", "unknown"}
)
POLARITIES = frozenset({"supports", "contradicts", "reports"})
LOG_ORIGINS = frozenset({"independent_provider_telemetry", "synthetic_control"})
EVIDENCE_TYPES = frozenset(
    {
        "public_report_assertion",
        "synthetic_model_record",
        "application_readback",
        "provider_telemetry",
        "released_reproduction",
        "unavailable_original",
        "unknown",
    }
)
TEMPORAL_APPLICABILITY = frozenset({"applies", "stale", "unknown", "missing"})
COMPLETENESS_VALUES = frozenset({"complete", "partial", "unknown"})
# These three stay distinct through normalization and scoring.
DISTINCT_EVIDENCE_TYPES = (
    "public_report_assertion",
    "synthetic_model_record",
    "application_readback",
)
CERTIFICATION_INPUTS = frozenset(
    {
        "certify_real_world",
        "real_world_authenticity_certified",
        "incident_detection_claimed",
        "incident_prevention_claimed",
        "detected_incident",
        "prevented_incident",
        "confidence",
    }
)

SOURCE_FIELDS = frozenset(
    {
        "id",
        "canonical_url",
        "publisher",
        "observation_origin",
        "independence_group",
        "depends_on",
        "duplicate_of",
        "access_level",
        "collection_boundary",
        "custody",
        "redaction",
        "locally_held",
        "public_bytes",
        "content_digest",
        "byte_offset",
        "retrieved_document_offset",
        "retrieval",
        "reported_not_held",
        "evidence_type",
    }
)
SOURCE_OPTIONAL = frozenset({"reported_not_held", "evidence_type"})
EXTRACTION_FIELDS = frozenset(
    {"id", "analyst_id", "analysis_origin", "source_ids"}
)
EVENT_FIELDS = frozenset(
    {
        "id",
        "extraction_ids",
        "necessary_source_ids",
        "event_kind",
        "statement",
        "polarity",
        "actor_binding",
        "actor_ref",
        "event_time",
        "observed_time",
        "time_basis",
        "authenticity",
        "verification_method",
        "conflicts_with",
        "producer",
        "subject",
        "actor_scope",
        "task_scope",
        "coverage_interval",
        "observation_availability",
        "evidence_type",
        "temporal_applicability",
        "scope_binding",
    }
)
EVENT_OPTIONAL = frozenset(
    {
        "producer",
        "subject",
        "actor_scope",
        "task_scope",
        "coverage_interval",
        "observation_availability",
        "evidence_type",
        "temporal_applicability",
        "scope_binding",
    }
)
CLAIM_FIELDS = frozenset(
    {
        "id",
        "proposition",
        "world_claim",
        "required_event_kinds",
        "insufficient_event_kinds",
        "minimum_independent_groups",
        "requires_bound_actor",
        "requires_event_time",
        "event_ids",
        "evidence_slots",
        "coverage_assumption",
        "subject",
        "absence_policy",
    }
)
CLAIM_OPTIONAL = frozenset({"coverage_assumption", "subject", "absence_policy"})
ABSENCE_POLICIES = frozenset({"unresolved", "no_effect_if_covered"})
SCOPE_BINDINGS = frozenset(
    {"bound", "unverified_binding", "conflicting", "misbound", "unknown"}
)
SLOT_FIELDS = frozenset({"id", "source_id", "blocks_upgrade", "role"})
GRAPH_FIELDS = frozenset(
    {"id", "source_records", "extractions", "observed_events", "claims", "notes"}
)


def content_sha256(text: str) -> str:
    """Digest of the exact UTF-8 bytes of a pinned excerpt."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_keys(node: dict[str, Any], allowed: frozenset[str], kind: str) -> None:
    if not isinstance(node, dict):
        raise ValueError(f"{kind} must be an object")
    unknown = set(node) - allowed
    if unknown:
        raise ValueError(f"unknown {kind} field: {sorted(unknown)}")
    missing = set(allowed - set(node))
    if kind == "source_record":
        missing -= SOURCE_OPTIONAL
    if kind == "observed_event":
        missing -= EVENT_OPTIONAL
    if kind == "claim":
        missing -= CLAIM_OPTIONAL
    if kind == "graph":
        missing.discard("notes")
    if missing:
        raise ValueError(f"{kind} missing field: {sorted(missing)}")


def _enum(value: Any, allowed: frozenset[str], field: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"unknown {field}: {value!r}")
    return value


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"invalid or blank field: {field}")
    return value.strip()


def _id_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or item.strip() == "" for item in value
    ):
        raise ValueError(f"{field} must be a list of nonblank strings")
    if len(value) != len(set(value)):
        raise ValueError(f"duplicate edge in {field}")
    return [item.strip() for item in value]


def _optional_str(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty(value, field)


def _offset(value: Any, field: str, *, byte_len: int | None) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"start", "end"}:
        raise ValueError(f"{field} must be {{start, end}} or null")
    start, end = value["start"], value["end"]
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
        raise ValueError(f"invalid {field}")
    if byte_len is not None and (start != 0 or end != byte_len):
        if field == "byte_offset":
            raise ValueError("byte_offset must span pinned public_bytes")
    return {"start": start, "end": end}


def make_source(**overrides: Any) -> dict[str, Any]:
    """Blank source record. Unknown stays unknown until a caller sets it."""
    node: dict[str, Any] = {
        "id": "source",
        "canonical_url": None,
        "publisher": "unknown",
        "observation_origin": "unknown",
        "independence_group": "unknown",
        "depends_on": [],
        "duplicate_of": None,
        "access_level": "unknown",
        "collection_boundary": "unknown",
        "custody": "unknown",
        "redaction": "unknown",
        "locally_held": False,
        "public_bytes": None,
        "content_digest": None,
        "byte_offset": None,
        "retrieved_document_offset": None,
        "retrieval": None,
    }
    node.update(overrides)
    return node


def make_extraction(**overrides: Any) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": "extraction",
        "analyst_id": "unknown",
        "analysis_origin": "unknown",
        "source_ids": [],
    }
    node.update(overrides)
    return node


def make_event(**overrides: Any) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": "event",
        "extraction_ids": [],
        "necessary_source_ids": [],
        "event_kind": "unknown",
        "statement": "unknown",
        "polarity": "reports",
        "actor_binding": "unknown",
        "actor_ref": None,
        "event_time": None,
        "observed_time": None,
        "time_basis": "missing",
        "authenticity": "unknown",
        "verification_method": "none",
        "conflicts_with": [],
    }
    node.update(overrides)
    return node


def make_claim(**overrides: Any) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": "claim",
        "proposition": "unknown",
        "world_claim": True,
        "required_event_kinds": [],
        "insufficient_event_kinds": [],
        "minimum_independent_groups": 1,
        "requires_bound_actor": False,
        "requires_event_time": False,
        "event_ids": [],
        "evidence_slots": [],
    }
    node.update(overrides)
    return node


def _reject_certification_inputs(graph: dict[str, Any]) -> None:
    found = CERTIFICATION_INPUTS & set(graph)
    if found:
        raise ValueError(
            "certification flags are not inputs: " + ", ".join(sorted(found))
        )


def validate_graph(graph: dict[str, Any]) -> None:
    """Reject cycles, duplicate nodes or edges, dangling ids, and bad pins.

    A missing timestamp cannot be stored under ``time_basis: missing``.
    There is no input that certifies real-world authenticity.
    """
    if not isinstance(graph, dict):
        raise ValueError("graph must be an object")
    _reject_certification_inputs(graph)
    _require_keys(graph, GRAPH_FIELDS, "graph")
    _nonempty(graph["id"], "graph.id")

    sources = graph["source_records"]
    extractions = graph["extractions"]
    events = graph["observed_events"]
    claims = graph["claims"]
    for collection, kind in (
        (sources, "source_records"),
        (extractions, "extractions"),
        (events, "observed_events"),
        (claims, "claims"),
    ):
        if not isinstance(collection, list):
            raise ValueError(f"{kind} must be a list")

    nodes: dict[str, str] = {}
    by_source: dict[str, dict[str, Any]] = {}
    content_keys: set[tuple[Any, ...]] = set()

    for source in sources:
        _require_keys(source, SOURCE_FIELDS, "source_record")
        sid = _nonempty(source["id"], "source_record.id")
        if sid in nodes:
            raise ValueError(f"duplicate node id: {sid}")
        nodes[sid] = "source_record"
        by_source[sid] = source
        _enum(source["observation_origin"], OBSERVATION_ORIGINS, "observation_origin")
        _enum(source["access_level"], ACCESS_LEVELS, "access_level")
        _enum(source["custody"], CUSTODY_VALUES, "custody")
        _enum(source["redaction"], REDACTION_VALUES, "redaction")
        _nonempty(source["independence_group"], "independence_group")
        _nonempty(source["publisher"], "publisher")
        _nonempty(source["collection_boundary"], "collection_boundary")
        if source["canonical_url"] is not None:
            _nonempty(source["canonical_url"], "canonical_url")
        depends = _id_list(source["depends_on"], f"{sid}.depends_on")
        duplicate_of = _optional_str(source["duplicate_of"], f"{sid}.duplicate_of")
        if not isinstance(source["locally_held"], bool):
            raise ValueError(f"{sid}.locally_held must be boolean")
        public = source["public_bytes"]
        if public is None:
            if source["content_digest"] is not None or source["byte_offset"] is not None:
                raise ValueError(f"{sid}: digest without public bytes")
            if source["locally_held"]:
                raise ValueError(f"{sid}: locally_held requires public bytes")
            if source["access_level"] == "public_bytes":
                raise ValueError(f"{sid}: public_bytes access requires bytes")
            byte_len = None
        else:
            if not isinstance(public, str) or public == "":
                raise ValueError(f"{sid}: public_bytes must be non-empty text")
            raw = public.encode("utf-8")
            byte_len = len(raw)
            if source["content_digest"] != hashlib.sha256(raw).hexdigest():
                raise ValueError(f"digest mismatch: {sid}")
            if source["access_level"] != "public_bytes":
                raise ValueError(f"{sid}: pinned bytes require access_level public_bytes")
            if source["locally_held"] is not True:
                raise ValueError(f"{sid}: pinned bytes are locally held")
        pinned_offset = _offset(source["byte_offset"], "byte_offset", byte_len=byte_len)
        if byte_len is not None and pinned_offset is None:
            raise ValueError(f"{sid}: pinned bytes require byte_offset")
        doc_off = _offset(
            source["retrieved_document_offset"],
            "retrieved_document_offset",
            byte_len=None,
        )
        if doc_off is not None and byte_len is not None:
            if doc_off["end"] - doc_off["start"] != byte_len:
                raise ValueError(
                    f"{sid}: retrieved document offset span does not match pinned bytes"
                )
        _validate_retrieval(source["retrieval"], sid)
        _validate_reported(source)
        if source.get("evidence_type") is not None:
            _enum(source["evidence_type"], EVIDENCE_TYPES, "evidence_type")
        identity = (
            source["canonical_url"],
            None if doc_off is None else doc_off["start"],
            None if doc_off is None else doc_off["end"],
            source["content_digest"],
        )
        if source["content_digest"] is not None and identity in content_keys:
            if duplicate_of is None:
                raise ValueError(f"duplicate content identity: {sid}")
            source["depends_on"] = depends
            source["duplicate_of"] = duplicate_of
            continue
        if source["content_digest"] is not None:
            content_keys.add(identity)
        source["depends_on"] = depends
        source["duplicate_of"] = duplicate_of

    by_extraction: dict[str, dict[str, Any]] = {}
    for extraction in extractions:
        _require_keys(extraction, EXTRACTION_FIELDS, "extraction")
        eid = _nonempty(extraction["id"], "extraction.id")
        if eid in nodes:
            raise ValueError(f"duplicate node id: {eid}")
        nodes[eid] = "extraction"
        by_extraction[eid] = extraction
        _nonempty(extraction["analyst_id"], "analyst_id")
        _enum(extraction["analysis_origin"], ANALYSIS_ORIGINS, "analysis_origin")
        extraction["source_ids"] = _id_list(extraction["source_ids"], f"{eid}.source_ids")

    by_event: dict[str, dict[str, Any]] = {}
    for event in events:
        _require_keys(event, EVENT_FIELDS, "observed_event")
        evid = _nonempty(event["id"], "observed_event.id")
        if evid in nodes:
            raise ValueError(f"duplicate node id: {evid}")
        nodes[evid] = "observed_event"
        by_event[evid] = event
        _enum(event["event_kind"], EVENT_KINDS, "event_kind")
        _enum(event["polarity"], POLARITIES, "polarity")
        _enum(event["actor_binding"], ACTOR_BINDINGS, "actor_binding")
        _enum(event["authenticity"], AUTHENTICITY_VALUES, "authenticity")
        _enum(event["time_basis"], TIME_BASES, "time_basis")
        _enum(event["verification_method"], VERIFICATION_METHODS, "verification_method")
        _nonempty(event["statement"], f"{evid}.statement")
        _optional_str(event["actor_ref"], f"{evid}.actor_ref")
        event_time = _optional_str(event["event_time"], f"{evid}.event_time")
        observed_time = _optional_str(event["observed_time"], f"{evid}.observed_time")
        if event["time_basis"] in {"missing", "unknown"} and (
            event_time is not None or observed_time is not None
        ):
            raise ValueError(f"fabricated chronology: {evid}")
        if event["time_basis"] in {"source_stated", "reconstructed"} and event_time is None:
            raise ValueError(f"{evid}: {event['time_basis']} requires event_time")
        event["extraction_ids"] = _id_list(event["extraction_ids"], f"{evid}.extraction_ids")
        event["necessary_source_ids"] = _id_list(
            event["necessary_source_ids"], f"{evid}.necessary_source_ids"
        )
        event["conflicts_with"] = _id_list(event["conflicts_with"], f"{evid}.conflicts_with")
        _validate_event_lineage(event)

    by_claim: dict[str, dict[str, Any]] = {}
    for claim in claims:
        _require_keys(claim, CLAIM_FIELDS, "claim")
        cid = _nonempty(claim["id"], "claim.id")
        if cid in nodes:
            raise ValueError(f"duplicate node id: {cid}")
        nodes[cid] = "claim"
        by_claim[cid] = claim
        _nonempty(claim["proposition"], f"{cid}.proposition")
        if not isinstance(claim["world_claim"], bool):
            raise ValueError(f"{cid}.world_claim must be boolean")
        if not isinstance(claim["requires_bound_actor"], bool):
            raise ValueError(f"{cid}.requires_bound_actor must be boolean")
        if not isinstance(claim["requires_event_time"], bool):
            raise ValueError(f"{cid}.requires_event_time must be boolean")
        minimum = claim["minimum_independent_groups"]
        if not isinstance(minimum, int) or minimum < 1:
            raise ValueError(f"{cid}.minimum_independent_groups must be >= 1")
        required = _id_list(claim["required_event_kinds"], f"{cid}.required_event_kinds")
        insufficient = _id_list(
            claim["insufficient_event_kinds"], f"{cid}.insufficient_event_kinds"
        )
        for kind in required + insufficient:
            _enum(kind, EVENT_KINDS, "event_kind")
        if set(required) & set(insufficient):
            raise ValueError(f"{cid}: event kind cannot be both required and insufficient")
        claim["event_ids"] = _id_list(claim["event_ids"], f"{cid}.event_ids")
        if not isinstance(claim["evidence_slots"], list):
            raise ValueError(f"{cid}.evidence_slots must be a list")
        slot_ids: set[str] = set()
        for slot in claim["evidence_slots"]:
            _require_keys(slot, SLOT_FIELDS, "evidence_slot")
            slot_id = _nonempty(slot["id"], "evidence_slot.id")
            if slot_id in slot_ids:
                raise ValueError(f"duplicate node id: {slot_id}")
            slot_ids.add(slot_id)
            _nonempty(slot["source_id"], f"{slot_id}.source_id")
            _nonempty(slot["role"], f"{slot_id}.role")
            if not isinstance(slot["blocks_upgrade"], bool):
                raise ValueError(f"{slot_id}.blocks_upgrade must be boolean")
        _validate_coverage_assumption(claim.get("coverage_assumption"), cid)
        if claim.get("subject") is not None:
            _nonempty(claim["subject"], f"{cid}.subject")
        if claim.get("absence_policy") is not None:
            _enum(claim["absence_policy"], ABSENCE_POLICIES, "absence_policy")

    _check_references(by_source, by_extraction, by_event, by_claim)
    _check_independence_groups(by_source)
    _check_cycles(by_source, by_extraction, by_event, by_claim)


def _validate_retrieval(retrieval: Any, sid: str) -> None:
    if retrieval is None:
        return
    allowed = {"retrieved_at", "http_status", "body_sha256", "body_nbytes"}
    if not isinstance(retrieval, dict) or set(retrieval) != allowed:
        raise ValueError(f"{sid}.retrieval fields must be {sorted(allowed)}")
    _nonempty(retrieval["retrieved_at"], f"{sid}.retrieval.retrieved_at")
    status = retrieval["http_status"]
    if not isinstance(status, int):
        raise ValueError(f"{sid}.retrieval.http_status must be an integer")
    digest = retrieval["body_sha256"]
    nbytes = retrieval["body_nbytes"]
    if status == 200:
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"{sid}.retrieval.body_sha256 must be sha256 hex")
        if not isinstance(nbytes, int) or nbytes < 0:
            raise ValueError(f"{sid}.retrieval.body_nbytes must be a non-negative integer")
    else:
        if digest is not None or nbytes is not None:
            raise ValueError(f"{sid}: failed retrieval has no body pin")


def _validate_reported(source: dict[str, Any]) -> None:
    reported = source.get("reported_not_held")
    if reported is None:
        return
    if not isinstance(reported, dict):
        raise ValueError(f"{source['id']}.reported_not_held must be an object")
    if reported.get("held_by_audit") is True:
        raise ValueError(
            f"{source['id']}: reported counts are not held by this audit"
        )
    allowed = {
        "messages_and_files",
        "transcripts",
        "agents_on_board",
        "spoofed_transcripts",
        "precision",
        "held_by_audit",
    }
    unknown = set(reported) - allowed
    if unknown:
        raise ValueError(f"unknown reported_not_held field: {sorted(unknown)}")


def _check_references(
    sources: dict[str, dict[str, Any]],
    extractions: dict[str, dict[str, Any]],
    events: dict[str, dict[str, Any]],
    claims: dict[str, dict[str, Any]],
) -> None:
    def source_id(ref: str, where: str) -> None:
        if ref not in sources:
            raise ValueError(f"dangling reference: {where} -> {ref}")

    def extraction_id(ref: str, where: str) -> None:
        if ref not in extractions:
            raise ValueError(f"dangling reference: {where} -> {ref}")

    def event_id(ref: str, where: str) -> None:
        if ref not in events:
            raise ValueError(f"dangling reference: {where} -> {ref}")

    for source in sources.values():
        for dep in source["depends_on"]:
            source_id(dep, f"{source['id']}.depends_on")
        if source["duplicate_of"] is not None:
            source_id(source["duplicate_of"], f"{source['id']}.duplicate_of")
            if source["duplicate_of"] == source["id"]:
                raise ValueError(f"cycle: {source['id']} duplicates itself")
    for extraction in extractions.values():
        if not extraction["source_ids"]:
            raise ValueError(f"dangling reference: {extraction['id']} has no source")
        for sid in extraction["source_ids"]:
            source_id(sid, f"{extraction['id']}.source_ids")
    for event in events.values():
        if not event["extraction_ids"]:
            raise ValueError(f"dangling reference: {event['id']} has no extraction")
        for eid in event["extraction_ids"]:
            extraction_id(eid, f"{event['id']}.extraction_ids")
        for sid in event["necessary_source_ids"]:
            source_id(sid, f"{event['id']}.necessary_source_ids")
        for other in event["conflicts_with"]:
            event_id(other, f"{event['id']}.conflicts_with")
    for claim in claims.values():
        classified = set(claim["required_event_kinds"]) | set(claim["insufficient_event_kinds"])
        for evid in claim["event_ids"]:
            event_id(evid, f"{claim['id']}.event_ids")
            kind = events[evid]["event_kind"]
            if kind not in classified:
                raise ValueError(
                    f"{claim['id']}: event kind {kind!r} is not classified"
                )
        for slot in claim["evidence_slots"]:
            source_id(slot["source_id"], f"{slot['id']}.source_id")
            if not slot["blocks_upgrade"]:
                continue
            source = sources[slot["source_id"]]
            # A gate is legal only for bytes this audit holds. Unavailable
            # originals, unpinned narratives, duplicates, and broken custody
            # cannot prevent supported.
            if source_unavailable(source):
                raise ValueError(
                    f"{slot['id']}: unavailable source {slot['source_id']} "
                    "cannot be an upgrade gate"
                )
            if not record_integrity(source):
                raise ValueError(
                    f"{slot['id']}: blocks_upgrade on {slot['source_id']} "
                    "requires evidence this audit holds"
                )


def _check_independence_groups(sources: dict[str, dict[str, Any]]) -> None:
    for source in sources.values():
        for dep_id in source["depends_on"]:
            dep = sources[dep_id]
            if source["independence_group"] != dep["independence_group"]:
                raise ValueError(
                    "independence group mismatch: "
                    f"{source['id']} depends on {dep_id}"
                )
        if source["duplicate_of"] is not None:
            canon = sources[source["duplicate_of"]]
            if source["independence_group"] != canon["independence_group"]:
                raise ValueError(
                    "independence group mismatch: "
                    f"{source['id']} duplicates {source['duplicate_of']}"
                )


def _check_cycles(
    sources: dict[str, dict[str, Any]],
    extractions: dict[str, dict[str, Any]],
    events: dict[str, dict[str, Any]],
    claims: dict[str, dict[str, Any]],
) -> None:
    edges: set[tuple[str, str, str]] = set()

    def add(src: str, dst: str, relation: str) -> None:
        edge = (src, dst, relation)
        if edge in edges:
            raise ValueError(f"duplicate edge: {src} -{relation}-> {dst}")
        edges.add(edge)

    for source in sources.values():
        for dep in source["depends_on"]:
            add(dep, source["id"], "depends_on")
        if source["duplicate_of"] is not None:
            add(source["duplicate_of"], source["id"], "duplicate_of")
    for extraction in extractions.values():
        for sid in extraction["source_ids"]:
            add(sid, extraction["id"], "extracted_by")
    for event in events.values():
        for eid in event["extraction_ids"]:
            add(eid, event["id"], "yields")
    for claim in claims.values():
        for evid in claim["event_ids"]:
            add(evid, claim["id"], "offered_to")

    adjacent: dict[str, list[str]] = {}
    for src, dst, _relation in edges:
        adjacent.setdefault(src, []).append(dst)
        adjacent.setdefault(dst, [])
    color: dict[str, int] = {}

    def visit(node: str) -> None:
        color[node] = 1
        for nxt in adjacent.get(node, []):
            state = color.get(nxt, 0)
            if state == 1:
                raise ValueError(f"cycle: {node} -> {nxt}")
            if state == 0:
                visit(nxt)
        color[node] = 2

    for node in list(adjacent):
        if color.get(node, 0) == 0:
            visit(node)


def record_integrity(source: dict[str, Any]) -> bool:
    """True only for pinned excerpt bytes, not for upstream authenticity."""
    if source.get("duplicate_of"):
        return False
    if source.get("access_level") != "public_bytes":
        return False
    if source.get("redaction") != "none":
        return False
    if source.get("custody") != "intact":
        return False
    if source.get("locally_held") is not True:
        return False
    public = source.get("public_bytes")
    if not isinstance(public, str) or public == "":
        return False
    return source.get("content_digest") == content_sha256(public)


def event_verified(event: dict[str, Any], sources: dict[str, dict[str, Any]]) -> bool:
    """Verification is a method outcome. Asserted authenticity does not count."""
    if event["authenticity"] in {"forged", "disputed"}:
        return False
    method = event["verification_method"]
    if method in {"none", "unknown", "self_report"}:
        return False
    necessary = event["necessary_source_ids"]
    if not necessary or any(not record_integrity(sources[sid]) for sid in necessary):
        return False
    if method == "excerpt_sha256":
        return event["event_kind"] == "narrative_report"
    if method == "independent_log_digest":
        if event["event_kind"] not in {"independent_service_log", "committed_effect"}:
            return False
        origins = {sources[sid]["observation_origin"] for sid in necessary}
        return origins <= LOG_ORIGINS
    return False


def rejection_reason(event: dict[str, Any], sources: dict[str, dict[str, Any]]) -> str:
    if event["authenticity"] == "forged":
        return "forged representation cannot establish the event"
    if event["authenticity"] == "disputed":
        return "altered record is not verification of the event"
    method = event["verification_method"]
    if method == "self_report":
        return "self-reported authenticity is not verification"
    if method in {"none", "unknown"}:
        return "verification method does not establish the event"
    necessary = event["necessary_source_ids"]
    if not necessary or any(not record_integrity(sources[sid]) for sid in necessary):
        return "necessary source is not public bytes held by this audit"
    if method == "excerpt_sha256" and event["event_kind"] != "narrative_report":
        return "excerpt digest verifies publication bytes, not this event kind"
    if method == "independent_log_digest" and event["event_kind"] not in {
        "independent_service_log",
        "committed_effect",
    }:
        return "independent log digest does not establish this event kind"
    return "event is not verified"


def _groups_for(
    event_list: list[dict[str, Any]], sources: dict[str, dict[str, Any]]
) -> list[str]:
    groups: set[str] = set()
    for event in event_list:
        for sid in event["necessary_source_ids"]:
            source = sources[sid]
            if source.get("duplicate_of"):
                continue
            groups.add(source["independence_group"])
    return sorted(groups)


def source_unavailable(source: dict[str, Any]) -> bool:
    """True when the record is not in hand. Unavailability is not a gate."""
    if source.get("access_level") in {"withheld", "private_original", "unobserved", "unknown"}:
        return True
    if source.get("locally_held") is True:
        return False
    if source.get("access_level") == "redacted":
        return True
    return source.get("redaction") == "withheld_original"


def default_evidence_type(origin: str) -> str:
    """Map an origin to a type. The three named types are never rewritten onto each other."""
    if origin in {"reused_transcript_dump", "correlated_analysis_of_single_dataset"}:
        return "public_report_assertion"
    if origin == "synthetic_control":
        return "synthetic_model_record"
    if origin == "independent_provider_telemetry":
        return "provider_telemetry"
    if origin == "released_reproduction":
        return "released_reproduction"
    if origin == "unavailable_private_original":
        return "unavailable_original"
    return "unknown"


def _lineage_root(
    source: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    seen: set[str] | None = None,
) -> dict[str, Any]:
    seen = set() if seen is None else seen
    if source["id"] in seen:
        return source
    seen.add(source["id"])
    if source.get("duplicate_of"):
        return _lineage_root(sources[source["duplicate_of"]], sources, seen)
    deps = source.get("depends_on") or []
    if deps:
        roots = [_lineage_root(sources[dep], sources, seen) for dep in deps]
        root_ids = {item["id"] for item in roots}
        if len(root_ids) == 1:
            return roots[0]
    return source


def _legacy_corroboration_key(
    source: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    seen: set[str] | None = None,
) -> str:
    """Previous per-record key. Used only to keep an already-unified label stable."""
    seen = set() if seen is None else seen
    if source["id"] in seen:
        return "group:" + source["independence_group"]
    seen = set(seen)
    seen.add(source["id"])
    if source.get("duplicate_of"):
        return _legacy_corroboration_key(sources[source["duplicate_of"]], sources, seen)
    deps = source.get("depends_on") or []
    if deps:
        root_keys = {
            _legacy_corroboration_key(sources[dep], sources, seen) for dep in deps
        }
        if len(root_keys) == 1:
            return next(iter(root_keys))
    digest = source.get("content_digest")
    if isinstance(digest, str) and digest:
        return "digest:" + digest
    return "group:" + _lineage_root(source, sources)["independence_group"]


def _origin_keys(sources: dict[str, dict[str, Any]]) -> dict[str, str]:
    """One key per shared origin.

    Duplicate bytes and explicit dependency or duplicate edges collapse.
    A different digest does not split an independence group. A component the
    old digest key already unified keeps that label.
    """
    parent = {sid: sid for sid in sources}

    def find(sid: str) -> str:
        while parent[sid] != sid:
            parent[sid] = parent[parent[sid]]
            sid = parent[sid]
        return sid

    def union(left: str, right: str) -> None:
        root_left, root_right = find(left), find(right)
        if root_left == root_right:
            return
        if root_right < root_left:
            root_left, root_right = root_right, root_left
        parent[root_right] = root_left

    for source in sources.values():
        if source.get("duplicate_of"):
            union(source["id"], source["duplicate_of"])
        for dep in source.get("depends_on") or []:
            union(source["id"], dep)
    grouped: dict[str, list[str]] = {}
    for source in sources.values():
        grouped.setdefault(source["independence_group"], []).append(source["id"])
    for ids in grouped.values():
        head = ids[0]
        for other in ids[1:]:
            union(head, other)
    digested: dict[str, list[str]] = {}
    for source in sources.values():
        digest = source.get("content_digest")
        if isinstance(digest, str) and digest:
            digested.setdefault(digest, []).append(source["id"])
    for ids in digested.values():
        head = ids[0]
        for other in ids[1:]:
            union(head, other)
    legacy = {sid: _legacy_corroboration_key(sources[sid], sources) for sid in sources}
    members: dict[str, list[str]] = {}
    for sid in sources:
        members.setdefault(find(sid), []).append(sid)
    resolved: dict[str, str] = {}
    for group in members.values():
        old = {legacy[sid] for sid in group}
        if len(old) == 1:
            label = next(iter(old))
        else:
            groups = {sources[sid]["independence_group"] for sid in group}
            label = (
                "group:" + next(iter(groups))
                if len(groups) == 1
                else "origin:" + min(group)
            )
        for sid in group:
            resolved[sid] = label
    return resolved


def _corroboration_key(
    source: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    seen: set[str] | None = None,
) -> str:
    """One key per shared origin. A second report of that record does not mint a key."""
    del seen
    return _origin_keys(sources)[source["id"]]


def _corroboration_keys(
    events: list[dict[str, Any]], sources: dict[str, dict[str, Any]]
) -> list[str]:
    seen: set[str] = set()
    keys: list[str] = []
    for event in events:
        if not event["necessary_source_ids"]:
            continue
        key = _corroboration_key(sources[event["necessary_source_ids"][0]], sources)
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def _interval(value: Any, field: str) -> dict[str, str | None] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"start", "end"}:
        raise ValueError(f"{field} must be {{start, end}} or null")
    start, end = value["start"], value["end"]
    for item, name in ((start, "start"), (end, "end")):
        if item is not None and (not isinstance(item, str) or item.strip() == ""):
            raise ValueError(f"invalid {field}.{name}")
    if isinstance(start, str) and isinstance(end, str) and end <= start:
        raise ValueError(f"invalid {field}")
    return {"start": start, "end": end}


def _validate_event_lineage(event: dict[str, Any]) -> None:
    evid = event["id"]
    for field in ("producer", "subject", "actor_scope", "task_scope"):
        if field in event and event[field] is not None:
            _nonempty(event[field], f"{evid}.{field}")
    if event.get("evidence_type") is not None:
        _enum(event["evidence_type"], EVIDENCE_TYPES, "evidence_type")
    if event.get("temporal_applicability") is not None:
        _enum(event["temporal_applicability"], TEMPORAL_APPLICABILITY, "temporal_applicability")
    if event.get("scope_binding") is not None:
        _enum(event["scope_binding"], SCOPE_BINDINGS, "scope_binding")
    if event.get("observation_availability") is not None:
        _enum(
            event["observation_availability"],
            frozenset({"available", "withheld", "redacted", "unobserved", "unknown"}),
            "observation_availability",
        )
    if "coverage_interval" in event:
        _interval(event["coverage_interval"], f"{evid}.coverage_interval")


def _validate_coverage_assumption(value: Any, cid: str) -> None:
    if value is None:
        return
    allowed = {"operation", "interval", "completeness"}
    if not isinstance(value, dict) or set(value) != allowed:
        raise ValueError(f"{cid}.coverage_assumption fields must be {sorted(allowed)}")
    if value["operation"] is not None:
        _nonempty(value["operation"], f"{cid}.coverage_assumption.operation")
    _enum(value["completeness"], COMPLETENESS_VALUES, "completeness")
    _interval(value["interval"], f"{cid}.coverage_assumption.interval")
    if value["completeness"] == "complete":
        interval = value["interval"]
        if (
            not isinstance(interval, dict)
            or not interval.get("start")
            or not interval.get("end")
            or not value["operation"]
        ):
            raise ValueError(
                f"{cid}: complete coverage requires an operation and a closed interval"
            )


def _coverage_assumption(claim: dict[str, Any]) -> dict[str, Any]:
    raw = claim.get("coverage_assumption")
    if not raw:
        return {
            "declared": False,
            "operation": None,
            "interval": {"start": None, "end": None},
            "completeness": "not_declared",
        }
    interval = raw["interval"] or {"start": None, "end": None}
    return {
        "declared": True,
        "operation": raw["operation"],
        "interval": {"start": interval.get("start"), "end": interval.get("end")},
        "completeness": raw["completeness"],
    }


def _time_outside(event_time: str | None, interval: dict[str, Any]) -> bool:
    start, end = interval.get("start"), interval.get("end")
    if not event_time or not start or not end:
        return False
    return event_time < start or event_time >= end


def _exclusion(
    event: dict[str, Any], claim: dict[str, Any], assumption: dict[str, Any]
) -> str | None:
    if event.get("temporal_applicability") == "stale" or _time_outside(
        event.get("event_time"), assumption["interval"]
    ):
        return "stale_record"
    if event.get("scope_binding") == "misbound":
        return "misbound_record"
    claim_subject = claim.get("subject")
    event_subject = event.get("subject")
    if (
        isinstance(claim_subject, str)
        and isinstance(event_subject, str)
        and event_subject not in {"unknown", claim_subject}
    ):
        return "misbound_record"
    return None


def _evidence_type_for(
    event: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> str:
    if event.get("evidence_type"):
        return event["evidence_type"]
    if event["necessary_source_ids"]:
        source = sources[event["necessary_source_ids"][0]]
        if source.get("evidence_type"):
            return source["evidence_type"]
        return default_evidence_type(source["observation_origin"])
    return "unknown"


def bind_observation(
    event: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    extractions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Lineage record the qualifier consumes. Unknown stays unknown.

    A content digest identifies pinned bytes. It does not certify the assertion.
    """
    necessary = [sources[sid] for sid in event["necessary_source_ids"]]
    primary = necessary[0] if necessary else None
    used = [extractions[eid] for eid in event["extraction_ids"] if eid in extractions]
    producer = event.get("producer")
    if producer in (None, "", "unknown") and used:
        producer = used[0]["analyst_id"]
    if not producer:
        producer = "unknown"
    evidence_type = _evidence_type_for(event, sources)
    origin = primary["observation_origin"] if primary else "unknown"
    digest = primary.get("content_digest") if primary else None
    source_ref = "unknown"
    if primary is not None:
        source_ref = primary.get("canonical_url") or primary["id"]
    availability = event.get("observation_availability")
    if availability is None and primary is not None:
        availability = "unobserved" if source_unavailable(primary) else slot_coverage(primary)
    if availability is None:
        availability = "unknown"
    interval = event.get("coverage_interval") or {"start": None, "end": None}
    temporal = event.get("temporal_applicability")
    if temporal is None:
        if event["time_basis"] in {"missing", "unknown"}:
            temporal = "missing" if event["time_basis"] == "missing" else "unknown"
        elif event["time_basis"] == "source_stated" and event.get("event_time"):
            temporal = "applies"
        else:
            temporal = "unknown"
    scope = event.get("scope_binding")
    if scope is None:
        if event["actor_binding"] in {"unverified_binding", "conflicting"}:
            scope = event["actor_binding"]
        elif event["actor_binding"] == "bound":
            scope = "bound"
        else:
            scope = "unknown"
    return {
        "event_id": event["id"],
        "producer": producer,
        "analyst_origin": used[0]["analysis_origin"] if used else "unknown",
        "observation_origin": origin,
        "evidence_type": evidence_type,
        "collection_boundary": primary["collection_boundary"] if primary else "unknown",
        "source_ref": source_ref,
        "content_digest": digest,
        "byte_identity": bool(digest),
        "digest_certifies_assertion": False,
        "subject": event.get("subject") or "unknown",
        "actor_scope": event.get("actor_scope") or "unknown",
        "task_scope": event.get("task_scope") or "unknown",
        "event_time": event.get("event_time"),
        "observation_availability": availability,
        "coverage_interval": {
            "start": interval.get("start"),
            "end": interval.get("end"),
        },
        "authenticity": event["authenticity"],
        "temporal_applicability": temporal,
        "scope_binding": scope,
        "corroboration_key": (
            _corroboration_key(primary, sources) if primary is not None else "unknown"
        ),
        "independence_group": primary["independence_group"] if primary else "unknown",
    }


def normalize_lineage(graph: dict[str, Any]) -> dict[str, Any]:
    """Validate the graph and bind every observation. Qualification reads this."""
    validate_graph(graph)
    sources = {node["id"]: node for node in graph["source_records"]}
    extractions = {node["id"]: node for node in graph["extractions"]}
    observations = [
        bind_observation(event, sources, extractions) for event in graph["observed_events"]
    ]
    counts = {kind: 0 for kind in DISTINCT_EVIDENCE_TYPES}
    for item in observations:
        if item["evidence_type"] in counts:
            counts[item["evidence_type"]] += 1
        else:
            counts.setdefault(item["evidence_type"], 0)
            counts[item["evidence_type"]] += 1
    return {
        "contract_version": CONTRACT_VERSION,
        "graph_id": graph["id"],
        "observations": observations,
        "evidence_type_counts": counts,
        "claims": {
            claim["id"]: {"coverage_assumption": _coverage_assumption(claim)}
            for claim in graph["claims"]
        },
    }


def slot_coverage(source: dict[str, Any]) -> str:
    """One of available, withheld, redacted, unobserved."""
    access = source["access_level"]
    redaction = source["redaction"]
    if access in {"withheld", "private_original"}:
        return "withheld"
    if access == "redacted" or (
        access in {"public_bytes", "public_narrative"}
        and redaction in {"partial", "withheld_original"}
    ):
        return "redacted"
    if access in {"unobserved", "unknown"} or redaction == "unknown":
        return "unobserved"
    if access in {"public_bytes", "public_narrative"} and redaction == "none":
        return "available"
    return "unobserved"


def _blocker_reason(status: str, source: dict[str, Any]) -> str:
    if status == "withheld":
        return f"withheld source {source['id']} is not held by this audit"
    if status == "redacted":
        return f"redacted source {source['id']} cannot upgrade the claim"
    if status == "unobserved":
        return f"unobserved source {source['id']} prevents an upgrade"
    return (
        f"available source {source['id']} does not verify the required event kind"
    )


def _type_counts(lineage: list[dict[str, Any]]) -> dict[str, int]:
    counts = {kind: 0 for kind in DISTINCT_EVIDENCE_TYPES}
    for item in lineage:
        kind = item["evidence_type"]
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _dimensions(
    lineage: list[dict[str, Any]],
    assumption: dict[str, Any],
    unverified_binding: bool,
) -> dict[str, str]:
    """Authenticity, time, scope, and completeness stay separate fields."""
    if any(item["authenticity"] == "forged" for item in lineage):
        authenticity = "forged"
    elif any(item["authenticity"] == "disputed" for item in lineage):
        authenticity = "disputed"
    elif any(item["byte_identity"] for item in lineage):
        authenticity = "byte_identified"
    else:
        authenticity = "unknown"
    if any(item["temporal_applicability"] == "stale" for item in lineage):
        temporal = "stale"
    elif any(item["temporal_applicability"] == "applies" for item in lineage):
        temporal = "applies"
    elif any(item["temporal_applicability"] == "missing" for item in lineage):
        temporal = "missing"
    else:
        temporal = "unknown"
    if any(item["scope_binding"] == "misbound" for item in lineage):
        scope = "misbound"
    elif unverified_binding:
        scope = "unverified_binding"
    elif any(item["scope_binding"] == "bound" for item in lineage):
        scope = "bound"
    else:
        scope = "unknown"
    return {
        "authenticity": authenticity,
        "temporal_applicability": temporal,
        "scope_binding": scope,
        "collection_completeness": assumption["completeness"],
    }


def qualify_claim(
    graph: dict[str, Any], claim_id: str
) -> dict[str, Any]:
    """Derive one claim verdict from normalized lineage. Does not read a confidence score.

    A ``blocks_upgrade`` slot prevents ``supported`` only for evidence this
    audit holds (``record_integrity``). Validation rejects the flag otherwise.
    On held evidence the slot stays until a verified supporting event uses
    that source. An unavailable original is recorded and is not a gate. A
    second report of the same record does not add an independent observation.
    Absence of a sink row is evidence of no effect only when a declared
    coverage assumption is complete for that operation and interval.
    """
    validate_graph(graph)
    sources = {node["id"]: node for node in graph["source_records"]}
    extractions = {node["id"]: node for node in graph["extractions"]}
    events = {node["id"]: node for node in graph["observed_events"]}
    claims = {node["id"]: node for node in graph["claims"]}
    if claim_id not in claims:
        raise KeyError(claim_id)
    claim = claims[claim_id]
    offered = [events[eid] for eid in claim["event_ids"]]
    required = set(claim["required_event_kinds"])
    assumption = _coverage_assumption(claim)
    lineage = [bind_observation(event, sources, extractions) for event in offered]
    lineage_by_id = {item["event_id"]: item for item in lineage}

    verified = [event for event in offered if event_verified(event, sources)]
    exclusions: dict[str, str] = {}
    admissible: list[dict[str, Any]] = []
    for event in verified:
        if event["event_kind"] not in required:
            continue
        why = _exclusion(event, claim, assumption)
        if why:
            exclusions[event["id"]] = why
            continue
        admissible.append(event)
    verified_support = [event for event in admissible if event["polarity"] == "supports"]
    verified_contra = [event for event in admissible if event["polarity"] == "contradicts"]
    support_keys = _corroboration_keys(verified_support, sources)
    seen_keys: set[str] = set()
    duplicated_report_ids: list[str] = []
    for event in offered:
        key = lineage_by_id[event["id"]]["corroboration_key"]
        if key in seen_keys:
            duplicated_report_ids.append(event["id"])
        else:
            seen_keys.add(key)
    narrative_groups = _groups_for(
        [event for event in verified if event["event_kind"] == "narrative_report"],
        sources,
    )
    cited_groups = _groups_for(offered, sources)
    analysts = sorted(
        {
            extractions[eid]["analyst_id"]
            for event in offered
            for eid in event["extraction_ids"]
        }
    )
    surfaces = sorted(
        {
            sid
            for event in offered
            for sid in event["necessary_source_ids"]
            if record_integrity(sources[sid])
        }
    )
    conflict_ids = {
        other
        for event in offered
        for other in event["conflicts_with"]
        if other in claim["event_ids"]
    }
    polarity_conflict = any(event["polarity"] == "supports" for event in offered) and any(
        event["polarity"] == "contradicts" for event in offered
    )
    source_conflict = bool(conflict_ids or polarity_conflict or (verified_support and verified_contra))
    unverified_binding = any(
        event["actor_binding"] in {"unverified_binding", "conflicting"} for event in offered
    ) or any(why == "misbound_record" for why in exclusions.values())

    def _bound(selected: list[dict[str, Any]]) -> bool:
        return bool(selected) and all(
            event["actor_binding"] == "bound" for event in selected
        )

    def _stated_time(event: dict[str, Any]) -> bool:
        return event["time_basis"] == "source_stated" and bool(event["event_time"])

    actor_ok = not claim["requires_bound_actor"] or _bound(verified_support)
    contra_actor_ok = not claim["requires_bound_actor"] or _bound(verified_contra)
    time_ok = not claim["requires_event_time"] or (
        bool(verified_support) and all(_stated_time(event) for event in verified_support)
    )
    contra_time_ok = not claim["requires_event_time"] or (
        bool(verified_contra) and all(_stated_time(event) for event in verified_contra)
    )
    enough_groups = len(support_keys) >= claim["minimum_independent_groups"]

    coverage_counts = {"available": 0, "withheld": 0, "redacted": 0, "unobserved": 0}
    blockers: list[dict[str, str]] = []
    unavailable: list[dict[str, Any]] = []
    verified_necessary = {
        sid
        for event in verified_support
        for sid in event["necessary_source_ids"]
        if record_integrity(sources[sid])
    }
    for slot in claim["evidence_slots"]:
        source = sources[slot["source_id"]]
        status = slot_coverage(source)
        coverage_counts[status] += 1
        if source_unavailable(source):
            unavailable.append(
                {
                    "slot_id": slot["id"],
                    "source_id": slot["source_id"],
                    "access_level": source["access_level"],
                    "independence_group": source["independence_group"],
                    "coverage_status": status,
                    "reason": "recorded unavailable; not an upgrade gate",
                }
            )
        verifies_claim = slot["source_id"] in verified_necessary
        # Validation rejects this flag unless record_integrity holds.
        # A remaining gate on held evidence still prevents supported.
        if slot["blocks_upgrade"] and not verifies_claim:
            blockers.append(
                {
                    "slot_id": slot["id"],
                    "source_id": slot["source_id"],
                    "coverage_status": status,
                    "reason": _blocker_reason(status, source),
                }
            )
    denominator = sum(coverage_counts.values())
    if denominator != len(claim["evidence_slots"]):
        raise RuntimeError("coverage statuses do not partition evidence slots")
    upgrade_blocked = bool(blockers)

    missing_requirements: list[dict[str, Any]] = []
    invalid_requirements: list[dict[str, Any]] = []
    if unavailable and not assumption["declared"]:
        missing_requirements.append(
            {
                "requirement": "coverage_assumption",
                "status": "missing",
                "operation": None,
                "interval": {"start": None, "end": None},
                "source_ids": [item["source_id"] for item in unavailable],
                "reason": (
                    "missing records require an explicit coverage assumption; "
                    "absence is not evidence of no effect"
                ),
            }
        )
    if assumption["declared"] and assumption["completeness"] == "complete" and unavailable:
        invalid_requirements.append(
            {
                "requirement": "coverage_assumption",
                "status": "invalid",
                "operation": assumption["operation"],
                "interval": assumption["interval"],
                "source_ids": [item["source_id"] for item in unavailable],
                "reason": (
                    "complete coverage is not established while an original "
                    "remains unavailable"
                ),
            }
        )
    for event_id, why in exclusions.items():
        invalid_requirements.append(
            {
                "requirement": why,
                "status": "invalid",
                "event_id": event_id,
                "reason": why.replace("_", " "),
            }
        )
    for event in offered:
        if event["authenticity"] == "disputed":
            invalid_requirements.append(
                {
                    "requirement": "altered_record",
                    "status": "invalid",
                    "event_id": event["id"],
                    "reason": "altered record is not verification of the event",
                }
            )
    held_collection = any(
        record_integrity(sources[slot["source_id"]]) for slot in claim["evidence_slots"]
    )
    coverage_established = (
        assumption["declared"]
        and assumption["completeness"] == "complete"
        and not unavailable
        and held_collection
        and not any(
            item["requirement"] == "coverage_assumption" for item in invalid_requirements
        )
    )
    absence_is_no_effect = (
        coverage_established
        and not verified_support
        and not verified_contra
        and not upgrade_blocked
        and (
            "committed_effect" in required
            or claim.get("absence_policy") == "no_effect_if_covered"
        )
    )

    if verified_support and verified_contra:
        evidence_complete = False
        property_holds = None
    elif verified_contra and not verified_support and contra_actor_ok and contra_time_ok:
        evidence_complete = True
        property_holds = False
    elif absence_is_no_effect:
        evidence_complete = True
        property_holds = False
    elif (
        verified_support
        and enough_groups
        and actor_ok
        and time_ok
        and not source_conflict
        and not upgrade_blocked
    ):
        evidence_complete = True
        property_holds = True
    else:
        evidence_complete = False
        property_holds = None

    # Covered absence refutes effect-existence; it is not an enforcement failure
    # unless a mechanism was separately shown to have been exercised wrongly.
    classified = classify_conclusion(
        evidence_complete=evidence_complete,
        property_holds=property_holds,
        mechanism_exercised=bool(property_holds is False and not absence_is_no_effect),
    )

    if any(event["authenticity"] == "forged" for event in offered):
        evidence_status: EvidenceStatus = "misbound"
    elif evidence_complete:
        evidence_status = "authentic"
    elif surfaces:
        evidence_status = "unverified"
    else:
        evidence_status = "missing"

    if evidence_complete and property_holds is True:
        effect_status: EffectStatus = (
            "committed"
            if any(event["event_kind"] == "committed_effect" for event in verified_support)
            else "unobserved"
        )
        failure_origin: FailureOrigin = "none"
    elif evidence_complete and property_holds is False:
        effect_status = "unobserved"
        failure_origin = "evidence"
    elif evidence_status in {"misbound", "unverified", "missing"} and (
        offered or claim["evidence_slots"]
    ):
        effect_status = "unobserved"
        failure_origin = "evidence"
    else:
        effect_status = "unobserved"
        failure_origin = "undetermined"
    decision_status: DecisionStatus = "unknown"

    established_time = None
    established_observed = None
    established_basis = "missing"
    if evidence_complete and property_holds is True and claim["requires_event_time"]:
        established_time = verified_support[0]["event_time"]
        established_observed = verified_support[0]["observed_time"]
        established_basis = "source_stated"
    rejected_times = []
    for event in offered:
        if event["event_kind"] not in required:
            if event["event_time"] is not None:
                rejected_times.append(
                    {
                        "event_id": event["id"],
                        "event_time": event["event_time"],
                        "time_basis": event["time_basis"],
                        "reason": "narrative or insufficient-kind time is not the claim chronology",
                    }
                )
            continue
        if event["time_basis"] == "reconstructed" and event["event_time"] is not None:
            rejected_times.append(
                {
                    "event_id": event["id"],
                    "event_time": event["event_time"],
                    "time_basis": "reconstructed",
                    "reason": "reconstructed timestamp is not an event chronology",
                }
            )
        elif event["time_basis"] in {"missing", "unknown"}:
            rejected_times.append(
                {
                    "event_id": event["id"],
                    "event_time": None,
                    "time_basis": event["time_basis"],
                    "reason": "missing timestamp is not a chronology",
                }
            )

    reported = _reported_counts(claim, sources)
    kinds_present = sorted({event["event_kind"] for event in offered})
    rejections = [
        {
            "event_id": event["id"],
            "event_kind": event["event_kind"],
            "reason": rejection_reason(event, sources),
        }
        for event in offered
        if not event_verified(event, sources)
    ]
    blocker_text = (
        blockers[0]["reason"]
        if blockers
        else "no admissible verified observation"
    )
    if evidence_complete and property_holds is True:
        reason = (
            "fixture rule satisfied by verified admissible observations; "
            "this does not certify real-world authenticity"
        )
    elif evidence_complete and property_holds is False and absence_is_no_effect:
        reason = (
            "coverage for the stated operation and interval is established "
            "and the sink has no effect row; this does not certify a real-world event"
        )
    elif evidence_complete and property_holds is False:
        reason = "verified admissible observation contradicts the claim"
    elif missing_requirements:
        reason = "missing_evidence: " + missing_requirements[0]["reason"]
    elif invalid_requirements:
        reason = "missing_evidence: " + invalid_requirements[0]["reason"]
    else:
        reason = f"missing_evidence: {blocker_text}"

    qualified = {
        "claim_id": claim_id,
        "proposition": claim["proposition"],
        "conclusion_class": classified["conclusion_class"],
        "finding_label": classified["finding_label"],
        "property_holds": classified["property_holds"],
        "reason": reason,
        "evidence_status": evidence_status,
        "decision_status": decision_status,
        "effect_status": effect_status,
        "failure_origin": failure_origin,
        "source_conflict": source_conflict,
        "unverified_binding": unverified_binding,
        "independent_observation_count": len(support_keys),
        "duplicated_report_ids": duplicated_report_ids,
        "verified_narrative_group_count": len(narrative_groups),
        "investigator_count": len(analysts),
        "investigators": analysts,
        "publication_surface_count": len(surfaces),
        "cited_independence_groups": cited_groups,
        "verified_event_ids": [event["id"] for event in verified],
        "kinds_present": kinds_present,
        "kind_rejections": rejections,
        "chronology": {
            "event_time": established_time,
            "observed_time": established_observed,
            "time_basis": established_basis,
            "fabricated": False,
        },
        "rejected_times": rejected_times,
        "coverage": {**coverage_counts, "denominator": denominator},
        "coverage_assumption": assumption,
        "coverage_established": coverage_established,
        "absence_of_sink_is_no_effect": absence_is_no_effect,
        "unavailable_sources": unavailable,
        "missing_requirements": missing_requirements,
        "invalid_requirements": invalid_requirements,
        "lineage": lineage,
        "evidence_type_counts": _type_counts(lineage),
        "dimensions": _dimensions(lineage, assumption, unverified_binding),
        "upgrade_blocked_by": blockers,
        "primary_upgrade_blocker": blockers[0]["source_id"] if blockers else None,
        "reported_counts": reported,
        "real_world_authenticity_certified": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "diagnosis": diagnosis(
            evidence_status=evidence_status,
            decision_status=decision_status,
            effect_status=effect_status,
            failure_origin=failure_origin,
        ),
    }
    return qualified


def _reported_counts(
    claim: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    merged: dict[str, Any] | None = None
    for slot in claim["evidence_slots"]:
        reported = sources[slot["source_id"]].get("reported_not_held")
        if not reported:
            continue
        merged = dict(reported)
        merged["held_by_audit"] = False
    return merged


def qualify_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Qualify every claim. Real-world certification stays false."""
    validate_graph(graph)
    claims = {
        claim["id"]: qualify_claim(graph, claim["id"]) for claim in graph["claims"]
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "graph_id": graph["id"],
        "real_world_authenticity_certified": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "claims": claims,
    }
