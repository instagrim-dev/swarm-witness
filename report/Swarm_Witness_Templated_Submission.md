# Swarm Witness Evidence for Agent Authorization

**Author:** Jonathan Maye-Hobbs  
**Affiliation:** Independent

With Apart Research

## Abstract

Delegated agents need authority and outcome evidence that retain their meaning across execution and recovery boundaries. We study this problem through BMO, an existing implementation of inter-agent authority and settlement mechanisms, and Swarm Witness, an experimental instrument for qualifying claims about those mechanisms. We extract selected transaction contracts and implement a separate SQLite reference. Six ledger cases calibrate one-use claim behavior. A distinct settlement protocol tests two valid continuations and seven negative controls using fixture-authored records checked by BMO's production transactions. A committed claim leaves the effect-applied proposition unresolved; bound applied and definite no-effect records support or refute it, while invalid terminal evidence does not resolve it. A separate application-owned SQLite witness executes twelve histories and varies evidence access across forty-eight packets. Its historical qualifier produces eleven affirmative safety judgments that match controlled truth but lack sufficient evidence. A later evaluator preserves all twenty-four warranted decisive judgments while respecting the twenty-four unresolved conditions. EvidenceGraph composition further shows that translation can preserve both useful inferences and their assumption limitations. Together, the studies demonstrate bounded portability of selected authority and settlement contracts across two implementations, while showing which observations justify a conclusion. The contribution is contract extraction and evidence-sufficiency analysis, not a new authorization primitive. External empirical transfer remains untested.

## 1 Introduction

A correct local control can coexist with a policy violation elsewhere in the same execution. In the application studied here, a worker passes a remote URL allowlist test while a forbidden downstream write commits. The actor transcript does not establish what reached storage. A record from the application-owned sink, bound to the same run, establishes the forbidden effect. The observations answer different questions because the control and the write cross different boundaries.

This creates a practical problem for authorization research. A receipt can establish that a message was delivered without identifying who caused an event. A recorded allow can establish a decision without establishing current authority at execution. A successful test can establish the tested behavior without establishing a broader system property. The research question is therefore: **what evidence is sufficient to justify a specified authorization claim?** The studies follow that question in one chain: authority, a terminal outcome, a warrant, and translation.

Swarm Witness is the research instrument for that question. BMO, SoundGate, and EvidenceGraph predate it. BMO implements owned authority and settlement. SoundGate studies whether restart preserves a durable refusal. EvidenceGraph studies why a receipt does not establish event attribution. A classical SQLite gate implements the selected BMO contract separately and is not an independent adjudicator. On the application packets, the Swarm Witness qualifier and the invariant checker are the paired methods. The EvidenceGraph adapter is a composed method, not ground truth.

The contribution is the extraction and comparison of those selected contracts, together with observation interventions that show which records justify a conclusion. The BMO mechanisms are preexisting. Bounded contract portability across the two implementations is demonstrated. This track evaluates whether authority and evidence obligations survive agent handoffs and recovery, using observable outcomes and matched controls.

## 2 Claims and observations

### 2.1 The object of a conclusion

A claim specifies a proposition, principal, action, authority policy, and evaluated scope. Time belongs to that scope. Entitlement when a decision is issued and authorization when an effect commits can differ, depending on whether the declared revocation policy withdraws previously issued permission. Neither policy is assumed by default.

Table 1 separates claims that a single execution can raise. A *warrant* is the conclusion justified by the observations available for that claim. The *method output* is the conclusion an implementation actually returns. Keeping these separate permits the experiment to detect an unwarranted answer even when the answer happens to match the controlled truth.

**Table 1. Distinct propositions require observations at the corresponding boundary. All statements concern the declared scope and policy.**

| Claim | Proposition | Observation needed |
| --- | --- | --- |
| Local control | A named control makes the decision prescribed by its own rule. | Subject class and the control's decision. |
| `P_commitment` | An effect committed. | A bound sink record; a claim of no commitment also needs complete coverage. |
| Commit authorization | Every observed commit was authorized under the declared policy. | Commit identity, authority state, relevant times, and revocation policy. |
| `P_effect` | Unauthorized downstream effects do not commit. | Effect records with authorization evidence and sufficient coverage to support an absence claim. |
| `P_system` | All five declared boundary properties hold. | A conclusion for each boundary: URL access, local file disclosure, configuration execution, credential scope, and downstream effects. |

The system proposition is a conjunction. One refuted component refutes it; every component must be supported to support it. A passing URL control alone cannot establish the conjunction. Likewise, a committed write establishes an effect, while permission for that write requires additional evidence.

### 2.2 Evidence admission and provenance

The protocol binds records to claims through identifiers for the run, event, principal, and relevant scope. It records the source and role of each observation, distinguishes decision records from effect records, and requires coverage information when a conclusion depends on absence. The declared requirements make each premise explicit: an unrelated record, a repeated account of the same event, or an incomplete set of rows cannot justify a missing premise.

Provenance identifies where a record came from and what the experiment trusts about it. Multiple documents derived from one observation do not constitute multiple independent observations. A source digest preserves the identity of an input; it does not authenticate the event that the input describes. In the application experiment, the sink observer is a separate read-only connection, but the worker and database share an operating-system user. The protocol's trust boundary therefore covers the declared application interfaces, not a hostile process that writes directly to the database.

### 2.3 Conditional semantics

Let `W` be a set of possible worlds, `P` the subset satisfying a fixed proposition, and `Gamma(o)` the nonempty set of worlds compatible with admitted observations `o`. Support is licensed when `Gamma(o)` is contained in `P`; refutation is licensed when the two sets are disjoint. Otherwise the conclusion is unresolved. Invalid observations and empty compatibility sets do not license a vacuous conclusion.

This rule is sound if the actual world remains in `Gamma(o)`. It also gives useful experimental invariants: opposite-truth worlds with indistinguishable observations remain unresolved; irrelevant observations do not change a conclusion; and consistent refinement preserves a decisive conclusion about the same fixed event or time. The supplement states the set-theoretic arguments and checks 2,646 cases in a four-world model [7]. These results specify conditions an implementation should satisfy. They do not prove that an adapter authenticates external records or constructs a sound abstraction of every deployment.

## 3 Experimental design

### 3.1 Application execution and controlled observation

The principal study executes twelve fixed histories across six declared families against an application-owned SQLite sink. Histories exercise authority state, effects that are attempted or prevented, transcript claims, and the relation between a local control and a broader property. The worker emits actor records. The sink records committed effects, and a separate observer opens it read-only. A fresh interpreter reopens the database to check persistence. Eight effects are present in the retained cold readback.

Each execution yields four evidence packets. The *actor-only* condition supplies the worker's records without the observations required to establish settlement. The *discriminating readback* condition adds the bound application observations. The *duplicate and irrelevant* condition retains that evidence while adding records that should not change its meaning. The *withheld or misbound* condition removes or breaks a required evidence relationship. These are forty-eight views of twelve executions, not forty-eight independent executions.

An explicit warrant file specifies the justified conclusion for each history and evidence condition separately from the method implementations. The actor-only and withheld or misbound conditions warrant unresolved conclusions. The other two conditions provide twenty-four warranted decisive conclusions. Controlled truth is retained separately so that factual error and insufficient evidence can be measured independently. Cases and warrants are author specified; separate implementations do not make their construction independent.

### 3.2 Methods and outcome measures

Swarm Witness qualifies a claim from the supplied records. The invariant checker, identified as `strong_invariant` in the implementation, separately checks the family-specific evidence and property requirements under the same observation budget. The always-unresolved reference measures the limit of unconditional abstention. The checker is a concrete comparator for these families, rather than a general designation of method strength.

An *unsupported support* is a supported output where the packet's warrant is refuted or unresolved. A *correct decisive conclusion* agrees with a supported or refuted warrant. A *correct abstention* returns unresolved where the warrant is unresolved. The latter two use different denominators. Reporting both prevents an always-unresolved method from appearing adequate simply because it never overclaims.

### 3.3 Public records and evidence translation

A separate public-record study evaluates twelve claims at two evidence stages, giving twenty-four conditions per method. Its warrants describe what the retained public material establishes. A smaller controlled comparison covers four claims over three histories. Their denominators remain separate from the application study. Where the public records cannot establish the underlying event, an evidence warrant is available without a corresponding verified truth label.

The public LessWrong reproduction by Palan and colleagues [8] is one source record; its post and appendix are not independent observations. It concerns a reproduction environment, while original incident transcripts and platform logs are unavailable to this study. Conclusions are limited to the material actually retained.

An additional EvidenceGraph experiment tests whether an adapter can express prior evidence disciplines in the claim protocol. Its 130 packets comprise 120 attribution cases, eight native execution cases, and two further controls. Agreement with the adapter measures composition. Agreement with separately stated warrants and with the native method are reported separately because they answer different questions.

## 4 Results

The results follow the chain below. A later boundary needs its own observation, and it does not revise an earlier count.

**Evidence chain. A later claim needs its own observation.**

| Boundary | What it can establish | What it cannot establish alone | Where it is tested |
| --- | --- | --- | --- |
| Authority and claim | A scoped one-use claim by the current owner | That the delegated edit applied | BMO and SQLite, 6 cases, 22 steps |
| Terminal settlement | An applied edit, or a definite no-effect | System safety, or a live external agent | S01-S09, including the initial 2 |
| Effect and warrant | A committed effect, or a justified absence | Safety from a local pass, or from an incomplete ledger | 12 histories, viewed as 48 packets |
| Evidence translation | A classifier conclusion from admitted premises | That the adapter's premises were independently verified | 70 of 130 packets |

### 4.1 Valid authority does not settle an effect

The question is whether BMO and the classical gate satisfy the same bounded claim contract. The observation is the retained comparison of six cases and 22 paired steps. That comparison is compare-only: it reads recorded transactions and does not re-execute BMO. The result is that both implementations match on dispositions and the relevant ledger-state projections, covering repeated claims, spent and unspent authority after reopen, rollback, wrong-task requests, and noncurrent owner revisions [7]. The implication is a calibrated claim contract. A scope-control packet refutes the further claim that these traces establish external settlement, and Table 3 is not part of these six cases.

### 4.2 The same claim still needs a terminal record

The question is which terminal records resolve the effect-applied proposition after one committed first-edit claim. The observation is fixture-authored records read by both arms. It is not a live model edit, and it is not part of the six-case ledger count. The result is Table 3. S02 refutes only the effect-applied proposition. The implication is that refusal leaves the committed claim in place and leaves that proposition unresolved. Effect-applied asks whether the delegated effect entered. It is not `P_effect`, and it is not `P_system`.

**Table 3. Terminal evidence, settlement, and the effect-applied verdict. Both arms match on every case.**

| Case | Terminal evidence | Settlement | Effect-applied |
| --- | --- | --- | --- |
| S01 | Bound applied records, in order | applied | supported |
| S02 | Bound no-effect records | not entered | refuted |
| S03 | Applied label, mutation missing | refused | unresolved |
| S04 | Artifact recorded before the mutation | refused | unresolved |
| S05 | Mutation and artifact bound to another call | refused | unresolved |
| S06 | No-effect label contradicted by a write | refused | unresolved |
| S07 | Applied label, no terminal records | refused | unresolved |
| S08 | Applied label and an unrelated tool record | refused | unresolved |
| S09 | No-effect label, no terminal records | refused | unresolved |

S02 refutes only the effect-applied proposition. Refusal leaves the committed claim in place and that proposition unresolved.

### 4.3 A local pass is not the observed effect

The question is whether a passing local control establishes `P_effect` or `P_system`. The observation is the witness `aew-v1-local-control-pass-broader-effect`: `remote_url_allowlist` passes, the actor-only packet lacks the sink record, and the application readback supplies it [7]. The result is that actor-only `P_effect` stays unresolved, while the readback refutes `P_effect` and therefore `P_system`; the local control remains supported. Complete observations of the clean authority-current commit support `P_effect` and leave `P_system` unresolved. The implication is that a record answers only its proposition. `P_effect` says unauthorized downstream effects do not commit. `P_system` is the conjunction of the five boundary properties.

### 4.4 Truth can agree with an unwarranted conclusion

The question is whether the historical qualifier's supports are warranted by the packet. That qualifier is the published result for these application packets, not a measure of BMO. The observation is 48 packets from 12 histories, with warrants kept separate from controlled truth. The result is Table 2. The implication is that a true proposition can still be an unwarranted support, and a later replay does not replace Table 2.

**Table 2. Native comparison on 48 evidence packets from 12 executed histories. Decisive coverage and abstention have separate denominators of 24.**

| Method | Unsupported supports | Correct decisive conclusions | Correct abstentions |
| --- | ---: | ---: | ---: |
| Swarm Witness | 11 | 24/24 | 13/24 |
| Invariant checker | 0 | 24/24 | 24/24 |
| Always unresolved | 0 | 0/24 | 24/24 |

Table 2 is the historical comparison. Its eleven *unsupported supports* are withheld or misbound packets whose controlled propositions happen to be true. The current evaluator is a separate replay of those same 48 files and does not replace Table 2. The sixteen-case challenge is a separate denominator: the historical record still marks the spoofed sink supported, while the later admission check leaves it unresolved and records a malformed packet as a rejection rather than a verdict.

**Table 2b. Historical Swarm Witness and the current evaluator on the same 48 packets.**

| Evaluator | Unsupported supports | Correct decisive | Correct abstentions |
| --- | ---: | ---: | ---: |
| Historical Swarm Witness | 11 | 24/24 | 13/24 |
| Current evaluator | 0 | 24/24 | 24/24 |

The current replay also has 0 unsupported refutations. On the twelve actor-only packets, the historical record says prevented and the current evaluator says unobserved. Attribution is not evaluated on this layer, and the replay makes 0 additional source requests.

### 4.5 Translation can carry a premise forward

The question is what public records and translated packets justify. The observation on the public layer is 24 conditions, separate from the 48 packets. The result is that Swarm Witness and the invariant checker each return 22 warranted abstentions and both warranted decisive conclusions, with no *unsupported supports*; a naive passing rule produces 24 *unsupported supports*. Four controlled claims remain a smaller, separate denominator [7]. The implication is that public agreement is not the application result.

The translated-evidence question is whether composition adds a source or only a representation. The observation is the 130-packet corpus and, inside it, the frozen 70-packet slice: 332 supplied records and no further request. Both composed classifiers preserve all 130 adapter decisions, including ten unsupported attribution supports and one factually wrong supported attribution [6, 7]. The result on the slice is Table 4. The implication is composition fidelity on packets already inside that corpus, not unseen validation. The historical refutation nominee on the slice stays unresolved.

**Table 4. Frozen-slice representation study: 70 of the 130 packets. Raw arms abstain on all 70. Composed arms abstain on 34. Derived records are not extra sources.**

| Arm | Assessor coverage | Warrant coverage | Unsupported vs warrant |
| --- | ---: | ---: | ---: |
| Raw, either method | 0/36 | 0/26 | 0 |
| Adapted, either method | 36/36 | 26/26 | 10 |

The ten *unsupported supports* are false-exclusivity packets the assessor supports and the warrant leaves unresolved. Both classifiers accept the adapter's projected polarity, so the result is not a Swarm Witness-specific advantage.

## 5 Related work and interpretation

Complete mediation, causal order, and possible-worlds semantics motivate the distinction between a local check and the observations that establish an effect [1, 2, 3, 4]. SoundGate studies whether restart preserves a durable refusal [5]. EvidenceGraph studies why possession of a receipt does not establish event attribution [6].

The corpus is small and deliberately constructed. Packet conditions are dependent views of the same histories, so their counts are neither population rates nor estimates of deployment reliability. Public warrants are author specified. The historical qualifier's eleven *unsupported supports* remain the published comparison. Table 2b shows the current evaluator on the same files and does not replace that count. Further validation would require new families with explicit warrants and observations obtained under the trust boundaries of the intended deployment.

## 6 Conclusion

BMO and the classical ledger satisfy the same retained claim contract. The comparison that shows this reads recorded transactions and does not re-execute BMO. Table 3 then separates the effect-applied proposition from that claim: bound applied records support it, bound no-effect records refute only that proposition, and refusal leaves it unresolved while the committed claim remains. Those are the first two boundaries in the evidence chain.

The other studies qualify what may be concluded next, and what translation adds. The historical qualifier's eleven *unsupported supports* remain the published 48-packet comparison; the current evaluator and the sixteen-case challenge do not replace that count. Table 4 shows that an admitted-premise adapter makes 36 assessor labels and 26 warrant labels decisive for both classifiers, and still supports ten false-exclusivity packets the warrant leaves unresolved. Those 70 packets already belong to the 130-packet corpus. Recovery is fidelity to the shared adapter. External empirical transfer remains untested. These are the later boundaries in the same chain.

## Code and data

Source, protocols, and retained results are in the repository [7]. Reproduction commands are in `evidence/ACCESS.md`. Native re-execution requires the pinned BMO source.

## References

1. Saltzer, J. H. and Schroeder, M. D. (1975). The protection of information in computer systems. *Proceedings of the IEEE*, 63(9), 1278–1308. https://doi.org/10.1109/PROC.1975.9939.
2. Schneider, F. B. (2000). Enforceable security policies. *ACM Transactions on Information and System Security*, 3(1), 30–50. https://doi.org/10.1145/353323.353382.
3. Lamport, L. (1978). Time, clocks, and the ordering of events in a distributed system. *Communications of the ACM*, 21(7), 558–565. https://doi.org/10.1145/359545.359563.
4. Fagin, R., Halpern, J. Y., Moses, Y. and Vardi, M. Y. (1995; paperback edition 2004). *Reasoning About Knowledge*. MIT Press. https://mitpress.mit.edu/9780262562003/reasoning-about-knowledge/.
5. *A Restart Is Not Permission: When an Agent Gate Forgets No.* Apart Swarm Alignment project (2026). https://apartresearch.com/sprints/projects/a-restart-is-not-permission-when-an-agent-gate-forgets-no-ga92.
6. Junejo, R. (2026). *Receipt Possession Is Not Event Attribution*. Apart Swarm Alignment project. https://apartresearch.com/sprints/projects/ryan-junejo-4omn.
7. Maye-Hobbs, J. (2026). *Swarm Witness*. Source and evidence package. https://github.com/instagrim-dev/swarm-witness.
8. Palan, M., Chute, C., Kim, M. and Van Roy, B. (2026). *OpenAI-HuggingFace: A Reproduction & Lessons for Alignment Testing*. LessWrong. https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment.

## Appendix A Limitations and dual use

**Observation and trust boundaries.** The application experiment uses a real local worker and SQLite sink under a controlled harness. Its observer reads committed state separately from the actor transcript, but shares an operating-system user with the worker. Direct database modification by a process with that user's privileges is outside the declared boundary. The experiment establishes the retained local executions; it does not establish adversarial isolation of telemetry or observation authenticity in an external service.

**Inference and generalization.** The finite semantics assumes a valid abstraction and an actual world compatible with admitted observations. Neither a digest nor a finite check proves these assumptions for new records. Authored schedules, public-record warrants, and retrospective adapter cases cover specified behaviors rather than a representative sample of agent deployments. The application histories, public-record comparison, and EvidenceGraph translation use separate denominators. Agreement among methods is not an independent validation of their shared premises.

**Incident scope.** The public reproduction [8] is distinct from the application witness. The original incident's transcripts and platform logs are not available in this package. The study makes no detection or prevention claim about that incident. Supplemental synthetic studies and label replays remain evidence about their declared inputs, rather than observations of emergent agent coordination or successful behavior in an external deployment.

**Potential misuse.** Descriptions of stale authority, receipt reuse, and incomplete evidence could help identify weak audit boundaries. The application experiments use controlled records and local effects. They contain no production credentials or secret access paths. Their purpose is to make incorrect authorization conclusions observable and reproducible.

**Prior material.** SoundGate, EvidenceGraph, and BMO predate this protocol. Their mechanisms and retained source revisions are attributed in the repository's preexisting-material record. The protocol, controlled comparison, and evidence representations are distinguished from those underlying systems.

### Sprint contribution and prior work

Before the November 6–8, 2026 sprint, Swarm Witness consisted of an October 26 UTC repository scaffold and a preliminary paired-oversight research direction. Its README, license, setup check, and placeholder research directories contained no runnable experiment, implemented research protocol, retained measurement, or manuscript. The sprint produced the evidence-sufficiency protocol and qualifier, application-owned SQLite effect witness, separate classical contract reference, native BMO ledger and settlement comparisons, adversarial and representation studies, formal checks, retained results, and paper. BMO's underlying authority and settlement implementation, SoundGate, and EvidenceGraph are prior work, not sprint inventions. The contribution claimed here is the new contract extraction, experimental comparisons, and analysis of observations sufficient to warrant authorization conclusions. Bounded contract portability does not establish full-system equivalence or external empirical transfer.

## LLM Usage Statement

The operator developed the preexisting BMO authority and settlement implementation and orchestrated the comparisons, the retained measurements, and which conclusions the evidence was allowed to support. AI assistants contributed counterfactual challenge of the claims, research design, implementation, validation scripts, and manuscript drafting. The author is responsible for the claims, interpretation, and released artifacts.
