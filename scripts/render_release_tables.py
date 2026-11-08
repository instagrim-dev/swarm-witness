#!/usr/bin/env python3
"""Numeric rows for the canonical manuscript, taken from versioned results.

The manuscript stays the publication source. This renderer does not invent a
combined denominator and does not rewrite the historical comparison.
"""

from __future__ import annotations

import json
from pathlib import Path


def release_figures(repo_root: Path) -> dict[str, object]:
    repo_root = Path(repo_root)
    tables = (repo_root / "report" / "bounded_comparison_v1" / "TABLES.md").read_text(encoding="utf-8")
    native = _table_row(tables, "swarm_witness | 48 | 11 |")
    current = _table_row(tables, "swarm_witness | 48 | 0 |")
    contracts = json.loads(
        (repo_root / "report" / "architecture_contracts_v1" / "cases.json").read_text(encoding="utf-8")
    )
    representation = json.loads(
        (
            repo_root
            / "evidence"
            / "external_calibration_v1"
            / "representation_v2"
            / "result.json"
        ).read_text(encoding="utf-8")
    )
    challenge_v1 = json.loads(
        (
            repo_root
            / "evidence"
            / "effect_witness_v1"
            / "native_projection_challenge_v1"
            / "ledger.json"
        ).read_text(encoding="utf-8")
    )
    challenge_v2 = json.loads(
        (
            repo_root
            / "evidence"
            / "effect_witness_v1"
            / "native_projection_challenge_v2"
            / "ledger.json"
        ).read_text(encoding="utf-8")
    )
    raw = representation["arms"]["raw_qualifier"]
    composed = representation["arms"]["composed_qualifier"]
    return {
        "compare_only": contracts["compare_only"],
        "live_model_edit": contracts["live_model_edit"],
        "ledger_case_count": contracts["ledger_case_count"],
        "ledger_step_count": contracts["ledger_step_count"],
        "initial_settlement_case_count": contracts["initial_settlement_case_count"],
        "controls_case_count": contracts["controls_case_count"],
        "historical_row": native,
        "current_row": current,
        "representation_packet_count": representation["packet_count"],
        "representation_overlap": representation["overlap_with_130_packet_corpus"],
        "built_corpus_count": representation["built_corpus_count"],
        "raw_assessor": raw["assessor"]["decisive_coverage"],
        "raw_warrant": raw["warrant"]["decisive_coverage"],
        "raw_unsupported": raw["warrant"]["unsupported_support"],
        "composed_assessor": composed["assessor"]["decisive_coverage"],
        "composed_warrant": composed["warrant"]["decisive_coverage"],
        "composed_unsupported": composed["warrant"]["unsupported_support"],
        "challenge_v1_count": challenge_v1["case_count"],
        "challenge_v2_count": challenge_v2["case_count"],
        "challenge_v1_spoofed": _historical_status(challenge_v1, "sink-spoofed"),
        "challenge_v2_spoofed": _epistemic_status(challenge_v2, "sink-spoofed"),
        "challenge_v2_rejections": sum(
            row["execution_status"] == "rejected" for row in challenge_v2["rows"]
        ),
    }


def render_markdown(repo_root: Path) -> str:
    figures = release_figures(repo_root)
    return "\n".join(
        [
            "# Release tables",
            "",
            "These rows are read from versioned results. They are not a summed denominator.",
            "",
            f"- Ledger cases: {figures['ledger_case_count']}. Ledger steps: {figures['ledger_step_count']}.",
            f"- Initial settlement cases: {figures['initial_settlement_case_count']}. Controls run: {figures['controls_case_count']}.",
            f"- Historical native row: {figures['historical_row']}",
            f"- Current evaluator row: {figures['current_row']}",
            f"- Representation overlap: {figures['representation_overlap']} of {figures['built_corpus_count']}.",
            f"- Raw assessor/warrant/unsupported: {figures['raw_assessor']} / {figures['raw_warrant']} / {figures['raw_unsupported']}.",
            f"- Composed assessor/warrant/unsupported: {figures['composed_assessor']} / {figures['composed_warrant']} / {figures['composed_unsupported']}.",
            f"- Challenge counts stay {figures['challenge_v1_count']} and {figures['challenge_v2_count']}.",
            f"- Spoofed sink: historical {figures['challenge_v1_spoofed']}; later check {figures['challenge_v2_spoofed']}.",
            f"- Later challenge rejections: {figures['challenge_v2_rejections']}.",
            "",
        ]
    )


def _table_row(text: str, marker: str) -> str:
    for line in text.splitlines():
        if marker in line:
            return line.strip()
    raise ValueError(marker)


def _historical_status(document: dict, needle: str) -> str:
    for row in document["rows"]:
        if needle in row["case_id"]:
            status = row["swarm_witness"]
            if isinstance(status, dict):
                return status["epistemic_status"]
            return status
    raise ValueError(needle)


def _epistemic_status(document: dict, needle: str) -> str:
    for row in document["rows"]:
        if needle in row["case_id"]:
            return row["epistemic_status"]
    raise ValueError(needle)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = root / "report" / "release_tables_v1.md"
    destination.write_text(render_markdown(root), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
