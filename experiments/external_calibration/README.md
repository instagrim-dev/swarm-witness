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
5. **Transfer probe** — EvidenceGraph ATTR packets on seeds 1–2 after seed-0 calibration.

```bash
PYTHONPATH=src python experiments/external_calibration/run.py
```

Writes:

- `evidence/external_calibration_v1/packets.json`
- `evidence/external_calibration_v1/matrix.csv`
- `evidence/external_calibration_v1/matrix.json`
- `evidence/external_calibration_v1/summary.json`
- `evidence/external_calibration_v1/REPORT.md`
- `evidence/external_calibration_v1/PROFILE_LABELS.md`
- `report/external_calibration_v1/MATRIX.md`
- `report/external_calibration_v1/PROFILE_LABELS.md`

Native prior arms are scored beside naive / weak_checklist / strong_invariant /
swarm_witness on the **same** translated packets. SoundGate packets score only
the named policy as a native arm; other policies stay reference-only.

Seed-0 calibration remains retrospective. The seed 1–2 ATTR probe can earn
`transfer_claim` for that family only. Agreement with the authored
`strong_invariant` baseline alone is not external calibration. Unqualified
global `strong` remains undefined; use earned profile labels.
