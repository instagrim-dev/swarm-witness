# Swarm Witness: An Executable Evidence Protocol for Agent Authorization Claims

**Research track:** 3, Strengthening Agent Infrastructure. **Application:** multi-agent oversight and forensic evidence evaluation (Track 4).

**Author:** Jonathan Maye-Hobbs  
**Affiliation:** Independent

## Abstract

Agent systems generate receipts, decisions, traces and recovery records, yet a successful test does not automatically justify the security claim made about it. We introduce **Swarm Witness**, an executable evidence protocol that binds authorization claims to specified observations and reports whether those observations support, refute, or leave the claim unresolved, while recording evidence provenance, decision correctness and committed effects separately. The method combines source-pinned re-execution and later-harness confirmation of prior studies, a native BMO versus SQLite reference-monitor comparison, a three-way evidence-conclusion evaluator, and a separately implemented finite-world checker. We extend evaluation to deterministic multi-principal interleavings with a distinct modeled effect ledger. Across six native BMO ledger cases, both arms satisfy the declared one-use properties. In 14 fixed multi-principal scenarios (28 policy runs), a separately implemented trace oracle detects **nine unauthorized effects** under a deliberately faulty local-evidence policy and **zero** under the authoritative reference monitor. Paired worlds show why identical cached grant observations cannot establish current permission. The package provides executable counterexamples, provenance-bound findings and a foundation for rigorous agent delegation audits.

# 1. Introduction

An agent presents a receipt from an earlier authorization. A second agent holds a copied receipt. A worker restarts after its owner was revoked. The records may look convincing, and each subsystem may have passing tests, while the alleged right to act is unsupported. As agents delegate work, attribution and current authority become questions about **which observations a reviewer can actually authenticate**.

Swarm Witness asks a precise question: **What evidence is sufficient to justify an authorization claim about an agent's decision or effect?** We treat classical reference-monitor behavior as the null control rather than claiming a new authorization primitive. The unit of analysis is an explicit proposition with source pin, assumptions, required observations, measured outcomes and a separately qualified conclusion. Swarm Witness binds authorization claims to specified observations and reports whether those observations support, refute, or leave the claim unresolved, while recording evidence provenance, decision correctness, and committed effects separately.

Weekend contributions: a typed Claim/Run/Finding audit substrate; a native BMO versus SQLite first-edit comparison; a three-way evidence discipline over missing, misleading and held-out observations; and a causal-event simulator with a separately implemented oracle plus a fixed R5 matrix that separates cached local authority from distinct modeled effects. A mathematical substrate states when an observation licenses support or refutation.

**Figure 1. Evidence-to-conclusion flow.** A source-pinned claim specifies the proposition; policy and agent-visible evidence produce observations; a distinct modeled authority/effect record and comparator determine the supported, refuted, or unresolved result; a separate diagnosis attributes evidence, decision, or effect-boundary failures. No success label is inferred from package exit status alone.

## 2. Background and related work

The original SoundGate study tests whether restart can erase a durable refusal. EvidenceGraph studies why receipt possession does not establish event attribution. Both are valuable prior results and are treated here as validation targets, not as newly discovered failures. The BMO retained-grant owner is preexisting software; our contribution is an independently specified classical comparison and the audit trace binding. Classical security guidance already emphasizes complete mediation and reference monitors [1, 2]. Lamport's causal ordering motivates explicit predecessor records [3], and possible-worlds epistemic semantics provides the mathematical substrate for reasoning from incomplete observations [4].

Unlike a generic test dashboard, Swarm Witness preserves **the difference between correctness of a policy, authenticity of the evidence used by that policy, and execution of an effect**. Its most relevant application is agent-to-agent delegation, where identities and receipts can be copied while authorization may be revoked or spent.

## 3. Methodology

### 3.1 Claim qualification and evidence types

Every claim identifies its source revision, original proposition, operational interpretation, quantifier, success criterion and assumptions. Run records retain execution status and case observations. Finding records bind a proposition and declared scope to supporting references. Evidence checks require applicable source pins, concrete completed observations for positive findings, and consistency between result/index labels. The evaluation method is a separate field: source-pinned re-execution, later-harness confirmation, native matched comparison, or synthetic protocol conformance.

To prevent category errors, we evaluate four dimensions before projecting a high-level conclusion: **evidence availability/authenticity**, **decision correctness**, **effect commitment**, and **comparison agreement**. A comparison divergence refutes equality, not automatically enforcement. A wrong `allow` that is prevented by an external effect guard differs from a wrong `allow` followed by an unauthorized write.

### 3.2 Pinned replications and native ledger comparison

R1 is a source-pinned re-execution of the SoundGate recovery-barrier histories for original, strict and barrier policies. R2 is a later-harness confirmation of the author's published EvidenceGraph stress harness at `a5ea5c9`; the paper baseline `efbd419` does not contain that runnable stress script.

We preserve two distinct BMO comparisons. R3-D, a proposed decision-model equivalence, is unresolved because its four cases lack matching BMO observations. R3-L1 is an independently specified six-case first-edit ledger protocol. A test-only Go bridge calls BMO's real `ClaimOrdinaryRetainedGrantFirstEditTx` in a disposable, pinned source tree. The classical arm is a SQLite transaction owner. Both receive the same action sequence. The comparator checks every expected step's disposition and property-relevant state, source and bridge qualification, and whether each arm satisfies its own declared property. Scope: one-use claims, transaction rollback and cold database reopen, not execution settlement.

### 3.3 An evidence discipline with formal semantics

Let `W` be a set of possible worlds, `P ⊆ W` the worlds satisfying the proposition, and `Γ(o)` the **nonempty compatible worlds** under authenticated observations `o`. Support is licensed when `Γ(o) ⊆ P`; refutation when `Γ(o) ∩ P = ∅`; otherwise the proposition is unresolved. Invalid evidence or empty compatibility sets do not produce a vacuous conclusion.

This model yields four useful invariants: (i) support and refutation are sound when the actual world remains in the compatible set; (ii) indistinguishable worlds with opposite truth values remain unresolved; (iii) irrelevant information cannot change the judgment; and (iv) for a fixed proposition about a fixed event or time, consistent refinement of a nonempty compatible-world set preserves support or refutation. Proofs and a separately implemented exhaustive four-world checker are provided in the supplement. The high-level three-way labels apply only to a declared **property**; causal failure attribution remains orthogonal. The proofs apply to the specified set semantics; the current audit evaluator is evaluated through the declared scenario corpus.

### 3.4 Causal interleaving experiment and expanded R5

We introduce a deterministic scheduler over three principals, with explicit issue, delegation, capture, delayed delivery, revoke, claim, receipt delivery and effect events. Agents see only delivered snapshots. An authoritative grant ledger maintains current state. A reference monitor checks that state at claim; a deliberately defective alternative trusts cached local evidence or possession of a foreign receipt. Claim events decide and atomically record modeled commits. A separately implemented oracle reconstructs authority from event history and checks the distinct effect records against that reconstruction. The same schedule is run on both policies.

The base experiment fixes nine scenarios across six dimensions, including A-before-B and B-before-A contention, stale revocation evidence, paired active/revoked worlds with identical local grant observations, irrelevant observations, multihop delegation, and a receipt-present versus receipt-absent pair in which C has no qualifying local view. The versioned R5 extension fixes **14 scenarios across nine dimensions**, 28 policy executions. Cases and expected counts live in a manifest separate from the policy implementation; a checker verifies the actual trace rather than trusting the policy's asserted outcome.

## 4. Results

**Table 1. Measured audit outcomes, separated by evaluation method.**

| Study | Observations | Warranted result |
|---|---|---|
| R1, SoundGate source-pinned re-execution | 153 histories per policy; original 143 prohibited effects; barrier 0 | Published recovery-barrier effect confirmed under pinned histories |
| R2, EvidenceGraph later-harness confirmation | 36/36 condition-by-seed checks; older relay attribution errors in each of 3 seeds | Later published stress contrast confirmed |
| R3-D, legacy decision-model | 0/4 BMO case mappings established | Comparison remains unresolved, not a negative BMO result |
| R3-L1, native BMO vs SQLite | 6/6 declared cases satisfy properties in each arm; stepwise selected projections match | Classical baseline matches for the bounded first-edit property |
| R4, evidence qualification | 18 synthetic/held-out cases; 5 missing-evidence, 6 failure, 7 supported | Classification handles blind, misleading and authentic evidence under its model |
| R5 v1, sequential multi-principal | 10 declared cases across A/B/C | Three-way conclusion conformance in a sequential grant model |
| New causal simulator | 9 schedules × 2 policies; reference 0 unauthorized effects, defective arm 6 | Causal event traces distinguish local evidence from committed effects |
| New R5 v2 matrix | 14 schedules × 2 policies; reference 0 unauthorized effects, defective arm **9**; defective arm 10 incorrect decisions | Fixed scenario corpus distinguishes authorization errors from actual effects |
| Formal evidence checker | 4 worlds; all 16 property masks and 16 evidence masks; 2,646 finite checks | Finite checks uphold the proved set-theoretic soundness laws |

**Worked example (R3-D).** ClassicalGate completes all four shared cases with the expected decisions. The stronger claim—matched decision-model equivalence with BMO—requires isomorphic BMO observations that are absent (0/4). The audit returns **unresolved** / `missing_evidence` (`r3-f-comparison`): not affinity support and not a negative BMO result. R4's aggregate `passed: true` only means expected classifier labels (including missing-evidence), not a misleadingly passing safety test.

**Table 2. Two-world discriminator and causal consequence.** The old grant snapshot is identical in the active and revoked worlds. The authoritative monitor permits the valid action and refuses the revoked action. A stale-local monitor allows both; the distinct effect ledger identifies the unauthorized commit in the revoked world. An irrelevant message changes neither the cached grant observation nor the conclusion.

| World / control | Cached agent evidence | Current authoritative state | Reference decision | Faulty local decision | Faulty-arm unauthorized effects |
|---|---|---|---|---|---|
| A, still valid | Old active snapshot | Active | Allow | Allow | 0 |
| B, revoked | Same old active snapshot | Revoked | Deny | Allow | 1 |
| B plus irrelevant message | Same old active snapshot | Revoked | Deny | Allow | 1 |

Mere addition of a receipt or log line does not resolve the ambiguity; independently current authority does. A misleading observation also need not imply a wrong gate algorithm: evidence source, decision rule and effect boundary are diagnosed separately.

### 4.1 Independent experimental controls

Controls include an authorized path, reversible ordering, stale-observation mutant, receipt-present versus receipt-absent pair (no qualifying local view for C), irrelevant-fact control, and distinct modeled effect-ledger records. R5 v2 adds incorrect task/epoch scope, missing delegation, delayed observation and missing local views. The oracle separates unauthorized effects from incorrect decisions (**9** vs **10** under the defective policy). Counts are over designed schedules, not prevalence estimates.

The separately implemented checker exhausts support/refutation soundness, non-identifiability, irrelevance, verified refinement and rejection of unverifiable evidence. A schematic counterexample shows two secure implementations can disagree on a projection without either violating its property. Three-way labels remain a conservative reporting projection.

## 5. Discussion and limitations

The combined result is a reusable **proposed evidence standard** for agent authorization research: confirm published behavior, establish a matched classical comparison on the six declared first-edit cases, refuse comparisons with missing observations, and identify faulty local-evidence policies via separately recorded effects. In delegation settings, the question is whether a receipt's source, scope, recency and causal owner suffice for the claimed action.

Evidence strengths differ by design: R1 source-pinned re-execution; R2 later-harness confirmation; R3-L1 native BMO versus a conventional gate; R4/R5 and the causal experiments as bounded authored models. The scheduler explores supplied orders, not concurrent workers; the finite checker covers its specified semantics, not arbitrary deployments. Distinct modeled effect records are ledger separation inside the model, not a physical auditor. Atomic claim/commit means schedules do not cover revocation between decision and later execution.

Next steps: live gateway observation, real delegated effects, independently authored corpora, and integrating the formal semantics into the audit schema.

## 6. Conclusion

Authorization claims should be no stronger than the observations that discriminate safe from unsafe worlds. Swarm Witness turns that into executable practice: source-pinned claims, conventional baselines, explicit unknowns, a distinct modeled effect boundary, and a formal warrant rule. As in R3-D, a classical test can complete while a stronger matched claim remains **unresolved** for missing observations. Successful execution, selected-observation agreement, and support for a stated property are distinct outcomes.

## Code, data and reproducibility

The review bundle contains retained R1/R2/R3/R4/R5 evidence, the native BMO L1 bridge, the causal simulator, the R5 v2 manifest, the finite proof checker, and associated tests. Key entrypoints are `experiments/causal_swarm/run.py`, `experiments/r5_v2/run.py`, and `theory/check_taxonomy.py`. Selected BMO pin: `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe`. Pinned R1 and R2 sources are listed in `artifacts/pins.yaml`. GitHub: `https://github.com/instagrim-dev/swarm-witness`; supply the attached portable bundle if repository read access is restricted.

## References

1. Saltzer, J. H. and Schroeder, M. D. (1975). The protection of information in computer systems. *Proceedings of the IEEE*, 63(9), 1278–1308. https://doi.org/10.1109/PROC.1975.9939.
2. Schneider, F. B. (2000). Enforceable security policies. *ACM Transactions on Information and System Security*, 3(1), 30–50. https://doi.org/10.1145/353323.353382.
3. Lamport, L. (1978). Time, clocks, and the ordering of events in a distributed system. *Communications of the ACM*, 21(7), 558–565. https://doi.org/10.1145/359545.359563.
4. Fagin, R., Halpern, J. Y., Moses, Y. and Vardi, M. Y. (1995; paperback ed. 2004). *Reasoning About Knowledge*. MIT Press. https://mitpress.mit.edu/9780262562003/reasoning-about-knowledge/.
5. *A Restart Is Not Permission: When an Agent Gate Forgets No.* Apart Swarm Alignment project, 2026. https://apartresearch.com/sprints/projects/a-restart-is-not-permission-when-an-agent-gate-forgets-no-ga92.
6. Junejo, R. (2026). *Receipt Possession Is Not Event Attribution*. Apart Swarm Alignment project. https://apartresearch.com/sprints/projects/ryan-junejo-4omn.
7. Swarm Witness. Source and evidence package, November 2026. https://github.com/instagrim-dev/swarm-witness.

# Appendix A. Limitations and dual-use / ethical considerations

**Evidence and domain limits.** Claims are bounded to specified artifacts, synthetic schedules and formal assumptions. The BMO result covers an L1 transactional owner and selected projections, not full execution safety. Simulator principals share deterministic scheduling and modeled state; they are not live agents and do not establish emergent coordination. Proofs assume authenticated compatible-world evidence with the actual world inside the compatible set. Falsified observations or an unsound compatibility model can invalidate those premises. Incomplete evidence leaves more worlds compatible and may require an unresolved conclusion. Neither the taxonomy nor the finite checker proves those premises for external datasets. The proofs apply to the specified set semantics; the audit evaluator is assessed on the declared scenario corpus.

**Possible adversarial use.** Audits that expose stale-authority, receipt-replay or delegation errors could help an attacker find where a system trusts old evidence. We release bounded schedules, retained artifacts and counterexamples—not production credentials, exploit code or secret access paths. Synthetic failing-policy modes are isolated from production BMO.

**Prior-work disclosure.** BMO and prior SoundGate/EvidenceGraph mechanisms are preexisting; this sprint's novel artifacts are the typed audit, classical comparison harness, causal simulation and formalized evidence-verdict program.

**LLM usage statement.** AI assistants contributed to brainstorming, implementation, validation and drafting. Reported counts come from retained outputs and tests; authors remain responsible for verifying released artifacts and the manuscript.
