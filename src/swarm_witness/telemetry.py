"""Forensic telemetry ingestion (forensic-telemetry-v1).

Normative statement: ``protocol/forensic_telemetry_v1.md``.

Adapters normalize offline agent/tool records, independent service or effect
logs, and pinned public excerpts into records this audit can pin. Verdicts
are ``qualify_graph`` / ``qualify_claim`` from evidence-provenance-v1. This
module does not reimplement that rule. The LessWrong reproduction post and
its appendix are one public record. The original transcript dump and the
Hugging Face platform logs stay unavailable and are not upgrade gates.
``validate_graph`` rejects ``blocks_upgrade`` on a source this audit does
not hold. A ``blocks_upgrade`` slot on a held source still prevents
``supported`` until a verified supporting event uses that source.

Missing logs are not given rows or effect times. A missing actor, call,
scope, or timestamp stays missing: the adapter does not mint an identity or
a chronology. A tool-call row never becomes a committed effect, and a
matching credential never confirms one. Synthetic rows stay labeled
``synthetic_control``. Nothing here certifies a real-world event or claims
that Swarm Witness detected or prevented the incident.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from swarm_witness.provenance import (
    CONTRACT_VERSION,
    EVENT_KINDS,
    LOG_ORIGINS,
    OBSERVATION_ORIGINS,
    content_sha256,
    make_event,
    make_extraction,
    make_source,
    qualify_claim,
    qualify_graph,
    validate_graph,
)

TELEMETRY_VERSION = "forensic-telemetry-v1"

AGENT_SURFACES = {
    "requested_command": "transcript_visible_command",
    "displayed_tool_call": "tool_call_arguments",
    "tool_response": "actual_tool_response",
}
SERVICE_SURFACES = {
    "api_event": "independent_service_log",
    "service_log": "independent_service_log",
    "committed_effect": "committed_effect",
}
EXCERPT_SURFACES = {
    "public_excerpt": "narrative_report",
    "message_board_excerpt": "message_board_record",
}
AGENT_KINDS = frozenset(AGENT_SURFACES.values())
EFFECT_KINDS = frozenset(SERVICE_SURFACES.values())
NARRATIVE_KINDS = frozenset(EXCERPT_SURFACES.values())
LINK_STATUSES = frozenset({"confirmed", "conflicting", "unlinked", "spoof_suspected"})
STATUS_RANK = {"confirmed": 0, "spoof_suspected": 1, "conflicting": 2, "unlinked": 3}

ROW_FIELDS = frozenset(
    {
        "record_id",
        "surface",
        "origin",
        "synthetic",
        "independence_group",
        "publisher",
        "raw",
        "public_bytes",
        "actor",
        "actor_binding",
        "binding_basis",
        "credential",
        "call_id",
        "object",
        "action",
        "result",
        "event_time",
        "ingest_time",
        "collection_boundary",
        "redaction",
        "parent_id",
        "parent_ids",
        "authenticity",
        "polarity",
        "access_level",
        "custody",
        "locally_held",
        "canonical_url",
        "time_basis",
        "source_id",
        "depends_on",
        "locator",
    }
)
EXCERPT_FIELDS = frozenset(
    {
        "record_id",
        "pinned_source_id",
        "surface",
        "polarity",
        "synthetic",
        "event_time",
        "time_basis",
        "ingest_time",
    }
)
NORMALIZED_FIELDS = frozenset(
    {
        "id",
        "schema_version",
        "adapter",
        "record_class",
        "event_kind",
        "observation_origin",
        "source_id",
        "raw_reference",
        "event_time",
        "ingest_time",
        "actor_ref",
        "credential_ref",
        "call_ref",
        "object_scope",
        "action",
        "result",
        "source_digest",
        "collection_boundary",
        "redaction",
        "parent_ids",
        "depends_on",
        "authenticity",
        "actor_binding",
        "binding_basis",
        "time_basis",
        "polarity",
        "statement",
        "public_bytes",
        "synthetic",
        "access_level",
        "custody",
        "locally_held",
        "independence_group",
        "publisher",
        "unavailable_fields",
        "record_flags",
        "verification_method",
        "conflicts_with",
    }
)
FORBIDDEN_INPUT_FIELDS = frozenset(
    {
        "injection_flag",
        "harness_truth",
        "hidden_label",
        "privileged",
        "confirmed_effect",
        "ground_truth",
        "future_stage",
        "truth",
    }
)
# Source column, normalized field, where it lands in the provenance graph.
FIELD_MAP = (
    ("record_id", "id", "source_record.id and observed_event.id"),
    ("origin", "observation_origin", "source_record.observation_origin"),
    ("raw or public_bytes", "public_bytes", "source_record.public_bytes"),
    ("sha256 of public_bytes", "source_digest", "source_record.content_digest"),
    ("locator, url, offsets, retrieval", "raw_reference", "source_record locators"),
    ("event_time", "event_time", "observed_event.event_time when the basis allows it"),
    ("ingest_time", "ingest_time", "observed_event.observed_time only with a stated event_time"),
    ("actor", "actor_ref", "observed_event.actor_ref"),
    ("credential", "credential_ref", "not a provenance field; salted hash only"),
    ("call_id", "call_ref", "not a provenance field"),
    ("object", "object_scope", "statement only"),
    ("action", "action", "statement only"),
    ("result", "result", "statement only"),
    ("collection_boundary", "collection_boundary", "source_record.collection_boundary"),
    ("redaction", "redaction", "source_record.redaction"),
    ("parent_id", "parent_ids", "reconciliation correlation, not depends_on"),
    ("depends_on", "depends_on", "source_record.depends_on"),
)
_TRACKED_ABSENCES = (
    "event_time",
    "ingest_time",
    "actor_ref",
    "credential_ref",
    "call_ref",
    "action",
    "result",
    "public_bytes",
)
_ABSENT_TIME = {"", "null", "missing", "unknown", "none"}
_REDACTION_MARKERS = {"[REDACTED]", "REDACTED"}


class UnsupportedAttachment(ValueError):
    """The file type is not an adapter input. No rows are produced."""


def read_rows(path: Path, *, kind: str) -> list[dict[str, Any]]:
    """Read JSONL, CSV, or an excerpt YAML file. Refuse every other type."""
    suffix = path.suffix.lower()
    if kind in {"agent", "service"}:
        if suffix == ".jsonl":
            return _read_jsonl(path)
        if suffix == ".csv":
            return _read_csv(path)
        raise UnsupportedAttachment(
            f"unsupported attachment {path.name}; no rows read"
        )
    if kind == "excerpt":
        if suffix in {".yaml", ".yml"}:
            return _read_excerpt_specs(path)
        raise UnsupportedAttachment(
            f"unsupported attachment {path.name}; no rows read"
        )
    raise UnsupportedAttachment(f"unsupported attachment kind {kind!r}; no rows read")


def adapt_agent_tool_records(
    rows: list[dict[str, Any]], *, salt: str, locator_prefix: str = "agent"
) -> list[dict[str, Any]]:
    """Normalize requested commands, displayed tool calls, and tool responses."""
    return _adapt_rows(
        rows,
        adapter="agent_tool_record",
        surfaces=AGENT_SURFACES,
        salt=salt,
        locator_prefix=locator_prefix,
    )


def adapt_service_effect_logs(
    rows: list[dict[str, Any]], *, salt: str, locator_prefix: str = "service"
) -> list[dict[str, Any]]:
    """Normalize API events, service logs, and committed-effect logs."""
    return _adapt_rows(
        rows,
        adapter="service_effect_log",
        surfaces=SERVICE_SURFACES,
        salt=salt,
        locator_prefix=locator_prefix,
    )


def adapt_public_excerpts(
    specs: list[dict[str, Any]],
    pinned_sources: dict[str, dict[str, Any]],
    *,
    salt: str,
) -> list[dict[str, Any]]:
    """Pin a public excerpt as a reported narrative. It is not an effect log."""
    if not isinstance(specs, list):
        raise ValueError("excerpts must be a list")
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ValueError(f"excerpt {index} must be an object")
        unknown = set(spec) - EXCERPT_FIELDS
        if unknown:
            raise ValueError(f"unknown excerpt field: {sorted(unknown)}")
        record_id = _nonempty(spec.get("record_id"), "record_id")
        if record_id in seen:
            raise ValueError(f"duplicate record id: {record_id}")
        seen.add(record_id)
        surface = spec.get("surface")
        if surface not in EXCERPT_SURFACES:
            raise ValueError(f"surface {surface!r} is not a public excerpt")
        if spec.get("synthetic") is not False:
            raise ValueError("a pinned public excerpt is not synthetic telemetry")
        polarity = spec.get("polarity") or "reports"
        if polarity not in {"reports", "contradicts", "supports"}:
            raise ValueError(f"unknown polarity: {polarity!r}")
        source_id = _nonempty(spec.get("pinned_source_id"), "pinned_source_id")
        try:
            source = pinned_sources[source_id]
        except KeyError as exc:
            raise ValueError(f"unpinned excerpt source: {source_id}") from exc
        public = source.get("public_bytes")
        if not isinstance(public, str) or public == "":
            raise ValueError(f"{source_id} has no pinned public bytes")
        if source.get("content_digest") != content_sha256(public):
            raise ValueError(f"pinned digest mismatch: {source_id}")
        event_time = _optional_time(spec.get("event_time"), f"{record_id}.event_time")
        ingest_time = _optional_time(spec.get("ingest_time"), f"{record_id}.ingest_time")
        time_basis = _time_basis(spec.get("time_basis"), event_time, record_id)
        if "retrieval" in source and source["retrieval"] is not None:
            # A page retrieval time is not an event time and not an ingest time.
            if ingest_time == source["retrieval"].get("retrieved_at"):
                raise ValueError(f"{record_id}: retrieval time is not ingest time")
        event = _finish_event(
            record_id=record_id,
            adapter="public_excerpt",
            record_class=surface,
            event_kind=EXCERPT_SURFACES[surface],
            origin=source["observation_origin"],
            source_id=source_id,
            raw_reference={
                "locator": f"{source['canonical_url']}#{source_id}",
                "canonical_url": source["canonical_url"],
                "byte_offset": _copy_offset(source["byte_offset"]),
                "retrieved_document_offset": _copy_offset(
                    source["retrieved_document_offset"]
                ),
                "retrieval": _copy_retrieval(source["retrieval"]),
                "duplicate_of": source["duplicate_of"],
            },
            event_time=event_time,
            ingest_time=ingest_time,
            actor_ref=None,
            credential_ref=None,
            call_ref=None,
            object_scope=None,
            action=None,
            result=None,
            public_bytes=public,
            source_digest=source["content_digest"],
            collection_boundary=source["collection_boundary"],
            redaction=source["redaction"],
            parent_ids=[],
            depends_on=list(source["depends_on"]),
            authenticity="not_checked",
            actor_binding="not_applicable",
            binding_basis="not_applicable",
            time_basis=time_basis,
            polarity=polarity,
            synthetic=False,
            access_level=source["access_level"],
            custody=source["custody"],
            locally_held=source["locally_held"],
            independence_group=source["independence_group"],
            publisher=source["publisher"],
            record_flags=[],
            secrets=[],
        )
        events.append(event)
    return events


def reconcile_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Link records without treating a token, a narrative, or a log as an effect."""
    by_id = {event["id"]: event for event in events}
    if len(by_id) != len(events):
        raise ValueError("duplicate normalized record id")
    links: list[dict[str, Any]] = []
    ordered = sorted(by_id)
    for index, left_id in enumerate(ordered):
        for right_id in ordered[index + 1 :]:
            left = by_id[left_id]
            right = by_id[right_id]
            correlation = _correlation(left, right)
            if correlation is None:
                continue
            status, flags = _classify_pair(left, right, correlation)
            links.append(_make_link(left, right, status, flags, correlation))
    linked = {link["left_id"] for link in links} | {
        link["right_id"] for link in links if link["right_id"]
    }
    for record_id in ordered:
        if record_id in linked:
            continue
        event = by_id[record_id]
        status, flags = _classify_singleton(event)
        links.append(_make_link(event, None, status, flags, "singleton"))
    _annotate_links(links, by_id)
    links.sort(key=lambda link: link["id"])
    return {
        "schema_version": TELEMETRY_VERSION,
        "provenance_contract": CONTRACT_VERSION,
        "links": links,
        "real_world_authenticity_certified": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
    }


def apply_conflicts(
    events: list[dict[str, Any]], links: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Copy disagreement links onto provenance ``conflicts_with`` ids."""
    extra: dict[str, set[str]] = {}
    for link in links:
        if link["status"] not in {"conflicting", "spoof_suspected"}:
            continue
        if not link["right_id"]:
            continue
        extra.setdefault(link["left_id"], set()).add(f"ev-{link['right_id']}")
        extra.setdefault(link["right_id"], set()).add(f"ev-{link['left_id']}")
    updated: list[dict[str, Any]] = []
    for event in events:
        item = dict(event)
        item["conflicts_with"] = sorted(extra.get(event["id"], set()))
        updated.append(item)
    return updated


def load_origin_packet(directory: Path, *, salt: str) -> dict[str, Any]:
    """Read the two record origins. Do not read a harness-truth file.

    A missing origin file is a missing origin. No actor, time, or effect row
    is created to fill it. Issue #41's application export is that packet when
    it is present; this loader does not invent the export.
    """
    directory = Path(directory)
    origins = (
        ("actor_tool", "actor_records.jsonl", "agent"),
        ("service_effect", "service_records.jsonl", "service"),
    )
    events: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for origin, name, kind in origins:
        path = directory / name
        if not path.is_file():
            missing.append(
                {
                    "origin": origin,
                    "path": name,
                    "rows": 0,
                    "event_time": None,
                    "invented": False,
                }
            )
            continue
        rows = read_rows(path, kind=kind)
        if kind == "agent":
            adapted = adapt_agent_tool_records(rows, salt=salt, locator_prefix=name)
        else:
            adapted = adapt_service_effect_logs(rows, salt=salt, locator_prefix=name)
        events.extend(adapted)
    return {
        "schema_version": TELEMETRY_VERSION,
        "events": events,
        "missing_origins": missing,
        "truth_files_read": [],
    }


def comparator_packet(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One lossless view for every comparator. No second, privileged copy."""
    packet = []
    for event in events:
        if set(event) != NORMALIZED_FIELDS:
            raise ValueError("packet record is not the normalized contract")
        packet.append({key: event[key] for key in sorted(NORMALIZED_FIELDS)})
    packet.sort(key=lambda item: item["id"])
    return packet


def verify_digest(event: dict[str, Any]) -> bool:
    """True when ``source_digest`` is the sha256 of the held bytes."""
    public = event.get("public_bytes")
    digest = event.get("source_digest")
    if public is None:
        return digest is None
    if not isinstance(public, str):
        return False
    return digest == content_sha256(public)


def source_from_event(event: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the provenance source. Does not add bytes the record lacks."""
    raw = event["raw_reference"]
    return make_source(
        id=event["source_id"],
        canonical_url=raw["canonical_url"],
        publisher=event["publisher"],
        observation_origin=event["observation_origin"],
        independence_group=event["independence_group"],
        depends_on=list(event["depends_on"]),
        duplicate_of=raw["duplicate_of"],
        access_level=event["access_level"],
        collection_boundary=event["collection_boundary"],
        custody=event["custody"],
        redaction=event["redaction"],
        locally_held=event["locally_held"],
        public_bytes=event["public_bytes"],
        content_digest=event["source_digest"],
        byte_offset=_copy_offset(raw["byte_offset"]),
        retrieved_document_offset=_copy_offset(raw["retrieved_document_offset"]),
        retrieval=_copy_retrieval(raw["retrieval"]),
    )


def assemble_graph(
    events: list[dict[str, Any]],
    *,
    extra_sources: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    pinned_sources: dict[str, dict[str, Any]] | None = None,
    graph_id: str,
    notes: str,
) -> dict[str, Any]:
    """Emit a provenance graph. Unavailable sources contribute no events."""
    pinned_sources = pinned_sources or {}
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in extra_sources:
        if source["id"] in seen:
            raise ValueError(f"duplicate source id: {source['id']}")
        sources.append(source)
        seen.add(source["id"])
    extractions: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    for event in events:
        if set(event) != NORMALIZED_FIELDS:
            missing = NORMALIZED_FIELDS - set(event)
            extra = set(event) - NORMALIZED_FIELDS
            raise ValueError(f"normalized record fields mismatch: {missing or extra}")
        source_id = event["source_id"]
        if source_id not in seen:
            if source_id in pinned_sources:
                sources.append(_copy_source(pinned_sources[source_id]))
            else:
                sources.append(source_from_event(event))
            seen.add(source_id)
        extractions.append(
            make_extraction(
                id=f"ext-{event['id']}",
                analyst_id="forensic-telemetry-v1",
                analysis_origin="unknown",
                source_ids=[source_id],
            )
        )
        observed.append(_provenance_event(event))
    graph = {
        "id": graph_id,
        "source_records": sources,
        "extractions": extractions,
        "observed_events": observed,
        "claims": claims,
        "notes": notes,
    }
    validate_graph(graph)
    return graph


def qualify_telemetry_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Score claims with the provenance contract, including upgrade blockers."""
    qualified = qualify_graph(graph)
    if qualified["contract_version"] != CONTRACT_VERSION:
        raise ValueError("provenance contract mismatch")
    return qualified


def probe_held_source_gate(
    graph: dict[str, Any], claim_id: str, held_source_id: str
) -> dict[str, Any]:
    """Offer a verified narrative that does not use ``held_source_id``.

    The slot is marked ``blocks_upgrade`` only when that source is held.
    An unavailable source is rejected instead of being turned into a gate.
    The probe is not written into the saved graph.
    """
    import copy

    from swarm_witness.provenance import source_unavailable

    probed = copy.deepcopy(graph)
    sources = {source["id"]: source for source in probed["source_records"]}
    if held_source_id not in sources:
        raise KeyError(held_source_id)
    if source_unavailable(sources[held_source_id]):
        raise ValueError(
            f"unavailable source {held_source_id} cannot be an upgrade gate"
        )
    found = False
    for claim in probed["claims"]:
        if claim["id"] != claim_id:
            continue
        found = True
        slotted = False
        for slot in claim["evidence_slots"]:
            if slot["source_id"] == held_source_id:
                slot["blocks_upgrade"] = True
                slotted = True
        if not slotted:
            claim["evidence_slots"].append(
                {
                    "id": "slot-held-gate-probe",
                    "source_id": held_source_id,
                    "blocks_upgrade": True,
                    "role": "held source used only to exercise the upgrade rule",
                }
            )
    if not found:
        raise KeyError(claim_id)
    text = "synthetic narrative that does not use the gated source"
    digest = content_sha256(text)
    nbytes = len(text.encode("utf-8"))
    source_id = "src-unrelated-probe-log"
    probed["source_records"].append(
        make_source(
            id=source_id,
            canonical_url="fixture://telemetry/unrelated-probe-log",
            publisher="fixture",
            observation_origin="synthetic_control",
            independence_group="synthetic:unrelated-probe-log",
            collection_boundary=(
                "Synthetic narrative used to exercise a held-source upgrade gate. "
                "Not an incident log and not a platform log."
            ),
            public_bytes=text,
            content_digest=digest,
            byte_offset={"start": 0, "end": nbytes},
            retrieved_document_offset={"start": 0, "end": nbytes},
            access_level="public_bytes",
            custody="intact",
            redaction="none",
            locally_held=True,
        )
    )
    probed["extractions"].append(
        make_extraction(
            id="ext-unrelated-probe-log",
            analyst_id="forensic-telemetry-v1",
            analysis_origin="unknown",
            source_ids=[source_id],
        )
    )
    probed["observed_events"].append(
        make_event(
            id="ev-unrelated-probe-log",
            extraction_ids=["ext-unrelated-probe-log"],
            necessary_source_ids=[source_id],
            event_kind="narrative_report",
            statement=(
                "synthetic_control; unrelated narrative; does not use the gated source"
            ),
            polarity="supports",
            actor_binding="not_applicable",
            actor_ref=None,
            event_time=None,
            observed_time=None,
            time_basis="missing",
            authenticity="not_checked",
            verification_method="excerpt_sha256",
        )
    )
    for claim in probed["claims"]:
        if claim["id"] == claim_id:
            claim["event_ids"] = [*claim["event_ids"], "ev-unrelated-probe-log"]
    return qualify_claim(probed, claim_id)


def unavailable_telemetry(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sources with no ingested log row and no invented effect time."""
    rows = []
    for source in sources:
        rows.append(
            {
                "source_id": source["id"],
                "observation_origin": source["observation_origin"],
                "access_level": source["access_level"],
                "redaction": source["redaction"],
                "independence_group": source["independence_group"],
                "event_time": None,
                "ingested_as_log": False,
                "public_bytes_held": source.get("public_bytes") is not None,
            }
        )
    return rows


def blinded_stage_summary(
    stage_a: dict[str, Any], stage_b: dict[str, Any], unknowns: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compact stage labels. Full qualifications stay on the runs."""

    def _compact(qualified: dict[str, Any]) -> dict[str, Any]:
        claims = {}
        for claim_id, claim in qualified["claims"].items():
            claims[claim_id] = {
                "finding_label": claim["finding_label"],
                "conclusion_class": claim["conclusion_class"],
                "effect_status": claim["effect_status"],
                "primary_upgrade_blocker": claim["primary_upgrade_blocker"],
                "chronology_event_time": claim["chronology"]["event_time"],
                "real_world_authenticity_certified": claim[
                    "real_world_authenticity_certified"
                ],
                "incident_detection_claimed": claim["incident_detection_claimed"],
                "incident_prevention_claimed": claim["incident_prevention_claimed"],
            }
        return claims

    return {
        "schema_version": TELEMETRY_VERSION,
        "provenance_contract": CONTRACT_VERSION,
        "stage_a_withheld": (
            "Synthetic telemetry is withheld. Private and unobserved logs stay missing."
        ),
        "stage_b_added": (
            "Labeled synthetic_control rows only. They are not added to the "
            "incident effect claim."
        ),
        "stage_a": _compact(stage_a),
        "stage_b": _compact(stage_b),
        "unknowns": unknowns,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "real_world_authenticity_certified": False,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip() == "":
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{line_no} is not a JSON object") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}:{line_no} is not a JSON object")
        rows.append(item)
    return rows


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path.name} has no header")
        unknown = set(reader.fieldnames) - ROW_FIELDS
        if unknown:
            raise ValueError(f"unknown csv field: {sorted(unknown)}")
        rows = []
        for row in reader:
            item = {}
            for key, value in row.items():
                if key is None:
                    raise ValueError(f"{path.name} has an extra csv column")
                item[key] = None if value is None or value == "" else value
            rows.append(item)
    return rows


def _read_excerpt_specs(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("excerpt file must be an object")
    unknown = set(payload) - {"schema_version", "excerpts"}
    if unknown:
        raise ValueError(f"unknown excerpt file field: {sorted(unknown)}")
    if payload.get("schema_version") != TELEMETRY_VERSION:
        raise ValueError("excerpt schema_version mismatch")
    specs = payload.get("excerpts")
    if not isinstance(specs, list):
        raise ValueError("excerpts must be a list")
    return specs


def _adapt_rows(
    rows: list[dict[str, Any]],
    *,
    adapter: str,
    surfaces: dict[str, str],
    salt: str,
    locator_prefix: str,
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    _reject_forbidden(rows)
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"row {index} must be an object")
        unknown = set(row) - ROW_FIELDS
        if unknown:
            raise ValueError(f"unknown field {sorted(unknown)} at row {index}")
        record_id = _nonempty(row.get("record_id"), "record_id")
        if record_id in seen:
            raise ValueError(f"duplicate record id: {record_id}")
        seen.add(record_id)
        surface = row.get("surface")
        if surface not in surfaces:
            raise ValueError(f"surface {surface!r} is not accepted by {adapter}")
        if "synthetic" not in row:
            raise ValueError(f"{record_id}: synthetic must be explicit")
        synthetic = _bool(row.get("synthetic"), "synthetic")
        origin = row.get("origin")
        if origin not in OBSERVATION_ORIGINS:
            raise ValueError(f"unknown observation_origin: {origin!r}")
        publisher = _nonempty(row.get("publisher"), "publisher")
        group = _nonempty(row.get("independence_group"), "independence_group")
        boundary = _nonempty(row.get("collection_boundary"), "collection_boundary")
        public = _row_bytes(row, record_id)
        actor_ref, actor_secret = _identifier(
            row.get("actor"), role="actor", salt=salt
        )
        credential_ref, credential_secret = _identifier(
            row.get("credential"),
            role="credential",
            salt=salt,
            always_redact=True,
        )
        secrets = [item for item in (actor_secret, credential_secret) if item]
        _reject_plaintext(row, secrets)
        binding_basis = row.get("binding_basis") or "not_provided"
        actor_binding = _actor_binding(
            row.get("actor_binding"), binding_basis, actor_ref
        )
        event_time = _optional_time(row.get("event_time"), f"{record_id}.event_time")
        ingest_time = _optional_time(row.get("ingest_time"), f"{record_id}.ingest_time")
        time_basis = _time_basis(row.get("time_basis"), event_time, record_id)
        if public is None:
            access = row.get("access_level")
            redaction = row.get("redaction")
            if access is None or redaction is None:
                raise ValueError(
                    f"{record_id}: a row without bytes must name access_level and redaction"
                )
            locally_held = _bool(row.get("locally_held", False), "locally_held")
            if locally_held:
                raise ValueError(f"{record_id}: locally_held requires public bytes")
            custody = row.get("custody") or "unknown"
            digest = None
            canonical = row.get("canonical_url")
            offset = None
        else:
            access = row.get("access_level") or "public_bytes"
            redaction = row.get("redaction") or "none"
            locally_held = True
            custody = row.get("custody") or "intact"
            digest = content_sha256(public)
            canonical = row.get("canonical_url")
            nbytes = len(public.encode("utf-8"))
            offset = {"start": 0, "end": nbytes}
        if row.get("parent_id") not in (None, "") and row.get("parent_ids") not in (
            None,
            "",
            [],
        ):
            raise ValueError(f"{record_id}: set parent_id or parent_ids, not both")
        parent_ids = _id_list(row.get("parent_ids"))
        if row.get("parent_id"):
            parent_ids = _id_list(row.get("parent_id"))
        authenticity = row.get("authenticity") or "not_checked"
        polarity = row.get("polarity") or "reports"
        if polarity not in {"supports", "contradicts", "reports"}:
            raise ValueError(f"unknown polarity: {polarity!r}")
        source_id = row.get("source_id") or f"src-{record_id}"
        event = _finish_event(
            record_id=record_id,
            adapter=adapter,
            record_class=surface,
            event_kind=surfaces[surface],
            origin=origin,
            source_id=source_id,
            raw_reference={
                "locator": row.get("locator") or f"{locator_prefix}#{record_id}",
                "canonical_url": canonical,
                "byte_offset": offset,
                "retrieved_document_offset": _copy_offset(offset),
                "retrieval": None,
                "duplicate_of": None,
            },
            event_time=event_time,
            ingest_time=ingest_time,
            actor_ref=actor_ref,
            credential_ref=credential_ref,
            call_ref=_plain(row.get("call_id")),
            object_scope=_plain(row.get("object")),
            action=_plain(row.get("action")),
            result=_plain(row.get("result")),
            public_bytes=public,
            source_digest=digest,
            collection_boundary=boundary,
            redaction=redaction,
            parent_ids=parent_ids,
            depends_on=_id_list(row.get("depends_on")),
            authenticity=authenticity,
            actor_binding=actor_binding,
            binding_basis=str(binding_basis),
            time_basis=time_basis,
            polarity=polarity,
            synthetic=synthetic,
            access_level=access,
            custody=custody,
            locally_held=locally_held,
            independence_group=group,
            publisher=publisher,
            record_flags=_record_flags(
                stated_binding=row.get("actor_binding"),
                binding_basis=str(binding_basis),
                actor_ref=actor_ref,
                event_kind=surfaces[surface],
                object_scope=_plain(row.get("object")),
            ),
            secrets=secrets,
        )
        if event["event_kind"] not in EVENT_KINDS:
            raise ValueError(f"unmapped event kind: {event['event_kind']}")
        events.append(event)
    return events


def _finish_event(**fields: Any) -> dict[str, Any]:
    secrets: list[str] = fields.pop("secrets")
    record_class = fields["record_class"]
    corpus = "synthetic_control" if fields["synthetic"] else "reported"
    statement = (
        f"{corpus}; {record_class}; source={fields['source_id']}; "
        f"call={fields['call_ref'] or 'none'}; "
        f"action={fields['action'] or 'none'}; "
        f"result={fields['result'] or 'none'}; "
        f"object={fields['object_scope'] or 'none'}"
    )
    verification = _verification_method(
        event_kind=fields["event_kind"],
        origin=fields["origin"],
        public=fields["public_bytes"],
        digest=fields["source_digest"],
        redaction=fields["redaction"],
        access=fields["access_level"],
        custody=fields["custody"],
        locally_held=fields["locally_held"],
        authenticity=fields["authenticity"],
    )
    event = {
        "id": fields["record_id"],
        "schema_version": TELEMETRY_VERSION,
        "adapter": fields["adapter"],
        "record_class": record_class,
        "event_kind": fields["event_kind"],
        "observation_origin": fields["origin"],
        "source_id": fields["source_id"],
        "raw_reference": fields["raw_reference"],
        "event_time": fields["event_time"],
        "ingest_time": fields["ingest_time"],
        "actor_ref": fields["actor_ref"],
        "credential_ref": fields["credential_ref"],
        "call_ref": fields["call_ref"],
        "object_scope": fields["object_scope"],
        "action": fields["action"],
        "result": fields["result"],
        "source_digest": fields["source_digest"],
        "collection_boundary": fields["collection_boundary"],
        "redaction": fields["redaction"],
        "parent_ids": list(fields["parent_ids"]),
        "depends_on": list(fields["depends_on"]),
        "authenticity": fields["authenticity"],
        "actor_binding": fields["actor_binding"],
        "binding_basis": fields["binding_basis"],
        "time_basis": fields["time_basis"],
        "polarity": fields["polarity"],
        "statement": statement,
        "public_bytes": fields["public_bytes"],
        "synthetic": fields["synthetic"],
        "access_level": fields["access_level"],
        "custody": fields["custody"],
        "locally_held": fields["locally_held"],
        "independence_group": fields["independence_group"],
        "publisher": fields["publisher"],
        "unavailable_fields": [
            name for name in _TRACKED_ABSENCES if fields.get(name) is None
        ],
        "record_flags": sorted(set(fields["record_flags"])),
        "verification_method": verification,
        "conflicts_with": [],
    }
    if set(event) != NORMALIZED_FIELDS:
        raise RuntimeError("normalized field set drifted")
    _assert_no_secrets(event, secrets)
    return event


def _verification_method(
    *,
    event_kind: str,
    origin: str,
    public: str | None,
    digest: str | None,
    redaction: str,
    access: str,
    custody: str,
    locally_held: bool,
    authenticity: str,
) -> str:
    if authenticity == "forged":
        return "none"
    held = (
        isinstance(public, str)
        and public != ""
        and digest == content_sha256(public)
        and redaction == "none"
        and access == "public_bytes"
        and custody == "intact"
        and locally_held is True
    )
    if not held:
        return "none"
    if event_kind == "narrative_report":
        return "excerpt_sha256"
    if event_kind in {"independent_service_log", "committed_effect"} and origin in LOG_ORIGINS:
        return "independent_log_digest"
    return "none"


def _provenance_event(event: dict[str, Any]) -> dict[str, Any]:
    """Map times without promoting ingest time or a missing effect time."""
    event_time = None
    observed = None
    if event["time_basis"] in {"source_stated", "reconstructed"}:
        event_time = event["event_time"]
        observed = event["ingest_time"]
    return make_event(
        id=f"ev-{event['id']}",
        extraction_ids=[f"ext-{event['id']}"],
        necessary_source_ids=[event["source_id"]],
        event_kind=event["event_kind"],
        statement=event["statement"],
        polarity=event["polarity"],
        actor_binding=event["actor_binding"],
        actor_ref=event["actor_ref"],
        event_time=event_time,
        observed_time=observed,
        time_basis=event["time_basis"],
        authenticity=event["authenticity"],
        verification_method=event["verification_method"],
        conflicts_with=list(event["conflicts_with"]),
    )


def _correlation(left: dict[str, Any], right: dict[str, Any]) -> str | None:
    if left["id"] in right["parent_ids"] or right["id"] in left["parent_ids"]:
        return "parent"
    tokens = {
        left.get("actor_ref"),
        right.get("actor_ref"),
        left.get("credential_ref"),
        right.get("credential_ref"),
    }
    shared = set(left["parent_ids"]) & set(right["parent_ids"])
    if shared - tokens - {None}:
        return "parent"
    call = left.get("call_ref")
    if call and call == right.get("call_ref") and call not in tokens:
        return "call"
    if left.get("actor_ref") and left["actor_ref"] == right.get("actor_ref"):
        return "token_only"
    if left.get("credential_ref") and left["credential_ref"] == right.get("credential_ref"):
        return "token_only"
    return None


def _classify_pair(
    left: dict[str, Any], right: dict[str, Any], correlation: str
) -> tuple[str, list[str]]:
    if correlation == "token_only":
        return "unlinked", ["token_only"]
    if left["authenticity"] == "forged" or right["authenticity"] == "forged":
        return "spoof_suspected", ["forged"]
    if _response_mismatch(left, right):
        return "spoof_suspected", ["response_command_mismatch"]
    if left["action"] and right["action"] and left["action"] != right["action"]:
        return "conflicting", ["action_mismatch"]
    if (
        left["event_time"] is not None
        and right["event_time"] is not None
        and left["event_time"] != right["event_time"]
    ):
        return "conflicting", ["timestamp_disagreement"]
    if _origin_blocked(left) or _origin_blocked(right):
        return "unlinked", [_origin_flag(left, right)]
    if left["event_kind"] in NARRATIVE_KINDS or right["event_kind"] in NARRATIVE_KINDS:
        return "unlinked", ["reported_not_effect"]
    left_agent = left["event_kind"] in AGENT_KINDS
    right_agent = right["event_kind"] in AGENT_KINDS
    left_effect = left["event_kind"] in EFFECT_KINDS
    right_effect = right["event_kind"] in EFFECT_KINDS
    if not left_effect and not right_effect:
        return "unlinked", ["absent_effect"]
    if not left_agent and not right_agent:
        if _service_pair_agrees(left, right):
            return "confirmed", ["service_corroboration"]
        if left["event_time"] is None or right["event_time"] is None:
            return "unlinked", ["missing_time"]
        return "unlinked", ["effect_not_held"]
    if left["event_time"] is None or right["event_time"] is None:
        return "unlinked", ["missing_time"]
    agent = left if left_agent else right
    effect = right if left_agent else left
    if not _bound_principal(agent) or not _bound_principal(effect):
        return "unlinked", ["unverified_binding"]
    if not _held(effect):
        return "unlinked", ["effect_not_held"]
    if not _held(agent):
        return "unlinked", ["agent_record_not_held"]
    binding_flags = _effect_binding_flags(agent, effect)
    if binding_flags:
        if any(flag.endswith("_mismatch") for flag in binding_flags):
            return "conflicting", binding_flags
        return "unlinked", binding_flags
    return "confirmed", []


def _classify_singleton(event: dict[str, Any]) -> tuple[str, list[str]]:
    if event["event_kind"] in NARRATIVE_KINDS:
        return "unlinked", ["reported_not_effect"]
    if event["authenticity"] == "forged":
        return "spoof_suspected", ["absent_effect", "forged"]
    if event["event_kind"] in EFFECT_KINDS:
        return "unlinked", ["missing_transcript"]
    if event["event_kind"] in AGENT_KINDS:
        return "unlinked", ["absent_effect"]
    return "unlinked", ["unlinked"]


def _annotate_links(
    links: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]
) -> None:
    agent_partners: dict[str, set[str]] = {}
    service_partners: dict[str, set[str]] = {}
    effect_links: dict[str, list[dict[str, Any]]] = {}
    for link in links:
        if link["right_id"] is None:
            continue
        if link["correlation"] in {"token_only", "singleton"}:
            continue
        if link["status"] not in {"confirmed", "conflicting"}:
            continue
        left = by_id[link["left_id"]]
        right = by_id[link["right_id"]]
        for agent, service in ((left, right), (right, left)):
            if agent["event_kind"] in AGENT_KINDS and service["event_kind"] in EFFECT_KINDS:
                agent_partners.setdefault(agent["id"], set()).add(service["id"])
                service_partners.setdefault(service["id"], set()).add(agent["id"])
        if link["status"] != "confirmed":
            continue
        agent, effect = _agent_effect(left, right)
        if agent is None or effect is None or effect["event_kind"] != "committed_effect":
            continue
        effect_links.setdefault(agent["id"], []).append(link)
        effect_links.setdefault(effect["id"], []).append(link)
    ambiguous: set[str] = set()
    for group in effect_links.values():
        if len(group) > 1:
            ambiguous.update(link["id"] for link in group)
    for link in links:
        if link["id"] in ambiguous:
            link["ambiguous"] = True
            link["flags"].append("ambiguous_effect")
        if link["status"] in {"confirmed", "conflicting"} and link["right_id"]:
            left = by_id[link["left_id"]]
            right = by_id[link["right_id"]]
            agent, service = _agent_effect(left, right)
            if (
                agent is not None
                and service is not None
                and len(service_partners.get(service["id"], ())) > 1
            ):
                link["ambiguous"] = True
                link["flags"].append("ambiguous_actor")
        if link["right_id"] and link["status"] in {"confirmed", "conflicting"}:
            left = by_id[link["left_id"]]
            right = by_id[link["right_id"]]
            if any(
                len(agent_partners.get(side["id"], ())) > 1
                for side in (left, right)
                if side["event_kind"] in AGENT_KINDS
            ):
                link["flags"].append("one_to_many")
            if any(
                len(service_partners.get(side["id"], ())) > 1
                for side in (left, right)
                if side["event_kind"] in EFFECT_KINDS
            ):
                link["flags"].append("many_to_one")
        link["confirmed_effect"] = _confirmed_effect(link, by_id)
    groups: dict[str, list[dict[str, Any]]] = {}
    for link in links:
        groups.setdefault(link["left_id"], []).append(link)
        if link["right_id"]:
            groups.setdefault(link["right_id"], []).append(link)
    for endpoint, group in groups.items():
        best = min(group, key=lambda item: (STATUS_RANK[item["status"]], item["id"]))
        best["primary_for"].append(endpoint)
    for link in links:
        link["primary_for"] = sorted(set(link["primary_for"]))
        link["primary"] = bool(link["primary_for"])
        link["flags"] = sorted(set(link["flags"]))
        if link["status"] not in LINK_STATUSES:
            raise RuntimeError(f"bad link status: {link['status']}")


def _confirmed_effect(link: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> bool:
    if link["ambiguous"] or link["status"] != "confirmed" or not link["right_id"]:
        return False
    left = by_id[link["left_id"]]
    right = by_id[link["right_id"]]
    agent, effect = _agent_effect(left, right)
    if agent is None or effect is None or effect["event_kind"] != "committed_effect":
        return False
    if effect["polarity"] != "supports":
        return False
    if effect["verification_method"] != "independent_log_digest":
        return False
    if effect["observation_origin"] not in LOG_ORIGINS:
        return False
    if effect["authenticity"] == "forged" or not _held(effect) or not _held(agent):
        return False
    if "invalid_binding" in effect["record_flags"] or "invalid_binding" in agent["record_flags"]:
        return False
    if "invalid_scope" in effect["record_flags"] or not effect["object_scope"]:
        return False
    if _effect_binding_flags(agent, effect):
        return False
    return _bound_principal(agent) and _bound_principal(effect)


def _agent_effect(
    left: dict[str, Any], right: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if left["event_kind"] in AGENT_KINDS and right["event_kind"] in EFFECT_KINDS:
        return left, right
    if right["event_kind"] in AGENT_KINDS and left["event_kind"] in EFFECT_KINDS:
        return right, left
    return None, None


def _response_mismatch(left: dict[str, Any], right: dict[str, Any]) -> bool:
    classes = {left["record_class"], right["record_class"]}
    if "tool_response" not in classes:
        return False
    if not classes & {"displayed_tool_call", "requested_command"}:
        return False
    return bool(left["result"] and right["result"] and left["result"] != right["result"])


def _service_pair_agrees(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left["event_time"] is None or right["event_time"] is None:
        return False
    if left["event_time"] != right["event_time"]:
        return False
    if not left["action"] or left["action"] != right["action"]:
        return False
    return (
        _held(left)
        and _held(right)
        and _bound_principal(left)
        and _bound_principal(right)
    )


def _origin_blocked(event: dict[str, Any]) -> bool:
    if event["redaction"] != "none":
        return True
    if event["access_level"] != "public_bytes":
        return True
    return event["locally_held"] is not True


def _origin_flag(left: dict[str, Any], right: dict[str, Any]) -> str:
    for event in (left, right):
        if event["redaction"] in {"partial", "withheld_original"} or event["access_level"] == "redacted":
            return "redacted_origin"
    return "unverified_origin"


def _held(event: dict[str, Any]) -> bool:
    return (
        event["locally_held"] is True
        and isinstance(event["public_bytes"], str)
        and event["public_bytes"] != ""
        and event["source_digest"] == content_sha256(event["public_bytes"])
        and event["redaction"] == "none"
        and event["access_level"] == "public_bytes"
        and event["custody"] == "intact"
    )


def _stated(event: dict[str, Any], field: str) -> str | None:
    value = event.get(field)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _effect_binding_flags(agent: dict[str, Any], effect: dict[str, Any]) -> list[str]:
    """Actor, object, and operation must agree, or the pair is not one effect.

    A shared call id is not a verified mapping. Equal stated bindings are.
    """
    flags: list[str] = []
    for field, mismatch in (
        ("actor_ref", "actor_mismatch"),
        ("object_scope", "object_mismatch"),
        ("action", "operation_mismatch"),
    ):
        left, right = _stated(agent, field), _stated(effect, field)
        if left and right and left == right:
            continue
        flags.append(mismatch if left and right else "unresolved_binding")
    return flags


def _bound_principal(event: dict[str, Any]) -> bool:
    return (
        event["actor_binding"] == "bound"
        and event["binding_basis"] == "source_stated_principal"
        and bool(event["actor_ref"])
    )


def _make_link(
    left: dict[str, Any],
    right: dict[str, Any] | None,
    status: str,
    flags: list[str],
    correlation: str,
) -> dict[str, Any]:
    if right is None:
        return {
            "id": f"link:{left['id']}:-",
            "left_id": left["id"],
            "right_id": None,
            "status": status,
            "flags": list(flags),
            "correlation": correlation,
            "confirmed_effect": False,
            "ambiguous": False,
            "primary": False,
            "primary_for": [],
            "provenance_path": _prov_path(left),
        }
    ordered = sorted((left, right), key=lambda event: event["id"])
    return {
        "id": f"link:{ordered[0]['id']}:{ordered[1]['id']}",
        "left_id": ordered[0]["id"],
        "right_id": ordered[1]["id"],
        "status": status,
        "flags": list(flags),
        "correlation": correlation,
        "confirmed_effect": False,
        "ambiguous": False,
        "primary": False,
        "primary_for": [],
        "provenance_path": _prov_path(ordered[0]) + _prov_path(ordered[1]),
    }


def _prov_path(event: dict[str, Any]) -> list[str]:
    return [event["source_id"], f"ext-{event['id']}", f"ev-{event['id']}"]


def _row_bytes(row: dict[str, Any], record_id: str) -> str | None:
    raw = row.get("raw")
    public = row.get("public_bytes")
    if raw not in (None, "") and public not in (None, ""):
        if raw != public:
            raise ValueError(f"{record_id}: raw and public_bytes disagree")
        return str(raw)
    if raw not in (None, ""):
        return str(raw)
    if public not in (None, ""):
        return str(public)
    return None


def _identifier(
    value: Any,
    *,
    role: str,
    salt: str,
    always_redact: bool = False,
) -> tuple[str | None, str | None]:
    """Canonicalize a stated identifier. Never mint one the row omitted.

    The digest covers the stated value only. It does not add the record id,
    so a redaction is not turned into a fresh unique actor.
    """
    text = _plain(value)
    if text is None:
        return None, None
    marker = text.upper() in _REDACTION_MARKERS or text.startswith("redacted:")
    if not always_redact and not marker:
        return text, None
    if not salt:
        raise ValueError("redaction salt required before a credential can be canonicalized")
    digest = hashlib.sha256(f"{salt}\0{role}\0{text}".encode("utf-8")).hexdigest()
    secret = None if marker else text
    return f"redacted:{digest}", secret


def _record_flags(
    *,
    stated_binding: Any,
    binding_basis: str,
    actor_ref: str | None,
    event_kind: str,
    object_scope: str | None,
) -> list[str]:
    flags = []
    if stated_binding == "bound" and (
        actor_ref is None or binding_basis != "source_stated_principal"
    ):
        flags.append("invalid_binding")
    if event_kind in EFFECT_KINDS and object_scope is None:
        flags.append("invalid_scope")
    return flags


def _reject_forbidden(rows: list[Any]) -> None:
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        found = FORBIDDEN_INPUT_FIELDS & set(row)
        if found:
            raise ValueError(
                f"row {index} carries privileged fields {sorted(found)}; no rows emitted"
            )


def _reject_plaintext(row: dict[str, Any], secrets: list[str]) -> None:
    if not secrets:
        return
    exposed = {key: value for key, value in row.items() if key != "credential"}
    blob = json.dumps(exposed, default=str)
    for secret in secrets:
        if secret in blob:
            raise ValueError("credential plaintext appears outside the credential field")


def _assert_no_secrets(event: dict[str, Any], secrets: list[str]) -> None:
    if not secrets:
        return
    blob = json.dumps(event, default=str)
    for secret in secrets:
        if secret in blob:
            raise ValueError("credential plaintext leaked into a normalized record")


def _actor_binding(stated: Any, basis: Any, actor_ref: str | None) -> str:
    if actor_ref is None:
        if stated in {None, "", "unknown"}:
            return "unknown"
        if stated == "not_applicable":
            return "not_applicable"
        return "unverified_binding"
    if basis == "token_match":
        return "unverified_binding"
    if stated in {None, ""}:
        return "unknown"
    if stated == "bound" and basis != "source_stated_principal":
        return "unverified_binding"
    if stated not in {"bound", "unverified_binding", "conflicting", "unknown", "not_applicable"}:
        raise ValueError(f"unknown actor_binding: {stated!r}")
    return str(stated)


def _time_basis(stated: Any, event_time: str | None, record_id: str) -> str:
    if stated in (None, ""):
        return "source_stated" if event_time is not None else "missing"
    if stated == "reconstructed":
        if event_time is None:
            raise ValueError(f"{record_id}: reconstructed time without a stated value")
        return "reconstructed"
    if stated == "source_stated":
        if event_time is None:
            raise ValueError(f"{record_id}: source_stated time requires event_time")
        return "source_stated"
    if stated in {"missing", "unknown"}:
        if event_time is not None:
            raise ValueError(f"{record_id}: missing time cannot carry event_time")
        return str(stated)
    raise ValueError(f"unknown time_basis: {stated!r}")


def _optional_time(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid {field}")
    text = value.strip()
    if text.lower() in _ABSENT_TIME:
        return None
    return text


def _plain(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if text == "" or text.lower() in {"null", "none"}:
        return None
    return text


def _bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    raise ValueError(f"{field} must be boolean")


def _id_list(value: Any) -> list[str]:
    if value is None or value == "" or value == []:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [part for part in str(value).split("|") if part != ""]
    if any(not isinstance(item, str) or item.strip() == "" for item in items):
        raise ValueError("ids must be nonblank strings")
    cleaned = [item.strip() for item in items]
    if len(cleaned) != len(set(cleaned)):
        raise ValueError("duplicate id")
    return cleaned


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"invalid or blank field: {field}")
    return value.strip()


def _copy_offset(value: Any) -> dict[str, int] | None:
    if value is None:
        return None
    return {"start": value["start"], "end": value["end"]}


def _copy_retrieval(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "retrieved_at": value["retrieved_at"],
        "http_status": value["http_status"],
        "body_sha256": value["body_sha256"],
        "body_nbytes": value["body_nbytes"],
    }


def _copy_source(source: dict[str, Any]) -> dict[str, Any]:
    import copy

    return copy.deepcopy(source)
