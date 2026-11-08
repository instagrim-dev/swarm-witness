# EvidenceGraph expanded native conformance (event-level)

Scoring unit: **recorded tool event E produced registry mutation M**.
Assessor inputs are observable records and declared assumptions only.
Native outcomes and private dispatch bindings are scoring-only.
`transfer_claim` stays false; this is expanded native conformance.

Attribution claims: 120

## Per-method attribution tallies (vs warrant)

| Method | Cells | Agree warrant | Correct decisive | Unsupported support | Missed decisive |
|---|---:|---:|---:|---:|---:|
| `evidencegraph_safer_produced` | 120 | 110 | 48 | 10 | 0 |
| `evidencegraph_legacy_produced` | 120 | 88 | 48 | 32 | 0 |
| `eg_evidence_derived_adapter` | 120 | 110 | 48 | 10 | 0 |
| `naive` | 120 | 72 | 0 | 0 | 48 |
| `weak_checklist` | 120 | 72 | 0 | 0 | 48 |
| `strong_invariant` | 120 | 72 | 0 | 0 | 48 |
| `swarm_witness` | 120 | 72 | 0 | 0 | 48 |

## Boundary preservation (adapter vs native safer)

| Scenario | Claims | Adapter matches safer |
|---|---:|---:|
| `clean` | 12 | 12 |
| `missing_tokens` | 12 | 12 |
| `missing_clock_bound` | 12 | 12 |
| `dependent_witnesses` | 12 | 12 |
| `full_receipt_relay` | 12 | 12 |
| `false_exclusivity` | 12 | 12 |
| `capture_window_edge` | 12 | 12 |

## Fabricated / successful-execution family

Adapter cells: 10; matches native safer executed: 10; adapter refutations: 2; native refutations: 2.


Adapter vs safer on listed boundaries: 84/84.

## Reading

Classifier abstention on these raw packets means the frozen classifiers do not consume them as verifying evidence. That does not establish adapter correctness; adapter vs native safer is the conformance column, and warrant/factual_outcome stay separate.

False-exclusivity: agreement with native safer can coexist with a wrong attribution when both accept the same false exclusivity premise.

Capture-window edge: real-event attributions can remain supported while invented-receipt absence contradictions become unresolved — blanket abstention cannot reproduce that split.

## Result (this freeze)

Propositions and candidate sets are selected from public entities; native object_ids/candidates/outcomes are scoring-only. The adapter computes receipt-commitment matching, temporal compatibility, affirmative exclusivity/independence, and absence under covering capture. Boundary agreement with native safer is reported above; it is not explained by a receipt-presence shortcut on mutation entities. `transfer_claim` remains false.
