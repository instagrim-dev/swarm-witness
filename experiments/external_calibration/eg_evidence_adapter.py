"""Evidence-derived assessor for event-level EvidenceGraph packets.

Part of the evaluated method stack: receipt matching, temporal compatibility,
affirmative trust assumptions, and absence under covering capture are computed
here and scored as adapter capability. Does not read native verdicts, private
truth, or scenario names.

Assessments return structured predicate records for projection into classifier
verifying observations; decisions are unchanged by those fields.
"""

from __future__ import annotations

import hashlib
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
    values = [
        float(b.get("bound_seconds")) for b in bounds if b.get("bound_seconds") is not None
    ]
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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def receipt_of(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if not event:
        return None
    receipt = (event.get("attrs") or {}).get("receipt")
    return receipt if isinstance(receipt, dict) else None


def receipt_token(event: dict[str, Any] | None) -> str | None:
    receipt = receipt_of(event)
    if not receipt:
        return None
    tok = receipt.get("receipt_token") or receipt.get("token")
    return str(tok) if isinstance(tok, str) else None


def commitment_of(mutation: dict[str, Any] | None) -> str | None:
    if not mutation:
        return None
    value = (mutation.get("attrs") or {}).get("receipt_token_sha256")
    return str(value) if isinstance(value, str) else None


def receipt_matches_commitment(
    event: dict[str, Any] | None, mutation: dict[str, Any] | None
) -> str:
    """bound | mismatch | unbound | unavailable — mirrors EG RegistrySubstrate.binding."""
    commitment = commitment_of(mutation)
    if commitment is None:
        return "unavailable"
    token = receipt_token(event)
    if token is None:
        return "unbound"
    return "bound" if sha256_text(token) == commitment else "mismatch"


def intervals_compatible(
    *,
    mutation: dict[str, Any] | None,
    event: dict[str, Any] | None,
    clock_bound_seconds: float,
) -> bool:
    """True when event and mutation intervals are compatible within the clock bound."""
    if not mutation or not event:
        return False
    m0 = _parse_ts(mutation.get("time_lower"))
    m1 = _parse_ts(mutation.get("time_upper")) or m0
    e0 = _parse_ts(event.get("time_lower"))
    e1 = _parse_ts(event.get("time_upper"))
    if None in (m0, m1, e0, e1):
        return False
    pad = timedelta(seconds=float(clock_bound_seconds))
    if e0 > m1 + pad:
        return False
    if e1 < m0 - pad:
        return False
    return True


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


def _registry_mutations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for obs in observations:
        if "registry_mutation_population" in set(obs.get("observation_types") or []):
            rows = obs.get("registry_mutations")
            if isinstance(rows, list):
                return rows
    mutation = _entity(observations, "registry_mutation_record")
    return [mutation] if mutation else []


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


def claimed_mutation_absent(
    event: dict[str, Any] | None, registry_mutations: list[dict[str, Any]]
) -> tuple[bool, str]:
    """Whether the receipt's claimed registry key is absent from observed mutations."""
    receipt = receipt_of(event)
    if not receipt or receipt.get("accepted") is not True:
        return False, "no_accepted_receipt"
    claimed_id = receipt.get("event_id")
    claimed_name = receipt.get("name")
    claimed_ns = receipt.get("namespace")
    present_ids = set()
    present_keys = set()
    for mutation in registry_mutations:
        if not mutation:
            continue
        attrs = mutation.get("attrs") or {}
        key = mutation.get("natural_key") or attrs.get("id")
        if key:
            present_ids.add(str(key))
        if attrs.get("name") is not None:
            present_keys.add((attrs.get("namespace"), attrs.get("name")))
    if claimed_id and str(claimed_id) in present_ids:
        return False, "claimed_event_id_present_in_registry"
    if claimed_name is not None and (claimed_ns, claimed_name) in present_keys:
        return False, "claimed_name_present_in_registry"
    return True, "claimed_mutation_absent_from_registry"


def _attr_predicates(
    *,
    event: dict[str, Any] | None,
    mutation: dict[str, Any] | None,
    decl: dict[str, Any],
) -> dict[str, Any]:
    """Structured checks already performed; exclusivity_declared is premise only."""
    bound_seconds = _clock_bound_seconds(decl)
    exclusive = _exclusive(decl)
    independent = _independent(decl)
    binding = receipt_matches_commitment(event, mutation)
    temporal = (
        intervals_compatible(
            mutation=mutation, event=event, clock_bound_seconds=bound_seconds
        )
        if bound_seconds is not None
        else False
    )
    return {
        "clock_bound_present": bound_seconds is not None,
        "clock_bound_seconds": bound_seconds,
        "independence_declared": independent is not None,
        "independence_status": independent,
        "exclusivity_declared": exclusive,
        # Recorded premise only — not independently verified.
        "exclusivity_independently_verified": False,
        "receipt_binding": binding,
        "temporal_compatible": temporal,
        "event_has_event_uuid": bool(
            event and (event.get("attrs") or {}).get("event_uuid") is not None
        ),
        "mutation_present": mutation is not None,
        "event_present": event is not None,
    }


def assess_attribution(claim: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Return supported | refuted | unresolved with structured predicates."""
    del claim
    decl = _decl(observations)
    mutation = _entity(observations, "registry_mutation_record")
    event = _entity(observations, "tool_event_record")
    predicates = _attr_predicates(event=event, mutation=mutation, decl=decl)

    def _result(verdict: str, reason: str, capability: str, **extra: Any) -> dict[str, Any]:
        out = {
            "verdict": verdict,
            "reason": reason,
            "capability": capability,
            "predicates": predicates,
            "family": "event_attribution",
        }
        out.update(extra)
        return out

    if event is not None and (event.get("attrs") or {}).get("event_uuid") is None:
        return _result(
            "unresolved", "proposed_entity_is_not_a_tool_event", "event_identity"
        )

    if not predicates["clock_bound_present"]:
        return _result("unresolved", "no_clock_bound", "clock_reconciliation")

    if predicates["independence_status"] is None:
        return _result("unresolved", "independence_undeclared", "witness_independence")
    if predicates["independence_status"] is False:
        return _result("unresolved", "dependent_witnesses", "witness_independence")

    if predicates["exclusivity_declared"] is None:
        return _result("unresolved", "exclusivity_undeclared", "token_exclusivity")
    if predicates["exclusivity_declared"] is False:
        return _result("unresolved", "exclusivity_not_established", "token_exclusivity")

    binding = predicates["receipt_binding"]
    if binding == "unbound":
        return _result(
            "unresolved", "missing_receipt_token_or_commitment", "receipt_binding"
        )
    if binding == "unavailable":
        return _result("unresolved", "commitment_unavailable", "receipt_binding")
    if binding == "mismatch":
        return _result(
            "unresolved", "receipt_token_commitment_mismatch", "receipt_binding"
        )

    if not predicates["temporal_compatible"]:
        return _result("unresolved", "temporal_incompatible", "clock_reconciliation")

    if event is None or mutation is None:
        return _result("unresolved", "no_unique_proposed_event", "receipt_binding")

    return _result(
        "supported",
        "exclusive_independent_bound_temporally_compatible",
        "receipt_binding",
        binding=binding,
    )


def assess_fabricated_execution(
    claim: dict[str, Any], observations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Refute successful-execution only when capture covers and claimed mutation is absent."""
    del claim
    decl = _decl(observations)
    event = _entity(observations, "tool_event_record", "successful_execution_claim")
    pops = _populations(observations)
    mutations = _registry_mutations(observations)
    independent = _independent(decl)
    covers, cover_reason = capture_covers_execution(
        populations=pops,
        event=event,
        clock_bound_seconds=_clock_bound_seconds(decl),
    )
    absent, absent_reason = claimed_mutation_absent(event, mutations)
    predicates = {
        "independence_declared": independent is not None,
        "independence_status": independent,
        "capture_covers_execution": covers,
        "coverage_detail": cover_reason,
        "claimed_mutation_absent": absent,
        "absence_detail": absent_reason,
        "clock_bound_present": _clock_bound_seconds(decl) is not None,
    }

    def _result(verdict: str, reason: str, capability: str, **extra: Any) -> dict[str, Any]:
        out = {
            "verdict": verdict,
            "reason": reason,
            "capability": capability,
            "predicates": predicates,
            "family": "fabricated_execution",
            "coverage_detail": cover_reason,
            "absence_detail": absent_reason,
        }
        out.update(extra)
        return out

    if independent is False:
        return _result(
            "unresolved",
            "dependent_witnesses_block_absence_contradiction",
            "witness_independence",
        )
    if independent is None:
        return _result("unresolved", "independence_undeclared", "witness_independence")

    if not covers:
        return _result("unresolved", cover_reason, "capture_coverage")

    if not absent:
        return _result("unresolved", absent_reason, "absence_check")

    return _result(
        "refuted",
        "absence_under_complete_covering_capture",
        "capture_coverage",
    )
