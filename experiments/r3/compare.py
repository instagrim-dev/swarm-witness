#!/usr/bin/env python3
"""R3 matched decision-model comparison from shared cases.yaml.

ClassicalGate decisions are computed per case. BMO decisions come only from
matching test assertions or the instrumented harness — never from package
pass/fail counts. Missing BMO cases block ``classical_baseline_matches``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from swarm_witness.classical_gate import ClassicalGate
from swarm_witness.schema import validate_finding, validate_run

ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = Path(__file__).resolve().parent / "cases.yaml"
PINS_PATH = ROOT / "artifacts" / "pins.yaml"
EV = ROOT / "evidence" / "r3"
RUNS_DIR = EV / "runs"
FINDINGS_DIR = EV / "findings"
SUMMARY = EV / "summary.json"
RESULT = EV / "result.yaml"
BMO_LOG = EV / "bmo_go_test.log"
BASELINE_MD = ROOT / "baselines" / "r3_durable_grant_table.md"

CLAIM_ID = "r3"
PROTOCOL_ID = "r3-matched-decision-model"
FINDING_ID = "r3-f-comparison"


def load_cases(path: Path = CASES_PATH) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("cases"):
        raise ValueError("cases.yaml must contain a non-empty cases list")
    return data


def load_bmo_git_rev(pins_path: Path = PINS_PATH) -> str:
    pins = yaml.safe_load(pins_path.read_text(encoding="utf-8"))
    rev = pins.get("r3", {}).get("git_rev")
    if not isinstance(rev, str) or not rev.strip():
        raise ValueError("artifacts/pins.yaml r3.git_rev is required")
    return rev.strip()


def _case_record(
    *,
    case_id: str,
    arm: str,
    source_pin: str,
    execution_status: str,
    inputs: dict[str, Any],
    action: str,
    decision: str | None,
    evaluator_outcome: str,
    observation_refs: list[str],
    extra_observations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = f"{arm}-{case_id}"
    observations: dict[str, Any] = {
        "case_id": case_id,
        "inputs": dict(inputs),
        "action": action,
        "decision": decision,
        "effect": None,
        "evaluator_outcome": evaluator_outcome,
        "arm": arm,
        "observation_refs": list(observation_refs),
        "bmo_git_rev": source_pin if arm == "bmo" else None,
    }
    if extra_observations:
        observations.update(extra_observations)
    return {
        "id": run_id,
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": case_id,
        "source_pin": source_pin,
        "execution_status": execution_status,
        "observations": observations,
    }


def emit_classical_runs(
    cases_data: dict[str, Any] | None = None,
    *,
    source_pin: str | None = None,
) -> list[dict[str, Any]]:
    """Call ClassicalGate for each shared case; return validated Run dicts."""
    data = cases_data or load_cases()
    pin = source_pin or load_bmo_git_rev()
    runs: list[dict[str, Any]] = []
    for case in data["cases"]:
        case_id = case["case_id"]
        inputs = dict(case["inputs"])
        grant_row = case["classical"]["grant_row"]
        action_id = inputs["action_id"]
        request = inputs["request"]
        grant_version = int(inputs["grant_version"])
        gate = ClassicalGate.from_grants({action_id: grant_row})
        decision = gate.decide(
            action_id=action_id, request=request, grant_version=grant_version
        )
        expected = case["expected_decision"]
        evaluator_outcome = "ok" if decision == expected else "decision_mismatch"
        run = _case_record(
            case_id=case_id,
            arm="classical",
            source_pin=pin,
            execution_status="completed",
            inputs=inputs,
            action=request,
            decision=decision,
            evaluator_outcome=evaluator_outcome,
            observation_refs=[
                f"classical-{case_id}.observations.decision",
                f"classical-{case_id}.observations.inputs.grant_version",
            ],
            extra_observations={
                "grant_row": dict(grant_row),
                "expected_decision": expected,
                "claim_level": "decision_model",
                "epistemic_extension": case.get("epistemic_extension"),
            },
        )
        validate_run(run)
        runs.append(run)
    return runs


def probe_bmo_case(case: dict[str, Any]) -> dict[str, Any]:
    """Narrow instrumented harness probe for one BMO case.

    Returns decision only when an isomorphic observation is available.
    Declared ``isomorphism: none`` → missing (scientific honesty).
    Never invents allow/deny from package pass counts.
    """
    bmo = case.get("bmo") or {}
    source = bmo.get("observation_source")
    isomorphism = bmo.get("isomorphism")
    if source not in {"matching_test_assertion", "instrumented_harness"}:
        return {
            "execution_status": "failed",
            "decision": None,
            "evaluator_outcome": "invalid_observation_source",
            "note": f"unsupported observation_source: {source!r}",
        }
    if isomorphism != "isomorphic":
        return {
            "execution_status": "missing",
            "decision": None,
            "evaluator_outcome": "missing_isomorphic_observation",
            "note": (bmo.get("note") or "").strip()
            or "No isomorphic BMO observation for this case input shape.",
            "observation_source": source,
            "probe_id": bmo.get("probe_id"),
            "isomorphism": isomorphism,
        }
    # Future: matching assertion / harness that yields a real decision.
    return {
        "execution_status": "missing",
        "decision": None,
        "evaluator_outcome": "missing_isomorphic_observation",
        "note": "isomorphic probe not implemented for this case",
        "observation_source": source,
        "probe_id": bmo.get("probe_id"),
    }


def emit_bmo_runs(
    cases_data: dict[str, Any] | None = None,
    *,
    bmo_git_rev: str | None = None,
    package_pass_count: int | None = None,
) -> list[dict[str, Any]]:
    """Emit per-case BMO Run records via instrumented harness probes.

    ``package_pass_count`` is recorded as metadata only and must never become
    a decision source.
    """
    data = cases_data or load_cases()
    pin = bmo_git_rev or load_bmo_git_rev()
    runs: list[dict[str, Any]] = []
    for case in data["cases"]:
        case_id = case["case_id"]
        inputs = dict(case["inputs"])
        probe = probe_bmo_case(case)
        decision = probe.get("decision")
        status = probe["execution_status"]
        refs = [f"bmo-{case_id}.observations.evaluator_outcome"]
        if decision is not None:
            refs.insert(0, f"bmo-{case_id}.observations.decision")
        run = _case_record(
            case_id=case_id,
            arm="bmo",
            source_pin=pin,
            execution_status=status,
            inputs=inputs,
            action=inputs["request"],
            decision=decision,
            evaluator_outcome=probe["evaluator_outcome"],
            observation_refs=refs,
            extra_observations={
                "probe": {
                    k: v
                    for k, v in probe.items()
                    if k not in {"execution_status", "decision", "evaluator_outcome"}
                },
                "package_pass_count_metadata_only": package_pass_count,
                "decision_source": "instrumented_harness_probe",
                "epistemic_extension": case.get("epistemic_extension"),
                "expected_decision": case.get("expected_decision"),
            },
        )
        # Hard guard: pass counts must not fill decisions.
        if package_pass_count is not None and decision is not None:
            if probe.get("isomorphism") != "isomorphic":
                raise RuntimeError(
                    "refusing to emit BMO decision without isomorphic observation"
                )
        validate_run(run)
        runs.append(run)
    return runs


def _index_runs(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {r["case_id"]: r for r in runs}


def build_comparison_finding(
    *,
    cases: list[dict[str, Any]],
    classical_runs: list[dict[str, Any]],
    bmo_runs: list[dict[str, Any]],
    bmo_git_rev: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Pair classical/BMO case records; label from pairs only.

    Any missing/failed/unrun BMO case blocks ``classical_baseline_matches``.
    """
    classical_by = _index_runs(classical_runs)
    bmo_by = _index_runs(bmo_runs)
    pairs: list[dict[str, Any]] = []
    run_ids: list[str] = []
    supporting: list[str] = []
    missing_bmo = 0
    matched = 0
    completed_pairs = 0

    for case in cases:
        case_id = case["case_id"]
        c_run = classical_by.get(case_id)
        b_run = bmo_by.get(case_id)
        if c_run is None or b_run is None:
            pairs.append(
                {
                    "case_id": case_id,
                    "classical_status": None if c_run is None else c_run["execution_status"],
                    "bmo_status": "missing" if b_run is None else b_run["execution_status"],
                    "decision_match": False,
                    "note": "missing arm run record",
                }
            )
            missing_bmo += 1 if b_run is None else 0
            continue

        run_ids.extend([c_run["id"], b_run["id"]])
        c_obs = c_run["observations"]
        b_obs = b_run["observations"]
        c_status = c_run["execution_status"]
        b_status = b_run["execution_status"]
        c_decision = c_obs.get("decision")
        b_decision = b_obs.get("decision")

        inputs_match = c_obs.get("inputs") == b_obs.get("inputs")
        both_completed = c_status == "completed" and b_status == "completed"
        decision_match = (
            both_completed
            and inputs_match
            and c_decision is not None
            and c_decision == b_decision
        )
        if b_status in {"missing", "failed", "unrun"} or b_decision is None:
            missing_bmo += 1
        if both_completed:
            completed_pairs += 1
        if decision_match:
            matched += 1

        pair = {
            "case_id": case_id,
            "classical_status": c_status,
            "bmo_status": b_status,
            "classical_decision": c_decision,
            "bmo_decision": b_decision,
            "inputs_match": inputs_match,
            "decision_match": decision_match,
            "epistemic_extension": case.get("epistemic_extension"),
            "bmo_evaluator_outcome": b_obs.get("evaluator_outcome"),
        }
        pairs.append(pair)
        supporting.extend(
            [
                f"{c_run['id']}.observations.decision",
                f"{b_run['id']}.observations.evaluator_outcome",
            ]
        )

    if missing_bmo > 0:
        # Scientific honesty: incomplete isomorphic BMO coverage.
        label = "assumption_dependent"
        proposition = (
            "Matched ClassicalGate decision-model cases lack isomorphic BMO "
            "observations for one or more shared cases; classical_baseline_matches "
            "is not warranted"
        )
    elif completed_pairs == len(cases) and matched == len(cases):
        label = "classical_baseline_matches"
        proposition = (
            "All shared R3 cases completed on both arms with matching inputs "
            "and matching allow/deny decisions"
        )
    elif completed_pairs == len(cases) and matched < len(cases):
        label = "contradicted_in_scope"
        proposition = (
            "Shared R3 cases completed on both arms but decisions disagree "
            "on one or more cases"
        )
    else:
        label = "unresolved"
        proposition = "R3 matched comparison incomplete"

    finding = {
        "id": FINDING_ID,
        "claim_id": CLAIM_ID,
        "run_ids": run_ids or ["r3-no-runs"],
        "proposition": proposition,
        "scope": (
            f"R3 shared cases.yaml decision-model comparison at BMO "
            f"git_rev {bmo_git_rev}"
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": supporting
        or ["r3-comparison.pairs"],
    }
    # Schema requires non-empty run_ids / supporting refs — keep placeholders honest.
    if finding["run_ids"] == ["r3-no-runs"]:
        finding["supporting_observation_refs"] = ["r3-comparison.no_pairs"]
    validate_finding(finding)
    return finding, pairs


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_runs(runs: list[dict[str, Any]], runs_dir: Path = RUNS_DIR) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    for run in runs:
        write_json(runs_dir / f"{run['id']}.json", run)


def update_baseline_table(pairs: list[dict[str, Any]], label: str) -> None:
    if not BASELINE_MD.is_file():
        return
    table_lines = [
        "| Case | Classical | BMO | Match | BMO status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for p in pairs:
        table_lines.append(
            f"| {p['case_id']} | {p.get('classical_decision')} | "
            f"{p.get('bmo_decision')} | {p.get('decision_match')} | "
            f"{p.get('bmo_status')} |"
        )
    table_lines.append("")
    table_lines.append(f"Overall finding label: `{label}`.")
    body = BASELINE_MD.read_text(encoding="utf-8")
    marker = "## Discriminating comparison (from latest run)\n"
    if marker not in body:
        return
    head, _, rest = body.partition(marker)
    tail = ""
    if "\n## " in rest:
        _, tail = rest.split("\n## ", 1)
        tail = "\n## " + tail
    BASELINE_MD.write_text(
        head + marker + "\n" + "\n".join(table_lines) + "\n" + tail,
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-pass-count",
        type=int,
        default=None,
        help="Optional BMO package pass count metadata (never used as decisions)",
    )
    args = parser.parse_args(argv)

    EV.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)

    cases_data = load_cases()
    bmo_git_rev = load_bmo_git_rev()
    classical_runs = emit_classical_runs(cases_data, source_pin=bmo_git_rev)
    bmo_runs = emit_bmo_runs(
        cases_data,
        bmo_git_rev=bmo_git_rev,
        package_pass_count=args.package_pass_count,
    )
    write_runs(classical_runs)
    write_runs(bmo_runs)

    finding, pairs = build_comparison_finding(
        cases=cases_data["cases"],
        classical_runs=classical_runs,
        bmo_runs=bmo_runs,
        bmo_git_rev=bmo_git_rev,
    )
    write_json(FINDINGS_DIR / f"{FINDING_ID}.json", finding)

    matched = sum(1 for p in pairs if p.get("decision_match"))
    missing_bmo = sum(
        1 for p in pairs if p.get("bmo_status") in {"missing", "failed", "unrun", None}
    )
    summary = {
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "bmo_git_rev": bmo_git_rev,
        "cases_path": str(CASES_PATH.relative_to(ROOT)),
        "case_count": len(cases_data["cases"]),
        "matched_decisions": matched,
        "missing_bmo_cases": missing_bmo,
        "pairs": pairs,
        "finding_id": FINDING_ID,
        "label": finding["label"],
        "notes": (
            "Decision-model comparison only. BMO decisions require isomorphic "
            "observations; missing probes yield assumption_dependent, never "
            "classical_baseline_matches. Package pass counts are not decisions."
        ),
    }
    write_json(SUMMARY, summary)

    # Non-authoritative mirror for older tooling.
    result = {
        "claim_id": CLAIM_ID,
        "label": finding["label"],
        "authoritative": "finding",
        "finding_path": f"evidence/r3/findings/{FINDING_ID}.json",
        "metrics": {
            "case_count": summary["case_count"],
            "matched_decisions": matched,
            "missing_bmo_cases": missing_bmo,
        },
        "evidence_path": "evidence/r3/summary.json",
        "bmo_git_rev": bmo_git_rev,
        "notes": summary["notes"],
    }
    RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")
    update_baseline_table(pairs, finding["label"])

    print(
        json.dumps(
            {
                "label": finding["label"],
                "matched": f"{matched}/{len(pairs)}",
                "missing_bmo": missing_bmo,
                "bmo_git_rev": bmo_git_rev,
                "finding": str(FINDINGS_DIR / f"{FINDING_ID}.json"),
            }
        )
    )
    # Exit 0 when comparison ran honestly (including assumption_dependent).
    return 0 if finding["label"] in {
        "classical_baseline_matches",
        "assumption_dependent",
        "contradicted_in_scope",
    } else 1


if __name__ == "__main__":
    sys.exit(main())
