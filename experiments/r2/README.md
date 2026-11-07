# R2 — Receipt possession ≠ event attribution

Reproduces the Apart Research / CrashLabs claim that a matching or copied
receipt token does not establish event attribution without an explicit
exclusivity or authenticity declaration (paper: *Receipt possession is not
event attribution*, EvidenceGraph stress pack).

## Pins

See `artifacts/pins.yaml` (`r2`). Runnable sources:

1. **Report PDF** — pinned blob URL (`report_pdf_sha256` in pins).
2. **Baseline before the sprint extension** — `efbd419` on
   `https://github.com/crashlabsai/evidencegraph` (cited in the paper; no
   `scripts/incident_stress.py` yet).
3. **Runnable stress pack (primary)** — same repo at
   `a5ea5c9947039009ca795275d834be7b61069080`, which publishes
   `scripts/incident_stress.py`, `src/evidencegraph/validate/stress.py`, and
   `docs/sprint/`.

The PDF’s “Code and Data” section originally said the sprint extension was
held pending disclosure; it is now on `main` and is what this harness runs.

## Run

From the swarm-witness root:

```bash
./experiments/r2/run_r2.sh
python3 experiments/r2/parse_summary.py
```

Requirements: Python 3.13+ via `uv`, `git`, `curl`, network for the first
`uv sync --locked`.

Upstream paper commands (from the pinned `evidencegraph` tree; output dir is
arbitrary):

```bash
cd third_party/r2/evidencegraph
uv sync --locked
uv run python scripts/incident_stress.py NEW_DIRECTORY --seeds 0 1 2
uv run eg verify NEW_DIRECTORY/bundles/0-full_receipt_relay --recompute
```

`run_r2.sh` uses `third_party/r2/reproduction` (absolute path in `run.log`).

Outputs land under `evidence/r2/` (`run.log`, `RESULTS.md`, `results.json`,
`summary.json`, `result.yaml`).

## Success criterion (claim card)

Across the published counterexamples, supported attributions that rest only on
receipt possession (no exclusivity/authenticity declaration) stay at **0**.
Headline paper checks this run targets:

- old-rule full-token relay: **1** wrong supported attribution / 12
- safer default on relay: **0** supported
- clean evidence with exclusivity undeclared: **12** correct attributions withheld
- **36** / 36 condition-by-seed contract checks
