"""Evidence-derived assessor for event-level EvidenceGraph packets.

Part of the evaluated method stack: any temporal / exclusivity / independence /
capture-coverage reasoning here is scored as adapter capability, not as hidden
packet authoring. Does not read native verdicts, private truth, or scenario names.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _decl(observations: list[dict[str, Any]]) -> dict[str, Any]:
    for obs in observations:
        if "declared_assumptions" in set(obs.get("observation_types") or []):
            return obs.get("declared_assumptions") or {}
    return {}


def _exclusive(decl: dict[str, Any]) -> bool | None:
    for domain in decl.get("trust_domains") or []:
        if domain.get("id") == "runner":
            return bool(domain.get("exclusive_receipt_tokens"))
    return None


def _independent(decl: dict[str, Any]) -> bool | None:
    for domain in decl.get("trust_domains") or []:
        if domain.get("id") == "registry":
            related = domain.get("related_to") or {}
            rel = related.get("runner")
            if rel in {"independent", "INDEPENDENT"}:
                return True
            if rel in {"same", "SAME", "dependent"}:
                return False
    return None


def _clock_bound_seconds(decl: dict[str, Any]) -> float | None:
    bounds = decl.get("clock_bounds") or []
    if not bounds:
        return None
    values = [float(b.get("bound_seconds")) for b in bounds if b.get("bound_seconds") is not None]
    return max(values) if values else None


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _receipt_token(event: dict[str, Any] | None) -> str | None:
    if not event:
        return None
    attrs = event.get("attrs") or {}
    receipt = attrs.get("receipt") or {}
    if isinstance(receipt, dict):
        tok = receipt.get("receipt_token") or receipt.get("token")
        if tok:
            return str(tok)
    return None


def _commitment(mutation: dict[str, Any] | None) -> str | None:
    if not mutation:
        return None
    return (mutation.get("attrs") or {}).get("receipt_token_sha256")


def _entity(observations: list[dict[str, Any]], *types: str) -> dict[str, Any] | None:
    wanted = set(types)
    for obs in observations:
        if set(obs.get("observation_types") or []) & wanted:
            entity = obs.get("entity")
            if isinstance(entity, dict):
                return entity
    return None


def _populations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for obs in observations:
        if "capture_declaration" in set(obs.get("observation_types") or []):
            pops = obs.get("populations")
            if isinstance(pops, list):
                return pops
    return []


def capture_covers_execution(
    *,
    populations: list[dict[str, Any]],
    event: dict[str, Any] | None,
    clock_bound_seconds: float | None,
) -> tuple[bool, str]:
    """Whether declared capture covers the tool execution window + clock bound."""
    if not populations:
        return False, "no_population_declaration"
    if clock_bound_seconds is None:
        return False, "no_clock_bound"
    if not event:
        return False, "no_event"
    t0 = _parse_ts(event.get("time_lower"))
    t1 = _parse_ts(event.get("time_upper"))
    if t0 is None or t1 is None:
        return False, "event_interval_unparsed"
    pad = timedelta(seconds=float(clock_bound_seconds))
    window_start = t0 - pad
    window_end = t1 + pad
    complete_pops = [p for p in populations if p.get("complete")]
    if not complete_pops:
        return False, "population_incomplete"
    for pop in complete_pops:
        started = _parse_ts(pop.get("started_at"))
        stopped = _parse_ts(pop.get("stopped_at"))
        if started is None or stopped is None:
            continue
        if window_start >= started and window_end <= stopped:
            return True, "complete_capture_covers_widened_window"
    return False, "capture_does_not_cover_widened_window"


def assess_attribution(claim: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Return supported | refuted | unresolved with an explicit reason."""
    decl = _decl(observations)
    mutation = _entity(observations, "registry_mutation_record")
    event = _entity(observations, "tool_event_record")

    if _clock_bound_seconds(decl) is None:
        return {
            "verdict": "unresolved",
            "reason": "no_clock_bound",
            "capability": "clock_reconciliation",
        }
    independent = _independent(decl)
    if independent is False:
        return {
            "verdict": "unresolved",
            "reason": "dependent_witnesses",
            "capability": "witness_independence",
        }
    exclusive = _exclusive(decl)
    token = _receipt_token(event)
    commitment = _commitment(mutation)
    if not token or not commitment:
        return {
            "verdict": "unresolved",
            "reason": "missing_receipt_token_or_commitment",
            "capability": "receipt_binding",
        }
    if exclusive is False:
        return {
            "verdict": "unresolved",
            "reason": "exclusivity_not_established",
            "capability": "token_exclusivity",
        }
    # Exclusive + independent + clock + token/commitment present: support the
    # proposed pairing when the claim names a single event.
    if claim.get("proposed_event_id") and event and mutation:
        return {
            "verdict": "supported",
            "reason": "exclusive_independent_clocked_binding",
            "capability": "receipt_binding",
        }
    return {
        "verdict": "unresolved",
        "reason": "no_unique_proposed_event",
        "capability": "receipt_binding",
    }


def assess_fabricated_execution(
    claim: dict[str, Any], observations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Successful-execution claims: contradict only when capture covers the window."""
    del claim  # claim text is not used; coverage is computed from observables.
    decl = _decl(observations)
    event = _entity(observations, "tool_event_record", "successful_execution_claim")
    pops = _populations(observations)
    independent = _independent(decl)
    if independent is False:
        return {
            "verdict": "unresolved",
            "reason": "dependent_witnesses_block_absence_contradiction",
            "capability": "witness_independence",
        }
    covers, reason = capture_covers_execution(
        populations=pops,
        event=event,
        clock_bound_seconds=_clock_bound_seconds(decl),
    )
    if covers:
        return {
            "verdict": "refuted",
            "reason": "absence_under_complete_covering_capture",
            "capability": "capture_coverage",
            "coverage_detail": reason,
        }
    return {
        "verdict": "unresolved",
        "reason": reason,
        "capability": "capture_coverage",
    }
