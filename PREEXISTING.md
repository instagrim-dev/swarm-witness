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

### BMO paths exercised by R3 (read-only `go test`)

Exact preexisting test / implementation paths consulted for the retained-grant
vs classical admit comparison (`experiments/r3/run_bmo_tests.sh`):

- `internal/sessioncompaction/ordinary_retry_retained_grant_owner_witness_test.go` (preferred)
- `internal/sessioncompaction/ordinary_retry_retained_grant_test.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_race_test.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_census.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_post_chain.go`
- Package under test: `./internal/sessioncompaction/` with
  `-run 'RetainedGrant|OrdinaryRetainedGrant'`

Related preexisting BMO retained-grant surfaces (not edited; may load as
dependencies of the package tests):

- `internal/agent/ordinary_retry_retained_grant_projection.go`
- `internal/agent/ordinary_retry_retained_grant_projection_test.go`
- `internal/app/ordinary_retry_retained_grant_early.go`
- `internal/app/ordinary_retry_retained_grant_projection.go`
- `internal/db/migrations/20261101033000_ordinary_retry_retained_grant_transfers.sql`
