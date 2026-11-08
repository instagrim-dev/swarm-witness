"""Project adapter assessments into verifying observations for frozen classifiers.

Does not re-implement attribution. Does not read warrants, private labels, or
native-method verdicts. Serializes structured adapter predicates only.
"""

from __future__ import annotations

import json
from typing import Any

from eg_evidence_adapter import assess_attribution, assess_fabricated_execution

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


def _supporting_meta(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Carry authenticity/access basis and ids from supporting raw records."""
    ids: list[str] = []
    groups: list[str] = []
    authenticities: list[str] = []
    access_levels: list[str] = []
    for obs in observations:
        oid = obs.get("id")
        if isinstance(oid, str):
            ids.append(oid)
        group = obs.get("independence_group")
        if isinstance(group, str):
            groups.append(group)
        auth = obs.get("authenticity")
        if isinstance(auth, str):
            authenticities.append(auth)
        access = obs.get("access_level")
        if isinstance(access, str):
            access_levels.append(access)
    # Prefer the shared group used by EG event packets.
    independence_group = groups[0] if groups else "eg-adapter-derivation"
    # Keep admissible authenticity for frozen admission (not derived_same_origin).
    authenticity = (
        "authentic_public_text"
        if all(a == "authentic_public_text" for a in authenticities) or not authenticities
        else authenticities[0]
    )
    access_level = (
        "raw_telemetry_public"
        if all(a == "raw_telemetry_public" for a in access_levels) or not access_levels
        else access_levels[0]
    )
    return {
        "supporting_observation_ids": ids,
        "independence_group": independence_group,
        "authenticity": authenticity,
        "access_level": access_level,
    }


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

    claim_id = claim["id"]
    family = _family(claim, assessment)
    meta = _supporting_meta(raw_observations)
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
        "independence_group": meta["independence_group"],
        "authenticity": meta["authenticity"],
        "access_level": meta["access_level"],
        "anchor": "composed method: adapter predicate projection (not an independent witness)",
        "quote": quote,
        "applies_to": [claim_id],
        "observation_types": _evidence_types(family),
        "time_basis": "source_stated",
        "event_time": "adapter-derivation",
        "literal_polarity": polarity,
        "literal_claims": [claim_id],
        "derivation": "adapter_checks",
        "supporting_observation_ids": meta["supporting_observation_ids"],
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
