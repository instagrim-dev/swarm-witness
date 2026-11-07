# R5-v3 — wider-coverage research protocol (issue #11)

Versioned extension of the R5 claim-audit method. This is **not** the
historical `r5_v2` causal matrix (`claims/r5_v2.yaml`, `evidence/r5_v2/`,
14 scenarios / 28 arms after PR #33). **R5 v1 is retained unmodified**
(`experiments/swarm_r5/`, `evidence/r5/`).

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
  `concurrency_traces/`, regenerated from the integrated settlement ledger
  (PR #23 semantics, source commit `28b3642`). sha256 digests are in
  `PROVENANCE.md`. PR #15, #19, and #21 snapshots are not current. Reference
  vs mutant contention shares seed, event_count, and `schedule_id`; the run
  documents are not byte-identical. Sequential cases are **not** relabeled
  as races. No live concurrent swarm claim.

## One-click local entry

```bash
python3 experiments/swarm_r5_v3/run.py
python3 -m pytest -v tests/test_r5_v3_swarm_audit.py
python scripts/check_evidence.py --write-index
```

Expect: Finding `reproduced` for claim `r5_v3`; v1 and historical r5_v2
evidence untouched;
coverage dimension count ≥ 6; concurrency rows cite `multi-agent-sim-v1`.

## Explicit exclusions

- Live BMO mesh equivalence / production concurrency guarantees
- Overwriting R5 v1 denominators or Findings
- New verdict labels invented only to enlarge the matrix
- Taxonomy formalization (issue #12)
