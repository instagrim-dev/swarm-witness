"""Offline SQLite L1 surface used only when native BMO tree is unavailable.

Implements the shared claim/reopen/inspect contract with an independent
ClassicalLedgerGate database (separate file from the classical arm). This is
NOT ClaimOrdinaryRetainedGrantFirstEditTx. Manifest mode records
``offline_sqlite_l1_not_native`` so findings cannot be reported as native BMO.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from classical_adapter import ClassicalAdapter
from protocol import CaseSpec

ADAPTER_ID = "bmo_l1_first_edit"
MODE = "offline_sqlite_l1_not_native"


def run_offline_l1(cases: list[CaseSpec], work_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for case in cases:
        adapter = ClassicalAdapter(work_dir / case.case_id)
        try:
            adapter.open_case(case)
            for action in case.actions:
                row = adapter.apply(action)
                row["adapter_id"] = ADAPTER_ID
                row["notes"] = (row.get("notes") or "") + f"; mode={MODE}"
                row["native_result"] = {
                    **(row.get("native_result") or {}),
                    "mode": MODE,
                    "native_bmo": False,
                }
                rows.append(row)
        finally:
            adapter.close()
    manifest = {
        "adapter_id": ADAPTER_ID,
        "mode": MODE,
        "native_bmo": False,
        "notes": (
            "Offline SQLite L1 stand-in; not ClaimOrdinaryRetainedGrantFirstEditTx. "
            "Pair validity may complete for pipeline tests; do not publish as native "
            "BMO classical reduction without the tagged disposable-tree bridge."
        ),
    }
    return rows, manifest
