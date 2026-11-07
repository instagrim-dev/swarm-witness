"""Multi-agent / swarm generalization of the three-way conclusion method.

Protocol ``r5-swarm-audit-v1`` evaluates authorization claims across a swarm of
agents (A, B, C) under classical one-use grant rules:

- Concurrent / contended claims on a shared one-use grant
- Delegation chains (A→B→C) requiring per-delegate grant evidence
- Cross-agent receipt misuse
- Missing peer-scoped observations

Each case is classified as ``missing_evidence``, ``failed_enforcement``, or
``supported`` via ``conclusion_classes``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from swarm_witness.conclusion_classes import classify_conclusion

AgentId = Literal["A", "B", "C"]
GrantState = Literal["active", "revoked", "spent"]
GateMode = Literal["correct", "broken_allow"]


SWARM_AGENTS: tuple[AgentId, ...] = ("A", "B", "C")


@dataclass
class SwarmState:
    """In-memory swarm grant and receipt ledger."""

    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    # grant_id -> {owner, state, epoch, spent}
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    # receipt_id -> {agent, grant_id, call_id}
    claims: list[dict[str, Any]] = field(default_factory=list)

    def seed_shared_grant(
        self, grant_id: str, *, owner: AgentId, epoch: str = "epoch-1"
    ) -> None:
        self.grants[grant_id] = {
            "owner": owner,
            "state": "active",
            "epoch": epoch,
            "spent": False,
            "assignees": {owner},
        }

    def assign_delegate(self, grant_id: str, delegate: AgentId) -> None:
        g = self.grants[grant_id]
        g["assignees"] = set(g.get("assignees") or set()) | {delegate}

    def revoke(self, grant_id: str) -> None:
        self.grants[grant_id]["state"] = "revoked"

    def observe_grant(self, grant_id: str) -> dict[str, Any] | None:
        g = self.grants.get(grant_id)
        if g is None:
            return None
        return {
            "grant_id": grant_id,
            "owner": g["owner"],
            "state": "spent" if g["spent"] else g["state"],
            "epoch": g["epoch"],
            "assignees": sorted(g["assignees"]),
        }


def _required_decision(
    *,
    agent: AgentId,
    grant: dict[str, Any] | None,
    use_foreign_receipt: bool,
) -> str:
    """Classical swarm null for a claim attempt."""
    if grant is None:
        return "deny"
    if grant["state"] == "revoked" or grant["state"] == "spent":
        return "deny"
    if agent not in grant["assignees"]:
        return "deny"
    if use_foreign_receipt:
        # Foreign receipt never authorizes without assignee + active grant.
        return "deny"
    return "allow"


def attempt_claim(
    state: SwarmState,
    *,
    agent: AgentId,
    grant_id: str,
    call_id: str,
    observe_grant: bool,
    use_foreign_receipt_from: AgentId | None = None,
    gate_mode: GateMode = "correct",
) -> dict[str, Any]:
    """Attempt a swarm claim and classify the three-way conclusion."""
    observed = state.observe_grant(grant_id) if observe_grant else None
    foreign = use_foreign_receipt_from is not None
    required = _required_decision(
        agent=agent,
        grant=observed,
        use_foreign_receipt=foreign,
    )

    if not observe_grant or observed is None:
        classified = classify_conclusion(
            evidence_complete=False, property_holds=None
        )
        return {
            "agent": agent,
            "grant_id": grant_id,
            "call_id": call_id,
            "observe_grant": observe_grant,
            "observed_grant": observed,
            "foreign_receipt_from": use_foreign_receipt_from,
            "gate_mode": gate_mode,
            "decision": None,
            "required_decision": None,
            "assessment": "unsupported",
            "conclusion_class": classified["conclusion_class"],
            "finding_label": classified["finding_label"],
            "property_holds": None,
            "reason": (
                f"agent {agent} lacks observed grant {grant_id} "
                "(swarm peer activity / foreign receipt is not substitute evidence)"
            ),
        }

    # Gate decision
    if gate_mode == "broken_allow":
        decision = "allow"
    else:
        decision = required

    holds = decision == required
    classified = classify_conclusion(
        evidence_complete=True, property_holds=holds
    )

    if decision == "allow" and holds:
        # Commit one-use spend
        state.grants[grant_id]["spent"] = True
        state.grants[grant_id]["state"] = "spent"
        receipt_id = f"receipt-{call_id}"
        state.receipts[receipt_id] = {
            "agent": agent,
            "grant_id": grant_id,
            "call_id": call_id,
        }
        state.claims.append(
            {"agent": agent, "grant_id": grant_id, "call_id": call_id}
        )

    assessment = (
        "enforcement_failed"
        if not holds
        else ("permission_justified" if decision == "allow" else "permission_refuted")
    )
    return {
        "agent": agent,
        "grant_id": grant_id,
        "call_id": call_id,
        "observe_grant": observe_grant,
        "observed_grant": observed,
        "foreign_receipt_from": use_foreign_receipt_from,
        "gate_mode": gate_mode,
        "decision": decision,
        "required_decision": required,
        "assessment": assessment,
        "conclusion_class": classified["conclusion_class"],
        "finding_label": classified["finding_label"],
        "property_holds": holds,
        "reason": classified["reason"]
        + f"; agent={agent} decision={decision} required={required}",
    }


def run_swarm_protocol_cases() -> list[dict[str, Any]]:
    """Execute the declared multi-agent swarm cases (≥3 agents)."""
    cases: list[dict[str, Any]] = []

    # --- missing_evidence: C acts without observing any grant ---
    st = SwarmState()
    st.seed_shared_grant("grant-shared", owner="A")
    st.assign_delegate("grant-shared", "B")
    st.assign_delegate("grant-shared", "C")
    r = attempt_claim(
        st, agent="C", grant_id="grant-shared", call_id="c-blind", observe_grant=False
    )
    cases.append(
        {
            "case_id": "swarm_missing_peer_observation",
            "name": "Agent C claims without observing swarm grant state",
            "role": "missing_evidence",
            "expected_conclusion_class": "missing_evidence",
            "expected_assessment": "unsupported",
            "agents": ["A", "B", "C"],
            "result": r,
        }
    )

    # --- supported: contended one-use grant; first allow, second deny ---
    st = SwarmState()
    st.seed_shared_grant("grant-contend", owner="A")
    st.assign_delegate("grant-contend", "B")
    st.assign_delegate("grant-contend", "C")
    first = attempt_claim(
        st, agent="A", grant_id="grant-contend", call_id="a1", observe_grant=True
    )
    second = attempt_claim(
        st, agent="B", grant_id="grant-contend", call_id="b1", observe_grant=True
    )
    cases.append(
        {
            "case_id": "swarm_contention_first_claim_supported",
            "name": "Agent A first claim on shared one-use grant",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_justified",
            "agents": ["A", "B", "C"],
            "result": first,
        }
    )
    cases.append(
        {
            "case_id": "swarm_contention_second_deny_supported",
            "name": "Agent B second claim denied after spend",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_refuted",
            "agents": ["A", "B", "C"],
            "result": second,
        }
    )

    # --- failed_enforcement: broken gate allows second claim after spend ---
    st = SwarmState()
    st.seed_shared_grant("grant-broken", owner="A")
    st.assign_delegate("grant-broken", "B")
    st.assign_delegate("grant-broken", "C")
    attempt_claim(
        st, agent="A", grant_id="grant-broken", call_id="a2", observe_grant=True
    )
    broken = attempt_claim(
        st,
        agent="B",
        grant_id="grant-broken",
        call_id="b2",
        observe_grant=True,
        gate_mode="broken_allow",
    )
    cases.append(
        {
            "case_id": "swarm_contention_broken_second_allow",
            "name": "Broken gate allows B after A spent shared grant",
            "role": "failed_enforcement",
            "expected_conclusion_class": "failed_enforcement",
            "expected_assessment": "enforcement_failed",
            "agents": ["A", "B", "C"],
            "result": broken,
        }
    )

    # --- delegation chain A→B→C: each hop needs assignee + active observation ---
    st = SwarmState()
    st.seed_shared_grant("grant-chain", owner="A")
    # B not yet assigned → B missing if we only observe grant without assignee
    st.assign_delegate("grant-chain", "B")
    r_b = attempt_claim(
        st, agent="B", grant_id="grant-chain", call_id="b-chain", observe_grant=True
    )
    cases.append(
        {
            "case_id": "swarm_delegation_b_supported",
            "name": "Delegate B claims after assignment with observed active grant",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_justified",
            "agents": ["A", "B", "C"],
            "result": r_b,
        }
    )

    # Fresh chain for C without assignment → deny (supported enforcement)
    st = SwarmState()
    st.seed_shared_grant("grant-chain2", owner="A")
    st.assign_delegate("grant-chain2", "B")
    # C not assignee
    r_c = attempt_claim(
        st, agent="C", grant_id="grant-chain2", call_id="c-chain", observe_grant=True
    )
    cases.append(
        {
            "case_id": "swarm_delegation_c_not_assignee_deny",
            "name": "Agent C denied: not in grant assignees (A→B only)",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_refuted",
            "agents": ["A", "B", "C"],
            "result": r_c,
        }
    )

    # Full chain A→B→C with C assigned, active → supported allow
    st = SwarmState()
    st.seed_shared_grant("grant-chain3", owner="A")
    st.assign_delegate("grant-chain3", "B")
    st.assign_delegate("grant-chain3", "C")
    r_c_ok = attempt_claim(
        st, agent="C", grant_id="grant-chain3", call_id="c-ok", observe_grant=True
    )
    cases.append(
        {
            "case_id": "swarm_delegation_chain_c_supported",
            "name": "Agent C claims after A→B→C assignment",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_justified",
            "agents": ["A", "B", "C"],
            "result": r_c_ok,
        }
    )

    # --- cross-agent receipt misuse ---
    st = SwarmState()
    st.seed_shared_grant("grant-xfer", owner="A")
    st.assign_delegate("grant-xfer", "B")
    st.assign_delegate("grant-xfer", "C")
    attempt_claim(
        st, agent="A", grant_id="grant-xfer", call_id="a-xfer", observe_grant=True
    )
    # After spend, C tries with foreign receipt pattern + observed spent grant
    misuse = attempt_claim(
        st,
        agent="C",
        grant_id="grant-xfer",
        call_id="c-misuse",
        observe_grant=True,
        use_foreign_receipt_from="A",
    )
    cases.append(
        {
            "case_id": "swarm_cross_agent_receipt_deny_supported",
            "name": "Agent C denied using A's receipt after grant spent",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_refuted",
            "agents": ["A", "B", "C"],
            "result": misuse,
        }
    )

    # Broken: allow C via A's receipt after revoke
    st = SwarmState()
    st.seed_shared_grant("grant-misuse-broken", owner="A")
    st.assign_delegate("grant-misuse-broken", "C")
    st.revoke("grant-misuse-broken")
    broken_misuse = attempt_claim(
        st,
        agent="C",
        grant_id="grant-misuse-broken",
        call_id="c-bad",
        observe_grant=True,
        use_foreign_receipt_from="A",
        gate_mode="broken_allow",
    )
    cases.append(
        {
            "case_id": "swarm_cross_agent_receipt_broken_allow",
            "name": "Broken gate allows C on revoked grant via foreign receipt",
            "role": "failed_enforcement",
            "expected_conclusion_class": "failed_enforcement",
            "expected_assessment": "enforcement_failed",
            "agents": ["A", "B", "C"],
            "result": broken_misuse,
        }
    )

    # --- concurrent three-agent observation missing for swarm-wide claim ---
    st = SwarmState()
    st.seed_shared_grant("grant-swarm", owner="A")
    st.assign_delegate("grant-swarm", "B")
    st.assign_delegate("grant-swarm", "C")
    # "Swarm authorized" claim without observing grant for all peers → missing
    r = attempt_claim(
        st, agent="B", grant_id="grant-swarm", call_id="b-noobs", observe_grant=False
    )
    cases.append(
        {
            "case_id": "swarm_concurrent_missing_observation",
            "name": "Swarm concurrent path: B lacks grant observation",
            "role": "missing_evidence",
            "expected_conclusion_class": "missing_evidence",
            "expected_assessment": "unsupported",
            "agents": ["A", "B", "C"],
            "result": r,
        }
    )

    return cases


def evaluate_swarm_method_success(cases: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    agents_seen: set[str] = set()
    for case in cases:
        agents_seen.update(case.get("agents") or [])
        got = case["result"]["conclusion_class"]
        want = case["expected_conclusion_class"]
        if got != want:
            errors.append(f"{case['case_id']}: class {got!r} want {want!r}")
        if case["result"]["assessment"] != case["expected_assessment"]:
            errors.append(
                f"{case['case_id']}: assessment "
                f"{case['result']['assessment']!r} want {case['expected_assessment']!r}"
            )

    if agents_seen != {"A", "B", "C"}:
        errors.append(f"swarm must involve agents A,B,C; saw {sorted(agents_seen)}")

    classes = {c["result"]["conclusion_class"] for c in cases}
    three_way = classes == {
        "missing_evidence",
        "failed_enforcement",
        "supported",
    }
    if not three_way:
        errors.append(f"did not exercise all three classes: {sorted(classes)}")

    roles = {c["role"] for c in cases}
    for need in ("missing_evidence", "failed_enforcement", "supported"):
        if need not in roles and need not in {c["role"] for c in cases}:
            pass  # roles use those names already

    return {
        "passed": not errors,
        "errors": errors,
        "case_count": len(cases),
        "agent_count": len(agents_seen),
        "agents": sorted(agents_seen),
        "three_way_classes_exercised": three_way,
        "missing_evidence_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "missing_evidence"
        ),
        "failed_enforcement_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "failed_enforcement"
        ),
        "supported_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "supported"
        ),
        "all_checks_pass": not errors,
    }
