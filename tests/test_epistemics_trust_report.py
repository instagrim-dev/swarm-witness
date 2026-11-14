"""The epistemics report is the measurement, with the sprint's page and boundary rules."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "report" / "epistemics_trust_v1" / "manuscript.md"
PDF = ROOT / "report" / "epistemics_trust_v1" / "Epistemics_Trust_Templated.pdf"
CLOSED = ROOT / "report" / "Swarm_Witness_Final_Submission.md"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _measurement():
    return _load("epistemics_trust_v1", ROOT / "experiments" / "epistemics_trust_v1" / "run.py").measure(ROOT)


def _manuscript_module():
    return _load("epistemics_manuscript", ROOT / "experiments" / "epistemics_trust_v1" / "manuscript.py")


def test_report_counts_come_from_the_measurement():
    result = _measurement()
    module = _manuscript_module()
    text = module.render_manuscript(result)
    intact = result["intact_actor_consumer"]
    retained = result["retained_verdict_consumer"]
    admission = result["admission_consumer"]
    assert f"| Intact actor record | {intact['unsupported_supports']} |" in text
    assert f"| Historical Swarm Witness label | {retained['unsupported_supports']} |" in text
    assert f"| Invariant checker | {admission['unsupported_supports']} |" in text
    assert f"{retained['correct_decisive']}/{retained['decisive_opportunities']}" in text
    assert "aew-v1-h-local-pass-broader-effect" in text
    challenge = result["challenge_probes"]
    for names in challenge["separating_cases"].values():
        for name in names:
            assert name in text
    assert "sixteen mutations of one discriminating-readback packet" in text
    assert "not added to the 48" in text
    assert "64" not in text
    assert "active on nine" not in text
    assert "Table N" not in text
    assert "13 records" in text
    assert f"{intact['correct_abstentions']}/24" in text
    abstract = module.abstract_text(text)
    assert 150 <= module.word_count(abstract) <= 250
    for heading in (
        "## Abstract",
        "## References",
        "## Appendix A Limitations and dual use",
        "## LLM Usage Statement",
    ):
        assert heading in text
    assert text.startswith(f"# {module.TITLE}\n")
    assert MANUSCRIPT.read_text(encoding="utf-8") == text


def test_preexisting_boundary_is_marked_and_the_closed_paper_stays():
    preexisting = (ROOT / "PREEXISTING.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "November 13–15, 2026" in preexisting
    assert "experiments/epistemics_trust_v1/" in preexisting
    assert "The November 6–8 manuscript is not rewritten." in preexisting
    assert "report/epistemics_trust_v1/manuscript.md" in readme
    assert "preexisting" in readme.lower()
    closed = CLOSED.read_text(encoding="utf-8")
    assert closed.startswith("# Swarm Witness Evidence for Agent Authorization\n")
    assert "Its eleven *unsupported supports* are withheld or misbound packets" in closed
    assert "An Intact Actor Log Is Not an Effect Warrant" not in closed


def test_templated_pdf_keeps_the_body_inside_the_sprint_cap():
    geometry = _load(
        "inspect_rendered_pages", ROOT / "scripts" / "inspect_rendered_pages.py"
    ).geometry
    measured = geometry(PDF)
    assert measured["references_begin_page"] is not None
    assert measured["body_pages_before_references"] <= 8
    assert measured["body_pages_before_references"] >= 1
    reader_text = []
    from pypdf import PdfReader

    for page in PdfReader(str(PDF)).pages:
        reader_text.append(page.extract_text() or "")
    combined = "\n".join(reader_text)
    assert "An Intact Actor Log Is Not an Effect Warrant" in combined
    assert "Limitations and dual use" in combined
    assert "Jonathan Maye-Hobbs" in combined
    assert "AI x Epistemics Research Sprint" in combined
    assert "Swarm Alignment Hackathon" not in combined
