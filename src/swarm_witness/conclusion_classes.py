"""Conclusion taxonomy for Swarm Witness audits.

Core three-way classes for a single mechanism evaluation:

1. ``missing_evidence`` — discriminating observations absent/incomplete.
   Finding ``unresolved``.
2. ``failed_enforcement`` — evidence sufficient *and authentic*, and the
   exercised mechanism violates the property. Finding ``contradicted_in_scope``.
3. ``supported`` — evidence sufficient/authentic and the property holds.
   Finding ``reproduced`` (or ``classical_baseline_matches`` for matched
   baseline comparisons).

Matched classical↔implementation comparisons additionally emit
``comparison_divergent`` when paired observations disagree. That refutes the
*equality* proposition without diagnosing that either gate failed enforcement.
It still maps to Finding ``contradicted_in_scope`` (equality contradicted).
"""

from __future__ import annotations

from typing import Any, Literal

ConclusionClass = Literal[
    "missing_evidence",
    "failed_enforcement",
    "supported",
    "comparison_divergent",
]

CONCLUSION_TO_FINDING_LABEL: dict[ConclusionClass, str] = {
    "missing_evidence": "unresolved",
    "failed_enforcement": "contradicted_in_scope",
    "supported": "reproduced",
    "comparison_divergent": "contradicted_in_scope",
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
    """Classify paired classical↔implementation comparisons.

    Outcomes are independent:
    - incomplete / unpaired → ``missing_evidence``
    - arms disagree → ``comparison_divergent`` (equality refuted; *not*
      ``failed_enforcement`` — either arm may still satisfy its own property)
    - arms agree + property fail → ``failed_enforcement``
    - arms agree + property success → ``supported`` / ``classical_baseline_matches``
    """
    if not evidence_complete or arms_agree is None:
        return classify_conclusion(
            evidence_complete=False, property_holds=None, comparison=True
        )
    if not arms_agree:
        return {
            "conclusion_class": "comparison_divergent",
            "finding_label": finding_label_for(
                "comparison_divergent", comparison=True
            ),
            "property_holds": property_holds,
            "arms_agree": False,
            "reason": (
                "cross-arm equality proposition refuted; not a diagnosis that "
                "either authorization mechanism failed enforcement"
            ),
        }
    if property_holds is None:
        raise ValueError("property_holds required when arms agree under complete evidence")
    out = classify_conclusion(
        evidence_complete=True, property_holds=property_holds, comparison=True
    )
    out["arms_agree"] = True
    return out


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
        # Ambiguous between failed_enforcement and comparison_divergent;
        # callers with richer context should prefer the explicit field.
        return "failed_enforcement"
    if label in {"reproduced", "classical_baseline_matches"}:
        return "supported"
    return None


def assert_label_matches_conclusion(label: str, conclusion_class: str) -> None:
    expected = finding_label_for(
        conclusion_class,  # type: ignore[arg-type]
        comparison=(label == SUPPORTED_COMPARISON_LABEL),
    )
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
