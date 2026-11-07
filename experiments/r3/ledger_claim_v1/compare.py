#!/usr/bin/env python3
"""Three-stage comparator for r3-ledger-claim-v1.

1. Pair validity
2. Property outcome (per backend)
3. Cross-backend agreement
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))

from protocol import (  # noqa: E402
    CLAIM_ID,
    PROTOCOL_ID,
    evaluate_case_property,
    load_cases,
    project_state,
    validate_step_observation,
)
from swarm_witness.schema import validate_finding  # noqa: E402


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(obj)
    return rows


def pair_validity(
    *,
    cases: list[Any],
    classical_steps: list[dict[str, Any]],
    bmo_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    pairs: list[dict[str, Any]] = []

    def index(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
        out: dict[tuple[str, int], dict[str, Any]] = {}
        for row in rows:
            try:
                obs = validate_step_observation(row)
            except ValueError as exc:
                errors.append(f"invalid observation: {exc}")
                continue
            key = (obs.case_id, obs.step)
            if key in out:
                errors.append(f"duplicate observation for {key}")
            out[key] = obs.to_dict()
        return out

    c_idx = index(classical_steps)
    b_idx = index(bmo_steps)

    for case in cases:
        for action in case.actions:
            key = (case.case_id, action.step)
            c = c_idx.get(key)
            b = b_idx.get(key)
            pair: dict[str, Any] = {
                "case_id": case.case_id,
                "step": action.step,
                "op": action.op,
                "classical_present": c is not None,
                "bmo_present": b is not None,
                "valid": True,
                "notes": [],
            }
            if c is None or b is None:
                pair["valid"] = False
                pair["notes"].append("missing arm observation")
                errors.append(f"{case.case_id} step {action.step}: missing arm")
            else:
                if c.get("execution_status") != "completed" or b.get("execution_status") != "completed":
                    pair["valid"] = False
                    pair["notes"].append("incomplete execution_status")
                    errors.append(
                        f"{case.case_id} step {action.step}: incomplete execution_status"
                    )
                # Input mismatch is not a policy disagreement.
                if action.op == "claim_first_edit":
                    c_in = c.get("inputs") or {}
                    b_in = b.get("inputs") or {}
                    shared_keys = (
                        "call_id",
                        "task_id",
                        "grant_id",
                        "owner_revision",
                        "retry_epoch",
                        "transaction_completion",
                    )
                    for sk in shared_keys:
                        if c_in.get(sk) != b_in.get(sk):
                            pair["valid"] = False
                            pair["notes"].append(f"input mismatch on {sk}")
                            errors.append(
                                f"{case.case_id} step {action.step}: input mismatch {sk}"
                            )
            pairs.append(pair)

    return {
        "valid": not errors and all(p["valid"] for p in pairs),
        "errors": errors,
        "pairs": pairs,
    }


def property_outcomes(
    cases: list[Any],
    *,
    classical_steps: list[dict[str, Any]],
    bmo_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    def by_case(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            out.setdefault(str(row.get("case_id")), []).append(row)
        for cid in out:
            out[cid].sort(key=lambda r: int(r.get("step") or 0))
        return out

    c_by = by_case(classical_steps)
    b_by = by_case(bmo_steps)
    results: dict[str, Any] = {"classical": {}, "bmo": {}}
    for case in cases:
        results["classical"][case.case_id] = evaluate_case_property(
            case, c_by.get(case.case_id, [])
        )
        results["bmo"][case.case_id] = evaluate_case_property(
            case, b_by.get(case.case_id, [])
        )
    return results


def agreement(
    cases: list[Any],
    *,
    classical_steps: list[dict[str, Any]],
    bmo_steps: list[dict[str, Any]],
    validity: dict[str, Any],
) -> dict[str, Any]:
    if not validity.get("valid"):
        return {
            "result": "unresolved",
            "reason": "pair validity failed",
            "case_results": {},
        }

    def last_state(rows: list[dict[str, Any]], case_id: str) -> dict[str, Any] | None:
        case_rows = [r for r in rows if r.get("case_id") == case_id]
        inspects = [r for r in case_rows if r.get("op") == "inspect"]
        target = inspects[-1] if inspects else (case_rows[-1] if case_rows else None)
        if target is None:
            return None
        return project_state(target.get("state"))

    case_results: dict[str, Any] = {}
    equal_all = True
    for case in cases:
        c_state = last_state(classical_steps, case.case_id)
        b_state = last_state(bmo_steps, case.case_id)
        equal = c_state is not None and c_state == b_state
        if not equal:
            equal_all = False
        case_results[case.case_id] = {
            "equal": equal,
            "classical": c_state,
            "bmo": b_state,
        }

    if equal_all:
        return {"result": "matched", "reason": "equal projections", "case_results": case_results}
    return {
        "result": "divergent",
        "reason": "property-relevant projections differ",
        "case_results": case_results,
    }


def classify_finding(
    *,
    validity: dict[str, Any],
    properties: dict[str, Any],
    agree: dict[str, Any],
    run_ids: list[str],
    native_bmo: bool = True,
) -> dict[str, Any]:
    """Map comparator stages onto Finding labels.

    matched → classical_baseline_matches only as equality statement.
    divergent → contradicted_in_scope only for the agreement proposition.
    missing/corrupt → unresolved.
    Offline (non-native) BMO stand-in cannot upgrade beyond unresolved.
    """
    if not native_bmo:
        label = "unresolved"
        proposition = (
            "Native BMO ClaimOrdinaryRetainedGrantFirstEditTx was not measured "
            "(offline SQLite L1 stand-in or missing bridge); ledger-claim comparison "
            "remains unresolved for the BMO pin"
        )
    elif not validity.get("valid") or agree.get("result") == "unresolved":
        label = "unresolved"
        proposition = (
            "Matched ledger-claim comparison incomplete: required paired "
            "observations missing, corrupt, or input-mismatched"
        )
    elif agree.get("result") == "divergent":
        label = "contradicted_in_scope"
        proposition = (
            "Backends disagree on the property-relevant projection for one or "
            "more r3-ledger-claim-v1 cases"
        )
    else:
        # matched projections
        both_pass = all(
            properties["classical"][cid]["passed"] and properties["bmo"][cid]["passed"]
            for cid in properties["classical"]
        )
        both_fail = all(
            (not properties["classical"][cid]["passed"])
            and (not properties["bmo"][cid]["passed"])
            for cid in properties["classical"]
        )
        label = "classical_baseline_matches"
        if both_pass:
            proposition = (
                "Across declared synthetic cases, ClassicalLedgerGate and BMO L1 "
                "emitted equal property-relevant observations and both satisfied "
                "the one-use ledger-claim trace properties"
            )
        elif both_fail:
            proposition = (
                "Backends agree on property-relevant projections but both fail "
                "trace properties (agreement is not successful enforcement)"
            )
        else:
            # Equal projections but mixed property outcomes should be rare;
            # treat as equality-only match with note.
            proposition = (
                "Backends agree on property-relevant projections; per-backend "
                "property outcomes differ or are mixed"
            )

    finding = {
        "id": "r3-ledger-claim-v1-comparison",
        "claim_id": CLAIM_ID,
        "run_ids": run_ids or ["r3-ledger-claim-v1-no-runs"],
        "proposition": proposition,
        "scope": (
            "r3-ledger-claim-v1 L1 first-edit claim/transfer under cold DB reopen "
            "and explicit rollback; not external execute/settle or process restart"
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            "r3-ledger-meta.observations.agreement.result",
            "r3-ledger-meta.observations.validity.valid",
        ],
    }
    # Schema requires resolvable refs for non-unresolved labels. Runner may
    # rewrite these after meta observations are finalized.
    validate_finding(finding)
    return finding


def compare_run(run_dir: Path, cases_path: Path | None = None) -> dict[str, Any]:
    run_dir = Path(run_dir)
    cases_path = cases_path or (Path(__file__).resolve().parent / "cases.yaml")
    bundle = load_cases(cases_path)
    cases = bundle["cases"]

    classical_path = run_dir / "classical.ndjson"
    bmo_path = run_dir / "bmo.ndjson"
    classical_steps = load_ndjson(classical_path)
    bmo_steps = load_ndjson(bmo_path)

    # Truncated / stale / package-log-only must not succeed.
    if not classical_steps and not bmo_steps:
        validity = {
            "valid": False,
            "errors": ["no observations on either arm"],
            "pairs": [],
        }
    else:
        validity = pair_validity(
            cases=cases, classical_steps=classical_steps, bmo_steps=bmo_steps
        )

    properties = property_outcomes(
        cases, classical_steps=classical_steps, bmo_steps=bmo_steps
    )
    agree = agreement(
        cases,
        classical_steps=classical_steps,
        bmo_steps=bmo_steps,
        validity=validity,
    )

    run_ids: list[str] = []
    runs_dir = run_dir / "runs"
    if runs_dir.is_dir():
        run_ids = sorted(p.stem for p in runs_dir.glob("*.json"))

    manifest_path = run_dir / "source_manifest.json"
    native_bmo = True
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            native_bmo = bool((manifest.get("bmo") or {}).get("native_bmo"))
        except (OSError, json.JSONDecodeError, TypeError):
            native_bmo = False

    finding = classify_finding(
        validity=validity,
        properties=properties,
        agree=agree,
        run_ids=run_ids,
        native_bmo=native_bmo,
    )

    summary = {
        "protocol_id": PROTOCOL_ID,
        "claim_id": CLAIM_ID,
        "run_dir": str(run_dir),
        "validity": validity,
        "properties": properties,
        "agreement": agree,
        "native_bmo": native_bmo,
        "finding": finding,
    }
    return summary


def write_compare_artifacts(run_dir: Path, summary: dict[str, Any]) -> None:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    findings_dir = run_dir / "findings"
    findings_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    finding = summary["finding"]
    (findings_dir / f"{finding['id']}.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )
    result = {
        "claim_id": CLAIM_ID,
        "label": finding["label"],
        "authoritative": "finding",
        "finding_path": f"findings/{finding['id']}.json",
        # Avoid metric keys that collide with r3-ledger-meta observation names
        # (evidence_index requires exact equality when names overlap).
        "metrics": {
            "classical_pass_count": sum(
                1 for v in summary["properties"]["classical"].values() if v["passed"]
            ),
            "bmo_pass_count": sum(
                1 for v in summary["properties"]["bmo"].values() if v["passed"]
            ),
            "native_bmo": bool(summary.get("native_bmo")),
        },
        "notes": summary["agreement"].get("reason"),
    }
    (run_dir / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).resolve().parent / "cases.yaml",
    )
    args = parser.parse_args(argv)
    summary = compare_run(args.run_dir, cases_path=args.cases)
    write_compare_artifacts(args.run_dir, summary)
    print(
        json.dumps(
            {
                "label": summary["finding"]["label"],
                "agreement": summary["agreement"]["result"],
                "validity": summary["validity"]["valid"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
