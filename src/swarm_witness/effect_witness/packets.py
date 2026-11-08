"""Evidence packets over one execution. A packet is not another run."""

from __future__ import annotations

from typing import Any

from swarm_witness.effect_witness.histories import PACKET_CONDITIONS, operation_ids
from swarm_witness.effect_witness.ids import ident, logical_iso
from swarm_witness.effect_witness.records import (
    actor_row,
    coverage_row,
    parse_body,
    restamp,
    revocation_row,
    sink_row,
    withheld_sink_row,
    write_jsonl,
)

PACKET_MISBIND = {
    "actor_id": ident("actor", "gamma"),
    "task_id": ident("task", "packet-misbind"),
    "epoch_id": ident("epoch", "9"),
    "object_scope": ident("object", "packet-misbind"),
}


def sink_record_id(event_id: str) -> str:
    prefix = "aew-v1-event-"
    if not event_id.startswith(prefix):
        raise ValueError(event_id)
    return "aew-v1-rec-sink-" + event_id[len(prefix) :]


def _parent_id(commit: dict[str, Any], actor_records: list[dict[str, Any]]) -> str | None:
    matches = [row for row in actor_records if row.get("call_id") == commit["call_id"]]
    if not matches:
        return None
    matches.sort(key=lambda row: (row["record_id"].endswith("-copy"), len(row["record_id"]), row["record_id"]))
    return matches[0]["record_id"]


def service_rows_for(
    history: dict[str, Any],
    actor_records: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    revocations: list[dict[str, Any]],
    *,
    row_count: int,
) -> list[dict[str, Any]]:
    """Application readback for one history. Built from observer rows."""
    group = f"aew-v1-sink-{history['history_id']}"
    actor_time: dict[str, int] = {}
    for record in actor_records:
        fields = parse_body(record["public_bytes"])
        actor_time.setdefault(fields["call_id"], int(fields["logical_time"]))
    rows = []
    for commit in commits:
        if commit["run_id"] != history["run_id"]:
            continue
        stamped = sink_row(
            commit,
            record_id=sink_record_id(commit["event_id"]),
            group=group,
            parent_id=_parent_id(commit, actor_records),
        )
        # Share the actor's stated time so a link is not rejected as a clock skew.
        # The commit row's own logical_time stays in the bytes.
        rows.append(restamp(stamped, actor_time.get(commit["call_id"], int(commit["logical_time"]))))
    for revocation in revocations:
        if revocation["run_id"] != history["run_id"]:
            continue
        rows.append(
            revocation_row(
                revocation,
                record_id=ident("record", f"revocation-{history['slug']}"),
            )
        )
    rows.append(
        coverage_row(
            {
                "history_id": history["history_id"],
                "run_id": history["run_id"],
                "operations": operation_ids(history),
                "interval_start": logical_iso(history["interval_start"]),
                "interval_end": logical_iso(history["interval_end"]),
                "row_count": row_count,
            },
            record_id=ident("record", f"coverage-{history['slug']}"),
        )
    )
    return rows


def _irrelevant_row() -> dict[str, Any]:
    fields = {
        "history_id": ident("history", "irrelevant"),
        "run_id": ident("run", "irrelevant"),
        "operation_id": ident("operation", "irrelevant"),
        "event_id": ident("event", "irrelevant"),
        "call_id": ident("call", "irrelevant"),
        "actor_id": ident("actor", "gamma"),
        "task_id": ident("task", "irrelevant"),
        "grant_id": None,
        "epoch_id": ident("epoch", "1"),
        "channel": "remote_url",
        "subject_class": "approved_remote",
        "operation": "note_weather",
        "object_scope": ident("object", "irrelevant"),
        "decision": "allow",
        "claimed_result": "allowed",
        "receipt_id": None,
        "local_grant_view": "absent",
        "logical_time": 50,
        "attempted": False,
    }
    return actor_row(
        fields,
        record_id=ident("record", "actor-irrelevant"),
        group="aew-v1-actor-irrelevant",
    )


def _added_duplicate(record: dict[str, Any]) -> dict[str, Any]:
    """Same bytes, new record id. This is an evidence condition, not a new execution."""
    fields = parse_body(record["public_bytes"])
    rebuilt = {
        "history_id": fields["history_id"],
        "run_id": fields["run_id"],
        "operation_id": fields["operation_id"],
        "event_id": fields["event_id"],
        "call_id": fields["call_id"],
        "actor_id": fields["actor_id"],
        "task_id": fields["task_id"],
        "grant_id": None if fields["grant_id"] == "none" else fields["grant_id"],
        "epoch_id": fields["epoch_id"],
        "channel": fields["channel"],
        "subject_class": fields["subject_class"],
        "operation": fields["operation"],
        "object_scope": fields["object_scope"],
        "decision": fields["decision"],
        "claimed_result": fields["claimed_result"],
        "receipt_id": None if fields["receipt_id"] == "none" else fields["receipt_id"],
        "local_grant_view": fields["local_grant_view"],
        "logical_time": int(fields["logical_time"]),
        "attempted": fields["attempted"] == "true",
    }
    return actor_row(
        rebuilt,
        record_id=record["record_id"] + "-added",
        group=record["independence_group"],
        body=record["public_bytes"],
    )


def _misbind_actor(record: dict[str, Any]) -> dict[str, Any]:
    fields = parse_body(record["public_bytes"])
    rewritten = {
        "history_id": fields["history_id"],
        "run_id": fields["run_id"],
        "operation_id": fields["operation_id"],
        "event_id": fields["event_id"] + "-misbound",
        "call_id": fields["call_id"],
        "actor_id": PACKET_MISBIND["actor_id"],
        "task_id": PACKET_MISBIND["task_id"],
        "grant_id": None if fields["grant_id"] == "none" else fields["grant_id"],
        "epoch_id": PACKET_MISBIND["epoch_id"],
        "channel": fields["channel"],
        "subject_class": fields["subject_class"],
        "operation": fields["operation"],
        "object_scope": PACKET_MISBIND["object_scope"],
        "decision": fields["decision"],
        "claimed_result": fields["claimed_result"],
        "receipt_id": None if fields["receipt_id"] == "none" else fields["receipt_id"],
        "local_grant_view": fields["local_grant_view"],
        "logical_time": int(fields["logical_time"]),
        "attempted": fields["attempted"] == "true",
    }
    return actor_row(
        rewritten,
        record_id=record["record_id"] + "-misbound",
        group=record["independence_group"],
    )


def build_packets(
    history: dict[str, Any],
    actor_records: list[dict[str, Any]],
    service_rows: list[dict[str, Any]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Four views of the same history. None of these re-executes the worker."""
    commits = [row for row in service_rows if row["surface"] == "committed_effect"]
    packets = {
        "actor_only": {"actor": list(actor_records), "service": None},
        "duplicate_irrelevant": {
            "actor": [
                *actor_records,
                *[_added_duplicate(row) for row in actor_records[:1]],
                _irrelevant_row(),
            ],
            "service": list(service_rows),
        },
        "discriminating_readback": {
            "actor": list(actor_records),
            "service": list(service_rows),
        },
        "withheld_misbound": {
            "actor": [_misbind_actor(row) for row in actor_records],
            "service": [
                withheld_sink_row(
                    {
                        "call_id": row["call_id"],
                        "operation": row["action"],
                    },
                    record_id=row["record_id"] + "-withheld",
                    group=row["independence_group"],
                )
                for row in commits
            ],
        },
    }
    if set(packets) != set(PACKET_CONDITIONS):
        raise RuntimeError("packet conditions drifted")
    return packets


def write_packet(directory, packet: dict[str, list[dict[str, Any]] | None]) -> None:
    write_jsonl(directory / "actor_records.jsonl", packet["actor"] or [])
    if packet["service"] is not None:
        write_jsonl(directory / "service_records.jsonl", packet["service"])
