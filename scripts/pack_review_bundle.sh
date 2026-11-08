#!/usr/bin/env bash
# Pack judge-facing evidence + report without local work trees or secrets.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT}/dist"
STAGING="${OUT_DIR}/swarm-witness-review-bundle"
ZIP="${OUT_DIR}/swarm-witness-review-bundle.zip"

rm -rf "${STAGING}" "${ZIP}"
mkdir -p "${STAGING}"

copy_tree() {
  local src="$1"
  local dst="$2"
  mkdir -p "$(dirname "${dst}")"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude 'bmo_work/' --exclude 'classical_work/' \
      --exclude '**/tree/' --exclude '.bmo-session-fences/' \
      "${src}" "${dst}"
  else
    cp -R "${src}" "${dst}"
  fi
}

copy_tree "${ROOT}/claims/" "${STAGING}/claims/"
# Copy artifacts but never nest the previous review ZIP inside a new one.
mkdir -p "${STAGING}/artifacts"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude 'swarm-witness-review-bundle.zip' \
    "${ROOT}/artifacts/" "${STAGING}/artifacts/"
else
  cp -R "${ROOT}/artifacts/." "${STAGING}/artifacts/"
  rm -f "${STAGING}/artifacts/swarm-witness-review-bundle.zip"
fi
copy_tree "${ROOT}/baselines/" "${STAGING}/baselines/"
copy_tree "${ROOT}/evidence/" "${STAGING}/evidence/"
copy_tree "${ROOT}/src/" "${STAGING}/src/"
copy_tree "${ROOT}/tests/" "${STAGING}/tests/"
# Whole experiment tree. A partial list omitted incident audit, provenance,
# telemetry, coordination, detection-latency, and property inputs that
# pytest and the ACCESS.md runners import. Work-tree excludes still apply.
copy_tree "${ROOT}/experiments/" "${STAGING}/experiments/"
copy_tree "${ROOT}/theory/" "${STAGING}/theory/"
copy_tree "${ROOT}/docs/" "${STAGING}/docs/"
mkdir -p "${STAGING}/scripts"
cp "${ROOT}/scripts/check_evidence.py" "${STAGING}/scripts/"
cp "${ROOT}/scripts/validate_claims.py" "${STAGING}/scripts/"
cp "${ROOT}/scripts/annotate_conclusion_classes.py" "${STAGING}/scripts/"
cp "${ROOT}/scripts/pack_review_bundle.sh" "${STAGING}/scripts/"
cp "${ROOT}/pyproject.toml" "${STAGING}/"
# Drop bulky disposable trees if any slipped through.
find "${STAGING}/evidence" -type d \( -name bmo_work -o -name classical_work -o -name tree \) -prune -exec rm -rf {} + 2>/dev/null || true
find "${STAGING}" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

mkdir -p "${STAGING}/report"
cp "${ROOT}/report/Swarm_Witness_Apart_Submission.pdf" "${STAGING}/report/"
cp "${ROOT}/report/Swarm_Witness_Final_Submission.pdf" "${STAGING}/report/"
cp "${ROOT}/report/Swarm_Witness_Final_Submission.docx" "${STAGING}/report/"
cp "${ROOT}/report/Swarm_Witness_Final_Submission.md" "${STAGING}/report/"
cp "${ROOT}/report/Swarm_Witness_Templated_Submission.pdf" "${STAGING}/report/"
cp "${ROOT}/report/Swarm_Witness_Templated_Submission.docx" "${STAGING}/report/"
cp "${ROOT}/report/Swarm_Witness_Templated_Submission.md" "${STAGING}/report/"
cp "${ROOT}/report/Swarm_Witness_Slides.pdf" "${STAGING}/report/"
mkdir -p "${STAGING}/report/slides" "${STAGING}/report/fonts"
cp "${ROOT}/report/slides/slides.html" "${STAGING}/report/slides/"
cp "${ROOT}/report/slides/Swarm_Witness_Slides.pdf" "${STAGING}/report/slides/"
cp "${ROOT}/report/fonts/"*.ttf "${STAGING}/report/fonts/" 2>/dev/null || true
cp "${ROOT}/report/fig01_evidence_to_warrant.png" "${STAGING}/report/"
cp "${ROOT}/report/ABSTRACT.md" "${STAGING}/report/"
cp "${ROOT}/report/body.md" "${STAGING}/report/"
cp "${ROOT}/report/LIMITATIONS_DUAL_USE.md" "${STAGING}/report/"
cp "${ROOT}/report/SUBMISSION_FORM.md" "${STAGING}/report/"
cp "${ROOT}/report/SOURCES.md" "${STAGING}/report/"
cp "${ROOT}/scripts/build_submission_variants.sh" "${STAGING}/scripts/"
cp "${ROOT}/scripts/build_templated_submission.py" "${STAGING}/scripts/"
cp "${ROOT}/README.md" "${STAGING}/"
cp "${ROOT}/PREEXISTING.md" "${STAGING}/"
cp "${ROOT}/CHECKLIST.md" "${STAGING}/"
cp "${ROOT}/evidence/ACCESS.md" "${STAGING}/ACCESS.md"

# Exclude accidental absolute-path dumps / caches.
find "${STAGING}" -name '.DS_Store' -delete 2>/dev/null || true

# Fail if a path advertised in evidence/ACCESS.md is absent from the bundle.
ACCESS_MD="${ROOT}/evidence/ACCESS.md" STAGING="${STAGING}" ROOT="${ROOT}" python3 - <<'PY'
import os
import re
import sys
from pathlib import Path

access_path = Path(os.environ["ACCESS_MD"])
staging = Path(os.environ["STAGING"])
root = Path(os.environ["ROOT"])
text = access_path.read_text(encoding="utf-8")
end = re.search(r"^## Pack a portable review bundle\s*$", text, re.M)
if end is None:
    sys.exit("ACCESS.md is missing the portable review-bundle section")
section = text[: end.start()]

paths: list[str] = []
last = None
for token in re.findall(r"`([^`]+)`", section):
    token = token.strip()
    if not token or token.startswith("<") or "://" in token or " " in token:
        continue
    if re.fullmatch(r"\.[A-Za-z0-9]+", token) and last and "." in Path(last).name:
        swapped = str(Path(last).with_suffix(token))
        paths.append(swapped)
        last = swapped
        continue
    if "/" in token:
        if token.startswith("dist/") or token.endswith(".zip"):
            continue
        rel = token.strip("/")
        paths.append(rel)
        last = rel
        continue
    if (root / token).exists():
        paths.append(token)
        last = token

for fence in re.findall(r"```(?:bash|sh)?\n(.*?)```", section, re.S):
    logical: list[str] = []
    buf = ""
    for line in fence.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("\\"):
            buf += stripped[:-1].strip() + " "
            continue
        buf += stripped
        logical.append(buf)
        buf = ""
    if buf.strip():
        logical.append(buf.strip())
    for line in logical:
        for match in re.finditer(r"(?:^|\s)[A-Za-z_][A-Za-z0-9_]*=([^\s]+)", line):
            val = match.group(1).strip("'\"")
            if val.startswith("/") or val.startswith(".venv"):
                continue
            if val == "src" or "/" in val:
                paths.append(val.strip("/"))
        for tok in line.split():
            tok = tok.strip("'\"")
            if (
                not tok
                or tok.startswith("-")
                or tok.startswith("/")
                or tok.startswith(".venv")
                or tok.startswith("http")
                or "/" not in tok
                or tok.endswith(".zip")
            ):
                continue
            paths.append(tok.strip("/"))

ordered: list[str] = []
seen: set[str] = set()
for path in paths:
    if path not in seen:
        seen.add(path)
        ordered.append(path)
if not ordered:
    sys.exit("no advertised paths parsed from evidence/ACCESS.md")

missing = [path for path in ordered if not (staging / path).exists()]
if missing:
    for path in missing:
        print(f"advertised path missing from bundle: {path}", file=sys.stderr)
    sys.exit(1)
print(f"advertised paths present in bundle: {len(ordered)}")
PY

(
  cd "${OUT_DIR}"
  rm -f swarm-witness-review-bundle.zip
  zip -qr swarm-witness-review-bundle.zip swarm-witness-review-bundle
)

# Also publish a repo-tree copy for judges with read access (dist/ is gitignored).
mkdir -p "${ROOT}/artifacts"
cp -f "${ZIP}" "${ROOT}/artifacts/swarm-witness-review-bundle.zip"

echo "Wrote ${ZIP}"
echo "Also wrote ${ROOT}/artifacts/swarm-witness-review-bundle.zip"
unzip -l "${ZIP}" | tail -5
du -h "${ZIP}"
