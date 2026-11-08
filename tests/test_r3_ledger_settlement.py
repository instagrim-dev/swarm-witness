"""Settlement continuation: contract, staged verdict, and retained-study isolation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SETTLEMENT = ROOT / "experiments" / "r3" / "ledger_settlement_v1"
CLAIM = ROOT / "experiments" / "r3" / "ledger_claim_v1"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SETTLEMENT))

from swarm_witness.classical_ledger_gate import ClassicalLedgerGate  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


protocol = _load("settlement_protocol_under_test", SETTLEMENT / "protocol.py")
compare = _load("settlement_compare_under_test", SETTLEMENT / "compare.py")
adapter_mod = _load("settlement_adapter_under_test", SETTLEMENT / "classical_adapter.py")


def test_claim_without_settlement_leaves_the_effect_unresolved(tmp_path: Path) -> None:
    gate = ClassicalLedgerGate(tmp_path / "ledger.sqlite")
    gate.open_case(
        {
            "task_id": "task-alpha",
            "grant_id": "grant-alpha",
            "owner_revision": 1,
            "retry_epoch": "epoch-1",
            "initial_spent": False,
        }
    )
    claim = gate.claim_first_edit(
        call_id="call-s01",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert claim["disposition"] == "committed"
    state = gate.inspect()
    assert state["settlement"] is None
    assert protocol.effect_verdict({"settlement": None}) == "unresolved"
    gate.close()


def test_applied_and_no_effect_satisfy_one_contract_and_differ() -> None:
    applied = {
        "disposition": "applied",
        "call_id": "call-s01",
        "tool_bound": True,
        "mutation_bound": True,
        "artifact_bound": True,
        "source_receipt_bound": False,
    }
    no_effect = {
        "disposition": "not_entered",
        "call_id": "call-s02",
        "tool_bound": True,
        "mutation_bound": False,
        "artifact_bound": False,
        "source_receipt_bound": True,
    }
    assert protocol.contract_conformant(applied)
    assert protocol.contract_conformant(no_effect)
    assert protocol.effect_verdict({"settlement": applied}) == "supported"
    assert protocol.effect_verdict({"settlement": no_effect}) == "refuted"
    assert applied["disposition"] != no_effect["disposition"]


def test_classical_continuations_resolve_at_the_settlement_step(tmp_path: Path) -> None:
    bundle = protocol.load_cases(SETTLEMENT / "cases.yaml")
    rows = []
    for case in bundle["cases"]:
        adapter = adapter_mod.ClassicalAdapter(tmp_path / case.case_id)
        adapter.open_case(case)
        for action in case.actions:
            rows.append(adapter.apply(action))
        adapter.close()
    stages = compare.evidence_stages(bundle["cases"], rows)
    assert stages["S01"]["verdicts"][1]["effect_verdict"] == "unresolved"
    assert stages["S01"]["resolving_observation"]["op"] == "settle_applied"
    assert stages["S01"]["resolving_observation"]["to"] == "supported"
    assert stages["S02"]["verdicts"][1]["effect_verdict"] == "unresolved"
    assert stages["S02"]["resolving_observation"]["op"] == "settle_no_effect"
    assert stages["S02"]["resolving_observation"]["to"] == "refuted"
    for case in bundle["cases"]:
        assert compare.evaluate_arm(case, [r for r in rows if r["case_id"] == case.case_id])["passed"]


def test_retained_claim_protocol_is_unchanged() -> None:
    claim_cases = yaml.safe_load((CLAIM / "cases.yaml").read_text(encoding="utf-8"))
    assert claim_cases["protocol_id"] == "r3-ledger-claim-v1"
    assert [case["case_id"] for case in claim_cases["cases"]] == [
        "T01", "T02", "T03", "T04", "T05", "T06",
    ]
    settlement_cases = yaml.safe_load((SETTLEMENT / "cases.yaml").read_text(encoding="utf-8"))
    assert settlement_cases["protocol_id"] == "r3-ledger-settlement-v1"
    assert settlement_cases["bmo_base_rev"] == "c8297333b3bf31ded96ca0e8b39c531d3bcea97f"
