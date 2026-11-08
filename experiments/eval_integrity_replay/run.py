#!/usr/bin/env python3
"""Run eval-integrity replay v1 and publish evidence (issue #50)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.eval_integrity_replay import (  # noqa: E402
    CLAIM_ID,
    PROTOCOL_ID,
    SOURCE_PIN,
    evaluate,
    write_fixtures,
)
from swarm_witness.evidence_index import generate_and_write_index  # noqa: E402
from swarm_witness.schema import validate_finding, validate_run  # noqa: E402

RUN_ID = "eval-integrity-replay-v1-run"
FINDING_ID = "eval-integrity-replay-v1-f"
EV = ROOT / "evidence" / "eval_integrity_replay_v1"


def main() -> dict:
    manifest = write_fixtures(ROOT)
    rows, totals, interventions = evaluate()
    swarm = totals["by_method"]["swarm_witness"]
    naive = totals["by_method"]["naive_pass"]
    intervention_pass = all(i["passed"] for i in interventions)
    external_rows = [
        r
        for r in rows
        if r["method"] == "swarm_witness" and not r.get("synthetic")
    ]
    # The pinned judge does not order source access against scored behavior
    # and does not independently verify target success.
    ordering_established = False
    retained_valid = False
    conclusion_change = False
    headline_eligible = False
    label_replay_abstains = all(r["predicted"] == "unresolved" for r in external_rows)

    observations = {
        "passed": (
            swarm["false_support"] == 0
            and label_replay_abstains
            and intervention_pass
            and headline_eligible is False
            and retained_valid is False
        ),
        "study_kind": "label_replay",
        "manifest_id": manifest["id"],
        "git_sha": next(
            s["revision"] for s in manifest["sources"] if s["id"] == "git_reproduction"
        ),
        "hf_sha": next(
            s["revision"]
            for s in manifest["sources"]
            if s["id"] == "hf_replication_dataset"
        ),
        "denominator": manifest["denominator"],
        "totals": totals,
        "interventions": interventions,
        "intervention_pass": intervention_pass,
        "conclusion_change": conclusion_change,
        "retained_valid_success": retained_valid,
        "ordering_established": ordering_established,
        "label_replay_abstains": label_replay_abstains,
        "swarm_false_support": swarm["false_support"],
        "naive_false_support": naive["false_support"],
        "headline_eligible": headline_eligible,
        "real_world_authenticity_certified": False,
        "detection_or_prevention_claimed": False,
        "transfer_claim": False,
        "original_incident_logs_available": False,
    }

    run = {
        "id": RUN_ID,
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "eval-integrity-matrix",
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "observations": observations,
    }
    validate_run(run)

    finding = {
        "id": FINDING_ID,
        "claim_id": CLAIM_ID,
        "run_ids": [RUN_ID],
        "proposition": (
            "On the pinned envsrc judge labels, source-access is replayed "
            "without establishing exposure-before-scored-behavior or an "
            "independent successful outcome. Headline eligibility stays false."
            if observations["passed"]
            else "Eval-integrity label replay failed a declared acceptance check."
        ),
        "scope": (
            "Released reproduction analysis and Hub trajectories pinned in "
            "experiments/eval_integrity_replay/corpus_manifest.json; not "
            "original private incident logs; not live prevention."
        ),
        "label": "reproduced" if observations["passed"] else "contradicted_in_scope",
        "conclusion_class": "supported" if observations["passed"] else "failed_enforcement",
        "basis": "computed",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.passed",
            f"{RUN_ID}.observations.conclusion_change",
            f"{RUN_ID}.observations.swarm_false_support",
            f"{RUN_ID}.observations.intervention_pass",
        ],
    }
    validate_finding(finding)

    runs_dir = EV / "runs"
    findings_dir = EV / "findings"
    runs_dir.mkdir(parents=True, exist_ok=True)
    findings_dir.mkdir(parents=True, exist_ok=True)
    for path in runs_dir.glob("*.json"):
        path.unlink()
    for path in findings_dir.glob("*.json"):
        path.unlink()
    (runs_dir / f"{RUN_ID}.json").write_text(
        json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (findings_dir / f"{FINDING_ID}.json").write_text(
        json.dumps(finding, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (EV / "rows.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (EV / "summary.json").write_text(
        json.dumps(
            {
                "passed": observations["passed"],
                "totals": totals,
                "interventions": interventions,
                "manifest": {
                    "id": manifest["id"],
                    "denominator": manifest["denominator"],
                    "frozen_case_ids": manifest["frozen_case_ids"],
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (EV / "REPORT.md").write_text(
        "\n".join(
            [
                "# Eval integrity replay v1",
                "",
                f"Protocol `{PROTOCOL_ID}`. Issue #50.",
                "",
                f"- git pin: `{observations['git_sha']}`",
                f"- HF pin: `{observations['hf_sha']}`",
                f"- frozen cases: {manifest['denominator']['frozen_scored_cases']}",
                f"- judge denominator: {manifest['denominator']['envsrc_judge_runs_total']}",
                f"- swarm false support: {swarm['false_support']}",
                f"- naive false support: {naive['false_support']}",
                f"- study kind: {observations['study_kind']}",
                f"- ordering established: {ordering_established}",
                f"- conclusion change: {conclusion_change}",
                f"- retained valid success: {retained_valid}",
                f"- interventions passed: {intervention_pass}",
                f"- overall passed: {observations['passed']}",
                f"- headline eligible: {observations['headline_eligible']}",
                "",
                "Label replay of released source-access judgments. "
                "Does not establish exposure before scored behavior or a verified success. "
                "Original private incident logs unavailable. Transfer/detection/prevention false.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    generate_and_write_index(ROOT)
    print(json.dumps({"passed": observations["passed"], "totals": totals}, indent=2))
    return observations


if __name__ == "__main__":
    main()
