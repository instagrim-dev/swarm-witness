"""Stable run, operation, actor, task, grant, and event identifiers."""

from __future__ import annotations


def logical_iso(logical: int) -> str:
    """Map a logical second onto a fixed UTC timestamp. Replay does not use the clock."""
    if not isinstance(logical, int) or isinstance(logical, bool):
        raise ValueError("logical time must be an int")
    if logical < 0 or logical >= 86400:
        raise ValueError(f"logical time out of range: {logical}")
    hour, rem = divmod(logical, 3600)
    minute, second = divmod(rem, 60)
    return f"2026-04-01T{hour:02d}:{minute:02d}:{second:02d}Z"


def block_base(index: int) -> int:
    return index * 100


def ident(kind: str, slug: str) -> str:
    prefixes = {
        "history": "aew-v1-h",
        "run": "aew-v1-run",
        "task": "aew-v1-task",
        "grant": "aew-v1-grant",
        "epoch": "aew-v1-epoch",
        "actor": "aew-v1-actor",
        "operation": "aew-v1-op",
        "event": "aew-v1-event",
        "call": "aew-v1-call",
        "object": "aew-v1-object",
        "record": "aew-v1-rec",
        "revocation": "aew-v1-revocation",
        "receipt": "aew-v1-receipt",
    }
    if kind not in prefixes:
        raise KeyError(kind)
    return f"{prefixes[kind]}-{slug}"
