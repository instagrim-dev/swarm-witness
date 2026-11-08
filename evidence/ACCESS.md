# Evidence access and reproduction

The repository contains the observations, claim definitions, warrants, and method outputs used by the paper. Retained results can be inspected without obtaining the private BMO source checkout.

## Evidence map

| Study | Protocol and inputs | Retained results |
| --- | --- | --- |
| Application effect witness | `experiments/effect_witness/PROTOCOL.md`, `experiments/effect_witness/native_warrants_v1.yaml` | `evidence/effect_witness_v1/` |
| Native, public, and controlled comparisons | `experiments/incident_audit/`, `src/swarm_witness/native_comparison.py` | `report/bounded_comparison_v1/TABLES.md`, `report/bounded_comparison_v1/ledger.csv` |
| EvidenceGraph composition | `experiments/external_calibration/` | `report/external_calibration_v1/`, `evidence/external_calibration_v1/` |
| SoundGate | `claims/r1_restart.yaml`, `experiments/r1/` | `evidence/r1/`, including `evidence/r1/raw.json.gz` |
| EvidenceGraph stress confirmation | `claims/r2_receipt.yaml`, `experiments/r2/` | `evidence/r2/` |
| Native BMO and SQLite first-edit comparison | `experiments/r3/ledger_claim_v1/` | `evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2/` |
| Four-world evidence semantics | `theory/` | `evidence/taxonomy_theory/`, `artifacts/taxonomy_proof_checks.json` |
| Additional controlled protocols | `experiments/`, `protocol/`, `claims/` | `evidence/index.yaml` and the corresponding study directories |

The [paper and publication sources](../report/README.md) identify the current manuscript and exports. Source revisions are recorded in `artifacts/pins.yaml`; [preexisting material](../PREEXISTING.md) identifies the underlying systems.

## Install and validate

Python 3.11 or later is required. Run these commands from the repository root or an extracted review bundle.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py
```

The index validates the retained findings and their evidence references. A completed command is not itself a supported authorization claim; the per-case outputs carry that conclusion.

## Reproduce the principal experiments

```bash
PYTHONPATH=src python experiments/effect_witness/run.py /tmp/swarm-witness-effect
python scripts/render_bounded_comparison.py
PYTHONPATH=src python experiments/external_calibration/run.py
python theory/check_taxonomy.py
```

The application runner creates twelve histories and four evidence conditions per history in the supplied output directory. Its `witness.json` records the local control, actor-only conclusion, and application readback conclusion. The comparison renderer uses the retained packets under `evidence/effect_witness_v1/` and preserves the separate public, controlled, and native denominators. Its generated ledger and tables are in `report/bounded_comparison_v1/`. The EvidenceGraph report distinguishes composition agreement from agreement with warrants and native judgments.

The [comparison reproduction guide](../report/bounded_comparison_v1/REPLAY.md) describes the input and output relationships. Re-executing runners that use their default paths can replace generated results in the checkout; use a disposable checkout when retaining an unchanged copy of the published outputs matters.

## Supporting studies

```bash
python experiments/r3/ledger_claim_v1/compare.py --run-dir evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2
python experiments/r3/ledger_settlement_v1/compare.py --run-dir evidence/r3/ledger_settlement_v1/2026-11-08-ledger-settlement-v1
python experiments/r3/ledger_settlement_v1/compare.py --run-dir evidence/r3/ledger_settlement_v1/2026-11-08-ledger-settlement-v1-controls
PYTHONPATH=src python experiments/external_calibration/heldout_pipeline_v1.py
PYTHONPATH=src python experiments/causal_swarm/run.py --output /tmp/swarm-witness-causal
PYTHONPATH=src python experiments/r5_v2/run.py --output /tmp/swarm-witness-r5-v2
PYTHONPATH=src python experiments/taxonomy_formal/run.py
PYTHONPATH=src python experiments/multi_agent_sim/run.py
PYTHONPATH=src python experiments/swarm_r5_v3/run.py
```

The first command compares the retained six-case BMO and SQLite ledger records. The next two compare the separate settlement protocol: first the two bound continuations, then the run that adds the negative controls. Those commands do not re-execute BMO. The pipeline command rescores the frozen 70-packet set and rewrites `evidence/external_calibration_v1/heldout_v1/pipeline_v1.json`. It does not add packets. Native BMO re-execution requires Go and access to source revision `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe` for the ledger study, and `c8297333b3bf31ded96ca0e8b39c531d3bcea97f` for the settlement study, as described in the corresponding protocol READMEs. The causal and settlement experiments use declared model schedules. They are separate from the local application execution and the public reproduction record.

## Build the paper

Install Pandoc and LibreOffice, then run:

```bash
python -m pip install -e '.[paper]'
bash scripts/build_submission_variants.sh
```

Both paper layouts, their PDF and DOCX exports, and the Markdown extracts derive from `report/Swarm_Witness_Final_Submission.md`. The committed template and fonts are included with the source.

## Pack a portable review bundle

```bash
bash scripts/pack_review_bundle.sh
```

The output is `dist/swarm-witness-review-bundle.zip`. It contains the current paper, publication dependencies, source, protocols, retained evidence, and tests. Historical presentations, caches, disposable worktrees, and earlier bundles are excluded. External SoundGate, EvidenceGraph, and BMO source checkouts are not included; their access requirements and pins remain documented.

Where repository access is restricted, the bundle can be shared with readers who need the retained evidence. It supports local inspection and the included reproduction commands without changing repository visibility.
