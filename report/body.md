# 1. Introduction

An agent presents a receipt from an earlier authorization. A second agent holds a copied receipt. A worker restarts after its owner was revoked. The records may look convincing, and each subsystem may have passing tests, while the alleged right to act is unsupported. As agents delegate work, attribution and current authority become questions about **which observations a reviewer can actually authenticate**.

Swarm Witness asks a precise question: **What evidence is sufficient to justify a safety claim about an agent's decision or effect?** We treat classical reference-monitor behavior as the null control rather than claiming a new authorization primitive. The unit of analysis is an explicit proposition with source pin, assumptions, required observations, measured outcomes and a separately qualified conclusion.

Our weekend contributions are four connected results. First, a reproducible audit substrate assigns typed Claim, Run and Finding records to original source artifacts. Second, a native test-only BMO adapter and independent SQLite monitor test the same bounded first-edit property rather than comparing Go test pass counts. Third, a three-way evidence discipline is checked against missing, misleading and held-out observations. Fourth, an independent causal-event simulator and a larger, fixed R5 test matrix expose where cached local authority diverges from independently recorded effects. A mathematical substrate states exactly when an observation licenses support or refutation.

**Figure 1. Evidence-to-conclusion flow.** A source-pinned claim establishes the proposition; policy and agent-visible evidence produce observations; an independent authority/effect record and comparator determine the supported, refuted, or unresolved result; a separate diagnosis attributes evidence, decision, or effect-boundary failures. No success label is inferred from package exit status alone.

## 2. Background and related work

The original SoundGate study tests whether restart can erase a durable refusal. EvidenceGraph studies why receipt possession does not establish event attribution. Both are valuable prior results and are treated here as validation targets, not as newly discovered failures. The BMO retained-grant owner is preexisting software; our contribution is an independently specified classical comparison and the audit trace binding. Classical security guidance already emphasizes complete mediation and reference monitors [1, 2]. Lamport's causal ordering motivates explicit predecessor records [3], and possible-worlds epistemic semantics provides the mathematical substrate for reasoning from incomplete observations [4].

Unlike a generic test dashboard, Swarm Witness preserves **the difference between correctness of a policy, authenticity of the evidence used by that policy, and execution of an effect**. Its most relevant application is agent-to-agent delegation, where identities and receipts can be copied while authorization may be revoked or spent.

## 3. Methodology

### 3.1 Claim qualification and evidence types

Every claim identifies its source revision, original proposition, operational interpretation, quantifier, success criterion and assumptions. Run records retain execution status and case observations. Finding records bind a proposition and declared scope to supporting references. Evidence checks require applicable source pins, concrete completed observations for positive findings, and consistency between result/index labels. The evaluation method is a separate field: pinned re-execution, later-harness confirmation, native matched comparison, or synthetic protocol conformance.

To prevent category errors, we evaluate four dimensions before projecting a high-level conclusion: **evidence availability/authenticity**, **decision correctness**, **effect commitment**, and **comparison agreement**. A comparison divergence refutes equality, not automatically enforcement. A wrong `allow` that is prevented by an external effect guard differs from a wrong `allow` followed by an unauthorized write.

### 3.2 Pinned replications and native ledger comparison

R1 re-executes the pinned SoundGate recovery-barrier histories for original, strict and barrier policies. R2 confirms the author's later published EvidenceGraph stress harness at `a5ea5c9`; the paper baseline `efbd419` does not contain that runnable stress script.

We preserve two distinct BMO comparisons. R3-D, a proposed decision-model equivalence, is unresolved because its four cases lack matching BMO observations. R3-L1 is an independently specified six-case first-edit ledger protocol. A test-only Go bridge calls BMO's real `ClaimOrdinaryRetainedGrantFirstEditTx` in a disposable, pinned source tree. The classical arm is a SQLite transaction owner. Both receive the same action sequence. The comparator checks every expected step's disposition and property-relevant state, source and bridge qualification, and whether each arm satisfies its own declared property. Scope: one-use claims, transaction rollback and cold database reopen, not execution settlement.

### 3.3 An evidence discipline with formal semantics

Let `W` be a set of possible worlds, `P ⊆ W` the worlds satisfying the proposition, and `Γ(o)` the **nonempty compatible worlds** under authenticated observations `o`. Support is licensed when `Γ(o) ⊆ P`; refutation when `Γ(o) ∩ P = ∅`; otherwise the proposition is unresolved. Invalid evidence or empty compatibility sets do not produce a vacuous conclusion.

This model yields four useful invariants: (i) support and refutation are sound when the actual world remains in the compatible set; (ii) indistinguishable worlds with opposite truth values remain unresolved; (iii) irrelevant information cannot change the judgment; and (iv) verified refinement cannot flip an already supported result into refuted without violating the assumptions. Proofs and a separately encoded exhaustive four-world checker are provided in the supplement. The high-level three-way labels apply only to a declared **property**; causal failure attribution remains orthogonal.

### 3.4 Causal interleaving experiment and expanded R5

We introduce a deterministic scheduler over three principals, with explicit issue, delegation, capture, delayed delivery, revoke, claim, receipt delivery and effect events. Agents see only delivered snapshots. An authoritative grant ledger maintains current state. A reference monitor checks that state at claim; a deliberately defective alternative trusts cached local evidence or possession of a foreign receipt. A separately implemented oracle reconstructs authority and effect validity from event history and a distinct effect ledger. The same schedule is run on both policies.

The base experiment fixes eight scenarios across six dimensions, including A-before-B and B-before-A contention, stale revocation evidence, paired active/revoked worlds with identical local views, irrelevant observations, multihop delegation and receipt replay. The versioned R5 extension fixes **13 scenarios across nine dimensions**, 26 policy executions. Cases and expected counts live in a manifest separate from the policy implementation; a checker verifies the actual trace rather than trusting the policy's asserted outcome.

## 4. Results

**Table 1. Measured audit outcomes, separated by evaluation method.**

| Study | Observations | Warranted result |
|---|---|---|
| R1, SoundGate pinned re-execution | 153 histories per policy; original 143 prohibited effects; barrier 0 | Published recovery-barrier effect confirmed under pinned histories |
| R2, EvidenceGraph later-harness confirmation | 36/36 condition-by-seed checks; older relay attribution errors in each of 3 seeds | Later published stress contrast confirmed |
| R3-D, legacy decision-model | 0/4 BMO case mappings established | Comparison remains unresolved, not a negative BMO result |
| R3-L1, native BMO vs SQLite | 6/6 declared cases satisfy properties in each arm; stepwise selected projections match | Classical baseline matches for the bounded first-edit property |
| R4, evidence qualification | 18 synthetic/held-out cases; 5 missing-evidence, 6 failure, 7 supported | Classification handles blind, misleading and authentic evidence under its model |
| R5 v1, sequential multi-principal | 10 declared cases across A/B/C | Three-way conclusion conformance in a sequential grant model |
| New causal simulator | 8 schedules × 2 policies; reference 0 unauthorized effects, defective arm 6 | Causal event traces distinguish local evidence from committed effects |
| New R5 v2 matrix | 13 schedules × 2 policies; reference 0 unauthorized effects, defective arm **9**; defective arm 10 incorrect decisions | Fixed scenario corpus distinguishes authorization errors from actual effects |
| Formal evidence checker | 4 worlds; all 16 property masks and 16 evidence masks; 2,646 finite checks | Finite checks uphold the proved set-theoretic soundness laws |

**Table 2. Two-world discriminator and causal consequence.** The old grant snapshot is identical in the active and revoked worlds. The authoritative monitor permits the valid action and refuses the revoked action. A stale-local monitor allows both; the independent effect observer identifies the unauthorized commit in the revoked world. An irrelevant message changes neither the cached authority observation nor the conclusion.

| World / control | Cached agent evidence | Current authoritative state | Reference decision | Faulty local decision | Faulty-arm unauthorized effects |
|---|---|---|---|---|---|
| A, still valid | Old active snapshot | Active | Allow | Allow | 0 |
| B, revoked | Same old active snapshot | Revoked | Deny | Allow | 1 |
| B plus irrelevant message | Same old active snapshot | Revoked | Deny | Allow | 1 |

The case is important because mere addition of a receipt or log line does not resolve the ambiguity. The differentiating fact is independently current authority. Equally, discovering a misleading observation does not necessarily identify an incorrect gate algorithm: the evidence source, decision rule and effect boundary must be diagnosed separately.

### 4.1 Independent experimental controls

The simulator includes an always-useful authorized path, reversible schedule ordering, a stale-observation mutant, a receipt-replay mutant, an irrelevant-fact control, and independently reconstructed effect ledger records. The R5 v2 matrix exercises incorrect task and epoch scope, missing delegation, delayed observation and missing local views. The oracle flags unauthorized effects and incorrect decisions separately: **9** versus **10** in the defective policy across the fixed matrix. These are counts over designed test schedules, not estimates of real-world attack prevalence.

The mathematical checker independently implements compatible-world set semantics, rather than importing the production conclusion classifier. It exhaustively checks support/refutation soundness, non-identifiability, irrelevant-information non-upgrade, verified refinement and rejection of unverifiable or inconsistent evidence. A countermodel proves that two secure implementations can disagree on a projection without either violating its security property. The three-way category is therefore a conservative reporting projection, not an exhaustive causal explanation.

## 5. Discussion and limitations

The combined result is a reusable **evidence qualification standard** for agent authorization research. It can confirm a published behavior, establish a bounded classical reduction, refuse a comparison with missing observations, and identify a faulty local-evidence policy through separately recorded effects. The formal substrate explains why additional verified information is required before a conclusion can be upgraded. In delegation settings, the question shifts from whether a receipt exists to whether its source, scope, recency and causal owner are sufficient for the claimed action.

The evaluation deliberately spans different evidence strengths. R1 is source-pinned re-execution; R2 confirms a later author-published harness; R3-L1 evaluates the actual BMO transaction owner against a conventional gate; R4/R5 and the new causal experiments are bounded authored models. The interleaving scheduler deterministically explores supplied orders rather than executing concurrent workers, and the finite checker establishes properties of its specified semantics rather than arbitrary deployed agent systems. Source-independent effect observation in the simulator is independence between model ledgers, not an independent physical auditor. These boundaries determine where the reported result applies.

Next steps are live gateway-side observation, real delegated effects, independently authored case corpora, and integration of the formal evidence semantics into the audit schema. These follow naturally from the demonstrated experimental contract; no novel cryptography is required for the present claim.

## 6. Conclusion

Agent-safety claims should be no stronger than the observations that discriminate safe from unsafe worlds. Swarm Witness turns that rule into executable research practice: source-pinned claims, conventional baselines, explicit unknown results, an independently observed synthetic effect boundary, and a formal standard for when evidence warrants support. The primary finding is not that agent authorization requires a new primitive. It is that **a test can pass while the safety claim remains unwarranted, and a well-designed audit can make the difference mechanically visible**.

## Code, data and reproducibility

The review bundle contains retained R1/R2/R3/R4/R5 evidence, the native BMO L1 bridge, the causal simulator, the R5 v2 manifest, the finite proof checker, and associated tests. Key entrypoints are `experiments/causal_swarm/run.py`, `experiments/r5_v2/run.py`, and `theory/check_taxonomy.py`. Selected BMO pin: `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe`. Pinned R1 and R2 sources are listed in `artifacts/pins.yaml`. GitHub: `https://github.com/instagrim-dev/swarm-witness`; supply the attached portable bundle if repository read access is restricted.
