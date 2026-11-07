# R3 — BMO retained-grant vs classical admit check

Compares BMO’s preexisting ordinary-retry retained-grant owner witness (and
related sessioncompaction tests) to a classical **durable grant table checked
before admit**. The null model is `ClassicalGate` in
`src/swarm_witness/classical_gate.py`: retained start claim alone never
authorizes relaunch; rejection survives map reload; only `active_grant` allows
execute; stale/unknown defaults to deny.

## Pins

See `artifacts/pins.yaml` (`r3`):

- `bmo_root`: `/Users/user1/Documents/dev/bmo` (preexisting; not modified)
- Preferred tests:
  `internal/sessioncompaction/ordinary_retry_retained_grant_owner_witness_test.go`

## Run

From the swarm-witness root:

```bash
./experiments/r3/run_bmo_tests.sh
python3 experiments/r3/compare.py
pytest tests/test_classical_gate.py -v
```

Requirements: Go toolchain able to build BMO; read-only access to the pinned
`bmo_root`. Weekend code lives only under this `swarm-witness/` tree.

Outputs under `evidence/r3/`:

- `bmo_go_test.log` — verbatim `go test` output
- `summary.json` — comparison rows + pass/fail counts
- `result.yaml` — conclusion label (expected: `classical_baseline_matches`)

## Success criterion (claim card)

`relaunch_without_fresh_durable_grant == 0` when the classical admit barrier is
enforced — i.e. retained metadata / spent / rejected / stale grant states deny,
and only a current active durable grant allows execute.
