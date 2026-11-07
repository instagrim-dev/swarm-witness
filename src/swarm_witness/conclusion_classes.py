"""Three-way conclusion taxonomy for Swarm Witness audits.

A security mechanism can appear to "work" while the warranted Finding still
depends on whether evidence is adequate and whether enforcement held:

1. ``missing_evidence`` — required discriminating observations absent or
   incomplete; do not treat agreement-on-ignorance as support. Maps to Finding
   label ``unresolved``.
2. ``failed_enforcement`` — evidence sufficient to evaluate the property, and
   the exercised mechanism violates it. Maps to ``contradicted_in_scope``.
3. ``supported`` — evidence sufficient and the property holds under the stated
   scope. Maps to ``reproduced`` (or ``classical_baseline_matches`` for matched
   baseline comparisons).

These classes are mutually exclusive for a single claim evaluation. Negative
controls must show that irrelevant facts do not upgrade ``missing_evidence``,
and that ``failed_enforcement`` is not labeled ``supported``.
"""

from __future__ import annotations

from typing import Any, Literal

ConclusionClass = Literal["missing_evidence", "failed_enforcement", "supported"]

CONCLUSION_TO_FINDING_LABEL: dict[ConclusionClass, str] = {
    "missing_evidence": "unresolved",
    "failed_enforcement": "contradicted_in_scope",
    "supported": "reproduced",
}


def classify_conclusion(
    *,
    evidence_complete: bool,
    property_holds: bool | None,
) -> dict[str, Any]:
    """Map evidence completeness + property outcome onto a conclusion class.

    ``property_holds`` must be ``None`` when evidence is incomplete; callers
    must not invent a pass/fail from missing observations.
    """
    if not evidence_complete:
        return {
            "conclusion_class": "missing_evidence",
            "finding_label": CONCLUSION_TO_FINDING_LABEL["missing_evidence"],
            "property_holds": None,
            "reason": "required discriminating evidence missing or incomplete",
        }
    if property_holds is None:
        raise ValueError(
            "property_holds must be True or False when evidence_complete is True"
        )
    if property_holds:
        return {
            "conclusion_class": "supported",
            "finding_label": CONCLUSION_TO_FINDING_LABEL["supported"],
            "property_holds": True,
            "reason": "evidence complete and property holds in scope",
        }
    return {
        "conclusion_class": "failed_enforcement",
        "finding_label": CONCLUSION_TO_FINDING_LABEL["failed_enforcement"],
        "property_holds": False,
        "reason": "evidence complete but exercised enforcement violates the property",
    }


def required_permission_decision(observed_grant: str) -> str:
    """Classical null: active → allow; revoked → deny."""
    if observed_grant == "active":
        return "allow"
    if observed_grant == "revoked":
        return "deny"
    raise ValueError(f"unknown observed_grant: {observed_grant!r}")
