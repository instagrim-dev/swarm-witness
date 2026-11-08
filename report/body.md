## 1 Introduction

A correct local control can coexist with a policy violation elsewhere in the same execution. In the application studied here, a worker passes a remote URL allowlist test while a forbidden downstream write commits. The actor transcript does not establish what reached storage. A record from the application-owned sink, bound to the same run, establishes the forbidden effect. The observations answer different questions because the control and the write cross different boundaries.

This creates a practical problem for authorization research. A receipt can establish that a message was delivered without identifying who caused an event. A recorded allow can establish a decision without establishing current authority at execution. A successful test can establish the tested behavior without establishing a broader system property. The research question is therefore: **what evidence is sufficient to justify a specified authorization claim?**

Swarm Witness is the research instrument for that question. BMO is the preexisting implementation of owned authority and settlement. A classical SQLite gate implements the selected contract separately and is not an independent adjudicator. The Swarm Witness qualifier is one evaluated method. The EvidenceGraph adapter derives records from admitted premises and is part of a composed method, not ground truth.

The contribution is the extraction and comparison of those selected contracts, together with observation interventions that show which records justify a conclusion. The BMO mechanisms are preexisting. The experiments establish behavior on the declared cases. They do not establish transfer to an unrelated platform.

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

H1: a committed first-edit claim leaves effect-applied unresolved. H2: bound records support it or refute only effect-applied; refusal leaves it unresolved. H3: Table 2 is the historical qualifier and its eleven unwarranted supports; Table 2b is the current evaluator and does not replace Table 2. H4: translation is part of the method. The sixteen-case challenge is a separate denominator.

### 4.1 Native transaction-contract calibration

The retained native comparison establishes that BMO and an independent classical implementation satisfy the same bounded transaction contract. BMO exposes `ClaimOrdinaryRetainedGrantFirstEditTx`. The comparator is an independent SQLite `ClassicalLedgerGate`. On six cases and 22 paired steps, both implementations satisfy the declared properties and match on dispositions and the relevant ledger-state projections. The cases cover repeated claims, spent and unspent authority after database reopen, rollback, wrong-task requests, and noncurrent owner revisions [7]. The comparison measures claim and transfer behavior. It supplies a calibrated upstream result from which to ask which later observations establish a delegated effect.

A scope-control packet refutes the further proposition that these ledger traces establish external settlement. That refutation follows from the experiment's declared scope. The packet contains no measured downstream execution, and it does not show that an effect failed to occur. Table 3 is the later settlement measurement, and it is not part of these six cases.

### 4.2 From transaction authorization to observed settlement

The settlement experiment starts from one committed first-edit claim and then varies only the terminal records. Both native BMO and the classical gate read those fixture-authored records. Table 3 is the resulting discrimination. It is not part of the six-case ledger count, and it does not claim that a live model edit was executed.

**Table 3. Terminal evidence, settlement, and the effect-applied verdict. Both arms match on every row.**

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

### 4.3 A local control and a forbidden effect

The application study asks the downstream question for a different owner. In the named witness, the ordinary `remote_url_allowlist` test passes. The actor-only packet leaves `P_effect` unresolved. The application readback establishes a forbidden downstream commit and therefore refutes `P_effect`. That refutation also refutes `P_system`, while the passing local control remains correctly reported. The witness identifier is `aew-v1-local-control-pass-broader-effect` [7].

The clean authority-current control provides the complementary result: complete observations of an authorized commit support `P_effect`. They leave `P_system` unresolved because this one boundary does not establish every component. These paired outcomes show why a record of settlement and the proposition being evaluated must remain explicit.

### 4.4 Warrant and truth diverge

Both methods recover all twenty-four warranted decisive conclusions in the native comparison. Their treatment of incomplete evidence differs substantially (Table 2).

**Table 2. Native comparison on 48 evidence packets from 12 executed histories. Decisive coverage and abstention have separate denominators of 24.**

| Method | Unsupported supports | Correct decisive conclusions | Correct abstentions |
| --- | ---: | ---: | ---: |
| Swarm Witness | 11 | 24/24 | 13/24 |
| Invariant checker | 0 | 24/24 | 24/24 |
| Always unresolved | 0 | 0/24 | 24/24 |

Table 2 is the historical comparison. Its eleven unsupported supports are the published Swarm Witness result, and later code does not rewrite them. All eleven are withheld or misbound packets. Their controlled propositions happen to be true, so they are unwarranted conclusions rather than false propositions. The invariant checker on that same historical comparison avoids the eleven and still recovers the 24 decisive conclusions. The always-unresolved reference avoids them by recovering none.

The current evaluator is a separate replay of those same 48 files. It does not replace Table 2.

**Table 2b. Historical Swarm Witness and the current evaluator on the same 48 packets.**

| Evaluator | Unsupported supports | Correct decisive | Correct abstentions |
| --- | ---: | ---: | ---: |
| Historical Swarm Witness | 11 | 24/24 | 13/24 |
| Current evaluator | 0 | 24/24 | 24/24 |

The current replay also has 0 unsupported refutations. On the twelve actor-only packets, the historical record says prevented and the current evaluator says unobserved. Attribution is not evaluated on this layer, and the replay makes 0 additional source requests.

### 4.5 Public and translated evidence

On the twenty-four public-record conditions, Swarm Witness and the invariant checker agree throughout: each returns twenty-two warranted abstentions and both warranted decisive conclusions, with no unsupported supports or refutations. A naive rule that treats a passing result as support produces twenty-four unsupported supports. The smaller controlled comparison also ties the two principal methods, with two correct decisive conclusions and two correct abstentions across four claims [7].

In the EvidenceGraph study, both composed classifiers preserve all 130 adapter decisions. This includes ten unsupported attribution supports and one factually wrong supported attribution under a false exclusivity premise. The agreement establishes that the composition preserves the adapter's behavior; it does not establish independent correctness. The result makes the adapter's assumptions part of the method that must be examined, rather than treating translation as a neutral change of format [6, 7].

The frozen 70-packet pipeline asks whether those same observations become usable once a qualified adapter supplies a decisive record. Raw Swarm Witness and the raw invariant checker do not treat the packet bytes as that record, so both abstain. The assessor is decisive on 36 packets. The separate warrant is decisive on 26.

**Table 4. Frozen 70-packet pipeline. Raw arms abstain on 70 packets and adapted arms on 34. The adapter reads 332 records and requests none further. The adapted verdict equals the adapter verdict.**

| Arm | Assessor coverage | Warrant coverage | Unsupported vs warrant |
| --- | ---: | ---: | ---: |
| Raw, either method | 0/36 | 0/26 | 0 |
| Adapted, either method | 36/36 | 26/26 | 10 |

The ten unsupported supports are false-exclusivity packets the assessor supports and the warrant leaves unresolved. Both classifiers accept the adapter's projected polarity, so the result is not a Swarm Witness-specific advantage and does not establish transfer.

## 5 Related work and interpretation

Complete mediation, causal order, and possible-worlds semantics motivate the distinction between a local check and the observations that establish an effect [1, 2, 3, 4]. SoundGate studies whether restart preserves a durable refusal [5]. EvidenceGraph studies why possession of a receipt does not establish event attribution [6].

The corpus is small and deliberately constructed. Packet conditions are dependent views of the same histories, so their counts are neither population rates nor estimates of deployment reliability. Public warrants are author specified, and the study does not demonstrate transfer to independently authored claim families. The historical qualifier's eleven unsupported supports remain the published comparison. Table 2b shows the current evaluator on the same files and does not replace that count. Further validation would require new families with explicit warrants and observations obtained under the trust boundaries of the intended deployment.

## 6 Conclusion

BMO and a classical ledger satisfy the same claim and settlement contract, and Table 3 shows which terminal records support, refute, or leave unresolved an effect. The historical qualifier can overstate incomplete evidence; Table 2b is the later evaluator on those files. Table 4 recovers the 26 warrant-decisive labels and also the ten false-exclusivity supports the warrant leaves unresolved.

## Code and data

Source, protocols, and retained results are in the repository [7]. Reproduction commands are in `evidence/ACCESS.md`. Native re-execution requires the pinned BMO source.
