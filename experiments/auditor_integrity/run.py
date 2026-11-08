#!/usr/bin/env python3
"""Run auditor-integrity v1 and publish evidence (issue #51)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.auditor_integrity import (  # noqa: E402
    CLAIM_ID,
    PROTOCOL_ID,
    SOURCE_PIN,
    build_cases,
    evaluate_from_disk,
    negative_mutations,
    summarize,
    validate_freeze,
    write_split_fixtures,
)
from swarm_witness.evidence_index import generate_and_write_index  # noqa: E402
from swarm_witness.schema import validate_finding, validate_run  # noqa: E402

RUN_ID = "auditor-integrity-v1-run"
FINDING_ID = "auditor-integrity-v1-f"
EV = ROOT / "evidence" / "auditor_integrity_v1"


def main() -> dict:
    digests = write_split_fixtures(ROOT)
    cases = build_cases()
    freeze = validate_freeze(cases)
    rows, totals = evaluate_from_disk(ROOT)
    mutations = negative_mutations()
    mutation_pass = all(m.get("passed", False) for m in mutations)

    swarm = totals["by_method"]["swarm_witness"]
    naive = totals["by_method"]["naive_pass"]
    checklist = totals["by_method"]["strong_checklist"]

    observations = {
        "passed": (
            freeze["case_count"] >= 12
            and swarm["false_support"] == 0
            and mutation_pass
            and swarm["correct_supported"] >= 2
            and swarm["correct_unresolved"] >= 2
        ),
        "freeze": freeze,
        "digests": digests,
        "totals": totals,
        "mutations": mutations,
        "mutation_pass": mutation_pass,
        "swarm_false_support": swarm["false_support"],
        "swarm_correct_supported": swarm["correct_supported"],
        "swarm_correct_refuted": swarm["correct_refuted"],
        "swarm_correct_unresolved": swarm["correct_unresolved"],
        "swarm_correct_decisive_coverage": swarm["correct_decisive_coverage"],
        "naive_false_support": naive["false_support"],
        "checklist_false_support": checklist["false_support"],
        "real_world_authenticity_certified": False,
        "detection_or_prevention_claimed": False,
        "synthetic_only": True,
        "external_trace_boundary": "issue_50",
    }

    run = {
        "id": RUN_ID,
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "auditor-integrity-matrix",
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
            "On a frozen synthetic auditor-integrity matrix, Swarm Witness "
            "records zero false supports while retaining supported positives "
            "and unresolved unknowns under the same evidence budget as a "
            "naive PASS shortcut and a strong checklist."
            if observations["passed"]
            else "Auditor-integrity matrix failed a declared acceptance check."
        ),
        "scope": (
            "Controlled synthetic packets under auditor-integrity-v1; not "
            "external reproduction traces and not a detection/prevention claim."
        ),
        "label": "reproduced" if observations["passed"] else "contradicted_in_scope",
        "basis": "computed",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.passed",
            f"{RUN_ID}.observations.swarm_false_support",
            f"{RUN_ID}.observations.swarm_correct_decisive_coverage",
            f"{RUN_ID}.observations.mutation_pass",
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
                "mutations": mutations,
                "freeze": freeze,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    report = EV / "REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# Auditor integrity v1",
                "",
                f"Protocol `{PROTOCOL_ID}`. Issue #51.",
                "",
                f"- cases: {freeze['case_count']}",
                f"- mechanisms: {', '.join(freeze['mechanisms'])}",
                f"- swarm false support: {swarm['false_support']}",
                f"- swarm correct supported: {swarm['correct_supported']}",
                f"- swarm correct refuted: {swarm['correct_refuted']}",
                f"- swarm correct unresolved: {swarm['correct_unresolved']}",
                f"- swarm decisive coverage: {swarm['correct_decisive_coverage']}",
                f"- naive false support: {naive['false_support']}",
                f"- checklist false support: {checklist['false_support']}",
                f"- mutation pass: {mutation_pass}",
                f"- overall passed: {observations['passed']}",
                "",
                "Synthetic controls only. External reproduction traces are issue #50.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    generate_and_write_index(ROOT)
    print(json.dumps({"passed": observations["passed"], "summary": totals}, indent=2))
    return observations


if __name__ == "__main__":
    main()
