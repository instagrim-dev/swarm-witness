"""Tests for independent formal epistemics (issue #12).

The formal package must not import production conclusion_classes. Core
invariants are checked against the formal oracle, not classify_conclusion.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from swarm_witness.formal.epistemic_model import (
    ArmObservation,
    Observation,
    TrustAssumptions,
    compatible_worlds,
    decision_correct_property,
    diagnose,
    diagnose_matched_comparison,
    epistemic_status,
    project_three_way,
    required_decision,
)
from swarm_witness.formal.finite_models import (
    check_core_invariants,
    enumerate_permission_worlds,
    run_counterexample_suite,
)


FORMAL_DIR = Path(__file__).resolve().parents[1] / "src" / "swarm_witness" / "formal"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
                # Also record full swarm_witness.* targets.
                names.add(node.module)
    return names


def test_formal_package_does_not_import_conclusion_classes():
    forbidden = {
        "swarm_witness.conclusion_classes",
        "swarm_witness.evidence_sufficiency",
        "swarm_witness.swarm_audit",
    }
    for path in FORMAL_DIR.glob("*.py"):
        imported = _imported_modules(path)
        for bad in forbidden:
            assert bad not in imported, f"{path.name} imports {bad}"
        # Direct from-import of classify_* would show as conclusion_classes module.
        assert "conclusion_classes" not in imported


def test_formal_module_importable_without_conclusion_classes(monkeypatch):
    # Ensure loading formal does not require conclusion_classes to be present
    # as a dependency of the formal oracle itself.
    mod = importlib.import_module("swarm_witness.formal.epistemic_model")
    assert hasattr(mod, "compatible_worlds")
    assert hasattr(mod, "diagnose")


def test_enumerate_worlds_size():
    worlds = enumerate_permission_worlds()
    assert len(worlds) == 8


def test_blind_gamma_keeps_both_grants():
    worlds = enumerate_permission_worlds()
    gamma = compatible_worlds(worlds, Observation())
    assert {w.grant for w in gamma} == {"active", "revoked"}
    assert epistemic_status(decision_correct_property, gamma) == "unresolved"


def test_verified_grant_shrinks_gamma():
    worlds = enumerate_permission_worlds()
    o = Observation(observed_grant="active", authentic=True)
    gamma = compatible_worlds(worlds, o)
    assert gamma
    assert all(w.grant == "active" for w in gamma)
    assert len(gamma) < len(worlds)


def test_unverified_grant_does_not_shrink_under_default_trust():
    worlds = enumerate_permission_worlds()
    o = Observation(observed_grant="active", authentic=None)
    assert compatible_worlds(worlds, o) == worlds


def test_known_misbind_empties_gamma_under_default_trust():
    worlds = enumerate_permission_worlds()
    o = Observation(observed_grant="active", authentic=False)
    assert compatible_worlds(worlds, o) == frozenset()


def test_support_requires_authentic_correct_decision():
    worlds = enumerate_permission_worlds()
    d = diagnose(
        worlds,
        Observation(
            observed_grant="active",
            authentic=True,
            decision_observed="allow",
        ),
        decision_correct_property,
    )
    assert d.three_way == "supported"
    assert d.failure_origin == "none"
    assert d.evidence_status == "authentic"
    assert project_three_way(d) == "supported"


def test_failed_enforcement_requires_authentic_wrong_decision():
    worlds = enumerate_permission_worlds()
    d = diagnose(
        worlds,
        Observation(
            observed_grant="revoked",
            authentic=True,
            decision_observed="allow",
        ),
        decision_correct_property,
    )
    assert d.three_way == "failed_enforcement"
    assert d.failure_origin == "decision_policy"
    assert d.decision_status == "incorrect"


def test_misbound_is_evidence_failure_not_supported():
    worlds = enumerate_permission_worlds()
    d = diagnose(
        worlds,
        Observation(
            observed_grant="revoked",
            authentic=False,
            decision_observed="deny",
        ),
        decision_correct_property,
    )
    assert d.three_way != "supported"
    assert d.evidence_status == "misbound"
    assert d.failure_origin == "evidence"
    assert d.three_way != "failed_enforcement"


def test_irrelevant_does_not_upgrade():
    worlds = enumerate_permission_worlds()
    blind = diagnose(worlds, Observation(), decision_correct_property)
    irr = diagnose(
        worlds,
        Observation(irrelevant_fact="receipt_print_color=blue"),
        decision_correct_property,
    )
    assert blind.three_way == irr.three_way == "missing_evidence"
    assert blind.gamma_size == irr.gamma_size


def test_comparison_divergence_is_not_enforcement_failure():
    d = diagnose_matched_comparison(
        ArmObservation("classical", "allow", True),
        ArmObservation("other", "deny", True),
    )
    assert d.three_way == "comparison_divergent"
    assert d.failure_origin == "comparison_equality"
    assert d.three_way != "failed_enforcement"


def test_comparison_agree_property_fail_is_failed_enforcement():
    d = diagnose_matched_comparison(
        ArmObservation("classical", "allow", False),
        ArmObservation("other", "allow", False),
    )
    assert d.three_way == "failed_enforcement"


def test_comparison_incomplete_is_missing_evidence():
    d = diagnose_matched_comparison(
        ArmObservation("classical", "allow", True, evidence_complete=False),
        ArmObservation("other", "allow", True, evidence_complete=True),
    )
    assert d.three_way == "missing_evidence"


def test_effect_boundary_origin_when_unauthorized_effect_committed():
    worlds = enumerate_permission_worlds()
    d = diagnose(
        worlds,
        Observation(
            observed_grant="revoked",
            authentic=True,
            decision_observed="allow",
            effect_observed=True,
        ),
        decision_correct_property,
    )
    assert d.three_way == "failed_enforcement"
    assert d.failure_origin == "effect_boundary"
    assert d.effect_status == "committed"


def test_core_invariants_pass():
    report = check_core_invariants()
    assert report.passed, report.errors
    assert report.world_count == 8
    assert all(report.theorem_results.values())


def test_counterexample_suite_passes():
    cases = run_counterexample_suite()
    assert {c["id"] for c in cases} >= {
        "C1_known_false_observation",
        "C2_incomplete_observation",
        "C3_correct_but_different_implementations",
        "C4_three_way_lossy_for_orthogonal_diagnoses",
        "C5_correct_decision_does_not_forge_P_eff_support",
        "C6_unauthorized_effect_under_correct_deny",
    }
    failed = [c["id"] for c in cases if not c["passed"]]
    assert not failed, failed


def test_correct_decision_does_not_forge_support_for_P_eff():
    """Regression B1: classical-null agreement ≠ support for arbitrary P."""
    from swarm_witness.formal.epistemic_model import no_unauthorized_effect_property

    worlds = enumerate_permission_worlds()
    o = Observation(
        observed_grant="revoked",
        authentic=True,
        decision_observed="deny",
    )
    d = diagnose(worlds, o, no_unauthorized_effect_property)
    gamma = compatible_worlds(worlds, o)
    assert epistemic_status(no_unauthorized_effect_property, gamma) == "unresolved"
    assert d.epistemic_status == "unresolved"
    assert d.three_way != "supported"


def test_unauthorized_effect_under_correct_deny_is_enforcement_failure():
    """Regression B2: effect-boundary applies even when decision is correct."""
    from swarm_witness.formal.epistemic_model import no_unauthorized_effect_property

    worlds = enumerate_permission_worlds()
    o = Observation(
        observed_grant="revoked",
        authentic=True,
        decision_observed="deny",
        effect_observed=True,
    )
    d = diagnose(worlds, o, no_unauthorized_effect_property)
    assert d.three_way == "failed_enforcement"
    assert d.failure_origin == "effect_boundary"
    assert d.epistemic_status == "refute"
    assert d.decision_status == "correct"


def test_epistemic_status_never_forged_against_gamma():
    """Regression B3: diagnosis.epistemic_status == epistemic_status(P, Γ)."""
    from swarm_witness.formal.epistemic_model import no_unauthorized_effect_property

    worlds = enumerate_permission_worlds()
    props = (decision_correct_property, no_unauthorized_effect_property, lambda _w: True)
    observations = [
        Observation(),
        Observation(observed_grant="revoked", authentic=True, decision_observed="allow"),
        Observation(
            observed_grant="revoked",
            authentic=True,
            decision_observed="deny",
            effect_observed=True,
        ),
        Observation(observed_grant="active", authentic=True, decision_observed="allow"),
    ]
    for prop in props:
        for o in observations:
            gamma = compatible_worlds(worlds, o)
            d = diagnose(worlds, o, prop)
            assert d.epistemic_status == epistemic_status(prop, gamma)


def test_required_decision_classical_null():
    assert required_decision("active") == "allow"
    assert required_decision("revoked") == "deny"


def test_unsafe_trust_misbind_still_refuses_supported():
    """Even if trust keeps nonempty Γ on misbind, diagnose refuses support."""
    worlds = enumerate_permission_worlds()
    trust = TrustAssumptions(empty_gamma_on_known_misbind=False)
    d = diagnose(
        worlds,
        Observation(
            observed_grant="active",
            authentic=False,
            decision_observed="allow",
        ),
        decision_correct_property,
        trust=trust,
    )
    assert d.three_way != "supported"
    assert d.failure_origin == "evidence"


def test_experiment_runner_exits_zero():
    import importlib.util

    run_path = (
        Path(__file__).resolve().parents[1]
        / "experiments"
        / "taxonomy_formal"
        / "run.py"
    )
    spec = importlib.util.spec_from_file_location("taxonomy_formal_run", run_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main([]) == 0


@pytest.mark.parametrize(
    "left_dec,right_dec,expect",
    [
        ("allow", "allow", "supported"),
        ("allow", "deny", "comparison_divergent"),
    ],
)
def test_matched_equality_object_classes(left_dec, right_dec, expect):
    d = diagnose_matched_comparison(
        ArmObservation("L", left_dec, True),
        ArmObservation("R", right_dec, True),
    )
    assert d.three_way == expect
