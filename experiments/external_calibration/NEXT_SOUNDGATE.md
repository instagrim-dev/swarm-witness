# Status — SoundGate and later corpora

SoundGate R1, BMO L1, and LessWrong reproduction-scope packets are now part of
the combined matrix. See `README.md` and `report/external_calibration_v1/MATRIX.md`.

Regenerate:

```bash
PYTHONPATH=src python experiments/external_calibration/run.py
```

Held-out / fresh families are required before any `transfer_claim`.
