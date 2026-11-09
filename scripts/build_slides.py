#!/usr/bin/env python3
"""Build the results-guide figure from the manuscript and print the slide PDF.

The guide figure repeats the manuscript table. It does not introduce counts.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "report" / "Swarm_Witness_Final_Submission.md"
GUIDE = ROOT / "report" / "slides" / "figures" / "results-guide.svg"
SLIDES = ROOT / "report" / "slides" / "slides.html"
PDF = ROOT / "report" / "slides" / "Swarm_Witness_Slides.pdf"
CHROME = os.environ.get(
    "CHROME",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def guide_table(markdown: str) -> list[list[str]]:
    lines = markdown.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("**Evidence chain."))
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        rows.append(cells)
    if len(rows) < 2:
        raise ValueError("The manuscript results guide has no rows.")
    return rows


def _wrap(text: str, limit: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = word if not current else f"{current} {word}"
        if len(trial) <= limit:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


SUPPORT = "#1F7A4D"
REFUTE = "#9B3A3A"
UNRESOLVED = "#9A6B12"
OVERCLAIM = "#C2410C"
UNTESTED = "#5C6B73"


def _icon(kind: str, x: float, y: float, color: str, radius: float = 13) -> str:
    if kind == "check":
        return (
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="none" stroke="{color}" stroke-width="3"/>'
            f'<path d="M{x - 6} {y} l4 5 l8 -9" fill="none" stroke="{color}" stroke-width="3"/>'
        )
    if kind == "cross":
        return (
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="none" stroke="{color}" stroke-width="3"/>'
            f'<path d="M{x - 5} {y - 5} l10 10 M{x + 5} {y - 5} l-10 10" fill="none" stroke="{color}" stroke-width="3"/>'
        )
    if kind == "dash":
        return (
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="none" stroke="{color}" stroke-width="3"/>'
            f'<path d="M{x - 6} {y} h12" fill="none" stroke="{color}" stroke-width="3"/>'
        )
    if kind == "warn":
        return (
            f'<path d="M{x} {y - radius - 2} l{radius} {radius * 2} h-{radius * 2} z" fill="none" stroke="{color}" stroke-width="3"/>'
            f'<path d="M{x} {y - 2} v7" stroke="{color}" stroke-width="3"/>'
        )
    if kind == "stop":
        return (
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="none" stroke="{color}" stroke-width="3"/>'
            f'<path d="M{x - radius + 4} {y - radius + 4} l{2 * radius - 8} {2 * radius - 8}" stroke="{color}" stroke-width="3"/>'
        )
    return (
        f'<circle cx="{x}" cy="{y}" r="{radius}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="3 3"/>'
    )


def _row_mark(name: str) -> tuple[str, str]:
    return {
        "Authority and claim": ("check", SUPPORT),
        "Terminal settlement": ("trio", SUPPORT),
        "Effect and warrant": ("warn", OVERCLAIM),
        "Evidence translation": ("warn", OVERCLAIM),
    }.get(name, ("open", UNTESTED))


def _line_fill(line: str) -> str:
    lowered = line.lower()
    if "unsupported" in lowered or "eleven" in lowered:
        return OVERCLAIM
    if "untested" in lowered or "does not replace" in lowered or lowered.startswith("not "):
        return UNTESTED
    if "match" in lowered or "effect-applied only" in lowered:
        return SUPPORT
    return "#1a1a1a"


def _phrase_text(x: int | float, y: int | float, size: int, fill: str, line: str) -> str:
    shown = line.replace("*", "")
    pieces = re.split(r"(unsupported supports?)", shown)
    opening = f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}">'
    if len(pieces) == 1:
        return f"{opening}{escape(shown)}</text>"
    spans = []
    for piece in pieces:
        if not piece:
            continue
        italic = ' font-style="italic"' if re.fullmatch(r"unsupported supports?", piece) else ""
        spans.append(f"<tspan{italic}>{escape(piece)}</tspan>")
    return opening + "".join(spans) + "</text>"


def guide_svg(rows: list[list[str]]) -> str:
    header, body = rows[0], rows[1:]
    limits = (16, 24, 26, 22)
    origins = (110, 390, 820, 1220)
    wrapped = []
    for row in body:
        cells = [_wrap(cell.replace("*", ""), limit) for cell, limit in zip(row, limits)]
        height = 34 + 28 * max(len(cell) for cell in cells)
        wrapped.append((row[0], cells, height))
    width = 1600
    y = 24
    header_lines = [_wrap(label, limit) for label, limit in zip(header, limits)]
    header_height = 28 + 26 * max(len(lines) for lines in header_lines)
    legend = 70
    total = y + header_height + sum(item[2] for item in wrapped) + legend
    description = " ".join(" ".join(row) for row in rows)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total}" role="img">',
        f"<desc>{escape(description)}</desc>",
        "<defs><style>",
        '@font-face { font-family: "Old Standard TT"; src: url("../../fonts/OldStandardTT-regular.ttf"); font-weight: 400; }',
        '@font-face { font-family: "Old Standard TT"; src: url("../../fonts/OldStandardTT-bold.ttf"); font-weight: 700; }',
        'text { font-family: "Old Standard TT", "Times New Roman", Times, serif; fill: #1a1a1a; }',
        "</style></defs>",
        f'<rect width="{width}" height="{total}" fill="#ffffff"/>',
    ]
    parts.append(f'<rect x="32" y="{y}" width="1536" height="{header_height}" fill="#eeeeee" stroke="#d9d9d9"/>')
    for lines, origin in zip(header_lines, (48, *origins[1:])):
        for index, line in enumerate(lines):
            parts.append(
                f'<text x="{origin}" y="{y + 28 + index * 26}" font-size="20" font-weight="700">{escape(line)}</text>'
            )
    cursor = y + header_height
    for name, cells, height in wrapped:
        parts.append(f'<rect x="32" y="{cursor}" width="1536" height="{height}" fill="#ffffff" stroke="#d9d9d9"/>')
        kind, color = _row_mark(name)
        mark_y = cursor + height / 2
        if kind == "trio":
            parts.append(_icon("check", 52, mark_y - 16, SUPPORT, 9))
            parts.append(_icon("cross", 52, mark_y, REFUTE, 9))
            parts.append(_icon("dash", 52, mark_y + 16, UNRESOLVED, 9))
        else:
            parts.append(_icon(kind, 64, mark_y, color, 12))
        for lines, origin in zip(cells, origins):
            for index, line in enumerate(lines):
                parts.append(_phrase_text(origin, cursor + 30 + index * 28, 20, "#1a1a1a", line))
        cursor += height
    legend_y = cursor + 28
    legend_items = (
        ("check", SUPPORT, "Supported"),
        ("cross", REFUTE, "Refuted"),
        ("dash", UNRESOLVED, "Unresolved"),
        ("warn", OVERCLAIM, "Unsupported support"),
        ("open", UNTESTED, "Untested or not carried forward"),
    )
    legend_x = 48
    for kind, color, label in legend_items:
        parts.append(_icon(kind, legend_x + 12, legend_y, color, 11))
        italic = ' font-style="italic"' if kind == "warn" else ""
        parts.append(
            f'<text x="{legend_x + 32}" y="{legend_y + 6}" font-size="20" fill="{color}"{italic}>{escape(label)}</text>'
        )
        legend_x += 250 if kind != "warn" else 310
    parts.append("</svg>\n")
    return "\n".join(parts)


def write_guide() -> None:
    GUIDE.write_text(guide_svg(guide_table(MANUSCRIPT.read_text(encoding="utf-8"))), encoding="utf-8")


def print_pdf() -> None:
    if not Path(CHROME).exists():
        raise SystemExit(f"Chrome is required to print the slides: {CHROME}")
    PDF.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={PDF}",
            SLIDES.as_uri(),
        ],
        check=True,
    )


def main() -> None:
    write_guide()
    print(GUIDE.relative_to(ROOT))
    print_pdf()
    print(PDF.relative_to(ROOT))


if __name__ == "__main__":
    main()
