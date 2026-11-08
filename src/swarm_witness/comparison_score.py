"""Paired scores for the frozen public and reproduction comparison.

Verdict functions do not call this module. Rates with a zero denominator are
null, and the raw counts are kept. Beating the naive PASS baseline is recorded
and is not a superiority claim.
"""

from __future__ import annotations

from typing import Any

UNDETERMINED = "undetermined"
DECISIVE = frozenset({"supported", "refuted"})


def rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def naive_origin(claim: dict[str, Any], observations: list[dict[str, Any]]) -> str:
    """Credulous origin: the first named origin in the packet, else the report."""
    for obs in observations:
        if claim["id"] not in obs.get("applies_to", []):
            continue
        origin = obs.get("named_origin")
        if isinstance(origin, str) and origin.strip():
            return origin.strip()
    if claim.get("family") == "attribution":
        return "report_named_actor"
    return UNDETERMINED


def always_unresolved_origin() -> str:
    return UNDETERMINED


def _method_rows(rows: list[dict[str, Any]], method: str) -> list[dict[str, Any]]:
    return [row for row in rows if row["method"] == method]


def summarize_method(rows: list[dict[str, Any]], *, truth_known: bool) -> dict[str, Any]:
    """One method, one layer. `rows` are already filtered to that method."""
    cell_count = len(rows)
    unsupported_support = 0
    unsupported_refutation = 0
    correct_abstention = 0
    correct_decisive = 0
    decisive_opportunities = 0
    false_proposition_support = 0
    false_proposition_refutation = 0
    unsupported_attribution = 0
    unique_origin_cases = 0
    correct_concrete_origin = 0
    attribution_abstentions = 0
    concrete_assignments = 0
    for row in rows:
        predicted = row["predicted"]
        warrant = row["adjudicated"]
        if predicted == "supported" and warrant != "supported":
            unsupported_support += 1
        if predicted == "refuted" and warrant != "refuted":
            unsupported_refutation += 1
        if predicted == "unresolved" and warrant == "unresolved":
            correct_abstention += 1
        if warrant in DECISIVE:
            decisive_opportunities += 1
            if predicted == warrant:
                correct_decisive += 1
        if truth_known:
            holds = row["proposition_holds"]
            if predicted == "supported" and holds is False:
                false_proposition_support += 1
            if predicted == "refuted" and holds is True:
                false_proposition_refutation += 1
        origin = row["attributed_origin"]
        warranted_origin = row["warranted_origin"]
        if origin != UNDETERMINED:
            concrete_assignments += 1
            if origin != warranted_origin:
                unsupported_attribution += 1
        else:
            attribution_abstentions += 1
        if warranted_origin != UNDETERMINED:
            unique_origin_cases += 1
            if origin == warranted_origin:
                correct_concrete_origin += 1
    return {
        "cell_count": cell_count,
        "unsupported_support": unsupported_support,
        "unsupported_refutation": unsupported_refutation,
        "correct_abstention": correct_abstention,
        "correct_decisive": correct_decisive,
        "decisive_opportunities": decisive_opportunities,
        "correct_decisive_coverage": rate(correct_decisive, decisive_opportunities),
        "false_proposition_support": (
            false_proposition_support if truth_known else None
        ),
        "false_proposition_refutation": (
            false_proposition_refutation if truth_known else None
        ),
        "truth_known": truth_known,
        "unsupported_attribution": unsupported_attribution,
        "unique_origin_cases": unique_origin_cases,
        "correct_concrete_origin": correct_concrete_origin,
        "correct_attribution_coverage": rate(
            correct_concrete_origin, unique_origin_cases
        ),
        "attribution_abstentions": attribution_abstentions,
        "concrete_assignments": concrete_assignments,
        "accuracy_among_concrete_assignments": rate(
            correct_concrete_origin, concrete_assignments
        ),
        "record_requests": 0,
    }


def layer_summary(
    rows: list[dict[str, Any]], methods: list[str], *, truth_known: bool
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for method in methods:
        out[method] = summarize_method(_method_rows(rows, method), truth_known=truth_known)
    return out
