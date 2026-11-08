"""External calibration: EvidenceGraph, SoundGate, BMO, LessWrong adapters."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r2_packets_preserve_native_scenarios():
    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from r2_packets import FOCAL, build_packets

    packets = build_packets()
    assert len(packets) == 6
    scenarios = {p["claim"]["scenario"] for p in packets}
    assert scenarios <= set(FOCAL)
    relay = next(p for p in packets if p["claim"]["id"] == "EG-R2-ATTR-relay-possession")
    assert relay["warranted_conclusion"]["status"] == "unresolved"
    assert relay["native_arms"]["evidencegraph_safer_independent_binding"]["verdict"] == (
        "unresolved"
    )
    assert (
        relay["native_arms"]["evidencegraph_old_implicit_token_exclusivity"]["verdict"]
        == "supported"
    )
    shared = next(
        p for p in packets if p["claim"]["id"] == "EG-R2-ATTR-shared-tokens-no-exclusivity"
    )
    assert shared["observations"][0]["authenticity"] == "authentic_public_text"
    assert "token_exclusivity" in shared["claim"]["required_observation_types"]
    assert "token_exclusivity" not in shared["observations"][0]["observation_types"]
    false_ex = next(
        p for p in packets if p["claim"]["id"] == "EG-R2-ATTR-false-exclusivity"
    )
    assert set(false_ex["claim"]["required_observation_types"]).issubset(
        set(false_ex["observations"][0]["observation_types"])
    )
    # Scorer diagnostics stay out of method observation inputs.
    obs = false_ex["observations"][0]
    assert "premise_status" not in obs
    assert "invalid_assumption_control" not in obs["quote"]
    assert "confident_errors" not in obs["quote"]
    assert false_ex["factual_outcome"]["premise_status"] == "false"
    assert "confident_errors" in false_ex["factual_outcome"]


def test_r1_packets_separate_restriction_and_availability():
    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from r1_packets import build_packets

    packets = build_packets()
    by_id = {p["claim"]["id"]: p for p in packets}
    assert by_id["SG-R1-RESTRICT-strict"]["warranted_conclusion"]["status"] == "supported"
    assert by_id["SG-R1-AVAIL-strict"]["warranted_conclusion"]["status"] == "refuted"
    assert by_id["SG-R1-RESTRICT-barrier"]["warranted_conclusion"]["status"] == "supported"
    assert by_id["SG-R1-AVAIL-barrier"]["warranted_conclusion"]["status"] == "supported"
    # Only the named policy is scored as a native arm for each claim.
    assert set(by_id["SG-R1-AVAIL-strict"]["native_arms"]) == {"soundgate_policy_strict"}
    assert (
        by_id["SG-R1-AVAIL-strict"]["native_arms"]["soundgate_policy_strict"]["verdict"]
        == "refuted"
    )
    assert (
        by_id["SG-R1-AVAIL-barrier"]["native_arms"]["soundgate_policy_barrier"]["verdict"]
        == "supported"
    )
    assert "soundgate_policy_barrier" in by_id["SG-R1-AVAIL-strict"]["cross_policy_reference"]


def test_lw_packets_do_not_score_copied_warrants_as_native():
    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from lw_packets import build_packets

    packets = build_packets()
    by_id = {p["claim"]["id"]: p for p in packets}
    assert by_id["LW-K-release"]["warranted_conclusion"]["status"] == "supported"
    assert by_id["LW-K-certify"]["warranted_conclusion"]["status"] == "unresolved"
    assert by_id["LW-K-census"]["warranted_conclusion"]["status"] == "supported"
    assert by_id["LW-K-gate"]["warranted_conclusion"]["status"] == "unresolved"
    assert by_id["LW-K-env-scope"]["warranted_conclusion"]["status"] == "refuted"
    assert "lesswrong_scope_discipline" not in by_id["LW-K-certify"]["native_arms"]
    assert by_id["LW-K-certify"]["author_scope_reading"]["reconstruction"] is True
    assert (
        by_id["LW-K-certify"]["native_arms"]["reconstructed_narrative_overread"][
            "reconstruction"
        ]
        is True
    )


def test_r2_event_packets_export_relations_without_leaking_native():
    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from r2_event_packets import build_packets

    packets = build_packets()
    assert packets
    families = {p["claim"]["family"] for p in packets}
    assert families == {"event_attribution", "fabricated_execution"}
    scenarios = {p["claim"]["scenario"] for p in packets}
    assert "missing_tokens" in scenarios
    assert "missing_clock_bound" in scenarios
    assert "dependent_witnesses" in scenarios
    assert "capture_window_edge" in scenarios
    assert "fabricated" in scenarios

    clean_attr = [
        p
        for p in packets
        if p["claim"]["scenario"] == "clean" and p["claim"]["family"] == "event_attribution"
    ]
    assert clean_attr
    sample = clean_attr[0]
    assert "evidencegraph_safer_produced" in sample["native_arms"]
    assert "eg_evidence_derived_adapter" in sample["native_arms"]
    # Assessor observations exclude native outcomes / private truth / scenario title.
    for obs in sample["observations"]:
        blob = json.dumps(obs)
        assert "native_outcome" not in blob
        assert "premise_status" not in blob
        assert "confident_errors" not in blob
        assert "private_truth" not in blob
    decl = next(
        o for o in sample["observations"] if "declared_assumptions" in o["observation_types"]
    )
    assert "title" not in decl["declared_assumptions"]
    assert "clock_bounds" in decl["declared_assumptions"]

    # Proposed tool_event_record entities must be real tool events (event_uuid).
    for packet in packets:
        if packet["claim"]["family"] != "event_attribution":
            continue
        for obs in packet["observations"]:
            if "tool_event_record" not in obs.get("observation_types", []):
                continue
            assert (obs.get("entity") or {}).get("attrs", {}).get("event_uuid")

    clock = next(
        p for p in packets if p["claim"]["scenario"] == "missing_clock_bound"
    )
    assert clock["native_arms"]["evidencegraph_safer_produced"]["verdict"] == "unresolved"
    assert clock["native_arms"]["eg_evidence_derived_adapter"]["verdict"] == "unresolved"
    assert clock["native_arms"]["eg_evidence_derived_adapter"]["reason"] == "no_clock_bound"

    fab = [
        p
        for p in packets
        if p["claim"]["scenario"] == "fabricated"
        and p["claim"]["family"] == "fabricated_execution"
    ]
    assert fab
    for packet in fab:
        assert "fabricated_receipt_record" not in json.dumps(packet["observations"])
        assert packet["native_arms"]["evidencegraph_safer_executed"]["verdict"] == "refuted"
        assert packet["native_arms"]["eg_evidence_derived_adapter"]["verdict"] == "refuted"

    edge_fab = [
        p
        for p in packets
        if p["claim"]["scenario"] == "capture_window_edge"
        and p["claim"]["family"] == "fabricated_execution"
    ]
    assert edge_fab
    assert all(
        p["native_arms"]["evidencegraph_safer_executed"]["verdict"] == "unresolved"
        for p in edge_fab
    )
    assert all(
        p["native_arms"]["eg_evidence_derived_adapter"]["verdict"] == "unresolved"
        for p in edge_fab
    )
    edge_attr = [
        p
        for p in packets
        if p["claim"]["scenario"] == "capture_window_edge"
        and p["claim"]["family"] == "event_attribution"
        and p["native_arms"]["evidencegraph_safer_produced"]["verdict"] == "supported"
    ]
    assert edge_attr, "capture-window edge must retain some supported attributions"

    # Factual labels: native abstention must not invent known=false without private truth.
    for packet in packets:
        if packet["claim"]["family"] != "event_attribution":
            continue
        factual = packet["factual_outcome"]
        if factual.get("known") is True:
            assert "truth_event_uuid" in factual or factual.get("proposition_holds") is not None


def test_eg_adapter_behavioral_predicates_and_input_independence():
    """Discriminating checks: binding, temporal, trust, absence; native-field independence."""
    import copy
    from datetime import datetime, timedelta

    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from eg_evidence_adapter import assess_attribution, assess_fabricated_execution
    from r2_event_packets import (
        assessor_input_fingerprint,
        build_packets,
        mutate_native_fields_for_independence_check,
    )

    packets = build_packets()
    clean = next(
        p
        for p in packets
        if p["claim"]["scenario"] == "clean" and p["claim"]["family"] == "event_attribution"
    )
    assert clean["native_arms"]["eg_evidence_derived_adapter"]["verdict"] == "supported"

    # Receipt token no longer matches commitment → must not stay supported.
    obs = copy.deepcopy(clean["observations"])
    for row in obs:
        if "tool_event_record" in row.get("observation_types", []):
            row["entity"]["attrs"]["receipt"]["receipt_token"] = "deadbeef_not_matching"
    result = assess_attribution(clean["claim"], obs)
    assert result["verdict"] == "unresolved"
    assert result["reason"] == "receipt_token_commitment_mismatch"

    # Event interval one day after mutation → temporal incompatibility.
    obs = copy.deepcopy(clean["observations"])
    for row in obs:
        if "tool_event_record" in row.get("observation_types", []):
            start = datetime.fromisoformat(row["entity"]["time_lower"].replace("Z", "+00:00"))
            row["entity"]["time_lower"] = (start + timedelta(days=1)).isoformat()
            row["entity"]["time_upper"] = (
                start + timedelta(days=1, microseconds=100)
            ).isoformat()
    result = assess_attribution(clean["claim"], obs)
    assert result["verdict"] == "unresolved"
    assert result["reason"] == "temporal_incompatible"

    # Trust-domain declarations removed → affirmative assumptions missing.
    obs = copy.deepcopy(clean["observations"])
    for row in obs:
        if "declared_assumptions" in row.get("observation_types", []):
            row["declared_assumptions"]["trust_domains"] = []
    result = assess_attribution(clean["claim"], obs)
    assert result["verdict"] == "unresolved"
    assert result["reason"] in {"independence_undeclared", "exclusivity_undeclared"}

    # Clean successful event under complete capture must not be refuted by absence.
    export = json.loads(
        (ROOT / "evidence" / "external_calibration_v1" / "eg_native_relations_seed0.json").read_text(
            encoding="utf-8"
        )
    )
    scenario = next(s for s in export["scenarios"] if s["scenario"] == "clean")
    event = next(
        e
        for e in scenario["public_entities"]["tool_events"]
        if (e.get("attrs") or {}).get("event_uuid")
        and ((e.get("attrs") or {}).get("receipt") or {}).get("accepted") is True
    )
    decl = scenario["declared_assumptions"]
    exec_obs = [
        {
            "observation_types": ["declared_assumptions"],
            "declared_assumptions": {
                "clock_bounds": decl.get("clock_bounds") or [],
                "trust_domains": decl.get("trust_domains") or [],
            },
        },
        {
            "observation_types": ["capture_declaration"],
            "populations": scenario["public_entities"]["populations"],
        },
        {
            "observation_types": ["tool_event_record", "successful_execution_claim"],
            "entity": event,
        },
        {
            "observation_types": ["registry_mutation_population"],
            "registry_mutations": scenario["public_entities"]["registry_mutations"],
        },
    ]
    result = assess_fabricated_execution({"id": "clean-exec"}, exec_obs)
    assert result["verdict"] == "unresolved"
    assert result["reason"] == "claimed_event_id_present_in_registry"

    # The retained population declares 12 mutations and lists event-000007.
    # Dropping only that detail row must not refute the genuine execution.
    genuine = next(
        e
        for e in scenario["public_entities"]["tool_events"]
        if ((e.get("attrs") or {}).get("receipt") or {}).get("event_id") == "event-000007"
    )
    populations = scenario["public_entities"]["populations"]
    assert populations[0]["count"] == 12
    assert "event-000007" in populations[0]["event_ids"]
    mutations = list(scenario["public_entities"]["registry_mutations"])
    assert len(mutations) == 12

    def _execution_obs(rows):
        observed = copy.deepcopy(exec_obs)
        for row in observed:
            if "successful_execution_claim" in row.get("observation_types", []):
                row["entity"] = genuine
            if "registry_mutation_population" in row.get("observation_types", []):
                row["registry_mutations"] = rows
        return observed

    held = assess_fabricated_execution({"id": "genuine-held"}, _execution_obs(mutations))
    assert held["verdict"] == "unresolved"
    assert held["reason"] == "claimed_event_id_present_in_registry"
    assert held["predicates"]["population_detail_complete"] is True
    trimmed = [
        row
        for row in mutations
        if str(row.get("natural_key")) != "event-000007"
        and str((row.get("attrs") or {}).get("id")) != "event-000007"
    ]
    assert len(trimmed) == 11
    missing = assess_fabricated_execution(
        {"id": "genuine-missing-detail"}, _execution_obs(trimmed)
    )
    assert missing["verdict"] == "unresolved"
    assert missing["reason"] == "population_lists_events_missing_detail_rows"
    assert missing["reason"] != "absence_under_complete_covering_capture"
    assert missing["predicates"]["claimed_mutation_absent"] is False
    assert missing["predicates"]["capture_covers_execution"] is False
    assert missing["predicates"]["population_detail_complete"] is False
    assert missing["predicates"]["population_missing_event_ids"] == ["event-000007"]
    assert missing["predicates"]["coverage_detail"] == missing["reason"]
    assert missing["predicates"]["absence_detail"] == missing["reason"]

    # Changing native outcomes/object_ids/candidates must not change assessor inputs.
    import tempfile
    from pathlib import Path

    mutated = mutate_native_fields_for_independence_check(export)
    tmp = Path(tempfile.mkdtemp()) / "mutated_export.json"
    tmp.write_text(json.dumps(mutated), encoding="utf-8")
    alt_packets = build_packets(tmp)
    base_fp = {
        (p["claim"]["scenario"], p["claim"]["mutation_id"]): assessor_input_fingerprint(
            p["observations"]
        )
        for p in packets
        if p["claim"]["family"] == "event_attribution"
    }
    alt_fp = {
        (p["claim"]["scenario"], p["claim"]["mutation_id"]): assessor_input_fingerprint(
            p["observations"]
        )
        for p in alt_packets
        if p["claim"]["family"] == "event_attribution"
    }
    assert base_fp == alt_fp


def test_composed_classifiers_consume_adapter_derivations():
    """Support / refute / unresolved / false-exclusivity + composed-input independence."""
    import copy
    import tempfile
    from pathlib import Path

    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from eg_adapter_projector import composed_observations, project_checks
    from r2_event_packets import (
        assessor_input_fingerprint,
        build_packets,
        mutate_native_fields_for_independence_check,
    )
    from swarm_witness.incident_audit import swarm_witness_verdict
    from swarm_witness.strong_invariant import strong_invariant_verdict

    packets = build_packets()

    def _composed(packet):
        assessment, projected = composed_observations(
            packet["claim"], packet["observations"]
        )
        obs = list(packet["observations"]) + projected
        return assessment, projected, obs

    # Support path: clean attribution.
    clean = next(
        p
        for p in packets
        if p["claim"]["scenario"] == "clean" and p["claim"]["family"] == "event_attribution"
    )
    assessment, projected, composed_obs = _composed(clean)
    assert assessment["verdict"] == "supported"
    assert len(projected) == 1
    proj = projected[0]
    assert proj["id"]
    assert clean["claim"]["id"] in proj["applies_to"]
    assert "independence_group" in proj
    assert proj["derivation"] == "adapter_checks"
    assert proj["literal_polarity"] == "supports"
    assert set(proj["observation_types"]) == {
        "registry_mutation_record",
        "tool_event_record",
    }
    assert assessment["predicates"]["exclusivity_declared"] is True
    assert assessment["predicates"]["exclusivity_independently_verified"] is False
    assert strong_invariant_verdict(clean["claim"], composed_obs)["epistemic_status"] == (
        "supported"
    )
    assert swarm_witness_verdict(clean["claim"], composed_obs)["epistemic_status"] == (
        "supported"
    )
    assert (
        strong_invariant_verdict(clean["claim"], clean["observations"])["epistemic_status"]
        == "unresolved"
    )

    # Unresolved path: mismatched token → no decisive projection.
    obs = copy.deepcopy(clean["observations"])
    for row in obs:
        if "tool_event_record" in row.get("observation_types", []):
            row["entity"]["attrs"]["receipt"]["receipt_token"] = "deadbeef_not_matching"
    assessment, projected = composed_observations(clean["claim"], obs)
    assert assessment["verdict"] == "unresolved"
    assert projected == []
    assert (
        strong_invariant_verdict(clean["claim"], obs + projected)["epistemic_status"]
        == "unresolved"
    )

    # Refutation path: fabricated receipt under complete capture.
    fab = next(
        p
        for p in packets
        if p["claim"]["scenario"] == "fabricated"
        and p["claim"]["family"] == "fabricated_execution"
    )
    assessment, projected, composed_obs = _composed(fab)
    assert assessment["verdict"] == "refuted"
    assert projected and projected[0]["literal_polarity"] == "refutes"
    assert set(projected[0]["observation_types"]) == {
        "successful_execution_claim",
        "capture_declaration",
        "registry_mutation_population",
    }
    assert strong_invariant_verdict(fab["claim"], composed_obs)["epistemic_status"] == (
        "refuted"
    )
    assert swarm_witness_verdict(fab["claim"], composed_obs)["epistemic_status"] == (
        "refuted"
    )

    # Premise limitation: false-exclusivity decisive support preserved.
    false_ex = next(
        p
        for p in packets
        if p["claim"]["scenario"] == "false_exclusivity"
        and p["claim"]["family"] == "event_attribution"
        and p["native_arms"]["eg_evidence_derived_adapter"]["verdict"] == "supported"
    )
    assessment, projected, composed_obs = _composed(false_ex)
    assert assessment["verdict"] == "supported"
    assert assessment["predicates"]["exclusivity_declared"] is True
    assert assessment["predicates"]["exclusivity_independently_verified"] is False
    assert strong_invariant_verdict(false_ex["claim"], composed_obs)["epistemic_status"] == (
        "supported"
    )

    # Independence: raw fingerprints/verdicts unchanged; composed input stable from public evidence.
    export = json.loads(
        (ROOT / "evidence" / "external_calibration_v1" / "eg_native_relations_seed0.json").read_text(
            encoding="utf-8"
        )
    )
    mutated = mutate_native_fields_for_independence_check(export)
    tmp = Path(tempfile.mkdtemp()) / "mutated_export.json"
    tmp.write_text(json.dumps(mutated), encoding="utf-8")
    alt_packets = build_packets(tmp)

    def _attr_key(packet):
        return (packet["claim"]["scenario"], packet["claim"]["mutation_id"])

    def _composed_fp(packet):
        assessment, projected = composed_observations(
            packet["claim"], packet["observations"]
        )
        # Complete composed assessor input fingerprint.
        return assessor_input_fingerprint(list(packet["observations"]) + projected), assessment[
            "verdict"
        ]

    base_raw = {
        _attr_key(p): assessor_input_fingerprint(p["observations"])
        for p in packets
        if p["claim"]["family"] == "event_attribution"
    }
    alt_raw = {
        _attr_key(p): assessor_input_fingerprint(p["observations"])
        for p in alt_packets
        if p["claim"]["family"] == "event_attribution"
    }
    assert base_raw == alt_raw

    base_comp = {
        _attr_key(p): _composed_fp(p)
        for p in packets
        if p["claim"]["family"] == "event_attribution"
    }
    alt_comp = {
        _attr_key(p): _composed_fp(p)
        for p in alt_packets
        if p["claim"]["family"] == "event_attribution"
    }
    assert base_comp == alt_comp

    # project_checks must ignore non-assessment inputs (no second algorithm).
    empty = project_checks(clean["claim"], clean["observations"], {"verdict": "unresolved"})
    assert empty == []


def test_composed_classifiers_do_not_promote_spoofed_or_wrong_target_evidence():
    """Spoofed, unauthenticated, and cross-event premises stay unresolved.

    Raw classifiers already abstain. The composed arms must abstain too, and
    must not relabel another event's evidence or upgrade authenticity.
    """
    import copy

    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from eg_adapter_projector import composed_observations, project_checks
    from r2_event_packets import build_packets
    from swarm_witness.incident_audit import swarm_witness_verdict
    from swarm_witness.strong_invariant import strong_invariant_verdict

    packets = build_packets()

    def _natural_key(packet):
        for obs in packet["observations"]:
            if "registry_mutation_record" in (obs.get("observation_types") or []):
                return (obs.get("entity") or {}).get("natural_key")
        return None

    def _packet(natural_key):
        return next(
            packet
            for packet in packets
            if packet["claim"]["scenario"] == "clean"
            and packet["claim"]["family"] == "event_attribution"
            and _natural_key(packet) == natural_key
        )

    def _probe(claim, observations):
        assessment, projected = composed_observations(claim, observations)
        composed = list(observations) + projected
        return {
            "assessment": assessment["verdict"],
            "reason": assessment["reason"],
            "strong": strong_invariant_verdict(claim, composed)["epistemic_status"],
            "swarm": swarm_witness_verdict(claim, composed)["epistemic_status"],
            "raw_strong": strong_invariant_verdict(claim, observations)["epistemic_status"],
            "raw_swarm": swarm_witness_verdict(claim, observations)["epistemic_status"],
            "derived_authenticity": [obs.get("authenticity") for obs in projected],
            "projected": projected,
        }

    left = _packet("event-000006")
    right = _packet("event-000007")
    claim = left["claim"]
    own = _probe(claim, left["observations"])
    assert own["assessment"] == own["strong"] == own["swarm"] == "supported"
    assert own["raw_strong"] == own["raw_swarm"] == "unresolved"
    derived = own["projected"][0]
    quals = derived["premise_qualifications"]
    covered = set()
    for qual in quals:
        covered.update(qual["observation_types"])
        assert qual["authenticity"] == derived["authenticity"]
        assert qual["access_level"] == derived["access_level"]
    assert set(claim["required_observation_types"]).issubset(covered)
    assert all("declared_assumptions" not in qual["observation_types"] for qual in quals)
    assert derived["authenticity"] == "authentic_public_text"
    entity_ids = {qual["entity_id"] for qual in quals}
    assert claim["mutation_id"] in entity_ids
    assert claim["proposed_event_id"] in entity_ids
    # event-000007 evidence supports its own claim, so the cross pair is a real promotion.
    assert _probe(right["claim"], right["observations"])["assessment"] == "supported"

    def _mark_mutation(observations, authenticity):
        copied = copy.deepcopy(observations)
        marked = False
        for row in copied:
            if "registry_mutation_record" in (row.get("observation_types") or []):
                row["authenticity"] = authenticity
                marked = True
        assert marked
        return copied

    def _unchanged(observations):
        return [
            (
                obs.get("id"),
                obs.get("authenticity"),
                tuple(obs.get("applies_to") or []),
                (obs.get("entity") or {}).get("entity_id"),
            )
            for obs in observations
        ]

    for authenticity in ("spoofed_tool_line", "unauthenticated_tool_line"):
        marked = _mark_mutation(left["observations"], authenticity)
        result = _probe(claim, marked)
        assert result["raw_strong"] == result["raw_swarm"] == "unresolved"
        assert result["assessment"] == "unresolved"
        assert result["reason"] == "required_premise_not_admitted"
        assert result["strong"] == result["swarm"] == "unresolved"
        assert "authentic_public_text" not in result["derived_authenticity"]
        assert result["assessment"] != "supported"
        forced = project_checks(
            claim,
            marked,
            {"verdict": "supported", "reason": "laundered", "predicates": {}},
        )
        assert forced == []

    before = _unchanged(right["observations"])
    crossed = _probe(claim, right["observations"])
    assert _unchanged(right["observations"]) == before
    assert crossed["raw_strong"] == crossed["raw_swarm"] == "unresolved"
    assert crossed["assessment"] == "unresolved"
    assert crossed["reason"] == "premise_entity_not_bound_to_claim"
    assert crossed["strong"] == crossed["swarm"] == "unresolved"
    assert crossed["derived_authenticity"] == []
    assert all(claim["id"] not in (obs.get("applies_to") or []) for obs in crossed["projected"])
    forced = project_checks(
        claim,
        right["observations"],
        {"verdict": "supported", "reason": "laundered", "predicates": {}},
    )
    assert forced == []


def test_external_calibration_runner_matrix():
    out = ROOT / "evidence" / "external_calibration_v1"
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    subprocess.run(
        [sys.executable, str(ROOT / "experiments" / "external_calibration" / "run.py")],
        cwd=ROOT,
        check=True,
        env=env,
    )
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["retrospective_calibration"] is True
    eg = summary["profiles"]["evidencegraph_attribution"]
    assert eg["attr_claim_count"] == 4
    # Warrant agreement and native-safer agreement stay separate.
    assert eg["safer_native_matches_warranted"] == 3
    assert eg["strong_matches_native_safer"] == eg["attr_claim_count"]
    assert eg["swarm_matches_native_safer"] == eg["attr_claim_count"]
    assert eg["strong_matches_warranted"] == 3
    assert eg["swarm_matches_warranted"] == 3
    assert summary["methods"]["soundgate_policy_barrier"]["unsupported_support"] == 0
    barrier = summary["profiles"]["soundgate_barrier_joint"]
    assert barrier["claim_count"] == 2
    assert barrier["barrier_native_matches_warranted"] == 2
    assert "bmo_l1" in summary["corpora"]
    assert summary["corpora"]["bmo_l1"]["claims"] == 7
    lw = summary["profiles"]["lesswrong_reproduction_scope"]
    assert lw["external_native_method_scored"] is False
    assert lw["strong_matches_warranted"] == lw["claim_count"]
    assert lw["swarm_matches_warranted"] == lw["claim_count"]
    settle = [
        row
        for row in json.loads((out / "matrix.json").read_text())["rows"]
        if row["claim_id"] == "BMO-L1-NOT-EXECUTION-SETTLEMENT"
        and row["method"] == "strong_invariant"
    ]
    assert settle and settle[0]["warranted"] == "refuted"
    assert settle[0]["predicted"] == "refuted"
    env_row = [
        row
        for row in json.loads((out / "matrix.json").read_text())["rows"]
        if row["claim_id"] == "LW-K-env-scope" and row["method"] == "strong_invariant"
    ]
    assert env_row and env_row[0]["warranted"] == "refuted"
    assert env_row[0]["predicted"] == "refuted"
    repeat = summary["seed_repeatability"]
    assert repeat["seeds"] == [1, 2]
    assert repeat["attr_claim_count"] == 8
    assert repeat["strong_matches_native_safer"] == repeat["attr_claim_count"]
    assert repeat["strong_matches_warranted"] == 6
    assert repeat["repeats_seed0"] is True
    assert repeat["transfer_claim"] is False
    # Identical encoded inputs cannot earn transfer regardless of scores.
    assert summary["transfer_claim"] is False
    assert "evidencegraph_r2_seed_repeatability" in summary["corpora"]
    assert "evidencegraph_r2_event" in summary["corpora"]
    assert summary["corpora"]["evidencegraph_r2_event"]["transfer_claim"] is False
    capability = summary["evidencegraph_event_conformance"]
    assert capability["attr_claim_count"] > 0
    assert "eg_evidence_derived_adapter" in capability["methods"]
    boundaries = capability["boundaries_adapter_vs_safer"]
    assert boundaries["missing_clock_bound"]["adapter_matches_safer"] == boundaries[
        "missing_clock_bound"
    ]["claims"]
    assert boundaries["missing_tokens"]["adapter_matches_safer"] == boundaries["missing_tokens"][
        "claims"
    ]
    attrc = capability["attribution_conformance"]
    assert attrc["adapter_matches_safer_all_attr"] == attrc["attr_claim_count"] == 120
    assert attrc["correct_decisive"] == 48
    assert attrc["unsupported_support"] == 10
    assert attrc["missed_decisive_strong"] == 48
    assert attrc["missed_decisive_swarm"] == 48
    assert attrc["factually_wrong_supported_attributions"] == 1
    fab = capability["fabricated_execution"]
    assert fab["native_executed_comparisons"] == 8
    assert fab["additional_controls"] == 2
    assert fab["total_cells"] == 10
    assert fab["adapter_matches_on_native_executed_only"] == 8
    assert capability["warrant_qualification"]["primary_result"] == (
        "adapter_vs_native_safer_conformance"
    )
    capability_md = (out / "EVENT_CAPABILITY.md").read_text(encoding="utf-8")
    assert "8 native execution comparisons" in capability_md
    assert "2 additional controls" in capability_md
    assert "not fully independent of evaluated methods" in capability_md
    integ = capability["classifier_integration"]
    assert integ["transfer_claim"] is False
    assert integ["packet_denominator"] == 130
    assert integ["strong_on_adapter_matches_adapter"] == integ["integration_cells"] == 130
    assert integ["swarm_on_adapter_matches_adapter"] == integ["integration_cells"]
    assert integ["strong_on_adapter_matches_safer_attr"] == integ["safer_attr_cells"] == 120
    assert integ["strong_on_adapter_matches_safer_native_exec"] == integ["native_exec_cells"] == 8
    assert integ["strong_on_adapter_matches_safer_control"] == integ["control_exec_cells"] == 2
    assert integ["strong_on_adapter_matches_safer_exec_mapping"] == 10
    assert integ["raw_strong_decisive"] == 0
    assert integ["raw_swarm_decisive"] == 0
    assert integ["raw_strong_packets"] == 130
    assert integ["raw_swarm_packets"] == 130
    assert integ["composed_strong_decisive"] > 0
    assert "Raw strong:" in capability_md
    assert "raw Swarm Witness:" in capability_md
    assert "native execution comparisons" in capability_md
    assert "additional controls" in capability_md
    assert "Classifier integration" in capability_md
    assert "preserve the adapter" in capability_md
    assert (out / "EVENT_CAPABILITY.md").exists()
    assert (ROOT / "report" / "external_calibration_v1" / "EVENT_CAPABILITY.md").exists()
    assert (out / "PROFILE_LABELS.md").exists()
    assert (ROOT / "report" / "external_calibration_v1" / "PROFILE_LABELS.md").exists()
    labels = (out / "PROFILE_LABELS.md").read_text(encoding="utf-8")
    assert "no external LW native method scored" in labels
    assert "matches_evidencegraph_safer_native_verdicts_on_r2_seed0" in labels
    assert "repeats_evidencegraph_attribution_across_r2_seeds" in labels
    assert "transfers_evidencegraph_attribution_across_r2_seeds" not in labels
