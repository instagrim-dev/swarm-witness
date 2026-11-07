"""Executable finite-model checks for formal epistemic invariants.

The checker enumerates a small permission world set and verifies theorems by
exhaustion. It does **not** call ``swarm_witness.conclusion_classes``; the
formal definitions in ``epistemic_model`` are the oracle.

Finite-model limits (documented):
* Grant domain size 2 (active/revoked).
* Decision domain size 2 (allow/deny).
* Effect boolean.
* At most two named implementations for comparison counterexamples.
* No continuous time, concurrency interleavings, or cryptographic adversary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from swarm_witness.formal.epistemic_model import (
    ArmObservation,
    FormalDiagnosis,
    Observation,
    TrustAssumptions,
    World,
    compatible_worlds,
    decision_correct_property,
    diagnose,
    diagnose_matched_comparison,
    epistemic_status,
    no_unauthorized_effect_property,
    required_decision,
)


@dataclass(frozen=True)
class FiniteModelReport:
    passed: bool
    world_count: int
    theorem_results: dict[str, bool]
    counterexamples: list[dict[str, Any]]
    errors: list[str]
    limits: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


FINITE_MODEL_LIMITS = [
    "grant ∈ {active, revoked}",
    "decision ∈ {allow, deny}",
    "effect_committed ∈ {false, true}",
    "≤2 implementation arms in comparison models",
    "no concurrent interleavings (see issue #10)",
    "no cryptographic authenticity adversary beyond a misbind flag",
]


def enumerate_permission_worlds() -> frozenset[World]:
    """Cartesian product of grant × decision × effect for one mechanism."""
    worlds: set[World] = set()
    for grant in ("active", "revoked"):
        for decision in ("allow", "deny"):
            for effect in (False, True):
                wid = f"{grant}:{decision}:{'eff' if effect else 'noeff'}"
                worlds.add(
                    World(
                        world_id=wid,
                        grant=grant,  # type: ignore[arg-type]
                        decision=decision,  # type: ignore[arg-type]
                        effect_committed=effect,
                    )
                )
    return frozenset(worlds)


def _obs(
    *,
    grant: str | None = None,
    authentic: bool | None = None,
    decision: str | None = None,
    effect: bool | None = None,
    irrelevant: str | None = None,
) -> Observation:
    return Observation(
        observed_grant=grant,  # type: ignore[arg-type]
        authentic=authentic,
        decision_observed=decision,  # type: ignore[arg-type]
        effect_observed=effect,
        irrelevant_fact=irrelevant,
    )


def _observation_space() -> list[Observation]:
    """Finite observation fragment used for exhaustive invariant checks."""
    obs: list[Observation] = [_obs(), _obs(irrelevant="receipt_print_color=blue")]
    for grant in ("active", "revoked"):
        for authentic in (True, False, None):
            obs.append(_obs(grant=grant, authentic=authentic))
            for decision in ("allow", "deny"):
                obs.append(_obs(grant=grant, authentic=authentic, decision=decision))
                for effect in (False, True):
                    obs.append(
                        _obs(
                            grant=grant,
                            authentic=authentic,
                            decision=decision,
                            effect=effect,
                        )
                    )
            for effect in (False, True):
                obs.append(_obs(grant=grant, authentic=authentic, effect=effect))
    return obs


def theorem_support_soundness(worlds: frozenset[World]) -> tuple[bool, list[str]]:
    """T1: supported ⇒ Γ≠∅ ∧ ∀w∈Γ. P(w), and diagnosis.epistemic_status matches
    the independent epistemic_status(P, Γ). Checked for P_dec and P_eff over the
    finite observation fragment — not merely for classical-null agreement.
    """
    errors: list[str] = []
    props = (
        ("P_dec", decision_correct_property),
        ("P_eff", no_unauthorized_effect_property),
    )
    for o in _observation_space():
        for prop_name, prop in props:
            gamma = compatible_worlds(worlds, o)
            independent = epistemic_status(prop, gamma)
            d = diagnose(worlds, o, prop)
            if d.epistemic_status != independent:
                errors.append(
                    f"{prop_name}: forged epistemic_status={d.epistemic_status!r} "
                    f"≠ independent {independent!r} for {o}"
                )
            if d.three_way != "supported":
                continue
            if not gamma:
                errors.append(f"{prop_name}: supported with empty Γ for {o}")
                continue
            if not all(prop(w) for w in gamma):
                errors.append(
                    f"{prop_name}: supported but Γ contains P-violators for {o}"
                )
            if independent != "support":
                errors.append(
                    f"{prop_name}: supported while independent status="
                    f"{independent!r} for {o}"
                )
            # For P_dec with a verified decision, classical null must agree.
            if (
                prop_name == "P_dec"
                and o.authentic is True
                and o.observed_grant is not None
                and o.decision_observed is not None
                and o.decision_observed
                != required_decision(o.observed_grant)
            ):
                errors.append(
                    f"P_dec supported despite decision "
                    f"{o.decision_observed} ≠ required for {o.observed_grant}"
                )
    return not errors, errors


def theorem_refutation_soundness(worlds: frozenset[World]) -> tuple[bool, list[str]]:
    """T2: failed_enforcement only under authentic evidence when Γ unanimously
    falsifies P; never from incomplete/misbound alone under default trust.
    Unauthorized effect under a *correct* deny is effect_boundary.
    """
    errors: list[str] = []
    props = (
        ("P_dec", decision_correct_property),
        ("P_eff", no_unauthorized_effect_property),
    )

    # Incomplete must not yield failed_enforcement.
    d_blind = diagnose(worlds, _obs(), decision_correct_property)
    if d_blind.three_way == "failed_enforcement":
        errors.append("blind observation yielded failed_enforcement")

    # Misbound under default trust → missing_evidence, failure_origin=evidence.
    d_mis = diagnose(
        worlds,
        _obs(grant="active", authentic=False, decision="allow"),
        decision_correct_property,
    )
    if d_mis.three_way == "failed_enforcement":
        errors.append("misbound observation yielded failed_enforcement")
    if d_mis.failure_origin != "evidence":
        errors.append(f"misbound failure_origin={d_mis.failure_origin!r} want evidence")

    # Authentic + wrong decision → failed_enforcement for P_dec.
    d_bad = diagnose(
        worlds,
        _obs(grant="revoked", authentic=True, decision="allow"),
        decision_correct_property,
    )
    if d_bad.three_way != "failed_enforcement":
        errors.append(
            f"authentic revoked+allow → {d_bad.three_way}, want failed_enforcement"
        )
    if d_bad.failure_origin != "decision_policy":
        errors.append(
            f"authentic wrong decision origin={d_bad.failure_origin!r} "
            "want decision_policy"
        )

    # Unauthorized effect under *correct* deny → effect_boundary (not supported).
    d_eff_deny = diagnose(
        worlds,
        _obs(
            grant="revoked",
            authentic=True,
            decision="deny",
            effect=True,
        ),
        no_unauthorized_effect_property,
    )
    if d_eff_deny.three_way != "failed_enforcement":
        errors.append(
            f"deny+committed effect → {d_eff_deny.three_way}, "
            "want failed_enforcement"
        )
    if d_eff_deny.failure_origin != "effect_boundary":
        errors.append(
            f"deny+committed effect origin={d_eff_deny.failure_origin!r} "
            "want effect_boundary"
        )
    if d_eff_deny.epistemic_status != "refute":
        errors.append(
            f"deny+committed effect epistemic_status="
            f"{d_eff_deny.epistemic_status!r} want refute"
        )

    # Wrong decision + committed effect under deny → still effect_boundary.
    d_eff = diagnose(
        worlds,
        _obs(
            grant="revoked",
            authentic=True,
            decision="allow",
            effect=True,
        ),
        no_unauthorized_effect_property,
    )
    if d_eff.failure_origin != "effect_boundary":
        errors.append(
            f"committed unauthorized effect origin={d_eff.failure_origin!r} "
            "want effect_boundary"
        )

    # Exhaustive: failed_enforcement ⇒ authentic ∧ Γ⊭P (independent check).
    for o in _observation_space():
        for prop_name, prop in props:
            d = diagnose(worlds, o, prop)
            if d.three_way != "failed_enforcement":
                continue
            if d.evidence_status != "authentic":
                errors.append(
                    f"{prop_name}: failed_enforcement with evidence_status="
                    f"{d.evidence_status!r} for {o}"
                )
            gamma = compatible_worlds(worlds, o)
            independent = epistemic_status(prop, gamma)
            if independent != "refute":
                errors.append(
                    f"{prop_name}: failed_enforcement while independent status="
                    f"{independent!r} for {o}"
                )
            if d.epistemic_status != independent:
                errors.append(
                    f"{prop_name}: forged epistemic_status on refute path for {o}"
                )
    return not errors, errors


def theorem_indistinguishability(worlds: frozenset[World]) -> tuple[bool, list[str]]:
    """T3: if two worlds agree on all observed channels, Γ cannot separate them;
    when they disagree on P, epistemic status must be unresolved under that o.
    """
    errors: list[str] = []
    # Blind observation: active-correct and revoked-correct both compatible.
    o = _obs()
    gamma = compatible_worlds(worlds, o)
    active_ok = next(
        w
        for w in gamma
        if w.grant == "active" and decision_correct_property(w) and not w.effect_committed
    )
    revoked_ok = next(
        w
        for w in gamma
        if w.grant == "revoked" and decision_correct_property(w) and not w.effect_committed
    )
    if active_ok not in gamma or revoked_ok not in gamma:
        errors.append("blind Γ missing canonical active/revoked worlds")
    status = epistemic_status(decision_correct_property, gamma)
    # Under blind o, Γ contains both correct and incorrect decision worlds.
    if status != "unresolved":
        # Actually decision_correct is True on some and False on others → unresolved.
        errors.append(f"blind epistemic_status={status!r} want unresolved")
    d = diagnose(worlds, o, decision_correct_property)
    if d.three_way != "missing_evidence":
        errors.append(f"blind three_way={d.three_way!r} want missing_evidence")
    return not errors, errors


def theorem_non_upgrade(worlds: frozenset[World]) -> tuple[bool, list[str]]:
    """T4: irrelevant facts do not upgrade missing_evidence."""
    errors: list[str] = []
    blind = diagnose(worlds, _obs(), decision_correct_property)
    irrelevant = diagnose(
        worlds,
        _obs(irrelevant="receipt_print_color=blue"),
        decision_correct_property,
    )
    if blind.three_way != "missing_evidence":
        errors.append("baseline blind not missing_evidence")
    if irrelevant.three_way != "missing_evidence":
        errors.append("irrelevant fact upgraded three_way away from missing_evidence")
    if irrelevant.gamma_size != blind.gamma_size:
        errors.append("irrelevant fact changed Γ size")
    return not errors, errors


def theorem_monotonic_refinement(worlds: frozenset[World]) -> tuple[bool, list[str]]:
    """T5: adding a verified informative observation shrinks Γ (⊆);
    conclusions may upgrade only when Γ becomes unanimous under verified o.
    """
    errors: list[str] = []
    o0 = _obs()
    g0 = compatible_worlds(worlds, o0)
    o1 = _obs(grant="active", authentic=True)
    g1 = compatible_worlds(worlds, o1)
    if not g1 <= g0:
        errors.append("verified grant observation expanded Γ")
    o2 = _obs(grant="active", authentic=True, decision="allow")
    g2 = compatible_worlds(worlds, o2)
    if not g2 <= g1:
        errors.append("verified decision observation expanded Γ")

    # Unverified grant reading must not shrink Γ under default trust.
    o_u = _obs(grant="active", authentic=None)
    g_u = compatible_worlds(worlds, o_u)
    if g_u != g0:
        errors.append("unverified grant reading changed Γ under default trust")

    d0 = diagnose(worlds, o0, decision_correct_property)
    d2 = diagnose(worlds, o2, decision_correct_property)
    if d0.three_way != "missing_evidence":
        errors.append("pre-refinement not missing_evidence")
    if d2.three_way != "supported":
        errors.append("post-refinement active+allow not supported")
    return not errors, errors


def theorem_mutual_exclusivity_mechanism() -> tuple[bool, list[str]]:
    """T6: for a single mechanism_property evaluation, projected classes are
    mutually exclusive and jointly cover the finite observation fragment.
    ``comparison_divergent`` is reserved for matched_equality objects.
    """
    errors: list[str] = []
    worlds = enumerate_permission_worlds()
    allowed = {"missing_evidence", "failed_enforcement", "supported"}
    seen: set[str] = set()
    for o in _observation_space():
        for prop in (decision_correct_property, no_unauthorized_effect_property):
            d = diagnose(worlds, o, prop)
            if d.three_way not in allowed:
                errors.append(
                    f"mechanism_property emitted {d.three_way!r} outside {allowed}"
                )
            # Exclusivity: a single diagnosis carries exactly one projected label
            # (enforced by the type); check the label is a member of the partition.
            labels_on_row = {
                cls
                for cls in allowed
                if cls == d.three_way
            }
            if len(labels_on_row) != 1:
                errors.append(
                    f"projected label not unique for {o}: {labels_on_row}"
                )
            seen.add(d.three_way)
            if d.three_way == "comparison_divergent":
                errors.append("mechanism_property emitted comparison_divergent")
    if not allowed <= seen:
        errors.append(f"mechanism suite incomplete: missing {allowed - seen}")
    return not errors, errors


def run_counterexample_suite(worlds: frozenset[World] | None = None) -> list[dict[str, Any]]:
    """Explicit countermodels required by issue #12 acceptance criteria."""
    worlds = worlds or enumerate_permission_worlds()
    out: list[dict[str, Any]] = []

    # C1: known-false observation must not yield unwarranted supported.
    d_false = diagnose(
        worlds,
        _obs(grant="revoked", authentic=False, decision="deny"),
        decision_correct_property,
    )
    out.append(
        {
            "id": "C1_known_false_observation",
            "description": (
                "Misbound grant observation with a decision that happens to "
                "match classical null for the *false* reading"
            ),
            "three_way": d_false.three_way,
            "failure_origin": d_false.failure_origin,
            "evidence_status": d_false.evidence_status,
            "passed": (
                d_false.three_way != "supported"
                and d_false.failure_origin == "evidence"
                and d_false.evidence_status == "misbound"
            ),
            "reason": d_false.reason,
        }
    )

    # C2: incomplete observation → missing_evidence; A/B indistinguishable.
    d_inc = diagnose(worlds, _obs(), decision_correct_property)
    g_inc = compatible_worlds(worlds, _obs())
    grants = {w.grant for w in g_inc}
    out.append(
        {
            "id": "C2_incomplete_observation",
            "description": "Blind observation leaves active and revoked compatible",
            "three_way": d_inc.three_way,
            "compatible_grants": sorted(grants),
            "passed": (
                d_inc.three_way == "missing_evidence"
                and grants == {"active", "revoked"}
            ),
            "reason": d_inc.reason,
        }
    )

    # C3: correct-but-different implementations → comparison_divergent, not
    # failed_enforcement.
    left = ArmObservation(
        arm_id="classical",
        decision="allow",
        property_holds=True,
        evidence_complete=True,
    )
    right = ArmObservation(
        arm_id="alt_correct",
        decision="deny",  # different disposition
        property_holds=True,  # still satisfies *its* stated local criterion
        evidence_complete=True,
    )
    d_cmp = diagnose_matched_comparison(left, right)
    out.append(
        {
            "id": "C3_correct_but_different_implementations",
            "description": (
                "Two complete arms disagree on disposition while each reports "
                "local property success — equality refuted, not enforcement failure"
            ),
            "three_way": d_cmp.three_way,
            "failure_origin": d_cmp.failure_origin,
            "passed": (
                d_cmp.three_way == "comparison_divergent"
                and d_cmp.failure_origin == "comparison_equality"
                and d_cmp.three_way != "failed_enforcement"
            ),
            "reason": d_cmp.reason,
        }
    )

    # C4 (bonus): collapsing comparison into failed_enforcement loses causal info.
    # Demonstrated by showing the typed product retains comparison_equality
    # while a naive three-way-only encoding would have to reuse contradicted.
    out.append(
        {
            "id": "C4_three_way_lossy_for_orthogonal_diagnoses",
            "description": (
                "Epistemic status × failure_origin × decision/effect are needed; "
                "comparison_divergent and evidence-misbind both refute 'supported' "
                "but differ in origin"
            ),
            "diagnoses": [
                {
                    "case": "comparison",
                    "failure_origin": d_cmp.failure_origin,
                    "three_way": d_cmp.three_way,
                },
                {
                    "case": "misbind",
                    "failure_origin": d_false.failure_origin,
                    "three_way": d_false.three_way,
                },
            ],
            "passed": (
                d_cmp.failure_origin != d_false.failure_origin
                and d_cmp.three_way != d_false.three_way
            ),
            "reason": (
                "orthogonal origins retained only in the typed product; "
                "a single three-way label cannot carry both"
            ),
        }
    )

    # C5: correct deny without effect channel must not support P_eff (Γ mixed).
    d_peff_mixed = diagnose(
        worlds,
        _obs(grant="revoked", authentic=True, decision="deny"),
        no_unauthorized_effect_property,
    )
    g_peff_mixed = compatible_worlds(
        worlds, _obs(grant="revoked", authentic=True, decision="deny")
    )
    out.append(
        {
            "id": "C5_correct_decision_does_not_forge_P_eff_support",
            "description": (
                "Authentic revoked+deny without effect observation leaves "
                "P_eff unresolved on Γ — must not emit supported"
            ),
            "three_way": d_peff_mixed.three_way,
            "epistemic_status": d_peff_mixed.epistemic_status,
            "gamma_P_eff": sorted(
                {no_unauthorized_effect_property(w) for w in g_peff_mixed}
            ),
            "passed": (
                d_peff_mixed.three_way != "supported"
                and d_peff_mixed.epistemic_status == "unresolved"
                and d_peff_mixed.epistemic_status
                == epistemic_status(
                    no_unauthorized_effect_property, g_peff_mixed
                )
            ),
            "reason": d_peff_mixed.reason,
        }
    )

    # C6: unauthorized effect under correct deny is failed_enforcement for P_eff.
    o_deny_eff = _obs(
        grant="revoked",
        authentic=True,
        decision="deny",
        effect=True,
    )
    d_peff_eff = diagnose(worlds, o_deny_eff, no_unauthorized_effect_property)
    out.append(
        {
            "id": "C6_unauthorized_effect_under_correct_deny",
            "description": (
                "Authentic revoked+deny+effect=True falsifies P_eff — "
                "failed_enforcement with failure_origin=effect_boundary"
            ),
            "three_way": d_peff_eff.three_way,
            "failure_origin": d_peff_eff.failure_origin,
            "epistemic_status": d_peff_eff.epistemic_status,
            "passed": (
                d_peff_eff.three_way == "failed_enforcement"
                and d_peff_eff.failure_origin == "effect_boundary"
                and d_peff_eff.epistemic_status == "refute"
            ),
            "reason": d_peff_eff.reason,
        }
    )

    # C7: same package under P_dec may be supported; joint P_dec∧P_eff refutes.
    def mechanism_ok(world: World) -> bool:
        return decision_correct_property(world) and no_unauthorized_effect_property(
            world
        )

    d_pdec_eff = diagnose(worlds, o_deny_eff, decision_correct_property)
    d_joint = diagnose(worlds, o_deny_eff, mechanism_ok)
    out.append(
        {
            "id": "C7_P_dec_supported_joint_refutes_unauth_effect",
            "description": (
                "Same revoked+deny+effect package: P_dec can be supported "
                "(lossy) while P_dec∧P_eff is failed_enforcement/effect_boundary"
            ),
            "p_dec_three_way": d_pdec_eff.three_way,
            "p_dec_effect_status": d_pdec_eff.effect_status,
            "p_dec_projection_lossy": d_pdec_eff.projection_lossy,
            "joint_three_way": d_joint.three_way,
            "joint_failure_origin": d_joint.failure_origin,
            "passed": (
                d_pdec_eff.three_way == "supported"
                and d_pdec_eff.effect_status == "committed"
                and d_pdec_eff.projection_lossy is True
                and d_pdec_eff.epistemic_status
                == epistemic_status(
                    decision_correct_property, compatible_worlds(worlds, o_deny_eff)
                )
                and d_joint.three_way == "failed_enforcement"
                and d_joint.failure_origin == "effect_boundary"
            ),
            "reason": d_pdec_eff.reason + " || " + d_joint.reason,
        }
    )
    return out


def check_core_invariants(
    worlds: frozenset[World] | None = None,
) -> FiniteModelReport:
    """Run all finite-model theorem checks and the counterexample suite."""
    worlds = worlds or enumerate_permission_worlds()
    theorem_results: dict[str, bool] = {}
    errors: list[str] = []

    checks = [
        ("T1_support_soundness", theorem_support_soundness),
        ("T2_refutation_soundness", theorem_refutation_soundness),
        ("T3_indistinguishability", theorem_indistinguishability),
        ("T4_non_upgrade", theorem_non_upgrade),
        ("T5_monotonic_refinement", theorem_monotonic_refinement),
    ]
    for name, fn in checks:
        ok, errs = fn(worlds)
        theorem_results[name] = ok
        errors.extend(f"{name}: {e}" for e in errs)

    ok6, errs6 = theorem_mutual_exclusivity_mechanism()
    theorem_results["T6_mutual_exclusivity_mechanism_object"] = ok6
    errors.extend(f"T6_mutual_exclusivity_mechanism_object: {e}" for e in errs6)

    counterexamples = run_counterexample_suite(worlds)
    theorem_results["C_counterexample_suite"] = all(c["passed"] for c in counterexamples)
    for c in counterexamples:
        if not c["passed"]:
            errors.append(f"counterexample {c['id']} failed")

    # Independence guard: this module's import graph must not include
    # conclusion_classes. Enforced in tests; recorded here as a soft note.
    return FiniteModelReport(
        passed=not errors,
        world_count=len(worlds),
        theorem_results=theorem_results,
        counterexamples=counterexamples,
        errors=errors,
        limits=list(FINITE_MODEL_LIMITS),
    )


def diagnosis_to_mapping_row(d: FormalDiagnosis) -> dict[str, Any]:
    return {
        "three_way": d.three_way,
        "epistemic_status": d.epistemic_status,
        "evidence_status": d.evidence_status,
        "decision_status": d.decision_status,
        "effect_status": d.effect_status,
        "failure_origin": d.failure_origin,
        "gamma_size": d.gamma_size,
        "projection_lossy": d.projection_lossy,
        "reason": d.reason,
    }
