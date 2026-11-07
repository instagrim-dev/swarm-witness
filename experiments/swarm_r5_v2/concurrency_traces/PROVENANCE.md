# Provenance of pinned concurrency traces

These JSON files are **pinned copies** of `evidence/multi_agent_sim/runs/mas-*.json`
from the independent multi-agent simulator (GitHub issue #10, PR #15,
protocol `multi-agent-sim-v1`, source pin `swarm-witness-multi-agent-sim-v1`).

They are consumed by R5-v2 concurrency-derived scenario rows so this protocol
does **not** re-implement the simulator and does **not** silently treat
sequential harness cases as races. Digests below are enforced by
`verify_pinned_concurrency_digests` / `evaluate_r5_v2_success`.

## sha256 digests

- `mas-interleave_a_first_reference.json`: `32cd1c67269c595cc3f8bff7e7a753121c004e767e593ee33288761ccc38a67d`
- `mas-interleave_b_first_reference.json`: `1b36d36334cdf003a2fee1d236fb14c7ccc1cd911075aba50fcc41c934bfa2fa`
- `mas-mutant_ignore_spend_contention.json`: `d982ab66a9ac831fae27c29d4d8755ca6f373e490f4069433a0a8e25a4c6a39e`
- `mas-reference_contention_one_use.json`: `65983060e566b6fa5cb17478adf4f723659616a03cabc2d7f237c2cfebff5c9d`
- `mas-revocation_late_observation_reference.json`: `6784fbf4df9a0aad5af832cb2c6cc4acb7c2d0e43ffbe9ffbb998f5d633b0829`

## What the pins prove (and do not)

- Reference vs mutant contention pins share `seed=404` and `event_count=11`.
- Their upstream `schedule_id` strings differ (`sched-ref-contend` vs
  `sched-mut-contend`). R5-v2 therefore claims
  `reference_vs_mutant_same_seed_contention`, **not** byte-identical
  `schedule_id` equality (that remains an untested seam pending simulator
  regeneration).
- Pinned run JSON does not embed the full step list; schedule identity beyond
  seed+event_count is not re-proven here.

Regenerate (when the simulator package is available on the branch):

```bash
python3 experiments/multi_agent_sim/run.py
cp evidence/multi_agent_sim/runs/mas-interleave_a_first_reference.json \
   evidence/multi_agent_sim/runs/mas-interleave_b_first_reference.json \
   evidence/multi_agent_sim/runs/mas-reference_contention_one_use.json \
   evidence/multi_agent_sim/runs/mas-mutant_ignore_spend_contention.json \
   evidence/multi_agent_sim/runs/mas-revocation_late_observation_reference.json \
   experiments/swarm_r5_v2/concurrency_traces/
# then refresh sha256 lines above and re-run experiments/swarm_r5_v2/run.py
```

Exclusions carried with the simulator claim remain in force: no live BMO mesh
equivalence, no production concurrency guarantees, no unbounded swarm safety.
