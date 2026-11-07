# Run qualification — 2026-11-07-ledger-v1-repair2

Selected authoritative run for `r3_ledger_claim_v1` after review P1/P2 repairs.

## Native provenance

- Pin: `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe` via `git archive` (not dirty HEAD)
- Bridge injected from `experiments/r3/ledger_claim_v1/{bmo_adapter_test,bmo_adapter_fixture}.go`
- Hashes and inventory: `source_manifest.json` → `bmo.source_inventory`, `bmo.bridge`
- Go exit: `0`; `native_bmo: true`; adapter `bmo_l1_first_edit`
- Bridge log archived at run-root `bmo_go_test.log` (portable relative path)

## Comparator scope

- Step-wise disposition + projection equality (grant_spent, counts, call_id)
- `classical_baseline_matches` requires both arms pass case properties
- Grant/epoch/task/owner-revision identity hashes are **not** cross-arm equality keys
  (see `observed_identities` on native state rows when present)

## Not established

Full event-trace observational equivalence; live execution safety; process restart;
concurrency; general BMO equivalence; legacy decision-model R3 (still unresolved).
