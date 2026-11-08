"""Conformance for the retained-observation binding of issue #40."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from swarm_witness.evidence_binding import (
    FINITE_ABSTRACTIONS,
    MEMBERSHIP_ASSUMPTIONS,
    PROTOCOL_ID,
    audit_claim_run,
    audit_entrypoint,
    bind_family,
    collapse_origins,
    finite_abstraction,
    load_property_case,
    records_from_lineage,
    records_from_property_case,
    binding_from_property_case,
)
from swarm_witness.evidence_binding_conformance import run_conformance
from swarm_witness.schema import validate_claim, validate_finding, validate_run

ROOT = Path(__file__).resolve().parents[1]
RUN_PATH = ROOT / "evidence" / "evidence_binding_v1" / "runs" / "evidence-binding-v1-run.json"

ABSTRACTION_FIELDS = (
    "proposition",
    "quantifier",
    "actor_scope",
    "task_scope",
    "target_event",
    "target_time",
    "worlds",
    "satisfying_worlds",
    "observation_constraints",
)


def _claim() -> dict:
    return {
        "id": "evidence_binding_v1",
        "source_ref": "protocol/evidence_binding_v1.md",
        "source_version": "evidence-binding-v1",
        "original_proposition": "Retained observations license a nonempty subset judgment.",
        "operational_interpretation": "Translate records, then apply the production verdict.",
        "property": "Conditional soundness of the evidence binding.",
        "scope": "Declared families on retained records.",
        "quantifier": "The records offered to this run.",
        "success_criterion": "The production verdict matches the reference on those records.",
        "assumptions": ["Actual-world membership is assumed, not certified by a hash."],
    }


def _run(observations: dict, run_id: str = "evidence-binding-probe") -> dict:
    return {
        "id": run_id,
        "claim_id": "evidence_binding_v1",
        "protocol_id": PROTOCOL_ID,
        "case_id": "probe",
        "source_pin": "evidence-binding-v1",
        "execution_status": "completed",
        "observations": observations,
    }


def _public(record_id: str, **overrides: object) -> dict:
    record: dict = {
        "id": record_id,
        "kind": "public",
        "authenticity": "authentic_public_text",
        "family": "P_url",
        "channel": "remote_url",
        "polarity": "supports",
        "independence_group": record_id,
        "event_time": "2026-01-01T00:00:00Z",
        "time_basis": "source_stated",
        "locally_held": True,
        "access_level": "public_bytes",
    }
    record.update(overrides)
    return record


def test_every_supported_family_documents_a_finite_abstraction():
    assert set(FINITE_ABSTRACTIONS) == {
        "P_url",
        "P_file_read",
        "P_exec",
        "P_identity",
        "P_effect",
        "P_local_control",
        "P_decision_entitlement",
        "P_commit_authorization",
        "P_commitment",
        "P_system",
        "P_dec",
        "P_eff",
        "comparison_equality",
    }
    for family in FINITE_ABSTRACTIONS:
        documented = finite_abstraction(family)
        assert documented is not None
        for field in ABSTRACTION_FIELDS:
            assert documented[field], family
        assert documented["worlds"]
        assert set(documented["satisfying_worlds"]) <= set(documented["worlds"])
    system = finite_abstraction("P_system")
    assert system is not None
    assert "conjunction" in system["proposition"]
    assert "URL allowlist" in system["observation_constraints"]


def test_unsupported_family_returns_an_explicit_unresolved_reason():
    result = bind_family([], family="population_attribution", claim={})
    assert result["epistemic_status"] == "unresolved"
    assert result["conclusion_class"] == "missing_evidence"
    assert "population_attribution" in result["reason"]
    assert "no finite abstraction" in result["reason"]
    assert result["real_world_authenticity_certified"] is False
    latency = bind_family([], family="historical_response_latency", claim={})
    assert "historical_response_latency" in latency["reason"]


def test_entrypoint_runs_retained_workflow_and_native_packet_not_bitmasks():
    entry = audit_entrypoint(ROOT)
    system = entry["retained_system"]
    url = entry["retained_url"]
    native = entry["native"]
    assert system["input"] == "retained_workflow"
    assert system["case_id"] == "url_held_worker_local_read"
    assert system["epistemic_status"] == "refuted"
    assert system["conclusion_class"] == "failed_enforcement"
    assert system["failure_origin"] == "effect_boundary"
    assert system["decision_status"] == "unknown"
    assert system["effect_status"] == "committed"
    assert system["fault_attribution"] == "undetermined"
    assert system["comparison_status"] == "not_applicable"
    assert url["epistemic_status"] == "supported"
    assert entry["url_allowlist_supports_p_system"] is False
    assert native["input"] == "native_witness_packet"
    assert native["event_count"] > 0
    assert native["truth_files_read"] == []
    assert native["epistemic_status"] == "unresolved"
    assert native["evidence_status"] == "missing"
    assert native["authenticity_counts"]["not_checked"] > 0
    assert native["authenticity_counts"]["forged"] > 0
    assert entry["sqlite_witness_built"] is False
    assert entry["detection_or_prevention_claimed"] is False
    with pytest.raises(ValueError, match="bitmasks"):
        audit_claim_run(
            _claim(),
            _run({"property_mask": 15, "evidence_mask": 1, "verified": True}),
        )


def test_claim_run_path_uses_retained_records():
    case = load_property_case(ROOT)
    records = records_from_property_case(case)
    binding = binding_from_property_case(case)
    binding["family"] = "P_file_read"
    result = audit_claim_run(_claim(), _run({"records": records, "binding": binding}))
    validate_claim(_claim())
    validate_run(_run({"records": records, "binding": binding}))
    assert result["epistemic_status"] == "refuted"
    assert result["conclusion_class"] == "failed_enforcement"
    assert result["failure_origin"] == "effect_boundary"
    assert "property_mask" not in result


def test_nondeciding_authenticity_does_not_support_or_refute():
    for authenticity in (
        "spoofed_tool_line",
        "unauthenticated_tool_line",
        "unavailable",
        "not_checked",
    ):
        for polarity in ("supports", "contradicts"):
            result = bind_family(
                [
                    _public(
                        f"{authenticity}-{polarity}",
                        authenticity=authenticity,
                        polarity=polarity,
                        coverage="complete",
                    )
                ],
                family="P_url",
                claim={},
            )
            assert result["epistemic_status"] == "unresolved", authenticity
            assert result["conclusion_class"] == "missing_evidence"
    spoof = bind_family(
        [_public("spoof", authenticity="spoofed_tool_line", coverage="complete")],
        family="P_url",
        claim={},
    )
    assert spoof["evidence_status"] == "misbound"
    assert spoof["compatible_worlds"] == []
    missing = bind_family(
        [_public("plain", authenticity="not_checked", coverage="complete")],
        family="P_url",
        claim={},
    )
    assert missing["evidence_status"] == "missing"
    assert missing["compatible_worlds"]


def test_missing_observations_preserve_alternatives_until_a_completeness_premise():
    partial = bind_family([_public("partial")], family="P_url", claim={})
    assert partial["epistemic_status"] == "unresolved"
    pair = partial["compatible_world_pair"]
    assert pair is not None
    assert pair["satisfying"] in partial["compatible_worlds"]
    assert pair["violating"] in partial["compatible_worlds"]
    duplicate = _public("partial-copy", content_digest="other-digest", independence_group="partial")
    duplicated = bind_family([_public("partial"), duplicate], family="P_url", claim={})
    assert duplicated["compatible_world_pair"] == pair
    assert duplicated["independent_origin_count"] == 1
    discriminating = bind_family(
        [_public("partial"), _public("full", coverage="complete", independence_group="full")],
        family="P_url",
        claim={},
    )
    assert discriminating["epistemic_status"] == "supported"
    assert discriminating["compatible_world_pair"] is None
    assert discriminating["compatible_worlds"] == ["clear"]


def test_closed_world_absence_needs_a_declared_completeness_premise():
    quiet = {
        "id": "quiet",
        "kind": "model_event",
        "authenticity": "model_ledger",
        "channel": "remote_url",
        "committed": False,
        "decision": "deny",
        "subject_class": "unapproved",
        "independence_group": "quiet",
        "event_time": 1,
        "time_basis": "source_stated",
    }
    open_result = bind_family([quiet], family="P_commitment", claim={"ledger_declared": True})
    assert open_result["epistemic_status"] == "unresolved"
    assert "coverage_unobserved" in open_result["compatible_worlds"]
    closed = bind_family(
        [quiet],
        family="P_commitment",
        claim={
            "ledger_declared": True,
            "completeness_premise": {
                "declared": True,
                "operation": "effect_commit",
                "completeness": "complete",
            },
        },
    )
    assert closed["epistemic_status"] == "refuted"
    assert closed["compatible_worlds"] == ["no_effect_row"]
    assert closed["reason"] == "no_effect_row"


def test_lesswrong_group_is_one_origin_across_digests_and_dependencies():
    graph = yaml.safe_load(
        (ROOT / "experiments" / "provenance" / "incident_lineage.yaml").read_text(
            encoding="utf-8"
        )
    )["graphs"][0]
    records = records_from_lineage(graph)
    lesswrong = [
        record
        for record in records
        if record["independence_group"] == "lesswrong-reproduction-2026-09"
    ]
    assert len(lesswrong) == 2
    assert len({record["content_digest"] for record in lesswrong}) == 2
    _, keys = collapse_origins(lesswrong)
    assert len(set(keys.values())) == 1
    judged = bind_family(
        [
            _public(
                "post",
                coverage="complete",
                independence_group="lesswrong-reproduction-2026-09",
                content_digest="digest-post",
            ),
            _public(
                "appendix",
                coverage="complete",
                independence_group="lesswrong-reproduction-2026-09",
                content_digest="digest-appendix",
                depends_on=["post"],
            ),
        ],
        family="P_url",
        claim={"minimum_independent_groups": 2},
    )
    assert judged["independent_origin_count"] == 1
    assert judged["epistemic_status"] == "unresolved"
    lineage = bind_family(records, family="P_system", claim={})
    assert lineage["epistemic_status"] == "unresolved"
    assert lineage["unavailable_sources"]
    assert lineage["real_world_authenticity_certified"] is False


def test_unavailable_original_is_recorded_and_is_not_a_gate():
    support = _public("held", coverage="complete", independence_group="held")
    unavailable = _public(
        "original",
        authenticity="unavailable",
        access_level="withheld",
        observation_availability="withheld",
        locally_held=False,
        independence_group="missing-original",
        polarity="reports",
    )
    result = bind_family([support, unavailable], family="P_url", claim={})
    assert result["epistemic_status"] == "supported"
    assert {item["id"] for item in result["unavailable_sources"]} == {"original"}
    with pytest.raises(ValueError, match="upgrade gate"):
        bind_family(
            [support, {**unavailable, "blocks_upgrade": True}],
            family="P_url",
            claim={},
        )
    held_gate = _public(
        "gate",
        polarity="reports",
        independence_group="gate",
        blocks_upgrade=True,
    )
    blocked = bind_family([support, held_gate], family="P_url", claim={})
    assert blocked["epistemic_status"] == "unresolved"
    assert blocked["evidence_status"] == "unverified"
    assert blocked["reason"] == "upgrade_blocked"


def test_effect_confirmation_requires_actor_object_and_operation():
    case = load_property_case(ROOT)
    records = records_from_property_case(case)
    binding = binding_from_property_case(case)
    binding.update(
        {
            "target_actor": "alice",
            "target_object": "other-object",
            "target_operation": "local_read",
        }
    )
    mismatched = bind_family(records, family="P_file_read", claim=binding)
    assert mismatched["epistemic_status"] == "unresolved"
    mapped = []
    for record in records:
        item = dict(record)
        if item["id"] == "read-1":
            item["verified_mapping"] = True
        mapped.append(item)
    confirmed = bind_family(mapped, family="P_file_read", claim=binding)
    assert confirmed["epistemic_status"] == "refuted"
    assert confirmed["failure_origin"] == "effect_boundary"


def test_refuted_text_is_not_failed_enforcement_and_time_binds_refutation():
    untimed = bind_family(
        [
            _public(
                "untimed",
                family="P_eff",
                polarity="contradicts",
                exercised_mechanism=False,
                event_time=None,
                time_basis="missing",
            )
        ],
        family="P_eff",
        claim={"requires_event_time": True},
    )
    assert untimed["epistemic_status"] == "unresolved"
    assert untimed["property_holds"] is None
    timed = bind_family(
        [
            _public(
                "timed",
                family="P_eff",
                polarity="contradicts",
                exercised_mechanism=False,
            )
        ],
        family="P_eff",
        claim={"requires_event_time": True},
    )
    assert timed["epistemic_status"] == "refuted"
    assert timed["conclusion_class"] == "refuted"
    assert timed["conclusion_class"] != "failed_enforcement"
    assert timed["failure_origin"] == "undetermined"
    assert timed["mechanism_exercised"] is False
    stale = bind_family(
        [
            _public(
                "stale",
                coverage="complete",
                temporal_applicability="stale",
                authenticity="authentic_public_text",
            )
        ],
        family="P_url",
        claim={},
    )
    assert stale["epistemic_status"] == "unresolved"
    assert stale["evidence_status"] == "authentic"
    assert stale["fabricated"] is False
    assert stale["stale_is_fabricated"] is False
    assert stale["stale_record_ids"] == ["stale"]


def test_comparison_decision_effect_and_fault_stay_separate():
    arms = []
    for index, decision in enumerate(("allow", "deny")):
        arms.append(
            {
                "id": f"arm-{index}",
                "kind": "comparison_arm",
                "decision": decision,
                "property_holds": True,
                "evidence_complete": True,
                "grant": "active",
                "effect_committed": False,
                "authenticity": "model_ledger",
                "independence_group": f"arm-{index}",
                "time_basis": "source_stated",
                "event_time": 1,
            }
        )
    divergent = bind_family(arms, family="comparison_equality", claim={})
    assert divergent["conclusion_class"] == "comparison_divergent"
    assert divergent["failure_origin"] == "comparison_equality"
    assert divergent["decision_status"] == "unknown"
    assert divergent["effect_status"] == "not_applicable"
    assert divergent["fault_attribution"] == "undetermined"
    for arm in arms:
        arm["decision"] = "deny"
        arm["grant"] = "revoked"
        arm["property_holds"] = False
        arm["effect_committed"] = True
    unauthorized = bind_family(arms, family="comparison_equality", claim={})
    assert unauthorized["conclusion_class"] == "failed_enforcement"
    assert unauthorized["failure_origin"] == "effect_boundary"
    assert unauthorized["decision_status"] == "correct"
    assert unauthorized["effect_status"] == "committed"
    blame = bind_family(
        [
            _public(
                "other-prop",
                coverage="complete",
                attribute_fault=True,
                actor_ref="bob",
                actor_binding="bound",
                proposition_family="P_identity",
                family="P_identity",
                channel="credential",
            )
        ],
        family="P_url",
        claim={},
    )
    assert blame["fault_attribution"] == "undetermined"
    named = bind_family(
        [
            _public(
                "same-prop",
                coverage="complete",
                attribute_fault=True,
                actor_ref="ada",
                actor_binding="bound",
                proposition_family="P_url",
            )
        ],
        family="P_url",
        claim={},
    )
    assert named["epistemic_status"] == "supported"
    assert named["fault_attribution"] == "ada"


def test_irrelevant_addition_does_not_move_a_supported_world_set():
    held = _public("held", coverage="complete", independence_group="held")
    other = _public(
        "other",
        family="P_identity",
        channel="credential",
        polarity="contradicts",
        coverage="complete",
        independence_group="other",
    )
    before = bind_family([held], family="P_url", claim={})
    after = bind_family([held, other], family="P_url", claim={})
    assert before["epistemic_status"] == after["epistemic_status"] == "supported"
    assert before["compatible_worlds"] == after["compatible_worlds"]


def test_membership_assumptions_deny_hash_and_test_certificates():
    result = bind_family([_public("held", coverage="complete")], family="P_url", claim={})
    assert result["source_digest_proves_authenticity"] is False
    assert result["passing_tests_prove_completeness"] is False
    assert result["real_world_authenticity_certified"] is False
    assert result["detection_or_prevention_claimed"] is False
    assert result["actual_world_membership"].startswith("assumed")
    text = " ".join(MEMBERSHIP_ASSUMPTIONS).lower()
    assert "content digest" in text
    assert "passing conformance test" in text
    assert "does not certify" in text or "not proof" in text


def test_reference_does_not_call_the_production_verdict():
    import ast

    reference_path = ROOT / "src" / "swarm_witness" / "formal" / "evidence_reference.py"
    reference_tree = ast.parse(reference_path.read_text(encoding="utf-8"))
    imported: list[str] = []
    called: list[str] = []
    for node in ast.walk(reference_tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.append(node.func.id)
    assert imported == ["__future__"]
    assert "production_verdict" not in called
    production = (ROOT / "src" / "swarm_witness" / "evidence_binding.py").read_text(
        encoding="utf-8"
    )
    assert "evidence_reference" not in production
    assert "evaluate_case" not in production
    assert "mask_verdict" not in production


def test_conformance_catches_each_mutation_and_agrees_when_unmutated():
    report = run_conformance(ROOT)
    assert report["passed"] is True
    assert report["domain"]["passed"] is True
    assert report["domain"]["compared"] > 0
    assert report["domain"]["refinements"] > 0
    assert report["records"]["passed"] is True
    assert report["records"]["invalid_evidence_status"] == "misbound"
    assert report["records"]["not_checked_evidence_status"] == "missing"
    assert report["records"]["empty_verified"] is True
    assert report["entrypoint_agreement"] is True
    assert report["mutations"] == {
        "verification": True,
        "empty_set": True,
        "property_kind": True,
        "temporal_binding": True,
    }


def test_committed_run_matches_the_entrypoint():
    import json

    saved = json.loads(RUN_PATH.read_text(encoding="utf-8"))
    validate_run(saved)
    finding = json.loads(
        (
            ROOT
            / "evidence"
            / "evidence_binding_v1"
            / "findings"
            / "evidence-binding-v1-f.json"
        ).read_text(encoding="utf-8")
    )
    validate_finding(finding)
    report = run_conformance(ROOT)
    observed = saved["observations"]
    assert observed["passed"] is True
    assert observed["retained_case_id"] == "url_held_worker_local_read"
    assert observed["retained_p_system_epistemic"] == report["retained_system_epistemic"]
    assert observed["retained_p_system_conclusion"] == "failed_enforcement"
    assert observed["retained_failure_origin"] == "effect_boundary"
    assert observed["retained_decision_status"] == "unknown"
    assert observed["retained_effect_status"] == "committed"
    assert observed["retained_fault_attribution"] == "undetermined"
    assert observed["retained_p_url_epistemic"] == "supported"
    assert observed["url_allowlist_supports_p_system"] is False
    assert observed["native_epistemic"] == "unresolved"
    assert observed["native_evidence_status"] == "missing"
    assert observed["native_packet_event_count"] == report["native_event_count"]
    assert observed["native_truth_files_read"] == 0
    assert observed["reference_agreement"] is True
    assert observed["real_world_authenticity_certified"] is False
    assert observed["detection_or_prevention_claimed"] is False
    assert observed["source_digest_proves_authenticity"] is False
    assert observed["passing_tests_prove_completeness"] is False
    assert observed["sqlite_witness_built"] is False
    assert finding["label"] == "reproduced"
    assert finding["basis"] == "computed"
