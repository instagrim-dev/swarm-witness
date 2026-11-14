#!/usr/bin/env python3
"""Render the epistemics sprint report and its official-template PDF.

Writes only under report/epistemics_trust_v1/. The closed Swarm Alignment
exports are not rebuilt.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "epistemics_trust_v1"
DOCX = OUT / "Epistemics_Trust_Templated.docx"
PDF = OUT / "Epistemics_Trust_Templated.pdf"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fontconfig(directory: Path) -> str:
    config = ET.Element("fontconfig")
    ET.SubElement(config, "include", ignore_missing="yes").text = "/etc/fonts/fonts.conf"
    ET.SubElement(config, "dir").text = str(ROOT / "report" / "fonts")
    path = directory / "fonts.conf"
    ET.ElementTree(config).write(path, encoding="utf-8", xml_declaration=True)
    return str(path)


def main() -> None:
    run = _load("epistemics_trust_v1", ROOT / "experiments" / "epistemics_trust_v1" / "run.py")
    manuscript = _load(
        "epistemics_manuscript", ROOT / "experiments" / "epistemics_trust_v1" / "manuscript.py"
    )
    builder = _load(
        "build_templated_submission", ROOT / "scripts" / "build_templated_submission.py"
    )
    text = manuscript.render_manuscript(run.measure(ROOT))
    abstract_words = manuscript.word_count(manuscript.abstract_text(text))
    if not 150 <= abstract_words <= 250:
        raise SystemExit(f"abstract is {abstract_words} words; the sprint requires 150–250")
    OUT.mkdir(parents=True, exist_ok=True)
    source = OUT / "manuscript.md"
    source.write_text(text, encoding="utf-8")
    builder.export_templated_docx(source, DOCX)
    office = os.environ.get("SOFFICE", "soffice")
    with TemporaryDirectory(prefix="swarm-witness-epistemics-pdf-") as directory:
        profile = Path(directory) / "libreoffice"
        env = os.environ.copy()
        env["FONTCONFIG_FILE"] = _fontconfig(Path(directory))
        subprocess.run(
            [
                office,
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--convert-to",
                "pdf:writer_pdf_Export",
                "--outdir",
                str(OUT),
                str(DOCX),
            ],
            check=True,
            env=env,
        )
    if not PDF.is_file() or PDF.stat().st_size == 0:
        raise SystemExit("PDF conversion did not produce the epistemics report")
    geometry = _load(
        "inspect_rendered_pages", ROOT / "scripts" / "inspect_rendered_pages.py"
    ).geometry(PDF)
    body = geometry["body_pages_before_references"]
    if body is None or body > 8 or body < 1:
        raise SystemExit(f"body pages before references: {body}")
    print(
        f"{PDF.relative_to(ROOT)} pages={geometry['page_count']} "
        f"body={body} abstract_words={abstract_words}"
    )


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    main()
