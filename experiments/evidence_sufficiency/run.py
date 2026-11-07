#!/usr/bin/env python3
"""Execute R4 evidence-sufficiency protocol and write Claim/Run/Finding evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.evidence_sufficiency import (  # noqa: E402
    evaluate_method_success,
    run_protocol_cases,
)
from swarm_witness.schema import validate_finding, validate_run  # noqa: E402

CLAIM_ID = "r4"
PROTOCOL_ID = "r4-evidence-sufficiency-v1"
SOURCE_PIN = "swarm-witness-r4-v1"
EV = ROOT / "evidence" / "r4"


def build_runs(cases: list[dict]) -> list[dict]:
    runs: list[dict] = []
    for case in cases:
        result = case["result"]
        run = {
            "id": f"r4-{case['case_id']}",
            "claim_id": CLAIM_ID,
            "protocol_id": PROTOCOL_ID,
            "case_id": case["case_id"],
            "source_pin": SOURCE_PIN,
            "execution_status": "completed",
            "observations": {
                "role": case["role"],
                "assessment": result["assessment"],
                "decision": result["decision"],
                "justified_permission_claim": result["justified_permission_claim"],
                "ground_truth_grant": result["ground_truth_grant"],
                "include_current_grant": result["observations"]["include_current_grant"],
                "include_irrelevant": result["observations"]["include_irrelevant"],
                "observed_grant": result["observations"]["observed_grant"],
                "reason": result["reason"],
                "expected_assessment": case["expected_assessment"],
                "assessment_match": result["assessment"] == case["expected_assessment"],
                "ground_truth_mismatch": bool(case.get("ground_truth_mismatch")),
                "misbound_detected": result.get("misbound_detected"),
            },
        }
        validate_run(run)
        runs.append(run)
    return runs


def build_meta_run(score: dict) -> dict:
    run = {
        "id": "r4-method-score",
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "method_score",
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "observations": {
            "passed": score["passed"],
            "indistinguishable_when_blind": score["indistinguishable_when_blind"],
            "discriminator_separates_worlds": score["discriminator_separates_worlds"],
            "case_count": score["case_count"],
            "unsupported_blind_count": score["unsupported_blind_count"],
            "errors": score["errors"],
            "all_checks_pass": score["passed"],
        },
    }
    validate_run(run)
    return run


def build_finding(runs: list[dict], score: dict) -> dict:
    label = "reproduced" if score["passed"] else "contradicted_in_scope"
    finding = {
        "id": "r4-f-evidence-sufficiency",
        "claim_id": CLAIM_ID,
        "run_ids": [r["id"] for r in runs],
        "proposition": (
            "Identical old receipts with unobserved current grant leave Worlds A "
            "(valid) and B (revoked) indistinguishable, so permission claims stay "
            "unsupported; observing current grant state distinguishes them; an "
            "irrelevant observation does not; legitimate allow proceeds when the "
            "discriminating evidence is present"
            if score["passed"]
            else "Evidence-sufficiency protocol failed one or more declared checks"
        ),
        "scope": (
            "Synthetic two-world grant/receipt protocol under "
            "r4-evidence-sufficiency-v1; not multi-agent delegation or live BMO"
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            "r4-method-score.observations.passed",
            "r4-method-score.observations.indistinguishable_when_blind",
            "r4-method-score.observations.discriminator_separates_worlds",
            "r4-method-score.observations.all_checks_pass",
        ],
    }
    validate_finding(finding)
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
                "assessment": c["result"]["assessment"],
                "decision": c["result"]["decision"],
                "expected_assessment": c["expected_assessment"],
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
            "unsupported_blind_count": score["unsupported_blind_count"],
            "all_checks_pass": score["passed"],
        },
        "notes": (
            "Worlds A/B indistinguishability under shared receipt; "
            "discriminator = current grant state"
        ),
    }
    (ev_dir / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )
    return {"finding": finding, "summary": summary, "score": score}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=EV,
        help="Evidence slot directory (default evidence/r4)",
    )
    args = parser.parse_args(argv)
    cases = run_protocol_cases()
    score = evaluate_method_success(cases)
    out = write_evidence(args.evidence_dir, cases, score)
    print(
        json.dumps(
            {
                "label": out["finding"]["label"],
                "passed": score["passed"],
                "case_count": score["case_count"],
                "errors": score["errors"],
            }
        )
    )
    return 0 if score["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
