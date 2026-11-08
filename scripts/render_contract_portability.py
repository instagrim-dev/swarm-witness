#!/usr/bin/env python3
"""Render the retained ledger and settlement contracts.

This reads published observation rows. It does not re-execute BMO and does not
choose a new correctness label from one arm.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ARCHITECTURE_CONTEXT = "e0038cc48872b274c22deaed8e24236530e9821e"
LEDGER_PIN = "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe"
SETTLEMENT_PIN = "c8297333b3bf31ded96ca0e8b39c531d3bcea97f"

LEDGER_RUN = "2026-11-07-ledger-v1-repair2"
INITIAL_RUN = "2026-11-08-ledger-settlement-v1"
CONTROLS_RUN = "2026-11-08-ledger-settlement-v1-controls"


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SETTLEMENT = _load(
    ROOT / "experiments" / "r3" / "ledger_settlement_v1" / "protocol.py",
    "ledger_settlement_protocol_report",
)
_COMPARE = _load(
    ROOT / "experiments" / "r3" / "ledger_settlement_v1" / "compare.py",
    "ledger_settlement_compare_report",
)
_LEDGER = _load(
    ROOT / "experiments" / "r3" / "ledger_claim_v1" / "protocol.py",
    "ledger_claim_protocol_report",
)
_LEDGER_COMPARE = _load(
    ROOT / "experiments" / "r3" / "ledger_claim_v1" / "compare.py",
    "ledger_claim_compare_report",
)


def load_settlement_cases(repo_root: Path) -> list[Any]:
    loaded = _SETTLEMENT.load_cases(
        repo_root / "experiments" / "r3" / "ledger_settlement_v1" / "cases.yaml"
    )
    return list(loaded["cases"])


def load_ledger_cases(repo_root: Path) -> list[Any]:
    loaded = _LEDGER.load_cases(repo_root / "experiments" / "r3" / "ledger_claim_v1" / "cases.yaml")
    return list(loaded["cases"])


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _call_owner(cases: list[Any]) -> dict[str, str]:
    owner: dict[str, str] = {}
    for case in cases:
        for action in case.actions:
            if action.call_id:
                owner[str(action.call_id)] = case.case_id
    return owner


def _observed_call_ids(row: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for pocket in (row.get("inputs"), row.get("native_result")):
        if isinstance(pocket, dict) and isinstance(pocket.get("call_id"), str):
            found.append(pocket["call_id"])
    state = row.get("state") if isinstance(row.get("state"), dict) else {}
    for key in ("claim_call_ids", "transfer_call_ids"):
        values = state.get(key) or []
        found.extend(str(value) for value in values)
    settlement = state.get("settlement")
    if isinstance(settlement, dict) and isinstance(settlement.get("call_id"), str):
        found.append(settlement["call_id"])
    return found


def validate_observations(cases: list[Any], rows: list[dict[str, Any]]) -> None:
    """Reject missing, extra, duplicate, or cross-case rows for one arm."""
    declared = {(case.case_id, action.step) for case in cases for action in case.actions}
    seen: dict[tuple[str, int], int] = {}
    owner = _call_owner(cases)
    errors: list[str] = []
    for row in rows:
        key = (str(row.get("case_id")), int(row.get("step") or 0))
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            errors.append(f"duplicate {key[0]} step {key[1]}")
        elif key not in declared:
            errors.append(f"extra {key[0]} step {key[1]}")
        for call_id in _observed_call_ids(row):
            other = owner.get(call_id)
            if other is not None and other != key[0]:
                errors.append(f"cross-case {key[0]} carries {call_id} from {other}")
    for case_id, step in sorted(declared):
        if seen.get((case_id, step), 0) == 0:
            errors.append(f"missing {case_id} step {step}")
    if errors:
        raise ValueError("; ".join(errors))


def _arm(row: dict[str, Any]) -> str:
    adapter = str(row.get("adapter_id") or "")
    if adapter.startswith("bmo"):
        return "bmo"
    if adapter.startswith("classical"):
        return "classical"
    raise ValueError(f"unknown adapter {adapter}")


def _select(cases: list[Any], expected: set[str] | None) -> list[Any]:
    if expected is None:
        return cases
    return [case for case in cases if case.case_id in expected]


def _stage_row(
    *,
    protocol_id: str,
    run_id: str,
    case: Any,
    arm: str,
    stage: str,
    observation: dict[str, Any],
    resolving: dict[str, Any] | None,
    scope: str,
    source_refs: list[dict[str, str]],
) -> dict[str, Any]:
    state = observation.get("state") if isinstance(observation.get("state"), dict) else {}
    settlement = state.get("settlement") if isinstance(state.get("settlement"), dict) else None
    if stage == "settlement" and settlement is not None:
        disposition = settlement.get("disposition")
    else:
        disposition = observation.get("disposition")
    return {
        "protocol_id": protocol_id,
        "run_id": run_id,
        "case_id": case.case_id,
        "arm": arm,
        "stage": stage,
        "contract_disposition": disposition,
        "effect_applied_verdict": _SETTLEMENT.effect_verdict(state),
        "resolving_observation": resolving,
        "scope": scope,
        "source_refs": source_refs,
        "persisted_state": {
            "claim_count": state.get("claim_count"),
            "settlement_present": settlement is not None,
            "grant_spent": state.get("grant_spent"),
        },
    }


def _run_rows(
    *,
    protocol_id: str,
    run_id: str,
    cases: list[Any],
    classical: list[dict[str, Any]],
    bmo: list[dict[str, Any]],
    scope: str,
    source_refs: list[dict[str, str]],
    include_settlement: bool,
) -> list[dict[str, Any]]:
    validate_observations(cases, classical)
    validate_observations(cases, bmo)
    stages = {
        "classical": _COMPARE.evidence_stages(cases, classical),
        "bmo": _COMPARE.evidence_stages(cases, bmo),
    }
    by_arm = {"classical": classical, "bmo": bmo}
    rows = []
    for case in cases:
        for arm, observations in by_arm.items():
            indexed = {
                (row["case_id"], int(row["step"])): row
                for row in observations
                if row["case_id"] == case.case_id
            }
            claim_action = next(action for action in case.actions if action.op == "claim_first_edit")
            resolving = stages[arm][case.case_id]["resolving_observation"]
            rows.append(
                _stage_row(
                    protocol_id=protocol_id,
                    run_id=run_id,
                    case=case,
                    arm=arm,
                    stage="claim",
                    observation=indexed[(case.case_id, claim_action.step)],
                    resolving=resolving,
                    scope=scope,
                    source_refs=source_refs,
                )
            )
            if not include_settlement:
                continue
            settle_action = next(action for action in case.actions if str(action.op).startswith("settle_"))
            rows.append(
                _stage_row(
                    protocol_id=protocol_id,
                    run_id=run_id,
                    case=case,
                    arm=arm,
                    stage="settlement",
                    observation=indexed[(case.case_id, settle_action.step)],
                    resolving=resolving,
                    scope=scope,
                    source_refs=source_refs,
                )
            )
    return rows


def build_contract_report(repo_root: Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    ledger_cases = load_ledger_cases(repo_root)
    settlement_cases = load_settlement_cases(repo_root)
    ledger_dir = repo_root / "evidence" / "r3" / "ledger_claim_v1" / LEDGER_RUN
    initial_dir = repo_root / "evidence" / "r3" / "ledger_settlement_v1" / INITIAL_RUN
    controls_dir = repo_root / "evidence" / "r3" / "ledger_settlement_v1" / CONTROLS_RUN
    loaded = {
        "ledger": {
            "classical": _read_ndjson(ledger_dir / "classical.ndjson"),
            "bmo": _read_ndjson(ledger_dir / "bmo.ndjson"),
        },
        "initial": {
            "classical": _read_ndjson(initial_dir / "classical.ndjson"),
            "bmo": _read_ndjson(initial_dir / "bmo.ndjson"),
        },
        "controls": {
            "classical": _read_ndjson(controls_dir / "classical.ndjson"),
            "bmo": _read_ndjson(controls_dir / "bmo.ndjson"),
        },
    }
    ledger_scope = (
        "Selected first-edit claim contract on six cases. Compare-only retained rows. "
        "Not a settlement measurement and not a live model edit."
    )
    settlement_scope = (
        "Fixture-authored terminal records checked by the production settler and the classical gate. "
        "Compare-only. Bounded conformance is not full-system equivalence and not a live model edit."
    )
    ledger_refs = [
        {"role": "ledger_measurement", "ref": LEDGER_PIN, "path": "internal/sessioncompaction/ordinary_retry_retained_grant.go"},
        {"role": "architecture_context", "ref": ARCHITECTURE_CONTEXT, "path": "internal/a2a/managedsupervisor/supervisor.go"},
    ]
    settlement_refs = [
        {"role": "settlement_measurement", "ref": SETTLEMENT_PIN, "path": "internal/sessioncompaction/ordinary_retry_first_edit_settlement.go"},
        {"role": "architecture_context", "ref": ARCHITECTURE_CONTEXT, "path": "internal/permission/coordinator_delegation_v2.go"},
    ]
    rows = []
    rows.extend(
        _run_rows(
            protocol_id="r3-ledger-claim-v1",
            run_id=LEDGER_RUN,
            cases=ledger_cases,
            classical=loaded["ledger"]["classical"],
            bmo=loaded["ledger"]["bmo"],
            scope=ledger_scope,
            source_refs=ledger_refs,
            include_settlement=False,
        )
    )
    initial_cases = _select(settlement_cases, {"S01", "S02"})
    rows.extend(
        _run_rows(
            protocol_id="r3-ledger-settlement-v1",
            run_id=INITIAL_RUN,
            cases=initial_cases,
            classical=loaded["initial"]["classical"],
            bmo=loaded["initial"]["bmo"],
            scope=settlement_scope,
            source_refs=settlement_refs,
            include_settlement=True,
        )
    )
    rows.extend(
        _run_rows(
            protocol_id="r3-ledger-settlement-v1",
            run_id=CONTROLS_RUN,
            cases=settlement_cases,
            classical=loaded["controls"]["classical"],
            bmo=loaded["controls"]["bmo"],
            scope=settlement_scope,
            source_refs=settlement_refs,
            include_settlement=True,
        )
    )
    native_bmo, native_note = _LEDGER_COMPARE.qualify_native_bmo(
        run_dir=ledger_dir,
        bmo_steps=loaded["ledger"]["bmo"],
    )
    return {
        "independent_adjudication": False,
        "compare_only": True,
        "live_model_edit": False,
        "full_system_equivalence": False,
        "source_pins": {
            "architecture_context": ARCHITECTURE_CONTEXT,
            "ledger_measurement": LEDGER_PIN,
            "settlement_measurement": SETTLEMENT_PIN,
        },
        "ledger_case_count": 6,
        "ledger_step_count": sum(len(case.actions) for case in ledger_cases),
        "initial_settlement_case_count": 2,
        "controls_case_count": len(settlement_cases),
        "ledger_native_requalification": {
            "native_bmo": native_bmo,
            "note": native_note,
            "retained_receipt_rewritten": False,
        },
        "rows": rows,
        "observations": loaded,
    }


def render_markdown(report: dict[str, Any]) -> str:
    pins = report["source_pins"]
    lines = [
        "# Portable transaction and settlement contract",
        "",
        "This report is generated from retained rows. The comparison commands are compare-only. They do not re-execute BMO, and the fixture-authored settlement rows are not a live model edit.",
        "",
        "The same author implemented both arms. That is a separate implementation, not independent adjudication. Agreement on these cases is bounded conformance. It is not full-system equivalence, and it does not measure the subordinate supervisor or signed delegation at the architecture-context pin.",
        "",
        "| Pin | Role | Revision |",
        "| --- | --- | --- |",
        f"| Architecture context | Supervisor and delegation surfaces, not measured by S01–S09 | `{pins['architecture_context']}` |",
        f"| Ledger measurement | T01–T06 claim contract | `{pins['ledger_measurement']}` |",
        f"| Settlement measurement | S01–S09 terminal-record contract | `{pins['settlement_measurement']}` |",
        "",
        "Another implementation can adopt the contract below. This measurement does not certify an unrelated deployment.",
        "",
        "## Obligations",
        "",
        "- Identity and scope binding: a terminal record names the claim's call. A call that belongs to another case is a cross-case input and is rejected.",
        "- One-use claim: the six-case ledger consumes the retained-grant claim. A later claim on the spent grant is outside this settlement table.",
        "- Transactional failure: a refused settlement does not insert a settlement row.",
        "- Terminal-record qualification: applied evidence binds the tool, mutation, and artifact. Definite no-effect binds the tool and a source receipt.",
        "- Refusal state: the committed claim remains, and effect-applied stays unresolved.",
        "- Unresolved outcome: a missing, misordered, misbound, or contradictory terminal record does not become definite no-effect.",
        "",
        "## Stage table",
        "",
        "The initial settlement run contains S01 and S02. The controls run contains nine cases, including those two. Do not add the denominators. The ledger run contains six cases and "
        f"{report['ledger_step_count']} paired steps. A fresh compare of those retained rows still matches. Re-qualifying native BMO from the bridge files beside the comparator does not: {report['ledger_native_requalification']['note']}. The retained receipt is not rewritten by this report.",
        "",
        "| Run | Case | Arm | Stage | Contract disposition | Effect-applied | Resolving record |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["rows"]:
        if row["protocol_id"] != "r3-ledger-settlement-v1" or row["run_id"] != CONTROLS_RUN:
            continue
        resolving = row["resolving_observation"]
        record = "none" if not resolving else f"step {resolving['step']} {resolving['from']} to {resolving['to']}"
        lines.append(
            f"| controls | {row['case_id']} | {row['arm']} | {row['stage']} | {row['contract_disposition']} | {row['effect_applied_verdict']} | {record} |"
        )
    lines.extend(
        [
            "",
            "S02 refutes only the effect-applied proposition. Refusal leaves that proposition unresolved and leaves the committed claim in place.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    published = {key: value for key, value in report.items() if key != "observations"}
    (output / "cases.json").write_text(json.dumps(published, indent=2) + "\n", encoding="utf-8")
    (output / "CONTRACT_MAP.md").write_text(render_markdown(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_report(build_contract_report(ROOT), args.output)


if __name__ == "__main__":
    main()
