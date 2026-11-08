#!/usr/bin/env python3
"""Build both paper layouts and Markdown extracts from the canonical manuscript.

Requires Pandoc and python-docx. The committed Apart template supplies page
geometry, embedded fonts, and branding; its legacy styles and prose are omitted.
"""
from __future__ import annotations

import os
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
SOURCE = REPORT / "Swarm_Witness_Final_Submission.md"
TEMPLATE = REPORT / "official-template.docx"


def read_manuscript() -> tuple[str, dict[str, str], dict[str, re.Match[str]]]:
    text = SOURCE.read_text(encoding="utf-8").strip() + "\n"
    title = re.search(r"^# ([^\n]+)$", text, re.M)
    if title is None:
        raise ValueError("The manuscript needs a level-one title.")
    metadata = {"title": title.group(1)}
    for name in ("Author", "Affiliation"):
        match = re.search(rf"^\*\*{name}:\*\*\s+([^\n]+)$", text, re.M)
        if match is None:
            raise ValueError(f"The manuscript needs **{name}:** metadata.")
        metadata[name.lower()] = match.group(1).strip()
    headings = {
        match.group(1): match
        for match in re.finditer(r"^## ([^\n]+)$", text, re.M)
    }
    for name in ("Abstract", "References", "Appendix A Limitations and dual use", "LLM Usage Statement"):
        if name not in headings:
            raise ValueError(f"The manuscript needs a '{name}' section.")
    return text, metadata, headings


def write_extracts(text: str, headings: dict[str, re.Match[str]], branding: str) -> None:
    abstract = headings["Abstract"]
    body_start = next(match.start() for match in headings.values() if match.start() > abstract.start())
    appendix = headings["Appendix A Limitations and dual use"]
    extracts = {
        "ABSTRACT.md": text[abstract.end():body_start].strip(),
        "body.md": text[body_start:headings["References"].start()].strip(),
        "LIMITATIONS_DUAL_USE.md": text[appendix.start():].strip(),
        "Swarm_Witness_Templated_Submission.md": (
            text[:abstract.start()].rstrip() + "\n\n" + branding + "\n\n" + text[abstract.start():].strip()
        ),
    }
    for filename, content in extracts.items():
        (REPORT / filename).write_text(content + "\n", encoding="utf-8")


def template_branding(template) -> tuple[object, str]:
    for element in template.element.body.iter(qn("w:p")):
        words = [node.text for node in element.iter(qn("w:t")) if node.text]
        if "Apart Research" in words and "With" in words:
            return deepcopy(element), " ".join(words)
    raise ValueError("The committed template has no Apart Research branding paragraph.")


def retain_template_fonts(converted: Path) -> None:
    """Keep template fonts as complete parts without importing legacy styles."""
    repaired = converted.with_suffix(".fonts.docx")
    with ZipFile(converted) as source, ZipFile(TEMPLATE) as reference:
        font_parts = [name for name in reference.namelist() if name.startswith("word/fonts/")]
        replacements = ["word/fontTable.xml", "word/_rels/fontTable.xml.rels", *font_parts]
        content_types = etree.fromstring(source.read("[Content_Types].xml"))
        extensions = {Path(name).suffix.lstrip(".") for name in font_parts}
        existing = {element.get("Extension") for element in content_types}
        for element in etree.fromstring(reference.read("[Content_Types].xml")):
            if element.get("Extension") in extensions - existing:
                content_types.append(deepcopy(element))
        with ZipFile(repaired, "w", compression=ZIP_DEFLATED) as output:
            for item in source.infolist():
                if item.filename in replacements:
                    continue
                content = (
                    etree.tostring(content_types, xml_declaration=True, encoding="UTF-8")
                    if item.filename == "[Content_Types].xml" else source.read(item.filename)
                )
                output.writestr(item, content)
            for name in replacements:
                output.writestr(name, reference.read(name))
    repaired.replace(converted)


def style_document(doc, metadata: dict[str, str], template, *, templated: bool) -> None:
    # Pandoc and Word use different capitalization for some built-in style
    # names. Stable OOXML IDs avoid python-docx's localized name aliases.
    styles = {style.style_id: style for style in doc.styles}
    geometry = template.sections[0]
    for section in doc.sections:
        for name in ("page_width", "page_height", "orientation", "top_margin", "bottom_margin", "left_margin", "right_margin", "header_distance", "footer_distance"):
            setattr(section, name, getattr(geometry, name))
    font_name = "Old Standard TT" if templated else "Times New Roman"
    for name in ("Normal", "BodyText", "FirstParagraph", "Compact"):
        if name not in styles:
            continue
        style = styles[name]
        style.font.name = font_name
        style.font.size = Pt(11)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.line_spacing = 1.1
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.widow_control = True
    for name, size in (("Title", 18), ("Heading1", 13), ("Heading2", 11.5), ("Heading3", 11)):
        style = styles[name]
        style.font.name = font_name
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(12 if name != "Title" else 0)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True
        borders = style.element.find("w:pPr/w:pBdr", style.element.nsmap)
        if borders is not None:
            borders.getparent().remove(borders)
    for name in ("VerbatimChar", "SourceCode"):
        if name in styles:
            styles[name].font.name = "DejaVu Sans Mono"
            styles[name].font.size = Pt(9)
    for style in styles.values():
        fonts = style.element.find("w:rPr/w:rFonts", style.element.nsmap)
        if fonts is not None and style.font.name:
            for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
                fonts.attrib.pop(qn(f"w:{attribute}"), None)
    in_references = False
    for index, paragraph in enumerate(doc.paragraphs):
        if index == 0:
            paragraph.style = styles["Title"]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif re.fullmatch(r"Heading\d", paragraph.style.style_id):
            level = int(paragraph.style.style_id[-1])
            paragraph.style = styles[f"Heading{max(1, level - 1)}"]
        elif "Author:" in paragraph.text and metadata["author"] in paragraph.text:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.keep_with_next = True
        elif "Affiliation:" in paragraph.text and metadata["affiliation"] in paragraph.text:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.keep_with_next = True
        if paragraph.text == "References":
            in_references = True
            paragraph.paragraph_format.page_break_before = True
        elif paragraph.style.style_id.startswith("Heading") and in_references:
            in_references = False
        elif in_references:
            paragraph.paragraph_format.space_after = Pt(4)
            for run in paragraph.runs:
                run.font.size = Pt(9.5)
        if paragraph.style.style_id.startswith("Heading") or paragraph.style.style_id == "Title":
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)
        if paragraph.text.startswith("Appendix A"):
            paragraph.paragraph_format.page_break_before = True
        if paragraph.text.startswith("Table "):
            paragraph.paragraph_format.keep_with_next = True
    for table in doc.tables:
        format_table(table, doc.sections[0])
    for section in doc.sections:
        footer = section.footer.paragraphs[0]
        footer.clear()
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run()
        run.font.name = font_name
        run.font.size = Pt(9)
        field = OxmlElement("w:fldSimple")
        field.set(qn("w:instr"), "PAGE")
        run._r.addnext(field)
    doc.core_properties.title = metadata["title"]
    doc.core_properties.author = metadata["author"]
    doc.core_properties.last_modified_by = metadata["author"]
    doc.core_properties.subject = ""
    doc.core_properties.comments = ""
    doc.core_properties.keywords = ""


def format_table(table, section) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    available = section.page_width - section.left_margin - section.right_margin
    weights = [
        max(12, min(60, max(len(row.cells[index].text) for row in table.rows))) ** 0.5
        for index in range(len(table.columns))
    ]
    for index, weight in enumerate(weights):
        width = int(available * weight / sum(weights))
        table.columns[index].width = width
        for row in table.rows:
            row.cells[index].width = width
    properties = table._tbl.tblPr
    for old in properties.findall(qn("w:tblBorders")):
        properties.remove(old)
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        edge = OxmlElement(f"w:{side}")
        for key, value in (("val", "single"), ("sz", "4"), ("color", "D9D9D9")):
            edge.set(qn(f"w:{key}"), value)
        borders.append(edge)
    properties.append(borders)
    for row_index, row in enumerate(table.rows):
        row_properties = row._tr.get_or_add_trPr()
        if row_properties.find(qn("w:cantSplit")) is None:
            row_properties.append(OxmlElement("w:cantSplit"))
        if row_index == 0 and row_properties.find(qn("w:tblHeader")) is None:
            row_properties.append(OxmlElement("w:tblHeader"))
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell_borders = deepcopy(borders)
            cell_borders.tag = qn("w:tcBorders")
            cell._tc.get_or_add_tcPr().append(cell_borders)
            margins = OxmlElement("w:tcMar")
            for side, width in (("top", "60"), ("bottom", "60"), ("left", "100"), ("right", "100")):
                margin = OxmlElement(f"w:{side}")
                margin.set(qn("w:w"), width)
                margin.set(qn("w:type"), "dxa")
                margins.append(margin)
            cell._tc.get_or_add_tcPr().append(margins)
            if row_index == 0:
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), "EEEEEE")
                cell._tc.get_or_add_tcPr().append(shading)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_before = Pt(3)
                paragraph.paragraph_format.space_after = Pt(3)
                paragraph.paragraph_format.line_spacing = 1.0
                paragraph.paragraph_format.keep_with_next = row_index < len(table.rows) - 1
                for run in paragraph.runs:
                    run.font.size = Pt(9.5)
                    run.font.color.rgb = RGBColor(0, 0, 0)
                    if row_index == 0:
                        run.font.bold = True


def main() -> None:
    text, metadata, headings = read_manuscript()
    template = Document(TEMPLATE)
    brand_element, brand_text = template_branding(template)
    with TemporaryDirectory(prefix="swarm-witness-paper-") as directory:
        converted = Path(directory) / "manuscript.docx"
        subprocess.run(
            [
                os.environ.get("PANDOC", "pandoc"), str(SOURCE),
                "--from=gfm", "--to=docx", "--standalone",
                f"--resource-path={REPORT}",
                "--output", str(converted),
            ],
            check=True,
        )
        for variant, templated in (("Final", False), ("Templated", True)):
            doc = Document(converted)
            style_document(doc, metadata, template, templated=templated)
            if templated:
                abstract = next(p for p in doc.paragraphs if p.text == "Abstract")
                abstract._p.addprevious(deepcopy(brand_element))
            destination = REPORT / f"Swarm_Witness_{variant}_Submission.docx"
            doc.save(destination)
            retain_template_fonts(destination)
            print(destination.relative_to(ROOT))
    write_extracts(text, headings, brand_text)


if __name__ == "__main__":
    main()
