#!/usr/bin/env python3
"""Compare staged claim and settlement observations.

Cross-arm equality uses the ledger projection and the shared settlement
contract. The applied and no-effect continuations are scored separately, so a
difference between those outcomes is not a cross-arm divergence.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

_LOCAL_PROTOCOL = HERE / "protocol.py"
_local_spec = importlib.util.spec_from_file_location(
    "ledger_settlement_v1_protocol_compare", _LOCAL_PROTOCOL
)
if _local_spec is None or _local_spec.loader is None:
    raise ImportError(f"cannot load {_LOCAL_PROTOCOL}")
_local_protocol = importlib.util.module_from_spec(_local_spec)
_local_spec.loader.exec_module(_local_protocol)
CLAIM_ID = _local_protocol.CLAIM_ID
PROTOCOL_ID = _local_protocol.PROTOCOL_ID
contract_conformant = _local_protocol.contract_conformant
effect_verdict = _local_protocol.effect_verdict
load_cases = _local_protocol.load_cases
settlement_projection = _local_protocol.settlement_projection
from swarm_witness.conclusion_classes import classify_matched_comparison  # noqa: E402
from swarm_witness.schema import validate_finding  # noqa: E402

_CLAIM_PROTOCOL = HERE.parent / "ledger_claim_v1" / "protocol.py"
_spec = importlib.util.spec_from_file_location("ledger_claim_v1_protocol_compare", _CLAIM_PROTOCOL)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load {_CLAIM_PROTOCOL}")
_claim_protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_claim_protocol)
project_ledger = _claim_protocol.project_state


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(obj)
    return rows


def _index(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    out: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        out[(str(row.get("case_id")), int(row.get("step") or 0))] = row
    return out


def _ledger(state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(state, dict):
        return None
    return project_ledger(state)


def _view(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    state = row.get("state") if isinstance(row.get("state"), dict) else None
    settlement = None if state is None else state.get("settlement")
    if settlement is not None and not isinstance(settlement, dict):
        settlement = None
    return {
        "disposition": row.get("disposition"),
        "ledger": _ledger(state),
        "settlement": settlement_projection(settlement),
        "effect_verdict": effect_verdict(state),
        "contract_conformant": contract_conformant(settlement) if settlement else False,
    }


def evaluate_arm(case: Any, steps: list[dict[str, Any]]) -> dict[str, Any]:
    by_step = {int(s["step"]): s for s in steps if isinstance(s, dict) and "step" in s}
    errors: list[str] = []
    for exp in case.expected.get("steps") or []:
        step_no = exp.get("step")
        obs = by_step.get(step_no)
        if obs is None:
            errors.append(f"missing step {step_no}")
            continue
        if obs.get("execution_status") != "completed":
            errors.append(f"step {step_no}: execution_status {obs.get('execution_status')!r}")
            continue
        if "disposition" in exp and obs.get("disposition") != exp["disposition"]:
            errors.append(
                f"step {step_no}: disposition {obs.get('disposition')!r} != {exp['disposition']!r}"
            )
        view = _view(obs)
        if "effect_verdict" in exp and view and view["effect_verdict"] != exp["effect_verdict"]:
            errors.append(
                f"step {step_no}: effect_verdict {view['effect_verdict']!r} != {exp['effect_verdict']!r}"
            )
        if "settlement_disposition" in exp:
            got = None if view is None or view["settlement"] is None else view["settlement"]["disposition"]
            if got != exp["settlement_disposition"]:
                errors.append(
                    f"step {step_no}: settlement_disposition {got!r} != {exp['settlement_disposition']!r}"
                )
            if view and not view["contract_conformant"]:
                errors.append(f"step {step_no}: settlement contract not satisfied")
    final = by_step.get(max(by_step)) if by_step else None
    ledger = None if final is None else _ledger(final.get("state"))
    expected_final = case.expected.get("final_state") or {}
    for key, want in expected_final.items():
        got = None if ledger is None else ledger.get(key)
        if got != want:
            errors.append(f"final {key}: {got!r} != {want!r}")
    return {"case_id": case.case_id, "passed": not errors, "errors": errors}


def pair_validity(cases: list[Any], classical: list[dict[str, Any]], bmo: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    c_idx = _index(classical)
    b_idx = _index(bmo)
    declared = {(case.case_id, action.step) for case in cases for action in case.actions}
    for source, idx in (("classical", c_idx), ("bmo", b_idx)):
        for key in idx:
            if key not in declared:
                errors.append(f"undeclared extra {source} observation for {key[0]} step {key[1]}")
            row = idx[key]
            if row.get("protocol_id") != PROTOCOL_ID:
                errors.append(f"{source} {key}: protocol_id {row.get('protocol_id')!r}")
    pairs = []
    for case in cases:
        for action in case.actions:
            key = (case.case_id, action.step)
            present = key in c_idx and key in b_idx
            if not present:
                errors.append(f"{case.case_id} step {action.step}: missing arm")
            pairs.append({"case_id": case.case_id, "step": action.step, "valid": present})
    return {"valid": not errors, "errors": errors, "pairs": pairs}


def agreement(cases: list[Any], classical: list[dict[str, Any]], bmo: list[dict[str, Any]], validity: dict[str, Any]) -> dict[str, Any]:
    if not validity.get("valid"):
        return {"result": "unresolved", "reason": "pair validity failed", "case_results": {}}
    c_idx = _index(classical)
    b_idx = _index(bmo)
    case_results: dict[str, Any] = {}
    equal_all = True
    for case in cases:
        steps = []
        case_equal = True
        for action in case.actions:
            c = _view(c_idx.get((case.case_id, action.step)))
            b = _view(b_idx.get((case.case_id, action.step)))
            equal = c is not None and b is not None and c["disposition"] == b["disposition"] and c["ledger"] == b["ledger"] and c["settlement"] == b["settlement"]
            if not equal:
                case_equal = False
                equal_all = False
            steps.append({
                "step": action.step,
                "op": action.op,
                "equal": equal,
                "classical": c,
                "bmo": b,
            })
        case_results[case.case_id] = {"equal": case_equal, "steps": steps}
    if equal_all:
        return {
            "result": "matched",
            "reason": "equal ledger projections and settlement contracts at every paired step",
            "case_results": case_results,
        }
    return {
        "result": "divergent",
        "reason": "disposition, ledger projection, or settlement contract differs at a paired step",
        "case_results": case_results,
    }


def evidence_stages(cases: list[Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    idx = _index(rows)
    out: dict[str, Any] = {}
    for case in cases:
        verdicts = []
        previous = None
        resolving = None
        for action in case.actions:
            row = idx.get((case.case_id, action.step))
            verdict = effect_verdict(None if row is None else row.get("state"))
            verdicts.append({"step": action.step, "op": action.op, "effect_verdict": verdict})
            if previous is not None and verdict != previous and resolving is None:
                resolving = {"step": action.step, "op": action.op, "from": previous, "to": verdict}
            previous = verdict
        out[case.case_id] = {"verdicts": verdicts, "resolving_observation": resolving}
    return out


def behavioral_difference(cases: list[Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    idx = _index(rows)
    outcomes = {}
    for case in cases:
        settle = next((a for a in case.actions if a.op.startswith("settle_")), None)
        if settle is None:
            continue
        view = _view(idx.get((case.case_id, settle.step)))
        outcomes[case.case_id] = None if view is None or view["settlement"] is None else view["settlement"]["disposition"]
    values = list(outcomes.values())
    return {
        "settlement_dispositions": outcomes,
        "continuations_differ": len(set(values)) > 1,
        "note": "Applied and no-effect records are different continuations. Their difference is not a cross-arm disagreement.",
    }


def compare_observations(cases: list[Any], classical: list[dict[str, Any]], bmo: list[dict[str, Any]], *, native_bmo: bool) -> dict[str, Any]:
    validity = pair_validity(cases, classical, bmo)
    properties = {
        "classical": {case.case_id: evaluate_arm(case, [r for r in classical if r.get("case_id") == case.case_id]) for case in cases},
        "bmo": {case.case_id: evaluate_arm(case, [r for r in bmo if r.get("case_id") == case.case_id]) for case in cases},
    }
    agree = agreement(cases, classical, bmo, validity)
    both_pass = all(
        properties["classical"][case.case_id]["passed"] and properties["bmo"][case.case_id]["passed"]
        for case in cases
    )
    if not native_bmo or not validity.get("valid"):
        classified = classify_matched_comparison(evidence_complete=False, arms_agree=None, property_holds=None)
    else:
        classified = classify_matched_comparison(
            evidence_complete=True,
            arms_agree=agree.get("result") == "matched",
            property_holds=both_pass,
        )
    stages = {
        "classical": evidence_stages(cases, classical),
        "bmo": evidence_stages(cases, bmo),
    }
    difference = {
        "classical": behavioral_difference(cases, classical),
        "bmo": behavioral_difference(cases, bmo),
    }
    return {
        "protocol_id": PROTOCOL_ID,
        "claim_id": CLAIM_ID,
        "validity": validity,
        "properties": properties,
        "agreement": agree,
        "evidence_stages": stages,
        "behavioral_difference": difference,
        "native_bmo": native_bmo,
        "conclusion_class": classified["conclusion_class"],
        "finding_label": classified["finding_label"],
        "both_arms_pass": both_pass,
    }


def build_finding(summary: dict[str, Any], run_ids: list[str]) -> dict[str, Any]:
    label = summary["finding_label"]
    cls = summary["conclusion_class"]
    if cls == "supported":
        proposition = (
            "After a committed retained-grant claim, the ledger view leaves the "
            "delegated effect unresolved. BMO's existing applied settlement supports "
            "that effect, and BMO's existing definite no-effect settlement refutes it. "
            "Both continuations match the classical settlement contract on the shared "
            "ledger prefix and on the continuation's own settlement record."
        )
    elif cls == "comparison_divergent":
        proposition = (
            "The classical settlement contract and the native BMO settlement record "
            "differ on a paired step. Equality is refused. Per-arm contract and "
            "evidence-stage results remain separate measurements."
        )
    elif cls == "failed_enforcement":
        proposition = (
            "The arms agree, and at least one continuation fails the declared "
            "settlement contract or the staged effect verdict."
        )
    else:
        proposition = (
            "The settlement-inclusive comparison did not obtain a qualified native "
            "BMO measurement for both continuations."
        )
    finding = {
        "id": "r3-ledger-settlement-v1-comparison",
        "claim_id": CLAIM_ID,
        "run_ids": run_ids or ["r3-ledger-settlement-v1-no-runs"],
        "proposition": proposition,
        "scope": (
            "r3-ledger-settlement-v1 committed claim followed by BMO "
            "SettleOrdinaryRetryFirstEditTx or SettleOrdinaryRetryFirstEditNoEffectTx; "
            "not a replacement for the retained r3-ledger-claim-v1 calibration"
        ),
        "label": label,
        "basis": "computed",
        "conclusion_class": cls,
        "supporting_observation_refs": [
            "r3-ledger-settlement-meta.observations.agreement.result",
            "r3-ledger-settlement-meta.observations.validity.valid",
        ],
    }
    validate_finding(finding)
    finding["conclusion_class"] = cls
    return finding


def write_compare_artifacts(run_dir: Path, summary: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    findings = run_dir / "findings"
    findings.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    finding = summary["finding"]
    (findings / f"{finding['id']}.json").write_text(json.dumps(finding, indent=2) + "\n", encoding="utf-8")
    (run_dir / "result.yaml").write_text(
        yaml.safe_dump(
            {
                "claim_id": CLAIM_ID,
                "label": finding["label"],
                "authoritative": "finding",
                "finding_path": f"findings/{finding['id']}.json",
                "native_bmo": bool(summary.get("native_bmo")),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=HERE / "cases.yaml")
    args = parser.parse_args(argv)
    bundle = load_cases(args.cases)
    summary_path = args.run_dir / "summary.json"
    prior = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
    native = bool(prior.get("native_bmo"))
    summary = compare_observations(
        bundle["cases"],
        load_ndjson(args.run_dir / "classical.ndjson"),
        load_ndjson(args.run_dir / "bmo.ndjson"),
        native_bmo=native,
    )
    print(json.dumps({"agreement": summary["agreement"]["result"], "conclusion_class": summary["conclusion_class"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
