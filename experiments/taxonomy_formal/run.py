#!/usr/bin/env python3
"""Run independent finite-model checks for taxonomy formalization (issue #12).

Usage:
  python experiments/taxonomy_formal/run.py
  python experiments/taxonomy_formal/run.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure src/ is importable when run from a bare checkout.
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from swarm_witness.formal.epistemic_model import (  # noqa: E402
    ArmObservation,
    Observation,
    decision_correct_property,
    diagnose,
    diagnose_matched_comparison,
)
from swarm_witness.formal.finite_models import (  # noqa: E402
    check_core_invariants,
    diagnosis_to_mapping_row,
    enumerate_permission_worlds,
)


def r3_r4_r5_mapping() -> list[dict]:
    """Map formal diagnoses onto existing experiment observation shapes."""
    worlds = enumerate_permission_worlds()
    rows: list[dict] = []

    # --- R4 ---
    r4_cases = [
        (
            "r4_blind_world_ab",
            Observation(),
            "missing_evidence",
            "R4 Worlds A/B without current grant — indistinguishable",
        ),
        (
            "r4_supported_active_allow",
            Observation(
                observed_grant="active",
                authentic=True,
                decision_observed="allow",
            ),
            "supported",
            "R4 discriminated World A with correct allow",
        ),
        (
            "r4_failed_enforcement_revoked_allow",
            Observation(
                observed_grant="revoked",
                authentic=True,
                decision_observed="allow",
            ),
            "failed_enforcement",
            "R4 broken gate allows under revoked grant",
        ),
        (
            "r4_misbound_observation",
            Observation(
                observed_grant="active",
                authentic=False,
                decision_observed="allow",
            ),
            "missing_evidence",
            "R4 misbound: evidence invalidity (not decision_policy)",
        ),
        (
            "r4_irrelevant_blind",
            Observation(irrelevant_fact="receipt_print_color=blue"),
            "missing_evidence",
            "R4 irrelevant fact must not upgrade",
        ),
    ]
    for case_id, obs, expect, note in r4_cases:
        d = diagnose(worlds, obs, decision_correct_property)
        rows.append(
            {
                "experiment": "R4",
                "case_id": case_id,
                "note": note,
                "expected_three_way": expect,
                "formal": diagnosis_to_mapping_row(d),
                "claim_status": (
                    "supported"
                    if d.three_way == expect
                    else "unsupported"
                ),
                "still_unverifiable": False,
            }
        )

    # --- R3-L1 ---
    # Supported matched L1 (arms agree + properties hold).
    d_l1_ok = diagnose_matched_comparison(
        ArmObservation("classical", "allow", True),
        ArmObservation("bmo_l1", "allow", True),
    )
    rows.append(
        {
            "experiment": "R3-L1",
            "case_id": "r3_l1_matched_supported",
            "note": "Native-qualified matched L1 agreement + property success",
            "expected_three_way": "supported",
            "formal": diagnosis_to_mapping_row(d_l1_ok),
            "claim_status": (
                "supported" if d_l1_ok.three_way == "supported" else "unsupported"
            ),
            "still_unverifiable": False,
        }
    )
    d_l1_div = diagnose_matched_comparison(
        ArmObservation("classical", "allow", True),
        ArmObservation("bmo_l1", "deny", True),
    )
    rows.append(
        {
            "experiment": "R3-L1",
            "case_id": "r3_l1_comparison_divergent",
            "note": "Arm divergence refutes equality ≠ failed_enforcement",
            "expected_three_way": "comparison_divergent",
            "formal": diagnosis_to_mapping_row(d_l1_div),
            "claim_status": (
                "supported"
                if d_l1_div.three_way == "comparison_divergent"
                and d_l1_div.failure_origin == "comparison_equality"
                else "unsupported"
            ),
            "still_unverifiable": False,
        }
    )
    rows.append(
        {
            "experiment": "R3-L1",
            "case_id": "r3_legacy_decision_model",
            "note": (
                "Legacy r3-matched-decision-model lacks isomorphic BMO "
                "observations — still missing_evidence / unresolved"
            ),
            "expected_three_way": "missing_evidence",
            "formal": diagnosis_to_mapping_row(
                diagnose(worlds, Observation(), decision_correct_property)
            ),
            "claim_status": "supported",
            "still_unverifiable": True,
        }
    )

    # --- R5 ---
    r5_cases = [
        (
            "r5_missing_peer_observation",
            Observation(),
            "missing_evidence",
            "Missing peer grant observation",
        ),
        (
            "r5_contention_broken_second_allow",
            Observation(
                observed_grant="revoked",
                authentic=True,
                decision_observed="allow",
                effect_observed=False,  # R5 broken-allow does not commit
            ),
            "failed_enforcement",
            "Broken second allow after spend; effect prevented",
        ),
        (
            "r5_contention_first_claim_supported",
            Observation(
                observed_grant="active",
                authentic=True,
                decision_observed="allow",
                effect_observed=True,
            ),
            "supported",
            "First claim under active shared grant",
        ),
    ]
    for case_id, obs, expect, note in r5_cases:
        d = diagnose(worlds, obs, decision_correct_property)
        rows.append(
            {
                "experiment": "R5",
                "case_id": case_id,
                "note": note,
                "expected_three_way": expect,
                "formal": diagnosis_to_mapping_row(d),
                "claim_status": (
                    "supported" if d.three_way == expect else "unsupported"
                ),
                "still_unverifiable": False,
            }
        )

    rows.append(
        {
            "experiment": "R5",
            "case_id": "r5_unbounded_population_safety",
            "note": (
                "Unbounded population-scale or live BMO-mesh safety is outside "
                "the finite model — still unverifiable"
            ),
            "expected_three_way": None,
            "formal": None,
            "claim_status": "still_unverifiable",
            "still_unverifiable": True,
        }
    )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report on stdout",
    )
    args = parser.parse_args(argv)

    report = check_core_invariants()
    mapping = r3_r4_r5_mapping()
    payload = {
        "finite_model": report.to_dict(),
        "experiment_mapping": mapping,
        "oracle": "swarm_witness.formal (independent of conclusion_classes)",
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("Swarm Witness taxonomy formalization — finite-model check")
        print(f"  worlds enumerated: {report.world_count}")
        print(f"  passed: {report.passed}")
        for name, ok in report.theorem_results.items():
            print(f"  [{'OK' if ok else 'FAIL'}] {name}")
        if report.errors:
            print("errors:")
            for e in report.errors:
                print(f"  - {e}")
        print("counterexamples:")
        for c in report.counterexamples:
            print(f"  [{'OK' if c['passed'] else 'FAIL'}] {c['id']}: {c['description']}")
        print("experiment mapping:")
        for row in mapping:
            status = row["claim_status"]
            print(
                f"  [{status}] {row['experiment']}/{row['case_id']}: {row['note']}"
            )
        print("limits:")
        for lim in report.limits:
            print(f"  - {lim}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
