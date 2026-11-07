# Multi-agent simulator (post-submission research)

Independent experimental harness for **causal interleavings** of principals
A/B/C with per-agent local observations and a separate authoritative
grant/effect ledger. Implements GitHub issue #10.

This is **not** a prerequisite for the Apart submission and does **not**
relabel R5 v1 (`experiments/swarm_r5/`) as concurrent.

## Model under test

| Component | Role |
| --- | --- |
| Deterministic scheduler | Replayable schedules (`seed` + ordered steps) |
| Agent mailboxes | Independently delivered observations |
| Authoritative ledger | Grant ownership, spend, committed effects |
| Reference / mutant policies | Decide from *local* evidence only |
| Oracle | Required decision from authoritative state (separate code) |
| Evaluator | Post-hoc audit conclusion + observation denominators |

Native observations on each claim distinguish **decision**, **committed
effect**, **authoritative owner state**, and **audit conclusion**. A bad
decision is never silently asserted to be an executed unauthorized effect:
both fields are recorded independently (see `audit_diagnosis` axes), and the
reference arm's ledger **refuses** spent/revoked settlement (`effect_settlement=
refused`) even when a local policy decision was `allow`.

Observation denominators distinguish `current_grant_observation` from
`stale_grant_observation`; adversarial late deliveries are not labeled current.

## Cases

| Theme | Cases |
| --- | --- |
| Competing interleavings | A-first vs B-first on the same shared grant |
| Revocation / late observation | Stale active delivery after revoke (commit refused) |
| Reference vs mutant | Identical TOCTOU schedule; reference preserves one-use; mutant double-commits |
| Paired worlds | Blind / irrelevant / distinguished active↔revoked |

## Exclusions (explicit)

- Live BMO mesh equivalence
- Production concurrency guarantees
- Unbounded swarm safety
- Automatic upgrade of the R5 sequential Finding

A simulated interleaving is not a live distributed-system deployment.

## Run

```bash
python3 experiments/multi_agent_sim/run.py
pytest -v tests/test_multi_agent_sim.py
```

Output: `evidence/multi_agent_sim/` (runs, findings, machine-readable
`traces/`, reproducible `manifests/`).

Pins: `artifacts/pins.yaml` → `multi_agent_sim.source_pin`.
