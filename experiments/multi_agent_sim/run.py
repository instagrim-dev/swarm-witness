#!/usr/bin/env python3
"""Execute multi-agent simulator protocol and write evidence + traces.

Model under test: deterministic in-process causal interleaving simulator with
per-agent local observations and a separate authoritative ledger.

Excluded: live BMO mesh equivalence, production concurrency guarantees,
unbounded swarm safety. Does not upgrade or relabel R5 v1 sequential findings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.multi_agent_sim.protocol import (  # noqa: E402
    CLAIM_ID,
    PROTOCOL_ID,
    SOURCE_PIN,
    evaluate_protocol_success,
    replay_traces_match,
    run_protocol_cases,
)
from swarm_witness.schema import validate_finding, validate_run  # noqa: E402

EV = ROOT / "evidence" / "multi_agent_sim"


def build_runs(cases: list[dict]) -> list[dict]:
    runs: list[dict] = []
    for case in cases:
        evaluation = case["evaluation"]
        run = {
            "id": f"mas-{case['case_id']}",
            "claim_id": CLAIM_ID,
            "protocol_id": PROTOCOL_ID,
            "case_id": case["case_id"],
            "source_pin": SOURCE_PIN,
            "execution_status": "completed",
            "observations": {
                "role": case["role"],
                "agents": case["agents"],
                "policy_id": case["policy_id"],
                "schedule_id": evaluation["schedule_id"],
                "seed": evaluation["seed"],
                "one_use_ok": evaluation["one_use_ok"],
                "event_count": evaluation["event_count"],
                "claim_count": evaluation["claim_count"],
                "claims": evaluation["claims"],
                "expected": case["expected"],
                "model": "deterministic_in_process_interleaving_simulator",
                "exclusions": [
                    "live_bmo_mesh_equivalence",
                    "production_concurrency_guarantees",
                    "unbounded_swarm_safety",
                ],
            },
        }
        validate_run(run)
        runs.append(run)
    return runs


def build_meta_run(score: dict, replay_ok: bool) -> dict:
    run = {
        "id": "mas-method-score",
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
            "missing_evidence_count": score["missing_evidence_count"],
            "failed_enforcement_count": score["failed_enforcement_count"],
            "supported_count": score["supported_count"],
            "replay_stable": replay_ok,
            "errors": score["errors"],
            "observation_denominator_note": (
                "Each claim evaluation records required_count/present_count for "
                "current_grant_observation plus irrelevant_count and receipt_count"
            ),
        },
    }
    validate_run(run)
    return run


def build_finding(runs: list[dict], score: dict, replay_ok: bool) -> dict:
    label = "reproduced" if score["passed"] and replay_ok else "contradicted_in_scope"
    finding = {
        "id": "mas-f-multi-agent-sim",
        "claim_id": CLAIM_ID,
        "run_ids": [r["id"] for r in runs],
        "proposition": (
            "Under multi-agent-sim-v1, independently scheduled principals A/B/C "
            "with per-agent local observations and an authoritative ledger yield "
            "reproducible interleaving traces that distinguish decision, committed "
            "effect, authoritative owner state, and audit conclusion; reference "
            "vs mutant arms share schedules; paired worlds stay missing_evidence "
            "until a discriminating observation"
            if score["passed"] and replay_ok
            else "Multi-agent simulator protocol failed one or more declared checks"
        ),
        "scope": (
            "Deterministic in-process multi-agent interleaving simulator; classical "
            "one-use shared grants; not live BMO mesh, not production concurrency "
            "guarantees, not unbounded swarm safety; separate from R5 sequential v1"
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            "mas-method-score.observations.passed",
            "mas-method-score.observations.replay_stable",
            "mas-method-score.observations.three_way_classes_exercised",
            "mas-method-score.observations.all_checks_pass",
        ],
    }
    validate_finding(finding)
    finding["conclusion_class"] = "supported" if label == "reproduced" else "failed_enforcement"
    finding["evaluation_method"] = "synthetic_protocol_conformance"
    return finding


def write_evidence(ev_dir: Path, cases: list[dict], score: dict, replay_ok: bool) -> dict:
    runs_dir = ev_dir / "runs"
    findings_dir = ev_dir / "findings"
    traces_dir = ev_dir / "traces"
    manifests_dir = ev_dir / "manifests"
    for d in (runs_dir, findings_dir, traces_dir, manifests_dir):
        d.mkdir(parents=True, exist_ok=True)
    for path in runs_dir.glob("*.json"):
        path.unlink()
    for path in findings_dir.glob("*.json"):
        path.unlink()
    for path in traces_dir.glob("*.json"):
        path.unlink()
    for path in manifests_dir.glob("*.json"):
        path.unlink()

    runs = build_runs(cases)
    meta = build_meta_run(score, replay_ok)
    all_runs = runs + [meta]
    for run in all_runs:
        (runs_dir / f"{run['id']}.json").write_text(
            json.dumps(run, indent=2) + "\n", encoding="utf-8"
        )

    for case in cases:
        (traces_dir / f"{case['case_id']}.json").write_text(
            json.dumps(case["trace"], indent=2) + "\n", encoding="utf-8"
        )
        (manifests_dir / f"{case['case_id']}.json").write_text(
            json.dumps(case["manifest"], indent=2) + "\n", encoding="utf-8"
        )

    finding = build_finding(all_runs, score, replay_ok)
    (findings_dir / f"{finding['id']}.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )

    summary = {
        "protocol_id": PROTOCOL_ID,
        "claim_id": CLAIM_ID,
        "source_pin": SOURCE_PIN,
        "model": "deterministic_in_process_interleaving_simulator",
        "exclusions": [
            "live_bmo_mesh_equivalence",
            "production_concurrency_guarantees",
            "unbounded_swarm_safety",
            "r5_v1_relabeled_as_concurrent",
        ],
        "replay_stable": replay_ok,
        "cases": [
            {
                "case_id": c["case_id"],
                "role": c["role"],
                "policy_id": c["policy_id"],
                "claims": [
                    {
                        "call_id": cl["call_id"],
                        "decision": cl["decision"],
                        "committed_effect": cl["committed_effect"],
                        "conclusion_class": cl["conclusion_class"],
                    }
                    for cl in c["evaluation"]["claims"]
                ],
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
            "missing_evidence_count": score["missing_evidence_count"],
            "failed_enforcement_count": score["failed_enforcement_count"],
            "supported_count": score["supported_count"],
            "replay_stable": replay_ok,
            "all_checks_pass": score["passed"] and replay_ok,
        },
        "notes": (
            "Multi-agent causal interleaving simulator (post-submission research); "
            "not a live distributed deployment"
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
    cases = run_protocol_cases()
    score = evaluate_protocol_success(cases)
    replay_ok = replay_traces_match()
    out = write_evidence(args.evidence_dir, cases, score, replay_ok)
    print(
        json.dumps(
            {
                "label": out["finding"]["label"],
                "passed": score["passed"] and replay_ok,
                "case_count": score["case_count"],
                "replay_stable": replay_ok,
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
    return 0 if score["passed"] and replay_ok else 1


if __name__ == "__main__":
    sys.exit(main())
