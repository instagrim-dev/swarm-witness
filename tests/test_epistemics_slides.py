"""The epistemics slides repeat the sprint report and keep the denominators apart."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLIDES = ROOT / "report" / "epistemics_trust_v1" / "slides" / "slides.html"
PDF = ROOT / "report" / "epistemics_trust_v1" / "slides" / "Epistemics_Trust_Slides.pdf"
CLOSED = ROOT / "report" / "slides" / "slides.html"


def test_epistemics_slides_repeat_the_report_counts():
    text = SLIDES.read_text(encoding="utf-8")
    for phrase in (
        "An Intact Actor Log",
        "Track 2, Trust Infrastructure",
        "Jonathan Maye-Hobbs",
        "Apart Research",
        "Four views of twelve histories",
        "Not added to the 48",
        "Does not replace November Table 2 or Table 2b",
        "13 records",
        "26",
        "22/24",
        "24/24",
        "aew-v1-h-local-pass-broader-effect",
        "9 unsupported supports",
        "supported for the barrier and refuted for the original policy",
        "SoundGate is a representation probe",
        "not a cryptographic guarantee",
        "python experiments/epistemics_trust_v1/run.py",
        "Public commit ea58c7d contains that runner.",
        "November Table 2 or Table 2b",
        "13 records",
        "unknown subject beside an authorized sink",
    ):
        assert phrase in text, phrase
    assert "Admission is the missing check" not in text
    assert "together with" not in text
    assert text.count('class="slide') == 8
    assert "64" not in text
    assert "Track 4" not in text
    closed = CLOSED.read_text(encoding="utf-8")
    assert "Track 4, Multi-Agent Oversight and Control" in closed
    assert "An Intact Actor Log" not in closed


def test_epistemics_narration_keeps_captions_off_the_picture():
    import json
    import subprocess

    video = ROOT / "report" / "epistemics_trust_v1" / "slides" / "Epistemics_Trust_Narration.mp4"
    captions = ROOT / "report" / "epistemics_trust_v1" / "slides" / "Epistemics_Trust_Narration.vtt"
    probed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,codec_type",
            "-of", "json", str(video),
        ],
        check=True, capture_output=True, text=True,
    )
    codecs = [(row["codec_type"], row["codec_name"]) for row in json.loads(probed.stdout)["streams"]]
    assert codecs == [("video", "h264"), ("audio", "aac"), ("subtitle", "mov_text")]
    text = captions.read_text(encoding="utf-8")
    assert text.startswith("WEBVTT\n")
    assert "Jonathan" not in text
    assert "together with" not in text
    assert "their own denominator" not in text
    assert text.count("-->") == 38


def test_epistemics_slide_pdf_is_eight_pages():
    reader = PdfReader(str(PDF))
    assert len(reader.pages) == 8
    combined = "\n".join((page.extract_text() or "") for page in reader.pages)
    assert "An Intact Actor Log" in combined
    assert "Not added to the 48" in combined
    folded = " ".join(combined.split())
    assert "supported for the barrier and refuted for the original policy" in folded
    assert "SoundGate is a representation probe" in folded
    assert "Public commit ea58c7d contains that runner." in folded
    assert "d406f4e" not in combined
    assert "External empirical transfer remains untested" not in combined
