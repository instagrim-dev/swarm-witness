"""Blinded incident-audit acceptance checks for issue #27."""

from __future__ import annotations

import ast
import copy
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
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402

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


def _pins():
    spec = importlib.util.spec_from_file_location(
        "incident_verify_pins", EXP / "verify_pins.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_pins_quotes_and_unavailable_telemetry():
    pins = _pins()
    manifest = _load("corpus_manifest.yaml")
    excerpts = _load("excerpts_v1.yaml")
    passages = _load("pinned_passages.yaml")
    assert pins.manifest_errors(manifest, excerpts) == []
    assert pins.passage_errors(excerpts, passages) == []
    raw = b'<a href="#x">&gt;70,000 messages and files</a>'
    assert b">70,000 messages and files" not in raw
    assert pins.quote_in_unescaped(">70,000 messages and files", raw)
    first = b'<script>window.requestId = "Root=1-aaaa";</script><p>allowlist</p>'
    second = b'<script>window.requestId = "Root=1-bbbb";</script><p>allowlist</p>'
    assert first != second
    assert pins.normalize_huggingface_html(first) == pins.normalize_huggingface_html(
        second
    )
    assert pins.sha256(pins.normalize_huggingface_html(first)) == pins.sha256(
        pins.normalize_huggingface_html(second)
    )
    unavailable = {item["id"] for item in manifest["unavailable"]}
    assert set(pins.UNAVAILABLE_TELEMETRY) <= unavailable
    claims, observations, _protocol, rows = _rows()
    assert all(obs.get("access_level") != "raw_telemetry_public" for obs in observations)
    world = {claim["id"] for claim in claims if claim["kind"] == "world_effect"}
    for row in rows:
        if row["method"] != "swarm_witness" or row["claim_id"] not in world:
            continue
        assert row["predicted"] == "unresolved"
        assert row["swarm"]["verification_status"] == "raw_telemetry_unverified"


def test_sufficiency_refutation_is_not_failed_enforcement():
    claims, observations, _protocol, _adjudication = _bundle()
    by_id = {claim["id"]: claim for claim in claims}
    stage_b = observations_for_stage(observations, "B")
    for claim_id in ("C03", "C05"):
        verdict = swarm_witness_verdict(by_id[claim_id], stage_b)
        assert verdict["epistemic_status"] == "refuted"
        assert verdict["conclusion_class"] == "refuted"
        assert verdict["conclusion_class"] != "failed_enforcement"
        assert verdict["effect_status"] == "unobserved"
        assert verdict["decision_status"] == "unknown"
        assert verdict["failure_origin"] == "undetermined"
        assert verdict["evidence_status"] == "authentic"
        assert verdict["verification_status"] == "raw_telemetry_unverified"
        assert verdict["real_world_authenticity_certified"] is False
        assert verdict["detection_or_prevention_claimed"] is False
    assert swarm_witness_verdict(by_id["C05"], stage_b)["failure_origin"] != "effect_boundary"


def _census_packet():
    comp = ROOT / "experiments" / "incident_audit" / "comparison"
    claims = yaml.safe_load((comp / "claims_v1.yaml").read_text())["claims"]
    packets = prepare_observations(
        yaml.safe_load((comp / "packets_v1.yaml").read_text())["observations"]
    )
    claim = next(item for item in claims if item["id"] == "K-census")
    return claim, packets


def test_spoofed_or_unauthenticated_census_is_not_supported():
    claim, packets = _census_packet()
    strong = strong_invariant_verdict(claim, packets)
    swarm = swarm_witness_verdict(claim, packets)
    assert strong["epistemic_status"] == "supported"
    assert swarm["epistemic_status"] == "supported"
    assert swarm["evidence_status"] == "authentic"
    for authenticity in ("spoofed_tool_line", "unauthenticated_tool_line"):
        altered = copy.deepcopy(packets)
        census = next(obs for obs in altered if obs["id"] == "CENSUS")
        census["authenticity"] = authenticity
        strong_bad = strong_invariant_verdict(claim, altered)
        swarm_bad = swarm_witness_verdict(claim, altered)
        assert strong_bad["epistemic_status"] == "unresolved"
        assert swarm_bad["epistemic_status"] == "unresolved"
        assert strong_bad.get("evidence_status") != "authentic"
        assert swarm_bad["evidence_status"] != "authentic"
        assert swarm_bad["real_world_authenticity_certified"] is False


def test_context_record_does_not_attribute_census_to_bob():
    claim, packets = _census_packet()
    alone_strong = strong_invariant_verdict(claim, packets)
    alone_swarm = swarm_witness_verdict(claim, packets)
    assert alone_strong["epistemic_status"] == "supported"
    assert alone_swarm["epistemic_status"] == "supported"
    assert alone_strong["attributed_origin"] == "undetermined"
    assert alone_swarm["attributed_origin"] == "undetermined"
    contextual = prepare_observations(
        [
            {
                "id": "CTX-BOB",
                "source_id": "context",
                "independence_group": "context-bob",
                "stage": "A",
                "publication_ordinal": 3,
                "authenticity": "authentic_public_text",
                "access_level": "released_reproduction_transcript",
                "locally_held": True,
                "quote": "Policy allows Bob to read an unrelated file.",
                "applies_to": ["K-census"],
                "literal_claims": ["K-other"],
                "literal_polarity": "supports",
                "observation_types": ["policy_allow"],
                "named_origin": "Bob",
            }
        ]
    )
    with_bob = [*packets, *contextual]
    strong = strong_invariant_verdict(claim, with_bob)
    swarm = swarm_witness_verdict(claim, with_bob)
    assert strong["epistemic_status"] == "supported"
    assert swarm["epistemic_status"] == "supported"
    assert strong["attributed_origin"] == "undetermined"
    assert swarm["attributed_origin"] == "undetermined"
    assert strong["attributed_origin"] != "Bob"
    assert swarm["attributed_origin"] != "Bob"
