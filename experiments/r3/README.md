# R3 — matched decision-model comparison

Shared case manifest: `cases.yaml`. Both arms consume the same inputs.

## Classical arm (decision-model)

`ClassicalGate` in `src/swarm_witness/classical_gate.py`:

- Inputs: `(state, request, grant_version)`
- `active_grant` + matching version + `execute` → allow
- `retained_start_claim` + `relaunch` → deny
- stale `grant_version` → deny
- `rejected` + `execute` → deny

**Not** a durability / fresh-process restart claim. `dump`/`load` are
in-process fixture copies only.

## BMO arm

`run_bmo_cases.py` uses a narrow instrumented harness. Decisions are emitted
only from matching test assertions or isomorphic harness probes. Package
pass/fail counts are metadata only and **never** fill decisions. Missing
isomorphic observations → `execution_status=missing`.

Pinned revision: `artifacts/pins.yaml` → `r3.git_rev`
(`4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe`). Recorded on every BMO run.

## Epistemic extension

Case `stale_grant_version` is the home for the extension: same input shape as
`active_grant_execute`; distinguishing observation = `grant_version`.

## Run

```bash
python3 experiments/r3/run_classical_cases.py
python3 experiments/r3/run_bmo_cases.py
python3 experiments/r3/compare.py
pytest tests/test_classical_gate.py tests/test_r3_compare.py -v
```

Optional (metadata only; does not supply isomorphic decisions):

```bash
./experiments/r3/run_bmo_tests.sh
```

## Outputs

- `evidence/r3/runs/classical-<case_id>.json`
- `evidence/r3/runs/bmo-<case_id>.json`
- `evidence/r3/findings/r3-f-comparison.json` (authoritative label)
- `evidence/r3/summary.json` / `result.yaml` (mirrors)

## Success / honesty

Unmatched or missing BMO cases **cannot** yield Finding
`classical_baseline_matches`. Emitting `assumption_dependent` / `missing` when
BMO lacks isomorphic observations is scientific success for this task.
