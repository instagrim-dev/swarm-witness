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


def _misbound(record: dict[str, Any], fields: dict[str, str]) -> bool:
    record_id = str(record.get("record_id") or "")
    event_id = fields.get("event_id") or ""
    return record_id.endswith("-misbound") or event_id.endswith("-misbound")


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


def project_packet_observations(
    history_id: str, records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """One observation per retained record, plus no copied property verdict."""
    claim_id = p_effect_claim_id(history_id)
    observations: list[dict[str, Any]] = []
    held_sinks: list[tuple[dict[str, Any], dict[str, str]]] = []
    coverage: tuple[dict[str, Any], dict[str, str]] | None = None
    for record in records:
        text = record.get("public_bytes")
        fields = _parse_body(text) if isinstance(text, str) and text.strip() else {}
        record_history = fields.get("history_id")
        applies = record_history in {None, "", history_id}
        quote = text if isinstance(text, str) and text.strip() else str(record.get("record_id") or "")
        obs = _base_observation(record, claim_id, applies=applies, quote=quote)
        if _misbound(record, fields):
            obs["binding"] = "misbound"
        if record.get("surface") == "requested_command":
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
            coverage = (record, fields)
            obs["observation_types"] = ["effect_coverage"]
            observations.append(obs)
            continue
        if _held_sink(record) and fields.get("history_id") == history_id:
            held_sinks.append((record, fields))
            observations.append(obs)
            continue
        observations.append(obs)

    unauthorized = [
        (record, fields)
        for record, fields in held_sinks
        if fields.get("subject_class") == "unauthorized_effect"
    ]
    if unauthorized:
        by_id = {obs["id"]: obs for obs in observations}
        for record, _fields in unauthorized:
            obs = by_id[record["record_id"]]
            obs["authenticity"] = APPLICATION_AUTHENTICITY
            obs["access_level"] = SINK_ACCESS
            obs["locally_held"] = True
            obs["binding"] = "bound"
            obs["observation_types"] = [EFFECT_TYPE]
            obs["literal_polarity"] = "refutes"
            obs["literal_claims"] = [claim_id]
            obs["named_origin"] = SINK_ACCESS
        return observations

    authorized = [
        (record, fields)
        for record, fields in held_sinks
        if fields.get("subject_class") == "authorized_effect"
    ]
    by_id = {obs["id"]: obs for obs in observations}
    # A positive observer count with missing commit details is not absence.
    if not _census_matches(coverage, held_sinks):
        return observations
    if coverage is not None and authorized:
        for record, _fields in authorized:
            obs = by_id[record["record_id"]]
            obs["authenticity"] = APPLICATION_AUTHENTICITY
            obs["access_level"] = SINK_ACCESS
            obs["locally_held"] = True
            obs["binding"] = "bound"
            obs["observation_types"] = [EFFECT_TYPE]
            obs["literal_polarity"] = "supports"
            obs["literal_claims"] = [claim_id]
            obs["named_origin"] = SINK_ACCESS
    elif coverage is not None:
        record, fields = coverage
        subjects = sorted({item[1].get("subject_class", "") for item in held_sinks})
        obs = by_id[record["record_id"]]
        obs["quote"] = (
            str(record.get("public_bytes") or "")
            + "observed_sink_subjects="
            + (",".join(subjects) if subjects else "none")
            + "\n"
        )
        obs["authenticity"] = APPLICATION_AUTHENTICITY
        obs["access_level"] = SINK_ACCESS
        obs["locally_held"] = True
        obs["binding"] = "bound"
        obs["observation_types"] = [EFFECT_TYPE]
        obs["literal_polarity"] = "supports"
        obs["literal_claims"] = [claim_id]
        obs["named_origin"] = SINK_ACCESS
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
