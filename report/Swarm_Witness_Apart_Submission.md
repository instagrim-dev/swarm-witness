---
title: "Swarm Witness: Executable Evidence Auditing for Agent Authorization Claims"
---

**Tracks:** 3 (primary — Strengthening Agent Infrastructure); 4 (application surface only)

**Authors:** *[to be provided]*  
**Affiliations:** *[to be provided]*  
**With** Apart Research

## Abstract

When agent-safety controls produce apparently valid evidence, what additional
observations, assumptions, and comparisons are required before we can justify
claims about their behavior? We introduce Swarm Witness—an executable
evidence-auditing method for agent authorization claims—built around
source-pinned experiments, conventional reference monitors, and fail-closed
findings. Classical authorization is the null hypothesis. We confirm two prior
safety findings (R1 pinned SoundGate re-execution; R2 published-harness
confirmation at a later stress revision), report a bounded native BMO ledger
match (R3-L1) beside an incomplete decision-model comparison (R3-D unresolved),
and exercise a three-way evidence classifier on synthetic and held-out artifacts
(R4/R5). Findings separate conclusion from evaluation method. The method also
separates comparison divergence from enforcement failure, and records evidence /
decision / effect diagnoses so misbound observations and wrong decisions
prevented at the effect boundary are not conflated. Primary track: strengthening agent infrastructure (Track 3); synthetic
multi-principal cases illustrate a Track 4 application surface, not live swarm
oversight or unbounded population safety.

# 1. Introduction

**Research question.** When agent-safety controls produce apparently valid
evidence, what additional observations, assumptions, and comparisons are
required before we can justify claims about their behavior?

Authorization gates, receipt graphs, and retained grants are agent-facing
controls that auditors must score carefully. A mechanism can work as
implemented while the evidence used to justify broader claims remains
insufficient. Swarm Witness—an executable evidence-auditing method for agent
authorization claims—makes that distinction testable through pinned
reproductions, matched classical controls, and explicit observation boundaries.
Classical authorization is the **null hypothesis**—not a new architecture we
propose, and not a claim that BMO is equivalent to classical security.

**Threat / failure modes.** (i) An admission gate forgets an acknowledged
rejection across restart when the durable log is not recovered before admit.
(ii) A verifier treats possession of a copied receipt token as event
attribution without exclusivity or authenticity. (iii) Retained start/grant
metadata or an old receipt is treated as standing authority without consulting
current grant state.

**Main contributions (claimed).**

1. **Executable claim qualification** that refuses to upgrade conclusions
   without necessary observations, and that separates *what* was established
   (conclusion) from *how* it was obtained (evaluation method).
2. **Pinned / harness confirmations** of two prior projects (R1/R2) as
   controlled exemplars—not weekend discoveries of those mechanisms.
3. **Two distinct R3 protocols:** **R3-D** decision-model comparison remains
   unresolved (missing isomorphic BMO observations); **R3-L1** reports a
   bounded native ledger match under fail-closed qualification. Cross-arm
   *divergence* refutes equality without diagnosing enforcement failure.
4. **Three-way conclusion projection (R4/R5)** with separable diagnoses
   (`evidence_status`, `decision_status`, `effect_status`, `failure_origin`),
   including misbound and held-out misleading artifacts, bounded handoff, and
   sequential multi-principal transfer (A/B/C)—not concurrent live swarm
   oversight.

**Primary track: 3** (Strengthening Agent Infrastructure). Track **4**
(Multi-Agent Oversight) is an application surface illustrated by synthetic
multi-principal cases, not a demonstrated real-swarm result. Preexisting BMO
code and Oct 25 scaffold are marked in `PREEXISTING.md`.

# 2. Related Work

We build on Apart Swarm Alignment themes of identity, durable commitments, and
oversight under copy/rename/relay (Hammond et al., 2025; Chan et al., 2025;
Greenblatt et al., 2024). Concrete targets:

- **SoundGate / “A Restart Is Not Permission”** — durable auth decisions and
  recovery-barrier repair (pinned package `soundgate==0.1.3`, source revision
  `6568403`). Original authors already reported the core repair; we re-execute
  under pin.
- **EvidenceGraph / Junejo “Receipt Possession Is Not Event Attribution”** —
  later stress harness at git rev `a5ea5c9`; paper baseline rev `efbd419`
  predates the stress script—we confirm the later harness, not the earlier
  tree.
- **BMO ordinary-retry retained grant** — preexisting durable grant /
  owner-witness surfaces under pinned `git_rev`; our new work is the matched
  ClassicalLedgerGate comparison and evidence packaging, not BMO itself.

In-repo baseline cards state inherited mechanism classes (recover-before-admit;
no-implicit-exclusivity; durable grant-table checks) without equating every
proxy to a decision match. Swarm Witness differs from building a new gate: it
asks what labels survive matched baselines and discriminating checks.

# 3. Methods

**Claim cards** (`claims/*.yaml`) fix `property`, `scope`, `quantifier`,
`success_criterion`, and `assumptions`. **Pins** freeze revisions. **Findings**
carry a conclusion label and an `evaluation_method`.
`scripts/check_evidence.py` fails closed if the index disagrees with findings;
it does not re-execute harnesses.

**R1.** Pinned SoundGate re-execution at `6568403`
(`evaluation_method=pinned_reexecution`).

**R2.** Confirmation of the authors’ later-published stress harness at
`a5ea5c9` (`published_harness_confirmation`)—not execution of paper rev
`efbd419`.

**R3-D.** Decision-model comparison; unmatched BMO observations → `unresolved`
(comparison not established).

**R3-L1.** Native ledger match at pin `4b717d7`. Disagreement →
`comparison_divergent` (equality refuted ≠ `failed_enforcement`).

**R4.** Three-way projection plus diagnoses; misbound → `failure_origin=evidence`;
authentic broken gate → `decision_policy`; held-out fixture under
`experiments/evidence_sufficiency/held_out/`.

**R5.** Sequential A/B/C model; broken allow → `effect_status=prevented`,
`failure_origin=decision_policy`.

# 4. Results

| Claim | Conclusion | Evaluation method |
| --- | --- | --- |
| R1 SoundGate | `reproduced` | `pinned_reexecution` |
| R2 EvidenceGraph | `reproduced` | `published_harness_confirmation` |
| R3-D decision-model | `unresolved` | `matched_decision_model` |
| R3-L1 ledger | `classical_baseline_matches` | `native_matched_baseline` |
| R4 evidence sufficiency | `reproduced` | `synthetic_protocol_conformance` (+ held-out) |
| R5 multi-principal | `reproduced` | `synthetic_protocol_conformance` |

Metrics cite `evidence/*/summary.json`.

## 4.1 R1 — SoundGate recovery barrier (`reproduced`)

Fresh local rebuild+sweep; `all_checks_pass: true`;
`raw_sha256=51b4acd6…`. Histories per policy: **153**.

| Policy | cases | prohibited_effect | refused_before_ack | supported | fresh_work |
| --- | ---: | ---: | ---: | ---: | ---: |
| original | 153 | **143** | 4 | 6 | 149 |
| strict | 153 | 0 | **147** | 6 | 6 |
| barrier | 153 | **0** | 0 | **153** | 153 |

Barrier restores acknowledge-and-restrict across restart under the published
histories; original loses restrictions (143 prohibited effects). This
establishes reproducibility within tested conditions, not a new recovery
principle.

## 4.2 R2 — Receipt ≠ attribution (`reproduced` = published-harness confirmation)

Later stress harness at `a5ea5c9` (not paper rev `efbd419`);
`condition_by_seed_checks` **36**, passed **36**; seeds 0,1,2;
`all_contract_checks_pass: true`; `source_tree_sha256=2962568f…`.

| Metric (per seed) | seed 0 | seed 1 | seed 2 |
| --- | ---: | ---: | ---: |
| old_rule wrong attributions on relay | 1 | 1 | 1 |
| safer supported on relay | 0 | 0 | 0 |
| safer correct on relay | 0 | 0 | 0 |
| clean withheld without exclusivity | 12 | 12 | 12 |
| shared_tokens correct | 0 | 0 | 0 |
| false_exclusivity confident errors | 1 | 1 | 1 |

## 4.3 R3-D — Decision-model comparison (`unresolved`)

**0/4** isomorphic BMO observations; Finding `r3-f-comparison` **`unresolved`**
— comparison **not established**, not an observed negative equality result.

| Case | ClassicalGate | BMO decision | BMO status |
| --- | --- | --- | --- |
| retained_start_claim_relaunch | deny | — | missing |
| rejected_execute | deny | — | missing |
| active_grant_execute | allow | — | missing |
| stale_grant_version | deny | — | missing |

## 4.4 R3-L1 — Ledger claim (`classical_baseline_matches`)

Across T01–T06, ClassicalLedgerGate and native BMO L1 at pin `4b717d7` matched
dispositions and projections with both arms satisfying declared properties.
Equality failure would be `comparison_divergent`, not automatic
`failed_enforcement`. Selected run:
`evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2/`.

## 4.5 R4 — Three-way projection (`reproduced` = synthetic + held-out)

Cases under `r4-evidence-sufficiency-v1` exercise all three classes, bounded
handoff, misbound controls (`failure_origin=evidence`), authentic broken gates
(`failure_origin=decision_policy`), and held-out
`held_out_misleading_grant_observation`. Finding
`r4-f-evidence-sufficiency` **`reproduced`**; `all_checks_pass: true`.

## 4.6 R5 — Multi-principal transfer (`reproduced` = synthetic conformance)

Ten sequential A/B/C cases: missing observation (2); wrong-decision allows with
`effect_status=prevented` (2); supported contention, assignee hops, and
ledger-bound receipt deny (6). Finding `r5-f-swarm-audit` **`reproduced`**;
`model: sequential_shared_grant_multi_principal`.

# 5. Discussion

**Synthesis.** An executable audit can preserve the difference between an
observed security property, an incomplete comparison, comparison divergence,
and a conclusion invalidated by unreliable evidence.

**Implications.** Diagnostic labels must not introduce the unsupported
inferences the method was built to catch: equality ≠ enforcement; misbinding ≠
gate policy; wrong decision with prevented effect ≠ committed illicit effect.

**Limitations (summary).** R3-D incomplete; R3-L1 projection-scoped; R4/R5 mostly
synthetic conformance (one held-out fixture); no live concurrent agents. Full
Limitations appendix follows.

**Future work.** Isomorphic R3-D probes; more externally supplied artifacts;
genuine contested concurrent handoffs.

# Appendix A. Limitations and Dual-Use / Ethical Considerations

## What each result does and does not establish

**R1 (`reproduced`).** Establishes that, on the pinned SoundGate recovery-barrier
harness (source revision `6568403`), the barrier policy yields
`prohibited_effects = 0` across 153 histories while the original policy yields
143 prohibited effects, with 147 strict refusal-startup refusals under the
strict policy. Does **not** establish that every agent admission gate is
restart-safe, that SoundGate is free of other defect classes, or that
recover-before-admit is a new multi-agent invention (that classical reduction
remains an authored baseline question under test). Committed
`evidence/r1/raw.json.gz` supports local inspection of the sweep artifact
(`gzip -dc evidence/r1/raw.json.gz > evidence/r1/raw.json`); recorded
`raw_sha256` is an integrity check and **does not replace** inspecting
`raw.json` / analysis case records.

**R2 (`reproduced`).** Establishes that the stress pack executed at harness rev
`a5ea5c9` passes 36/36 condition-by-seed checks: old-rule relay wrong
attributions are 1 per seed; safer relay supported attributions are 0; clean
runs withhold all 12 attributions without exclusivity declarations. Paper
baseline `efbd419` is the pre-extension tree (no `incident_stress.py`); its
baseline *behavior* is represented by replaying the authors’ later-published
stress pack at `a5ea5c9`, not by running a missing harness at `efbd419`. Does
**not** establish that all receipt or ledger systems are safe under relay/copy,
or that exclusivity declarations themselves cannot be gamed outside the modeled
threat surface.

**R3 decision-model (`unresolved`).** Establishes that the matched ClassicalGate
decision-model comparison against BMO is **incomplete**: 0/4 required cases
have isomorphic BMO observations, so the comparison Finding is `unresolved`
(comparison not performed). ClassicalGate is a **decision-model** null
(`state`, `request`, `grant_version`)—not a restart-durability claim.
Selected preferred Go tests on the pinned BMO revision are package metadata
only and do not fill decisions or substitute for a matched comparative label.
Does **not** establish ClassicalGate↔BMO API equivalence, assumption-dependent
affinity, or a methodological reduction of BMO’s durable-grant story to
classical controls.

**R3 ledger-claim-v1 (`classical_baseline_matches`, bounded).** Establishes
equal dispositions and property-relevant projections (grant_spent, counts,
call_id sets) across T01–T06 for ClassicalLedgerGate vs native
`ClaimOrdinaryRetainedGrantFirstEditTx` at pin `4b717d7` under fail-closed
native qualification. Does **not** claim synthetic classical grant/epoch
aliases equal native durable hashes, full event-trace observational
equivalence, live execution safety, process-restart correctness, concurrency
behavior, or general BMO equivalence. Legacy decision-model R3 remains
separately unresolved.

**R4 three-way projection (`reproduced` = synthetic conformance + held-out).**
Establishes classification into missing_evidence / failed_enforcement /
supported with separable diagnoses, including misbound evidence
(`failure_origin=evidence`) and one held-out misleading artifact. Does **not**
prove the taxonomy is necessary or sufficient versus other assurance models.
`reproduced` here is protocol conformance, not external replication.

**R5 multi-principal transfer (`reproduced` = synthetic conformance).**
Establishes taxonomy transfer on a sequential three-principal model; broken
allows use `effect_status=prevented` and `failure_origin=decision_policy`.
Does **not** establish concurrent worker execution or live swarm oversight.

## Finite experiments and checker scope

Pinned histories, seeds `{0,1,2}`, and preferred Go tests are finite. Passing
them does not imply equivalence across versions, storage backends, concurrent
writers outside the model, or production deployments. Labels apply to the
stated scope on the claim cards only. `scripts/check_evidence.py` binds
reported metrics to linked Run observations when keys overlap; it does not
re-execute harnesses or prove metric completeness beyond that binding.

## Dual-use / adversarial use of the audit method

An executable claim-audit method can help **defenders** find weak gates and
attribution gaps—and can also help **adversaries** locate the same gaps
(restart races, possession-as-attribution, retained-metadata relaunch). We
publish **tests, pins, matched baselines, and labels**, not exploit kits,
weaponized harnesses, or production credentials. Reproduction artifacts are
scoped to already-public or author-local preexisting trees (`PREEXISTING.md`).

## Preexisting code vs weekend analysis

Oct 25 scaffold paths and the external BMO tree at pinned `bmo_root` /
`git_rev` predate this sprint and were not modified for R3 beyond read-only
`go test`. Weekend work is the Swarm Witness schema, pins, claim cards,
baselines, experiment wrappers, evidence records, index checker, and this
report. Judges should score the audit contribution, not treat preexisting BMO
surfaces as sprint inventions.
