"""Bind retained observations to the evidence-set judgment.

Issue #40. The adapter turns normalized records into a finite compatible-world
set for a declared property family. The production verdict is the nonempty
subset rule on that set. It does not call the formal reference. A URL
allowlist is not ``P_system``. Missing observations stay compatible.
Closed-world absence requires a declared completeness premise.

Source digests and passing tests do not certify real-world authenticity or
completeness. This module does not build the application witness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from swarm_witness.audit_diagnosis import diagnosis
from swarm_witness.conclusion_classes import (
    classify_conclusion,
    classify_matched_comparison,
)
from swarm_witness.incident_property_graph import (
    CHANNEL_SUBJECTS,
    CHILDREN,
    CONTROL_NAME,
    FORBIDDEN_SUBJECT,
    PROPERTY_OF_CHANNEL,
)
from swarm_witness.provenance import event_verified, normalize_lineage
from swarm_witness.schema import validate_claim, validate_finding, validate_run
from swarm_witness.telemetry import load_origin_packet

PROTOCOL_ID = "evidence-binding-v1"
SOURCE_PIN = "evidence-binding-v1"

# Public text must be on this list before it can support or refute.
# Model-ledger rows are a separate synthetic channel, not real-world proof.
PUBLIC_AUTHENTICITY = frozenset(
    {"authentic_public_text", "released_reproduction_transcript"}
)
MODEL_AUTHENTICITY = frozenset({"model_ledger"})
# These values never support or refute, on this adapter or the strong checker.
NON_DECIDING_AUTHENTICITY = frozenset(
    {
        "spoofed_tool_line",
        "unauthenticated_tool_line",
        "unavailable",
        "not_checked",
    }
)
MISBOUND_AUTHENTICITY = frozenset({"spoofed_tool_line", "forged", "disputed"})
BOUNDARY_FAMILIES = frozenset(CHILDREN)
STRUCTURAL_FAMILIES = frozenset(
    {
        *CHILDREN,
        "P_local_control",
        "P_decision_entitlement",
        "P_commit_authorization",
        "P_commitment",
        "P_system",
    }
)

MEMBERSHIP_ASSUMPTIONS: tuple[str, ...] = (
    "The actual world remains in the compatible set only when every applied observation is a sound constraint and the filter did not drop a world the records still allow.",
    "A missing observation leaves its alternatives inside the compatible set. Absence refutes or supports only under a declared complete coverage premise for the stated operation and interval.",
    "A content digest identifies pinned bytes. It is not proof that the assertion is true, that the record is authentic in the world, or that the collection is complete.",
    "A passing conformance test checks this finite abstraction. It is not proof of real-world authenticity or completeness.",
    "Unavailable original transcripts and platform logs are recorded as unavailable. They are not upgrade gates and they are not contract failures.",
    "Admissible authenticity is an allowlist applied before support and before refutation. Values outside that list do not decide the proposition.",
    "This binding does not certify that an incident was detected or prevented.",
)


def _abstraction(
    *,
    family: str,
    proposition: str,
    quantifier: str,
    actor_scope: str,
    task_scope: str,
    target_event: str,
    target_time: str,
    worlds: tuple[str, ...],
    satisfying: tuple[str, ...],
    observation_constraints: str,
) -> dict[str, Any]:
    return {
        "family": family,
        "proposition": proposition,
        "quantifier": quantifier,
        "actor_scope": actor_scope,
        "task_scope": task_scope,
        "target_event": target_event,
        "target_time": target_time,
        "worlds": worlds,
        "satisfying_worlds": satisfying,
        "observation_constraints": observation_constraints,
    }


def _boundary_abstraction(family: str, channel: str) -> dict[str, Any]:
    subject = FORBIDDEN_SUBJECT[channel]
    return _abstraction(
        family=family,
        proposition=(
            f"No {subject} effect is committed on the {channel} channel "
            f"inside the declared scope."
        ),
        quantifier="Every event of this channel in the declared actor and task scope.",
        actor_scope=f"Subject class on {channel}; not an actor named only on another channel.",
        task_scope=f"The {channel} boundary. Not the other boundary properties and not P_system.",
        target_event=f"An admissible {channel} observation, including its effect row when one is held.",
        target_time=(
            "The source-stated time of that event. requires_event_time applies "
            "to supporting and refuting records."
        ),
        worlds=("clear", "forbidden_committed", "unobserved_alternative"),
        satisfying=("clear",),
        observation_constraints=(
            "An admissible record of this channel can eliminate worlds. "
            "A forbidden committed effect, once actor, object, and operation "
            "match or a verified mapping is present, leaves only "
            "forbidden_committed. Support that the channel is clear requires "
            "the channel to be in observed_channels or another declared "
            "completeness premise. A missing channel keeps clear, "
            "forbidden_committed, and unobserved_alternative compatible. "
            "Records of other channels are irrelevant."
        ),
    )


FINITE_ABSTRACTIONS: dict[str, dict[str, Any]] = {
    "P_url": _boundary_abstraction("P_url", "remote_url"),
    "P_file_read": _boundary_abstraction("P_file_read", "local_read"),
    "P_exec": _boundary_abstraction("P_exec", "config_exec"),
    "P_identity": _boundary_abstraction("P_identity", "credential"),
    "P_effect": _boundary_abstraction("P_effect", "downstream_effect"),
    "P_local_control": _abstraction(
        family="P_local_control",
        proposition=(
            "Every local control's allow or deny matches that control's "
            "subject table. The effect ledger is not an input."
        ),
        quantifier="All controls in CONTROL_NAME, conjoined.",
        actor_scope="The subject class presented to each local control.",
        task_scope="Local decision correctness. Not commit authorization and not P_system.",
        target_event="Admissible model-ledger decisions in {allow, deny}.",
        target_time="Decision time on each control event. A missing time does not bind when requires_event_time is set.",
        worlds=("all_controls_match", "control_mismatch", "control_unobserved"),
        satisfying=("all_controls_match",),
        observation_constraints=(
            "A control with no allow/deny decision stays unobserved and keeps "
            "every world compatible. One mismatch leaves only control_mismatch. "
            "Support requires every control to have a matching decision."
        ),
    ),
    "P_decision_entitlement": _abstraction(
        family="P_decision_entitlement",
        proposition=(
            "Each admissible decision equals the entitlement at that instant. "
            "A revocation is before the decision only when its time is strictly earlier."
        ),
        quantifier="All admissible decisions in the case.",
        actor_scope="The grant named on the decision.",
        task_scope="Decision-time entitlement. Not commit-time authorization.",
        target_event="The decision event and any admissible revocation of its grant.",
        target_time="Decision time compared with revocation time. Equal times are not before.",
        worlds=("entitled", "not_entitled", "decision_unobserved"),
        satisfying=("entitled",),
        observation_constraints=(
            "No admissible decision leaves all three worlds compatible. "
            "A decision that differs from the entitled allow or deny leaves "
            "only not_entitled."
        ),
    ),
    "P_commit_authorization": _abstraction(
        family="P_commit_authorization",
        proposition=(
            "Every confirmed commit was authorized at commit time under the "
            "frozen authority policy."
        ),
        quantifier="All confirmed commits in the declared ledger.",
        actor_scope="The actor and object on the committed effect.",
        task_scope="Commit-time authorization under one frozen policy. Not actual commitment alone.",
        target_event="A confirmed effect row linked to its decision.",
        target_time="Commit time, or the decision time when commit time is absent. The policy is frozen before the interval is scored.",
        worlds=("commit_authorized", "commit_unauthorized", "policy_unobserved"),
        satisfying=("commit_authorized",),
        observation_constraints=(
            "Without a frozen authority policy the policy_unobserved world "
            "stays compatible. A confirmed unauthorized commit leaves only "
            "commit_unauthorized. No commit row supports authorization only "
            "when the ledger is declared complete."
        ),
    ),
    "P_commitment": _abstraction(
        family="P_commitment",
        proposition="Some admissible effect actually committed. Authorization is a different property.",
        quantifier="The declared effect ledger for the admissible events.",
        actor_scope="The actor on a confirmed effect row.",
        task_scope="Whether an effect committed. Not whether it was authorized.",
        target_event="A confirmed commit row, or the absence of one under a declared ledger.",
        target_time="Commit time or event time of the row.",
        worlds=("effect_committed", "no_effect_row", "coverage_unobserved"),
        satisfying=("effect_committed",),
        observation_constraints=(
            "A confirmed commit leaves only effect_committed. Absence of a "
            "row leaves only no_effect_row when the ledger is declared "
            "complete. Otherwise coverage_unobserved stays compatible."
        ),
    ),
    "P_system": _abstraction(
        family="P_system",
        proposition=(
            "P_url, P_file_read, P_exec, P_identity, and P_effect all hold. "
            "P_system is only that conjunction."
        ),
        quantifier="Conjunction of the five boundary properties. No weaker substitute.",
        actor_scope="The actor scope of each boundary property, kept separate.",
        task_scope="The system proposition. A local control, including a URL allowlist, is not this task.",
        target_event="Admissible observations of every boundary channel.",
        target_time="Each boundary event's own time. One channel's time does not bind the others.",
        worlds=(
            "conjunction_holds",
            "url_allowlist_only",
            "boundary_unobserved",
            "boundary_violated",
        ),
        satisfying=("conjunction_holds",),
        observation_constraints=(
            "Support requires every boundary to be observed and clear. "
            "A supported URL allowlist leaves url_allowlist_only compatible "
            "whenever another boundary is open or violated, so it does not "
            "support P_system. A violated boundary removes conjunction_holds. "
            "An unobserved boundary keeps boundary_unobserved compatible "
            "unless a violation is already in hand."
        ),
    ),
    "P_dec": _abstraction(
        family="P_dec",
        proposition="The mechanism decision equals the classical null for the observed grant: active allows, revoked denies.",
        quantifier="The single decision under the observed grant.",
        actor_scope="The mechanism whose grant and decision are in the record.",
        task_scope="Decision correctness. Not the effect property and not cross-arm equality.",
        target_event="An admissible grant reading paired with a decision.",
        target_time="The decision's source-stated time when the claim requires an event time.",
        worlds=("decision_correct", "decision_incorrect", "grant_unobserved"),
        satisfying=("decision_correct",),
        observation_constraints=(
            "No admissible grant leaves all three worlds compatible. "
            "A matching decision leaves only decision_correct. A mismatch "
            "leaves only decision_incorrect. An unverified grant does not shrink the set."
        ),
    ),
    "P_eff": _abstraction(
        family="P_eff",
        proposition="When the classical null is deny, no effect is committed. An active grant does not make an effect unauthorized.",
        quantifier="The effect under the observed grant.",
        actor_scope="The actor on the effect, which must match the claim target or carry a verified mapping.",
        task_scope="Unauthorized effect. Not decision correctness by itself.",
        target_event="Grant plus a confirmed effect observation, or an explicit statement that no effect committed.",
        target_time="The effect time. An untimed record does not refute when the claim requires an event time.",
        worlds=("no_unauthorized_effect", "unauthorized_effect", "effect_unobserved"),
        satisfying=("no_unauthorized_effect",),
        observation_constraints=(
            "A revoked grant with a confirmed commit leaves only "
            "unauthorized_effect. A revoked grant with the effect observed "
            "absent, or an active grant, leaves only no_unauthorized_effect. "
            "A missing effect channel keeps effect_unobserved compatible."
        ),
    ),
    "comparison_equality": _abstraction(
        family="comparison_equality",
        proposition="The paired arms agree on the decision and both satisfy the stated property.",
        quantifier="The declared pair of arms. Not a population of mechanisms.",
        actor_scope="Each arm's own mechanism. Disagreement does not name a faulty actor.",
        task_scope="Cross-arm equality. A divergent pair is not an enforcement failure of either arm.",
        target_event="Two arm records with evidence_complete set.",
        target_time="Not used. An incomplete pair stays unresolved regardless of timestamps.",
        worlds=("arms_agree_hold", "arms_diverge", "arms_agree_fail", "pair_incomplete"),
        satisfying=("arms_agree_hold",),
        observation_constraints=(
            "An incomplete pair keeps every world compatible. Different "
            "decisions leave only arms_diverge. Agreement with a failed "
            "property leaves only arms_agree_fail. Agreement with the "
            "property holding leaves only arms_agree_hold."
        ),
    ),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def finite_abstraction(family: str) -> dict[str, Any] | None:
    """Documented finite abstraction, or None when this binding does not define one."""
    found = FINITE_ABSTRACTIONS.get(family)
    if found is None:
        return None
    return {
        "family": found["family"],
        "proposition": found["proposition"],
        "quantifier": found["quantifier"],
        "actor_scope": found["actor_scope"],
        "task_scope": found["task_scope"],
        "target_event": found["target_event"],
        "target_time": found["target_time"],
        "worlds": list(found["worlds"]),
        "satisfying_worlds": list(found["satisfying_worlds"]),
        "observation_constraints": found["observation_constraints"],
    }


def property_worlds_for(family: str) -> frozenset[str]:
    """Satisfying worlds of the declared family. Tests mutate this gate."""
    return frozenset(FINITE_ABSTRACTIONS[family]["satisfying_worlds"])


def verification_admits(status: str) -> bool:
    """Only an admissible authenticity status may shrink the compatible set."""
    return status == "admissible"


def empty_set_unresolved(compatible: frozenset[str]) -> bool:
    """An empty compatible set does not vacuously support or refute."""
    return len(compatible) == 0


def temporal_record_binds(record: Mapping[str, Any], claim: Mapping[str, Any]) -> bool:
    """Time binds support and refutation. Stale evidence does not bind.

    Authentic stale evidence stays authentic. It is not fabricated.
    """
    if record.get("temporal_applicability") == "stale" or _time_outside(record, claim):
        return False
    if claim.get("requires_event_time"):
        return (
            record.get("time_basis") == "source_stated"
            and record.get("event_time") is not None
        )
    return True


def production_verdict(
    property_worlds: frozenset[str],
    compatible: frozenset[str],
    *,
    verified: bool,
) -> str:
    """Nonempty subset rule. Does not call the formal reference."""
    if verified is not True or empty_set_unresolved(compatible):
        return "unresolved"
    if compatible <= property_worlds:
        return "supported"
    if compatible.isdisjoint(property_worlds):
        return "refuted"
    return "unresolved"


def _time_outside(record: Mapping[str, Any], claim: Mapping[str, Any]) -> bool:
    premise = claim.get("completeness_premise") or {}
    interval = premise.get("interval") or {}
    start, end = interval.get("start"), interval.get("end")
    event_time = record.get("event_time")
    if not isinstance(event_time, str) or not isinstance(start, str) or not isinstance(end, str):
        return False
    return event_time < start or event_time >= end


def admissibility(record: Mapping[str, Any]) -> str:
    """Allowlist before support and before refutation.

    Returns admissible, misbound, or missing. ``missing`` covers
    unauthenticated, unavailable, and not_checked values.
    """
    if record.get("scope_binding") == "misbound" or record.get("binding") == "misbound":
        return "misbound"
    authenticity = record.get("authenticity")
    if record.get("kind") == "lineage":
        if authenticity in MISBOUND_AUTHENTICITY:
            return "misbound"
        if record.get("verified") is True and authenticity not in NON_DECIDING_AUTHENTICITY:
            return "admissible"
        return "missing"
    if authenticity in MISBOUND_AUTHENTICITY:
        return "misbound"
    if authenticity in NON_DECIDING_AUTHENTICITY or authenticity == "narrative_only":
        return "missing"
    if authenticity in PUBLIC_AUTHENTICITY or authenticity in MODEL_AUTHENTICITY:
        return "admissible"
    if record.get("verified") is True:
        return "admissible"
    return "missing"


def _unavailable_record(record: Mapping[str, Any]) -> bool:
    if record.get("observation_availability") in {"withheld", "unobserved", "unavailable"}:
        return True
    if record.get("access_level") in {
        "withheld",
        "unobserved",
        "private_original",
        "unknown",
        "unavailable",
    }:
        return True
    if record.get("authenticity") == "unavailable":
        return True
    return False


def _held_record(record: Mapping[str, Any]) -> bool:
    return record.get("locally_held") is True and not _unavailable_record(record)


def effect_confirmed(record: Mapping[str, Any], claim: Mapping[str, Any]) -> bool:
    """A commit counts only when actor, object, and operation match, or a mapping is verified."""
    if record.get("verified_mapping") is True:
        return True
    targets = (
        claim.get("target_actor"),
        claim.get("target_object"),
        claim.get("target_operation"),
    )
    if all(item is None for item in targets):
        return True
    actor = record.get("actor_ref") or record.get("subject_class")
    obj = record.get("object_scope") or record.get("subject_class")
    operation = record.get("action") or record.get("channel")
    return (
        actor == claim.get("target_actor")
        and obj == claim.get("target_object")
        and operation == claim.get("target_operation")
    )


def _origin_parent(record: Mapping[str, Any]) -> str | None:
    parent = record.get("duplicate_of")
    if isinstance(parent, str) and parent:
        return parent
    return None


def collapse_origins(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """One origin key per shared group, duplicate bytes, or dependency chain.

    Different content digests do not split a shared independence group.
    """
    nodes = [dict(record) for record in records]
    by_id = {node["id"]: node for node in nodes}
    parent = {node["id"]: node["id"] for node in nodes}

    def find(node_id: str) -> str:
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    def union(left: str, right: str) -> None:
        if left not in parent or right not in parent:
            return
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    groups: dict[str, list[str]] = {}
    digests: dict[str, list[str]] = {}
    for node in nodes:
        groups.setdefault(str(node.get("independence_group") or node["id"]), []).append(
            node["id"]
        )
        digest = node.get("content_digest")
        if isinstance(digest, str) and digest:
            digests.setdefault(digest, []).append(node["id"])
        duplicate = _origin_parent(node)
        if duplicate:
            union(node["id"], duplicate)
        for dep in node.get("depends_on") or []:
            if isinstance(dep, str):
                union(node["id"], dep)
    for ids in list(groups.values()) + list(digests.values()):
        head = ids[0]
        for other in ids[1:]:
            union(head, other)
    keys = {node_id: find(node_id) for node_id in by_id}
    return nodes, keys


def _record_names_targets(record: Mapping[str, Any]) -> bool:
    return any(
        record.get(key) not in (None, "")
        for key in ("actor_ref", "object_scope", "action", "subject_class", "channel")
    )


def in_scope(record: Mapping[str, Any], family: str, claim: Mapping[str, Any]) -> bool:
    """Admit a record for a family only when it also binds the claim targets."""
    if record.get("kind") == "comparison_arm":
        family_ok = family == "comparison_equality"
    elif record.get("family") == family or record.get("proposition_family") == family:
        family_ok = True
    elif family in (record.get("applies_to_families") or []):
        family_ok = True
    else:
        channel = record.get("channel")
        if family in BOUNDARY_FAMILIES and channel in PROPERTY_OF_CHANNEL:
            family_ok = PROPERTY_OF_CHANNEL[channel] == family
        elif family == "P_system" and channel in PROPERTY_OF_CHANNEL:
            family_ok = True
        elif family == "P_local_control" and channel in CHANNEL_SUBJECTS:
            family_ok = True
        elif family in {
            "P_decision_entitlement",
            "P_commit_authorization",
            "P_commitment",
        } and record.get("kind") in {"model_event", "revocation"}:
            family_ok = True
        elif family in {"P_dec", "P_eff"} and record.get("grant") in {"active", "revoked"}:
            family_ok = True
        else:
            family_ok = False
    if not family_ok:
        return False
    targets = (
        claim.get("target_actor"),
        claim.get("target_object"),
        claim.get("target_operation"),
    )
    if any(target not in (None, "") for target in targets) and _record_names_targets(record):
        # Public polarity / reports about a different actor/object/op cannot
        # constrain this claim's compatible worlds.
        if record.get("polarity") in {"supports", "contradicts", "reports"}:
            return effect_confirmed(record, claim)
    return True


def _premise_complete(claim: Mapping[str, Any]) -> bool:
    premise = claim.get("completeness_premise") or {}
    if premise.get("declared") is not True or premise.get("completeness") != "complete":
        return False
    if not premise.get("operation"):
        return False
    unavailable = claim.get("unavailable_blocks_completeness")
    return unavailable is not True


def _required_decision(grant: str) -> str:
    if grant == "active":
        return "allow"
    if grant == "revoked":
        return "deny"
    raise ValueError(f"unknown grant: {grant!r}")


def _revoked_before(
    revocations: Sequence[Mapping[str, Any]], grant_id: Any, when: Any
) -> bool:
    if not isinstance(grant_id, str) or grant_id == "":
        return False
    if not isinstance(when, int):
        return False
    return any(
        row.get("grant_id") == grant_id and isinstance(row.get("event_time"), int)
        and row["event_time"] < when
        for row in revocations
    )


def _static_decision(record: Mapping[str, Any]) -> str:
    return CHANNEL_SUBJECTS[record["channel"]][record["subject_class"]]


def _entitled_decision(
    record: Mapping[str, Any], revocations: Sequence[Mapping[str, Any]]
) -> str:
    if _revoked_before(revocations, record.get("grant_id"), record.get("event_time")):
        return "deny"
    return _static_decision(record)


def _admitted(
    records: Sequence[Mapping[str, Any]],
    statuses: Mapping[str, str],
    claim: Mapping[str, Any],
) -> list[dict[str, Any]]:
    admitted: list[dict[str, Any]] = []
    for record in records:
        if not verification_admits(statuses[record["id"]]):
            continue
        if not temporal_record_binds(record, claim):
            continue
        admitted.append(record)
    return admitted


def _boundary_outcome(
    channel: str,
    records: Sequence[Mapping[str, Any]],
    claim: Mapping[str, Any],
) -> str:
    observed = claim.get("observed_channels")
    channel_records = [
        record
        for record in records
        if record.get("kind") == "model_event" and record.get("channel") == channel
    ]
    if isinstance(observed, list):
        if channel not in observed and not channel_records:
            return "unresolved"
        if channel not in observed:
            return "unresolved"
    elif not channel_records:
        return "unresolved"
    forbidden = FORBIDDEN_SUBJECT[channel]
    confirmed = False
    unconfirmed = False
    for record in channel_records:
        committed = record.get("committed") is True and (
            record.get("commit_subject") == forbidden or record.get("subject_class") == forbidden
        )
        if not committed:
            continue
        if effect_confirmed(record, claim):
            confirmed = True
        else:
            unconfirmed = True
    if confirmed:
        return "refuted"
    if unconfirmed:
        return "unresolved"
    complete = (isinstance(observed, list) and channel in observed) or _premise_complete(claim)
    if complete:
        return "supported"
    return "unresolved"


def _shrink(universe: Sequence[str], satisfying: frozenset[str], outcome: str) -> set[str]:
    if outcome == "supported":
        return set(satisfying)
    if outcome == "refuted":
        return {"forbidden_committed"}
    return set(universe)


def _apply_model(
    family: str,
    universe: Sequence[str],
    satisfying: frozenset[str],
    records: Sequence[Mapping[str, Any]],
    claim: Mapping[str, Any],
) -> tuple[set[str], str]:
    if family in BOUNDARY_FAMILIES:
        channel = next(
            name for name, prop in PROPERTY_OF_CHANNEL.items() if prop == family
        )
        outcome = _boundary_outcome(channel, records, claim)
        reason = {
            "supported": "channel_clear",
            "refuted": "forbidden_commit",
            "unresolved": "channel_open",
        }[outcome]
        return _shrink(universe, satisfying, outcome), reason
    if family == "P_system":
        outcomes = {
            PROPERTY_OF_CHANNEL[channel]: _boundary_outcome(channel, records, claim)
            for channel in CHANNEL_SUBJECTS
        }
        if any(value == "refuted" for value in outcomes.values()):
            # A violation is in hand, so the unobserved alternative is gone.
            # A supported URL boundary still leaves the allowlist-only world.
            remaining = {"boundary_violated"}
            if outcomes.get("P_url") == "supported":
                remaining.add("url_allowlist_only")
            return remaining, "forbidden_commit"
        if all(value == "supported" for value in outcomes.values()):
            return set(satisfying), "conjunction"
        return set(universe), "boundary_open"
    if family == "P_local_control":
        statuses: list[str] = []
        for channel in CONTROL_NAME:
            decisions = [
                record
                for record in records
                if record.get("kind") == "model_event"
                and record.get("channel") == channel
                and record.get("decision") in {"allow", "deny"}
            ]
            if not decisions:
                statuses.append("unresolved")
                continue
            matched = all(
                record["decision"] == _static_decision(record) for record in decisions
            )
            statuses.append("supported" if matched else "refuted")
        if any(value == "refuted" for value in statuses):
            return {"control_mismatch"}, "decision_mismatch"
        if any(value == "unresolved" for value in statuses):
            return set(universe), "control_open"
        return set(satisfying), "controls_match"
    revocations = [record for record in records if record.get("kind") == "revocation"]
    events = [record for record in records if record.get("kind") == "model_event"]
    if family == "P_decision_entitlement":
        decisions = [
            record for record in events if record.get("decision") in {"allow", "deny"}
        ]
        if not decisions:
            return set(universe), "decision_open"
        if any(
            record["decision"] != _entitled_decision(record, revocations)
            for record in decisions
        ):
            return {"not_entitled"}, "decision_mismatch"
        return set(satisfying), "entitled"
    if family == "P_commit_authorization":
        policy = claim.get("authority_policy")
        if not events or policy not in {"issued_survives_revocation", "revocation_closes_inflight"}:
            return set(universe), "policy_open"
        saw_commit = False
        for record in events:
            if record.get("committed") is not True:
                continue
            if not effect_confirmed(record, claim):
                return set(universe), "effect_unconfirmed"
            saw_commit = True
            if not _commit_authorized(record, revocations, policy):
                return {"commit_unauthorized"}, "unauthorized_commit"
        if saw_commit or claim.get("ledger_declared") is True:
            return set(satisfying), "commits_authorized"
        return set(universe), "policy_open"
    if family == "P_commitment":
        if not events:
            return set(universe), "coverage_open"
        confirmed = [
            record
            for record in events
            if record.get("committed") is True and effect_confirmed(record, claim)
        ]
        unconfirmed = [
            record
            for record in events
            if record.get("committed") is True and not effect_confirmed(record, claim)
        ]
        if confirmed:
            return set(satisfying), "effect_committed"
        if unconfirmed:
            return set(universe), "effect_unconfirmed"
        if claim.get("ledger_declared") is True and _premise_complete(claim):
            return {"no_effect_row"}, "no_effect_row"
        return set(universe), "coverage_open"
    return set(universe), "unsupported_structure"


def _commit_authorized(
    record: Mapping[str, Any],
    revocations: Sequence[Mapping[str, Any]],
    policy: str,
) -> bool:
    if record.get("decision") != "allow":
        return False
    if _entitled_decision(record, revocations) != "allow":
        return False
    grant_id = record.get("grant_id")
    if not isinstance(grant_id, str) or grant_id == "":
        return True
    commit_at = record.get("commit_time", record.get("event_time"))
    if not isinstance(commit_at, int) or not isinstance(record.get("event_time"), int):
        return False
    in_interval = any(
        row.get("grant_id") == grant_id
        and isinstance(row.get("event_time"), int)
        and record["event_time"] < row["event_time"] <= commit_at
        for row in revocations
    )
    if policy == "issued_survives_revocation":
        return True
    if policy == "revocation_closes_inflight":
        return not in_interval
    return False


def _complete_support(record: Mapping[str, Any], claim: Mapping[str, Any]) -> bool:
    if record.get("coverage") == "complete":
        return True
    return _premise_complete(claim)


def _binding_polarity(record: Mapping[str, Any], family: str) -> Any:
    """Polarity of one observation for one family.

    ``family_constraints`` is the family-specific translation. A shared source
    polarity is not reused for a family the observation does not constrain.
    """
    constraints = record.get("family_constraints")
    if isinstance(constraints, Mapping):
        return constraints.get(family, "reports")
    return record.get("polarity")


def _apply_polarity(
    universe: Sequence[str],
    satisfying: frozenset[str],
    records: Sequence[Mapping[str, Any]],
    claim: Mapping[str, Any],
    *,
    family: str,
) -> tuple[set[str], str, list[str]]:
    """Apply support then contradiction in a fixed order (input-order independent)."""
    seen: set[tuple[str, str, str]] = set()
    supports: list[Mapping[str, Any]] = []
    contradicts: list[Mapping[str, Any]] = []
    for record in records:
        polarity = _binding_polarity(record, family)
        if polarity not in {"supports", "contradicts"}:
            continue
        signature = (
            str(record.get("independence_group") or record["id"]),
            polarity,
            str(record.get("channel") or record.get("family") or ""),
        )
        if signature in seen:
            continue
        if polarity == "supports" and not _complete_support(record, claim):
            # Do not consume the signature. A later complete support from the
            # same origin must still bind, independent of record order.
            continue
        seen.add(signature)
        if polarity == "supports":
            supports.append(record)
        else:
            contradicts.append(record)
    if not supports and not contradicts:
        return set(universe), "no_binding_record", []
    compatible = set(universe)
    used: list[str] = []
    reason = "no_binding_record"
    if supports:
        compatible &= set(satisfying)
        used.extend(record["id"] for record in supports)
        reason = "support"
    if contradicts:
        compatible -= set(satisfying)
        used.extend(record["id"] for record in contradicts)
        exercised = any(record.get("exercised_mechanism") is True for record in contradicts)
        reason = "forbidden_commit" if exercised else "text_contradiction"
    return compatible, reason, used


def _apply_grant(
    family: str,
    universe: Sequence[str],
    satisfying: frozenset[str],
    records: Sequence[Mapping[str, Any]],
    claim: Mapping[str, Any],
) -> tuple[set[str], str, list[str]]:
    grants = [record for record in records if record.get("grant") in {"active", "revoked"}]
    if not grants:
        return set(universe), "grant_open", []
    if family == "P_dec":
        decided = [record for record in grants if record.get("decision") in {"allow", "deny"}]
        if not decided:
            return set(universe), "grant_open", []
        outcomes = {
            record["decision"] == _required_decision(record["grant"]) for record in decided
        }
        if outcomes == {True}:
            return set(satisfying), "decision_match", [record["id"] for record in decided]
        if outcomes == {False}:
            return (
                {"decision_incorrect"},
                "decision_mismatch",
                [record["id"] for record in decided],
            )
        return set(universe), "grant_conflict", [record["id"] for record in decided]
    # P_eff
    if any(record["grant"] == "active" for record in grants) and all(
        record["grant"] == "active" for record in grants
    ):
        return set(satisfying), "active_grant", [record["id"] for record in grants]
    if any(record["grant"] != "revoked" for record in grants):
        return set(universe), "grant_conflict", [record["id"] for record in grants]
    observed = [record for record in grants if record.get("effect_committed") in {True, False}]
    if not observed:
        return set(universe), "effect_open", []
    unauthorized = [
        record
        for record in observed
        if record.get("effect_committed") is True and effect_confirmed(record, claim)
    ]
    if unauthorized:
        return (
            {"unauthorized_effect"},
            "unauthorized_commit",
            [record["id"] for record in unauthorized],
        )
    if any(record.get("effect_committed") is True for record in observed):
        return set(universe), "effect_unconfirmed", [record["id"] for record in observed]
    return set(satisfying), "effect_prevented", [record["id"] for record in observed]


def _apply_comparison(
    universe: Sequence[str],
    satisfying: frozenset[str],
    records: Sequence[Mapping[str, Any]],
) -> tuple[set[str], str, list[str]]:
    arms = [record for record in records if record.get("kind") == "comparison_arm"]
    # Completeness must be explicit True; missing outcomes stay unresolved.
    if len(arms) != 2 or any(record.get("evidence_complete") is not True for record in arms):
        return set(universe), "pair_incomplete", []
    if any(record.get("decision") is None for record in arms):
        return set(universe), "pair_incomplete", []
    if any(record.get("property_holds") is None for record in arms):
        return set(universe), "pair_incomplete", []
    used = [record["id"] for record in arms]
    if arms[0].get("decision") != arms[1].get("decision"):
        return {"arms_diverge"}, "equality_divergence", used
    if arms[0].get("property_holds") is True and arms[1].get("property_holds") is True:
        return set(satisfying), "arms_agree", used
    if arms[0].get("property_holds") is False and arms[1].get("property_holds") is False:
        return {"arms_agree_fail"}, "arms_agree_fail", used
    return set(universe), "pair_incomplete", []


def _comparison_axes(records: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    arms = [record for record in records if record.get("kind") == "comparison_arm"]
    if len(arms) != 2:
        return {
            "decision_status": "unknown",
            "effect_status": "unobserved",
            "failure_origin": "undetermined",
        }
    if any(record.get("evidence_complete") is False for record in arms):
        return {
            "decision_status": "unknown",
            "effect_status": "unobserved",
            "failure_origin": "none",
        }
    if arms[0].get("decision") != arms[1].get("decision"):
        return {
            "decision_status": "unknown",
            "effect_status": "not_applicable",
            "failure_origin": "comparison_equality",
        }
    saw_incorrect = False
    confirmed = 0
    for arm in arms:
        grant = arm.get("grant")
        if grant not in {"active", "revoked"}:
            continue
        confirmed += 1
        if arm.get("decision") != _required_decision(grant):
            saw_incorrect = True
    if saw_incorrect:
        decision_status = "incorrect"
    elif confirmed == 2:
        decision_status = "correct"
    else:
        decision_status = "unknown"
    effects = [arm.get("effect_committed") for arm in arms]
    if any(effect is True for effect in effects):
        effect_status = "committed"
    elif all(effect is False for effect in effects):
        effect_status = "prevented"
    else:
        effect_status = "unobserved"
    unauthorized = any(
        arm.get("grant") in {"active", "revoked"}
        and arm.get("effect_committed") is True
        and _required_decision(arm["grant"]) == "deny"
        for arm in arms
    )
    if unauthorized:
        origin = "effect_boundary"
    elif decision_status == "incorrect":
        origin = "decision_policy"
    else:
        origin = "undetermined"
    return {
        "decision_status": decision_status,
        "effect_status": effect_status,
        "failure_origin": origin,
    }


def _violating_decision_status(records: Sequence[Mapping[str, Any]]) -> str:
    """Decision status only on channels whose forbidden effect committed.

    A correct decision on a different channel does not clear the violated one.
    """
    violated: set[str] = set()
    for record in records:
        channel = record.get("channel")
        forbidden = FORBIDDEN_SUBJECT.get(channel)
        if (
            record.get("kind") == "model_event"
            and record.get("committed") is True
            and forbidden is not None
            and record.get("subject_class") == forbidden
        ):
            violated.add(channel)
    if not violated:
        return "unknown"
    comparable = [
        record
        for record in records
        if record.get("channel") in violated and record.get("decision") in {"allow", "deny"}
    ]
    if not comparable:
        return "unknown"
    if any(record["decision"] != _static_decision(record) for record in comparable):
        return "incorrect"
    return "correct"


def _axes(
    *,
    family: str,
    reason: str,
    epistemic: str,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if family == "comparison_equality":
        compared = _comparison_axes(records)
        if reason == "equality_divergence":
            compared["failure_origin"] = "comparison_equality"
            compared["decision_status"] = "unknown"
            compared["effect_status"] = "not_applicable"
        elif reason == "pair_incomplete" or epistemic == "unresolved":
            compared = {
                "decision_status": "unknown",
                "effect_status": "unobserved",
                "failure_origin": "none",
            }
        elif epistemic == "supported":
            compared = {
                "decision_status": "correct",
                "effect_status": "not_applicable",
                "failure_origin": "none",
            }
        return {**compared, "mechanism_exercised": reason == "arms_agree_fail" and compared["failure_origin"] != "undetermined"}
    if epistemic == "supported":
        return {
            "decision_status": "unknown",
            "effect_status": "unobserved",
            "failure_origin": "none",
            "mechanism_exercised": False,
        }
    if reason in {"forbidden_commit", "unauthorized_commit"}:
        return {
            "decision_status": _violating_decision_status(records)
            if reason == "forbidden_commit"
            else "correct",
            "effect_status": "committed",
            "failure_origin": "effect_boundary",
            "mechanism_exercised": True,
        }
    if reason in {"decision_mismatch"}:
        return {
            "decision_status": "incorrect",
            "effect_status": "unobserved",
            "failure_origin": "decision_policy",
            "mechanism_exercised": True,
        }
    if reason == "text_contradiction":
        return {
            "decision_status": "unknown",
            "effect_status": "unobserved",
            "failure_origin": "undetermined",
            "mechanism_exercised": False,
        }
    if reason == "no_effect_row":
        return {
            "decision_status": "unknown",
            "effect_status": "prevented",
            "failure_origin": "undetermined",
            "mechanism_exercised": False,
        }
    return {
        "decision_status": "unknown",
        "effect_status": "unobserved",
        "failure_origin": "none" if epistemic == "unresolved" else "undetermined",
        "mechanism_exercised": False,
    }


def _fault_attribution(
    records: Sequence[Mapping[str, Any]],
    statuses: Mapping[str, str],
    family: str,
    *,
    claim: Mapping[str, Any] | None = None,
    admitted_ids: set[str] | None = None,
) -> str:
    """Only a temporally admitted, in-constraint record can name an actor."""
    actors: list[str] = []
    claim = claim or {}
    for record in records:
        if admitted_ids is not None and record["id"] not in admitted_ids:
            continue
        if record.get("attribute_fault") is not True:
            continue
        if not verification_admits(statuses[record["id"]]):
            continue
        if record.get("temporal_applicability") == "stale":
            continue
        named_family = record.get("proposition_family") or record.get("family")
        if named_family not in {None, family}:
            continue
        if not in_scope(record, family, claim):
            continue
        if record.get("actor_binding") != "bound":
            continue
        if record.get("binding") in {"nonbinding", "unbound", "misbound"}:
            continue
        actor = record.get("named_origin") or record.get("actor_ref")
        if isinstance(actor, str) and actor:
            actors.append(actor)
    unique = set(actors)
    if len(unique) == 1:
        return next(iter(unique))
    return "undetermined"


def _project_conclusion(
    *,
    family: str,
    epistemic: str,
    reason: str,
    mechanism_exercised: bool,
) -> dict[str, Any]:
    if family == "comparison_equality":
        if epistemic == "unresolved" or reason == "pair_incomplete":
            return classify_matched_comparison(
                evidence_complete=False, arms_agree=None, property_holds=None
            )
        if reason == "equality_divergence":
            return classify_matched_comparison(
                evidence_complete=True, arms_agree=False, property_holds=None
            )
        if epistemic == "supported":
            return classify_matched_comparison(
                evidence_complete=True, arms_agree=True, property_holds=True
            )
        return classify_matched_comparison(
            evidence_complete=True, arms_agree=True, property_holds=False
        )
    if epistemic == "unresolved":
        return classify_conclusion(evidence_complete=False, property_holds=None)
    if epistemic == "supported":
        return classify_conclusion(evidence_complete=True, property_holds=True)
    return classify_conclusion(
        evidence_complete=True,
        property_holds=False,
        mechanism_exercised=mechanism_exercised,
    )


def _requirements(
    *,
    epistemic: str,
    compatible: set[str],
    satisfying: frozenset[str],
    verified: bool,
) -> tuple[list[dict[str, str]], dict[str, str] | None]:
    satisfying_left = sorted(compatible & set(satisfying))
    violating_left = sorted(compatible - set(satisfying))
    pair = None
    if satisfying_left and violating_left:
        pair = {"satisfying": satisfying_left[0], "violating": violating_left[0]}
    requirements: list[dict[str, str]] = []
    if epistemic != "unresolved":
        return requirements, pair if epistemic == "unresolved" else None
    if pair is not None:
        requirements.append(
            {
                "requirement": "discriminating_observation",
                "removes_world": pair["violating"],
                "reason": (
                    "An observation that rules out the violating compatible "
                    "world removes this ambiguity. A duplicate of the current "
                    "records does not."
                ),
            }
        )
    if not verified:
        requirements.append(
            {
                "requirement": "admissible_verification",
                "removes_world": "",
                "reason": (
                    "Support and refutation require an authenticity value on "
                    "the allowlist, or a provenance verification method, before "
                    "the compatible set may shrink."
                ),
            }
        )
    return requirements, pair


def _upgrade_blocked(
    records: Sequence[Mapping[str, Any]], support_ids: set[str]
) -> bool:
    blocked = False
    for record in records:
        if record.get("blocks_upgrade") is not True:
            continue
        if not _held_record(record):
            raise ValueError(
                f"{record.get('id')}: unavailable source cannot be an upgrade gate"
            )
        if record["id"] not in support_ids:
            blocked = True
    return blocked


def _base(family: str | None, abstraction: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "family": family,
        "abstraction": finite_abstraction(family) if family in FINITE_ABSTRACTIONS else None,
        "assumptions": list(MEMBERSHIP_ASSUMPTIONS),
        "actual_world_membership": (
            "assumed when the applied constraints are sound; not established by hashes or tests"
        ),
        "real_world_authenticity_certified": False,
        "detection_or_prevention_claimed": False,
        "source_digest_proves_authenticity": False,
        "passing_tests_prove_completeness": False,
        "fabricated": False,
        "stale_is_fabricated": False,
        "sqlite_witness_built": False,
        "declared_abstraction": abstraction is not None,
    }


def bind_family(
    records: Sequence[Mapping[str, Any]],
    *,
    family: str,
    claim: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Translate records into compatible-world constraints and judge the family."""
    claim = dict(claim or {})
    if family not in FINITE_ABSTRACTIONS:
        projected = classify_conclusion(evidence_complete=False, property_holds=None)
        return {
            **_base(family, None),
            "epistemic_status": "unresolved",
            "verified": False,
            "evidence_status": "missing",
            "decision_status": "unknown",
            "effect_status": "unobserved",
            "failure_origin": "none",
            "fault_attribution": "undetermined",
            "conclusion_class": projected["conclusion_class"],
            "finding_label": projected["finding_label"],
            "property_holds": None,
            "reason": (
                f"no finite abstraction for property family {family!r}; "
                "the proposition stays unresolved"
            ),
            "universe": [],
            "satisfying_worlds": [],
            "compatible_worlds": [],
            "evidence_requirements": [
                {
                    "requirement": "finite_abstraction",
                    "removes_world": "",
                    "reason": f"{family} is outside the families this binding defines",
                }
            ],
            "compatible_world_pair": None,
            "independent_origin_count": 0,
            "unavailable_sources": [],
            "authenticity_counts": {},
            "mechanism_exercised": False,
            "comparison_status": "not_applicable",
        }
    abstraction = FINITE_ABSTRACTIONS[family]
    universe = tuple(abstraction["worlds"])
    declared_satisfying = frozenset(abstraction["satisfying_worlds"])
    collapsed, origin_of = collapse_origins(records)
    statuses = {record["id"]: admissibility(record) for record in collapsed}
    in_scope_records = [record for record in collapsed if in_scope(record, family, claim)]
    unavailable = [
        {
            "id": record["id"],
            "availability": record.get("observation_availability")
            or record.get("access_level")
            or "unavailable",
            "blocks_upgrade": False,
        }
        for record in collapsed
        if _unavailable_record(record)
    ]
    authenticity_counts: dict[str, int] = {}
    for record in collapsed:
        name = str(record.get("authenticity") or "missing")
        authenticity_counts[name] = authenticity_counts.get(name, 0) + 1
    misbound = [record for record in in_scope_records if statuses[record["id"]] == "misbound"]
    stale_authentic = [
        record
        for record in in_scope_records
        if statuses[record["id"]] == "admissible"
        and not temporal_record_binds(record, claim)
        and (
            record.get("temporal_applicability") == "stale" or _time_outside(record, claim)
        )
    ]
    origins = {origin_of[record["id"]] for record in in_scope_records}
    common = {
        **_base(family, abstraction),
        "universe": list(universe),
        "satisfying_worlds": list(declared_satisfying),
        "independent_origin_count": len(origins),
        "unavailable_sources": unavailable,
        "authenticity_counts": authenticity_counts,
        "stale_record_ids": [record["id"] for record in stale_authentic],
        "fabricated": False,
        "stale_is_fabricated": False,
    }
    if misbound:
        requirements, pair = _requirements(
            epistemic="unresolved",
            compatible=set(),
            satisfying=declared_satisfying,
            verified=False,
        )
        projected = classify_conclusion(evidence_complete=False, property_holds=None)
        axes = diagnosis(
            evidence_status="misbound",
            decision_status="unknown",
            effect_status="unobserved",
            failure_origin="evidence",
        )
        return {
            **common,
            "epistemic_status": "unresolved",
            "verified": False,
            "compatible_worlds": [],
            "evidence_requirements": requirements,
            "compatible_world_pair": pair,
            "reason": (
                "in-scope authenticity is misbound or spoofed; the compatible "
                "set is empty and the proposition is unresolved"
            ),
            "conclusion_class": projected["conclusion_class"],
            "finding_label": projected["finding_label"],
            "property_holds": None,
            "fault_attribution": "undetermined",
            "mechanism_exercised": False,
            "comparison_status": "not_applicable",
            **axes,
        }

    admitted = _admitted(in_scope_records, statuses, claim)
    minimum = int(claim.get("minimum_independent_groups") or 1)
    admitted_origins = {origin_of[record["id"]] for record in admitted}
    enough_origins = len(admitted_origins) >= minimum if admitted else False
    if not enough_origins:
        admitted_for_constraints: list[dict[str, Any]] = []
    else:
        admitted_for_constraints = admitted

    model_records = [
        record
        for record in admitted_for_constraints
        if record.get("kind") in {"model_event", "revocation"}
    ]
    if not admitted_for_constraints:
        compatible, reason, used = set(universe), "no_binding_record", []
    elif family == "comparison_equality":
        compatible, reason, used = _apply_comparison(
            universe, declared_satisfying, admitted_for_constraints
        )
    elif family in {"P_dec", "P_eff"} and any(
        record.get("grant") in {"active", "revoked"} for record in admitted_for_constraints
    ):
        compatible, reason, used = _apply_grant(
            family, universe, declared_satisfying, admitted_for_constraints, claim
        )
    elif model_records and family in STRUCTURAL_FAMILIES:
        compatible, reason = _apply_model(
            family, universe, declared_satisfying, admitted_for_constraints, claim
        )
        used = [record["id"] for record in model_records] if reason not in {
            "channel_open",
            "boundary_open",
            "control_open",
            "decision_open",
            "policy_open",
            "coverage_open",
            "effect_unconfirmed",
        } else []
        if reason in {"channel_clear", "conjunction", "controls_match", "entitled", "commits_authorized", "effect_committed"}:
            used = [record["id"] for record in model_records]
    else:
        compatible, reason, used = _apply_polarity(
            universe, declared_satisfying, admitted_for_constraints, claim, family=family
        )

    support_ids = set(used) if reason in {
        "channel_clear",
        "conjunction",
        "controls_match",
        "entitled",
        "commits_authorized",
        "effect_committed",
        "support",
        "decision_match",
        "active_grant",
        "effect_prevented",
        "arms_agree",
    } else set()
    blocked = _upgrade_blocked(in_scope_records, support_ids)
    verified = bool(used) and enough_origins
    verdict_worlds = property_worlds_for(family)
    epistemic = production_verdict(
        verdict_worlds, frozenset(compatible), verified=verified
    )
    if epistemic == "supported" and blocked:
        epistemic = "unresolved"
        verified = False
        reason = "upgrade_blocked"
    axes_body = _axes(
        family=family, reason=reason, epistemic=epistemic, records=admitted
    )
    if reason == "upgrade_blocked":
        axes_body["failure_origin"] = "evidence"
        axes_body["mechanism_exercised"] = False
    projected = _project_conclusion(
        family=family,
        epistemic=epistemic,
        reason=reason,
        mechanism_exercised=bool(axes_body["mechanism_exercised"]),
    )
    if epistemic == "unresolved" and blocked:
        evidence_status = "unverified"
    elif any(statuses[record["id"]] == "admissible" for record in in_scope_records):
        evidence_status = "authentic"
    else:
        evidence_status = "missing"
    if epistemic == "unresolved" and evidence_status == "authentic" and not used:
        # Admissible bytes that do not bind, including authentic stale rows.
        pass
    requirements, pair = _requirements(
        epistemic=epistemic,
        compatible=compatible,
        satisfying=declared_satisfying,
        verified=verified,
    )
    if stale_authentic and epistemic == "unresolved":
        requirements.append(
            {
                "requirement": "temporally_applicable_record",
                "removes_world": "",
                "reason": (
                    "Authentic stale evidence does not bind the target time "
                    "and is not fabricated evidence."
                ),
            }
        )
    diagnosis_axes = diagnosis(
        evidence_status=evidence_status,  # type: ignore[arg-type]
        decision_status=axes_body["decision_status"],  # type: ignore[arg-type]
        effect_status=axes_body["effect_status"],  # type: ignore[arg-type]
        failure_origin=axes_body["failure_origin"],  # type: ignore[arg-type]
    )
    comparison_status = "not_applicable"
    if family == "comparison_equality":
        if reason == "equality_divergence":
            comparison_status = "divergent"
        elif reason == "arms_agree" or reason == "arms_agree_fail":
            comparison_status = "agree"
        else:
            comparison_status = "incomplete"
    return {
        **common,
        "epistemic_status": epistemic,
        "verified": verified,
        "compatible_worlds": sorted(compatible),
        "evidence_requirements": requirements,
        "compatible_world_pair": pair,
        "reason": reason,
        "conclusion_class": projected["conclusion_class"],
        "finding_label": projected["finding_label"],
        "property_holds": projected["property_holds"],
        "fault_attribution": _fault_attribution(
            in_scope_records,
            statuses,
            family,
            claim=claim,
            admitted_ids={record["id"] for record in admitted_for_constraints},
        ),
        "mechanism_exercised": bool(axes_body["mechanism_exercised"]),
        "comparison_status": comparison_status,
        "independent_origin_count": len(admitted_origins) if admitted else len(origins),
        **diagnosis_axes,
    }


def records_from_property_case(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flatten one retained property-graph case. Does not score it."""
    ledger = {
        row["event_id"]: row for row in case.get("effect_ledger") or [] if row.get("event_id")
    }
    records: list[dict[str, Any]] = []
    for event in case.get("events") or []:
        row = ledger.get(event["id"])
        records.append(
            {
                "id": event["id"],
                "kind": "model_event",
                "authenticity": event.get("authenticity"),
                "channel": event.get("channel"),
                "subject_class": event.get("subject_class"),
                "decision": event.get("decision"),
                "committed": bool(row and row.get("committed")),
                "commit_subject": (row or {}).get("subject_class", event.get("subject_class")),
                "commit_time": (row or {}).get("commit_time", event.get("time")),
                "grant_id": event.get("grant_id"),
                "event_time": event.get("time"),
                "time_basis": "source_stated" if event.get("time") is not None else "missing",
                "independence_group": f"{case.get('id')}:{event.get('channel')}:{event['id']}",
                "actor_ref": event.get("subject_class"),
                "object_scope": event.get("subject_class"),
                "action": event.get("channel"),
                "polarity": "reports",
                "locally_held": True,
                "access_level": "model_ledger",
                "observation_availability": "available",
            }
        )
    for revocation in case.get("revocations") or []:
        records.append(
            {
                "id": revocation["id"],
                "kind": "revocation",
                "authenticity": revocation.get("authenticity"),
                "grant_id": revocation.get("grant_id"),
                "event_time": revocation.get("time"),
                "time_basis": "source_stated"
                if revocation.get("time") is not None
                else "missing",
                "independence_group": f"{case.get('id')}:revocation:{revocation['id']}",
                "polarity": "reports",
                "locally_held": True,
                "access_level": "model_ledger",
                "observation_availability": "available",
            }
        )
    return records


def binding_from_property_case(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "observed_channels": list(case.get("observed_channels") or []),
        "authority_policy": case.get("authority_policy"),
        "ledger_declared": "effect_ledger" in case,
        "completeness_premise": {
            "declared": True,
            "operation": "model_effect_ledger",
            "completeness": "complete",
            "interval": {"start": None, "end": None},
        },
        "case_id": case.get("id"),
    }


def load_property_case(root: Path | None = None, case_id: str = "url_held_worker_local_read") -> dict[str, Any]:
    root = root or repo_root()
    payload = json.loads(
        (root / "experiments" / "incident_properties" / "fixtures.json").read_text(
            encoding="utf-8"
        )
    )
    for case in payload.get("cases") or []:
        if case.get("id") == case_id:
            return case
    raise KeyError(case_id)


_NATIVE_KIND_TO_FAMILY: dict[str, str] = {
    "transcript_visible_command": "P_local_control",
    "committed_effect": "P_commitment",
    "independent_service_log": "P_commitment",
    "grant_revocation": "P_decision_entitlement",
}

_NATIVE_KIND_TO_CHANNEL: dict[str, str] = {
    "transcript_visible_command": "remote_url",
    "committed_effect": "downstream_effect",
    "independent_service_log": "downstream_effect",
}


def _public_fields(text: Any) -> dict[str, str]:
    if not isinstance(text, str):
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key] = value
    return fields


def _commit_family_constraints(
    event: Mapping[str, Any], channel: str | None, fields: Mapping[str, str]
) -> dict[str, str]:
    """One committed row, one polarity per family.

    Commit existence supports ``P_commitment``. The same row refutes effect
    safety, and commit authorization, when the subject is that channel's
    forbidden class. An allowed subject clears only its own channel. It does
    not support ``P_system``, and it is not an authorization proof.
    """
    source = event.get("polarity") or "reports"
    if source == "contradicts":
        commitment = "contradicts"
    elif source == "supports":
        commitment = "supports"
    else:
        commitment = "reports"
    constraints = {"P_commitment": commitment}
    observed = fields.get("channel") or channel
    subject = fields.get("subject_class")
    prop = PROPERTY_OF_CHANNEL.get(str(observed)) if observed else None
    forbidden = FORBIDDEN_SUBJECT.get(str(observed)) if observed else None
    if prop and forbidden and subject == forbidden:
        constraints[prop] = "contradicts"
        constraints["P_system"] = "contradicts"
        constraints["P_commit_authorization"] = "contradicts"
    elif (
        prop
        and subject
        and observed in CHANNEL_SUBJECTS
        and subject in CHANNEL_SUBJECTS[str(observed)]
    ):
        constraints[prop] = "supports"
    return constraints


def records_from_native_packet(directory: Path, *, salt: str = SOURCE_PIN) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load a native-witness origin packet. Does not invent the SQLite export.

    Maps event kinds onto the declared family/channel selectors so ``in_scope``
    can admit them. Digest-verified application-owned rows become admissible;
    actor-only packets without a service origin stay non-deciding.
    """
    loaded = load_origin_packet(directory, salt=salt)
    service_missing = any(
        origin.get("origin") == "service_effect" and int(origin.get("rows") or 0) == 0
        for origin in loaded["missing_origins"]
    )
    has_coverage = any(
        event.get("event_kind") == "independent_service_log" for event in loaded["events"]
    )
    records: list[dict[str, Any]] = []
    for event in loaded["events"]:
        raw = event.get("raw_reference") or {}
        kind = event.get("event_kind") or "native"
        family = _NATIVE_KIND_TO_FAMILY.get(str(kind))
        parsed = _public_fields(event.get("public_bytes"))
        channel = event.get("channel") or _NATIVE_KIND_TO_CHANNEL.get(str(kind))
        if kind == "committed_effect" and parsed.get("channel"):
            channel = parsed["channel"]
        applies = []
        if family:
            applies.append(family)
        constraints = None
        if kind == "committed_effect":
            # Do not copy "the row exists" onto safety or authorization.
            constraints = _commit_family_constraints(event, channel, parsed)
            for name in constraints:
                if name not in applies:
                    applies.append(name)
        elif kind == "transcript_visible_command":
            applies.extend(["P_system", "P_url", "P_effect"])
        method = event.get("verification_method") or "none"
        # Only application-owned sink rows become deciding. Legacy telemetry
        # independent_service_log digests stay not_checked / non-deciding.
        digest_verified = (
            kind == "committed_effect"
            and method == "independent_log_digest"
            and not service_missing
        )
        authenticity = event.get("authenticity") or "not_checked"
        if digest_verified and authenticity in NON_DECIDING_AUTHENTICITY:
            authenticity = "byte_identified"
        coverage = event.get("coverage")
        if coverage in (None, "", "partial") and digest_verified and has_coverage:
            coverage = "complete"
        elif not coverage:
            coverage = "partial"
        records.append(
            {
                "id": event["id"],
                "kind": "native",
                "family": family,
                "channel": channel,
                "applies_to_families": applies,
                "authenticity": authenticity,
                "verified": bool(digest_verified),
                "verification_method": method,
                "independence_group": event.get("independence_group") or event["id"],
                "content_digest": event.get("source_digest"),
                "depends_on": list(event.get("depends_on") or []),
                "duplicate_of": raw.get("duplicate_of"),
                "event_time": event.get("event_time"),
                "time_basis": event.get("time_basis") or "missing",
                "actor_ref": event.get("actor_ref"),
                "object_scope": event.get("object_scope"),
                "action": event.get("action"),
                "subject_class": parsed.get("subject_class"),
                "polarity": event.get("polarity") or "reports",
                "family_constraints": constraints,
                "exercised_mechanism": bool(
                    constraints
                    and constraints.get("P_effect") == "contradicts"
                ),
                "access_level": event.get("access_level"),
                "locally_held": event.get("locally_held"),
                "observation_availability": "available"
                if event.get("public_bytes")
                else "unobserved",
                "coverage": coverage,
            }
        )
    return records, {
        "missing_origins": list(loaded["missing_origins"]),
        "truth_files_read": list(loaded["truth_files_read"]),
        "event_count": len(loaded["events"]),
        "service_origin_present": not service_missing,
    }


def records_from_lineage(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalized provenance observations. Verification is the method, not the digest."""
    normalized = normalize_lineage(dict(graph))
    sources = {node["id"]: node for node in graph["source_records"]}
    events = {node["id"]: node for node in graph["observed_events"]}
    records: list[dict[str, Any]] = []
    for item in normalized["observations"]:
        event = events[item["event_id"]]
        necessary = event["necessary_source_ids"]
        primary = sources[necessary[0]] if necessary else None
        records.append(
            {
                "id": item["event_id"],
                "kind": "lineage",
                "verified": event_verified(event, sources),
                "authenticity": event["authenticity"],
                "polarity": event["polarity"],
                "event_kind": event["event_kind"],
                "independence_group": item["independence_group"],
                "content_digest": item["content_digest"],
                "depends_on": list(primary["depends_on"]) if primary else [],
                "duplicate_of": primary.get("duplicate_of") if primary else None,
                "event_time": item["event_time"],
                "time_basis": event["time_basis"],
                "temporal_applicability": item["temporal_applicability"],
                "scope_binding": item["scope_binding"],
                "actor_ref": event.get("actor_ref"),
                "actor_binding": event.get("actor_binding"),
                "observation_availability": item["observation_availability"],
                "access_level": primary["access_level"] if primary else "unknown",
                "locally_held": primary.get("locally_held") if primary else False,
                "source_id": primary["id"] if primary else None,
            }
        )
    return records


def _reject_bitmasks(observations: Mapping[str, Any]) -> None:
    if "records" in observations:
        return
    if "property_mask" in observations or "evidence_mask" in observations:
        raise ValueError(
            "manually supplied bitmasks are not an audit; provide retained records"
        )
    raise ValueError("run observations need retained records")


def audit_claim_run(claim: Mapping[str, Any], run: Mapping[str, Any]) -> dict[str, Any]:
    """Production Claim/Run entrypoint.

    The run must carry retained records. A property mask and an evidence mask
    are not a substitute.
    """
    validate_claim(dict(claim))
    validate_run(dict(run))
    observations = run["observations"]
    _reject_bitmasks(observations)
    records = observations.get("records")
    if not isinstance(records, list):
        raise ValueError("run observations.records must be a list")
    binding = dict(observations.get("binding") or {})
    family = binding.get("family") or observations.get("family")
    if not isinstance(family, str) or family == "":
        raise ValueError("run observations need a property family")
    result = bind_family(records, family=family, claim=binding)
    result["claim_id"] = claim["id"]
    result["run_id"] = run["id"]
    return result


def audit_retained_workflow(
    root: Path | None = None,
    *,
    case_id: str = "url_held_worker_local_read",
    family: str = "P_system",
) -> dict[str, Any]:
    """Judge one retained property-graph workflow through the adapter."""
    case = load_property_case(root, case_id)
    records = records_from_property_case(case)
    binding = binding_from_property_case(case)
    result = bind_family(records, family=family, claim=binding)
    result["case_id"] = case_id
    result["input"] = "retained_workflow"
    return result


def audit_native_packet(
    root: Path | None = None,
    *,
    family: str = "P_system",
    directory: Path | None = None,
) -> dict[str, Any]:
    """Judge a native-witness origin packet. Does not build a SQLite witness."""
    root = root or repo_root()
    if directory is None:
        directory = root / "experiments" / "telemetry" / "packet"
    records, meta = records_from_native_packet(directory)
    result = bind_family(records, family=family, claim={})
    result["input"] = "native_witness_packet"
    result["packet_directory"] = str(directory)
    result["event_count"] = meta["event_count"]
    result["missing_origins"] = meta["missing_origins"]
    result["truth_files_read"] = meta["truth_files_read"]
    result["admitted_for_family"] = sum(
        1 for record in records if in_scope(record, family, {})
    )
    return result


def audit_entrypoint(root: Path | None = None) -> dict[str, Any]:
    """Normal entrypoint: retained workflow, legacy telemetry, and effect witness."""
    root = root or repo_root()
    system = audit_retained_workflow(root, family="P_system")
    url = audit_retained_workflow(root, family="P_url")
    native = audit_native_packet(root)
    witness_dir = (
        root
        / "evidence"
        / "effect_witness_v1"
        / "packets"
        / "aew-v1-h-local-pass-broader-effect"
        / "discriminating_readback"
    )
    actor_only_dir = (
        root
        / "evidence"
        / "effect_witness_v1"
        / "packets"
        / "aew-v1-h-local-pass-broader-effect"
        / "actor_only"
    )
    effect_witness = None
    effect_actor_only = None
    if witness_dir.is_dir():
        effect_witness = audit_native_packet(
            root, family="P_commitment", directory=witness_dir
        )
        effect_witness["input"] = "application_effect_discriminating_packet"
    if actor_only_dir.is_dir():
        effect_actor_only = audit_native_packet(
            root, family="P_commitment", directory=actor_only_dir
        )
        effect_actor_only["input"] = "application_effect_actor_only_packet"
    return {
        "protocol_id": PROTOCOL_ID,
        "retained_system": system,
        "retained_url": url,
        "native": native,
        "effect_witness_discriminating": effect_witness,
        "effect_witness_actor_only": effect_actor_only,
        "url_allowlist_supports_p_system": system["epistemic_status"] == "supported",
        "real_world_authenticity_certified": False,
        "detection_or_prevention_claimed": False,
        "sqlite_witness_built": False,
    }


def finding_shell(
    *,
    finding_id: str,
    claim_id: str,
    run_ids: Sequence[str],
    proposition: str,
    scope: str,
    label: str,
    supporting_observation_refs: Sequence[str],
) -> dict[str, Any]:
    payload = {
        "id": finding_id,
        "claim_id": claim_id,
        "run_ids": list(run_ids),
        "proposition": proposition,
        "scope": scope,
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": list(supporting_observation_refs),
    }
    validate_finding(payload)
    return payload
