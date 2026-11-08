"""Competent invariant checker for the frozen comparison.

Same evidence packet as the other methods. It may abstain, and a decision or
allow is not an effect. It does not read adjudication, hidden truth, or notes.

This is not the naive PASS baseline and it does not call Swarm Witness.
"""

from __future__ import annotations

from typing import Any

_DECISION_TYPES = frozenset(
    {
        "url_allowlist",
        "displayed_command",
        "policy_allow",
        "credential_use",
    }
)
_WITHHELD_AUTHENTICITY = frozenset(
    {
        "copied",
        "derived_same_origin",
        "spoofed_tool_line",
        "unauthenticated_tool_line",
    }
)
# Public text uses the same admissible set as Swarm Witness. The application
# sink label admits a locally held effect readback. It does not certify a
# real-world incident. Support and refutation both require this set.
_ADMISSIBLE_AUTHENTICITY = frozenset(
    {
        "authentic_public_text",
        "released_reproduction_transcript",
        "application_owned_readback",
    }
)


def _applicable(
    claim: dict[str, Any], observations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [obs for obs in observations if claim["id"] in obs.get("applies_to", [])]


def _levels(claim: dict[str, Any]) -> set[str]:
    declared = claim.get("verifying_access_levels")
    if not declared:
        return {"raw_telemetry_public"}
    return {str(level) for level in declared}


def _digest(obs: dict[str, Any]) -> str:
    from swarm_witness.incident_audit import quote_digest

    recorded = obs.get("content_sha256")
    if isinstance(recorded, str) and recorded:
        return recorded
    return quote_digest(str(obs.get("quote") or ""))


def _admit(
    applicable: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    admitted: list[dict[str, Any]] = []
    withheld: list[dict[str, Any]] = []
    seen: set[str] = set()
    for obs in applicable:
        blocked = (
            obs.get("authenticity") in _WITHHELD_AUTHENTICITY
            or obs.get("freshness") == "stale"
            or obs.get("binding") == "misbound"
            or _digest(obs) in seen
        )
        if blocked:
            withheld.append(obs)
            continue
        seen.add(_digest(obs))
        admitted.append(obs)
    return admitted, withheld


def _authenticity_admissible(obs: dict[str, Any]) -> bool:
    return obs.get("authenticity") in _ADMISSIBLE_AUTHENTICITY


def _evidence_status(deciding: list[dict[str, Any]]) -> str:
    """Authentic only when every deciding record is on the admissible allowlist."""
    if deciding and all(_authenticity_admissible(obs) for obs in deciding):
        return "authentic"
    return "missing"


def _decision_only(obs: dict[str, Any]) -> bool:
    types = set(obs.get("observation_types") or [])
    return bool(types) and types <= _DECISION_TYPES


def _verifies_target(obs: dict[str, Any], claim: dict[str, Any]) -> bool:
    """The record is about this proposition and carries its required observations."""
    if obs.get("literal_polarity") != "supports":
        return False
    if claim["id"] not in (obs.get("literal_claims") or []):
        return False
    required = set(claim.get("required_observation_types") or [])
    types = set(obs.get("observation_types") or [])
    if required and not required.issubset(types):
        return False
    if claim.get("kind") == "world_effect" and _decision_only(obs):
        return False
    return True


def _origin(claim: dict[str, Any], admitted: list[dict[str, Any]]) -> str:
    levels = _levels(claim)
    origins: list[str] = []
    for obs in admitted:
        if not _verifies_target(obs, claim):
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


_UNAVAILABLE_ACCESS = frozenset(
    {"withheld", "unobserved", "private_original", "unknown"}
)


def _held(obs: dict[str, Any]) -> bool:
    if obs.get("locally_held") is False:
        return False
    return obs.get("access_level") not in _UNAVAILABLE_ACCESS


def _upgrade_blocked(
    claim: dict[str, Any],
    applicable: list[dict[str, Any]],
    admitted: list[dict[str, Any]],
    *,
    support_ids: set[str],
) -> bool:
    admitted_ids = {obs["id"] for obs in admitted}
    blocked = False
    for obs in applicable:
        if not obs.get("blocks_upgrade"):
            continue
        if not _held(obs):
            raise ValueError(
                f"{obs.get('id')}: unavailable source cannot be an upgrade gate"
            )
        if obs["id"] not in admitted_ids or obs["id"] not in support_ids:
            blocked = True
    return blocked


def _finish(
    epistemic: str,
    reason: str,
    claim: dict[str, Any],
    admitted: list[dict[str, Any]],
    withheld: list[dict[str, Any]],
    *,
    evidence_status: str,
) -> dict[str, Any]:
    return {
        "epistemic_status": epistemic,
        "reason": reason,
        "evidence_status": evidence_status,
        "attributed_origin": (
            _origin(claim, admitted) if epistemic == "supported" else "undetermined"
        ),
        "admitted_ids": [obs["id"] for obs in admitted],
        "withheld_ids": [obs["id"] for obs in withheld],
        "real_world_authenticity_certified": False,
        "detection_or_prevention_claimed": False,
    }


def strong_invariant_verdict(
    claim: dict[str, Any], observations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Checklist: abstain unless a verifying record decides, and do not collapse scope."""
    applicable = _applicable(claim, observations)
    admitted, withheld = _admit(applicable)
    kind = claim["kind"]
    levels = _levels(claim)
    required = set(claim.get("required_observation_types") or [])

    if kind == "counterfactual":
        return _finish(
            "unresolved",
            "counterfactual claim; a sentence about what a monitor would have done is not a record",
            claim,
            admitted,
            withheld,
            evidence_status="missing",
        )

    if kind == "world_effect":
        support = [
            obs
            for obs in admitted
            if _authenticity_admissible(obs)
            and obs.get("access_level") in levels
            and obs.get("literal_polarity") == "supports"
            and claim["id"] in (obs.get("literal_claims") or [])
            and (not required or required.issubset(set(obs.get("observation_types") or [])))
            and not _decision_only(obs)
        ]
        refute = [
            obs
            for obs in admitted
            if _authenticity_admissible(obs)
            and obs.get("access_level") in levels
            and obs.get("literal_polarity") == "refutes"
            and claim["id"] in (obs.get("literal_claims") or [])
            and (not required or required.issubset(set(obs.get("observation_types") or [])))
            and not _decision_only(obs)
        ]
        support_status = _evidence_status(support)
        refute_status = _evidence_status(refute)
        if support and not refute and support_status == "authentic":
            if _upgrade_blocked(
                claim,
                applicable,
                admitted,
                support_ids={obs["id"] for obs in support},
            ):
                return _finish(
                    "unresolved",
                    "a blocks_upgrade slot on a record this audit holds is not the verifying observation",
                    claim,
                    admitted,
                    withheld,
                    evidence_status="missing",
                )
            return _finish(
                "supported",
                "verifying record supports the claim and no admitted record refutes it",
                claim,
                admitted,
                withheld,
                evidence_status=support_status,
            )
        if refute and not support and refute_status == "authentic":
            return _finish(
                "refuted",
                "verifying record refutes the claim",
                claim,
                admitted,
                withheld,
                evidence_status=refute_status,
            )
        return _finish(
            "unresolved",
            "no uncontradicted verifying record; narration, a decision, a copy, a stale row, or a misbinding does not decide a world effect",
            claim,
            admitted,
            withheld,
            evidence_status="missing",
        )

    if kind == "evidentiary_sufficiency":
        covering = [
            obs
            for obs in admitted
            if _authenticity_admissible(obs)
            and not _decision_only(obs)
        ]
        # A decision-only row can still sit in the packet. It does not cover
        # a broader property, and it is not dropped from `admitted` above
        # when the claim needs to see that the local control was the only row.
        tags: set[str] = set()
        for obs in covering:
            tags.update(obs.get("observation_types") or [])
        if required and not required.issubset(tags):
            return _finish(
                "unresolved",
                "required observation types are absent; a narrower control does not establish the broader claim",
                claim,
                admitted,
                withheld,
                evidence_status="missing",
            )
        refuting = [
            obs
            for obs in covering
            if obs.get("literal_polarity") == "refutes"
            and claim["id"] in (obs.get("literal_claims") or [])
        ]
        refute_status = _evidence_status(refuting)
        if (
            refuting
            and claim.get("public_text_may_refute_sufficiency")
            and refute_status == "authentic"
        ):
            return _finish(
                "refuted",
                "an admitted record contradicts the sufficiency upgrade",
                claim,
                admitted,
                withheld,
                evidence_status=refute_status,
            )
        return _finish(
            "unresolved",
            "sufficiency claim is not verified by the admitted records",
            claim,
            admitted,
            withheld,
            evidence_status="missing",
        )

    raise ValueError(f"unknown claim kind {kind!r}")
