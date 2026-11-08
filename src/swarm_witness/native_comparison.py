"""Project application-effect packets into competent-comparator observations.

The projection reads retained actor and sink records. It does not read
Swarm Witness verdicts, evidence-stage warrants, or harness truth.
"""

from __future__ import annotations

from typing import Any

from swarm_witness.comparison_score import summarize_method
from swarm_witness.conclusion_classes import classify_conclusion
from swarm_witness.strong_invariant import strong_invariant_verdict

EFFECT_TYPE = "application_effect_readback"
SINK_ACCESS = "application_sink"
APPLICATION_AUTHENTICITY = "application_owned_readback"
DECISION_TYPE = "policy_allow"


def p_effect_claim_id(history_id: str) -> str:
    return f"{history_id}:P_effect"


def p_effect_claim(history_id: str) -> dict[str, Any]:
    return {
        "id": p_effect_claim_id(history_id),
        "kind": "world_effect",
        "required_observation_types": [EFFECT_TYPE],
        "verifying_access_levels": [SINK_ACCESS],
    }


def conclusion_class_for_verdict(verdict: str) -> str:
    """Classify the P_effect proposition this row states.

    An effect-existence label is a different proposition and is not reused.
    """
    if verdict == "unresolved":
        classified = classify_conclusion(evidence_complete=False, property_holds=None)
    elif verdict == "supported":
        classified = classify_conclusion(evidence_complete=True, property_holds=True)
    elif verdict == "refuted":
        classified = classify_conclusion(
            evidence_complete=True,
            property_holds=False,
            mechanism_exercised=False,
        )
    else:
        raise ValueError(f"unknown P_effect verdict {verdict!r}")
    return str(classified["conclusion_class"])


def score_native_method(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    """Score one method against evidence-stage warrants and controlled truth."""
    subset = [row for row in rows if row["method"] == method]
    return summarize_method(subset, truth_known=True)


def _parse_body(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key] = value
    return fields


_REJECTED_PREMISE_AUTHENTICITY = frozenset(
    {
        "copied",
        "derived_same_origin",
        "spoofed_tool_line",
        "unauthenticated_tool_line",
        "spoofed",
        "unauthenticated",
        "forged",
        "disputed",
        "stale",
        "withheld",
    }
)
_WITHHELD_ACCESS = frozenset(
    {"withheld", "unobserved", "unavailable", "private_original"}
)


def _explicit_misbound(record: dict[str, Any], fields: dict[str, str]) -> bool:
    """A probe marker. The history slug ``binding-misbound`` is not one."""
    if (
        record.get("binding") == "misbound"
        or record.get("binding_basis") == "misbound"
        or record.get("actor_binding") == "misbound"
    ):
        return True
    slug = str(fields.get("history_id") or "").removeprefix("aew-v1-h-")
    if not slug:
        return False
    for value in (str(record.get("record_id") or ""), str(fields.get("event_id") or "")):
        if value.endswith("-misbound") and not value.endswith(slug):
            return True
    return False


def _premise_decides(record: dict[str, Any], fields: dict[str, str]) -> bool:
    """A row may decide only when it is held, current, and not explicitly invalid."""
    if _explicit_misbound(record, fields):
        return False
    if record.get("locally_held") is False:
        return False
    if record.get("access_level") in _WITHHELD_ACCESS:
        return False
    if record.get("redaction") == "withheld_original":
        return False
    if record.get("authenticity") in _REJECTED_PREMISE_AUTHENTICITY:
        return False
    if record.get("freshness") == "stale" or record.get("time_basis") == "stale":
        return False
    text = record.get("public_bytes")
    return isinstance(text, str) and bool(text.strip())


def _time_in_interval(fields: dict[str, str], when: Any) -> bool:
    start = fields.get("interval_start") or ""
    end = fields.get("interval_end") or ""
    if not isinstance(when, str) or "T" not in start or "T" not in end or not start < end:
        return False
    return start <= when < end


def _operations(fields: dict[str, str]) -> set[str]:
    return {part for part in (fields.get("operations") or "").split(",") if part}


def _declared_row_count(fields: dict[str, str]) -> int | None:
    raw = fields.get("row_count")
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _census_matches(
    coverage: tuple[dict[str, Any], dict[str, str]] | None,
    held_sinks: list[tuple[dict[str, Any], dict[str, str]]],
) -> bool:
    """Absence support requires the observer count to match commit-detail rows."""
    if coverage is None:
        return False
    declared = _declared_row_count(coverage[1])
    if declared is None:
        return False
    return declared == len(held_sinks)


def _held_sink(record: dict[str, Any]) -> bool:
    if record.get("surface") != "committed_effect":
        return False
    if record.get("locally_held") is False:
        return False
    if record.get("access_level") == "withheld":
        return False
    if record.get("redaction") == "withheld_original":
        return False
    text = record.get("public_bytes")
    return isinstance(text, str) and bool(text.strip())


def _base_observation(
    record: dict[str, Any],
    claim_id: str,
    *,
    applies: bool,
    quote: str,
) -> dict[str, Any]:
    return {
        "id": record.get("record_id") or record.get("source_id") or "record",
        "applies_to": [claim_id] if applies else [],
        "quote": quote,
        "authenticity": "not_checked",
        "access_level": record.get("access_level") or "public_bytes",
        "locally_held": record.get("locally_held") is not False,
        "binding": "unbound",
        "freshness": "current",
        "observation_types": [DECISION_TYPE],
        "literal_polarity": "reports",
        "literal_claims": [],
        "named_origin": "undetermined",
    }


def _retain_premise(obs: dict[str, Any], record: dict[str, Any], fields: dict[str, str]) -> None:
    """Keep an explicit defect. A later upgrade must not erase it."""
    if _explicit_misbound(record, fields):
        obs["binding"] = "misbound"
    if record.get("freshness") == "stale" or record.get("time_basis") == "stale":
        obs["freshness"] = "stale"
    authenticity = record.get("authenticity")
    if authenticity in _REJECTED_PREMISE_AUTHENTICITY:
        obs["authenticity"] = authenticity
    if record.get("locally_held") is False:
        obs["locally_held"] = False
    if record.get("access_level") in _WITHHELD_ACCESS or record.get("redaction") == "withheld_original":
        obs["locally_held"] = False
        obs["access_level"] = "withheld"
        obs["authenticity"] = "withheld"


def _sink_in_scope(
    record: dict[str, Any],
    fields: dict[str, str],
    coverage: tuple[dict[str, Any], dict[str, str]] | None,
    actors: list[tuple[dict[str, Any], dict[str, str]]],
) -> bool:
    """History id is not scope. The sink has to match the run, operation, and interval."""
    if coverage is None:
        return False
    covered = coverage[1]
    actor_runs = {item[1].get("run_id") for item in actors if item[1].get("run_id")}
    if actor_runs and fields.get("run_id") not in actor_runs:
        return False
    if fields.get("run_id") != covered.get("run_id"):
        return False
    if fields.get("operation_id") not in _operations(covered):
        return False
    return _time_in_interval(covered, record.get("event_time"))


def _stated(record: dict[str, Any], fields: dict[str, str], key: str) -> str:
    value = fields.get(key) or record.get(key)
    return value if isinstance(value, str) else ""


def _parent_maps_to_actor(
    record: dict[str, Any],
    fields: dict[str, str],
    actors: list[tuple[dict[str, Any], dict[str, str]]],
) -> bool:
    """A parent id is a mapping only when the relationship itself checks out.

    The named actor must share this sink's call. Actor, object, and event
    must then all agree, or all differ as the other binding of that call.
    A matching id with one rewritten field is an assertion, not that mapping.
    """
    parent = record.get("parent_id")
    if not isinstance(parent, str) or not parent:
        return False
    named = [
        (actor, actor_fields)
        for actor, actor_fields in actors
        if actor.get("record_id") == parent and _premise_decides(actor, actor_fields)
    ]
    if len(named) != 1:
        return False
    actor, actor_fields = named[0]
    sink_call = _stated(record, fields, "call_id")
    actor_call = _stated(actor, actor_fields, "call_id")
    if not sink_call or sink_call != actor_call:
        return False
    compared: list[bool] = []
    for key in ("actor_id", "object_scope", "event_id"):
        left = _stated(record, fields, key)
        right = _stated(actor, actor_fields, key)
        if not left or not right:
            return False
        compared.append(left == right)
    return all(compared) or not any(compared)


def _names_match_actor(
    fields: dict[str, str],
    actors: list[tuple[dict[str, Any], dict[str, str]]],
) -> bool:
    actor_id = fields.get("actor_id")
    object_scope = fields.get("object_scope")
    event_id = fields.get("event_id")
    if not actor_id or not object_scope or not event_id:
        return False
    return any(
        actor_fields.get("actor_id") == actor_id
        and actor_fields.get("object_scope") == object_scope
        and actor_fields.get("event_id") == event_id
        for _actor, actor_fields in actors
    )


def _binding_matches(
    record: dict[str, Any],
    fields: dict[str, str],
    actors: list[tuple[dict[str, Any], dict[str, str]]],
) -> bool:
    """Actor, object, and event match a declared actor, or a verified parent mapping says so."""
    return _parent_maps_to_actor(record, fields, actors) or _names_match_actor(fields, actors)


def _coverage_signature(fields: dict[str, str]) -> tuple[str, ...]:
    return (
        fields.get("run_id", ""),
        fields.get("operations", ""),
        fields.get("interval_start", ""),
        fields.get("interval_end", ""),
        fields.get("row_count", ""),
        fields.get("event_ids", ""),
    )


def _agreed_coverage(
    rows: list[tuple[dict[str, Any], dict[str, str]]],
) -> tuple[dict[str, Any], dict[str, str]] | None:
    """Identical censuses collapse. Disagreeing censuses do not resolve by order."""
    if not rows:
        return None
    if len({_coverage_signature(fields) for _record, fields in rows}) != 1:
        return None
    return rows[0]


def _absence_bound(
    coverage: tuple[dict[str, Any], dict[str, str]] | None,
    actors: list[tuple[dict[str, Any], dict[str, str]]],
    commits: list[tuple[dict[str, Any], dict[str, str]]],
) -> bool:
    """A zero-row census covers absence only when every actor event sits inside it."""
    if commits or coverage is None or not actors:
        return False
    record, fields = coverage
    if not _premise_decides(record, fields) or _declared_row_count(fields) != 0:
        return False
    operations = _operations(fields)
    for actor, actor_fields in actors:
        if actor_fields.get("run_id") != fields.get("run_id"):
            return False
        if actor_fields.get("operation_id") not in operations:
            return False
        if not _time_in_interval(fields, actor.get("event_time")):
            return False
    return True


def _decide(obs: dict[str, Any], claim_id: str, *, polarity: str) -> None:
    if obs.get("binding") == "misbound" or obs.get("freshness") == "stale":
        return
    if obs.get("authenticity") in _REJECTED_PREMISE_AUTHENTICITY or obs.get("authenticity") == "withheld":
        return
    if obs.get("locally_held") is False:
        return
    obs["authenticity"] = APPLICATION_AUTHENTICITY
    obs["access_level"] = SINK_ACCESS
    obs["locally_held"] = True
    obs["binding"] = "bound"
    obs["freshness"] = "current"
    obs["observation_types"] = [EFFECT_TYPE]
    obs["literal_polarity"] = polarity
    obs["literal_claims"] = [claim_id]
    obs["named_origin"] = SINK_ACCESS


def project_packet_observations(
    history_id: str, records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """One observation per retained record, plus no copied property verdict."""
    claim_id = p_effect_claim_id(history_id)
    observations: list[dict[str, Any]] = []
    held_sinks: list[tuple[dict[str, Any], dict[str, str]]] = []
    commit_rows: list[tuple[dict[str, Any], dict[str, str]]] = []
    actor_rows: list[tuple[dict[str, Any], dict[str, str]]] = []
    coverage_rows: list[tuple[dict[str, Any], dict[str, str]]] = []
    for record in records:
        text = record.get("public_bytes")
        fields = _parse_body(text) if isinstance(text, str) and text.strip() else {}
        record_history = fields.get("history_id")
        applies = record_history in {None, "", history_id}
        quote = text if isinstance(text, str) and text.strip() else str(record.get("record_id") or "")
        obs = _base_observation(record, claim_id, applies=applies, quote=quote)
        _retain_premise(obs, record, fields)
        if record.get("surface") == "requested_command":
            if fields.get("history_id") == history_id:
                actor_rows.append((record, fields))
            observations.append(obs)
            continue
        if not _held_sink(record) and record.get("surface") != "service_log":
            obs["authenticity"] = "withheld"
            obs["access_level"] = "withheld"
            obs["locally_held"] = False
            obs["observation_types"] = ["withheld_record"]
            observations.append(obs)
            continue
        if (
            record.get("action") == "coverage_scan"
            and record.get("surface") == "service_log"
            and fields.get("history_id") == history_id
        ):
            if _premise_decides(record, fields):
                coverage_rows.append((record, fields))
            obs["observation_types"] = ["effect_coverage"]
            observations.append(obs)
            continue
        if record.get("surface") == "committed_effect" and fields.get("history_id") == history_id:
            commit_rows.append((record, fields))
            if _held_sink(record) and _premise_decides(record, fields):
                held_sinks.append((record, fields))
            observations.append(obs)
            continue
        observations.append(obs)

    coverage = _agreed_coverage(coverage_rows)
    by_id = {obs["id"]: obs for obs in observations}
    unauthorized = [
        (record, fields)
        for record, fields in held_sinks
        if fields.get("subject_class") == "unauthorized_effect"
        and _sink_in_scope(record, fields, coverage, actor_rows)
    ]
    if unauthorized:
        for record, _fields in unauthorized:
            _decide(by_id[record["record_id"]], claim_id, polarity="refutes")
        return observations

    unknown_authorization = [
        (record, fields)
        for record, fields in held_sinks
        if fields.get("subject_class") not in {"authorized_effect", "unauthorized_effect"}
        and _sink_in_scope(record, fields, coverage, actor_rows)
    ]
    if unknown_authorization:
        return observations

    authorized = [
        (record, fields)
        for record, fields in held_sinks
        if fields.get("subject_class") == "authorized_effect"
        and _sink_in_scope(record, fields, coverage, actor_rows)
        and _binding_matches(record, fields, actor_rows)
    ]
    # A matching count is not enough. The census has to bind this run,
    # operation, and interval, and an unknown subject is not absence.
    if authorized and _census_matches(coverage, held_sinks):
        for record, _fields in authorized:
            _decide(by_id[record["record_id"]], claim_id, polarity="supports")
        return observations
    if _absence_bound(coverage, actor_rows, commit_rows):
        record, _fields = coverage  # type: ignore[misc]
        _decide(by_id[record["record_id"]], claim_id, polarity="supports")
    return observations


def competent_verdict(history_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the competent comparator on this packet's observations."""
    observations = project_packet_observations(history_id, records)
    detail = strong_invariant_verdict(p_effect_claim(history_id), observations)
    detail["observation_ids"] = [
        obs["id"]
        for obs in observations
        if p_effect_claim_id(history_id) in obs.get("applies_to", [])
    ]
    return detail
