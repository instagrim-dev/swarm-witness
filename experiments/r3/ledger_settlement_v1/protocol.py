"""Typed contract for protocol r3-ledger-settlement-v1.

A committed first-edit claim is staged before settlement. The claim and ledger
view come first. The bound execution and settlement record come second.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROTOCOL_ID = "r3-ledger-settlement-v1"
CLAIM_ID = "r3_ledger_settlement_v1"
DISPOSITIONS = frozenset(
    {"committed", "refused", "rolled_back", "error", "observed", "unsupported"}
)
OPS = frozenset({"claim_first_edit", "inspect", "settle_applied", "settle_no_effect"})
TX_COMPLETIONS = frozenset({"commit", "rollback_after_native_success"})
SETTLEMENT_OUTCOMES = frozenset({"applied", "not_entered"})
EVIDENCE_SHAPES = frozenset(
    {
        "bound",
        "missing_mutation",
        "swapped",
        "wrong_call",
        "write_present",
        "missing",
        "unrelated",
    }
)
# Only a bound terminal record may decide the effect-applied proposition.
DECISIVE_EVIDENCE = frozenset({"bound"})


@dataclass(frozen=True)
class Action:
    step: int
    op: str
    call_id: str | None = None
    task_id: str | None = None
    grant_id: str | None = None
    owner_revision: int | None = None
    retry_epoch: str | None = None
    transaction_completion: str = "commit"
    outcome: str | None = None
    evidence: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    name: str
    description: str
    fixture: dict[str, Any]
    actions: tuple[Action, ...]
    expected: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict, compare=False)


def _require_mapping(data: Any, where: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{where} must be a mapping")
    return data


def parse_action(raw: dict[str, Any]) -> Action:
    raw = _require_mapping(raw, "action")
    step = raw.get("step")
    if not isinstance(step, int) or step < 1:
        raise ValueError(f"action.step must be a positive int, got {step!r}")
    op = raw.get("op")
    if op not in OPS:
        raise ValueError(f"unsupported op {op!r}")
    tx = raw.get("transaction_completion", "commit")
    if op == "claim_first_edit" and tx not in TX_COMPLETIONS:
        raise ValueError(f"invalid transaction_completion {tx!r}")
    if op == "claim_first_edit":
        for key in ("call_id", "task_id", "grant_id", "retry_epoch"):
            val = raw.get(key)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"claim_first_edit requires nonblank {key}")
        if not isinstance(raw.get("owner_revision"), int):
            raise ValueError("claim_first_edit requires integer owner_revision")
    if op in {"settle_applied", "settle_no_effect"}:
        if not isinstance(raw.get("call_id"), str) or not str(raw.get("call_id")).strip():
            raise ValueError(f"{op} requires nonblank call_id")
        outcome = "applied" if op == "settle_applied" else "not_entered"
        declared = raw.get("outcome", outcome)
        if declared != outcome:
            raise ValueError(f"{op} outcome must be {outcome!r}")
        evidence = raw.get("evidence", "bound")
        if evidence not in EVIDENCE_SHAPES:
            raise ValueError(f"unsupported evidence {evidence!r}")
        if op == "settle_applied" and evidence == "write_present":
            raise ValueError("write_present belongs to settle_no_effect")
    else:
        outcome = None
        evidence = None
    call_id = raw.get("call_id")
    return Action(
        step=step,
        op=str(op),
        call_id=None if call_id is None else str(call_id),
        task_id=None if raw.get("task_id") is None else str(raw["task_id"]),
        grant_id=None if raw.get("grant_id") is None else str(raw["grant_id"]),
        owner_revision=raw.get("owner_revision")
        if isinstance(raw.get("owner_revision"), int)
        else None,
        retry_epoch=None if raw.get("retry_epoch") is None else str(raw["retry_epoch"]),
        transaction_completion=str(tx),
        outcome=outcome,
        evidence=None if evidence is None else str(evidence),
        raw=dict(raw),
    )


def parse_case(raw: dict[str, Any]) -> CaseSpec:
    raw = _require_mapping(raw, "case")
    case_id = raw.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id required")
    fixture = _require_mapping(raw.get("fixture"), f"{case_id}.fixture")
    for key in ("task_id", "grant_id", "retry_epoch"):
        if not isinstance(fixture.get(key), str) or not str(fixture[key]).strip():
            raise ValueError(f"{case_id}.fixture.{key} required")
    if not isinstance(fixture.get("owner_revision"), int):
        raise ValueError(f"{case_id}.fixture.owner_revision must be int")
    if not isinstance(fixture.get("initial_spent"), bool):
        raise ValueError(f"{case_id}.fixture.initial_spent must be bool")
    actions_raw = raw.get("actions")
    if not isinstance(actions_raw, list) or not actions_raw:
        raise ValueError(f"{case_id}.actions must be a non-empty list")
    actions = tuple(parse_action(a) for a in actions_raw)
    steps = [a.step for a in actions]
    if steps != list(range(1, len(actions) + 1)):
        raise ValueError(f"{case_id}: action steps must be contiguous from 1")
    expected = _require_mapping(raw.get("expected"), f"{case_id}.expected")
    if "final_state" not in expected:
        raise ValueError(f"{case_id}.expected.final_state required")
    return CaseSpec(
        case_id=case_id.strip(),
        name=str(raw.get("name") or case_id).strip(),
        description=str(raw.get("description") or "").strip(),
        fixture=dict(fixture),
        actions=actions,
        expected=dict(expected),
        raw=dict(raw),
    )


def load_cases(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    data = _require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "cases.yaml")
    if data.get("protocol_id") != PROTOCOL_ID:
        raise ValueError(
            f"protocol_id must be {PROTOCOL_ID!r}, got {data.get('protocol_id')!r}"
        )
    cases_raw = data.get("cases")
    if not isinstance(cases_raw, list) or not cases_raw:
        raise ValueError("cases must be a non-empty list")
    cases = [parse_case(c) for c in cases_raw]
    ids = [c.case_id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate case_id in {path}")
    return {
        "protocol_id": PROTOCOL_ID,
        "claim_id": str(data.get("claim_id") or CLAIM_ID),
        "bmo_base_rev": data.get("bmo_base_rev"),
        "cases": cases,
        "path": str(path),
    }


def settlement_projection(settlement: dict[str, Any] | None) -> dict[str, Any] | None:
    if not settlement:
        return None
    return {
        "disposition": settlement.get("disposition"),
        "call_id": settlement.get("call_id"),
        "tool_bound": bool(settlement.get("tool_bound")),
        "mutation_bound": bool(settlement.get("mutation_bound")),
        "artifact_bound": bool(settlement.get("artifact_bound")),
        "source_receipt_bound": bool(settlement.get("source_receipt_bound")),
    }


def contract_conformant(settlement: dict[str, Any] | None) -> bool:
    """Shared settlement contract for both arms.

    Applied binds tool, mutation, and artifact, and carries no no-effect receipt.
    A definite no-effect binds the tool and a source receipt, and carries neither
    mutation nor artifact.
    """
    projected = settlement_projection(settlement)
    if projected is None or not projected.get("call_id"):
        return False
    if projected["disposition"] == "applied":
        return bool(
            projected["tool_bound"]
            and projected["mutation_bound"]
            and projected["artifact_bound"]
            and not projected["source_receipt_bound"]
        )
    if projected["disposition"] == "not_entered":
        return bool(
            projected["tool_bound"]
            and projected["source_receipt_bound"]
            and not projected["mutation_bound"]
            and not projected["artifact_bound"]
        )
    return False


def effect_verdict(state: dict[str, Any] | None) -> str:
    """Whether the recorded settlement establishes that the claimed edit applied.

    A claim and ledger view alone stay unresolved. A conforming applied record
    supports the delegated effect. A conforming definite no-effect refutes it.
    """
    if not isinstance(state, dict):
        return "unresolved"
    settlement = state.get("settlement")
    if not isinstance(settlement, dict) or not contract_conformant(settlement):
        return "unresolved"
    if settlement.get("disposition") == "applied":
        return "supported"
    if settlement.get("disposition") == "not_entered":
        return "refuted"
    return "unresolved"
