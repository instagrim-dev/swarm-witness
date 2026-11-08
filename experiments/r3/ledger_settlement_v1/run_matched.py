#!/usr/bin/env python3
"""Run the settlement-inclusive retained-grant comparison.

The retained r3-ledger-claim-v1 evidence is not overwritten. This runner
materializes BMO at the settlement pin, injects the claim bridge plus the
settlement continuation, and compares it with ClassicalLedgerGate.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CLAIM_DIR = HERE.parent / "ledger_claim_v1"
sys.path.insert(0, str(CLAIM_DIR))
sys.path.insert(0, str(ROOT / "src"))

_adapter_spec = importlib.util.spec_from_file_location(
    "ledger_settlement_v1_adapter_runner", HERE / "classical_adapter.py"
)
if _adapter_spec is None or _adapter_spec.loader is None:
    raise ImportError("cannot load settlement classical adapter")
_adapter_mod = importlib.util.module_from_spec(_adapter_spec)
_adapter_spec.loader.exec_module(_adapter_mod)
ClassicalAdapter = _adapter_mod.ClassicalAdapter

_compare_spec = importlib.util.spec_from_file_location(
    "ledger_settlement_v1_compare_runner", HERE / "compare.py"
)
if _compare_spec is None or _compare_spec.loader is None:
    raise ImportError("cannot load settlement compare")
_compare_mod = importlib.util.module_from_spec(_compare_spec)
_compare_spec.loader.exec_module(_compare_mod)
build_finding = _compare_mod.build_finding
compare_observations = _compare_mod.compare_observations
write_compare_artifacts = _compare_mod.write_compare_artifacts

_protocol_spec = importlib.util.spec_from_file_location(
    "ledger_settlement_v1_protocol_runner", HERE / "protocol.py"
)
if _protocol_spec is None or _protocol_spec.loader is None:
    raise ImportError("cannot load settlement protocol")
_protocol_mod = importlib.util.module_from_spec(_protocol_spec)
_protocol_spec.loader.exec_module(_protocol_mod)
CLAIM_ID = _protocol_mod.CLAIM_ID
PROTOCOL_ID = _protocol_mod.PROTOCOL_ID
load_cases = _protocol_mod.load_cases
from swarm_witness.schema import validate_run  # noqa: E402

sys.path[:] = [p for p in sys.path if Path(p).resolve() != HERE.resolve()]
sys.path.insert(0, str(CLAIM_DIR))
sys.modules.pop("protocol", None)

_spec = importlib.util.spec_from_file_location("ledger_claim_bmo_adapter", CLAIM_DIR / "bmo_adapter.py")
if _spec is None or _spec.loader is None:
    raise ImportError("cannot load claim bmo_adapter")
_bmo_adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bmo_adapter)

PIN_REV = "c8297333b3bf31ded96ca0e8b39c531d3bcea97f"
EVIDENCE_ROOT = ROOT / "evidence" / "r3" / "ledger_settlement_v1"
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
BRIDGE_FILES = (
    CLAIM_DIR / "bmo_adapter_test.go",
    CLAIM_DIR / "bmo_adapter_fixture.go",
    HERE / "bmo_settlement_probe.go",
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_run_id(run_id: str) -> Path:
    if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError(f"run_id {run_id!r} is not a safe token")
    run_dir = (EVIDENCE_ROOT / run_id).resolve()
    run_dir.relative_to(EVIDENCE_ROOT.resolve())
    if run_dir.exists():
        raise FileExistsError(f"run_id {run_id!r} already exists; refusing overwrite")
    return run_dir


def run_classical(cases: list[Any], work_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        adapter = ClassicalAdapter(work_dir / case.case_id)
        try:
            adapter.open_case(case)
            for action in case.actions:
                rows.append(adapter.apply(action))
        finally:
            adapter.close()
    return rows


def _probe_input(cases: list[Any], db_dir: Path) -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "db_dir": str(db_dir),
        "cases": [
            {
                "case_id": case.case_id,
                "fixture": dict(case.fixture),
                "actions": [
                    {
                        "step": action.step,
                        "op": action.op,
                        "call_id": action.call_id,
                        "task_id": action.task_id,
                        "grant_id": action.grant_id,
                        "owner_revision": action.owner_revision,
                        "retry_epoch": action.retry_epoch,
                        "transaction_completion": action.transaction_completion,
                        "outcome": action.outcome,
                    }
                    for action in case.actions
                ],
            }
            for case in cases
        ],
    }


def _missing(cases: list[Any], note: str) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        for action in case.actions:
            rows.append(
                {
                    "protocol_id": PROTOCOL_ID,
                    "case_id": case.case_id,
                    "step": action.step,
                    "op": action.op,
                    "adapter_id": "bmo_l1_first_edit",
                    "execution_status": "missing",
                    "disposition": "unsupported",
                    "inputs": {"call_id": action.call_id, "outcome": action.outcome},
                    "native_result": {"reason": note},
                    "state": None,
                    "notes": note,
                }
            )
    return rows


def _keep_settlement(row: dict[str, Any]) -> dict[str, Any]:
    state = row.get("state")
    settlement = state.get("settlement") if isinstance(state, dict) else None
    if isinstance(state, dict):
        ledger = _bmo_adapter.project_state(state) or {}
        ledger["settlement"] = settlement if isinstance(settlement, dict) else None
        row["state"] = ledger
    return row


def run_bmo(cases: list[Any], work_dir: Path, bmo_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    work_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "adapter_id": "bmo_l1_first_edit",
        "pin": PIN_REV,
        "native_bmo": False,
        "mode": "missing",
        "bridge": {path.name: _sha256_file(path) for path in BRIDGE_FILES},
    }
    pin_err = _bmo_adapter.verify_pin(bmo_root, PIN_REV)
    if pin_err:
        manifest["notes"] = pin_err
        return _missing(cases, pin_err), manifest
    tree, inventory = _bmo_adapter.prepare_disposable_tree(bmo_root, work_dir / "tree", pin=PIN_REV)
    target = tree / "internal" / "sessioncompaction"
    for path in BRIDGE_FILES:
        shutil.copy2(path, target / path.name)
    manifest["source_inventory"] = inventory
    cases_path = work_dir / "probe_cases.json"
    out_path = work_dir / "bmo.ndjson"
    db_dir = work_dir / "case_dbs"
    db_dir.mkdir(parents=True, exist_ok=True)
    cases_path.write_text(json.dumps(_probe_input(cases, db_dir), indent=2) + "\n", encoding="utf-8")
    env = os.environ.copy()
    env["SWARM_WITNESS_R3_CASES"] = str(cases_path.resolve())
    env["SWARM_WITNESS_R3_OUT"] = str(out_path.resolve())
    cmd = [
        "go", "test", "-tags=swarm_witness_r3", "./internal/sessioncompaction/",
        "-run", "^TestSwarmWitnessR3Probe$", "-count=1",
    ]
    manifest["command"] = cmd
    proc = subprocess.run(cmd, cwd=str(tree), env=env, capture_output=True, text=True, check=False)
    log_path = work_dir / "bmo_go_test.log"
    log_path.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    manifest["exit_code"] = proc.returncode
    manifest["log_path"] = str(log_path)
    rows: list[dict[str, Any]] = []
    if out_path.is_file():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(_keep_settlement(obj))
    completed = bool(rows) and all(r.get("execution_status") == "completed" for r in rows)
    if proc.returncode == 0 and completed and all(r.get("adapter_id") == "bmo_l1_first_edit" for r in rows):
        manifest["native_bmo"] = True
        manifest["mode"] = "go_test_bridge_native"
        manifest["notes"] = (
            "native claim plus SettleOrdinaryRetryFirstEditTx / "
            "SettleOrdinaryRetryFirstEditNoEffectTx"
        )
        return rows, manifest
    manifest["notes"] = f"go test exit={proc.returncode}; native qualification refused"
    if not rows:
        return _missing(cases, manifest["notes"]), manifest
    return rows, manifest


def execute_run(*, run_id: str, bmo_root: Path, cases_path: Path) -> Path:
    bundle = load_cases(cases_path)
    cases = list(bundle["cases"])
    run_dir = validate_run_id(run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    classical = run_classical(cases, run_dir / "classical_work")
    bmo_rows, manifest = run_bmo(cases, run_dir / "bmo_work", bmo_root)
    for name, rows in (("classical.ndjson", classical), ("bmo.ndjson", bmo_rows)):
        (run_dir / name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    work_log = run_dir / "bmo_work" / "bmo_go_test.log"
    if work_log.is_file():
        shutil.copy2(work_log, run_dir / "bmo_go_test.log")
    portable = dict(manifest)
    portable["log_path"] = "bmo_go_test.log"
    portable["bmo_root"] = "<local-checkout>"
    (run_dir / "source_manifest.json").write_text(
        json.dumps(
            {
                "protocol_id": PROTOCOL_ID,
                "claim_id": CLAIM_ID,
                "run_id": run_id,
                "bmo_pin": PIN_REV,
                "bmo": portable,
                "cases_sha256": _sha256_text(cases_path.read_text(encoding="utf-8")),
                "created_unix": int(time.time()),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    summary = compare_observations(cases, classical, bmo_rows, native_bmo=bool(manifest.get("native_bmo")))
    summary["native_qualification"] = manifest.get("notes")
    runs = run_dir / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": "r3-ledger-settlement-meta",
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "meta",
        "source_pin": PIN_REV,
        "execution_status": "completed",
        "observations": {
            "agreement": {"result": summary["agreement"]["result"]},
            "validity": {"valid": summary["validity"]["valid"]},
        },
    }
    validate_run(meta)
    (runs / "r3-ledger-settlement-meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    summary["finding"] = build_finding(summary, ["r3-ledger-settlement-meta"])
    write_compare_artifacts(run_dir, summary)
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bmo-root", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=HERE / "cases.yaml")
    args = parser.parse_args(argv)
    run_dir = execute_run(run_id=args.run_id, bmo_root=args.bmo_root, cases_path=args.cases)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "run_dir": str(run_dir),
        "native_bmo": summary.get("native_bmo"),
        "agreement": summary["agreement"]["result"],
        "conclusion_class": summary["conclusion_class"],
        "label": summary["finding"]["label"],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
