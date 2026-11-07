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
   failed enforcement, and genuinely supported conclusions—including bounded
   principal→delegate handoff under the same rules.
4. **Multi-agent / swarm generalization (R5):** the same taxonomy applied to a
   synthetic three-agent swarm (A/B/C) with shared-grant contention, delegation
   chains, and cross-agent receipt misuse. Unbounded population-scale or live
   BMO-mesh safety is **not** claimed; the established result is method
   generalization under classical one-use swarm dynamics.

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
git-archive pin inventory, bridge hashes, archived log).

**R4 (three-way conclusions).** Worlds A (grant active) and B (grant revoked)
share an identical old receipt. Taxonomy in
`src/swarm_witness/conclusion_classes.py`: **missing_evidence** → Finding
`unresolved`; **failed_enforcement** → `contradicted_in_scope`; **supported** →
`reproduced`. Blind/irrelevant cases must stay missing_evidence. A broken gate
that allows under an observed revoked grant must be failed_enforcement. Correct
allow/deny under observed grant is supported. Protocol:
`experiments/evidence_sufficiency/`.

**R5 (swarm generalization).** Protocol `r5-swarm-audit-v1` instantiates agents
A/B/C on classical one-use shared grants (`src/swarm_witness/swarm_audit.py`).
Cases cover missing peer observation, contended spend (correct and broken),
delegation-chain assignee checks, and cross-agent receipt misuse. Each case is
labeled with the same three-way classes.

# 4. Results

Labels from `evidence/index.yaml` / findings only: R1 **reproduced**, R2
**reproduced**, R3 decision-model **unresolved**, R3 ledger-claim-v1
**classical_baseline_matches** (bounded L1), R4 **reproduced**, R5
**reproduced**. Metrics cite `evidence/*/summary.json`.

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

## 4.5 R4 — Three-way conclusions (`reproduced`)

Seventeen synthetic cases under `r4-evidence-sufficiency-v1` exercise all three
classes, including a **bounded handoff** slice: a principal receipt alone does
not authorize a delegate (`missing_evidence`); allowing via that receipt while
the delegate grant is revoked is `failed_enforcement`; an observed active
delegate grant with a correct gate is `supported`. Core gate cases still cover
blind Worlds A/B, revoked-still-allows, and active-still-denies. The ledger
comparator uses the same taxonomy via `classify_matched_comparison`. Cross-study
map: `baselines/three_way_conclusion_map.md`. Findings across R1–R5 carry an
explicit `conclusion_class` annotation. Finding `r4-f-evidence-sufficiency`
label **`reproduced`**; `all_checks_pass: true`; `three_way_classes_exercised:
true`.

## 4.6 R5 — Multi-agent / swarm generalization (`reproduced`)

Ten cases under `r5-swarm-audit-v1` with agents **A, B, C**: missing peer grant
observation (2); failed enforcement on broken post-spend allow and
foreign-receipt allow under revoke (2); supported contention, delegation-chain
assignee checks, and cross-agent receipt deny (6). Finding `r5-f-swarm-audit`
label **`reproduced`**; `agent_count: 3`; `three_way_classes_exercised: true`.
This establishes **method generalization** to a synthetic swarm under classical
one-use shared grants—not live BMO mesh equivalence or unbounded population
safety.

# 5. Discussion

**Synthesis.** R1/R2 are pinned reproductions used as exemplars; R3-L1 is a
bounded classical match; R4 defines the three-way discipline; R5 shows that
discipline still separates missing evidence, failed enforcement, and supported
outcomes when three agents contend for grants, form delegation chains, and
misuse receipts. Original authors of R1/R2 already reported those mechanisms’
core behaviors.

**Implications.** Multi-agent settings amplify evidence gaps and enforcement
failures; an audit method must refuse to treat peer activity or foreign receipts
as substitute observations. Swarm Witness makes that refusal executable.

**Limitations (summary).** ClassicalGate is a decision-model null; legacy R3 is
incomplete; ledger-claim equality is projection-scoped; R4/R5 are synthetic
(not live BMO mesh); R5 uses three agents and classical one-use grants—not
cryptographic multiparty auth or unbounded scale. Full Limitations appendix follows.

**Future work.** Isomorphic decision-model R3 probes; grant/epoch alias maps;
larger synthetic populations; continuous baseline-vs-claim diffs.
