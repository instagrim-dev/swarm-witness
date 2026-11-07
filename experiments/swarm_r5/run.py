#!/usr/bin/env python3
"""Execute R5 multi-agent swarm audit and write Claim/Run/Finding evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.schema import validate_finding, validate_run  # noqa: E402
from swarm_witness.swarm_audit import (  # noqa: E402
    evaluate_swarm_method_success,
    run_swarm_protocol_cases,
)

CLAIM_ID = "r5"
PROTOCOL_ID = "r5-swarm-audit-v1"
SOURCE_PIN = "swarm-witness-r5-v1"
EV = ROOT / "evidence" / "r5"


def build_runs(cases: list[dict]) -> list[dict]:
    runs: list[dict] = []
    for case in cases:
        result = case["result"]
        run = {
            "id": f"r5-{case['case_id']}",
            "claim_id": CLAIM_ID,
            "protocol_id": PROTOCOL_ID,
            "case_id": case["case_id"],
            "source_pin": SOURCE_PIN,
            "execution_status": "completed",
            "observations": {
                "role": case["role"],
                "agents": case["agents"],
                "assessment": result["assessment"],
                "conclusion_class": result["conclusion_class"],
                "finding_label": result["finding_label"],
                "property_holds": result["property_holds"],
                "decision": result["decision"],
                "required_decision": result.get("required_decision"),
                "agent": result["agent"],
                "grant_id": result["grant_id"],
                "observe_grant": result["observe_grant"],
                "gate_mode": result.get("gate_mode"),
                "foreign_receipt_from": result.get("foreign_receipt_from"),
                "presented_receipt": result.get("presented_receipt"),
                "effect_committed": result.get("effect_committed"),
                "evidence_status": result.get("evidence_status"),
                "decision_status": result.get("decision_status"),
                "effect_status": result.get("effect_status"),
                "failure_origin": result.get("failure_origin"),
                "reason": result["reason"],
                "expected_conclusion_class": case["expected_conclusion_class"],
                "expected_assessment": case["expected_assessment"],
                "conclusion_match": (
                    result["conclusion_class"] == case["expected_conclusion_class"]
                ),
            },
        }
        validate_run(run)
        runs.append(run)
    return runs


def build_meta_run(score: dict) -> dict:
    run = {
        "id": "r5-method-score",
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "method_score",
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "observations": {
            "passed": score["passed"],
            "all_checks_pass": score["all_checks_pass"],
            "three_way_classes_exercised": score["three_way_classes_exercised"],
            "case_count": score["case_count"],
            "agent_count": score["agent_count"],
            "agents": score["agents"],
            "model": score.get("model"),
            "missing_evidence_count": score["missing_evidence_count"],
            "failed_enforcement_count": score["failed_enforcement_count"],
            "supported_count": score["supported_count"],
            "errors": score["errors"],
        },
    }
    validate_run(run)
    return run


def build_finding(runs: list[dict], score: dict) -> dict:
    label = "reproduced" if score["passed"] else "contradicted_in_scope"
    finding = {
        "id": "r5-f-swarm-audit",
        "claim_id": CLAIM_ID,
        "run_ids": [r["id"] for r in runs],
        "proposition": (
            "Under r5-swarm-audit-v1 with agents A/B/C in a sequential shared-grant "
            "model, the three-way conclusion method classifies missing peer "
            "observations as missing_evidence; broken allows as high-level "
            "failed_enforcement with failure_origin=decision_policy and "
            "effect_status=prevented (not effect-boundary failure); and correct "
            "sequential contention, A→B then B→C assignee hops, and ledger-bound "
            "cross-agent receipt denies as supported"
            if score["passed"]
            else "Swarm audit protocol failed one or more declared checks"
        ),
        "scope": (
            "Synthetic sequential multi-principal model (named A/B/C, in-memory "
            "ledger); not concurrent worker execution, not live BMO mesh, not "
            "cryptographic multi-party auth, not unbounded population scale"
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            "r5-method-score.observations.passed",
            "r5-method-score.observations.three_way_classes_exercised",
            "r5-method-score.observations.agent_count",
            "r5-method-score.observations.all_checks_pass",
        ],
    }
    validate_finding(finding)
    finding["conclusion_class"] = "supported"
    finding["evaluation_method"] = "synthetic_protocol_conformance"
    return finding


def write_evidence(ev_dir: Path, cases: list[dict], score: dict) -> dict:
    runs_dir = ev_dir / "runs"
    findings_dir = ev_dir / "findings"
    runs_dir.mkdir(parents=True, exist_ok=True)
    findings_dir.mkdir(parents=True, exist_ok=True)
    for path in runs_dir.glob("*.json"):
        path.unlink()
    for path in findings_dir.glob("*.json"):
        path.unlink()

    runs = build_runs(cases)
    meta = build_meta_run(score)
    all_runs = runs + [meta]
    for run in all_runs:
        (runs_dir / f"{run['id']}.json").write_text(
            json.dumps(run, indent=2) + "\n", encoding="utf-8"
        )

    finding = build_finding(all_runs, score)
    (findings_dir / f"{finding['id']}.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )

    summary = {
        "protocol_id": PROTOCOL_ID,
        "claim_id": CLAIM_ID,
        "cases": [
            {
                "case_id": c["case_id"],
                "role": c["role"],
                "agents": c["agents"],
                "conclusion_class": c["result"]["conclusion_class"],
                "assessment": c["result"]["assessment"],
                "decision": c["result"]["decision"],
            }
            for c in cases
        ],
        "score": score,
        "finding_id": finding["id"],
        "label": finding["label"],
    }
    (ev_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    result = {
        "claim_id": CLAIM_ID,
        "label": finding["label"],
        "authoritative": "finding",
        "finding_path": f"findings/{finding['id']}.json",
        "metrics": {
            "case_count": score["case_count"],
            "agent_count": score["agent_count"],
            "missing_evidence_count": score["missing_evidence_count"],
            "failed_enforcement_count": score["failed_enforcement_count"],
            "supported_count": score["supported_count"],
            "all_checks_pass": score["passed"],
        },
        "notes": (
            "Sequential three-principal shared-grant taxonomy transfer "
            "(not concurrent swarm execution)"
        ),
    }
    (ev_dir / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )
    return {"finding": finding, "summary": summary, "score": score}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=EV)
    args = parser.parse_args(argv)
    cases = run_swarm_protocol_cases()
    score = evaluate_swarm_method_success(cases)
    out = write_evidence(args.evidence_dir, cases, score)
    print(
        json.dumps(
            {
                "label": out["finding"]["label"],
                "passed": score["passed"],
                "case_count": score["case_count"],
                "agents": score["agents"],
                "three_way": score["three_way_classes_exercised"],
                "counts": {
                    "missing_evidence": score["missing_evidence_count"],
                    "failed_enforcement": score["failed_enforcement_count"],
                    "supported": score["supported_count"],
                },
                "errors": score["errors"],
            }
        )
    )
    return 0 if score["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
