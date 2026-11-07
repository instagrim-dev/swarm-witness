"""Reference monitor and deliberately defective alternatives.

Policies decide from *local* observations only. They do not read the
authoritative ledger. The mutant arm exercises the same schedules/inputs as
the reference arm.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

from swarm_witness.multi_agent_sim.agents import AgentMailbox
from swarm_witness.multi_agent_sim.events import AgentId

PolicyId = Literal["reference", "mutant_always_allow", "mutant_ignore_spend"]
Decision = Literal["allow", "deny"]


class Policy(Protocol):
    policy_id: PolicyId
    # When True, ledger settlement refuses spent/revoked grants.
    enforce_effect_boundary: bool

    def decide(
        self,
        mailbox: AgentMailbox,
        *,
        agent: AgentId,
        grant_id: str,
        use_foreign_receipt: bool = False,
    ) -> Decision: ...


def _local_classical_decision(
    mailbox: AgentMailbox,
    *,
    agent: AgentId,
    grant_id: str,
    use_foreign_receipt: bool,
) -> Decision | None:
    """Return a decision from local grant evidence, or None if incomplete."""
    observed = mailbox.observed_grant(grant_id)
    if observed is None:
        return None
    if observed["state"] in {"revoked", "spent"}:
        return "deny"
    if agent not in observed.get("assignees", []):
        return "deny"
    if use_foreign_receipt:
        return "deny"
    return "allow"


class ReferencePolicy:
    """Correct classical one-use gate over delivered local observations."""

    policy_id: PolicyId = "reference"
    enforce_effect_boundary: bool = True

    def decide(
        self,
        mailbox: AgentMailbox,
        *,
        agent: AgentId,
        grant_id: str,
        use_foreign_receipt: bool = False,
    ) -> Decision:
        local = _local_classical_decision(
            mailbox,
            agent=agent,
            grant_id=grant_id,
            use_foreign_receipt=use_foreign_receipt,
        )
        # Fail-closed when local evidence is missing.
        return "deny" if local is None else local


class MutantAlwaysAllowPolicy:
    """Defective: allows whenever any grant observation exists (ignores state)."""

    policy_id: PolicyId = "mutant_always_allow"
    # Defective effect boundary: settles even when authoritative state forbids it.
    enforce_effect_boundary: bool = False

    def decide(
        self,
        mailbox: AgentMailbox,
        *,
        agent: AgentId,
        grant_id: str,
        use_foreign_receipt: bool = False,
    ) -> Decision:
        observed = mailbox.observed_grant(grant_id)
        if observed is None:
            return "deny"
        return "allow"


class MutantIgnoreSpendPolicy:
    """Defective: treats spent grants as still claimable by assignees."""

    policy_id: PolicyId = "mutant_ignore_spend"
    # Defective effect boundary: double-commit counterexample requires bypass.
    enforce_effect_boundary: bool = False

    def decide(
        self,
        mailbox: AgentMailbox,
        *,
        agent: AgentId,
        grant_id: str,
        use_foreign_receipt: bool = False,
    ) -> Decision:
        observed = mailbox.observed_grant(grant_id)
        if observed is None:
            return "deny"
        if observed["state"] == "revoked":
            return "deny"
        if agent not in observed.get("assignees", []):
            return "deny"
        if use_foreign_receipt:
            return "deny"
        # Bug: spent is treated as active.
        return "allow"


POLICIES: dict[PolicyId, Policy] = {
    "reference": ReferencePolicy(),
    "mutant_always_allow": MutantAlwaysAllowPolicy(),
    "mutant_ignore_spend": MutantIgnoreSpendPolicy(),
}


def get_policy(policy_id: PolicyId) -> Policy:
    return POLICIES[policy_id]


def local_evidence_complete(mailbox: AgentMailbox, grant_id: str) -> bool:
    return mailbox.observed_grant(grant_id) is not None


def decision_record(
    policy: Policy,
    mailbox: AgentMailbox,
    *,
    agent: AgentId,
    grant_id: str,
    use_foreign_receipt: bool = False,
) -> dict[str, Any]:
    evidence_complete = local_evidence_complete(mailbox, grant_id)
    decision = policy.decide(
        mailbox,
        agent=agent,
        grant_id=grant_id,
        use_foreign_receipt=use_foreign_receipt,
    )
    return {
        "policy_id": policy.policy_id,
        "decision": decision,
        "local_evidence_complete": evidence_complete,
        "observed_grant": mailbox.observed_grant(grant_id),
        "use_foreign_receipt": use_foreign_receipt,
    }
