#!/usr/bin/env bash
# Fetch the Junejo report PDF, pin EvidenceGraph (sprint stress pack on main),
# and re-run the published 12×3 paired evidence conditions.
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

export PATH="${HOME}/.local/bin:${PATH}"

mkdir -p "$TP" "$EV"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing dependency: $1" >&2; exit 1; }; }
need git
need curl
need python3
need uv

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

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

echo "==> run published stress pack (seeds 0 1 2 → 36 checks)"
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

echo "==> parse summary.json + validate result.yaml"
python3 "$ROOT/experiments/r2/parse_summary.py"

echo "R2 complete. See $EV/summary.json and $EV/result.yaml"
