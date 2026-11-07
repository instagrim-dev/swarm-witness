# Apart submission form checklist

Title: Swarm Witness: A Testable Evidence Standard for Agent Safety Claims
Tracks: 3 (primary), 4 (application surface only)

Abstract:
Agent-safety systems generate receipts, decisions, traces and recovery records, yet a successful test does not automatically justify the security claim made about it. We introduce Swarm Witness, an executable method for qualifying authorization and evidence claims against pinned artifacts, conventional controls and explicitly verified observations. The method combines two independent reproductions or confirmations of prior studies, a native BMO versus SQLite reference-monitor comparison, a three-way evidence-conclusion evaluator, and an independently checked finite-world semantics. We extend the evaluation to deterministic multi-principal interleavings with separately reconstructed effect observations. Across six native BMO ledger cases, both arms satisfy the declared one-use properties. In 13 fixed multi-principal scenarios (26 policy runs), the independent trace oracle detects nine unauthorized effects under a deliberately faulty local-evidence policy and zero under the authoritative reference monitor. Paired worlds show why identical cached receipts cannot establish current permission; independently delivered authority changes the warranted decision. The result is a practical, reproducible distinction between missing evidence, incorrect decisions, committed effects and supported findings, rather than another agent permission mechanism. The package provides executable counterexamples, provenance-bound findings and a foundation for rigorous agent delegation audits.

Author: Jonathan Maye-Hobbs
Affiliation: None

PDF: report/Swarm_Witness_Final_Submission.pdf
GitHub: https://github.com/instagrim-dev/swarm-witness (currently private —
grant judge read access, publish a mirror, or attach
`artifacts/swarm-witness-review-bundle.zip` from `bash scripts/pack_review_bundle.sh`;
see `evidence/ACCESS.md` and `CHECKLIST.md` remaining user steps)
Video: none unless completed

## Labels (v2; from evidence/index.yaml)

| Claim | Label |
| --- | --- |
| R1 SoundGate recovery barrier | reproduced (pinned replication) |
| R2 EvidenceGraph receipt stress | reproduced (pinned replication) |
| R3 BMO vs ClassicalGate (decision-model) | unresolved |
| R3 ledger-claim-v1 (L1) | classical_baseline_matches |
| R4 evidence sufficiency | reproduced (synthetic conformance) |
| R5 multi-principal sequential model | reproduced (synthetic conformance) |
| Causal interleaving simulator (#10) | 8 cases / 16 arms, reference 0 vs mutant 6 unauthorized effects |
| Expanded R5 v2 (#11) | 13 cases / 26 arms, reference 0 vs mutant 9 unauthorized effects |
| Formal theory (#12) | 2,646 finite checks, zero violations |

## Template chrome note

Official Guidelines-tab template copy URL (also in `report/SOURCES.md`):

https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing

If the submission form / judges require the exact Google Docs official template
chrome, paste ABSTRACT + body sections + Limitations/Dual-Use appendix into that
Doc before final submit. The PDF above is still submission-ready content
(Apart recommended structure + required appendix).
