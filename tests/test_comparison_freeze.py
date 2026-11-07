"""Frozen comparison: one LessWrong record, unavailable logs are not gates."""

from __future__ import annotations

import ast
import copy
import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.incident_audit import prepare_observations  # noqa: E402
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402


def _run():
    spec = importlib.util.spec_from_file_location(
        "incident_compare", ROOT / "experiments" / "incident_audit" / "compare.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(ROOT)


def test_comparison_completes_and_does_not_certify_the_incident():
    result = _run()
    summary = result["summary"]
    assert summary["comparison_completed"] is True
    assert summary["superiority_claim"] is False
    assert summary["real_world_authenticity_certified"] is False
    assert summary["unavailable_blocks_comparison"] is False
    assert summary["unavailable_are_upgrade_gates"] is False
    assert summary["detection_or_prevention_claimed"] is False
    assert summary["one_public_record"] is True
    assert 10 <= summary["public_claim_count"] <= 12
    assert summary["public_cell_count"] == summary["public_claim_count"] * 2
    assert summary["public_strong_unsupported_support"] < summary[
        "public_naive_unsupported_support"
    ]
    assert summary["public_always_unresolved_correct_decisive"] == 0
    assert summary["public_strong_decisive_opportunities"] > 0
    assert summary["public_strong_correct_decisive"] > 0
    assert summary["lineage_incident_supported"] == 0
    assert summary["lineage_reproduction_independent_observations"] == 1
    assert summary["controlled_history_count"] != summary["public_claim_count"]
    assert summary["controlled_cell_count"] != summary["public_cell_count"]
    public = summary["layers"]["public"]
    controlled = summary["layers"]["controlled"]
    assert public["naive"]["correct_attribution_coverage"] is None
    assert public["naive"]["unique_origin_cases"] == 0
    assert controlled["always_unresolved"]["unique_origin_cases"] > 0
    assert controlled["always_unresolved"]["correct_attribution_coverage"] == 0
    assert controlled["naive"]["false_proposition_support"] > controlled[
        "strong_invariant"
    ]["false_proposition_support"]
    assert controlled["strong_invariant"]["unsupported_attribution"] == 0
    assert controlled["swarm_witness"]["unsupported_attribution"] == 0
    assert controlled["naive"]["unsupported_attribution"] > 0
    assert public["naive"]["correct_decisive_coverage"] == 0
    assert public["strong_invariant"]["correct_decisive_coverage"] == 1
    assert public["always_unresolved"]["correct_decisive_coverage"] == 0
    assert (
        public["strong_invariant"]["unsupported_support"]
        == public["swarm_witness"]["unsupported_support"]
    )
    assert controlled["strong_invariant"]["record_requests"] == 0
    lineage = summary["layers"]["lineage"]
    assert lineage["reproduction_conclusion"] == "supported"
    assert set(lineage["reproduction_unavailable"]) == {
        "src-transcript-dump",
        "src-hf-platform-logs",
    }
    assert "ev-lw-appendix" in lineage["reproduction_duplicated_reports"]


def test_held_blocks_upgrade_prevents_support_and_unavailable_cannot_be_a_gate():
    comp = ROOT / "experiments" / "incident_audit" / "comparison"
    claims = yaml.safe_load((comp / "claims_v1.yaml").read_text())["claims"]
    packets = prepare_observations(
        yaml.safe_load((comp / "packets_v1.yaml").read_text())["observations"]
    )
    claim = next(item for item in claims if item["id"] == "K-gate")
    blocked = strong_invariant_verdict(claim, packets)
    assert blocked["epistemic_status"] == "unresolved"
    opened = copy.deepcopy(packets)
    slot = next(obs for obs in opened if obs["id"] == "HELD-SLOT")
    slot["blocks_upgrade"] = False
    assert strong_invariant_verdict(claim, opened)["epistemic_status"] == "supported"
    illegal = copy.deepcopy(packets)
    missing = next(obs for obs in illegal if obs["id"] == "UNAVAIL-transcripts")
    missing["blocks_upgrade"] = True
    try:
        strong_invariant_verdict(claim, illegal)
    except ValueError as exc:
        assert "cannot be an upgrade gate" in str(exc)
    else:
        raise AssertionError("unavailable blocks_upgrade was accepted")


def test_qualifiers_do_not_read_warrants():
    for name in ("strong_invariant.py", "incident_audit.py", "comparison_score.py"):
        source = (ROOT / "src" / "swarm_witness" / name).read_text(encoding="utf-8")
        assert "warrants_v1.yaml" not in source
        assert "truth_v1" not in source
        tree = ast.parse(source)
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "open" not in called
