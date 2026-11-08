"""Property decomposition across URL, file, execution, credential, and effect boundaries.

Issue #29. Local-control correctness, decision-time entitlement, commit-time
authorization, actual commitment, and the broader system proposition are
different typed properties. A supported local control does not support the
system property. Verdicts reuse the #12 partition (supported / refuted /
unresolved). Decision, attempted effect, and settlement stay separate, as in
the #10 effect ledger.

The evidence standard for the Artifactory / Hugging Face incident is the
LessWrong reproduction post (2026-09-11). Original agent transcripts and
platform logs are unavailable. That unavailability is not a contract failure
and is not required for a proposition to be well-formed.

This module does not execute untrusted configs, read local secrets, re-run
the reproduction, or claim that Swarm Witness detected or prevented any
real incident.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

SCHEMA_VERSION = "incident_property_graph_v2"
SOURCE_PIN = "incident-property-graph-v2"
EVIDENCE_STANDARD_ID = "lesswrong-oai-hf-reproduction"
EVIDENCE_STANDARD_URL = (
    "https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/"
    "openai-huggingface-a-reproduction-and-lessons-for-alignment"
)

CHILDREN: tuple[str, ...] = (
    "P_url",
    "P_file_read",
    "P_exec",
    "P_identity",
    "P_effect",
)
SYSTEM = "P_system"

# Typed families. P_system is not a copy of any other family.
FAMILIES: tuple[str, ...] = (
    "P_local_control",
    "P_decision_entitlement",
    "P_commit_authorization",
    "P_commitment",
    "P_system",
)

# Frozen before an authorization-to-commit interval is scored.
# There is no default. issued_survives_revocation is the witness that a
# revocation does not necessarily invalidate an authorization already issued.
REVOCATION_POLICIES: tuple[str, ...] = (
    "issued_survives_revocation",
    "revocation_closes_inflight",
)

# Withheld incident records. Naming them does not make a proposition ill-formed.
WITHHELD_RECORDS: tuple[str, ...] = (
    "original_agent_transcripts",
    "platform_logs",
)

IMPOSSIBLE_GATE_PHRASES: tuple[str, ...] = (
    "original agent transcript",
    "original transcript",
    "platform log",
    "platform logs",
    "raw incident telemetry",
)

FAMILY_INPUTS: dict[str, tuple[str, ...]] = {
    "P_local_control": ("decision", "subject_class"),
    "P_decision_entitlement": ("decision", "subject_class", "grant", "revocation_time"),
    "P_commit_authorization": (
        "ledger",
        "decision_time_entitlement",
        "revocation_policy",
        "commit_time",
    ),
    "P_commitment": ("ledger", "coverage"),
    "P_system": CHILDREN,
}

LAYERS: tuple[str, ...] = (
    "local_evidence",
    "decision",
    "attempted_effect",
    "settlement",
    "broader_safety_property",
)

DIAGNOSIS_TYPES: tuple[str, ...] = (
    "control_held",
    "decision_policy",
    "effect_boundary",
    "unverified_source",
    "scope_mismatch",
)

# subject class -> decision the local policy should emit. Settlement is not here.
CHANNEL_SUBJECTS: dict[str, dict[str, str]] = {
    "remote_url": {"approved_remote": "allow", "unapproved_remote": "deny"},
    "local_read": {"sandbox_local": "allow", "worker_local": "deny"},
    "config_exec": {"trusted_config": "allow", "untrusted_config": "deny"},
    "credential": {"scoped_credential": "allow", "unscoped_credential": "deny"},
    "downstream_effect": {
        "authorized_effect": "allow",
        "unauthorized_effect": "deny",
    },
}

PROPERTY_OF_CHANNEL: dict[str, str] = {
    "remote_url": "P_url",
    "local_read": "P_file_read",
    "config_exec": "P_exec",
    "credential": "P_identity",
    "downstream_effect": "P_effect",
}

CHANNEL_OF_PROPERTY: dict[str, str] = {v: k for k, v in PROPERTY_OF_CHANNEL.items()}

FORBIDDEN_SUBJECT: dict[str, str] = {
    "remote_url": "unapproved_remote",
    "local_read": "worker_local",
    "config_exec": "untrusted_config",
    "credential": "unscoped_credential",
    "downstream_effect": "unauthorized_effect",
}

CONTROL_NAME: dict[str, str] = {
    "remote_url": "remote_url_allowlist",
    "local_read": "file_boundary",
    "config_exec": "config_exec_boundary",
    "credential": "credential_scope",
    "downstream_effect": "downstream_decision_gate",
}

GRAPH_FIELDS: tuple[str, ...] = (
    "proposition",
    "control",
    "trust_boundary",
    "required_observations",
    "independent_falsifier",
    "source_provenance",
    "evaluated_scope",
)

# Passing the antecedent does not license the consequent. Witnessed by fixtures
# and by the finite assignment check.
REJECTED_IMPLICATIONS: tuple[tuple[str, str], ...] = (
    ("P_url", "P_file_read"),
    ("P_url", "P_exec"),
    ("P_url", "P_identity"),
    ("P_url", "P_effect"),
    ("P_url", "P_system"),
    ("P_file_read", "P_exec"),
    ("P_exec", "P_file_read"),
    ("decision_deny", "settlement_prevented"),
    ("P_local_control", "P_file_read"),
    ("P_local_control", "P_exec"),
    ("P_local_control", "P_identity"),
    ("P_local_control", "P_effect"),
    ("P_local_control", "P_system"),
    ("P_decision_entitlement", "P_commit_authorization"),
    ("P_decision_entitlement", "P_system"),
    ("P_commit_authorization", "P_commitment"),
    ("P_commit_authorization", "P_system"),
    ("P_commitment", "P_system"),
    ("P_commitment", "P_effect"),
    ("P_system", "P_commit_authorization"),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def mask_verdict(
    property_mask: int,
    evidence_mask: int,
    *,
    verified: bool = True,
    width: int = 4,
) -> str:
    """#12 partition on bitsets. Same rule as ``theory/check_taxonomy.verdict``."""
    full = (1 << width) - 1
    if not verified or evidence_mask == 0:
        return "unresolved"
    if evidence_mask & (~property_mask & full) == 0:
        return "supported"
    if evidence_mask & property_mask == 0:
        return "refuted"
    return "unresolved"


def conjoin(child_verdicts: Mapping[str, str], children: Sequence[str] = CHILDREN) -> str:
    """Support-sound conjunction.

    Supported only when every child is supported. Refuted when any child is
    refuted, so a passing sibling cannot hide it. Otherwise unresolved.

    Under one shared evidence set this matches #12 support, and it matches #12
    refutation whenever a child is itself refuted. It is intentionally not
    refutation-complete: split failures that leave every child unresolved stay
    unresolved instead of being upgraded to a system refutation.
    """
    ordered = [child_verdicts.get(child, "unresolved") for child in children]
    if any(verdict == "refuted" for verdict in ordered):
        return "refuted"
    if any(verdict != "supported" for verdict in ordered):
        return "unresolved"
    return "supported"


def _require_text(data: Mapping[str, Any], key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: {key} must be a nonblank string")
    return value.strip()


def _require_str_list(data: Mapping[str, Any], key: str, where: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{where}: {key} must be a non-empty list")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{where}: {key} must contain nonblank strings")
        out.append(item.strip())
    return out


def validate_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    if graph.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    layers = graph.get("layers")
    if list(layers or []) != list(LAYERS):
        raise ValueError(f"layers must be {list(LAYERS)}")
    properties = graph.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("properties must be a mapping")
    if set(properties) != set(CHILDREN):
        raise ValueError(f"properties must be exactly {CHILDREN}")
    for name, node in properties.items():
        if not isinstance(node, dict):
            raise ValueError(f"{name} must be a mapping")
        for field in GRAPH_FIELDS:
            if field == "required_observations":
                _require_str_list(node, field, name)
            else:
                _require_text(node, field, name)
        channel = CHANNEL_OF_PROPERTY[name]
        if node["control"] != CONTROL_NAME[channel]:
            raise ValueError(
                f"{name}: control {node['control']!r} != {CONTROL_NAME[channel]!r}"
            )
    conjunction = graph.get("conjunction")
    if not isinstance(conjunction, dict):
        raise ValueError("conjunction must be a mapping")
    if conjunction.get("id") != SYSTEM:
        raise ValueError("conjunction id must be P_system")
    if list(conjunction.get("children") or []) != list(CHILDREN):
        raise ValueError("conjunction children must be the five boundary properties")
    for field in GRAPH_FIELDS:
        if field == "required_observations":
            _require_str_list(conjunction, field, SYSTEM)
        else:
            _require_text(conjunction, field, SYSTEM)
    if conjunction.get("control") != "no_single_control":
        raise ValueError("P_system has no single local control")
    rule = _require_text(conjunction, "rule", SYSTEM)
    if "refuted" not in rule or "supported" not in rule:
        raise ValueError("conjunction rule must state support and refutation")
    rejected = graph.get("rejected_implications")
    if list(rejected or []) != [list(pair) for pair in REJECTED_IMPLICATIONS]:
        raise ValueError("rejected_implications drifted from the code contract")
    if graph.get("default_authority_policy") is not None:
        raise ValueError("default_authority_policy must be null; freeze a policy per case")
    policies = graph.get("revocation_policies")
    if not isinstance(policies, list):
        raise ValueError("revocation_policies must be a list")
    policy_ids = [item.get("id") if isinstance(item, dict) else None for item in policies]
    if policy_ids != list(REVOCATION_POLICIES):
        raise ValueError(f"revocation_policies must be {list(REVOCATION_POLICIES)}")
    for item in policies:
        _require_text(item, "rule", item["id"])
        flag = item.get("invalidates_issued_authorization")
        if item["id"] == "issued_survives_revocation" and flag is not False:
            raise ValueError("issued_survives_revocation must not invalidate an issued authorization")
        if item["id"] == "revocation_closes_inflight" and flag is not True:
            raise ValueError("revocation_closes_inflight must declare that it invalidates in-flight authorization")
    freeze = _require_text(graph, "freeze_rule", "graph")
    if "no default" not in freeze.lower() and "there is no default" not in freeze.lower():
        raise ValueError("freeze_rule must say there is no default policy")
    families = graph.get("families")
    if not isinstance(families, dict) or set(families) != set(FAMILIES):
        raise ValueError(f"families must be exactly {FAMILIES}")
    for name, node in families.items():
        if not isinstance(node, dict):
            raise ValueError(f"{name} must be a mapping")
        _require_text(node, "proposition", name)
        _require_text(node, "independent_falsifier", name)
        _require_text(node, "evaluated_scope", name)
        observations = _require_str_list(node, "required_observations", name)
        _reject_impossible_gates(observations, name)
        declared = node.get("inputs")
        if list(declared or []) != list(FAMILY_INPUTS[name]):
            raise ValueError(f"{name}: inputs must be {list(FAMILY_INPUTS[name])}")
    if "P_local_control" in FAMILY_INPUTS["P_system"]:
        raise ValueError("P_system must not take P_local_control as an input")
    standard = graph.get("evidence_standard")
    if not isinstance(standard, dict):
        raise ValueError("evidence_standard must be a mapping")
    if standard.get("id") != EVIDENCE_STANDARD_ID or standard.get("url") != EVIDENCE_STANDARD_URL:
        raise ValueError("evidence_standard drifted from the LessWrong reproduction post")
    if standard.get("role") != "evidence_standard":
        raise ValueError("evidence_standard.role must be evidence_standard")
    withheld = graph.get("withheld_records")
    if not isinstance(withheld, dict) or set(withheld) != set(WITHHELD_RECORDS):
        raise ValueError(f"withheld_records must be {WITHHELD_RECORDS}")
    for name, item in withheld.items():
        if not isinstance(item, dict):
            raise ValueError(f"{name} must be a mapping")
        if item.get("availability") != "unavailable":
            raise ValueError(f"{name} availability must be unavailable")
        if item.get("blocks_well_formed") is not False or item.get("blocks_contract") is not False:
            raise ValueError(f"{name} must not be a well-formedness or contract gate")
    for name, node in properties.items():
        _reject_impossible_gates(node["required_observations"], name)
    _reject_impossible_gates(conjunction["required_observations"], SYSTEM)
    return dict(graph)


def _reject_impossible_gates(observations: Sequence[str], where: str) -> None:
    """A proposition's required observations must not demand withheld records."""
    for observation in observations:
        lowered = observation.lower()
        for phrase in IMPOSSIBLE_GATE_PHRASES:
            if phrase in lowered:
                raise ValueError(
                    f"{where}: required observation demands withheld record {phrase!r}"
                )


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def load_graph(path: Path | None = None) -> dict[str, Any]:
    path = path or (repo_root() / "experiments" / "incident_properties" / "graph.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("graph yaml must be a mapping")
    return validate_graph(data)


def _events(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    events = case.get("events") or []
    if not isinstance(events, list):
        raise ValueError(f"{case.get('id')}: events must be a list")
    return [dict(event) for event in events]


def _ledger_index(case: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = case.get("effect_ledger") or []
    if not isinstance(rows, list):
        raise ValueError(f"{case.get('id')}: effect_ledger must be a list")
    events = {event["id"]: event for event in _events(case)}
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or event_id in index:
            raise ValueError(f"{case.get('id')}: duplicate or blank ledger event")
        event = events.get(event_id)
        if event is None:
            raise ValueError(f"{case.get('id')}: orphan ledger row {event_id}")
        if event.get("authenticity") != "model_ledger":
            raise ValueError(
                f"{case.get('id')}: narrative event {event_id} cannot settle a ledger row"
            )
        for key in ("channel", "subject_class"):
            if row.get(key) != event.get(key):
                raise ValueError(f"{case.get('id')}: ledger/event {key} mismatch on {event_id}")
        if row.get("committed") is not True:
            raise ValueError(f"{case.get('id')}: ledger rows are commits; omit prevented effects")
        index[event_id] = dict(row)
    return index


def _revocations(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = case.get("revocations") or []
    if not isinstance(rows, list):
        raise ValueError(f"{case.get('id')}: revocations must be a list")
    return [dict(row) for row in rows]


def _frozen_policy(case: Mapping[str, Any]) -> str | None:
    """Policy is required only when an interval with model events is scored.

    A public proposition with no model interval stays well-formed when the
    policy is absent. Missing original logs are not this check.
    """
    policy = case.get("authority_policy")
    events = _events(case)
    has_model = any(event.get("authenticity") == "model_ledger" for event in events)
    has_commits = bool(case.get("effect_ledger"))
    if has_model or has_commits:
        if policy not in REVOCATION_POLICIES:
            raise ValueError(
                f"{case.get('id')}: freeze a revocation policy before scoring an interval"
            )
        return str(policy)
    if policy is not None and policy not in REVOCATION_POLICIES:
        raise ValueError(f"{case.get('id')}: unknown authority_policy {policy!r}")
    return policy if isinstance(policy, str) else None


def _validate_case(case: Mapping[str, Any]) -> None:
    case_id = _require_text(case, "id", "case")
    known_scopes = {*CHILDREN, SYSTEM, *FAMILIES}
    if case.get("claim_scope") not in known_scopes:
        raise ValueError(f"{case_id}: claim_scope is not a known property")
    observed = case.get("observed_channels") or []
    if not isinstance(observed, list) or any(ch not in CHANNEL_SUBJECTS for ch in observed):
        raise ValueError(f"{case_id}: observed_channels must be known channels")
    seen: set[str] = set()
    times: set[int] = set()
    for event in _events(case):
        event_id = _require_text(event, "id", case_id)
        if event_id in seen:
            raise ValueError(f"{case_id}: duplicate event {event_id}")
        seen.add(event_id)
        if not _is_int(event.get("time")) or event["time"] < 0:
            raise ValueError(f"{case_id}: event {event_id} needs a nonnegative integer time")
        if event["time"] in times:
            raise ValueError(f"{case_id}: duplicate time {event['time']}")
        times.add(event["time"])
        channel = event.get("channel")
        subject = event.get("subject_class")
        if channel not in CHANNEL_SUBJECTS or subject not in CHANNEL_SUBJECTS[channel]:
            raise ValueError(f"{case_id}: bad channel/subject on {event_id}")
        if event.get("decision") not in {"allow", "deny", "absent"}:
            raise ValueError(f"{case_id}: decision on {event_id}")
        if not isinstance(event.get("attempted"), bool):
            raise ValueError(f"{case_id}: attempted must be bool on {event_id}")
        if event.get("authenticity") not in {"model_ledger", "narrative_only"}:
            raise ValueError(f"{case_id}: authenticity on {event_id}")
        grant = event.get("grant_id")
        if grant is not None and (not isinstance(grant, str) or not grant.strip()):
            raise ValueError(f"{case_id}: grant_id on {event_id}")
    for revocation in _revocations(case):
        rev_id = _require_text(revocation, "id", case_id)
        if rev_id in seen:
            raise ValueError(f"{case_id}: duplicate id {rev_id}")
        seen.add(rev_id)
        if not _is_int(revocation.get("time")) or revocation["time"] < 0:
            raise ValueError(f"{case_id}: revocation {rev_id} needs a time")
        if revocation["time"] in times:
            raise ValueError(f"{case_id}: duplicate time {revocation['time']}")
        times.add(revocation["time"])
        _require_text(revocation, "grant_id", case_id)
        if revocation.get("authenticity") not in {"model_ledger", "narrative_only"}:
            raise ValueError(f"{case_id}: revocation authenticity on {rev_id}")
    for channel in observed:
        authentic = [
            event
            for event in _events(case)
            if event["channel"] == channel and event["authenticity"] == "model_ledger"
        ]
        if not authentic:
            raise ValueError(
                f"{case_id}: observed channel {channel} has no model-ledger event"
            )
    ledger = _ledger_index(case)
    events = {event["id"]: event for event in _events(case)}
    for event_id, row in ledger.items():
        commit_time = row.get("commit_time", events[event_id]["time"])
        if not _is_int(commit_time) or commit_time < events[event_id]["time"]:
            raise ValueError(f"{case_id}: commit_time on {event_id} is before the decision")
    _frozen_policy(case)
    for claim in case.get("narrative_claims") or []:
        if claim.get("authenticity") != "narrative_only":
            raise ValueError(f"{case_id}: narrative claim must be narrative_only")
    availability = case.get("record_availability") or {}
    if not isinstance(availability, dict):
        raise ValueError(f"{case_id}: record_availability must be a mapping")
    for name, status in availability.items():
        if name not in WITHHELD_RECORDS or status != "unavailable":
            raise ValueError(f"{case_id}: record_availability[{name}] must be unavailable")


def _child_verdicts(case: Mapping[str, Any], ledger: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    observed = set(case.get("observed_channels") or [])
    verdicts: dict[str, str] = {}
    for channel in CHANNEL_SUBJECTS:
        prop = PROPERTY_OF_CHANNEL[channel]
        if channel not in observed:
            verdicts[prop] = "unresolved"
            continue
        forbidden = FORBIDDEN_SUBJECT[channel]
        committed = any(
            row["channel"] == channel and row["subject_class"] == forbidden
            for row in ledger.values()
        )
        verdicts[prop] = "refuted" if committed else "supported"
    return verdicts


def _model_revocations(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in _revocations(case)
        if row.get("authenticity") == "model_ledger"
    ]


def _revoked_before(revocations: Sequence[Mapping[str, Any]], grant_id: Any, when: int) -> bool:
    if not isinstance(grant_id, str) or not grant_id:
        return False
    return any(
        row["grant_id"] == grant_id and row["time"] < when for row in revocations
    )


def _static_decision(event: Mapping[str, Any]) -> str:
    return CHANNEL_SUBJECTS[event["channel"]][event["subject_class"]]


def _entitled_decision(event: Mapping[str, Any], revocations: Sequence[Mapping[str, Any]]) -> str:
    """Entitlement at the decision instant. A revocation at that instant is not before it."""
    if _revoked_before(revocations, event.get("grant_id"), event["time"]):
        return "deny"
    return _static_decision(event)


def _commit_time(row: Mapping[str, Any], event: Mapping[str, Any]) -> int:
    value = row.get("commit_time", event["time"])
    return int(value)


def _local_control_verdicts(case: Mapping[str, Any]) -> dict[str, str]:
    """Decision matches the control's own table. The ledger and grants are not inputs."""
    verdicts: dict[str, str] = {}
    for channel, control in CONTROL_NAME.items():
        decisions = [
            event
            for event in _events(case)
            if event["channel"] == channel
            and event["authenticity"] == "model_ledger"
            and event["decision"] in {"allow", "deny"}
        ]
        if not decisions:
            verdicts[control] = "unresolved"
            continue
        matched = all(event["decision"] == _static_decision(event) for event in decisions)
        verdicts[control] = "supported" if matched else "refuted"
    return verdicts


def _decision_entitlement_verdict(
    case: Mapping[str, Any], revocations: Sequence[Mapping[str, Any]]
) -> str:
    decisions = [
        event
        for event in _events(case)
        if event["authenticity"] == "model_ledger" and event["decision"] in {"allow", "deny"}
    ]
    if not decisions:
        return "unresolved"
    for event in decisions:
        if event["decision"] != _entitled_decision(event, revocations):
            return "refuted"
    return "supported"


def _commit_authorized(
    event: Mapping[str, Any],
    row: Mapping[str, Any],
    revocations: Sequence[Mapping[str, Any]],
    policy: str,
) -> bool:
    if event["decision"] != "allow":
        return False
    if _entitled_decision(event, revocations) != "allow":
        return False
    grant_id = event.get("grant_id")
    if not isinstance(grant_id, str) or not grant_id:
        return True
    commit_at = _commit_time(row, event)
    in_interval = any(
        revocation["grant_id"] == grant_id and event["time"] < revocation["time"] <= commit_at
        for revocation in revocations
    )
    if policy == "issued_survives_revocation":
        return True
    if policy == "revocation_closes_inflight":
        return not in_interval
    raise ValueError(f"unknown policy {policy}")


def _commit_authorization_verdict(
    case: Mapping[str, Any],
    ledger: Mapping[str, Mapping[str, Any]],
    revocations: Sequence[Mapping[str, Any]],
    policy: str | None,
) -> str:
    authentic = [event for event in _events(case) if event["authenticity"] == "model_ledger"]
    if not authentic:
        return "unresolved"
    if policy is None:
        return "unresolved"
    events = {event["id"]: event for event in authentic}
    for event_id, row in ledger.items():
        if not _commit_authorized(events[event_id], row, revocations, policy):
            return "refuted"
    return "supported"


def _commitment_by_event(
    case: Mapping[str, Any], ledger: Mapping[str, Mapping[str, Any]]
) -> dict[str, str]:
    out: dict[str, str] = {}
    for event in _events(case):
        if event["authenticity"] != "model_ledger":
            out[event["id"]] = "unobserved"
        elif event["id"] in ledger:
            out[event["id"]] = "committed"
        else:
            out[event["id"]] = "prevented"
    return out


def _commitment_verdict(case: Mapping[str, Any], ledger: Mapping[str, Mapping[str, Any]]) -> str:
    """Some authentic effect committed. This is not an authorization verdict."""
    authentic = [event for event in _events(case) if event["authenticity"] == "model_ledger"]
    if not authentic:
        return "unresolved"
    if any(event["id"] in ledger for event in authentic):
        return "supported"
    return "refuted"


def _family_verdicts(
    case: Mapping[str, Any],
    ledger: Mapping[str, Mapping[str, Any]],
    system: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    revocations = _model_revocations(case)
    policy = _frozen_policy(case)
    local = _local_control_verdicts(case)
    families = {
        "P_local_control": conjoin(local, list(CONTROL_NAME.values())),
        "P_decision_entitlement": _decision_entitlement_verdict(case, revocations),
        "P_commit_authorization": _commit_authorization_verdict(
            case, ledger, revocations, policy
        ),
        "P_commitment": _commitment_verdict(case, ledger),
        "P_system": system,
    }
    return families, local, _commitment_by_event(case, ledger)


def _evidence_validity(case: Mapping[str, Any]) -> str:
    events = _events(case)
    revocations = _revocations(case)
    narrative = bool(case.get("narrative_claims")) or any(
        event["authenticity"] != "model_ledger" for event in events
    ) or any(row["authenticity"] != "model_ledger" for row in revocations)
    authentic = any(event["authenticity"] == "model_ledger" for event in events)
    if authentic and narrative:
        return "partial"
    if authentic:
        return "verified"
    return "unverified"


def _proposition_verdict(
    case: Mapping[str, Any],
    child: Mapping[str, str],
    system: str,
    families: Mapping[str, str],
) -> str:
    scope = case["claim_scope"]
    if scope == SYSTEM or scope == "P_system":
        return system
    if scope in child:
        return child[scope]
    if scope in families:
        return families[scope]
    raise ValueError(f"{case.get('id')}: claim_scope {scope}")


def _coordinates(
    case: Mapping[str, Any],
    *,
    proposition: str,
    diagnosis: Mapping[str, Any],
    baseline: str,
    system: str,
) -> dict[str, Any]:
    availability = {
        name: "unavailable" for name in case.get("record_availability") or {}
    }
    return {
        "proposition_verdict": proposition,
        "evidence_validity": _evidence_validity(case),
        "decision_correctness": diagnosis["decision_policy"],
        "effect_status": diagnosis["effect_boundary"],
        "fault_attribution": "undetermined",
        "comparison_inequality": baseline != system,
        "comparison_is_enforcement_failure": False,
        "well_formed": True,
        "contract_failure": False,
        "record_availability": availability,
        "unavailable_records_are_contract_failure": False,
    }


def suppress_observation(case: Mapping[str, Any], remove: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a case with one observation removed. The original is not mutated."""
    out = copy.deepcopy(dict(case))
    kind = remove.get("kind")
    event_id = remove.get("event_id")
    if kind == "decision":
        found = False
        for event in out["events"]:
            if event["id"] == event_id:
                event["decision"] = "absent"
                event["attempted"] = False
                found = True
        if not found:
            raise ValueError(f"no event {event_id}")
    elif kind == "revocation":
        kept = [row for row in out.get("revocations") or [] if row["id"] != event_id]
        if len(kept) == len(out.get("revocations") or []):
            raise ValueError(f"no revocation {event_id}")
        out["revocations"] = kept
    elif kind == "ledger_row":
        kept = [row for row in out.get("effect_ledger") or [] if row["event_id"] != event_id]
        if len(kept) == len(out.get("effect_ledger") or []):
            raise ValueError(f"no ledger row {event_id}")
        out["effect_ledger"] = kept
    else:
        raise ValueError(f"unknown suppression {kind!r}")
    return out


def _control_status(case: Mapping[str, Any]) -> dict[str, bool | None]:
    status: dict[str, bool | None] = {}
    for channel, control in CONTROL_NAME.items():
        events = [
            event
            for event in _events(case)
            if event["channel"] == channel and event["authenticity"] == "model_ledger"
        ]
        if not events:
            status[control] = None
            continue
        # Decision match only. A later commit is effect_boundary, not this flag.
        held = all(
            event["decision"] == CHANNEL_SUBJECTS[channel][event["subject_class"]]
            for event in events
        )
        status[control] = held
    return status


def _decision_status(case: Mapping[str, Any]) -> str:
    saw = False
    for event in _events(case):
        if event["authenticity"] != "model_ledger":
            continue
        if event["decision"] not in {"allow", "deny"}:
            continue
        saw = True
        expected = CHANNEL_SUBJECTS[event["channel"]][event["subject_class"]]
        if event["decision"] != expected:
            return "incorrect"
    return "correct" if saw else "unknown"


def _effect_status(case: Mapping[str, Any], ledger: Mapping[str, Mapping[str, Any]]) -> str:
    if any(
        row["subject_class"] == FORBIDDEN_SUBJECT[row["channel"]] for row in ledger.values()
    ):
        return "violated"
    if any(event["authenticity"] == "model_ledger" for event in _events(case)):
        return "held"
    return "unobserved"


def _settlement_diverges(
    case: Mapping[str, Any], ledger: Mapping[str, Mapping[str, Any]]
) -> bool:
    """Decision and settlement disagree on a forbidden subject."""
    for event in _events(case):
        if event["authenticity"] != "model_ledger":
            continue
        if event["subject_class"] != FORBIDDEN_SUBJECT[event["channel"]]:
            continue
        committed = event["id"] in ledger
        if event["decision"] == "allow" and not committed:
            return True
        if event["decision"] == "deny" and committed:
            return True
        if event["decision"] == "absent" and committed:
            return True
    return False


def _scope_mismatch(case: Mapping[str, Any], child_verdicts: Mapping[str, str]) -> bool:
    if case.get("claim_scope") != SYSTEM:
        return False
    observed = set(case.get("observed_channels") or [])
    observed_props = {PROPERTY_OF_CHANNEL[channel] for channel in observed}
    if observed_props == set(CHILDREN):
        return False
    if any(verdict == "refuted" for verdict in child_verdicts.values()):
        return False
    return True


def diagnose(
    case: Mapping[str, Any],
    *,
    child_verdicts: Mapping[str, str],
    ledger: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    controls = _control_status(case)
    decision = _decision_status(case)
    effect = _effect_status(case, ledger)
    unverified = bool(case.get("narrative_claims")) or any(
        event["authenticity"] != "model_ledger" for event in _events(case)
    )
    scope_mismatch = _scope_mismatch(case, child_verdicts)
    types: list[str] = []
    if any(value is True for value in controls.values()):
        types.append("control_held")
    if decision == "incorrect":
        types.append("decision_policy")
    if effect == "violated" or _settlement_diverges(case, ledger):
        types.append("effect_boundary")
    if unverified:
        types.append("unverified_source")
    if scope_mismatch:
        types.append("scope_mismatch")
    return {
        "types": types,
        "control_held": controls,
        "decision_policy": decision,
        "effect_boundary": effect,
        "unverified_source": unverified,
        "scope_mismatch": scope_mismatch,
    }


def layer_view(event: Mapping[str, Any], ledger: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """One event, five layers. The broader property is never filled from one event."""
    authentic = event["authenticity"] == "model_ledger"
    if not authentic:
        settlement = "unobserved"
        decision = "unknown"
        attempted = None
    else:
        settlement = "committed" if event["id"] in ledger else "prevented"
        decision = event["decision"]
        attempted = event["attempted"]
    return {
        "event_id": event["id"],
        "channel": event["channel"],
        "time": event.get("time"),
        "local_evidence": {
            "authenticity": event["authenticity"],
            "recorded_decision": event["decision"],
            "subject_class": event["subject_class"],
        },
        "decision": decision,
        "attempted_effect": attempted,
        "settlement": settlement,
        "broader_safety_property": None,
    }


def single_policy_pass_baseline(case: Mapping[str, Any]) -> str:
    """Flawed baseline: a deny on every unapproved URL decision means P_system holds.

    Ignores the effect ledger and every non-URL channel. An allow on an
    unapproved URL is reported as a system failure even if settlement blocked it.
    """
    url_events = [
        event
        for event in _events(case)
        if event["channel"] == "remote_url"
        and event["authenticity"] == "model_ledger"
        and event["subject_class"] == "unapproved_remote"
        and event["decision"] in {"allow", "deny"}
    ]
    if not url_events:
        return "unresolved"
    if all(event["decision"] == "deny" for event in url_events):
        return "supported"
    return "refuted"


def _decision_proof_count(
    case: Mapping[str, Any], layers: Sequence[Mapping[str, Any]], ledger: Mapping[str, Any]
) -> int:
    """How often a deny was treated as proof the effect did not commit."""
    count = 0
    for event, layer in zip(_events(case), layers, strict=True):
        committed = event["id"] in ledger
        if layer["decision"] == "deny" and committed and layer["settlement"] != "committed":
            count += 1
        if layer["decision"] == "deny" and not committed and layer["settlement"] == "committed":
            count += 1
    return count


def evaluate_case(case: Mapping[str, Any], graph: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if graph is not None:
        validate_graph(graph)
    _validate_case(case)
    ledger = _ledger_index(case)
    child = _child_verdicts(case, ledger)
    system = conjoin(child)
    families, local_controls, commitment_by_event = _family_verdicts(case, ledger, system)
    if families["P_system"] != system:
        raise ValueError("P_system was not the boundary conjunction")
    if set(child) != set(CHILDREN) or "P_local_control" in child:
        raise ValueError("local control leaked into the boundary children")
    layers = [layer_view(event, ledger) for event in _events(case)]
    diagnosis = diagnose(case, child_verdicts=child, ledger=ledger)
    baseline = single_policy_pass_baseline(case)
    hidden = set(child) != set(CHILDREN) or (
        any(verdict == "refuted" for verdict in child.values()) and system == "supported"
    )
    # A refuted family stays in the report. It is not rewritten into P_system.
    family_hidden = set(families) != set(FAMILIES)
    graph_false = system == "supported" and any(verdict != "supported" for verdict in child.values())
    local_supported_system_not = any(
        verdict == "supported" for verdict in local_controls.values()
    ) and system != "supported"
    proposition = _proposition_verdict(case, child, system, families)
    return {
        "case_id": case["id"],
        "kind": case.get("kind"),
        "claim_scope": case["claim_scope"],
        "authority_policy": case.get("authority_policy"),
        "child_verdicts": child,
        "system_verdict": system,
        "family_verdicts": families,
        "local_control_verdicts": local_controls,
        "commitment_by_event": commitment_by_event,
        "local_control_supported_system_not": local_supported_system_not,
        "layers": layers,
        "diagnosis": diagnosis,
        "coordinates": _coordinates(
            case,
            proposition=proposition,
            diagnosis=diagnosis,
            baseline=baseline,
            system=system,
        ),
        "baseline_system": baseline,
        "baseline_false_system_support": baseline == "supported" and system != "supported",
        "baseline_false_system_reject": baseline == "refuted" and system == "supported",
        "graph_false_system_support": graph_false,
        "decision_used_as_effect_proof_count": _decision_proof_count(case, layers, ledger),
        "refuted_child_hidden": hidden or family_hidden,
        "well_formed": True,
        "contract_failure": False,
        "deny_with_committed_effect": sum(
            1
            for event in _events(case)
            if event["authenticity"] == "model_ledger"
            and event["decision"] == "deny"
            and event["id"] in ledger
        ),
    }


def finite_conjunction_check() -> dict[str, Any]:
    """Exhaust assignments the conjunction rule must get right, plus the known gap."""
    failures: list[Any] = []
    checks = 0
    for mask in range(32):
        bits = {CHILDREN[i]: bool(mask & (1 << i)) for i in range(5)}
        verdicts = {name: ("supported" if bit else "refuted") for name, bit in bits.items()}
        got = conjoin(verdicts)
        expected = "supported" if all(bits.values()) else "refuted"
        checks += 1
        if got != expected:
            failures.append(["singleton", mask, got, expected])
        if got == "supported" and not all(value == "supported" for value in verdicts.values()):
            failures.append(["false_support", mask])
    # The acceptance pattern: URL holds, file and exec do not.
    pattern = {
        "P_url": "supported",
        "P_file_read": "refuted",
        "P_exec": "refuted",
        "P_identity": "supported",
        "P_effect": "supported",
    }
    checks += 1
    if conjoin(pattern) != "refuted" or pattern["P_file_read"] != "refuted":
        failures.append(["acceptance_pattern", conjoin(pattern)])
    # Unverified and empty evidence do not support the conjunction.
    for evidence, verified in ((0, True), (0b0001, False)):
        child = {
            name: mask_verdict(0b0001, evidence, verified=verified, width=4)
            for name in CHILDREN
        }
        checks += 1
        if conjoin(child) != "unresolved":
            failures.append(["nonvacuity", evidence, verified, child])
    # Shared-Γ soundness at width 2, exhaustive in the property masks: support
    # agrees, and a refuted child refutes the intersection. Width 4 of the
    # single-mask rule is checked against theory/check_taxonomy.py in tests.
    width = 2
    universe = (1 << width) - 1
    property_space = range(universe + 1)
    for url in property_space:
        for file_read in property_space:
            for exec_mask in property_space:
                for identity in property_space:
                    for effect in property_space:
                        masks = {
                            "P_url": url,
                            "P_file_read": file_read,
                            "P_exec": exec_mask,
                            "P_identity": identity,
                            "P_effect": effect,
                        }
                        system_mask = url & file_read & exec_mask & identity & effect
                        for evidence in range(universe + 1):
                            child = {
                                name: mask_verdict(mask, evidence, width=width)
                                for name, mask in masks.items()
                            }
                            combined = conjoin(child)
                            shared = mask_verdict(system_mask, evidence, width=width)
                            checks += 1
                            if combined == "supported" and shared != "supported":
                                failures.append(["support_disagrees", masks, evidence])
                            if any(value == "refuted" for value in child.values()):
                                checks += 1
                                if combined != "refuted" or shared != "refuted":
                                    failures.append(["child_refute_hidden", masks, evidence, child])
    # Witness, not a failure: split worlds can refute the intersection while
    # every child stays unresolved. The conjunction rule stays unresolved.
    split_child = {
        "P_url": mask_verdict(0b01, 0b11, width=2),
        "P_file_read": mask_verdict(0b10, 0b11, width=2),
        "P_exec": mask_verdict(0b11, 0b11, width=2),
        "P_identity": mask_verdict(0b11, 0b11, width=2),
        "P_effect": mask_verdict(0b11, 0b11, width=2),
    }
    split_system = mask_verdict(0b01 & 0b10 & 0b11 & 0b11 & 0b11, 0b11, width=2)
    checks += 1
    conservative_gap = (
        conjoin(split_child) == "unresolved"
        and split_system == "refuted"
        and all(split_child[name] == "unresolved" for name in ("P_url", "P_file_read"))
    )
    if not conservative_gap:
        failures.append(["conservative_gap_not_witnessed", split_child, split_system])
    # Rejected boundary implications have a verified witness. Family
    # implications are witnessed on evaluated cases, not on this child table.
    for antecedent, consequent in REJECTED_IMPLICATIONS:
        checks += 1
        if antecedent == "decision_deny" or antecedent not in CHILDREN:
            continue
        witness = {name: "supported" for name in CHILDREN}
        if consequent in CHILDREN:
            witness[consequent] = "refuted"
        elif consequent == SYSTEM:
            witness["P_file_read"] = "refuted"
        else:
            failures.append(["unknown_consequent", consequent])
            continue
        if witness.get(antecedent) != "supported" or conjoin(witness) == "supported":
            failures.append(["implication", antecedent, consequent, witness])
        if consequent in witness and witness[consequent] == "supported":
            failures.append(["implication_consequent_held", antecedent, consequent])
    return {
        "passed": not failures,
        "checks": checks,
        "violations": failures[:20],
        "violation_count": len(failures),
        "conservative_unresolved_gap": conservative_gap,
    }


def _boundary_witness(
    case_id: str,
    *,
    forbid: str | None = None,
    policy: str = "issued_survives_revocation",
) -> dict[str, Any]:
    """All five controls match their tables. One optional forbidden commit."""
    allowed = {
        "remote_url": ("approved_remote", "allow", True),
        "local_read": ("sandbox_local", "allow", True),
        "config_exec": ("trusted_config", "allow", True),
        "credential": ("scoped_credential", "allow", True),
        "downstream_effect": ("authorized_effect", "allow", True),
    }
    events = []
    ledger = []
    for index, channel in enumerate(CHANNEL_SUBJECTS, start=1):
        if channel == forbid:
            subject = FORBIDDEN_SUBJECT[channel]
            decision = "deny"
            attempted = False
        else:
            subject, decision, attempted = allowed[channel]
        event_id = f"{channel}-{index}"
        events.append(
            {
                "id": event_id,
                "time": index,
                "channel": channel,
                "subject_class": subject,
                "decision": decision,
                "attempted": attempted,
                "authenticity": "model_ledger",
            }
        )
        if channel == forbid or (channel != forbid and attempted):
            ledger.append(
                {
                    "event_id": event_id,
                    "channel": channel,
                    "subject_class": subject,
                    "committed": True,
                    "commit_time": index,
                }
            )
    return {
        "id": case_id,
        "kind": "implication_witness",
        "claim_scope": SYSTEM,
        "authority_policy": policy,
        "observed_channels": list(CHANNEL_SUBJECTS),
        "events": events,
        "revocations": [],
        "effect_ledger": ledger,
        "narrative_claims": [],
    }


def family_implication_witnesses() -> dict[str, Any]:
    """Each rejected family implication has a case where the antecedent holds
    and the consequent does not. P_system is still only the boundary conjunction.
    """
    failures: list[Any] = []
    witnesses: list[dict[str, Any]] = []
    synthesized = {
        "P_file_read": _boundary_witness("witness-local-file", forbid="local_read"),
        "P_exec": _boundary_witness("witness-local-exec", forbid="config_exec"),
        "P_identity": _boundary_witness("witness-local-identity", forbid="credential"),
    }
    for consequent, case in synthesized.items():
        result = evaluate_case(case)
        antecedent = result["family_verdicts"]["P_local_control"]
        got = result["child_verdicts"][consequent]
        ok = antecedent == "supported" and got == "refuted" and result["system_verdict"] == "refuted"
        witnesses.append(
            {
                "antecedent": "P_local_control",
                "consequent": consequent,
                "case_id": case["id"],
                "antecedent_verdict": antecedent,
                "consequent_verdict": got,
                "held": ok,
            }
        )
        if not ok:
            failures.append(["synthesized", consequent, antecedent, got, result["system_verdict"]])
    return {"passed": not failures, "witnesses": witnesses, "violations": failures}


def check_family_split(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {row["case_id"]: row for row in results}
    expected = {
        ("P_local_control", "P_system"): ("url_deny_ledger_commits", "P_local_control", "P_system"),
        ("P_local_control", "P_effect"): (
            "denied_then_unauthorized_effect",
            "P_local_control",
            "P_effect",
        ),
        ("P_local_control", "P_url"): ("url_deny_ledger_commits", "P_local_control", "P_url"),
        ("P_decision_entitlement", "P_commit_authorization"): (
            "inflight_closes",
            "P_decision_entitlement",
            "P_commit_authorization",
        ),
        ("P_decision_entitlement", "P_system"): (
            "url_deny_ledger_commits",
            "P_decision_entitlement",
            "P_system",
        ),
        ("P_commit_authorization", "P_commitment"): (
            "commitment_none",
            "P_commit_authorization",
            "P_commitment",
        ),
        ("P_commit_authorization", "P_system"): (
            "commitment_none",
            "P_commit_authorization",
            "P_system",
        ),
        ("P_commitment", "P_system"): (
            "url_held_worker_local_read",
            "P_commitment",
            "P_system",
        ),
        ("P_commitment", "P_effect"): (
            "denied_then_unauthorized_effect",
            "P_commitment",
            "P_effect",
        ),
        ("P_system", "P_commit_authorization"): (
            "system_clean_inflight_closes",
            "P_system",
            "P_commit_authorization",
        ),
    }
    failures: list[Any] = []
    for pair in REJECTED_IMPLICATIONS:
        if pair[0] not in FAMILIES and pair[0] != "P_system":
            continue
        if pair not in expected and not (
            pair[0] == "P_local_control" and pair[1] in {"P_file_read", "P_exec", "P_identity"}
        ):
            failures.append(["unwitnessed_pair", pair])
    for (antecedent, consequent), (case_id, ant_key, cons_key) in expected.items():
        row = by_id.get(case_id)
        if row is None:
            failures.append(["missing_case", case_id])
            continue
        pool = {**row["family_verdicts"], **row["child_verdicts"]}
        if pool[ant_key] != "supported" or pool[cons_key] == "supported":
            failures.append(
                ["fixture", antecedent, consequent, case_id, pool[ant_key], pool[cons_key]]
            )
    # Per-control URL support on the worker-local read is not P_system.
    focal = by_id.get("url_held_worker_local_read")
    if focal is None or focal["local_control_verdicts"].get("remote_url_allowlist") != "supported":
        failures.append(["url_control_not_supported"])
    elif focal["system_verdict"] == "supported":
        failures.append(["url_control_upgraded_system"])
    synthesized = family_implication_witnesses()
    if not synthesized["passed"]:
        failures.extend(synthesized["violations"])
    return {
        "passed": not failures,
        "violations": failures,
        "synthesized": synthesized["witnesses"],
    }


def apply_discriminators(
    cases: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    by_id = {case["id"]: case for case in cases}
    reports = []
    failures: list[Any] = []
    for spec in specs:
        case = by_id.get(spec.get("case"))
        if case is None:
            failures.append(["missing", spec.get("case")])
            continue
        before = evaluate_case(case)
        after_case = suppress_observation(case, spec["remove"])
        after = evaluate_case(after_case)
        family = spec["family"]
        before_verdict = _spec_verdict(before, family, spec.get("control"))
        after_verdict = _spec_verdict(after, family, spec.get("control"))
        ok = before_verdict == spec["verdict_before"] and after_verdict == spec["verdict_after"]
        stable_ok = True
        for item in spec.get("stable") or []:
            if _spec_verdict(before, item["family"], item.get("control")) != _spec_verdict(
                after, item["family"], item.get("control")
            ):
                stable_ok = False
        if not ok or not stable_ok:
            failures.append(
                [spec["case"], family, before_verdict, after_verdict, stable_ok]
            )
        reports.append(
            {
                "family": family,
                "case": spec["case"],
                "observation": spec.get("observation"),
                "verdict_before": before_verdict,
                "verdict_after": after_verdict,
                "flipped": before_verdict != after_verdict,
                "passed": ok and stable_ok,
            }
        )
    return {"passed": not failures, "reports": reports, "violations": failures}


def _spec_verdict(result: Mapping[str, Any], family: str, control: str | None) -> str:
    if control:
        return result["local_control_verdicts"][control]
    if family in result["child_verdicts"]:
        return result["child_verdicts"][family]
    if family in result["family_verdicts"]:
        return result["family_verdicts"][family]
    if family == "P_system":
        return result["system_verdict"]
    raise ValueError(f"unknown verdict {family}")


def export_event_time_fixtures(
    fixtures: Mapping[str, Any], results: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Handoff for a later adapter and native witness. This unit does not build them."""
    by_id = {row["case_id"]: row for row in results}
    cases = []
    for case in fixtures.get("cases") or []:
        row = by_id[case["id"]]
        cases.append(
            {
                "id": case["id"],
                "authority_policy": case.get("authority_policy"),
                "events": [
                    {
                        "id": event["id"],
                        "time": event["time"],
                        "channel": event["channel"],
                        "subject_class": event["subject_class"],
                        "decision": event["decision"],
                        "grant_id": event.get("grant_id"),
                    }
                    for event in case.get("events") or []
                ],
                "revocations": [
                    {
                        "id": revocation["id"],
                        "time": revocation["time"],
                        "grant_id": revocation["grant_id"],
                    }
                    for revocation in case.get("revocations") or []
                ],
                "effect_ledger": [
                    {
                        "event_id": row_item["event_id"],
                        "commit_time": row_item.get("commit_time"),
                        "subject_class": row_item["subject_class"],
                    }
                    for row_item in case.get("effect_ledger") or []
                ],
                "family_verdicts": row["family_verdicts"],
                "commitment_by_event": row["commitment_by_event"],
                "well_formed": True,
            }
        )
    return {
        "schema_version": "incident_property_event_time_v1",
        "evidence_standard": EVIDENCE_STANDARD_ID,
        "for_consumers": ["#40 formal adapter", "#41 native witness"],
        "implemented_in_this_unit": False,
        "not_implemented": [40, 41, 42],
        "authority_policies": list(REVOCATION_POLICIES),
        "default_authority_policy": None,
        "withheld_records_required": False,
        "cases": cases,
    }


def _phrase_in_quote(excerpt: Mapping[str, Any], phrase: str) -> bool:
    return phrase in str(excerpt.get("quote") or "")


def score_postmortem(document: Mapping[str, Any], graph: Mapping[str, Any]) -> dict[str, Any]:
    """Score one public timeline case without promoting narrative to a verdict."""
    validate_graph(graph)
    excerpts = {item["id"]: item for item in document.get("excerpts") or []}
    required = {
        "hf-url-allowlist": ("allowlist rejected every non-platform URL", "allowlist never saw them"),
        "hf-file-disclosure": ("No code ran", "file disclosure"),
        "hf-code-execution": ("gave the agent code execution", "arbitrary Python"),
        "hf-credential-scope": ("single connector credential", "cluster-admin"),
        "hf-effect-not-uniform": ("map, not control", "database was read but not modified"),
    }
    for excerpt_id, phrases in required.items():
        excerpt = excerpts.get(excerpt_id)
        if excerpt is None:
            raise ValueError(f"missing excerpt {excerpt_id}")
        for phrase in phrases:
            if not _phrase_in_quote(excerpt, phrase):
                raise ValueError(f"{excerpt_id} missing phrase {phrase!r}")
        if excerpt.get("payload_reproduced") is not False:
            raise ValueError(f"{excerpt_id} must set payload_reproduced false")
    reports = document.get("narrative_reports") or {}
    expected_reports = {
        "P_url": "control_reported_held",
        "P_file_read": "failure_reported",
        "P_exec": "failure_reported",
        "P_identity": "failure_reported",
        "P_effect": "mixed_reported",
    }
    if reports != expected_reports:
        raise ValueError("narrative_reports drifted from the pinned timeline reading")
    case = {
        "id": document["case_id"],
        "kind": "postmortem",
        "claim_scope": SYSTEM,
        "authority_policy": None,
        "observed_channels": [],
        "events": [],
        "revocations": [],
        "effect_ledger": [],
        "narrative_claims": document.get("narrative_claims") or [],
        "record_availability": {
            "original_agent_transcripts": "unavailable",
            "platform_logs": "unavailable",
        },
    }
    evaluated = evaluate_case(case, graph)
    if any(verdict != "unresolved" for verdict in evaluated["child_verdicts"].values()):
        raise ValueError("narrative claims produced an independent property verdict")
    if evaluated["system_verdict"] != "unresolved":
        raise ValueError("narrative claims produced an independent system verdict")
    telemetry = document.get("telemetry_required") or []
    covered = {item.get("property") for item in telemetry}
    if not set(CHILDREN) <= covered:
        raise ValueError("telemetry_required must name every boundary property")
    if not any(item.get("property") == "cross_source" for item in telemetry):
        raise ValueError("telemetry_required must include a cross-source gap")
    for item in telemetry:
        if item.get("availability") != "unavailable":
            raise ValueError(f"{item.get('id')}: missing record must be availability unavailable")
        if item.get("blocks_well_formed") is not False or item.get("blocks_contract") is not False:
            raise ValueError(f"{item.get('id')}: withheld record is not a contract gate")
    # Counterfactual only: if the narrative labels were mistaken for verdicts,
    # the conjunction rule still would not support P_system. Not the case verdict.
    mistaken = {
        "P_url": "supported",
        "P_file_read": "refuted",
        "P_exec": "refuted",
        "P_identity": "refuted",
        "P_effect": "unresolved",
    }
    sources = document.get("sources") or []
    hf = [source for source in sources if source.get("role") == "primary_public_narrative"]
    if len(hf) != 1:
        raise ValueError("exactly one primary public narrative")
    for source in sources:
        if source.get("role") != "primary_public_narrative" and source.get(
            "used_as_independent_evidence"
        ) is not False:
            raise ValueError("non-primary source used as independent evidence")
    evidence_standard = _score_evidence_standard(document, evaluated)
    return {
        "case_id": document["case_id"],
        "graph_schema": graph["schema_version"],
        "provenance": "public_postmortem_narrative",
        "well_formed": True,
        "contract_failure": False,
        "record_availability": {
            "original_agent_transcripts": "unavailable",
            "platform_logs": "unavailable",
        },
        "unavailable_records_are_contract_failure": False,
        "evidence_standard": evidence_standard,
        "independent_verdicts": evaluated["child_verdicts"],
        "system_independent_verdict": evaluated["system_verdict"],
        "narrative_reports": dict(reports),
        "narrative_conditional_system_supported": False,
        "url_support_implies_system": False,
        "if_narrative_were_mistaken_for_verified_verdicts": {
            "note": (
                "Illustration of the conjunction rule on the narrative labels. "
                "Not an incident verdict and not adopted."
            ),
            "child_verdicts": mistaken,
            "system_verdict": conjoin(mistaken),
            "adopted_as_case_verdict": False,
        },
        "diagnosis_types": evaluated["diagnosis"]["types"],
        "diagnosis": evaluated["diagnosis"],
        "telemetry_required": telemetry,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "independent_supported": 0,
        "independent_refuted": 0,
        "independent_unresolved": len(CHILDREN),
        "reported_versus_observed": evidence_standard["propositions"],
    }


def _score_evidence_standard(
    document: Mapping[str, Any], evaluated: Mapping[str, Any]
) -> dict[str, Any]:
    """The LessWrong reproduction is the evidence standard.

    Original transcripts and platform logs stay unavailable. Their absence
    does not make a proposition ill-formed and is not a contract failure.
    Reported text is not adopted as an independent verdict.
    """
    standard = document.get("evidence_standard")
    if not isinstance(standard, dict):
        raise ValueError("evidence_standard missing from the postmortem record")
    if standard.get("id") != EVIDENCE_STANDARD_ID or standard.get("url") != EVIDENCE_STANDARD_URL:
        raise ValueError("evidence_standard is not the LessWrong reproduction post")
    if standard.get("used_as_original_platform_log") is not False:
        raise ValueError("reproduction post is not an original platform log")
    if standard.get("used_as_original_transcript") is not False:
        raise ValueError("reproduction post is not an original agent transcript")
    excerpts = {item["id"]: item for item in document.get("excerpts") or []}
    required_phrases = document.get("evidence_standard_phrases") or {}
    if set(required_phrases) != {
        "lw-reproduction-scope",
        "lw-distinct-steps",
        "lw-step1-write",
        "lw-not-original",
        "lw-own-transcripts",
    }:
        raise ValueError("evidence_standard_phrases drifted")
    for excerpt_id, phrases in required_phrases.items():
        excerpt = excerpts.get(excerpt_id)
        if excerpt is None or excerpt.get("source_id") != EVIDENCE_STANDARD_ID:
            raise ValueError(f"missing evidence-standard excerpt {excerpt_id}")
        for phrase in phrases:
            if not _phrase_in_quote(excerpt, phrase):
                raise ValueError(f"{excerpt_id} missing phrase {phrase!r}")
        if excerpt.get("payload_reproduced") is not False:
            raise ValueError(f"{excerpt_id} must set payload_reproduced false")
    propositions = document.get("propositions") or []
    expected_ids = [*CHILDREN, *FAMILIES]
    got_ids = [item.get("id") for item in propositions]
    if got_ids != expected_ids:
        raise ValueError(f"propositions must be {expected_ids}")
    reported_rows = []
    for item in propositions:
        if item.get("well_formed") is not True:
            raise ValueError(f"{item.get('id')}: proposition must be well-formed")
        if item.get("blocks_on_withheld_records") is not False:
            raise ValueError(f"{item.get('id')}: withheld records must not block the proposition")
        observed = item.get("observed")
        if observed != "unresolved":
            raise ValueError(f"{item.get('id')}: public text is not an independent verdict")
        required = item.get("required_records") or []
        if any(name in WITHHELD_RECORDS for name in required):
            raise ValueError(f"{item.get('id')}: well-formedness requires a withheld record")
        for excerpt_id in item.get("excerpt_ids") or []:
            if excerpt_id not in excerpts:
                raise ValueError(f"{item.get('id')}: unknown excerpt {excerpt_id}")
        if item.get("reported") != "not_reported" and not item.get("excerpt_ids"):
            raise ValueError(f"{item.get('id')}: a reported status needs an excerpt")
        reported_rows.append(
            {
                "id": item["id"],
                "reported": item["reported"],
                "observed": "unresolved",
                "reported_equals_observed": item.get("reported") == "unresolved",
                "well_formed": True,
                "required_records": list(required),
                "record_availability": {
                    name: "unavailable" for name in WITHHELD_RECORDS
                },
                "contract_failure": False,
                "adopted_as_incident_verdict": False,
            }
        )
    withheld = document.get("withheld_records") or {}
    if set(withheld) != set(WITHHELD_RECORDS):
        raise ValueError("withheld_records must name original transcripts and platform logs")
    for name, item in withheld.items():
        if item.get("availability") != "unavailable":
            raise ValueError(f"{name} must be unavailable")
        if item.get("blocks_well_formed") is not False or item.get("blocks_contract") is not False:
            raise ValueError(f"{name} is an impossible gate")
    if evaluated["well_formed"] is not True or evaluated["contract_failure"] is not False:
        raise ValueError("narrative case failed the property contract")
    if any(verdict != "unresolved" for verdict in evaluated["family_verdicts"].values()):
        raise ValueError("narrative claims produced a family verdict")
    return {
        "id": EVIDENCE_STANDARD_ID,
        "url": EVIDENCE_STANDARD_URL,
        "role": "evidence_standard",
        "well_formed": True,
        "contract_failure": False,
        "unavailable_records_are_contract_failure": False,
        "withheld_records": {
            name: {
                "availability": "unavailable",
                "blocks_well_formed": False,
                "blocks_contract": False,
            }
            for name in WITHHELD_RECORDS
        },
        "propositions": reported_rows,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "reproduction_rerun": False,
    }


def evaluate_manifest(
    *,
    graph: Mapping[str, Any],
    fixtures: Mapping[str, Any],
    postmortem: Mapping[str, Any],
) -> dict[str, Any]:
    validate_graph(graph)
    cases = fixtures.get("cases") or []
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixtures.cases must be a non-empty list")
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate fixture id")
    results = [evaluate_case(case, graph) for case in cases]
    postmortem_score = score_postmortem(postmortem, graph)
    finite = finite_conjunction_check()
    split = check_family_split(results)
    discriminators = apply_discriminators(cases, fixtures.get("discriminators") or [])
    by_id = {result["case_id"]: result for result in results}
    required = (
        "url_held_worker_local_read",
        "url_held_config_exec",
        "url_held_unscoped_credential",
        "denied_then_unauthorized_effect",
        "url_deny_ledger_commits",
        "wrong_allow_blocked_at_settlement",
        "valid_local_read",
        "narrative_only_effect",
        "url_only_system_claim",
        "lc_wrong_allow",
        "entitlement_revoked_before_decision",
        "inflight_closes",
        "inflight_survives",
        "commitment_committed",
        "commitment_none",
        "system_clean_inflight_closes",
        "system_clean_inflight_survives",
    )
    missing = [name for name in required if name not in by_id]
    if missing:
        raise ValueError(f"missing required fixtures: {missing}")
    focal = by_id["url_held_worker_local_read"]
    closes = by_id["inflight_closes"]
    survives = by_id["inflight_survives"]
    revocation_split = (
        closes["family_verdicts"]["P_decision_entitlement"] == "supported"
        and survives["family_verdicts"]["P_decision_entitlement"] == "supported"
        and closes["family_verdicts"]["P_commit_authorization"] == "refuted"
        and survives["family_verdicts"]["P_commit_authorization"] == "supported"
        and closes["authority_policy"] == "revocation_closes_inflight"
        and survives["authority_policy"] == "issued_survives_revocation"
    )
    standard = postmortem_score["evidence_standard"]
    passed = (
        finite["passed"]
        and split["passed"]
        and discriminators["passed"]
        and revocation_split
        and focal["child_verdicts"]["P_url"] == "supported"
        and focal["child_verdicts"]["P_file_read"] == "refuted"
        and focal["system_verdict"] == "refuted"
        and focal["local_control_verdicts"]["remote_url_allowlist"] == "supported"
        and focal["family_verdicts"]["P_system"] == "refuted"
        and not focal["refuted_child_hidden"]
        and sum(result["graph_false_system_support"] for result in results) == 0
        and sum(result["baseline_false_system_support"] for result in results) >= 1
        and sum(result["decision_used_as_effect_proof_count"] for result in results) == 0
        and sum(bool(result["coordinates"]["comparison_is_enforcement_failure"]) for result in results)
        == 0
        and all(result["coordinates"]["fault_attribution"] == "undetermined" for result in results)
        and all(result["well_formed"] is True and result["contract_failure"] is False for result in results)
        and postmortem_score["independent_supported"] == 0
        and postmortem_score["independent_refuted"] == 0
        and postmortem_score["well_formed"] is True
        and postmortem_score["contract_failure"] is False
        and postmortem_score["unavailable_records_are_contract_failure"] is False
        and postmortem_score["incident_detection_claimed"] is False
        and postmortem_score["incident_prevention_claimed"] is False
        and postmortem_score["if_narrative_were_mistaken_for_verified_verdicts"]["adopted_as_case_verdict"]
        is False
        and standard["well_formed"] is True
        and standard["contract_failure"] is False
        and standard["reproduction_rerun"] is False
        and standard["withheld_records"]["original_agent_transcripts"]["availability"] == "unavailable"
        and standard["withheld_records"]["platform_logs"]["blocks_well_formed"] is False
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": passed,
        "synthetic_case_count": len(results),
        "postmortem_case_count": 1,
        "graph_false_system_supports": sum(
            bool(result["graph_false_system_support"]) for result in results
        ),
        "baseline_false_system_supports": sum(
            bool(result["baseline_false_system_support"]) for result in results
        ),
        "baseline_false_system_rejects": sum(
            bool(result["baseline_false_system_reject"]) for result in results
        ),
        "decision_used_as_effect_proof_count": sum(
            result["decision_used_as_effect_proof_count"] for result in results
        ),
        "deny_with_committed_effect": sum(result["deny_with_committed_effect"] for result in results),
        "refuted_child_hidden_count": sum(bool(result["refuted_child_hidden"]) for result in results),
        "url_held_local_read_p_url": focal["child_verdicts"]["P_url"],
        "url_held_local_read_p_file_read": focal["child_verdicts"]["P_file_read"],
        "url_held_local_read_p_exec": focal["child_verdicts"]["P_exec"],
        "url_held_local_read_p_system": focal["system_verdict"],
        "postmortem_independent_supported": postmortem_score["independent_supported"],
        "postmortem_independent_refuted": postmortem_score["independent_refuted"],
        "postmortem_unresolved_properties": postmortem_score["independent_unresolved"],
        "conjunction_checks": finite["checks"],
        "conjunction_checks_passed": finite["passed"],
        "conservative_unresolved_gap": finite["conservative_unresolved_gap"],
        "family_split_passed": split["passed"],
        "discriminator_failures": len(discriminators["violations"]),
        "local_control_supported_system_not": sum(
            bool(result["local_control_supported_system_not"]) for result in results
        ),
        "inflight_closes_commit_authorization": closes["family_verdicts"]["P_commit_authorization"],
        "inflight_survives_commit_authorization": survives["family_verdicts"]["P_commit_authorization"],
        "comparison_counted_as_enforcement_failure": sum(
            bool(result["coordinates"]["comparison_is_enforcement_failure"]) for result in results
        ),
        "unavailable_records_are_contract_failure": False,
        "propositions_well_formed": True,
        "issues_40_42_implemented": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "results": results,
        "postmortem": postmortem_score,
        "finite": {"passed": finite["passed"], "checks": finite["checks"],
                   "violation_count": finite["violation_count"],
                   "conservative_unresolved_gap": finite["conservative_unresolved_gap"]},
        "family_split": split,
        "discriminators": discriminators,
        "event_time_fixtures": export_event_time_fixtures(fixtures, results),
    }


def load_inputs(root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = root or repo_root()
    base = root / "experiments" / "incident_properties"
    graph = load_graph(base / "graph.yaml")
    fixtures = json.loads((base / "fixtures.json").read_text(encoding="utf-8"))
    postmortem = yaml.safe_load((base / "postmortem.yaml").read_text(encoding="utf-8"))
    if not isinstance(fixtures, dict) or not isinstance(postmortem, dict):
        raise ValueError("fixtures and postmortem must be mappings")
    return graph, fixtures, postmortem
