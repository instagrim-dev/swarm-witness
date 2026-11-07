"""R1 parse derives denominators from case records; no successful no-op."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swarm_witness.schema import validate_finding, validate_run

ROOT = Path(__file__).resolve().parents[1]
PARSE = ROOT / "experiments" / "r1" / "parse_summary.py"


def _load_parse():
    import importlib.util

    spec = importlib.util.spec_from_file_location("r1_parse_summary", PARSE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_count_from_case_records_not_hardcoded():
    mod = _load_parse()
    cases = [
        {"policy": "original", "status": "prohibited_effect"},
        {"policy": "original", "status": "supported"},
        {"policy": "barrier", "status": "supported"},
        {"policy": "barrier", "status": "supported"},
        {"policy": "strict", "status": "refused_before_ack"},
        {"policy": "strict", "status": "supported"},
    ]
    counted = mod.count_from_case_records(cases)
    assert counted["histories_per_policy"] == 2
    assert counted["case_record_count"] == 6
    assert counted["prohibited_effects_by_policy"]["original"] == 1
    assert counted["prohibited_effects_by_policy"]["barrier"] == 0
    # Denominator is counted from this fixture, not a planned constant.
    assert counted["histories_per_policy"] != 153


def test_count_rejects_empty_cases():
    mod = _load_parse()
    with pytest.raises(ValueError, match="non-empty"):
        mod.count_from_case_records([])


def test_derive_from_retained_analysis(tmp_path, monkeypatch):
    mod = _load_parse()
    analysis = {
        "all_checks_pass": True,
        "raw_sha256": "abc",
        "analyzer_sha256": "def",
        "cases": (
            [{"policy": "original", "status": "prohibited_effect"} for _ in range(3)]
            + [{"policy": "strict", "status": "refused_before_ack"} for _ in range(3)]
            + [{"policy": "barrier", "status": "supported"} for _ in range(3)]
        ),
    }
    analysis_path = tmp_path / "local-run-analysis.json"
    analysis_path.write_text(json.dumps(analysis), encoding="utf-8")

    monkeypatch.setattr(mod, "EV", tmp_path)
    monkeypatch.setattr(mod, "ANALYSIS", analysis_path)
    monkeypatch.setattr(mod, "SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(mod, "RESULT", tmp_path / "result.yaml")
    monkeypatch.setattr(mod, "RAW", tmp_path / "raw.json")
    monkeypatch.setattr(mod, "CARGO_LOG", tmp_path / "cargo.log")
    monkeypatch.setattr(mod, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(mod, "FINDINGS_DIR", tmp_path / "findings")
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    run, finding = mod.derive_from_analysis(analysis_path)
    validate_run(run)
    validate_finding(finding)
    assert run["execution_status"] == "completed"
    assert run["observations"]["histories_per_policy"] == 3
    assert run["observations"]["denominator_source"] == "counted_from_cases"
    assert run["observations"]["prohibited_effects_barrier"] == 0
    assert finding["label"] == "reproduced"
    assert finding["basis"] == "computed"
    assert (tmp_path / "runs" / f"{mod.RUN_ID}.json").is_file()
    assert (tmp_path / "findings" / f"{mod.FINDING_ID}.json").is_file()


def test_missing_analysis_writes_unrun_unresolved(tmp_path, monkeypatch):
    mod = _load_parse()
    monkeypatch.setattr(mod, "EV", tmp_path)
    monkeypatch.setattr(mod, "ANALYSIS", tmp_path / "missing.json")
    monkeypatch.setattr(mod, "SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(mod, "RESULT", tmp_path / "result.yaml")
    monkeypatch.setattr(mod, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(mod, "FINDINGS_DIR", tmp_path / "findings")
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    rc = mod.main([])
    assert rc == 1
    run = json.loads((tmp_path / "runs" / f"{mod.RUN_ID}.json").read_text())
    finding = json.loads((tmp_path / "findings" / f"{mod.FINDING_ID}.json").read_text())
    validate_run(run)
    validate_finding(finding)
    assert run["execution_status"] == "unrun"
    assert finding["label"] == "unresolved"


def test_committed_analysis_counts_match_records():
    """Regression: committed local-run-analysis denominators come from cases."""
    mod = _load_parse()
    analysis_path = ROOT / "evidence" / "r1" / "local-run-analysis.json"
    if not analysis_path.is_file():
        pytest.skip("committed local-run-analysis.json not present")
    data = json.loads(analysis_path.read_text(encoding="utf-8"))
    counted = mod.count_from_case_records(data["cases"])
    assert counted["histories_per_policy"] == len(
        [c for c in data["cases"] if c["policy"] == "barrier"]
    )
    assert counted["prohibited_effects_by_policy"]["barrier"] == sum(
        1 for c in data["cases"] if c["policy"] == "barrier" and c["status"] == "prohibited_effect"
    )
    # Must equal the field only if the analyzer agrees; source of truth is cases.
    assert counted["histories_per_policy"] == data["histories_per_policy"]
