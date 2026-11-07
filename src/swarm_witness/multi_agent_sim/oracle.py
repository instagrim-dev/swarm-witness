"""Ground-truth oracle over the authoritative ledger.

Oracle predicates are intentionally separate from policy implementations so
expected and actual decisions are never computed from the same code path.
"""

from __future__ import annotations

from typing import Any

from swarm_witness.multi_agent_sim.events import AgentId
from swarm_witness.multi_agent_sim.ledger import AuthoritativeLedger


def authoritative_required_decision(
    ledger: AuthoritativeLedger,
    *,
    agent: AgentId,
    grant_id: str,
    use_foreign_receipt: bool = False,
) -> str:
    """Classical one-use null over authoritative owner state."""
    grant = ledger.grants.get(grant_id)
    if grant is None:
        return "deny"
    if grant["spent"] or grant["state"] in {"revoked", "spent"}:
        return "deny"
    if agent not in grant["assignees"]:
        return "deny"
    if use_foreign_receipt:
        return "deny"
    return "allow"


def oracle_one_use_holds(ledger: AuthoritativeLedger, grant_id: str) -> bool:
    """One-use safety: at most one committed effect per grant."""
    return (
        sum(1 for e in ledger.committed_effects if e["grant_id"] == grant_id) <= 1
    )


def oracle_summary(
    ledger: AuthoritativeLedger,
    *,
    agent: AgentId,
    grant_id: str,
    use_foreign_receipt: bool = False,
) -> dict[str, Any]:
    return {
        "required_decision": authoritative_required_decision(
            ledger,
            agent=agent,
            grant_id=grant_id,
            use_foreign_receipt=use_foreign_receipt,
        ),
        "one_use_holds": oracle_one_use_holds(ledger, grant_id),
        "authoritative_owner_state": ledger.owner_state_projection(grant_id),
    }
