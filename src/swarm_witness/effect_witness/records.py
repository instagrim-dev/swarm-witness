"""Canonical actor and sink bytes. The sink text is not a decision flag."""

from __future__ import annotations

import json
from typing import Any

from swarm_witness.effect_witness.boundary import ADAPTER_SALT, COLLECTION_BOUNDARY
from swarm_witness.effect_witness.ids import logical_iso

PUBLISHER_ACTOR = "aew-v1-actor"
PUBLISHER_SINK = "aew-v1-harness"


def actor_body(fields: dict[str, Any]) -> str:
    """Actor transcript body. It does not contain a sink commit flag."""
    ordered = (
        ("history_id", fields["history_id"]),
        ("run_id", fields["run_id"]),
        ("operation_id", fields["operation_id"]),
        ("event_id", fields["event_id"]),
        ("call_id", fields["call_id"]),
        ("actor_id", fields["actor_id"]),
        ("task_id", fields["task_id"]),
        ("grant_id", fields.get("grant_id") or "none"),
        ("epoch_id", fields["epoch_id"]),
        ("channel", fields["channel"]),
        ("subject_class", fields["subject_class"]),
        ("operation", fields["operation"]),
        ("object_scope", fields["object_scope"]),
        ("decision", fields["decision"]),
        ("claimed_result", fields["claimed_result"]),
        ("attempted", "true" if fields["attempted"] else "false"),
        ("receipt_id", fields.get("receipt_id") or "none"),
        ("local_grant_view", fields["local_grant_view"]),
        ("logical_time", str(fields["logical_time"])),
    )
    lines = ["aew-v1 actor record", "record_class=synthetic_control"]
    lines.extend(f"{key}={value}" for key, value in ordered)
    return "\n".join(lines) + "\n"


def sink_body(row: dict[str, Any]) -> str:
    """Observer text for one committed row. No decision and no allow flag."""
    ordered = (
        ("history_id", row["history_id"]),
        ("run_id", row["run_id"]),
        ("operation_id", row["operation_id"]),
        ("event_id", row["event_id"]),
        ("call_id", row["call_id"]),
        ("actor_id", row["actor_id"]),
        ("task_id", row["task_id"]),
        ("grant_id", row.get("grant_id") or "none"),
        ("epoch_id", row["epoch_id"]),
        ("channel", row["channel"]),
        ("subject_class", row["subject_class"]),
        ("operation", row["operation"]),
        ("object_scope", row["object_scope"]),
        ("readback", "commit_row"),
        ("logical_time", str(row["logical_time"])),
    )
    lines = ["aew-v1 sink commit", "record_class=synthetic_control"]
    lines.extend(f"{key}={value}" for key, value in ordered)
    return "\n".join(lines) + "\n"


def coverage_body(
    *,
    history_id: str,
    run_id: str,
    operations: list[str],
    interval_start: str,
    interval_end: str,
    row_count: int,
) -> str:
    lines = [
        "aew-v1 observer coverage",
        "record_class=synthetic_control",
        f"history_id={history_id}",
        f"run_id={run_id}",
        "operations=" + ",".join(operations),
        f"interval_start={interval_start}",
        f"interval_end={interval_end}",
        f"row_count={row_count}",
    ]
    return "\n".join(lines) + "\n"


def revocation_body(row: dict[str, Any]) -> str:
    lines = [
        "aew-v1 grant revocation",
        "record_class=synthetic_control",
        f"history_id={row['history_id']}",
        f"run_id={row['run_id']}",
        f"revocation_id={row['revocation_id']}",
        f"grant_id={row['grant_id']}",
        f"policy={row['policy']}",
        f"logical_time={row['logical_time']}",
    ]
    return "\n".join(lines) + "\n"


def parse_body(text: str) -> dict[str, str]:
    lines = text.strip().splitlines()
    if not lines:
        raise ValueError("empty record body")
    fields = {"header": lines[0]}
    for line in lines[1:]:
        if "=" not in line:
            raise ValueError(f"record line has no key: {line!r}")
        key, value = line.split("=", 1)
        fields[key] = value
    return fields


def _row(
    *,
    record_id: str,
    surface: str,
    publisher: str,
    group: str,
    body: str | None,
    call_id: str | None,
    actor: str | None,
    action: str | None,
    result: str | None,
    object_scope: str | None,
    logical_time: int | None,
    parent_id: str | None = None,
    withheld: bool = False,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "record_id": record_id,
        "surface": surface,
        "origin": "synthetic_control",
        "synthetic": True,
        "independence_group": group,
        "publisher": publisher,
        "collection_boundary": COLLECTION_BOUNDARY,
        "actor_binding": "bound" if actor else "not_applicable",
        "binding_basis": "source_stated_principal" if actor else "not_provided",
        "polarity": "supports" if surface == "committed_effect" else "reports",
        "authenticity": "not_checked",
        "canonical_url": f"fixture://aew-v1/{surface}/{record_id}",
        "source_id": f"src-{record_id}",
        "locator": f"{ADAPTER_SALT}#{record_id}",
    }
    if actor:
        row["actor"] = actor
    if call_id:
        row["call_id"] = call_id
    if action:
        row["action"] = action
    if result:
        row["result"] = result
    if object_scope:
        row["object"] = object_scope
    if parent_id:
        row["parent_id"] = parent_id
    if withheld or body is None:
        row["access_level"] = "withheld"
        row["redaction"] = "withheld_original"
        row["locally_held"] = False
        row["custody"] = "unknown"
        row["time_basis"] = "missing"
    else:
        row["raw"] = body
        row["public_bytes"] = body
        row["access_level"] = "public_bytes"
        row["redaction"] = "none"
        row["locally_held"] = True
        row["custody"] = "intact"
        if logical_time is None:
            row["time_basis"] = "missing"
        else:
            row["event_time"] = logical_iso(logical_time)
            row["time_basis"] = "source_stated"
    return row


def actor_row(fields: dict[str, Any], *, record_id: str, group: str, body: str | None = None) -> dict[str, Any]:
    text = body if body is not None else actor_body(fields)
    return _row(
        record_id=record_id,
        surface="requested_command",
        publisher=PUBLISHER_ACTOR,
        group=group,
        body=text,
        call_id=fields["call_id"],
        actor=fields["actor_id"],
        action=fields["operation"],
        result=fields["claimed_result"],
        object_scope=fields["object_scope"],
        logical_time=int(fields["logical_time"]),
    )


def sink_row(commit: dict[str, Any], *, record_id: str, group: str, parent_id: str | None) -> dict[str, Any]:
    return _row(
        record_id=record_id,
        surface="committed_effect",
        publisher=PUBLISHER_SINK,
        group=group,
        body=sink_body(commit),
        call_id=commit["call_id"],
        actor=commit["actor_id"],
        action=commit["operation"],
        result="commit_row",
        object_scope=commit["object_scope"],
        logical_time=int(commit["logical_time"]),
        parent_id=parent_id,
    )


def coverage_row(fields: dict[str, Any], *, record_id: str) -> dict[str, Any]:
    body = coverage_body(
        history_id=fields["history_id"],
        run_id=fields["run_id"],
        operations=list(fields["operations"]),
        interval_start=fields["interval_start"],
        interval_end=fields["interval_end"],
        row_count=int(fields["row_count"]),
    )
    return _row(
        record_id=record_id,
        surface="service_log",
        publisher=PUBLISHER_SINK,
        group=f"aew-v1-coverage-{fields['history_id']}",
        body=body,
        call_id=None,
        actor=None,
        action="coverage_scan",
        result=str(fields["row_count"]),
        object_scope=None,
        logical_time=None,
    )


def revocation_row(rev: dict[str, Any], *, record_id: str) -> dict[str, Any]:
    return _row(
        record_id=record_id,
        surface="service_log",
        publisher=PUBLISHER_SINK,
        group=f"aew-v1-revocation-{rev['history_id']}",
        body=revocation_body(rev),
        call_id=None,
        actor=None,
        action="grant_revoked",
        result=rev["policy"],
        object_scope=None,
        logical_time=int(rev["logical_time"]),
    )


def withheld_sink_row(commit: dict[str, Any], *, record_id: str, group: str) -> dict[str, Any]:
    """Same call id, no bytes. Withholding is not a commit observation."""
    return _row(
        record_id=record_id,
        surface="committed_effect",
        publisher=PUBLISHER_SINK,
        group=group,
        body=None,
        call_id=commit["call_id"],
        actor=None,
        action=commit["operation"],
        result=None,
        object_scope=None,
        logical_time=None,
        withheld=True,
    )


def restamp(record: dict[str, Any], logical: int) -> dict[str, Any]:
    """Set the adapter clock without changing the record bytes or the commit time."""
    if record.get("public_bytes") in (None, ""):
        return dict(record)
    updated = dict(record)
    updated["event_time"] = logical_iso(logical)
    updated["time_basis"] = "source_stated"
    return updated


def write_jsonl(path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, sort_keys=True, separators=(",", ":"))
        for row in sorted(rows, key=lambda item: item["record_id"])
    ]
    text = ("\n".join(lines) + "\n") if lines else ""
    path.write_text(text, encoding="utf-8")
