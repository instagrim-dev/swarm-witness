# Swarm Witness: An Executable Evidence Protocol for Agent Authorization Claims

**Author:** Jonathan Maye-Hobbs  
**Affiliation:** Independent  
**With** Apart Research

**Research track:** 3, Strengthening Agent Infrastructure. **Application:** Track 4.

## Abstract

A passing agent-safety check can leave the security claim about that check unwarranted. This paper asks what evidence is sufficient to justify an authorization claim about an agent's decision or effect. On the same-run witness aew-v1-local-control-pass-broader-effect, the ordinary remote URL allowlist passes, actor-only evidence leaves P_effect unresolved, and the application-owned readback refutes P_effect. That pass does not support P_system. On the frozen public comparison, Swarm Witness matches the authored strong_invariant checker: both record 0 unsupported supports, and naive PASS records 24. That tie is agreement with an authored comparator, not an externally calibrated meaning of “strong.” Separately, retrospective external calibration against retained EvidenceGraph, SoundGate, BMO L1, and LessWrong disciplines yields source-grounded profile labels (attribution; restriction and availability; ledger vs non-settlement; reproduction scope), not a single ordered ladder. superiority_claim stays false. External calibration reports warrant agreement and native-method agreement separately; LessWrong has no scored external native method. A seed 1–2 EvidenceGraph ATTR probe does not earn full warrant transfer while the false-exclusivity premise divergence remains.
 The formal guarantee is conditional on the adapter's observation and abstraction assumptions, including that the actual world remains in the compatible set. Public warrants, the controlled comparison of one LessWrong reproduction record, and the twelve-history application witness use separate denominators. The LessWrong post and its appendix are that one public record. They are not the original incident and not the application experiment. Original transcripts and platform logs are unavailable and are not qualification gates. This study does not claim that Swarm Witness detected or prevented the Artifactory or Hugging Face incident. Separately coded verdict logic, author curation of excerpts and warrants, replay from retained inputs, and the observation sources themselves remain different objects.

## 1. Introduction

This paper asks one question: what evidence is sufficient to justify an authorization claim about an agent's decision or effect?

The named same-run witness is aew-v1-local-control-pass-broader-effect, on run aew-v1-run-local-pass-broader-effect. The ordinary remote_url_allowlist test passes. Actor-only evidence leaves P_effect unresolved. The application-owned readback refutes P_effect. A passing allowlist does not support P_system. The witness is a local synthetic control on a SQLite sink the application owns. It is not the Artifactory / Hugging Face incident, and it is not the public LessWrong reproduction.

On the frozen public comparison, Swarm Witness matches the authored strong_invariant checker. Both record 0 unsupported supports. Naive PASS records 24. That tie is not external calibration of “strong.” Retrospective calibration against prior disciplines (report/external_calibration_v1/MATRIX.md) recovers named profiles rather than a single strength ordering. superiority_claim stays false: no held-out run shows a useful advantage over the authored checker under the same evidence budget. The 4–4.5/5 aspiration is not a result. An earlier author-curated staged comparison reported fewer unsupported conclusions than naive PASS and a weak checklist. Mechanical withholding of later-stage evidence is not independent curation. That earlier comparison sits beside the authored-checker tie and does not replace it.

The formal guarantee is conditional on the adapter's observation and abstraction assumptions. Support requires the nonempty compatible set to sit inside the proposition, and refutation requires an empty intersection, only for the finite abstraction declared for that family, and only if the actual world remains in the compatible set. A source hash, a passing test, or assistant agreement does not establish that membership. Separately coded verdict logic, author curation of excerpts and warrants, replay from retained inputs, and the observation sources themselves are different objects. Assistant agreement is not independent verification.

The LessWrong reproduction post and its appendix are one public record. They are not the original incident and not the twelve-history application experiment. Original transcripts and platform logs are recorded unavailable and are not qualification gates. This study does not claim that Swarm Witness detected or prevented the incident.

An agent presents a receipt from an earlier authorization. A second agent holds a copied receipt. A worker restarts after its owner was revoked. The records may look convincing, and each subsystem may have passing tests, while the alleged right to act is unsupported. As agents delegate work, attribution and current authority become questions about which observations a reviewer can actually authenticate. We treat classical reference-monitor behavior as the null control rather than claiming a new authorization primitive. The unit of analysis is an explicit proposition with source pin, assumptions, required observations, measured outcomes and a separately qualified conclusion. Swarm Witness binds authorization claims to specified observations and reports whether those observations support, refute, or leave the claim unresolved, while recording evidence provenance, decision correctness, and committed effects separately.

Weekend contributions: a typed Claim/Run/Finding audit substrate; a native BMO versus SQLite first-edit comparison; a three-way evidence discipline over missing, misleading and held-out observations; and a causal-event simulator with a separately implemented oracle plus a fixed R5 matrix that separates cached local authority from distinct modeled effects. A mathematical substrate states when an observation licenses support or refutation.

Figure 1. Evidence-to-conclusion flow. A source-pinned claim specifies the proposition; policy and agent-visible evidence produce observations; a distinct modeled authority/effect record and comparator determine the supported, refuted, or unresolved result; a separate diagnosis attributes evidence, decision, or effect-boundary failures. No success label is inferred from package exit status alone.

## 2. Related Work

The original SoundGate study tests whether restart can erase a durable refusal. EvidenceGraph studies why receipt possession does not establish event attribution. Both are valuable prior results and are treated here as validation targets, not as newly discovered failures. The BMO retained-grant owner is preexisting software; our contribution is an independently specified classical comparison and the audit trace binding. Classical security guidance already emphasizes complete mediation and reference monitors [1, 2]. Lamport's causal ordering motivates explicit predecessor records [3], and possible-worlds epistemic semantics provides the mathematical substrate for reasoning from incomplete observations [4].

Unlike a generic test dashboard, Swarm Witness preserves the difference between correctness of a policy, authenticity of the evidence used by that policy, and execution of an effect. Its most relevant application is agent-to-agent delegation, where identities and receipts can be copied while authorization may be revoked or spent.

## 3. Methods

3.1 Claim qualification and evidence types

Every claim identifies its source revision, original proposition, operational interpretation, quantifier, success criterion and assumptions. Run records retain execution status and case observations. Finding records bind a proposition and declared scope to supporting references. Evidence checks require applicable source pins, concrete completed observations for positive findings, and consistency between result/index labels. The evaluation method is a separate field: source-pinned re-execution, later-harness confirmation, native matched comparison, or synthetic protocol conformance.

To prevent category errors, we evaluate four dimensions before projecting a high-level conclusion: evidence availability/authenticity, decision correctness, effect commitment, and comparison agreement. A comparison divergence refutes equality, not automatically enforcement. A wrong allow that is prevented by an external effect guard differs from a wrong allow followed by an unauthorized write.

3.2 Pinned replications and native ledger comparison

R1 is a source-pinned re-execution of the SoundGate recovery-barrier histories for original, strict and barrier policies. R2 is a later-harness confirmation of the author's published EvidenceGraph stress harness at a5ea5c9; the paper baseline efbd419 does not contain that runnable stress script.

We preserve two distinct BMO comparisons. R3-D, a proposed decision-model equivalence, is unresolved because its four cases lack matching BMO observations. R3-L1 is an independently specified six-case first-edit ledger protocol. A test-only Go bridge calls BMO's real ClaimOrdinaryRetainedGrantFirstEditTx in a disposable, pinned source tree. The classical arm is a SQLite transaction owner. Both receive the same action sequence. The comparator checks every expected step's disposition and property-relevant state, source and bridge qualification, and whether each arm satisfies its own declared property. Scope: one-use claims, transaction rollback and cold database reopen, not execution settlement.

3.3 An evidence discipline with formal semantics

Let W be a set of possible worlds, P ⊆ W the worlds satisfying the proposition, and Γ(o) the nonempty compatible worlds under authenticated observations o. Support is licensed when Γ(o) ⊆ P; refutation when Γ(o) ∩ P = ∅; otherwise the proposition is unresolved. Invalid evidence or empty compatibility sets do not produce a vacuous conclusion.

This model yields four useful invariants: (i) support and refutation are sound when the actual world remains in the compatible set; (ii) indistinguishable worlds with opposite truth values remain unresolved; (iii) irrelevant information cannot change the judgment; and (iv) for a fixed proposition about a fixed event or time, consistent refinement of a nonempty compatible-world set preserves support or refutation. Proofs and a separately implemented exhaustive four-world checker are provided in the supplement. The high-level three-way labels apply only to a declared property; causal failure attribution remains orthogonal. The proofs apply to the specified set semantics; the current audit evaluator is evaluated through the declared scenario corpus. The formal guarantee is conditional on the adapter's observation and abstraction assumptions. The adapter does not prove that the actual world is in the compatible set, and a passing local check is not a substitute for the declared family.

3.4 Causal interleaving experiment and expanded R5

We introduce a deterministic scheduler over three principals, with explicit issue, delegation, capture, delayed delivery, revoke, claim, receipt delivery and effect events. Agents see only delivered snapshots. An authoritative grant ledger maintains current state. A reference monitor checks that state at claim; a deliberately defective alternative trusts cached local evidence or possession of a foreign receipt. Claim events decide and atomically record modeled commits. A separately implemented oracle reconstructs authority from event history and checks the distinct effect records against that reconstruction. The same schedule is run on both policies.

The base experiment fixes nine scenarios across six dimensions, including A-before-B and B-before-A contention, stale revocation evidence, paired active/revoked worlds with identical local grant observations, irrelevant observations, multihop delegation, and a receipt-present versus receipt-absent pair in which C has no qualifying local view. The versioned R5 extension fixes 14 scenarios across nine dimensions, 28 policy executions. Cases and expected counts live in a manifest separate from the policy implementation; a checker verifies the actual trace rather than trusting the policy's asserted outcome.

## 4. Results

Table 1. Measured audit outcomes, separated by evaluation method.

Worked example (R3-D). ClassicalGate completes all four shared cases with the expected decisions. The stronger claim—matched decision-model equivalence with BMO—requires isomorphic BMO observations that are absent (0/4). The audit returns unresolved / missing_evidence (r3-f-comparison): not affinity support and not a negative BMO result. R4's aggregate passed: true only means expected classifier labels (including missing-evidence), not a misleadingly passing safety test.

Table 2. Two-world discriminator and causal consequence. The old grant snapshot is identical in the active and revoked worlds. The authoritative monitor permits the valid action and refuses the revoked action. A stale-local monitor allows both; the distinct effect ledger identifies the unauthorized commit in the revoked world. An irrelevant message changes neither the cached grant observation nor the conclusion.

Mere addition of a receipt or log line does not resolve the ambiguity; independently current authority does. A misleading observation also need not imply a wrong gate algorithm: evidence source, decision rule and effect boundary are diagnosed separately.

4.1 Independent experimental controls

Controls include an authorized path, reversible ordering, stale-observation mutant, receipt-present versus receipt-absent pair (no qualifying local view for C), irrelevant-fact control, and distinct modeled effect-ledger records. R5 v2 adds incorrect task/epoch scope, missing delegation, delayed observation and missing local views. The oracle separates unauthorized effects from incorrect decisions (9 vs 10 under the defective policy). Counts are over designed schedules, not prevalence estimates.

The separately implemented checker exhausts support/refutation soundness, non-identifiability, irrelevance, verified refinement and rejection of unverifiable evidence. A schematic counterexample shows two secure implementations can disagree on a projection without either violating its property. Three-way labels remain a conservative reporting projection.

4.2 Bounded comparison under partial observation

Public warrants, the controlled comparison, and the application-owned twelve-history witness keep separate denominators. Counts are regenerated from retained runs by python3 scripts/render_bounded_comparison.py. Every method's per-case output is report/bounded_comparison_v1/ledger.csv. Input digests are report/bounded_comparison_v1/source_sha256.json.

On the public layer, twelve claims at two stages give 24 cells per method. Naive PASS has 24 unsupported supports and correct decisive coverage 0 of 2. The strong checker and Swarm Witness each have 0 unsupported supports, 0 unsupported refutations, 22 correct abstentions, and correct decisive coverage 2 of 2. They match on all 24 predicted statuses. The always-unresolved reference also has correct decisive coverage 0 of 2. Unique warranted origins are 0, so attribution coverage is not applicable. The weak checklist is an ablation on this layer, with 11 unsupported supports, and it is not the competent baseline.

On the controlled layer, four claims over three histories give 4 cells. Naive PASS has 2 unsupported supports and 2 supports of false propositions. The strong checker and Swarm Witness have 0 of each, and both abstain on certification and on the held blocks_upgrade slot. Always-unresolved attribution coverage is 0 of 1: a unique origin is available, and that method never assigns it. Record requests are 0.

The application witness is twelve histories, not those cells. On aew-v1-local-control-pass-broader-effect the URL allowlist passes and stays supported, actor-only evidence leaves P_effect unresolved, and the application readback refutes P_effect. A clean covered commit, aew-v1-h-authority-current, supports P_effect and leaves P_system unresolved. Public C04 at stage B stays unresolved for the strong checker and for Swarm Witness. The retained workflow url_held_worker_local_read refutes P_system while P_url stays supported. The native telemetry packet stays unresolved.

A fourth ledger layer scores the same twelve histories under four evidence conditions with matched methods (swarm_witness, always_unresolved, strong_abstention). Adjudication is the discriminating-readback P_effect for each history. The layer adds 144 rows (ledger total 352). Swarm Witness has 0 unsupported supports and matches readback on 12 of 12; strong abstention matches readback on 12 of 12 and refuses the other conditions by design. This is acceptance evidence for native integration, not a superiority claim.

The earlier staged comparison, naive 24 and checklist 12 against Swarm Witness 0 unsupported conclusions, remains the author-curated result. Its ablations stay in the generated table, including text-trust unsupported conclusions of 13. Mechanical withholding of stage B is not independent curation.

4.3 Retrospective external calibration (profile labels)

A separate denominator asks whether the frozen classifiers recover claim-assessment disciplines already demonstrated by prior systems under matched observation access (experiments/external_calibration/). Packets translate retained native assessments under matched observation access. Profiles: EvidenceGraph attribution (warrant agreement vs native-safer agreement, reported separately); SoundGate restriction and availability (matching-policy arms only); BMO L1 ledger vs evidentiary non-settlement; LessWrong scope scored against author warrants only—no external LW native method is claimed. A seed 1–2 ATTR probe reports warrant and native-safer transfer separately (PROFILE_LABELS.md). Naive and weak checklist identify specific shortcuts. “Strong” means conformance to a named applicable profile, not an unqualified global grade.

## 5. Discussion and Limitations

The combined result is a reusable proposed evidence standard for agent authorization research: confirm published behavior, establish a matched classical comparison on the six declared first-edit cases, refuse comparisons with missing observations, and identify faulty local-evidence policies via separately recorded effects. In delegation settings, the question is whether a receipt's source, scope, recency and causal owner suffice for the claimed action.

Evidence strengths differ by design: R1 source-pinned re-execution; R2 later-harness confirmation; R3-L1 native BMO versus a conventional gate; R4/R5 and the causal experiments as bounded authored models. The scheduler explores supplied orders, not concurrent workers; the finite checker covers its specified semantics, not arbitrary deployments. Distinct modeled effect records are ledger separation inside the model, not a physical auditor. Atomic claim/commit means schedules do not cover revocation between decision and later execution.

For the 2026 OpenAI–Hugging Face agent-swarm incident, the evidence standard is the public LessWrong reproduction by Palan, Chute, Kim, and Van Roy (https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment). Original agent transcripts and platform logs are unavailable. Acceptance and qualification use that reproduction and the executable protocols in this package. No criterion requires the withheld originals. Where a public proposition cannot be adjudicated, the warrant stays unresolved.

Author reassessment against this completed evidence, not a judge outcome:

Impact/innovation: 3/5. Constraint: Swarm Witness ties the authored strong_invariant checker on the frozen public comparison (both 0 unsupported supports; naive PASS has 24). That tie is not an external meaning of “strong.” Retrospective profile calibration against EvidenceGraph, SoundGate, BMO L1, and LessWrong is reported separately; superiority_claim stays false. Warrant vs native-method agreements are not collapsed. The seed 1–2 ATTR probe does not earn full warrant transfer. No held-out run shows a useful advantage under the same evidence budget. The 4–4.5/5 aspiration is not a result.

Execution: 3/5. Constraint: tables were regenerated from retained data, and the advertised commands were rerun from a fresh review-bundle extract in this environment without private BMO access. No separate reviewer reproduced the study. Assistant agreement is not independent verification.

Clarity: 4/5. Constraint: this is an author judgment that the manuscript states one question, the witness aew-v1-local-control-pass-broader-effect, the authored-checker tie versus external profile calibration, separate denominators, and the conditional formal boundary, and that it labels the earlier staged comparison as author-curated. It is not a judge score, and it does not convert the tie into a superiority result.

Next steps: held-out or fresh claim families for transfer claims; live gateway observation; real delegated effects; independently authored corpora; integrating the formal semantics into the audit schema. A higher innovation assessment stays contingent on measured transfer or advantage beyond retrospective profile matches.

### Limitations

Evidence and domain limits. Claims are bounded to specified artifacts, synthetic schedules and formal assumptions. The formal guarantee is conditional on the adapter's observation and abstraction assumptions, including actual-world membership in the compatible set. For the 2026 OpenAI–Hugging Face incident, the evidence standard is the public LessWrong reproduction by Palan, Chute, Kim, and Van Roy (https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment). The post and its appendix are one public record, not the original incident and not the twelve-history application experiment. Original agent transcripts and platform logs are unavailable. No acceptance or qualification criterion is satisfiable only by those withheld originals. The frozen public comparison ties the authored strong_invariant checker and does not claim detection or prevention. Retrospective external calibration defines profile labels rather than an unqualified global “strong” (report/external_calibration_v1/MATRIX.md; PROFILE_LABELS.md). Warrant agreement is distinct from native-method agreement; LessWrong has no scored external native method. Full EvidenceGraph ATTR warrant transfer on seeds 1–2 is not earned while false-exclusivity premise divergence remains.
 Assistant agreement is not independent verification. The BMO result covers an L1 transactional owner and selected projections, not full execution safety. Simulator principals share deterministic scheduling and modeled state; they are not live agents and do not establish emergent coordination. Proofs assume authenticated compatible-world evidence with the actual world inside the compatible set. Falsified observations or an unsound compatibility model can invalidate those premises. Incomplete evidence leaves more worlds compatible and may require an unresolved conclusion. Neither the taxonomy nor the finite checker proves those premises for external datasets. The proofs apply to the specified set semantics; the audit evaluator is assessed on the declared scenario corpus.

### Future Work

Live gateway-side observation, real delegated effects, independently authored case corpora, and integration of the formal evidence semantics into the audit schema.

## 6. Conclusion

Authorization claims should be no stronger than the observations that discriminate safe from unsafe worlds. Swarm Witness turns that into executable practice: source-pinned claims, conventional baselines, explicit unknowns, a distinct modeled effect boundary, and a formal warrant rule. As in R3-D, a classical test can complete while a stronger matched claim remains unresolved for missing observations. Successful execution, selected-observation agreement, and support for a stated property are distinct outcomes.

## Code and Data

The review bundle contains retained R1/R2/R3/R4/R5 evidence, the incident audit, provenance, telemetry, coordination, detection latency, the application effect witness, evidence binding, the native BMO L1 bridge, the causal simulator, the R5 v2 manifest, the finite proof checker, and associated tests. Key entrypoints are experiments/incident_audit/compare.py, experiments/effect_witness/run.py, experiments/evidence_binding/run.py, scripts/render_bounded_comparison.py, experiments/causal_swarm/run.py, experiments/r5_v2/run.py, and theory/check_taxonomy.py. Selected BMO pin: 4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe. Pinned R1 and R2 sources are listed in artifacts/pins.yaml. GitHub: https://github.com/instagrim-dev/swarm-witness; supply the attached portable bundle if repository read access is restricted. The bundle replay recorded for this draft is report/bounded_comparison_v1/REPLAY.md.

- Code repository: https://github.com/instagrim-dev/swarm-witness
- Other artifacts: `dist/swarm-witness-review-bundle.zip`

## Author Contributions

J. Maye-Hobbs designed the audit protocol, implemented the experiments, and wrote the manuscript.

## References

Saltzer, J. H. and Schroeder, M. D. (1975). The protection of information in computer systems. *Proceedings of the IEEE*, 63(9), 1278–1308. https://doi.org/10.1109/PROC.1975.9939.
Schneider, F. B. (2000). Enforceable security policies. *ACM Transactions on Information and System Security*, 3(1), 30–50. https://doi.org/10.1145/353323.353382.
Lamport, L. (1978). Time, clocks, and the ordering of events in a distributed system. *Communications of the ACM*, 21(7), 558–565. https://doi.org/10.1145/359545.359563.
Fagin, R., Halpern, J. Y., Moses, Y. and Vardi, M. Y. (1995; paperback ed. 2004). *Reasoning About Knowledge*. MIT Press. https://mitpress.mit.edu/9780262562003/reasoning-about-knowledge/.
*A Restart Is Not Permission: When an Agent Gate Forgets No.* Apart Swarm Alignment project, 2026. https://apartresearch.com/sprints/projects/a-restart-is-not-permission-when-an-agent-gate-forgets-no-ga92.
Junejo, R. (2026). *Receipt Possession Is Not Event Attribution*. Apart Swarm Alignment project. https://apartresearch.com/sprints/projects/ryan-junejo-4omn.
Swarm Witness. Source and evidence package, November 2026. https://github.com/instagrim-dev/swarm-witness.
Palan, M., Chute, C., Kim, M. and Van Roy, B. (2026). *OpenAI-HuggingFace: A Reproduction & Lessons for Alignment Testing*. LessWrong. https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment.

## Appendix A. Limitations and Dual-Use / Ethical Considerations

Evidence and domain limits. Claims are bounded to specified artifacts, synthetic schedules and formal assumptions. The formal guarantee is conditional on the adapter's observation and abstraction assumptions, including actual-world membership in the compatible set. For the 2026 OpenAI–Hugging Face incident, the evidence standard is the public LessWrong reproduction by Palan, Chute, Kim, and Van Roy (https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment). The post and its appendix are one public record, not the original incident and not the twelve-history application experiment. Original agent transcripts and platform logs are unavailable. No acceptance or qualification criterion is satisfiable only by those withheld originals. The frozen public comparison ties the authored strong_invariant checker and does not claim detection or prevention. Retrospective external calibration defines profile labels rather than an unqualified global “strong” (report/external_calibration_v1/MATRIX.md; PROFILE_LABELS.md). Warrant agreement is distinct from native-method agreement; LessWrong has no scored external native method. Full EvidenceGraph ATTR warrant transfer on seeds 1–2 is not earned while false-exclusivity premise divergence remains.
 Assistant agreement is not independent verification. The BMO result covers an L1 transactional owner and selected projections, not full execution safety. Simulator principals share deterministic scheduling and modeled state; they are not live agents and do not establish emergent coordination. Proofs assume authenticated compatible-world evidence with the actual world inside the compatible set. Falsified observations or an unsound compatibility model can invalidate those premises. Incomplete evidence leaves more worlds compatible and may require an unresolved conclusion. Neither the taxonomy nor the finite checker proves those premises for external datasets. The proofs apply to the specified set semantics; the audit evaluator is assessed on the declared scenario corpus.

Possible adversarial use. Audits that expose stale-authority, receipt-replay or delegation errors could help an attacker find where a system trusts old evidence. We release bounded schedules, retained artifacts and counterexamples—not production credentials, exploit code or secret access paths. Synthetic failing-policy modes are isolated from production BMO.

Prior-work disclosure. BMO and prior SoundGate/EvidenceGraph mechanisms are preexisting; this sprint's novel artifacts are the typed audit, classical comparison harness, causal simulation and formalized evidence-verdict program.

## LLM Usage Statement

AI assistants contributed to brainstorming, implementation, validation and drafting. Reported counts come from retained outputs and tests; authors remain responsible for verifying released artifacts and the manuscript.
