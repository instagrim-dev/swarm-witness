#!/usr/bin/env python3
"""Run bounded, deterministic interleavings with an independently coded oracle.

A passing score requires the manifest's declared scenario ids, both policy
arms, the comparison fields the oracle actually reports, the paired-world and
irrelevant-fact controls, and a nonempty event denominator on every arm.
{"cases": []} and empty expected-result dicts fail closed.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from swarm_witness.causal_simulator import independent_oracle, local_visible_claim, simulate

POLICIES = ('reference', 'broken_local')
REQUIRED_COMPARISON_FIELDS = (
    'valid_effects', 'unauthorized_effects', 'incorrect_decisions',
)
PAIRED_WORLD_IDS = ('active_same_local_view', 'revoked_same_local_view')
IRRELEVANT_CONTROL_IDS = ('revoked_stale_view', 'revoked_irrelevant_extra')

# Historical protocols. A truncated or substituted manifest must not pass
# under these names. The schedules themselves stay in the JSON files.
PROTOCOL_CONTRACTS = {
    'causal-swarm-v1': {
        'scenario_ids': (
            'contention_a_first', 'contention_b_first', 'revoked_stale_view',
            'active_same_local_view', 'revoked_same_local_view',
            'revoked_irrelevant_extra', 'delegation_a_b_c',
            'foreign_receipt_replay',
        ),
        'arm_count': 16,
        'dimension_count': 6,
    },
    'r5-v2-causal-matrix': {
        'scenario_ids': (
            'contention_a_first', 'contention_b_first', 'revoked_stale_view',
            'active_same_local_view', 'revoked_same_local_view',
            'revoked_irrelevant_extra', 'delegation_a_b_c', 'missing_delegate_c',
            'foreign_receipt_replay', 'wrong_task_scope', 'wrong_epoch_scope',
            'missing_local_view', 'delayed_stale_delivery',
        ),
        'arm_count': 26,
        'dimension_count': 9,
    },
}


def _error(kind, **detail):
    row = {'error': kind}
    row.update(detail)
    return row


def run_manifest(manifest: Path, output: Path) -> dict:
    manifest = Path(manifest)
    raw = json.loads(manifest.read_text())
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    results = []
    if not isinstance(raw, dict):
        errors.append(_error('manifest_not_object'))
        raw = {}
    protocol = raw.get('protocol')
    cases = raw.get('cases')
    if not isinstance(cases, list) or not cases:
        errors.append(_error('empty_or_missing_cases'))
        cases = []

    by_id = {}
    seen = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(_error('case_not_object', index=index))
            continue
        case_id = case.get('id')
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(_error('missing_scenario_id', index=index))
            continue
        if case_id in by_id:
            errors.append(_error('duplicate_scenario_id', case_id=case_id))
            continue
        dimension = case.get('dimension')
        if not isinstance(dimension, str) or not dimension.strip():
            errors.append(_error('missing_dimension', case_id=case_id))
        expected = case.get('expected')
        if not isinstance(expected, dict) or not expected:
            errors.append(_error('empty_expected', case_id=case_id))
            expected = {}
        arms_complete = True
        for policy in POLICIES:
            arm = expected.get(policy) if isinstance(expected, dict) else None
            if not isinstance(arm, dict) or not arm:
                errors.append(_error('empty_expected_arm', case_id=case_id, policy=policy))
                arms_complete = False
                continue
            missing = [key for key in REQUIRED_COMPARISON_FIELDS if key not in arm]
            if missing:
                errors.append(_error(
                    'missing_comparison_fields', case_id=case_id, policy=policy,
                    fields=missing,
                ))
                arms_complete = False
        if not arms_complete:
            continue
        by_id[case_id] = case
        seen.append(case_id)
        for policy in POLICIES:
            try:
                trace = simulate(case, policy)
                observed = independent_oracle(trace)
            except Exception as exc:
                errors.append(_error(
                    'simulation_failed', case_id=case_id, policy=policy, detail=str(exc),
                ))
                continue
            arm_expected = expected[policy]
            mismatched = [
                key for key, want in arm_expected.items()
                if key not in observed or observed[key] != want
            ]
            causal_events = observed.get('causal_events')
            denominator_ok = isinstance(causal_events, int) and causal_events > 0
            if not denominator_ok:
                errors.append(_error(
                    'empty_denominator', case_id=case_id, policy=policy,
                    causal_events=causal_events,
                ))
            matched = not mismatched and denominator_ok
            record = {
                'case_id': case_id, 'dimension': dimension, 'policy': policy,
                'expected': arm_expected, 'observed': observed, 'passed': matched,
            }
            results.append(record)
            if mismatched:
                errors.append(record)
            (output / f'{case_id}.{policy}.json').write_text(
                json.dumps(trace, indent=2) + '\n')

    contract = PROTOCOL_CONTRACTS.get(protocol) if isinstance(protocol, str) else None
    if contract:
        declared = list(contract['scenario_ids'])
        missing_ids = [item for item in declared if item not in by_id]
        extra_ids = [item for item in seen if item not in declared]
        if missing_ids or extra_ids:
            errors.append(_error(
                'declared_scenario_ids', missing=missing_ids, extra=extra_ids,
            ))
        expected_arms = contract['arm_count']
        dimensions = {case.get('dimension') for case in by_id.values()}
        if len(dimensions) != contract['dimension_count']:
            errors.append(_error(
                'dimension_count', expected=contract['dimension_count'],
                observed=len(dimensions),
            ))
    else:
        explicit = raw.get('declared_scenario_ids')
        if isinstance(explicit, list):
            declared = list(explicit)
            if set(declared) != set(seen) or len(declared) != len(seen):
                errors.append(_error(
                    'declared_scenario_ids', declared=declared, ran=seen,
                ))
        else:
            declared = list(seen)
            if not declared:
                errors.append(_error('declared_scenario_ids', missing=[], extra=[]))
        if isinstance(raw.get('expected_arm_count'), int):
            expected_arms = raw['expected_arm_count']
        else:
            expected_arms = len(declared) * len(POLICIES)
    if isinstance(raw.get('expected_arm_count'), int) and raw['expected_arm_count'] != expected_arms:
        errors.append(_error(
            'expected_arm_count_conflict',
            declared=raw['expected_arm_count'], contract=expected_arms,
        ))
    if len(results) != expected_arms:
        errors.append(_error(
            'arm_count', expected=expected_arms, observed=len(results),
        ))

    if all(item in by_id for item in PAIRED_WORLD_IDS):
        try:
            active = simulate(by_id[PAIRED_WORLD_IDS[0]], 'broken_local')
            revoked = simulate(by_id[PAIRED_WORLD_IDS[1]], 'broken_local')
            same = local_visible_claim(active, 'b1') == local_visible_claim(revoked, 'b1')
        except Exception as exc:
            same = False
            errors.append(_error('paired_worlds', detail=str(exc)))
        else:
            if not same:
                errors.append(_error('paired_worlds', detail='local observations unequal'))
    else:
        same = False
        errors.append(_error('paired_worlds_missing', required=list(PAIRED_WORLD_IDS)))

    if all(item in by_id for item in IRRELEVANT_CONTROL_IDS):
        try:
            stale = simulate(by_id[IRRELEVANT_CONTROL_IDS[0]], 'broken_local')
            extra = simulate(by_id[IRRELEVANT_CONTROL_IDS[1]], 'broken_local')
            irrelevance = (
                local_visible_claim(stale, 'b1') == local_visible_claim(extra, 'b1')
                and independent_oracle(stale)['unauthorized_effects']
                == independent_oracle(extra)['unauthorized_effects']
            )
        except Exception as exc:
            irrelevance = False
            errors.append(_error('irrelevant_control', detail=str(exc)))
        else:
            if not irrelevance:
                errors.append(_error('irrelevant_control', detail='changed conclusion'))
    else:
        irrelevance = False
        errors.append(_error(
            'irrelevant_control_missing', required=list(IRRELEVANT_CONTROL_IDS),
        ))

    causal_denoms = [
        row['observed'].get('causal_events', 0)
        for row in results if isinstance(row.get('observed'), dict)
    ]
    min_causal = min(causal_denoms) if causal_denoms else 0
    if min_causal <= 0 and not any(
        isinstance(item, dict) and item.get('error') == 'empty_denominator'
        for item in errors
    ):
        errors.append(_error('empty_denominator', causal_events=min_causal))

    scenario_count = len(seen)
    arm_count = len(results)
    dimension_count = len({
        case.get('dimension') for case in by_id.values()
        if isinstance(case.get('dimension'), str) and case.get('dimension')
    })
    passed = (
        not errors
        and scenario_count > 0
        and arm_count == scenario_count * len(POLICIES)
        and arm_count == expected_arms
        and same is True
        and irrelevance is True
        and min_causal > 0
    )
    summary = {
        'protocol': protocol,
        'scenario_count': scenario_count,
        'arm_count': arm_count,
        'dimension_count': dimension_count,
        'expected_arm_count': expected_arms,
        'declared_scenario_ids': declared,
        'passed': passed,
        'failures': [
            item for item in errors
            if isinstance(item, dict) and 'expected' in item and 'observed' in item
        ],
        'errors': errors,
        'paired_worlds_local_indistinguishable': same,
        'irrelevant_control_unchanged': irrelevance,
        'denominators': {
            'scenario_count': scenario_count,
            'arm_count': arm_count,
            'min_causal_events': min_causal,
        },
        'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'results': results,
    }
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', type=Path, default=Path(__file__).with_name('scenarios.json'))
    ap.add_argument('--output', type=Path, default=ROOT / 'artifacts' / 'causal_swarm_v1')
    args = ap.parse_args()
    summary = run_manifest(args.cases, args.output)
    print(json.dumps({
        key: summary[key] for key in (
            'protocol', 'scenario_count', 'arm_count', 'dimension_count', 'passed',
            'paired_worlds_local_indistinguishable', 'irrelevant_control_unchanged',
        )
    }))
    sys.exit(0 if summary['passed'] else 1)
