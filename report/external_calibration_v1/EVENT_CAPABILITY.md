# EvidenceGraph expanded native conformance (event-level)

Scoring unit: **recorded tool event E produced registry mutation M**.
Assessor inputs are observable records and declared assumptions only.
Native outcomes and private dispatch bindings are scoring-only.
`transfer_claim` stays false; this is expanded native conformance.

Attribution claims: 120

## Per-method attribution tallies (vs warrant)

| Method | Cells | Agree warrant | Correct decisive | Unsupported support | Missed decisive |
|---|---:|---:|---:|---:|---:|
| `evidencegraph_safer_produced` | 120 | 119 | 57 | 1 | 0 |
| `evidencegraph_legacy_produced` | 120 | 97 | 57 | 23 | 0 |
| `eg_evidence_derived_adapter` | 120 | 119 | 57 | 1 | 0 |
| `naive` | 120 | 63 | 0 | 0 | 57 |
| `weak_checklist` | 120 | 63 | 0 | 0 | 57 |
| `strong_invariant` | 120 | 63 | 0 | 0 | 57 |
| `swarm_witness` | 120 | 63 | 0 | 0 | 57 |

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

Adapter cells: 8; matches native safer executed: 8; adapter refutations: 2; native refutations: 2.

## Reading

If strong/swarm abstain while the evidence-derived adapter recovers native safer boundaries, the missing capability is in the frozen classifiers' consumption of raw observables (they require verifying observation types/polarity). Retain that gap before changing methods.

False-exclusivity: agreement with native safer can coexist with a wrong attribution when both accept the same false exclusivity premise.

Capture-window edge: real-event attributions can remain supported while invented-receipt absence contradictions become unresolved — blanket abstention cannot reproduce that split.

## Result (this freeze)

The frozen evidence-derived adapter preserves EvidenceGraph’s event-level attribution, witness-independence, and capture-window decisions across the paired evidence conditions (adapter matches native safer on every listed boundary; fabricated/executed family 8/8 with native). Strong / Swarm Witness abstain on raw observables (0 correct decisive / 57 missed decisive) — a strong/swarm tie that locates the gap in classifier consumption of verifying observation types, not in the adapter’s boundary logic. Retain that result before changing the method. `transfer_claim` remains false.
