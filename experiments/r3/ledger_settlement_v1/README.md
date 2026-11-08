# r3-ledger-settlement-v1

Settlement continuation of the retained `r3-ledger-claim-v1` calibration.
The retained six-case comparison is unchanged. This protocol starts from a
committed first-edit claim and then calls BMO's existing settlement
transactions.

## Question

Once the grant has been correctly claimed and the ledger transaction has
committed, which added observation establishes the delegated effect?

## Arms

| Arm | Implementation |
| --- | --- |
| Classical | `ClassicalLedgerGate` records the shared settlement contract: `applied` binds tool, mutation, and artifact; `not_entered` binds the tool and a definite no-effect receipt |
| BMO | Pinned `c8297333b3bf31ded96ca0e8b39c531d3bcea97f`. The bridge calls `ClaimOrdinaryRetainedGrantFirstEditTx`, then `SettleOrdinaryRetryFirstEditTx` or `SettleOrdinaryRetryFirstEditNoEffectTx` |

The native tool, mutation, artifact, and no-effect rows are the records those
settlement transactions require. They are fixture-authored inputs to the
production settler, not a live model edit.

## Cases

- `S01`: valid claim, ledger inspect, applied settlement, ledger inspect.
- `S02`: valid claim, ledger inspect, definite no-effect settlement, ledger inspect.
- `S03`–`S05`: an applied label with a missing mutation, swapped artifact/mutation order, or wrong call ID. These refuse and leave the effect unresolved.
- `S06`: a no-effect label contradicted by a write. It does not produce a definite no-effect settlement.
- `S07`–`S09`: an applied or no-effect label with missing or unrelated terminal evidence. The effect-applied proposition stays unresolved.

`S02`'s refutation applies only to the effect-applied proposition. The first published run, `2026-11-08-ledger-settlement-v1`, contains `S01` and `S02`. Later controls are a separate run and are not added to the six-case ledger calibration.

The ledger view after the claim leaves the delegated effect unresolved. The
settlement record is the observation that can change that verdict. Equality
is within a case: the ledger prefix and that case's settlement contract.
`S01` and `S02` are expected to differ in the later record.

## Run

```bash
python3 experiments/r3/ledger_settlement_v1/run_matched.py \
  --bmo-root "$BMO_ROOT" \
  --run-id 2026-11-08-ledger-settlement-v1
```

Existing run directories are refused. This command does not write
`evidence/r3/ledger_claim_v1/` or `evidence/r3_ledger_claim_v1/`.
