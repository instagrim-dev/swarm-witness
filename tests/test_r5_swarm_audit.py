"""R5 multi-agent swarm audit tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.schema import validate_claim, validate_finding, validate_run  # noqa: E402
from swarm_witness.swarm_audit import (  # noqa: E402
    evaluate_swarm_method_success,
    run_independent_probes,
    run_swarm_protocol_cases,
)


def test_swarm_involves_three_agents_and_three_classes():
    cases = run_swarm_protocol_cases()
    score = evaluate_swarm_method_success(cases)
    assert score["passed"] is True, score["errors"]
    assert score["agent_count"] == 3
    assert score["agents"] == ["A", "B", "C"]
    assert score["model"] == "sequential_shared_grant_multi_principal"
    assert score["three_way_classes_exercised"] is True
    assert score["case_count"] >= 8
    assert score["failed_enforcement_count"] >= 2
    assert score["missing_evidence_count"] >= 2


def test_broken_allow_does_not_commit_effect_and_receipts_bind():
    cases = {c["case_id"]: c for c in run_swarm_protocol_cases()}
    broken = cases["swarm_contention_broken_second_allow"]["result"]
    assert broken["decision"] == "allow"
    assert broken["effect_committed"] is False
    misuse = cases["swarm_cross_agent_receipt_deny_supported"]["result"]
    assert misuse["presented_receipt"]["receipt_id"] == "receipt-a-xfer"
    broken_rx = cases["swarm_cross_agent_receipt_broken_allow"]["result"]
    assert broken_rx["presented_receipt"]["receipt_id"] == "receipt-a-prior"
    assert broken_rx["effect_committed"] is False


def test_independent_probe_suite_passes_and_detects_tamper():
    score = run_independent_probes()
    assert score["passed"] is True, score["errors"]
    # Tamper: flip expected class so the suite must fail (discriminating check).
    import json
    from pathlib import Path

    probes = json.loads(
        (ROOT / "experiments" / "swarm_r5" / "independent_probes.json").read_text(
            encoding="utf-8"
        )
    )
    probes[0]["expected_conclusion_class"] = "supported"
    bad = run_independent_probes(probes)
    assert bad["passed"] is False


def test_runner_writes_valid_evidence(tmp_path: Path):
    spec = importlib.util.spec_from_file_location(
        "r5_run", ROOT / "experiments" / "swarm_r5" / "run.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["r5_run"] = mod
    spec.loader.exec_module(mod)
    cases = mod.run_swarm_protocol_cases()
    score = mod.evaluate_swarm_method_success(cases)
    out = mod.write_evidence(tmp_path, cases, score)
    assert out["finding"]["label"] == "reproduced"
    assert out["finding"]["conclusion_class"] == "supported"
    validate_finding(
        {k: v for k, v in out["finding"].items() if k != "conclusion_class"}
    )
    for path in (tmp_path / "runs").glob("*.json"):
        validate_run(json.loads(path.read_text(encoding="utf-8")))
    claim = validate_claim(
        __import__("yaml").safe_load(
            (ROOT / "claims" / "r5_swarm_audit.yaml").read_text(encoding="utf-8")
        )
    )
    assert claim.id == "r5"
