#!/usr/bin/env python3
"""Fill the official Apart DOCX template with Swarm Witness content (guidance removed)."""
from __future__ import annotations

import re
import shutil
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
TEMPLATE = REPORT / "official-template.docx"
OUT_DOCX = REPORT / "Swarm_Witness_Templated_Submission.docx"
OUT_MD = REPORT / "Swarm_Witness_Templated_Submission.md"

TITLE = "Swarm Witness: An Executable Evidence Protocol for Agent Authorization Claims"
AUTHOR = "Jonathan Maye-Hobbs"
AFFILIATION = "Independent"


def _set_run_text(run, text: str) -> None:
    run.text = text


def _replace_first_text(element, old: str, new: str) -> bool:
    for node in element.iter(qn("w:t")):
        if node.text and old in node.text:
            node.text = node.text.replace(old, new, 1)
            return True
    return False


def _clear_paragraph(paragraph: Paragraph) -> None:
    p = paragraph._p
    for child in list(p):
        if child.tag.endswith("}r") or child.tag.endswith("}hyperlink"):
            p.remove(child)


def _set_paragraph_text(paragraph: Paragraph, text: str) -> None:
    _clear_paragraph(paragraph)
    run = paragraph.add_run(text)


def _delete_paragraph(paragraph: Paragraph) -> None:
    p = paragraph._p
    parent = p.getparent()
    if parent is not None:
        parent.remove(p)


def _delete_table(table) -> None:
    tbl = table._tbl
    parent = tbl.getparent()
    if parent is not None:
        parent.remove(tbl)


def _load_parts() -> dict[str, str]:
    abstract = (REPORT / "ABSTRACT.md").read_text().strip()
    # strip markdown bold for DOCX plain runs
    abstract = re.sub(r"\*\*([^*]+)\*\*", r"\1", abstract)
    body = (REPORT / "body.md").read_text()
    lim = (REPORT / "LIMITATIONS_DUAL_USE.md").read_text()
    final = (REPORT / "Swarm_Witness_Final_Submission.md").read_text()
    # Heading depth is not part of the boundary: the manuscript uses
    # "# Appendix A", and a literal "## Appendix" split would keep that
    # section inside References and then append a second appendix below.
    refs = _between_headings(final, "References", "Appendix")
    refs = re.sub(r"^\d+\.\s+", "", refs, flags=re.M)
    return {
        "abstract": abstract,
        "intro": _section_after(body, "# 1. Introduction", "## 2."),
        "related": _section_after(body, "## 2. Background and related work", "## 3."),
        "methods": _section_after(body, "## 3. Methodology", "## 4."),
        "results": _section_after(body, "## 4. Results", "## 5."),
        "discussion": _section_after(body, "## 5. Discussion and limitations", "## 6."),
        "conclusion": _section_after(body, "## 6. Conclusion", "## Code"),
        "code": _section_after(body, "## Code, data and reproducibility", None),
        "limitations": _strip_md_heading(lim),
        "refs": refs,
        "llm": (
            "AI assistants contributed to research brainstorming, implementation, "
            "validation scripts and draft writing. Reported experimental counts are "
            "taken from retained program outputs and tests; the author remains "
            "responsible for verifying released artifacts and the manuscript."
        ),
    }


def _heading_label(raw: str) -> str:
    """Drop ATX marks so a boundary matches at any heading depth."""
    return re.sub(r"^#+\s*", "", raw.strip())


def _find_heading(text: str, label: str) -> re.Match[str] | None:
    """First ATX heading of any depth whose title starts with label."""
    label = _heading_label(label)
    if not label:
        raise ValueError("empty heading label")
    return re.search(rf"^#{{1,6}}[ \t]+{re.escape(label)}.*$", text, re.M)


def _between_headings(text: str, start: str, end: str | None) -> str:
    start_match = _find_heading(text, start)
    if start_match is None:
        raise ValueError(f"missing {start}")
    rest = text[start_match.end() :]
    if end:
        end_match = _find_heading(rest, end)
        if end_match is None:
            raise ValueError(f"missing end {end}")
        rest = rest[: end_match.start()]
    return rest.strip()


def _section_after(text: str, start: str, end: str | None) -> str:
    return _strip_md(_between_headings(text, start, end))


def _strip_md_heading(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    return _strip_md("\n".join(lines).strip())


def _strip_md(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = re.sub(r"^\|.*\|$", "", text, flags=re.M)  # drop markdown tables for DOCX body
    text = re.sub(r"^-{3,}$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _paragraphs_to_blocks(text: str) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    return blocks


def fill_template() -> Path:
    if not TEMPLATE.exists():
        raise SystemExit(f"missing template: {TEMPLATE}")
    parts = _load_parts()
    doc = Document(str(TEMPLATE))

    # Title
    title_cell = doc.tables[0].rows[0].cells[0]
    _replace_first_text(title_cell._tc, "PROJECT TITLE", TITLE)

    # Authors + abstract live in second row
    abs_cell = doc.tables[0].rows[1].cells[0]
    _replace_first_text(abs_cell._tc, "Author name 1", AUTHOR)
    # first Affiliation after author 1
    replaced_aff = False
    for node in abs_cell._tc.iter(qn("w:t")):
        if node.text and node.text.strip() == "Affiliation" and not replaced_aff:
            node.text = AFFILIATION
            replaced_aff = True
    for n in range(2, 7):
        _replace_first_text(abs_cell._tc, f"Author name {n}", "")
    # remaining Affiliation placeholders
    for node in abs_cell._tc.iter(qn("w:t")):
        if node.text and node.text.strip() == "Affiliation":
            node.text = ""

    # Replace abstract guidance runs with real abstract (collapse into first long run)
    guidance_bits = []
    for node in abs_cell._tc.iter(qn("w:t")):
        if node.text and (
            "Summarize your project" in node.text
            or "Make sure to cover" in node.text
            or "Polish it last" in node.text
        ):
            guidance_bits.append(node)
    if guidance_bits:
        guidance_bits[0].text = parts["abstract"]
        for node in guidance_bits[1:]:
            node.text = ""

    # Delete the "How to use this template" info box (second top-level table)
    if len(doc.tables) > 1:
        _delete_table(doc.tables[1])

    # Replace body guidance by rebuilding from section headings onward.
    # Strategy: clear all body paragraphs after the front-matter tables, then append content.
    body_start = None
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip().startswith("1. Introduction"):
            body_start = i
            break
    if body_start is None:
        raise SystemExit("could not find Introduction heading")

    # Remove everything from Introduction to end
    for p in list(doc.paragraphs[body_start:]):
        _delete_paragraph(p)

    def add_heading(text: str, level: int = 2) -> None:
        doc.add_heading(text, level=level)

    def add_blocks(text: str) -> None:
        for block in _paragraphs_to_blocks(text):
            # preserve simple numbered/bulleted lines as separate paragraphs
            for line in block.splitlines():
                line = line.strip()
                if line:
                    doc.add_paragraph(line)

    add_heading("1. Introduction", 2)
    add_blocks(parts["intro"])
    add_heading("2. Related Work", 2)
    add_blocks(parts["related"])
    add_heading("3. Methods", 2)
    add_blocks(parts["methods"])
    add_heading("4. Results", 2)
    add_blocks(parts["results"])
    # Re-add compact result tables as plain text lines (markdown tables stripped)
    add_blocks(
        "Table 1 (summary). R1 confirms the SoundGate recovery barrier under pinned "
        "histories. R2 confirms the later EvidenceGraph stress harness. R3-D remains "
        "unresolved (0/4 BMO mappings). R3-L1 matches on six first-edit cases. R4 "
        "classifies 18 evidence cases. Causal simulator: 9×2 arms, defective 6 "
        "unauthorized effects, reference 0. R5 v2: 14×2 arms, defective 9 unauthorized "
        "effects and 10 incorrect decisions. Formal checker: 2,646 finite checks."
    )
    add_blocks(
        "Table 2 (paired worlds). Identical cached grant observations in active vs "
        "revoked worlds; reference allows only the active world; faulty local allows "
        "both; distinct effect ledger records the unauthorized commit."
    )
    add_heading("5. Discussion and Limitations", 2)
    add_blocks(parts["discussion"])
    add_heading("Limitations", 3)
    add_blocks(parts["limitations"].split("**Possible adversarial")[0])
    add_heading("Future Work", 3)
    add_blocks(
        "Live gateway-side observation, real delegated effects, independently authored "
        "case corpora, and integration of the formal evidence semantics into the audit schema."
    )
    add_heading("6. Conclusion", 2)
    add_blocks(parts["conclusion"])
    add_heading("Code and Data", 2)
    add_blocks(parts["code"])
    doc.add_paragraph("Code repository: https://github.com/instagrim-dev/swarm-witness")
    doc.add_paragraph(
        "Other artifacts: dist/swarm-witness-review-bundle.zip (portable evidence pack)"
    )
    add_heading("Author Contributions (optional)", 2)
    doc.add_paragraph(
        "J. Maye-Hobbs designed the audit protocol, implemented the experiments, "
        "and wrote the manuscript."
    )
    add_heading("References", 2)
    for line in parts["refs"].splitlines():
        line = line.strip()
        if line:
            doc.add_paragraph(line)
    add_heading("Appendix A. Limitations and Dual-Use / Ethical Considerations", 2)
    add_blocks(parts["limitations"])
    add_heading("LLM Usage Statement", 2)
    add_blocks(parts["llm"])

    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_DOCX))

    # Companion markdown for review (templated structure, no guidance)
    md = f"""# {TITLE}

**Author:** {AUTHOR}  
**Affiliation:** {AFFILIATION}  
**With** Apart Research

**Research track:** 3, Strengthening Agent Infrastructure. **Application:** Track 4.

## Abstract

{parts['abstract']}

## 1. Introduction

{parts['intro']}

## 2. Related Work

{parts['related']}

## 3. Methods

{parts['methods']}

## 4. Results

{parts['results']}

## 5. Discussion and Limitations

{parts['discussion']}

### Limitations

{parts['limitations']}

### Future Work

Live gateway-side observation, real delegated effects, independently authored case corpora, and integration of the formal evidence semantics into the audit schema.

## 6. Conclusion

{parts['conclusion']}

## Code and Data

{parts['code']}

- Code repository: https://github.com/instagrim-dev/swarm-witness
- Other artifacts: `dist/swarm-witness-review-bundle.zip`

## Author Contributions

J. Maye-Hobbs designed the audit protocol, implemented the experiments, and wrote the manuscript.

## References

{parts['refs']}

## Appendix A. Limitations and Dual-Use / Ethical Considerations

{parts['limitations']}

## LLM Usage Statement

{parts['llm']}
"""
    OUT_MD.write_text(md)
    return OUT_DOCX


if __name__ == "__main__":
    path = fill_template()
    print(f"Wrote {path}")
    print(f"Wrote {OUT_MD}")
