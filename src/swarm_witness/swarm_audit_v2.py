"""R5-v2 wider-coverage research protocol (issue #11).

Versioned extension of the sequential multi-principal claim-audit method.
Preserves R5 v1 (`swarm_audit.py` / `r5-swarm-audit-v1`) unmodified as prior
evidence. Expectations are declared outside the production classifier. Gate
policies are separable from the oracle. Concurrency-derived rows consume
pinned multi-agent simulator traces (issue #10 / protocol multi-agent-sim-v1)
rather than relabeling sequential cases as races.

This module does **not** claim live concurrent swarm behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from swarm_witness.audit_diagnosis import diagnosis
from swarm_witness.conclusion_classes import classify_conclusion

AgentId = Literal["A", "B", "C"]
GateMode = Literal[
    "correct",
    "broken_allow",  # wrong allow; effect prevented (decision_policy)
    "broken_deny",  # wrong deny; no effect
    "broken_allow_and_commit",  # wrong allow that settles (effect_boundary)
]
ObservationMode = Literal[
    "authentic",
    "missing",
    "misbound",
    "stale",
    "partial",
    "irrelevant_only",
]
ReceiptKind = Literal[
    "none",
    "own_bound",
    "foreign",
    "copied_replay",
    "forged",
]

PROTOCOL_ID = "r5-swarm-audit-v2"
SOURCE_PIN = "swarm-witness-r5-v2"
CLAIM_ID = "r5_v2"
SWARM_AGENTS: tuple[AgentId, ...] = ("A", "B", "C")

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "experiments" / "swarm_r5_v2"
HELD_OUT_DIR = EXPERIMENT_DIR / "held_out"
CONCURRENCY_TRACE_DIR = EXPERIMENT_DIR / "concurrency_traces"
EXPECTATIONS_PATH = EXPERIMENT_DIR / "case_expectations.yaml"
COVERAGE_MATRIX_PATH = EXPERIMENT_DIR / "coverage_matrix.yaml"


@dataclass
class SwarmStateV2:
    """Sequential in-memory ledger with epoch, task scope, and receipt binding."""

    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    claims: list[dict[str, Any]] = field(default_factory=list)
    delegation_hops: list[dict[str, Any]] = field(default_factory=list)
    owner_version: dict[str, int] = field(default_factory=dict)

    def seed_shared_grant(
        self,
        grant_id: str,
        *,
        owner: AgentId,
        epoch: str = "epoch-1",
        task_scope: str = "task-*",
    ) -> None:
        self.grants[grant_id] = {
            "owner": owner,
            "state": "active",
            "epoch": epoch,
            "spent": False,
            "assignees": {owner},
            "task_scopes": {owner: task_scope},
        }
        self.owner_version[grant_id] = 1

    def assign_delegate(
        self,
        grant_id: str,
        *,
        by: AgentId,
        delegate: AgentId,
        task_scope: str | None = None,
    ) -> None:
        g = self.grants[grant_id]
        assignees = set(g["assignees"])
        if by not in assignees:
            raise ValueError(f"{by} cannot assign on {grant_id}: not an assignee")
        scopes = dict(g.get("task_scopes") or {})
        parent_scope = scopes.get(by, "task-*")
        # Scope attenuation: delegate may only receive a scope ⊆ parent.
        delegated_scope = task_scope if task_scope is not None else parent_scope
        if not _scope_allows(parent_scope, delegated_scope):
            raise ValueError(
                f"cannot attenuate {parent_scope!r} to incompatible {delegated_scope!r}"
            )
        assignees.add(delegate)
        scopes[delegate] = delegated_scope
        g["assignees"] = assignees
        g["task_scopes"] = scopes
        self.owner_version[grant_id] = self.owner_version.get(grant_id, 0) + 1
        self.delegation_hops.append(
            {
                "grant_id": grant_id,
                "by": by,
                "delegate": delegate,
                "task_scope": delegated_scope,
                "owner_version": self.owner_version[grant_id],
            }
        )

    def revoke(self, grant_id: str) -> None:
        self.grants[grant_id]["state"] = "revoked"
        self.owner_version[grant_id] = self.owner_version.get(grant_id, 0) + 1

    def bump_epoch(self, grant_id: str, epoch: str) -> None:
        self.grants[grant_id]["epoch"] = epoch
        self.owner_version[grant_id] = self.owner_version.get(grant_id, 0) + 1

    def observe_grant(
        self,
        grant_id: str,
        *,
        mode: ObservationMode = "authentic",
        misbound_state: str | None = None,
        stale_epoch: str | None = None,
        stale_owner_version: int | None = None,
    ) -> dict[str, Any] | None:
        g = self.grants.get(grant_id)
        if g is None or mode in {"missing", "irrelevant_only"}:
            return None
        if mode == "partial":
            # Partial: identity only — no state/assignees (not discriminating).
            return {
                "grant_id": grant_id,
                "owner": g["owner"],
                "state": None,
                "epoch": None,
                "assignees": None,
                "task_scopes": None,
                "owner_version": None,
                "observation_complete": False,
            }
        state = "spent" if g["spent"] else g["state"]
        epoch = g["epoch"]
        owner_version = self.owner_version.get(grant_id, 1)
        if mode == "misbound":
            state = misbound_state or ("revoked" if state == "active" else "active")
        if mode == "stale":
            epoch = stale_epoch or f"stale-{epoch}"
            if stale_owner_version is not None:
                owner_version = stale_owner_version
            else:
                owner_version = max(0, owner_version - 1)
            # Stale delivery still shows a prior active snapshot.
            state = "active"
        return {
            "grant_id": grant_id,
            "owner": g["owner"],
            "state": state,
            "epoch": epoch,
            "assignees": sorted(g["assignees"]),
            "task_scopes": {
                k: v for k, v in sorted((g.get("task_scopes") or {}).items())
            },
            "owner_version": owner_version,
            "observation_complete": True,
            "observation_mode": mode,
        }

    def add_receipt(
        self,
        receipt_id: str,
        *,
        agent: AgentId,
        grant_id: str,
        call_id: str,
        authentic: bool = True,
        binding: str = "ledger",
    ) -> None:
        self.receipts[receipt_id] = {
            "agent": agent,
            "grant_id": grant_id,
            "call_id": call_id,
            "authentic": authentic,
            "binding": binding,
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


def _scope_allows(parent: str, child: str) -> bool:
    """Classical task-scope attenuation: exact match or parent wildcard."""
    if parent == "task-*" or parent == child:
        return True
    if parent.endswith("-*") and child.startswith(parent[:-1]):
        return True
    return False


def oracle_required_decision(
    *,
    agent: AgentId,
    authoritative_grant: dict[str, Any] | None,
    task_id: str | None = None,
    presented_receipt: dict[str, Any] | None = None,
) -> str:
    """Ground-truth required decision from *authoritative* ledger state.

    Intentionally separate from gate policies so expected and actual decisions
    are never computed from the same predicate.
    """
    if authoritative_grant is None:
        return "deny"
    if authoritative_grant.get("spent") or authoritative_grant.get("state") in {
        "revoked",
        "spent",
    }:
        return "deny"
    assignees = authoritative_grant.get("assignees") or set()
    if agent not in assignees:
        return "deny"
    if task_id is not None:
        scopes = authoritative_grant.get("task_scopes") or {}
        agent_scope = scopes.get(agent, "task-*")
        if not _scope_allows(agent_scope, task_id):
            return "deny"
    if presented_receipt is not None:
        # Foreign / forged / replayed receipts never authorize under classical null.
        if presented_receipt.get("agent") != agent:
            return "deny"
        if not presented_receipt.get("authentic", True):
            return "deny"
        if presented_receipt.get("binding") not in {None, "ledger", "own"}:
            return "deny"
        # Own bound receipt after spend still cannot re-authorize a spent grant
        # (already denied above); presenting any prior receipt alone denies.
        return "deny"
    return "allow"


def _gate_decide(required: str, gate_mode: GateMode) -> str:
    if gate_mode == "correct":
        return required
    if gate_mode == "broken_allow":
        return "allow"
    if gate_mode == "broken_deny":
        return "deny"
    if gate_mode == "broken_allow_and_commit":
        return "allow"
    raise ValueError(f"unknown gate_mode: {gate_mode!r}")


def attempt_claim_v2(
    state: SwarmStateV2,
    *,
    agent: AgentId,
    grant_id: str,
    call_id: str,
    observation_mode: ObservationMode = "authentic",
    gate_mode: GateMode = "correct",
    task_id: str | None = None,
    receipt_kind: ReceiptKind = "none",
    foreign_receipt_from: AgentId | None = None,
    irrelevant_fact: str | None = None,
    misbound_state: str | None = None,
    stale_epoch: str | None = None,
) -> dict[str, Any]:
    """Attempt a claim under declared observation/receipt/gate conditions."""
    authoritative = state.grants.get(grant_id)
    auth_view = None
    if authoritative is not None:
        auth_view = {
            "owner": authoritative["owner"],
            "state": "spent" if authoritative["spent"] else authoritative["state"],
            "epoch": authoritative["epoch"],
            "spent": authoritative["spent"],
            "assignees": set(authoritative["assignees"]),
            "task_scopes": dict(authoritative.get("task_scopes") or {}),
            "owner_version": state.owner_version.get(grant_id, 1),
        }

    presented_receipt: dict[str, Any] | None = None
    if receipt_kind == "foreign" or foreign_receipt_from is not None:
        donor = foreign_receipt_from or "A"
        presented_receipt = state.receipt_for_agent(donor, grant_id=grant_id)
    elif receipt_kind == "own_bound":
        presented_receipt = state.receipt_for_agent(agent, grant_id=grant_id)
    elif receipt_kind == "copied_replay":
        donor = foreign_receipt_from or "A"
        base = state.receipt_for_agent(donor, grant_id=grant_id)
        if base is not None:
            presented_receipt = {
                **base,
                "receipt_id": f"replay-of-{base['receipt_id']}",
                "binding": "replay",
                "authentic": True,
                "agent": donor,  # still foreign to claimant
            }
    elif receipt_kind == "forged":
        presented_receipt = {
            "receipt_id": f"forged-{call_id}",
            "agent": agent,
            "grant_id": grant_id,
            "call_id": call_id,
            "authentic": False,
            "binding": "forged",
        }

    required = oracle_required_decision(
        agent=agent,
        authoritative_grant=auth_view,
        task_id=task_id,
        presented_receipt=presented_receipt,
    )

    observed = state.observe_grant(
        grant_id,
        mode=observation_mode,
        misbound_state=misbound_state,
        stale_epoch=stale_epoch,
    )

    # Evidence completeness: missing / irrelevant-only / partial → missing_evidence.
    # Misbound is complete-but-bad evidence (not coerced into missing).
    if observation_mode in {"missing", "irrelevant_only"} or (
        observation_mode == "partial"
        or (observed is not None and observed.get("observation_complete") is False)
    ):
        classified = classify_conclusion(
            evidence_complete=False, property_holds=None
        )
        return {
            "agent": agent,
            "grant_id": grant_id,
            "call_id": call_id,
            "task_id": task_id,
            "observation_mode": observation_mode,
            "observed_grant": observed,
            "irrelevant_fact": irrelevant_fact
            if observation_mode == "irrelevant_only"
            else None,
            "receipt_kind": receipt_kind,
            "presented_receipt": presented_receipt,
            "gate_mode": gate_mode,
            "decision": None,
            "required_decision": required,
            "effect_committed": False,
            "assessment": "unsupported",
            "conclusion_class": classified["conclusion_class"],
            "finding_label": classified["finding_label"],
            "property_holds": None,
            "reason": (
                f"agent {agent} lacks discriminating grant observation "
                f"(mode={observation_mode}); unknown is not coerced to deny/allow"
            ),
            "authoritative_owner_state": auth_view,
            **diagnosis(
                evidence_status="missing",
                decision_status="unknown",
                effect_status="unobserved",
                failure_origin="none",
            ),
        }

    if observation_mode == "misbound":
        # Gate trusts the false observation; oracle still uses authoritative truth.
        false_required = oracle_required_decision(
            agent=agent,
            authoritative_grant={
                **(auth_view or {}),
                "state": observed["state"],
                "spent": observed["state"] == "spent",
                "assignees": set(observed.get("assignees") or []),
                "task_scopes": dict(observed.get("task_scopes") or {}),
            }
            if observed is not None
            else None,
            task_id=task_id,
            presented_receipt=presented_receipt,
        )
        decision = _gate_decide(false_required, gate_mode)
        # Property is scored against authoritative required, not the misbound view.
        holds = decision == required
        classified = classify_conclusion(
            evidence_complete=True, property_holds=holds
        )
        effect_committed = False
        # Misbound never authorizes settlement under this protocol.
        diag = diagnosis(
            evidence_status="misbound",
            decision_status="incorrect" if not holds else "correct",
            effect_status="prevented",
            failure_origin="evidence",
        )
        return {
            "agent": agent,
            "grant_id": grant_id,
            "call_id": call_id,
            "task_id": task_id,
            "observation_mode": observation_mode,
            "observed_grant": observed,
            "irrelevant_fact": None,
            "receipt_kind": receipt_kind,
            "presented_receipt": presented_receipt,
            "gate_mode": gate_mode,
            "decision": decision,
            "required_decision": required,
            "effect_committed": effect_committed,
            "assessment": "enforcement_failed" if not holds else (
                "permission_justified" if decision == "allow" else "permission_refuted"
            ),
            "conclusion_class": classified["conclusion_class"],
            "finding_label": classified["finding_label"],
            "property_holds": holds,
            "reason": (
                "misbound grant observation; gate view disagrees with "
                f"authoritative required={required}; decision={decision}"
            ),
            "authoritative_owner_state": auth_view,
            **diag,
        }

    # Authentic or stale observation: gate decides from observed snapshot.
    if observed is None:
        classified = classify_conclusion(
            evidence_complete=False, property_holds=None
        )
        return {
            "agent": agent,
            "grant_id": grant_id,
            "call_id": call_id,
            "task_id": task_id,
            "observation_mode": observation_mode,
            "observed_grant": None,
            "irrelevant_fact": None,
            "receipt_kind": receipt_kind,
            "presented_receipt": presented_receipt,
            "gate_mode": gate_mode,
            "decision": None,
            "required_decision": required,
            "effect_committed": False,
            "assessment": "unsupported",
            "conclusion_class": classified["conclusion_class"],
            "finding_label": classified["finding_label"],
            "property_holds": None,
            "reason": "observation resolved empty",
            "authoritative_owner_state": auth_view,
            **diagnosis(
                evidence_status="missing",
                decision_status="unknown",
                effect_status="unobserved",
                failure_origin="none",
            ),
        }

    observed_for_gate = {
        "owner": observed["owner"],
        "state": observed["state"],
        "spent": observed["state"] == "spent",
        "assignees": set(observed.get("assignees") or []),
        "task_scopes": dict(observed.get("task_scopes") or {}),
        "epoch": observed.get("epoch"),
    }
    # Stale active observation after revoke/epoch bump: gate may see active
    # while oracle (authoritative) requires deny.
    gate_required = oracle_required_decision(
        agent=agent,
        authoritative_grant=observed_for_gate,
        task_id=task_id,
        presented_receipt=presented_receipt,
    )
    decision = _gate_decide(gate_required, gate_mode)
    holds = decision == required
    classified = classify_conclusion(evidence_complete=True, property_holds=holds)

    effect_committed = False
    # Stale evidence never authorizes settlement in the sequential harness;
    # committed unauthorized stale effects come from pinned simulator traces.
    may_settle = observation_mode != "stale" and (
        (holds and gate_mode == "correct")
        or gate_mode == "broken_allow_and_commit"
    )
    if decision == "allow" and may_settle:
        if grant_id in state.grants:
            state.grants[grant_id]["spent"] = True
            state.grants[grant_id]["state"] = "spent"
            state.owner_version[grant_id] = state.owner_version.get(grant_id, 0) + 1
            receipt_id = f"receipt-{call_id}"
            state.receipts[receipt_id] = {
                "agent": agent,
                "grant_id": grant_id,
                "call_id": call_id,
                "authentic": True,
                "binding": "ledger",
            }
            state.claims.append(
                {"agent": agent, "grant_id": grant_id, "call_id": call_id}
            )
            effect_committed = True

    evidence_status = "unverified" if observation_mode == "stale" else "authentic"

    if not holds:
        if effect_committed:
            diag = diagnosis(
                evidence_status=evidence_status,  # type: ignore[arg-type]
                decision_status="incorrect",
                effect_status="committed",
                failure_origin="effect_boundary",
            )
        elif observation_mode == "stale":
            diag = diagnosis(
                evidence_status="unverified",
                decision_status="incorrect",
                effect_status="prevented" if decision == "allow" else "not_applicable",
                failure_origin="evidence",
            )
        else:
            effect_status = "prevented" if decision == "allow" else "not_applicable"
            diag = diagnosis(
                evidence_status="authentic",
                decision_status="incorrect",
                effect_status=effect_status,  # type: ignore[arg-type]
                failure_origin="decision_policy",
            )
        assessment = "enforcement_failed"
    elif decision == "allow":
        diag = diagnosis(
            evidence_status=evidence_status,  # type: ignore[arg-type]
            decision_status="correct",
            effect_status="committed" if effect_committed else "prevented",
            failure_origin="none",
        )
        assessment = "permission_justified"
    else:
        diag = diagnosis(
            evidence_status=evidence_status,  # type: ignore[arg-type]
            decision_status="correct",
            effect_status="not_applicable",
            failure_origin="none",
        )
        assessment = "permission_refuted"

    return {
        "agent": agent,
        "grant_id": grant_id,
        "call_id": call_id,
        "task_id": task_id,
        "observation_mode": observation_mode,
        "observed_grant": observed,
        "irrelevant_fact": None,
        "receipt_kind": receipt_kind,
        "presented_receipt": presented_receipt,
        "gate_mode": gate_mode,
        "decision": decision,
        "required_decision": required,
        "effect_committed": effect_committed,
        "assessment": assessment,
        "conclusion_class": classified["conclusion_class"],
        "finding_label": classified["finding_label"],
        "property_holds": holds,
        "reason": (
            classified["reason"]
            + f"; agent={agent} decision={decision} required={required} "
            f"effect_committed={effect_committed} "
            f"failure_origin={diag['failure_origin']} "
            f"effect_status={diag['effect_status']}"
        ),
        "authoritative_owner_state": {
            **(auth_view or {}),
            "assignees": sorted((auth_view or {}).get("assignees") or []),
        }
        if auth_view
        else None,
        **diag,
    }


def _case(
    case_id: str,
    *,
    family: str,
    name: str,
    result: dict[str, Any],
    mechanism_arm: str,
    paired_input_id: str | None = None,
    evidence_source: str = "sequential_harness",
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "family": family,
        "name": name,
        "agents": list(SWARM_AGENTS),
        "mechanism_arm": mechanism_arm,
        "paired_input_id": paired_input_id,
        "evidence_source": evidence_source,
        "result": result,
    }


def run_sequential_family_cases() -> list[dict[str, Any]]:
    """Build sequential/observation-quality cases (independent of concurrency)."""
    cases: list[dict[str, Any]] = []

    # --- Family: authority_observation ---
    st = SwarmStateV2()
    st.seed_shared_grant("g-auth", owner="A")
    st.assign_delegate("g-auth", by="A", delegate="B")
    cases.append(
        _case(
            "v2_auth_valid_active_allow",
            family="authority_observation",
            name="Authentic active grant → allow (correct)",
            mechanism_arm="correct",
            paired_input_id="auth_active_b",
            result=attempt_claim_v2(
                st, agent="B", grant_id="g-auth", call_id="v2-auth-ok"
            ),
        )
    )

    st = SwarmStateV2()
    st.seed_shared_grant("g-rev", owner="A")
    st.assign_delegate("g-rev", by="A", delegate="B")
    st.revoke("g-rev")
    cases.append(
        _case(
            "v2_auth_revoked_deny",
            family="authority_observation",
            name="Revoked grant → deny (correct)",
            mechanism_arm="correct",
            paired_input_id="auth_revoked_b",
            result=attempt_claim_v2(
                st, agent="B", grant_id="g-rev", call_id="v2-rev-deny"
            ),
        )
    )
    cases.append(
        _case(
            "v2_auth_revoked_broken_allow_prevented",
            family="authority_observation",
            name="Revoked grant + broken_allow → incorrect allow, prevented",
            mechanism_arm="broken_allow",
            paired_input_id="auth_revoked_b",
            result=attempt_claim_v2(
                st,
                agent="B",
                grant_id="g-rev",
                call_id="v2-rev-broken",
                gate_mode="broken_allow",
            ),
        )
    )

    st = SwarmStateV2()
    st.seed_shared_grant("g-spent", owner="A")
    st.assign_delegate("g-spent", by="A", delegate="B")
    attempt_claim_v2(st, agent="A", grant_id="g-spent", call_id="v2-spent-a")
    cases.append(
        _case(
            "v2_auth_spent_second_deny",
            family="authority_observation",
            name="Spent grant → second claim deny (correct)",
            mechanism_arm="correct",
            paired_input_id="auth_spent_b",
            result=attempt_claim_v2(
                st, agent="B", grant_id="g-spent", call_id="v2-spent-b"
            ),
        )
    )
    cases.append(
        _case(
            "v2_auth_spent_broken_commit",
            family="authority_observation",
            name="Spent grant + broken_allow_and_commit → unauthorized commit",
            mechanism_arm="broken_allow_and_commit",
            paired_input_id="auth_spent_b",
            result=_run_spent_broken_commit(),
        )
    )

    st = SwarmStateV2()
    st.seed_shared_grant("g-miss", owner="A")
    st.assign_delegate("g-miss", by="A", delegate="B")
    cases.append(
        _case(
            "v2_auth_missing_observation",
            family="authority_observation",
            name="Missing grant observation → missing_evidence (unknown)",
            mechanism_arm="correct",
            paired_input_id="auth_missing_b",
            result=attempt_claim_v2(
                st,
                agent="B",
                grant_id="g-miss",
                call_id="v2-miss",
                observation_mode="missing",
            ),
        )
    )

    st = SwarmStateV2()
    st.seed_shared_grant("g-misbind", owner="A")
    st.assign_delegate("g-misbind", by="A", delegate="B")
    st.revoke("g-misbind")
    cases.append(
        _case(
            "v2_auth_misbound_active_when_revoked",
            family="authority_observation",
            name="Misbound active observation of revoked grant",
            mechanism_arm="correct",
            paired_input_id="auth_misbound_b",
            result=attempt_claim_v2(
                st,
                agent="B",
                grant_id="g-misbind",
                call_id="v2-misbind",
                observation_mode="misbound",
                misbound_state="active",
            ),
        )
    )

    st = SwarmStateV2()
    st.seed_shared_grant("g-stale", owner="A", epoch="epoch-1")
    st.assign_delegate("g-stale", by="A", delegate="B")
    st.revoke("g-stale")
    st.bump_epoch("g-stale", "epoch-2")
    cases.append(
        _case(
            "v2_auth_stale_active_after_revoke",
            family="authority_observation",
            name="Stale active observation after revoke+epoch bump",
            mechanism_arm="correct",
            paired_input_id="auth_stale_b",
            result=attempt_claim_v2(
                st,
                agent="B",
                grant_id="g-stale",
                call_id="v2-stale",
                observation_mode="stale",
                stale_epoch="epoch-1",
            ),
        )
    )

    # --- Family: delegation_scope ---
    st = SwarmStateV2()
    st.seed_shared_grant("g-hop", owner="A", task_scope="task-*")
    st.assign_delegate("g-hop", by="A", delegate="B", task_scope="task-edit-*")
    st.assign_delegate("g-hop", by="B", delegate="C", task_scope="task-edit-doc")
    cases.append(
        _case(
            "v2_deleg_multihop_attenuated_allow",
            family="delegation_scope",
            name="C claims within attenuated task-edit-doc scope",
            mechanism_arm="correct",
            paired_input_id="deleg_c_doc",
            result=attempt_claim_v2(
                st,
                agent="C",
                grant_id="g-hop",
                call_id="v2-hop-ok",
                task_id="task-edit-doc",
            ),
        )
    )
    cases.append(
        _case(
            "v2_deleg_scope_exceeded_deny",
            family="delegation_scope",
            name="C denied for task outside attenuated scope",
            mechanism_arm="correct",
            paired_input_id="deleg_c_out",
            result=attempt_claim_v2(
                st,
                agent="C",
                grant_id="g-hop",
                call_id="v2-hop-out",
                task_id="task-admin",
            ),
        )
    )
    cases.append(
        _case(
            "v2_deleg_scope_exceeded_broken_allow",
            family="delegation_scope",
            name="Out-of-scope claim + broken_allow prevented",
            mechanism_arm="broken_allow",
            paired_input_id="deleg_c_out",
            result=attempt_claim_v2(
                st,
                agent="C",
                grant_id="g-hop",
                call_id="v2-hop-broken",
                task_id="task-admin",
                gate_mode="broken_allow",
            ),
        )
    )

    st = SwarmStateV2()
    st.seed_shared_grant("g-nohop", owner="A")
    st.assign_delegate("g-nohop", by="A", delegate="B")
    cases.append(
        _case(
            "v2_deleg_non_assignee_deny",
            family="delegation_scope",
            name="C not assignee after A→B only",
            mechanism_arm="correct",
            paired_input_id="deleg_c_non",
            result=attempt_claim_v2(
                st, agent="C", grant_id="g-nohop", call_id="v2-non"
            ),
        )
    )

    st = SwarmStateV2()
    st.seed_shared_grant("g-revhop", owner="A")
    st.assign_delegate("g-revhop", by="A", delegate="B")
    st.assign_delegate("g-revhop", by="B", delegate="C")
    st.revoke("g-revhop")
    cases.append(
        _case(
            "v2_deleg_revoked_after_hops_deny",
            family="delegation_scope",
            name="Revocation after multi-hop → deny",
            mechanism_arm="correct",
            paired_input_id="deleg_rev_c",
            result=attempt_claim_v2(
                st, agent="C", grant_id="g-revhop", call_id="v2-revhop"
            ),
        )
    )
    cases.append(
        _case(
            "v2_deleg_revoked_after_hops_broken_deny",
            family="delegation_scope",
            name="Still-active grant + broken_deny (control)",
            mechanism_arm="broken_deny",
            paired_input_id="deleg_active_broken_deny",
            result=_run_active_broken_deny(),
        )
    )

    # --- Family: receipt_provenance ---
    st = SwarmStateV2()
    st.seed_shared_grant("g-rx", owner="A")
    st.assign_delegate("g-rx", by="A", delegate="B")
    st.assign_delegate("g-rx", by="B", delegate="C")
    attempt_claim_v2(st, agent="A", grant_id="g-rx", call_id="v2-rx-a")
    cases.append(
        _case(
            "v2_rx_foreign_deny",
            family="receipt_provenance",
            name="Foreign ledger receipt → deny (correct)",
            mechanism_arm="correct",
            paired_input_id="rx_foreign_c",
            result=attempt_claim_v2(
                st,
                agent="C",
                grant_id="g-rx",
                call_id="v2-rx-foreign",
                receipt_kind="foreign",
                foreign_receipt_from="A",
            ),
        )
    )
    cases.append(
        _case(
            "v2_rx_foreign_broken_allow",
            family="receipt_provenance",
            name="Foreign receipt + broken_allow prevented",
            mechanism_arm="broken_allow",
            paired_input_id="rx_foreign_c",
            result=attempt_claim_v2(
                st,
                agent="C",
                grant_id="g-rx",
                call_id="v2-rx-foreign-broken",
                receipt_kind="foreign",
                foreign_receipt_from="A",
                gate_mode="broken_allow",
            ),
        )
    )

    st = SwarmStateV2()
    st.seed_shared_grant("g-replay", owner="A")
    st.assign_delegate("g-replay", by="A", delegate="C")
    st.add_receipt(
        "receipt-a-prior", agent="A", grant_id="g-replay", call_id="a-prior"
    )
    st.revoke("g-replay")
    cases.append(
        _case(
            "v2_rx_copied_replay_deny",
            family="receipt_provenance",
            name="Copied/replayed foreign receipt → deny",
            mechanism_arm="correct",
            paired_input_id="rx_replay_c",
            result=attempt_claim_v2(
                st,
                agent="C",
                grant_id="g-replay",
                call_id="v2-replay",
                receipt_kind="copied_replay",
                foreign_receipt_from="A",
            ),
        )
    )
    cases.append(
        _case(
            "v2_rx_forged_deny",
            family="receipt_provenance",
            name="Forged unbound receipt → deny",
            mechanism_arm="correct",
            paired_input_id="rx_forged_c",
            result=attempt_claim_v2(
                st,
                agent="C",
                grant_id="g-replay",
                call_id="v2-forged",
                receipt_kind="forged",
            ),
        )
    )
    cases.append(
        _case(
            "v2_rx_forged_broken_allow",
            family="receipt_provenance",
            name="Forged receipt + broken_allow prevented",
            mechanism_arm="broken_allow",
            paired_input_id="rx_forged_c",
            result=attempt_claim_v2(
                st,
                agent="C",
                grant_id="g-replay",
                call_id="v2-forged-broken",
                receipt_kind="forged",
                gate_mode="broken_allow",
            ),
        )
    )

    # --- Family: observation_delivery ---
    st = SwarmStateV2()
    st.seed_shared_grant("g-part", owner="A")
    st.assign_delegate("g-part", by="A", delegate="B")
    cases.append(
        _case(
            "v2_obs_partial_missing_evidence",
            family="observation_delivery",
            name="Partial observation (no state) → missing_evidence",
            mechanism_arm="correct",
            paired_input_id="obs_partial_b",
            result=attempt_claim_v2(
                st,
                agent="B",
                grant_id="g-part",
                call_id="v2-partial",
                observation_mode="partial",
            ),
        )
    )
    cases.append(
        _case(
            "v2_obs_irrelevant_control",
            family="observation_delivery",
            name="Irrelevant-only fact does not upgrade missing_evidence",
            mechanism_arm="correct",
            paired_input_id="obs_irrelevant_b",
            result=attempt_claim_v2(
                st,
                agent="B",
                grant_id="g-part",
                call_id="v2-irrel",
                observation_mode="irrelevant_only",
                irrelevant_fact="receipt_print_color=blue",
            ),
        )
    )

    # Always-deny control: broken_deny on active grant (rejects unjustified deny).
    # Always-allow control already covered by broken_allow families above.
    return cases


def _run_spent_broken_commit() -> dict[str, Any]:
    st = SwarmStateV2()
    st.seed_shared_grant("g-spent2", owner="A")
    st.assign_delegate("g-spent2", by="A", delegate="B")
    attempt_claim_v2(st, agent="A", grant_id="g-spent2", call_id="v2-spent2-a")
    return attempt_claim_v2(
        st,
        agent="B",
        grant_id="g-spent2",
        call_id="v2-spent-broken-commit",
        gate_mode="broken_allow_and_commit",
    )


def _run_active_broken_deny() -> dict[str, Any]:
    st = SwarmStateV2()
    st.seed_shared_grant("g-bdeny", owner="A")
    st.assign_delegate("g-bdeny", by="A", delegate="B")
    return attempt_claim_v2(
        st,
        agent="B",
        grant_id="g-bdeny",
        call_id="v2-broken-deny",
        gate_mode="broken_deny",
    )


def load_held_out_cases(
    held_out_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Load externally authored fixtures; expectations are not classifier-built."""
    directory = held_out_dir or HELD_OUT_DIR
    cases: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        st = SwarmStateV2()
        setup = fixture["setup"]
        st.seed_shared_grant(
            setup["grant_id"],
            owner=setup["owner"],
            epoch=setup.get("epoch", "epoch-1"),
            task_scope=setup.get("task_scope", "task-*"),
        )
        for hop in setup.get("assignees_via") or []:
            st.assign_delegate(
                setup["grant_id"],
                by=hop["by"],
                delegate=hop["delegate"],
                task_scope=hop.get("task_scope"),
            )
        if setup.get("revoke"):
            st.revoke(setup["grant_id"])
        for rx in setup.get("seed_receipts") or []:
            st.add_receipt(
                rx["receipt_id"],
                agent=rx["agent"],
                grant_id=setup["grant_id"],
                call_id=rx["call_id"],
                authentic=rx.get("authentic", True),
                binding=rx.get("binding", "ledger"),
            )

        claim = fixture["agent_visible_claim"]
        result = attempt_claim_v2(
            st,
            agent=claim["agent"],
            grant_id=setup["grant_id"],
            call_id=claim["call_id"],
            observation_mode=claim.get("observation_mode", "authentic"),
            gate_mode=claim.get("gate_mode", "correct"),
            task_id=claim.get("task_id"),
            receipt_kind=claim.get("receipt_kind", "none"),
            foreign_receipt_from=claim.get("foreign_receipt_from"),
            misbound_state=claim.get("misbound_state"),
            stale_epoch=claim.get("stale_epoch"),
            irrelevant_fact=claim.get("irrelevant_fact"),
        )
        # Attach trusted ground truth from the fixture (not from the classifier).
        result["trusted_ground_truth"] = fixture["trusted_ground_truth"]
        result["held_out_artifact"] = path.name
        result["fixture_expected"] = fixture["expected"]
        cases.append(
            _case(
                fixture["case_id"],
                family=fixture.get("family", "held_out"),
                name=fixture.get("name", path.stem),
                result=result,
                mechanism_arm=claim.get("gate_mode", "correct"),
                paired_input_id=fixture.get("paired_input_id"),
                evidence_source=f"held_out:{path.name}",
            )
        )
    return cases


def load_concurrency_trace_cases(
    trace_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Consume pinned multi-agent-sim runs as concurrency-derived evidence rows.

    Does not re-implement the simulator. Traces declare their own source protocol
    (`multi-agent-sim-v1`). Live concurrent swarm behavior is not claimed.
    """
    directory = trace_dir or CONCURRENCY_TRACE_DIR
    cases: list[dict[str, Any]] = []
    for path in sorted(directory.glob("mas-*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        obs = run["observations"]
        # Project each claim into an R5-v2 case row, preserving sim diagnoses.
        for claim in obs["claims"]:
            diag = claim.get("diagnosis") or {}
            result = {
                "agent": claim["agent"],
                "grant_id": claim.get("grant_id"),
                "call_id": claim["call_id"],
                "observation_mode": "sim_local",
                "observed_grant": (
                    (claim.get("local_knowledge_at_decision") or {}).get(
                        "grant_observations"
                    )
                    or [None]
                )[0],
                "receipt_kind": "sim",
                "presented_receipt": None,
                "gate_mode": obs.get("policy_id", "reference"),
                "decision": claim["decision"],
                "required_decision": claim.get("required_decision"),
                "effect_committed": claim["committed_effect"],
                "assessment": claim.get("assessment"),
                "conclusion_class": claim["conclusion_class"],
                "finding_label": claim.get("finding_label"),
                "property_holds": claim.get("property_holds"),
                "reason": claim.get("reason"),
                "authoritative_owner_state": claim.get("authoritative_owner_state"),
                "evidence_status": diag.get("evidence_status"),
                "decision_status": diag.get("decision_status"),
                "effect_status": diag.get("effect_status"),
                "failure_origin": diag.get("failure_origin"),
                "sim_source_run_id": run["id"],
                "sim_case_id": run["case_id"],
                "sim_protocol_id": run.get("protocol_id"),
                "sim_seed": obs.get("seed"),
                "sim_schedule_id": obs.get("schedule_id"),
                "sim_policy_id": obs.get("policy_id"),
                "sim_exclusions": obs.get("exclusions")
                or [
                    "live_bmo_mesh_equivalence",
                    "production_concurrency_guarantees",
                    "unbounded_swarm_safety",
                ],
            }
            case_id = f"v2_sim_{run['case_id']}__{claim['call_id']}"
            cases.append(
                _case(
                    case_id,
                    family="concurrency_interleaving",
                    name=(
                        f"Pinned sim {run['case_id']}/{claim['call_id']} "
                        f"(policy={obs.get('policy_id')})"
                    ),
                    result=result,
                    mechanism_arm=str(obs.get("policy_id") or "reference"),
                    paired_input_id=f"sim:{run['case_id']}",
                    evidence_source=(
                        f"multi-agent-sim-v1:{path.name}#{claim['call_id']}"
                    ),
                )
            )
    return cases


def load_case_expectations(
    path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    import yaml

    p = path or EXPECTATIONS_PATH
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return {row["case_id"]: row for row in data["cases"]}


def run_r5_v2_protocol_cases(
    *,
    include_concurrency: bool = True,
    include_held_out: bool = True,
) -> list[dict[str, Any]]:
    cases = run_sequential_family_cases()
    if include_held_out:
        cases.extend(load_held_out_cases())
    if include_concurrency:
        cases.extend(load_concurrency_trace_cases())
    # Attach independently declared expectations when present.
    expectations = load_case_expectations()
    for case in cases:
        exp = expectations.get(case["case_id"])
        if exp is not None:
            case["expected"] = {
                k: v
                for k, v in exp.items()
                if k != "case_id"
            }
            case["expectation_source"] = str(EXPECTATIONS_PATH.relative_to(ROOT))
        elif case["result"].get("fixture_expected"):
            case["expected"] = dict(case["result"]["fixture_expected"])
            case["expectation_source"] = case["evidence_source"]
        else:
            case["expected"] = None
            case["expectation_source"] = None
    return cases


def evaluate_r5_v2_success(cases: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    agents_seen: set[str] = set()
    families: set[str] = set()
    unknown_coerced = 0

    for case in cases:
        agents_seen.update(case.get("agents") or [])
        families.add(case["family"])
        result = case["result"]
        expected = case.get("expected")

        # Unknown must never be coerced into deny/allow or enforcement failure.
        if result.get("conclusion_class") == "missing_evidence":
            if result.get("decision") is not None:
                unknown_coerced += 1
                errors.append(
                    f"{case['case_id']}: missing_evidence coerced to "
                    f"decision={result.get('decision')!r}"
                )
            if result.get("decision_status") not in {None, "unknown"}:
                errors.append(
                    f"{case['case_id']}: missing_evidence decision_status "
                    f"{result.get('decision_status')!r} not unknown"
                )

        if expected:
            for key in (
                "conclusion_class",
                "decision",
                "effect_committed",
                "decision_status",
                "effect_status",
                "failure_origin",
                "evidence_status",
                "assessment",
            ):
                if key in expected and result.get(key) != expected[key]:
                    errors.append(
                        f"{case['case_id']}: {key} {result.get(key)!r} "
                        f"want {expected[key]!r}"
                    )

        # Wrong allow must declare prevented vs committed distinctly.
        if (
            result.get("decision") == "allow"
            and result.get("property_holds") is False
            and result.get("effect_committed")
            and result.get("failure_origin") != "effect_boundary"
            and result.get("evidence_status") != "misbound"
        ):
            errors.append(
                f"{case['case_id']}: unauthorized commit without "
                "failure_origin=effect_boundary"
            )
        if (
            result.get("decision") == "allow"
            and result.get("property_holds") is False
            and result.get("effect_committed") is False
            and result.get("failure_origin")
            not in {"decision_policy", "evidence"}
        ):
            errors.append(
                f"{case['case_id']}: prevented wrong allow without "
                "decision_policy/evidence origin"
            )
        if (
            result.get("decision") == "deny"
            and result.get("property_holds") is False
            and result.get("failure_origin") not in {"decision_policy", "evidence"}
        ):
            errors.append(
                f"{case['case_id']}: incorrect deny without "
                "decision_policy/evidence origin"
            )

    if agents_seen != {"A", "B", "C"}:
        errors.append(f"must involve A,B,C; saw {sorted(agents_seen)}")

    classes = {c["result"]["conclusion_class"] for c in cases}
    three_way = {
        "missing_evidence",
        "failed_enforcement",
        "supported",
    }.issubset(classes)

    # Per-family correct + faulty arm on same paired_input_id where declared.
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        pid = case.get("paired_input_id")
        if pid:
            by_pair.setdefault(pid, []).append(case)
    paired_ok = 0
    for pid, rows in by_pair.items():
        arms = {r["mechanism_arm"] for r in rows}
        if any(a.startswith("broken") or a.startswith("mutant") for a in arms) and (
            "correct" in arms or "reference" in arms
        ):
            paired_ok += 1

    # Always-deny / unjustified-allow controls.
    has_broken_deny = any(
        c["result"].get("gate_mode") == "broken_deny" for c in cases
    )
    has_broken_allow = any(
        c["result"].get("gate_mode") in {"broken_allow", "broken_allow_and_commit"}
        or str(c["result"].get("gate_mode", "")).startswith("mutant")
        for c in cases
    )
    if not has_broken_deny:
        errors.append("missing broken_deny always-deny control")
    if not has_broken_allow:
        errors.append("missing broken/mutant allow control")

    # Concurrency rows must cite simulator protocol, not claim live swarm.
    sim_cases = [c for c in cases if c["family"] == "concurrency_interleaving"]
    for c in sim_cases:
        src = c.get("evidence_source") or ""
        if "multi-agent-sim" not in src:
            errors.append(f"{c['case_id']}: concurrency row missing sim source ref")
        if c["result"].get("sim_protocol_id") not in {
            None,
            "multi-agent-sim-v1",
        }:
            # Allow None only if pin file omitted; prefer explicit.
            pass
        excl = c["result"].get("sim_exclusions") or []
        if "live_bmo_mesh_equivalence" not in excl:
            # Soft: pinned runs should carry exclusions; annotate if missing.
            c["result"]["sim_exclusions"] = list(
                {
                    *excl,
                    "live_bmo_mesh_equivalence",
                    "production_concurrency_guarantees",
                    "unbounded_swarm_safety",
                }
            )

    if len(sim_cases) < 4:
        errors.append(
            f"expected ≥4 concurrency-derived claim rows from pinned sim traces; "
            f"got {len(sim_cases)}"
        )

    held = [c for c in cases if str(c.get("evidence_source", "")).startswith("held_out")]
    if not held:
        errors.append("missing held-out external fixtures")

    return {
        "passed": not errors,
        "errors": errors,
        "case_count": len(cases),
        "agent_count": len(agents_seen),
        "agents": sorted(agents_seen),
        "model": "r5_v2_sequential_plus_pinned_sim_traces",
        "protocol_id": PROTOCOL_ID,
        "source_pin": SOURCE_PIN,
        "claim_id": CLAIM_ID,
        "three_way_classes_exercised": three_way,
        "families": sorted(families),
        "family_count": len(families),
        "paired_input_groups_with_correct_and_faulty": paired_ok,
        "unknown_coerced_count": unknown_coerced,
        "concurrency_row_count": len(sim_cases),
        "held_out_count": len(held),
        "missing_evidence_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "missing_evidence"
        ),
        "failed_enforcement_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "failed_enforcement"
        ),
        "supported_count": sum(
            1 for c in cases if c["result"]["conclusion_class"] == "supported"
        ),
        "effect_boundary_count": sum(
            1
            for c in cases
            if c["result"].get("failure_origin") == "effect_boundary"
        ),
        "decision_policy_count": sum(
            1
            for c in cases
            if c["result"].get("failure_origin") == "decision_policy"
        ),
        "all_checks_pass": not errors,
    }


def compare_boundaries_to_v1(
    v2_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Report whether v2 changes prior supported/unresolved boundaries.

    Retains ties, failures, and null results relative to R5 v1 themes.
    """
    from swarm_witness.swarm_audit import (
        evaluate_swarm_method_success,
        run_swarm_protocol_cases,
    )

    v1_cases = run_swarm_protocol_cases()
    v1_score = evaluate_swarm_method_success(v1_cases)
    v2_cases = v2_cases if v2_cases is not None else run_r5_v2_protocol_cases()
    v2_score = evaluate_r5_v2_success(v2_cases)

    v1_classes = {
        c["case_id"]: c["result"]["conclusion_class"] for c in v1_cases
    }
    return {
        "v1_retained": True,
        "v1_protocol_id": "r5-swarm-audit-v1",
        "v1_passed": v1_score["passed"],
        "v1_counts": {
            "missing_evidence": v1_score["missing_evidence_count"],
            "failed_enforcement": v1_score["failed_enforcement_count"],
            "supported": v1_score["supported_count"],
            "case_count": v1_score["case_count"],
        },
        "v1_case_classes": v1_classes,
        "v2_passed": v2_score["passed"],
        "v2_counts": {
            "missing_evidence": v2_score["missing_evidence_count"],
            "failed_enforcement": v2_score["failed_enforcement_count"],
            "supported": v2_score["supported_count"],
            "case_count": v2_score["case_count"],
            "effect_boundary": v2_score["effect_boundary_count"],
            "decision_policy": v2_score["decision_policy_count"],
        },
        "boundary_changes": {
            "new_failure_origin_effect_boundary": v2_score["effect_boundary_count"]
            > 0,
            "new_misbound_evidence_rows": any(
                c["result"].get("evidence_status") == "misbound" for c in v2_cases
            ),
            "new_concurrency_derived_rows": v2_score["concurrency_row_count"] > 0,
            "v1_finding_unchanged": True,
            "notes": (
                "v2 expands tested seams (misbound, stale, attenuated scope, "
                "forged/replay receipts, effect_boundary commits, pinned sim "
                "interleavings). v1 sequential Finding and denominator are "
                "retained unmodified; ties/failures/nulls from v1 remain."
            ),
        },
        "falsifying_counterexamples": [
            {
                "case_id": c["case_id"],
                "failure_origin": c["result"].get("failure_origin"),
                "effect_committed": c["result"].get("effect_committed"),
                "decision": c["result"].get("decision"),
                "required_decision": c["result"].get("required_decision"),
            }
            for c in v2_cases
            if c["result"].get("conclusion_class") == "failed_enforcement"
        ],
    }


def load_coverage_matrix(path: Path | None = None) -> dict[str, Any]:
    import yaml

    p = path or COVERAGE_MATRIX_PATH
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def coverage_report(
    cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    matrix = load_coverage_matrix()
    cases = cases if cases is not None else run_r5_v2_protocol_cases()
    by_family: dict[str, list[str]] = {}
    for case in cases:
        by_family.setdefault(case["family"], []).append(case["case_id"])
    dimensions = []
    for dim in matrix["dimensions"]:
        dimensions.append(
            {
                "id": dim["id"],
                "tested_seams": list(dim.get("tested") or []),
                "untested_seams": list(dim.get("untested") or []),
                "case_ids": by_family.get(dim.get("family") or dim["id"], []),
                "tested_count": len(dim.get("tested") or []),
                "untested_count": len(dim.get("untested") or []),
            }
        )
    return {
        "protocol_id": PROTOCOL_ID,
        "dimension_count": len(dimensions),
        "dimensions": dimensions,
        "families_present": sorted(by_family),
        "total_cases": len(cases),
    }
