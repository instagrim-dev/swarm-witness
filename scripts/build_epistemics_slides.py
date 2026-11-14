#!/usr/bin/env python3
"""Print the epistemics slide PDF and a matching PowerPoint deck.

The closed Swarm Alignment slides are not rebuilt.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLIDES = ROOT / "report" / "epistemics_trust_v1" / "slides" / "slides.html"
PDF = ROOT / "report" / "epistemics_trust_v1" / "slides" / "Epistemics_Trust_Slides.pdf"
PPTX = ROOT / "report" / "epistemics_trust_v1" / "slides" / "Epistemics_Trust_Slides.pptx"
FRAMES = ROOT / ".build" / "epistemics-slides"
CHROME = os.environ.get(
    "CHROME",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)
PPTX_PYTHON = os.environ.get(
    "PPTX_PYTHON",
    str(ROOT / ".build" / "tts-venv" / "bin" / "python"),
)

RENDER = r"""
import Foundation
import PDFKit
import AppKit

let pdfPath = CommandLine.arguments[1]
let outDir = CommandLine.arguments[2]
let document = PDFDocument(url: URL(fileURLWithPath: pdfPath))!
try FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
for index in 0..<document.pageCount {
    let page = document.page(at: index)!
    let bounds = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2
    let width = bounds.width * scale
    let height = bounds.height * scale
    let image = NSImage(size: NSSize(width: width, height: height))
    image.lockFocus()
    NSColor.white.set()
    NSRect(x: 0, y: 0, width: width, height: height).fill()
    let context = NSGraphicsContext.current!.cgContext
    context.saveGState()
    context.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: context)
    context.restoreGState()
    image.unlockFocus()
    guard let tiff = image.tiffRepresentation,
          let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else {
        fputs("page \(index) did not render\n", stderr)
        exit(1)
    }
    try png.write(to: URL(fileURLWithPath: "\(outDir)/slide-\(index + 1).png"))
}
"""

PACK = r"""
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches

pdf_frames = sorted(Path(sys.argv[1]).glob("slide-*.png"), key=lambda path: int(path.stem.split("-")[1]))
destination = Path(sys.argv[2])
presentation = Presentation()
presentation.slide_width = Inches(13.333333)
presentation.slide_height = Inches(7.5)
blank = presentation.slide_layouts[6]
for frame in pdf_frames:
    slide = presentation.slides.add_slide(blank)
    slide.shapes.add_picture(str(frame), 0, 0, width=presentation.slide_width, height=presentation.slide_height)
presentation.save(destination)
print(f"{len(pdf_frames)} {destination}")
"""


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


def write_pptx() -> None:
    frames = FRAMES / "frames"
    if frames.exists():
        for old in frames.glob("slide-*.png"):
            old.unlink()
    subprocess.run(["swift", "-e", RENDER, str(PDF), str(frames)], check=True)
    python = PPTX_PYTHON if Path(PPTX_PYTHON).exists() else sys.executable
    subprocess.run([python, "-c", PACK, str(frames), str(PPTX)], check=True)


def main() -> None:
    print_pdf()
    write_pptx()
    print(PDF.relative_to(ROOT))
    print(PPTX.relative_to(ROOT))


if __name__ == "__main__":
    main()
