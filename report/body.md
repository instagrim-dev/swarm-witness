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
3. **Evidence-sufficiency audit (R4)** that refuses to justify permission when
   Worlds with identical old receipts differ only in unobserved current grant
   state, and that upgrades only when a discriminating observation is supplied.
4. **Not claimed:** generalization to multi-agent delegation / swarm behavior.

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

**R4 (evidence sufficiency).** Worlds A (grant active) and B (grant revoked)
share an identical old receipt. Without observing current grant state,
assessments must remain **unsupported** and identical. Observing current grant
must separate allow vs deny. An irrelevant observation must not upgrade
unsupported assessments. Misbound observations are recorded as adversarial
controls. Protocol: `experiments/evidence_sufficiency/`.

# 4. Results

Labels from `evidence/index.yaml` / findings only: R1 **reproduced**, R2
**reproduced**, R3 decision-model **unresolved**, R3 ledger-claim-v1
**classical_baseline_matches** (bounded L1), R4 **reproduced**. Metrics cite
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

## 4.5 R4 — Evidence sufficiency (`reproduced`)

Nine synthetic cases under `r4-evidence-sufficiency-v1`: blind Worlds A/B with
the same old receipt remain **unsupported** and indistinguishable; an irrelevant
fact does not upgrade them; observing current grant separates allow (A) from
deny (B); legitimate allow proceeds when that evidence is present for A;
misbound observations are flagged as adversarial controls. Finding
`r4-f-evidence-sufficiency` label **`reproduced`**;
`all_checks_pass: true`; `unsupported_blind_count: 4`. This is the
cross-study methodological probe: the kit refuses an unsupported permission
finding when evidence is insufficient, then revises only after a discriminating
observation.

# 5. Discussion

**Synthesis.** R1 is a reproduced mechanism failure under pin; R2 is a
reproduced evidence-attribution failure; R3-L1 is an observed classical-baseline
match on a narrow L1 surface; R4 shows the audit method can withhold a success
label when Worlds sharing a receipt are still indistinguishable. None alone
establishes safety across a multi-agent population. Original authors of R1/R2
already reported the core behaviors—their role here is as controlled exemplars
for the auditing method.

**Implications.** A security mechanism can work as implemented while broader
claims remain under-supported. Swarm Witness makes that gap testable. Classical
reference monitors explain some agent-safety results; missing observations
explain others; the executable audit should prevent either case from being
overstated.

**Limitations (summary).** ClassicalGate is a decision-model null (not restart
durability); legacy R3 is incomplete; ledger-claim equality is projection-scoped;
R4 is synthetic (not live BMO or delegated agents); R1/R2 inspectability and pin
bindings are as above; multi-agent handoff is future work. Full Limitations and
Dual-Use appendix follows.

**Future work.** Isomorphic decision-model R3 probes; explicit grant/epoch
alias maps; delegated multi-agent handoff under the same evidence-sufficiency
discipline; continuous baseline-vs-claim diffs.
