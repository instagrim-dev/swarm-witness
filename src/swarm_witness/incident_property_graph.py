"""Property decomposition across URL, file, execution, credential, and effect boundaries.

Issue #29. A local control can hold while a broader safety property fails.
Verdicts reuse the #12 evidence-set partition (supported / refuted / unresolved):
verified and nonempty evidence is required; an empty or unverified set supports
nothing. Decision, attempted effect, and settlement stay separate coordinates,
as in the #10 effect ledger. A correct decision is not a settlement observation.

This module does not execute untrusted configs, read local secrets, or claim
that Swarm Witness detected or prevented any real incident. Public postmortem
text is narrative provenance, not an effect ledger.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

SCHEMA_VERSION = "incident_property_graph_v1"
SOURCE_PIN = "incident-property-graph-v1"

CHILDREN: tuple[str, ...] = (
    "P_url",
    "P_file_read",
    "P_exec",
    "P_identity",
    "P_effect",
)
SYSTEM = "P_system"

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
    return dict(graph)


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


def _validate_case(case: Mapping[str, Any]) -> None:
    case_id = _require_text(case, "id", "case")
    if case.get("claim_scope") not in {*CHILDREN, SYSTEM}:
        raise ValueError(f"{case_id}: claim_scope is not a known property")
    observed = case.get("observed_channels") or []
    if not isinstance(observed, list) or any(ch not in CHANNEL_SUBJECTS for ch in observed):
        raise ValueError(f"{case_id}: observed_channels must be known channels")
    seen: set[str] = set()
    for event in _events(case):
        event_id = _require_text(event, "id", case_id)
        if event_id in seen:
            raise ValueError(f"{case_id}: duplicate event {event_id}")
        seen.add(event_id)
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
    _ledger_index(case)
    for claim in case.get("narrative_claims") or []:
        if claim.get("authenticity") != "narrative_only":
            raise ValueError(f"{case_id}: narrative claim must be narrative_only")


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
    layers = [layer_view(event, ledger) for event in _events(case)]
    diagnosis = diagnose(case, child_verdicts=child, ledger=ledger)
    baseline = single_policy_pass_baseline(case)
    hidden = set(child) != set(CHILDREN) or (
        any(verdict == "refuted" for verdict in child.values()) and system == "supported"
    )
    graph_false = system == "supported" and any(verdict != "supported" for verdict in child.values())
    return {
        "case_id": case["id"],
        "kind": case.get("kind"),
        "claim_scope": case["claim_scope"],
        "child_verdicts": child,
        "system_verdict": system,
        "layers": layers,
        "diagnosis": diagnosis,
        "baseline_system": baseline,
        "baseline_false_system_support": baseline == "supported" and system != "supported",
        "baseline_false_system_reject": baseline == "refuted" and system == "supported",
        "graph_false_system_support": graph_false,
        "decision_used_as_effect_proof_count": _decision_proof_count(case, layers, ledger),
        "refuted_child_hidden": hidden,
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
    # Rejected implications have a verified witness.
    for antecedent, consequent in REJECTED_IMPLICATIONS:
        checks += 1
        if antecedent == "decision_deny":
            continue
        witness = {name: "supported" for name in CHILDREN}
        if consequent in CHILDREN:
            witness[consequent] = "refuted"
        elif consequent == SYSTEM:
            witness["P_file_read"] = "refuted"
        else:
            failures.append(["unknown_consequent", consequent])
            continue
        if witness[antecedent] != "supported" or conjoin(witness) == "supported":
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
        "observed_channels": [],
        "events": [],
        "effect_ledger": [],
        "narrative_claims": document.get("narrative_claims") or [],
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
    return {
        "case_id": document["case_id"],
        "graph_schema": graph["schema_version"],
        "provenance": "public_postmortem_narrative",
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
    )
    missing = [name for name in required if name not in by_id]
    if missing:
        raise ValueError(f"missing required fixtures: {missing}")
    focal = by_id["url_held_worker_local_read"]
    passed = (
        finite["passed"]
        and focal["child_verdicts"]["P_url"] == "supported"
        and focal["child_verdicts"]["P_file_read"] == "refuted"
        and focal["system_verdict"] == "refuted"
        and not focal["refuted_child_hidden"]
        and sum(result["graph_false_system_support"] for result in results) == 0
        and sum(result["baseline_false_system_support"] for result in results) >= 1
        and sum(result["decision_used_as_effect_proof_count"] for result in results) == 0
        and postmortem_score["independent_supported"] == 0
        and postmortem_score["independent_refuted"] == 0
        and postmortem_score["incident_detection_claimed"] is False
        and postmortem_score["incident_prevention_claimed"] is False
        and postmortem_score["if_narrative_were_mistaken_for_verified_verdicts"]["adopted_as_case_verdict"]
        is False
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
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "results": results,
        "postmortem": postmortem_score,
        "finite": {"passed": finite["passed"], "checks": finite["checks"],
                   "violation_count": finite["violation_count"],
                   "conservative_unresolved_gap": finite["conservative_unresolved_gap"]},
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
