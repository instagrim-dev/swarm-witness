from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from swarm_witness.labels import CONCLUSION_LABELS

EXECUTION_STATUSES = frozenset(
    {
        "assigned",
        "attempted",
        "completed",
        "failed",
        "unrun",
        "missing",
    }
)

BASIS_VALUES = frozenset({"authored", "computed"})


@dataclass(frozen=True)
class Claim:
    id: str
    source_ref: str
    source_version: str
    original_proposition: str
    operational_interpretation: str
    property: str
    scope: str
    quantifier: str
    success_criterion: str
    assumptions: tuple[str, ...]


@dataclass(frozen=True)
class Run:
    id: str
    claim_id: str
    protocol_id: str
    case_id: str
    source_pin: str
    execution_status: str
    observations: dict[str, Any]


@dataclass(frozen=True)
class Finding:
    id: str
    claim_id: str
    run_ids: tuple[str, ...]
    proposition: str
    scope: str
    label: str
    basis: str
    supporting_observation_refs: tuple[str, ...]


def _require_nonblank_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"invalid or blank field: {key}")
    return value.strip()


def _require_nonblank_str_list(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if isinstance(value, str) or not isinstance(value, list):
        raise ValueError(f"{key} must be a non-empty list of nonblank strings")
    if not value:
        raise ValueError(f"{key} must be a non-empty list of nonblank strings")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or item.strip() == "":
            raise ValueError(f"{key} must be a non-empty list of nonblank strings")
        out.append(item.strip())
    return tuple(out)


def validate_claim(data: dict[str, Any]) -> Claim:
    return Claim(
        id=_require_nonblank_str(data, "id"),
        source_ref=_require_nonblank_str(data, "source_ref"),
        source_version=_require_nonblank_str(data, "source_version"),
        original_proposition=_require_nonblank_str(data, "original_proposition"),
        operational_interpretation=_require_nonblank_str(
            data, "operational_interpretation"
        ),
        property=_require_nonblank_str(data, "property"),
        scope=_require_nonblank_str(data, "scope"),
        quantifier=_require_nonblank_str(data, "quantifier"),
        success_criterion=_require_nonblank_str(data, "success_criterion"),
        assumptions=_require_nonblank_str_list(data, "assumptions"),
    )


def validate_run(data: dict[str, Any]) -> Run:
    execution_status = data.get("execution_status")
    if execution_status not in EXECUTION_STATUSES:
        raise ValueError(f"invalid or missing execution_status: {execution_status!r}")
    observations = data.get("observations")
    if observations is None:
        observations = {}
    if not isinstance(observations, dict):
        raise ValueError("observations must be a dict")
    return Run(
        id=_require_nonblank_str(data, "id"),
        claim_id=_require_nonblank_str(data, "claim_id"),
        protocol_id=_require_nonblank_str(data, "protocol_id"),
        case_id=_require_nonblank_str(data, "case_id"),
        source_pin=_require_nonblank_str(data, "source_pin"),
        execution_status=str(execution_status),
        observations=dict(observations),
    )


def validate_finding(data: dict[str, Any]) -> Finding:
    label = data.get("label")
    if label not in CONCLUSION_LABELS:
        raise ValueError(f"unknown conclusion label: {label!r}")
    basis = data.get("basis")
    if basis not in BASIS_VALUES:
        raise ValueError(f"invalid or missing basis: {basis!r}")
    return Finding(
        id=_require_nonblank_str(data, "id"),
        claim_id=_require_nonblank_str(data, "claim_id"),
        run_ids=_require_nonblank_str_list(data, "run_ids"),
        proposition=_require_nonblank_str(data, "proposition"),
        scope=_require_nonblank_str(data, "scope"),
        label=str(label),
        basis=str(basis),
        supporting_observation_refs=_require_nonblank_str_list(
            data, "supporting_observation_refs"
        ),
    )
