# R5 — sequential multi-principal audit (taxonomy transfer)

In-memory sequential shared-grant model with named principals A/B/C.
Not concurrent workers or live BMO mesh.

```bash
python3 experiments/swarm_r5/run.py
python scripts/check_evidence.py --write-index
```

Expect: `reproduced`; `model=sequential_shared_grant_multi_principal`;
all three conclusion classes; broken allows leave `effect_committed=false`.

Causal interleavings / independently scheduled principals (issue #10) live in
[`experiments/multi_agent_sim/`](../multi_agent_sim/) and do not relabel this
R5 v1 Finding.
