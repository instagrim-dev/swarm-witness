"""Classical settlement adapter.

Claim behavior is ClassicalLedgerGate. Settlement records the shared contract
for the continuation named by the action. It does not execute BMO's settler.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from swarm_witness.classical_ledger_gate import ClassicalLedgerGate

_LOCAL_PROTOCOL = Path(__file__).resolve().parent / "protocol.py"
_local_spec = importlib.util.spec_from_file_location(
    "ledger_settlement_v1_protocol_adapter", _LOCAL_PROTOCOL
)
if _local_spec is None or _local_spec.loader is None:
    raise ImportError(f"cannot load {_LOCAL_PROTOCOL}")
_local_protocol = importlib.util.module_from_spec(_local_spec)
_local_spec.loader.exec_module(_local_protocol)
PROTOCOL_ID = _local_protocol.PROTOCOL_ID
Action = _local_protocol.Action
CaseSpec = _local_protocol.CaseSpec

ADAPTER_ID = "classical_ledger_gate"

_CLAIM_PROTOCOL = Path(__file__).resolve().parents[1] / "ledger_claim_v1" / "protocol.py"
_spec = importlib.util.spec_from_file_location("ledger_claim_v1_protocol", _CLAIM_PROTOCOL)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load {_CLAIM_PROTOCOL}")
_claim_protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_claim_protocol)
project_ledger = _claim_protocol.project_state


class ClassicalAdapter:
    def __init__(self, work_dir: Path) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.gate = ClassicalLedgerGate(self.work_dir / "classical.sqlite")
        self._case: CaseSpec | None = None

    def open_case(self, case: CaseSpec) -> None:
        self._case = case
        self.gate.open_case(case.fixture)

    def close(self) -> None:
        self.gate.close()

    def _state(self) -> dict[str, Any]:
        raw = self.gate.inspect()
        projected = project_ledger(raw) or {}
        projected["settlement"] = raw.get("settlement")
        return projected

    def _row(
        self,
        action: Action,
        *,
        disposition: str,
        native_result: dict[str, Any],
        inputs: dict[str, Any],
        notes: str = "",
    ) -> dict[str, Any]:
        if self._case is None:
            raise RuntimeError("open_case required")
        return {
            "protocol_id": PROTOCOL_ID,
            "case_id": self._case.case_id,
            "step": action.step,
            "op": action.op,
            "adapter_id": ADAPTER_ID,
            "execution_status": "completed",
            "disposition": disposition,
            "inputs": inputs,
            "native_result": native_result,
            "state": self._state(),
            "notes": notes,
        }

    def apply(self, action: Action) -> dict[str, Any]:
        if action.op == "inspect":
            return self._row(
                action,
                disposition="observed",
                native_result={},
                inputs={},
            )
        if action.op == "claim_first_edit":
            inputs = {
                "call_id": action.call_id,
                "task_id": action.task_id,
                "grant_id": action.grant_id,
                "owner_revision": action.owner_revision,
                "retry_epoch": action.retry_epoch,
                "transaction_completion": action.transaction_completion,
            }
            result = self.gate.claim_first_edit(**inputs)
            return self._row(
                action,
                disposition=str(result["disposition"]),
                native_result=result,
                inputs=inputs,
                notes=str(result.get("reason") or ""),
            )
        if action.op in {"settle_applied", "settle_no_effect"}:
            outcome = "applied" if action.op == "settle_applied" else "not_entered"
            evidence = action.evidence or "bound"
            inputs = {"call_id": action.call_id, "outcome": outcome, "evidence": evidence}
            result = self.gate.settle_continuation(
                call_id=str(action.call_id), outcome=outcome, evidence=evidence
            )
            return self._row(
                action,
                disposition=str(result["disposition"]),
                native_result=result,
                inputs=inputs,
                notes=str(result.get("reason") or ""),
            )
        raise ValueError(f"unsupported op {action.op!r}")
