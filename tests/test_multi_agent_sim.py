"""Multi-agent simulator (issue #10) acceptance tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.multi_agent_sim import (  # noqa: E402
    evaluate_protocol_success,
    replay_traces_match,
    run_protocol_cases,
    run_scenario,
)
from swarm_witness.multi_agent_sim.policy import get_policy  # noqa: E402
from swarm_witness.multi_agent_sim.scenarios import (  # noqa: E402
    interleaving_a_first,
    interleaving_b_first,
    mutant_contention_arm,
    reference_contention_arm,
)
from swarm_witness.multi_agent_sim.scheduler import run_schedule  # noqa: E402
from swarm_witness.schema import validate_claim, validate_finding, validate_run  # noqa: E402


def test_protocol_passes_acceptance_bundle():
    cases = run_protocol_cases()
    score = evaluate_protocol_success(cases)
    assert score["passed"] is True, score["errors"]
    assert score["three_way_classes_exercised"] is True
    assert score["case_count"] >= 8
    assert score["missing_evidence_count"] >= 2
    assert score["failed_enforcement_count"] >= 1
    assert score["supported_count"] >= 2


def test_two_materially_different_interleavings():
    a = run_scenario(interleaving_a_first())
    b = run_scenario(interleaving_b_first())
    a_winners = [
        c["agent"] for c in a["evaluation"]["claims"] if c["committed_effect"]
    ]
    b_winners = [
        c["agent"] for c in b["evaluation"]["claims"] if c["committed_effect"]
    ]
    assert a_winners == ["A"]
    assert b_winners == ["B"]
    assert a["trace"] != b["trace"]


def test_decision_effect_owner_conclusion_are_distinct_fields():
    case = run_scenario(interleaving_a_first())
    for claim in case["evaluation"]["claims"]:
        assert "decision" in claim
        assert "committed_effect" in claim
        assert "authoritative_owner_state" in claim
        assert "conclusion_class" in claim
        assert "local_knowledge_at_decision" in claim
        assert "evaluator_learned_afterward" in claim
        # Schema independence: presence of decision does not imply effect.
        assert isinstance(claim["committed_effect"], bool)
        denom = claim["observation_denominators"]
        assert denom["required_count"] == 1
        assert "present_count" in denom


def test_reference_permits_progress_and_one_use_mutant_counterexample():
    ref = run_scenario(reference_contention_arm())
    mut = run_scenario(mutant_contention_arm())
    assert ref["manifest"]["schedule"]["steps"] == mut["manifest"]["schedule"]["steps"]
    assert ref["evaluation"]["one_use_ok"] is True
    assert mut["evaluation"]["one_use_ok"] is False
    mut_commits = [c for c in mut["evaluation"]["claims"] if c["committed_effect"]]
    assert len(mut_commits) == 2
    bad = next(c for c in mut["evaluation"]["claims"] if c["call_id"] == "b-claim")
    assert bad["decision"] == "allow"
    assert bad["committed_effect"] is True
    assert bad["required_decision"] == "deny"
    assert bad["conclusion_class"] == "failed_enforcement"
    assert bad["diagnosis"]["decision_status"] == "incorrect"
    assert bad["diagnosis"]["effect_status"] == "committed"


def test_paired_worlds_indistinguishable_until_distinguishing_observation():
    cases = {c["case_id"]: c for c in run_protocol_cases()}
    ka = cases["paired_world_active_blind"]["claims_by_id"]["b-blind"][
        "local_knowledge_at_decision"
    ]
    kr = cases["paired_world_revoked_blind"]["claims_by_id"]["b-blind"][
        "local_knowledge_at_decision"
    ]
    assert ka["grant_observations"] == kr["grant_observations"] == []
    assert (
        cases["paired_world_active_blind"]["claims_by_id"]["b-blind"]["conclusion_class"]
        == "missing_evidence"
    )
    assert (
        cases["paired_world_active_irrelevant"]["claims_by_id"]["b-irr"][
            "conclusion_class"
        ]
        == "missing_evidence"
    )
    assert (
        cases["paired_world_revoked_irrelevant"]["claims_by_id"]["b-irr"][
            "conclusion_class"
        ]
        == "missing_evidence"
    )
    da = cases["paired_world_active_distinguished"]["claims_by_id"]["b-disc"]
    dr = cases["paired_world_revoked_distinguished"]["claims_by_id"]["b-disc"]
    assert da["decision"] == "allow" and dr["decision"] == "deny"
    assert da["conclusion_class"] == dr["conclusion_class"] == "supported"


def test_replay_stability_same_seed_schedule():
    assert replay_traces_match() is True
    spec = interleaving_a_first()
    t1 = run_schedule(spec.schedule, get_policy("reference")).relevant_trace()
    t2 = run_schedule(spec.schedule, get_policy("reference")).relevant_trace()
    assert t1 == t2


def test_revocation_late_observation_case_present():
    cases = {c["case_id"]: c for c in run_protocol_cases()}
    late = cases["revocation_late_observation_reference"]
    b_late = late["claims_by_id"]["b-late"]
    c_fresh = late["claims_by_id"]["c-fresh"]
    assert b_late["conclusion_class"] == "failed_enforcement"
    assert b_late["committed_effect"] is True
    assert c_fresh["conclusion_class"] == "supported"
    assert c_fresh["decision"] == "deny"


def test_runner_writes_valid_evidence(tmp_path: Path):
    spec = importlib.util.spec_from_file_location(
        "mas_run", ROOT / "experiments" / "multi_agent_sim" / "run.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["mas_run"] = mod
    spec.loader.exec_module(mod)
    cases = mod.run_protocol_cases()
    score = mod.evaluate_protocol_success(cases)
    replay_ok = mod.replay_traces_match()
    out = mod.write_evidence(tmp_path, cases, score, replay_ok)
    assert out["finding"]["label"] == "reproduced"
    validate_finding(
        {k: v for k, v in out["finding"].items() if k not in {"conclusion_class", "evaluation_method"}}
    )
    for path in (tmp_path / "runs").glob("*.json"):
        validate_run(json.loads(path.read_text(encoding="utf-8")))
    assert (tmp_path / "traces").glob("*.json")
    assert (tmp_path / "manifests").glob("*.json")
    claim = validate_claim(
        yaml.safe_load(
            (ROOT / "claims" / "multi_agent_sim.yaml").read_text(encoding="utf-8")
        )
    )
    assert claim.id == "multi_agent_sim"


def test_does_not_mutate_r5_sequential_semantics():
    """R5 sequential module remains importable and passing (no relabel)."""
    from swarm_witness.swarm_audit import (
        evaluate_swarm_method_success,
        run_swarm_protocol_cases,
    )

    cases = run_swarm_protocol_cases()
    score = evaluate_swarm_method_success(cases)
    assert score["passed"] is True
