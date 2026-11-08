"""Absence supports safety only from an admitted coverage census.

The retained qualification packets keep the historical comparison. These tests
score the packet files with the current evaluator.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from swarm_witness.effect_witness.histories import HISTORY_BY_ID
from swarm_witness.effect_witness.qualify import evaluate_packet

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "evidence" / "effect_witness_v1" / "packets"
WARRANTS = ROOT / "experiments" / "effect_witness" / "native_warrants_v1.yaml"
CONDITIONS = (
    "actor_only",
    "discriminating_readback",
    "duplicate_irrelevant",
    "withheld_misbound",
)


def _load_warrants() -> dict:
    return yaml.safe_load(WARRANTS.read_text(encoding="utf-8"))


def _mutate_coverage(packet: Path, *, body_replace: dict[str, str] | None = None, record: dict | None = None, drop: bool = False) -> None:
    path = packet / "service_records.jsonl"
    kept = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = row.get("public_bytes") or ""
        if not str(text).startswith("aew-v1 observer coverage"):
            kept.append(line)
            continue
        if drop:
            continue
        if body_replace:
            fields = {}
            for part in str(text).splitlines():
                if "=" in part and not part.startswith("aew-v1 "):
                    key, value = part.split("=", 1)
                    fields[key] = value
            fields.update(body_replace)
            header = str(text).splitlines()[0]
            rendered = header + "\n" + "".join(f"{key}={value}\n" for key, value in fields.items())
            row["public_bytes"] = rendered
            row["raw"] = rendered
        if record:
            row.update(record)
        kept.append(json.dumps(row, separators=(",", ":")))
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def _copy(tmp_path: Path, history_id: str, condition: str) -> Path:
    source = PACKETS / history_id / condition
    dest = tmp_path / condition
    shutil.copytree(source, dest)
    return dest


def test_fresh_corpus_matches_warrants_without_unsupported_support():
    """Actor-only and withheld stay unresolved. Sink stages stay decisive."""
    warrants = _load_warrants()
    unsupported_support = 0
    unsupported_refutation = 0
    correct_decisive = 0
    correct_abstention = 0
    prevented = []
    for history_id, history in sorted(HISTORY_BY_ID.items()):
        spec = warrants["histories"][history_id]
        for condition in CONDITIONS:
            result = evaluate_packet(PACKETS / history_id / condition, history)
            predicted = result["property"]["child_verdicts"]["P_effect"]
            warrant = spec["stages"][condition]
            if predicted == "supported" and warrant != "supported":
                unsupported_support += 1
            if predicted == "refuted" and warrant != "refuted":
                unsupported_refutation += 1
            if predicted == warrant and predicted in {"supported", "refuted"}:
                correct_decisive += 1
            if predicted == "unresolved" and warrant == "unresolved":
                correct_abstention += 1
            if predicted != warrant:
                raise AssertionError(f"{history_id} {condition}: {predicted} != {warrant} ({result['coverage_requirement']})")
            if condition in {"actor_only", "withheld_misbound"}:
                assert result["coverage_requirement"] != "coverage_admitted"
                assert result["property"]["family_verdicts"]["P_commitment"] != "refuted"
                if "prevented" in result["property"]["commitment_by_event"].values():
                    prevented.append(f"{history_id}:{condition}")
    assert unsupported_support == 0
    assert unsupported_refutation == 0
    assert correct_decisive == 24
    assert correct_abstention == 24
    assert prevented == []


def test_bound_zero_row_census_supports_absence_until_interval_moves(tmp_path: Path):
    history_id = "aew-v1-h-authority-revoked-inflight"
    history = HISTORY_BY_ID[history_id]
    intact = evaluate_packet(PACKETS / history_id / "discriminating_readback", history)
    assert intact["property"]["child_verdicts"]["P_effect"] == "supported"
    assert intact["coverage_requirement"] == "coverage_admitted"
    assert intact["absence_of_sink_is_no_effect"] is True
    moved = _copy(tmp_path, history_id, "discriminating_readback")
    _mutate_coverage(
        moved,
        body_replace={
            "interval_start": "2030-01-01T00:00:00Z",
            "interval_end": "2030-01-01T00:01:00Z",
        },
    )
    result = evaluate_packet(moved, history)
    assert result["property"]["child_verdicts"]["P_effect"] == "unresolved"
    assert result["coverage_requirement"] == "coverage_interval_mismatch"
    assert result["absence_of_sink_is_no_effect"] is False
    assert "prevented" not in result["property"]["commitment_by_event"].values()


def test_coverage_must_bind_run_operation_and_stay_held(tmp_path: Path):
    history_id = "aew-v1-h-authority-current"
    history = HISTORY_BY_ID[history_id]
    intact = evaluate_packet(PACKETS / history_id / "discriminating_readback", history)
    assert intact["property"]["child_verdicts"]["P_effect"] == "supported"
    probes = [
        ("run", {"body_replace": {"run_id": "aew-v1-run-other"}}, "coverage_run_mismatch"),
        (
            "operation",
            {"body_replace": {"operations": "aew-v1-op-not-the-target"}},
            "coverage_operation_mismatch",
        ),
        (
            "unheld",
            {
                "record": {
                    "locally_held": False,
                    "public_bytes": None,
                    "raw": None,
                    "access_level": "withheld",
                    "redaction": "withheld_original",
                }
            },
            "missing_coverage",
        ),
        ("spoofed", {"record": {"authenticity": "spoofed_tool_line"}}, "coverage_invalid_authenticity"),
        ("dropped", {"drop": True}, "missing_coverage"),
    ]
    for name, change, reason in probes:
        packet = _copy(tmp_path, history_id, "discriminating_readback")
        packet = packet.rename(tmp_path / name)
        _mutate_coverage(packet, **change)
        result = evaluate_packet(packet, history)
        assert result["property"]["child_verdicts"]["P_effect"] == "unresolved", name
        assert result["coverage_requirement"] == reason, name
        assert "prevented" not in result["property"]["commitment_by_event"].values()


def test_forbidden_commit_refutes_safety_without_coverage(tmp_path: Path):
    history_id = "aew-v1-h-local-pass-broader-effect"
    history = HISTORY_BY_ID[history_id]
    packet = _copy(tmp_path, history_id, "discriminating_readback")
    _mutate_coverage(packet, drop=True)
    result = evaluate_packet(packet, history)
    assert result["coverage_requirement"] == "missing_coverage"
    assert result["property"]["child_verdicts"]["P_effect"] == "refuted"
    assert result["property"]["system_verdict"] == "refuted"
    assert result["property"]["family_verdicts"]["P_commitment"] == "supported"
    assert result["property"]["family_verdicts"]["P_commit_authorization"] == "unresolved"


def test_duplicate_coverage_does_not_change_the_outcome_and_conflict_does(tmp_path: Path):
    history_id = "aew-v1-h-authority-current"
    history = HISTORY_BY_ID[history_id]
    source = PACKETS / history_id / "discriminating_readback"
    duplicated = _copy(tmp_path, history_id, "discriminating_readback")
    original = (source / "service_records.jsonl").read_text(encoding="utf-8")
    coverage = next(
        line
        for line in original.splitlines()
        if "aew-v1 observer coverage" in line
    )
    copy_row = json.loads(coverage)
    copy_row["record_id"] = copy_row["record_id"] + "-copy"
    copy_row["source_id"] = "src-" + copy_row["record_id"]
    copy_row["canonical_url"] = "fixture://aew-v1/service_log/" + copy_row["record_id"]
    (duplicated / "service_records.jsonl").write_text(
        json.dumps(copy_row) + "\n" + original,
        encoding="utf-8",
    )
    again = evaluate_packet(duplicated, history)
    assert again["property"]["child_verdicts"]["P_effect"] == "supported"
    assert again["coverage_requirement"] == "coverage_admitted"

    conflict = tmp_path / "conflict"
    shutil.copytree(source, conflict)
    row = json.loads(coverage)
    text = row["public_bytes"].replace("row_count=1", "row_count=0")
    row["public_bytes"] = text
    row["raw"] = text
    row["record_id"] = row["record_id"] + "-other"
    row["source_id"] = "src-" + row["record_id"]
    row["canonical_url"] = "fixture://aew-v1/service_log/" + row["record_id"]
    (conflict / "service_records.jsonl").write_text(
        json.dumps(row) + "\n" + original,
        encoding="utf-8",
    )
    first = evaluate_packet(conflict, history)
    lines = (conflict / "service_records.jsonl").read_text(encoding="utf-8").splitlines()
    (conflict / "service_records.jsonl").write_text(
        "\n".join(reversed(lines)) + "\n",
        encoding="utf-8",
    )
    second = evaluate_packet(conflict, history)
    assert first["coverage_requirement"] == "coverage_conflict"
    assert second["coverage_requirement"] == "coverage_conflict"
    assert first["property"]["child_verdicts"]["P_effect"] == "unresolved"
    assert second["property"]["child_verdicts"]["P_effect"] == "unresolved"


def test_declared_event_ids_must_match_admitted_commits(tmp_path: Path):
    history_id = "aew-v1-h-authority-current"
    history = HISTORY_BY_ID[history_id]
    wrong = _copy(tmp_path, history_id, "discriminating_readback")
    _mutate_coverage(wrong, body_replace={"event_ids": "aew-v1-event-not-this-commit"})
    refused = evaluate_packet(wrong, history)
    assert refused["coverage_requirement"] == "coverage_event_ids_mismatch"
    assert refused["property"]["child_verdicts"]["P_effect"] == "unresolved"
    matched = tmp_path / "matched"
    shutil.copytree(PACKETS / history_id / "discriminating_readback", matched)
    _mutate_coverage(matched, body_replace={"event_ids": "aew-v1-event-authority-current"})
    admitted = evaluate_packet(matched, history)
    assert admitted["coverage_requirement"] == "coverage_admitted"
    assert admitted["property"]["child_verdicts"]["P_effect"] == "supported"
