#!/usr/bin/env python3
"""Execute R5-v2 wider-coverage protocol and write Claim/Run/Finding evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.schema import validate_finding, validate_run  # noqa: E402
from swarm_witness.swarm_audit_v2 import (  # noqa: E402
    CLAIM_ID,
    PROTOCOL_ID,
    SOURCE_PIN,
    compare_boundaries_to_v1,
    coverage_report,
    evaluate_r5_v2_success,
    run_r5_v2_protocol_cases,
)

EV = ROOT / "evidence" / "r5_v2"


def build_runs(cases: list[dict]) -> list[dict]:
    runs: list[dict] = []
    for case in cases:
        result = case["result"]
        run = {
            "id": f"r5v2-{case['case_id']}",
            "claim_id": CLAIM_ID,
            "protocol_id": PROTOCOL_ID,
            "case_id": case["case_id"],
            "source_pin": SOURCE_PIN,
            "execution_status": "completed",
            "observations": {
                "family": case["family"],
                "agents": case["agents"],
                "mechanism_arm": case.get("mechanism_arm"),
                "paired_input_id": case.get("paired_input_id"),
                "evidence_source": case.get("evidence_source"),
                "expectation_source": case.get("expectation_source"),
                "assessment": result.get("assessment"),
                "conclusion_class": result["conclusion_class"],
                "finding_label": result.get("finding_label"),
                "property_holds": result.get("property_holds"),
                "decision": result.get("decision"),
                "required_decision": result.get("required_decision"),
                "agent": result.get("agent"),
                "grant_id": result.get("grant_id"),
                "call_id": result.get("call_id"),
                "observation_mode": result.get("observation_mode"),
                "gate_mode": result.get("gate_mode"),
                "receipt_kind": result.get("receipt_kind"),
                "presented_receipt": result.get("presented_receipt"),
                "effect_committed": result.get("effect_committed"),
                "evidence_status": result.get("evidence_status"),
                "decision_status": result.get("decision_status"),
                "effect_status": result.get("effect_status"),
                "failure_origin": result.get("failure_origin"),
                "authoritative_owner_state": _jsonable(
                    result.get("authoritative_owner_state")
                ),
                "trusted_ground_truth": result.get("trusted_ground_truth"),
                "held_out_artifact": result.get("held_out_artifact"),
                "sim_source_run_id": result.get("sim_source_run_id"),
                "sim_protocol_id": result.get("sim_protocol_id"),
                "sim_exclusions": result.get("sim_exclusions"),
                "expected": case.get("expected"),
                "conclusion_match": (
                    case.get("expected") is None
                    or result["conclusion_class"]
                    == case["expected"].get("conclusion_class")
                ),
                "reason": result.get("reason"),
            },
        }
        validate_run(run)
        runs.append(run)
    return runs


def _jsonable(value):
    if value is None:
        return None
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(v, set):
                out[k] = sorted(v)
            else:
                out[k] = _jsonable(v) if isinstance(v, dict) else v
        return out
    return value


def build_meta_run(score: dict, coverage: dict, boundaries: dict) -> dict:
    run = {
        "id": "r5v2-method-score",
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
            "families": score.get("families"),
            "family_count": score.get("family_count"),
            "paired_input_groups_with_correct_and_faulty": score.get(
                "paired_input_groups_with_correct_and_faulty"
            ),
            "concurrency_row_count": score.get("concurrency_row_count"),
            "held_out_count": score.get("held_out_count"),
            "missing_evidence_count": score["missing_evidence_count"],
            "failed_enforcement_count": score["failed_enforcement_count"],
            "supported_count": score["supported_count"],
            "effect_boundary_count": score.get("effect_boundary_count"),
            "decision_policy_count": score.get("decision_policy_count"),
            "unknown_coerced_count": score.get("unknown_coerced_count"),
            "coverage_dimension_count": coverage.get("dimension_count"),
            "coverage": coverage,
            "boundary_comparison": boundaries,
            "errors": score["errors"],
            "exclusions": [
                "live_bmo_mesh_equivalence",
                "production_concurrency_guarantees",
                "unbounded_swarm_safety",
                "r5_v1_overwrite",
                "new_verdict_label_for_matrix_padding",
            ],
        },
    }
    validate_run(run)
    return run


def build_finding(runs: list[dict], score: dict) -> dict:
    label = "reproduced" if score["passed"] else "contradicted_in_scope"
    finding = {
        "id": "r5v2-f-swarm-audit",
        "claim_id": CLAIM_ID,
        "run_ids": [r["id"] for r in runs],
        "proposition": (
            "Under r5-swarm-audit-v2 the three-way conclusion method classifies "
            "orthogonal authorization, delegation, receipt, observation-quality, "
            "decision/effect, held-out, and pinned multi-agent-sim concurrency "
            "rows with independently declared expectations; missing evidence stays "
            "unknown; prevented wrong allows are decision_policy; committed "
            "unauthorized effects are effect_boundary; R5 v1 remains unmodified"
            if score["passed"]
            else "R5-v2 protocol failed one or more declared checks"
        ),
        "scope": (
            "Synthetic sequential harness plus pinned multi-agent-sim-v1 traces; "
            "not live concurrent swarm behavior; not live BMO mesh; not a new "
            "verdict taxonomy; does not overwrite R5 v1 evidence"
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            "r5v2-method-score.observations.passed",
            "r5v2-method-score.observations.three_way_classes_exercised",
            "r5v2-method-score.observations.coverage_dimension_count",
            "r5v2-method-score.observations.boundary_comparison",
            "r5v2-method-score.observations.concurrency_row_count",
            "r5v2-method-score.observations.held_out_count",
        ],
    }
    validate_finding(finding)
    finding["conclusion_class"] = "supported" if score["passed"] else "failed_enforcement"
    finding["evaluation_method"] = "synthetic_protocol_conformance"
    return finding


def write_evidence(
    ev_dir: Path,
    cases: list[dict],
    score: dict,
    coverage: dict,
    boundaries: dict,
) -> dict:
    runs_dir = ev_dir / "runs"
    findings_dir = ev_dir / "findings"
    runs_dir.mkdir(parents=True, exist_ok=True)
    findings_dir.mkdir(parents=True, exist_ok=True)
    for path in runs_dir.glob("*.json"):
        path.unlink()
    for path in findings_dir.glob("*.json"):
        path.unlink()

    runs = build_runs(cases)
    meta = build_meta_run(score, coverage, boundaries)
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
        "source_pin": SOURCE_PIN,
        "prior_protocol_retained": "r5-swarm-audit-v1",
        "model": score.get("model"),
        "exclusions": meta["observations"]["exclusions"],
        "cases": [
            {
                "case_id": c["case_id"],
                "family": c["family"],
                "mechanism_arm": c.get("mechanism_arm"),
                "evidence_source": c.get("evidence_source"),
                "conclusion_class": c["result"]["conclusion_class"],
                "decision": c["result"].get("decision"),
                "effect_committed": c["result"].get("effect_committed"),
                "failure_origin": c["result"].get("failure_origin"),
            }
            for c in cases
        ],
        "score": score,
        "coverage": coverage,
        "boundary_comparison": boundaries,
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
            "family_count": score["family_count"],
            "coverage_dimension_count": coverage["dimension_count"],
            "missing_evidence_count": score["missing_evidence_count"],
            "failed_enforcement_count": score["failed_enforcement_count"],
            "supported_count": score["supported_count"],
            "concurrency_row_count": score["concurrency_row_count"],
            "held_out_count": score["held_out_count"],
            "all_checks_pass": score["passed"],
        },
        "notes": (
            "R5-v2 wider coverage; v1 retained; concurrency from pinned "
            "multi-agent-sim-v1 traces only"
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
    cases = run_r5_v2_protocol_cases()
    score = evaluate_r5_v2_success(cases)
    coverage = coverage_report(cases)
    boundaries = compare_boundaries_to_v1(cases)
    out = write_evidence(args.evidence_dir, cases, score, coverage, boundaries)
    print(
        json.dumps(
            {
                "label": out["finding"]["label"],
                "passed": score["passed"],
                "case_count": score["case_count"],
                "families": score["families"],
                "coverage_dimensions": coverage["dimension_count"],
                "concurrency_rows": score["concurrency_row_count"],
                "held_out": score["held_out_count"],
                "v1_retained": boundaries["v1_retained"],
                "boundary_changes": boundaries["boundary_changes"],
                "counts": {
                    "missing_evidence": score["missing_evidence_count"],
                    "failed_enforcement": score["failed_enforcement_count"],
                    "supported": score["supported_count"],
                    "effect_boundary": score["effect_boundary_count"],
                    "decision_policy": score["decision_policy_count"],
                },
                "errors": score["errors"],
            },
            indent=2,
        )
    )
    return 0 if score["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
