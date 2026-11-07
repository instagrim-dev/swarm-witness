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
# Synthetic protocols + R3-L1 comparator (label verification; no BMO tree).
mkdir -p "${STAGING}/experiments"
copy_tree "${ROOT}/experiments/r1/" "${STAGING}/experiments/r1/"
copy_tree "${ROOT}/experiments/r2/" "${STAGING}/experiments/r2/"
copy_tree "${ROOT}/experiments/r3/" "${STAGING}/experiments/r3/"
copy_tree "${ROOT}/experiments/evidence_sufficiency/" "${STAGING}/experiments/evidence_sufficiency/"
copy_tree "${ROOT}/experiments/swarm_r5/" "${STAGING}/experiments/swarm_r5/"
copy_tree "${ROOT}/experiments/swarm_r5_v2/" "${STAGING}/experiments/swarm_r5_v2/"
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
cp "${ROOT}/report/ABSTRACT.md" "${STAGING}/report/"
cp "${ROOT}/report/body.md" "${STAGING}/report/"
cp "${ROOT}/report/LIMITATIONS_DUAL_USE.md" "${STAGING}/report/"
cp "${ROOT}/report/SUBMISSION_FORM.md" "${STAGING}/report/"
cp "${ROOT}/README.md" "${STAGING}/"
cp "${ROOT}/PREEXISTING.md" "${STAGING}/"
cp "${ROOT}/CHECKLIST.md" "${STAGING}/"
cp "${ROOT}/evidence/ACCESS.md" "${STAGING}/ACCESS.md"

# Exclude accidental absolute-path dumps / caches.
find "${STAGING}" -name '.DS_Store' -delete 2>/dev/null || true

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
