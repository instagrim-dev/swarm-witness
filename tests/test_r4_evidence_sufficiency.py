"""R4 evidence-sufficiency protocol tests."""

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


def test_blind_worlds_indistinguishable_and_unsupported():
    a = assess_permission(WORLDS["A"], blind_observation())
    b = assess_permission(WORLDS["B"], blind_observation())
    assert a["assessment"] == b["assessment"] == "unsupported"
    assert a["decision"] is None and b["decision"] is None
    assert a["visible_receipt"] == b["visible_receipt"]
    assert a["justified_permission_claim"] is False


def test_discriminator_separates_worlds():
    a = assess_permission(WORLDS["A"], true_observation(WORLDS["A"]))
    b = assess_permission(WORLDS["B"], true_observation(WORLDS["B"]))
    assert a["assessment"] == "permission_justified"
    assert b["assessment"] == "permission_refuted"
    assert a["decision"] == "allow"
    assert b["decision"] == "deny"


def test_irrelevant_observation_does_not_upgrade():
    a = assess_permission(WORLDS["A"], blind_observation(irrelevant=True))
    assert a["assessment"] == "unsupported"
    assert a["justified_permission_claim"] is False


def test_protocol_score_passes():
    cases = run_protocol_cases()
    score = evaluate_method_success(cases)
    assert score["passed"] is True
    assert score["indistinguishable_when_blind"] is True
    assert score["discriminator_separates_worlds"] is True


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
    validate_finding(out["finding"])
    for path in (tmp_path / "runs").glob("*.json"):
        validate_run(json.loads(path.read_text(encoding="utf-8")))
    claim = validate_claim(
        __import__("yaml").safe_load(
            (ROOT / "claims" / "r4_evidence_sufficiency.yaml").read_text(encoding="utf-8")
        )
    )
    assert claim.id == "r4"
