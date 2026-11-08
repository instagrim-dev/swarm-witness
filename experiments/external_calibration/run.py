"""Score external-calibration packets under matched observation access.

    PYTHONPATH=src python experiments/external_calibration/run.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swarm_witness.incident_audit import (  # noqa: E402
    checklist_verdict,
    naive_verdict,
    swarm_witness_verdict,
)
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402

from r1_packets import SOURCE_REV as R1_REV  # noqa: E402
from r1_packets import build_packets as build_r1_packets  # noqa: E402
from r2_packets import SOURCE_REV as R2_REV  # noqa: E402
from r2_packets import build_packets as build_r2_packets  # noqa: E402
from r3_packets import SOURCE_REV as R3_REV  # noqa: E402
from r3_packets import build_packets as build_r3_packets  # noqa: E402
from lw_packets import SOURCE_REV as LW_REV  # noqa: E402
from lw_packets import build_packets as build_lw_packets  # noqa: E402

OUT = ROOT / "evidence" / "external_calibration_v1"
REPORT = ROOT / "report" / "external_calibration_v1"


def _epistemic(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("epistemic_status") or value.get("verdict") or "unresolved")
    return str(value)


def _score_classifiers(claim: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    naive = naive_verdict(claim, observations)
    weak = checklist_verdict(claim, observations)
    strong = strong_invariant_verdict(claim, observations)
    swarm = swarm_witness_verdict(claim, observations)
    return {
        "naive": {"verdict": naive if isinstance(naive, str) else _epistemic(naive)},
        "weak_checklist": {
            "verdict": weak if isinstance(weak, str) else _epistemic(weak)
        },
        "strong_invariant": {
            "verdict": _epistemic(strong),
            "reason": strong.get("reason") if isinstance(strong, dict) else None,
        },
        "swarm_witness": {
            "verdict": _epistemic(swarm),
            "reason": swarm.get("reason") if isinstance(swarm, dict) else None,
            "conclusion_class": swarm.get("conclusion_class")
            if isinstance(swarm, dict)
            else None,
        },
    }


def _category(predicted: str, warranted: str) -> str:
    if predicted == warranted:
        if predicted == "unresolved":
            return "justified_abstention"
        return "correct_decisive"
    if predicted == "supported" and warranted != "supported":
        return "unsupported_support"
    if predicted == "refuted" and warranted != "refuted":
        return "unsupported_refutation"
    if predicted == "unresolved" and warranted != "unresolved":
        return "missed_decisive"
    return "mismatch"


def _score_corpus(
    *,
    corpus: str,
    packets: list[dict[str, Any]],
    source_revision: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matrix_rows: list[dict[str, Any]] = []
    detail: list[dict[str, Any]] = []
    for packet in packets:
        claim = packet["claim"]
        observations = packet["observations"]
        warranted = packet["warranted_conclusion"]["status"]
        classifiers = _score_classifiers(claim, observations)
        native = packet["native_arms"]
        methods: dict[str, dict[str, Any]] = {
            **{name: {"verdict": arm["verdict"]} for name, arm in native.items()},
            **classifiers,
        }
        detail.append(
            {
                "corpus": corpus,
                "claim": claim,
                "assumptions": packet["assumptions"],
                "observations": observations,
                "native_arms": native,
                "warranted_conclusion": packet["warranted_conclusion"],
                "factual_outcome": packet["factual_outcome"],
                "row_refs": packet["row_refs"],
                "classifier_verdicts": classifiers,
            }
        )
        for method, payload in methods.items():
            predicted = payload["verdict"]
            matrix_rows.append(
                {
                    "corpus": corpus,
                    "claim_id": claim["id"],
                    "scenario": claim.get("scenario"),
                    "family": claim.get("family") or "",
                    "proposition": claim["proposition"],
                    "method": method,
                    "predicted": predicted,
                    "warranted": warranted,
                    "category": _category(predicted, warranted),
                    "factual_known": bool(packet["factual_outcome"].get("known")),
                    "source_revision": source_revision,
                    "warrant_basis": packet["warranted_conclusion"]["basis"],
                }
            )
    return matrix_rows, detail


def _method_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    methods = sorted({row["method"] for row in rows})
    out: dict[str, Any] = {}
    for method in methods:
        cells = [row for row in rows if row["method"] == method]
        counts = {
            "cells": len(cells),
            "unsupported_support": 0,
            "unsupported_refutation": 0,
            "justified_abstention": 0,
            "correct_decisive": 0,
            "missed_decisive": 0,
            "mismatch": 0,
        }
        for cell in cells:
            key = cell["category"]
            counts[key] = counts.get(key, 0) + 1
        out[method] = counts
    return out


def _write_report(
    path: Path,
    *,
    title: str,
    intro: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    lines = [
        f"# {title}",
        "",
        intro,
        "",
        f"Claims: {summary.get('claim_count')}",
        f"Matrix rows: {summary.get('matrix_rows')}",
        "",
        "## Calibration statements",
        "",
    ]
    for statement in summary.get("calibration_statements") or []:
        lines.append(f"- {statement}")
    lines.extend(
        [
            "",
            "## Per-method tallies (vs warranted conclusion)",
            "",
            "| Method | Cells | Unsupported support | Unsupported refutation | Justified abstention | Correct decisive | Missed decisive |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for method, counts in summary["methods"].items():
        lines.append(
            f"| `{method}` | {counts['cells']} | {counts.get('unsupported_support', 0)} | "
            f"{counts.get('unsupported_refutation', 0)} | {counts.get('justified_abstention', 0)} | "
            f"{counts.get('correct_decisive', 0)} | {counts.get('missed_decisive', 0)} |"
        )
    lines.extend(
        [
            "",
            "## Per-case matrix",
            "",
            "| Corpus | Claim | Scenario | Method | Predicted | Warranted | Category |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['corpus']} | `{row['claim_id']}` | {row['scenario']} | `{row['method']}` | "
            f"{row['predicted']} | {row['warranted']} | {row['category']} |"
        )
    lines.extend(
        [
            "",
            "## Level label consequence",
            "",
            "Do **not** treat an unqualified global `strong` as calibrated. Prefer "
            "source-grounded profile labels (attribution / recovery / availability / "
            "transaction / reproduction scope) when the corresponding matrix supports them.",
            "",
            "Retrospective calibration only; `transfer_claim` remains false until "
            "fresh or held-out families are scored.",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    r2_packets = build_r2_packets()
    r1_packets = build_r1_packets()
    r3_packets = build_r3_packets()
    lw_packets = build_lw_packets()
    r2_rows, r2_detail = _score_corpus(
        corpus="evidencegraph_r2", packets=r2_packets, source_revision=R2_REV
    )
    r1_rows, r1_detail = _score_corpus(
        corpus="soundgate_r1", packets=r1_packets, source_revision=R1_REV
    )
    r3_rows, r3_detail = _score_corpus(
        corpus="bmo_l1", packets=r3_packets, source_revision=R3_REV
    )
    lw_rows, lw_detail = _score_corpus(
        corpus="lesswrong_reproduction", packets=lw_packets, source_revision=LW_REV
    )
    all_rows = r2_rows + r1_rows + r3_rows + lw_rows
    all_detail = r2_detail + r1_detail + r3_detail + lw_detail

    attr_rows = [
        row
        for row in r2_rows
        if row["claim_id"].startswith("EG-R2-ATTR-")
        and row["method"]
        in {
            "strong_invariant",
            "swarm_witness",
            "evidencegraph_safer_independent_binding",
        }
    ]
    sg_restrict = [
        row
        for row in r1_rows
        if row["claim_id"].startswith("SG-R1-RESTRICT-")
        and row["method"] in {"strong_invariant", "swarm_witness", "soundgate_policy_barrier"}
    ]
    sg_avail = [
        row
        for row in r1_rows
        if row["claim_id"].startswith("SG-R1-AVAIL-")
        and row["method"] in {"strong_invariant", "swarm_witness", "soundgate_policy_barrier"}
    ]

    def match_count(rows: list[dict[str, Any]], method: str) -> int:
        return sum(
            1 for row in rows if row["method"] == method and row["predicted"] == row["warranted"]
        )

    summary = {
        "retrospective_calibration": True,
        "transfer_claim": False,
        "claim_count": len({row["claim_id"] for row in all_rows}),
        "matrix_rows": len(all_rows),
        "corpora": {
            "evidencegraph_r2": {
                "source_revision": R2_REV,
                "claims": len(r2_packets),
                "rows": len(r2_rows),
            },
            "soundgate_r1": {
                "source_revision": R1_REV,
                "claims": len(r1_packets),
                "rows": len(r1_rows),
            },
            "bmo_l1": {
                "source_revision": R3_REV,
                "claims": len(r3_packets),
                "rows": len(r3_rows),
            },
            "lesswrong_reproduction": {
                "source_revision": LW_REV,
                "claims": len(lw_packets),
                "rows": len(lw_rows),
            },
        },
        "methods": _method_summary(all_rows),
        "profiles": {
            "evidencegraph_attribution": {
                "attr_claim_count": len({row["claim_id"] for row in attr_rows}),
                "strong_matches_warranted": match_count(attr_rows, "strong_invariant"),
                "swarm_matches_warranted": match_count(attr_rows, "swarm_witness"),
                "safer_native_matches_warranted": match_count(
                    attr_rows, "evidencegraph_safer_independent_binding"
                ),
            },
            "soundgate_restriction": {
                "claim_count": len({row["claim_id"] for row in sg_restrict}),
                "strong_matches_warranted": match_count(sg_restrict, "strong_invariant"),
                "swarm_matches_warranted": match_count(sg_restrict, "swarm_witness"),
                "barrier_native_matches_warranted": match_count(
                    sg_restrict, "soundgate_policy_barrier"
                ),
            },
            "soundgate_availability": {
                "claim_count": len({row["claim_id"] for row in sg_avail}),
                "strong_matches_warranted": match_count(sg_avail, "strong_invariant"),
                "swarm_matches_warranted": match_count(sg_avail, "swarm_witness"),
                "barrier_native_matches_warranted": match_count(
                    sg_avail, "soundgate_policy_barrier"
                ),
            },
            "bmo_transaction_ledger": {
                "claim_count": len({row["claim_id"] for row in r3_rows}),
                "strong_matches_warranted": match_count(r3_rows, "strong_invariant"),
                "swarm_matches_warranted": match_count(r3_rows, "swarm_witness"),
                "bmo_native_matches_warranted": match_count(r3_rows, "bmo_l1_native"),
            },
            "lesswrong_reproduction_scope": {
                "claim_count": len({row["claim_id"] for row in lw_rows}),
                "strong_matches_warranted": match_count(lw_rows, "strong_invariant"),
                "swarm_matches_warranted": match_count(lw_rows, "swarm_witness"),
                "scope_native_matches_warranted": match_count(
                    lw_rows, "lesswrong_scope_discipline"
                ),
            },
        },
        "calibration_statements": [
            (
                "EvidenceGraph attribution: strong_invariant and swarm_witness match "
                "warranted Junejo safer discipline on all ATTR focal packets "
                f"({match_count(attr_rows, 'strong_invariant')}/"
                f"{len({row['claim_id'] for row in attr_rows})})."
            ),
            (
                "SoundGate: restriction and availability are separate profiles. "
                "Barrier native policy matches both; strict matches restriction but "
                "fails availability — a no-prohibited-effects-only 'strong' label "
                "would erase that difference."
            ),
            (
                "BMO L1: ledger first-edit properties can be supported while "
                "execution settlement remains unresolved under the declared scope."
            ),
            (
                "LessWrong: reproduction release/census can be supported while "
                "original-incident certification, unsatisfied upgrade slots, and "
                "environment-identity claims stay unresolved — evaluate released "
                "evidence at its actual scope."
            ),
            (
                "Unqualified global 'strong' remains undefined; use profile labels "
                "when earned (attribution / restriction+availability / ledger / "
                "reproduction_scope)."
            ),
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    (OUT / "packets.json").write_text(
        json.dumps(all_detail, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT / "matrix.json").write_text(
        json.dumps({"rows": all_rows, "summary": summary}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fieldnames = list(all_rows[0].keys()) if all_rows else []
    with (OUT / "matrix.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    intro = (
        "Retrospective calibration of the frozen classifier ladder against "
        "prior retained disciplines (EvidenceGraph R2 attribution; SoundGate R1 "
        "restriction vs availability; BMO L1 ledger vs non-settlement; LessWrong "
        "reproduction scope). Not a held-out transfer claim. Not agreement with "
        "the authored strong_invariant baseline alone."
    )
    _write_report(
        OUT / "REPORT.md",
        title=(
            "External calibration v1 — EvidenceGraph + SoundGate + BMO L1 + LessWrong"
        ),
        intro=intro,
        rows=all_rows,
        summary=summary,
    )
    _write_report(
        REPORT / "MATRIX.md",
        title=(
            "External calibration v1 — EvidenceGraph + SoundGate + BMO L1 + LessWrong"
        ),
        intro=intro,
        rows=all_rows,
        summary=summary,
    )
    (REPORT / "R2_MATRIX.md").write_text(
        "# Moved\n\nSee `report/external_calibration_v1/MATRIX.md`.\n",
        encoding="utf-8",
    )

    print(json.dumps({k: summary[k] for k in summary if k != "methods"}, indent=2))
    print(f"wrote {OUT}")
    print(f"wrote {REPORT / 'MATRIX.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
