#!/usr/bin/env bash
# Fetch the official Apart Swarm Alignment 2026 report template (Guidelines tab).
# Exact copy URL recorded in report/SOURCES.md.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
DOC_ID="1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE"
COPY_URL="https://docs.google.com/document/d/${DOC_ID}/copy?usp=sharing"
EXPORT_DOCX="https://docs.google.com/document/d/${DOC_ID}/export?format=docx"
EXPORT_PDF="https://docs.google.com/document/d/${DOC_ID}/export?format=pdf"

echo "Official template copy URL: ${COPY_URL}"
curl -fsSL -o "${ROOT}/official-template.docx" "${EXPORT_DOCX}"
curl -fsSL -o "${ROOT}/official-template.pdf" "${EXPORT_PDF}"
echo "Wrote ${ROOT}/official-template.docx and official-template.pdf"
