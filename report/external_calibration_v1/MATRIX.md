# External calibration v1 — EvidenceGraph + SoundGate + BMO L1 + LessWrong + transfer probe

Retrospective calibration of the frozen classifier ladder against prior retained disciplines (EvidenceGraph R2 seed-0 attribution; SoundGate R1 restriction vs availability; BMO L1 ledger vs non-settlement; LessWrong reproduction scope), plus a held-out EvidenceGraph ATTR transfer probe on seeds 1–2. Not agreement with the authored strong_invariant baseline alone.

Claims: 31
Matrix rows: 197

## Calibration statements

- EvidenceGraph attribution (seed 0): report warrant agreement and native-safer agreement separately — strong vs warrant 3/4; strong vs safer native 4/4; safer vs warrant 3/4. false_exclusivity is the premise-failure divergence under matched observation access.
- SoundGate: only the matching-policy native arm is scored against each claim. Cross-policy tallies are reference-only. Barrier matches restriction and availability on its own claims; strict matches restriction but fails availability.
- BMO L1: ledger first-edit properties can be supported while the evidentiary claim that those traces establish execution settlement is refuted under declared scope.
- LessWrong: classifiers are scored against author warrants_v1. No independently specified LessWrong executable method is scored. Environment identity is refuted given disclosed differences; certification and upgrade-slot claims stay unresolved.
- Transfer probe (EG ATTR seeds 1–2): not earned on full warrant agreement (6/8); native-safer agreement 8/8.
- Unqualified global 'strong' remains undefined; use earned profile labels in PROFILE_LABELS.md.

## Per-method tallies (vs warranted conclusion)

| Method | Cells | Unsupported support | Unsupported refutation | Justified abstention | Correct decisive | Missed decisive |
|---|---:|---:|---:|---:|---:|---:|
| `bmo_l1_native` | 7 | 0 | 0 | 0 | 7 | 0 |
| `classical_ledger_gate` | 7 | 0 | 0 | 0 | 7 | 0 |
| `evidencegraph_accept_success_claims` | 14 | 10 | 0 | 0 | 4 | 0 |
| `evidencegraph_old_implicit_token_exclusivity` | 14 | 9 | 0 | 1 | 4 | 0 |
| `evidencegraph_safer_independent_binding` | 14 | 3 | 0 | 7 | 4 | 0 |
| `naive` | 31 | 12 | 0 | 1 | 18 | 0 |
| `r3_agreement` | 7 | 0 | 0 | 0 | 7 | 0 |
| `reconstructed_narrative_overread` | 5 | 3 | 0 | 0 | 2 | 0 |
| `soundgate_policy_barrier` | 2 | 0 | 0 | 0 | 2 | 0 |
| `soundgate_policy_original` | 1 | 0 | 0 | 0 | 1 | 0 |
| `soundgate_policy_strict` | 2 | 0 | 0 | 0 | 2 | 0 |
| `strong_invariant` | 31 | 3 | 0 | 9 | 19 | 0 |
| `swarm_witness` | 31 | 3 | 0 | 9 | 19 | 0 |
| `weak_checklist` | 31 | 10 | 0 | 2 | 19 | 0 |

## Per-case matrix

| Corpus | Claim | Scenario | Method | Predicted | Warranted | Category |
|---|---|---|---|---|---|---|
| evidencegraph_r2 | `EG-R2-ATTR-clean-isolated` | clean | `evidencegraph_safer_independent_binding` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-ATTR-clean-isolated` | clean | `evidencegraph_old_implicit_token_exclusivity` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-ATTR-clean-isolated` | clean | `evidencegraph_accept_success_claims` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-ATTR-clean-isolated` | clean | `naive` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-ATTR-clean-isolated` | clean | `weak_checklist` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-ATTR-clean-isolated` | clean | `strong_invariant` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-ATTR-clean-isolated` | clean | `swarm_witness` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-ATTR-relay-possession` | full_receipt_relay | `evidencegraph_safer_independent_binding` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ATTR-relay-possession` | full_receipt_relay | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-relay-possession` | full_receipt_relay | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-relay-possession` | full_receipt_relay | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-relay-possession` | full_receipt_relay | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-relay-possession` | full_receipt_relay | `strong_invariant` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ATTR-relay-possession` | full_receipt_relay | `swarm_witness` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-MUTATION-relay-receipt-present` | full_receipt_relay | `evidencegraph_safer_independent_binding` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-MUTATION-relay-receipt-present` | full_receipt_relay | `evidencegraph_old_implicit_token_exclusivity` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-MUTATION-relay-receipt-present` | full_receipt_relay | `evidencegraph_accept_success_claims` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-MUTATION-relay-receipt-present` | full_receipt_relay | `naive` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-MUTATION-relay-receipt-present` | full_receipt_relay | `weak_checklist` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-MUTATION-relay-receipt-present` | full_receipt_relay | `strong_invariant` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-MUTATION-relay-receipt-present` | full_receipt_relay | `swarm_witness` | supported | supported | correct_decisive |
| evidencegraph_r2 | `EG-R2-ATTR-shared-tokens-no-exclusivity` | shared_tokens_no_attack | `evidencegraph_safer_independent_binding` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ATTR-shared-tokens-no-exclusivity` | shared_tokens_no_attack | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-shared-tokens-no-exclusivity` | shared_tokens_no_attack | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-shared-tokens-no-exclusivity` | shared_tokens_no_attack | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-shared-tokens-no-exclusivity` | shared_tokens_no_attack | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-shared-tokens-no-exclusivity` | shared_tokens_no_attack | `strong_invariant` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ATTR-shared-tokens-no-exclusivity` | shared_tokens_no_attack | `swarm_witness` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ATTR-false-exclusivity` | false_exclusivity | `evidencegraph_safer_independent_binding` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-false-exclusivity` | false_exclusivity | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-false-exclusivity` | false_exclusivity | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-false-exclusivity` | false_exclusivity | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-false-exclusivity` | false_exclusivity | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-false-exclusivity` | false_exclusivity | `strong_invariant` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ATTR-false-exclusivity` | false_exclusivity | `swarm_witness` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ABSENCE-incomplete-capture` | incomplete_capture | `evidencegraph_safer_independent_binding` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ABSENCE-incomplete-capture` | incomplete_capture | `evidencegraph_old_implicit_token_exclusivity` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ABSENCE-incomplete-capture` | incomplete_capture | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2 | `EG-R2-ABSENCE-incomplete-capture` | incomplete_capture | `naive` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ABSENCE-incomplete-capture` | incomplete_capture | `weak_checklist` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ABSENCE-incomplete-capture` | incomplete_capture | `strong_invariant` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2 | `EG-R2-ABSENCE-incomplete-capture` | incomplete_capture | `swarm_witness` | unresolved | unresolved | justified_abstention |
| soundgate_r1 | `SG-R1-RESTRICT-original` | original | `soundgate_policy_original` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-original` | original | `naive` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-original` | original | `weak_checklist` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-original` | original | `strong_invariant` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-original` | original | `swarm_witness` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-strict` | strict | `soundgate_policy_strict` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-strict` | strict | `naive` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-strict` | strict | `weak_checklist` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-strict` | strict | `strong_invariant` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-strict` | strict | `swarm_witness` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-strict` | strict | `soundgate_policy_strict` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-strict` | strict | `naive` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-strict` | strict | `weak_checklist` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-strict` | strict | `strong_invariant` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-strict` | strict | `swarm_witness` | refuted | refuted | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-barrier` | barrier | `soundgate_policy_barrier` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-barrier` | barrier | `naive` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-barrier` | barrier | `weak_checklist` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-barrier` | barrier | `strong_invariant` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-RESTRICT-barrier` | barrier | `swarm_witness` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-barrier` | barrier | `soundgate_policy_barrier` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-barrier` | barrier | `naive` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-barrier` | barrier | `weak_checklist` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-barrier` | barrier | `strong_invariant` | supported | supported | correct_decisive |
| soundgate_r1 | `SG-R1-AVAIL-barrier` | barrier | `swarm_witness` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T01` | T01 | `bmo_l1_native` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T01` | T01 | `classical_ledger_gate` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T01` | T01 | `r3_agreement` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T01` | T01 | `naive` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T01` | T01 | `weak_checklist` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T01` | T01 | `strong_invariant` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T01` | T01 | `swarm_witness` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T02` | T02 | `bmo_l1_native` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T02` | T02 | `classical_ledger_gate` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T02` | T02 | `r3_agreement` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T02` | T02 | `naive` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T02` | T02 | `weak_checklist` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T02` | T02 | `strong_invariant` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T02` | T02 | `swarm_witness` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T03` | T03 | `bmo_l1_native` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T03` | T03 | `classical_ledger_gate` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T03` | T03 | `r3_agreement` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T03` | T03 | `naive` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T03` | T03 | `weak_checklist` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T03` | T03 | `strong_invariant` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T03` | T03 | `swarm_witness` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T04` | T04 | `bmo_l1_native` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T04` | T04 | `classical_ledger_gate` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T04` | T04 | `r3_agreement` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T04` | T04 | `naive` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T04` | T04 | `weak_checklist` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T04` | T04 | `strong_invariant` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T04` | T04 | `swarm_witness` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T05` | T05 | `bmo_l1_native` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T05` | T05 | `classical_ledger_gate` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T05` | T05 | `r3_agreement` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T05` | T05 | `naive` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T05` | T05 | `weak_checklist` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T05` | T05 | `strong_invariant` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T05` | T05 | `swarm_witness` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T06` | T06 | `bmo_l1_native` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T06` | T06 | `classical_ledger_gate` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T06` | T06 | `r3_agreement` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T06` | T06 | `naive` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T06` | T06 | `weak_checklist` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T06` | T06 | `strong_invariant` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-LEDGER-T06` | T06 | `swarm_witness` | supported | supported | correct_decisive |
| bmo_l1 | `BMO-L1-NOT-EXECUTION-SETTLEMENT` | scope | `bmo_l1_native` | refuted | refuted | correct_decisive |
| bmo_l1 | `BMO-L1-NOT-EXECUTION-SETTLEMENT` | scope | `classical_ledger_gate` | refuted | refuted | correct_decisive |
| bmo_l1 | `BMO-L1-NOT-EXECUTION-SETTLEMENT` | scope | `r3_agreement` | refuted | refuted | correct_decisive |
| bmo_l1 | `BMO-L1-NOT-EXECUTION-SETTLEMENT` | scope | `naive` | refuted | refuted | correct_decisive |
| bmo_l1 | `BMO-L1-NOT-EXECUTION-SETTLEMENT` | scope | `weak_checklist` | refuted | refuted | correct_decisive |
| bmo_l1 | `BMO-L1-NOT-EXECUTION-SETTLEMENT` | scope | `strong_invariant` | refuted | refuted | correct_decisive |
| bmo_l1 | `BMO-L1-NOT-EXECUTION-SETTLEMENT` | scope | `swarm_witness` | refuted | refuted | correct_decisive |
| lesswrong_reproduction | `LW-K-release` | reproduction_release | `reconstructed_narrative_overread` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-release` | reproduction_release | `naive` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-release` | reproduction_release | `weak_checklist` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-release` | reproduction_release | `strong_invariant` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-release` | reproduction_release | `swarm_witness` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-certify` | incident_certification | `reconstructed_narrative_overread` | supported | unresolved | unsupported_support |
| lesswrong_reproduction | `LW-K-certify` | incident_certification | `naive` | supported | unresolved | unsupported_support |
| lesswrong_reproduction | `LW-K-certify` | incident_certification | `weak_checklist` | unresolved | unresolved | justified_abstention |
| lesswrong_reproduction | `LW-K-certify` | incident_certification | `strong_invariant` | unresolved | unresolved | justified_abstention |
| lesswrong_reproduction | `LW-K-certify` | incident_certification | `swarm_witness` | unresolved | unresolved | justified_abstention |
| lesswrong_reproduction | `LW-K-census` | reproduction_census | `reconstructed_narrative_overread` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-census` | reproduction_census | `naive` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-census` | reproduction_census | `weak_checklist` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-census` | reproduction_census | `strong_invariant` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-census` | reproduction_census | `swarm_witness` | supported | supported | correct_decisive |
| lesswrong_reproduction | `LW-K-gate` | held_upgrade_slot | `reconstructed_narrative_overread` | supported | unresolved | unsupported_support |
| lesswrong_reproduction | `LW-K-gate` | held_upgrade_slot | `naive` | supported | unresolved | unsupported_support |
| lesswrong_reproduction | `LW-K-gate` | held_upgrade_slot | `weak_checklist` | supported | unresolved | unsupported_support |
| lesswrong_reproduction | `LW-K-gate` | held_upgrade_slot | `strong_invariant` | unresolved | unresolved | justified_abstention |
| lesswrong_reproduction | `LW-K-gate` | held_upgrade_slot | `swarm_witness` | unresolved | unresolved | justified_abstention |
| lesswrong_reproduction | `LW-K-env-scope` | environment_difference | `reconstructed_narrative_overread` | supported | refuted | unsupported_support |
| lesswrong_reproduction | `LW-K-env-scope` | environment_difference | `naive` | supported | refuted | unsupported_support |
| lesswrong_reproduction | `LW-K-env-scope` | environment_difference | `weak_checklist` | refuted | refuted | correct_decisive |
| lesswrong_reproduction | `LW-K-env-scope` | environment_difference | `strong_invariant` | refuted | refuted | correct_decisive |
| lesswrong_reproduction | `LW-K-env-scope` | environment_difference | `swarm_witness` | refuted | refuted | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s1` | clean | `evidencegraph_safer_independent_binding` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s1` | clean | `evidencegraph_old_implicit_token_exclusivity` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s1` | clean | `evidencegraph_accept_success_claims` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s1` | clean | `naive` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s1` | clean | `weak_checklist` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s1` | clean | `strong_invariant` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s1` | clean | `swarm_witness` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s1` | full_receipt_relay | `evidencegraph_safer_independent_binding` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s1` | full_receipt_relay | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s1` | full_receipt_relay | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s1` | full_receipt_relay | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s1` | full_receipt_relay | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s1` | full_receipt_relay | `strong_invariant` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s1` | full_receipt_relay | `swarm_witness` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s1` | shared_tokens_no_attack | `evidencegraph_safer_independent_binding` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s1` | shared_tokens_no_attack | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s1` | shared_tokens_no_attack | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s1` | shared_tokens_no_attack | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s1` | shared_tokens_no_attack | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s1` | shared_tokens_no_attack | `strong_invariant` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s1` | shared_tokens_no_attack | `swarm_witness` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s1` | false_exclusivity | `evidencegraph_safer_independent_binding` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s1` | false_exclusivity | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s1` | false_exclusivity | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s1` | false_exclusivity | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s1` | false_exclusivity | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s1` | false_exclusivity | `strong_invariant` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s1` | false_exclusivity | `swarm_witness` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s2` | clean | `evidencegraph_safer_independent_binding` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s2` | clean | `evidencegraph_old_implicit_token_exclusivity` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s2` | clean | `evidencegraph_accept_success_claims` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s2` | clean | `naive` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s2` | clean | `weak_checklist` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s2` | clean | `strong_invariant` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-clean-isolated-s2` | clean | `swarm_witness` | supported | supported | correct_decisive |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s2` | full_receipt_relay | `evidencegraph_safer_independent_binding` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s2` | full_receipt_relay | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s2` | full_receipt_relay | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s2` | full_receipt_relay | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s2` | full_receipt_relay | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s2` | full_receipt_relay | `strong_invariant` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-relay-possession-s2` | full_receipt_relay | `swarm_witness` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s2` | shared_tokens_no_attack | `evidencegraph_safer_independent_binding` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s2` | shared_tokens_no_attack | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s2` | shared_tokens_no_attack | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s2` | shared_tokens_no_attack | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s2` | shared_tokens_no_attack | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s2` | shared_tokens_no_attack | `strong_invariant` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-shared-tokens-no-exclusivity-s2` | shared_tokens_no_attack | `swarm_witness` | unresolved | unresolved | justified_abstention |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s2` | false_exclusivity | `evidencegraph_safer_independent_binding` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s2` | false_exclusivity | `evidencegraph_old_implicit_token_exclusivity` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s2` | false_exclusivity | `evidencegraph_accept_success_claims` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s2` | false_exclusivity | `naive` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s2` | false_exclusivity | `weak_checklist` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s2` | false_exclusivity | `strong_invariant` | supported | unresolved | unsupported_support |
| evidencegraph_r2_transfer_seeds | `EG-R2-ATTR-false-exclusivity-s2` | false_exclusivity | `swarm_witness` | supported | unresolved | unsupported_support |

## Level label consequence

Do **not** treat an unqualified global `strong` as calibrated. Prefer source-grounded profile labels (attribution / recovery / availability / transaction / reproduction scope) when the corresponding matrix supports them.

Retrospective calibration only; `transfer_claim` remains false until fresh or held-out families are scored.

