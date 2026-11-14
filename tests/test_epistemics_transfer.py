"""SoundGate R1 is the transfer family. It is not the forty-eight or the sixteen."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "experiments" / "epistemics_trust_v1" / "transfer_soundgate.py"
    spec = importlib.util.spec_from_file_location("transfer_soundgate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _measure():
    return _module().measure(ROOT)


def test_soundgate_transfer_is_outside_the_twelve_histories():
    data = json.loads((ROOT / "evidence" / "r1" / "local-run-analysis.json").read_text())
    cases = data["cases"]
    prohibited = sum(1 for row in cases if row["status"] == "prohibited_effect")
    unavailable = sum(1 for row in cases if not row["fresh_work"])
    result = _measure()
    assert result["rows"] == 459
    assert result["dependence"] == "153 cuts under 3 policies"
    assert result["relation_to_48"] == "separate"
    assert result["restriction"]["intact_run"]["unsupported_supports"] == prohibited == 143
    assert result["availability"]["intact_run"]["unsupported_supports"] == unavailable == 151
    assert result["restriction"]["effect_field"]["correct_decisive"] == 459
    assert result["availability"]["effect_field"]["correct_decisive"] == 459
    assert result["restriction"]["effect_field"]["unsupported_supports"] == 0
    proof = _module().protocol_transfer(ROOT)
    assert proof["projection_matches"] is True
    assert proof["intact_run_unsupported_supports"] == 1
    by_policy = {row["policy"]: row for row in proof["claims"]}
    assert by_policy["barrier"]["projection"] == "supported"
    assert by_policy["original"]["projection"] == "refuted"
    assert by_policy["original"]["intact_run"] == "supported"
    closed = (ROOT / "report" / "Swarm_Witness_Final_Submission.md").read_text(encoding="utf-8")
    assert "External empirical transfer remains untested" in closed
