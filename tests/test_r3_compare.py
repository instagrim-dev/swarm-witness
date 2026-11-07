"""R3 matched decision-model comparison: unmatched BMO cannot succeed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from swarm_witness.schema import validate_finding, validate_run

ROOT = Path(__file__).resolve().parents[1]
COMPARE = ROOT / "experiments" / "r3" / "compare.py"
CASES = ROOT / "experiments" / "r3" / "cases.yaml"


def _load_compare():
    spec = importlib.util.spec_from_file_location("r3_compare", COMPARE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _minimal_case_record(
    *,
    case_id: str,
    arm: str,
    execution_status: str,
    decision: str | None,
    inputs: dict,
    evaluator_outcome: str,
) -> dict:
    return {
        "id": f"{arm}-{case_id}",
        "claim_id": "r3",
        "protocol_id": "r3-matched-decision-model",
        "case_id": case_id,
        "source_pin": "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe",
        "execution_status": execution_status,
        "observations": {
            "case_id": case_id,
            "inputs": inputs,
            "action": inputs.get("request"),
            "decision": decision,
            "effect": None,
            "evaluator_outcome": evaluator_outcome,
            "arm": arm,
            "observation_refs": [f"{arm}-{case_id}.observations.decision"],
        },
    }


def test_unmatched_bmo_case_cannot_yield_classical_baseline_matches(tmp_path):
    """classical completed, bmo missing → compare rejects success label."""
    mod = _load_compare()
    cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 4

    classical_runs: list[dict] = []
    bmo_runs: list[dict] = []
    for case in cases:
        cid = case["case_id"]
        inputs = case["inputs"]
        classical_runs.append(
            _minimal_case_record(
                case_id=cid,
                arm="classical",
                execution_status="completed",
                decision=case["expected_decision"],
                inputs=inputs,
                evaluator_outcome="ok",
            )
        )
        # One (or all) BMO arms missing — unmatched.
        bmo_runs.append(
            _minimal_case_record(
                case_id=cid,
                arm="bmo",
                execution_status="missing",
                decision=None,
                inputs=inputs,
                evaluator_outcome="missing_isomorphic_observation",
            )
        )

    finding, pairs = mod.build_comparison_finding(
        cases=cases,
        classical_runs=classical_runs,
        bmo_runs=bmo_runs,
        bmo_git_rev="4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe",
    )
    validate_finding(finding)
    assert finding["label"] != "classical_baseline_matches"
    assert finding["label"] in {"assumption_dependent", "unresolved"}
    assert any(p["bmo_status"] == "missing" for p in pairs)
    assert finding["label"] != "classical_baseline_matches"


def test_all_matched_decisions_may_emit_classical_baseline_matches():
    mod = _load_compare()
    cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]
    classical_runs = []
    bmo_runs = []
    for case in cases:
        cid = case["case_id"]
        inputs = case["inputs"]
        decision = case["expected_decision"]
        classical_runs.append(
            _minimal_case_record(
                case_id=cid,
                arm="classical",
                execution_status="completed",
                decision=decision,
                inputs=inputs,
                evaluator_outcome="ok",
            )
        )
        bmo_runs.append(
            _minimal_case_record(
                case_id=cid,
                arm="bmo",
                execution_status="completed",
                decision=decision,
                inputs=inputs,
                evaluator_outcome="ok",
            )
        )
    finding, pairs = mod.build_comparison_finding(
        cases=cases,
        classical_runs=classical_runs,
        bmo_runs=bmo_runs,
        bmo_git_rev="4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe",
    )
    validate_finding(finding)
    assert all(p["decision_match"] for p in pairs)
    assert finding["label"] == "classical_baseline_matches"


def test_cases_yaml_lists_four_required_intents():
    data = yaml.safe_load(CASES.read_text(encoding="utf-8"))
    ids = {c["case_id"] for c in data["cases"]}
    assert "retained_start_claim_relaunch" in ids
    assert "rejected_execute" in ids
    assert "active_grant_execute" in ids
    assert "stale_grant_version" in ids
    stale = next(c for c in data["cases"] if c["case_id"] == "stale_grant_version")
    assert stale["epistemic_extension"]["distinguishing_observation"] == "grant_version"


def test_classical_arm_emits_validated_runs(tmp_path, monkeypatch):
    mod = _load_compare()
    monkeypatch.setattr(mod, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(mod, "FINDINGS_DIR", tmp_path / "findings")
    monkeypatch.setattr(mod, "EV", tmp_path)
    monkeypatch.setattr(mod, "SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(mod, "RESULT", tmp_path / "result.yaml")

    classical = mod.emit_classical_runs()
    assert len(classical) >= 4
    for run in classical:
        validate_run(run)
        assert run["execution_status"] == "completed"
        assert run["observations"]["arm"] == "classical"
        assert run["observations"]["decision"] in {"allow", "deny"}
        assert "grant_version" in run["observations"]["inputs"]


def test_bmo_missing_isomorphic_cannot_fill_from_pass_counts(tmp_path, monkeypatch):
    """Instrumented harness must not invent decisions from go-test pass tallies."""
    mod = _load_compare()
    monkeypatch.setattr(mod, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(mod, "FINDINGS_DIR", tmp_path / "findings")
    monkeypatch.setattr(mod, "EV", tmp_path)
    monkeypatch.setattr(mod, "SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(mod, "RESULT", tmp_path / "result.yaml")
    # Fake a green BMO package log — still must not invent isomorphic decisions.
    log = tmp_path / "bmo_go_test.log"
    log.write_text(
        "--- PASS: TestOrdinaryRetryRetainedGrantShapeControls (0.01s)\n"
        "ok  github.com/instagrim-dev/bmo/internal/sessioncompaction\t0.2s\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "BMO_LOG", log)

    bmo_runs = mod.emit_bmo_runs(
        bmo_git_rev="4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe",
        package_pass_count=6,
    )
    for run in bmo_runs:
        validate_run(run)
        assert run["observations"]["arm"] == "bmo"
        # Without isomorphic probes, decisions must not be filled from pass counts.
        if run["execution_status"] == "missing":
            assert run["observations"]["decision"] is None
            assert run["observations"]["evaluator_outcome"] == (
                "missing_isomorphic_observation"
            )
        else:
            # If a probe completed, it must cite an observation_ref, not pass_count.
            assert "package_pass_count" not in run["observations"].get(
                "decision_source", ""
            )
