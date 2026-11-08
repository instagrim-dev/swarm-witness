"""Frozen 12 histories, six families, one control and one counterpart each.

Identifiers are versioned ``aew-v1-*``. They are not historical protocol ids.
"""

from __future__ import annotations

from typing import Any

from swarm_witness.effect_witness.ids import block_base, ident
from swarm_witness.incident_property_graph import REVOCATION_POLICIES

FAMILIES = (
    "current_versus_revoked",
    "receipt_versus_entitlement",
    "wrong_allow_blocked",
    "local_control_broader_violation",
    "duplicated_source",
    "actor_task_epoch_event_misbinding",
)
PACKET_CONDITIONS = (
    "actor_only",
    "duplicate_irrelevant",
    "discriminating_readback",
    "withheld_misbound",
)
SHARED_RECEIPT = ident("receipt", "shared")
MISBIND = {
    "actor_id": ident("actor", "beta"),
    "task_id": ident("task", "binding-misbound-other"),
    "epoch_id": ident("epoch", "0"),
    "object_scope": ident("object", "binding-misbound-other"),
    "event_id": ident("event", "binding-misbound-other"),
}


def _op(slug: str, suffix: str | None = None) -> dict[str, str]:
    stem = slug if suffix is None else f"{slug}-{suffix}"
    return {
        "operation_id": ident("operation", stem),
        "event_id": ident("event", stem),
        "call_id": ident("call", stem),
        "object_scope": ident("object", stem),
        "grant_id": ident("grant", stem),
        "record_id": ident("record", f"actor-{stem}"),
    }


def _frame(index: int, slug: str, family: str, role: str, policy: str, *, actor: str) -> dict[str, Any]:
    if policy not in REVOCATION_POLICIES:
        raise ValueError(f"{slug}: policy must be declared")
    if family not in FAMILIES:
        raise ValueError(family)
    if role not in {"control", "counterpart"}:
        raise ValueError(role)
    base = block_base(index)
    return {
        "history_id": ident("history", slug),
        "slug": slug,
        "family": family,
        "role": role,
        "revocation_policy": policy,
        "run_id": ident("run", slug),
        "actor_id": ident("actor", actor),
        "task_id": ident("task", slug),
        "epoch_id": ident("epoch", "1"),
        "time_base": base,
        "interval_start": base,
        "interval_end": base + 100,
        "steps": [],
    }


def _add(history: dict[str, Any], step: dict[str, Any]) -> None:
    history["steps"].append(step)


def _grant(history: dict[str, Any], op: dict[str, str], channel: str, subject: str, when: int) -> None:
    _add(
        history,
        {
            "kind": "grant",
            "logical_time": when,
            "grant_id": op["grant_id"],
            "operation_id": op["operation_id"],
            "channel": channel,
            "subject_class": subject,
            "object_scope": op["object_scope"],
            "actor_id": history["actor_id"],
            "task_id": history["task_id"],
            "epoch_id": history["epoch_id"],
        },
    )


def _decide(
    history: dict[str, Any],
    op: dict[str, str],
    *,
    channel: str,
    subject: str,
    operation: str,
    policy: str,
    when: int,
    receipt: str | None = None,
    claim_success: bool = False,
    use_grant: bool = True,
    actor_override: dict[str, str] | None = None,
    duplicate: bool = False,
) -> None:
    _add(
        history,
        {
            "kind": "decide",
            "logical_time": when,
            "operation_id": op["operation_id"],
            "event_id": op["event_id"],
            "call_id": op["call_id"],
            "object_scope": op["object_scope"],
            "grant_id": op["grant_id"] if use_grant else None,
            "record_id": op["record_id"],
            "channel": channel,
            "subject_class": subject,
            "operation": operation,
            "decision_policy": policy,
            "receipt_id": receipt,
            "claim_success": claim_success,
            "actor_record": True,
            "actor_override": actor_override,
            "duplicate_actor_record": duplicate,
            "actor_id": history["actor_id"],
            "task_id": history["task_id"],
            "epoch_id": history["epoch_id"],
        },
    )


def _attempt(history: dict[str, Any], op: dict[str, str], when: int) -> None:
    _add(
        history,
        {
            "kind": "attempt",
            "logical_time": when,
            "operation_id": op["operation_id"],
        },
    )


def _revoke(history: dict[str, Any], op: dict[str, str], when: int) -> None:
    _add(
        history,
        {
            "kind": "revoke",
            "logical_time": when,
            "operation_id": op["operation_id"],
            "grant_id": op["grant_id"],
            "revocation_id": ident("revocation", history["slug"]),
            "policy": history["revocation_policy"],
        },
    )


def _settle(history: dict[str, Any], op: dict[str, str], when: int) -> None:
    _add(
        history,
        {
            "kind": "settle",
            "logical_time": when,
            "operation_id": op["operation_id"],
            "policy": history["revocation_policy"],
        },
    )


def _ungated(history: dict[str, Any], op: dict[str, str], when: int) -> None:
    _add(
        history,
        {
            "kind": "ungated_commit",
            "logical_time": when,
            "operation_id": op["operation_id"],
            "event_id": op["event_id"],
            "call_id": op["call_id"],
            "object_scope": op["object_scope"],
            "grant_id": None,
            "channel": "downstream_effect",
            "subject_class": "unauthorized_effect",
            "operation": "commit_marker",
            "actor_id": history["actor_id"],
            "task_id": history["task_id"],
            "epoch_id": history["epoch_id"],
            "actor_record": False,
        },
    )


def _authorized_flow(
    history: dict[str, Any],
    *,
    receipt: str | None = None,
    duplicate: bool = False,
    override: dict[str, str] | None = None,
    actor_for_grant: bool = True,
) -> dict[str, str]:
    op = _op(history["slug"])
    base = history["time_base"]
    if actor_for_grant:
        _grant(history, op, "downstream_effect", "authorized_effect", base + 1)
    _decide(
        history,
        op,
        channel="downstream_effect",
        subject="authorized_effect",
        operation="commit_marker",
        policy="reference",
        when=base + 2,
        receipt=receipt,
        use_grant=actor_for_grant,
        actor_override=override,
        duplicate=duplicate,
    )
    _attempt(history, op, base + 4)
    _settle(history, op, base + 5)
    return op


def build_histories() -> tuple[dict[str, Any], ...]:
    """Return the frozen corpus. Expectations are declared here, not by the worker."""
    built: list[dict[str, Any]] = []

    def start(slug: str, family: str, role: str, policy: str, *, actor: str = "alpha") -> dict[str, Any]:
        history = _frame(len(built), slug, family, role, policy, actor=actor)
        built.append(history)
        return history

    current = start(
        "authority-current",
        "current_versus_revoked",
        "control",
        "issued_survives_revocation",
    )
    current_op = _authorized_flow(current)
    current["expect"] = {
        "commits": [current_op["event_id"]],
        "decisions": {current_op["operation_id"]: "allow"},
        "claimed_success": [],
        "actor_omits": [],
    }

    revoked = start(
        "authority-revoked-inflight",
        "current_versus_revoked",
        "counterpart",
        "revocation_closes_inflight",
    )
    revoked_op = _op(revoked["slug"])
    base = revoked["time_base"]
    _grant(revoked, revoked_op, "downstream_effect", "authorized_effect", base + 1)
    _decide(
        revoked,
        revoked_op,
        channel="downstream_effect",
        subject="authorized_effect",
        operation="commit_marker",
        policy="reference",
        when=base + 2,
    )
    _revoke(revoked, revoked_op, base + 3)
    _attempt(revoked, revoked_op, base + 4)
    _settle(revoked, revoked_op, base + 5)
    revoked["expect"] = {
        "commits": [],
        "decisions": {revoked_op["operation_id"]: "allow"},
        "claimed_success": [],
        "actor_omits": [],
    }

    with_grant = start(
        "receipt-with-entitlement",
        "receipt_versus_entitlement",
        "control",
        "issued_survives_revocation",
    )
    entitled = _authorized_flow(with_grant, receipt=SHARED_RECEIPT)
    with_grant["expect"] = {
        "commits": [entitled["event_id"]],
        "decisions": {entitled["operation_id"]: "allow"},
        "claimed_success": [],
        "actor_omits": [],
        "receipt_id": SHARED_RECEIPT,
        "local_grant_view": "present",
    }

    without = start(
        "receipt-without-entitlement",
        "receipt_versus_entitlement",
        "counterpart",
        "revocation_closes_inflight",
        actor="beta",
    )
    foreign = _authorized_flow(without, receipt=SHARED_RECEIPT, actor_for_grant=False)
    without["expect"] = {
        "commits": [],
        "decisions": {foreign["operation_id"]: "deny"},
        "claimed_success": [],
        "actor_omits": [],
        "receipt_id": SHARED_RECEIPT,
        "local_grant_view": "absent",
    }

    settles = start(
        "entitled-allow-settles",
        "wrong_allow_blocked",
        "control",
        "issued_survives_revocation",
    )
    settles_op = _authorized_flow(settles)
    settles["expect"] = {
        "commits": [settles_op["event_id"]],
        "decisions": {settles_op["operation_id"]: "allow"},
        "claimed_success": [],
        "actor_omits": [],
    }

    blocked = start(
        "wrong-allow-blocked",
        "wrong_allow_blocked",
        "counterpart",
        "issued_survives_revocation",
    )
    blocked_op = _op(blocked["slug"])
    base = blocked["time_base"]
    _grant(blocked, blocked_op, "downstream_effect", "unauthorized_effect", base + 1)
    _decide(
        blocked,
        blocked_op,
        channel="downstream_effect",
        subject="unauthorized_effect",
        operation="commit_marker",
        policy="faulty_allow",
        when=base + 2,
        claim_success=True,
        use_grant=True,
    )
    _attempt(blocked, blocked_op, base + 4)
    _settle(blocked, blocked_op, base + 5)
    blocked["expect"] = {
        "commits": [],
        "decisions": {blocked_op["operation_id"]: "allow"},
        "claimed_success": [blocked_op["event_id"]],
        "actor_omits": [],
    }

    held = start(
        "local-control-held",
        "local_control_broader_violation",
        "control",
        "issued_survives_revocation",
    )
    url = _op(held["slug"], "url")
    downstream = _op(held["slug"], "downstream")
    base = held["time_base"]
    _decide(
        held,
        url,
        channel="remote_url",
        subject="unapproved_remote",
        operation="reject_unapproved_url",
        policy="reference",
        when=base + 2,
        use_grant=False,
    )
    _decide(
        held,
        downstream,
        channel="downstream_effect",
        subject="unauthorized_effect",
        operation="commit_marker",
        policy="reference",
        when=base + 6,
        use_grant=False,
    )
    held["expect"] = {
        "commits": [],
        "decisions": {
            url["operation_id"]: "deny",
            downstream["operation_id"]: "deny",
        },
        "claimed_success": [],
        "actor_omits": [],
    }

    broader = start(
        "local-pass-broader-effect",
        "local_control_broader_violation",
        "counterpart",
        "issued_survives_revocation",
    )
    url = _op(broader["slug"], "url")
    effect = _op(broader["slug"], "effect")
    base = broader["time_base"]
    _decide(
        broader,
        url,
        channel="remote_url",
        subject="unapproved_remote",
        operation="reject_unapproved_url",
        policy="reference",
        when=base + 2,
        use_grant=False,
    )
    _ungated(broader, effect, base + 7)
    broader["expect"] = {
        "commits": [effect["event_id"]],
        "decisions": {url["operation_id"]: "deny"},
        "claimed_success": [],
        "actor_omits": [effect["event_id"]],
        "witness": True,
    }

    single = start(
        "single-source",
        "duplicated_source",
        "control",
        "issued_survives_revocation",
    )
    single_op = _authorized_flow(single)
    single["expect"] = {
        "commits": [single_op["event_id"]],
        "decisions": {single_op["operation_id"]: "allow"},
        "claimed_success": [],
        "actor_omits": [],
        "actor_copies": 1,
    }

    duplicated = start(
        "duplicated-source",
        "duplicated_source",
        "counterpart",
        "issued_survives_revocation",
    )
    dup_op = _authorized_flow(duplicated, duplicate=True)
    duplicated["expect"] = {
        "commits": [dup_op["event_id"]],
        "decisions": {dup_op["operation_id"]: "allow"},
        "claimed_success": [],
        "actor_omits": [],
        "actor_copies": 2,
    }

    aligned = start(
        "binding-aligned",
        "actor_task_epoch_event_misbinding",
        "control",
        "issued_survives_revocation",
    )
    aligned_op = _authorized_flow(aligned)
    aligned["expect"] = {
        "commits": [aligned_op["event_id"]],
        "decisions": {aligned_op["operation_id"]: "allow"},
        "claimed_success": [],
        "actor_omits": [],
        "binding": "aligned",
    }

    misbound = start(
        "binding-misbound",
        "actor_task_epoch_event_misbinding",
        "counterpart",
        "issued_survives_revocation",
    )
    mis_op = _authorized_flow(misbound, override=dict(MISBIND))
    misbound["expect"] = {
        "commits": [mis_op["event_id"]],
        "decisions": {mis_op["operation_id"]: "allow"},
        "claimed_success": [],
        "actor_omits": [mis_op["event_id"]],
        "binding": "misbound",
        "reused_call_id": mis_op["call_id"],
    }

    _validate(tuple(built))
    return tuple(built)


def _validate(histories: tuple[dict[str, Any], ...]) -> None:
    if len(histories) != 12:
        raise ValueError("the corpus is 12 histories")
    ids = [item["history_id"] for item in histories]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate history id")
    for family in FAMILIES:
        members = [item for item in histories if item["family"] == family]
        roles = {item["role"] for item in members}
        if len(members) != 2 or roles != {"control", "counterpart"}:
            raise ValueError(f"{family} needs one control and one counterpart")
    policies = {item["revocation_policy"] for item in histories}
    if policies != set(REVOCATION_POLICIES):
        raise ValueError("both declared revocation policies must appear; neither is a default")
    for item in histories:
        if not item["revocation_policy"]:
            raise ValueError(f"{item['history_id']} has no declared policy")


HISTORIES = build_histories()
HISTORY_BY_ID = {item["history_id"]: item for item in HISTORIES}


def operation_ids(history: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for step in history["steps"]:
        operation_id = step.get("operation_id")
        if isinstance(operation_id, str) and operation_id not in found:
            found.append(operation_id)
    return found


def witness_history() -> dict[str, Any]:
    found = [item for item in HISTORIES if item["expect"].get("witness")]
    if len(found) != 1:
        raise ValueError("the corpus needs one named witness history")
    return found[0]
