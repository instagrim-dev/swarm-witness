#!/usr/bin/env python3
"""Numeric rows for the canonical manuscript, taken from versioned results.

The manuscript stays the publication source. This renderer does not invent a
combined denominator and does not rewrite the historical comparison.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.comparison_score import summarize_method  # noqa: E402
from swarm_witness.native_comparison import competent_verdict  # noqa: E402


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


_TERMINAL_EVIDENCE = {
    ("applied", None): "Bound applied records, in order",
    ("not_entered", None): "Bound no-effect records",
    ("applied", "missing_mutation"): "Applied label, mutation missing",
    ("applied", "swapped"): "Artifact recorded before the mutation",
    ("applied", "wrong_call"): "Mutation and artifact bound to another call",
    ("not_entered", "write_present"): "No-effect label contradicted by a write",
    ("applied", "missing"): "Applied label, no terminal records",
    ("applied", "unrelated"): "Applied label and an unrelated tool record",
    ("not_entered", "missing"): "No-effect label, no terminal records",
}


def _ratio(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def _method_cells(summary: dict[str, int], *, cells: int) -> list[str]:
    unresolved = cells - int(summary["decisive_opportunities"])
    return [
        str(summary["unsupported_support"]),
        _ratio(int(summary["correct_decisive"]), int(summary["decisive_opportunities"])),
        _ratio(int(summary["correct_abstention"]), unresolved),
    ]


def _score_rows(rows: list[dict[str, object]]) -> dict[str, int]:
    return summarize_method(rows, truth_known=True)


def _historical_method_rows(repo_root: Path) -> dict[str, list[dict[str, object]]]:
    packets = json.loads(
        (repo_root / "experiments/effect_witness/historical_qualification_packets_v1.json").read_text(
            encoding="utf-8"
        )
    )
    warrants = yaml.safe_load(
        (repo_root / "experiments/effect_witness/native_warrants_v1.yaml").read_text(encoding="utf-8")
    )
    grouped: dict[str, list[dict[str, object]]] = {
        "Swarm Witness": [],
        "Invariant checker": [],
        "Always unresolved": [],
    }
    packet_root = repo_root / "evidence/effect_witness_v1/packets"
    for history_id, spec in warrants["histories"].items():
        for stage, warrant in spec["stages"].items():
            predicted_swarm = packets[history_id][stage]["property"]["child_verdicts"]["P_effect"]
            records = []
            for name in ("actor_records.jsonl", "service_records.jsonl"):
                path = packet_root / history_id / stage / name
                if not path.is_file():
                    continue
                records.extend(
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            predicted_strong = competent_verdict(history_id, records)["epistemic_status"]
            common = {
                "adjudicated": warrant,
                "proposition_holds": bool(spec["proposition_holds"]),
                "attributed_origin": "undetermined",
                "warranted_origin": "undetermined",
            }
            grouped["Swarm Witness"].append({**common, "predicted": predicted_swarm})
            grouped["Invariant checker"].append({**common, "predicted": predicted_strong})
            grouped["Always unresolved"].append({**common, "predicted": "unresolved"})
    return grouped


def _replay_method_rows(repo_root: Path, method: str) -> list[dict[str, object]]:
    document = json.loads(
        (repo_root / "report/bounded_comparison_v1/evaluator_replay_v2.json").read_text(encoding="utf-8")
    )
    return [
        {
            "predicted": row["predicted"],
            "adjudicated": row["adjudicated"],
            "proposition_holds": row["proposition_holds"],
            "attributed_origin": row.get("attributed_origin", "undetermined"),
            "warranted_origin": row.get("warranted_origin", "undetermined"),
        }
        for row in document["rows"]
        if row["method"] == method
    ]


def _effect_applied(state: dict) -> str:
    settlement = state.get("settlement")
    if not isinstance(settlement, dict):
        return "unresolved"
    if settlement.get("disposition") == "applied":
        return "supported"
    if settlement.get("disposition") == "not_entered":
        return "refuted"
    return "unresolved"


def _settlement_table(repo_root: Path) -> list[list[str]]:
    cases = yaml.safe_load(
        (repo_root / "experiments/r3/ledger_settlement_v1/cases.yaml").read_text(encoding="utf-8")
    )["cases"]
    evidence = {}
    outcome = {}
    for case in cases:
        settle = next(action for action in case["actions"] if str(action["op"]).startswith("settle_"))
        evidence[case["case_id"]] = settle.get("evidence")
        outcome[case["case_id"]] = settle["outcome"]
    rows = []
    run = repo_root / "evidence/r3/ledger_settlement_v1/2026-11-08-ledger-settlement-v1-controls"
    indexed = {}
    for arm in ("classical", "bmo"):
        for line in (run / f"{arm}.ndjson").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("op", "")).startswith("settle_"):
                indexed[(arm, row["case_id"])] = row
    for case_id in [case["case_id"] for case in cases]:
        classical = indexed[("classical", case_id)]
        bmo = indexed[("bmo", case_id)]
        if classical["disposition"] != bmo["disposition"] or _effect_applied(classical["state"]) != _effect_applied(bmo["state"]):
            raise ValueError(f"{case_id} arms disagree")
        label = _TERMINAL_EVIDENCE[(outcome[case_id], evidence[case_id])]
        settlement = classical["state"].get("settlement")
        raw_settlement = settlement["disposition"] if isinstance(settlement, dict) else classical["disposition"]
        settlement_cell = str(raw_settlement).replace("_", " ")
        rows.append([case_id, label, settlement_cell, _effect_applied(classical["state"])])
    return rows


def _representation_table(repo_root: Path) -> list[list[str]]:
    document = json.loads(
        (repo_root / "evidence/external_calibration_v1/representation_v2/result.json").read_text(
            encoding="utf-8"
        )
    )
    raws = [document["arms"]["raw_strong"], document["arms"]["raw_qualifier"]]
    composed = [document["arms"]["composed_strong"], document["arms"]["composed_qualifier"]]
    if any(arm["assessor"]["decisive_coverage"] != raws[0]["assessor"]["decisive_coverage"] for arm in raws):
        raise ValueError("raw assessor arms differ")
    if any(arm["warrant"]["decisive_coverage"] != raws[0]["warrant"]["decisive_coverage"] for arm in raws):
        raise ValueError("raw warrant arms differ")
    if any(arm["assessor"]["decisive_coverage"] != composed[0]["assessor"]["decisive_coverage"] for arm in composed):
        raise ValueError("composed assessor arms differ")
    if any(arm["warrant"]["unsupported_support"] != composed[0]["warrant"]["unsupported_support"] for arm in composed):
        raise ValueError("composed unsupported arms differ")
    raw = raws[0]
    adapted = composed[0]
    return [
        [
            "Raw, either method",
            raw["assessor"]["decisive_coverage"],
            raw["warrant"]["decisive_coverage"],
            str(raw["warrant"]["unsupported_support"]),
        ],
        [
            "Adapted, either method",
            adapted["assessor"]["decisive_coverage"],
            adapted["warrant"]["decisive_coverage"],
            str(adapted["warrant"]["unsupported_support"]),
        ],
    ]


def canonical_tables(repo_root: Path) -> dict[str, list[list[str]]]:
    """Manuscript table bodies read from retained rows, without a summed denominator."""
    repo_root = Path(repo_root)
    historical = _historical_method_rows(repo_root)
    current = _score_rows(_replay_method_rows(repo_root, "swarm_witness"))
    return {
        "Table 2": [
            ["Swarm Witness", *_method_cells(_score_rows(historical["Swarm Witness"]), cells=48)],
            ["Invariant checker", *_method_cells(_score_rows(historical["Invariant checker"]), cells=48)],
            ["Always unresolved", *_method_cells(_score_rows(historical["Always unresolved"]), cells=48)],
        ],
        "Table 2b": [
            ["Historical Swarm Witness", *_method_cells(_score_rows(historical["Swarm Witness"]), cells=48)],
            ["Current evaluator", *_method_cells(current, cells=48)],
        ],
        "Table 3": _settlement_table(repo_root),
        "Table 4": _representation_table(repo_root),
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
