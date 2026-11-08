"""The v2 challenge keeps v1 frozen and separates rejection from a verdict."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "experiments" / "effect_witness" / "native_projection_challenge_v2.py"
V1_LEDGER = (
    ROOT
    / "evidence"
    / "effect_witness_v1"
    / "native_projection_challenge_v1"
    / "ledger.json"
)
INVALID = (
    "sink-misbound",
    "sink-spoofed",
    "sink-unauthenticated",
    "sink-run-mismatch",
    "sink-actor-mismatch",
    "sink-object-mismatch",
    "sink-mapped-actor-mismatch",
)
MALFORMED = (
    "mixed-unknown-authorization",
    "sink-unknown-subject",
    "coverage-withheld",
)


def _runner():
    spec = importlib.util.spec_from_file_location("native_projection_challenge_v2", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_invalid_sink_premises_are_not_decisive(tmp_path: Path):
    document = _runner().evaluate_challenge_v2(ROOT, tmp_path)
    rows = {row["case_id"]: row for row in document["rows"]}
    assert document["case_count"] == 16
    assert set(rows) == {row["case_id"] for row in json.loads(V1_LEDGER.read_text())["rows"]}
    for case_id in INVALID:
        row = rows[case_id]
        assert row["execution_status"] == "completed"
        assert row["epistemic_status"] == "unresolved"
        assert row["epistemic_status"] not in {"supported", "refuted"}
        assert row["rejected_ids"]
        assert row["reasons"]
    assert rows["clean-positive"]["epistemic_status"] == "supported"
    assert rows["clean-positive"]["matches_warrant"] is True


def test_duplicate_is_not_a_verdict_and_malformed_input_stays_rejected(tmp_path: Path):
    before = V1_LEDGER.read_bytes()
    document = _runner().evaluate_challenge_v2(ROOT, tmp_path)
    assert V1_LEDGER.read_bytes() == before
    rows = {row["case_id"]: row for row in document["rows"]}
    duplicate = rows["coverage-duplicate"]
    assert duplicate["execution_status"] == "completed"
    assert duplicate["epistemic_status"] == "supported"
    assert "exact_duplicate_not_independent" in duplicate["reasons"]
    for case_id in MALFORMED:
        row = rows[case_id]
        assert row["execution_status"] == "rejected"
        assert row["epistemic_status"] is None
        assert row["raw_error"]
        assert row["matches_warrant"] is False
