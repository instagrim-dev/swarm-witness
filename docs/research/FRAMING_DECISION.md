# Decision: an implemented inter-agent architecture and its transferable evidence contracts

**Status:** selected by the user on 8 November 2026.  
**Applies to:** the Swarm Witness paper, repository introduction, result summaries and subsequent implementation work.  
**Canonical manuscript:** `report/Swarm_Witness_Final_Submission.md`. Keep the current registered/publication title unless the user explicitly changes it.

## Central thesis

> Delegated agents need authority and outcome evidence that retain their meaning across ownership, execution and recovery boundaries. BMO supplies implemented mechanisms for those boundaries. Swarm Witness extracts and independently exercises selected transaction and settlement contracts, then varies the observations available to an assessor to determine which conclusions they justify.

The contribution is architecture-backed and experimentally inspectable. It is neither merely a receipt-labeling convention nor a claim that BMO invented authorization. BMO's existing mechanisms make the problem concrete; the new work is the contract extraction, independent reference implementation, staged evidence comparison, negative controls and evidence-sufficiency analysis. [S03–S05, S15–S23]

## Roles that must never be conflated

| Name | Role | What it establishes here |
|---|---|---|
| BMO | Preexisting implementation with ownership, delegated authority, execution and settlement mechanisms | A concrete system from which selected contracts are measured. Broader source surfaces are architectural context. |
| Classical ledger/reference implementation | Separately implemented selected transaction and settlement contract | Bounded implementation-independent conformance; not a rival that must lose. |
| Swarm Witness research instrument | Study protocols, staged observations, warrants, comparisons and retained evidence | Makes gaps between system behavior and warranted inference observable. |
| Swarm Witness qualifier | One evaluated decision implementation, versioned over time | Its answers are observations of the study, not the study's correctness labels. |
| Invariant checker | A concrete comparator under declared evidence requirements | An experimental control, not a universal guarantee of correctness. |
| EvidenceGraph adapter/assessor | Structured semantic inference and premise admission | Its derived answers and assumptions are part of the composed method, not independent ground truth. |

BMO's subordinate peer supervisor explicitly requires configuration and owner-provided admission. Do not describe it as an automatically enabled, universal cross-platform backend. A signature authenticates a delegation envelope; the App must still join it to current authority state. [S15, S16]

## Transferability: three distinct claims

1. **Architectural reuse:** source-backed design for maintaining authority and outcome evidence across agent boundaries. This is a defensible interpretation of the implemented BMO mechanisms, not a numerical deployment result.
2. **Contract portability:** BMO and the separately implemented SQLite arm satisfy the same selected contract on the declared ledger and settlement cases. Describe this as **bounded two-implementation conformance**, or **bounded evidence of contract portability**. It is not formal equivalence of the complete systems. [S03–S05]
3. **External empirical transfer:** integration and evaluation in an unrelated agent platform or independently selected claim family. Not established by the retained experiments. Its absence does not erase the first two claims and is not a prerequisite for publishing them.

Two implementations written by the same author are separately implemented, not independently curated or independently adjudicated. Do not equate model agreement with independent verification.

## Hypothesis-to-evidence trajectory

| ID | Testable proposition | Delivered evidence | Interpretation |
|---|---|---|---|
| H1 | A correctly committed first-edit claim does not by itself determine whether the edit applied. | S01/S02 are unresolved at the claim stage and diverge only with bound terminal records. | Correct authorization and observed execution are distinct. |
| H2 | The selected settlement contract can distinguish bound applied, bound no-effect and invalid/missing terminal evidence. | S01 applied; S02 definite no-effect; S03–S09 refusal and unresolved effect-applied proposition in both arms. | The contract resolves uncertainty only at the appropriate boundary in these cases. |
| H3 | Agreement with controlled truth can conceal an insufficient evidence warrant. | Historical evaluator: eleven affirmative effect-safety answers with unresolved warrants, despite true underlying propositions. Later replay preserves decisive coverage while resolving those cases differently. | A positive diagnostic research finding, plus a versioned implementation repair. |
| H4 | An observation representation and its translation are part of the evaluated method. | 130-packet composition preserves adapter decisions and its known assumption limitations; raw classifiers abstain on the 70-packet slice. | Composition fidelity and representation capability must be distinguished from independent correctness. |

H1/H2 do not say BMO fails. BMO's measured settlement behavior is a **positive example of an implemented boundary that respects its evidence contract**. H3's component defect does not imply the research hypothesis failed. H4 does not prove external evaluator transfer. [S03–S14]

## Proposition discipline

- `effect-applied` in the settlement protocol: whether the claimed edit applied according to the bound terminal contract. S02 refutes this proposition only.
- `P_commitment`: whether a relevant effect committed.
- `P_effect`: whether unauthorized downstream effects did not commit in the declared scope. An authorized observed commit does not by itself prove complete safety.
- `P_system`: the declared conjunction of boundary properties.
- A refusal to settle does not prove no effect. A no-effect settlement is not a mechanism failure. A malformed input rejection is not automatically an epistemic refutation.

## Wording decisions

Lead with the experimental finding: **truth, control correctness and evidentiary justification can separate, and the study identifies the records that resolve those distinctions.**

Use “supports with unresolved warrants” or “affirmative judgments not justified by the supplied observations” in reader-facing prose when that is the precise phenomenon. Keep existing machine identifiers such as `unsupported_support` intact for traceability. Do not rename schemas merely to improve tone.

Version every statement about eleven versus zero. Table N is the historical qualifier; Table N2 is the repaired 48-packet replay. The newer 16-case challenge is another denominator and still contains disagreements and input rejections. Do not call the eleven historical outcomes the current qualifier's results. [S06, S07]

## Novelty and inherited mechanisms

BMO, SoundGate and EvidenceGraph are preexisting systems. The current study contributes new comparisons and observation interventions, not retroactive invention of their mechanisms. Classical reasoning is the null/reference contract. Matching it can demonstrate portability and calibration; superiority is not required. [S23]

## Out of scope for this decision

A universal proof of agent safety; hostile-host telemetry guarantees; measured deployment reliability; end-to-end live BMO edit execution from fixture-authored settlement rows; a new backend; a general agent simulator; claims about every broader BMO authority path based only on S01–S09.

## Release criterion

The selected architecture-backed claim remains stable. Implementation findings may narrow particular results, but must not silently replace the contribution with either “just packaging” or “general swarm safety.” A null comparison and a diagnosed component failure are publishable when their propositions, observations and mechanisms are explicit.
