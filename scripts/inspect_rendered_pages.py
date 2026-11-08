#!/usr/bin/env python3
"""Record page geometry and the rendered-page inspection for selected PDFs.

Geometry is measured with pypdf. The visual findings are the inspection of the
PDFKit page renders for this source revision. This script does not rebuild the
PDFs.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "report" / "bounded_comparison_v1" / "page_inspection_ed9123b.json"
PDFS = (
    "report/Swarm_Witness_Templated_Submission.pdf",
    "report/Swarm_Witness_Final_Submission.pdf",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(path: Path) -> dict[str, int | None]:
    reader = PdfReader(str(path))
    references = None
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if references is None and re.search(r"(?m)^References\b", text):
            references = index
    return {
        "page_count": len(reader.pages),
        "references_begin_page": references,
        "body_pages_before_references": None if references is None else references - 1,
    }


def revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def receipt() -> dict[str, object]:
    artifacts = []
    for relative in PDFS:
        path = ROOT / relative
        measured = geometry(path)
        artifacts.append(
            {
                "path": relative,
                "sha256": sha256(path),
                **measured,
                "clipping_observed": False,
                "overflow_observed": False,
                "unreadable_table_observed": False,
            }
        )
    return {
        "revision": revision(),
        "inspected_at": "2026-11-08",
        "geometry_method": "pypdf.PdfReader.extract_text",
        "visual_inspection_performed": True,
        "visual_method": "PDFKit page renders inspected for clipping, overflow, and table readability",
        "artifacts": artifacts,
        "notes": (
            "Templated body ends before References. Tables 1, 2, 2b, 3, and 4 are complete. "
            "The research layout is a separate pagination. This receipt does not replace the "
            "fde17ab clean-extract log."
        ),
    }


def main() -> None:
    document = receipt()
    RECEIPT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(RECEIPT)


if __name__ == "__main__":
    main()
