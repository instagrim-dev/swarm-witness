# Provenance of pinned concurrency traces

These JSON files are **pinned copies** of `evidence/multi_agent_sim/runs/mas-*.json`
from the independent multi-agent simulator (GitHub issue #10, PR #15,
protocol `multi-agent-sim-v1`, source pin `swarm-witness-multi-agent-sim-v1`).

They are consumed by R5-v2 concurrency-derived scenario rows so this protocol
does **not** re-implement the simulator and does **not** silently treat
sequential harness cases as races.

Regenerate (when the simulator package is available on the branch):

```bash
python3 experiments/multi_agent_sim/run.py
cp evidence/multi_agent_sim/runs/mas-interleave_a_first_reference.json \
   evidence/multi_agent_sim/runs/mas-interleave_b_first_reference.json \
   evidence/multi_agent_sim/runs/mas-reference_contention_one_use.json \
   evidence/multi_agent_sim/runs/mas-mutant_ignore_spend_contention.json \
   evidence/multi_agent_sim/runs/mas-revocation_late_observation_reference.json \
   experiments/swarm_r5_v2/concurrency_traces/
```

Exclusions carried with the simulator claim remain in force: no live BMO mesh
equivalence, no production concurrency guarantees, no unbounded swarm safety.
