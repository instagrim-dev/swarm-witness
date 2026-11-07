"""Contract tests for r3-ledger-claim-v1 protocol."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "r3" / "ledger_claim_v1"
CASES = PKG / "cases.yaml"


def _load_protocol():
    sys.path.insert(0, str(PKG))
    name = "ledger_protocol"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PKG / "protocol.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_cases_yaml_loads_t01_through_t06():
    proto = _load_protocol()
    bundle = proto.load_cases(CASES)
    ids = [c.case_id for c in bundle["cases"]]
    assert ids == ["T01", "T02", "T03", "T04", "T05", "T06"]
    assert bundle["protocol_id"] == "r3-ledger-claim-v1"


def test_actions_never_embed_expected_decisions():
    data = yaml.safe_load(CASES.read_text(encoding="utf-8"))
    for case in data["cases"]:
        for action in case["actions"]:
            assert "expected_decision" not in action
            assert "disposition" not in action
            assert "expected" not in action


def test_reject_blank_case_id():
    proto = _load_protocol()
    with pytest.raises(ValueError, match="case_id"):
        proto.parse_case(
            {
                "case_id": "  ",
                "fixture": {
                    "task_id": "t",
                    "grant_id": "g",
                    "owner_revision": 1,
                    "retry_epoch": "e",
                    "initial_spent": False,
                },
                "actions": [{"step": 1, "op": "inspect"}],
                "expected": {"final_state": {"grant_spent": False, "claim_count": 0}},
            }
        )


def test_reject_noncontiguous_steps():
    proto = _load_protocol()
    with pytest.raises(ValueError, match="contiguous"):
        proto.parse_case(
            {
                "case_id": "TX",
                "fixture": {
                    "task_id": "t",
                    "grant_id": "g",
                    "owner_revision": 1,
                    "retry_epoch": "e",
                    "initial_spent": False,
                },
                "actions": [
                    {"step": 1, "op": "inspect"},
                    {"step": 3, "op": "inspect"},
                ],
                "expected": {"final_state": {"grant_spent": False, "claim_count": 0}},
            }
        )


def test_reject_claim_without_call_id():
    proto = _load_protocol()
    with pytest.raises(ValueError, match="call_id"):
        proto.parse_action(
            {
                "step": 1,
                "op": "claim_first_edit",
                "task_id": "t",
                "grant_id": "g",
                "owner_revision": 1,
                "retry_epoch": "e",
            }
        )


def test_validate_step_observation_rejects_bad_disposition():
    proto = _load_protocol()
    with pytest.raises(ValueError, match="disposition"):
        proto.validate_step_observation(
            {
                "protocol_id": "r3-ledger-claim-v1",
                "case_id": "T01",
                "step": 1,
                "op": "inspect",
                "adapter_id": "x",
                "execution_status": "completed",
                "disposition": "allow",
                "inputs": {},
            }
        )


def test_equal_but_wrong_state_fails_property():
    proto = _load_protocol()
    bundle = proto.load_cases(CASES)
    case = next(c for c in bundle["cases"] if c.case_id == "T01")
    # Both arms could agree on wrong state; property must still fail.
    bad_steps = [
        {
            "protocol_id": "r3-ledger-claim-v1",
            "case_id": "T01",
            "step": 1,
            "op": "claim_first_edit",
            "adapter_id": "x",
            "execution_status": "completed",
            "disposition": "committed",
            "inputs": {},
            "state": {
                "grant_spent": True,
                "claim_count": 2,
                "transfer_count": 2,
                "claims": [],
                "transfers": [],
                "claim_call_ids": ["a", "b"],
                "transfer_call_ids": ["a", "b"],
            },
        },
        {
            "protocol_id": "r3-ledger-claim-v1",
            "case_id": "T01",
            "step": 2,
            "op": "claim_first_edit",
            "adapter_id": "x",
            "execution_status": "completed",
            "disposition": "refused",
            "inputs": {},
            "state": None,
        },
        {
            "protocol_id": "r3-ledger-claim-v1",
            "case_id": "T01",
            "step": 3,
            "op": "inspect",
            "adapter_id": "x",
            "execution_status": "completed",
            "disposition": "observed",
            "inputs": {},
            "state": {
                "grant_spent": True,
                "claim_count": 2,
                "transfer_count": 2,
                "claims": [],
                "transfers": [],
                "claim_call_ids": ["a", "b"],
                "transfer_call_ids": ["a", "b"],
            },
        },
    ]
    result = proto.evaluate_case_property(case, bad_steps)
    assert result["passed"] is False
    assert any("claim_count" in e or "claim_call_ids" in e for e in result["errors"])
