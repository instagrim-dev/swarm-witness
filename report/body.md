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
