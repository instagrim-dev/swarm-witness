"""The current slides repeat the manuscript guide and leave the old deck behind."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLIDES = ROOT / "report" / "slides"


def _builder():
    spec = importlib.util.spec_from_file_location("build_slides", ROOT / "scripts" / "build_slides.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_guide_figure_repeats_the_manuscript_table():
    module = _builder()
    rows = module.guide_table((ROOT / "report" / "Swarm_Witness_Final_Submission.md").read_text(encoding="utf-8"))
    figure = (SLIDES / "figures" / "results-guide.svg").read_text(encoding="utf-8")
    assert figure == module.guide_svg(rows)
    for row in rows:
        for cell in row:
            assert cell.replace("`", "") in figure


def test_slides_use_the_current_partition():
    text = "\n".join(path.read_text(encoding="utf-8") for path in SLIDES.rglob("*") if path.suffix in {".html", ".svg"})
    for phrase in (
        "Track 4, Multi-Agent Oversight and Control",
        "Jonathan Maye-Hobbs",
        "Apart Research",
        "Bounded contract portability is demonstrated",
        "External empirical transfer remains untested",
        "SoundGate",
        "invariant checker",
        "NOT A BMO RESULT",
        "does not replace Table 2",
        "eleven unsupported supports",
        "sixteen-case challenge",
        "70-packet slice",
        "inside 130",
        "Not P_effect",
        "Not a live model edit",
        "evidence/ACCESS.md",
    ):
        assert phrase in text, phrase
    for stale in ("Track 3", "R3-D", "R5 v2", "review-bundle", "9 / 0", "superiority"):
        assert stale not in text
