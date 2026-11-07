# Formal epistemics of the Swarm Witness taxonomy

**Issue:** [#12](https://github.com/instagrim-dev/swarm-witness/issues/12)  
**Code oracle:** `src/swarm_witness/formal/` (independent of `conclusion_classes`)  
**Finite checks:** `python experiments/taxonomy_formal/run.py`  
**Not claimed:** universal swarm alignment, cryptographic novelty, production BMO
correctness, or optimality of the three-way naming scheme.

## 1. Research question

Under what assumptions is the Swarm Witness conclusion discipline
**sound and conservative**? We give mathematical semantics for worlds,
observations, compatibility, and diagnoses; prove core invariants on a finite
model (or exhibit counterexamples that force revision); and separate
**evidence validity** from **enforcement failure**.

Weekend R4/R5 runs show only bounded executable conformance. This note supplies
the missing formal layer.

## 2. Definitions

### 2.1 Worlds

Let \(W\) be a nonempty set of possible worlds. For the permission fragment used
in finite checks, each \(w \in W\) carries:

| Component | Domain | Meaning |
| --- | --- | --- |
| \(\mathsf{grant}(w)\) | \(\{\mathsf{active},\mathsf{revoked}\}\) | Ground-truth current authority |
| \(\mathsf{decision}(w)\) | \(\{\mathsf{allow},\mathsf{deny}\}\) | Mechanism disposition |
| \(\mathsf{effect}(w)\) | \(\{\bot,\top\}\) | Whether a side effect committed |

Optional \(\mathsf{impl}(w)\) labels an implementation arm for matched
comparisons.

### 2.2 Claim / property

A **property** is \(P: W \to \{\bot,\top\}\). Standing examples:

- \(P_{\mathsf{dec}}(w) \iff \mathsf{decision}(w) = \delta^*(\mathsf{grant}(w))\),
  where classical null \(\delta^*(\mathsf{active})=\mathsf{allow}\),
  \(\delta^*(\mathsf{revoked})=\mathsf{deny}\).
- \(P_{\mathsf{eff}}(w) \iff \bigl(\delta^*(\mathsf{grant}(w))=\mathsf{deny}
  \Rightarrow \neg\mathsf{effect}(w)\bigr)\).

### 2.3 Observation availability and authenticity

An **observation** \(o\) is a partial channel map:

- \(\mathsf{obs\_grant}(o) \in \{\mathsf{active},\mathsf{revoked},\bot\}\)
- \(\mathsf{auth}(o) \in \{\top,\bot,?\}\) — verified authentic / known-misbound /
  unverified
- optional \(\mathsf{obs\_decision}(o)\), \(\mathsf{obs\_effect}(o)\)
- optional irrelevant facts (non-discriminating by trust assumption)

**Availability ≠ authenticity.** A channel may be populated (`?`) without a
verified binding to ground truth.

### 2.4 Trust assumptions \(T\)

Default \(T_0\):

1. Verified authenticity is required before a grant reading shrinks \(\Gamma\).
2. Irrelevant facts never shrink \(\Gamma\).
3. A known-misbound grant channel yields \(\Gamma(o)=\emptyset\).

### 2.5 Compatibility \(\Gamma(o; W, T)\)

\[
\Gamma(o; W, T) \;=\;
\{ w \in W \mid o \text{ is consistent with } w \text{ under } T \}.
\]

Operationally (permission fragment, \(T_0\)):

- If \(\mathsf{obs\_grant}=\bot\): \(\Gamma = W\).
- If \(\mathsf{auth}=\bot\): \(\Gamma = \emptyset\).
- If \(\mathsf{auth}=?\): \(\Gamma = W\) (do not trust the reading).
- If \(\mathsf{auth}=\top\): keep worlds whose grant (and optionally
  decision/effect) match the verified readings.

### 2.6 Epistemic status

\[
\begin{align*}
\mathsf{support}(P,o) &\iff \Gamma\neq\emptyset \land \forall w\in\Gamma.\, P(w), \\
\mathsf{refute}(P,o) &\iff \Gamma\neq\emptyset \land \forall w\in\Gamma.\, \neg P(w), \\
\mathsf{unresolved}(P,o) &\iff \text{otherwise (empty }\Gamma\text{ or conflict)}.
\end{align*}
\]

### 2.7 Decision, committed effect, comparator agreement

- **Decision evidence** is present when \(\mathsf{obs\_decision}(o)\) is set
  under authentic grant evidence.
- **Committed effect** is present when \(\mathsf{obs\_effect}(o)\) is set.
- **Comparator agreement** for arms \(A,B\): dispositions equal under complete
  paired observations. Agreement is a proposition about *equality*, not about
  either arm’s local enforcement.

### 2.8 Typed diagnosis product

\[
D \;=\; (\mathsf{epistemic\_status},\;
\mathsf{evidence\_status},\;
\mathsf{decision\_status},\;
\mathsf{effect\_status},\;
\mathsf{failure\_origin}).
\]

Domains match `swarm_witness.audit_diagnosis` /
`swarm_witness.formal.epistemic_model`.

**`failed_enforcement`** is defined only when:

1. evidence is **authentic** (not missing/unverified/misbound),
2. verified **decision** and/or **effect** channels are present so that
   \(\Gamma\) is discriminative for the stated property \(P\), and
3. \(\mathsf{refute}(P,o)\) holds — i.e. \(\Gamma\neq\emptyset\) and
   \(\forall w\in\Gamma.\,\neg P(w)\).

Classical-null mismatch alone does **not** forge `supported` or
`failed_enforcement` for an arbitrary \(P\): those labels follow the epistemic
projection of \(P\) on \(\Gamma\). Classical mismatch is recorded on
`decision_status` / `failure_origin` (`decision_policy` when the observed
decision ≠ \(\delta^*\); `effect_boundary` when an unauthorized effect is
observed under a deny-required grant — including when the decision itself was
`deny`).

Mere disagreement between two otherwise complete arms is
\(\mathsf{failure\_origin}=\mathsf{comparison\_equality}\)
(class `comparison_divergent`), **not** `failed_enforcement`.

### 2.9 Three-way projection \(\pi\)

For a **mechanism-property** evaluation object \(E\),

\[
\pi(D) \in \{\mathsf{missing\_evidence},\;
\mathsf{failed\_enforcement},\;
\mathsf{supported}\}.
\]

For a **matched-equality** evaluation object,

\[
\pi(D) \in \{\mathsf{missing\_evidence},\;
\mathsf{comparison\_divergent},\;
\mathsf{failed\_enforcement},\;
\mathsf{supported}\}.
\]

\(\pi\) is **lossy** whenever orthogonal origins (evidence vs comparison vs
decision_policy) would be collapsed by a single three-way label. The typed
product is then required.

## 3. Theorems

Proofs below are by exhaustion on the finite permission model
\(|W|=2\cdot2\cdot2=8\) (grant × decision × effect), plus explicit
construction for comparison arms. Machine checks:
`swarm_witness.formal.finite_models.check_core_invariants`.

### T1 — Support soundness

**Statement.** Under \(T_0\), for \(P\in\{P_{\mathsf{dec}},P_{\mathsf{eff}}\}\)
and every observation in the finite fragment: if
\(\pi(D)=\mathsf{supported}\), then \(\Gamma(o)\neq\emptyset\),
\(\forall w\in\Gamma(o).\,P(w)\), and
`FormalDiagnosis.epistemic_status` equals the independently computed
\(\mathsf{support}/\mathsf{refute}/\mathsf{unresolved}\) projection of \(P\)
on \(\Gamma\). In particular, classical-null agreement of an observed decision
does **not** by itself warrant `supported` for \(P_{\mathsf{eff}}\) when
\(\Gamma\) still contains effect-committed and effect-free worlds.

**Proof sketch.** `diagnose` sets `three_way=supported` only when the
independent `epistemic_status(P, Γ)` is `support` under authentic evidence.
Exhaustion over the finite observation fragment × \(\{P_{\mathsf{dec}},
P_{\mathsf{eff}}\}\) confirms the implication; the forged-status regression
(correct deny without effect channel) is C5. ∎

### T2 — Refutation / enforcement soundness

**Statement.** Under \(T_0\), \(\pi(D)=\mathsf{failed\_enforcement}\) only if
evidence is authentic and \(\mathsf{refute}(P,o)\) holds for the stated \(P\).
Incomplete or misbound observations do **not** yield `failed_enforcement`.
Unauthorized committed effect under a *correct* deny is
`failure_origin=effect_boundary` (not `supported`).

**Proof sketch.** `failed_enforcement` is emitted only on the authentic path
when independent status is `refute`. Origin is `effect_boundary` when an
unauthorized effect is observed under deny-required grants, else
`decision_policy` when the decision mismatches \(\delta^*\`. Blind/misbind
branches return `missing_evidence`. Exhaustion + C6. ∎

### T3 — Indistinguishable-world non-identifiability

**Statement.** If \(w_1,w_2\) agree on all channels read by \(o\), then
\(w_1\in\Gamma(o)\Leftrightarrow w_2\in\Gamma(o)\). If additionally
\(P(w_1)\neq P(w_2)\), then \(\mathsf{unresolved}(P,o)\).

**Proof sketch.** Compatibility filters only on observed channels; agreement on
those channels preserves joint membership. Distinct \(P\)-values on a nonempty
\(\Gamma\) force unresolved. Blind \(o\) keeps both active and revoked worlds,
so \(P_{\mathsf{dec}}\) is unresolved and \(\pi=\mathsf{missing\_evidence}\). ∎

### T4 — Non-upgrade under irrelevant facts

**Statement.** If \(o'\) extends \(o\) only by an irrelevant fact (non-
discriminating under \(T_0\)), then \(\Gamma(o')=\Gamma(o)\) and
\(\pi(D')=\pi(D)\). In particular, irrelevant facts cannot upgrade
`missing_evidence` to `supported` or `failed_enforcement`.

**Proof sketch.** Irrelevant facts are ignored by `compatible_worlds`. Same
\(\Gamma\) and same diagnose inputs ⇒ same projection. ∎

### T5 — Monotonic refinement under verified observations

**Statement.** If \(o'\) adds only *verified* informative channels beyond \(o\),
then \(\Gamma(o')\subseteq\Gamma(o)\). Unverified grant readings do not shrink
\(\Gamma\) under \(T_0\). Upgrades of \(\pi\) to `supported` /
`failed_enforcement` occur only after authentic evidence makes \(\Gamma\)
decide the mechanism evaluation.

**Proof sketch.** Each verified filter is a subset constraint. The unverified
branch returns \(W\) unchanged. Diagnose upgrades require the authentic path. ∎

### T6 — Mutual exclusivity / exhaustiveness for a stated object

**Statement.** For evaluation object kind `mechanism_property`, the projected
labels \(\{\mathsf{missing\_evidence},\mathsf{failed\_enforcement},
\mathsf{supported}\}\) are mutually exclusive and jointly cover the diagnose
outcomes of the permission fragment. For `matched_equality`,
`comparison_divergent` is an additional exhaustive alternative when arms
disagree. A single three-way vocabulary is **not** exhaustive for the product
of orthogonal diagnoses without information loss (counterexample C4).

## 4. Counterexamples

| ID | Scenario | Result |
| --- | --- | --- |
| **C1** | Known-false (misbound) grant observation | `evidence_status=misbound`, `failure_origin=evidence`; **not** `supported`; **not** `failed_enforcement` under \(T_0\) |
| **C2** | Incomplete (blind) observation | \(\Gamma\) contains active and revoked; `missing_evidence` |
| **C3** | Correct-but-different implementations (arms disagree, each locally “ok”) | `comparison_divergent` / `comparison_equality` — **not** `failed_enforcement` |
| **C4** | Orthogonal origins | Misbind vs comparison disagreement need distinct coordinates; collapsing to one three-way label loses causal information |
| **C5** | Correct deny, no effect channel, evaluate \(P_{\mathsf{eff}}\) | `epistemic_status=unresolved`; **not** `supported` (classical agreement must not forge support) |
| **C6** | Correct deny + committed unauthorized effect | `failed_enforcement` / `effect_boundary`; **not** `supported` |

These are the acceptance-criterion models: none yields an unwarranted
`supported` finding or a falsely attributed enforcement failure under \(T_0\).

## 5. Relation to production classifiers

| Formal notion | Production surface |
| --- | --- |
| \(\pi\) for mechanism_property | `classify_conclusion` |
| matched equality + divergence | `classify_matched_comparison` → `comparison_divergent` |
| typed product axes | `audit_diagnosis.diagnosis` |
| R4 executable cases | `evidence_sufficiency.assess_permission` |
| R5 swarm cases | `swarm_audit` |

**Independence.** Finite-model theorems use only `swarm_witness.formal` as
oracle. Optional tests may check agreement with production helpers on selected
cases; production code is never the soundness oracle.

**Where three-way remains lossy.** Misbound observations that end-to-end disagree
with ground truth are still labeled `failed_enforcement` at the *high-level*
Finding projection in R4, but with `failure_origin=evidence`. The formal model
under \(T_0\) prefers `missing_evidence` + `failure_origin=evidence` for pure
misbinds (empty \(\Gamma\)), making the validity/enforcement split unavoidable
in the typed product even when Finding labels reuse `contradicted_in_scope`.

## 6. Mapping to R3-L1, R4, R5

| Observation | Formal class | Claim status |
| --- | --- | --- |
| R4 blind A/B | `missing_evidence`; A/B indistinguishable | **supported** (method) |
| R4 correct allow/deny | `supported` | **supported** |
| R4 broken revoked-allow | `failed_enforcement` / `decision_policy` | **supported** |
| R4 misbound | `failure_origin=evidence` (validity ≠ enforcement) | **supported** as separation; high-level Finding may still say contradicted |
| R4 irrelevant control | stays `missing_evidence` | **supported** |
| R3-L1 matched agree + pass | `supported` | **supported** (bounded L1) |
| R3-L1 arm divergence | `comparison_divergent` | **supported** (equality ≠ enforcement) |
| R3 legacy decision-model | `missing_evidence` | **still unverifiable** (no isomorphic BMO obs.) |
| R5 missing peer obs. | `missing_evidence` | **supported** (method) |
| R5 broken allow, effect prevented | `failed_enforcement`; `effect_status=prevented` | **supported** |
| Unbounded swarm / live mesh safety | — | **still unverifiable** |

## 7. Reproducibility

```bash
cd /path/to/swarm-witness
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python experiments/taxonomy_formal/run.py
python experiments/taxonomy_formal/run.py --json
pytest -q tests/test_formal_epistemics.py
```

Expected: all theorem flags `OK`, counterexamples C1–C4 `OK`, exit code 0.

## 8. Finite-model limits

- Grant/decision domains size 2; boolean effect; \(|W|=8\) for one mechanism.
- ≤2 comparison arms; no concurrent interleavings (issue #10).
- Authenticity is a three-valued flag, not a cryptographic game.
- No claim of completeness for richer authorization logics.

## 9. Possible falsifiers

1. A verified-authentic observation package under \(T_0\) for which the
   implementation emits `supported` while some \(w\in\Gamma\) falsifies \(P\)
   (including \(P_{\mathsf{eff}}\) under a correct deny without an effect
   observation).
2. A blind/irrelevant observation that upgrades to `supported` /
   `failed_enforcement`.
3. A matched pair that disagrees on disposition yet is labeled
   `failed_enforcement` with `failure_origin=decision_policy` without
   per-arm property failure.
4. A known-misbound observation labeled `supported`.
5. An authentic revoked+deny+effect=\(\top\) package labeled `supported` (or
   anything other than `failed_enforcement` with `effect_boundary`).
6. Any diagnosis whose `epistemic_status` field disagrees with
   \(\mathsf{support}/\mathsf{refute}/\mathsf{unresolved}\) computed from
   \(P\) and \(\Gamma(o)\) alone.

## 10. What remains

- Extending \(\Gamma\) to concurrent multi-agent interleavings (depends on #10).
- Richer authenticity games (crypto / relay adversaries).
- Optional machine-checked proof in a proof assistant (Lean/Isabelle) — not
  required here; finite exhaustion covers the stated fragment.
- Harmonizing R4’s high-level Finding projection for misbinds with the formal
  preference for empty-\(\Gamma\) `missing_evidence` while retaining
  `failure_origin=evidence` (documentation + diagnosis already separate the
  axes; Finding vocabulary remains coarse).
