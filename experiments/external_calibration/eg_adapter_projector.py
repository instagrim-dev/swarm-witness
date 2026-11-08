"""Project adapter assessments into verifying observations for frozen classifiers.

Does not re-implement attribution. Does not read warrants, private labels, or
native-method verdicts. Serializes structured adapter predicates only.

A decisive record is emitted only after the required premises are admitted and
their entity identifiers are bound to the claim. The record keeps every
required premise's qualification and does not inherit authenticity from an
unrelated observation.
"""

from __future__ import annotations

import json
from typing import Any

from eg_evidence_adapter import (
    ADMISSIBLE_PREMISE_AUTHENTICITY,
    admit_required_premises,
    assess_attribution,
    assess_fabricated_execution,
    required_observation_types,
)

# Fixed evidence bundles (not claim-copied requirements).
ATTRIBUTION_EVIDENCE_TYPES = [
    "registry_mutation_record",
    "tool_event_record",
]
EXECUTION_EVIDENCE_TYPES = [
    "successful_execution_claim",
    "capture_declaration",
    "registry_mutation_population",
]


def _family(claim: dict[str, Any], assessment: dict[str, Any]) -> str:
    return str(
        assessment.get("family")
        or claim.get("family")
        or "event_attribution"
    )


def _evidence_types(family: str) -> list[str]:
    if family == "fabricated_execution":
        return list(EXECUTION_EVIDENCE_TYPES)
    return list(ATTRIBUTION_EVIDENCE_TYPES)


def _supporting_ids(observations: list[dict[str, Any]]) -> list[str]:
    return [obs["id"] for obs in observations if isinstance(obs.get("id"), str)]


def _independence_group(observations: list[dict[str, Any]]) -> str:
    """Prefer the shared group used by EG event packets."""
    for obs in observations:
        group = obs.get("independence_group")
        if isinstance(group, str):
            return group
    return "eg-adapter-derivation"


def _shared_field(premises: list[dict[str, Any]], field: str) -> str | None:
    """Return the field only when every required premise carries that same value."""
    if not premises:
        return None
    values = [obs.get(field) for obs in premises]
    first = values[0]
    if isinstance(first, str) and all(value == first for value in values):
        return first
    return None


def _covers_required(claim: dict[str, Any], premises: list[dict[str, Any]]) -> bool:
    covered: set[str] = set()
    for obs in premises:
        covered.update(obs.get("observation_types") or [])
    return set(required_observation_types(claim)).issubset(covered)


def assess_for_claim(
    claim: dict[str, Any], observations: list[dict[str, Any]]
) -> dict[str, Any]:
    family = claim.get("family") or "event_attribution"
    if family == "fabricated_execution":
        return assess_fabricated_execution(claim, observations)
    return assess_attribution(claim, observations)


def project_checks(
    claim: dict[str, Any],
    raw_observations: list[dict[str, Any]],
    assessment: dict[str, Any],
) -> list[dict[str, Any]]:
    """Emit zero or one decisive verifying observation from the adapter assessment.

    Unresolved → no decisive polarity observation (classifiers abstain).
    """
    verdict = assessment.get("verdict")
    if verdict not in {"supported", "refuted"}:
        return []

    admission = admit_required_premises(claim, raw_observations)
    if not admission["admitted"]:
        return []
    premises = admission["premises"]
    if not _covers_required(claim, premises):
        return []
    # Shared qualification only. Never default to authentic_public_text, and
    # never take authenticity from the first observation in the bundle.
    authenticity = _shared_field(premises, "authenticity")
    access_level = _shared_field(premises, "access_level")
    if authenticity not in ADMISSIBLE_PREMISE_AUTHENTICITY or access_level is None:
        return []

    claim_id = claim["id"]
    family = _family(claim, assessment)
    predicates = assessment.get("predicates") or {}
    polarity = "supports" if verdict == "supported" else "refutes"
    quote = (
        f"adapter_derivation verdict={verdict}; reason={assessment.get('reason')}; "
        f"capability={assessment.get('capability')}; "
        f"predicates={json.dumps(predicates, sort_keys=True, default=str)}"
    )
    # Reuse the same shape as r2_event_packets._obs (id, applies_to, independence_group).
    record = {
        "id": f"{claim_id}-adapter-derivation",
        "source_id": "eg-evidence-derived-adapter",
        "stage": "A",
        "publication_ordinal": 1,
        "independence_group": (
            _shared_field(premises, "independence_group")
            or _independence_group(raw_observations)
        ),
        "authenticity": authenticity,
        "access_level": access_level,
        "anchor": "composed method: adapter predicate projection (not an independent witness)",
        "quote": quote,
        "applies_to": [claim_id],
        "observation_types": _evidence_types(family),
        "time_basis": "source_stated",
        "event_time": "adapter-derivation",
        "literal_polarity": polarity,
        "literal_claims": [claim_id],
        "derivation": "adapter_checks",
        "supporting_observation_ids": _supporting_ids(premises),
        "premise_qualifications": list(admission["qualifications"]),
        "adapter_assessment": {
            "verdict": verdict,
            "reason": assessment.get("reason"),
            "capability": assessment.get("capability"),
            "predicates": predicates,
        },
        "composed_method_trusts_derivation": True,
    }
    return [record]


def composed_observations(
    claim: dict[str, Any], raw_observations: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """assessment, projected list — projector sees only claim + raw + assessment."""
    assessment = assess_for_claim(claim, raw_observations)
    projected = project_checks(claim, raw_observations, assessment)
    return assessment, projected
