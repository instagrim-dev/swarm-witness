"""Classical durable-grant admit barrier (R3 null model).

A durable map of action_id → grant state is checked before admit. Restart
reloads the map. A retained start claim without an active grant is never
permission to relaunch.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClassicalGate:
    grants: dict[str, str] = field(default_factory=dict)  # action_id -> state

    def decide(self, action_id: str, request: str) -> str:
        state = self.grants.get(action_id)
        if request == "relaunch" and state == "retained_start_claim":
            return "deny"
        if request == "execute" and state == "active_grant":
            return "allow"
        if request == "execute" and state == "rejected":
            return "deny"
        return "deny"

    def dump(self) -> dict[str, str]:
        return dict(self.grants)

    @classmethod
    def load(cls, data: dict[str, str]) -> ClassicalGate:
        return cls(grants=dict(data))
