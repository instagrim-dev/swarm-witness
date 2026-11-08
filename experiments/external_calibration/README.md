# External calibration (retrospective)

Calibrates the frozen classifier ladder against **prior claim-assessment
disciplines**, under matched observation access.

## Question

Can one executable evidence protocol recover and transfer the
claim-assessment disciplines demonstrated across existing systems, under
matched observation access?

## Corpora

1. **EvidenceGraph R2** — attribution vs possession; false exclusivity; incomplete capture.
2. **SoundGate R1** — restriction survival **and** useful availability as separate claims.
3. **BMO L1** — ledger first-edit properties vs non-settlement scope.
4. **LessWrong reproduction** — release/census vs original-incident certification, upgrade slots, and environment identity.

```bash
PYTHONPATH=src python experiments/external_calibration/run.py
```

Writes:

- `evidence/external_calibration_v1/packets.json`
- `evidence/external_calibration_v1/matrix.csv`
- `evidence/external_calibration_v1/matrix.json`
- `evidence/external_calibration_v1/summary.json`
- `evidence/external_calibration_v1/REPORT.md`
- `report/external_calibration_v1/MATRIX.md`

Native prior arms are scored beside naive / weak_checklist / strong_invariant /
swarm_witness on the **same** translated packets.

This run is **retrospective calibration**. It does not claim held-out transfer.
Agreement with the authored `strong_invariant` baseline alone is not external
calibration. Unqualified global `strong` remains undefined; use profile labels.
