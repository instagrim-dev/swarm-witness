#!/usr/bin/env python3
"""Versioned wider R5 matrix, with fixed external manifest and independent oracle."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments'/'causal_swarm'))
from run import run_manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=Path,default=Path(__file__).with_name('cases.json'))
    ap.add_argument('--output',type=Path,default=ROOT/'artifacts'/'r5_v2')
    a=ap.parse_args();s=run_manifest(a.cases,a.output)
    print(json.dumps({k:s[k] for k in ('protocol','scenario_count','arm_count','dimension_count','passed')}))
    sys.exit(0 if s['passed'] else 1)
