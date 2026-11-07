#!/usr/bin/env bash
# Clone/pin SoundGate, extract the paper recovery-barrier harness, rebuild, and
# run the published 153-history byte-prefix sweep. Optionally run the 0.1.4
# cargo regression test.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIN_REV="656840348dcf9660f8db7add9f3ca9f794a55926"
PIN_SHORT="6568403"
GIT_URL="https://github.com/sajjadanwar0/soundgate-paper"
REPORT_URL="https://pys8vc40ox3z7qxp.public.blob.vercel-storage.com/files/3a2f7a366143ba50-f54638af-31fd-40ff-9022-1a3d9350b49f-incident-sprint-report.pdf"
REPORT_SHA256="3a2f7a366143ba50ed6a598517f760f39cbc574f39438c444b3f10e58293a09f"
ARTIFACT_ZIP_SHA256="aec08353d0b4562f567cd476a0344d20af775579a187f6ee30293efd7d217be2"
BARRIER_FIX_REV="175fcdf6e2fc2a0a5f7eeead989b4b35be560cd6"

TP="$ROOT/third_party/r1"
EV="$ROOT/evidence/r1"
DEST="$TP/soundgate"
PDF="$TP/report.pdf"
ZIP="$TP/incident-sprint-artifact.zip"
ART="$TP/incident-sprint-artifact"
RB="$ART/recovery-barrier"

mkdir -p "$TP" "$EV"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing dependency: $1" >&2; exit 1; }; }
need git
need curl
need python3
need cargo
need rustc

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

echo "==> clone / checkout $PIN_SHORT"
if [[ ! -d "$DEST/.git" ]]; then
  git clone --filter=blob:none "$GIT_URL" "$DEST"
fi
git -C "$DEST" fetch --filter=blob:none origin "$PIN_REV" >/dev/null 2>&1 || true
git -C "$DEST" checkout --force "$PIN_REV"

echo "==> extract embedded artifact ZIP from PDF (FlateDecode EmbeddedFile)"
python3 - <<PY
from pathlib import Path
import re, zlib, hashlib, sys
pdf = Path(${PDF@Q}).read_bytes()
m = re.search(rb"91 0 obj\r?\n<<.*?/Length\s+(\d+)>>\r?\nstream\r?\n", pdf, re.S)
if not m:
    sys.exit("could not locate EmbeddedFile stream in report.pdf")
raw = pdf[m.end(): m.end() + int(m.group(1))]
out = zlib.decompress(raw)
digest = hashlib.sha256(out).hexdigest()
want = ${ARTIFACT_ZIP_SHA256@Q}
if digest != want:
    sys.exit(f"artifact zip sha256 mismatch: {digest} != {want}")
Path(${ZIP@Q}).write_bytes(out)
print("wrote", ${ZIP@Q}, "sha256", digest)
PY

rm -rf "$ART"
unzip -qo "$ZIP" -d "$TP"
# ZIP root is incident-sprint-artifact/
test -d "$RB"

echo "==> build original / strict / barrier / instrumented binaries"
rm -rf "$RB/local-build" "$RB/local-run"
(
  cd "$RB"
  python3 build.py --output local-build | tee "$EV/build.log"
)

echo "==> run published byte-prefix sweep (153 histories × 3 policies)"
(
  cd "$RB"
  python3 -B experiment.py --build local-build --output local-run | tee "$EV/experiment.log"
  python3 -B analyze.py --raw local-run/raw.json --output "$EV/local-run-analysis.json" \
    | tee "$EV/analyze-local.log"
  python3 -B check.py local-run/raw.json "$EV/local-run-analysis.json" \
    | tee "$EV/check-local.log"
  cp -f local-build/build.json "$EV/build.json"
  # Keep raw out of the repo by default (multi-MB); record path + hash via parse step.
  cp -f local-run/raw.json "$EV/raw.json"
)

echo "==> optional: soundgate 0.1.4 wal_recovery_barrier regression"
git -C "$DEST" checkout --force "$BARRIER_FIX_REV"
(
  cd "$DEST/soundgate"
  cargo test --test wal_recovery_barrier -- --nocapture \
    | tee "$EV/cargo-wal-recovery-barrier.log"
)
git -C "$DEST" checkout --force "$PIN_REV"

echo "==> parse summary.json + validate result.yaml"
python3 "$ROOT/experiments/r1/parse_summary.py"

echo "R1 complete. See $EV/summary.json and $EV/result.yaml"
