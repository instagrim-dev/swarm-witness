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

**Handoff transferability (bounded).** A principal’s old receipt does not authorize
a delegate. Without delegate-scoped current grant evidence the class is
`missing_evidence`; allowing from the principal receipt alone under a revoked
delegate grant is `failed_enforcement`; observing an active delegate grant with
a correct gate is `supported`. This is not a multi-agent population result.

This card is an authored interpretation of labels already produced by runners;
it is not itself a Finding.
