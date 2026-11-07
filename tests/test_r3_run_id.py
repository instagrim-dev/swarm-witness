"""Immutable run_id containment for r3-ledger-claim-v1."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "r3" / "ledger_claim_v1"


def _load():
    sys.path.insert(0, str(PKG))
    sys.path.insert(0, str(ROOT / "src"))
    name = "ledger_run_matched"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PKG / "run_matched.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_run_id_rejects_path_escape(tmp_path: Path):
    mod = _load()
    with pytest.raises(ValueError):
        mod.validate_run_id("../..", evidence_root=tmp_path)
    with pytest.raises(ValueError):
        mod.validate_run_id("a/b", evidence_root=tmp_path)


def test_run_id_refuses_existing(tmp_path: Path):
    mod = _load()
    existing = tmp_path / "already"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        mod.validate_run_id("already", evidence_root=tmp_path)


def test_run_id_accepts_safe_token(tmp_path: Path):
    mod = _load()
    path = mod.validate_run_id("2026-11-07-ledger-v1-repair", evidence_root=tmp_path)
    assert path == (tmp_path / "2026-11-07-ledger-v1-repair").resolve()
