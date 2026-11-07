# Accessing Swarm Witness evidence (judges / external reviewers)

The GitHub repository may be **private**. This file describes how to verify
labels without needing the author’s local absolute paths or a full BMO checkout.

## What is self-contained in-repo

| Artifact | Path |
| --- | --- |
| Label index | `evidence/index.yaml` |
| R1 | `evidence/r1/` (+ `raw.json.gz`) |
| R2 | `evidence/r2/` |
| R3 decision-model (unresolved) | `evidence/r3/` |
| R3-L1 selected run | `evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2/` |
| R3-L1 index mirror | `evidence/r3_ledger_claim_v1/` |
| R4 evidence sufficiency | `evidence/r4/` |
| R5 multi-principal audit | `evidence/r5/` |
| Causal simulator (#10) | `evidence/causal_swarm/`, `artifacts/causal_swarm_v1/` |
| Expanded R5 v2 (#11) | `evidence/r5_v2/`, `artifacts/r5_v2/` |
| Formal taxonomy (#12) | `evidence/taxonomy_theory/`, `theory/`, `artifacts/taxonomy_proof_checks.json` |
| Claims / pins | `claims/`, `artifacts/pins.yaml` |
| Final report PDF | `report/Swarm_Witness_Final_Submission.pdf` |
| Final editable report | `report/Swarm_Witness_Final_Submission.docx` |

R3-L1 `source_manifest.json` uses portable locators (`bmo_go_test.log`,
`<local-checkout>`, relative `cases_path`). Bridge log is archived at the run
root. Native re-execution needs a BMO tree containing pin
`4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe` and Go; label verification does not.

## Verify from a fresh review-bundle extract

The portable zip includes `src/`, all R3/R4/R5 study sources and comparator,
new causal-swarm and R5-v2 runners, `theory/`, `tests/`, raw evidence,
`report/`, `scripts/`, and `pyproject.toml`.

```bash
unzip swarm-witness-review-bundle.zip && cd swarm-witness-review-bundle
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py
python3 experiments/r3/ledger_claim_v1/compare.py \
  --run-dir evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2
# expect: classical_baseline_matches, native qualification ok
python3 experiments/evidence_sufficiency/run.py  # R4
python3 experiments/swarm_r5/run.py             # R5 v1
PYTHONPATH=src python3 experiments/causal_swarm/run.py --output /tmp/causal-swarm-recheck
PYTHONPATH=src python3 experiments/r5_v2/run.py --output /tmp/r5-v2-recheck
python3 theory/check_taxonomy.py               # 2,646 finite instances
# expect: R5-v1 synthetic conformance; v2 13 cases/26 arms; formal checker passes
python scripts/check_evidence.py --write-index
python scripts/check_evidence.py
```

## Pack a portable review bundle

```bash
bash scripts/pack_review_bundle.sh
# writes dist/swarm-witness-review-bundle.zip
# and artifacts/swarm-witness-review-bundle.zip (committed copy for repo readers)
```

R1/R2 third-party trees and native BMO product checkouts are **not** bundled
(see `PREEXISTING.md`).

## Private-repo access

If Apart judges cannot clone `instagrim-dev/swarm-witness`, the author must
either (a) grant temporary read access, (b) publish a public mirror, or
(c) attach `artifacts/swarm-witness-review-bundle.zip` to the submission.
Author: Jonathan Maye-Hobbs. No institutional affiliation.
