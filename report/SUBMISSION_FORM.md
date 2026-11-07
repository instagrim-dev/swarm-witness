# Apart submission form checklist

Title: Swarm Witness: Executable Evidence Auditing for Agent Authorization Claims
Tracks: 3 (primary), 4 (application surface only)

Abstract:

When agent-safety controls produce apparently valid evidence, what additional
observations, assumptions, and comparisons are required before we can justify
claims about their behavior? We introduce Swarm Witness—an executable
evidence-auditing method for agent authorization claims—built around
source-pinned experiments, conventional reference monitors, and fail-closed
findings. Classical authorization is the null hypothesis. We confirm two prior
safety findings (R1 pinned SoundGate re-execution; R2 published-harness
confirmation at a later stress revision), report a bounded native BMO ledger
match (R3-L1) beside an incomplete decision-model comparison (R3-D unresolved),
and exercise a three-way evidence classifier on synthetic and held-out artifacts
(R4/R5). Findings separate conclusion from evaluation method. The method also
separates comparison divergence from enforcement failure, and records evidence /
decision / effect diagnoses so misbound observations and wrong decisions
prevented at the effect boundary are not conflated. Primary track: strengthening agent infrastructure (Track 3); synthetic
multi-principal cases illustrate a Track 4 application surface, not live swarm
oversight or unbounded population safety.


Authors: <!-- user-provided; leave blank — do not invent names -->
Affiliations: <!-- user-provided; leave blank -->
Author hint (unconfirmed): git history on this repo includes commits by
`Jon M <…instagrim-dev@users.noreply.github.com>` — paste only after you confirm.

PDF: report/Swarm_Witness_Apart_Submission.pdf
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

## Template chrome note

Official Guidelines-tab template copy URL (also in `report/SOURCES.md`):

https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing

If the submission form / judges require the exact Google Docs official template
chrome, paste ABSTRACT + body sections + Limitations/Dual-Use appendix into that
Doc before final submit. The PDF above is still submission-ready content
(Apart recommended structure + required appendix).
