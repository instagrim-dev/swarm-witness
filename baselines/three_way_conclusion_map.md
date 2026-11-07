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
| R5 swarm A/B/C | all three | Contention, delegation chains, cross-agent receipt misuse |

**Handoff / swarm transferability.** A principal’s old receipt does not authorize
a delegate or peer. Without scoped current grant evidence the class is
`missing_evidence`; allowing from a foreign receipt or after shared-grant spend
under a broken gate is `failed_enforcement`; correct assignee + active grant
observation is `supported`. R5 establishes method generalization to a synthetic
three-agent swarm—not unbounded population safety.

This card is an authored interpretation of labels already produced by runners;
it is not itself a Finding.
