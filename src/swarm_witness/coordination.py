"""Coordination and causal-contribution qualifier (coordination-attribution-v1).

Normative statement: ``protocol/coordination_attribution_v1.md``.

This module does not define a provenance graph. Every agent, task, message,
delegation, adoption, effect, time, and edge cites nodes from an
``evidence-provenance-v1`` graph. Verification, independence groups, coverage,
and chronology all come from ``swarm_witness.provenance``. A label is withheld
when that lineage does not admit it.

A remaining ``blocks_upgrade`` slot prevents an upgrade to ``supported``.
Verified bytes from some other source do not clear a withheld transcript, an
unobserved platform log, or any other blocking slot. This module calls
``qualify_claim`` and will not report a supported incident verdict while that
blocker remains.

Nothing here claims Swarm Witness detected or prevented an incident.
"""

from __future__ import annotations

import copy
import random
from typing import Any

from swarm_witness.conclusion_classes import classify_conclusion
from swarm_witness.provenance import (
    CERTIFICATION_INPUTS,
    CONTRACT_VERSION,
    event_verified,
    qualify_claim,
    rejection_reason,
    slot_coverage,
    validate_graph,
)

COORDINATION_VERSION = "coordination-attribution-v1"

LABELS = frozenset(
    {
        "communication_observed",
        "delegation_evidenced",
        "goal_adoption_inferred",
        "causal_contribution_unresolved",
    }
)
EDGE_KINDS = frozenset(
    {
        "communication",
        "delegation",
        "adoption",
        "contribution",
        "temporal_correlation",
        "shared_vocabulary",
        "reused_file",
        "relay",
        "duplicate_report",
        "possession",
        "investigator_inference",
    }
)
PROPOSITION_KINDS = frozenset(
    {
        "board_participation",
        "delegated_workstream",
        "collective_causal_impact",
        "negative_control",
        "synthetic_distinction",
    }
)
WORLD_KINDS = frozenset(
    {
        "board_participation",
        "delegated_workstream",
        "collective_causal_impact",
    }
)
IDENTIFIER_STATUSES = frozenset({"lineage", "copied", "forged", "missing", "unknown"})
CONTENT_RELATIONS = frozenset(
    {
        "original",
        "relay",
        "repetition",
        "reused_file",
        "investigator_aggregate",
        "unknown",
    }
)
COUNT_LABELS = frozenset({"investigator_reported", "directly_processed"})
FIELD_UNITS = {
    "agents_on_board": "agents",
    "messages_and_files": "messages_and_files",
    "transcripts": "transcripts",
    "spoofed_transcripts": "transcripts",
}
DIRECT_UNITS = frozenset(
    {"publication_sentences", "agent_instances", "messages", "effects"}
)
NON_CAUSAL_KINDS = frozenset(
    {
        "temporal_correlation",
        "shared_vocabulary",
        "reused_file",
        "relay",
        "duplicate_report",
        "possession",
        "investigator_inference",
    }
)

CASE_FIELDS = frozenset(
    {
        "id",
        "proposition",
        "proposition_kind",
        "provenance_claim_id",
        "populations",
        "agent_instances",
        "tasks",
        "messages",
        "delegations",
        "adoptions",
        "effects",
        "observed_times",
        "source_citations",
        "edges",
    }
)
AGENT_FIELDS = frozenset(
    {
        "id",
        "actor_ref",
        "identifier_status",
        "provenance_event_ids",
        "provenance_source_ids",
    }
)
TASK_FIELDS = frozenset(
    {"id", "statement", "provenance_event_ids", "provenance_source_ids"}
)
MESSAGE_FIELDS = frozenset(
    {
        "id",
        "artifact_ref",
        "speaker_agent_id",
        "relation_to_content",
        "provenance_event_ids",
        "provenance_source_ids",
    }
)
DELEGATION_FIELDS = frozenset(
    {
        "id",
        "from_agent_id",
        "to_agent_id",
        "task_id",
        "message_id",
        "provenance_event_ids",
        "provenance_source_ids",
    }
)
ADOPTION_FIELDS = frozenset(
    {
        "id",
        "agent_id",
        "task_id",
        "provenance_event_ids",
        "provenance_source_ids",
    }
)
EFFECT_FIELDS = frozenset(
    {"id", "statement", "provenance_event_ids", "provenance_source_ids"}
)
TIME_FIELDS = frozenset({"id", "provenance_event_id"})
CITATION_FIELDS = frozenset({"id", "provenance_source_id"})
EDGE_FIELDS = frozenset(
    {
        "id",
        "kind",
        "from_id",
        "to_id",
        "provenance_event_ids",
        "provenance_source_ids",
        "source_citation_ids",
    }
)
POPULATION_FIELDS = frozenset(
    {
        "id",
        "count_label",
        "unit",
        "provenance_source_id",
        "reported_field",
        "record_ids",
    }
)

SCALE_AGENTS = 1200
SCALE_MESSAGES = 70000
SCALE_HANDOFFS = 1200
SCALE_SEED = 30


def _require_keys(node: dict[str, Any], allowed: frozenset[str], kind: str) -> None:
    if not isinstance(node, dict):
        raise ValueError(f"{kind} must be an object")
    unknown = set(node) - allowed
    if unknown:
        raise ValueError(f"unknown {kind} field: {sorted(unknown)}")
    missing = allowed - set(node)
    if kind == "population":
        label = node.get("count_label")
        if label == "investigator_reported":
            missing -= {"record_ids"}
        elif label == "directly_processed":
            missing -= {"provenance_source_id", "reported_field"}
    if missing:
        raise ValueError(f"{kind} missing field: {sorted(missing)}")


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"invalid or blank field: {field}")
    return value.strip()


def _id_list(value: Any, field: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or item.strip() == "" for item in value
    ):
        raise ValueError(f"{field} must be a list of nonblank strings")
    if len(value) != len(set(value)):
        raise ValueError(f"duplicate id in {field}")
    if not allow_empty and not value:
        raise ValueError(f"{field} must cite at least one id")
    return [item.strip() for item in value]


def _optional_str(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty(value, field)


def _reject_certification(node: dict[str, Any], where: str) -> None:
    found = CERTIFICATION_INPUTS & set(node)
    if found:
        raise ValueError(
            f"{where} cannot certify or score the incident: " + ", ".join(sorted(found))
        )


def _index_provenance(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_graph(graph)
    return {
        "sources": {node["id"]: node for node in graph["source_records"]},
        "events": {node["id"]: node for node in graph["observed_events"]},
        "claims": {node["id"]: node for node in graph["claims"]},
    }


def _ancestry(source_id: str, sources: dict[str, dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    stack = [source_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        source = sources[current]
        stack.extend(source["depends_on"])
        if source["duplicate_of"]:
            stack.append(source["duplicate_of"])
    for other in sources.values():
        if other["duplicate_of"] in seen:
            seen.add(other["id"])
    return seen


def _event_lineage(
    event_ids: list[str], prov: dict[str, dict[str, Any]]
) -> set[str]:
    lineage: set[str] = set()
    for event_id in event_ids:
        event = prov["events"][event_id]
        for source_id in event["necessary_source_ids"]:
            lineage |= _ancestry(source_id, prov["sources"])
    return lineage


def _groups(event_ids: list[str], prov: dict[str, dict[str, Any]]) -> list[str]:
    groups: set[str] = set()
    for event_id in event_ids:
        event = prov["events"][event_id]
        if not event_verified(event, prov["sources"]):
            continue
        for source_id in event["necessary_source_ids"]:
            source = prov["sources"][source_id]
            if source.get("duplicate_of"):
                continue
            groups.add(source["independence_group"])
    return sorted(groups)


def _verified(
    event_ids: list[str],
    prov: dict[str, dict[str, Any]],
    *,
    kind: str | None = None,
) -> list[dict[str, Any]]:
    selected = []
    for event_id in event_ids:
        event = prov["events"][event_id]
        if not event_verified(event, prov["sources"]):
            continue
        if event["authenticity"] == "forged" or event["polarity"] == "contradicts":
            continue
        if kind is not None and event["event_kind"] != kind:
            continue
        selected.append(event)
    return selected


def _time_view(events: list[dict[str, Any]]) -> dict[str, Any]:
    seams: list[str] = []
    if not events:
        return {
            "event_time": None,
            "observed_time": None,
            "time_basis": "missing",
            "complete": False,
            "seams": ["incomplete_timeline"],
        }
    for event in events:
        if event["time_basis"] == "reconstructed":
            seams.append("reconstructed_time_rejected")
        elif event["time_basis"] != "source_stated" or not event["event_time"]:
            seams.append("incomplete_timeline")
    if seams:
        return {
            "event_time": None,
            "observed_time": None,
            "time_basis": "missing",
            "complete": False,
            "seams": sorted(set(seams)),
        }
    first = events[0]
    return {
        "event_time": first["event_time"],
        "observed_time": first["observed_time"],
        "time_basis": "source_stated",
        "complete": True,
        "seams": [],
    }


def _actor_blocked(agents: list[dict[str, Any]], events: list[dict[str, Any]]) -> bool:
    if any(agent["identifier_status"] in {"copied", "forged"} for agent in agents):
        return True
    return any(
        event["authenticity"] == "forged" or event["actor_binding"] == "conflicting"
        for event in events
    )


def _bound_log(agent: dict[str, Any], logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if agent["identifier_status"] != "lineage" or not agent["actor_ref"]:
        return None
    for event in logs:
        if (
            event["id"] in agent["provenance_event_ids"]
            and event["actor_binding"] == "bound"
            and event["actor_ref"] == agent["actor_ref"]
        ):
            return event
    return None


def validate_case(case: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    """Reject a coordination case that leaves the provenance graph or invents a clock."""
    if not isinstance(case, dict):
        raise ValueError("coordination case must be an object")
    _reject_certification(case, "case")
    _require_keys(case, CASE_FIELDS, "case")
    prov = _index_provenance(graph)
    case_id = _nonempty(case["id"], "case.id")
    _nonempty(case["proposition"], f"{case_id}.proposition")
    kind = case["proposition_kind"]
    if kind not in PROPOSITION_KINDS:
        raise ValueError(f"unknown proposition_kind: {kind!r}")
    claim_id = case["provenance_claim_id"]
    if claim_id is not None:
        _nonempty(claim_id, f"{case_id}.provenance_claim_id")
        if claim_id not in prov["claims"]:
            raise ValueError(f"dangling provenance claim: {claim_id}")

    records: dict[str, str] = {}

    def take_id(node_id: str, node_kind: str) -> None:
        if node_id in records:
            raise ValueError(f"duplicate coordination id: {node_id}")
        records[node_id] = node_kind

    agents = []
    for agent in case["agent_instances"]:
        _require_keys(agent, AGENT_FIELDS, "agent_instance")
        _reject_certification(agent, agent.get("id", "agent"))
        agent_id = _nonempty(agent["id"], "agent_instance.id")
        take_id(agent_id, "agent_instance")
        if agent["identifier_status"] not in IDENTIFIER_STATUSES:
            raise ValueError(f"unknown identifier_status: {agent['identifier_status']!r}")
        agent["actor_ref"] = _optional_str(agent["actor_ref"], f"{agent_id}.actor_ref")
        agent["provenance_event_ids"] = _id_list(
            agent["provenance_event_ids"], f"{agent_id}.provenance_event_ids", allow_empty=False
        )
        agent["provenance_source_ids"] = _id_list(
            agent["provenance_source_ids"],
            f"{agent_id}.provenance_source_ids",
            allow_empty=False,
        )
        agents.append(agent)
    by_agent = {agent["id"]: agent for agent in agents}

    tasks = []
    for task in case["tasks"]:
        _require_keys(task, TASK_FIELDS, "task")
        task_id = _nonempty(task["id"], "task.id")
        take_id(task_id, "task")
        _nonempty(task["statement"], f"{task_id}.statement")
        task["provenance_event_ids"] = _id_list(
            task["provenance_event_ids"], f"{task_id}.provenance_event_ids", allow_empty=False
        )
        task["provenance_source_ids"] = _id_list(
            task["provenance_source_ids"], f"{task_id}.provenance_source_ids", allow_empty=False
        )
        tasks.append(task)
    by_task = {task["id"]: task for task in tasks}

    messages = []
    for message in case["messages"]:
        _require_keys(message, MESSAGE_FIELDS, "message")
        message_id = _nonempty(message["id"], "message.id")
        take_id(message_id, "message")
        _nonempty(message["artifact_ref"], f"{message_id}.artifact_ref")
        if message["relation_to_content"] not in CONTENT_RELATIONS:
            raise ValueError(
                f"unknown relation_to_content: {message['relation_to_content']!r}"
            )
        speaker = message["speaker_agent_id"]
        if speaker is not None:
            _nonempty(speaker, f"{message_id}.speaker_agent_id")
            if speaker not in by_agent:
                raise ValueError(f"dangling speaker: {speaker}")
        message["provenance_event_ids"] = _id_list(
            message["provenance_event_ids"],
            f"{message_id}.provenance_event_ids",
            allow_empty=False,
        )
        message["provenance_source_ids"] = _id_list(
            message["provenance_source_ids"],
            f"{message_id}.provenance_source_ids",
            allow_empty=False,
        )
        messages.append(message)
    by_message = {message["id"]: message for message in messages}

    delegations = []
    for delegation in case["delegations"]:
        _require_keys(delegation, DELEGATION_FIELDS, "delegation")
        delegation_id = _nonempty(delegation["id"], "delegation.id")
        take_id(delegation_id, "delegation")
        for ref, pool in (
            (delegation["from_agent_id"], by_agent),
            (delegation["to_agent_id"], by_agent),
            (delegation["task_id"], by_task),
            (delegation["message_id"], by_message),
        ):
            _nonempty(ref, f"{delegation_id} endpoint")
            if ref not in pool:
                raise ValueError(f"dangling delegation endpoint: {ref}")
        delegation["provenance_event_ids"] = _id_list(
            delegation["provenance_event_ids"],
            f"{delegation_id}.provenance_event_ids",
            allow_empty=False,
        )
        delegation["provenance_source_ids"] = _id_list(
            delegation["provenance_source_ids"],
            f"{delegation_id}.provenance_source_ids",
            allow_empty=False,
        )
        delegations.append(delegation)
    by_delegation = {delegation["id"]: delegation for delegation in delegations}

    adoptions = []
    for adoption in case["adoptions"]:
        _require_keys(adoption, ADOPTION_FIELDS, "adoption")
        adoption_id = _nonempty(adoption["id"], "adoption.id")
        take_id(adoption_id, "adoption")
        if adoption["agent_id"] not in by_agent or adoption["task_id"] not in by_task:
            raise ValueError(f"dangling adoption endpoint on {adoption_id}")
        adoption["provenance_event_ids"] = _id_list(
            adoption["provenance_event_ids"],
            f"{adoption_id}.provenance_event_ids",
            allow_empty=False,
        )
        adoption["provenance_source_ids"] = _id_list(
            adoption["provenance_source_ids"],
            f"{adoption_id}.provenance_source_ids",
            allow_empty=False,
        )
        adoptions.append(adoption)

    effects = []
    for effect in case["effects"]:
        _require_keys(effect, EFFECT_FIELDS, "effect")
        effect_id = _nonempty(effect["id"], "effect.id")
        take_id(effect_id, "effect")
        _nonempty(effect["statement"], f"{effect_id}.statement")
        effect["provenance_event_ids"] = _id_list(
            effect["provenance_event_ids"],
            f"{effect_id}.provenance_event_ids",
            allow_empty=False,
        )
        effect["provenance_source_ids"] = _id_list(
            effect["provenance_source_ids"],
            f"{effect_id}.provenance_source_ids",
            allow_empty=False,
        )
        effects.append(effect)
    by_effect = {effect["id"]: effect for effect in effects}

    citations = []
    for citation in case["source_citations"]:
        _require_keys(citation, CITATION_FIELDS, "source_citation")
        citation_id = _nonempty(citation["id"], "source_citation.id")
        take_id(citation_id, "source_citation")
        source_id = _nonempty(citation["provenance_source_id"], f"{citation_id}.provenance_source_id")
        if source_id not in prov["sources"]:
            raise ValueError(f"dangling provenance source: {source_id}")
        citations.append(citation)
    by_citation = {citation["id"]: citation for citation in citations}

    cited_events: set[str] = set()
    cited_sources: set[str] = set()
    for collection in (agents, tasks, messages, delegations, adoptions, effects):
        for record in collection:
            cited_events.update(record["provenance_event_ids"])
            cited_sources.update(record["provenance_source_ids"])

    edges = []
    for edge in case["edges"]:
        _require_keys(edge, EDGE_FIELDS, "edge")
        _reject_certification(edge, edge.get("id", "edge"))
        edge_id = _nonempty(edge["id"], "edge.id")
        take_id(edge_id, "edge")
        if edge["kind"] not in EDGE_KINDS:
            raise ValueError(f"unknown edge kind: {edge['kind']!r}")
        if edge["from_id"] not in records or edge["to_id"] not in records:
            raise ValueError(f"{edge_id} endpoint is not a coordination record")
        edge["provenance_event_ids"] = _id_list(
            edge["provenance_event_ids"], f"{edge_id}.provenance_event_ids", allow_empty=False
        )
        edge["provenance_source_ids"] = _id_list(
            edge["provenance_source_ids"], f"{edge_id}.provenance_source_ids", allow_empty=False
        )
        edge["source_citation_ids"] = _id_list(
            edge["source_citation_ids"], f"{edge_id}.source_citation_ids", allow_empty=False
        )
        for event_id in edge["provenance_event_ids"]:
            if event_id not in prov["events"]:
                raise ValueError(f"dangling provenance event: {event_id}")
        for citation_id in edge["source_citation_ids"]:
            if citation_id not in by_citation:
                raise ValueError(f"dangling source citation: {citation_id}")
        citation_sources = {
            by_citation[citation_id]["provenance_source_id"]
            for citation_id in edge["source_citation_ids"]
        }
        if citation_sources != set(edge["provenance_source_ids"]):
            raise ValueError(f"{edge_id} source citations do not match provenance_source_ids")
        cited_events.update(edge["provenance_event_ids"])
        cited_sources.update(edge["provenance_source_ids"])
        edges.append(edge)

    if not edges:
        raise ValueError(f"{case_id} has no edges")

    times = []
    time_events = []
    for observed in case["observed_times"]:
        _require_keys(observed, TIME_FIELDS, "observed_time")
        time_id = _nonempty(observed["id"], "observed_time.id")
        take_id(time_id, "observed_time")
        event_id = _nonempty(observed["provenance_event_id"], f"{time_id}.provenance_event_id")
        if event_id not in prov["events"]:
            raise ValueError(f"dangling provenance event: {event_id}")
        if "event_time" in observed or "observed_time" in observed or "time_basis" in observed:
            raise ValueError(f"{time_id} cannot supply a clock; time comes from provenance")
        times.append(observed)
        time_events.append(event_id)
    if len(time_events) != len(set(time_events)):
        raise ValueError("duplicate observed_time for one provenance event")
    if set(time_events) != cited_events:
        raise ValueError(
            f"{case_id} observed_time records must cover every cited provenance event"
        )

    populations = []
    for population in case["populations"]:
        _require_keys(population, POPULATION_FIELDS, "population")
        population_id = _nonempty(population["id"], "population.id")
        take_id(population_id, "population")
        label = population["count_label"]
        if label not in COUNT_LABELS:
            raise ValueError(f"unknown count_label: {label!r}")
        if "count" in population or "held_by_audit" in population:
            raise ValueError(f"{population_id} cannot declare its own count or custody")
        if label == "investigator_reported":
            source_id = _nonempty(
                population["provenance_source_id"], f"{population_id}.provenance_source_id"
            )
            field = _nonempty(population["reported_field"], f"{population_id}.reported_field")
            if source_id not in prov["sources"]:
                raise ValueError(f"dangling provenance source: {source_id}")
            reported = prov["sources"][source_id].get("reported_not_held") or {}
            if field not in reported:
                raise ValueError(
                    f"{population_id} field {field} is not on the provenance lineage"
                )
            if population["unit"] != FIELD_UNITS.get(field):
                raise ValueError(f"{population_id} unit does not match {field}")
            if reported.get("held_by_audit") is True:
                raise ValueError(f"{source_id}: reported counts are not held by this audit")
            cited_sources.add(source_id)
        else:
            if population["unit"] not in DIRECT_UNITS:
                raise ValueError(f"unknown directly_processed unit: {population['unit']!r}")
            population["record_ids"] = _id_list(
                population["record_ids"], f"{population_id}.record_ids", allow_empty=False
            )
            for record_id in population["record_ids"]:
                if record_id not in records:
                    raise ValueError(f"dangling population record: {record_id}")
        populations.append(population)

    citation_sources = {citation["provenance_source_id"] for citation in citations}
    if citation_sources != cited_sources:
        raise ValueError(
            f"{case_id} source citations must match the cited provenance sources"
        )

    claim_sources: set[str] = set()
    if claim_id is not None:
        claim_sources = {slot["source_id"] for slot in prov["claims"][claim_id]["evidence_slots"]}
    for record in agents + tasks + messages + delegations + adoptions + effects + edges:
        lineage = _event_lineage(record["provenance_event_ids"], prov)
        for source_id in record["provenance_source_ids"]:
            if source_id in lineage or source_id in claim_sources:
                continue
            coverage = slot_coverage(prov["sources"][source_id])
            if coverage == "available":
                raise ValueError(
                    f"{record['id']} cites {source_id} outside the cited event lineage"
                )

    for agent in agents:
        if agent["identifier_status"] != "lineage":
            continue
        refs = {
            prov["events"][event_id]["actor_ref"]
            for event_id in agent["provenance_event_ids"]
            if prov["events"][event_id]["actor_ref"]
        }
        if agent["actor_ref"] is None or agent["actor_ref"] not in refs:
            raise ValueError(f"{agent['id']} actor_ref is not on its provenance events")

    return {
        "prov": prov,
        "agents": by_agent,
        "tasks": by_task,
        "messages": by_message,
        "delegations": by_delegation,
        "effects": by_effect,
        "citations": by_citation,
        "edges": edges,
        "populations": populations,
    }


def _population_view(
    population: dict[str, Any], prov: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    if population["count_label"] == "investigator_reported":
        source = prov["sources"][population["provenance_source_id"]]
        reported = dict(source["reported_not_held"])
        reported["held_by_audit"] = False
        return {
            "id": population["id"],
            "count_label": "investigator_reported",
            "unit": population["unit"],
            "count": reported[population["reported_field"]],
            "precision": reported.get("precision", "unknown"),
            "held_by_audit": False,
            "directly_processed": False,
            "traced_causal_actors": False,
            "provenance_source_id": source["id"],
            "reported_field": population["reported_field"],
        }
    return {
        "id": population["id"],
        "count_label": "directly_processed",
        "unit": population["unit"],
        "count": len(population["record_ids"]),
        "precision": "exact_records_in_case",
        "held_by_audit": False,
        "directly_processed": True,
        "traced_causal_actors": False,
        "record_ids": list(population["record_ids"]),
    }


def _unavailable(
    source_ids: set[str], prov: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    rows = []
    for source_id in sorted(source_ids):
        source = prov["sources"][source_id]
        status = slot_coverage(source)
        if status == "available":
            continue
        rows.append(
            {
                "source_id": source_id,
                "coverage_status": status,
                "access_level": source["access_level"],
                "observation_origin": source["observation_origin"],
            }
        )
    return rows


def _qualify_edge(
    edge: dict[str, Any], indexed: dict[str, Any]
) -> dict[str, Any]:
    prov = indexed["prov"]
    events = [prov["events"][event_id] for event_id in edge["provenance_event_ids"]]
    logs = _verified(edge["provenance_event_ids"], prov, kind="independent_service_log")
    narratives = _verified(edge["provenance_event_ids"], prov, kind="narrative_report")
    effects = _verified(edge["provenance_event_ids"], prov, kind="committed_effect")
    seams: list[str] = []
    labels: list[str] = []
    agents = [
        indexed["agents"][endpoint]
        for endpoint in (edge["from_id"], edge["to_id"])
        if endpoint in indexed["agents"]
    ]
    delegation = indexed["delegations"].get(edge["from_id"]) or indexed["delegations"].get(
        edge["to_id"]
    )
    if delegation is not None:
        agents = [
            indexed["agents"][delegation["from_agent_id"]],
            indexed["agents"][delegation["to_agent_id"]],
        ]
    message = indexed["messages"].get(edge["from_id"]) or indexed["messages"].get(edge["to_id"])
    if delegation is not None:
        message = indexed["messages"].get(delegation["message_id"])
    if message is not None and message["speaker_agent_id"] is not None:
        speaker_agent = indexed["agents"][message["speaker_agent_id"]]
        if speaker_agent not in agents:
            agents.append(speaker_agent)
    blocked = _actor_blocked(agents, events)
    if blocked:
        seams.append("forged_or_copied_actor")
    if any(event["event_kind"] == "narrative_report" for event in events) and not logs:
        seams.append("narrative_is_not_communication")
    if message is not None and message["relation_to_content"] == "investigator_aggregate":
        seams.append("narrative_is_not_communication")
    if message is not None and message["relation_to_content"] == "relay":
        seams.append("relay_not_authorship")
    if message is not None and message["relation_to_content"] == "repetition":
        seams.append("possession_not_contribution")
    if edge["kind"] == "relay":
        seams.append("relay_not_authorship")
    if edge["kind"] == "possession":
        seams.append("possession_not_contribution")
    if edge["kind"] == "reused_file":
        seams.append("reused_file_without_handoff")
    if edge["kind"] == "duplicate_report":
        seams.append("duplicate_report")
    if edge["kind"] == "temporal_correlation":
        seams.append("temporal_correlation_not_causal")
    if edge["kind"] == "shared_vocabulary":
        seams.append("shared_vocabulary_not_causal")
    if edge["kind"] == "investigator_inference":
        seams.append("investigator_inference_not_handoff")

    support_for_time = logs + [
        event
        for event in effects
        if event["time_basis"] == "source_stated"
    ]
    if edge["kind"] in {"contribution", "temporal_correlation", "investigator_inference"}:
        # A narrative window is not an effect chronology.
        if any(event["event_kind"] == "narrative_report" and event["event_time"] for event in events):
            seams.append("narrative_time_not_promoted")
        clock = _time_view(effects)
    elif edge["kind"] == "delegation":
        clock = _time_view(logs)
    else:
        clock = _time_view(support_for_time or [])
        if not support_for_time:
            clock = {
                "event_time": None,
                "observed_time": None,
                "time_basis": "missing",
                "complete": False,
                "seams": [],
            }
    seams.extend(clock["seams"])

    authorship = False
    speaker = None
    if message is not None and message["speaker_agent_id"] is not None:
        speaker = indexed["agents"][message["speaker_agent_id"]]
        log = _bound_log(speaker, logs)
        authorship = (
            log is not None
            and not blocked
            and message["relation_to_content"] == "original"
            and edge["kind"] == "communication"
        )
    if (
        edge["kind"] == "communication"
        and authorship
        and speaker is not None
        and not blocked
    ):
        labels.append("communication_observed")

    delegation_ok = False
    if edge["kind"] == "delegation" and delegation is not None and not blocked:
        sender = indexed["agents"][delegation["from_agent_id"]]
        recipient = indexed["agents"][delegation["to_agent_id"]]
        handed = indexed["messages"][delegation["message_id"]]
        sender_log = _bound_log(sender, logs)
        recipient_log = _bound_log(recipient, logs)
        if indexed["tasks"].get(delegation["task_id"]) is None:
            seams.append("missing_delegation_records")
        elif handed["relation_to_content"] != "original":
            seams.append("possession_not_contribution")
        elif sender_log is None or recipient_log is None:
            seams.append("missing_agent_instances")
        elif not clock["complete"]:
            pass
        elif sender_log["id"] not in handed["provenance_event_ids"]:
            seams.append("missing_delegation_records")
        elif sender_log["id"] not in delegation["provenance_event_ids"]:
            seams.append("missing_delegation_records")
        elif recipient_log["id"] not in delegation["provenance_event_ids"]:
            seams.append("missing_delegation_records")
        else:
            delegation_ok = True
            labels.append("delegation_evidenced")
    elif edge["kind"] == "delegation":
        seams.append("missing_delegation_records")

    if (
        edge["kind"] in {"adoption", "shared_vocabulary"}
        and narratives
        and not blocked
        and (
            message is None
            or message["relation_to_content"] not in {"relay", "repetition", "investigator_aggregate"}
        )
    ):
        labels.append("goal_adoption_inferred")
        seams.append("goal_adoption_is_inference")

    link_class = "unresolved"
    causal = False
    if "forged_or_copied_actor" in seams and edge["kind"] in {"communication", "delegation", "contribution"}:
        link_class = "forged_or_copied_actor"
    elif edge["kind"] in NON_CAUSAL_KINDS:
        link_class = {
            "temporal_correlation": "temporal_correlation",
            "shared_vocabulary": "shared_vocabulary",
            "reused_file": "reused_file",
            "relay": "relay",
            "duplicate_report": "duplicate_report",
            "possession": "possession",
            "investigator_inference": "investigator_inference",
        }[edge["kind"]]
    elif delegation_ok:
        link_class = "traced_handoff"
    elif "incomplete_timeline" in seams or "reconstructed_time_rejected" in seams:
        link_class = "incomplete_timeline"

    return {
        "id": edge["id"],
        "kind": edge["kind"],
        "from_id": edge["from_id"],
        "to_id": edge["to_id"],
        "provenance_event_ids": list(edge["provenance_event_ids"]),
        "provenance_source_ids": list(edge["provenance_source_ids"]),
        "source_citation_ids": list(edge["source_citation_ids"]),
        "labels": sorted(set(labels)),
        "link_class": link_class,
        "event_time": clock["event_time"],
        "observed_time": clock["observed_time"],
        "time_basis": clock["time_basis"],
        "authorship_supported": authorship,
        "causal_link_supported": causal,
        "delegation_ok": delegation_ok,
        "verified_service_log_ids": [event["id"] for event in logs],
        "verified_effect_ids": [event["id"] for event in effects],
        "seams": sorted(set(seams)),
    }


def _blocking_source_ids(claim: dict[str, Any] | None) -> list[str]:
    if claim is None:
        return []
    return [
        slot["source_id"]
        for slot in claim["evidence_slots"]
        if slot["blocks_upgrade"]
    ]


def _clears_blockers(events: list[dict[str, Any]], blocking_ids: list[str]) -> bool:
    """A supporting event clears a blocker only by using that source itself."""
    if not blocking_ids:
        return True
    used = {source_id for event in events for source_id in event["necessary_source_ids"]}
    return all(source_id in used for source_id in blocking_ids)


def _guard_verdict(qualification: dict[str, Any]) -> dict[str, Any]:
    """Drop a supported label when a blocks_upgrade slot is still unused.

    ``qualify_claim`` already refuses that upgrade. This guard is the
    coordination boundary: a caller cannot carry the forbidden verdict out.
    """
    blocked = list(qualification.get("upgrade_blocked_by") or [])
    label = qualification["finding_label"]
    refused = bool(blocked) and label in {"reproduced", "classical_baseline_matches"}
    if refused:
        label = "unresolved"
    return {
        "finding_label": label,
        "conclusion_class": (
            "missing_evidence" if refused else qualification["conclusion_class"]
        ),
        "upgrade_blocked_by": blocked,
        "primary_upgrade_blocker": qualification.get("primary_upgrade_blocker"),
        "refused_blocked_support": refused,
    }


def _connect_contribution(qualified_edges: list[dict[str, Any]], indexed: dict[str, Any]) -> None:
    prov = indexed["prov"]
    blocking_ids = _blocking_source_ids(indexed.get("provenance_claim"))
    evidenced = {
        edge["from_id"]
        for edge in qualified_edges
        if edge["delegation_ok"] and edge["from_id"] in indexed["delegations"]
    }
    for edge in qualified_edges:
        if edge["kind"] != "contribution":
            edge["causal_link_supported"] = False
            continue
        effect = indexed["effects"].get(edge["to_id"])
        delegation = indexed["delegations"].get(edge["from_id"])
        goods = []
        if effect is not None:
            goods = [
                event
                for event in _verified(effect["provenance_event_ids"], prov, kind="committed_effect")
                if event["time_basis"] == "source_stated" and event["event_time"]
            ]
        linked = (
            delegation is not None
            and delegation["id"] in evidenced
            and bool(goods)
            and edge["from_id"] in evidenced
            and _clears_blockers(goods, blocking_ids)
        )
        if goods and blocking_ids and not _clears_blockers(goods, blocking_ids):
            edge["seams"] = sorted(set(edge["seams"]) | {"upgrade_blocker_remains"})
        if linked:
            edge["causal_link_supported"] = True
            edge["link_class"] = "traced_handoff"
            edge["labels"] = sorted(set(edge["labels"]) - {"causal_contribution_unresolved"})
            edge["event_time"] = goods[0]["event_time"]
            edge["observed_time"] = goods[0]["observed_time"]
            edge["time_basis"] = "source_stated"
            edge["seams"] = sorted(
                set(edge["seams"]) - {"narrative_time_not_promoted", "incomplete_timeline"}
            )
        else:
            edge["causal_link_supported"] = False
            edge["labels"] = sorted(set(edge["labels"]) | {"causal_contribution_unresolved"})
            edge["event_time"] = None
            edge["observed_time"] = None
            edge["time_basis"] = "missing"
            if edge["link_class"] == "traced_handoff":
                edge["link_class"] = "unresolved"


def coordination_added_value(
    graph: dict[str, Any],
    claim_id: str | None,
    admissible_event_ids: list[str],
) -> dict[str, Any]:
    """Ask whether coordination-only admissible events would change the provenance verdict.

    The augmented claim is the existing provenance claim plus verified handoff
    or effect events that were not already on it. No new facts are inserted.
    """
    if claim_id is None:
        return {
            "added": False,
            "individual_claim_id": None,
            "individual_finding_label": None,
            "augmented_finding_label": None,
            "admissible_events_not_on_individual_claim": [],
            "upgrade_blocked_by": [],
            "primary_upgrade_blocker": None,
            "refused_blocked_support": False,
            "reason": "no individual provenance claim is cited",
        }
    individual = _guard_verdict(qualify_claim(graph, claim_id))
    claims = {claim["id"]: claim for claim in graph["claims"]}
    current = set(claims[claim_id]["event_ids"])
    classified = set(claims[claim_id]["required_event_kinds"]) | set(
        claims[claim_id]["insufficient_event_kinds"]
    )
    events = {event["id"]: event for event in graph["observed_events"]}
    sources = {source["id"]: source for source in graph["source_records"]}
    extra = []
    for event_id in admissible_event_ids:
        event = events[event_id]
        if event_id in current:
            continue
        if event["event_kind"] not in classified:
            continue
        if event["event_kind"] not in {"independent_service_log", "committed_effect"}:
            continue
        if not event_verified(event, sources):
            continue
        extra.append(event_id)
    if not extra:
        return {
            "added": False,
            "individual_claim_id": claim_id,
            "individual_finding_label": individual["finding_label"],
            "augmented_finding_label": individual["finding_label"],
            "admissible_events_not_on_individual_claim": [],
            "upgrade_blocked_by": individual["upgrade_blocked_by"],
            "primary_upgrade_blocker": individual["primary_upgrade_blocker"],
            "refused_blocked_support": individual["refused_blocked_support"],
            "reason": "coordination cites no admissible event beyond the individual claim",
        }
    cloned = copy.deepcopy(graph)
    for claim in cloned["claims"]:
        if claim["id"] == claim_id:
            claim["event_ids"] = list(claim["event_ids"]) + extra
    augmented = _guard_verdict(qualify_claim(cloned, claim_id))
    # Support is not added while a blocking slot is still unused. A verified
    # contradiction may still change the verdict; a supported label may not.
    added = (
        individual["finding_label"] == "unresolved"
        and augmented["finding_label"] != individual["finding_label"]
        and not augmented["upgrade_blocked_by"]
        and not augmented["refused_blocked_support"]
    )
    return {
        "added": added,
        "individual_claim_id": claim_id,
        "individual_finding_label": individual["finding_label"],
        "augmented_finding_label": augmented["finding_label"],
        "admissible_events_not_on_individual_claim": extra,
        "upgrade_blocked_by": augmented["upgrade_blocked_by"],
        "primary_upgrade_blocker": augmented["primary_upgrade_blocker"],
        "refused_blocked_support": augmented["refused_blocked_support"],
        "reason": (
            "a coordination-only admissible event changes the provenance verdict"
            if added
            else (
                "a blocks_upgrade slot still prevents support"
                if augmented["upgrade_blocked_by"] or augmented["refused_blocked_support"]
                else "the added admissible events do not change the provenance verdict"
            )
        ),
    }


def _withheld(label: str, applied: set[str], seams: set[str], causal: bool) -> str:
    if label in applied:
        raise RuntimeError(label)
    if label == "causal_contribution_unresolved" and causal:
        return "traced_handoff_supports_link"
    if label == "goal_adoption_inferred" and (
        "communication_observed" in applied or "narrative_is_not_communication" in seams
    ):
        return "communication_is_not_goal_contagion"
    order = (
        "forged_or_copied_actor",
        "relay_not_authorship",
        "possession_not_contribution",
        "reused_file_without_handoff",
        "duplicate_report",
        "temporal_correlation_not_causal",
        "shared_vocabulary_not_causal",
        "investigator_inference_not_handoff",
        "narrative_is_not_communication",
        "incomplete_timeline",
        "missing_agent_instances",
        "missing_delegation_records",
        "narrative_time_not_promoted",
        "upgrade_blocker_remains",
    )
    for seam in order:
        if seam in seams:
            return seam
    if label == "communication_observed":
        return "no_verified_independent_service_log"
    if label == "delegation_evidenced":
        return "no_traced_handoff"
    return "not_admissible"


def _falsifiers(kind: str) -> list[str]:
    common = [
        "Possession or repetition of board content is not authorship and is not causal contribution.",
        "A copied or forged actor identifier is not a bound participant.",
        "A verified narrative_report verifies publication bytes only.",
        "A blocks_upgrade slot that no verified supporting event uses prevents an upgrade to supported. A log from a different source does not clear it.",
    ]
    specific = {
        "board_participation": [
            "communication_observed requires a verified independent_service_log with a bound speaker.",
            "An investigator-reported agent count is not a set of traced causal actors.",
            "A second publication in the same independence group is duplicate_report.",
        ],
        "delegated_workstream": [
            "delegation_evidenced requires both bound agents, an original message, a task, a verified independent_service_log for each agent, and source_stated times.",
            "An outline sentence is investigator_inference, not a handoff.",
        ],
        "collective_causal_impact": [
            "causal_contribution stays unresolved without a delegation_evidenced path to a verified committed_effect.",
            "A source_stated window on a narrative_report is not the effect chronology.",
            "Temporal correlation, shared vocabulary, a reused file, and investigator inference are not traced handoffs.",
        ],
    }
    return specific.get(kind, []) + common


def _world_complete(
    kind: str,
    applied: set[str],
    causal: bool,
    traced_actors: int,
    populations: list[dict[str, Any]],
    unavailable: list[dict[str, str]],
) -> bool:
    if unavailable:
        return False
    reported = [row for row in populations if row["count_label"] == "investigator_reported"]
    if any(row["held_by_audit"] is not False for row in reported):
        return False
    if kind == "board_participation":
        return "communication_observed" in applied and not reported
    if kind == "delegated_workstream":
        return "delegation_evidenced" in applied and not reported
    if kind == "collective_causal_impact":
        if not causal or traced_actors < 1:
            return False
        for row in reported:
            if row["unit"] == "agents" and row["count"] != traced_actors:
                return False
        return True
    return False


def qualify_case(case: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    """Qualify one coordination case along ``graph``'s evidence lineage."""
    indexed = validate_case(case, graph)
    prov = indexed["prov"]
    claim_id = case["provenance_claim_id"]
    indexed["provenance_claim"] = prov["claims"][claim_id] if claim_id else None
    qualified_edges = [_qualify_edge(edge, indexed) for edge in indexed["edges"]]
    _connect_contribution(qualified_edges, indexed)

    applied: set[str] = set()
    seams: set[str] = set()
    for edge in qualified_edges:
        applied.update(edge["labels"])
        seams.update(edge["seams"])
        edge.pop("delegation_ok", None)

    if not indexed["agents"]:
        seams.add("missing_agent_instances")
    if not indexed["delegations"] and case["proposition_kind"] in {
        "delegated_workstream",
        "collective_causal_impact",
    }:
        seams.add("missing_delegation_records")

    populations = [_population_view(row, prov) for row in indexed["populations"]]
    if any(row["count_label"] == "investigator_reported" for row in populations):
        seams.add("investigator_reported_population")

    cited_sources: set[str] = set()
    cited_events: list[str] = []
    for edge in qualified_edges:
        cited_sources.update(edge["provenance_source_ids"])
        cited_events.extend(edge["provenance_event_ids"])
    unavailable = _unavailable(cited_sources, prov)
    if any(row["coverage_status"] == "withheld" for row in unavailable):
        seams.add("withheld_source")
    if any(row["coverage_status"] == "unobserved" for row in unavailable):
        seams.add("unobserved_source")
    if any(row["coverage_status"] == "redacted" for row in unavailable):
        seams.add("redacted_source")

    causal = any(edge["causal_link_supported"] for edge in qualified_edges)
    traced = sorted(
        {
            indexed["delegations"][edge["from_id"]]["from_agent_id"]
            for edge in qualified_edges
            if edge["causal_link_supported"] and edge["from_id"] in indexed["delegations"]
        }
    )
    if case["proposition_kind"] == "collective_causal_impact" and not causal:
        applied.add("causal_contribution_unresolved")
        seams.add("causal_contribution_unresolved")

    admissible = []
    for edge in qualified_edges:
        if "delegation_evidenced" in edge["labels"]:
            admissible.extend(edge["verified_service_log_ids"])
        if edge["kind"] == "contribution":
            admissible.extend(edge["verified_effect_ids"])
    value = coordination_added_value(
        graph, case["provenance_claim_id"], list(dict.fromkeys(admissible))
    )
    if not value["added"]:
        seams.add("no_added_qualification_value")

    groups = _groups(list(dict.fromkeys(cited_events)), prov)
    kind_rejections = []
    for event_id in dict.fromkeys(cited_events):
        event = prov["events"][event_id]
        if event_verified(event, prov["sources"]):
            if event["event_kind"] == "narrative_report":
                kind_rejections.append(
                    {
                        "event_id": event_id,
                        "event_kind": event["event_kind"],
                        "reason": "excerpt digest verifies publication bytes, not communication or contribution",
                    }
                )
            continue
        kind_rejections.append(
            {
                "event_id": event_id,
                "event_kind": event["event_kind"],
                "reason": rejection_reason(event, prov["sources"]),
            }
        )

    if value.get("upgrade_blocked_by") or value.get("refused_blocked_support"):
        seams.add("upgrade_blocker_remains")
    world = case["proposition_kind"] in WORLD_KINDS
    complete = False
    if world:
        complete = _world_complete(
            case["proposition_kind"],
            applied,
            causal,
            len(traced),
            populations,
            unavailable,
        )
        # Incident and other provenance claims stay unresolved while a
        # blocking slot is unused, including when some other log verifies.
        if value.get("upgrade_blocked_by") or value.get("refused_blocked_support"):
            complete = False
    classified = classify_conclusion(
        evidence_complete=complete,
        property_holds=True if complete else None,
    )
    if classified["finding_label"] in {"reproduced", "classical_baseline_matches"} and (
        value.get("upgrade_blocked_by") or value.get("refused_blocked_support")
    ):
        classified = classify_conclusion(evidence_complete=False, property_holds=None)
    withheld = [
        {
            "label": label,
            "reason": _withheld(label, applied, seams, causal),
        }
        for label in sorted(LABELS - applied)
    ]
    individual = None
    if case["provenance_claim_id"] is not None:
        individual_claim = qualify_claim(graph, case["provenance_claim_id"])
        guarded = _guard_verdict(individual_claim)
        individual = {
            "claim_id": case["provenance_claim_id"],
            "finding_label": guarded["finding_label"],
            "primary_upgrade_blocker": guarded["primary_upgrade_blocker"],
            "upgrade_blocked_by": [row["source_id"] for row in guarded["upgrade_blocked_by"]],
            "independent_observation_count": individual_claim["independent_observation_count"],
            "coverage_denominator": individual_claim["coverage"]["denominator"],
            "refused_blocked_support": guarded["refused_blocked_support"],
        }

    return {
        "case_id": case["id"],
        "proposition": case["proposition"],
        "proposition_kind": case["proposition_kind"],
        "world_claim": world,
        "labels": sorted(applied),
        "withheld_labels": withheld,
        "edges": qualified_edges,
        "populations": populations,
        "traced_causal_actor_ids": traced,
        "traced_causal_actor_count": len(traced),
        "investigator_reported_agents_are_traced_actors": False,
        "independent_observation_count": len(groups),
        "independence_groups": groups,
        "unavailable_telemetry": unavailable,
        "kind_rejections": kind_rejections,
        "added_claim_qualification_value": value["added"],
        "qualification_value": value,
        "primary_upgrade_blocker": value.get("primary_upgrade_blocker"),
        "upgrade_blocked_by": [
            row["source_id"] for row in value.get("upgrade_blocked_by") or []
        ],
        "supported_while_blocked": False,
        "refused_blocked_support": bool(value.get("refused_blocked_support")),
        "individual": individual,
        "falsifiers": _falsifiers(case["proposition_kind"]),
        "unsupported_seams": sorted(seams),
        "intent_inferred": False,
        "goal_contagion_claimed": False,
        "conclusion_class": classified["conclusion_class"],
        "finding_label": classified["finding_label"],
        "property_holds": classified["property_holds"],
        "reason": classified["reason"],
        "real_world_authenticity_certified": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "provenance_contract": CONTRACT_VERSION,
        "coordination_version": COORDINATION_VERSION,
    }


def attribute_synthetic_scale(
    *,
    n_agents: int = SCALE_AGENTS,
    n_messages: int = SCALE_MESSAGES,
    n_handoffs: int = SCALE_HANDOFFS,
    seed: int = SCALE_SEED,
) -> dict[str, Any]:
    """One-pass attribution of an explicit synthetic handoff stream.

    The stream is size-comparable to the reported board and is not that board.
    Pairs are counted only for declared handoffs. No agent-pair matrix is built.
    """
    if n_agents < 2 or n_messages < 1 or n_handoffs < 0 or n_handoffs > n_messages:
        raise ValueError("synthetic scale sizes are out of range")
    rng = random.Random(seed)
    records_visited = 0
    pairs_considered = 0
    for index in range(n_messages):
        speaker = index % n_agents
        handoff = index < n_handoffs
        recipient = None
        if handoff:
            recipient = rng.randrange(n_agents - 1)
            if recipient >= speaker:
                recipient += 1
            pairs_considered += 1
        record = {
            "record_label": "synthetic",
            "incident_record": False,
            "message_id": f"syn-m-{index}",
            "from_agent": f"syn-a-{speaker}",
            "to_agent": None if recipient is None else f"syn-a-{recipient}",
            "kind": "handoff" if handoff else "message",
        }
        if record["record_label"] != "synthetic" or record["incident_record"] is not False:
            raise ValueError("scale fixture must stay synthetic")
        if not record["message_id"].startswith("syn-"):
            raise ValueError("scale fixture must not invent incident ids")
        records_visited += 1
    all_pairs = n_agents * (n_agents - 1) // 2
    return {
        "synthetic": True,
        "population_label": "synthetic",
        "incident_records_invented": False,
        "n_agents": n_agents,
        "n_messages": n_messages,
        "n_handoffs": n_handoffs,
        "seed": seed,
        "records_visited": records_visited,
        "pairs_considered": pairs_considered,
        "all_pairs": all_pairs,
        "agent_pair_matrix_allocated": False,
        "attribution_rule": "explicit_handoff_only",
    }


def attribute_stream(records: Any) -> dict[str, Any]:
    """Attribute an already-built synthetic stream without pairing the population."""
    if not isinstance(records, list):
        records = list(records)
    pairs = 0
    visited = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("synthetic record must be an object")
        if record.get("record_label") != "synthetic" or record.get("incident_record") is not False:
            raise ValueError("stream records must be labeled synthetic")
        message_id = record.get("message_id")
        if not isinstance(message_id, str) or not message_id.startswith("syn-"):
            raise ValueError("stream records must not use incident ids")
        visited += 1
        if record.get("kind") == "handoff":
            pairs += 1
    return {
        "synthetic": True,
        "incident_records_invented": False,
        "records_visited": visited,
        "pairs_considered": pairs,
        "agent_pair_matrix_allocated": False,
        "attribution_rule": "explicit_handoff_only",
    }
