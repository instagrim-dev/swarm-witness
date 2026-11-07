"""Classical decision-model admit gate (R3 null model).

Decision-model only: consults an in-memory grant map keyed by action_id with
explicit ``state`` and ``version``. Matching ``grant_version`` is required for
any allow. This is **not** a durability / fresh-process restart claim —
``dump`` / ``load`` are in-process fixture copies only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClassicalGate:
    """Null-model admit barrier over (state, request, grant_version)."""

    grants: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_grants(cls, grants: dict[str, dict[str, Any]]) -> ClassicalGate:
        normalized: dict[str, dict[str, Any]] = {}
        for action_id, row in grants.items():
            if not isinstance(row, dict):
                raise TypeError(f"grant row for {action_id!r} must be a dict")
            if "state" not in row or "version" not in row:
                raise ValueError(
                    f"grant row for {action_id!r} requires state and version"
                )
            normalized[action_id] = {
                "state": str(row["state"]),
                "version": int(row["version"]),
            }
        return cls(grants=normalized)

    def decide(self, action_id: str, request: str, grant_version: int) -> str:
        row = self.grants.get(action_id)
        if row is None:
            return "deny"
        if int(grant_version) != int(row["version"]):
            return "deny"
        state = row["state"]
        if request == "relaunch" and state == "retained_start_claim":
            return "deny"
        if request == "execute" and state == "active_grant":
            return "allow"
        if request == "execute" and state == "rejected":
            return "deny"
        return "deny"

    def dump(self) -> dict[str, dict[str, Any]]:
        """In-process fixture copy — not restart durability evidence."""
        return {k: dict(v) for k, v in self.grants.items()}

    @classmethod
    def load(cls, data: dict[str, dict[str, Any]]) -> ClassicalGate:
        """Rebuild from dump() output — not fresh-process recovery evidence."""
        return cls.from_grants(data)
