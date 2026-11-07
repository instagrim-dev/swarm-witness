# Appendix A. Limitations and Dual-Use / Ethical Considerations

## What each result does and does not establish

**R1 (`reproduced`).** Establishes that, on the pinned SoundGate recovery-barrier
harness (source revision `6568403`), the barrier policy yields
`prohibited_effects = 0` across 153 histories while the original policy yields
143 prohibited effects, with 147 strict refusal-startup refusals under the
strict policy. Does **not** establish that every agent admission gate is
restart-safe, that SoundGate is free of other defect classes, or that
recover-before-admit is a new multi-agent invention (it matches the classical
durable-log baseline).

**R2 (`reproduced`).** Establishes that the pinned EvidenceGraph stress pack
(`a5ea5c9` / baseline `efbd419`) passes 36/36 condition-by-seed checks: old-rule
relay wrong attributions are 1 per seed; safer relay supported attributions are
0; clean runs withhold all 12 attributions without exclusivity declarations.
Does **not** establish that all receipt or ledger systems are safe under
relay/copy, or that exclusivity declarations themselves cannot be gamed outside
the modeled threat surface.

**R3 (`assumption_dependent`).** Establishes that preferred BMO retained-grant
tests pass (6/6) and that ClassicalGate vs BMO comparison yields 3/3 ok proxy
rows with **0** isomorphic decision matches across 4 rows (one
`proxy_mismatch`). Does **not** establish that ClassicalGate and BMO share an
API or that deny/allow-shaped proxies imply decision equivalence. Retained
metadata ≠ relaunch authority remains a classical durable-grant-table claim,
shown here only via mechanism-class affinity under stated assumptions.

## Finite experiments are not general equivalence

Pinned histories, seeds `{0,1,2}`, and preferred Go tests are finite. Passing
them does not imply equivalence across versions, storage backends, concurrent
writers outside the model, or production deployments. Labels apply to the
stated scope on the claim cards only.

## Dual-use / adversarial use of the audit method

An executable claim-audit method can help **defenders** find weak gates and
attribution gaps—and can also help **adversaries** locate the same gaps
(restart races, possession-as-attribution, retained-metadata relaunch). We
publish **tests, pins, matched baselines, and labels**, not exploit kits,
weaponized harnesses, or production credentials. Reproduction artifacts are
scoped to already-public or author-local preexisting trees (`PREEXISTING.md`).

## Preexisting code vs weekend analysis

Oct 25 scaffold paths and the external BMO tree at pinned `bmo_root` predate
this sprint and were not modified for R3 beyond read-only `go test`. Weekend
work is the Swarm Witness schema, pins, claim cards, baselines, experiment
wrappers, evidence records, index checker, and this report. Judges should
score the audit contribution, not treat preexisting BMO surfaces as sprint
inventions.
