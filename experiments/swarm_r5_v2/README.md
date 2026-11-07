# R5-v2 — wider-coverage research protocol (issue #11)

Versioned extension of the R5 claim-audit method. **R5 v1 is retained
unmodified** (`experiments/swarm_r5/`, `evidence/r5/`).

## What this is

- Orthogonal coverage matrix (`coverage_matrix.yaml`) with tested **and**
  untested seams across ≥6 dimensions. Every tested seam is bound to ≥1 case
  via `seams` tags (enforced by `coverage_report` / evaluator).
- Separable oracle vs gate policies; correct and faulty arms on shared inputs
  for each major family (including observation_delivery).
- Held-out / adversarial fixtures under `held_out/` (expectations authored in
  the fixtures, not by the classifier).
- Independently declared expectations in `case_expectations.yaml`.
- Concurrency-derived rows from **pinned** `multi-agent-sim-v1` runs in
  `concurrency_traces/` (issue #10 / PR #15) with sha256 digests in
  `PROVENANCE.md`. Reference vs mutant contention is scored as
  same-seed / same-event_count (not byte-identical `schedule_id`). Sequential
  cases are **not** relabeled as races. No live concurrent swarm claim.

## One-click local entry

```bash
python3 experiments/swarm_r5_v2/run.py
python3 -m pytest -v tests/test_r5_v2_swarm_audit.py
python scripts/check_evidence.py --write-index
```

Expect: Finding `reproduced` for claim `r5_v2`; v1 evidence untouched;
coverage dimension count ≥ 6; concurrency rows cite `multi-agent-sim-v1`.

## Explicit exclusions

- Live BMO mesh equivalence / production concurrency guarantees
- Overwriting R5 v1 denominators or Findings
- New verdict labels invented only to enlarge the matrix
- Taxonomy formalization (issue #12)
