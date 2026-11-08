"""Sixteen-case native projection challenge.

The warrant is the label. A row records Swarm Witness and the competent
comparator separately. Their agreement is not the correctness label.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

from swarm_witness.effect_witness.histories import HISTORY_BY_ID
from swarm_witness.effect_witness.qualify import evaluate_packet
from swarm_witness.effect_witness.records import write_jsonl
from swarm_witness.native_comparison import competent_verdict

ROOT = Path(__file__).resolve().parents[2]
PACKETS = ROOT / "evidence" / "effect_witness_v1" / "packets"
CHALLENGE = ROOT / "experiments" / "effect_witness" / "native_projection_challenge_v1.yaml"
LEDGER = (
    ROOT
    / "evidence"
    / "effect_witness_v1"
    / "native_projection_challenge_v1"
    / "ledger.json"
)


def load_records(history_id: str, condition: str) -> list[dict[str, Any]]:
    directory = PACKETS / history_id / condition
    rows: list[dict[str, Any]] = []
    for name in ("actor_records.jsonl", "service_records.jsonl"):
        path = directory / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _sink(records: list[dict[str, Any]]) -> dict[str, Any]:
    return next(row for row in records if row.get("surface") == "committed_effect")


def _coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    return next(row for row in records if row.get("action") == "coverage_scan")


def _replace_body(record: dict[str, Any], **updates: str) -> None:
    fields: dict[str, str] = {}
    for line in str(record["public_bytes"]).splitlines():
        if "=" in line and not line.startswith("aew-v1 "):
            key, value = line.split("=", 1)
            fields[key] = value
    fields.update(updates)
    header = str(record["public_bytes"]).splitlines()[0]
    rendered = header + "\n" + "".join(f"{key}={value}\n" for key, value in fields.items())
    record["public_bytes"] = rendered
    record["raw"] = rendered


def build_cases(history_id: str) -> dict[str, list[dict[str, Any]]]:
    """The sixteen declared mutations. Order inside a case is the scored order."""
    base = load_records(history_id, "discriminating_readback")
    cases: dict[str, list[dict[str, Any]]] = {"clean-positive": copy.deepcopy(base)}

    misbound = copy.deepcopy(base)
    sink = _sink(misbound)
    sink["record_id"] = sink["record_id"] + "-misbound"
    cases["sink-misbound"] = misbound

    spoofed = copy.deepcopy(base)
    _sink(spoofed)["authenticity"] = "spoofed_tool_line"
    cases["sink-spoofed"] = spoofed

    unauthenticated = copy.deepcopy(base)
    _sink(unauthenticated)["authenticity"] = "unauthenticated_tool_line"
    cases["sink-unauthenticated"] = unauthenticated

    stale = copy.deepcopy(base)
    _sink(stale)["freshness"] = "stale"
    cases["sink-stale"] = stale

    wrong_run = copy.deepcopy(base)
    _replace_body(_sink(wrong_run), run_id="aew-v1-run-other")
    cases["sink-run-mismatch"] = wrong_run

    wrong_actor = copy.deepcopy(base)
    _replace_body(_sink(wrong_actor), actor_id="aew-v1-actor-other")
    _sink(wrong_actor)["actor"] = "aew-v1-actor-other"
    _sink(wrong_actor)["parent_id"] = None
    cases["sink-actor-mismatch"] = wrong_actor

    wrong_object = copy.deepcopy(base)
    _replace_body(_sink(wrong_object), object_scope="aew-v1-object-other")
    _sink(wrong_object)["object"] = "aew-v1-object-other"
    _sink(wrong_object)["parent_id"] = None
    cases["sink-object-mismatch"] = wrong_object

    mapped_actor = copy.deepcopy(base)
    _replace_body(_sink(mapped_actor), actor_id="aew-v1-actor-other")
    _sink(mapped_actor)["actor"] = "aew-v1-actor-other"
    cases["sink-mapped-actor-mismatch"] = mapped_actor

    mixed = copy.deepcopy(base)
    extra = copy.deepcopy(_sink(mixed))
    extra["record_id"] = extra["record_id"] + "-unknown"
    extra["source_id"] = "src-" + extra["record_id"]
    _replace_body(extra, subject_class="unknown")
    _replace_body(_coverage(mixed), row_count="2")
    cases["mixed-unknown-authorization"] = mixed + [extra]

    conflict = copy.deepcopy(base)
    other = copy.deepcopy(_coverage(conflict))
    other["record_id"] = other["record_id"] + "-other"
    other["source_id"] = "src-" + other["record_id"]
    _replace_body(other, row_count="0")
    cases["coverage-conflict"] = conflict + [other]

    duplicate = copy.deepcopy(base)
    copied = copy.deepcopy(_coverage(duplicate))
    copied["record_id"] = copied["record_id"] + "-copy"
    copied["source_id"] = "src-" + copied["record_id"]
    cases["coverage-duplicate"] = duplicate + [copied]

    unknown = copy.deepcopy(base)
    _replace_body(_sink(unknown), subject_class="unknown")
    cases["sink-unknown-subject"] = unknown

    wrong_operation = copy.deepcopy(base)
    _replace_body(_coverage(wrong_operation), operations="aew-v1-op-not-the-target")
    cases["coverage-operation-mismatch"] = wrong_operation

    outside = copy.deepcopy(base)
    _replace_body(
        _coverage(outside),
        interval_start="2030-01-01T00:00:00Z",
        interval_end="2030-01-01T00:01:00Z",
    )
    cases["coverage-interval-outside"] = outside

    withheld = copy.deepcopy(base)
    coverage = _coverage(withheld)
    coverage["locally_held"] = False
    coverage["access_level"] = "withheld"
    coverage["redaction"] = "withheld_original"
    cases["coverage-withheld"] = withheld
    return cases


def swarm_witness_status(history_id: str, records: list[dict[str, Any]], directory: Path) -> str:
    """Score P_effect through the ordinary packet entrypoint."""
    directory.mkdir(parents=True, exist_ok=True)
    actor = [row for row in records if row.get("surface") == "requested_command"]
    service = [row for row in records if row.get("surface") != "requested_command"]
    write_jsonl(directory / "actor_records.jsonl", actor)
    write_jsonl(directory / "service_records.jsonl", service)
    try:
        result = evaluate_packet(directory, HISTORY_BY_ID[history_id])
    except (RuntimeError, ValueError) as exc:
        return f"entrypoint_rejected:{exc}"
    if result.get("refused"):
        return "unresolved"
    verdict = result["property"]["child_verdicts"]["P_effect"]
    if verdict not in {"supported", "refuted", "unresolved"}:
        raise ValueError(verdict)
    return verdict


def paired_ledger(tmp: Path) -> dict[str, Any]:
    spec = yaml.safe_load(CHALLENGE.read_text(encoding="utf-8"))
    history_id, _condition = spec["source_packet"].split("/", 1)
    cases = build_cases(history_id)
    if set(cases) != set(spec["cases"]):
        raise ValueError("challenge cases and warrants diverged")
    rows = []
    for case_id, case in spec["cases"].items():
        records = cases[case_id]
        competent = competent_verdict(history_id, records)["epistemic_status"]
        swarm = swarm_witness_status(history_id, records, tmp / case_id)
        warrant = case["expected"]
        rows.append(
            {
                "case_id": case_id,
                "mutation": case["mutation"],
                "warrant": warrant,
                "competent_comparator": competent,
                "swarm_witness": swarm,
                "competent_matches_warrant": competent == warrant,
                "swarm_witness_matches_warrant": swarm == warrant,
            }
        )
    return {
        "protocol_id": spec["protocol_id"],
        "source_packet": spec["source_packet"],
        "proposition": spec["proposition"],
        "label": "separately declared warrant",
        "agreement_is_not_the_label": True,
        "case_count": len(rows),
        "rows": rows,
    }


def main() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        ledger = paired_ledger(Path(raw))
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(LEDGER)


if __name__ == "__main__":
    main()
