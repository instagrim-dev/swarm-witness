# Swarm Witness Evidence for Agent Authorization

**Author:** Jonathan Maye-Hobbs  
**Affiliation:** Independent

## Abstract

An agent can pass a local safety check while committing an effect that a broader policy forbids. Assessing such a run requires separating the property being tested, the authority for the action, and evidence that the effect occurred. We present Swarm Witness, an executable protocol for qualifying authorization claims from partial observations. Each claim binds a proposition and scope to source records and receives a supported, refuted, or unresolved conclusion. A worker and application-owned SQLite sink provide twelve controlled histories, each examined under four evidence conditions. In one history, a URL allowlist passes while a forbidden downstream effect commits. The actor transcript leaves the no-unauthorized-effect claim unresolved; sink readback refutes it. Across forty-eight evidence packets, Swarm Witness and an invariant checker recover all twenty-four warranted decisive conclusions. Swarm Witness also supports eleven cases whose observations warrant abstention; the invariant checker makes no unsupported supports. A separate twenty-four-cell public-record comparison yields identical conclusions for both methods. A possible-worlds formulation states the conditions for sound qualification, conditional on faithful observations and a valid abstraction. The experiments expose a distinction that factual agreement alone misses: a conclusion can be true while exceeding the evidence available to the assessor.

## 1 Introduction

A correct local control can coexist with a policy violation elsewhere in the same execution. In the application studied here, a worker passes a remote URL allowlist test while a forbidden downstream write commits. The actor transcript does not establish what reached storage. A record from the application-owned sink, bound to the same run, establishes the forbidden effect. The observations answer different questions because the control and the write cross different boundaries.

This creates a practical problem for authorization research. A receipt can establish that a message was delivered without identifying who caused an event. A recorded allow can establish a decision without establishing current authority at execution. A successful test can establish the tested behavior without establishing a broader system property. The research question is therefore: **what evidence is sufficient to justify a specified authorization claim?**

Swarm Witness makes that question executable. It represents a scoped proposition, the records supplied to an assessor, and the conclusion warranted by those records. The central experiment varies observation access while holding each underlying execution fixed. A separate comparison checks whether the implemented qualifier respects the resulting evidence requirements. Its eleven unsupported positive conclusions are a substantive result: they expose an inference failure that agreement with the underlying truth would conceal.

The contribution is a protocol and experimental instrument for studying evidence sufficiency. It combines an application effect witness, controlled evidence conditions, explicit warrants, and a conditional semantics for support, refutation, and abstention. Conventional authorization mechanisms remain the reference point. The experiments establish behavior on the declared cases; the invariant checker matches or exceeds the current qualifier in the principal comparisons.

## 2 Claims and observations

### 2.1 The object of a conclusion

A claim specifies a proposition, principal, action, authority policy, and evaluated scope. Time belongs to that scope. Entitlement when a decision is issued and authorization when an effect commits can differ, depending on whether the declared revocation policy withdraws previously issued permission. Neither policy is assumed by default.

Table 1 separates claims that a single execution can raise. A *warrant* is the conclusion justified by the observations available for that claim. The *method output* is the conclusion an implementation actually returns. Keeping these separate permits the experiment to detect an unwarranted answer even when the answer happens to match the controlled truth.

**Table 1. Distinct propositions require observations at the corresponding boundary. All statements concern the declared scope and policy.**

| Claim | Proposition | Observation needed |
| --- | --- | --- |
| Local control | A named control makes the decision prescribed by its own rule. | Subject class and the control's decision. |
| Commitment | An effect committed. | A bound sink record; a claim of no commitment also needs complete coverage. |
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

### 4.1 A local control and a forbidden effect

In the named application witness, the ordinary `remote_url_allowlist` test passes. The actor-only packet leaves `P_effect` unresolved. The application readback establishes a forbidden downstream commit and therefore refutes `P_effect`. That refutation also refutes `P_system`, while the passing local control remains correctly reported. The witness identifier is `aew-v1-local-control-pass-broader-effect` [7].

The clean authority-current control provides the complementary result: complete observations of an authorized commit support `P_effect`. They leave `P_system` unresolved because this one boundary does not establish every component. These paired outcomes show why a record of settlement and the proposition being evaluated must remain explicit.

### 4.2 Warrant and truth diverge

Both methods recover all twenty-four warranted decisive conclusions in the native comparison. Their treatment of incomplete evidence differs substantially (Table 2).

**Table 2. Native comparison on 48 evidence packets from 12 executed histories. Decisive coverage and abstention have separate denominators of 24.**

| Method | Unsupported supports | Correct decisive conclusions | Correct abstentions |
| --- | ---: | ---: | ---: |
| Swarm Witness | 11 | 24/24 | 13/24 |
| Invariant checker | 0 | 24/24 | 24/24 |
| Always unresolved | 0 | 0/24 | 24/24 |

All eleven unsupported supports occur in the withheld or misbound condition. Their underlying controlled propositions happen to be true. They are therefore eleven unwarranted conclusions, not eleven false propositions. The missing observations leave alternatives unresolved for the assessor even though the experiment retains the actual outcome. Evaluating only agreement with that outcome would miss the failure.

The invariant checker avoids these unsupported supports while recovering the same decisive conclusions. The always-unresolved reference also avoids unsupported support, but recovers none of the conclusions for which the evidence is sufficient. On this corpus, the checker provides the most informative behavior consistent with the specified warrants.

Table N2 replays the same 48 packet files with the current evaluator and does not replace the retained 11 unsupported supports. That replay has 0 unsupported supports, 0 unsupported refutations, correct decisive 24 of 24, and 24 correct abstentions. The twelve retained actor-only diagnostics say prevented; the current evaluator records those incomplete observations as unobserved. Attribution is not evaluated on this layer, and the replay makes 0 additional source requests.

### 4.3 Public and translated evidence

On the twenty-four public-record conditions, Swarm Witness and the invariant checker agree throughout: each returns twenty-two warranted abstentions and both warranted decisive conclusions, with no unsupported supports or refutations. A naive rule that treats a passing result as support produces twenty-four unsupported supports. The smaller controlled comparison also ties the two principal methods, with two correct decisive conclusions and two correct abstentions across four claims [7].

In the EvidenceGraph study, both composed classifiers preserve all 130 adapter decisions. This includes ten unsupported attribution supports and one factually wrong supported attribution under a false exclusivity premise. The agreement establishes that the composition preserves the adapter's behavior; it does not establish independent correctness. The result makes the adapter's assumptions part of the method that must be examined, rather than treating translation as a neutral change of format [6, 7].

## 5 Related work and interpretation

Complete mediation and reference-monitor reasoning motivate the distinction between a local check and the boundary at which an action becomes effective [1, 2]. Causal ordering provides a basis for relating authorization, revocation, and execution events [3]. Possible-worlds semantics supplies the language for reasoning about what observations establish [4]. Swarm Witness uses these foundations to define a concrete experimental interface between claims, evidence conditions, and warranted conclusions.

SoundGate studies whether restart preserves a durable refusal [5]. EvidenceGraph studies why possession of a receipt does not establish event attribution [6]. Retained supporting experiments confirm selected behavior under pinned sources or later published harnesses. A native first-edit comparison also matches a preexisting BMO transactional owner with a SQLite baseline on six declared cases, covering one-use claims, rollback, and cold reopen [7]. These studies motivate the protocol's distinctions; they do not turn a ledger property into a guarantee about later execution.

The principal result is the separation of three judgments that can otherwise collapse into a single pass label: whether the relevant property holds, whether a control behaved as specified, and whether the available observations justify the conclusion. The application witness separates a correct local control from a forbidden effect. The incomplete-evidence comparison then separates truth from warrant. Together they give a concrete way to investigate where an authorization argument loses support.

The same distinction changes how positive evidence should be interpreted. An observed forbidden commit can refute a universal no-unauthorized-effect claim. Supporting that claim requires sufficient coverage as well as valid individual records. A missing row is not evidence that an effect was absent. Similarly, adapter composition can add useful inferences while retaining a mistaken premise. Both coverage and translation assumptions belong in the experimental method.

The corpus is small and deliberately constructed. Packet conditions are dependent views of the same histories, so their counts are neither population rates nor estimates of deployment reliability. Public warrants are author specified, and the study does not demonstrate transfer to independently authored claim families. The current qualifier's eleven unsupported supports are a limit of the implementation. The formal specification does not remove that limit. Further validation would require new families with explicit warrants and observations obtained under the trust boundaries of the intended deployment.

## 6 Conclusion

Authorization conclusions require evidence that addresses the claimed property at the relevant boundary. Application readback can distinguish a passing local control from a forbidden effect in the same execution. The matched comparison also shows that the current Swarm Witness qualifier can overstate incomplete evidence even when its conclusion happens to be true. Scoped claims, controlled observation conditions, and separately specified warrants make these relationships explicit and testable.

## Code and data

Source, protocols, retained observations, per-case results, and source revisions are available in the Swarm Witness repository [7]. The application protocol and warrant file accompany the effect-witness experiment. The bounded comparison ledger contains each method's output; the EvidenceGraph capability report separates composition, native-method agreement, and warrant agreement. Reproduction commands and access requirements are documented in `evidence/ACCESS.md`. Native BMO re-execution requires its pinned source; the retained comparison records can be inspected without that checkout.

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

## LLM Usage Statement

AI assistants contributed to research design, implementation, validation scripts, and manuscript drafting. The author is responsible for the claims, interpretation, and released artifacts.
