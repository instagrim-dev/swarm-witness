# Swarm Witness: What Do Agent-Safety Mechanisms Actually Establish?

**Apart Research — Swarm Alignment sprint (weekend 2026-11-06 … 2026-11-08)**  
**Tracks:** 3 (Strengthening Agent Infrastructure) and 4 (Multi-Agent Oversight and Control)

When agent-safety controls produce apparently valid evidence, what additional
observations, assumptions, and comparisons are required before we can justify
claims about their behavior? Swarm Witness is an executable claim-audit kit that
pins third-party artifacts, states claim cards, runs discriminating checks
against classical baselines (the null hypothesis), and records fail-closed
labels. It is **not** a new authorization architecture, a proof that BMO equals
classical security, or primarily a dual replication.

Pinned results: SoundGate (R1) **reproduced**; EvidenceGraph (R2) **reproduced**;
legacy BMO decision-model (R3) **unresolved**; native L1 ledger-claim
(r3-ledger-claim-v1) **classical_baseline_matches** (bounded); three-way
evidence-sufficiency (R4) **reproduced** (synthetic conformance); multi-principal
transfer (R5) **reproduced** (sequential shared-grant model).

## Submission PDF

Apart-ready report: [`report/Swarm_Witness_Apart_Submission.pdf`](report/Swarm_Witness_Apart_Submission.pdf) (form field cheat sheet: [`report/SUBMISSION_FORM.md`](report/SUBMISSION_FORM.md)).

## Preexisting material

Scaffold, monitors, and the external BMO tree predate this sprint. Full disclosure: [`PREEXISTING.md`](PREEXISTING.md).

## Schema (v2)

Typed validators in `swarm_witness.schema`: `validate_claim` → `Claim`, `validate_run` → `Run`, `validate_finding` → `Finding`. Strings are nonblank; `assumptions` / `run_ids` / `supporting_observation_refs` are non-empty `list[str]` (strings are not coerced to character lists). `Finding.label` ∈ `CONCLUSION_LABELS`; `Run.execution_status` ∈ `assigned|attempted|completed|failed|unrun|missing`; `Finding.basis` ∈ `authored|computed`.

Evidence layout: `evidence/<rN>/runs/*.json`, `evidence/<rN>/findings/*.json`, convenience mirrors `summary.json` / `result.yaml`. Regenerate the index from findings:

```bash
python scripts/check_evidence.py --write-index
python scripts/check_evidence.py
```

## Quick verification (local kit)

```bash
cd /path/to/swarm-witness
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
python scripts/validate_claims.py
python scripts/check_evidence.py
wc -w report/ABSTRACT.md   # expect 150–250
```

## Reproduction experiments

| Experiment | Command | Output |
| --- | --- | --- |
| R1 SoundGate | `bash experiments/r1/run_r1.sh` | `evidence/r1/findings/`, `summary.json` |
| R1 inspect raw | `gzip -dc evidence/r1/raw.json.gz > evidence/r1/raw.json` | local `raw.json` (gitignored) |
| R2 EvidenceGraph | `bash experiments/r2/run_r2.sh` | `evidence/r2/findings/`, `summary.json` |
| R3 matched compare | `python3 experiments/r3/compare.py` | `evidence/r3/findings/r3-f-comparison.json` |
| R3 Go tests (metadata) | `bash experiments/r3/run_bmo_tests.sh` | `evidence/r3/bmo_go_test.log` |
| R3 ledger-claim-v1 | `python3 experiments/r3/ledger_claim_v1/run_matched.py --run-id <id>` | `evidence/r3/ledger_claim_v1/<id>/` |
| R4 evidence sufficiency | `python3 experiments/evidence_sufficiency/run.py` | `evidence/r4/` |
| R5 swarm audit | `python3 experiments/swarm_r5/run.py` | `evidence/r5/` |

Derived protocol **r3-ledger-claim-v1** lives under
[`experiments/r3/ledger_claim_v1/`](experiments/r3/ledger_claim_v1/). Selected
native run: `evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2/` (mirrored
at `evidence/r3_ledger_claim_v1/`). Legacy decision-model R3 stays `unresolved`.

**R4** (`experiments/evidence_sufficiency/`) is the methodological probe: three-way
conclusions (`missing_evidence` / `failed_enforcement` / `supported`) via
`conclusion_classes.py`.

Judge access / portable bundle: [`evidence/ACCESS.md`](evidence/ACCESS.md),
`bash scripts/pack_review_bundle.sh`.

Pre-submit checklist: [`CHECKLIST.md`](CHECKLIST.md).

## Taxonomy formalization (issue #12)

Independent epistemic semantics, finite-model soundness checks, counterexamples,
and a reviewable note live under
[`src/swarm_witness/formal/`](src/swarm_witness/formal/) and
[`analysis/taxonomy_formalization/RESEARCH_NOTE.md`](analysis/taxonomy_formalization/RESEARCH_NOTE.md).
The formal oracle does **not** call production `conclusion_classes`; projected
labels follow the epistemic status of the stated property on Γ, not
classical-null decision agreement alone.

```bash
python experiments/taxonomy_formal/run.py
pytest -q tests/test_formal_epistemics.py
```
