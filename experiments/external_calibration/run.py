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
                "author_scope_reading": packet.get("author_scope_reading"),
                "evidence_translation": packet.get("evidence_translation"),
                "cross_policy_reference": packet.get("cross_policy_reference"),
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


def _match_count(rows: list[dict[str, Any]], method: str) -> int:
    return sum(
        1 for row in rows if row["method"] == method and row["predicted"] == row["warranted"]
    )


def _sg_native_method(claim_id: str) -> str:
    if claim_id.endswith("-original") or "-original" in claim_id:
        return "soundgate_policy_original"
    if claim_id.endswith("-strict") or "-strict" in claim_id:
        return "soundgate_policy_strict"
    if claim_id.endswith("-barrier") or "-barrier" in claim_id:
        return "soundgate_policy_barrier"
    raise KeyError(f"unrecognized SoundGate claim_id={claim_id!r}")


def _write_profile_labels(path: Path, summary: dict[str, Any]) -> None:
    profiles = summary["profiles"]
    transfer = summary.get("transfer") or {}
    lines = [
        "# Earned profile labels (retrospective)",
        "",
        "Source-grounded labels from `report/external_calibration_v1/MATRIX.md`.",
        "An unqualified global `strong` is not earned.",
        "",
        "Agreement with an **authored scoring warrant** is distinct from agreement "
        "with a **retained native prior method**. LessWrong has no scored external "
        "native method in-repo; `warrants_v1` is the scoring key only.",
        "",
        f"`transfer_claim`: `{summary.get('transfer_claim')}`",
        "",
        "| Profile label | Status | Evidence |",
        "|---|---|---|",
    ]

    def status(ok: bool) -> str:
        return "earned" if ok else "not earned"

    eg = profiles["evidencegraph_attribution"]
    warrant_ok = (
        eg["strong_matches_warranted"] == eg["attr_claim_count"]
        and eg["swarm_matches_warranted"] == eg["attr_claim_count"]
    )
    native_ok = (
        eg["strong_matches_native_safer"] == eg["attr_claim_count"]
        and eg["swarm_matches_native_safer"] == eg["attr_claim_count"]
    )
    lines.append(
        f"| `matches_evidencegraph_attr_warrants_on_r2_seed0` | {status(warrant_ok)} | "
        f"strong/swarm vs warrant {eg['strong_matches_warranted']}/"
        f"{eg['attr_claim_count']} |"
    )
    lines.append(
        f"| `matches_evidencegraph_safer_native_verdicts_on_r2_seed0` | "
        f"{status(native_ok)} | strong/swarm vs safer native "
        f"{eg['strong_matches_native_safer']}/{eg['attr_claim_count']}; "
        f"safer vs warrant {eg['safer_native_matches_warranted']}/"
        f"{eg['attr_claim_count']} (false-exclusivity premise divergence) |"
    )

    barrier = profiles["soundgate_barrier_joint"]
    barrier_ok = (
        barrier["barrier_native_matches_warranted"] == barrier["claim_count"]
        and barrier["strong_matches_warranted"] == barrier["claim_count"]
        and barrier["swarm_matches_warranted"] == barrier["claim_count"]
    )
    lines.append(
        f"| `matches_soundgate_barrier_restriction_and_availability` | "
        f"{status(barrier_ok)} | matching-policy arms only; barrier "
        f"restrict+avail {barrier['barrier_native_matches_warranted']}/"
        f"{barrier['claim_count']} |"
    )

    bmo = profiles["bmo_transaction_ledger"]
    bmo_ok = (
        bmo["strong_matches_warranted"] == bmo["claim_count"]
        and bmo["swarm_matches_warranted"] == bmo["claim_count"]
    )
    lines.append(
        f"| `matches_bmo_l1_ledger_and_non_settlement_sufficiency` | "
        f"{status(bmo_ok)} | {bmo['strong_matches_warranted']}/"
        f"{bmo['claim_count']} including evidentiary NOT-EXECUTION-SETTLEMENT |"
    )

    lw = profiles["lesswrong_reproduction_scope"]
    lw_ok = (
        lw["strong_matches_warranted"] == lw["claim_count"]
        and lw["swarm_matches_warranted"] == lw["claim_count"]
    )
    lines.append(
        f"| `matches_author_lw_scope_warrants` | {status(lw_ok)} | "
        f"strong/swarm vs author warrants_v1 {lw['strong_matches_warranted']}/"
        f"{lw['claim_count']}; no external LW native method scored |"
    )

    t_ok = bool(transfer.get("earned"))
    lines.extend(
        [
            f"| `transfers_evidencegraph_attribution_across_r2_seeds` | "
            f"{status(t_ok)} | held-out seeds {transfer.get('held_out_seeds')}: "
            f"strong/swarm vs warrant "
            f"{transfer.get('strong_matches_warranted')}/"
            f"{transfer.get('attr_claim_count')}; vs safer native "
            f"{transfer.get('strong_matches_native_safer')}/"
            f"{transfer.get('attr_claim_count')} |",
            "",
            "Naive / weak_checklist remain shortcut ablations "
            f"(unsupported_support naive="
            f"{summary['methods']['naive']['unsupported_support']}, "
            f"weak="
            f"{summary['methods']['weak_checklist']['unsupported_support']}).",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    r2_packets = build_r2_packets(seed=0)
    r1_packets = build_r1_packets()
    r3_packets = build_r3_packets()
    lw_packets = build_lw_packets()
    transfer_packets = build_r2_packets(seed=1) + build_r2_packets(seed=2)
    # Transfer probe uses ATTR family only (possession≠attribution discipline).
    transfer_attr_packets = [
        packet
        for packet in transfer_packets
        if packet["claim"]["id"].startswith("EG-R2-ATTR-")
    ]

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
    transfer_rows, transfer_detail = _score_corpus(
        corpus="evidencegraph_r2_transfer_seeds",
        packets=transfer_attr_packets,
        source_revision=R2_REV,
    )
    all_rows = r2_rows + r1_rows + r3_rows + lw_rows + transfer_rows
    all_detail = r2_detail + r1_detail + r3_detail + lw_detail + transfer_detail

    attr_claim_ids = sorted(
        {row["claim_id"] for row in r2_rows if row["claim_id"].startswith("EG-R2-ATTR-")}
    )

    def _verdict_map(rows: list[dict[str, Any]], method: str) -> dict[str, str]:
        return {
            row["claim_id"]: row["predicted"]
            for row in rows
            if row["method"] == method
        }

    attr_strong = _verdict_map(r2_rows, "strong_invariant")
    attr_swarm = _verdict_map(r2_rows, "swarm_witness")
    attr_safer = _verdict_map(r2_rows, "evidencegraph_safer_independent_binding")
    attr_warrant = {
        row["claim_id"]: row["warranted"]
        for row in r2_rows
        if row["claim_id"].startswith("EG-R2-ATTR-") and row["method"] == "strong_invariant"
    }

    def _agree(left: dict[str, str], right: dict[str, str], ids: list[str]) -> int:
        return sum(1 for cid in ids if left.get(cid) == right.get(cid))

    sg_restrict = [
        row
        for row in r1_rows
        if row["claim_id"].startswith("SG-R1-RESTRICT-")
        and row["method"]
        in {
            "strong_invariant",
            "swarm_witness",
            _sg_native_method(row["claim_id"]),
        }
    ]
    sg_avail = [
        row
        for row in r1_rows
        if row["claim_id"].startswith("SG-R1-AVAIL-")
        and row["method"]
        in {
            "strong_invariant",
            "swarm_witness",
            _sg_native_method(row["claim_id"]),
        }
    ]
    sg_barrier = [
        row
        for row in r1_rows
        if row["claim_id"] in {"SG-R1-RESTRICT-barrier", "SG-R1-AVAIL-barrier"}
        and row["method"]
        in {"strong_invariant", "swarm_witness", "soundgate_policy_barrier"}
    ]
    transfer_ids = sorted({row["claim_id"] for row in transfer_rows})
    transfer_strong_map = _verdict_map(transfer_rows, "strong_invariant")
    transfer_swarm_map = _verdict_map(transfer_rows, "swarm_witness")
    transfer_safer_map = _verdict_map(
        transfer_rows, "evidencegraph_safer_independent_binding"
    )
    transfer_warrant = {
        row["claim_id"]: row["warranted"]
        for row in transfer_rows
        if row["method"] == "strong_invariant"
    }
    transfer_claim_count = len(transfer_ids)
    transfer_strong = _agree(transfer_strong_map, transfer_warrant, transfer_ids)
    transfer_swarm = _agree(transfer_swarm_map, transfer_warrant, transfer_ids)
    transfer_strong_native = _agree(transfer_strong_map, transfer_safer_map, transfer_ids)
    transfer_swarm_native = _agree(transfer_swarm_map, transfer_safer_map, transfer_ids)
    transfer_earned = (
        transfer_claim_count > 0
        and transfer_strong == transfer_claim_count
        and transfer_swarm == transfer_claim_count
    )

    summary = {
        "retrospective_calibration": True,
        "transfer_claim": transfer_earned,
        "claim_count": len({row["claim_id"] for row in all_rows}),
        "matrix_rows": len(all_rows),
        "corpora": {
            "evidencegraph_r2": {
                "source_revision": R2_REV,
                "claims": len(r2_packets),
                "rows": len(r2_rows),
                "seed": 0,
                "role": "calibration",
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
            "evidencegraph_r2_transfer_seeds": {
                "source_revision": R2_REV,
                "claims": len(transfer_attr_packets),
                "rows": len(transfer_rows),
                "seeds": [1, 2],
                "role": "held_out_transfer_probe",
                "family": "EG-R2-ATTR",
            },
        },
        "methods": _method_summary(all_rows),
        "profiles": {
            "evidencegraph_attribution": {
                "attr_claim_count": len(attr_claim_ids),
                "strong_matches_warranted": _agree(
                    attr_strong, attr_warrant, attr_claim_ids
                ),
                "swarm_matches_warranted": _agree(
                    attr_swarm, attr_warrant, attr_claim_ids
                ),
                "strong_matches_native_safer": _agree(
                    attr_strong, attr_safer, attr_claim_ids
                ),
                "swarm_matches_native_safer": _agree(
                    attr_swarm, attr_safer, attr_claim_ids
                ),
                "safer_native_matches_warranted": _agree(
                    attr_safer, attr_warrant, attr_claim_ids
                ),
                "premise_failure_claim": "EG-R2-ATTR-false-exclusivity",
                "note": (
                    "Warrant agreement and native-safer agreement are separate. "
                    "false_exclusivity: safer supports under a false premise; "
                    "warrant stays unresolved."
                ),
            },
            "soundgate_restriction": {
                "claim_count": len({row["claim_id"] for row in sg_restrict}),
                "strong_matches_warranted": _match_count(sg_restrict, "strong_invariant"),
                "swarm_matches_warranted": _match_count(sg_restrict, "swarm_witness"),
            },
            "soundgate_availability": {
                "claim_count": len({row["claim_id"] for row in sg_avail}),
                "strong_matches_warranted": _match_count(sg_avail, "strong_invariant"),
                "swarm_matches_warranted": _match_count(sg_avail, "swarm_witness"),
            },
            "soundgate_barrier_joint": {
                "claim_count": len({row["claim_id"] for row in sg_barrier}),
                "strong_matches_warranted": _match_count(sg_barrier, "strong_invariant"),
                "swarm_matches_warranted": _match_count(sg_barrier, "swarm_witness"),
                "barrier_native_matches_warranted": _match_count(
                    sg_barrier, "soundgate_policy_barrier"
                ),
            },
            "bmo_transaction_ledger": {
                "claim_count": len({row["claim_id"] for row in r3_rows}),
                "strong_matches_warranted": _match_count(r3_rows, "strong_invariant"),
                "swarm_matches_warranted": _match_count(r3_rows, "swarm_witness"),
                "bmo_native_matches_warranted": _match_count(r3_rows, "bmo_l1_native"),
            },
            "lesswrong_reproduction_scope": {
                "claim_count": len({row["claim_id"] for row in lw_rows}),
                "strong_matches_warranted": _match_count(lw_rows, "strong_invariant"),
                "swarm_matches_warranted": _match_count(lw_rows, "swarm_witness"),
                "external_native_method_scored": False,
                "note": (
                    "warrants_v1 is the author scoring key. "
                    "reconstructed_narrative_overread is an ablation only."
                ),
            },
        },
        "transfer": {
            "held_out_seeds": [1, 2],
            "family": "EG-R2-ATTR",
            "attr_claim_count": transfer_claim_count,
            "strong_matches_warranted": transfer_strong,
            "swarm_matches_warranted": transfer_swarm,
            "strong_matches_native_safer": transfer_strong_native,
            "swarm_matches_native_safer": transfer_swarm_native,
            "earned": transfer_earned,
            "note": (
                "Frozen classifiers on EvidenceGraph ATTR packets from seeds 1–2. "
                "Warrant agreement is separate from native-safer agreement. "
                "Not a new held-out project family."
            ),
        },
        "calibration_statements": [
            (
                "EvidenceGraph attribution (seed 0): report warrant agreement and "
                "native-safer agreement separately — "
                f"strong vs warrant {_agree(attr_strong, attr_warrant, attr_claim_ids)}/"
                f"{len(attr_claim_ids)}; strong vs safer native "
                f"{_agree(attr_strong, attr_safer, attr_claim_ids)}/{len(attr_claim_ids)}; "
                f"safer vs warrant {_agree(attr_safer, attr_warrant, attr_claim_ids)}/"
                f"{len(attr_claim_ids)}. false_exclusivity is the premise-failure "
                "divergence under matched observation access."
            ),
            (
                "SoundGate: only the matching-policy native arm is scored against "
                "each claim. Cross-policy tallies are reference-only. Barrier "
                "matches restriction and availability on its own claims; strict "
                "matches restriction but fails availability."
            ),
            (
                "BMO L1: ledger first-edit properties can be supported while the "
                "evidentiary claim that those traces establish execution settlement "
                "is refuted under declared scope."
            ),
            (
                "LessWrong: classifiers are scored against author warrants_v1. "
                "No independently specified LessWrong executable method is scored. "
                "Environment identity is refuted given disclosed differences; "
                "certification and upgrade-slot claims stay unresolved."
            ),
            (
                "Transfer probe (EG ATTR seeds 1–2): "
                + (
                    "earned on warrant agreement "
                    f"({transfer_strong}/{transfer_claim_count})."
                    if transfer_earned
                    else (
                        "not earned on full warrant agreement "
                        f"({transfer_strong}/{transfer_claim_count}); "
                        f"native-safer agreement "
                        f"{transfer_strong_native}/{transfer_claim_count}."
                    )
                )
            ),
            (
                "Unqualified global 'strong' remains undefined; use earned "
                "profile labels in PROFILE_LABELS.md."
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
        "prior retained disciplines (EvidenceGraph R2 seed-0 attribution; "
        "SoundGate R1 restriction vs availability; BMO L1 ledger vs "
        "non-settlement; LessWrong reproduction scope), plus a held-out "
        "EvidenceGraph ATTR transfer probe on seeds 1–2. Not agreement with "
        "the authored strong_invariant baseline alone."
    )
    _write_report(
        OUT / "REPORT.md",
        title=(
            "External calibration v1 — EvidenceGraph + SoundGate + BMO L1 + "
            "LessWrong + transfer probe"
        ),
        intro=intro,
        rows=all_rows,
        summary=summary,
    )
    _write_report(
        REPORT / "MATRIX.md",
        title=(
            "External calibration v1 — EvidenceGraph + SoundGate + BMO L1 + "
            "LessWrong + transfer probe"
        ),
        intro=intro,
        rows=all_rows,
        summary=summary,
    )
    _write_profile_labels(OUT / "PROFILE_LABELS.md", summary)
    _write_profile_labels(REPORT / "PROFILE_LABELS.md", summary)
    (REPORT / "R2_MATRIX.md").write_text(
        "# Moved\n\nSee `report/external_calibration_v1/MATRIX.md`.\n",
        encoding="utf-8",
    )

    print(json.dumps({k: summary[k] for k in summary if k != "methods"}, indent=2))
    print(f"wrote {OUT}")
    print(f"wrote {REPORT / 'MATRIX.md'}")
    print(f"wrote {REPORT / 'PROFILE_LABELS.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
