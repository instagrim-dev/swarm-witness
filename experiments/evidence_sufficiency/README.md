# R4 — three-way conclusions (missing / failed / supported)

Executable check that Swarm Witness distinguishes:

| Class | Meaning | Finding label |
| --- | --- | --- |
| `missing_evidence` | Required discriminating observation absent | `unresolved` |
| `failed_enforcement` | Evidence complete; mechanism violates property | `contradicted_in_scope` |
| `supported` | Evidence complete; property holds | `reproduced` |

Worlds A (grant active) and B (grant revoked) share an identical old receipt.

```bash
python3 experiments/evidence_sufficiency/run.py
python scripts/check_evidence.py --write-index
```

Output: `evidence/r4/`. Taxonomy: `src/swarm_witness/conclusion_classes.py`.
