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
# Full clone/sync/stress (writes results.json, then Run + Finding)
./experiments/r2/run_r2.sh

# Or derive Run/Finding from retained results without re-stress
./experiments/r2/run_r2.sh --derive-only
# equivalent: SWARM_WITNESS_R2_REUSE_RESULTS=1 ./experiments/r2/run_r2.sh
```

Requirements for a full run: Python 3.13+ via `uv`, `git`, `curl`, network for
the first `uv sync --locked`.

Upstream paper commands (from the pinned `evidencegraph` tree; output dir is
arbitrary):

```bash
cd third_party/r2/evidencegraph
uv sync --locked
uv run python scripts/incident_stress.py NEW_DIRECTORY --seeds 0 1 2
uv run eg verify NEW_DIRECTORY/bundles/0-full_receipt_relay --recompute
```

`run_r2.sh` uses `third_party/r2/reproduction` (absolute path in `run.log`).

### Honesty contract

- Success requires a `completed` Run whose `condition_by_seed_checks` and
  scenario tallies are **counted from** `results.json` row records.
- If results are missing or the runner aborts, the script writes
  `execution_status=unrun|failed` plus Finding `label=unresolved` and exits
  nonzero — never a successful empty no-op.
- Authoritative label: `evidence/r2/findings/*.json`. `summary.json` /
  `result.yaml` are convenience mirrors only.
- `baselines/r2_*.md` is authored mechanism interpretation only — **not** an
  empirical `classical_baseline_matches` finding.

## Success criterion (claim card)

Across the published counterexamples, supported attributions that rest only on
receipt possession (no exclusivity/authenticity declaration) stay at **0**.
Headline paper checks this run targets (values counted from retained rows):

- old-rule full-token relay: **1** wrong supported attribution / 12
- safer default on relay: **0** supported
- clean evidence with exclusivity undeclared: **12** correct attributions withheld
- condition-by-seed contract checks equal to the retained row count (typically 36)
