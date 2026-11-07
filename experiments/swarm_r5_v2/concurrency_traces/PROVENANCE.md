# Provenance of pinned concurrency traces

These JSON files are pinned copies of `evidence/multi_agent_sim/runs/mas-*.json`
from the multi-agent simulator, protocol `multi-agent-sim-v1`.

Current source commit `28b364251a0c4205483aad4f6d49cdedea8b5d5c`
(PR #23, `cursor/stale-decision-evidence-integrity-6e36`, stacked on #19).
That commit is the current reference: the contention loser is stale at the
decision (no current grant observation), the revoked-grant reference effect is
`effect_settlement=refused` with `committed_effect=false`, and the forged
assignee reference observation is `misbound` with `failure_origin=evidence`
while the effect stays prevented.

Superseded, not current:

- PR #15 `490d0bd5c6bbb4159b9e002e7a3ce4a22ca7e38e` recorded the revoked-grant
  reference arm as committing (`failure_origin=effect_boundary`).
- PR #19 `c23f2954660e22ea5dace762197107c604f13bb8` refused that effect, but the
  contention loser still had a current grant observation and the forged
  assignee reference was `decision_policy`, not misbound evidence.

R5-v2 does not vendor the simulator. Digests below are enforced by
`verify_pinned_concurrency_digests` / `evaluate_r5_v2_success`.

## sha256 digests

- `mas-interleave_a_first_reference.json`: `5187d3988062c1fb96ae7cb56a48e3a236ad75a91f8adaaabec063cba336d2f9`
- `mas-interleave_b_first_reference.json`: `278426a8048d32763475ffe1a9cf38d8cf9f889c36935a8c68aea58243d2baf4`
- `mas-mutant_forged_assignee_boundary.json`: `3534af27d6e1eaade4040f152613eec60d75f7d41ebdce98af6bd9e1ade043cb`
- `mas-mutant_ignore_spend_contention.json`: `435c588145452b3822c5a8db3808dc2bbbc1aa3851f5e892b2ed355bfb5378e8`
- `mas-reference_contention_one_use.json`: `1228a071ac39926116f53ed6173017eab1d0df24791e6eb4472bcac76992f984`
- `mas-reference_forged_assignee_boundary.json`: `f5bd8c80f213ecd6f64a58697f6e905939dad9a21a675a8224f84bd46e4f52a9`
- `mas-revocation_late_observation_reference.json`: `f4208f67948bdd3f385d0dc16f97ec2698d1ecdd8cd2c8e376b46074660e1f14`

## What the pins prove (and do not)

- Reference vs mutant contention pins share `seed=404`, `event_count=11`, and
  `schedule_id=sched-toctou-contend`.
- Their run documents are not byte-identical: the reference refuses the second
  effect and the mutant commits it. `reference_vs_mutant_byte_identical_schedule_id`
  stays an untested seam.
- The contention reference loser (`b-claim`) has no current grant observation
  (`observation_freshness=stale`). An allow there coexists with a refused effect.
- `b-late` on the revoked-grant reference arm is refused, not committed.
- `b-forge` on the forged-assignee reference arm is misbound evidence; the
  effect is prevented. The mutant arm of that scenario commits and is not the
  reference.

Regenerate from the simulator commit above (do not merge that stack into this
branch, and do not copy #15 or #19 run files):

```bash
git show 28b364251a0c4205483aad4f6d49cdedea8b5d5c:evidence/multi_agent_sim/runs/mas-interleave_a_first_reference.json
# repeat for each mas-*.json listed above, write into this directory,
# refresh the sha256 lines, then re-run experiments/swarm_r5_v2/run.py
```

Exclusions carried with the simulator claim remain in force: no live BMO mesh
equivalence, no production concurrency guarantees, no unbounded swarm safety.
