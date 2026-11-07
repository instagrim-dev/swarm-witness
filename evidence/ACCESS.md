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
| R5 multi-agent / swarm audit | `evidence/r5/` |
| Claims / pins | `claims/`, `artifacts/pins.yaml` |
| Report PDF | `report/Swarm_Witness_Apart_Submission.pdf` |

R3-L1 `source_manifest.json` uses portable locators (`bmo_go_test.log`,
`<local-checkout>`, relative `cases_path`). Bridge log is archived at the run
root. Native re-execution needs a BMO tree containing pin
`4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe` and Go; label verification does not.

## Verify without re-running harnesses

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py
python3 experiments/r3/ledger_claim_v1/compare.py \
  --run-dir evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2
# expect: classical_baseline_matches, native qualification ok
```

## Re-run synthetic protocols (idempotent)

```bash
python3 experiments/evidence_sufficiency/run.py  # R4 → evidence/r4
python3 experiments/swarm_r5/run.py             # R5 → evidence/r5
# expect: reproduced; three_way true; R5 agents ["A","B","C"]
python scripts/check_evidence.py --write-index
python scripts/check_evidence.py
```

## Pack a portable review bundle

```bash
bash scripts/pack_review_bundle.sh
# writes dist/swarm-witness-review-bundle.zip
```

The zip includes claims, evidence, report, `src/`, synthetic experiment runners
(R4/R5), `scripts/`, and `pyproject.toml` so judges can install and re-run R4/R5
without a BMO checkout. R1/R2 third-party trees and native BMO are **not**
bundled (see `PREEXISTING.md`).

## Private-repo access

If Apart judges cannot clone `instagrim-dev/swarm-witness`, the author must
either (a) grant temporary read access, (b) publish a public mirror, or
(c) attach `dist/swarm-witness-review-bundle.zip` to the submission. The audit
kit itself does not require opening unrelated private BMO product trees.
