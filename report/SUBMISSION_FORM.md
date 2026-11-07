# Apart submission form checklist

Title: Swarm Witness: What Do Agent-Safety Mechanisms Actually Establish?
Tracks: 3, 4

Abstract:

When agent-safety controls produce apparently valid evidence, what additional
observations, assumptions, and comparisons are required before we can justify
claims about their behavior? We introduce Swarm Witness, an executable
claim-audit method that makes those distinctions explicit through source-pinned
experiments, conventional reference monitors, and fail-closed findings.
Classical authorization is the null hypothesis—not a new primitive we invent.
We reproduce two established safety findings (R1 restart-safe authorization; R2
receipt-attribution ambiguity), compare a bounded BMO ledger property against a
classical reference monitor (R3-L1), and test a three-way evidence classification
on synthetic authorization and multi-principal scenarios (R4/R5). R4 separates
missing evidence, failed enforcement, and supported conclusions, including a
negative control that known-false grant observations cannot yield unqualified
support. R5 transfers that taxonomy to a sequential three-principal shared-grant
model (contention, A→B then B→C assignee hops, ledger-bound receipt misuse)—not
concurrent live swarm execution. The contribution is reusable audit discipline,
not a swarm authorization architecture or general BMO equivalence.

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
