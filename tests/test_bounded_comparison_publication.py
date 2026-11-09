"""Publication consistency, evidence denominators, and native warrants."""

from __future__ import annotations

import importlib.util
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LESSWRONG = "https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment"


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


def test_markdown_extracts_and_mirror_match_the_canonical_manuscript():
    report = ROOT / "report"
    source = (report / "Swarm_Witness_Final_Submission.md").read_text(encoding="utf-8")
    sections = list(re.finditer(r"^## ([^\n]+)$", source, re.M))
    abstract_index = next(i for i, section in enumerate(sections) if section[1] == "Abstract")
    abstract = sections[abstract_index]
    body_start = sections[abstract_index + 1].start()
    references = next(section for section in sections if section[1] == "References")
    appendix = next(section for section in sections if section[1].startswith("Appendix A"))

    expected = {
        "ABSTRACT.md": source[abstract.end():body_start],
        "body.md": source[body_start:references.start()],
        "LIMITATIONS_DUAL_USE.md": source[appendix.start():],
    }
    for filename, content in expected.items():
        assert (report / filename).read_text(encoding="utf-8").strip() == content.strip(), filename

    mirror = (report / "Swarm_Witness_Templated_Submission.md").read_text(encoding="utf-8")
    assert mirror.splitlines()[0] == source.splitlines()[0]
    assert mirror.split("## Abstract", 1)[1].strip() == source.split("## Abstract", 1)[1].strip()


def test_current_manuscripts_exclude_assessment_grades_and_metaprompting():
    report = ROOT / "report"
    texts = {
        filename: (report / filename).read_text(encoding="utf-8")
        for filename in (
            "Swarm_Witness_Final_Submission.md",
            "Swarm_Witness_Templated_Submission.md",
            "ABSTRACT.md",
            "body.md",
            "LIMITATIONS_DUAL_USE.md",
        )
    }
    for variant in ("Final", "Templated"):
        filename = f"Swarm_Witness_{variant}_Submission.docx"
        texts[filename] = "\n".join(_docx_paragraphs(report / filename))
    forbidden = re.compile(
        r"\b[0-5](?:\.\d+)?\s*/\s*5\b|\bmetaprompt(?:ing)?\b|\bself[- ]assessment\b",
        re.I,
    )
    for filename, text in texts.items():
        assert forbidden.search(text) is None, filename


def test_abstract_length_author_and_required_sections():
    abstract = (ROOT / "report" / "ABSTRACT.md").read_text()
    assert 150 <= len(abstract.split()) <= 250
    final = (ROOT / "report" / "Swarm_Witness_Final_Submission.md").read_text(encoding="utf-8")
    headings = re.findall(r"^#{1,6}\s+(.+)$", final, re.M)
    assert sum(heading.startswith("Appendix A") for heading in headings) == 1
    assert headings.count("References") == 1
    assert headings.count("LLM Usage Statement") == 1
    assert "Jonathan Maye-Hobbs" in final
    assert "Independent" in final
    assert LESSWRONG in final


def test_docx_exports_preserve_sections_references_and_table_cells():
    report = ROOT / "report"
    source = (report / "Swarm_Witness_Final_Submission.md").read_text(encoding="utf-8")
    source_refs = _reference_block(source.splitlines())
    source_tables = _markdown_tables(source)
    assert source_tables
    for variant in ("Final", "Templated"):
        docx = report / f"Swarm_Witness_{variant}_Submission.docx"
        assert docx.exists()
        paragraphs = _docx_paragraphs(docx)
        assert sum(paragraph.startswith("Appendix A") for paragraph in paragraphs) == 1
        assert paragraphs.count("References") == 1
        assert paragraphs.count("LLM Usage Statement") == 1
        docx_refs = _reference_block(paragraphs)
        assert LESSWRONG in source_refs
        assert LESSWRONG in docx_refs
        assert source_refs.count(LESSWRONG) == docx_refs.count(LESSWRONG)
        assert _manuscript_docx_tables(docx, source_tables) == source_tables
        if variant == "Templated":
            paragraphs = "\n".join(paragraphs)
            assert "PROJECT TITLE" not in paragraphs
            assert "How to use this template" not in paragraphs
            assert "Author name 2" not in paragraphs
            assert metadata_present(docx)


def test_positive_coverage_count_without_commit_detail_stays_unresolved():
    import json
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from swarm_witness.native_comparison import competent_verdict

    history_id = "aew-v1-h-local-pass-broader-effect"
    directory = (
        ROOT
        / "evidence"
        / "effect_witness_v1"
        / "packets"
        / history_id
        / "discriminating_readback"
    )
    records = []
    for name in ("actor_records.jsonl", "service_records.jsonl"):
        for line in (directory / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    assert competent_verdict(history_id, records)["epistemic_status"] == "refuted"
    without_commit = [row for row in records if row.get("surface") != "committed_effect"]
    assert competent_verdict(history_id, without_commit)["epistemic_status"] == "unresolved"


def test_evidence_free_actor_upgrade_is_unsupported_support_not_correct_decisive():
    import copy
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from swarm_witness.native_comparison import score_native_method

    result = _render()
    rows = result["native_rows"]
    assert result["native_swarm_unsupported_support"] == 11
    assert result["native_swarm_correct_decisive"] == 24
    assert result["native_strong_unsupported_support"] == 0
    assert result["native_strong_correct_decisive"] == 24
    text = Path(result["tables"]).read_text(encoding="utf-8")
    assert "`superiority_claim` remains false." in text
    assert "`external_empirical_transfer` is not tested, and the retained `transfer_claim` flag records that scope limit." in text
    assert "not a set of independently correct judgments" in text
    for row in rows:
        if row["predicted"] == "supported":
            assert row["conclusion_class"] == "supported"
        elif row["predicted"] == "refuted":
            assert row["conclusion_class"] == "refuted"
        else:
            assert row["conclusion_class"] == "missing_evidence"
        if row["stage"] == "actor_only":
            assert row["adjudicated"] == "unresolved"
            assert row["predicted"] != "supported"
    upgraded = copy.deepcopy(rows)
    target = next(
        row
        for row in upgraded
        if row["method"] == "swarm_witness"
        and row["stage"] == "actor_only"
        and row["history"] == "aew-v1-h-authority-current"
    )
    assert target["predicted"] == "unresolved"
    assert target["proposition_holds"] is True
    target["predicted"] = "supported"
    after = score_native_method(upgraded, "swarm_witness")
    assert after["unsupported_support"] == 12
    assert after["correct_decisive"] == 24


def test_manuscript_numeric_cells_equal_retained_rows():
    spec = importlib.util.spec_from_file_location(
        "render_release_tables",
        ROOT / "scripts" / "render_release_tables.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generated = module.canonical_tables(ROOT)
    text = (ROOT / "report" / "Swarm_Witness_Final_Submission.md").read_text(encoding="utf-8")
    published: dict[str, list[list[str]]] = {}
    caption = None
    rows: list[list[str]] = []
    for line in text.splitlines() + [""]:
        match = re.match(r"\*\*(Table (?:2b|2|3|4))\.", line)
        if match:
            caption = match.group(1)
            rows = []
            continue
        if caption and line.startswith("|"):
            cells = [_cell_text(cell) for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", cell.strip()) for cell in line.strip().strip("|").split("|")):
                rows.append(cells)
            continue
        if caption and rows:
            published[caption] = rows[1:]
            caption = None
            rows = []
    assert set(published) == set(generated)
    for name, expected in generated.items():
        assert published[name] == expected


def _reference_block(lines: list[str]) -> str:
    start = next(i for i, line in enumerate(lines) if re.sub(r"^#+\s*", "", line.strip()) == "References")
    end = next(
        i
        for i, line in enumerate(lines)
        if i > start and ("Appendix A" in line)
    )
    return "\n".join(lines[start:end])


def _cell_text(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("`", "").replace("**", "").replace("*", "")
    return " ".join(text.split())


def _markdown_tables(text: str) -> list[list[list[str]]]:
    tables = []
    rows = []
    for line in text.splitlines() + [""]:
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                rows.append([_cell_text(cell) for cell in cells])
        elif rows:
            tables.append(rows)
            rows = []
    return tables


def metadata_present(path: Path) -> bool:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
        footnote_root = ET.fromstring(archive.read("word/footnotes.xml"))
        footnotes = "".join(node.text or "" for node in footnote_root.iter(f"{W_NS}t"))
    title_tables = []
    for table in root.findall(f"{W_NS}body/{W_NS}tbl"):
        text = _cell_text("".join(node.text or "" for node in table.iter(f"{W_NS}t")))
        title_tables.append(text)
    if not title_tables:
        return False
    card = title_tables[0]
    return (
        "Swarm Witness Evidence for Agent Authorization" in card
        and "Jonathan Maye-Hobbs" in card
        and "Independent" in card
        and "Apart Research" in card
        and "How to use this template" not in card
        and "Research conducted at the Swarm Alignment Hackathon, November 2026" in footnotes
    )


def _manuscript_docx_tables(path: Path, source_tables: list[list[list[str]]]) -> list[list[list[str]]]:
    remaining = list(source_tables)
    found = []
    for table in _docx_tables(path):
        if remaining and table == remaining[0]:
            found.append(table)
            remaining.pop(0)
    return found


def _docx_tables(path: Path) -> list[list[list[str]]]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return [
        [
            [
                _cell_text("".join(node.text or "" for node in cell.iter(f"{W_NS}t")))
                for cell in row.findall(f"{W_NS}tc")
            ]
            for row in table.findall(f"{W_NS}tr")
        ]
        for table in root.iter(f"{W_NS}tbl")
    ]
