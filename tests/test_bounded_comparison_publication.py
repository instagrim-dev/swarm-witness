"""Issue #42 publication: separate denominators, lead, and reassessment."""

from __future__ import annotations

import importlib.util
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LESSWRONG = "https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment"
SCORES = (
    "Impact/innovation: 3/5. Constraint: Swarm Witness ties the strong checker on the frozen public comparison (both 0 unsupported supports; naive PASS has 24). superiority_claim stays false. No held-out run shows a useful advantage over the strong checker under the same evidence budget. The 4–4.5/5 aspiration is not a result.",
    "Execution: 3/5. Constraint: tables were regenerated from retained data, and the advertised commands were rerun from a fresh review-bundle extract in this environment without private BMO access. No separate reviewer reproduced the study. Assistant agreement is not independent verification.",
    "Clarity: 4/5. Constraint: this is an author judgment that the manuscript states one question, the witness aew-v1-local-control-pass-broader-effect, the strong-checker tie, separate denominators, and the conditional formal boundary, and that it labels the earlier staged comparison as author-curated. It is not a judge score, and it does not convert the tie into a superiority result.",
)


def _render():
    spec = importlib.util.spec_from_file_location(
        "render_bounded_comparison",
        ROOT / "scripts" / "render_bounded_comparison.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render(ROOT)


def _docx_paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    paragraphs = []
    for paragraph in root.iter(f"{W_NS}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{W_NS}t"))
        paragraphs.append(text.strip())
    return paragraphs


def test_tables_keep_separate_denominators_and_the_tie():
    result = _render()
    text = Path(result["tables"]).read_text(encoding="utf-8")
    assert result["public_naive_unsupported_support"] == 24
    assert result["public_strong_unsupported_support"] == 0
    assert result["public_swarm_unsupported_support"] == 0
    assert result["witness_id"] == "aew-v1-local-control-pass-broader-effect"
    assert "## Table P. Public warrants" in text
    assert "## Table C. Controlled comparison" in text
    assert "## Table A. Application-owned twelve-history witness" in text
    assert "## Table S. Earlier author-curated staged comparison" in text
    assert "not independent curation" in text
    assert "url_held_worker_local_read" in text
    assert "refutes `P_system`" in text
    assert "native telemetry packet stays unresolved" in text
    assert "not applicable (0/0)" in text
    assert "0/1" in text
    ledger = (ROOT / "report" / "bounded_comparison_v1" / "ledger.csv").read_text(encoding="utf-8")
    assert "public_warrants" in ledger
    assert "controlled_comparison" in ledger
    assert "staged_author_curated" in ledger
    assert "superiority_claim" in text


def test_readme_labels_the_staged_comparison_and_states_the_tie():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    line = next(
        row for row in readme.splitlines() if "fewer unsupported conclusions" in row
    )
    assert "author-curated" in line
    assert "strong checker" in line
    assert "not independent curation" in line
    assert "superiority_claim is false" in line


def test_manuscript_leads_with_question_witness_and_finding():
    body = (ROOT / "report" / "body.md").read_text(encoding="utf-8")
    intro = body.split("## 2. Background", 1)[0]
    question = intro.find("what evidence is sufficient")
    witness = intro.find("aew-v1-local-control-pass-broader-effect")
    finding = intro.find("matches the strong checker")
    guarantee = intro.find("conditional on the adapter's observation and abstraction assumptions")
    assert 0 <= question < witness < finding < guarantee
    assert "Both record 0 unsupported supports" in intro
    assert "Naive PASS records 24" in intro
    assert "Separately coded verdict logic" in intro
    assert "not the twelve-history application experiment" in intro
    assert "does not claim that Swarm Witness detected or prevented" in intro
    for score in SCORES:
        assert score in body
        assert score in (ROOT / "report" / "Swarm_Witness_Final_Submission.md").read_text(encoding="utf-8")
        assert score in (ROOT / "report" / "bounded_comparison_v1" / "REASSESSMENT.md").read_text(encoding="utf-8")


def test_abstract_length_author_and_single_appendix():
    abstract = (ROOT / "report" / "ABSTRACT.md").read_text()
    assert 150 <= len(abstract.split()) <= 250
    final = (ROOT / "report" / "Swarm_Witness_Final_Submission.md").read_text(encoding="utf-8")
    assert final.count("\n# Appendix A") == 1
    assert "Jonathan Maye-Hobbs" in final
    assert "Independent" in final
    assert LESSWRONG in final
    assert "4–4.5/5 aspiration is not a result" in final


def test_templated_docx_matches_markdown_appendix_and_lesswrong_refs():
    markdown = (ROOT / "report" / "Swarm_Witness_Templated_Submission.md").read_text(encoding="utf-8")
    docx = ROOT / "report" / "Swarm_Witness_Templated_Submission.docx"
    assert docx.exists()
    paragraphs = _docx_paragraphs(docx)
    md_appendices = [
        line for line in markdown.splitlines() if line.startswith("#") and "Appendix A" in line
    ]
    docx_appendices = [paragraph for paragraph in paragraphs if paragraph.startswith("Appendix A")]
    assert len(md_appendices) == 1
    assert len(docx_appendices) == 1
    md_refs = _reference_block(markdown.splitlines())
    docx_refs = _reference_block(paragraphs)
    assert LESSWRONG in md_refs
    assert LESSWRONG in docx_refs
    assert md_refs.count(LESSWRONG) == docx_refs.count(LESSWRONG)


def _reference_block(lines: list[str]) -> str:
    start = next(i for i, line in enumerate(lines) if line.strip() in {"## References", "References"})
    end = next(
        i
        for i, line in enumerate(lines)
        if i > start and ("Appendix A" in line)
    )
    return "\n".join(lines[start:end])
