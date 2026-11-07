# Sources and template provenance

## Official Apart report template (Guidelines tab)

**Exact copy URL (required):**

https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing

Document id: `1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE`

Fetched for local reference via Google Docs export (same document id):

- `report/official-template.docx` — `…/export?format=docx`
- `report/official-template.pdf` — `…/export?format=pdf`

Script: `report/fetch_template.sh`

Sprint page (Guidelines / submission rules):
https://apartresearch.com/sprints/swarm-alignment-2026

## Google Docs paste note (judges / final submit)

This environment cannot reliably write into the live Google Docs template
chrome. Submission-ready content is in:

- `report/ABSTRACT.md`
- `report/body.md`
- `report/LIMITATIONS_DUAL_USE.md`
- `report/Swarm_Witness_Final_Submission.pdf` (revised six-page research paper)
- `report/Swarm_Witness_Final_Submission.docx` (editable submission paper)

**Before final Apart form submit**, if judges require the exact official template
chrome (Apart header, author grid, guidance-stripped Docs layout), the author
must open the copy URL above and paste the abstract, body sections, and
Limitations / Dual-Use appendix into that Google Doc, then export PDF from Docs.
Our PDF remains content-complete and submission-ready on structure and page
budget.

## Evidence sources (metrics only; do not invent)

| Claim | Label | Primary metrics files |
| --- | --- | --- |
| R1 | reproduced | `evidence/r1/summary.json`, `evidence/r1/result.yaml`; raw inspect via `evidence/r1/raw.json.gz` |
| R2 | reproduced | `evidence/r2/summary.json`, `evidence/r2/result.yaml` (harness `a5ea5c9`; baseline behavior via stress pack vs `efbd419`) |
| R3 decision-model | unresolved | `evidence/r3/findings/r3-f-comparison.json`, `evidence/r3/summary.json`, `evidence/r3/result.yaml` |
| R3 ledger-claim-v1 | classical_baseline_matches | `evidence/r3_ledger_claim_v1/`, `evidence/r3/ledger_claim_v1/<run_id>/` |
| R4 evidence sufficiency | reproduced | `evidence/r4/findings/r4-f-evidence-sufficiency.json`, `evidence/r4/summary.json` |
| R5 swarm audit | reproduced | `evidence/r5/findings/r5-f-swarm-audit.json`, `evidence/r5/summary.json` |
| Causal simulator (#10) | synthetic model conformance | `evidence/causal_swarm/`, `artifacts/causal_swarm_v1/summary.json` |
| R5 v2 (#11) | fixed-case model conformance | `evidence/r5_v2/`, `artifacts/r5_v2/summary.json` |
| Formal soundness (#12) | conditional proof and exhaustive bounded check | `evidence/taxonomy_theory/`, `theory/`, `artifacts/taxonomy_proof_checks.json` |

Index: `evidence/index.yaml`. Pins: `artifacts/pins.yaml`. Baselines:
`baselines/r1_wal_recover_before_admit.md`,
`baselines/r2_no_implicit_exclusivity.md`,
`baselines/r3_durable_grant_table.md`. Preexisting: `PREEXISTING.md`.
