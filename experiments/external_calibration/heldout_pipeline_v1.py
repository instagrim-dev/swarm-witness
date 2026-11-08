"""Score raw and adapted classifiers on the frozen 70-packet held-out set.

The label is the retained assessor verdict. False-exclusivity packets stay in
the denominator. The separate warrant is recorded beside that label and is not
used to drop a case.
"""

from __future__ import annotations

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
from heldout_v1 import _eligible, _label  # noqa: E402
from r2_event_packets import build_packets  # noqa: E402
from swarm_witness.incident_audit import swarm_witness_verdict  # noqa: E402
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402

PROTOCOL = Path(__file__).with_name("heldout_pipeline_v1.yaml")
ELIGIBILITY = Path(__file__).with_name("heldout_v1.yaml")
RETAINED_LABELS = ROOT / "evidence" / "external_calibration_v1" / "heldout_v1" / "result.json"
OUT = ROOT / "evidence" / "external_calibration_v1" / "heldout_v1" / "pipeline_v1.json"
ARMS = (
    "raw_swarm_witness",
    "raw_strong_invariant",
    "adapted_swarm_witness",
    "adapted_strong_invariant",
)


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


def _blank() -> dict[str, int]:
    return {
        "correct_decisive": 0,
        "unsupported_support": 0,
        "unsupported_refutation": 0,
        "abstention": 0,
        "other": 0,
    }


def _time_call(function, claim: dict[str, Any], observations: list[dict[str, Any]]) -> tuple[str, float]:
    started = time.perf_counter()
    verdict = function(claim, observations)["epistemic_status"]
    return verdict, time.perf_counter() - started


def run() -> dict[str, Any]:
    protocol = yaml.safe_load(ELIGIBILITY.read_text(encoding="utf-8"))
    retained = json.loads(RETAINED_LABELS.read_text(encoding="utf-8"))
    retained_by_id = {row["claim_id"]: row for row in retained["rows"]}
    packets = [packet for packet in build_packets() if _eligible(packet, protocol)]
    packets.sort(key=lambda packet: packet["claim"]["id"])
    if [packet["claim"]["id"] for packet in packets] != [row["claim_id"] for row in retained["rows"]]:
        raise ValueError("held-out eligibility diverged from the retained 70 packets")

    totals = {arm: _blank() for arm in ARMS}
    processing = {arm: 0.0 for arm in ARMS}
    supplied = 0
    derived = 0
    rows = []
    for packet in packets:
        claim = packet["claim"]
        observations = packet["observations"]
        computed = _label(packet)["status"]
        frozen = retained_by_id[claim["id"]]
        if computed != frozen["visible_evidence_label"]:
            raise ValueError(f"{claim['id']}: assessor label changed")
        label = frozen["visible_evidence_label"]
        warrant = packet["warranted_conclusion"]["status"]
        assessment, projected = composed_observations(claim, observations)
        composed = list(observations) + projected
        supplied += len(observations)
        derived += len(projected)
        raw_swarm, raw_swarm_seconds = _time_call(swarm_witness_verdict, claim, observations)
        raw_strong, raw_strong_seconds = _time_call(strong_invariant_verdict, claim, observations)
        adapted_swarm, adapted_swarm_seconds = _time_call(swarm_witness_verdict, claim, composed)
        adapted_strong, adapted_strong_seconds = _time_call(
            strong_invariant_verdict, claim, composed
        )
        predicted = {
            "raw_swarm_witness": raw_swarm,
            "raw_strong_invariant": raw_strong,
            "adapted_swarm_witness": adapted_swarm,
            "adapted_strong_invariant": adapted_strong,
        }
        seconds = {
            "raw_swarm_witness": raw_swarm_seconds,
            "raw_strong_invariant": raw_strong_seconds,
            "adapted_swarm_witness": adapted_swarm_seconds,
            "adapted_strong_invariant": adapted_strong_seconds,
        }
        for arm, verdict in predicted.items():
            totals[arm][_category(verdict, label)] += 1
            processing[arm] += seconds[arm]
        rows.append(
            {
                "claim_id": claim["id"],
                "family": claim["family"],
                "scenario": claim.get("scenario"),
                "assessor_label": label,
                "warranted_conclusion": warrant,
                "adapter_verdict": assessment["verdict"],
                "derived_records": len(projected),
                "supplied_records": len(observations),
                "additional_source_requests": 0,
                **predicted,
            }
        )

    false_rows = [row for row in rows if row["scenario"] == "false_exclusivity"]
    assessor_decisive = retained["label_counts"]["supported"] + retained["label_counts"]["refuted"]
    warrant_decisive = sum(
        row["warranted_conclusion"] in {"supported", "refuted"} for row in rows
    )
    warrant_totals = {arm: _blank() for arm in ARMS}
    for row in rows:
        for arm in ARMS:
            warrant_totals[arm][_category(row[arm], row["warranted_conclusion"])] += 1
    warrant = {
        arm: {
            **counts,
            "decisive_coverage": f"{counts['correct_decisive']}/{warrant_decisive}",
        }
        for arm, counts in warrant_totals.items()
    }
    methods = {}
    for arm in ARMS:
        counts = totals[arm]
        adapted = arm.startswith("adapted_")
        methods[arm] = {
            **counts,
            "decisive_coverage": f"{counts['correct_decisive']}/{assessor_decisive}",
            "source_demand": {
                "supplied_records": supplied,
                "derived_records": derived if adapted else 0,
                "additional_source_requests": 0,
            },
        }
    return {
        "protocol_id": "heldout-pipeline-v1",
        "eligibility_protocol": "external-heldout-v1",
        "packet_count": len(rows),
        "assessor_decisive": assessor_decisive,
        "warrant_decisive": warrant_decisive,
        "label_source": "retained heldout_v1 assessor labels",
        "independent_jury": False,
        "superiority_claim": False,
        "transfer_claim": False,
        "adapter": "composed_observations",
        "false_exclusivity_packets_retained": len(false_rows),
        "false_exclusivity": {
            "packet_count": len(false_rows),
            "assessor_supported_warrant_unresolved": sum(
                1
                for row in false_rows
                if row["assessor_label"] == "supported" and row["warranted_conclusion"] == "unresolved"
            ),
            "raw_swarm_witness_supports": sum(
                1 for row in false_rows if row["raw_swarm_witness"] == "supported"
            ),
            "raw_strong_invariant_supports": sum(
                1 for row in false_rows if row["raw_strong_invariant"] == "supported"
            ),
            "adapted_swarm_witness_supports": sum(
                1 for row in false_rows if row["adapted_swarm_witness"] == "supported"
            ),
            "adapted_strong_invariant_supports": sum(
                1 for row in false_rows if row["adapted_strong_invariant"] == "supported"
            ),
        },
        "adapted_arms_agree": all(
            row["adapted_swarm_witness"] == row["adapted_strong_invariant"] for row in rows
        ),
        "adapter_matches_adapted_arms": all(
            row["adapter_verdict"] == row["adapted_swarm_witness"] == row["adapted_strong_invariant"]
            for row in rows
        ),
        "warrant": warrant,
        "processing_seconds": processing,
        "methods": methods,
        "rows": rows,
    }


def main() -> None:
    document = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
