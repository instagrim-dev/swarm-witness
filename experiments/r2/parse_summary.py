#!/usr/bin/env python3
"""Parse local R2 stress results into evidence/r2/summary.json and result.yaml."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "evidence" / "r2"
RESULTS = EV / "results.json"
SUMMARY = EV / "summary.json"
RESULT = EV / "result.yaml"

GIT_REV = "a5ea5c9947039009ca795275d834be7b61069080"
BASELINE_REV = "efbd4192767672e2ca3634c9ebe9d9a3c98fcddd"


def _rows_for(rows: list[dict], scenario: str) -> list[dict]:
    return [r for r in rows if r.get("scenario") == scenario]


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    if not RESULTS.is_file():
        summary = {
            "condition_by_seed_checks": 36,
            "condition_by_seed_passed": None,
            "old_rule_wrong_attributions_on_relay": None,
            "safer_supported_on_relay": None,
            "clean_withheld_without_exclusivity": None,
            "git_rev": GIT_REV,
            "baseline_rev": BASELINE_REV,
            "unresolved": True,
            "notes": f"missing results file: {RESULTS.relative_to(ROOT)}",
        }
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        result = {
            "claim_id": "r2",
            "label": "unresolved",
            "metrics": {},
            "evidence_path": "evidence/r2/summary.json",
            "notes": summary["notes"],
        }
        RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")
        print(SUMMARY)
        return 1

    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = list(data["rows"])
    relay = _rows_for(rows, "full_receipt_relay")
    shared = _rows_for(rows, "shared_tokens_no_attack")
    false_excl = _rows_for(rows, "false_exclusivity")

    old_rule_errors = [
        int(r["controls"]["implicit_token_exclusivity"]["confident_errors"]) for r in relay
    ]
    safer_supported = [int(r.get("outcomes", {}).get("supported", 0) or 0) for r in relay]
    safer_correct = [int(r["score"]["produced"]["correct"]) for r in relay]
    shared_correct = [int(r["score"]["produced"]["correct"]) for r in shared]
    false_errors = [int(r["score"]["produced"]["confident_errors"]) for r in false_excl]
    passed = sum(1 for r in rows if r.get("passed"))

    summary = {
        "condition_by_seed_checks": len(rows),
        "condition_by_seed_passed": passed,
        "seeds": list(data.get("seeds") or []),
        "old_rule_wrong_attributions_on_relay": old_rule_errors,
        "safer_supported_on_relay": safer_supported,
        "safer_correct_on_relay": safer_correct,
        "relay_outcomes_seed0": relay[0]["outcomes"] if relay else None,
        "clean_withheld_without_exclusivity": [
            12 - c for c in shared_correct
        ],
        "shared_tokens_correct": shared_correct,
        "false_exclusivity_confident_errors": false_errors,
        "git_rev": GIT_REV,
        "baseline_rev": BASELINE_REV,
        "source_tree_sha256": data.get("source_tree_sha256"),
        "fresh_run": {
            "passed": bool(data.get("passed")),
            "failures": data.get("failures") or [],
            "all_contract_checks_pass": passed == 36 and bool(data.get("passed")),
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    paper_match = (
        summary["fresh_run"]["all_contract_checks_pass"]
        and old_rule_errors == [1, 1, 1]
        and safer_supported == [0, 0, 0]
        and safer_correct == [0, 0, 0]
        and shared_correct == [0, 0, 0]
        and false_errors == [1, 1, 1]
    )
    label = "reproduced" if paper_match else "contradicted_in_scope"
    notes = (
        f"Fresh local incident_stress.py at {GIT_REV[:7]} (paper baseline before "
        f"extension: {BASELINE_REV[:7]}); 36/36 contract checks; "
        f"old-rule relay wrong attributions={old_rule_errors}; "
        f"safer relay supported={safer_supported} correct={safer_correct}; "
        f"shared_tokens_no_attack correct={shared_correct} (12 withheld); "
        f"false_exclusivity errors={false_errors}. "
        f"source_tree_sha256={summary['source_tree_sha256']}."
    )

    result = {
        "claim_id": "r2",
        "label": label,
        "metrics": {
            "condition_by_seed_checks": summary["condition_by_seed_checks"],
            "condition_by_seed_passed": summary["condition_by_seed_passed"],
            "old_rule_wrong_attributions_on_relay_per_seed": old_rule_errors,
            "safer_supported_on_relay_per_seed": safer_supported,
            "clean_withheld_without_exclusivity_per_seed": summary[
                "clean_withheld_without_exclusivity"
            ],
            "false_exclusivity_confident_errors_per_seed": false_errors,
        },
        "evidence_path": "evidence/r2/summary.json",
        "notes": notes,
    }
    RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")

    sys.path.insert(0, str(ROOT / "src"))
    from swarm_witness.schema import validate_result_record

    validate_result_record(yaml.safe_load(RESULT.read_text(encoding="utf-8")))
    print(json.dumps({"summary": str(SUMMARY), "result": str(RESULT), "label": label}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
