"""R4 evidence-sufficiency and three-way conclusion protocol tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.evidence_sufficiency import (  # noqa: E402
    WORLDS,
    assess_permission,
    blind_observation,
    evaluate_method_success,
    run_protocol_cases,
    true_observation,
)
from swarm_witness.schema import validate_claim, validate_finding, validate_run  # noqa: E402


def test_blind_worlds_are_missing_evidence():
    a = assess_permission(WORLDS["A"], blind_observation())
    b = assess_permission(WORLDS["B"], blind_observation())
    assert a["conclusion_class"] == b["conclusion_class"] == "missing_evidence"
    assert a["finding_label"] == "unresolved"
    assert a["decision"] is None and b["decision"] is None
    assert a["visible_receipt"] == b["visible_receipt"]


def test_correct_gate_is_supported():
    a = assess_permission(WORLDS["A"], true_observation(WORLDS["A"]))
    b = assess_permission(WORLDS["B"], true_observation(WORLDS["B"]))
    assert a["conclusion_class"] == "supported"
    assert b["conclusion_class"] == "supported"
    assert a["decision"] == "allow"
    assert b["decision"] == "deny"


def test_broken_gate_is_failed_enforcement_not_supported():
    b = assess_permission(
        WORLDS["B"],
        true_observation(WORLDS["B"]),
        gate_behavior="broken_allow_when_revoked",
    )
    assert b["decision"] == "allow"
    assert b["required_decision"] == "deny"
    assert b["conclusion_class"] == "failed_enforcement"
    assert b["finding_label"] == "contradicted_in_scope"
    assert b["assessment"] == "enforcement_failed"

    a = assess_permission(
        WORLDS["A"],
        true_observation(WORLDS["A"]),
        gate_behavior="broken_deny_when_active",
    )
    assert a["decision"] == "deny"
    assert a["required_decision"] == "allow"
    assert a["conclusion_class"] == "failed_enforcement"


def test_irrelevant_observation_stays_missing_evidence():
    a = assess_permission(WORLDS["A"], blind_observation(irrelevant=True))
    assert a["conclusion_class"] == "missing_evidence"
    assert a["justified_permission_claim"] is False


def test_protocol_exercises_all_three_classes():
    cases = run_protocol_cases()
    score = evaluate_method_success(cases)
    assert score["passed"] is True
    assert score["three_way_classes_exercised"] is True
    assert score["failed_enforcement_count"] >= 2
    assert score["missing_evidence_count"] >= 1
    assert score["supported_count"] >= 1


def test_runner_writes_valid_evidence(tmp_path: Path):
    spec = importlib.util.spec_from_file_location(
        "r4_run", ROOT / "experiments" / "evidence_sufficiency" / "run.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["r4_run"] = mod
    spec.loader.exec_module(mod)

    cases = mod.run_protocol_cases()
    score = mod.evaluate_method_success(cases)
    out = mod.write_evidence(tmp_path, cases, score)
    assert out["finding"]["label"] == "reproduced"
    assert "missing_evidence" in out["finding"]["proposition"]
    assert "failed_enforcement" in out["finding"]["proposition"]
    validate_finding(out["finding"])
    for path in (tmp_path / "runs").glob("*.json"):
        validate_run(json.loads(path.read_text(encoding="utf-8")))
    claim = validate_claim(
        __import__("yaml").safe_load(
            (ROOT / "claims" / "r4_evidence_sufficiency.yaml").read_text(encoding="utf-8")
        )
    )
    assert claim.id == "r4"
