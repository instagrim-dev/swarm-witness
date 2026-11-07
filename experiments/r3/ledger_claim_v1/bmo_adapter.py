"""BMO L1 adapter orchestrator for r3-ledger-claim-v1.

Prepares a disposable BMO tree at the pinned revision, copies the tagged
bridge into internal/sessioncompaction, and runs TestSwarmWitnessR3Probe.
Never fills decisions from package pass counts. Without a usable BMO tree,
emits execution_status=missing observations (fail-closed).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from protocol import PROTOCOL_ID, CaseSpec, project_state

ADAPTER_ID = "bmo_l1_first_edit"
PIN_REV = "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe"
BRIDGE_FILES = ("bmo_adapter_test.go", "bmo_adapter_fixture.go")


def bridge_dir() -> Path:
    return Path(__file__).resolve().parent


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def bridge_manifest() -> dict[str, str]:
    return {name: file_sha256(bridge_dir() / name) for name in BRIDGE_FILES}


def resolve_bmo_root(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("BMO_ROOT")
    if env:
        return Path(env)
    return None


def verify_pin(bmo_root: Path, expected: str = PIN_REV) -> str | None:
    try:
        got = subprocess.check_output(
            ["git", "-C", str(bmo_root), "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"git rev-parse failed: {exc}"
    if got != expected and not got.startswith(expected[:12]):
        return f"BMO HEAD {got} != pin {expected}"
    return None


def _missing_rows(case: CaseSpec, note: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action in case.actions:
        inputs: dict[str, Any] = {}
        if action.op == "claim_first_edit":
            inputs = {
                "call_id": action.call_id,
                "task_id": action.task_id,
                "grant_id": action.grant_id,
                "owner_revision": action.owner_revision,
                "retry_epoch": action.retry_epoch,
                "transaction_completion": action.transaction_completion,
            }
        rows.append(
            {
                "protocol_id": PROTOCOL_ID,
                "case_id": case.case_id,
                "step": action.step,
                "op": action.op,
                "adapter_id": ADAPTER_ID,
                "execution_status": "missing",
                "disposition": "unsupported",
                "inputs": inputs,
                "native_result": {"reason": note},
                "state": None,
                "notes": note,
            }
        )
    return rows


def prepare_disposable_tree(bmo_root: Path, work_root: Path) -> Path:
    """Copy BMO tree and inject bridge files only into sessioncompaction."""
    dest = work_root / "bmo"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        bmo_root,
        dest,
        ignore=shutil.ignore_patterns(".git", "bin", "dist", "node_modules"),
        symlinks=True,
    )
    target = dest / "internal" / "sessioncompaction"
    if not target.is_dir():
        raise FileNotFoundError(f"missing {target}")
    for name in BRIDGE_FILES:
        shutil.copy2(bridge_dir() / name, target / name)
    return dest


def cases_to_probe_input(cases: list[CaseSpec], db_dir: Path) -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "db_dir": str(db_dir),
        "cases": [
            {
                "case_id": c.case_id,
                "fixture": dict(c.fixture),
                "actions": [
                    {
                        "step": a.step,
                        "op": a.op,
                        "call_id": a.call_id,
                        "task_id": a.task_id,
                        "grant_id": a.grant_id,
                        "owner_revision": a.owner_revision,
                        "retry_epoch": a.retry_epoch,
                        "transaction_completion": a.transaction_completion,
                    }
                    for a in c.actions
                ],
            }
            for c in cases
        ],
    }


def run_bmo_probe(
    *,
    cases: list[CaseSpec],
    work_dir: Path,
    bmo_root: Path | None = None,
    allow_offline_l1: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (observations, manifest).

    Prefer disposable-tree Go bridge at the pin. If BMO is unavailable and
    ``allow_offline_l1`` is true, emit completed offline SQLite L1 traces
    marked ``native_bmo=false`` (pipeline inspectability only).
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "adapter_id": ADAPTER_ID,
        "pin": PIN_REV,
        "bridge": bridge_manifest(),
        "bmo_root": None,
        "mode": "missing",
        "native_bmo": False,
        "command": None,
        "exit_code": None,
        "log_path": str(work_dir / "bmo_go_test.log"),
    }

    root = resolve_bmo_root(bmo_root)
    if root is None or not root.is_dir():
        if allow_offline_l1:
            from local_l1_adapter import run_offline_l1

            rows, offline_manifest = run_offline_l1(cases, work_dir / "offline_l1")
            manifest.update(offline_manifest)
            manifest["bridge"] = bridge_manifest()
            manifest["pin"] = PIN_REV
            return rows, manifest
        rows = []
        for case in cases:
            rows.extend(_missing_rows(case, "bmo_root_unavailable"))
        manifest["notes"] = "BMO_ROOT not set or missing; fail-closed missing observations"
        return rows, manifest

    pin_err = verify_pin(root)
    if pin_err:
        if allow_offline_l1:
            from local_l1_adapter import run_offline_l1

            rows, offline_manifest = run_offline_l1(cases, work_dir / "offline_l1")
            manifest.update(offline_manifest)
            manifest["bridge"] = bridge_manifest()
            manifest["pin"] = PIN_REV
            manifest["bmo_root"] = str(root)
            manifest["notes"] = pin_err + "; fell back to offline L1"
            return rows, manifest
        rows = []
        for case in cases:
            rows.extend(_missing_rows(case, pin_err))
        manifest["notes"] = pin_err
        manifest["bmo_root"] = str(root)
        return rows, manifest

    manifest["bmo_root"] = str(root)
    try:
        tree = prepare_disposable_tree(root, work_dir / "tree")
    except OSError as exc:
        if allow_offline_l1:
            from local_l1_adapter import run_offline_l1

            rows, offline_manifest = run_offline_l1(cases, work_dir / "offline_l1")
            manifest.update(offline_manifest)
            manifest["bridge"] = bridge_manifest()
            manifest["pin"] = PIN_REV
            manifest["bmo_root"] = str(root)
            manifest["notes"] = f"disposable_tree_failed: {exc}; offline L1 fallback"
            return rows, manifest
        rows = []
        for case in cases:
            rows.extend(_missing_rows(case, f"disposable_tree_failed: {exc}"))
        manifest["notes"] = str(exc)
        return rows, manifest

    cases_path = work_dir / "probe_cases.json"
    out_path = work_dir / "bmo.ndjson"
    db_dir = work_dir / "case_dbs"
    db_dir.mkdir(parents=True, exist_ok=True)
    cases_path.write_text(
        json.dumps(cases_to_probe_input(cases, db_dir), indent=2) + "\n",
        encoding="utf-8",
    )
    if out_path.exists():
        out_path.unlink()

    env = os.environ.copy()
    env["SWARM_WITNESS_R3_CASES"] = str(cases_path.resolve())
    env["SWARM_WITNESS_R3_OUT"] = str(out_path.resolve())
    cmd = [
        "go",
        "test",
        "-tags=swarm_witness_r3",
        "./internal/sessioncompaction/",
        "-run",
        "^TestSwarmWitnessR3Probe$",
        "-count=1",
    ]
    manifest["command"] = cmd
    manifest["mode"] = "go_test_bridge"
    log_path = Path(manifest["log_path"])
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(tree),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        rows = []
        for case in cases:
            rows.extend(_missing_rows(case, f"go_test_failed: {exc}"))
        manifest["notes"] = str(exc)
        return rows, manifest

    log_path.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    manifest["exit_code"] = proc.returncode

    rows = []
    if out_path.is_file():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                # Never let a package-pass rewrite state.
                if obj.get("state") is not None:
                    obj["state"] = project_state(obj["state"])
                rows.append(obj)

    if not rows:
        if allow_offline_l1:
            from local_l1_adapter import run_offline_l1

            rows, offline_manifest = run_offline_l1(cases, work_dir / "offline_l1")
            manifest.update(offline_manifest)
            manifest["bridge"] = bridge_manifest()
            manifest["pin"] = PIN_REV
            manifest["bmo_root"] = str(root)
            manifest["command"] = cmd
            manifest["exit_code"] = proc.returncode
            manifest["notes"] = (
                "bridge produced no NDJSON; package log is metadata only; "
                "offline L1 fallback"
            )
            return rows, manifest
        for case in cases:
            rows.extend(
                _missing_rows(
                    case,
                    f"bridge_produced_no_ndjson exit={proc.returncode}",
                )
            )
        manifest["notes"] = "bridge produced no NDJSON; package log is metadata only"
        return rows, manifest

    # Native only if every observation completed (fixture hooks linked).
    completed = all(r.get("execution_status") == "completed" for r in rows)
    missing_any = any(r.get("execution_status") == "missing" for r in rows)
    if completed and not missing_any:
        manifest["native_bmo"] = True
        manifest["mode"] = "go_test_bridge_native"
        manifest["notes"] = "native ClaimOrdinaryRetainedGrantFirstEditTx bridge"
        return rows, manifest

    if allow_offline_l1:
        from local_l1_adapter import run_offline_l1

        rows, offline_manifest = run_offline_l1(cases, work_dir / "offline_l1")
        manifest.update(offline_manifest)
        manifest["bridge"] = bridge_manifest()
        manifest["pin"] = PIN_REV
        manifest["bmo_root"] = str(root)
        manifest["command"] = cmd
        manifest["exit_code"] = proc.returncode
        manifest["notes"] = (
            "bridge emitted missing/unsupported rows (fixture hooks unlinked); "
            "offline L1 fallback"
        )
        return rows, manifest

    manifest["native_bmo"] = False
    manifest["mode"] = "go_test_bridge_incomplete"
    manifest["notes"] = "bridge observations incomplete; fixture hooks unlinked"
    return rows, manifest
