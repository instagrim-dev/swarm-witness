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
