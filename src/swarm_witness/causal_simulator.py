"""Deterministic causal interleaving simulator for bounded authorization audits.

Each scheduled step has an actor, event ID and optional causal predecessors.
The agent receives only delivered observations. A separate authoritative ledger
records issuance, delegation, revocation and committed effects. The independent
trace oracle reconstructs truth without calling either policy's decision rule.
This is event-schedule simulation, not concurrent workers or a BMO integration.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping


class ScenarioError(ValueError):
    pass


@dataclass
class Grant:
    grant_id: str
    task_id: str
    owner: str
    epoch: str
    assignees: set[str] = field(default_factory=set)
    active: bool = True
    spent: bool = False
    revision: int = 1

    def snapshot(self, source_event: str) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "task_id": self.task_id,
            "owner": self.owner,
            "epoch": self.epoch,
            "assignees": sorted(self.assignees),
            "active": self.active,
            "spent": self.spent,
            "revision": self.revision,
            "source_event": source_event,
        }


class Runtime:
    def __init__(self, policy: str):
        if policy not in {"reference", "broken_local"}:
            raise ScenarioError(f"unknown policy {policy!r}")
        self.policy = policy
        self.grants: dict[str, Grant] = {}
        self.captured: dict[str, dict[str, Any]] = {}
        self.local_views: dict[str, dict[str, dict[str, Any]]] = {}
        self.local_receipts: dict[str, dict[str, dict[str, Any]]] = {}
        self.receipts: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.effect_log: list[dict[str, Any]] = []
        self.seen: set[str] = set()
        self.irrelevant: dict[str, list[str]] = {}

    def _valid_current(self, grant: Grant | None, actor: str, task: str, epoch: str) -> bool:
        # Policy under test, deliberately independent of trace oracle below.
        return bool(grant and grant.active and not grant.spent and
                    actor in grant.assignees and grant.task_id == task and grant.epoch == epoch)

    def _local_allows(self, actor: str, gid: str, task: str, epoch: str,
                      receipt_id: str | None) -> bool:
        view = self.local_views.get(actor, {}).get(gid)
        if view and view["active"] and not view["spent"] and actor in view["assignees"]:
            # Incorrectly trusts an old snapshot; ignores current version and scope.
            return True
        # Deliberate fault: foreign possession is treated as a capability.
        if receipt_id and receipt_id in self.local_receipts.get(actor, {}):
            return True
        return False

    def step(self, instruction: Mapping[str, Any]) -> dict[str, Any]:
        event_id = instruction.get("id")
        kind = instruction.get("op")
        actor = instruction.get("actor", "system")
        parents = list(instruction.get("parents", []))
        if not isinstance(event_id, str) or not event_id or event_id in self.seen:
            raise ScenarioError("event identifiers must be unique nonempty strings")
        if any(p not in self.seen for p in parents):
            raise ScenarioError(f"{event_id}: causal parent not yet occurred")
        self.seen.add(event_id)
        gid = instruction.get("grant_id")
        g = self.grants.get(gid)
        event: dict[str, Any] = {
            "seq": len(self.events) + 1, "event_id": event_id,
            "parents": parents, "op": kind, "actor": actor,
            "grant_id": gid, "task_id": instruction.get("task_id"),
            "epoch": instruction.get("epoch"), "call_id": instruction.get("call_id"),
            "receipt_id": instruction.get("receipt_id"),
            "decision": None, "effect_attempted": False, "effect_committed": False,
            "policy": self.policy,
            "local_view_before": deepcopy(self.local_views.get(actor, {}).get(gid)),
            "current_authority_visible_to_actor": False,
        }
        if kind == "issue":
            if gid in self.grants:
                raise ScenarioError(f"duplicate grant {gid}")
            owner = instruction["owner"]
            self.grants[gid] = Grant(gid, instruction["task_id"], owner,
                                     instruction["epoch"], {owner})
            event["owner"] = owner
            event["result"] = "issued"
        elif kind == "delegate":
            if g is None:
                raise ScenarioError("delegation of missing grant")
            delegate = instruction["delegate"]
            allowed = g.active and actor in g.assignees and not g.spent
            if allowed:
                g.assignees.add(delegate)
                g.revision += 1
            event.update({"delegate": delegate,
                          "decision": "allow" if allowed else "deny",
                          "result": "assigned" if allowed else "refused"})
        elif kind == "revoke":
            if g is None:
                raise ScenarioError("revocation of missing grant")
            g.active = False
            g.revision += 1
            event["result"] = "revoked"
        elif kind == "capture":
            if g is None:
                raise ScenarioError("capture of missing grant")
            self.captured[event_id] = g.snapshot(event_id)
            event["captured"] = deepcopy(self.captured[event_id])
            event["result"] = "captured"
        elif kind == "deliver_view":
            recipient = instruction["recipient"]
            source = instruction.get("capture_id")
            snap = (deepcopy(self.captured[source]) if source else
                    (g.snapshot(event_id) if g else None))
            if snap is None:
                raise ScenarioError("view delivery without grant")
            if snap["grant_id"] != gid:
                raise ScenarioError("snapshot/grant mismatch")
            self.local_views.setdefault(recipient, {})[gid] = snap
            event.update({"recipient": recipient, "source_capture": source,
                          "delivered_view": deepcopy(snap), "result": "delivered"})
        elif kind == "deliver_irrelevant":
            recipient = instruction["recipient"]
            value = instruction.get("value", "irrelevant-tag")
            self.irrelevant.setdefault(recipient, []).append(value)
            event.update({"recipient": recipient, "value": value, "result": "delivered"})
        elif kind == "deliver_receipt":
            recipient = instruction["recipient"]
            rid = instruction["receipt_id"]
            receipt = self.receipts.get(rid)
            if receipt is None:
                raise ScenarioError(f"receipt {rid} was never committed")
            self.local_receipts.setdefault(recipient, {})[rid] = deepcopy(receipt)
            event.update({"recipient": recipient, "delivered_receipt": deepcopy(receipt),
                          "result": "delivered"})
        elif kind == "claim":
            task, epoch = instruction["task_id"], instruction["epoch"]
            call_id = instruction["call_id"]
            rid = instruction.get("receipt_id")
            if self.policy == "reference":
                allow = self._valid_current(g, actor, task, epoch)
            else:
                allow = self._local_allows(actor, gid, task, epoch, rid)
            event["decision"] = "allow" if allow else "deny"
            event["effect_attempted"] = allow
            if allow:
                # Model's application boundary: broken-local deliberately bypasses
                # the authoritative pre-effect guard. Oracle evaluates the result.
                event["effect_committed"] = True
                if g:
                    g.spent = True
                    g.revision += 1
                receipt = {"receipt_id": f"receipt-{call_id}", "grant_id": gid,
                           "call_id": call_id, "agent": actor, "source_event": event_id}
                self.receipts[receipt["receipt_id"]] = receipt
                event["committed_receipt"] = deepcopy(receipt)
                # Separate application-side model ledger, inspected by the oracle.
                self.effect_log.append({"source_event":event_id,"grant_id":gid,
                                        "task_id":task,"epoch":epoch,"actor":actor,
                                        "call_id":call_id,"receipt_id":receipt["receipt_id"]})
            event["result"] = "claimed" if allow else "refused"
        elif kind == "inspect":
            event["result"] = "inspected"
        else:
            raise ScenarioError(f"unknown scheduled op {kind!r}")
        event["authority_after"] = self.grants[gid].snapshot(event_id) if gid in self.grants else None
        self.events.append(event)
        return event


def simulate(scenario: Mapping[str, Any], policy: str) -> dict[str, Any]:
    rt = Runtime(policy)
    for action in scenario["schedule"]:
        rt.step(action)
    return {"scenario_id": scenario["id"], "policy": policy,
            "model": "deterministic_causal_interleavings_v1",
            "agents": sorted(set(scenario.get("agents", ["A", "B", "C"]))),
            "events": rt.events, "effect_log": deepcopy(rt.effect_log)}


def independent_oracle(trace: Mapping[str, Any]) -> dict[str, Any]:
    """Replay authoritative history without invoking Runtime's policy methods.

    Effect validity is checked against *pre-effect* grant status reconstructed
    from issue/delegation/revocation/effect events. This oracle is for the model,
    not a verifier of real network/database events.
    """
    state: dict[str, dict[str, Any]] = {}
    invalid: list[str] = []
    bad_decisions: list[str] = []
    valid_effects: list[str] = []
    observed_events: set[str] = set()
    ledger_effects: dict[str, dict[str, Any]] = {}
    for row in trace.get("effect_log", []):
        source = row.get("source_event")
        if source in ledger_effects:
            invalid.append(f"{source}: duplicate independent effect ledger row")
        ledger_effects[source] = row
    for e in trace["events"]:
        eid, op, gid, actor = e["event_id"], e["op"], e["grant_id"], e["actor"]
        if eid in observed_events or any(x not in observed_events for x in e.get("parents", [])):
            invalid.append(f"{eid}: broken causal order")
        observed_events.add(eid)
        if op == "issue":
            if gid in state:
                invalid.append(f"{eid}: duplicate issue")
            state[gid] = {"active": True, "spent": False, "task": e["task_id"],
                          "epoch": e["epoch"], "assignees": {e["owner"]}}
            continue
        if op == "delegate":
            g = state.get(gid)
            entitled = bool(g and g["active"] and not g["spent"] and actor in g["assignees"])
            if e["decision"] != ("allow" if entitled else "deny"):
                bad_decisions.append(eid)
            if e["result"] == "assigned":
                if not entitled:
                    invalid.append(f"{eid}: unauthorized delegation")
                else:
                    g["assignees"].add(e["delegate"])
            continue
        if op == "revoke":
            if gid not in state:
                invalid.append(f"{eid}: revocation without grant")
            else:
                state[gid]["active"] = False
            continue
        if op != "claim":
            continue
        g = state.get(gid)
        entitled = bool(g and g["active"] and not g["spent"] and
                        e["task_id"] == g["task"] and e["epoch"] == g["epoch"] and
                        actor in g["assignees"])
        should = "allow" if entitled else "deny"
        if e["decision"] != should:
            bad_decisions.append(eid)
        committed = eid in ledger_effects
        if bool(e["effect_committed"]) != committed:
            invalid.append(f"{eid}: decision/independent-effect-ledger mismatch")
        if committed:
            row = ledger_effects[eid]
            if any(row.get(key) != e.get(key) for key in
                   ("grant_id", "task_id", "epoch", "actor", "call_id")):
                invalid.append(f"{eid}: effect-identity mismatch")
            if not entitled:
                invalid.append(f"{eid}: unauthorized committed effect")
            else:
                valid_effects.append(eid)
            if g:
                g["spent"] = True
        elif e["decision"] == "allow" and not e["effect_attempted"]:
            invalid.append(f"{eid}: allowed without effect attempt")
    for source in ledger_effects:
        if source not in observed_events:
            invalid.append(f"{source}: orphan independent effect ledger row")
    return {
        "valid_effects": len(valid_effects),
        "unauthorized_effects": len([s for s in invalid if "unauthorized committed effect" in s]),
        "incorrect_decisions": len(bad_decisions),
        "violation_events": invalid,
        "incorrect_decision_events": bad_decisions,
        "causal_events": len(observed_events),
    }


def local_visible_claim(trace: Mapping[str, Any], call_id: str) -> dict[str, Any]:
    for event in trace["events"]:
        if event["op"] == "claim" and event["call_id"] == call_id:
            return {"view": event["local_view_before"],
                    "receipt_id": event["receipt_id"]}
    raise KeyError(call_id)
