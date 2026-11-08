"""Differential conformance for the evidence binding.

The reference module is imported here and nowhere in the production verdict.
Mutations are applied to the production gates and compared with the unmutated
reference. The reference does not call ``production_verdict``.
"""

from __future__ import annotations

from typing import Any, Callable

from swarm_witness.evidence_binding import (
    audit_entrypoint,
    bind_family,
    production_verdict,
)
from swarm_witness.formal.evidence_reference import reference_verdict

import swarm_witness.evidence_binding as binding


def encode(result: dict[str, Any]) -> tuple[int, int, int]:
    prop = 0
    evidence = 0
    satisfying = set(result["satisfying_worlds"])
    compatible = set(result["compatible_worlds"])
    for index, world in enumerate(result["universe"]):
        if world in satisfying:
            prop |= 1 << index
        if world in compatible:
            evidence |= 1 << index
    return prop, evidence, len(result["universe"])


def reference_status(result: dict[str, Any]) -> str:
    prop, evidence, width = encode(result)
    return reference_verdict(
        prop, evidence, verified=bool(result["verified"]), width=width
    )


def _agree(result: dict[str, Any]) -> bool:
    if not result["universe"]:
        return result["epistemic_status"] == "unresolved"
    return result["epistemic_status"] == reference_status(result)


def _public(record_id: str, **overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": record_id,
        "kind": "public",
        "authenticity": "authentic_public_text",
        "family": "P_url",
        "channel": "remote_url",
        "polarity": "supports",
        "independence_group": record_id,
        "event_time": "2026-01-01T00:00:00Z",
        "time_basis": "source_stated",
        "locally_held": True,
        "access_level": "public_bytes",
    }
    record.update(overrides)
    return record


def _predicate_domain_checked(widths: list[int]) -> dict[str, Any]:
    compared = 0
    refinements = 0
    for width in widths:
        universe = [f"w{index}" for index in range(width)]
        full = (1 << width) - 1
        for prop in range(full + 1):
            property_worlds = frozenset(
                universe[index] for index in range(width) if prop & (1 << index)
            )
            for evidence in range(full + 1):
                compatible = frozenset(
                    universe[index] for index in range(width) if evidence & (1 << index)
                )
                for verified in (False, True):
                    produced = production_verdict(
                        property_worlds, compatible, verified=verified
                    )
                    referenced = reference_verdict(
                        prop, evidence, verified=verified, width=width
                    )
                    compared += 1
                    if produced != referenced:
                        return {
                            "passed": False,
                            "compared": compared,
                            "refinements": refinements,
                            "failure": [width, prop, evidence, verified, produced, referenced],
                        }
                    if not verified or not evidence or produced not in {"supported", "refuted"}:
                        continue
                    sub = evidence
                    while sub:
                        if sub != evidence:
                            refined_worlds = frozenset(
                                universe[index]
                                for index in range(width)
                                if sub & (1 << index)
                            )
                            refined_produced = production_verdict(
                                property_worlds, refined_worlds, verified=True
                            )
                            refined_referenced = reference_verdict(
                                prop, sub, verified=True, width=width
                            )
                            refinements += 1
                            if refined_produced != produced or refined_referenced != referenced:
                                return {
                                    "passed": False,
                                    "compared": compared,
                                    "refinements": refinements,
                                    "failure": ["refinement", width, prop, evidence, sub],
                                }
                        sub = (sub - 1) & evidence
    return {"passed": True, "compared": compared, "refinements": refinements, "failure": None}


def record_cases() -> dict[str, Any]:
    """Record-derived cases. Masks are not the input."""
    support = bind_family(
        [_public("support", coverage="complete")], family="P_url", claim={}
    )
    refute = bind_family(
        [
            _public(
                "refute",
                polarity="contradicts",
                coverage="complete",
                exercised_mechanism=False,
                family="P_eff",
            )
        ],
        family="P_eff",
        claim={"requires_event_time": True},
    )
    unresolved = bind_family([_public("partial")], family="P_url", claim={})
    invalid = bind_family(
        [_public("spoof", authenticity="spoofed_tool_line", coverage="complete")],
        family="P_url",
        claim={},
    )
    unchecked = bind_family(
        [_public("unchecked", authenticity="not_checked", coverage="complete")],
        family="P_url",
        claim={},
    )
    empty = bind_family(
        [
            _public("yes", coverage="complete", independence_group="yes", polarity="supports"),
            _public("no", coverage="complete", independence_group="no", polarity="contradicts"),
        ],
        family="P_url",
        claim={},
    )
    base = bind_family(
        [_public("held", coverage="complete", independence_group="held")],
        family="P_url",
        claim={},
    )
    irrelevant = bind_family(
        [
            _public("held", coverage="complete", independence_group="held"),
            _public(
                "other",
                family="P_identity",
                channel="credential",
                polarity="contradicts",
                coverage="complete",
                independence_group="other",
            ),
        ],
        family="P_url",
        claim={},
    )
    cases = {
        "support": support,
        "refute": refute,
        "unresolved": unresolved,
        "invalid_binding": invalid,
        "not_checked": unchecked,
        "empty_compatibility": empty,
        "irrelevant_addition": irrelevant,
    }
    failures = [name for name, result in cases.items() if not _agree(result)]
    irrelevant_ok = (
        base["epistemic_status"] == irrelevant["epistemic_status"] == "supported"
        and base["compatible_worlds"] == irrelevant["compatible_worlds"]
    )
    expected = {
        "support": "supported",
        "refute": "refuted",
        "unresolved": "unresolved",
        "invalid_binding": "unresolved",
        "not_checked": "unresolved",
        "empty_compatibility": "unresolved",
    }
    label_failures = [
        name
        for name, status in expected.items()
        if cases[name]["epistemic_status"] != status
    ]
    return {
        "passed": not failures and not label_failures and irrelevant_ok and empty["verified"] is True and empty["compatible_worlds"] == [],
        "agreement_failures": failures,
        "label_failures": label_failures,
        "irrelevant_preserved": irrelevant_ok,
        "invalid_evidence_status": invalid["evidence_status"],
        "not_checked_evidence_status": unchecked["evidence_status"],
        "empty_verified": empty["verified"],
    }


def _patched(name: str, fn: Callable[..., Any], body: Callable[[], Any]) -> Any:
    old = getattr(binding, name)
    setattr(binding, name, fn)
    try:
        return body()
    finally:
        setattr(binding, name, old)


def mutation_checks() -> dict[str, bool]:
    """Each production-gate mutation disagrees with the unmutated reference."""
    unchecked = _public("unchecked", authenticity="not_checked", coverage="complete")
    honest_verification = bind_family([unchecked], family="P_url", claim={})
    mutated_verification = _patched(
        "verification_admits",
        lambda status: True,
        lambda: bind_family([unchecked], family="P_url", claim={}),
    )
    verification_caught = (
        honest_verification["epistemic_status"] == "unresolved"
        and reference_status(honest_verification) == "unresolved"
        and mutated_verification["epistemic_status"] != "unresolved"
    )

    conflict = [
        _public("yes", coverage="complete", independence_group="yes"),
        _public("no", coverage="complete", independence_group="no", polarity="contradicts"),
    ]
    honest_empty = bind_family(conflict, family="P_url", claim={})
    mutated_empty = _patched(
        "empty_set_unresolved",
        lambda compatible: False,
        lambda: bind_family(conflict, family="P_url", claim={}),
    )
    empty_caught = (
        honest_empty["verified"] is True
        and honest_empty["compatible_worlds"] == []
        and honest_empty["epistemic_status"] == "unresolved"
        and reference_status(honest_empty) == "unresolved"
        and mutated_empty["epistemic_status"] == "supported"
    )

    held = _public("held", coverage="complete")
    honest_kind = bind_family([held], family="P_url", claim={})
    mutated_kind = _patched(
        "property_worlds_for",
        lambda family: frozenset({"not-a-declared-world"}),
        lambda: bind_family([held], family="P_url", claim={}),
    )
    kind_caught = (
        honest_kind["epistemic_status"] == "supported"
        and reference_status(honest_kind) == "supported"
        and mutated_kind["epistemic_status"] != honest_kind["epistemic_status"]
    )

    untimed = _public(
        "late",
        family="P_eff",
        polarity="contradicts",
        exercised_mechanism=False,
        event_time=None,
        time_basis="missing",
    )
    claim = {"requires_event_time": True}
    honest_time = bind_family([untimed], family="P_eff", claim=claim)
    mutated_time = _patched(
        "temporal_record_binds",
        lambda record, claim: True,
        lambda: bind_family([untimed], family="P_eff", claim=claim),
    )
    temporal_caught = (
        honest_time["epistemic_status"] == "unresolved"
        and reference_status(honest_time) == "unresolved"
        and mutated_time["epistemic_status"] == "refuted"
    )
    return {
        "verification": verification_caught,
        "empty_set": empty_caught,
        "property_kind": kind_caught,
        "temporal_binding": temporal_caught,
    }


def run_conformance(root: Any = None) -> dict[str, Any]:
    domain = _predicate_domain_checked(
        sorted({len(item["worlds"]) for item in binding.FINITE_ABSTRACTIONS.values()})
    )
    records = record_cases()
    mutations = mutation_checks()
    entry = audit_entrypoint(root)
    entry_agreement = all(
        _agree(entry[name]) for name in ("retained_system", "retained_url", "native")
    )
    passed = (
        domain["passed"]
        and records["passed"]
        and all(mutations.values())
        and entry_agreement
        and entry["retained_url"]["epistemic_status"] == "supported"
        and entry["retained_system"]["epistemic_status"] == "refuted"
        and entry["url_allowlist_supports_p_system"] is False
        and entry["native"]["epistemic_status"] == "unresolved"
        and entry["native"]["truth_files_read"] == []
        and entry["real_world_authenticity_certified"] is False
        and entry["detection_or_prevention_claimed"] is False
    )
    return {
        "passed": passed,
        "domain": domain,
        "records": records,
        "mutations": mutations,
        "entrypoint_agreement": entry_agreement,
        "native_event_count": entry["native"]["event_count"],
        "retained_system_epistemic": entry["retained_system"]["epistemic_status"],
        "retained_system_conclusion": entry["retained_system"]["conclusion_class"],
        "retained_system_failure_origin": entry["retained_system"]["failure_origin"],
        "retained_system_decision_status": entry["retained_system"]["decision_status"],
        "retained_system_effect_status": entry["retained_system"]["effect_status"],
        "retained_system_fault_attribution": entry["retained_system"]["fault_attribution"],
        "retained_url_epistemic": entry["retained_url"]["epistemic_status"],
        "native_epistemic": entry["native"]["epistemic_status"],
        "native_evidence_status": entry["native"]["evidence_status"],
        "url_allowlist_supports_p_system": entry["url_allowlist_supports_p_system"],
    }
