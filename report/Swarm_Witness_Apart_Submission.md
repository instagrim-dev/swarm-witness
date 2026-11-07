---
title: "Swarm Witness: What Do Agent-Safety Mechanisms Actually Establish?"
---

**Tracks:** 3 (Strengthening Agent Infrastructure), 4 (Multi-Agent Oversight and Control)

**Authors:** *[to be provided]*  
**Affiliations:** *[to be provided]*  
**With** Apart Research

## Abstract

After matching policy, observations, trust assumptions, durability, and
enforcement coverage, which claimed benefits of agent-safety mechanisms remain?
We test that question with Swarm Witness, an executable claim-audit kit that
pins third-party artifacts, states precise claim cards, runs discriminating
checks, and records fail-closed conclusion labels. Classical reductions
(recover-before-admit; no-implicit-exclusivity; durable grant-table checks) are
questions under test via matched baselines—not intro verdicts. On three pinned
targets we obtain: SoundGate recovery-barrier (R1) reproduced — 153
histories/policy, original prohibited effects 143 vs barrier 0, with 147 strict
refusal-startup refusals; EvidenceGraph receipt stress (R2) reproduced —
36/36 condition-by-seed checks, old-rule relay wrong attributions [1,1,1] per
seed vs safer supported [0,0,0], and clean withheld-without-exclusivity
[12,12,12]; BMO retained-grant vs ClassicalGate (R3) unresolved — matched
decision-model comparison incomplete (0/4 isomorphic BMO observations; selected
Go package tests are metadata only). Weekend contributions claimed here are
(1) pinned replications for R1/R2 and (2) the audit kit. A third,
methodological finding that a durable-grant story reduces to classical controls
is not claimed without a completed matched comparison. Auditors should publish
matched baselines and labels.

# 1. Introduction

**Research question.** After matching policy, observations, trust assumptions,
durability, and enforcement coverage, which claimed benefits of agent-safety
mechanisms remain?

Authorization gates, receipt graphs, and retained grants are agent-facing
controls that auditors must score carefully. When a report claims a restart-safe
refusal, receipt-based attribution, or retained-grant relaunch control, the
open question is whether the result is a new property, a repaired instance of a
classical mechanism, or an incomplete comparison. Classical reductions—
recover-before-admit for durable logs, no-implicit-exclusivity for receipt
tokens, and durable grant-table checks before admit—are **questions we test**
with matched baselines, not conclusions we assert in the introduction.

**Threat / failure modes.** (i) An admission gate forgets an acknowledged
rejection across restart when the durable log is not recovered before admit.
(ii) A verifier treats possession of a copied receipt token as event
attribution without exclusivity or authenticity. (iii) Retained start/grant
metadata is treated as standing relaunch authority without consulting a durable
grant table.

**Main contributions (claimed).**

1. **Audit kit:** Swarm Witness pins artifacts, types Claim/Run/Finding cards,
   states classical baselines, runs discriminating experiments, and fails closed
   on evidence consistency (`reproduced`, `unresolved`, …).
2. **Pinned replications:** SoundGate recovery barrier (R1) and EvidenceGraph
   receipt stress (R2) under published harnesses, with metrics from committed
   `evidence/*/summary.json`.

A third contribution—a **methodological finding** that a durable-grant story
reduces to classical controls—is **not claimed** here: R3’s matched
decision-model comparison is incomplete (`unresolved`).

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
  `6568403`).
- **EvidenceGraph / Junejo “Receipt Possession Is Not Event Attribution”** —
  stress harness at git rev `a5ea5c9`; paper baseline rev `efbd419` (pre-extension
  behavior; no runnable stress script at that rev).
- **BMO ordinary-retry retained grant** — preexisting durable grant /
  owner-witness tests under pinned `bmo_root` / `git_rev` (read-only `go test`
  as metadata).

In-repo baseline cards state mechanism classes without equating every proxy to
a decision match. Swarm Witness differs from building a new gate: it asks what
labels survive matched baselines and discriminating checks.

# 3. Methods

**Claim cards** (`claims/*.yaml`) fix `property`, `scope`, `quantifier`,
`success_criterion`, `assumptions`, `baseline`, and `discriminating_checks`.
**Pins** (`artifacts/pins.yaml`) freeze revisions and hashes. **Baselines**
state the mechanism class without equating every proxy to a decision match.
**Evidence** uses Finding labels; `scripts/check_evidence.py` fails closed if
`evidence/index.yaml` disagrees with findings or supporting refs are missing.
The checker’s metric-binding scope is limited: reported metrics must agree with
linked Run observations when keys overlap—it does not re-execute harnesses.

**R1 (SoundGate).** Rebuild and sweep the paper recovery-barrier harness at
pinned source `6568403`. Compare policies `original`, `strict`, and `barrier`
over the published histories. Success for reproduction: barrier
`prohibited_effects == 0` with original showing the defect. Full `raw.json` is
gitignored; committed `evidence/r1/raw.json.gz` supports local inspection
(`gzip -dc … > raw.json`). Recorded `raw_sha256` is integrity only—hash alone
does not replace inspecting analysis case records. Supplemental cargo
`wal_recovery_barrier` on 0.1.4 recorded in notes.

**R2 (EvidenceGraph).** The harness **runs at `a5ea5c9`**, which publishes
`incident_stress.py`. Paper baseline `efbd419` is the pre-extension tree
(no stress script); baseline *behavior* is represented by replaying the
authors’ later-published stress pack at `a5ea5c9` (old-rule vs safer-default
contrast), not by executing a missing harness at `efbd419`. Label `reproduced`
when all contract checks pass.

**R3 (BMO vs ClassicalGate).** Shared `cases.yaml` decision-model inputs;
ClassicalGate emits allow/deny per case. BMO decisions require isomorphic
observations from matching assertions or an instrumented harness—never package
pass counts. When any required BMO case is unmatched, the comparison Finding is
**`unresolved`** (incomplete comparative audit). Optional preferred Go tests are
metadata only.

# 4. Results

Labels from `evidence/index.yaml` / findings only: R1 **reproduced**, R2
**reproduced**, R3 **unresolved**. Metrics below cite `evidence/*/summary.json`.

## 4.1 R1 — SoundGate recovery barrier (`reproduced`)

Fresh local rebuild+sweep; `all_checks_pass: true`;
`raw_sha256=51b4acd6…`. Histories per policy: **153**.

| Policy | cases | prohibited_effect | refused_before_ack | supported | fresh_work |
| --- | ---: | ---: | ---: | ---: | ---: |
| original | 153 | **143** | 4 | 6 | 149 |
| strict | 153 | 0 | **147** | 6 | 6 |
| barrier | 153 | **0** | 0 | **153** | 153 |

Barrier restores acknowledge-and-restrict across restart under the published
histories; original loses restrictions (143 prohibited effects). Cargo
`wal_recovery_barrier` on 0.1.4: 3 passed (notes). Classical recover-before-admit
is an authored baseline interpretation (`baselines/r1_wal_recover_before_admit.md`),
not a separate empirical `classical_baseline_matches` Finding.

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
attribution without exclusivity; old rule errs once per seed on relay. Classical
no-implicit-exclusivity is authored interpretation
(`baselines/r2_no_implicit_exclusivity.md`).

## 4.3 R3 — Retained grant vs ClassicalGate (`unresolved`)

Matched decision-model comparison: **0/4** isomorphic BMO observations;
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

# 5. Discussion

**Implications.** For Tracks 3–4, durable identity and oversight claims should
be scored against classical admit and evidence rules under matched
observations. R1 and R2 show that published repairs can **reproduce** under
pinned harnesses; that is valuable engineering and audit evidence, not proof of
a new multi-agent primitive. R3 shows the fail-closed path: without isomorphic
BMO observations, the comparative audit stays **unresolved**.

**Limitations (summary).** ClassicalGate is a **decision-model** null (not
restart durability); R3 comparison is incomplete; R1 raw inspectability is via
committed `raw.json.gz`; R2 executable binding is `a5ea5c9` with `efbd419` as
behavioral baseline via published stress pack; evidence checker metric-binding
is scope-limited. Full Limitations and Dual-Use appendix follows.

**Future work.** Shared observation APIs for R3 isomorphic matches; expand pins;
automate baseline-vs-claim diffs for continuous oversight.


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

**R3 (`unresolved`).** Establishes that the matched ClassicalGate
decision-model comparison against BMO is **incomplete**: 0/4 required cases
have isomorphic BMO observations, so the comparison Finding is `unresolved`
(comparison not performed). ClassicalGate is a **decision-model** null
(`state`, `request`, `grant_version`)—not a restart-durability claim.
Selected preferred Go tests on the pinned BMO revision are package metadata
only and do not fill decisions or substitute for a matched comparative label.
Does **not** establish ClassicalGate↔BMO API equivalence, assumption-dependent
affinity, or a methodological reduction of BMO’s durable-grant story to
classical controls.

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

