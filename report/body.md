# 1. Introduction

Agent-facing “safety” components—authorization gates, receipt graphs, retained
grants—are frequently marketed as multi-agent innovations. Many instantiate
older durable-log, provenance, and admit-barrier patterns. When a report claims
a restart-safe refusal, receipt-based attribution, or retained-grant relaunch
control, auditors need to know whether the result is a new property, a repaired
instance of a classical mechanism, or an assumption-dependent analogy.

**Research question.** After matching policy, observations, trust assumptions,
durability, and enforcement coverage, which claimed benefits of agent-safety
mechanisms remain?

**Threat / failure modes.** (i) An admission gate forgets an acknowledged
rejection across restart when the durable log is not recovered before admit.
(ii) A verifier treats possession of a copied receipt token as event
attribution without exclusivity or authenticity. (iii) Retained start/grant
metadata is treated as standing relaunch authority without consulting a durable
grant table.

**Main contributions.**

1. **Swarm Witness claim-audit method:** pinned artifacts, typed claim cards,
   classical baselines, discriminating experiments, and fail-closed labels
   (`reproduced`, `assumption_dependent`, …) with an evidence index checker.
2. **Executable audits of three public/pinned targets** (SoundGate recovery
   barrier; EvidenceGraph receipt stress; BMO retained-grant owner path) with
   metrics taken only from committed `evidence/*/summary.json`.
3. **Classical baseline cards** showing when a “novel” repair is
   recover-before-admit or no-implicit-exclusivity reasserted, versus when
   mechanism-class proxies do not justify isomorphic decision claims.

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
  stress harness distinguishing possession from attribution (git rev
  `a5ea5c9`, paper baseline `efbd419`).
- **BMO ordinary-retry retained grant** — preexisting durable grant /
  owner-witness tests under pinned `bmo_root` (read-only `go test`).

Classical nulls (baselines in-repo): durable log validate/repair/replay before
admit; no implicit exclusivity for receipt tokens; durable grant table checked
before admit with retained metadata never authorizing relaunch. Swarm Witness
differs from building a new gate: it asks what labels survive matched baselines
and discriminating checks.

# 3. Methods

**Claim cards** (`claims/*.yaml`) fix `property`, `scope`, `quantifier`,
`success_criterion`, `assumptions`, `baseline`, and `discriminating_checks`.
**Pins** (`artifacts/pins.yaml`) freeze revisions and hashes. **Baselines**
state the mechanism class without equating every proxy to a decision match.
**Evidence** uses `ResultRecord` labels; `scripts/check_evidence.py` fails closed
if `evidence/index.yaml` disagrees with `result.yaml` or files are missing.

**R1 (SoundGate).** Rebuild and sweep the paper recovery-barrier harness at
pinned source `6568403`. Compare policies `original`, `strict`, and `barrier`
over the published histories. Success for reproduction: barrier
`prohibited_effects == 0` with original showing the defect. Supplemental cargo
`wal_recovery_barrier` on 0.1.4 recorded in notes.

**R2 (EvidenceGraph).** Run `incident_stress.py` at `a5ea5c9` against baseline
`efbd419`. Contract checks over seeds `{0,1,2}`: old-rule wrong attributions on
relay, safer supported/correct on relay, clean withheld without exclusivity,
false-exclusivity confident errors. Label `reproduced` when all contract checks
pass and the safer rule restores abstention under undeclared exclusivity.

**R3 (BMO vs ClassicalGate).** Run preferred retained-grant Go tests
read-only; compare four ClassicalGate conditions to BMO observations as
`mechanism_class_proxy`, `proxy_mismatch`, or isomorphic match. Do **not**
hardcode BMO decisions from ClassicalGate. Label `assumption_dependent` when
affinity is proxy-only (0 isomorphic matches).

# 4. Results

Labels from `evidence/index.yaml` / `result.yaml` only: R1 **reproduced**, R2
**reproduced**, R3 **assumption_dependent**. Metrics below cite
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
histories; original loses restrictions (143 prohibited effects). Cargo
`wal_recovery_barrier` on 0.1.4: 3 passed (notes). Mechanism class remains
classical recover-before-admit (`baselines/r1_wal_recover_before_admit.md`).

## 4.2 R2 — Receipt ≠ attribution (`reproduced`)

`condition_by_seed_checks` **36**, passed **36**; seeds 0,1,2;
`all_contract_checks_pass: true`;
`source_tree_sha256=2962568f…`.

| Metric (per seed) | seed 0 | seed 1 | seed 2 |
| --- | ---: | ---: | ---: |
| old_rule wrong attributions on relay | 1 | 1 | 1 |
| safer supported on relay | 0 | 0 | 0 |
| safer correct on relay | 0 | 0 | 0 |
| clean withheld without exclusivity | 12 | 12 | 12 |
| shared_tokens correct | 0 | 0 | 0 |
| false_exclusivity confident errors | 1 | 1 | 1 |

Relay seed-0 outcomes: ambiguous 10, unmatched 2. Safer default withholds
attribution without exclusivity; old rule errs once per seed on relay. Mechanism
class: no implicit exclusivity (`baselines/r2_no_implicit_exclusivity.md`).

## 4.3 R3 — Retained grant vs ClassicalGate (`assumption_dependent`)

BMO Go tests: **pass_count 6**, **fail_count 0**, `package_ok: true`. Comparison
rows: **proxy_rows_ok 3 / 3**, **isomorphic_decision_matches 0 / 4**.

| Condition | ClassicalGate | BMO observed | Relation |
| --- | --- | --- | --- |
| retained_start_claim + relaunch | deny | not_isomorphic | mechanism_class_proxy |
| rejected + restart + execute | deny | not_isomorphic | proxy_mismatch |
| active_grant + execute | allow | not_isomorphic | mechanism_class_proxy |
| stale grant copy vs current | deny | not_isomorphic | mechanism_class_proxy |

Proxy rows show deny/allow-shaped affinity (spent/prior-consumer, owner-witness
admit, wrong/altered grant). `rejected+restart` maps to process-reload in the
null model; BMO `LegacyWriterBoundary` is a writer-boundary race
(`proxy_mismatch`)—not claimed as a decision match.

# 5. Discussion

**Implications.** For Tracks 3–4, durable identity and oversight claims should
be scored against classical admit and evidence rules. R1 and R2 show that
published repairs can **reproduce** restorations of those rules under pinned
harnesses; that is valuable engineering and audit evidence, not proof of a new
multi-agent primitive. R3 shows how easy it is to over-claim: related tests and
proxy shapes ≠ isomorphic contracts.

**Limitations (summary).** Finite pinned sweeps ≠ general equivalence across
deployments; R3 is explicitly assumption-dependent; preexisting BMO surfaces
were consulted read-only. Full Limitations and Dual-Use appendix follows.

**Future work.** Expand pins to more gate implementations; strengthen R3 toward
shared observation APIs where isomorphic matches are possible; automate
baseline-vs-claim diff reports for continuous oversight of agent
infrastructure.
