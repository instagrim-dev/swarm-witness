#!/usr/bin/env python3
"""Write the detection-latency replay score, evidence record, and report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "detection_latency"))

from dataset import build_dataset, build_sources  # noqa: E402
from swarm_witness.detection_latency import PROTOCOL_ID, render_report, run_replay  # noqa: E402
from swarm_witness.latency_evidence import bind_incident_latency, load_telemetry_bundle  # noqa: E402
from swarm_witness.schema import validate_finding, validate_run  # noqa: E402

CLAIM_ID = "detection_latency"
SOURCE_PIN = PROTOCOL_ID
RUN_ID = "detection-latency-score"
FINDING_ID = "detection-latency-f-protocol"


def execute() -> dict:
    replay = run_replay(build_dataset(), build_sources())
    return bind_incident_latency(replay, load_telemetry_bundle(ROOT))


def build_run(score: dict) -> dict:
    observations = dict(score["metrics"])
    observations["replay"] = {
        "withheld_latency_claims": score["withheld_latency_claims"],
        "narrative_window": score["narrative_window"],
        "may_signal": score["may_signal"],
        "synthetic_control_measures": score["synthetic_control_measures"],
        "ties": score["ties"],
        "failures": score["failures"],
        "detectable_stage_ids": score["detectable_stage_ids"],
        "stages": score["stages"],
        "sources_retrieval": score["sources_retrieval"],
        "errors": score["errors"],
        "non_claims": score["non_claims"],
        "rules": score["rules"],
        "incident_latency": score["incident_latency"],
    }
    run = {
        "id": RUN_ID,
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "replay-v1",
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "observations": observations,
    }
    validate_run(run)
    return run


def build_finding(score: dict) -> dict:
    passed = bool(score["metrics"]["passed"])
    finding = {
        "id": FINDING_ID,
        "claim_id": CLAIM_ID,
        "run_ids": [RUN_ID],
        "proposition": (
            "Under detection-latency-replay-v1, forensic telemetry holds no "
            "trustworthy event time for the original incident, so no incident "
            "detection latency is emitted. Synthetic controls exercise the "
            "timestamp vocabulary, rules, shared alert budget, and source ablation."
            if passed
            else "The detection-latency replay failed a declared check."
        ),
        "scope": (
            "Offline synthetic_control traces, historical_replay publication "
            "milestones, and the forensic-telemetry-v1 qualification. This "
            "finding does not certify detection or prevention of the incident."
        ),
        "label": "reproduced" if passed else "contradicted_in_scope",
        "conclusion_class": "supported" if passed else "failed_enforcement",
        "basis": "computed",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.passed",
            f"{RUN_ID}.observations.historical_latency_result_count",
            f"{RUN_ID}.observations.withheld_latency_claim_count",
            f"{RUN_ID}.observations.incident_detection_claimed",
            f"{RUN_ID}.observations.incident_prevention_claimed",
            f"{RUN_ID}.observations.detectable_case_denominator",
            f"{RUN_ID}.observations.incident_latency_status",
            f"{RUN_ID}.observations.incident_detection_latency_emitted",
            f"{RUN_ID}.observations.incident_trustworthy_event_time_count",
            f"{RUN_ID}.observations.reproduction_one_public_record",
            f"{RUN_ID}.observations.reproduction_independent_observation_count",
            f"{RUN_ID}.observations.unavailable_row_count",
            f"{RUN_ID}.observations.unavailable_effect_time_count",
            f"{RUN_ID}.observations.unavailable_records_are_gates",
            f"{RUN_ID}.observations.held_source_gate_prevents_supported",
            f"{RUN_ID}.observations.unavailable_gate_rejected",
        ],
    }
    validate_finding(finding)
    return finding


def write_outputs(root: Path, score: dict | None = None) -> dict:
    score = execute() if score is None else score
    run = build_run(score)
    finding = build_finding(score)
    evidence = root / "evidence" / "detection_latency"
    runs = evidence / "runs"
    findings = evidence / "findings"
    runs.mkdir(parents=True, exist_ok=True)
    findings.mkdir(parents=True, exist_ok=True)
    _dump_json(runs / f"{RUN_ID}.json", run)
    _dump_json(findings / f"{FINDING_ID}.json", finding)
    metrics = score["metrics"]
    result = {
        "claim_id": CLAIM_ID,
        "label": finding["label"],
        "authoritative": "finding",
        "finding_path": f"findings/{FINDING_ID}.json",
        "metrics": metrics,
        "notes": (
            "Incident detection latency is absent. Forensic telemetry holds no "
            "trustworthy event time for the original incident. Synthetic durations "
            "live under observations.replay.synthetic_control_measures and are not "
            "incident measurements."
        ),
    }
    (evidence / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )
    summary = {
        "claim_id": CLAIM_ID,
        "label": finding["label"],
        "protocol_id": PROTOCOL_ID,
        "notes": result["notes"],
        **metrics,
    }
    _dump_json(evidence / "summary.json", summary)
    experiment = root / "experiments" / "detection_latency"
    _dump_json(experiment / "dataset.json", build_dataset())
    _dump_json(experiment / "sources.json", build_sources())
    report = root / "docs" / "detection_latency_replay_v1.md"
    report.write_text(render_report(score), encoding="utf-8")
    return score


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    score = write_outputs(args.root)
    metrics = score["metrics"]
    print(
        json.dumps(
            {
                "protocol": PROTOCOL_ID,
                "passed": metrics["passed"],
                "detectable_case_denominator": metrics["detectable_case_denominator"],
                "historical_latency_result_count": metrics["historical_latency_result_count"],
                "withheld_latency_claim_count": metrics["withheld_latency_claim_count"],
                "errors": score["errors"],
            }
        )
    )
    return 0 if metrics["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
