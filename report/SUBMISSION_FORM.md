# Apart submission form checklist

Title: Swarm Witness: What Do Agent-Safety Mechanisms Actually Establish?
Tracks: 3, 4

Abstract:

After matching policy, observations, trust assumptions, durability, and
enforcement coverage, which claimed benefits of agent-safety mechanisms remain?
We test that question with Swarm Witness, an executable claim-audit kit that
pins third-party artifacts, states precise claim cards, runs discriminating
checks, and records fail-closed conclusion labels. Classical reductions
(recover-before-admit; no-implicit-exclusivity; durable grant-table checks) are
questions under test via matched baselines—not intro verdicts. On three pinned
targets we obtain: SoundGate recovery-barrier (R1) reproduced — 153
histories/policy, original prohibited effects 143 vs barrier 0, with 147 strict
refusal-startup refusals; EvidenceGraph receipt stress (R2) reproduced —
36/36 condition-by-seed checks, old-rule relay wrong attributions [1,1,1] per
seed vs safer supported [0,0,0], and clean withheld-without-exclusivity
[12,12,12]; BMO retained-grant vs ClassicalGate (R3 decision-model) unresolved
— matched decision-model comparison incomplete (0/4 isomorphic BMO observations;
selected Go package tests are metadata only); separately, derived protocol
r3-ledger-claim-v1 reports a bounded L1 ledger-claim match
(`classical_baseline_matches`) for six synthetic cases under native pin
`4b717d7` (dispositions and property-relevant projections at every step; not
full identity-hash equality or general BMO equivalence). Weekend contributions
claimed here are (1) pinned replications for R1/R2, (2) the audit kit, and
(3) a scoped L1 ledger-claim comparison distinct from the unresolved
decision-model R3. Auditors should publish matched baselines and labels.

Authors: <!-- user-provided; leave blank — do not invent names -->
Affiliations: <!-- user-provided; leave blank -->

PDF: report/Swarm_Witness_Apart_Submission.pdf
GitHub: <!-- optional -->
Video: none unless completed

## Labels (v2; from evidence/index.yaml)

| Claim | Label |
| --- | --- |
| R1 SoundGate recovery barrier | reproduced |
| R2 EvidenceGraph receipt stress | reproduced |
| R3 BMO vs ClassicalGate (decision-model) | unresolved |
| R3 ledger-claim-v1 (L1) | classical_baseline_matches |

## Template chrome note

Official Guidelines-tab template copy URL (also in `report/SOURCES.md`):

https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing

If the submission form / judges require the exact Google Docs official template
chrome, paste ABSTRACT + body sections + Limitations/Dual-Use appendix into that
Doc before final submit. The PDF above is still submission-ready content
(Apart recommended structure + required appendix).
