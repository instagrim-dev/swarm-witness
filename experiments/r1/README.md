# R1 — SoundGate restart / recovery barrier

Reproduces the Apart Research claim that an acknowledged rejection survives
restart under SoundGate’s recovery barrier (paper: *A Restart Is Not
Permission…*, package `soundgate==0.1.3` at source revision `6568403`).

## Pins

See `artifacts/pins.yaml` (`r1`). Runnable sources:

1. **Paper artifact (primary sweep)** — ZIP embedded in the report PDF
   (`SHA-256 aec08353…`), containing `recovery-barrier/{build,experiment,analyze,check}.py`
   that rebuilds original / strict / barrier binaries from the pinned revision
   and runs the byte-prefix comparison.
2. **Upstream repo** — `https://github.com/sajjadanwar0/soundgate-paper` at
   `656840348dcf9660f8db7add9f3ca9f794a55926` (and later `0.1.4` regression
   `tests/wal_recovery_barrier.rs`).

## Run

From the swarm-witness root:

```bash
# Full clone/build/sweep (writes local-run-analysis.json, then Run + Finding)
./experiments/r1/run_r1.sh

# Or derive Run/Finding from retained analysis without rebuild
./experiments/r1/run_r1.sh --derive-only
# equivalent: SWARM_WITNESS_R1_REUSE_ANALYSIS=1 ./experiments/r1/run_r1.sh
```

Requirements for a full run: Python 3.11+, Rust/`cargo`, network (or cached
crates) for the first build, `curl`/`git`.

### Honesty contract

- Success requires a `completed` Run whose `histories_per_policy` and prohibited
  counts are **counted from** `local-run-analysis.json` case records.
- If analysis is missing or the runner aborts, the script writes
  `execution_status=unrun|failed` plus Finding `label=unresolved` and exits
  nonzero — never a successful empty no-op.
- Authoritative label: `evidence/r1/findings/*.json`. `summary.json` /
  `result.yaml` are convenience mirrors only.
- `baselines/r1_*.md` is authored mechanism interpretation only — **not** an
  empirical `classical_baseline_matches` finding.

## Success criterion (claim card)

`prohibited_effects == 0` under the **recovery barrier** policy after restart,
across each constructed history retained in the case records (denominator
counted from those records, not a planned constant).
