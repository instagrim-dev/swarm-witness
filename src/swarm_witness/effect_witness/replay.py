"""Cold replay of the twelve application histories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from swarm_witness.effect_witness.boundary import (
    DISCLAIMER,
    HARNESS_WRITE_TOKEN,
    TRUST_BOUNDARY,
    TRUTH_SENTINEL,
    WITNESS_VERSION,
)
from swarm_witness.effect_witness.histories import (
    FAMILIES,
    HISTORIES,
    PACKET_CONDITIONS,
    operation_ids,
    witness_history,
)
from swarm_witness.effect_witness.observer import (
    coverage_for,
    read_commits,
    read_commits_cold,
    read_revocations,
)
from swarm_witness.effect_witness.packets import build_packets, service_rows_for, write_packet
from swarm_witness.effect_witness.qualify import (
    application_property,
    build_witness,
    evaluate_packet,
)
from swarm_witness.effect_witness.records import write_jsonl
from swarm_witness.effect_witness.sink import EffectSink
from swarm_witness.effect_witness.worker import check_expect, execute_history


def _json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sql(commits: list[dict[str, Any]], revocations: list[dict[str, Any]]) -> str:
    lines = [
        "-- application-effect-witness-v1 retained sink",
        "-- " + TRUST_BOUNDARY,
        "BEGIN;",
        "CREATE TABLE commits (",
        "  event_id TEXT PRIMARY KEY,",
        "  operation_id TEXT NOT NULL,",
        "  run_id TEXT NOT NULL,",
        "  history_id TEXT NOT NULL,",
        "  actor_id TEXT NOT NULL,",
        "  task_id TEXT NOT NULL,",
        "  grant_id TEXT,",
        "  epoch_id TEXT NOT NULL,",
        "  call_id TEXT NOT NULL,",
        "  channel TEXT NOT NULL,",
        "  subject_class TEXT NOT NULL,",
        "  operation TEXT NOT NULL,",
        "  object_scope TEXT NOT NULL,",
        "  logical_time INTEGER NOT NULL",
        ");",
        "CREATE TABLE revocations (",
        "  revocation_id TEXT PRIMARY KEY,",
        "  grant_id TEXT NOT NULL,",
        "  run_id TEXT NOT NULL,",
        "  history_id TEXT NOT NULL,",
        "  policy TEXT NOT NULL,",
        "  logical_time INTEGER NOT NULL",
        ");",
    ]
    for row in commits:
        grant = "NULL" if row.get("grant_id") is None else "'" + row["grant_id"] + "'"
        values = [
            _quote(row["event_id"]),
            _quote(row["operation_id"]),
            _quote(row["run_id"]),
            _quote(row["history_id"]),
            _quote(row["actor_id"]),
            _quote(row["task_id"]),
            grant,
            _quote(row["epoch_id"]),
            _quote(row["call_id"]),
            _quote(row["channel"]),
            _quote(row["subject_class"]),
            _quote(row["operation"]),
            _quote(row["object_scope"]),
            str(int(row["logical_time"])),
        ]
        lines.append("INSERT INTO commits VALUES (" + ", ".join(values) + ");")
    for row in revocations:
        values = [
            _quote(row["revocation_id"]),
            _quote(row["grant_id"]),
            _quote(row["run_id"]),
            _quote(row["history_id"]),
            _quote(row["policy"]),
            str(int(row["logical_time"])),
        ]
        lines.append("INSERT INTO revocations VALUES (" + ", ".join(values) + ");")
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def replay(output_dir: Path, *, token: str = HARNESS_WRITE_TOKEN) -> dict[str, Any]:
    """Execute every frozen history once, then derive evidence packets."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "work" / "effects.sqlite"
    sink = EffectSink.create(db_path, token)
    traces = []
    try:
        for history in HISTORIES:
            trace = execute_history(sink, token, history)
            commits = [row for row in read_commits(db_path) if row["run_id"] == history["run_id"]]
            check_expect(history, trace, commits)
            traces.append(trace)
    finally:
        sink.close()

    cold = read_commits_cold(db_path)
    opened = read_commits(db_path)
    if cold != opened:
        raise RuntimeError("cold reopen did not match the live readback")
    revocations = read_revocations(db_path)
    by_trace = {trace["history_id"]: trace for trace in traces}

    actor_rows: list[dict[str, Any]] = []
    service_rows: list[dict[str, Any]] = []
    packet_results: dict[str, dict[str, Any]] = {}
    properties = []
    for history in HISTORIES:
        trace = by_trace[history["history_id"]]
        covered = coverage_for(
            db_path,
            run_id=history["run_id"],
            history_id=history["history_id"],
            operations=operation_ids(history),
            interval_start=history["interval_start"],
            interval_end=history["interval_end"],
        )
        service = service_rows_for(
            history,
            trace["actor_records"],
            cold,
            revocations,
            row_count=covered["row_count"],
        )
        actor_rows.extend(trace["actor_records"])
        service_rows.extend(service)
        packets = build_packets(history, trace["actor_records"], service)
        packet_results[history["history_id"]] = {}
        for condition in PACKET_CONDITIONS:
            directory = output_dir / "packets" / history["history_id"] / condition
            write_packet(directory, packets[condition])
            packet_results[history["history_id"]][condition] = evaluate_packet(directory, history)
        properties.append(
            application_property(
                history,
                trace["decisions"],
                cold,
                revocations,
            )
        )

    witness = build_witness(
        witness_history(),
        by_trace[witness_history()["history_id"]]["actor_records"],
        packet_results[witness_history()["history_id"]],
    )
    executions = len(HISTORIES)
    conditions = executions * len(PACKET_CONDITIONS)
    if conditions != 48:
        raise RuntimeError("evidence conditions drifted")
    absence = _absence_report(packet_results)
    summary = {
        "schema_version": WITNESS_VERSION,
        "execution_count": executions,
        "evidence_condition_count": conditions,
        "packets_are_independent_executions": False,
        "families": list(FAMILIES),
        "history_ids": [history["history_id"] for history in HISTORIES],
        "trust_boundary": TRUST_BOUNDARY,
        "witness": witness,
        "audit_conformance_passed": True,
        "audit_conformance_is_the_witness": False,
        "cold_reopen_matches": True,
        "commit_count": len(cold),
        "revocation_count": len(revocations),
        "absence": absence,
        "properties": properties,
        **DISCLAIMER,
    }
    truth = {
        "schema_version": WITNESS_VERSION,
        "role": "fixed harness truth for scoring",
        "hidden_injection_sentinel": TRUTH_SENTINEL,
        "histories": [
            {
                "history_id": history["history_id"],
                "family": history["family"],
                "role": history["role"],
                "revocation_policy": history["revocation_policy"],
                "expect": history["expect"],
                "decisions": by_trace[history["history_id"]]["decisions"],
                "commits": [row for row in cold if row["run_id"] == history["run_id"]],
            }
            for history in HISTORIES
        ],
        **DISCLAIMER,
    }
    packet_blob = json.dumps(packet_results, sort_keys=True)
    if TRUTH_SENTINEL in packet_blob or TRUTH_SENTINEL in json.dumps(summary):
        raise RuntimeError("the hidden truth sentinel leaked into packet results")
    observations = output_dir / "observations"
    write_jsonl(observations / "actor_records.jsonl", actor_rows)
    write_jsonl(observations / "service_records.jsonl", service_rows)
    _json(output_dir / "readback.json", {"commits": cold, "revocations": revocations})
    (output_dir / "sink" / "commits.sql").parent.mkdir(parents=True, exist_ok=True)
    (output_dir / "sink" / "commits.sql").write_text(_sql(cold, revocations), encoding="utf-8")
    _json(
        output_dir / "manifest.json",
        {
            "schema_version": WITNESS_VERSION,
            "trust_boundary": TRUST_BOUNDARY,
            "families": list(FAMILIES),
            "packet_conditions": list(PACKET_CONDITIONS),
            "histories": [
                {
                    "history_id": history["history_id"],
                    "family": history["family"],
                    "role": history["role"],
                    "revocation_policy": history["revocation_policy"],
                    "run_id": history["run_id"],
                    "expect": history["expect"],
                    "steps": history["steps"],
                }
                for history in HISTORIES
            ],
            **DISCLAIMER,
        },
    )
    _json(output_dir / "witness.json", witness)
    _json(output_dir / "summary.json", summary)
    _json(output_dir / "harness_truth" / "truth.json", truth)
    _json(output_dir / "qualification" / "packets.json", packet_results)
    _json(output_dir / "qualification" / "absence.json", absence)
    return summary


def _absence_report(packet_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    revoked = "aew-v1-h-authority-revoked-inflight"
    discriminating = packet_results[revoked]["discriminating_readback"]
    actor_only = packet_results[revoked]["actor_only"]
    return {
        "history_id": revoked,
        "covered_absence_is_no_effect": discriminating["absence_of_sink_is_no_effect"],
        "covered_uncovered_operation_is_no_effect": discriminating[
            "uncovered_absence_is_no_effect"
        ],
        "actor_only_absence_is_no_effect": actor_only["absence_of_sink_is_no_effect"],
        "rule": (
            "Absence is evidence of no effect only when the observer coverage "
            "names that operation and interval."
        ),
    }
