#!/usr/bin/env python3
"""Build both paper layouts and Markdown extracts from the canonical manuscript.

Requires Pandoc and python-docx. The templated export fills the Apart title
card and uses its heading color. Guidance text and the info box are omitted.
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


def _paragraph_text(element) -> str:
    return "".join(node.text or "" for node in element.iter(qn("w:t"))).strip()


def _set_paragraph_text(element, text: str, *, keep_italic: bool = False) -> None:
    runs = element.findall(qn("w:r"))
    if not runs:
        raise ValueError("template paragraph has no run")
    first = runs[0]
    for extra in runs[1:]:
        element.remove(extra)
    properties = first.find(qn("w:rPr"))
    if properties is not None and not keep_italic:
        for tag in ("w:i", "w:iCs", "w:u"):
            node = properties.find(qn(tag))
            if node is not None:
                properties.remove(node)
    node = first.find(qn("w:t"))
    if node is None:
        node = OxmlElement("w:t")
        first.append(node)
    node.set(qn("xml:space"), "preserve")
    node.text = text


def _fill_title_table(table, metadata: dict[str, str], abstract: str) -> None:
    """Put the manuscript into the template title card and drop unused author slots."""
    author_table = None
    for nested in table.iter(qn("w:tbl")):
        texts = [_paragraph_text(paragraph) for paragraph in nested.iter(qn("w:p"))]
        if any(text.startswith("Author name 1") for text in texts) and not any(
            "Apart Research" in text or text.startswith("PROJECT") or text.startswith("Summarize")
            for text in texts
        ):
            author_table = nested
    affiliation_used = False
    for paragraph in table.iter(qn("w:p")):
        text = _paragraph_text(paragraph)
        if "PROJECT TITLE" in text:
            for node in paragraph.iter(qn("w:t")):
                if node.text and "PROJECT TITLE" in node.text:
                    node.text = node.text.replace("PROJECT TITLE", metadata["title"])
        elif text.startswith("Summarize your project"):
            _set_paragraph_text(paragraph, abstract)
        else:
            for node in paragraph.iter(qn("w:t")):
                if node.text == "Author name 1":
                    node.text = metadata["author"]
                    break_mark = OxmlElement("w:br")
                    node.getparent().append(break_mark)
                elif node.text and node.text.startswith("Author name"):
                    node.text = ""
                elif node.text == "Affiliation":
                    node.text = "" if affiliation_used else metadata["affiliation"]
                    affiliation_used = True
    if author_table is None:
        raise ValueError("template author table was not filled")
    rows = author_table.findall(qn("w:tr"))
    for row in rows[1:]:
        author_table.remove(row)
    first_row = author_table.find(qn("w:tr"))
    cells = first_row.findall(qn("w:tc"))
    for cell in cells[1:]:
        first_row.remove(cell)
    grid = author_table.find(qn("w:tblGrid"))
    if grid is not None:
        columns = grid.findall(qn("w:gridCol"))
        if columns:
            columns[0].set(qn("w:w"), "4320")
        for column in columns[1:]:
            grid.remove(column)
    preferred = author_table.find(qn("w:tblPr") + "/" + qn("w:tblW"))
    if preferred is not None:
        preferred.set(qn("w:w"), "4320")
        preferred.set(qn("w:type"), "dxa")


def template_branding(template) -> tuple[object, str]:
    for element in template.element.body.iter(qn("w:p")):
        words = [node.text for node in element.iter(qn("w:t")) if node.text]
        if "Apart Research" in words and "With" in words:
            return deepcopy(element), " ".join(words)
    raise ValueError("The committed template has no Apart Research branding paragraph.")


def template_title_table(template, metadata: dict[str, str], abstract: str):
    table = deepcopy(template.tables[0]._tbl)
    _fill_title_table(table, metadata, abstract)
    # The card's Table1–Table4 styles are not in the Pandoc document. Keep the
    # borders written on each table so the title card still draws.
    for nested in (table, *table.iter(qn("w:tbl"))):
        style = nested.find(qn("w:tblPr") + "/" + qn("w:tblStyle"))
        if style is not None:
            style.getparent().remove(style)
    return table


def attach_template_footnote(converted: Path) -> None:
    """Keep the template's hackathon footnote on the title."""
    relationship_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    footnote_id = "1"
    link_id = "rIdSwarmAlignment"
    with ZipFile(TEMPLATE) as reference:
        template_footnotes = etree.fromstring(reference.read("word/footnotes.xml"))
        source_note = next(
            note for note in template_footnotes.findall(qn("w:footnote"))
            if note.get(qn("w:id")) == "0"
        )
    source_note.set(qn("w:id"), footnote_id)
    for link in source_note.iter(qn("w:hyperlink")):
        link.set(qn("r:id"), link_id)
    with ZipFile(converted) as source:
        footnotes = etree.fromstring(source.read("word/footnotes.xml"))
        footnotes.append(source_note)
        relationships = etree.fromstring(source.read("word/_rels/footnotes.xml.rels"))
        link = etree.Element(f"{{{relationship_ns}}}Relationship")
        link.set("Id", link_id)
        link.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink")
        link.set("Target", "https://apartresearch.com/sprints/swarm-alignment-2026")
        link.set("TargetMode", "External")
        relationships.append(link)
        document = etree.fromstring(source.read("word/document.xml"))
        references = document.findall(".//" + qn("w:footnoteReference"))
        if len(references) != 1:
            raise ValueError("the title card should keep one template footnote reference")
        references[0].set(qn("w:id"), footnote_id)
        replacements = {
            "word/footnotes.xml": etree.tostring(footnotes, xml_declaration=True, encoding="UTF-8"),
            "word/_rels/footnotes.xml.rels": etree.tostring(relationships, xml_declaration=True, encoding="UTF-8"),
            "word/document.xml": etree.tostring(document, xml_declaration=True, encoding="UTF-8"),
        }
        updated = converted.with_suffix(".footnote.docx")
        with ZipFile(updated, "w", compression=ZIP_DEFLATED) as output:
            for item in source.infolist():
                output.writestr(item, replacements.get(item.filename, source.read(item.filename)))
    updated.replace(converted)


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
        style.paragraph_format.line_spacing = 1.0 if templated else 1.1
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(3 if templated else 5)
        style.paragraph_format.widow_control = True
    for name, size in (("Title", 18), ("Heading1", 13), ("Heading2", 11.5), ("Heading3", 11)):
        style = styles[name]
        style.font.name = font_name
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0x43, 0x43, 0x43) if templated else RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt((8 if templated else 12) if name != "Title" else 0)
        style.paragraph_format.space_after = Pt(3 if templated else 5)
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
            color = RGBColor(0x43, 0x43, 0x43) if templated and paragraph.style.style_id.startswith("Heading") else RGBColor(0, 0, 0)
            for run in paragraph.runs:
                run.font.color.rgb = color
                if templated:
                    run.font.name = font_name
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
                abstract = next(paragraph.text for paragraph in doc.paragraphs if len(paragraph.text.split()) > 80)
                title_table = template_title_table(template, metadata, abstract)
                doc.element.body.insert(0, title_table)
                remove = []
                for paragraph in doc.paragraphs:
                    paragraph_text = paragraph.text.strip()
                    if (
                        paragraph_text == metadata["title"]
                        or paragraph_text in {"Abstract", brand_text}
                        or paragraph_text.startswith("Author:")
                        or paragraph_text.startswith("With")
                        or paragraph_text == abstract
                    ):
                        remove.append(paragraph._p)
                for element in remove:
                    element.getparent().remove(element)
            destination = REPORT / f"Swarm_Witness_{variant}_Submission.docx"
            doc.save(destination)
            if templated:
                attach_template_footnote(destination)
            retain_template_fonts(destination)
            print(destination.relative_to(ROOT))
    write_extracts(text, headings, brand_text)


if __name__ == "__main__":
    main()
