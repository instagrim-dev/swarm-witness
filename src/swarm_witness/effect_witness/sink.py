"""SQLite effect sink. The harness token is required for every write."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from swarm_witness.effect_witness.boundary import TRUST_BOUNDARY
from swarm_witness.incident_property_graph import (
    CHANNEL_SUBJECTS,
    REVOCATION_POLICIES,
)

SCHEMA = """
CREATE TABLE harness_ownership (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    owner TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    trust_boundary TEXT NOT NULL
);
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    history_id TEXT NOT NULL,
    revocation_policy TEXT NOT NULL
);
CREATE TABLE grants (
    grant_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    history_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    epoch_id TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    subject_class TEXT NOT NULL,
    object_scope TEXT NOT NULL,
    issued_at INTEGER NOT NULL
);
CREATE TABLE revocations (
    revocation_id TEXT PRIMARY KEY,
    grant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    history_id TEXT NOT NULL,
    policy TEXT NOT NULL,
    logical_time INTEGER NOT NULL
);
CREATE TABLE stages (
    operation_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    logical_time INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (operation_id, stage)
);
CREATE TABLE commits (
    event_id TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL,
    history_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    grant_id TEXT,
    epoch_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    subject_class TEXT NOT NULL,
    operation TEXT NOT NULL,
    object_scope TEXT NOT NULL,
    logical_time INTEGER NOT NULL
);
"""


class OwnershipError(PermissionError):
    """The caller does not hold the harness write token."""


class BarrierError(ValueError):
    """Decision, attempt, and commit were not in that order."""


class PolicyError(ValueError):
    """A revocation policy was missing or was not the one declared for the run."""


def token_hash(token: str) -> str:
    if not isinstance(token, str) or token == "":
        raise OwnershipError("harness write token is required")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def static_decision(channel: str, subject_class: str) -> str:
    return CHANNEL_SUBJECTS[channel][subject_class]


class EffectSink:
    """Application-owned store. Commits are rows, not a flag on the decision."""

    def __init__(self, connection: sqlite3.Connection, token: str):
        self._conn = connection
        self._token = token
        self._check_token(token)

    @classmethod
    def create(cls, path: Path, token: str) -> EffectSink:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO harness_ownership (id, owner, token_hash, trust_boundary) "
            "VALUES (1, ?, ?, ?)",
            ("aew-v1-harness", token_hash(token), TRUST_BOUNDARY),
        )
        conn.commit()
        return cls(conn, token)

    @classmethod
    def open(cls, path: Path, token: str) -> EffectSink:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return cls(conn, token)

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    def _check_token(self, token: str) -> None:
        row = self._conn.execute(
            "SELECT token_hash FROM harness_ownership WHERE id = 1"
        ).fetchone()
        if row is None or row["token_hash"] != token_hash(token):
            raise OwnershipError("harness write token does not own this sink")

    def _require(self, token: str) -> None:
        self._check_token(token)

    def declare_run(self, token: str, *, run_id: str, history_id: str, policy: str) -> None:
        self._require(token)
        if policy not in REVOCATION_POLICIES:
            raise PolicyError(
                "revocation policy must be declared per run; there is no default"
            )
        self._conn.execute(
            "INSERT INTO runs (run_id, history_id, revocation_policy) VALUES (?, ?, ?)",
            (run_id, history_id, policy),
        )
        self._conn.commit()

    def policy_for(self, run_id: str) -> str:
        row = self._conn.execute(
            "SELECT revocation_policy FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise PolicyError(f"run {run_id} has no declared revocation policy")
        return str(row["revocation_policy"])

    def issue_grant(self, token: str, grant: dict[str, Any]) -> None:
        self._require(token)
        self._conn.execute(
            "INSERT INTO grants (grant_id, run_id, history_id, actor_id, task_id, "
            "epoch_id, operation_id, channel, subject_class, object_scope, issued_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                grant["grant_id"],
                grant["run_id"],
                grant["history_id"],
                grant["actor_id"],
                grant["task_id"],
                grant["epoch_id"],
                grant["operation_id"],
                grant["channel"],
                grant["subject_class"],
                grant["object_scope"],
                grant["logical_time"],
            ),
        )
        self._conn.commit()

    def lookup_grant(self, grant_id: str | None) -> dict[str, Any] | None:
        if not grant_id:
            return None
        row = self._conn.execute(
            "SELECT * FROM grants WHERE grant_id = ?", (grant_id,)
        ).fetchone()
        return dict(row) if row else None

    def record_stage(self, token: str, *, operation_id: str, stage: str, logical_time: int, payload: dict[str, Any]) -> None:
        self._require(token)
        if stage not in {"decision", "attempt"}:
            raise BarrierError(f"unknown stage {stage}")
        self._conn.execute(
            "INSERT INTO stages (operation_id, stage, logical_time, payload) "
            "VALUES (?, ?, ?, ?)",
            (operation_id, stage, logical_time, json.dumps(payload, sort_keys=True)),
        )
        self._conn.commit()

    def stage(self, operation_id: str, name: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT logical_time, payload FROM stages WHERE operation_id = ? AND stage = ?",
            (operation_id, name),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload"])
        payload["logical_time"] = int(row["logical_time"])
        payload["stage"] = name
        return payload

    def insert_revocation(self, token: str, revocation: dict[str, Any]) -> None:
        """Record a revocation after the decision and before any commit."""
        self._require(token)
        policy = revocation["policy"]
        if policy not in REVOCATION_POLICIES:
            raise PolicyError("revocation policy must be one of the declared policies")
        if policy != self.policy_for(revocation["run_id"]):
            raise PolicyError("revocation policy does not match the policy frozen for the run")
        decision = self.stage(revocation["operation_id"], "decision")
        if decision is None:
            raise BarrierError("revocation inserted before a decision")
        if not decision["logical_time"] < revocation["logical_time"]:
            raise BarrierError("revocation is not after the decision")
        existing = self._conn.execute(
            "SELECT event_id FROM commits WHERE operation_id = ?",
            (revocation["operation_id"],),
        ).fetchone()
        if existing is not None:
            raise BarrierError("revocation inserted after settlement")
        self._conn.execute(
            "INSERT INTO revocations (revocation_id, grant_id, run_id, history_id, "
            "policy, logical_time) VALUES (?, ?, ?, ?, ?, ?)",
            (
                revocation["revocation_id"],
                revocation["grant_id"],
                revocation["run_id"],
                revocation["history_id"],
                policy,
                revocation["logical_time"],
            ),
        )
        self._conn.commit()

    def settle(self, token: str, request: dict[str, Any]) -> bool:
        """Commit only when the recorded decision, the attempt, and the frozen policy agree.

        ``request`` has no commit flag. A returned True means a row was inserted.
        The observer does not receive this return value.
        """
        self._require(token)
        if "commit_flag" in request or "decision" in request:
            raise BarrierError("settlement does not accept a decision or a commit flag")
        operation_id = request["operation_id"]
        decision = self.stage(operation_id, "decision")
        attempt = self.stage(operation_id, "attempt")
        if decision is None or attempt is None:
            raise BarrierError("settlement requires a decision and an attempt")
        commit_time = int(request["logical_time"])
        if not (int(decision["logical_time"]) < int(attempt["logical_time"]) < commit_time):
            raise BarrierError("decision, attempt, and commit are not in that order")
        policy = self.policy_for(request["run_id"])
        if request.get("policy") != policy:
            raise PolicyError("settlement must use the policy declared for the run")
        if decision["decision"] != "allow":
            return False
        if not self._entitled(decision):
            return False
        if decision["decision"] != static_decision(decision["channel"], decision["subject_class"]):
            return False
        if self._closed_by_revocation(decision, commit_time, policy):
            return False
        self._insert_commit(token, _commit_from_decision(decision, request, commit_time))
        return True

    def commit_outside_local_control(self, token: str, row: dict[str, Any]) -> None:
        """Insert a row on a path the local URL control does not see.

        The row has no decision and no allow flag. The URL gate is not an argument.
        """
        self._require(token)
        if "decision" in row or "commit_flag" in row or "allow" in row:
            raise BarrierError("an ungated commit has no decision flag")
        if row["channel"] == "remote_url":
            raise BarrierError("the URL control is not this path")
        self._insert_commit(token, row)

    def _entitled(self, decision: dict[str, Any]) -> bool:
        grant = self.lookup_grant(decision.get("grant_id"))
        if grant is None:
            return False
        for key in (
            "actor_id",
            "task_id",
            "epoch_id",
            "operation_id",
            "channel",
            "subject_class",
            "object_scope",
            "run_id",
        ):
            if grant[key] != decision[key]:
                return False
        return True

    def _closed_by_revocation(self, decision: dict[str, Any], commit_time: int, policy: str) -> bool:
        grant_id = decision.get("grant_id")
        if not grant_id:
            return False
        rows = self._conn.execute(
            "SELECT logical_time, policy FROM revocations WHERE grant_id = ?",
            (grant_id,),
        ).fetchall()
        in_interval = [
            row
            for row in rows
            if int(decision["logical_time"]) < int(row["logical_time"]) <= commit_time
        ]
        if not in_interval:
            return False
        if any(row["policy"] != policy for row in in_interval):
            raise PolicyError("a revocation carried a policy other than the run policy")
        if policy == "issued_survives_revocation":
            return False
        if policy == "revocation_closes_inflight":
            return True
        raise PolicyError(f"undeclared revocation policy {policy}")

    def _insert_commit(self, token: str, row: dict[str, Any]) -> None:
        self._require(token)
        self._conn.execute(
            "INSERT INTO commits (event_id, operation_id, run_id, history_id, actor_id, "
            "task_id, grant_id, epoch_id, call_id, channel, subject_class, operation, "
            "object_scope, logical_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["event_id"],
                row["operation_id"],
                row["run_id"],
                row["history_id"],
                row["actor_id"],
                row["task_id"],
                row.get("grant_id"),
                row["epoch_id"],
                row["call_id"],
                row["channel"],
                row["subject_class"],
                row["operation"],
                row["object_scope"],
                int(row["logical_time"]),
            ),
        )
        self._conn.commit()


def _commit_from_decision(decision: dict[str, Any], request: dict[str, Any], commit_time: int) -> dict[str, Any]:
    return {
        "event_id": decision["event_id"],
        "operation_id": decision["operation_id"],
        "run_id": decision["run_id"],
        "history_id": decision["history_id"],
        "actor_id": decision["actor_id"],
        "task_id": decision["task_id"],
        "grant_id": decision.get("grant_id"),
        "epoch_id": decision["epoch_id"],
        "call_id": decision["call_id"],
        "channel": decision["channel"],
        "subject_class": decision["subject_class"],
        "operation": decision["operation"],
        "object_scope": decision["object_scope"],
        "logical_time": commit_time,
        "path": request.get("path", "settlement"),
    }
