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

# Matched baseline comparisons use a dedicated success label when supported.
SUPPORTED_COMPARISON_LABEL = "classical_baseline_matches"


def finding_label_for(
    conclusion_class: ConclusionClass, *, comparison: bool = False
) -> str:
    if conclusion_class == "supported" and comparison:
        return SUPPORTED_COMPARISON_LABEL
    return CONCLUSION_TO_FINDING_LABEL[conclusion_class]


def classify_conclusion(
    *,
    evidence_complete: bool,
    property_holds: bool | None,
    comparison: bool = False,
) -> dict[str, Any]:
    """Map evidence completeness + property outcome onto a conclusion class.

    ``property_holds`` must be ``None`` when evidence is incomplete; callers
    must not invent a pass/fail from missing observations.
    """
    if not evidence_complete:
        return {
            "conclusion_class": "missing_evidence",
            "finding_label": finding_label_for("missing_evidence", comparison=comparison),
            "property_holds": None,
            "reason": "required discriminating evidence missing or incomplete",
        }
    if property_holds is None:
        raise ValueError(
            "property_holds must be True or False when evidence_complete is True"
        )
    if property_holds:
        cls: ConclusionClass = "supported"
        return {
            "conclusion_class": cls,
            "finding_label": finding_label_for(cls, comparison=comparison),
            "property_holds": True,
            "reason": "evidence complete and property holds in scope",
        }
    cls = "failed_enforcement"
    return {
        "conclusion_class": cls,
        "finding_label": finding_label_for(cls, comparison=comparison),
        "property_holds": False,
        "reason": "evidence complete but exercised enforcement violates the property",
    }


def classify_matched_comparison(
    *,
    evidence_complete: bool,
    arms_agree: bool | None,
    property_holds: bool | None,
) -> dict[str, Any]:
    """Three-way class for paired classical↔implementation comparisons.

    Incomplete pairs → missing_evidence. Complete evidence with disagreement or
    failed properties → failed_enforcement. Agreement + property success →
    supported (Finding ``classical_baseline_matches``).
    """
    if not evidence_complete or arms_agree is None:
        return classify_conclusion(
            evidence_complete=False, property_holds=None, comparison=True
        )
    if not arms_agree:
        return classify_conclusion(
            evidence_complete=True, property_holds=False, comparison=True
        )
    if property_holds is None:
        raise ValueError("property_holds required when arms agree under complete evidence")
    return classify_conclusion(
        evidence_complete=True, property_holds=property_holds, comparison=True
    )


def required_permission_decision(observed_grant: str) -> str:
    """Classical null: active → allow; revoked → deny."""
    if observed_grant == "active":
        return "allow"
    if observed_grant == "revoked":
        return "deny"
    raise ValueError(f"unknown observed_grant: {observed_grant!r}")


def conclusion_class_for_label(label: str) -> ConclusionClass | None:
    """Best-effort reverse map from Finding.label to conclusion class."""
    if label == "unresolved" or label == "assumption_dependent":
        return "missing_evidence"
    if label == "contradicted_in_scope":
        return "failed_enforcement"
    if label in {"reproduced", "classical_baseline_matches"}:
        return "supported"
    return None


def assert_label_matches_conclusion(label: str, conclusion_class: str) -> None:
    expected = finding_label_for(
        conclusion_class,  # type: ignore[arg-type]
        comparison=(label == SUPPORTED_COMPARISON_LABEL),
    )
    # supported may be reproduced or classical_baseline_matches
    if conclusion_class == "supported":
        if label not in {"reproduced", SUPPORTED_COMPARISON_LABEL}:
            raise ValueError(
                f"supported conclusion incompatible with Finding label {label!r}"
            )
        return
    if label != expected:
        raise ValueError(
            f"conclusion_class {conclusion_class!r} expects label {expected!r}, got {label!r}"
        )
