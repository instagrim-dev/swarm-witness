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

`BMO_ROOT` must contain pin object `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe`.
The runner materializes that commit via `git archive` (dirty HEAD is never
compiled), then injects `bmo_adapter_test.go` + `bmo_adapter_fixture.go` only.
`run_id` must be a safe filename token; existing run directories are refused
(immutable evidence).

When `BMO_ROOT` is absent, an offline SQLite L1 stand-in emits inspectable
traces (`native_bmo=false`). Findings stay **`unresolved`** until the native
bridge measures real L1 outcomes under fail-closed qualification (manifest,
exit 0, adapter identity, archive inventory, bridge hashes, archived log).
Matched runs can publish `classical_baseline_matches` on projection-scoped
equality (grant_spent, counts, call_id)—not synthetic grant/epoch hash parity.

Selected published run: `evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2/`.

The affirmative native requalification is
`evidence/r3/ledger_claim_v1/2026-11-08-ledger-bridge-requalify/`.
Its retained summary has `native_bmo=true`, agreement `matched`,
conclusion class `supported`, and finding label `classical_baseline_matches`. Compare that directory to re-check the
current bridge against that manifest. Comparing the 2026-11-07 run checks
the current bridge against the earlier manifest. A bridge-hash mismatch
there is a source-identity rejection: agreement can stay `matched` and
validity true while the printed label is `unresolved` and `native_bmo`
becomes false. That result does not replace the requalified run.

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
