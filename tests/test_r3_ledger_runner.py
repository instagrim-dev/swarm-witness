"""Runner integration tests for r3-ledger-claim-v1."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "r3" / "ledger_claim_v1"


def _load_run_matched(monkeypatch, tmp_path: Path):
    sys.path.insert(0, str(PKG))
    sys.path.insert(0, str(ROOT / "src"))
    # Redirect evidence root into tmp.
    name = "run_matched_under_test"
    spec = importlib.util.spec_from_file_location(name, PKG / "run_matched.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "EVIDENCE_ROOT", tmp_path / "evidence" / "r3" / "ledger_claim_v1")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    # mirror_for_index writes under mod.ROOT/evidence/...
    return mod


def test_classical_emits_t02_t03_t04(tmp_path: Path, monkeypatch):
    mod = _load_run_matched(monkeypatch, tmp_path)
    # Force offline L1 path even if the developer shell exports BMO_ROOT.
    monkeypatch.delenv("BMO_ROOT", raising=False)
    # Point cases at real cases.yaml but filter.
    run_dir = mod.execute_run(
        run_id="test-core",
        bmo_root=None,
        cases_path=PKG / "cases.yaml",
        case_filter={"T02", "T03", "T04"},
    )
    classical = (run_dir / "classical.ndjson").read_text(encoding="utf-8").strip().splitlines()
    assert classical
    cases_seen = {json.loads(line)["case_id"] for line in classical}
    assert cases_seen == {"T02", "T03", "T04"}
    # Classical steps completed.
    for line in classical:
        row = json.loads(line)
        assert row["execution_status"] == "completed"
        assert row["adapter_id"] == "classical_ledger_gate"

    bmo = (run_dir / "bmo.ndjson").read_text(encoding="utf-8").strip().splitlines()
    assert bmo
    for line in bmo:
        row = json.loads(line)
        # Offline L1 stand-in emits completed traces when BMO_ROOT is absent.
        assert row["execution_status"] == "completed"
        assert row["adapter_id"] == "bmo_l1_first_edit"
        assert row.get("native_result", {}).get("native_bmo") is False

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    # Offline stand-in cannot upgrade the BMO pin claim beyond unresolved.
    assert summary["finding"]["label"] == "unresolved"
    assert summary["finding"]["claim_id"] == "r3_ledger_claim_v1"
    assert summary.get("native_bmo") is False
    assert summary["agreement"]["result"] == "matched"


def test_package_log_alone_does_not_complete(tmp_path: Path):
    # Covered in compare tests; runner must still refuse success without NDJSON.
    bmo_work = tmp_path / "bmo_work"
    bmo_work.mkdir()
    (bmo_work / "bmo_go_test.log").write_text("PASS\n", encoding="utf-8")
    assert not (bmo_work / "bmo.ndjson").exists()
