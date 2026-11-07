# R5 — sequential multi-principal audit (taxonomy transfer)

In-memory sequential shared-grant model with named principals A/B/C.
Not concurrent workers or live BMO mesh.

```bash
python3 experiments/swarm_r5/run.py
python scripts/check_evidence.py --write-index
```

Expect: `reproduced`; `model=sequential_shared_grant_multi_principal`;
all three conclusion classes; broken allows leave `effect_committed=false`.

Wider-coverage follow-on (issue #11) lives in
[`experiments/swarm_r5_v2/`](../swarm_r5_v2/) as protocol `r5-swarm-audit-v2`
and does **not** overwrite this v1 Finding.

