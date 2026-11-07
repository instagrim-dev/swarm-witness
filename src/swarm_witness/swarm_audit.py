"""Multi-principal generalization of the three-way conclusion method.

Protocol ``r5-swarm-audit-v1`` evaluates authorization claims across named
principals A, B, and C under classical one-use shared-grant rules in an
in-memory sequential model (not separately scheduled concurrent workers):

- Sequential shared-grant contention (first spend wins; later claims deny)
- Direct assignee checks and sequential A→B then B→C assignment hops
- Cross-agent receipt misuse with ledger-bound receipt identities
- Missing peer-scoped observations

Broken gates may return an incorrect **decision** without committing an
unauthorized **effect**. Each case is classified as ``missing_evidence``,
``failed_enforcement``, or ``supported`` via ``conclusion_classes``.
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
    """In-memory multi-principal grant and receipt ledger (sequential model)."""

    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    claims: list[dict[str, Any]] = field(default_factory=list)
    delegation_hops: list[dict[str, Any]] = field(default_factory=list)

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

    def assign_delegate(
        self, grant_id: str, *, by: AgentId, delegate: AgentId
    ) -> None:
        """Record a sequential assignment hop. ``by`` must already be assignee."""
        g = self.grants[grant_id]
        assignees = set(g.get("assignees") or set())
        if by not in assignees:
            raise ValueError(f"{by} cannot assign on {grant_id}: not an assignee")
        assignees.add(delegate)
        g["assignees"] = assignees
        self.delegation_hops.append(
            {"grant_id": grant_id, "by": by, "delegate": delegate}
        )

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

    def receipt_for_agent(
        self, agent: AgentId, *, grant_id: str | None = None
    ) -> dict[str, Any] | None:
        for receipt_id, row in self.receipts.items():
            if row["agent"] != agent:
                continue
            if grant_id is not None and row["grant_id"] != grant_id:
                continue
            return {"receipt_id": receipt_id, **row}
        return None


def _required_decision(
    *,
    agent: AgentId,
    grant: dict[str, Any] | None,
    foreign_receipt: dict[str, Any] | None,
) -> str:
    """Classical null for a claim attempt under observed grant + receipt binding."""
    if grant is None:
        return "deny"
    if grant["state"] in {"revoked", "spent"}:
        return "deny"
    if agent not in grant["assignees"]:
        return "deny"
    if foreign_receipt is not None:
        # Presenting another agent's retained receipt never authorizes.
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
    """Attempt a multi-principal claim and classify the three-way conclusion."""
    observed = state.observe_grant(grant_id) if observe_grant else None
    foreign_receipt: dict[str, Any] | None = None
    receipt_binding_error: str | None = None
    if use_foreign_receipt_from is not None:
        foreign_receipt = state.receipt_for_agent(
            use_foreign_receipt_from, grant_id=grant_id
        )
        if foreign_receipt is None:
            # Flag requested a foreign receipt that is not on the ledger for
            # this grant — evidence incomplete for that misuse path.
            receipt_binding_error = (
                f"no retained receipt for agent {use_foreign_receipt_from} "
                f"on grant {grant_id}"
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
            "presented_receipt": foreign_receipt,
            "receipt_binding_error": receipt_binding_error,
            "gate_mode": gate_mode,
            "decision": None,
            "required_decision": None,
            "effect_committed": False,
            "assessment": "unsupported",
            "conclusion_class": classified["conclusion_class"],
            "finding_label": classified["finding_label"],
            "property_holds": None,
            "reason": (
                f"agent {agent} lacks observed grant {grant_id} "
                "(peer activity / foreign receipt is not substitute evidence)"
            ),
        }

    if use_foreign_receipt_from is not None and foreign_receipt is None:
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
            "presented_receipt": None,
            "receipt_binding_error": receipt_binding_error,
            "gate_mode": gate_mode,
            "decision": None,
            "required_decision": None,
            "effect_committed": False,
            "assessment": "unsupported",
            "conclusion_class": classified["conclusion_class"],
            "finding_label": classified["finding_label"],
            "property_holds": None,
            "reason": (
                "foreign-receipt misuse path requested but no ledger-bound "
                f"receipt for {use_foreign_receipt_from} on {grant_id} — "
                "missing_evidence"
            ),
        }

    required = _required_decision(
        agent=agent,
        grant=observed,
        foreign_receipt=foreign_receipt,
    )

    if gate_mode == "broken_allow":
        decision = "allow"
    else:
        decision = required

    holds = decision == required
    classified = classify_conclusion(
        evidence_complete=True, property_holds=holds
    )

    effect_committed = False
    # Only commit effects when the decision is both allow and correct.
    # Broken allows record the wrong decision without unauthorized spend.
    if decision == "allow" and holds:
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
        effect_committed = True

    assessment = (
        "enforcement_failed"
        if not holds
        else ("permission_justified" if decision == "allow" else "permission_refuted")
    )
    reason = classified["reason"] + (
        f"; agent={agent} decision={decision} required={required} "
        f"effect_committed={effect_committed}"
    )
    if foreign_receipt is not None:
        reason += f"; presented_receipt={foreign_receipt['receipt_id']}"
    return {
        "agent": agent,
        "grant_id": grant_id,
        "call_id": call_id,
        "observe_grant": observe_grant,
        "observed_grant": observed,
        "foreign_receipt_from": use_foreign_receipt_from,
        "presented_receipt": foreign_receipt,
        "receipt_binding_error": receipt_binding_error,
        "gate_mode": gate_mode,
        "decision": decision,
        "required_decision": required,
        "effect_committed": effect_committed,
        "assessment": assessment,
        "conclusion_class": classified["conclusion_class"],
        "finding_label": classified["finding_label"],
        "property_holds": holds,
        "reason": reason,
    }


def run_swarm_protocol_cases() -> list[dict[str, Any]]:
    """Execute declared multi-principal cases (≥3 agents, sequential model)."""
    cases: list[dict[str, Any]] = []

    # --- missing_evidence: C acts without observing any grant ---
    st = SwarmState()
    st.seed_shared_grant("grant-shared", owner="A")
    st.assign_delegate("grant-shared", by="A", delegate="B")
    st.assign_delegate("grant-shared", by="B", delegate="C")
    r = attempt_claim(
        st, agent="C", grant_id="grant-shared", call_id="c-blind", observe_grant=False
    )
    cases.append(
        {
            "case_id": "swarm_missing_peer_observation",
            "name": "Agent C claims without observing shared grant state",
            "role": "missing_evidence",
            "expected_conclusion_class": "missing_evidence",
            "expected_assessment": "unsupported",
            "agents": ["A", "B", "C"],
            "result": r,
        }
    )

    # --- supported: sequential contended one-use grant ---
    st = SwarmState()
    st.seed_shared_grant("grant-contend", owner="A")
    st.assign_delegate("grant-contend", by="A", delegate="B")
    st.assign_delegate("grant-contend", by="B", delegate="C")
    first = attempt_claim(
        st, agent="A", grant_id="grant-contend", call_id="a1", observe_grant=True
    )
    second = attempt_claim(
        st, agent="B", grant_id="grant-contend", call_id="b1", observe_grant=True
    )
    cases.append(
        {
            "case_id": "swarm_contention_first_claim_supported",
            "name": "Agent A first sequential claim on shared one-use grant",
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
            "name": "Agent B second sequential claim denied after spend",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_refuted",
            "agents": ["A", "B", "C"],
            "result": second,
        }
    )
    assert first["effect_committed"] is True
    assert second["effect_committed"] is False

    # --- failed_enforcement: wrong decision, no unauthorized effect ---
    st = SwarmState()
    st.seed_shared_grant("grant-broken", owner="A")
    st.assign_delegate("grant-broken", by="A", delegate="B")
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
            "name": "Broken gate decides allow for B after A spent (no effect commit)",
            "role": "failed_enforcement",
            "expected_conclusion_class": "failed_enforcement",
            "expected_assessment": "enforcement_failed",
            "agents": ["A", "B", "C"],
            "result": broken,
        }
    )
    assert broken["decision"] == "allow"
    assert broken["effect_committed"] is False
    assert st.grants["grant-broken"]["spent"] is True  # only A's spend

    # --- sequential assignment hops A→B then B→C ---
    st = SwarmState()
    st.seed_shared_grant("grant-chain", owner="A")
    st.assign_delegate("grant-chain", by="A", delegate="B")
    r_b = attempt_claim(
        st, agent="B", grant_id="grant-chain", call_id="b-chain", observe_grant=True
    )
    cases.append(
        {
            "case_id": "swarm_delegation_b_supported",
            "name": "Delegate B claims after A→B assignment hop",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_justified",
            "agents": ["A", "B", "C"],
            "result": r_b,
        }
    )

    st = SwarmState()
    st.seed_shared_grant("grant-chain2", owner="A")
    st.assign_delegate("grant-chain2", by="A", delegate="B")
    # C not assignee (only A→B hop)
    r_c = attempt_claim(
        st, agent="C", grant_id="grant-chain2", call_id="c-chain", observe_grant=True
    )
    cases.append(
        {
            "case_id": "swarm_delegation_c_not_assignee_deny",
            "name": "Agent C denied: not assignee after A→B hop only",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_refuted",
            "agents": ["A", "B", "C"],
            "result": r_c,
        }
    )

    st = SwarmState()
    st.seed_shared_grant("grant-chain3", owner="A")
    st.assign_delegate("grant-chain3", by="A", delegate="B")
    st.assign_delegate("grant-chain3", by="B", delegate="C")  # B→C hop
    r_c_ok = attempt_claim(
        st, agent="C", grant_id="grant-chain3", call_id="c-ok", observe_grant=True
    )
    cases.append(
        {
            "case_id": "swarm_delegation_chain_c_supported",
            "name": "Agent C claims after sequential A→B then B→C hops",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_justified",
            "agents": ["A", "B", "C"],
            "result": r_c_ok,
        }
    )
    assert len(st.delegation_hops) == 2

    # --- cross-agent receipt misuse with ledger-bound receipt ---
    st = SwarmState()
    st.seed_shared_grant("grant-xfer", owner="A")
    st.assign_delegate("grant-xfer", by="A", delegate="B")
    st.assign_delegate("grant-xfer", by="B", delegate="C")
    attempt_claim(
        st, agent="A", grant_id="grant-xfer", call_id="a-xfer", observe_grant=True
    )
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
            "name": "Agent C denied presenting A's ledger receipt after spend",
            "role": "supported",
            "expected_conclusion_class": "supported",
            "expected_assessment": "permission_refuted",
            "agents": ["A", "B", "C"],
            "result": misuse,
        }
    )
    assert misuse["presented_receipt"] is not None
    assert misuse["presented_receipt"]["receipt_id"] == "receipt-a-xfer"
    assert misuse["effect_committed"] is False

    # Seed a retained receipt, then revoke, then broken allow via that receipt.
    st = SwarmState()
    st.seed_shared_grant("grant-misuse-broken", owner="A")
    st.assign_delegate("grant-misuse-broken", by="A", delegate="C")
    # Issue a receipt for A without spending via direct ledger write so the
    # foreign receipt exists while grant can still be revoked.
    st.receipts["receipt-a-prior"] = {
        "agent": "A",
        "grant_id": "grant-misuse-broken",
        "call_id": "a-prior",
    }
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
            "name": "Broken gate decides allow for C via A's receipt (no effect)",
            "role": "failed_enforcement",
            "expected_conclusion_class": "failed_enforcement",
            "expected_assessment": "enforcement_failed",
            "agents": ["A", "B", "C"],
            "result": broken_misuse,
        }
    )
    assert broken_misuse["presented_receipt"]["receipt_id"] == "receipt-a-prior"
    assert broken_misuse["decision"] == "allow"
    assert broken_misuse["effect_committed"] is False
    assert st.grants["grant-misuse-broken"]["spent"] is False

    # --- missing observation on shared-grant path ---
    st = SwarmState()
    st.seed_shared_grant("grant-swarm", owner="A")
    st.assign_delegate("grant-swarm", by="A", delegate="B")
    st.assign_delegate("grant-swarm", by="B", delegate="C")
    r = attempt_claim(
        st, agent="B", grant_id="grant-swarm", call_id="b-noobs", observe_grant=False
    )
    cases.append(
        {
            "case_id": "swarm_concurrent_missing_observation",
            "name": "Shared-grant path: B lacks grant observation",
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
        # Wrong decisions must not commit unauthorized effects.
        if (
            case["result"].get("decision") == "allow"
            and case["result"].get("property_holds") is False
            and case["result"].get("effect_committed")
        ):
            errors.append(
                f"{case['case_id']}: failed_enforcement committed unauthorized effect"
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

    # Receipt-misuse cases must present a ledger-bound receipt id.
    for cid in (
        "swarm_cross_agent_receipt_deny_supported",
        "swarm_cross_agent_receipt_broken_allow",
    ):
        row = next(c for c in cases if c["case_id"] == cid)
        presented = row["result"].get("presented_receipt")
        if not presented or not presented.get("receipt_id"):
            errors.append(f"{cid}: missing ledger-bound presented_receipt")

    return {
        "passed": not errors,
        "errors": errors,
        "case_count": len(cases),
        "agent_count": len(agents_seen),
        "agents": sorted(agents_seen),
        "model": "sequential_shared_grant_multi_principal",
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
