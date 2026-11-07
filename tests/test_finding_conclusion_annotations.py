"""Every committed Finding with conclusion_class must match its label."""

from __future__ import annotations

import json
from pathlib import Path

from swarm_witness.conclusion_classes import assert_label_matches_conclusion

ROOT = Path(__file__).resolve().parents[1]


def test_all_findings_have_consistent_conclusion_class():
    findings = sorted((ROOT / "evidence").glob("*/findings/*.json"))
    assert findings
    for path in findings:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "conclusion_class" in data, f"{path} missing conclusion_class"
        assert_label_matches_conclusion(data["label"], data["conclusion_class"])
