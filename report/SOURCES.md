# Sources and template provenance

## Official Apart report template (Guidelines tab)

**Exact copy URL (required):**

https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing

Document id: `1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE`

Fetched for local reference via Google Docs export (same document id), and
replaced with the author’s local **Copy of Apart Research hackathon submission
template.docx** from Downloads (2026-11-07):

- `report/official-template.docx` — authoritative fill source (Downloads copy)
- `report/official-template-from-downloads.docx` — verbatim provenance copy
- `report/official-template.pdf` — earlier `…/export?format=pdf` snapshot

HackTalk links (Yan/Sikora): `docs/hackathon/Getting_Started_with_Swarm_Incidents_Links.md`

Script: `report/fetch_template.sh` · fill/rebuild: `bash scripts/build_submission_variants.sh`

Sprint page (Guidelines / submission rules):
https://apartresearch.com/sprints/swarm-alignment-2026

## Templated + slides variants (form upload)

Built locally from the official template chrome and current manuscript:

| Artifact | Use |
| --- | --- |
| `report/Swarm_Witness_Templated_Submission.docx` | Official template DOCX filled (guidance removed; title/author/abstract/body) |
| `report/Swarm_Witness_Templated_Submission.pdf` | PDF export of templated layout (Old Standard TT chrome) |
| `report/Swarm_Witness_Templated_Submission.md` | Markdown mirror of templated structure |
| `report/Swarm_Witness_Slides.pdf` | 8-slide deck for the form **Slides** field (also `report/slides/`) |
| `report/slides/slides.html` | Slide source |

Rebuild: `bash scripts/build_submission_variants.sh`

Also retained:

- `report/ABSTRACT.md`, `report/body.md`, `report/LIMITATIONS_DUAL_USE.md`
- `report/Swarm_Witness_Final_Submission.pdf` / `.docx` (research paper layout)

Optional: open the Google Docs copy URL above and paste from the templated
markdown if judges insist on the live Docs file rather than the filled DOCX/PDF.

## Incident evidence standard

For the 2026 OpenAI–Hugging Face agent-swarm incident, the evidence standard is the public LessWrong reproduction:

Palan, M., Chute, C., Kim, M. and Van Roy, B. (2026). *OpenAI-HuggingFace: A Reproduction & Lessons for Alignment Testing*. https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment

Original agent transcripts and platform logs are unavailable. Acceptance and qualification use that reproduction and the executable protocols in this package. No criterion requires the withheld originals.

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
