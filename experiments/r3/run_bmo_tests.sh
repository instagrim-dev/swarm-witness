#!/usr/bin/env bash
# Optional metadata: run preexisting BMO retained-grant witness tests.
# Pass/fail tallies are NOT isomorphic BMO decisions for cases.yaml.
# Use experiments/r3/run_bmo_cases.py + compare.py for the matched comparison.
# Does not modify the BMO tree; only records stdout/stderr under evidence/r3/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BMO="${BMO_ROOT:-/Users/user1/Documents/dev/bmo}"
EV="$ROOT/evidence/r3"
LOG="$EV/bmo_go_test.log"
PIN_REV="4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe"

mkdir -p "$EV"

# Record pin check (must match artifacts/pins.yaml r3.git_rev).
HEAD="$(git -C "$BMO" rev-parse HEAD)"
echo "bmo_git_rev_expected=$PIN_REV" | tee "$EV/bmo_pin.txt"
echo "bmo_git_rev_actual=$HEAD" | tee -a "$EV/bmo_pin.txt"
if [[ "$HEAD" != "$PIN_REV" ]]; then
  echo "WARNING: BMO HEAD $HEAD != pinned $PIN_REV" >&2
fi

# Preferred file: ordinary_retry_retained_grant_owner_witness_test.go
# Regex covers owner-witness, shape, race/writer-boundary, and related
# RetainedGrant tests in internal/sessioncompaction.
cd "$BMO"
go test ./internal/sessioncompaction/ -run 'RetainedGrant|OrdinaryRetainedGrant' -count=1 -v 2>&1 | tee "$LOG"
