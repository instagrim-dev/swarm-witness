"""Typed contract for protocol r3-ledger-claim-v1.

Operations: open_case → apply / reopen / inspect.
Actions describe operations; expected properties live outside adapter inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROTOCOL_ID = "r3-ledger-claim-v1"
CLAIM_ID = "r3_ledger_claim_v1"
DISPOSITIONS = frozenset(
    {"committed", "refused", "rolled_back", "error", "observed", "unsupported"}
)
OPS = frozenset({"claim_first_edit", "reopen", "inspect"})
TX_COMPLETIONS = frozenset({"commit", "rollback_after_native_success"})


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


@dataclass(frozen=True)
class StepObservation:
    """One adapter step result (claim / reopen / inspect)."""

    protocol_id: str
    case_id: str
    step: int
    op: str
    adapter_id: str
    execution_status: str
    disposition: str | None
    inputs: dict[str, Any]
    native_result: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "case_id": self.case_id,
            "step": self.step,
            "op": self.op,
            "adapter_id": self.adapter_id,
            "execution_status": self.execution_status,
            "disposition": self.disposition,
            "inputs": dict(self.inputs),
            "native_result": dict(self.native_result),
            "state": None if self.state is None else dict(self.state),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class StateObservation:
    """Property-relevant projection (identity-bound; not storage-byte equality)."""

    grant_spent: bool
    claim_count: int
    transfer_count: int
    claims: tuple[dict[str, Any], ...]
    transfers: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_spent": self.grant_spent,
            "claim_count": self.claim_count,
            "transfer_count": self.transfer_count,
            "claims": [dict(c) for c in self.claims],
            "transfers": [dict(t) for t in self.transfers],
            "claim_call_ids": [c["call_id"] for c in self.claims],
            "transfer_call_ids": [t["call_id"] for t in self.transfers],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateObservation:
        claims = tuple(dict(c) for c in (data.get("claims") or ()))
        transfers = tuple(dict(t) for t in (data.get("transfers") or ()))
        return cls(
            grant_spent=bool(data.get("grant_spent")),
            claim_count=int(data.get("claim_count", len(claims))),
            transfer_count=int(data.get("transfer_count", len(transfers))),
            claims=claims,
            transfers=transfers,
        )


def project_state(state: dict[str, Any] | StateObservation | None) -> dict[str, Any] | None:
    """Normalize a state payload to the shared property-relevant projection.

    Cross-arm equality is limited to one-use behavior actually observed on both
    backends: grant_spent, counts, and call_id sets. Synthetic classical
    grant_id / retry_epoch aliases are not compared to native BMO hashes until
    an explicit alias map is declared and negative-controlled. Raw native
    identity rows may still appear under ``observed_identities`` for audit.
    """
    if state is None:
        return None
    if isinstance(state, StateObservation):
        data = state.to_dict()
    elif isinstance(state, dict):
        data = state
    else:
        raise TypeError("state must be a dict or StateObservation")
    claims = [dict(c) for c in (data.get("claims") or [])]
    transfers = [dict(t) for t in (data.get("transfers") or [])]
    claims.sort(key=lambda c: (c.get("call_id") or ""))
    transfers.sort(key=lambda t: (t.get("call_id") or ""))
    claim_ids = [c.get("call_id") for c in claims]
    transfer_ids = [t.get("call_id") for t in transfers]
    return {
        "grant_spent": bool(data.get("grant_spent")),
        "claim_count": int(data.get("claim_count", len(claims))),
        "transfer_count": int(data.get("transfer_count", len(transfers))),
        # call_id-only rows: identity dimensions beyond call_id are not part of
        # the L1 equality claim without an alias map + negative control.
        "claims": [{"call_id": cid} for cid in claim_ids],
        "transfers": [{"call_id": tid} for tid in transfer_ids],
        "claim_call_ids": claim_ids,
        "transfer_call_ids": transfer_ids,
    }


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
    call_id = raw.get("call_id")
    if op == "claim_first_edit":
        for key in ("call_id", "task_id", "grant_id", "retry_epoch"):
            val = raw.get(key)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"claim_first_edit requires nonblank {key}")
        rev = raw.get("owner_revision")
        if not isinstance(rev, int):
            raise ValueError("claim_first_edit requires integer owner_revision")
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
    if "initial_spent" not in fixture or not isinstance(fixture["initial_spent"], bool):
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
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data = _require_mapping(data, "cases.yaml")
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
        "source_pin_key": data.get("source_pin_key"),
        "bmo_base_rev": data.get("bmo_base_rev"),
        "aliases": data.get("aliases") or {},
        "cases": cases,
        "path": str(path),
    }


def validate_step_observation(obs: dict[str, Any]) -> StepObservation:
    obs = _require_mapping(obs, "step observation")
    if obs.get("protocol_id") != PROTOCOL_ID:
        raise ValueError(f"protocol_id mismatch: {obs.get('protocol_id')!r}")
    for key in ("case_id", "op", "adapter_id", "execution_status"):
        val = obs.get(key)
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"step observation requires nonblank {key}")
    step = obs.get("step")
    if not isinstance(step, int) or step < 1:
        raise ValueError("step must be a positive int")
    if obs["op"] not in OPS:
        raise ValueError(f"unsupported op {obs['op']!r}")
    disposition = obs.get("disposition")
    if disposition is not None and disposition not in DISPOSITIONS:
        raise ValueError(f"invalid disposition {disposition!r}")
    inputs = obs.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    native = obs.get("native_result") or {}
    if not isinstance(native, dict):
        raise ValueError("native_result must be a dict")
    state = obs.get("state")
    if state is not None and not isinstance(state, dict):
        raise ValueError("state must be a dict or null")
    return StepObservation(
        protocol_id=PROTOCOL_ID,
        case_id=str(obs["case_id"]),
        step=step,
        op=str(obs["op"]),
        adapter_id=str(obs["adapter_id"]),
        execution_status=str(obs["execution_status"]),
        disposition=None if disposition is None else str(disposition),
        inputs=dict(inputs),
        native_result=dict(native),
        state=None if state is None else dict(state),
        notes=str(obs.get("notes") or ""),
    )


def match_expected_state(
    observed: dict[str, Any] | None, expected: dict[str, Any]
) -> list[str]:
    """Return human-readable mismatches for a partial expected state dict."""
    errors: list[str] = []
    if observed is None:
        return ["missing state observation"]
    proj = project_state(observed) or {}
    for key in ("grant_spent", "claim_count", "transfer_count"):
        if key in expected and proj.get(key) != expected[key]:
            errors.append(f"{key}: observed {proj.get(key)!r} != expected {expected[key]!r}")
    for key in ("claim_call_ids", "transfer_call_ids"):
        if key in expected:
            got = list(proj.get(key) or [])
            want = list(expected[key])
            if got != want:
                errors.append(f"{key}: observed {got!r} != expected {want!r}")
    return errors


def evaluate_case_property(
    case: CaseSpec, steps: list[dict[str, Any]]
) -> dict[str, Any]:
    """Evaluate one backend's trace against the case expected properties."""
    by_step = {s["step"]: s for s in steps if isinstance(s, dict)}
    errors: list[str] = []
    for exp in case.expected.get("steps") or []:
        step_no = exp.get("step")
        obs = by_step.get(step_no)
        if obs is None:
            errors.append(f"missing step {step_no}")
            continue
        if obs.get("execution_status") != "completed":
            errors.append(
                f"step {step_no}: execution_status {obs.get('execution_status')!r} "
                f"!= completed"
            )
            continue
        if "disposition" in exp and obs.get("disposition") != exp["disposition"]:
            errors.append(
                f"step {step_no}: disposition {obs.get('disposition')!r} "
                f"!= {exp['disposition']!r}"
            )
        if "state" in exp:
            errors.extend(
                f"step {step_no}: {e}"
                for e in match_expected_state(obs.get("state"), exp["state"])
            )

    # Final state: last inspect, else last step with state.
    inspect_steps = [
        s for s in steps if isinstance(s, dict) and s.get("op") == "inspect"
    ]
    final_obs = inspect_steps[-1] if inspect_steps else (steps[-1] if steps else None)
    final_state = None if final_obs is None else final_obs.get("state")
    errors.extend(
        f"final: {e}"
        for e in match_expected_state(final_state, case.expected["final_state"])
    )
    return {
        "case_id": case.case_id,
        "passed": not errors,
        "errors": errors,
        "final_state": project_state(final_state),
    }
