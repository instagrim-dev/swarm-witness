# Three-way conclusion map (authored baseline)

Swarm Witness classifies each claim evaluation into exactly one of:

| Conclusion class | Meaning | Default Finding label |
| --- | --- | --- |
| `missing_evidence` | Discriminating observations absent/incomplete | `unresolved` |
| `failed_enforcement` | Evidence complete; property violated | `contradicted_in_scope` |
| `supported` | Evidence complete; property holds | `reproduced` (or `classical_baseline_matches` for matched comparisons) |

## How weekend experiments map

| Experiment | Dominant class | Notes |
| --- | --- | --- |
| R1 SoundGate barrier | `supported` | Complete harness evidence; barrier property holds (`reproduced`) |
| R2 EvidenceGraph stress | `supported` | Complete stress evidence; contract checks hold (`reproduced`) |
| R3 decision-model | `missing_evidence` | No isomorphic BMO observations (`unresolved`) |
| R3 ledger-claim-v1 | `supported` | Native-qualified matched L1 (`classical_baseline_matches`) |
| R4 Worlds A/B + handoff | all three | Executable taxonomy probe, including bounded delegate handoff |
| R4 misbound observation | failed_enforcement | `failure_origin=evidence` (not decision_policy) |
| R4 held-out artifact | failed_enforcement | Externally supplied misleading observation |
| R5 sequential A/B/C | all three | Sequential contention; broken allow → effect prevented |
| R3-L1 arm divergence | comparison_divergent | Equality refuted ≠ failed_enforcement |

**Handoff / multi-principal transferability.** A principal’s old receipt does not
authorize a delegate or peer. Without scoped current grant evidence the class is
`missing_evidence`; allowing from a foreign ledger receipt or after shared-grant
spend under a broken gate is `failed_enforcement` (wrong decision, no
unauthorized effect commit in R5); correct assignee + authentic active grant
observation is `supported`. R5 establishes taxonomy transfer to a sequential
three-principal model—not concurrent swarm dynamics.

This card is an authored interpretation of labels already produced by runners;
it is not itself a Finding.
