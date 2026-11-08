#!/usr/bin/env bash
# Build both paper layouts from the canonical manuscript through DOCX to PDF.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${REPO_ROOT}/report"
PAPER_PYTHON="${PYTHON:-${CODEX_PRIMARY_RUNTIME_PYTHON:-python3}}"
PAPER_OFFICE="${SOFFICE:-soffice}"
PAPER_BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/swarm-witness-paper.XXXXXXXX")"
trap 'rm -rf "${PAPER_BUILD_DIR}"' EXIT

command -v "${PANDOC:-pandoc}" >/dev/null || { printf 'Pandoc is required.\n' >&2; exit 1; }
command -v "${PAPER_OFFICE}" >/dev/null || { printf 'LibreOffice (soffice) is required.\n' >&2; exit 1; }

# Fontconfig uses the bundled template font without changing the user's fonts.
if command -v fc-match >/dev/null 2>&1; then
  "${PAPER_PYTHON}" - "${REPORT_DIR}/fonts" "${PAPER_BUILD_DIR}/fonts.conf" <<'PY'
import sys
import xml.etree.ElementTree as ET
config = ET.Element("fontconfig")
ET.SubElement(config, "include", ignore_missing="yes").text = "/etc/fonts/fonts.conf"
ET.SubElement(config, "dir").text = sys.argv[1]
ET.ElementTree(config).write(sys.argv[2], encoding="utf-8", xml_declaration=True)
PY
  export FONTCONFIG_FILE="${PAPER_BUILD_DIR}/fonts.conf"
fi

"${PAPER_PYTHON}" "${REPO_ROOT}/scripts/build_templated_submission.py"
PAPER_PROFILE_URI="$("${PAPER_PYTHON}" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).as_uri())' "${PAPER_BUILD_DIR}/libreoffice")"
"${PAPER_OFFICE}" "-env:UserInstallation=${PAPER_PROFILE_URI}" --headless \
  --convert-to pdf:writer_pdf_Export --outdir "${PAPER_BUILD_DIR}" \
  "${REPORT_DIR}/Swarm_Witness_Final_Submission.docx" \
  "${REPORT_DIR}/Swarm_Witness_Templated_Submission.docx"

for variant in Final Templated; do
  paper_pdf="Swarm_Witness_${variant}_Submission.pdf"
  if [[ ! -s "${PAPER_BUILD_DIR}/${paper_pdf}" ]]; then
    printf 'PDF conversion did not produce %s.\n' "${paper_pdf}" >&2
    exit 1
  fi
done
for variant in Final Templated; do
  paper_pdf="Swarm_Witness_${variant}_Submission.pdf"
  cp "${PAPER_BUILD_DIR}/${paper_pdf}" "${REPORT_DIR}/${paper_pdf}"
  printf '%s\n' "report/${paper_pdf}"
done
