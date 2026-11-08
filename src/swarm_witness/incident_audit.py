"""Blinded postmortem qualification for public incident claims.

This is an evidence-stage audit of published reports. It reuses the R4
three-way projection and the #12 rule that support and refutation require a
verified, nonempty compatible-world set. It does not detect, replay, or
prevent live incidents.

World-effect propositions stay unresolved when the corpus contains only
postmortem narration. A second document in the same independence group is not
a new observation. Sufficiency propositions can be refuted by retrieved
public sentences that contradict the upgrade, because those sentences are the
object being checked.
"""

from __future__ import annotations

import hashlib
from typing import Any

from swarm_witness.audit_diagnosis import diagnosis
from swarm_witness.conclusion_classes import classify_conclusion

STAGES = ("A", "B")
EPISTEMIC = ("supported", "refuted", "unresolved")


def quote_digest(quote: str) -> str:
    return hashlib.sha256(quote.encode("utf-8")).hexdigest()


def prepare_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for raw in observations:
        item = dict(raw)
        quote = item.get("quote")
        if not isinstance(quote, str) or quote.strip() == "":
            raise ValueError(f"observation {item.get('id')!r} needs a quote")
        item["content_sha256"] = quote_digest(quote)
        prepared.append(item)
    return prepared


def observations_for_stage(
    observations: list[dict[str, Any]], stage: str
) -> list[dict[str, Any]]:
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}")
    allowed = {"A"} if stage == "A" else {"A", "B"}
    return [obs for obs in observations if obs.get("stage") in allowed]


def render_prompt(claim: dict[str, Any], observations: list[dict[str, Any]]) -> str:
    """Serialize the evidence budget a method is allowed to read."""
    lines = [
        f"claim_id: {claim['id']}",
        f"proposition: {claim['proposition'].strip()}",
        "evidence:",
    ]
    fields = (
        "source_id",
        "anchor",
        "quote",
        "authenticity",
        "independence_group",
        "access_level",
        "observation_types",
        "literal_claims",
        "literal_polarity",
        "naive_overread_supports",
        "counterfactual",
        "estimate_imprecise",
        "synthetic",
    )
    for obs in observations:
        if claim["id"] not in obs.get("applies_to", []):
            continue
        lines.append(f"- id: {obs['id']}")
        for field in fields:
            if field in obs:
                lines.append(f"  {field}: {obs[field]}")
    if lines[-1] == "evidence:":
        lines.append("- none")
    return "\n".join(lines)


def _applicable(
    claim: dict[str, Any], observations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [obs for obs in observations if claim["id"] in obs.get("applies_to", [])]


def naive_verdict(claim: dict[str, Any], observations: list[dict[str, Any]]) -> str:
    """Credulous report-assertion acceptance over the shared evidence budget.

    A surface assertion or a scope-collapsed overread supports the claim.
    Supporting sentences win over later refutations in the same package.
    """
    applicable = _applicable(claim, observations)
    claim_id = claim["id"]
    if any(claim_id in obs.get("naive_overread_supports", []) for obs in applicable):
        return "supported"
    literals = [
        obs
        for obs in applicable
        if claim_id in obs.get("literal_claims", [])
    ]
    if any(obs.get("literal_polarity") == "supports" for obs in literals):
        return "supported"
    if any(obs.get("literal_polarity") == "refutes" for obs in literals):
        return "refuted"
    return "unresolved"


def checklist_verdict(claim: dict[str, Any], observations: list[dict[str, Any]]) -> str:
    """Single-source checklist using the same observations as the other methods.

    Selects the earliest pre-registered source in the package. Abstains on a
    counterfactual, an author-flagged imprecise estimate, or an in-source
    contradiction. Does not consult independence groups, telemetry access, or
    property scope.
    """
    applicable = _applicable(claim, observations)
    if not applicable:
        return "unresolved"
    ordinal = min(int(obs["publication_ordinal"]) for obs in applicable)
    source_ids = sorted(
        obs["source_id"]
        for obs in applicable
        if int(obs["publication_ordinal"]) == ordinal
    )
    chosen = [obs for obs in applicable if obs["source_id"] == source_ids[0]]
    if any(obs.get("counterfactual") or obs.get("estimate_imprecise") for obs in chosen):
        return "unresolved"
    literals = [
        obs for obs in chosen if claim["id"] in obs.get("literal_claims", [])
    ]
    polarities = {obs.get("literal_polarity") for obs in literals}
    if "supports" in polarities and "refutes" in polarities:
        return "unresolved"
    if "refutes" in polarities:
        return "refuted"
    if "supports" in polarities:
        return "supported"
    return "unresolved"


def _verifying_levels(claim: dict[str, Any]) -> set[str]:
    """Access levels that may verify this claim.

    Public incident claims keep the default: a held verifying record. Original
    transcripts and platform logs are not that record. Their absence is not an
    upgrade gate and does not fail the comparison; the claim stays unsupported.
    """
    declared = claim.get("verifying_access_levels")
    if not declared:
        return {"raw_telemetry_public"}
    return {str(level) for level in declared}


def _record_digest(obs: dict[str, Any]) -> str:
    recorded = obs.get("content_sha256")
    if isinstance(recorded, str) and recorded:
        return recorded
    return quote_digest(obs["quote"])


def _conflicting_digests(rows: list[dict[str, Any]]) -> set[str]:
    """Same bytes with different polarities do not pick a winner by list order."""
    grouped: dict[str, set[Any]] = {}
    for obs in rows:
        grouped.setdefault(_record_digest(obs), set()).add(obs.get("literal_polarity"))
    return {digest for digest, polarities in grouped.items() if len(polarities) > 1}


def _admit(
    applicable: list[dict[str, Any]], *, count_derived_as_independent: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Drop copied receipts, same-origin derivatives, stale and misbound rows."""
    admitted: list[dict[str, Any]] = []
    withheld: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for obs in applicable:
        authenticity = obs.get("authenticity")
        dependent = authenticity in {"copied", "derived_same_origin"}
        unusable = obs.get("freshness") == "stale" or obs.get("binding") == "misbound"
        inauthentic = authenticity in _INAUTHENTIC
        if unusable or inauthentic or (dependent and not count_derived_as_independent):
            withheld.append(obs)
            continue
        eligible.append(obs)
    conflict = _conflicting_digests(eligible)
    seen_hashes: set[str] = set()
    for obs in eligible:
        digest = _record_digest(obs)
        if digest in conflict or digest in seen_hashes:
            withheld.append(obs)
            continue
        seen_hashes.add(digest)
        admitted.append(obs)
    return admitted, withheld


def _effect_record(
    obs: dict[str, Any], claim: dict[str, Any], polarity: str
) -> bool:
    if obs.get("literal_polarity") != polarity:
        return False
    if claim["id"] not in (obs.get("literal_claims") or []):
        return False
    required = set(claim.get("required_observation_types") or [])
    types = set(obs.get("observation_types") or [])
    if required and not required.issubset(types):
        return False
    if types and types <= {
        "url_allowlist",
        "displayed_command",
        "policy_allow",
        "credential_use",
    }:
        return False
    if not _authenticity_admissible(obs):
        return False
    if obs.get("access_level") not in _verifying_levels(claim):
        return False
    return True


_UNAVAILABLE_ACCESS = frozenset(
    {"withheld", "unobserved", "private_original", "unknown"}
)
_ADMISSIBLE_AUTHENTICITY = frozenset(
    {
        "authentic_public_text",
        "released_reproduction_transcript",
    }
)
_INAUTHENTIC = frozenset(
    {
        "spoofed_tool_line",
        "unauthenticated_tool_line",
    }
)


def _authenticity_admissible(obs: dict[str, Any]) -> bool:
    """Explicit authenticity required before support, refutation, or an authentic status."""
    return obs.get("authenticity") in _ADMISSIBLE_AUTHENTICITY


def _held(obs: dict[str, Any]) -> bool:
    if obs.get("locally_held") is False:
        return False
    return obs.get("access_level") not in _UNAVAILABLE_ACCESS


def _verifies_support(obs: dict[str, Any], claim: dict[str, Any]) -> bool:
    if _effect_record(obs, claim, "supports"):
        return True
    if claim.get("kind") != "evidentiary_sufficiency":
        return False
    required = set(claim.get("required_observation_types") or [])
    types = set(obs.get("observation_types") or [])
    return (
        obs.get("literal_polarity") == "supports"
        and claim["id"] in (obs.get("literal_claims") or [])
        and (not required or required.issubset(types))
    )


def _held_upgrade_blocked(
    claim: dict[str, Any],
    applicable: list[dict[str, Any]],
    admitted: list[dict[str, Any]],
) -> bool:
    """A held blocks_upgrade slot prevents support until that slot verifies.

    An unavailable original cannot be the slot. That configuration is rejected.
    """
    admitted_ids = {obs["id"] for obs in admitted}
    blocked = False
    for obs in applicable:
        if not obs.get("blocks_upgrade"):
            continue
        if not _held(obs):
            raise ValueError(
                f"{obs.get('id')}: unavailable source cannot be an upgrade gate"
            )
        if obs["id"] not in admitted_ids or not _verifies_support(obs, claim):
            blocked = True
    return blocked


def _attributed_origin(claim: dict[str, Any], admitted: list[dict[str, Any]]) -> str:
    """Unique verifying support origin, or undetermined. Does not read warrants.

    Only a record that verifies this proposition can carry the origin. Access
    level is applied after that check.
    """
    levels = _verifying_levels(claim)
    origins: list[str] = []
    for obs in admitted:
        if not _verifies_support(obs, claim):
            continue
        if obs.get("access_level") not in levels:
            continue
        origin = obs.get("named_origin")
        if isinstance(origin, str) and origin.strip():
            origins.append(origin.strip())
    unique = set(origins)
    if len(unique) == 1:
        return next(iter(unique))
    return "undetermined"


def _group(obs: dict[str, Any], *, ignore_independence: bool) -> str:
    if ignore_independence:
        return str(obs["id"])
    return str(obs["independence_group"])


def _project(epistemic: str) -> dict[str, Any]:
    if epistemic == "unresolved":
        classified = classify_conclusion(evidence_complete=False, property_holds=None)
        axes = diagnosis(
            evidence_status="missing",
            decision_status="unknown",
            effect_status="unobserved",
            failure_origin="none",
        )
    elif epistemic == "supported":
        classified = classify_conclusion(evidence_complete=True, property_holds=True)
        axes = diagnosis(
            evidence_status="authentic",
            decision_status="unknown",
            effect_status="unobserved",
            failure_origin="none",
        )
    elif epistemic == "refuted":
        classified = classify_conclusion(
            evidence_complete=True,
            property_holds=False,
            mechanism_exercised=False,
        )
        axes = diagnosis(
            evidence_status="authentic",
            decision_status="unknown",
            effect_status="unobserved",
            failure_origin="undetermined",
        )
    else:
        raise ValueError(f"unknown epistemic status {epistemic!r}")
    return {**classified, **axes}


def swarm_witness_verdict(
    claim: dict[str, Any],
    observations: list[dict[str, Any]],
    *,
    ignore_independence: bool = False,
    count_derived_as_independent: bool = False,
    public_text_verifies_world_effects: bool = False,
    scope_collapse: bool = False,
) -> dict[str, Any]:
    """Qualify one claim from the shared stage package.

    Ablation flags are off for the primary method. Turning them on is how the
    source-withholding and dependence analysis shows unsupported upgrades.
    """
    applicable = _applicable(claim, observations)
    admitted, withheld = _admit(
        applicable, count_derived_as_independent=count_derived_as_independent
    )
    support_groups: set[str] = set()
    refute_groups: set[str] = set()
    for obs in admitted:
        if claim["id"] not in obs.get("literal_claims", []):
            continue
        group = _group(obs, ignore_independence=ignore_independence)
        if obs.get("literal_polarity") == "supports":
            support_groups.add(group)
        elif obs.get("literal_polarity") == "refutes":
            refute_groups.add(group)
    literal_groups = support_groups | refute_groups
    if not literal_groups:
        assertion_status = "unasserted"
    elif support_groups and refute_groups and support_groups != refute_groups:
        assertion_status = "source_conflict"
    elif len(literal_groups) == 1:
        assertion_status = "single_source_asserted"
    else:
        assertion_status = "cross_source_asserted"

    kind = claim["kind"]
    reason = ""
    failure_origin = "none"
    evidence_status = "missing"
    epistemic = "unresolved"
    mechanism_exercised = False

    if kind == "counterfactual":
        epistemic = "unresolved"
        reason = (
            "counterfactual timing or response claim; a postmortem sentence "
            "does not verify what a monitor would have done"
        )
    elif kind == "world_effect":
        raw_support = [
            obs for obs in admitted if _effect_record(obs, claim, "supports")
        ]
        raw_refute = [
            obs for obs in admitted if _effect_record(obs, claim, "refutes")
        ]
        support_authentic = bool(raw_support) and all(
            _authenticity_admissible(obs) for obs in raw_support
        )
        refute_authentic = bool(raw_refute) and all(
            _authenticity_admissible(obs) for obs in raw_refute
        )
        if support_authentic and not raw_refute and not refute_groups:
            epistemic = "supported"
            evidence_status = "authentic"
            reason = (
                "a declared verifying record supports the effect and nothing "
                "admitted contradicts it"
            )
        elif refute_authentic and not raw_support and not support_groups:
            epistemic = "refuted"
            evidence_status = "authentic"
            failure_origin = "effect_boundary"
            mechanism_exercised = True
            reason = "a declared verifying record refutes the effect"
        elif public_text_verifies_world_effects and support_groups and not refute_groups:
            epistemic = "supported"
            evidence_status = "unverified"
            failure_origin = "evidence"
            reason = (
                "ablation: public narration was treated as telemetry and "
                "dependent text was allowed to verify a world effect"
            )
        elif public_text_verifies_world_effects and refute_groups and not support_groups:
            epistemic = "refuted"
            evidence_status = "unverified"
            failure_origin = "evidence"
            reason = "ablation: public narration was treated as a verified refutation"
        else:
            epistemic = "unresolved"
            evidence_status = "missing"
            reason = (
                "postmortem text asserts a world effect, but raw telemetry is "
                "not in the public corpus; copied or same-origin reports do not "
                "verify it"
            )
    elif kind == "evidentiary_sufficiency":
        covering = [obs for obs in admitted if _authenticity_admissible(obs)]
        tags: set[str] = set()
        for obs in covering:
            tags.update(obs.get("observation_types") or [])
        refuting = [
            obs
            for obs in covering
            if obs.get("literal_polarity") == "refutes"
            and claim["id"] in obs.get("literal_claims", [])
        ]
        required = set(claim.get("required_observation_types") or [])
        triggers = set(claim.get("scope_collapse_triggers") or [])
        if scope_collapse and refuting:
            epistemic = "refuted"
            evidence_status = (
                "authentic"
                if all(_authenticity_admissible(obs) for obs in refuting)
                else "unverified"
            )
            failure_origin = "undetermined"
            reason = "ablation still sees an explicit public contradiction"
        elif scope_collapse and any(
            triggers.intersection(obs.get("observation_types") or [])
            for obs in admitted
        ):
            epistemic = "supported"
            evidence_status = "unverified"
            failure_origin = "effect_boundary"
            reason = (
                "ablation: a narrower control was treated as the whole property"
            )
        elif not required.issubset(tags):
            epistemic = "unresolved"
            reason = (
                "required observation types are absent; a non-discriminating "
                "control or an unauthenticated tool line does not establish "
                "the broader claim"
            )
        elif refuting and claim.get("public_text_may_refute_sufficiency"):
            epistemic = "refuted"
            evidence_status = (
                "authentic"
                if all(_authenticity_admissible(obs) for obs in refuting)
                else "unverified"
            )
            failure_origin = "undetermined"
            reason = (
                "retrieved public sentences contradict the sufficiency upgrade; "
                "this checks the published argument, not raw worker telemetry"
            )
        else:
            epistemic = "unresolved"
            reason = "sufficiency claim is not verified by the admitted sentences"
    else:
        raise ValueError(f"unknown claim kind {kind!r}")

    if epistemic == "supported" and _held_upgrade_blocked(claim, applicable, admitted):
        epistemic = "unresolved"
        evidence_status = "unverified"
        reason = (
            "a blocks_upgrade slot on a record this audit holds is not the "
            "verifying observation, so the claim is not supported"
        )

    if epistemic == "unresolved":
        projected = classify_conclusion(evidence_complete=False, property_holds=None)
        axes = diagnosis(
            evidence_status="missing" if evidence_status == "missing" else "unverified",
            decision_status="unknown",
            effect_status="unobserved",
            failure_origin="none" if epistemic == "unresolved" else "undetermined",
        )
    elif epistemic == "refuted":
        projected = classify_conclusion(
            evidence_complete=True,
            property_holds=False,
            mechanism_exercised=mechanism_exercised,
        )
        if mechanism_exercised:
            origin = failure_origin if failure_origin != "none" else "undetermined"
            if origin not in {
                "none",
                "evidence",
                "decision_policy",
                "effect_boundary",
                "comparison_equality",
                "undetermined",
            }:
                origin = "undetermined"
            status = "misbound" if origin == "evidence" else "authentic"
            if evidence_status == "unverified":
                status = "unverified"
        else:
            # A refuted proposition does not establish enforcement or effect origin.
            origin = "undetermined"
            status = (
                evidence_status
                if evidence_status in {"authentic", "unverified"}
                else "missing"
            )
        axes = diagnosis(
            evidence_status=status,  # type: ignore[arg-type]
            decision_status="unknown",
            effect_status="unobserved",
            failure_origin=origin,  # type: ignore[arg-type]
        )
    else:
        projected = _project("supported")
        axes = {
            key: projected[key]
            for key in (
                "evidence_status",
                "decision_status",
                "effect_status",
                "failure_origin",
            )
        }
        if evidence_status == "unverified":
            axes = diagnosis(
                evidence_status="unverified",
                decision_status="unknown",
                effect_status="unobserved",
                failure_origin="evidence",
            )

    imprecise = any(obs.get("estimate_imprecise") for obs in admitted)
    return {
        "epistemic_status": epistemic,
        "assertion_status": assertion_status,
        "verification_status": (
            "raw_telemetry_verified"
            if any(obs.get("access_level") == "raw_telemetry_public" for obs in admitted)
            else "raw_telemetry_unverified"
        ),
        "conclusion_class": projected["conclusion_class"],
        "finding_label": projected["finding_label"],
        "property_holds": projected["property_holds"],
        "reason": reason,
        "document_count": len(applicable),
        "admitted_count": len(admitted),
        "withheld_dependent_count": len(withheld),
        "support_group_count": len(support_groups),
        "refute_group_count": len(refute_groups),
        "estimate_imprecise": imprecise,
        "attributed_origin": (
            _attributed_origin(claim, admitted)
            if epistemic == "supported"
            else "undetermined"
        ),
        "real_world_authenticity_certified": False,
        "detection_or_prevention_claimed": False,
        **axes,
    }


def score_category(
    predicted: str, adjudicated: str, protocol: dict[str, Any]
) -> str:
    for name, rule in protocol["categories"].items():
        if rule["predicted"] == predicted and rule["adjudicated"] == adjudicated:
            return str(name)
    raise KeyError(f"no score category for {predicted!r} vs {adjudicated!r}")


def _count(rows: list[dict[str, Any]], method: str, category: str) -> int:
    return sum(
        1
        for row in rows
        if row["method"] == method and row["category"] == category
    )


def summarize(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    methods = list(protocol["methods"])
    unsupported_names = list(protocol["primary_endpoint"]["unsupported_categories"])
    cell_count = len(rows) // len(methods)
    out: dict[str, Any] = {
        "cell_count_per_method": cell_count,
        "detection_or_prevention_claimed": False,
    }
    for method in methods:
        method_rows = [row for row in rows if row["method"] == method]
        if len(method_rows) != cell_count:
            raise ValueError(f"{method} cell count {len(method_rows)} != {cell_count}")
        unsupported = 0
        for category in protocol["categories"]:
            count = _count(rows, method, category)
            out[f"{method}_{category}"] = count
            if category in unsupported_names:
                unsupported += count
        out[f"{method}_unsupported"] = unsupported
        out[f"{method}_denominator"] = len(method_rows)
    endpoint = protocol["primary_endpoint"]
    if endpoint["success"] != "swarm_witness_strictly_less_than_each_baseline":
        raise ValueError("unsupported primary endpoint rule")
    swarm = out["swarm_witness_unsupported"]
    out["primary_endpoint_passed"] = swarm < out["naive_unsupported"] and swarm < out[
        "checklist_unsupported"
    ]
    return out


def evaluate(
    claims: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    adjudication: dict[str, Any],
    protocol: dict[str, Any],
    *,
    ignore_independence: bool = False,
    count_derived_as_independent: bool = False,
    public_text_verifies_world_effects: bool = False,
    scope_collapse: bool = False,
    stages: tuple[str, ...] = STAGES,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    warrants = adjudication["claims"]
    for stage in stages:
        selected = observations_for_stage(observations, stage)
        for claim in claims:
            warrant = warrants[claim["id"]][stage]["epistemic"]
            prompt = render_prompt(claim, selected)
            predictions = {
                "naive": naive_verdict(claim, selected),
                "checklist": checklist_verdict(claim, selected),
                "swarm_witness": swarm_witness_verdict(
                    claim,
                    selected,
                    ignore_independence=ignore_independence,
                    count_derived_as_independent=count_derived_as_independent,
                    public_text_verifies_world_effects=public_text_verifies_world_effects,
                    scope_collapse=scope_collapse,
                ),
            }
            for method, predicted_obj in predictions.items():
                if method == "swarm_witness":
                    predicted = predicted_obj["epistemic_status"]
                    detail = predicted_obj
                else:
                    predicted = predicted_obj
                    detail = {}
                rows.append(
                    {
                        "claim_id": claim["id"],
                        "stage": stage,
                        "method": method,
                        "predicted": predicted,
                        "adjudicated": warrant,
                        "category": score_category(predicted, warrant, protocol),
                        "prompt_sha256": quote_digest(prompt),
                        "observation_ids": [
                            obs["id"]
                            for obs in selected
                            if claim["id"] in obs.get("applies_to", [])
                        ],
                        "swarm": detail,
                    }
                )
    return rows
