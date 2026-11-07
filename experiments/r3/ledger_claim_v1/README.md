# r3-ledger-claim-v1

Derived R3 experiment: one-use retained-grant first-edit claim under cold DB
reopen and explicit rollback. Preserves legacy `r3-matched-decision-model`.

## Arms

| Arm | Implementation |
| --- | --- |
| Classical | `ClassicalLedgerGate` (`src/swarm_witness/classical_ledger_gate.py`) — independent SQLite owner |
| BMO | Tagged disposable-tree bridge calling `ClaimOrdinaryRetainedGrantFirstEditTx` |

Do **not** use `OrdinaryRetryRetainedGrantShapeEligible` as the admission result.

## Run

```bash
python3 experiments/r3/ledger_claim_v1/run_matched.py \
  --bmo-root "$BMO_ROOT" --run-id "$RUN_ID"

python3 experiments/r3/ledger_claim_v1/compare.py \
  --run-dir "evidence/r3/ledger_claim_v1/$RUN_ID"
```

`BMO_ROOT` must be at pin `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe`. The runner
copies a disposable tree and injects `bmo_adapter_test.go` +
`bmo_adapter_fixture.go` only. The working product checkout is untouched.

When `BMO_ROOT` is absent, an offline SQLite L1 stand-in emits inspectable
traces (`native_bmo=false`). Findings stay **`unresolved`** until the native
bridge measures real L1 outcomes.

## Bridge opt-in

```bash
SWARM_WITNESS_R3_CASES=<abs> SWARM_WITNESS_R3_OUT=<abs> \
  go test -tags=swarm_witness_r3 ./internal/sessioncompaction/ \
  -run '^TestSwarmWitnessR3Probe$' -count=1
```

Link owner-witness fixture helpers in `bmo_adapter_fixture.go` before expecting
`native_bmo=true`.

## Cases

T01–T06 in `cases.yaml`. First vertical slice: T02, T03, T04.
