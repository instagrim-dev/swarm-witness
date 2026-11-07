#!/usr/bin/env bash
# Run preexisting BMO sessioncompaction retained-grant witness tests.
# Does not modify the BMO tree; only records stdout/stderr under evidence/r3/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BMO="${BMO_ROOT:-/Users/user1/Documents/dev/bmo}"
EV="$ROOT/evidence/r3"
LOG="$EV/bmo_go_test.log"

mkdir -p "$EV"

# Preferred file: ordinary_retry_retained_grant_owner_witness_test.go
# Regex covers owner-witness, shape, race/writer-boundary, and related
# RetainedGrant tests in internal/sessioncompaction.
cd "$BMO"
go test ./internal/sessioncompaction/ -run 'RetainedGrant|OrdinaryRetainedGrant' -count=1 -v 2>&1 | tee "$LOG"
