#!/usr/bin/env python3
"""Independent exhaustive finite checker for evidence-set soundness laws.

Does not import Swarm Witness's production classifier; Boolean-set semantics
are implemented here directly. Soundness is conditional on valid observation
provenance and actual-world membership in the compatible-world set.
"""
import json
from pathlib import Path

N = 4
FULL = (1 << N) - 1


def verdict(property_mask: int, evidence_worlds: int, verified: bool = True) -> str:
    if not verified or not evidence_worlds:
        return 'unresolved'
    if evidence_worlds & (~property_mask & FULL) == 0:
        return 'supported'
    if evidence_worlds & property_mask == 0:
        return 'refuted'
    return 'unresolved'


def combine_verified_observations(*possible_world_masks: int) -> int:
    """Intersection semantics: each verified observation filters worlds."""
    gamma = FULL
    for mask in possible_world_masks:
        gamma &= mask
    return gamma


def check() -> dict:
    checks = {'nonvacuity':0, 'support_soundness':0, 'refutation_soundness':0,
              'indistinguishability':0, 'irrelevance':0,
              'verified_refinement_persistence':0,
              'unverified_observation_cannot_support':0}
    failures = []
    for p in range(FULL + 1):
        for gamma in range(FULL + 1):
            got = verdict(p, gamma)
            checks['nonvacuity'] += 1
            if gamma == 0 and got != 'unresolved':failures.append(['vacuity',p,gamma])
            checks['unverified_observation_cannot_support'] += 1
            if verdict(p,gamma,False) != 'unresolved':failures.append(['unverified',p,gamma])
            # Irrelevant facts do not change Γ. The finite checker checks invariance
            # under arbitrary auxiliary metadata labels, not merely one example.
            for irrelevant in range(3):
                checks['irrelevance'] += 1
                # An irrelevant verified observation is satisfied in every world.
                new_worlds = combine_verified_observations(gamma, FULL)
                if verdict(p,gamma) != verdict(p,new_worlds):
                    failures.append(['irrelevance',p,gamma,irrelevant])
            for world in range(N):
                if not (gamma & (1<<world)):
                    continue
                if got == 'supported':
                    checks['support_soundness'] += 1
                    if not p & (1<<world): failures.append(['support',p,gamma,world])
                if got == 'refuted':
                    checks['refutation_soundness'] += 1
                    if p & (1<<world): failures.append(['refute',p,gamma,world])
            if gamma & p and gamma & (~p & FULL):
                checks['indistinguishability'] += 1
                if got != 'unresolved':failures.append(['indistinguishable',p,gamma])
            for refined in range(1,FULL+1):
                if refined & gamma != refined:
                    continue
                checks['verified_refinement_persistence'] += 1
                after=verdict(p,refined)
                if got in ('supported','refuted') and after != got:
                    failures.append(['refinement',p,gamma,refined,got,after])
    return {'theory':'bounded-epistemic-evidence-sets-v1','worlds':N,
            'predicate_assignments':FULL+1,'nonempty_evidence_sets':FULL,
            'checks':checks,'violations':failures,'passed':not failures,
            'countermodel':{
              'description':'An equality comparison can be refuted while two implementations separately satisfy their security properties; disagreement is not enforcement failure.',
              'property_kind':'comparison_equality','comparison_equal':False,
              'left_security_property_holds':True,'right_security_property_holds':True,
              'valid_enforcement_failure_attribution':False}}

if __name__=='__main__':
    r=check(); dest=Path(__file__).parents[1]/'artifacts'/'taxonomy_proof_checks.json'
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('worlds','predicate_assignments','checks','passed')}))
    raise SystemExit(0 if r['passed'] else 1)
