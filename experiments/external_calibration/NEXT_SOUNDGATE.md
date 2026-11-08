# Status — completed corpora and remaining transfer bar

SoundGate R1, BMO L1, LessWrong scope (author warrants), and EvidenceGraph
seed-repeatability are in the combined matrix. See `README.md` and
`report/external_calibration_v1/MATRIX.md`.

Regenerate:

```bash
PYTHONPATH=src python experiments/external_calibration/run.py
```

`transfer_claim` stays false until fresh or genuinely held-out claim families
are scored. Seed 1–2 ATTR packets only check repeatability of identical
encoded classifier inputs.
