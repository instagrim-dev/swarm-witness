#!/usr/bin/env bash
# Export submission-ready PDF from markdown via pandoc HTML + Chrome headless.
# (weasyprint needs system pango; Chrome is available on this macOS host.)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
MD="${ROOT}/Swarm_Witness_Apart_Submission.md"
HTML_EMBED="${ROOT}/_build_submission.css_embedded.html"
PDF="${ROOT}/Swarm_Witness_Apart_Submission.pdf"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

pandoc "${MD}" -f markdown -t html5 --standalone -o "${ROOT}/_build_submission.html"
ROOT="${ROOT}" python3 - <<'PY'
from pathlib import Path
import os
root = Path(os.environ["ROOT"])
css = (root / "submission.css").read_text()
src = (root / "_build_submission.html").read_text()
if "</head>" in src:
    src = src.replace("</head>", f"<style>\n{css}\n</style>\n</head>")
else:
    src = (
        '<html><head><meta charset="utf-8"><style>'
        + css
        + "</style></head><body>"
        + src
        + "</body></html>"
    )
(root / "_build_submission.css_embedded.html").write_text(src)
print("embedded CSS")
PY

"${CHROME}" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="${PDF}" "file://${HTML_EMBED}"
echo "Wrote ${PDF}"
