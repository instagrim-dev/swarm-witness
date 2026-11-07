# Sound evidence conclusions: definitions, theorems and countermodels

**Research status.** A bounded mathematical formalization of the evidence-conclusion
projection, not a proof of production agent correctness or of the superiority of
three particular label names. Executable checker: `theory/check_taxonomy.py`.

## 1. Epistemic substrate and trust boundary

Let `W` be a nonempty finite set of possible worlds, `P ⊆ W` the worlds in
which a fully specified proposition is true, and `o` a set of observations.
Let `V(o)` mean the observation source and binding have been verified. Define
`Γ(o) = {w ∈ W : w is compatible with every verified observation in o}`.
An actual world `w*` is assumed to lie in `Γ(o)` only when `V(o)` holds and the
observation process is sound. Source presence alone does not establish `V`.
Do not permit the empty compatibility set to prove anything by vacuous truth.

For an observation-qualified proposition, define:

- `Support(o,P)` exactly when `V(o)`, `Γ(o) ≠ ∅`, and `Γ(o) ⊆ P`.
- `Refute(o,P)` exactly when `V(o)`, `Γ(o) ≠ ∅`, and `Γ(o) ∩ P = ∅`.
- `Unresolved(o,P)` otherwise.

`Support`, `Refute` and `Unresolved` form an exclusive and exhaustive partition
*for a single proposition under one observation semantics*. They are not
intrinsic causal diagnoses. In particular, `Refute(o, comparison-equality)` does
not mean authorization enforcement failed.

For an **enforcement-property** proposition `P_E`, only a verified violation of
that defined boundary may be recorded as `failed_enforcement`. A supported
`P_E` projects to `supported`; insufficient evidence projects to
`missing_evidence`. An independent coordinate records `failure_origin` in
`{evidence_provenance, incorrect_decision, effect_boundary, comparison,
undetermined}`, and a separate coordinate records decision/effect status.
The original three names can thus be a conservative *derived projection* of a
richer evidence judgment, but cannot replace that product.

## 2. Theorems and proofs

**T1 (Soundness of qualified support/refutation).** Suppose `V(o)` and
`w* ∈ Γ(o)`. If `Support(o,P)` then `w* ∈ P`; if `Refute(o,P)` then `w* ∉ P`.

*Proof.* In the support case, `Γ(o) ⊆ P` and `w* ∈ Γ(o)`, hence `w* ∈ P`.
In the refutation case, `Γ(o) ∩ P = ∅` and `w* ∈ Γ(o)`, hence `w* ∉ P`. QED.

**T2 (Indistinguishable-world non-identifiability).** Suppose `V(o)` and there
exist `w_a, w_b ∈ Γ(o)` with `w_a ∈ P` and `w_b ∉ P`. Then neither support
nor refutation is licensed, so the proposition is unresolved.

*Proof.* `Γ(o)` is not a subset of `P` because it contains `w_b`, and its
intersection with `P` is nonempty because it contains `w_a`. QED.

**T3 (Irrelevant evidence conserves judgment).** Let `x` be a verified but
non-discriminating observation such that `Γ(o ∪ {x}) = Γ(o)`, with equal
verification status. Then the judgment for `P` is unchanged.

*Proof.* All judgment predicates depend only on `V`, the emptiness of `Γ`,
subset containment and intersection. These values are identical. QED.

**T4 (Persistence under sound refinement).** Let `o'` extend `o` with
verified, consistent information such that `∅ ≠ Γ(o') ⊆ Γ(o)` and the actual
world remains compatible. If `P` was supported under `o`, it remains supported
under `o'`; if refuted, it remains refuted. An unresolved proposition may be
upgraded if all remaining worlds agree, but no valid refinement can flip a
supported proposition directly into refuted (or vice versa).

*Proof.* Set-subset transitivity preserves `Γ(o') ⊆ P` and likewise
`Γ(o') ∩ P = ∅`. Nonemptiness is given. QED.

**T5 (Nonvacuity and invalid sources).** If `Γ(o)=∅` or `¬V(o)`, neither
support nor refutation is licensed by these rules.

*Proof.* Nonempty-compatibility and source-verification are necessary
conjuncts of both predicates. QED.

## 3. Countermodels and domain-specific interpretation

**C1: Comparison divergence without enforcement failure.** Let two
implementations `A` and `B` both satisfy security invariant `S`, but have
different correct trace representations. For proposition `P_eq` asserting
identical projections, observations refute `P_eq`. The proposition `P_S`
asserting both satisfy `S` can still be supported. Therefore a rule
`not arms_agree ⇒ failed_enforcement` is unsound. Return a comparison-specific
finding rather than claiming the guard failed.

**C2: False evidence and uncertain origins.** A gate receives a fabricated
"grant active" record, while the independently verified world has the grant
revoked. An allow decision is incorrect relative to the verified world. This
establishes an end-to-end bad decision and evidence-provenance failure, not by
itself a faulty gate *decision function*. If the auditor cannot authenticate
what the actual grant was, `V(o)` is false and the permission claim is
unresolved. An illegitimate effect requires separate committed-effect evidence.

**C3: Same headline class, different effects.** Two histories can both have a
wrong allow decision: in one, an independent effect guard blocks execution;
in the other, it commits the write. A single `failed_enforcement` label cannot
encode the essential difference. Preserve `decision_status` and
`effect_status` as independent attributes.

## 4. Checked finite instances and limits

`theory/check_taxonomy.py` independently implements this set semantics, not
`swarm_witness.conclusion_classes`. It exhausts 4 labeled worlds, all 16
Boolean proposition assignments, all 16 information sets (including empty),
all sound nonempty refinements, and each possible actual world included in the
set. It checks T1–T5 against these finite models and emits
`artifacts/taxonomy_proof_checks.json`. Exhaustive finite checking is **not**
a substitute for the general proofs above; the proofs establish the claims
subject to the stated axioms. The checker is a regression test of those axioms.

## 5. Relation to existing experiments

R3-L1 compares a *selected property projection*, not an isomorphism of native
authority models. R4 tests the paired-world ignorance and evidence-misbinding
cases under a synthetic oracle. R5 v1 is a sequential three-principal model.
The causal simulator and R5 v2 add independently replayable event histories,
while remaining bounded simulations. None of these findings implies correctness
of arbitrary agents or live production grant lineage.
