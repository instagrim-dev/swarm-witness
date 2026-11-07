#!/usr/bin/env bash
# Build official-template-filled report + slides PDF variants.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT="${ROOT}/report"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

echo "== Filling official Apart DOCX template =="
python3 "${ROOT}/scripts/build_templated_submission.py"

echo "== Templated HTML chrome (Old Standard TT) =="
python3 - <<'PY'
from pathlib import Path
import re
root = Path(__file__).resolve().parents[1] if False else Path.cwd()
# script runs with cwd=ROOT from bash
root = Path(".").resolve()
report = root / "report"
md = (report / "Swarm_Witness_Templated_Submission.md").read_text()
# Convert light markdown to HTML body
import html as H
lines = md.splitlines()
out = []
in_ul = False
def close_ul():
    global in_ul
    if in_ul:
        out.append("</ul>"); in_ul = False
for line in lines:
    if line.startswith("# "):
        close_ul(); out.append(f"<h1>{H.escape(line[2:])}</h1>")
    elif line.startswith("## "):
        close_ul(); out.append(f"<h2>{H.escape(line[3:])}</h2>")
    elif line.startswith("### "):
        close_ul(); out.append(f"<h3>{H.escape(line[4:])}</h3>")
    elif line.startswith("- "):
        if not in_ul:
            out.append("<ul>"); in_ul = True
        out.append(f"<li>{H.escape(line[2:])}</li>")
    elif not line.strip():
        close_ul(); out.append("")
    else:
        close_ul()
        t = H.escape(line)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        out.append(f"<p>{t}</p>")
close_ul()
body = "\n".join(out)
css = """
@font-face { font-family: "Old Standard TT"; src: url("fonts/OldStandardTT-regular.ttf"); font-weight: 400; }
@font-face { font-family: "Old Standard TT"; src: url("fonts/OldStandardTT-bold.ttf"); font-weight: 700; }
@font-face { font-family: "Old Standard TT"; src: url("fonts/OldStandardTT-italic.ttf"); font-style: italic; }
@page { size: letter; margin: 0.7in 0.85in; }
html { font-family: "Old Standard TT", "Times New Roman", Times, serif; font-size: 11pt; line-height: 1.28; color: #111; }
h1 { font-size: 18pt; text-align: center; margin: 0 0 0.45em; }
h2 { font-size: 13pt; margin: 0.9em 0 0.35em; border-bottom: 1px solid #ccc; padding-bottom: 0.15em; }
h3 { font-size: 11.5pt; margin: 0.7em 0 0.25em; }
p { margin: 0.35em 0; text-align: justify; }
ul { margin: 0.3em 0 0.3em 1.2em; }
.front { text-align: center; margin-bottom: 1em; }
.authors { margin: 0.6em 0 0.2em; }
.with-apart { margin: 0.4em 0 0.8em; font-style: italic; }
.abstract-label { font-weight: 700; text-align: left; margin-top: 0.8em; }
"""
# Rebuild front matter specially from first lines
title = "Swarm Witness: An Executable Evidence Protocol for Agent Authorization Claims"
html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>
<div class="front">
  <h1>{H.escape(title)}</h1>
  <div class="authors"><strong>Jonathan Maye-Hobbs</strong><br/>Independent</div>
  <div class="with-apart">With Apart Research</div>
</div>
{body}
</body></html>
"""
# Drop duplicate title h1 from body conversion
html = html.replace(f"<h1>{H.escape(title)}</h1>\n", "", 1)
(report / "_templated_build.html").write_text(html)
print("wrote report/_templated_build.html")
PY

"${CHROME}" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="${REPORT}/Swarm_Witness_Templated_Submission.pdf" \
  "file://${REPORT}/_templated_build.html"
echo "Wrote ${REPORT}/Swarm_Witness_Templated_Submission.pdf"

echo "== Slides PDF =="
python3 - <<'PY'
from pathlib import Path
report = Path("report").resolve()
src = (report / "slides" / "slides.html").read_text()
fonts = report / "fonts"
built = report / "slides" / "_slides_build.html"
for name in ("OldStandardTT-regular.ttf", "OldStandardTT-bold.ttf", "OldStandardTT-italic.ttf"):
    src = src.replace(f'url("../fonts/{name}")', f'url("file://{fonts / name}")')
    src = src.replace(f'url("fonts/{name}")', f'url("file://{fonts / name}")')
built.write_text(src)
print("wrote", built)
PY
"${CHROME}" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="${REPORT}/slides/Swarm_Witness_Slides.pdf" \
  "file://${REPORT}/slides/_slides_build.html"
# also publish at report/ root for form upload convenience
cp "${REPORT}/slides/Swarm_Witness_Slides.pdf" "${REPORT}/Swarm_Witness_Slides.pdf"
echo "Wrote ${REPORT}/Swarm_Witness_Slides.pdf"

# Optional: LibreOffice docx→pdf if present
if command -v soffice >/dev/null 2>&1; then
  soffice --headless --convert-to pdf --outdir "${REPORT}" \
    "${REPORT}/Swarm_Witness_Templated_Submission.docx" || true
fi

python3 - <<'PY'
from pypdf import PdfReader
from pathlib import Path
for p in [
    Path('report/Swarm_Witness_Templated_Submission.pdf'),
    Path('report/Swarm_Witness_Slides.pdf'),
]:
    r = PdfReader(str(p))
    print(f"{p.name}: {len(r.pages)} pages, {p.stat().st_size} bytes")
PY
