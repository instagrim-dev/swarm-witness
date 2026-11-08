"""The contract report reads retained rows and keeps run identity."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_contract_portability.py"


def _renderer():
    spec = importlib.util.spec_from_file_location("render_contract_portability", RENDERER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(report, *, run_id, case_id, arm, stage):
    found = [
        row
        for row in report["rows"]
        if row["run_id"] == run_id
        and row["case_id"] == case_id
        and row["arm"] == arm
        and row["stage"] == stage
    ]
    assert len(found) == 1
    return found[0]


def test_report_preserves_protocol_and_run_identity():
    report = _renderer().build_contract_report(ROOT)
    assert report["independent_adjudication"] is False
    assert report["compare_only"] is True
    assert report["live_model_edit"] is False
    assert report["full_system_equivalence"] is False
    assert report["bounded_contract_portability"] == "demonstrated"
    assert report["external_empirical_transfer"] == "not_tested"
    pins = report["source_pins"]
    assert pins["architecture_context"] == "e0038cc48872b274c22deaed8e24236530e9821e"
    assert pins["ledger_measurement"] == "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe"
    assert pins["settlement_measurement"] == "c8297333b3bf31ded96ca0e8b39c531d3bcea97f"
    assert report["ledger_case_count"] == 6
    assert report["ledger_step_count"] == 22
    assert report["initial_settlement_case_count"] == 2
    assert report["controls_case_count"] == 9
    protocols = {row["protocol_id"] for row in report["rows"]}
    assert protocols == {"r3-ledger-claim-v1", "r3-ledger-settlement-v1"}
    required = {
        "protocol_id",
        "run_id",
        "case_id",
        "arm",
        "stage",
        "contract_disposition",
        "effect_applied_verdict",
        "resolving_observation",
        "scope",
        "source_refs",
    }
    assert required <= set(report["rows"][0])


def test_settlement_stage_is_the_discriminator():
    report = _renderer().build_contract_report(ROOT)
    run = "2026-11-08-ledger-settlement-v1-controls"
    for case_id in ("S01", "S02"):
        for arm in ("classical", "bmo"):
            claim = _rows(report, run_id=run, case_id=case_id, arm=arm, stage="claim")
            assert claim["effect_applied_verdict"] == "unresolved"
            assert claim["contract_disposition"] == "committed"
            assert claim["resolving_observation"] is None
    for arm in ("classical", "bmo"):
        applied = _rows(report, run_id=run, case_id="S01", arm=arm, stage="settlement")
        absent = _rows(report, run_id=run, case_id="S02", arm=arm, stage="settlement")
        assert applied["contract_disposition"] == "applied"
        assert applied["effect_applied_verdict"] == "supported"
        assert applied["resolving_observation"]["to"] == "supported"
        assert applied["resolving_observation"]["observation_id"] is None
        assert applied["resolving_observation"]["record_identity"] == "not_retained"
        assert applied["resolving_observation"]["call_id"] == "call-s01"
        assert absent["contract_disposition"] == "not_entered"
        assert absent["effect_applied_verdict"] == "refuted"
        assert absent["resolving_observation"]["to"] == "refuted"
        assert absent["resolving_observation"]["call_id"] == "call-s02"
        assert absent["resolving_observation"]["record_identity"] == "not_retained"
        for number in range(3, 10):
            refused = _rows(report, run_id=run, case_id=f"S0{number}", arm=arm, stage="settlement")
            assert refused["contract_disposition"] == "refused"
            assert refused["effect_applied_verdict"] == "unresolved"
            assert refused["effect_applied_verdict"] != "refuted"


def test_refusal_has_no_settlement_and_keeps_claim():
    report = _renderer().build_contract_report(ROOT)
    run = "2026-11-08-ledger-settlement-v1-controls"
    for number in range(3, 10):
        for arm in ("classical", "bmo"):
            row = _rows(report, run_id=run, case_id=f"S0{number}", arm=arm, stage="settlement")
            assert row["persisted_state"]["claim_count"] == 1
            assert row["persisted_state"]["settlement_present"] is False
            assert row["persisted_state"]["grant_spent"] is True


def test_rejects_missing_duplicate_and_cross_case_rows():
    module = _renderer()
    report = module.build_contract_report(ROOT)
    sample = next(row for row in report["observations"]["controls"]["classical"] if row["case_id"] == "S01")
    cases = module.load_settlement_cases(ROOT)
    with pytest.raises(ValueError, match="missing"):
        module.validate_observations(cases, [row for row in report["observations"]["controls"]["classical"] if row is not sample])
    with pytest.raises(ValueError, match="duplicate"):
        module.validate_observations(cases, report["observations"]["controls"]["classical"] + [dict(sample)])
    crossed = dict(sample)
    crossed["state"] = dict(sample["state"])
    crossed["state"]["claim_call_ids"] = ["call-s02"]
    with pytest.raises(ValueError, match="cross-case"):
        module.validate_observations(cases, [crossed if row is sample else row for row in report["observations"]["controls"]["classical"]])
