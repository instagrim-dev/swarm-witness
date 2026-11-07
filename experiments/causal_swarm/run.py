#!/usr/bin/env python3
"""Run bounded, deterministic interleavings with an independently coded oracle."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from swarm_witness.causal_simulator import independent_oracle, local_visible_claim, simulate


def run_manifest(manifest: Path, output: Path) -> dict:
    data = json.loads(Path(manifest).read_text())
    cases = data['cases']
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    results = []
    errors = []
    for case in cases:
        for policy in ('reference','broken_local'):
            trace = simulate(case, policy)
            observed = independent_oracle(trace)
            expected = case['expected'][policy]
            matched = all(observed[k] == v for k, v in expected.items())
            record = {'case_id':case['id'],'dimension':case['dimension'],'policy':policy,
                      'expected':expected,'observed':observed,'passed':matched}
            results.append(record)
            if not matched:errors.append(record)
            (output / f"{case['id']}.{policy}.json").write_text(json.dumps(trace,indent=2)+'\n')
    by_id = {c['id']:c for c in cases}
    if {'active_same_local_view','revoked_same_local_view'} <= by_id.keys():
        a=simulate(by_id['active_same_local_view'],'broken_local')
        b=simulate(by_id['revoked_same_local_view'],'broken_local')
        same = local_visible_claim(a,'b1') == local_visible_claim(b,'b1')
        if not same:errors.append({'paired_worlds':'local observations unequal'})
    else:same=None
    if {'revoked_stale_view','revoked_irrelevant_extra'} <= by_id.keys():
        a=simulate(by_id['revoked_stale_view'],'broken_local')
        b=simulate(by_id['revoked_irrelevant_extra'],'broken_local')
        irrelevance = (local_visible_claim(a,'b1')==local_visible_claim(b,'b1') and
                       independent_oracle(a)['unauthorized_effects'] == independent_oracle(b)['unauthorized_effects'])
        if not irrelevance: errors.append({'irrelevant_control':'changed conclusion'})
    else:irrelevance=None
    summary={'protocol':data['protocol'],'scenario_count':len(cases),'arm_count':len(results),
             'dimension_count':len(set(c['dimension'] for c in cases)),
             'passed':not errors,'failures':errors,'paired_worlds_local_indistinguishable':same,
             'irrelevant_control_unchanged':irrelevance,
             'manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),
             'results':results}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=Path,default=Path(__file__).with_name('scenarios.json'))
    ap.add_argument('--output',type=Path,default=ROOT/'artifacts'/'causal_swarm_v1')
    a=ap.parse_args();s=run_manifest(a.cases,a.output)
    print(json.dumps({k:s[k] for k in ('protocol','scenario_count','arm_count','dimension_count','passed','paired_worlds_local_indistinguishable','irrelevant_control_unchanged')}))
    sys.exit(0 if s['passed'] else 1)
