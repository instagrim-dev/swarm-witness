"""Comparator stage tests for r3-ledger-claim-v1."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "r3" / "ledger_claim_v1"


def _load(name: str, path: Path):
    sys.path.insert(0, str(PKG))
    sys.path.insert(0, str(ROOT / "src"))
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _step(
    case_id: str,
    step: int,
    op: str,
    *,
    adapter: str,
    disposition: str | None,
    state: dict | None,
    inputs: dict | None = None,
    execution_status: str = "completed",
) -> dict:
    return {
        "protocol_id": "r3-ledger-claim-v1",
        "case_id": case_id,
        "step": step,
        "op": op,
        "adapter_id": adapter,
        "execution_status": execution_status,
        "disposition": disposition,
        "inputs": inputs or {},
        "native_result": {},
        "state": state,
        "notes": "",
    }


def _t03_happy(adapter: str) -> list[dict]:
    spent = {
        "grant_spent": True,
        "claim_count": 1,
        "transfer_count": 1,
        "claims": [
            {
                "call_id": "call-t03-a",
                "task_id": "task-alpha",
                "grant_id": "grant-alpha",
                "owner_revision": 1,
                "retry_epoch": "epoch-1",
            }
        ],
        "transfers": [
            {
                "call_id": "call-t03-a",
                "task_id": "task-alpha",
                "grant_id": "grant-alpha",
                "owner_revision": 1,
                "retry_epoch": "epoch-1",
            }
        ],
        "claim_call_ids": ["call-t03-a"],
        "transfer_call_ids": ["call-t03-a"],
    }
    claim_inputs = {
        "call_id": "call-t03-a",
        "task_id": "task-alpha",
        "grant_id": "grant-alpha",
        "owner_revision": 1,
        "retry_epoch": "epoch-1",
        "transaction_completion": "commit",
    }
    return [
        _step("T03", 1, "reopen", adapter=adapter, disposition="observed", state={
            "grant_spent": False,
            "claim_count": 0,
            "transfer_count": 0,
            "claims": [],
            "transfers": [],
            "claim_call_ids": [],
            "transfer_call_ids": [],
        }),
        _step(
            "T03",
            2,
            "claim_first_edit",
            adapter=adapter,
            disposition="committed",
            state=spent,
            inputs=claim_inputs,
        ),
        _step("T03", 3, "inspect", adapter=adapter, disposition="observed", state=spent),
    ]


def test_equal_and_correct_is_matched(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    # Build minimal cases bundle with only T03 for focused fixture.
    all_cases = proto.load_cases(PKG / "cases.yaml")
    t03 = next(c for c in all_cases["cases"] if c.case_id == "T03")

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    c_steps = _t03_happy("classical_ledger_gate")
    b_steps = _t03_happy("bmo")
    (run_dir / "classical.ndjson").write_text(
        "\n".join(json.dumps(s) for s in c_steps) + "\n", encoding="utf-8"
    )
    (run_dir / "bmo.ndjson").write_text(
        "\n".join(json.dumps(s) for s in b_steps) + "\n", encoding="utf-8"
    )

    validity = compare.pair_validity(
        cases=[t03], classical_steps=c_steps, bmo_steps=b_steps
    )
    assert validity["valid"] is True
    props = compare.property_outcomes(
        [t03], classical_steps=c_steps, bmo_steps=b_steps
    )
    assert props["classical"]["T03"]["passed"]
    assert props["bmo"]["T03"]["passed"]
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "matched"


def test_equal_but_wrong_is_matched_not_enforcement():
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    t03 = next(c for c in proto.load_cases(PKG / "cases.yaml")["cases"] if c.case_id == "T03")
    wrong = {
        "grant_spent": False,
        "claim_count": 0,
        "transfer_count": 0,
        "claims": [],
        "transfers": [],
        "claim_call_ids": [],
        "transfer_call_ids": [],
    }
    claim_inputs = {
        "call_id": "call-t03-a",
        "task_id": "task-alpha",
        "grant_id": "grant-alpha",
        "owner_revision": 1,
        "retry_epoch": "epoch-1",
        "transaction_completion": "commit",
    }
    # Both refuse first claim — equal projections, both fail T03 property.
    c_steps = [
        _step("T03", 1, "reopen", adapter="c", disposition="observed", state=wrong),
        _step(
            "T03",
            2,
            "claim_first_edit",
            adapter="c",
            disposition="refused",
            state=wrong,
            inputs=claim_inputs,
        ),
        _step("T03", 3, "inspect", adapter="c", disposition="observed", state=wrong),
    ]
    b_steps = [
        _step("T03", 1, "reopen", adapter="b", disposition="observed", state=wrong),
        _step(
            "T03",
            2,
            "claim_first_edit",
            adapter="b",
            disposition="refused",
            state=wrong,
            inputs=claim_inputs,
        ),
        _step("T03", 3, "inspect", adapter="b", disposition="observed", state=wrong),
    ]
    validity = compare.pair_validity(cases=[t03], classical_steps=c_steps, bmo_steps=b_steps)
    props = compare.property_outcomes([t03], classical_steps=c_steps, bmo_steps=b_steps)
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "matched"
    assert props["classical"]["T03"]["passed"] is False
    finding = compare.classify_finding(
        validity=validity, properties=props, agree=agree, run_ids=["r1"]
    )
    assert finding["label"] == "classical_baseline_matches"
    assert "not successful enforcement" in finding["proposition"].lower() or (
        "both fail" in finding["proposition"].lower()
    )


def test_valid_divergence():
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    t03 = next(c for c in proto.load_cases(PKG / "cases.yaml")["cases"] if c.case_id == "T03")
    c_steps = _t03_happy("classical")
    b_steps = _t03_happy("bmo")
    # Mutate BMO final state claim identity while keeping counts — identity-bound diverge.
    for s in b_steps:
        if s.get("state") and s["state"].get("claims"):
            s["state"]["claims"][0]["call_id"] = "other"
            s["state"]["claim_call_ids"] = ["other"]
            s["state"]["transfers"][0]["call_id"] = "other"
            s["state"]["transfer_call_ids"] = ["other"]
    validity = compare.pair_validity(cases=[t03], classical_steps=c_steps, bmo_steps=b_steps)
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "divergent"


def test_truncated_ndjson_unresolved(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "classical.ndjson").write_text("{}\n", encoding="utf-8")
    (run_dir / "bmo.ndjson").write_text("", encoding="utf-8")
    summary = compare.compare_run(run_dir, cases_path=PKG / "cases.yaml")
    assert summary["finding"]["label"] == "unresolved"
    assert summary["validity"]["valid"] is False


def test_input_mismatch_not_policy_disagreement():
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    t03 = next(c for c in proto.load_cases(PKG / "cases.yaml")["cases"] if c.case_id == "T03")
    c_steps = _t03_happy("c")
    b_steps = _t03_happy("b")
    for s in b_steps:
        if s["op"] == "claim_first_edit":
            s["inputs"]["task_id"] = "task-OTHER"
    validity = compare.pair_validity(cases=[t03], classical_steps=c_steps, bmo_steps=b_steps)
    assert validity["valid"] is False
    assert any("input mismatch" in e for e in validity["errors"])
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "unresolved"


def test_green_package_log_cannot_fill_observations(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "bmo_go_test.log").write_text("PASS ok\n", encoding="utf-8")
    # No NDJSON — package log alone must not yield matched.
    summary = compare.compare_run(run_dir, cases_path=PKG / "cases.yaml")
    assert summary["finding"]["label"] == "unresolved"
