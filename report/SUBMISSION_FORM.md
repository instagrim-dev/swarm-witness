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
We reproduce bounded results on restart-safe authorization (R1) and
receipt-attribution ambiguity (R2); report a bounded native BMO L1 ledger match
alongside an unresolved decision-model R3; and make a three-way distinction
executable (R4): missing evidence, failed enforcement, and supported
conclusions. We then generalize that method to a synthetic three-agent swarm
(R5 reproduced): concurrent shared-grant contention, delegation chains A→B→C,
and cross-agent receipt misuse are classified under the same taxonomy. Our
contribution is reusable audit discipline across single-owner, handoff, and
multi-agent settings—not a new swarm authorization architecture, not a proof of
general BMO equivalence, and not unbounded population-scale safety.

Authors: <!-- user-provided; leave blank — do not invent names -->
Affiliations: <!-- user-provided; leave blank -->
Author hint (unconfirmed): git history on this repo includes commits by
`Jon M <…instagrim-dev@users.noreply.github.com>` — paste only after you confirm.

PDF: report/Swarm_Witness_Apart_Submission.pdf
GitHub: https://github.com/instagrim-dev/swarm-witness (currently private —
grant judge read access, publish a mirror, or attach
`dist/swarm-witness-review-bundle.zip` from `bash scripts/pack_review_bundle.sh`;
see `evidence/ACCESS.md`)
Video: none unless completed

## Labels (v2; from evidence/index.yaml)

| Claim | Label |
| --- | --- |
| R1 SoundGate recovery barrier | reproduced |
| R2 EvidenceGraph receipt stress | reproduced |
| R3 BMO vs ClassicalGate (decision-model) | unresolved |
| R3 ledger-claim-v1 (L1) | classical_baseline_matches |
| R4 evidence sufficiency (Worlds A/B) | reproduced |
| R5 multi-agent / swarm audit | reproduced |

## Template chrome note

Official Guidelines-tab template copy URL (also in `report/SOURCES.md`):

https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing

If the submission form / judges require the exact Google Docs official template
chrome, paste ABSTRACT + body sections + Limitations/Dual-Use appendix into that
Doc before final submit. The PDF above is still submission-ready content
(Apart recommended structure + required appendix).
