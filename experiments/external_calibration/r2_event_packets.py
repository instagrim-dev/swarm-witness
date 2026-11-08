"""Event-level EvidenceGraph packets from exported native relations.

Claim template: recorded tool event E produced registry mutation M.

Assessor inputs are built from public entities and declared assumptions only.
Native outcomes / object_ids / candidate lists are scoring-only and must not
shape the proposed event identity. Candidate sets are derived from public
receipt/content matches.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from eg_evidence_adapter import (
    assess_attribution,
    assess_fabricated_execution,
    receipt_of,
    sha256_text,
)

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


def _rel_by_subject(relations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in relations:
        sid = rel.get("subject_id")
        if sid:
            out[sid] = rel
    return out


def _is_tool_event(entity: dict[str, Any] | None) -> bool:
    return bool(entity and (entity.get("attrs") or {}).get("event_uuid"))


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


def _content_match(mutation: dict[str, Any], event: dict[str, Any]) -> bool:
    receipt = receipt_of(event)
    if not receipt or receipt.get("accepted") is not True:
        return False
    attrs = mutation.get("attrs") or {}
    return (
        receipt.get("name") == attrs.get("name")
        and receipt.get("sha256") == attrs.get("sha256")
        and receipt.get("namespace") == attrs.get("namespace")
    )


def _token_bound(mutation: dict[str, Any], event: dict[str, Any]) -> bool:
    commitment = (mutation.get("attrs") or {}).get("receipt_token_sha256")
    if not isinstance(commitment, str):
        return False
    receipt = receipt_of(event)
    token = receipt.get("receipt_token") if receipt else None
    if not isinstance(token, str):
        return False
    return sha256_text(token) == commitment


def select_event_for_mutation(
    mutation: dict[str, Any], events: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, list[str]]:
    """Choose a proposed tool event from public entities only (never native object_id)."""
    bound = [e for e in events if _is_tool_event(e) and _token_bound(mutation, e)]
    content = [e for e in events if _is_tool_event(e) and _content_match(mutation, e)]
    if len(bound) == 1:
        return bound[0], [bound[0]["entity_id"]]
    if len(content) == 1:
        return content[0], [content[0]["entity_id"]]
    if len(bound) > 1:
        ordered = sorted(bound, key=lambda e: e["entity_id"])
        return ordered[0], [e["entity_id"] for e in ordered]
    if len(content) > 1:
        ordered = sorted(content, key=lambda e: e["entity_id"])
        return ordered[0], [e["entity_id"] for e in ordered]
    return None, []


def _native_verdict_for_proposition(
    rel: dict[str, Any] | None, proposed_event_id: str | None
) -> dict[str, Any]:
    """Map a native produced relation onto the exact proposed (E, M) pair."""
    if not rel:
        return {
            "verdict": "unresolved",
            "native_outcome": None,
            "method": None,
            "rationale": "no native produced relation for mutation",
            "native_object_id": None,
            "proposition_aligned": False,
        }
    outcome = rel.get("outcome")
    object_id = rel.get("object_id")
    # Native support counts for this packet only when it names the same tool event.
    if outcome == "supported":
        # Count native support only when it names this exact tool event.
        aligned = bool(proposed_event_id and object_id == proposed_event_id)
        return {
            "verdict": "supported" if aligned else "unresolved",
            "native_outcome": outcome,
            "method": rel.get("method"),
            "rationale": rel.get("rationale"),
            "native_object_id": object_id,
            "native_candidates": list(rel.get("candidates") or []),
            "proposition_aligned": aligned,
            "note": (
                None
                if aligned
                else "native supported a different or non-event object; not this proposition"
            ),
        }
    return {
        "verdict": _map_native(outcome),
        "native_outcome": outcome,
        "method": rel.get("method"),
        "rationale": rel.get("rationale"),
        "native_object_id": object_id,
        "native_candidates": list(rel.get("candidates") or []),
        "proposition_aligned": True,
    }


def _factual_for_pair(
    *,
    mutation_key: str,
    event: dict[str, Any] | None,
    private_produced: dict[str, Any],
    premise_status: str | None = None,
) -> dict[str, Any]:
    """Private-truth identity for the selected pair. Native abstention cannot invent this."""
    truth = private_produced.get(mutation_key)
    if not isinstance(truth, dict):
        out: dict[str, Any] = {
            "known": False,
            "proposition_holds": None,
            "mutation_key": mutation_key,
        }
        if premise_status is not None:
            out["premise_status"] = premise_status
        return out
    truth_uuid = truth.get("event_uuid")
    event_uuid = (event or {}).get("attrs", {}).get("event_uuid") if event else None
    holds = bool(truth_uuid and event_uuid and truth_uuid == event_uuid)
    out = {
        "known": True,
        "proposition_holds": holds,
        "truth_event_uuid": truth_uuid,
        "proposed_event_uuid": event_uuid,
        "mutation_key": mutation_key,
    }
    if premise_status is not None:
        out["premise_status"] = premise_status
    return out


def _warrant_from_factual(
    factual: dict[str, Any], *, evidence_sufficient: bool
) -> str:
    """Evidence sufficiency for the selected pair — not private identity alone.

    factual_outcome carries execution truth. Warrant stays unresolved when the
    public evidence does not justify attribution (missing token/clock/independence/
    exclusivity/temporal fit), even if private identity would match.
    """
    if factual.get("premise_status") == "false":
        return "unresolved"
    if (
        factual.get("known")
        and factual.get("proposition_holds") is True
        and evidence_sufficient
    ):
        return "supported"
    return "unresolved"


def assessor_input_fingerprint(observations: list[dict[str, Any]]) -> str:
    """Stable hash of assessor-visible fields (excludes native scoring metadata)."""
    scrubbed = []
    for obs in observations:
        row = {
            k: v
            for k, v in obs.items()
            if k
            not in {
                "id",
                "applies_to",
                "independence_group",
                "anchor",
            }
        }
        scrubbed.append(row)
    blob = json.dumps(scrubbed, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_attribution_observations(
    *,
    claim_id: str,
    decl: dict[str, Any],
    populations: list[dict[str, Any]],
    mutation: dict[str, Any],
    event: dict[str, Any] | None,
    candidate_event_ids: list[str],
) -> list[dict[str, Any]]:
    mutation_label = (
        mutation.get("natural_key")
        or (mutation.get("attrs") or {}).get("id")
        or mutation["entity_id"]
    )
    observations = [
        _assumptions_obs(claim_id, decl),
        _capture_obs(claim_id, populations),
        _obs(
            obs_id=f"{claim_id}-mutation",
            claim_id=claim_id,
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
        event_label = (event.get("attrs") or {}).get("event_uuid") or event["entity_id"]
        observations.append(
            _obs(
                obs_id=f"{claim_id}-event",
                claim_id=claim_id,
                observation_types=["tool_event_record", "execution_interval"],
                quote=(
                    f"tool_event event_uuid={event_label}; "
                    f"receipt_present={bool(receipt_of(event))}; "
                    f"interval=[{event.get('time_lower')},{event.get('time_upper')}]"
                ),
                entity=event,
            )
        )
    if candidate_event_ids:
        observations.append(
            _obs(
                obs_id=f"{claim_id}-candidates",
                claim_id=claim_id,
                observation_types=["candidate_event_set"],
                quote=f"evidence_derived_candidate_tool_event_ids={candidate_event_ids}",
                candidate_event_ids=list(candidate_event_ids),
            )
        )
    return observations


def build_packets(export_path: Path = EXPORT) -> list[dict[str, Any]]:
    doc = json.loads(export_path.read_text(encoding="utf-8"))
    packets: list[dict[str, Any]] = []

    for scenario in doc["scenarios"]:
        name = scenario["scenario"]
        decl = scenario["declared_assumptions"]
        mutations = scenario["public_entities"]["registry_mutations"]
        events = [e for e in scenario["public_entities"]["tool_events"] if _is_tool_event(e)]
        safer_by = _rel_by_subject(scenario["native_relations"]["safer_produced"])
        legacy_by = _rel_by_subject(scenario["native_relations"]["legacy_produced"])
        private_produced = scenario["private_truth"]["produced"]
        populations = list(
            (scenario.get("public_entities") or {}).get("populations") or []
        )
        executed_by = {
            rel.get("subject_id"): rel
            for rel in (scenario["native_relations"].get("executed") or [])
            if rel.get("subject_id")
        }
        spoofed_uuids = {
            (s.get("event_uuid") if isinstance(s, dict) else s)
            for s in (scenario["private_truth"].get("spoofed") or [])
        }
        premise_status = "false" if name == "false_exclusivity" else None

        for mutation in mutations:
            mid = mutation["entity_id"]
            mkey = mutation.get("natural_key") or (mutation.get("attrs") or {}).get("id")
            event, cand_ids = select_event_for_mutation(mutation, events)
            proposed_event_id = event["entity_id"] if event else None
            # Guard: never accept a mutation entity as the proposed event.
            if event is not None and not _is_tool_event(event):
                event = None
                proposed_event_id = None
                cand_ids = []

            event_label = (
                (event.get("attrs") or {}).get("event_uuid")
                if event
                else "∅"
            ) or proposed_event_id or "∅"
            mutation_label = mkey or mid
            cid = (
                f"EG-EVT-{name}-{mutation_label}-"
                f"{hashlib.sha1(f'{mid}:{proposed_event_id}'.encode()).hexdigest()[:10]}"
            )

            safer_arm = _native_verdict_for_proposition(safer_by.get(mid), proposed_event_id)
            legacy_arm = _native_verdict_for_proposition(legacy_by.get(mid), proposed_event_id)

            factual = _factual_for_pair(
                mutation_key=str(mutation_label),
                event=event,
                private_produced=private_produced,
                premise_status=premise_status,
            )

            observations = build_attribution_observations(
                claim_id=cid,
                decl=decl,
                populations=populations,
                mutation=mutation,
                event=event,
                candidate_event_ids=cand_ids,
            )
            claim = {
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
            }
            adapter = assess_attribution(claim, observations)
            # Warrant uses the same public-evidence sufficiency gate as the adapter,
            # plus private identity — never native abstention as a factual label.
            warranted = _warrant_from_factual(
                factual, evidence_sufficient=(adapter["verdict"] == "supported")
            )

            packet = {
                "claim": claim,
                "assumptions": [
                    "Assessor sees public entities and declared case assumptions only.",
                    "Native outcomes and private dispatch bindings are scoring-only.",
                    "Proposed event identity is selected from public entities, not native object_id.",
                ],
                "observations": observations,
                "declared_assumptions": _assessor_decl(decl),
                "native_arms": {
                    "evidencegraph_safer_produced": safer_arm,
                    "evidencegraph_legacy_produced": legacy_arm,
                    "eg_evidence_derived_adapter": {
                        "verdict": adapter["verdict"],
                        "reason": adapter["reason"],
                        "capability": adapter.get("capability"),
                        "binding": adapter.get("binding"),
                        "predicates": adapter.get("predicates"),
                        "reconstruction": False,
                        "note": "Evaluated evidence-derived adapter; not a native EG export.",
                    },
                },
                "warranted_conclusion": {
                    "status": warranted,
                    "basis": "private_identity_and_adapter_sufficiency_predicate",
                    "note": (
                        f"safer_native_outcome={safer_arm.get('native_outcome')}; "
                        f"safer_aligned={safer_arm.get('proposition_aligned')}; "
                        "factual_outcome=execution truth; warrant uses adapter "
                        "support as the public-evidence sufficiency predicate "
                        "(method-dependent; conformance column is primary)"
                    ),
                    "depends_on_evaluated_method": True,
                },
                "factual_outcome": factual,
                "row_refs": {
                    "export": _export_ref(export_path),
                    "scenario": name,
                    "mutation_id": mid,
                    "case": scenario.get("case"),
                },
            }
            packets.append(packet)

        # Successful-execution family: every accepted public receipt, not only
        # native complete_registry_absence selections. Absence is checked by the adapter.
        for event in events:
            receipt = receipt_of(event)
            if not receipt or receipt.get("accepted") is not True:
                continue
            # Focus the family on absence candidates + spoofed controls: receipts
            # whose claimed event_id/name is not among registry mutations, OR that
            # appear in private spoofed (scoring-only membership for corpus coverage).
            claimed_id = receipt.get("event_id")
            mut_ids = {
                str(m.get("natural_key") or (m.get("attrs") or {}).get("id"))
                for m in mutations
            }
            mut_names = {
                ((m.get("attrs") or {}).get("namespace"), (m.get("attrs") or {}).get("name"))
                for m in mutations
            }
            claimed_absent = (claimed_id is None or str(claimed_id) not in mut_ids) and (
                (receipt.get("namespace"), receipt.get("name")) not in mut_names
            )
            euuid = (event.get("attrs") or {}).get("event_uuid")
            if not claimed_absent and euuid not in spoofed_uuids:
                continue

            subject_id = event["entity_id"]
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
                        f"{receipt.get('accepted')}; claimed_event_id={claimed_id}; "
                        f"interval=[{event.get('time_lower')},{event.get('time_upper')}]"
                    ),
                    entity=event,
                ),
                _obs(
                    obs_id=f"{cid}-registry-pop",
                    claim_id=cid,
                    observation_types=["registry_mutation_population"],
                    quote=f"registry_mutation_count={len(mutations)}",
                    registry_mutations=mutations,
                ),
            ]
            rel = executed_by.get(subject_id)
            has_native_executed = bool(rel and rel.get("method") == "complete_registry_absence")
            if has_native_executed:
                native_verdict = _map_native(rel.get("outcome"))
                native_arm = {
                    "verdict": native_verdict,
                    "native_outcome": rel.get("outcome"),
                    "method": rel.get("method"),
                    "rationale": rel.get("rationale"),
                    "comparison_role": "native_executed_relation",
                }
                comparison_role = "native_executed_comparison"
            else:
                # Additional control (e.g. relay spoofed receipt): no exported
                # native executed relation; mapped unresolved for reference only.
                native_arm = {
                    "verdict": "unresolved",
                    "native_outcome": None,
                    "method": None,
                    "rationale": "no native executed relation for this public event",
                    "comparison_role": "additional_control_no_native_executed",
                }
                comparison_role = "additional_control"
            # Factual: spoofed receipts never establish real execution.
            factual = {
                "spoofed": euuid in spoofed_uuids,
                "proposition_holds": False if euuid in spoofed_uuids else None,
                "known": euuid in spoofed_uuids,
                "native_executed_outcome": (rel or {}).get("outcome") if has_native_executed else None,
                "comparison_role": comparison_role,
            }
            # Execution warrants still consult native refutation when present;
            # that dependence is scoring-only and disclosed — not assessor input.
            if euuid in spoofed_uuids and has_native_executed and native_arm["verdict"] == "refuted":
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
                            "registry_mutation_population",
                        ],
                        "verifying_access_levels": ["raw_telemetry_public"],
                        "source_revision": SOURCE_REV,
                        "scenario": name,
                        "seed": scenario["seed"],
                        "family": "fabricated_execution",
                        "comparison_role": comparison_role,
                    },
                    "assumptions": [
                        "Successful-execution claims are a separate family from attribution.",
                        "Assessor inputs exclude private spoofed labels and native outcomes.",
                        (
                            "Corpus is 8 native executed comparisons plus additional "
                            "controls selected with private spoofed membership; "
                            "assessor observations remain public."
                            if comparison_role == "additional_control"
                            else "Native executed relation is the reference mapping."
                        ),
                    ],
                    "observations": observations,
                    "declared_assumptions": _assessor_decl(decl),
                    "native_arms": {
                        "evidencegraph_safer_executed": native_arm,
                        "eg_evidence_derived_adapter": {
                            "verdict": adapter["verdict"],
                            "reason": adapter["reason"],
                            "capability": adapter.get("capability"),
                            "coverage_detail": adapter.get("coverage_detail"),
                            "absence_detail": adapter.get("absence_detail"),
                            "predicates": adapter.get("predicates"),
                        },
                    },
                    "warranted_conclusion": {
                        "status": warranted,
                        "basis": (
                            "native_refutation_when_executed_relation_present"
                            if has_native_executed
                            else "additional_control_unresolved_without_native_executed"
                        ),
                        "note": (
                            f"comparison_role={comparison_role}; "
                            f"native_executed_outcome="
                            f"{(rel or {}).get('outcome') if has_native_executed else None}; "
                            f"private_spoofed={euuid in spoofed_uuids}; "
                            "warrant may depend on native refutation status "
                            "(assessor inputs do not)"
                        ),
                        "depends_on_evaluated_method": has_native_executed,
                    },
                    "factual_outcome": factual,
                    "row_refs": {
                        "export": _export_ref(export_path),
                        "scenario": name,
                        "event_uuid": euuid,
                        "subject_id": subject_id,
                        "comparison_role": comparison_role,
                    },
                }
            )

    return packets


def _export_ref(export_path: Path) -> str:
    try:
        return str(export_path.resolve().relative_to(ROOT))
    except ValueError:
        return str(export_path)


def mutate_native_fields_for_independence_check(doc: dict[str, Any]) -> dict[str, Any]:
    """Corrupt native outcomes/object_ids/candidates; public entities unchanged."""
    mutated = copy.deepcopy(doc)
    for scenario in mutated["scenarios"]:
        for key in ("safer_produced", "legacy_produced", "executed"):
            for rel in scenario["native_relations"].get(key) or []:
                rel["outcome"] = "supported"
                rel["object_id"] = "synthetic-native-object"
                rel["candidates"] = ["synthetic-candidate-a", "synthetic-candidate-b"]
                rel["rationale"] = "mutated for input-independence check"
    return mutated


if __name__ == "__main__":
    packets = build_packets()
    families: dict[str, int] = {}
    non_events = 0
    for p in packets:
        families.setdefault(p["claim"]["family"], 0)
        families[p["claim"]["family"]] += 1
        if p["claim"]["family"] == "event_attribution":
            for obs in p["observations"]:
                if "tool_event_record" in (obs.get("observation_types") or []):
                    ent = obs.get("entity") or {}
                    if not (ent.get("attrs") or {}).get("event_uuid"):
                        non_events += 1
    print(
        json.dumps(
            {
                "n": len(packets),
                "families": families,
                "tool_event_records_without_event_uuid": non_events,
                "scenarios": sorted({p["claim"]["scenario"] for p in packets}),
            },
            indent=2,
        )
    )
