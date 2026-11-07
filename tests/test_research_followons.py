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
