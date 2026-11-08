# Apart submission form checklist

Title: Swarm Witness: An Executable Evidence Protocol for Agent Authorization Claims
Tracks: 3 (primary), 4 (application surface only)

Abstract: see `report/ABSTRACT.md` (150–250 words). The manuscript leads with one question, the witness `aew-v1-local-control-pass-broader-effect`, and the frozen public tie with the strong checker (both 0 unsupported supports; naive PASS 24). `superiority_claim` stays false.

Author: Jonathan Maye-Hobbs
Affiliation: Independent

PDF (research layout): report/Swarm_Witness_Final_Submission.pdf
PDF (official template chrome): report/Swarm_Witness_Templated_Submission.pdf
DOCX (filled official template): report/Swarm_Witness_Templated_Submission.docx
Slides: report/Swarm_Witness_Slides.pdf
GitHub: https://github.com/instagrim-dev/swarm-witness (currently private —
grant judge read access, publish a mirror, or attach
`artifacts/swarm-witness-review-bundle.zip` from `bash scripts/pack_review_bundle.sh`;
see `evidence/ACCESS.md` and `CHECKLIST.md` remaining user steps)
Video: none unless completed
Rebuild variants: `bash scripts/build_submission_variants.sh`

## Labels (v2; from evidence/index.yaml)

| Claim | Label |
| --- | --- |
| R1 SoundGate recovery barrier | reproduced (pinned replication) |
| R2 EvidenceGraph receipt stress | reproduced (pinned replication) |
| R3 BMO vs ClassicalGate (decision-model) | unresolved |
| R3 ledger-claim-v1 (L1) | classical_baseline_matches |
| R4 evidence sufficiency | reproduced (synthetic conformance) |
| R5 multi-principal sequential model | reproduced (synthetic conformance) |
| Causal interleaving simulator (#10) | 9 cases / 18 arms, reference 0 vs mutant 6 unauthorized effects |
| Expanded R5 v2 (#11) | 14 cases / 28 arms, reference 0 vs mutant 9 unauthorized effects |
| Formal theory (#12) | 2,646 finite checks, zero violations |

## Template chrome note

Official Guidelines-tab template copy URL (also in `report/SOURCES.md`):

https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing

If the submission form / judges require the exact Google Docs official template
chrome, paste ABSTRACT + body sections + Limitations/Dual-Use appendix into that
copy and export PDF from Docs.
