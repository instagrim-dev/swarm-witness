"""Formal epistemic semantics for Swarm Witness conclusion discipline.

Definitions (see ``analysis/taxonomy_formalization/RESEARCH_NOTE.md``):

* Worlds ``W`` carry ground-truth grant, mechanism decision, and effect.
* An observation ``o`` is a partial channel map plus authenticity flags.
* Compatible set ``Γ(o; W, T)`` is the worlds consistent with ``o`` under
  trust assumptions ``T``.
* Epistemic status of proposition ``P`` given ``Γ`` is support / refute /
  unresolved (including empty ``Γ`` and conflicting worlds).
* ``failed_enforcement`` is *not* an epistemic projection alone: it is a
  property-/boundary-specific diagnosis that additionally requires authentic
  observations plus verified decision/effect channels that make ``Γ``
  refute the stated property ``P``. Classical-null mismatch alone must not
  forge ``supported`` / ``failed_enforcement`` for an arbitrary ``P``.
* Comparison disagreement is a separate failure origin
  (``comparison_equality``); it must not be identified with enforcement failure.

This module is the formal oracle. It must not call production classifiers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

GrantState = Literal["active", "revoked"]
Decision = Literal["allow", "deny"]
EpistemicStatus = Literal["support", "refute", "unresolved"]
ThreeWayClass = Literal[
    "missing_evidence",
    "failed_enforcement",
    "supported",
    "comparison_divergent",
]
EvidenceStatus = Literal["missing", "unverified", "authentic", "misbound"]
DecisionStatus = Literal["correct", "incorrect", "unknown"]
EffectStatus = Literal["committed", "prevented", "unobserved", "not_applicable"]
FailureOrigin = Literal[
    "none",
    "evidence",
    "decision_policy",
    "effect_boundary",
    "comparison_equality",
    "undetermined",
]

Property = Callable[["World"], bool]


@dataclass(frozen=True)
class World:
    """A possible world: ground truth grant, mechanism decision, committed effect."""

    world_id: str
    grant: GrantState
    decision: Decision
    effect_committed: bool
    # Optional labels for multi-arm / multi-implementation models.
    implementation_id: str = "default"


@dataclass(frozen=True)
class Observation:
    """Partial observation available to the auditor.

    ``observed_grant`` may be ``None`` (incomplete). ``authentic`` is the
    auditor's *verified* authenticity judgment for that grant channel:
    ``True`` means independently verified to match ground truth at observation
    time; ``False`` means known-false / misbound; ``None`` means unverified
    (availability without authenticity).
    """

    observed_grant: GrantState | None = None
    authentic: bool | None = None
    irrelevant_fact: str | None = None
    decision_observed: Decision | None = None
    effect_observed: bool | None = None


@dataclass(frozen=True)
class ArmObservation:
    """One arm of a matched classical↔implementation comparison.

    ``grant`` and ``effect_committed`` are optional boundary evidence.
    A failed ``property_holds`` flag does not by itself establish
    ``decision_status`` or ``failure_origin``; those axes are filled only
    when this evidence determines them (a correct deny under revoked
    authority can still commit an unauthorized effect).
    """

    arm_id: str
    decision: Decision
    property_holds: bool
    evidence_complete: bool = True
    grant: GrantState | None = None
    effect_committed: bool | None = None


@dataclass(frozen=True)
class TrustAssumptions:
    """Assumptions under which compatibility and diagnoses are scored."""

    require_verified_authenticity: bool = True
    treat_irrelevant_as_non_discriminating: bool = True
    # When True, a known-misbound observation yields empty Γ (no world is
    # compatible with a verified-false channel reading).
    empty_gamma_on_known_misbind: bool = True


@dataclass(frozen=True)
class EvaluationObject:
    """Stated evaluation object for mutual exclusivity / exhaustiveness.

    Three-way classes are mutually exclusive and exhaustive **for a single
    mechanism-evaluation object** whose proposition is a property of one
    mechanism under one observation package. Matched equality propositions
    and evidence-validity propositions are distinct evaluation objects and
    may require separate coordinates (typed product).
    """

    kind: Literal["mechanism_property", "matched_equality", "evidence_validity"]
    proposition_name: str


@dataclass(frozen=True)
class FormalDiagnosis:
    """Typed product: epistemic status × failure origin × decision/effect."""

    epistemic_status: EpistemicStatus
    evidence_status: EvidenceStatus
    decision_status: DecisionStatus
    effect_status: EffectStatus
    failure_origin: FailureOrigin
    gamma_size: int
    three_way: ThreeWayClass
    projection_lossy: bool
    reason: str


def required_decision(grant: GrantState) -> Decision:
    """Classical null: active → allow; revoked → deny."""
    if grant == "active":
        return "allow"
    if grant == "revoked":
        return "deny"
    raise ValueError(f"unknown grant: {grant!r}")


def decision_correct_property(world: World) -> bool:
    """P_dec: mechanism decision matches classical null for the world's grant."""
    return world.decision == required_decision(world.grant)


def no_unauthorized_effect_property(world: World) -> bool:
    """P_eff: no effect is committed when the decision should have been deny."""
    if required_decision(world.grant) == "deny":
        return not world.effect_committed
    return True


def compatible_worlds(
    worlds: frozenset[World],
    observation: Observation,
    trust: TrustAssumptions | None = None,
) -> frozenset[World]:
    """Γ(o; W, T): worlds compatible with observation under trust assumptions."""
    t = trust or TrustAssumptions()
    if observation.observed_grant is None:
        # Incomplete grant channel: under T₀ a decision/effect reading is not
        # an authenticated binding without a grant anchor, so Γ stays W
        # (irrelevant facts ignored; decision/effect filters do not apply).
        return frozenset(worlds)

    if observation.authentic is False:
        # Known-false channel reading: under default trust, no world is
        # compatible with a verified misbind of the grant channel.
        if t.empty_gamma_on_known_misbind:
            return frozenset()
        # Alternative trust: keep worlds whose grant equals the (false) reading
        # — models an auditor who treats the channel as truthful despite a
        # known misbind flag (unsafe; used only as a counterexample trust).
        return frozenset(w for w in worlds if w.grant == observation.observed_grant)

    if t.require_verified_authenticity and observation.authentic is not True:
        # Available but unverified: do not shrink Γ by the grant reading.
        return frozenset(worlds)

    # Verified-authentic grant observation: keep worlds matching the reading.
    gamma = {w for w in worlds if w.grant == observation.observed_grant}
    if observation.decision_observed is not None:
        gamma = {w for w in gamma if w.decision == observation.decision_observed}
    if observation.effect_observed is not None:
        gamma = {
            w for w in gamma if w.effect_committed == observation.effect_observed
        }
    return frozenset(gamma)


def epistemic_status(prop: Property, gamma: frozenset[World]) -> EpistemicStatus:
    """Support / refute / unresolved for P given compatible worlds Γ."""
    if not gamma:
        return "unresolved"
    values = {bool(prop(w)) for w in gamma}
    if values == {True}:
        return "support"
    if values == {False}:
        return "refute"
    return "unresolved"


def _evidence_status(observation: Observation) -> EvidenceStatus:
    if observation.observed_grant is None:
        return "missing"
    if observation.authentic is False:
        return "misbound"
    if observation.authentic is True:
        return "authentic"
    return "unverified"


def _effect_status(
    observation: Observation, *, decision: Decision | None
) -> EffectStatus:
    if observation.effect_observed is True:
        return "committed"
    if observation.effect_observed is False:
        return "prevented"
    if decision is None or observation.decision_observed is None:
        return "unobserved"
    # Decision observed but effect channel not in scope.
    return "not_applicable"


def diagnose(
    worlds: frozenset[World],
    observation: Observation,
    prop: Property,
    *,
    trust: TrustAssumptions | None = None,
    evaluation: EvaluationObject | None = None,
) -> FormalDiagnosis:
    """Full typed diagnosis; ``three_way`` is a documented projection."""
    t = trust or TrustAssumptions()
    evaluation = evaluation or EvaluationObject(
        kind="mechanism_property",
        proposition_name="decision_correct",
    )
    if evaluation.kind == "matched_equality":
        # A single Observation has no paired arms. Emitting comparison_divergent
        # here scores a definite equality finding from missing evidence
        # (including Observation()). Callers with pairs use
        # diagnose_matched_comparison(); incomplete pairs return missing_evidence.
        raise ValueError(
            "matched_equality cannot be diagnosed from one Observation; "
            "call diagnose_matched_comparison() with the paired arm "
            "observations, or leave those arms incomplete until the pair exists"
        )
    gamma = compatible_worlds(worlds, observation, t)
    status = epistemic_status(prop, gamma)
    ev = _evidence_status(observation)
    decision_obs = observation.decision_observed
    eff = _effect_status(observation, decision=decision_obs)

    # Decision status relative to classical null, only when authentic grant
    # and a decision observation are both present.
    if ev == "authentic" and decision_obs is not None and observation.observed_grant:
        required = required_decision(observation.observed_grant)
        dec_status: DecisionStatus = (
            "correct" if decision_obs == required else "incorrect"
        )
    else:
        dec_status = "unknown"

    failure_origin: FailureOrigin = "none"
    three_way: ThreeWayClass
    projection_lossy = False
    reason: str

    if ev == "missing" or (t.require_verified_authenticity and ev == "unverified"):
        three_way = "missing_evidence"
        reason = (
            "discriminating grant observation absent or unverified; "
            f"Γ size={len(gamma)}; epistemic_status={status}"
        )
        return FormalDiagnosis(
            # Keep the true epistemic projection of P on Γ; missing evidence
            # gates the three-way label without forging epistemic_status.
            epistemic_status=status,
            evidence_status=ev if ev != "unverified" else "unverified",
            decision_status="unknown",
            effect_status=eff,
            failure_origin="none",
            gamma_size=len(gamma),
            three_way=three_way,
            projection_lossy=False,
            reason=reason,
        )

    if ev == "misbound":
        # Evidence validity failure. High-level three-way projection is
        # necessarily lossy: validity ≠ enforcement.
        failure_origin = "evidence"
        projection_lossy = True
        if not gamma:
            three_way = "missing_evidence"
            reason = (
                "known-misbound observation → empty Γ under trust; "
                "evidence invalidity, not enforcement failure "
                "(failure_origin=evidence)"
            )
            return FormalDiagnosis(
                epistemic_status="unresolved",
                evidence_status="misbound",
                decision_status="unknown",
                effect_status=eff,
                failure_origin=failure_origin,
                gamma_size=0,
                three_way=three_way,
                projection_lossy=projection_lossy,
                reason=reason,
            )
        # Unsafe trust kept nonempty Γ; still do not emit supported.
        three_way = "missing_evidence"
        reason = (
            "misbound observation under non-default trust; refuse support "
            "(failure_origin=evidence)"
        )
        return FormalDiagnosis(
            epistemic_status=status,
            evidence_status="misbound",
            decision_status=dec_status,
            effect_status=eff,
            failure_origin=failure_origin,
            gamma_size=len(gamma),
            three_way=three_way,
            projection_lossy=projection_lossy,
            reason=reason,
        )

    # Authentic evidence path.
    if decision_obs is None and observation.effect_observed is None:
        # Authentic grant but no verified decision/effect evidence: may
        # epistemically support/refute a proposition that is already decided
        # by the grant channel alone, but cannot diagnose failed_enforcement.
        if status == "support":
            three_way = "supported"
            reason = (
                "authentic observation; Γ unanimous for P; "
                "no decision/effect channel"
            )
        elif status == "refute":
            three_way = "missing_evidence"
            projection_lossy = True
            failure_origin = "undetermined"
            reason = (
                "authentic observation refutes P on Γ, but verified decision/"
                "effect evidence absent — refuse failed_enforcement diagnosis"
            )
        else:
            three_way = "missing_evidence"
            reason = "authentic observation but Γ conflicting or empty for P"
        return FormalDiagnosis(
            epistemic_status=status,
            evidence_status="authentic",
            decision_status="unknown",
            effect_status=eff,
            failure_origin=failure_origin,
            gamma_size=len(gamma),
            three_way=three_way,
            projection_lossy=projection_lossy,
            reason=reason,
        )

    # Authentic + verified decision and/or effect evidence.
    # three_way follows the true epistemic projection of P on Γ — never the
    # classical-null decision alone. Classical mismatch is recorded on
    # decision_status / failure_origin without forging epistemic_status.
    if status == "support":
        three_way = "supported"
        # Three-way is lossy when classical channels record a problem that this
        # P does not care about (retained on decision_status / effect_status).
        unauthorized_effect = (
            observation.observed_grant is not None
            and observation.effect_observed is True
            and required_decision(observation.observed_grant) == "deny"
        )
        projection_lossy = dec_status == "incorrect" or unauthorized_effect
        reason = (
            "authentic evidence; Γ nonempty and unanimous for P "
            f"(decision_status={dec_status}; effect_status={eff}"
            f"{'; projection_lossy' if projection_lossy else ''})"
        )
        return FormalDiagnosis(
            epistemic_status=status,
            evidence_status="authentic",
            decision_status=dec_status,
            effect_status=eff,
            failure_origin="none",
            gamma_size=len(gamma),
            three_way=three_way,
            projection_lossy=projection_lossy,
            reason=reason,
        )

    if status == "refute":
        failure_origin = "undetermined"
        if (
            observation.observed_grant is not None
            and observation.effect_observed is True
            and required_decision(observation.observed_grant) == "deny"
        ):
            failure_origin = "effect_boundary"
        elif dec_status == "incorrect":
            failure_origin = "decision_policy"
        three_way = "failed_enforcement"
        reason = (
            "authentic evidence; Γ nonempty and unanimously falsifies P "
            f"(failure_origin={failure_origin}; effect_status={eff})"
        )
        return FormalDiagnosis(
            epistemic_status=status,
            evidence_status="authentic",
            decision_status=dec_status,
            effect_status=eff,
            failure_origin=failure_origin,
            gamma_size=len(gamma),
            three_way=three_way,
            projection_lossy=False,
            reason=reason,
        )

    # unresolved under authentic decision/effect evidence: need more
    # discriminating channels (e.g. effect) or P is not decided on Γ.
    three_way = "missing_evidence"
    reason = (
        "authentic decision/effect path inconclusive for stated P "
        f"(epistemic_status={status}; decision_status={dec_status})"
    )
    return FormalDiagnosis(
        epistemic_status=status,
        evidence_status="authentic",
        decision_status=dec_status,
        effect_status=eff,
        failure_origin="undetermined",
        gamma_size=len(gamma),
        three_way=three_way,
        projection_lossy=True,
        reason=reason,
    )


def _decision_status_from_arms(
    left: ArmObservation, right: ArmObservation
) -> DecisionStatus:
    """Classical decision status only when arm grants establish it.

    ``incorrect`` if either arm's grant shows a decision other than δ*.
    ``correct`` only when both arms carry grants and both match δ*.
    Otherwise ``unknown`` — agreement plus a failed property does not say
    which decision was wrong.
    """
    saw_incorrect = False
    confirmed = 0
    for arm in (left, right):
        if arm.grant is None:
            continue
        confirmed += 1
        if arm.decision != required_decision(arm.grant):
            saw_incorrect = True
    if saw_incorrect:
        return "incorrect"
    if confirmed == 2:
        return "correct"
    return "unknown"


def _effect_status_from_arms(
    left: ArmObservation, right: ArmObservation
) -> EffectStatus:
    """Effect status from carried boundary evidence, never assumed absent."""
    effects = (left.effect_committed, right.effect_committed)
    if any(effect is True for effect in effects):
        return "committed"
    if all(effect is False for effect in effects):
        return "prevented"
    return "unobserved"


def _unauthorized_committed_effect(arm: ArmObservation) -> bool:
    """Deny-required grant with a committed effect on this arm."""
    return (
        arm.grant is not None
        and arm.effect_committed is True
        and required_decision(arm.grant) == "deny"
    )


def _origin_when_property_fails(
    left: ArmObservation, right: ArmObservation
) -> FailureOrigin:
    """Attribute property failure only from grant and effect evidence.

    Unauthorized commit under a deny-required grant is ``effect_boundary``
    even when the decision itself matches δ* (two correct denies can still
    commit). A demonstrated decision mismatch is ``decision_policy``.
    Anything else stays ``undetermined``.
    """
    if _unauthorized_committed_effect(left) or _unauthorized_committed_effect(right):
        return "effect_boundary"
    if _decision_status_from_arms(left, right) == "incorrect":
        return "decision_policy"
    return "undetermined"


def diagnose_matched_comparison(
    left: ArmObservation,
    right: ArmObservation,
) -> FormalDiagnosis:
    """Classify a matched equality evaluation object.

    Disagreement refutes equality without diagnosing that either arm failed
    enforcement. Incomplete pairs are missing_evidence. When the arms agree
    and the stated property fails, ``decision_status`` stays ``unknown`` and
    ``failure_origin`` stays ``undetermined`` unless ``grant`` and
    ``effect_committed`` establish them.
    """
    if not left.evidence_complete or not right.evidence_complete:
        return FormalDiagnosis(
            epistemic_status="unresolved",
            evidence_status="missing",
            decision_status="unknown",
            effect_status="unobserved",
            failure_origin="none",
            gamma_size=0,
            three_way="missing_evidence",
            projection_lossy=False,
            reason="matched comparison incomplete — missing_evidence",
        )
    if left.decision != right.decision:
        return FormalDiagnosis(
            epistemic_status="refute",
            evidence_status="authentic",
            decision_status="unknown",
            effect_status="not_applicable",
            failure_origin="comparison_equality",
            gamma_size=2,
            three_way="comparison_divergent",
            projection_lossy=True,
            reason=(
                "cross-arm equality refuted; not a diagnosis that either "
                "authorization mechanism failed enforcement "
                "(failure_origin=comparison_equality)"
            ),
        )
    # Arms agree on decision. Property success is a separate conjunct.
    both_hold = left.property_holds and right.property_holds
    if both_hold:
        return FormalDiagnosis(
            epistemic_status="support",
            evidence_status="authentic",
            decision_status="correct",
            effect_status="not_applicable",
            failure_origin="none",
            gamma_size=2,
            three_way="supported",
            projection_lossy=False,
            reason="arms agree and both satisfy the claim success criterion",
        )
    decision_status = _decision_status_from_arms(left, right)
    effect_status = _effect_status_from_arms(left, right)
    failure_origin = _origin_when_property_fails(left, right)
    if failure_origin == "effect_boundary":
        reason = (
            "arms agree; boundary evidence shows an unauthorized committed "
            "effect under deny-required authority "
            f"(decision_status={decision_status}; effect_status={effect_status})"
        )
    elif failure_origin == "decision_policy":
        reason = (
            "arms agree; grant evidence shows a decision other than δ* "
            f"(decision_status={decision_status}; effect_status={effect_status})"
        )
    else:
        reason = (
            "arms agree and the stated property fails on at least one arm; "
            "grant/effect evidence does not establish decision_status or "
            f"failure_origin (decision_status={decision_status}; "
            f"effect_status={effect_status})"
        )
    return FormalDiagnosis(
        epistemic_status="refute",
        evidence_status="authentic",
        decision_status=decision_status,
        effect_status=effect_status,
        failure_origin=failure_origin,
        gamma_size=2,
        three_way="failed_enforcement",
        projection_lossy=failure_origin == "undetermined",
        reason=reason,
    )


def project_three_way(diagnosis: FormalDiagnosis) -> ThreeWayClass:
    """Projection π: typed diagnosis → three-way / four-way class label."""
    return diagnosis.three_way
