# R4 — evidence sufficiency (Worlds A/B)

Executable check that Swarm Witness refuses to justify a current-permission
claim from an old receipt when current grant state is unobserved.

| World | Hidden grant | Shared visible evidence |
| --- | --- | --- |
| A | active | same old receipt |
| B | revoked | same old receipt |

Without the discriminating observation (`current grant state`), assessments are
**unsupported** and identical. Supplying current grant separates allow vs deny.
An irrelevant fact must not upgrade the conclusion. Misbound observations are
recorded as adversarial controls.

```bash
python3 experiments/evidence_sufficiency/run.py
python scripts/check_evidence.py --write-index
```

Output: `evidence/r4/`.
