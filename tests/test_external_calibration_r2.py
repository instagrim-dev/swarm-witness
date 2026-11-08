"""External calibration: EvidenceGraph R2 + SoundGate R1 packets and matrix."""

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


def test_r1_packets_separate_restriction_and_availability():
    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from r1_packets import build_packets

    packets = build_packets()
    by_id = {p["claim"]["id"]: p for p in packets}
    assert by_id["SG-R1-RESTRICT-strict"]["warranted_conclusion"]["status"] == "supported"
    assert by_id["SG-R1-AVAIL-strict"]["warranted_conclusion"]["status"] == "refuted"
    assert by_id["SG-R1-RESTRICT-barrier"]["warranted_conclusion"]["status"] == "supported"
    assert by_id["SG-R1-AVAIL-barrier"]["warranted_conclusion"]["status"] == "supported"
    # Native barrier policy matches both profiles; strict does not.
    assert (
        by_id["SG-R1-AVAIL-strict"]["native_arms"]["soundgate_policy_strict"]["verdict"]
        == "refuted"
    )
    assert (
        by_id["SG-R1-AVAIL-barrier"]["native_arms"]["soundgate_policy_barrier"]["verdict"]
        == "supported"
    )


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
    assert summary["transfer_claim"] is False
    eg = summary["profiles"]["evidencegraph_attribution"]
    assert eg["attr_claim_count"] == 4
    assert eg["strong_matches_warranted"] == eg["attr_claim_count"]
    assert eg["swarm_matches_warranted"] == eg["attr_claim_count"]
    assert summary["methods"]["strong_invariant"]["unsupported_support"] == 0
    assert summary["methods"]["naive"]["unsupported_support"] >= 1
    assert "soundgate_r1" in summary["corpora"]
    assert summary["corpora"]["soundgate_r1"]["claims"] == 5
    assert "bmo_l1" in summary["corpora"]
    assert summary["corpora"]["bmo_l1"]["claims"] == 7
    assert "lesswrong_reproduction" in summary["corpora"]
    assert summary["corpora"]["lesswrong_reproduction"]["claims"] == 5
    lw = summary["profiles"]["lesswrong_reproduction_scope"]
    assert lw["strong_matches_warranted"] == lw["claim_count"]
    assert lw["swarm_matches_warranted"] == lw["claim_count"]
    settle = [
        row
        for row in json.loads((out / "matrix.json").read_text())["rows"]
        if row["claim_id"] == "BMO-L1-NOT-EXECUTION-SETTLEMENT"
        and row["method"] == "strong_invariant"
    ]
    assert settle and settle[0]["warranted"] == "unresolved"
    assert settle[0]["predicted"] == "unresolved"
    certify = [
        row
        for row in json.loads((out / "matrix.json").read_text())["rows"]
        if row["claim_id"] == "LW-K-certify" and row["method"] == "strong_invariant"
    ]
    assert certify and certify[0]["warranted"] == "unresolved"
    assert certify[0]["predicted"] == "unresolved"


def test_lw_packets_preserve_scope_discipline():
    sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))
    from lw_packets import build_packets

    packets = build_packets()
    by_id = {p["claim"]["id"]: p for p in packets}
    assert by_id["LW-K-release"]["warranted_conclusion"]["status"] == "supported"
    assert by_id["LW-K-certify"]["warranted_conclusion"]["status"] == "unresolved"
    assert by_id["LW-K-census"]["warranted_conclusion"]["status"] == "supported"
    assert by_id["LW-K-gate"]["warranted_conclusion"]["status"] == "unresolved"
    assert by_id["LW-K-env-scope"]["warranted_conclusion"]["status"] == "unresolved"
    assert (
        by_id["LW-K-certify"]["native_arms"]["reconstructed_narrative_overread"][
            "reconstruction"
        ]
        is True
    )
