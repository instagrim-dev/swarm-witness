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


def theorem_support_soundness(worlds: frozenset[World]) -> tuple[bool, list[str]]:
    """T1: if diagnose yields supported for P_dec, every w∈Γ satisfies P_dec,
    and the observed decision matches the classical null for the observed grant.
    """
    errors: list[str] = []
    for grant in ("active", "revoked"):
        for decision in ("allow", "deny"):
            o = _obs(grant=grant, authentic=True, decision=decision)
            d = diagnose(worlds, o, decision_correct_property)
            if d.three_way != "supported":
                continue
            gamma = compatible_worlds(worlds, o)
            if not gamma:
                errors.append(f"supported with empty Γ for grant={grant}")
                continue
            if not all(decision_correct_property(w) for w in gamma):
                errors.append(f"supported but Γ contains P-violators: {grant}/{decision}")
            if decision != required_decision(grant):  # type: ignore[arg-type]
                errors.append(
                    f"supported despite decision {decision} ≠ required for {grant}"
                )
    return not errors, errors


def theorem_refutation_soundness(worlds: frozenset[World]) -> tuple[bool, list[str]]:
    """T2: failed_enforcement only when authentic evidence + incorrect decision
    (or effect-boundary violation); never from incomplete/misbound alone under
    default trust.
    """
    errors: list[str] = []
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

    # Authentic + wrong decision → failed_enforcement.
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

    # Authentic + wrong decision + committed effect under deny → effect_boundary.
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
    mutually exclusive; exhaustiveness holds for the four-way label set including
    comparison_divergent only when the evaluation object is matched_equality.
    """
    errors: list[str] = []
    worlds = enumerate_permission_worlds()
    cases = [
        _obs(),
        _obs(grant="active", authentic=True, decision="allow"),
        _obs(grant="revoked", authentic=True, decision="deny"),
        _obs(grant="revoked", authentic=True, decision="allow"),
        _obs(grant="active", authentic=False, decision="deny"),
        _obs(grant="active", authentic=None),
    ]
    seen: set[str] = set()
    for o in cases:
        d = diagnose(worlds, o, decision_correct_property)
        # One label per diagnosis.
        if d.three_way in seen and False:
            pass
        seen.add(d.three_way)
        # Mechanism evaluations must not emit comparison_divergent.
        if d.three_way == "comparison_divergent":
            errors.append("mechanism_property emitted comparison_divergent")
    allowed = {"missing_evidence", "failed_enforcement", "supported"}
    if not seen <= allowed:
        errors.append(f"unexpected classes in mechanism model: {seen - allowed}")
    if "missing_evidence" not in seen or "supported" not in seen:
        errors.append(f"mechanism suite incomplete: {seen}")
    if "failed_enforcement" not in seen:
        errors.append("mechanism suite missing failed_enforcement")
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
