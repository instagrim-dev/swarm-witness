---
title: "Swarm Witness: What Do Agent-Safety Mechanisms Actually Establish?"
---

**Tracks:** 3 (Strengthening Agent Infrastructure), 4 (Multi-Agent Oversight and Control)

**Authors:** *[to be provided]*  
**Affiliations:** *[to be provided]*  
**With** Apart Research

## Abstract

When agent-safety controls produce apparently valid evidence, what additional
observations, assumptions, and comparisons are required before we can justify
claims about their behavior? We introduce Swarm Witness, an executable
claim-audit method that makes those distinctions explicit through source-pinned
experiments, conventional reference monitors, and fail-closed findings.
Classical authorization is the null hypothesis—not a new primitive we invent.
We reproduce two established safety findings (R1 restart-safe authorization; R2
receipt-attribution ambiguity), compare a bounded BMO ledger property against a
classical reference monitor (R3-L1), and test a three-way evidence classification
on synthetic authorization and multi-principal scenarios (R4/R5). R4 separates
missing evidence, failed enforcement, and supported conclusions, including a
negative control that known-false grant observations cannot yield unqualified
support. R5 transfers that taxonomy to a sequential three-principal shared-grant
model (contention, A→B then B→C assignee hops, ledger-bound receipt misuse)—not
concurrent live swarm execution. The contribution is reusable audit discipline,
not a swarm authorization architecture or general BMO equivalence.

# 1. Introduction

**Research question.** When agent-safety controls produce apparently valid
evidence, what additional observations, assumptions, and comparisons are
required before we can justify claims about their behavior?

Authorization gates, receipt graphs, and retained grants are agent-facing
controls that auditors must score carefully. A mechanism can work as
implemented while the evidence used to justify broader claims remains
insufficient. Swarm Witness makes that distinction testable through pinned
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

1. **Pinned claim auditing** of two prior projects (R1/R2) as controlled
   exemplars under source pins—not as weekend discoveries of those mechanisms.
2. **New classical reference-monitor comparison** against BMO’s transactional
   first-edit owner (r3-ledger-claim-v1), with a bounded L1 match under
   fail-closed native qualification; legacy decision-model R3 stays unresolved.
3. **Three-way conclusion method (R4)** that distinguishes missing evidence,
   failed enforcement, and supported conclusions—including bounded
   principal→delegate handoff and a misbound-observation negative control
   (known-false evidence cannot yield unqualified support).
4. **Multi-principal method transfer (R5):** the same taxonomy on a synthetic
   sequential shared-grant model with named principals A/B/C (sequential
   contention, A→B then B→C assignee hops, ledger-bound receipt misuse). This
   is **not** concurrent worker execution or live BMO-mesh safety.

Tracks: **3** (Strengthening Agent Infrastructure) and **4** (Multi-Agent
Oversight and Control). Preexisting BMO code and Oct 25 scaffold are marked in
`PREEXISTING.md`; judged weekend work is the audit method, pins, baselines,
experiments, and evidence packaging.

# 2. Related Work

We build on Apart Swarm Alignment themes of identity, durable commitments, and
oversight under copy/rename/relay (Hammond et al., 2025; Chan et al., 2025;
Greenblatt et al., 2024). Concrete targets:

- **SoundGate / “A Restart Is Not Permission”** — durable auth decisions and
  recovery-barrier repair (pinned package `soundgate==0.1.3`, source revision
  `6568403`). Original authors already reported the core repair; we reproduce
  under pin.
- **EvidenceGraph / Junejo “Receipt Possession Is Not Event Attribution”** —
  stress harness at git rev `a5ea5c9`; paper baseline rev `efbd419`. Again a
  bounded reproduction of a published information-quality failure.
- **BMO ordinary-retry retained grant** — preexisting durable grant /
  owner-witness surfaces under pinned `git_rev`; our new work is the matched
  ClassicalLedgerGate comparison and evidence packaging, not BMO itself.

In-repo baseline cards state inherited mechanism classes (recover-before-admit;
no-implicit-exclusivity; durable grant-table checks) without equating every
proxy to a decision match. Swarm Witness differs from building a new gate: it
asks what labels survive matched baselines and discriminating checks.

# 3. Methods

**Claim cards** (`claims/*.yaml`) fix `property`, `scope`, `quantifier`,
`success_criterion`, and `assumptions` (plus source_ref/version and original vs
operational interpretation). Classical baselines live in `baselines/*.md` as
authored notes, not Claim fields. **Pins** (`artifacts/pins.yaml`) freeze
revisions and hashes. **Evidence** uses Finding labels; `scripts/check_evidence.py`
fails closed if `evidence/index.yaml` disagrees with findings or supporting refs
are missing. The checker’s metric-binding scope is limited: reported metrics
must agree with linked Run observations when keys overlap—it does not re-execute
harnesses.

**R1 (SoundGate).** Rebuild and sweep the paper recovery-barrier harness at
pinned source `6568403`. Compare policies `original`, `strict`, and `barrier`
over the published histories. Success for reproduction: barrier
`prohibited_effects == 0` with original showing the defect. Full `raw.json` is
gitignored; committed `evidence/r1/raw.json.gz` supports local inspection.
Recorded `raw_sha256` is integrity only.

**R2 (EvidenceGraph).** The harness **runs at `a5ea5c9`**, which publishes
`incident_stress.py`. Paper baseline `efbd419` is the pre-extension tree
(no stress script); baseline *behavior* is represented by replaying the
authors’ later-published stress pack at `a5ea5c9`. Label `reproduced` when all
contract checks pass.

**R3 (two distinct protocols).** Legacy **r3-matched-decision-model** uses shared
`cases.yaml` decision-model inputs; ClassicalGate emits allow/deny per case.
BMO decisions require isomorphic observations—never package pass counts. When
any required BMO case is unmatched, that comparison Finding is **`unresolved`**.
Derived **r3-ledger-claim-v1** separately compares ClassicalLedgerGate (SQLite)
to native `ClaimOrdinaryRetainedGrantFirstEditTx` under pin `4b717d7` with
fail-closed native qualification (manifest, exit 0, adapter identity,
git-archive pin inventory, recomputed bridge/cases hashes when files are
present, archived log). Cross-arm divergence refutes equality
(`comparison_divergent`) without diagnosing `failed_enforcement` when each
arm may still satisfy its own property.

**R4 (three-way conclusions).** Worlds A (grant active) and B (grant revoked)
share an identical old receipt. Taxonomy in
`src/swarm_witness/conclusion_classes.py`: **missing_evidence** → Finding
`unresolved`; **failed_enforcement** → `contradicted_in_scope`; **supported** →
`reproduced`. Blind/irrelevant cases must stay missing_evidence. A broken gate
that allows under an observed revoked grant must be failed_enforcement. Correct
allow/deny under **authentic** observed grant is supported. Misbound observations (available but false vs ground truth) yield an end-to-end
unwarranted-permission finding with `failure_origin=evidence_misbinding`—not a
gate-policy diagnosis. Authentic broken gates use
`failure_origin=gate_enforcement`. Protocol:
`experiments/evidence_sufficiency/`.

**R5 (multi-principal transfer).** Protocol `r5-swarm-audit-v1` uses an
in-memory sequential ledger with principals A/B/C
(`src/swarm_witness/swarm_audit.py`). Cases cover missing peer observation,
sequential contended spend (correct and broken-decision-without-effect),
sequential A→B then B→C assignee hops, and ledger-bound cross-agent receipt
misuse. Each case uses the same three-way classes.

# 4. Results

Labels from `evidence/index.yaml` / findings only: R1 **reproduced**, R2
**reproduced**, R3 decision-model **unresolved**, R3 ledger-claim-v1
**classical_baseline_matches** (bounded L1), R4 **reproduced**, R5
**reproduced**. For R1/R2, `reproduced` means pinned independent replication.
For R4/R5 it means synthetic protocol conformance under self-authored
deterministic cases—not external replication. Metrics cite
`evidence/*/summary.json`.

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
principle. Classical recover-before-admit is an authored baseline interpretation
(`baselines/r1_wal_recover_before_admit.md`).

## 4.2 R2 — Receipt ≠ attribution (`reproduced`)

Harness at `a5ea5c9`; `condition_by_seed_checks` **36**, passed **36**; seeds
0,1,2; `all_contract_checks_pass: true`; `source_tree_sha256=2962568f…`.

| Metric (per seed) | seed 0 | seed 1 | seed 2 |
| --- | ---: | ---: | ---: |
| old_rule wrong attributions on relay | 1 | 1 | 1 |
| safer supported on relay | 0 | 0 | 0 |
| safer correct on relay | 0 | 0 | 0 |
| clean withheld without exclusivity | 12 | 12 | 12 |
| shared_tokens correct | 0 | 0 | 0 |
| false_exclusivity confident errors | 1 | 1 | 1 |

Relay seed-0 outcomes: ambiguous 10, unmatched 2. Safer default withholds
attribution without exclusivity; old rule errs once per seed on relay. Bounded
reproduction of a published information-quality failure; classical
no-implicit-exclusivity remains authored interpretation
(`baselines/r2_no_implicit_exclusivity.md`).

## 4.3 R3 — Retained grant vs ClassicalGate (`unresolved`)

Matched **decision-model** comparison: **0/4** isomorphic BMO observations;
`missing_bmo_cases: 4`. Comparison Finding `r3-f-comparison` label
**`unresolved`** — comparison not performed / incomplete. ClassicalGate arm
completed all four cases under the decision model (`state`, `request`,
`grant_version`); BMO arm records `execution_status=missing` /
`missing_isomorphic_observation` for each. Selected preferred Go tests on the
pinned BMO revision remain available as package metadata and are **not** used
as decisions or as a substitute comparative label.

| Case | ClassicalGate | BMO decision | BMO status |
| --- | --- | --- | --- |
| retained_start_claim_relaunch | deny | — | missing |
| rejected_execute | deny | — | missing |
| active_grant_execute | allow | — | missing |
| stale_grant_version | deny | — | missing |

## 4.4 R3 — Ledger claim L1 (`classical_baseline_matches`)

Derived protocol **r3-ledger-claim-v1** is distinct from §4.3. Across six
synthetic cases (T01–T06), ClassicalLedgerGate and the native BMO L1 bridge at
pin `4b717d7` recorded equal dispositions and property-relevant projections
(grant_spent, counts, call_id sets) at every step, and both arms satisfied the
declared one-use / reopen / rollback properties. Finding
`r3-ledger-claim-v1-comparison` label **`classical_baseline_matches`** under
fail-closed native qualification. Cross-arm equality does **not** claim native
grant/epoch hash identity parity with synthetic classical aliases. This does
not establish general BMO equivalence, multi-agent handoff, concurrency, or
process-restart correctness. Selected run:
`evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2/`.

## 4.5 R4 — Three-way conclusions (`reproduced` = synthetic conformance)

Synthetic cases under `r4-evidence-sufficiency-v1` exercise all three classes,
including **bounded handoff** and a **misbound negative control**: when the
supplied grant observation disagrees with ground truth, the end-to-end
conclusion is `failed_enforcement` with `failure_origin=evidence_misbinding`
(not `supported`; not a gate-enforcement diagnosis). Blind Worlds A/B stay
`missing_evidence`; authentic broken gates are `failed_enforcement` with
`failure_origin=gate_enforcement`. Cross-study map:
`baselines/three_way_conclusion_map.md`. Finding `r4-f-evidence-sufficiency`
label **`reproduced`**; `all_checks_pass: true`.

## 4.6 R5 — Multi-principal transfer (`reproduced` = synthetic conformance)

Ten cases under `r5-swarm-audit-v1` with principals **A, B, C** in a sequential
shared-grant model: missing peer observation (2); failed enforcement on broken
post-spend allow and foreign-receipt allow under revoke, both without
unauthorized effect commit (2); supported sequential contention, A→B then B→C
assignee hops, and ledger-bound cross-agent receipt deny (6). Finding
`r5-f-swarm-audit` label **`reproduced`**; `agent_count: 3`;
`model: sequential_shared_grant_multi_principal`. This establishes taxonomy
transfer to a small sequential multi-principal model—not concurrent swarm
dynamics or live BMO mesh safety.

# 5. Discussion

**Synthesis.** Swarm Witness reproduces two established safety findings (R1/R2),
compares a bounded BMO ledger property against a conventional reference monitor
(R3-L1), and tests three-way evidence classification on synthetic authorization
and multi-principal scenarios (R4/R5). That is the supported claim surface.

**Implications.** Multi-principal settings amplify evidence gaps and enforcement
failures; an audit method must refuse peer activity, foreign receipts, or
misbound observations as substitute warrant. Swarm Witness makes that refusal
executable.

**Limitations (summary).** ClassicalGate is a decision-model null; legacy R3 is
incomplete; ledger-claim equality is projection-scoped; R4/R5 are synthetic
sequential protocols (not live concurrent agents); R5 does not establish
emergent swarm dynamics. Full Limitations appendix follows.

**Future work.** Isomorphic decision-model R3 probes; grant/epoch alias maps;
genuine contested concurrent handoffs; continuous baseline-vs-claim diffs.

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

**R4 three-way conclusions (`reproduced` = synthetic conformance).** Establishes
that the audit method can classify synthetic cases into missing_evidence,
failed_enforcement, and supported, including a misbound-observation negative
control. Does **not** establish live BMO behavior or cryptographic receipt
authenticity. The Finding label `reproduced` here means protocol conformance,
not independent external replication.

**R5 multi-principal transfer (`reproduced` = synthetic conformance).**
Establishes that the same three-way method classifies a sequential in-memory
three-principal model covering shared-grant contention, A→B then B→C assignee
hops, and ledger-bound receipt misuse, distinguishing wrong decisions from
committed effects. Does **not** establish concurrent worker execution, live BMO
mesh equivalence, cryptographic multiparty authorization, or unbounded
population-scale swarm safety.

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
