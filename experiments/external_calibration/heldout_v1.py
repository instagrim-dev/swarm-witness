"""Score the frozen held-out eligibility set once.

Labels come from the visible-evidence assessor. Controlled truth is stored
beside those labels and is not the score target. Method agreement is not
independence and is not the label.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eg_evidence_adapter import (  # noqa: E402
    assess_attribution,
    assess_fabricated_execution,
)
from r2_event_packets import build_packets  # noqa: E402
from swarm_witness.incident_audit import swarm_witness_verdict  # noqa: E402
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402

PROTOCOL = Path(__file__).with_name("heldout_v1.yaml")
OUT = ROOT / "evidence" / "external_calibration_v1" / "heldout_v1" / "result.json"


def _eligible(packet: dict[str, Any], protocol: dict[str, Any]) -> bool:
    claim = packet["claim"]
    if claim.get("seed") != protocol["eligibility"]["seed"]:
        return False
    for rule in protocol["eligibility"]["include"]:
        if claim.get("family") != rule["family"]:
            continue
        scenarios = rule.get("scenarios")
        if scenarios is None or claim.get("scenario") in scenarios:
            return True
    return False


def _label(packet: dict[str, Any]) -> dict[str, Any]:
    claim = packet["claim"]
    observations = packet["observations"]
    if claim["family"] == "fabricated_execution":
        assessed = assess_fabricated_execution(claim, observations)
    else:
        assessed = assess_attribution(claim, observations)
    return {"status": assessed["verdict"], "reason": assessed["reason"]}


def _methods(claim: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    started = time.perf_counter()
    strong = strong_invariant_verdict(claim, observations)
    strong_seconds = time.perf_counter() - started
    started = time.perf_counter()
    swarm = swarm_witness_verdict(claim, observations)
    swarm_seconds = time.perf_counter() - started
    return {
        "strong_invariant": strong["epistemic_status"],
        "swarm_witness": swarm["epistemic_status"],
        "processing_seconds": {
            "strong_invariant": strong_seconds,
            "swarm_witness": swarm_seconds,
        },
        "supplied_records": len(observations),
        "additional_source_requests": 0,
    }


def _without_type(observations: list[dict[str, Any]], type_name: str) -> list[dict[str, Any]]:
    return [
        row
        for row in observations
        if type_name not in (row.get("observation_types") or [])
    ]


def _duplicate_type(observations: list[dict[str, Any]], type_name: str) -> list[dict[str, Any]]:
    copied = copy.deepcopy(observations)
    original = next(row for row in copied if type_name in (row.get("observation_types") or []))
    duplicate = copy.deepcopy(original)
    duplicate["id"] = str(original["id"]) + "-duplicate"
    return copied + [duplicate]


def _irrelevant(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extra = {
        "id": "heldout-irrelevant-observation",
        "observation_types": ["irrelevant_note"],
        "quote": "unrelated note",
        "applies_to": [],
        "authenticity": "not_checked",
        "access_level": "public_bytes",
        "locally_held": True,
    }
    return list(observations) + [extra]


def _intervention(packet: dict[str, Any], type_name: str) -> dict[str, Any]:
    claim = packet["claim"]
    base = packet["observations"]
    stages = {
        "removed": _without_type(base, type_name),
        "duplicated": _duplicate_type(base, type_name),
        "irrelevant": _irrelevant(base),
    }
    out = {}
    for name, observations in stages.items():
        if claim["family"] == "fabricated_execution":
            assessed = assess_fabricated_execution(claim, observations)
        else:
            assessed = assess_attribution(claim, observations)
        scored = _methods(claim, observations)
        out[name] = {
            "visible_evidence_label": assessed["verdict"],
            "strong_invariant": scored["strong_invariant"],
            "swarm_witness": scored["swarm_witness"],
            "supplied_records": scored["supplied_records"],
            "additional_source_requests": 0,
        }
    return out


def run() -> dict[str, Any]:
    protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    eligible = [packet for packet in build_packets() if _eligible(packet, protocol)]
    eligible.sort(key=lambda packet: packet["claim"]["id"])
    rows = []
    disagreements = []
    totals = {"supported": 0, "refuted": 0, "unresolved": 0}
    unsupported_support = {"strong_invariant": 0, "swarm_witness": 0}
    unsupported_refutation = {"strong_invariant": 0, "swarm_witness": 0}
    correct_decisive = {"strong_invariant": 0, "swarm_witness": 0}
    abstention = {"strong_invariant": 0, "swarm_witness": 0}
    supplied = 0
    processing = {"strong_invariant": 0.0, "swarm_witness": 0.0}
    for packet in eligible:
        claim = packet["claim"]
        label = _label(packet)
        scored = _methods(claim, packet["observations"])
        totals[label["status"]] = totals.get(label["status"], 0) + 1
        supplied += scored["supplied_records"]
        for method in ("strong_invariant", "swarm_witness"):
            predicted = scored[method]
            processing[method] += scored["processing_seconds"][method]
            if predicted == "unresolved":
                abstention[method] += 1
            elif predicted == label["status"] and predicted in {"supported", "refuted"}:
                correct_decisive[method] += 1
            if predicted == "supported" and label["status"] != "supported":
                unsupported_support[method] += 1
            if predicted == "refuted" and label["status"] != "refuted":
                unsupported_refutation[method] += 1
        if scored["strong_invariant"] != scored["swarm_witness"]:
            disagreements.append(
                {
                    "claim_id": claim["id"],
                    "visible_evidence_label": label["status"],
                    "strong_invariant": scored["strong_invariant"],
                    "swarm_witness": scored["swarm_witness"],
                    "resolution": "visible_evidence_label",
                }
            )
        factual = packet.get("factual_outcome") or {}
        rows.append(
            {
                "claim_id": claim["id"],
                "family": claim["family"],
                "scenario": claim.get("scenario"),
                "visible_evidence_label": label["status"],
                "visible_evidence_reason": label["reason"],
                "controlled_truth": factual.get("proposition_holds"),
                "strong_invariant": scored["strong_invariant"],
                "swarm_witness": scored["swarm_witness"],
                "supplied_records": scored["supplied_records"],
                "additional_source_requests": 0,
            }
        )
    clean = [
        packet
        for packet in eligible
        if packet["claim"]["family"] == "event_attribution" and packet["claim"].get("scenario") == "clean"
    ]
    fabricated = [
        packet for packet in eligible if packet["claim"]["family"] == "fabricated_execution"
    ]
    successful = clean[0]
    refutation_packet = next(
        (packet for packet in fabricated if _label(packet)["status"] == "refuted"),
        fabricated[0],
    )
    removed = _without_type(successful["observations"], "registry_mutation_record")
    return {
        "protocol_id": protocol["id"],
        "independent_jury": False,
        "authorship": protocol["authorship"],
        "eligibility_count": len(rows),
        "superiority_claim": False,
        "transfer_claim": False,
        "label_source": "frozen visible-evidence assessor",
        "controlled_truth_is_the_label": False,
        "agreement_is_not_the_label": True,
        "label_counts": totals,
        "unsupported_support": unsupported_support,
        "unsupported_refutation": unsupported_refutation,
        "correct_decisive": correct_decisive,
        "abstention": abstention,
        "source_demand": {
            "supplied_records": supplied,
            "additional_source_requests": 0,
        },
        "processing_seconds": processing,
        "disagreements": disagreements,
        "controls": {
            "successful": {
                "claim_id": successful["claim"]["id"],
                "visible_evidence_label": _label(successful)["status"],
                "controlled_truth": (successful.get("factual_outcome") or {}).get("proposition_holds"),
            },
            "unresolved": {
                "claim_id": successful["claim"]["id"],
                "intervention": "remove registry_mutation_record",
                "visible_evidence_label": assess_attribution(successful["claim"], removed)["verdict"],
            },
            "refutation": {
                "claim_id": refutation_packet["claim"]["id"],
                "visible_evidence_label": _label(refutation_packet)["status"],
                "controlled_truth": (refutation_packet.get("factual_outcome") or {}).get(
                    "proposition_holds"
                ),
            },
        },
        "discriminating_record": {
            "claim_id": successful["claim"]["id"],
            "record_type": "registry_mutation_record",
            "interventions": _intervention(successful, "registry_mutation_record"),
        },
        "rows": rows,
    }


def main() -> None:
    document = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stored = dict(document)
    # Processing time is retained in the execution log, not as a frozen equality.
    OUT.write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
