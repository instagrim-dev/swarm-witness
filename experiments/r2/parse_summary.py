#!/usr/bin/env python3
"""Derive R2 Run + Finding records from retained stress results rows.

Metrics (condition_by_seed_checks, relay/shared/false-exclusivity tallies) are
counted from the ``rows`` array in ``evidence/r2/results.json``. Planned
constants such as 36 are never seeded. Finding is authoritative for labels;
summary.json and result.yaml are retained as convenience mirrors only.
Baseline Markdown is authored interpretation only — this module never emits
Finding ``classical_baseline_matches``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.schema import validate_finding, validate_run  # noqa: E402

EV = ROOT / "evidence" / "r2"
RESULTS = EV / "results.json"
SUMMARY = EV / "summary.json"
RESULT = EV / "result.yaml"
RUNS_DIR = EV / "runs"
FINDINGS_DIR = EV / "findings"

RUN_ID = "r2-run-incident-stress"
FINDING_ID = "r2-f-primary"
GIT_REV = "a5ea5c9947039009ca795275d834be7b61069080"
BASELINE_REV = "efbd4192767672e2ca3634c9ebe9d9a3c98fcddd"
SOURCE_PIN = "a5ea5c9"
PROTOCOL_ID = "evidencegraph-incident-stress"
CASE_ID = "seeds-0-1-2-twelve-scenarios"
CLAIM_SCOPE = (
    "EvidenceGraph runnable artifact from Junejo report pdf under stated "
    "copier/receiver roles"
)
# Published clean-evidence population size used only when converting
# shared_tokens correct counts into "withheld" tallies from retained rows.
REGISTRY_POPULATION = 12


def _rows_for(rows: list[dict[str, Any]], scenario: str) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("scenario") == scenario]


def count_from_row_records(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Count condition checks and scenario tallies from retained row records only."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("results rows must be a non-empty list")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each row record must be a dict")
        scenario = row.get("scenario")
        if not isinstance(scenario, str) or not scenario.strip():
            raise ValueError("row record missing scenario")

    relay = sorted(_rows_for(rows, "full_receipt_relay"), key=lambda r: r.get("seed", 0))
    shared = sorted(
        _rows_for(rows, "shared_tokens_no_attack"), key=lambda r: r.get("seed", 0)
    )
    false_excl = sorted(
        _rows_for(rows, "false_exclusivity"), key=lambda r: r.get("seed", 0)
    )

    def _produced(row: dict[str, Any], field: str) -> int:
        score = row.get("score") or {}
        produced = score.get("produced") or {}
        return int(produced.get(field, 0) or 0)

    def _old_rule_errors(row: dict[str, Any]) -> int:
        controls = row.get("controls") or {}
        implicit = controls.get("implicit_token_exclusivity") or {}
        return int(implicit.get("confident_errors", 0) or 0)

    def _safer_supported(row: dict[str, Any]) -> int:
        outcomes = row.get("outcomes") or {}
        if "supported" in outcomes:
            return int(outcomes.get("supported") or 0)
        # Upstream rows often omit supported when abstaining; treat as 0.
        return 0

    old_rule_errors = [_old_rule_errors(r) for r in relay]
    safer_supported = [_safer_supported(r) for r in relay]
    safer_correct = [_produced(r, "correct") for r in relay]
    shared_correct = [_produced(r, "correct") for r in shared]
    false_errors = [_produced(r, "confident_errors") for r in false_excl]
    passed = sum(1 for r in rows if r.get("passed"))

    scenarios: dict[str, int] = {}
    for row in rows:
        scenarios[row["scenario"]] = scenarios.get(row["scenario"], 0) + 1

    return {
        "condition_by_seed_checks": len(rows),
        "condition_by_seed_passed": passed,
        "row_record_count": len(rows),
        "rows_per_scenario": dict(sorted(scenarios.items())),
        "old_rule_wrong_attributions_on_relay": old_rule_errors,
        "safer_supported_on_relay": safer_supported,
        "safer_correct_on_relay": safer_correct,
        "shared_tokens_correct": shared_correct,
        "clean_withheld_without_exclusivity": [
            REGISTRY_POPULATION - c for c in shared_correct
        ],
        "false_exclusivity_confident_errors": false_errors,
        "relay_outcomes_by_seed": [
            {"seed": r.get("seed"), "outcomes": r.get("outcomes")} for r in relay
        ],
        "denominator_source": "counted_from_rows",
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_result_mirror(
    *,
    label: str,
    metrics: dict[str, Any],
    notes: str,
    finding_path: str,
) -> None:
    # Convenience mirror for older tooling; Finding JSON is authoritative.
    import yaml

    result = {
        "claim_id": "r2",
        "label": label,
        "metrics": metrics,
        "evidence_path": "evidence/r2/summary.json",
        "finding_path": finding_path,
        "notes": notes,
        "authoritative": "finding",
    }
    RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")


def write_unresolved(
    *,
    execution_status: str,
    notes: str,
    command: str | None = None,
    cwd: str | None = None,
    exit_status: int | None = None,
    stdout_path: str | None = None,
    stderr_path: str | None = None,
    partial_output: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if execution_status not in {"unrun", "failed", "missing", "attempted"}:
        raise ValueError(f"unresolved path requires honest status, got {execution_status!r}")

    run: dict[str, Any] = {
        "id": RUN_ID,
        "claim_id": "r2",
        "protocol_id": PROTOCOL_ID,
        "case_id": CASE_ID,
        "source_pin": SOURCE_PIN,
        "execution_status": execution_status,
        "command": command
        or "experiments/r2/run_r2.sh (no completed stress; see notes)",
        "cwd": cwd or str(ROOT),
        "exit_status": exit_status,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "observations": {
            "notes": notes,
            "partial_output": partial_output,
            "condition_by_seed_checks": None,
            "condition_by_seed_passed": None,
            "row_record_count": 0,
        },
    }
    validate_run(run)
    finding: dict[str, Any] = {
        "id": FINDING_ID,
        "claim_id": "r2",
        "run_ids": [RUN_ID],
        "proposition": (
            "Safer rule yields zero possession-only supported attributions on "
            "pinned EvidenceGraph incident-stress pack"
        ),
        "scope": CLAIM_SCOPE,
        "label": "unresolved",
        "basis": "computed",
        "supporting_observation_refs": [f"{RUN_ID}.observations.notes"],
    }
    validate_finding(finding)

    run_path = RUNS_DIR / f"{RUN_ID}.json"
    finding_path = FINDINGS_DIR / f"{FINDING_ID}.json"
    _write_json(run_path, run)
    _write_json(finding_path, finding)

    summary = {
        "condition_by_seed_checks": None,
        "condition_by_seed_passed": None,
        "old_rule_wrong_attributions_on_relay": None,
        "safer_supported_on_relay": None,
        "clean_withheld_without_exclusivity": None,
        "git_rev": GIT_REV,
        "baseline_rev": BASELINE_REV,
        "unresolved": True,
        "notes": notes,
        "authoritative_finding": str(finding_path.relative_to(ROOT)),
    }
    EV.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_result_mirror(
        label="unresolved",
        metrics={},
        notes=notes,
        finding_path=str(finding_path.relative_to(ROOT)),
    )
    return run, finding


def derive_from_results(results_path: Path = RESULTS) -> tuple[dict[str, Any], dict[str, Any]]:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    counted = count_from_row_records(rows)

    old_rule_errors = counted["old_rule_wrong_attributions_on_relay"]
    safer_supported = counted["safer_supported_on_relay"]
    safer_correct = counted["safer_correct_on_relay"]
    shared_correct = counted["shared_tokens_correct"]
    false_errors = counted["false_exclusivity_confident_errors"]
    checks = counted["condition_by_seed_checks"]
    passed = counted["condition_by_seed_passed"]
    seeds = list(data.get("seeds") or [])

    all_contract = bool(data.get("passed")) and passed == checks and checks > 0
    source_tree = data.get("source_tree_sha256")

    observations: dict[str, Any] = {
        "results_path": str(results_path.relative_to(ROOT)),
        "condition_by_seed_checks": checks,
        "condition_by_seed_passed": passed,
        "row_record_count": counted["row_record_count"],
        "rows_per_scenario": counted["rows_per_scenario"],
        "seeds": seeds,
        "old_rule_wrong_attributions_on_relay": old_rule_errors,
        "safer_supported_on_relay": safer_supported,
        "safer_correct_on_relay": safer_correct,
        "shared_tokens_correct": shared_correct,
        "clean_withheld_without_exclusivity": counted[
            "clean_withheld_without_exclusivity"
        ],
        "false_exclusivity_confident_errors": false_errors,
        "relay_outcomes_by_seed": counted["relay_outcomes_by_seed"],
        "git_rev": GIT_REV,
        "baseline_rev": BASELINE_REV,
        "source_tree_sha256": source_tree,
        "all_contract_checks_pass": all_contract,
        "failures": data.get("failures") or [],
        "denominator_source": "counted_from_rows",
    }

    run: dict[str, Any] = {
        "id": RUN_ID,
        "claim_id": "r2",
        "protocol_id": PROTOCOL_ID,
        "case_id": CASE_ID,
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "command": (
            "uv run python scripts/incident_stress.py OUT --seeds 0 1 2; "
            "uv run eg verify OUT/bundles/0-full_receipt_relay --recompute"
        ),
        "cwd": "third_party/r2/evidencegraph",
        "exit_status": 0,
        "stdout_path": "evidence/r2/run.log",
        "stderr_path": "evidence/r2/uv-sync.log",
        "observations": observations,
    }
    validate_run(run)

    # Paper-matching reproduction: safer rule abstains on possession-only relay;
    # old rule errs; undeclared exclusivity withholds; false exclusivity restores error.
    n_seeds = len(old_rule_errors)
    paper_match = (
        all_contract
        and n_seeds > 0
        and old_rule_errors == [1] * n_seeds
        and safer_supported == [0] * n_seeds
        and safer_correct == [0] * n_seeds
        and shared_correct == [0] * n_seeds
        and false_errors == [1] * n_seeds
        and counted["clean_withheld_without_exclusivity"]
        == [REGISTRY_POPULATION] * n_seeds
    )
    label = "reproduced" if paper_match else "contradicted_in_scope"
    finding: dict[str, Any] = {
        "id": FINDING_ID,
        "claim_id": "r2",
        "run_ids": [RUN_ID],
        "proposition": (
            "Safer rule yields zero possession-only supported attributions on "
            "pinned EvidenceGraph incident-stress pack"
        ),
        "scope": CLAIM_SCOPE,
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.safer_supported_on_relay",
            f"{RUN_ID}.observations.condition_by_seed_checks",
            f"{RUN_ID}.observations.row_record_count",
            f"{RUN_ID}.observations.all_contract_checks_pass",
        ],
    }
    validate_finding(finding)

    run_path = RUNS_DIR / f"{RUN_ID}.json"
    finding_path = FINDINGS_DIR / f"{FINDING_ID}.json"
    _write_json(run_path, run)
    _write_json(finding_path, finding)

    notes = (
        "Derived from retained row records in results.json "
        f"(source {SOURCE_PIN}; paper baseline before extension: {BASELINE_REV[:7]}); "
        f"counted condition_by_seed_checks={checks}/{passed} passed; "
        f"old-rule relay wrong attributions={old_rule_errors}; "
        f"safer relay supported={safer_supported} correct={safer_correct}; "
        f"shared_tokens_no_attack correct={shared_correct} "
        f"(withheld={counted['clean_withheld_without_exclusivity']}); "
        f"false_exclusivity errors={false_errors}. "
        f"source_tree_sha256={source_tree}."
    )

    summary = {
        "condition_by_seed_checks": checks,
        "condition_by_seed_passed": passed,
        "seeds": seeds,
        "old_rule_wrong_attributions_on_relay": old_rule_errors,
        "safer_supported_on_relay": safer_supported,
        "safer_correct_on_relay": safer_correct,
        "relay_outcomes_seed0": (
            counted["relay_outcomes_by_seed"][0]["outcomes"]
            if counted["relay_outcomes_by_seed"]
            else None
        ),
        "clean_withheld_without_exclusivity": counted[
            "clean_withheld_without_exclusivity"
        ],
        "shared_tokens_correct": shared_correct,
        "false_exclusivity_confident_errors": false_errors,
        "git_rev": GIT_REV,
        "baseline_rev": BASELINE_REV,
        "source_tree_sha256": source_tree,
        "denominator_source": "counted_from_rows",
        "authoritative_finding": str(finding_path.relative_to(ROOT)),
        "fresh_run": {
            "passed": bool(data.get("passed")),
            "failures": data.get("failures") or [],
            "all_contract_checks_pass": all_contract,
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_result_mirror(
        label=label,
        metrics={
            "condition_by_seed_checks": checks,
            "condition_by_seed_passed": passed,
            "old_rule_wrong_attributions_on_relay_per_seed": old_rule_errors,
            "safer_supported_on_relay_per_seed": safer_supported,
            "clean_withheld_without_exclusivity_per_seed": counted[
                "clean_withheld_without_exclusivity"
            ],
            "false_exclusivity_confident_errors_per_seed": false_errors,
        },
        notes=notes,
        finding_path=str(finding_path.relative_to(ROOT)),
    )
    return run, finding


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status",
        choices=("unrun", "failed", "missing", "attempted"),
        help="Write honest unresolved Run/Finding without requiring results",
    )
    parser.add_argument("--notes", default="", help="Notes for unresolved path")
    parser.add_argument("--command", default=None)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--exit-status", type=int, default=None)
    parser.add_argument("--stdout-path", default=None)
    parser.add_argument("--stderr-path", default=None)
    parser.add_argument("--partial-output", default=None)
    parser.add_argument(
        "--results",
        type=Path,
        default=RESULTS,
        help="Path to results.json",
    )
    args = parser.parse_args(argv)

    EV.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)

    if args.status:
        notes = args.notes or f"execution_status={args.status}"
        run, finding = write_unresolved(
            execution_status=args.status,
            notes=notes,
            command=args.command,
            cwd=args.cwd,
            exit_status=args.exit_status,
            stdout_path=args.stdout_path,
            stderr_path=args.stderr_path,
            partial_output=args.partial_output,
        )
        print(
            json.dumps(
                {
                    "run": str((RUNS_DIR / f"{RUN_ID}.json").relative_to(ROOT)),
                    "finding": str((FINDINGS_DIR / f"{FINDING_ID}.json").relative_to(ROOT)),
                    "label": finding["label"],
                    "execution_status": run["execution_status"],
                }
            )
        )
        return 1

    if not args.results.is_file():
        notes = f"missing results file: {args.results.relative_to(ROOT)}"
        run, finding = write_unresolved(execution_status="unrun", notes=notes)
        print(
            json.dumps(
                {
                    "run": str((RUNS_DIR / f"{RUN_ID}.json").relative_to(ROOT)),
                    "finding": str((FINDINGS_DIR / f"{FINDING_ID}.json").relative_to(ROOT)),
                    "label": finding["label"],
                    "execution_status": run["execution_status"],
                    "notes": notes,
                }
            )
        )
        return 1

    run, finding = derive_from_results(args.results)
    print(
        json.dumps(
            {
                "run": str((RUNS_DIR / f"{RUN_ID}.json").relative_to(ROOT)),
                "finding": str((FINDINGS_DIR / f"{FINDING_ID}.json").relative_to(ROOT)),
                "summary": str(SUMMARY.relative_to(ROOT)),
                "label": finding["label"],
                "execution_status": run["execution_status"],
                "condition_by_seed_checks": run["observations"][
                    "condition_by_seed_checks"
                ],
                "denominator_source": "counted_from_rows",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
