#!/usr/bin/env bash
# Fetch the Junejo report PDF, pin EvidenceGraph (sprint stress pack on main),
# and re-run the published 12×3 paired evidence conditions — or derive
# Run/Finding from retained results.json. Never exits 0 as an empty no-op success.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIN_REV="a5ea5c9947039009ca795275d834be7b61069080"
PIN_SHORT="a5ea5c9"
BASELINE_REV="efbd4192767672e2ca3634c9ebe9d9a3c98fcddd"
GIT_URL="https://github.com/crashlabsai/evidencegraph"
REPORT_URL="https://pys8vc40ox3z7qxp.public.blob.vercel-storage.com/files/54d3ab064fa85a2f--413e-a31a-05a316b2660a-Junejo---Receipt-possession-is-not-event-attribution.pdf"
REPORT_SHA256="54d3ab064fa85a2f1ea566f4fa6f744571780ee21534fe6c24ac2cb455ded708"

TP="$ROOT/third_party/r2"
EV="$ROOT/evidence/r2"
DEST="$TP/evidencegraph"
PDF="$TP/report.pdf"
OUT="$TP/reproduction"
PARSE="$ROOT/experiments/r2/parse_summary.py"

export PATH="${HOME}/.local/bin:${PATH}"

mkdir -p "$TP" "$EV" "$EV/runs" "$EV/findings"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing dependency: $1" >&2; exit 1; }; }

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

write_failed() {
  local notes="${1:-run_r2.sh failed before completed observations}"
  local exit_code="${2:-1}"
  python3 "$PARSE" \
    --status failed \
    --notes "$notes" \
    --command "./experiments/r2/run_r2.sh" \
    --cwd "$ROOT" \
    --exit-status "$exit_code" \
    --stdout-path "evidence/r2/run.log" \
    --stderr-path "evidence/r2/uv-sync.log" \
    --partial-output "$notes" >/dev/null || true
}

on_err() {
  local code=$?
  write_failed "run_r2.sh aborted with exit $code" "$code"
  exit "$code"
}

# Prefer reusing retained results when asked (or when --derive-only).
if [[ "${1:-}" == "--derive-only" || "${SWARM_WITNESS_R2_REUSE_RESULTS:-}" == "1" ]]; then
  need python3
  echo "==> derive Run/Finding from retained results.json (no clone/stress)"
  if [[ ! -f "$EV/results.json" ]]; then
    python3 "$PARSE" \
      --status unrun \
      --notes "derive-only requested but evidence/r2/results.json missing" \
      --command "./experiments/r2/run_r2.sh --derive-only" \
      --cwd "$ROOT"
    exit 1
  fi
  python3 "$PARSE"
  exit $?
fi

trap on_err ERR

need git
need curl
need python3
need uv

echo "==> fetch report PDF"
if [[ ! -f "$PDF" ]]; then
  curl -fsSL -o "$PDF" "$REPORT_URL"
fi
got="$(sha256_file "$PDF")"
if [[ "$got" != "$REPORT_SHA256" ]]; then
  echo "report.pdf sha256 mismatch: got $got want $REPORT_SHA256" >&2
  exit 1
fi

echo "==> clone / checkout $PIN_SHORT (stress pack; paper baseline tip was ${BASELINE_REV:0:7})"
if [[ ! -d "$DEST/.git" ]]; then
  git clone --filter=blob:none "$GIT_URL" "$DEST"
fi
git -C "$DEST" fetch --filter=blob:none origin "$PIN_REV" >/dev/null 2>&1 || true
git -C "$DEST" checkout --force "$PIN_REV"

echo "==> uv sync --locked"
(
  cd "$DEST"
  # Avoid a parent VIRTUAL_ENV shadowing the project .venv.
  unset VIRTUAL_ENV
  uv sync --locked | tee "$EV/uv-sync.log"
)

echo "==> run published stress pack (seeds 0 1 2; checks counted from row records)"
rm -rf "$OUT"
(
  cd "$DEST"
  unset VIRTUAL_ENV
  {
    echo "==> uv run python scripts/incident_stress.py $OUT --seeds 0 1 2"
    uv run python scripts/incident_stress.py "$OUT" --seeds 0 1 2
    echo "stress_exit=$?"
    echo "==> uv run eg verify $OUT/bundles/0-full_receipt_relay --recompute"
    uv run eg verify "$OUT/bundles/0-full_receipt_relay" --recompute
    echo "verify_exit=$?"
  } | tee "$EV/run.log"
)

cp -f "$OUT/RESULTS.md" "$EV/RESULTS.md"
cp -f "$OUT/results.json" "$EV/results.json"

trap - ERR

echo "==> derive Run/Finding from row records + validate"
python3 "$PARSE"
echo "R2 complete. See $EV/runs/ and $EV/findings/ (Finding authoritative; summary.json is a mirror)."
