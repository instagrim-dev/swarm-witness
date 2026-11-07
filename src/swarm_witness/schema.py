from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from swarm_witness.labels import CONCLUSION_LABELS


@dataclass(frozen=True)
class ClaimCard:
    id: str
    property: str
    scope: str
    quantifier: str
    success_criterion: str
    assumptions: tuple[str, ...]
    baseline: str
    discriminating_checks: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResultRecord:
    claim_id: str
    label: str
    metrics: dict[str, Any]
    evidence_path: str
    notes: str


def validate_claim_card(data: dict[str, Any]) -> ClaimCard:
    required = (
        "id",
        "property",
        "scope",
        "quantifier",
        "success_criterion",
        "assumptions",
        "baseline",
    )
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise ValueError(f"claim card missing required fields: {', '.join(missing)}")
    return ClaimCard(
        id=str(data["id"]),
        property=str(data["property"]),
        scope=str(data["scope"]),
        quantifier=str(data["quantifier"]),
        success_criterion=str(data["success_criterion"]),
        assumptions=tuple(data["assumptions"]),
        baseline=str(data["baseline"]),
        discriminating_checks=tuple(data.get("discriminating_checks") or ()),
    )


def validate_result_record(data: dict[str, Any]) -> ResultRecord:
    label = data.get("label")
    if label not in CONCLUSION_LABELS:
        raise ValueError(f"unknown conclusion label: {label!r}")
    if not data.get("claim_id") or not data.get("evidence_path"):
        raise ValueError("result requires claim_id and evidence_path")
    return ResultRecord(
        claim_id=str(data["claim_id"]),
        label=str(label),
        metrics=dict(data.get("metrics") or {}),
        evidence_path=str(data["evidence_path"]),
        notes=str(data.get("notes") or ""),
    )
