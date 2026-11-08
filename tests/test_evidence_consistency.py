"""Evidence-consistency: findings must be supported by Claim/Run observations."""

from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stderr
from pathlib import Path

import pytest
import yaml

from swarm_witness.classical_gate import ClassicalGate
from swarm_witness.evidence_index import (
    check_consistency,
    expected_index_from_findings,
    generate_and_write_index,
    load_evidence_tree,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_check_evidence():
    spec = importlib.util.spec_from_file_location(
        "check_evidence", ROOT / "scripts" / "check_evidence.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def tmp_tree(tmp_path: Path) -> Path:
    """Minimal valid R1-shaped tree (reproduced + supporting observations)."""
    claims = tmp_path / "claims"
    claims.mkdir()
    (claims / "r1_restart.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "r1",
                "source_ref": "apart://test",
                "source_version": "656840348dcf9660f8db7add9f3ca9f794a55926",
                "original_proposition": "ack survives restart",
                "operational_interpretation": "barrier prohibited_effects==0",
                "property": "ack survives",
                "scope": "test scope",
                "quantifier": "each history",
                "success_criterion": "prohibited_effects == 0",
                "assumptions": ["intact records"],
            }
        ),
        encoding="utf-8",
    )
    pins = tmp_path / "artifacts"
    pins.mkdir()
    (pins / "pins.yaml").write_text(
        yaml.safe_dump(
            {
                "r1": {
                    "source_revision": "6568403",
                    "git_rev": "656840348dcf9660f8db7add9f3ca9f794a55926",
                }
            }
        ),
        encoding="utf-8",
    )
    runs = tmp_path / "evidence" / "r1" / "runs"
    findings = tmp_path / "evidence" / "r1" / "findings"
    runs.mkdir(parents=True)
    findings.mkdir(parents=True)
    (runs / "r1-run-barrier-sweep.json").write_text(
        json.dumps(
            {
                "id": "r1-run-barrier-sweep",
                "claim_id": "r1",
                "protocol_id": "soundgate-recovery-barrier",
                "case_id": "policy-barrier-sweep",
                "source_pin": "6568403",
                "execution_status": "completed",
                "observations": {
                    "prohibited_effects_barrier": 0,
                    "histories_per_policy": 153,
                    "all_checks_pass": True,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (findings / "r1-f-primary.json").write_text(
        json.dumps(
            {
                "id": "r1-f-primary",
                "claim_id": "r1",
                "run_ids": ["r1-run-barrier-sweep"],
                "proposition": "Barrier prohibited_effects==0",
                "scope": "test scope",
                "label": "reproduced",
                "basis": "computed",
                "supporting_observation_refs": [
                    "r1-run-barrier-sweep.observations.prohibited_effects_barrier",
                    "r1-run-barrier-sweep.observations.histories_per_policy",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "evidence" / "r1" / "result.yaml").write_text(
        yaml.safe_dump(
            {
                "claim_id": "r1",
                "label": "reproduced",
                "metrics": {
                    "prohibited_effects_barrier": 0,
                    "histories_per_policy": 153,
                },
                "evidence_path": "evidence/r1/summary.json",
                "finding_path": "evidence/r1/findings/r1-f-primary.json",
                "authoritative": "finding",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "evidence" / "r1" / "summary.json").write_text(
        json.dumps(
            {
                "prohibited_effects_barrier": 0,
                "histories_per_policy": 153,
                "authoritative_finding": "evidence/r1/findings/r1-f-primary.json",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    generate_and_write_index(tmp_path)
    return tmp_path


def test_reproduced_with_unresolved_only_summary_fails(tmp_tree: Path):
    """finding label=reproduced, run observations empty / status unresolved-only → FAIL"""
    run_path = tmp_tree / "evidence" / "r1" / "runs" / "r1-run-barrier-sweep.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["observations"] = {
        "notes": "no sweep executed",
        "status": "unresolved",
        "prohibited_effects_barrier": None,
    }
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (tmp_tree / "evidence" / "r1" / "summary.json").write_text(
        json.dumps({"status": "unresolved", "unresolved": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    finding_path = tmp_tree / "evidence" / "r1" / "findings" / "r1-f-primary.json"
    finding = json.loads(finding_path.read_text(encoding="utf-8"))
    finding["supporting_observation_refs"] = [
        "r1-run-barrier-sweep.observations.notes",
        "r1-run-barrier-sweep.observations.status",
    ]
    finding_path.write_text(json.dumps(finding, indent=2) + "\n", encoding="utf-8")

    errors = check_consistency(tmp_tree)
    assert errors, "expected consistency failure for reproduced + unresolved-only"
    joined = "\n".join(errors).lower()
    assert "unresolved" in joined or "reproduced" in joined


def test_mismatched_observation_ref_fails(tmp_tree: Path):
    """A supporting ref that names a real run but a missing field is an explicit failure."""
    finding_path = tmp_tree / "evidence" / "r1" / "findings" / "r1-f-primary.json"
    finding = json.loads(finding_path.read_text(encoding="utf-8"))
    finding["supporting_observation_refs"] = [
        "r1-run-barrier-sweep.observations.not_a_recorded_field",
    ]
    finding_path.write_text(json.dumps(finding, indent=2) + "\n", encoding="utf-8")

    errors = check_consistency(tmp_tree)
    assert errors
    assert any("not_a_recorded_field" in err or "unresolved" in err for err in errors)


def test_unregistered_claim_id_fails(tmp_tree: Path):
    """finding.claim_id not in claims/ → FAIL"""
    finding_path = tmp_tree / "evidence" / "r1" / "findings" / "r1-f-primary.json"
    finding = json.loads(finding_path.read_text(encoding="utf-8"))
    finding["claim_id"] = "not-a-registered-claim"
    finding_path.write_text(json.dumps(finding, indent=2) + "\n", encoding="utf-8")

    errors = check_consistency(tmp_tree)
    assert errors
    assert any("claim" in e.lower() for e in errors)


def test_metrics_disagree_with_run_observations_fails(tmp_tree: Path):
    """finding/result cites prohibited_effects=0 but run observations say 143 → FAIL"""
    run_path = tmp_tree / "evidence" / "r1" / "runs" / "r1-run-barrier-sweep.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["observations"]["prohibited_effects_barrier"] = 143
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")

    errors = check_consistency(tmp_tree)
    assert errors
    joined = "\n".join(errors).lower()
    assert "metric" in joined or "prohibited_effects" in joined or "disagree" in joined


def test_index_generated_matches_findings(tmp_tree: Path):
    """hand-edited index disagreeing with findings → FAIL; generator overwrites/derives"""
    index_path = tmp_tree / "evidence" / "index.yaml"
    bogus = {
        "results": [
            {"claim_id": "r1", "label": "classical_baseline_matches", "finding_id": "r1-f-primary"}
        ]
    }
    index_path.write_text(yaml.safe_dump(bogus), encoding="utf-8")

    errors = check_consistency(tmp_tree)
    assert any("index" in e.lower() for e in errors)

    generate_and_write_index(tmp_tree)
    tree = load_evidence_tree(tmp_tree)
    expected = expected_index_from_findings(tree.findings)
    loaded = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    assert loaded == expected
    assert check_consistency(tmp_tree) == []


def test_always_deny_useful_op_not_presentable_as_match():
    """Integration with classical gate useful-op control (decisive acceptance)."""
    g = ClassicalGate.from_grants({"edit-1": {"state": "active_grant", "version": 2}})
    assert g.decide(action_id="edit-1", request="execute", grant_version=2) == "allow"

    def always_deny(*_args, **_kwargs):
        return "deny"

    g.decide = always_deny  # type: ignore[method-assign]
    assert g.decide(action_id="edit-1", request="execute", grant_version=2) == "deny"
    # Always-deny cannot satisfy the useful-operation allow assertion.
    with pytest.raises(AssertionError):
        assert g.decide(action_id="edit-1", request="execute", grant_version=2) == "allow"


def test_reviewer_probe_three_unregistered_reproduced_unresolved_fails(tmp_path: Path):
    """Three reproduced findings with unregistered claim ids + unresolved summaries → exit 1."""
    claims = tmp_path / "claims"
    claims.mkdir()
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "pins.yaml").write_text("{}\n", encoding="utf-8")
    evidence = tmp_path / "evidence"
    for i, claim_id in enumerate(("bogus-a", "bogus-b", "bogus-c"), start=1):
        slot = evidence / f"probe{i}"
        (slot / "runs").mkdir(parents=True)
        (slot / "findings").mkdir(parents=True)
        run_id = f"probe-run-{i}"
        (slot / "runs" / f"{run_id}.json").write_text(
            json.dumps(
                {
                    "id": run_id,
                    "claim_id": claim_id,
                    "protocol_id": "probe",
                    "case_id": f"case-{i}",
                    "source_pin": "deadbeef",
                    "execution_status": "completed",
                    "observations": {"status": "unresolved", "notes": "no support"},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (slot / "findings" / f"probe-f-{i}.json").write_text(
            json.dumps(
                {
                    "id": f"probe-f-{i}",
                    "claim_id": claim_id,
                    "run_ids": [run_id],
                    "proposition": "unsupported reproduced label",
                    "scope": "probe",
                    "label": "reproduced",
                    "basis": "authored",
                    "supporting_observation_refs": [f"{run_id}.observations.status"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (slot / "summary.json").write_text(
            json.dumps({"status": "unresolved"}, indent=2) + "\n",
            encoding="utf-8",
        )

    ce = _load_check_evidence()
    err = io.StringIO()
    with redirect_stderr(err):
        code = ce.main(["--root", str(tmp_path)])
    assert code == 1
    out = err.getvalue()
    assert "FAIL" in out


def test_real_tree_passes_check_evidence():
    ce = _load_check_evidence()
    err = io.StringIO()
    with redirect_stderr(err):
        code = ce.main([])
    assert code == 0, err.getvalue()
    assert check_consistency(ROOT) == []
