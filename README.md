# Swarm Witness: An Executable Evidence Protocol for Agent Authorization Claims

**Apart Swarm Alignment Hackathon 2026** | Primary: Track 3, Strengthening Agent Infrastructure | Application: Track 4, multi-agent oversight.

**An executable audit that distinguishes trustworthy authority from persuasive-looking receipts.** Swarm Witness links source-pinned claims to observations, causal schedules, effect ledgers, competing classical controls, and evidence-qualified findings. It tests when an agent's apparent permission is actually warranted.

## Primary results

| Study | Evidence and result | Evaluation scope |
| --- | --- | --- |
| R1 SoundGate | 153 histories/policy; prohibited effects original 143, recovery barrier 0 | Pinned external re-execution |
| R2 EvidenceGraph | 36/36 stress checks; wrong relay attributions for legacy rule | Confirmation of authors' later stress harness `a5ea5c9` |
| R3-D legacy decision comparison | `unresolved`, 0/4 matched BMO observations | Missing matched decision-model evidence |
| R3-L1 native BMO vs SQLite | 6/6 one-use ledger cases match | Native transactional owner, bounded claim/reopen/rollback properties |
| R4 evidence qualification | Held-out misleading observation, misleading receipt and provenance controls | Synthetic and held-out protocol conformance |
| R5 v1 | Ten sequential A/B/C scenarios | Synthetic multi-principal method transfer |
| #10 causal simulator | 9 schedules, 18 arms; defective policy produces six unauthorized effects, reference zero | Deterministic causal interleavings, model effect ledger |
| #11 R5 v2 | 14 fixed scenarios, 28 arms, nine dimensions; faulty local policy nine unauthorized effects, reference zero | Fixed synthetic matrix with separately reconstructed effects |
| #12 mathematical foundation | Five conditional theorems/countermodels; 2,646 finite checks, zero violations | Four-world possible-world model and written proofs |

The two policy arms are intentionally constructed controls. These numbers measure the tested schedules and are not estimates of incident prevalence in deployed agents.

## Submission

- [Final report, PDF](report/Swarm_Witness_Final_Submission.pdf) | [editable DOCX](report/Swarm_Witness_Final_Submission.docx) | [source Markdown](report/Swarm_Witness_Final_Submission.md)
- [Templated official chrome, PDF](report/Swarm_Witness_Templated_Submission.pdf) | [filled DOCX](report/Swarm_Witness_Templated_Submission.docx)
- [Slides PDF](report/Swarm_Witness_Slides.pdf) (form **Slides** field) · rebuild: `bash scripts/build_submission_variants.sh`
- [Methods and reproducibility map](docs/RESEARCH_FOLLOWONS_10_12.md) | [verification and access](evidence/ACCESS.md) | [submission checklist](CHECKLIST.md)
- [Original prior-work and preexisting-code disclosure](PREEXISTING.md).

## Independent research checks

Install Python 3.11+ and `pip install -e '.[dev]'`, then run:

```bash
pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py
PYTHONPATH=src python -m pytest -q tests/test_research_followons.py
PYTHONPATH=src python experiments/causal_swarm/run.py --output /tmp/swarm-witness-causal
PYTHONPATH=src python experiments/r5_v2/run.py --output /tmp/swarm-witness-r5-v2
python theory/check_taxonomy.py
```

The new tests include reversed claim order, paired worlds with identical cached evidence, fresh-view discrimination, stale revocation, receipt replay, scope mismatch, and a separately reconstructed effect history. The formal checker does not call the production conclusion classifier.

## Reproduction and review artifacts

Evidence is organized as typed `claims/`, `evidence/<study>/runs/`, `findings/`, result summaries, raw traces under `artifacts/`, and pinned source identities under `artifacts/pins.yaml`. The original R1–R5 evidence remains intact; R5 v2 has a new claim and does not overwrite R5 v1.

```bash
bash scripts/pack_review_bundle.sh
# outputs dist/swarm-witness-review-bundle.zip and artifacts/swarm-witness-review-bundle.zip
```

Reviewers can inspect the retained results without obtaining the private BMO working tree; native BMO re-execution requires access to its pinned source. Model-schedule experiments are distinct from live distributed-agent measurements. The mathematical soundness proofs are conditional on authenticated, compatible observations.

Author: Jonathan Maye-Hobbs · Affiliation: Independent. Prefer uploading `Swarm_Witness_Templated_Submission.pdf` (or the filled DOCX) plus `Swarm_Witness_Slides.pdf`; attach the review ZIP or grant reviewers access if the repository stays private.
