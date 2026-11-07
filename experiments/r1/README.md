# R1 — SoundGate restart / recovery barrier

Reproduces the Apart Research claim that an acknowledged rejection survives
restart under SoundGate’s recovery barrier (paper: *A Restart Is Not
Permission…*, package `soundgate==0.1.3` at source revision `6568403`).

## Pins

See `artifacts/pins.yaml` (`r1`). Runnable sources:

1. **Paper artifact (primary sweep)** — ZIP embedded in the report PDF
   (`SHA-256 aec08353…`), containing `recovery-barrier/{build,experiment,analyze,check}.py`
   that rebuilds original / strict / barrier binaries from the pinned revision
   and runs the 153-history byte-prefix comparison.
2. **Upstream repo** — `https://github.com/sajjadanwar0/soundgate-paper` at
   `656840348dcf9660f8db7add9f3ca9f794a55926` (and later `0.1.4` regression
   `tests/wal_recovery_barrier.rs`).

## Run

From the swarm-witness root:

```bash
./experiments/r1/run_r1.sh
python3 experiments/r1/parse_summary.py
```

Requirements: Python 3.11+, Rust/`cargo` 1.89+, network (or cached crates) for
the first build, `curl`/`git`.

Outputs land under `evidence/r1/` (`build.log`, `experiment.log`,
`local-run-analysis.json`, `summary.json`, optional `cargo-wal-recovery-barrier.log`).

## Success criterion (claim card)

`prohibited_effects == 0` under the **recovery barrier** policy after restart,
across the published 153 histories per policy.
