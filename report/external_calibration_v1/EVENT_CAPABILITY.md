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

Adapter vs safer on listed boundaries: 84/84.

Adapter vs safer on all attribution packets: 120/120.

## Fabricated / successful-execution family

**8 native execution comparisons** + **2 additional controls** (total cells 10; not ten exported native execution decisions).

Adapter matches the execution reference mapping: 10/10 (on native-executed only: 8/8). Adapter refutations: 2; native refutations among exported executed relations: 2.

Describe as 8 native execution comparisons + 2 additional controls (relay spoofed receipts with no exported executed relation, mapped unresolved). Do not imply ten exported native execution decisions.

## Warrant qualification (secondary)

Attribution warrants use the adapter’s support verdict as the public-evidence sufficiency predicate. Execution warrants consult native refutation status when an exported executed relation is present. Assessor inputs remain independent of native fields, but warrants are not fully independent of evaluated methods. **Primary result:** `adapter_vs_native_safer_conformance`.

## Reading

Use regenerated attribution counts: safer/adapter 48 correct decisive, 10 unsupported supports, and 1 factually wrong supported attribution. Strong/Swarm Witness: 48 missed decisive (replacing the earlier 57).

The ten unsupported supports are the false-exclusivity premise convention (all ten safer/adapter supports marked unwarranted, including correct event identities).

Classifier abstention on these raw packets means the frozen classifiers do not consume them as verifying evidence. That does not establish adapter correctness; adapter vs native safer is the conformance column.

Capture-window edge: real-event attributions can remain supported while invented-receipt absence contradictions become unresolved — blanket abstention cannot reproduce that split.

## Result (this freeze)

Propositions and candidate sets are selected from public entities; native object_ids/candidates/outcomes are scoring-only for assessor inputs. The adapter computes receipt-commitment matching, temporal compatibility, affirmative exclusivity/independence, and absence under covering capture. Boundary agreement with native safer is the primary conformance result; warrant columns remain qualified as method-dependent. `transfer_claim` remains false.
