"""Read-only effect observer. It never receives a decision or a commit flag."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

_COMMIT_SQL = """
SELECT event_id, operation_id, run_id, history_id, actor_id, task_id, grant_id,
       epoch_id, call_id, channel, subject_class, operation, object_scope, logical_time
FROM commits
ORDER BY logical_time, event_id
"""
_REVOCATION_SQL = """
SELECT revocation_id, grant_id, run_id, history_id, policy, logical_time
FROM revocations
ORDER BY logical_time, revocation_id
"""


def _connect_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{Path(path).resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    def authorizer(action: int, arg1, arg2, db_name, source) -> int:
        if action in (
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION,
            getattr(sqlite3, "SQLITE_RECURSIVE", 33),
        ):
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    conn.set_authorizer(authorizer)
    return conn


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql).fetchall()]


def read_commits(path: str | Path) -> list[dict[str, Any]]:
    """Committed rows only. Stages and decision payloads are not selected."""
    conn = _connect_ro(Path(path))
    try:
        return _rows(conn, _COMMIT_SQL)
    finally:
        conn.close()


def read_revocations(path: str | Path) -> list[dict[str, Any]]:
    conn = _connect_ro(Path(path))
    try:
        return _rows(conn, _REVOCATION_SQL)
    finally:
        conn.close()


def coverage_for(
    path: str | Path,
    *,
    run_id: str,
    history_id: str,
    operations: list[str],
    interval_start: int,
    interval_end: int,
) -> dict[str, Any]:
    """Count commit rows the observer can see for this run and interval."""
    rows = [
        row
        for row in read_commits(path)
        if row["run_id"] == run_id
        and interval_start <= int(row["logical_time"]) < interval_end
    ]
    return {
        "history_id": history_id,
        "run_id": run_id,
        "operations": list(operations),
        "interval_start": interval_start,
        "interval_end": interval_end,
        "row_count": len(rows),
        "event_ids": [row["event_id"] for row in rows],
    }


def read_commits_cold(path: str | Path) -> list[dict[str, Any]]:
    """Re-open the sink in a new interpreter and read commits."""
    program = (
        "import json, sys\n"
        "from swarm_witness.effect_witness.observer import read_commits\n"
        "json.dump(read_commits(sys.argv[1]), sys.stdout, sort_keys=True)\n"
    )
    env = os.environ.copy()
    src = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-c", program, str(path)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads(proc.stdout)
    if not isinstance(payload, list):
        raise RuntimeError("cold observer did not return a list")
    return payload
