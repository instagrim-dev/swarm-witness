"""Separable diagnostic dimensions for Swarm Witness audits.

The high-level three-way conclusion class is a *projection*. Causal attribution
requires independent axes so equality failure, bad evidence, wrong decisions,
and unauthorized effects are not collapsed into a single label.
"""

from __future__ import annotations

from typing import Any, Literal

EvidenceStatus = Literal["missing", "unverified", "authentic", "misbound"]
DecisionStatus = Literal["correct", "incorrect", "unknown"]
EffectStatus = Literal["committed", "prevented", "unobserved", "not_applicable"]
FailureOrigin = Literal[
    "none",
    "evidence",
    "decision_policy",
    "effect_boundary",
    "comparison_equality",
    "undetermined",
]

EVALUATION_METHODS = frozenset(
    {
        "pinned_reexecution",
        "published_harness_confirmation",
        "matched_decision_model",
        "native_matched_baseline",
        "synthetic_protocol_conformance",
        "held_out_artifact_audit",
        "public_postmortem_qualification",
    }
)


def diagnosis(
    *,
    evidence_status: EvidenceStatus,
    decision_status: DecisionStatus,
    effect_status: EffectStatus,
    failure_origin: FailureOrigin,
) -> dict[str, Any]:
    return {
        "evidence_status": evidence_status,
        "decision_status": decision_status,
        "effect_status": effect_status,
        "failure_origin": failure_origin,
    }


def attach_evaluation_method(finding: dict[str, Any], method: str) -> dict[str, Any]:
    if method not in EVALUATION_METHODS:
        raise ValueError(f"unknown evaluation_method: {method!r}")
    finding = dict(finding)
    finding["evaluation_method"] = method
    return finding
