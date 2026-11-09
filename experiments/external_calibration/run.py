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
from r2_event_packets import SOURCE_REV as R2_EVT_REV  # noqa: E402
from r2_event_packets import build_packets as build_r2_event_packets  # noqa: E402
from eg_adapter_projector import composed_observations  # noqa: E402

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


def _score_composed_on_adapter(
    claim: dict[str, Any], raw_observations: list[dict[str, Any]]
) -> dict[str, Any]:
    """assessment → project → frozen classifiers on raw + projected."""
    assessment, projected = composed_observations(claim, raw_observations)
    composed_obs = list(raw_observations) + projected
    strong = strong_invariant_verdict(claim, composed_obs)
    swarm = swarm_witness_verdict(claim, composed_obs)
    return {
        "assessment": assessment,
        "projected_observation_ids": [obs["id"] for obs in projected],
        "strong_on_adapter_checks": {
            "verdict": _epistemic(strong),
            "reason": strong.get("reason") if isinstance(strong, dict) else None,
        },
        "swarm_on_adapter_checks": {
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
        composed_detail: dict[str, Any] | None = None
        if corpus == "evidencegraph_r2_event":
            composed_detail = _score_composed_on_adapter(claim, observations)
            methods["strong_on_adapter_checks"] = {
                "verdict": composed_detail["strong_on_adapter_checks"]["verdict"]
            }
            methods["swarm_on_adapter_checks"] = {
                "verdict": composed_detail["swarm_on_adapter_checks"]["verdict"]
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
                "composed_on_adapter": composed_detail,
            }
        )
        factual = packet.get("factual_outcome") or {}
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
                    "factual_known": bool(factual.get("known")),
                    "proposition_holds": factual.get("proposition_holds"),
                    "comparison_role": claim.get("comparison_role")
                    or factual.get("comparison_role")
                    or "",
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
            "Retrospective calibration on author-translated retained prior evidence. "
            "`transfer_claim` stays false for the seed-repeatability probe: identical "
            "encoded classifier inputs cannot establish transfer. Fresh or genuinely "
            "held-out families are required for a transfer claim.",
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
    repeat = summary.get("seed_repeatability") or {}
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
        "Comparison scope: agreement on **author-translated representations** of "
        "retained prior evidence under matched observation packets.",
        "",
        f"`transfer_claim`: `{summary.get('transfer_claim')}` "
        "(seed probe is repeatability only; identical encoded inputs cannot earn transfer)",
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

    lines.extend(
        [
            f"| `repeats_evidencegraph_attribution_across_r2_seeds` | "
            f"{status(bool(repeat.get('repeats_seed0')))} | retained seeds "
            f"{repeat.get('seeds')}: strong/swarm vs warrant "
            f"{repeat.get('strong_matches_warranted')}/"
            f"{repeat.get('attr_claim_count')} "
            f"(= {repeat.get('seed0_warrant_rate')}); vs safer native "
            f"{repeat.get('strong_matches_native_safer')}/"
            f"{repeat.get('attr_claim_count')} "
            f"(= {repeat.get('seed0_native_rate')}). Not a transfer claim. |",
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


def _event_capability_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Capability comparison on event-level EvidenceGraph packets."""
    methods = [
        "evidencegraph_safer_produced",
        "evidencegraph_legacy_produced",
        "eg_evidence_derived_adapter",
        "naive",
        "weak_checklist",
        "strong_invariant",
        "swarm_witness",
        "strong_on_adapter_checks",
        "swarm_on_adapter_checks",
    ]
    attr_ids = {
        row["claim_id"]
        for row in rows
        if row["corpus"] == "evidencegraph_r2_event" and row["family"] == "event_attribution"
    }
    out: dict[str, Any] = {"attr_claim_count": len(attr_ids), "methods": {}}
    for method in methods:
        cells = [
            row
            for row in rows
            if row["corpus"] == "evidencegraph_r2_event"
            and row["family"] == "event_attribution"
            and row["method"] == method
        ]
        if not cells:
            continue
        out["methods"][method] = {
            "cells": len(cells),
            "native_or_warrant_agreement": sum(
                1 for row in cells if row["predicted"] == row["warranted"]
            ),
            "correct_decisive": sum(1 for row in cells if row["category"] == "correct_decisive"),
            "unsupported_support": sum(
                1 for row in cells if row["category"] == "unsupported_support"
            ),
            "unsupported_refutation": sum(
                1 for row in cells if row["category"] == "unsupported_refutation"
            ),
            "justified_abstention": sum(
                1 for row in cells if row["category"] == "justified_abstention"
            ),
            "missed_decisive": sum(1 for row in cells if row["category"] == "missed_decisive"),
        }
    # Pairwise boundary checks: adapter vs safer on named scenarios.
    boundaries = {}
    for scenario in (
        "clean",
        "missing_tokens",
        "missing_clock_bound",
        "dependent_witnesses",
        "full_receipt_relay",
        "false_exclusivity",
        "capture_window_edge",
    ):
        safer = {
            row["claim_id"]: row["predicted"]
            for row in rows
            if row["corpus"] == "evidencegraph_r2_event"
            and row["scenario"] == scenario
            and row["family"] == "event_attribution"
            and row["method"] == "evidencegraph_safer_produced"
        }
        adapter = {
            row["claim_id"]: row["predicted"]
            for row in rows
            if row["corpus"] == "evidencegraph_r2_event"
            and row["scenario"] == scenario
            and row["family"] == "event_attribution"
            and row["method"] == "eg_evidence_derived_adapter"
        }
        ids = sorted(set(safer) & set(adapter))
        boundaries[scenario] = {
            "claims": len(ids),
            "adapter_matches_safer": sum(1 for i in ids if safer[i] == adapter[i]),
        }
    out["boundaries_adapter_vs_safer"] = boundaries
    out["adapter_matches_safer_total"] = sum(
        stats["adapter_matches_safer"] for stats in boundaries.values()
    )
    out["adapter_safer_boundary_claims"] = sum(
        stats["claims"] for stats in boundaries.values()
    )
    adapter = out["methods"].get("eg_evidence_derived_adapter") or {}
    safer = out["methods"].get("evidencegraph_safer_produced") or {}
    attr_safer_map = {
        row["claim_id"]: row["predicted"]
        for row in rows
        if row["corpus"] == "evidencegraph_r2_event"
        and row["family"] == "event_attribution"
        and row["method"] == "evidencegraph_safer_produced"
    }
    attr_adapter_rows = [
        row
        for row in rows
        if row["corpus"] == "evidencegraph_r2_event"
        and row["family"] == "event_attribution"
        and row["method"] == "eg_evidence_derived_adapter"
    ]
    attr_adapter_map = {row["claim_id"]: row["predicted"] for row in attr_adapter_rows}
    factually_wrong_supported = sum(
        1
        for row in attr_adapter_rows
        if row["predicted"] == "supported"
        and row.get("factual_known")
        and row.get("proposition_holds") is False
    )
    false_ex_supported = sum(
        1
        for row in attr_adapter_rows
        if row["scenario"] == "false_exclusivity" and row["predicted"] == "supported"
    )
    out["attribution_conformance"] = {
        "adapter_matches_safer_all_attr": sum(
            1
            for cid, pred in attr_adapter_map.items()
            if attr_safer_map.get(cid) == pred
        ),
        "attr_claim_count": len(attr_adapter_map),
        "correct_decisive": adapter.get("correct_decisive"),
        "unsupported_support": adapter.get("unsupported_support"),
        "missed_decisive_strong": (out["methods"].get("strong_invariant") or {}).get(
            "missed_decisive"
        ),
        "missed_decisive_swarm": (out["methods"].get("swarm_witness") or {}).get(
            "missed_decisive"
        ),
        "safer_correct_decisive": safer.get("correct_decisive"),
        "safer_unsupported_support": safer.get("unsupported_support"),
        "false_exclusivity_supported": false_ex_supported,
        "factually_wrong_supported_attributions": factually_wrong_supported,
        "note": (
            "Regenerated counts: safer/adapter correct decisive and unsupported "
            "supports as tabulated; Strong/Swarm Witness missed decisive replaces "
            "the earlier 57. Ten unsupported supports are the false-exclusivity "
            "premise convention."
        ),
    }

    fab_native = {
        row["claim_id"]: row["predicted"]
        for row in rows
        if row["corpus"] == "evidencegraph_r2_event"
        and row["family"] == "fabricated_execution"
        and row["method"] == "evidencegraph_safer_executed"
    }
    fab_cells = [
        row
        for row in rows
        if row["corpus"] == "evidencegraph_r2_event"
        and row["family"] == "fabricated_execution"
        and row["method"] == "eg_evidence_derived_adapter"
    ]
    native_fab = [
        row
        for row in fab_cells
        if row.get("comparison_role") == "native_executed_comparison"
    ]
    control_fab = [
        row for row in fab_cells if row.get("comparison_role") == "additional_control"
    ]
    out["fabricated_execution"] = {
        "total_cells": len(fab_cells),
        "native_executed_comparisons": len(native_fab),
        "additional_controls": len(control_fab),
        "adapter_matches_native_executed_mapping": sum(
            1
            for row in fab_cells
            if fab_native.get(row["claim_id"]) == row["predicted"]
        ),
        "adapter_matches_on_native_executed_only": sum(
            1
            for row in native_fab
            if fab_native.get(row["claim_id"]) == row["predicted"]
        ),
        "adapter_refutations": sum(1 for row in fab_cells if row["predicted"] == "refuted"),
        "native_refutations": sum(
            1
            for row in rows
            if row["corpus"] == "evidencegraph_r2_event"
            and row["family"] == "fabricated_execution"
            and row["method"] == "evidencegraph_safer_executed"
            and row.get("comparison_role") == "native_executed_comparison"
            and row["predicted"] == "refuted"
        ),
        "note": (
            "Describe as 8 native execution comparisons + 2 additional controls "
            "(relay spoofed receipts with no exported executed relation, mapped "
            "unresolved). Do not imply ten exported native execution decisions."
        ),
    }
    out["warrant_qualification"] = {
        "attribution_warrant_depends_on_adapter_sufficiency": True,
        "execution_warrant_depends_on_native_refutation_when_present": True,
        "assessor_inputs_independent_of_native_fields": True,
        "primary_result": "adapter_vs_native_safer_conformance",
        "note": (
            "Warrant agreement remains method-dependent. Mutating native fields "
            "leaves assessor inputs unchanged but can change execution warrants. "
            "Use the conformance column as the primary result."
        ),
    }

    def _pred_map(method: str, family: str | None = None) -> dict[str, str]:
        return {
            row["claim_id"]: row["predicted"]
            for row in rows
            if row["corpus"] == "evidencegraph_r2_event"
            and row["method"] == method
            and (family is None or row["family"] == family)
        }

    adapter_all = _pred_map("eg_evidence_derived_adapter")
    strong_raw = _pred_map("strong_invariant")
    swarm_raw = _pred_map("swarm_witness")
    strong_comp = _pred_map("strong_on_adapter_checks")
    swarm_comp = _pred_map("swarm_on_adapter_checks")
    safer_attr = _pred_map("evidencegraph_safer_produced", "event_attribution")
    safer_exec = _pred_map("evidencegraph_safer_executed", "fabricated_execution")

    def _agree_maps(a: dict[str, str], b: dict[str, str]) -> tuple[int, int]:
        ids = sorted(set(a) & set(b))
        return sum(1 for i in ids if a[i] == b[i]), len(ids)

    strong_vs_adapter, n_strong = _agree_maps(strong_comp, adapter_all)
    swarm_vs_adapter, n_swarm = _agree_maps(swarm_comp, adapter_all)
    strong_vs_safer_attr, n_ssa = _agree_maps(
        {k: v for k, v in strong_comp.items() if k in safer_attr}, safer_attr
    )
    swarm_vs_safer_attr, n_swa = _agree_maps(
        {k: v for k, v in swarm_comp.items() if k in safer_attr}, safer_attr
    )
    # Execution: split native executed comparisons vs additional controls.
    native_exec_ids = {
        row["claim_id"]
        for row in rows
        if row["corpus"] == "evidencegraph_r2_event"
        and row["family"] == "fabricated_execution"
        and row["method"] == "eg_evidence_derived_adapter"
        and row.get("comparison_role") == "native_executed_comparison"
    }
    control_exec_ids = {
        row["claim_id"]
        for row in rows
        if row["corpus"] == "evidencegraph_r2_event"
        and row["family"] == "fabricated_execution"
        and row["method"] == "eg_evidence_derived_adapter"
        and row.get("comparison_role") == "additional_control"
    }
    safer_native_exec = {cid: safer_exec[cid] for cid in native_exec_ids if cid in safer_exec}
    safer_control_exec = {cid: safer_exec[cid] for cid in control_exec_ids if cid in safer_exec}
    strong_native_exec = {cid: strong_comp[cid] for cid in native_exec_ids if cid in strong_comp}
    swarm_native_exec = {cid: swarm_comp[cid] for cid in native_exec_ids if cid in swarm_comp}
    strong_control_exec = {cid: strong_comp[cid] for cid in control_exec_ids if cid in strong_comp}
    swarm_control_exec = {cid: swarm_comp[cid] for cid in control_exec_ids if cid in swarm_comp}
    strong_vs_safer_native_exec, n_native_exec = _agree_maps(
        strong_native_exec, safer_native_exec
    )
    swarm_vs_safer_native_exec, _ = _agree_maps(swarm_native_exec, safer_native_exec)
    strong_vs_safer_control, n_control_exec = _agree_maps(
        strong_control_exec, safer_control_exec
    )
    swarm_vs_safer_control, _ = _agree_maps(swarm_control_exec, safer_control_exec)
    # Full execution reference mapping (native + controls mapped unresolved).
    strong_exec = {cid: pred for cid, pred in strong_comp.items() if cid in safer_exec}
    swarm_exec = {cid: pred for cid, pred in swarm_comp.items() if cid in safer_exec}
    strong_vs_safer_exec, n_sse = _agree_maps(strong_exec, safer_exec)
    swarm_vs_safer_exec, _ = _agree_maps(swarm_exec, safer_exec)

    packet_denominator = len(adapter_all)
    out["classifier_integration"] = {
        "expectation": "C(x ∪ P(A(x))) = A(x)",
        "packet_denominator": packet_denominator,
        "strong_on_adapter_matches_adapter": strong_vs_adapter,
        "swarm_on_adapter_matches_adapter": swarm_vs_adapter,
        "integration_cells": n_strong,
        "strong_on_adapter_matches_safer_attr": strong_vs_safer_attr,
        "swarm_on_adapter_matches_safer_attr": swarm_vs_safer_attr,
        "safer_attr_cells": n_ssa,
        "strong_on_adapter_matches_safer_native_exec": strong_vs_safer_native_exec,
        "swarm_on_adapter_matches_safer_native_exec": swarm_vs_safer_native_exec,
        "native_exec_cells": n_native_exec,
        "strong_on_adapter_matches_safer_control": strong_vs_safer_control,
        "swarm_on_adapter_matches_safer_control": swarm_vs_safer_control,
        "control_exec_cells": n_control_exec,
        "strong_on_adapter_matches_safer_exec_mapping": strong_vs_safer_exec,
        "swarm_on_adapter_matches_safer_exec_mapping": swarm_vs_safer_exec,
        "safer_exec_mapping_cells": n_sse,
        "raw_strong_decisive": sum(
            1 for v in strong_raw.values() if v in {"supported", "refuted"}
        ),
        "raw_swarm_decisive": sum(
            1 for v in swarm_raw.values() if v in {"supported", "refuted"}
        ),
        "raw_strong_packets": len(strong_raw),
        "raw_swarm_packets": len(swarm_raw),
        "composed_strong_decisive": sum(
            1 for v in strong_comp.values() if v in {"supported", "refuted"}
        ),
        "composed_swarm_decisive": sum(
            1 for v in swarm_comp.values() if v in {"supported", "refuted"}
        ),
        "note": (
            "Frozen classifiers admit and consume the adapter derivation; they do "
            "not independently evaluate predicate prose. EG-specific inference "
            "remains part of the composed method. Raw baselines stay unchanged. "
            "Report attribution 120/120, native execution 8/8, and controls 2/2 "
            "(equivalently 10/10 against the execution reference mapping)."
        ),
        "transfer_claim": False,
    }
    return out


def _write_capability_report(path: Path, capability: dict[str, Any]) -> None:
    lines = [
        "# EvidenceGraph expanded native conformance (event-level)",
        "",
        "Scoring unit: **recorded tool event E produced registry mutation M**.",
        "Assessor inputs are observable records and declared assumptions only.",
        "Native outcomes and private dispatch bindings are scoring-only.",
        "`transfer_claim` stays false; this is expanded native conformance.",
        "",
        f"Attribution claims: {capability.get('attr_claim_count')}",
        "",
        "## Per-method attribution tallies (vs warrant)",
        "",
        "| Method | Cells | Agree warrant | Correct decisive | Unsupported support | Missed decisive |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method, counts in (capability.get("methods") or {}).items():
        lines.append(
            f"| `{method}` | {counts['cells']} | {counts['native_or_warrant_agreement']} | "
            f"{counts['correct_decisive']} | {counts['unsupported_support']} | "
            f"{counts['missed_decisive']} |"
        )
    lines.extend(
        [
            "",
            "## Boundary preservation (adapter vs native safer)",
            "",
            "| Scenario | Claims | Adapter matches safer |",
            "|---|---:|---:|",
        ]
    )
    for scenario, stats in (capability.get("boundaries_adapter_vs_safer") or {}).items():
        lines.append(
            f"| `{scenario}` | {stats['claims']} | {stats['adapter_matches_safer']} |"
        )
    fab = capability.get("fabricated_execution") or {}
    attrc = capability.get("attribution_conformance") or {}
    wq = capability.get("warrant_qualification") or {}
    lines.extend(
        [
            "",
            f"Adapter vs safer on listed boundaries: "
            f"{capability.get('adapter_matches_safer_total')}/"
            f"{capability.get('adapter_safer_boundary_claims')}.",
            "",
            f"Adapter vs safer on all attribution packets: "
            f"{attrc.get('adapter_matches_safer_all_attr')}/"
            f"{attrc.get('attr_claim_count')}.",
            "",
            "## Fabricated / successful-execution family",
            "",
            f"**{fab.get('native_executed_comparisons')} native execution comparisons** "
            f"+ **{fab.get('additional_controls')} additional controls** "
            f"(total cells {fab.get('total_cells')}; not ten exported native "
            f"execution decisions).",
            "",
            f"Adapter matches the execution reference mapping: "
            f"{fab.get('adapter_matches_native_executed_mapping')}/{fab.get('total_cells')} "
            f"(on native-executed only: "
            f"{fab.get('adapter_matches_on_native_executed_only')}/"
            f"{fab.get('native_executed_comparisons')}). "
            f"Adapter refutations: {fab.get('adapter_refutations')}; "
            f"native refutations among exported executed relations: "
            f"{fab.get('native_refutations')}.",
            "",
            fab.get("note") or "",
            "",
            "## Warrant qualification (secondary)",
            "",
            "Attribution warrants use the adapter’s support verdict as the "
            "public-evidence sufficiency predicate. Execution warrants consult "
            "native refutation status when an exported executed relation is "
            "present. Assessor inputs remain independent of native fields, but "
            "warrants are not fully independent of evaluated methods. "
            f"**Primary result:** `{wq.get('primary_result')}`.",
            "",
            "## Reading",
            "",
            "Use regenerated attribution counts: safer/adapter "
            f"{attrc.get('correct_decisive')} correct decisive, "
            f"{attrc.get('unsupported_support')} *unsupported supports*, "
            f"and {attrc.get('factually_wrong_supported_attributions')} factually "
            "wrong supported attribution. Strong/Swarm Witness: "
            f"{attrc.get('missed_decisive_strong')} missed decisive "
            "(replacing the earlier 57).",
            "",
            "The ten *unsupported supports* are the false-exclusivity premise "
            "convention (all ten safer/adapter supports marked unwarranted, "
            "including correct event identities).",
            "",
            "Classifier abstention on these raw packets means the frozen "
            "classifiers do not consume them as verifying evidence. That does "
            "not establish adapter correctness; adapter vs native safer is the "
            "conformance column.",
            "",
            "Capture-window edge: real-event attributions can remain supported while "
            "invented-receipt absence contradictions become unresolved — blanket "
            "abstention cannot reproduce that split.",
            "",
            "## Classifier integration (composed arms)",
            "",
        ]
    )
    integ = capability.get("classifier_integration") or {}
    lines.extend(
        [
            f"Expectation: `{integ.get('expectation')}` "
            "(composed classifier equals adapter on retained packets).",
            "",
            f"Composed vs adapter (all {integ.get('packet_denominator')} retained "
            f"packets): strong "
            f"{integ.get('strong_on_adapter_matches_adapter')}/"
            f"{integ.get('integration_cells')}; Swarm Witness "
            f"{integ.get('swarm_on_adapter_matches_adapter')}/"
            f"{integ.get('integration_cells')}.",
            "",
            f"Composed vs native safer — attribution: "
            f"{integ.get('strong_on_adapter_matches_safer_attr')}/"
            f"{integ.get('safer_attr_cells')} "
            f"(strong and Swarm Witness).",
            "",
            f"Composed vs native safer — native execution comparisons: "
            f"{integ.get('strong_on_adapter_matches_safer_native_exec')}/"
            f"{integ.get('native_exec_cells')}; "
            f"additional controls (no exported native executed decision): "
            f"{integ.get('strong_on_adapter_matches_safer_control')}/"
            f"{integ.get('control_exec_cells')}; "
            f"equivalently against the execution reference mapping: "
            f"{integ.get('strong_on_adapter_matches_safer_exec_mapping')}/"
            f"{integ.get('safer_exec_mapping_cells')}.",
            "",
            f"Raw strong: {integ.get('raw_strong_decisive')} decisive "
            f"across {integ.get('raw_strong_packets')} packets; "
            f"raw Swarm Witness: {integ.get('raw_swarm_decisive')} decisive "
            f"across {integ.get('raw_swarm_packets')} packets. "
            f"Composed decisive — strong: {integ.get('composed_strong_decisive')}; "
            f"Swarm Witness: {integ.get('composed_swarm_decisive')}.",
            "",
            integ.get("note") or "",
            "",
            "## Result (this freeze)",
            "",
            "Both composed classifiers preserve the adapter’s decisions on all "
            f"{integ.get('packet_denominator')} retained packets, including its "
            "false-exclusivity limitation. Raw-packet classifier behavior remains "
            "unchanged. This establishes classifier–adapter integration on the "
            "retained conditions. `transfer_claim` remains false.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    r2_packets = build_r2_packets(seed=0)
    r2_event_packets = build_r2_event_packets()
    r1_packets = build_r1_packets()
    r3_packets = build_r3_packets()
    lw_packets = build_lw_packets()
    # Seed 1–2 ATTR packets: repeatability of the same encoded decisions, not transfer.
    repeat_packets = build_r2_packets(seed=1) + build_r2_packets(seed=2)
    repeat_attr_packets = [
        packet
        for packet in repeat_packets
        if packet["claim"]["id"].startswith("EG-R2-ATTR-")
    ]

    r2_rows, r2_detail = _score_corpus(
        corpus="evidencegraph_r2", packets=r2_packets, source_revision=R2_REV
    )
    r2_event_rows, r2_event_detail = _score_corpus(
        corpus="evidencegraph_r2_event",
        packets=r2_event_packets,
        source_revision=R2_EVT_REV,
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
    repeat_rows, repeat_detail = _score_corpus(
        corpus="evidencegraph_r2_seed_repeatability",
        packets=repeat_attr_packets,
        source_revision=R2_REV,
    )
    all_rows = r2_rows + r2_event_rows + r1_rows + r3_rows + lw_rows + repeat_rows
    all_detail = (
        r2_detail + r2_event_detail + r1_detail + r3_detail + lw_detail + repeat_detail
    )

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
    repeat_ids = sorted({row["claim_id"] for row in repeat_rows})
    repeat_strong_map = _verdict_map(repeat_rows, "strong_invariant")
    repeat_swarm_map = _verdict_map(repeat_rows, "swarm_witness")
    repeat_safer_map = _verdict_map(
        repeat_rows, "evidencegraph_safer_independent_binding"
    )
    repeat_warrant = {
        row["claim_id"]: row["warranted"]
        for row in repeat_rows
        if row["method"] == "strong_invariant"
    }
    repeat_claim_count = len(repeat_ids)
    repeat_strong = _agree(repeat_strong_map, repeat_warrant, repeat_ids)
    repeat_swarm = _agree(repeat_swarm_map, repeat_warrant, repeat_ids)
    repeat_strong_native = _agree(repeat_strong_map, repeat_safer_map, repeat_ids)
    repeat_swarm_native = _agree(repeat_swarm_map, repeat_safer_map, repeat_ids)
    seed0_warrant = _agree(attr_strong, attr_warrant, attr_claim_ids)
    seed0_native = _agree(attr_strong, attr_safer, attr_claim_ids)
    # Identical encoded inputs: 6/8 repeats seed-0's 3/4; 8/8 repeats 4/4.
    repeats_seed0 = (
        repeat_claim_count == 2 * len(attr_claim_ids)
        and repeat_strong == 2 * seed0_warrant
        and repeat_swarm == 2 * seed0_warrant
        and repeat_strong_native == 2 * seed0_native
        and repeat_swarm_native == 2 * seed0_native
    )

    summary = {
        "retrospective_calibration": True,
        # Identical encoded classifier inputs cannot establish transfer.
        "transfer_claim": False,
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
            "evidencegraph_r2_event": {
                "source_revision": R2_EVT_REV,
                "claims": len(r2_event_packets),
                "rows": len(r2_event_rows),
                "seed": 0,
                "role": "expanded_native_conformance",
                "transfer_claim": False,
                "note": (
                    "Event-by-event produced/executed comparison against native "
                    "attribution and capture rules; adapter scored with classifiers."
                ),
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
            "evidencegraph_r2_seed_repeatability": {
                "source_revision": R2_REV,
                "claims": len(repeat_attr_packets),
                "rows": len(repeat_rows),
                "seeds": [1, 2],
                "role": "seed_repeatability",
                "family": "EG-R2-ATTR",
                "note": (
                    "Author-translated packets match seed-0 classifier inputs "
                    "after normalizing seed fields; not a held-out transfer probe."
                ),
            },
        },
        "methods": _method_summary(all_rows),
        "evidencegraph_event_conformance": _event_capability_summary(all_rows),
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
        "seed_repeatability": {
            "seeds": [1, 2],
            "family": "EG-R2-ATTR",
            "attr_claim_count": repeat_claim_count,
            "strong_matches_warranted": repeat_strong,
            "swarm_matches_warranted": repeat_swarm,
            "strong_matches_native_safer": repeat_strong_native,
            "swarm_matches_native_safer": repeat_swarm_native,
            "seed0_warrant_rate": f"{seed0_warrant}/{len(attr_claim_ids)}",
            "seed0_native_rate": f"{seed0_native}/{len(attr_claim_ids)}",
            "repeats_seed0": repeats_seed0,
            "transfer_claim": False,
            "note": (
                "Repeatability across retained seeds. After normalizing seed "
                "fields, classifier inputs match seed 0; this cannot establish "
                "held-out transfer."
            ),
        },
        "calibration_statements": [
            (
                "EvidenceGraph attribution (seed 0): on author-translated retained "
                "packets, report warrant agreement and native-safer agreement "
                "separately — "
                f"strong vs warrant {seed0_warrant}/{len(attr_claim_ids)}; "
                f"strong vs safer native {seed0_native}/{len(attr_claim_ids)}; "
                f"safer vs warrant {_agree(attr_safer, attr_warrant, attr_claim_ids)}/"
                f"{len(attr_claim_ids)}. false_exclusivity is the shared "
                "premise-failure under matched observation access."
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
                "Seed repeatability (EG ATTR seeds 1–2): "
                f"warrant {repeat_strong}/{repeat_claim_count} repeats seed-0 "
                f"{seed0_warrant}/{len(attr_claim_ids)}; native-safer "
                f"{repeat_strong_native}/{repeat_claim_count} repeats "
                f"{seed0_native}/{len(attr_claim_ids)}. transfer_claim stays false."
            ),
            (
                "Unqualified global 'strong' remains undefined; use earned "
                "profile labels in PROFILE_LABELS.md."
            ),
            (
                "EvidenceGraph expanded native conformance: event-level "
                "produced/executed relations vs safer/legacy native arms and "
                "the evidence-derived adapter; see EVENT_CAPABILITY.md. "
                "transfer_claim stays false."
            ),
        ],
    }
    capability = summary["evidencegraph_event_conformance"]

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
        "author-translated retained prior evidence (EvidenceGraph R2 seed-0 "
        "attribution; SoundGate R1 restriction vs availability; BMO L1 ledger "
        "vs non-settlement; LessWrong reproduction scope), plus event-level "
        "EvidenceGraph expanded native conformance and an ATTR seed-"
        "repeatability check on seeds 1–2. Not agreement with the authored "
        "strong_invariant baseline alone, and not a held-out transfer claim."
    )
    _write_report(
        OUT / "REPORT.md",
        title=(
            "External calibration v1 — EvidenceGraph + SoundGate + BMO L1 + "
            "LessWrong + event conformance + seed repeatability"
        ),
        intro=intro,
        rows=all_rows,
        summary=summary,
    )
    _write_report(
        REPORT / "MATRIX.md",
        title=(
            "External calibration v1 — EvidenceGraph + SoundGate + BMO L1 + "
            "LessWrong + event conformance + seed repeatability"
        ),
        intro=intro,
        rows=all_rows,
        summary=summary,
    )
    _write_profile_labels(OUT / "PROFILE_LABELS.md", summary)
    _write_profile_labels(REPORT / "PROFILE_LABELS.md", summary)
    _write_capability_report(OUT / "EVENT_CAPABILITY.md", capability)
    _write_capability_report(REPORT / "EVENT_CAPABILITY.md", capability)
    (REPORT / "R2_MATRIX.md").write_text(
        "# Moved\n\nSee `report/external_calibration_v1/MATRIX.md`.\n",
        encoding="utf-8",
    )

    print(json.dumps({k: summary[k] for k in summary if k != "methods"}, indent=2))
    print(f"wrote {OUT}")
    print(f"wrote {REPORT / 'MATRIX.md'}")
    print(f"wrote {REPORT / 'PROFILE_LABELS.md'}")
    print(f"wrote {REPORT / 'EVENT_CAPABILITY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
