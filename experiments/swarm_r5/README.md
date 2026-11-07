# R5 — multi-agent / swarm audit generalization

Generalizes the three-way conclusion method to a synthetic swarm of agents
**A, B, C** under classical one-use shared grants.

| Theme | Cases |
| --- | --- |
| Missing peer observation | claim without observing grant |
| Shared-grant contention | first allow / second deny; broken second allow |
| Delegation chain | assignee required; A→B→C allow |
| Cross-agent receipt | deny after spend; broken allow on revoke |

```bash
python3 experiments/swarm_r5/run.py
python3 scripts/annotate_conclusion_classes.py
python scripts/check_evidence.py --write-index
```

Output: `evidence/r5/`.
