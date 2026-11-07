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
We apply the method to two prior agent-safety projects, reproducing bounded
results on restart-safe authorization (R1: 153 histories/policy; barrier
prohibited effects 0 vs original 143) and receipt-attribution ambiguity (R2:
36/36 condition-by-seed checks). Separately, a new matched experiment compares
BMO’s transactional first-edit admission with an independent SQLite gate across
six synthetic cases; retained observations agree on the tested one-use
properties under a fail-closed native pin (`classical_baseline_matches`), while
the legacy decision-model R3 comparison remains unresolved. A fourth protocol
makes the audit method’s three-way distinction executable: missing evidence
(identical old receipts leave valid vs revoked worlds indistinguishable),
failed enforcement (revoked grant observed but a broken gate still allows),
and supported conclusions (correct allow/deny once discriminating evidence is
present) (R4 reproduced). Our contribution is that reusable distinction—not a
swarm-authorization architecture or a proof of general BMO equivalence.

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

## Template chrome note

Official Guidelines-tab template copy URL (also in `report/SOURCES.md`):

https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing

If the submission form / judges require the exact Google Docs official template
chrome, paste ABSTRACT + body sections + Limitations/Dual-Use appendix into that
Doc before final submit. The PDF above is still submission-ready content
(Apart recommended structure + required appendix).
