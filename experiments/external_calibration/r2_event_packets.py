"""Event-level EvidenceGraph packets from exported native relations.

Claim template: recorded tool event E produced registry mutation M.
Assessor inputs are observable records and declared assumptions only.
Native verdicts / private truth / scenario names stay out of observations.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from eg_evidence_adapter import assess_attribution, assess_fabricated_execution

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "evidence" / "external_calibration_v1" / "eg_native_relations_seed0.json"
SOURCE_REV = "a5ea5c9947039009ca795275d834be7b61069080"

NATIVE_TO_LOCAL = {
    "supported": "supported",
    "contradicted": "refuted",
    "ambiguous": "unresolved",
    "unmatched": "unresolved",
    "not_assessable": "unresolved",
}


def _map_native(outcome: str | None) -> str:
    return NATIVE_TO_LOCAL.get(str(outcome or ""), "unresolved")


def _entity_index(entities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {e["entity_id"]: e for e in entities}


def _rel_by_subject(relations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in relations:
        sid = rel.get("subject_id")
        if sid:
            out[sid] = rel
    return out


def _obs(
    *,
    obs_id: str,
    claim_id: str,
    observation_types: list[str],
    quote: str,
    **extra: Any,
) -> dict[str, Any]:
    record = {
        "id": obs_id,
        "source_id": "evidencegraph-r2-event",
        "stage": "A",
        "publication_ordinal": 1,
        "independence_group": f"eg-evt-{claim_id}",
        "authenticity": "authentic_public_text",
        "access_level": "raw_telemetry_public",
        "anchor": f"retained EvidenceGraph public entities @ {SOURCE_REV}",
        "quote": quote,
        "applies_to": [claim_id],
        "observation_types": observation_types,
        "time_basis": "source_stated",
        "event_time": "retained-r2-event",
    }
    record.update(extra)
    return record


def _assessor_decl(decl: dict[str, Any]) -> dict[str, Any]:
    """Strip scenario-identifying title; keep only assessor-usable assumptions."""
    return {
        "clock_bounds": list(decl.get("clock_bounds") or []),
        "trust_domains": list(decl.get("trust_domains") or []),
    }


def _assumptions_obs(claim_id: str, decl: dict[str, Any]) -> dict[str, Any]:
    assessor = _assessor_decl(decl)
    return _obs(
        obs_id=f"{claim_id}-decl",
        claim_id=claim_id,
        observation_types=["declared_assumptions"],
        quote=(
            "Declared trust domains and clock bounds from case.json "
            "(exclusive_receipt_tokens / independence / clock_bounds)."
        ),
        declared_assumptions=assessor,
    )


def _capture_obs(claim_id: str, populations: list[dict[str, Any]]) -> dict[str, Any]:
    return _obs(
        obs_id=f"{claim_id}-capture",
        claim_id=claim_id,
        observation_types=["capture_declaration"],
        quote=(
            "Public population.json capture declarations: "
            + "; ".join(
                f"{p.get('witness_id')}:complete={p.get('complete')},"
                f"[{p.get('started_at')},{p.get('stopped_at')}]"
                for p in populations
            )
        ),
        populations=populations,
    )


def _warrant_for_supported(
    *,
    mutation_key: str,
    event: dict[str, Any] | None,
    private_produced: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    truth = private_produced.get(mutation_key) or {}
    truth_uuid = truth.get("event_uuid")
    event_uuid = (event or {}).get("attrs", {}).get("event_uuid")
    holds = bool(truth_uuid and event_uuid and truth_uuid == event_uuid)
    return (
        "supported" if holds else "unresolved",
        {
            "proposition_holds": holds,
            "truth_event_uuid": truth_uuid,
            "proposed_event_uuid": event_uuid,
            "known": True,
        },
    )


def build_packets(export_path: Path = EXPORT) -> list[dict[str, Any]]:
    doc = json.loads(export_path.read_text(encoding="utf-8"))
    packets: list[dict[str, Any]] = []

    for scenario in doc["scenarios"]:
        name = scenario["scenario"]
        decl = scenario["declared_assumptions"]
        mutations = scenario["public_entities"]["registry_mutations"]
        events = scenario["public_entities"]["tool_events"]
        by_id = _entity_index(mutations + events)
        safer_by = _rel_by_subject(scenario["native_relations"]["safer_produced"])
        legacy_by = _rel_by_subject(scenario["native_relations"]["legacy_produced"])
        private_produced = scenario["private_truth"]["produced"]
        populations = list(
            (scenario.get("public_entities") or {}).get("populations") or []
        )
        executed = list(scenario["native_relations"].get("executed") or [])

        for mutation in mutations:
            mid = mutation["entity_id"]
            mkey = mutation.get("natural_key") or (mutation.get("attrs") or {}).get("id")
            safer = safer_by.get(mid) or {
                "outcome": "unmatched",
                "method": None,
                "rationale": "no safer produced relation",
                "candidates": [],
                "object_id": None,
            }
            legacy = legacy_by.get(mid) or {
                "outcome": "unmatched",
                "method": None,
                "rationale": "no legacy produced relation",
                "candidates": [],
                "object_id": None,
            }
            object_id = safer.get("object_id")
            event = by_id.get(object_id) if object_id else None
            # If unsupported, still propose first candidate when present for a concrete claim.
            if event is None and safer.get("candidates"):
                event = by_id.get(safer["candidates"][0])
            proposed_event_id = event["entity_id"] if event else None
            event_label = (
                (event.get("attrs") or {}).get("event_uuid")
                or (event or {}).get("natural_key")
                or proposed_event_id
                or "∅"
            )
            mutation_label = mkey or mid
            cid = (
                f"EG-EVT-{name}-{mutation_label}-"
                f"{hashlib.sha1(f'{mid}:{proposed_event_id}'.encode()).hexdigest()[:10]}"
            )

            native_safer_verdict = _map_native(safer.get("outcome"))
            if safer.get("outcome") == "supported":
                warranted, factual = _warrant_for_supported(
                    mutation_key=str(mutation_label),
                    event=event,
                    private_produced=private_produced,
                )
                # Native may confidently support a false premise (false_exclusivity).
                if factual.get("proposition_holds") is False:
                    warranted = "unresolved"
            else:
                warranted = native_safer_verdict
                factual = {
                    "proposition_holds": False,
                    "native_safer_outcome": safer.get("outcome"),
                    "known": True,
                }

            observations = [
                _assumptions_obs(cid, decl),
                _capture_obs(cid, populations),
                _obs(
                    obs_id=f"{cid}-mutation",
                    claim_id=cid,
                    observation_types=["registry_mutation_record", "receipt_commitment"],
                    quote=(
                        f"registry_mutation natural_key={mutation_label}; "
                        f"commitment={(mutation.get('attrs') or {}).get('receipt_token_sha256')}; "
                        f"interval=[{mutation.get('time_lower')},{mutation.get('time_upper')}]"
                    ),
                    entity=mutation,
                ),
            ]
            if event is not None:
                observations.append(
                    _obs(
                        obs_id=f"{cid}-event",
                        claim_id=cid,
                        observation_types=["tool_event_record", "execution_interval"],
                        quote=(
                            f"tool_event event_uuid={event_label}; "
                            f"receipt_present={bool(_receipt_present(event))}; "
                            f"interval=[{event.get('time_lower')},{event.get('time_upper')}]"
                        ),
                        entity=event,
                    )
                )
            # Candidate set as observables (ids only), not native outcomes.
            cand_ids = list(safer.get("candidates") or [])
            if cand_ids:
                observations.append(
                    _obs(
                        obs_id=f"{cid}-candidates",
                        claim_id=cid,
                        observation_types=["candidate_event_set"],
                        quote=f"candidate_tool_event_ids={cand_ids}",
                        candidate_event_ids=cand_ids,
                    )
                )

            packet = {
                "claim": {
                    "id": cid,
                    "kind": "world_effect",
                    "proposition": (
                        f"Recorded tool event {event_label} produced registry "
                        f"mutation {mutation_label}."
                    ),
                    "quantifier": f"mutation {mutation_label} under retained case",
                    "required_observation_types": [
                        "registry_mutation_record",
                        "tool_event_record",
                    ],
                    "verifying_access_levels": ["raw_telemetry_public"],
                    "source_revision": SOURCE_REV,
                    "scenario": name,
                    "seed": scenario["seed"],
                    "family": "event_attribution",
                    "proposed_event_id": proposed_event_id,
                    "mutation_id": mid,
                },
                "assumptions": [
                    "Assessor sees public entities and declared case assumptions only.",
                    "Native outcomes and private dispatch bindings are scoring-only.",
                ],
                "observations": observations,
                "declared_assumptions": _assessor_decl(decl),
                "native_arms": {
                    "evidencegraph_safer_produced": {
                        "verdict": native_safer_verdict,
                        "native_outcome": safer.get("outcome"),
                        "method": safer.get("method"),
                        "rationale": safer.get("rationale"),
                        "candidates": safer.get("candidates"),
                    },
                    "evidencegraph_legacy_produced": {
                        "verdict": _map_native(legacy.get("outcome")),
                        "native_outcome": legacy.get("outcome"),
                        "method": legacy.get("method"),
                        "rationale": legacy.get("rationale"),
                        "candidates": legacy.get("candidates"),
                    },
                },
                "warranted_conclusion": {
                    "status": warranted,
                    "basis": "private_truth_after_native_decision",
                    "note": (
                        f"native_safer_outcome={safer.get('outcome')}; "
                        "private event identity scored afterward"
                    ),
                },
                "factual_outcome": factual,
                "row_refs": {
                    "export": str(export_path.relative_to(ROOT)),
                    "scenario": name,
                    "mutation_id": mid,
                    "case": scenario.get("case"),
                },
            }
            # Adapter verdict is a scored method arm, computed from assessor inputs only.
            adapter = assess_attribution(packet["claim"], observations)
            packet["native_arms"]["eg_evidence_derived_adapter"] = {
                "verdict": adapter["verdict"],
                "reason": adapter["reason"],
                "capability": adapter.get("capability"),
                "reconstruction": False,
                "note": "Evaluated evidence-derived adapter; not a native EG export.",
            }
            packets.append(packet)

        # Successful-execution / absence claims from native executed relations
        # (separate family from attribution). Private spoofed set is scoring-only.
        spoofed_uuids = {
            (s.get("event_uuid") if isinstance(s, dict) else s)
            for s in (scenario["private_truth"].get("spoofed") or [])
        }
        for rel in executed:
            # Absence-based successful-execution contradictions only.
            if rel.get("method") != "complete_registry_absence":
                continue
            subject_id = rel.get("subject_id")
            event = by_id.get(subject_id) if subject_id else None
            if event is None:
                continue
            euuid = (event.get("attrs") or {}).get("event_uuid") or subject_id
            cid = (
                f"EG-FAB-{name}-{euuid}-"
                f"{hashlib.sha1(str(subject_id).encode()).hexdigest()[:8]}"
            )
            observations = [
                _assumptions_obs(cid, decl),
                _capture_obs(cid, populations),
                _obs(
                    obs_id=f"{cid}-receipt",
                    claim_id=cid,
                    observation_types=[
                        "tool_event_record",
                        "successful_execution_claim",
                    ],
                    quote=(
                        f"tool_event event_uuid={euuid}; accepted="
                        f"{((event.get('attrs') or {}).get('receipt') or {}).get('accepted')}; "
                        f"interval=[{event.get('time_lower')},{event.get('time_upper')}]"
                    ),
                    entity=event,
                ),
            ]
            native_verdict = _map_native(rel.get("outcome"))
            # Warrant: invented receipts never establish real execution; when native
            # contradicts under covering capture, warrant is refuted; when native
            # cannot assess, warrant stays unresolved (absence not established).
            if rel.get("outcome") == "contradicted":
                warranted = "refuted"
            else:
                warranted = "unresolved"
            adapter = assess_fabricated_execution({"id": cid}, observations)
            packets.append(
                {
                    "claim": {
                        "id": cid,
                        "kind": "world_effect",
                        "proposition": (
                            f"Successful receipt {euuid} establishes a real "
                            f"registry execution under the retained capture."
                        ),
                        "quantifier": f"successful receipt {euuid}",
                        "required_observation_types": [
                            "successful_execution_claim",
                            "capture_declaration",
                        ],
                        "verifying_access_levels": ["raw_telemetry_public"],
                        "source_revision": SOURCE_REV,
                        "scenario": name,
                        "seed": scenario["seed"],
                        "family": "fabricated_execution",
                    },
                    "assumptions": [
                        "Successful-execution claims are a separate family from attribution.",
                        "Assessor inputs exclude private spoofed labels and native outcomes.",
                    ],
                    "observations": observations,
                    "declared_assumptions": _assessor_decl(decl),
                    "native_arms": {
                        "evidencegraph_safer_executed": {
                            "verdict": native_verdict,
                            "native_outcome": rel.get("outcome"),
                            "method": rel.get("method"),
                            "rationale": rel.get("rationale"),
                        },
                        "eg_evidence_derived_adapter": {
                            "verdict": adapter["verdict"],
                            "reason": adapter["reason"],
                            "capability": adapter.get("capability"),
                            "coverage_detail": adapter.get("coverage_detail"),
                        },
                    },
                    "warranted_conclusion": {
                        "status": warranted,
                        "basis": "private_spoofed_after_native_executed",
                        "note": (
                            f"native_executed_outcome={rel.get('outcome')}; "
                            f"private_spoofed={euuid in spoofed_uuids}"
                        ),
                    },
                    "factual_outcome": {
                        "spoofed": euuid in spoofed_uuids,
                        "proposition_holds": False,
                        "native_executed_outcome": rel.get("outcome"),
                        "known": True,
                    },
                    "row_refs": {
                        "export": str(export_path.relative_to(ROOT)),
                        "scenario": name,
                        "event_uuid": euuid,
                        "subject_id": subject_id,
                    },
                }
            )

    return packets


def _receipt_present(event: dict[str, Any]) -> bool:
    receipt = (event.get("attrs") or {}).get("receipt")
    return bool(receipt)


if __name__ == "__main__":
    packets = build_packets()
    families = {}
    for p in packets:
        families.setdefault(p["claim"]["family"], 0)
        families[p["claim"]["family"]] += 1
    print(
        json.dumps(
            {"n": len(packets), "families": families, "scenarios": sorted({p['claim']['scenario'] for p in packets})},
            indent=2,
        )
    )
