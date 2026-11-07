"""R2 parse derives metrics from results.json rows; no successful no-op."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swarm_witness.schema import validate_finding, validate_run

ROOT = Path(__file__).resolve().parents[1]
PARSE = ROOT / "experiments" / "r2" / "parse_summary.py"


def _load_parse():
    import importlib.util

    spec = importlib.util.spec_from_file_location("r2_parse_summary", PARSE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _row(
    *,
    scenario: str,
    seed: int,
    passed: bool = True,
    produced_correct: int = 0,
    produced_errors: int = 0,
    old_rule_errors: int = 0,
    safer_supported: int = 0,
    outcomes: dict | None = None,
) -> dict:
    return {
        "scenario": scenario,
        "seed": seed,
        "passed": passed,
        "score": {
            "produced": {
                "correct": produced_correct,
                "confident_errors": produced_errors,
            }
        },
        "controls": {
            "implicit_token_exclusivity": {
                "confident_errors": old_rule_errors,
            }
        },
        "outcomes": outcomes
        if outcomes is not None
        else {"ambiguous": 0, "unmatched": 0, "supported": safer_supported},
    }


def test_count_from_row_records_not_hardcoded():
    mod = _load_parse()
    rows = [
        _row(
            scenario="full_receipt_relay",
            seed=0,
            old_rule_errors=1,
            safer_supported=0,
            produced_correct=0,
        ),
        _row(
            scenario="full_receipt_relay",
            seed=1,
            old_rule_errors=1,
            safer_supported=0,
            produced_correct=0,
        ),
        _row(
            scenario="shared_tokens_no_attack",
            seed=0,
            produced_correct=0,
        ),
        _row(
            scenario="false_exclusivity",
            seed=0,
            produced_errors=1,
        ),
        _row(scenario="clean", seed=0, passed=True),
    ]
    counted = mod.count_from_row_records(rows)
    assert counted["condition_by_seed_checks"] == 5
    assert counted["condition_by_seed_passed"] == 5
    assert counted["row_record_count"] == 5
    # Denominator is counted from this fixture, not a planned constant.
    assert counted["condition_by_seed_checks"] != 36
    assert counted["old_rule_wrong_attributions_on_relay"] == [1, 1]
    assert counted["safer_supported_on_relay"] == [0, 0]
    assert counted["shared_tokens_correct"] == [0]
    assert counted["false_exclusivity_confident_errors"] == [1]
    assert counted["clean_withheld_without_exclusivity"] == [12]


def test_count_rejects_empty_rows():
    mod = _load_parse()
    with pytest.raises(ValueError, match="non-empty"):
        mod.count_from_row_records([])


def test_derive_from_retained_results(tmp_path, monkeypatch):
    mod = _load_parse()
    rows = []
    for seed in (0, 1, 2):
        rows.append(
            _row(
                scenario="full_receipt_relay",
                seed=seed,
                old_rule_errors=1,
                safer_supported=0,
                produced_correct=0,
                outcomes={"ambiguous": 10, "unmatched": 2, "supported": 0},
            )
        )
        rows.append(
            _row(
                scenario="shared_tokens_no_attack",
                seed=seed,
                produced_correct=0,
            )
        )
        rows.append(
            _row(
                scenario="false_exclusivity",
                seed=seed,
                produced_errors=1,
            )
        )
        for scenario in (
            "clean",
            "fabricated",
            "missing_transcript",
            "copied_public_receipt",
            "missing_tokens",
            "missing_clock_bound",
            "dependent_witnesses",
            "incomplete_capture",
            "capture_window_edge",
        ):
            rows.append(_row(scenario=scenario, seed=seed))

    assert len(rows) == 36
    results = {
        "passed": True,
        "failures": [],
        "seeds": [0, 1, 2],
        "source_tree_sha256": "abc",
        "rows": rows,
    }
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(results), encoding="utf-8")

    monkeypatch.setattr(mod, "EV", tmp_path)
    monkeypatch.setattr(mod, "RESULTS", results_path)
    monkeypatch.setattr(mod, "SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(mod, "RESULT", tmp_path / "result.yaml")
    monkeypatch.setattr(mod, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(mod, "FINDINGS_DIR", tmp_path / "findings")
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    run, finding = mod.derive_from_results(results_path)
    validate_run(run)
    validate_finding(finding)
    assert run["execution_status"] == "completed"
    assert run["observations"]["condition_by_seed_checks"] == 36
    assert run["observations"]["denominator_source"] == "counted_from_rows"
    assert finding["label"] == "reproduced"
    assert finding["basis"] == "computed"
    assert finding["label"] != "classical_baseline_matches"
    assert (tmp_path / "runs" / f"{mod.RUN_ID}.json").is_file()
    assert (tmp_path / "findings" / f"{mod.FINDING_ID}.json").is_file()


def test_missing_results_writes_unrun_unresolved(tmp_path, monkeypatch):
    mod = _load_parse()
    monkeypatch.setattr(mod, "EV", tmp_path)
    monkeypatch.setattr(mod, "RESULTS", tmp_path / "missing.json")
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
    assert finding["label"] != "classical_baseline_matches"


def test_committed_results_counts_match_rows():
    """Regression: committed results.json denominators come from rows."""
    mod = _load_parse()
    results_path = ROOT / "evidence" / "r2" / "results.json"
    if not results_path.is_file():
        pytest.skip("committed results.json not present")
    data = json.loads(results_path.read_text(encoding="utf-8"))
    counted = mod.count_from_row_records(data["rows"])
    assert counted["condition_by_seed_checks"] == len(data["rows"])
    assert counted["condition_by_seed_passed"] == sum(
        1 for r in data["rows"] if r.get("passed")
    )
    assert counted["row_record_count"] == len(data["rows"])
