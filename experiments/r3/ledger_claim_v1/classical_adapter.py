"""ClassicalLedgerGate adapter implementing the shared operation contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from swarm_witness.classical_ledger_gate import ClassicalLedgerGate

from protocol import PROTOCOL_ID, CaseSpec, project_state

ADAPTER_ID = "classical_ledger_gate"


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

    def apply(self, action: dict[str, Any] | Any) -> dict[str, Any]:
        if self._case is None:
            raise RuntimeError("open_case required")
        op = action.op if hasattr(action, "op") else action["op"]
        step = action.step if hasattr(action, "step") else action["step"]
        if op == "reopen":
            self.gate.reopen()
            state = project_state(self.gate.inspect())
            return {
                "protocol_id": PROTOCOL_ID,
                "case_id": self._case.case_id,
                "step": step,
                "op": "reopen",
                "adapter_id": ADAPTER_ID,
                "execution_status": "completed",
                "disposition": "observed",
                "inputs": {},
                "native_result": {"reopened": True},
                "state": state,
                "notes": "cold database reopen",
            }
        if op == "inspect":
            state = project_state(self.gate.inspect())
            return {
                "protocol_id": PROTOCOL_ID,
                "case_id": self._case.case_id,
                "step": step,
                "op": "inspect",
                "adapter_id": ADAPTER_ID,
                "execution_status": "completed",
                "disposition": "observed",
                "inputs": {},
                "native_result": {},
                "state": state,
                "notes": "",
            }
        if op == "claim_first_edit":
            inputs = {
                "call_id": action.call_id if hasattr(action, "call_id") else action["call_id"],
                "task_id": action.task_id if hasattr(action, "task_id") else action["task_id"],
                "grant_id": action.grant_id if hasattr(action, "grant_id") else action["grant_id"],
                "owner_revision": (
                    action.owner_revision
                    if hasattr(action, "owner_revision")
                    else action["owner_revision"]
                ),
                "retry_epoch": (
                    action.retry_epoch
                    if hasattr(action, "retry_epoch")
                    else action["retry_epoch"]
                ),
                "transaction_completion": (
                    action.transaction_completion
                    if hasattr(action, "transaction_completion")
                    else action.get("transaction_completion", "commit")
                ),
            }
            result = self.gate.claim_first_edit(**inputs)
            state = project_state(self.gate.inspect())
            return {
                "protocol_id": PROTOCOL_ID,
                "case_id": self._case.case_id,
                "step": step,
                "op": "claim_first_edit",
                "adapter_id": ADAPTER_ID,
                "execution_status": "completed",
                "disposition": result["disposition"],
                "inputs": inputs,
                "native_result": result,
                "state": state,
                "notes": str(result.get("reason") or ""),
            }
        raise ValueError(f"unsupported op {op!r}")
