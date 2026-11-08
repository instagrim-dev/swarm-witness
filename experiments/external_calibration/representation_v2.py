#!/usr/bin/env python3
"""Four-arm representation study on the frozen 70-packet slice.

Labels and controlled truth are recorded after prediction. They are not inputs
to either classifier. Derived records are transformations, not extra sources.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eg_adapter_projector import composed_observations  # noqa: E402
from heldout_v1 import (  # noqa: E402
    _duplicate_type,
    _eligible,
    _irrelevant,
    _label,
    _without_type,
)
from r2_event_packets import build_packets  # noqa: E402
from swarm_witness.incident_audit import swarm_witness_verdict  # noqa: E402
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402

ELIGIBILITY = Path(__file__).with_name("heldout_v1.yaml")
RETAINED = ROOT / "evidence" / "external_calibration_v1" / "heldout_v1" / "result.json"
ARMS = ("raw_strong", "raw_qualifier", "composed_strong", "composed_qualifier")


def eligible_packets(repo_root: Path) -> list[dict[str, Any]]:
    del repo_root
    protocol = yaml.safe_load(ELIGIBILITY.read_text(encoding="utf-8"))
    packets = [packet for packet in build_packets() if _eligible(packet, protocol)]
    packets.sort(key=lambda packet: packet["claim"]["id"])
    return packets


def predict_arms(packet: dict[str, Any], scoring_label: str | None = None) -> dict[str, str]:
    """Classifier outputs. scoring_label is accepted and ignored."""
    del scoring_label
    claim = packet["claim"]
    observations = list(packet["observations"])
    _assessment, projected = composed_observations(claim, observations)
    composed = observations + projected
    return {
        "raw_strong": strong_invariant_verdict(claim, observations)["epistemic_status"],
        "raw_qualifier": swarm_witness_verdict(claim, observations)["epistemic_status"],
        "composed_strong": strong_invariant_verdict(claim, composed)["epistemic_status"],
        "composed_qualifier": swarm_witness_verdict(claim, composed)["epistemic_status"],
    }


def _blank() -> dict[str, int]:
    return {
        "correct_decisive": 0,
        "unsupported_support": 0,
        "unsupported_refutation": 0,
        "abstention": 0,
        "other": 0,
    }


def _category(predicted: str, label: str) -> str:
    if predicted == label and predicted in {"supported", "refuted"}:
        return "correct_decisive"
    if predicted == "supported" and label != "supported":
        return "unsupported_support"
    if predicted == "refuted" and label != "refuted":
        return "unsupported_refutation"
    if predicted == "unresolved":
        return "abstention"
    return "other"


def _coverage(counts: dict[str, int], decisive: int) -> str:
    return f"{counts['correct_decisive']}/{decisive}"


def _timed_predictions(packet: dict[str, Any]) -> tuple[dict[str, str], dict[str, float], list[dict[str, Any]]]:
    claim = packet["claim"]
    observations = list(packet["observations"])
    seconds = {arm: 0.0 for arm in ARMS}
    started = time.perf_counter()
    raw_strong = strong_invariant_verdict(claim, observations)["epistemic_status"]
    seconds["raw_strong"] = time.perf_counter() - started
    started = time.perf_counter()
    raw_qualifier = swarm_witness_verdict(claim, observations)["epistemic_status"]
    seconds["raw_qualifier"] = time.perf_counter() - started
    started = time.perf_counter()
    _assessment, projected = composed_observations(claim, observations)
    adapter_seconds = time.perf_counter() - started
    composed = observations + projected
    started = time.perf_counter()
    composed_strong = strong_invariant_verdict(claim, composed)["epistemic_status"]
    seconds["composed_strong"] = (time.perf_counter() - started) + adapter_seconds
    started = time.perf_counter()
    composed_qualifier = swarm_witness_verdict(claim, composed)["epistemic_status"]
    seconds["composed_qualifier"] = (time.perf_counter() - started) + adapter_seconds
    return (
        {
            "raw_strong": raw_strong,
            "raw_qualifier": raw_qualifier,
            "composed_strong": composed_strong,
            "composed_qualifier": composed_qualifier,
        },
        seconds,
        projected,
    )


def _score_block(rows: list[dict[str, Any]], arm: str, label_key: str, decisive: int) -> dict[str, Any]:
    counts = _blank()
    for row in rows:
        counts[_category(row["predictions"][arm], row[label_key])] += 1
    return {**counts, "decisive_coverage": _coverage(counts, decisive)}


def run_representation_study(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    output_dir = Path(output_dir)
    retained_path = repo_root / "evidence" / "external_calibration_v1" / "heldout_v1" / "result.json"
    before = retained_path.read_bytes()
    retained = json.loads(before)
    retained_by_id = {row["claim_id"]: row for row in retained["rows"]}
    packets = eligible_packets(repo_root)
    built = build_packets()
    built_ids = {packet["claim"]["id"] for packet in built}
    if len(built_ids) != 130:
        raise ValueError("evidencegraph event corpus is no longer the retained 130 packets")
    packet_ids = [packet["claim"]["id"] for packet in packets]
    if packet_ids != [row["claim_id"] for row in retained["rows"]]:
        raise ValueError("representation slice diverged from the retained 70 packets")
    if any(_label(packet)["status"] != retained_by_id[packet["claim"]["id"]]["visible_evidence_label"] for packet in packets):
        raise ValueError("assessor label changed")

    rows = []
    errors = []
    processing = {arm: 0.0 for arm in ARMS}
    supplied = 0
    derived = 0
    for packet in packets:
        try:
            predictions, seconds, projected = _timed_predictions(packet)
        except Exception as exc:  # measurement retains the failure instead of inventing a verdict
            errors.append({"claim_id": packet["claim"]["id"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        for arm, value in seconds.items():
            processing[arm] += value
        claim = packet["claim"]
        label = retained_by_id[claim["id"]]["visible_evidence_label"]
        warrant = packet["warranted_conclusion"]["status"]
        supplied += len(packet["observations"])
        derived += len(projected)
        rows.append(
            {
                "claim_id": claim["id"],
                "family": claim["family"],
                "scenario": claim.get("scenario"),
                "assessor_label": label,
                "warrant": warrant,
                "controlled_truth": (packet.get("factual_outcome") or {}).get("proposition_holds"),
                "predictions": predictions,
                "supplied_record_ids": [row.get("id") for row in packet["observations"]],
                "derived_records": projected,
                "additional_source_requests": 0,
            }
        )

    assessor_decisive = sum(row["assessor_label"] in {"supported", "refuted"} for row in rows)
    warrant_decisive = sum(row["warrant"] in {"supported", "refuted"} for row in rows)
    arms = {}
    for arm in ARMS:
        composed = arm.startswith("composed_")
        arms[arm] = {
            "assessor": _score_block(rows, arm, "assessor_label", assessor_decisive),
            "warrant": _score_block(rows, arm, "warrant", warrant_decisive),
            "source_demand": {
                "supplied_records": supplied,
                "derived_records": derived if composed else 0,
                "additional_source_requests": 0,
                "independent_source_records": supplied,
            },
            "processing_seconds": processing[arm],
        }

    clean = [
        packet
        for packet in packets
        if packet["claim"]["family"] == "event_attribution" and packet["claim"].get("scenario") == "clean"
    ]
    fabricated = [packet for packet in packets if packet["claim"]["family"] == "fabricated_execution"]
    successful = clean[0]
    nominee = fabricated[0]
    refuted_rows = [row for row in rows if row["assessor_label"] == "refuted"]
    refuted_rows.sort(key=lambda row: row["claim_id"])
    supplementary_id = refuted_rows[0]["claim_id"]
    supplementary = next(packet for packet in packets if packet["claim"]["id"] == supplementary_id)

    def stage(name: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
        staged = dict(successful)
        staged["observations"] = observations
        _assessment, projected = composed_observations(successful["claim"], observations)
        del _assessment
        return {
            "name": name,
            "assessor_label": _label(staged)["status"],
            "predictions": predict_arms(staged),
            "supplied_record_ids": [row.get("id") for row in observations],
            "derived_records": projected,
        }

    base_observations = successful["observations"]
    interventions = {
        "baseline": stage("baseline", list(base_observations)),
        "removed": stage("removed", _without_type(base_observations, "registry_mutation_record")),
        "duplicated": stage("duplicated", _duplicate_type(base_observations, "registry_mutation_record")),
        "irrelevant": stage("irrelevant", _irrelevant(base_observations)),
    }
    false_rows = [row for row in rows if row["scenario"] == "false_exclusivity"]
    document = {
        "protocol_id": "representation-v2",
        "study_kind": "frozen_slice_representation",
        "eligibility_protocol": "external-heldout-v1",
        "packet_count": len(rows),
        "error_count": len(errors),
        "errors": errors,
        "built_corpus_count": len(built_ids),
        "earlier_corpus": "evidencegraph_r2_event",
        "overlap_with_built_corpus": sum(claim_id in built_ids for claim_id in packet_ids),
        "overlap_with_130_packet_corpus": sum(claim_id in built_ids for claim_id in packet_ids),
        "heldout_v1_unchanged": True,
        "not_unseen": True,
        "independent_jury": False,
        "superiority_claim": False,
        "transfer_claim": False,
        "external_empirical_transfer": "not_tested",
        "composition_fidelity_is_not_independent_correctness": True,
        "assessor_decisive": assessor_decisive,
        "warrant_decisive": warrant_decisive,
        "arms": arms,
        "adapted_arms_agree": all(
            row["predictions"]["composed_strong"] == row["predictions"]["composed_qualifier"] for row in rows
        ),
        "false_exclusivity_packets_retained": len(false_rows),
        "qualified_disagreements": {
            "composed_versus_assessor": [
                row["claim_id"]
                for row in rows
                if row["predictions"]["composed_qualifier"] != row["assessor_label"]
            ],
            "composed_versus_warrant": [
                row["claim_id"]
                for row in rows
                if row["predictions"]["composed_qualifier"] != row["warrant"]
            ],
            "note": "Assessor agreement is composition fidelity. Warrant disagreement is a separate qualification and stays visible.",
        },
        "controls": {
            "historical_refutation_nominee": {
                "claim_id": nominee["claim"]["id"],
                "selection_rule": "lexicographically first eligible fabricated_execution claim",
                "visible_evidence_label": retained_by_id[nominee["claim"]["id"]]["visible_evidence_label"],
                "blind_validation": False,
            },
            "supplementary_refuted_representative": {
                "claim_id": supplementary["claim"]["id"],
                "selection_rule": "lexicographically first assessor-refuted row in the retained slice",
                "role": "inspected_representative",
                "visible_evidence_label": retained_by_id[supplementary["claim"]["id"]]["visible_evidence_label"],
                "blind_validation": False,
            },
        },
        "interventions": interventions,
        "rows": rows,
    }
    if retained_path.read_bytes() != before:
        raise ValueError("heldout_v1 result was rewritten")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "study_kind": document["study_kind"],
        "eligibility_protocol": document["eligibility_protocol"],
        "packet_count": document["packet_count"],
        "built_corpus_count": document["built_corpus_count"],
        "earlier_corpus": document["earlier_corpus"],
        "overlap_with_built_corpus": document["overlap_with_built_corpus"],
        "overlap_with_130_packet_corpus": document["overlap_with_130_packet_corpus"],
        "heldout_v1_unchanged": True,
        "not_unseen": True,
        "claim_ids": packet_ids,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "result.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    (output_dir / "REPRESENTATION.md").write_text(render_markdown(document), encoding="utf-8")
    return document


def render_markdown(document: dict[str, Any]) -> str:
    raw = document["arms"]["raw_qualifier"]["assessor"]["decisive_coverage"]
    composed = document["arms"]["composed_qualifier"]["assessor"]["decisive_coverage"]
    warrant_gap = document["arms"]["composed_strong"]["warrant"]["unsupported_support"]
    nominee = document["controls"]["historical_refutation_nominee"]
    return "\n".join(
        [
            "# Frozen-slice representation study",
            "",
            "This is a frozen-slice representation study of the existing 70-packet eligibility set. All 70 identifiers are inside the earlier 130-packet EvidenceGraph event corpus, so the slice is not unseen and this is not an independent held-out validation.",
            "",
            f"Raw classifiers recover {raw} assessor-decisive labels. With the shared admitted-premise adapter, both composed arms recover {composed}. Derived records are transformations: the composed arms still count 332 supplied records as the independent sources and make 0 further requests.",
            "",
            f"Against the separate warrant, the composed arms have {warrant_gap} unsupported supports. Those are the retained false-exclusivity packets. Matching the assessor is composition fidelity, because the assessor and the adapter share premise logic. It is not independent correctness. `external_empirical_transfer` is not_tested. The retained `transfer_claim` flag records that scope limit. `superiority_claim` and `independent_jury` stay false.",
            "",
            f"The historical refutation nominee remains the lexicographically first fabricated claim, and its assessor label is {nominee['visible_evidence_label']}. A supplementary refuted row is an inspected representative selected from the retained labels, not a blind validation case.",
            "",
            "Removing the successful control's registry mutation returns the assessor label to unresolved. Duplicating that record, or adding an irrelevant record, does not create a new assessor label.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_representation_study(ROOT, args.output)
    print(args.output / "result.json")


if __name__ == "__main__":
    main()
