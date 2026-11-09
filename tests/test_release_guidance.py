"""Reviewers can find the affirmative native ledger run without reading a failed identity check as the result."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AFFIRMATIVE = "evidence/r3/ledger_claim_v1/2026-11-08-ledger-bridge-requalify"
HISTORICAL = "evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2"


def test_reproduction_guides_name_the_requalified_native_run():
    texts = {
        "evidence/ACCESS.md": (ROOT / "evidence/ACCESS.md").read_text(encoding="utf-8"),
        "report/bounded_comparison_v1/REPLAY.md": (
            ROOT / "report/bounded_comparison_v1/REPLAY.md"
        ).read_text(encoding="utf-8"),
        "experiments/r3/ledger_claim_v1/README.md": (
            ROOT / "experiments/r3/ledger_claim_v1/README.md"
        ).read_text(encoding="utf-8"),
    }
    for name, text in texts.items():
        assert AFFIRMATIVE in text, name
        assert HISTORICAL in text, name
        assert "source-identity rejection" in text, name
    access = texts["evidence/ACCESS.md"]
    assert access.index(AFFIRMATIVE) < access.index(HISTORICAL)
