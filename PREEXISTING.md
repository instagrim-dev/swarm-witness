# Preexisting material

This submission builds on material that predates the Apart weekend sprint work
(2026-11-06 … 2026-11-08; scaffold landed at the start of that window).

## Oct 25 repository scaffold

- `protocol/`
- `scenarios/`
- `agents/`
- `monitors/`
- `analysis/`
- `paper/`
- `scripts/check.sh`
- `LICENSE` (MIT)
- `README.md` (replaced for Task 1)
- `.github/workflows/ci.yml`
- `.gitignore` (replaced for Task 1)

## External tree

- `/Users/user1/Documents/dev/bmo` (pinned `artifacts/pins.yaml` `r3.bmo_root`; preexisting — not modified this weekend)

### BMO paths consulted by R3 (read-only; pin `r3.git_rev`)

R3 is a **matched decision-model** comparison under `experiments/r3/cases.yaml`.
BMO decisions require isomorphic observations (matching test assertions or the
instrumented harness). Package pass counts from `run_bmo_tests.sh` are
**metadata only** and do not fill per-case decisions.

Pinned revision: `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe` (`artifacts/pins.yaml`).

Preexisting surfaces consulted when assessing isomorphism (not modified):

- `internal/sessioncompaction/ordinary_retry_retained_grant_owner_witness_test.go` (preferred)
- `internal/sessioncompaction/ordinary_retry_retained_grant_test.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_race_test.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_census.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_post_chain.go`
- Package under optional metadata `go test`: `./internal/sessioncompaction/` with
  `-run 'RetainedGrant|OrdinaryRetainedGrant'`

Related preexisting BMO retained-grant surfaces (not edited):

- `internal/agent/ordinary_retry_retained_grant_projection.go`
- `internal/agent/ordinary_retry_retained_grant_projection_test.go`
- `internal/app/ordinary_retry_retained_grant_early.go`
- `internal/app/ordinary_retry_retained_grant_projection.go`
- `internal/db/migrations/20261101033000_ordinary_retry_retained_grant_transfers.sql`

Honesty note: these BMO APIs are not isomorphic to ClassicalGate
`(state, request, grant_version)` inputs; R3 therefore records BMO cases as
`missing_isomorphic_observation` when no matching assertion/harness probe
exists. The comparison Finding label is then `unresolved` (incomplete
comparative audit)—not `classical_baseline_matches` or assumption-dependent
affinity.

## Derived protocol r3-ledger-claim-v1 (this delivery)

Separate from the legacy decision-model protocol. Classical arm is new
`ClassicalLedgerGate` (SQLite). BMO arm is a tagged test-only bridge stored
under `experiments/r3/ledger_claim_v1/` and copied into a disposable pin tree;
production BMO authorization code is not modified. L1 method under test:
`ClaimOrdinaryRetainedGrantFirstEditTx`. Offline SQLite L1 stand-in may emit
inspectable traces when `BMO_ROOT` is absent but cannot upgrade findings past
`unresolved` for the native BMO pin.
