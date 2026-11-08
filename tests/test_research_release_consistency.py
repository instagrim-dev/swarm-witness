"""Release consistency: distinct denominators, and comparison versus re-execution."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "report" / "Swarm_Witness_Final_Submission.md"
RENDERER = ROOT / "scripts" / "render_release_tables.py"


def _figures():
    spec = importlib.util.spec_from_file_location("render_release_tables", RENDERER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.release_figures(ROOT)


def _section(text: str, heading: str, following: str) -> str:
    start = text.index(heading)
    end = text.index(following, start + len(heading))
    return text[start:end]


def test_release_figures_keep_historical_current_and_challenge_apart():
    figures = _figures()
    assert figures["compare_only"] is True
    assert figures["live_model_edit"] is False
    assert figures["ledger_case_count"] == 6
    assert figures["initial_settlement_case_count"] == 2
    assert figures["controls_case_count"] == 9
    assert "| 11 |" in figures["historical_row"]
    assert figures["historical_row"] != figures["current_row"]
    assert "| 0 |" in figures["current_row"]
    assert figures["representation_packet_count"] == 70
    assert figures["representation_overlap"] == 70
    assert figures["built_corpus_count"] == 130
    assert figures["challenge_v1_count"] == 16
    assert figures["challenge_v2_count"] == 16
    assert figures["challenge_v1_spoofed"] == "supported"
    assert figures["challenge_v2_spoofed"] == "unresolved"
    assert figures["challenge_v2_rejections"] == 3
    assert figures["ledger_case_count"] + figures["controls_case_count"] != figures["controls_case_count"]
    assert figures["representation_packet_count"] + figures["built_corpus_count"] != figures["built_corpus_count"]


def test_manuscript_does_not_sum_overlapping_denominators():
    figures = _figures()
    text = MANUSCRIPT.read_text(encoding="utf-8")
    results = _section(text, "## 4 Results", "## 5 ")
    assert "does not re-execute BMO" in results
    assert "not a live model edit" in results
    assert "does not replace Table 2" in results
    assert "sixteen-case" in results
    assert "eleven" in results
    assert "refutes only the effect-applied proposition" in results
    assert f"{figures['raw_assessor']}" in results
    assert f"{figures['composed_assessor']}" in results
    assert f"{figures['composed_warrant']}" in results
    assert str(figures["composed_unsupported"]) in results
    assert "70" in results and "130" in results
    assert "current eleven" not in text.lower()
    for forbidden in ("15 cases", "64 packets", "200 packets", "79 packets"):
        assert forbidden not in text
    assert "spoofed" in results
    assert "rejection" in results


def test_each_result_subsection_states_question_observation_result_and_implication():
    text = MANUSCRIPT.read_text(encoding="utf-8")
    results = _section(text, "## 4 Results", "## 5 ")
    for heading in (
        "### 4.1 ",
        "### 4.2 ",
        "### 4.3 ",
        "### 4.4 ",
        "### 4.5 ",
    ):
        assert heading in results
    parts = results.split("### 4.")
    for part in parts[1:]:
        lowered = part.lower()
        for word in ("the question", "the observation", "the result", "the implication"):
            assert word in lowered, part[:80]


def test_conclusion_separates_the_contract_from_later_qualifications():
    text = MANUSCRIPT.read_text(encoding="utf-8")
    conclusion = _section(text, "## 6 Conclusion", "## Code and data")
    paragraphs = [block.strip() for block in conclusion.split("\n\n") if block.strip() and not block.startswith("#")]
    assert len(paragraphs) >= 2
    assert "BMO" in paragraphs[0]
    assert "effect-applied" in paragraphs[0]
    assert "eleven" in paragraphs[1]
    assert "130" in paragraphs[1]
    assert "transfer" in paragraphs[1].lower()
