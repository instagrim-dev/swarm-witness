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
    assert (out / "EVENT_CAPABILITY.md").exists()
    assert (ROOT / "report" / "external_calibration_v1" / "EVENT_CAPABILITY.md").exists()
    assert (out / "PROFILE_LABELS.md").exists()
    assert (ROOT / "report" / "external_calibration_v1" / "PROFILE_LABELS.md").exists()
    labels = (out / "PROFILE_LABELS.md").read_text(encoding="utf-8")
    assert "no external LW native method scored" in labels
    assert "matches_evidencegraph_safer_native_verdicts_on_r2_seed0" in labels
    assert "repeats_evidencegraph_attribution_across_r2_seeds" in labels
    assert "transfers_evidencegraph_attribution_across_r2_seeds" not in labels
