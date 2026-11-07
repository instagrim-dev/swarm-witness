# Apart submission form checklist

Title: Swarm Witness: An Executable Evidence Protocol for Agent Authorization Claims
Tracks: 3 (primary), 4 (application surface only)

Abstract:
Agent systems generate receipts, decisions, traces and recovery records, yet a successful test does not automatically justify the security claim made about it. We introduce Swarm Witness, an executable evidence protocol that binds authorization claims to specified observations and reports whether those observations support, refute, or leave the claim unresolved, while recording evidence provenance, decision correctness and committed effects separately. The method combines source-pinned re-execution and later-harness confirmation of prior studies, a native BMO versus SQLite reference-monitor comparison, a three-way evidence-conclusion evaluator, and a separately implemented finite-world checker. We extend evaluation to deterministic multi-principal interleavings with a distinct modeled effect ledger. Across six native BMO ledger cases, both arms satisfy the declared one-use properties. In 14 fixed multi-principal scenarios (28 policy runs), a separately implemented trace oracle detects nine unauthorized effects under a deliberately faulty local-evidence policy and zero under the authoritative reference monitor. Paired worlds show why identical cached grant observations cannot establish current permission. The package provides executable counterexamples, provenance-bound findings and a foundation for rigorous agent delegation audits.

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
