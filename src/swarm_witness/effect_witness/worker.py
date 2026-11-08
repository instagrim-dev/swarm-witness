"""Deterministic local worker. It does not hand its allow flag to the observer."""

from __future__ import annotations

from typing import Any

from swarm_witness.effect_witness.records import actor_body, actor_row, parse_body
from swarm_witness.effect_witness.sink import EffectSink, static_decision
from swarm_witness.incident_property_graph import REVOCATION_POLICIES


def decide_action(step: dict[str, Any], grant: dict[str, Any] | None) -> str:
    """Local decision. A receipt is not read. There is no commit flag."""
    if step["decision_policy"] == "faulty_allow":
        return "allow"
    if step["decision_policy"] != "reference":
        raise ValueError(f"unknown decision policy {step['decision_policy']}")
    expected = static_decision(step["channel"], step["subject_class"])
    if expected == "deny":
        return "deny"
    if grant is None:
        return "deny"
    for key in (
        "actor_id",
        "task_id",
        "epoch_id",
        "operation_id",
        "channel",
        "subject_class",
        "object_scope",
    ):
        if grant.get(key) != step.get(key):
            return "deny"
    return "allow"


def _claimed_result(step: dict[str, Any], decision: str) -> str:
    if step.get("claim_success"):
        return "success"
    if decision == "allow":
        return "allowed"
    return "denied"


def _will_attempt(history: dict[str, Any], operation_id: str) -> bool:
    return any(
        item["kind"] == "attempt" and item["operation_id"] == operation_id
        for item in history["steps"]
    )


def _actor_fields(history: dict[str, Any], step: dict[str, Any], decision: str, grant_view: str) -> dict[str, Any]:
    override = step.get("actor_override") or {}
    return {
        "history_id": history["history_id"],
        "run_id": history["run_id"],
        "operation_id": step["operation_id"],
        "event_id": override.get("event_id", step["event_id"]),
        "call_id": step["call_id"],
        "actor_id": override.get("actor_id", step["actor_id"]),
        "task_id": override.get("task_id", step["task_id"]),
        "grant_id": step.get("grant_id"),
        "epoch_id": override.get("epoch_id", step["epoch_id"]),
        "channel": step["channel"],
        "subject_class": step["subject_class"],
        "operation": step["operation"],
        "object_scope": override.get("object_scope", step["object_scope"]),
        "decision": decision,
        "claimed_result": _claimed_result(step, decision),
        "receipt_id": step.get("receipt_id"),
        "local_grant_view": grant_view,
        "logical_time": step["logical_time"],
        "attempted": _will_attempt(history, step["operation_id"]),
    }


def execute_history(sink: EffectSink, token: str, history: dict[str, Any]) -> dict[str, Any]:
    """Run one frozen history. Effect rows come back from the observer, not from here."""
    policy = history["revocation_policy"]
    if policy not in REVOCATION_POLICIES:
        raise ValueError("each history must declare a revocation policy")
    sink.declare_run(
        token,
        run_id=history["run_id"],
        history_id=history["history_id"],
        policy=policy,
    )
    actor_records: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for step in history["steps"]:
        kind = step["kind"]
        if kind == "grant":
            sink.issue_grant(
                token,
                {
                    "grant_id": step["grant_id"],
                    "run_id": history["run_id"],
                    "history_id": history["history_id"],
                    "actor_id": step["actor_id"],
                    "task_id": step["task_id"],
                    "epoch_id": step["epoch_id"],
                    "operation_id": step["operation_id"],
                    "channel": step["channel"],
                    "subject_class": step["subject_class"],
                    "object_scope": step["object_scope"],
                    "logical_time": step["logical_time"],
                },
            )
        elif kind == "decide":
            grant = sink.lookup_grant(step.get("grant_id"))
            decision = decide_action(step, grant)
            grant_view = "present" if grant is not None else "absent"
            payload = {
                "decision": decision,
                "operation_id": step["operation_id"],
                "event_id": step["event_id"],
                "call_id": step["call_id"],
                "run_id": history["run_id"],
                "history_id": history["history_id"],
                "actor_id": step["actor_id"],
                "task_id": step["task_id"],
                "epoch_id": step["epoch_id"],
                "grant_id": step.get("grant_id"),
                "channel": step["channel"],
                "subject_class": step["subject_class"],
                "operation": step["operation"],
                "object_scope": step["object_scope"],
                "receipt_id": step.get("receipt_id"),
                "local_grant_view": grant_view,
                "attempted": False,
            }
            sink.record_stage(
                token,
                operation_id=step["operation_id"],
                stage="decision",
                logical_time=step["logical_time"],
                payload=payload,
            )
            decisions.append(
                {
                    **payload,
                    "logical_time": step["logical_time"],
                    "attempted": _will_attempt(history, step["operation_id"]),
                }
            )
            if step.get("actor_record", True):
                fields = _actor_fields(history, step, decision, grant_view)
                body = actor_body(fields)
                group = f"aew-v1-actor-{history['history_id']}"
                actor_records.append(
                    actor_row(fields, record_id=step["record_id"], group=group, body=body)
                )
                if step.get("duplicate_actor_record"):
                    copy_id = step["record_id"] + "-copy"
                    actor_records.append(
                        actor_row(fields, record_id=copy_id, group=group, body=body)
                    )
        elif kind == "attempt":
            decision = sink.stage(step["operation_id"], "decision")
            if decision is None:
                raise ValueError("attempt before decision")
            sink.record_stage(
                token,
                operation_id=step["operation_id"],
                stage="attempt",
                logical_time=step["logical_time"],
                payload={"operation_id": step["operation_id"], "attempted": True},
            )
        elif kind == "revoke":
            sink.insert_revocation(
                token,
                {
                    "revocation_id": step["revocation_id"],
                    "grant_id": step["grant_id"],
                    "run_id": history["run_id"],
                    "history_id": history["history_id"],
                    "operation_id": step["operation_id"],
                    "policy": step["policy"],
                    "logical_time": step["logical_time"],
                },
            )
        elif kind == "settle":
            sink.settle(
                token,
                {
                    "operation_id": step["operation_id"],
                    "run_id": history["run_id"],
                    "logical_time": step["logical_time"],
                    "policy": step["policy"],
                    "path": "settlement",
                },
            )
        elif kind == "ungated_commit":
            sink.commit_outside_local_control(
                token,
                {
                    "event_id": step["event_id"],
                    "operation_id": step["operation_id"],
                    "run_id": history["run_id"],
                    "history_id": history["history_id"],
                    "actor_id": step["actor_id"],
                    "task_id": step["task_id"],
                    "grant_id": None,
                    "epoch_id": step["epoch_id"],
                    "call_id": step["call_id"],
                    "channel": step["channel"],
                    "subject_class": step["subject_class"],
                    "operation": step["operation"],
                    "object_scope": step["object_scope"],
                    "logical_time": step["logical_time"],
                },
            )
        else:
            raise ValueError(f"unknown step {kind}")
    return {
        "history_id": history["history_id"],
        "run_id": history["run_id"],
        "actor_records": actor_records,
        "decisions": decisions,
    }


def check_expect(history: dict[str, Any], trace: dict[str, Any], commits: list[dict[str, Any]]) -> None:
    """Compare the manifest with observer rows and actor records."""
    expect = history["expect"]
    got = sorted(row["event_id"] for row in commits if row["run_id"] == history["run_id"])
    if got != sorted(expect["commits"]):
        raise RuntimeError(f"{history['history_id']}: commits {got} != {expect['commits']}")
    decisions = {item["operation_id"]: item["decision"] for item in trace["decisions"]}
    if decisions != expect["decisions"]:
        raise RuntimeError(f"{history['history_id']}: decisions {decisions}")
    bodies = [parse_body(record["public_bytes"]) for record in trace["actor_records"]]
    claimed = sorted({body["event_id"] for body in bodies if body["claimed_result"] == "success"})
    if claimed != sorted(expect["claimed_success"]):
        raise RuntimeError(f"{history['history_id']}: claimed success {claimed}")
    actor_events = {body["event_id"] for body in bodies}
    omitted = [event_id for event_id in expect["actor_omits"] if event_id in actor_events]
    if omitted:
        raise RuntimeError(f"{history['history_id']}: actor recorded omitted events {omitted}")
    if "actor_copies" in expect:
        calls = [record["call_id"] for record in trace["actor_records"]]
        if len(set(calls)) != 1 or len(calls) != expect["actor_copies"]:
            raise RuntimeError(f"{history['history_id']}: actor copies {calls}")
    if "receipt_id" in expect:
        if any(body["receipt_id"] != expect["receipt_id"] for body in bodies):
            raise RuntimeError(f"{history['history_id']}: receipt was not the shared receipt")
        if any(body["local_grant_view"] != expect["local_grant_view"] for body in bodies):
            raise RuntimeError(f"{history['history_id']}: local grant view mismatch")
    if expect.get("binding") == "misbound":
        if any(body["actor_id"] == history["actor_id"] for body in bodies):
            raise RuntimeError(f"{history['history_id']}: misbound actor record used the sink actor")
        if any(body["call_id"] != expect["reused_call_id"] for body in bodies):
            raise RuntimeError(f"{history['history_id']}: misbound record did not reuse the call id")
    if expect.get("binding") == "aligned":
        commit = next(row for row in commits if row["run_id"] == history["run_id"])
        body = bodies[0]
        for key in ("actor_id", "task_id", "epoch_id", "object_scope", "event_id", "call_id"):
            if body[key] != str(commit[key]):
                raise RuntimeError(f"{history['history_id']}: binding drifted on {key}")
