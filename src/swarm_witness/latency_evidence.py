"""Bind incident detection latency to forensic telemetry event times.

The replay protocol stays in ``detection_latency``. This module does not invent
a clock. A duration is emitted only when both endpoints are ``source_stated``
times on evidence the audit holds. The original incident has no such pair, so
the result is an absence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from swarm_witness.detection_latency import TimestampError, _parse_exact
from swarm_witness.provenance import source_unavailable
from swarm_witness.telemetry import probe_held_source_gate

# Source ids from the forensic telemetry graph. Roles name the records; row
# counts and effect times are read from the executed bundle.
INCIDENT_UNAVAILABLE_SOURCES: tuple[tuple[str, str], ...] = (
    ("src-transcript-dump", "OpenAI transcript dump"),
    ("src-execution-log", "independent execution log"),
    ("src-board-dump", "Artifactory message-board dump"),
    ("src-hf-platform-logs", "Hugging Face platform logs"),
    ("src-hf-indicators", "redacted indicators"),
    ("src-launchpad-logs", "private launchpad logs"),
)
REPRODUCTION_SOURCE_IDS = (
    "src-lw-reproduction-post",
    "src-lw-reproduction-appendix",
)
REPRODUCTION_EVENT_IDS = ("lw-release", "lw-appendix")
REPRODUCTION_CLAIM = "tel_reproduction_record"
ORIGINAL_CLAIM = "tel_original_logs"
HELD_GATE_SOURCE = "src-metr-command"
UNAVAILABLE_GATE_SOURCE = "src-transcript-dump"
ABSENCE_REASON = "no_trustworthy_event_time_on_held_evidence"


def load_telemetry_bundle(root: Path) -> dict[str, Any]:
    """Execute the forensic telemetry qualification. Do not read a PR body."""
    path = root / "experiments" / "telemetry" / "qualify.py"
    spec = importlib.util.spec_from_file_location("telemetry_qualify_for_latency", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load telemetry qualification from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_bundle()


def trustworthy_event_time(
    event: dict[str, Any],
    source: dict[str, Any] | None,
    *,
    allow_synthetic: bool,
) -> str | None:
    """Return a source-stated instant the audit holds, or None.

    Ingest time, retrieval time, reconstructed time, and a clock on an
    unavailable source are not returned.
    """
    if source is None or source_unavailable(source):
        return None
    if source.get("locally_held") is not True:
        return None
    if source.get("access_level") != "public_bytes" or source.get("redaction") != "none":
        return None
    if event.get("synthetic") and not allow_synthetic:
        return None
    if event.get("time_basis") != "source_stated":
        return None
    value = event.get("event_time")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        _parse_exact(value.strip())
    except TimestampError:
        return None
    return value.strip()


def latency_from_held_events(
    start: dict[str, Any],
    end: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    *,
    claim_id: str,
    corpus_label: str,
) -> dict[str, Any]:
    """Subtract two held event times, or record an absence.

    A missing endpoint is not filled from ``ingest_time`` or from any other field.
    """
    absent = {
        "claim_id": claim_id,
        "corpus_label": corpus_label,
        "status": "absent",
        "seconds": None,
        "reason": ABSENCE_REASON,
    }
    allow_synthetic = corpus_label == "synthetic_control"
    start_time = trustworthy_event_time(
        start, sources.get(start.get("source_id")), allow_synthetic=allow_synthetic
    )
    end_time = trustworthy_event_time(
        end, sources.get(end.get("source_id")), allow_synthetic=allow_synthetic
    )
    if start_time is None or end_time is None:
        return absent
    seconds = int((_parse_exact(end_time) - _parse_exact(start_time)).total_seconds())
    if seconds < 0:
        return {**absent, "reason": "negative_interval"}
    return {
        "claim_id": claim_id,
        "corpus_label": corpus_label,
        "status": "published",
        "seconds": seconds,
        "reason": None,
        "start": start_time,
        "end": end_time,
    }


def incident_detection_latency(bundle: dict[str, Any]) -> dict[str, Any]:
    """Detection latency of the original incident from the executed telemetry graph.

    Unavailable originals contribute no rows and no effect times. They are not
    upgrade gates. No detector-alert time is held, so no incident duration is
    emitted.
    """
    graph = bundle["graph"]
    qualified = bundle["qualified"]
    claims = qualified["claims"]
    sources = {source["id"]: source for source in graph["source_records"]}
    events = list(bundle["events"])
    observed = list(graph["observed_events"])
    reproduction = claims[REPRODUCTION_CLAIM]
    original = claims[ORIGINAL_CLAIM]
    slots_by_source: dict[str, list[dict[str, Any]]] = {}
    for claim in graph["claims"]:
        for slot in claim["evidence_slots"]:
            slots_by_source.setdefault(slot["source_id"], []).append(slot)

    unavailable_records = [
        _unavailable_record(source_id, role, sources, events, observed, slots_by_source)
        for source_id, role in INCIDENT_UNAVAILABLE_SOURCES
    ]
    graph_claims = {claim["id"]: claim for claim in graph["claims"]}
    reproduction_record = _reproduction_record(
        reproduction, events, sources, graph_claims[REPRODUCTION_CLAIM]
    )
    incident_source_ids = set(REPRODUCTION_SOURCE_IDS) | {
        source_id for source_id, _role in INCIDENT_UNAVAILABLE_SOURCES
    }
    trustworthy = []
    for event in events:
        if event.get("source_id") not in incident_source_ids:
            continue
        instant = trustworthy_event_time(
            event, sources.get(event.get("source_id")), allow_synthetic=False
        )
        if instant is None:
            continue
        trustworthy.append(
            {
                "event_id": event["id"],
                "source_id": event["source_id"],
                "event_kind": event.get("event_kind"),
                "event_time": instant,
            }
        )
    effect_commit_at = next(
        (item["event_time"] for item in trustworthy if item["event_kind"] == "committed_effect"),
        None,
    )
    # Telemetry events have no detector-alert field. Do not promote another clock.
    detector_alert_at = None
    if trustworthy and detector_alert_at is None:
        reason = "detector_alert_time_not_held"
    else:
        reason = ABSENCE_REASON
    detection_claimed = bool(
        qualified.get("incident_detection_claimed")
        or reproduction.get("incident_detection_claimed")
        or original.get("incident_detection_claimed")
    )
    prevention_claimed = bool(
        qualified.get("incident_prevention_claimed")
        or reproduction.get("incident_prevention_claimed")
        or original.get("incident_prevention_claimed")
    )
    authenticity = bool(
        qualified.get("real_world_authenticity_certified")
        or reproduction.get("real_world_authenticity_certified")
        or original.get("real_world_authenticity_certified")
    )
    held_gate = _held_gate(graph, sources)
    unavailable_gate_rejected = _unavailable_gate_rejected(graph)
    record = {
        "claim_id": "incident_detection_latency",
        "corpus_label": "historical_replay",
        "status": "absent",
        "seconds": None,
        "reason": reason,
        "detector_alert_at": detector_alert_at,
        "effect_commit_at": effect_commit_at,
        "trustworthy_event_time_count": len(trustworthy),
        "trustworthy_event_times": trustworthy,
        "reproduction_record": reproduction_record,
        "original_logs": {
            "finding_label": original["finding_label"],
            "effect_status": original["effect_status"],
            "event_time": original["chronology"]["event_time"],
            "time_basis": original["chronology"]["time_basis"],
            "primary_upgrade_blocker": original["primary_upgrade_blocker"],
            "absence_of_sink_is_no_effect": original["absence_of_sink_is_no_effect"],
            "verified_event_count": len(original["verified_event_ids"]),
        },
        "unavailable_records": unavailable_records,
        "held_source_gate": held_gate,
        "unavailable_gate_rejected": unavailable_gate_rejected,
        "incident_detection_claimed": detection_claimed,
        "incident_prevention_claimed": prevention_claimed,
        "real_world_authenticity_certified": authenticity,
    }
    record["contract_errors"] = _contract_errors(record)
    record["metrics"] = _metrics(record)
    return record


def bind_incident_latency(score: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Attach the incident absence to a replay score. The score's protocol stays."""
    incident = incident_detection_latency(bundle)
    errors = [*score.get("errors", []), *incident["contract_errors"]]
    metrics = dict(score["metrics"])
    metrics.update(incident["metrics"])
    metrics["passed"] = not errors
    bound = dict(score)
    bound["errors"] = errors
    bound["metrics"] = metrics
    bound["incident_latency"] = incident
    return bound


def _unavailable_record(
    source_id: str,
    role: str,
    sources: dict[str, dict[str, Any]],
    events: list[dict[str, Any]],
    observed: list[dict[str, Any]],
    slots_by_source: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    source = sources.get(source_id)
    rows = [event for event in events if event.get("source_id") == source_id]
    graph_rows = [
        event
        for event in observed
        if source_id in (event.get("necessary_source_ids") or [])
    ]
    raw_times = [event.get("event_time") for event in (*rows, *graph_rows)]
    effect_times = [value for value in raw_times if value is not None]
    slots = slots_by_source.get(source_id, [])
    blocks = any(slot.get("blocks_upgrade") is True for slot in slots)
    return {
        "source_id": source_id,
        "role": role,
        "present": source is not None,
        "unavailable": source is not None and source_unavailable(source),
        "row_count": len(rows),
        "graph_event_count": len(graph_rows),
        "effect_time": effect_times[0] if effect_times else None,
        "blocks_upgrade": blocks,
        "upgrade_gate": blocks,
    }


def _reproduction_record(
    claim: dict[str, Any],
    events: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    graph_claim: dict[str, Any],
) -> dict[str, Any]:
    by_id = {event["id"]: event for event in events}
    rows = []
    for event_id in REPRODUCTION_EVENT_IDS:
        event = by_id[event_id]
        rows.append(
            {
                "event_id": event_id,
                "source_id": event["source_id"],
                "event_time": event.get("event_time"),
                "time_basis": event.get("time_basis"),
                "trustworthy_event_time": trustworthy_event_time(
                    event, sources.get(event.get("source_id")), allow_synthetic=False
                ),
            }
        )
    keys = {item["corroboration_key"] for item in claim["lineage"]}
    slotted = {slot["source_id"] for slot in graph_claim["evidence_slots"]}
    one_record = (
        claim["independent_observation_count"] == 1
        and len(keys) == 1
        and "ev-lw-appendix" in claim["duplicated_report_ids"]
        and set(REPRODUCTION_SOURCE_IDS) <= slotted
        and [row["source_id"] for row in rows] == list(REPRODUCTION_SOURCE_IDS)
        and all(not by_id[event_id].get("synthetic") for event_id in REPRODUCTION_EVENT_IDS)
    )
    bases = {row["time_basis"] for row in rows}
    times = {row["event_time"] for row in rows}
    return {
        "source_ids": list(REPRODUCTION_SOURCE_IDS),
        "independent_observation_count": claim["independent_observation_count"],
        "one_public_record": one_record,
        "effect_status": claim["effect_status"],
        "event_time": next(iter(times)) if len(times) == 1 else None,
        "time_basis": next(iter(bases)) if len(bases) == 1 else "mixed",
        "events": rows,
        "chronology_event_time": claim["chronology"]["event_time"],
        "chronology_time_basis": claim["chronology"]["time_basis"],
    }


def _held_gate(graph: dict[str, Any], sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source = sources.get(HELD_GATE_SOURCE)
    held = source is not None and not source_unavailable(source)
    if not held:
        return {
            "source_id": HELD_GATE_SOURCE,
            "held": False,
            "prevents_supported": False,
            "primary_upgrade_blocker": None,
            "finding_label": None,
            "conclusion_class": None,
        }
    probed = probe_held_source_gate(graph, REPRODUCTION_CLAIM, HELD_GATE_SOURCE)
    prevents = (
        probed["finding_label"] != "reproduced"
        and probed["conclusion_class"] != "supported"
        and probed["primary_upgrade_blocker"] == HELD_GATE_SOURCE
    )
    return {
        "source_id": HELD_GATE_SOURCE,
        "held": True,
        "prevents_supported": prevents,
        "primary_upgrade_blocker": probed["primary_upgrade_blocker"],
        "finding_label": probed["finding_label"],
        "conclusion_class": probed["conclusion_class"],
    }


def _unavailable_gate_rejected(graph: dict[str, Any]) -> bool:
    try:
        probe_held_source_gate(graph, REPRODUCTION_CLAIM, UNAVAILABLE_GATE_SOURCE)
    except ValueError as exc:
        return "cannot be an upgrade gate" in str(exc)
    return False


def _contract_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record["seconds"] is not None or record["status"] != "absent":
        errors.append("incident detection latency was emitted")
    reproduction = record["reproduction_record"]
    if not reproduction["one_public_record"]:
        errors.append("the LessWrong post and appendix are not one public record")
    if reproduction["independent_observation_count"] != 1:
        errors.append("reproduction independent observation count is not 1")
    if len(record["unavailable_records"]) != len(INCIDENT_UNAVAILABLE_SOURCES):
        errors.append("unavailable incident record list drifted")
    for row in record["unavailable_records"]:
        if not row["present"] or not row["unavailable"]:
            errors.append(f"{row['source_id']} is not an unavailable telemetry source")
        if row["row_count"] != 0 or row["graph_event_count"] != 0:
            errors.append(f"{row['source_id']} has ingested rows")
        if row["effect_time"] is not None:
            errors.append(f"{row['source_id']} has an effect time")
        if row["blocks_upgrade"] or row["upgrade_gate"]:
            errors.append(f"{row['source_id']} is an upgrade gate")
    if not record["held_source_gate"]["prevents_supported"]:
        errors.append("a blocks_upgrade slot on held evidence did not prevent supported")
    if not record["unavailable_gate_rejected"]:
        errors.append("an unavailable source was accepted as an upgrade gate")
    if record["incident_detection_claimed"] or record["incident_prevention_claimed"]:
        errors.append("incident detection or prevention was claimed")
    if record["real_world_authenticity_certified"]:
        errors.append("real-world authenticity was certified")
    return errors


def _metrics(record: dict[str, Any]) -> dict[str, Any]:
    rows = record["unavailable_records"]
    return {
        "incident_latency_status": record["status"],
        "incident_detection_latency_emitted": record["seconds"] is not None,
        "incident_detection_latency_seconds": record["seconds"],
        "incident_trustworthy_event_time_count": record["trustworthy_event_time_count"],
        "reproduction_one_public_record": record["reproduction_record"]["one_public_record"],
        "reproduction_independent_observation_count": record["reproduction_record"][
            "independent_observation_count"
        ],
        "unavailable_record_count": len(rows),
        "unavailable_row_count": sum(row["row_count"] for row in rows),
        "unavailable_effect_time_count": sum(row["effect_time"] is not None for row in rows),
        "unavailable_records_are_gates": any(
            row["blocks_upgrade"] or row["upgrade_gate"] for row in rows
        ),
        "held_source_gate_prevents_supported": record["held_source_gate"]["prevents_supported"],
        "unavailable_gate_rejected": record["unavailable_gate_rejected"],
        "incident_detection_claimed": record["incident_detection_claimed"],
        "incident_prevention_claimed": record["incident_prevention_claimed"],
        "real_world_authenticity_certified": record["real_world_authenticity_certified"],
    }
