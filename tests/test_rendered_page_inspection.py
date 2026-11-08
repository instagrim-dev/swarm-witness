"""The selected PDFs have a measured page receipt, not a skipped page count."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "report" / "bounded_comparison_v1" / "page_inspection_ed9123b.json"


def _inspector():
    spec = importlib.util.spec_from_file_location(
        "inspect_rendered_pages",
        ROOT / "scripts" / "inspect_rendered_pages.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_page_receipt_matches_rendered_pdfs():
    module = _inspector()
    document = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert document["visual_inspection_performed"] is True
    assert document["revision"]
    measured = {row["path"]: row for row in module.receipt()["artifacts"]}
    retained = {row["path"]: row for row in document["artifacts"]}
    assert set(measured) == {
        "report/Swarm_Witness_Templated_Submission.pdf",
        "report/Swarm_Witness_Final_Submission.pdf",
    }
    for path, row in measured.items():
        saved = retained[path]
        assert saved["sha256"] == row["sha256"]
        assert saved["page_count"] == row["page_count"]
        assert saved["references_begin_page"] == row["references_begin_page"]
        assert saved["body_pages_before_references"] == row["body_pages_before_references"]
        assert saved["clipping_observed"] is False
        assert saved["overflow_observed"] is False
        assert saved["unreadable_table_observed"] is False
        assert row["references_begin_page"] is not None
        assert row["body_pages_before_references"] == row["references_begin_page"] - 1
    templated = retained["report/Swarm_Witness_Templated_Submission.pdf"]
    assert templated["body_pages_before_references"] <= 8
