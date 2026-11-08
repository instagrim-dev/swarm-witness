# External calibration (retrospective)

Calibrates the frozen classifier ladder against **author-translated
representations of retained prior evidence**, under matched observation access.

## Question

Can one executable evidence protocol recover and transfer the
claim-assessment disciplines demonstrated across existing systems, under
matched observation access?

## Corpora

1. **EvidenceGraph R2** — scenario-level attribution vs possession (author-translated).
2. **EvidenceGraph R2 event** — expanded native conformance: event-by-event
   `produced` / `executed` relations against native safer/legacy rules and an
   evidence-derived adapter (observable records + declared assumptions only).
3. **SoundGate R1** — restriction survival **and** useful availability as separate claims.
4. **BMO L1** — ledger first-edit properties vs evidentiary non-settlement.
5. **LessWrong reproduction** — release/census vs original-incident certification, upgrade slots, and environment identity (author warrants only).
6. **Seed repeatability** — EvidenceGraph ATTR packets on seeds 1–2 with the same encoded classifier inputs as seed 0 (not transfer).

```bash
# Refresh native relation export (EvidenceGraph venv):
third_party/r2/evidencegraph/.venv/bin/python \
  experiments/external_calibration/eg_native_export.py

PYTHONPATH=src python experiments/external_calibration/run.py
```

Writes:

- `evidence/external_calibration_v1/eg_native_relations_seed0.json`
- `evidence/external_calibration_v1/packets.json`
- `evidence/external_calibration_v1/matrix.csv`
- `evidence/external_calibration_v1/matrix.json`
- `evidence/external_calibration_v1/summary.json`
- `evidence/external_calibration_v1/REPORT.md`
- `evidence/external_calibration_v1/PROFILE_LABELS.md`
- `evidence/external_calibration_v1/EVENT_CAPABILITY.md`
- `report/external_calibration_v1/MATRIX.md`
- `report/external_calibration_v1/PROFILE_LABELS.md`
- `report/external_calibration_v1/EVENT_CAPABILITY.md`

Native prior arms are scored beside naive / weak_checklist / strong_invariant /
swarm_witness on the **same** packets. The event corpus also scores
`eg_evidence_derived_adapter` (any temporal / capture / exclusivity reasoning
in that adapter is part of the evaluated method). SoundGate packets score only
the named policy as a native arm; other policies stay reference-only.
Scorer diagnostics (premise falsity, correctness/error counts) live in
`factual_outcome` / warrant notes, not in method observation inputs.

`transfer_claim` stays **false** for seed-repeatability and for expanded
native conformance. Fresh or genuinely held-out families are required for a
transfer claim. Unqualified global `strong` remains undefined; use earned
profile labels.
