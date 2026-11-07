"""Independent research acceptance probes for issues 10–12."""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'src'))
sys.path.insert(0,str(BASE/'experiments'/'causal_swarm'))
sys.path.insert(0,str(BASE/'theory'))

from swarm_witness.causal_simulator import (ScenarioError, Runtime, independent_oracle,
                                            local_visible_claim, simulate)
from run import run_manifest
from check_taxonomy import check, verdict, FULL


def cases(subdir):
    path=BASE/'experiments'/subdir/('cases.json' if subdir=='r5_v2' else 'scenarios.json')
    return json.loads(path.read_text())['cases']


def test_causal_interleavings_have_two_distinct_winners():
    cs={c['id']:c for c in cases('causal_swarm')}
    a=simulate(cs['contention_a_first'],'reference')
    b=simulate(cs['contention_b_first'],'reference')
    assert independent_oracle(a)['valid_effects']==1
    assert independent_oracle(b)['valid_effects']==1
    assert a['effect_log'][0]['actor']=='A'
    assert b['effect_log'][0]['actor']=='B'


def test_paired_worlds_identical_visibility_but_different_authority():
    cs={c['id']:c for c in cases('causal_swarm')}
    active=simulate(cs['active_same_local_view'],'reference')
    revoked=simulate(cs['revoked_same_local_view'],'reference')
    assert local_visible_claim(active,'b1')==local_visible_claim(revoked,'b1')
    assert independent_oracle(active)['valid_effects']==1
    assert independent_oracle(revoked)['valid_effects']==0
    assert [e['decision'] for e in active['events'] if e['op']=='claim']==['allow']
    assert [e['decision'] for e in revoked['events'] if e['op']=='claim']==['deny']
    # Intervene only on the evidence boundary: deliver the current authoritative
    # grant snapshot *after* any revoke, immediately before the same claim.
    # The two initially indistinguishable worlds now have discriminating views.
    updated = []
    for case in (cs['active_same_local_view'], cs['revoked_same_local_view']):
        revised = deepcopy(case)
        claim = revised['schedule'].pop()
        prior = revised['schedule'][-1]['id']
        revised['schedule'].append({'id':'e-fresh','op':'deliver_view',
                                    'actor':'transport','recipient':'B',
                                    'grant_id':'g','parents':[prior]})
        claim['parents']=['e-fresh']
        revised['schedule'].append(claim)
        updated.append(simulate(revised,'broken_local'))
    assert local_visible_claim(updated[0],'b1') != local_visible_claim(updated[1],'b1')
    assert [e['decision'] for e in updated[0]['events'] if e['op']=='claim'] == ['allow']
    assert [e['decision'] for e in updated[1]['events'] if e['op']=='claim'] == ['deny']
    assert all(independent_oracle(t)['unauthorized_effects']==0 for t in updated)


def test_bad_local_policy_produces_independent_oracle_counterexample():
    c=next(x for x in cases('causal_swarm') if x['id']=='revoked_stale_view')
    a=simulate(c,'reference'); b=simulate(c,'broken_local')
    assert independent_oracle(a)['unauthorized_effects']==0
    assert independent_oracle(b)['unauthorized_effects']==1
    assert independent_oracle(b)['incorrect_decisions']==1
    # A forged claim flag cannot alter the observer's effect ledger.
    tampered=deepcopy(b)
    next(x for x in tampered['events'] if x['op']=='claim')['effect_committed']=False
    assert any('decision/independent-effect-ledger mismatch' in x for x in
               independent_oracle(tampered)['violation_events'])


def test_missing_causal_parent_refused():
    rt=Runtime('reference')
    try:rt.step({'id':'not-first','op':'issue','grant_id':'g','task_id':'t','owner':'A','epoch':'e',
                 'parents':['missing']})
    except ScenarioError:pass
    else:raise AssertionError('missing causal predecessor admitted')


def test_externally_fixed_r5_v2_matrix_is_varied_and_passes(tmp_path):
    c=cases('r5_v2')
    assert len(c)>=12
    assert len({x['dimension'] for x in c})>=6
    s=run_manifest(BASE/'experiments/r5_v2/cases.json',tmp_path/'r5')
    assert s['passed'],s['failures']
    assert s['arm_count']==2*len(c)
    assert any(r['observed']['unauthorized_effects']>0 for r in s['results'])
    assert any(r['observed']['valid_effects']>0 for r in s['results'])


def _error_kinds(summary):
    return [item.get('error') for item in summary['errors'] if isinstance(item, dict) and 'error' in item]


def test_empty_manifest_does_not_pass(tmp_path):
    manifest = tmp_path / 'empty.json'
    manifest.write_text(json.dumps({'protocol': 'causal-swarm-v1', 'cases': []}))
    summary = run_manifest(manifest, tmp_path / 'out')
    assert summary['passed'] is False
    assert 'empty_or_missing_cases' in _error_kinds(summary)
    assert 'declared_scenario_ids' in _error_kinds(summary)
    assert summary['paired_worlds_local_indistinguishable'] is False
    assert summary['irrelevant_control_unchanged'] is False
    assert summary['denominators']['min_causal_events'] == 0


def test_empty_expected_dicts_do_not_pass(tmp_path):
    case = deepcopy(cases('causal_swarm')[0])
    case['expected'] = {'reference': {}, 'broken_local': {}}
    manifest = tmp_path / 'vacuous.json'
    manifest.write_text(json.dumps({'protocol': 'causal-swarm-v1', 'cases': [case]}))
    summary = run_manifest(manifest, tmp_path / 'out')
    assert summary['passed'] is False
    assert 'empty_expected_arm' in _error_kinds(summary)
    assert summary['arm_count'] == 0


def test_missing_comparison_field_does_not_pass(tmp_path):
    source = cases('causal_swarm')
    edited = deepcopy(source)
    del edited[0]['expected']['reference']['unauthorized_effects']
    manifest = tmp_path / 'partial.json'
    manifest.write_text(json.dumps({'protocol': 'causal-swarm-v1', 'cases': edited}))
    summary = run_manifest(manifest, tmp_path / 'out')
    assert summary['passed'] is False
    assert 'missing_comparison_fields' in _error_kinds(summary)


def test_truncated_declared_ids_and_arm_count_do_not_pass(tmp_path):
    source = cases('causal_swarm')
    manifest = tmp_path / 'truncated.json'
    manifest.write_text(json.dumps({
        'protocol': 'causal-swarm-v1',
        'cases': source[:4],
    }))
    summary = run_manifest(manifest, tmp_path / 'out')
    assert summary['passed'] is False
    assert summary['arm_count'] != 16
    assert 'declared_scenario_ids' in _error_kinds(summary)
    assert 'arm_count' in _error_kinds(summary)


def test_skipped_negative_controls_do_not_pass(tmp_path):
    """A schedule outside the historical ids still cannot skip the controls."""
    case = deepcopy(cases('causal_swarm')[0])
    case['id'] = 'solo_schedule'
    manifest = tmp_path / 'no-controls.json'
    manifest.write_text(json.dumps({
        'protocol': 'ad-hoc-probe',
        'declared_scenario_ids': ['solo_schedule'],
        'expected_arm_count': 2,
        'cases': [case],
    }))
    summary = run_manifest(manifest, tmp_path / 'out')
    assert summary['passed'] is False
    assert 'paired_worlds_missing' in _error_kinds(summary)
    assert 'irrelevant_control_missing' in _error_kinds(summary)


def test_zero_event_denominator_does_not_pass(tmp_path):
    case = {
        'id': 'empty_schedule',
        'dimension': 'denominator',
        'agents': ['A'],
        'schedule': [],
        'expected': {
            'reference': {'valid_effects': 0, 'unauthorized_effects': 0, 'incorrect_decisions': 0},
            'broken_local': {'valid_effects': 0, 'unauthorized_effects': 0, 'incorrect_decisions': 0},
        },
    }
    manifest = tmp_path / 'zero.json'
    manifest.write_text(json.dumps({'protocol': 'ad-hoc-probe', 'cases': [case]}))
    summary = run_manifest(manifest, tmp_path / 'out')
    assert summary['passed'] is False
    assert 'empty_denominator' in _error_kinds(summary)
    assert summary['denominators']['min_causal_events'] == 0


def test_shipped_causal_manifest_still_passes(tmp_path):
    summary = run_manifest(BASE / 'experiments/causal_swarm/scenarios.json', tmp_path / 'causal')
    assert summary['passed'] is True, summary['errors']
    assert summary['scenario_count'] == 8
    assert summary['arm_count'] == 16
    assert summary['expected_arm_count'] == 16
    assert summary['dimension_count'] == 6
    assert summary['paired_worlds_local_indistinguishable'] is True
    assert summary['irrelevant_control_unchanged'] is True
    assert summary['denominators']['min_causal_events'] > 0
    assert summary['manifest_sha256'] == '085cbd980fbcc4eee82e96320d2b7ad6c6f82170ae5e28dd307efe5ff5c05126'


def test_historical_simulator_commits_whenever_it_allows():
    """The retained causal model has no settlement gate after allow.

    The multi-agent ledger is the reference that can refuse an effect after
    a local allow. This historical simulator is not that ledger.
    """
    allowed = []
    for case in cases('causal_swarm'):
        for policy in ('reference', 'broken_local'):
            trace = simulate(case, policy)
            for event in trace['events']:
                if event['op'] == 'claim' and event['decision'] == 'allow':
                    allowed.append(event)
    assert allowed
    assert all(event['effect_committed'] is True for event in allowed)


def test_model_theorems_checked_without_production_classifier():
    summary=check()
    assert summary['passed'],summary['violations']
    assert sum(summary['checks'].values())>=2000
    # Actual world w0 in P, w1 outside P; indistinguishable from Γ={w0,w1}.
    assert verdict(0b0001,0b0011)=='unresolved'
    assert verdict(0b0001,0b0001)=='supported'
    assert verdict(0b0001,0b0010)=='refuted'
    assert verdict(FULL,0)=='unresolved'  # no vacuous license
    assert verdict(FULL,FULL,verified=False)=='unresolved'
