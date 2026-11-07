"""Blinded incident-audit acceptance checks for issue #27."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.incident_audit import (  # noqa: E402
    evaluate,
    observations_for_stage,
    prepare_observations,
    render_prompt,
    summarize,
    swarm_witness_verdict,
)

EXP = ROOT / "experiments" / "incident_audit"


def _load(name: str):
    return yaml.safe_load((EXP / name).read_text(encoding="utf-8"))


def _bundle():
    claim = yaml.safe_load((ROOT / "claims" / "incident_claims_v1.yaml").read_text())
    claims = claim["frozen_propositions"]
    observations = prepare_observations(_load("excerpts_v1.yaml")["observations"])
    protocol = _load("protocol_v1.yaml")
    adjudication = _load("adjudication_v1.yaml")
    return claims, observations, protocol, adjudication


def _rows():
    claims, observations, protocol, adjudication = _bundle()
    return claims, observations, protocol, evaluate(
        claims, observations, adjudication, protocol
    )


def _swarm(rows, claim_id, stage):
    return next(
        row
        for row in rows
        if row["claim_id"] == claim_id
        and row["stage"] == stage
        and row["method"] == "swarm_witness"
    )


def test_frozen_corpus_shape():
    claim = yaml.safe_load((ROOT / "claims" / "incident_claims_v1.yaml").read_text())
    propositions = claim["frozen_propositions"]
    assert 10 <= len(propositions) <= 12
    families = {item["family"] for item in propositions}
    assert len(families) >= 4
    assert set(claim["controls"]) == {
        "spoofed_tool_transcript",
        "copied_shared_receipt",
        "source_dependency",
        "url_allowlist_as_whole_system",
    }
    assert any(item["deliberately_ambiguous"] for item in propositions)
    assert any(item["discriminating_update"] for item in propositions)


def test_stage_b_markers_absent_from_stage_a_prompts_and_warrants():
    claims, observations, _protocol, adjudication = _bundle()
    stage_a = observations_for_stage(observations, "A")
    prompts = "\n".join(render_prompt(claim, stage_a) for claim in claims)
    warrants = "\n".join(
        adjudication["claims"][claim["id"]]["A"]["reason"] for claim in claims
    )
    stage_a_ids = {obs["id"] for obs in stage_a}
    for obs in observations:
        if obs["stage"] != "B":
            continue
        assert obs["id"] not in stage_a_ids
        assert obs["id"] not in prompts
        for marker in obs.get("leakage_markers", []):
            assert marker not in prompts
            assert marker not in warrants


def test_methods_share_observation_ids_and_abstentions_stay_in_denominator():
    claims, _observations, protocol, rows = _rows()
    totals = summarize(rows, protocol)
    assert totals["cell_count_per_method"] == len(claims) * 2
    for claim in claims:
        for stage in ("A", "B"):
            ids = {
                tuple(row["observation_ids"])
                for row in rows
                if row["claim_id"] == claim["id"] and row["stage"] == stage
            }
            assert len(ids) == 1
    assert totals["primary_endpoint_passed"] is True
    assert totals["swarm_witness_unsupported"] < totals["naive_unsupported"]
    assert totals["swarm_witness_unsupported"] < totals["checklist_unsupported"]
    accounted = sum(
        totals[f"swarm_witness_{name}"] for name in protocol["categories"]
    )
    assert accounted == totals["cell_count_per_method"]


def test_controls_ambiguous_case_and_discriminating_updates():
    _claims, _observations, _protocol, rows = _rows()
    for stage in ("A", "B"):
        ambiguous = _swarm(rows, "C04", stage)
        assert ambiguous["predicted"] == "unresolved"
        assert ambiguous["category"] == "correct_refusal"
    assert _swarm(rows, "C03", "A")["predicted"] == "unresolved"
    assert _swarm(rows, "C03", "B")["predicted"] == "refuted"
    assert _swarm(rows, "C05", "A")["predicted"] == "unresolved"
    assert _swarm(rows, "C05", "B")["predicted"] == "refuted"
    for claim_id in ("C03", "C05", "C11", "C12"):
        for stage in ("A", "B"):
            assert _swarm(rows, claim_id, stage)["category"] not in {
                "false_support_against_refuted",
                "false_support_against_unresolved",
            }
    copied = _swarm(rows, "C11", "B")
    assert copied["swarm"]["support_group_count"] == 1
    assert copied["swarm"]["withheld_dependent_count"] == 1
    assert copied["predicted"] == "unresolved"
    dependency = _swarm(rows, "C12", "B")
    assert dependency["predicted"] == "unresolved"
    assert dependency["swarm"]["support_group_count"] == 1
    hdf5 = _swarm(rows, "C06", "B")
    assert hdf5["predicted"] == "unresolved"
    assert hdf5["swarm"]["assertion_status"] == "cross_source_asserted"
    assert hdf5["swarm"]["verification_status"] == "raw_telemetry_unverified"


def test_ablations_change_the_unsupported_count_or_block_the_update():
    claims, observations, protocol, adjudication = _bundle()
    primary = summarize(
        evaluate(claims, observations, adjudication, protocol), protocol
    )
    trusted = summarize(
        evaluate(
            claims,
            observations,
            adjudication,
            protocol,
            ignore_independence=True,
            count_derived_as_independent=True,
            public_text_verifies_world_effects=True,
        ),
        protocol,
    )
    assert trusted["swarm_witness_unsupported"] > primary["swarm_witness_unsupported"]
    stage_a = observations_for_stage(observations, "A")
    by_id = {claim["id"]: claim for claim in claims}
    assert swarm_witness_verdict(by_id["C03"], stage_a)["epistemic_status"] == "unresolved"
    assert swarm_witness_verdict(by_id["C05"], stage_a)["epistemic_status"] == "unresolved"
    collapsed = swarm_witness_verdict(
        by_id["C05"], stage_a, scope_collapse=True
    )
    assert collapsed["epistemic_status"] == "supported"


def test_irrelevant_message_does_not_upgrade_delegation():
    claims, observations, _protocol, _adjudication = _bundle()
    claim = next(item for item in claims if item["id"] == "C08")
    stage_b = observations_for_stage(observations, "B")
    before = swarm_witness_verdict(claim, stage_b)
    extra = dict(stage_b[0])
    extra["id"] = "E-irrelevant"
    extra["applies_to"] = ["C08"]
    extra["literal_claims"] = []
    extra["quote"] = "unrelated sandbox wallpaper color"
    extra["content_sha256"] = "unused"
    after = swarm_witness_verdict(claim, [*stage_b, extra])
    assert before["epistemic_status"] == after["epistemic_status"] == "unresolved"


def test_qualifier_does_not_name_the_adjudication_file():
    source = (ROOT / "src" / "swarm_witness" / "incident_audit.py").read_text()
    assert "adjudication_v1.yaml" not in source
    tree = ast.parse(source)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "open" not in called


def test_runner_matches_summary_and_does_not_claim_prevention():
    spec = importlib.util.spec_from_file_location(
        "incident_audit_run", ROOT / "experiments" / "incident_audit" / "run.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run(ROOT)
    summary = json.loads(
        (ROOT / "evidence" / "incident_audit_v1" / "summary.json").read_text()
    )
    assert summary == result["summary"]
    assert summary["detection_or_prevention_claimed"] is False
    assert summary["primary_endpoint_passed"] is True
    finding = json.loads(
        (
            ROOT
            / "evidence"
            / "incident_audit_v1"
            / "findings"
            / "incident-audit-v1-f-comparison.json"
        ).read_text()
    )
    text = finding["proposition"].lower()
    assert "not incident detection or prevention" in text
    assert "would have prevented" not in text
