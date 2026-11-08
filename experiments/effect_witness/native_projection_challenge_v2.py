#!/usr/bin/env python3
"""Versioned rescore of the sixteen-case challenge.

Reads the v1 inputs and warrants. Writes only to the requested output directory.
An entrypoint rejection stays a rejection: it is not stored as an epistemic
unresolved answer.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "experiments" / "effect_witness" / "native_projection_challenge.py"
V1_LEDGER = (
    ROOT
    / "evidence"
    / "effect_witness_v1"
    / "native_projection_challenge_v1"
    / "ledger.json"
)


def _v1():
    spec = importlib.util.spec_from_file_location("native_projection_challenge_v1", V1)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {V1}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate_challenge_v2(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    del repo_root
    challenge = _v1()
    spec = __import__("yaml").safe_load(challenge.CHALLENGE.read_text(encoding="utf-8"))
    history_id, _condition = spec["source_packet"].split("/", 1)
    cases = challenge.build_cases(history_id)
    if set(cases) != set(spec["cases"]):
        raise ValueError("challenge cases and warrants diverged")
    historical = {
        row["case_id"]: row
        for row in json.loads(V1_LEDGER.read_text(encoding="utf-8"))["rows"]
    }
    rows = []
    for case_id, case in spec["cases"].items():
        records = cases[case_id]
        directory = output_dir / "packets" / case_id
        competent = challenge.competent_verdict(history_id, records)["epistemic_status"]
        status = challenge.swarm_witness_status(history_id, records, directory)
        warrant = case["expected"]
        if status.startswith("entrypoint_rejected:"):
            execution_status = "rejected"
            epistemic_status = None
            raw_error = status.removeprefix("entrypoint_rejected:")
            matches = False
            sink_rejections: list[dict[str, str]] = []
        else:
            from swarm_witness.effect_witness.qualify import evaluate_packet
            from swarm_witness.effect_witness.histories import HISTORY_BY_ID

            result = evaluate_packet(directory, HISTORY_BY_ID[history_id])
            execution_status = "completed"
            epistemic_status = status
            raw_error = None
            matches = status == warrant
            sink_rejections = list(result.get("sink_rejections") or [])
        duplicate_ids = [
            row["record_id"]
            for row in records
            if str(row.get("record_id", "")).endswith("-copy")
        ]
        rows.append(
            {
                "case_id": case_id,
                "execution_status": execution_status,
                "epistemic_status": epistemic_status,
                "raw_error": raw_error,
                "warrant": warrant,
                "matches_warrant": matches,
                "admitted_ids": [
                    row["record_id"]
                    for row in records
                    if row["record_id"] not in {item["record_id"] for item in sink_rejections}
                    and not str(row["record_id"]).endswith("-copy")
                ],
                "rejected_ids": [item["record_id"] for item in sink_rejections] + duplicate_ids,
                "reasons": [item["reason"] for item in sink_rejections]
                + (["exact_duplicate_not_independent"] if duplicate_ids else []),
                "historical_swarm_witness": historical[case_id]["swarm_witness"],
                "competent_comparator": competent,
                "ordinary_entrypoint": "swarm_witness.effect_witness.qualify.evaluate_packet",
            }
        )
    document = {
        "protocol_id": "native-projection-challenge-v2",
        "input_protocol": spec["protocol_id"],
        "input_ledger": "evidence/effect_witness_v1/native_projection_challenge_v1/ledger.json",
        "v1_ledger_unchanged": True,
        "case_count": len(rows),
        "rows": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ledger.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    trace = ["# Challenge v2 before and after", "", "The v1 ledger is not rewritten. A rejection is not an epistemic verdict.", ""]
    trace.append("| Case | Historical Swarm Witness | Current Swarm Witness | Comparator | Reason |")
    trace.append("| --- | --- | --- | --- | --- |")
    for row in rows:
        current = row["epistemic_status"] if row["execution_status"] == "completed" else f"rejected: {row['raw_error']}"
        reason = ", ".join(row["reasons"]) or "none"
        trace.append(
            f"| {row['case_id']} | {row['historical_swarm_witness']} | {current} | {row['competent_comparator']} | {reason} |"
        )
    (output_dir / "TRACE.md").write_text("\n".join(trace) + "\n", encoding="utf-8")
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluate_challenge_v2(ROOT, args.output)
    print(args.output / "ledger.json")


if __name__ == "__main__":
    main()
