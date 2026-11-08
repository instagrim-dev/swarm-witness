"""SQLite ClassicalLedgerGate — one-use ledger claim reference monitor.

Independent of ClassicalGate (decision-model). Implements shared policy for
protocol r3-ledger-claim-v1: atomic uniqueness for (grant_id, retry_epoch),
spent authority, cold database reopen without reminting.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS authority (
  grant_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  owner_revision INTEGER NOT NULL,
  retry_epoch TEXT NOT NULL,
  spent INTEGER NOT NULL DEFAULT 0 CHECK (spent IN (0, 1))
);

CREATE TABLE IF NOT EXISTS claims (
  call_id TEXT PRIMARY KEY,
  grant_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  owner_revision INTEGER NOT NULL,
  retry_epoch TEXT NOT NULL,
  UNIQUE (grant_id, retry_epoch)
);

CREATE TABLE IF NOT EXISTS transfers (
  call_id TEXT PRIMARY KEY,
  grant_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  owner_revision INTEGER NOT NULL,
  retry_epoch TEXT NOT NULL,
  UNIQUE (grant_id, retry_epoch),
  FOREIGN KEY (call_id) REFERENCES claims(call_id)
);

CREATE TABLE IF NOT EXISTS executions (
  call_id TEXT PRIMARY KEY,
  outcome TEXT NOT NULL CHECK (outcome IN ('applied', 'not_entered')),
  tool_bound INTEGER NOT NULL CHECK (tool_bound IN (0, 1)),
  mutation_bound INTEGER NOT NULL CHECK (mutation_bound IN (0, 1)),
  artifact_bound INTEGER NOT NULL CHECK (artifact_bound IN (0, 1)),
  source_receipt_bound INTEGER NOT NULL CHECK (source_receipt_bound IN (0, 1)),
  FOREIGN KEY (call_id) REFERENCES claims(call_id)
);
"""


@dataclass
class ClassicalLedgerGate:
    """SQLite-backed one-use first-edit claim owner."""

    db_path: Path
    _conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def reopen(self) -> None:
        """Cold database reopen: release handles and reacquire; do not remint."""
        path = self.db_path
        self.close()
        self.db_path = path
        self.open()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("ClassicalLedgerGate is closed")
        return self._conn

    def open_case(self, fixture: dict[str, Any]) -> None:
        self.open()
        spent = 1 if fixture.get("initial_spent") else 0
        self.conn.execute("DELETE FROM executions")
        self.conn.execute("DELETE FROM transfers")
        self.conn.execute("DELETE FROM claims")
        self.conn.execute("DELETE FROM authority")
        self.conn.execute(
            "INSERT INTO authority(grant_id, task_id, owner_revision, retry_epoch, spent) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                str(fixture["grant_id"]),
                str(fixture["task_id"]),
                int(fixture["owner_revision"]),
                str(fixture["retry_epoch"]),
                spent,
            ),
        )
        self.conn.commit()

    def inspect(self) -> dict[str, Any]:
        auth = self.conn.execute("SELECT * FROM authority").fetchone()
        if auth is None:
            return {
                "grant_spent": False,
                "claim_count": 0,
                "transfer_count": 0,
                "claims": [],
                "transfers": [],
                "claim_call_ids": [],
                "transfer_call_ids": [],
            }
        claims = [
            {
                "call_id": row["call_id"],
                "grant_id": row["grant_id"],
                "task_id": row["task_id"],
                "owner_revision": row["owner_revision"],
                "retry_epoch": row["retry_epoch"],
            }
            for row in self.conn.execute(
                "SELECT call_id, grant_id, task_id, owner_revision, retry_epoch "
                "FROM claims ORDER BY call_id"
            )
        ]
        transfers = [
            {
                "call_id": row["call_id"],
                "grant_id": row["grant_id"],
                "task_id": row["task_id"],
                "owner_revision": row["owner_revision"],
                "retry_epoch": row["retry_epoch"],
            }
            for row in self.conn.execute(
                "SELECT call_id, grant_id, task_id, owner_revision, retry_epoch "
                "FROM transfers ORDER BY call_id"
            )
        ]
        return {
            "grant_spent": bool(auth["spent"]),
            "claim_count": len(claims),
            "transfer_count": len(transfers),
            "claims": claims,
            "transfers": transfers,
            "claim_call_ids": [c["call_id"] for c in claims],
            "transfer_call_ids": [t["call_id"] for t in transfers],
            "authority": {
                "grant_id": auth["grant_id"],
                "task_id": auth["task_id"],
                "owner_revision": auth["owner_revision"],
                "retry_epoch": auth["retry_epoch"],
            },
            "settlement": self._settlement_view(),
        }

    def _settlement_view(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT call_id, outcome, tool_bound, mutation_bound, artifact_bound, "
            "source_receipt_bound FROM executions ORDER BY call_id"
        ).fetchall()
        if not row:
            return None
        if len(row) != 1:
            return {
                "disposition": "multiple",
                "call_id": None,
                "tool_bound": False,
                "mutation_bound": False,
                "artifact_bound": False,
                "source_receipt_bound": False,
            }
        item = row[0]
        return {
            "disposition": item["outcome"],
            "call_id": item["call_id"],
            "tool_bound": bool(item["tool_bound"]),
            "mutation_bound": bool(item["mutation_bound"]),
            "artifact_bound": bool(item["artifact_bound"]),
            "source_receipt_bound": bool(item["source_receipt_bound"]),
        }

    def settle_continuation(self, *, call_id: str, outcome: str) -> dict[str, Any]:
        """Record the declared settlement contract for one committed claim.

        ``applied`` binds tool, mutation, and artifact, with no no-effect receipt.
        ``not_entered`` binds the tool and a definite no-effect receipt, with no
        mutation or artifact. This is the classical contract, not BMO's settler.
        """
        if outcome not in {"applied", "not_entered"}:
            return {
                "disposition": "refused",
                "reason": "unknown_outcome",
                "native_ok": False,
            }
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            claim = self.conn.execute(
                "SELECT call_id FROM claims WHERE call_id = ?", (call_id,)
            ).fetchone()
            if claim is None:
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "refused",
                    "reason": "no_claim",
                    "native_ok": False,
                }
            existing = self.conn.execute(
                "SELECT call_id FROM executions WHERE call_id = ?", (call_id,)
            ).fetchone()
            if existing is not None:
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "refused",
                    "reason": "already_settled",
                    "native_ok": False,
                }
            if outcome == "applied":
                flags = (1, 1, 1, 0)
            else:
                flags = (1, 0, 0, 1)
            self.conn.execute(
                "INSERT INTO executions("
                "call_id, outcome, tool_bound, mutation_bound, artifact_bound, "
                "source_receipt_bound) VALUES (?, ?, ?, ?, ?, ?)",
                (call_id, outcome, *flags),
            )
            self.conn.execute("COMMIT")
            return {
                "disposition": "committed",
                "reason": "ok",
                "native_ok": True,
                "call_id": call_id,
                "outcome": outcome,
            }
        except sqlite3.IntegrityError as exc:
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            return {
                "disposition": "refused",
                "reason": "integrity_error",
                "error": str(exc),
                "native_ok": False,
            }
        except Exception as exc:  # noqa: BLE001 — surface as error disposition
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            return {
                "disposition": "error",
                "reason": "exception",
                "error": str(exc),
                "native_ok": False,
            }

    def claim_first_edit(
        self,
        *,
        call_id: str,
        task_id: str,
        grant_id: str,
        owner_revision: int,
        retry_epoch: str,
        transaction_completion: str = "commit",
    ) -> dict[str, Any]:
        """Attempt one-use claim+transfer. Never answers by case_id."""
        if transaction_completion not in {
            "commit",
            "rollback_after_native_success",
        }:
            raise ValueError(f"invalid transaction_completion {transaction_completion!r}")

        try:
            self.conn.execute("BEGIN IMMEDIATE")
            auth = self.conn.execute(
                "SELECT * FROM authority WHERE grant_id = ?", (grant_id,)
            ).fetchone()
            if auth is None:
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "refused",
                    "reason": "unknown_grant",
                    "native_ok": False,
                }
            if auth["spent"]:
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "refused",
                    "reason": "already_spent",
                    "native_ok": False,
                }
            if auth["task_id"] != task_id:
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "refused",
                    "reason": "wrong_task",
                    "native_ok": False,
                }
            if int(auth["owner_revision"]) != int(owner_revision):
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "refused",
                    "reason": "wrong_owner_revision",
                    "native_ok": False,
                }
            if auth["retry_epoch"] != retry_epoch:
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "refused",
                    "reason": "wrong_epoch",
                    "native_ok": False,
                }
            existing = self.conn.execute(
                "SELECT call_id FROM claims WHERE grant_id = ? AND retry_epoch = ?",
                (grant_id, retry_epoch),
            ).fetchone()
            if existing is not None:
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "refused",
                    "reason": "duplicate_claim",
                    "existing_call_id": existing["call_id"],
                    "native_ok": False,
                }

            self.conn.execute(
                "INSERT INTO claims(call_id, grant_id, task_id, owner_revision, retry_epoch) "
                "VALUES (?, ?, ?, ?, ?)",
                (call_id, grant_id, task_id, owner_revision, retry_epoch),
            )
            self.conn.execute(
                "INSERT INTO transfers(call_id, grant_id, task_id, owner_revision, retry_epoch) "
                "VALUES (?, ?, ?, ?, ?)",
                (call_id, grant_id, task_id, owner_revision, retry_epoch),
            )
            self.conn.execute(
                "UPDATE authority SET spent = 1 WHERE grant_id = ?", (grant_id,)
            )

            if transaction_completion == "rollback_after_native_success":
                self.conn.execute("ROLLBACK")
                return {
                    "disposition": "rolled_back",
                    "reason": "rollback_after_native_success",
                    "native_ok": True,
                }

            self.conn.execute("COMMIT")
            return {
                "disposition": "committed",
                "reason": "ok",
                "native_ok": True,
                "call_id": call_id,
            }
        except sqlite3.IntegrityError as exc:
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            return {
                "disposition": "refused",
                "reason": "integrity_error",
                "error": str(exc),
                "native_ok": False,
            }
        except Exception as exc:  # noqa: BLE001 — surface as error disposition
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            return {
                "disposition": "error",
                "reason": "exception",
                "error": str(exc),
                "native_ok": False,
            }
