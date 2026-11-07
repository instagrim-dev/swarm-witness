#!/usr/bin/env python3
"""Write the incident-property-graph evidence slot from the fixed fixtures.

Does not claim detection or prevention of the 2026 Hugging Face incident.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.evidence_index import generate_and_write_index  # noqa: E402
from swarm_witness.incident_property_graph import (  # noqa: E402
    SOURCE_PIN,
    evaluate_manifest,
    load_inputs,
)

CLAIM_ID = "incident_property_graph"
RUN_ID = "incident-property-graph-meta"
FINDING_ID = "incident-property-graph-f-separation"

SCALAR_KEYS = (
    "passed",
    "synthetic_case_count",
    "postmortem_case_count",
    "graph_false_system_supports",
    "baseline_false_system_supports",
    "baseline_false_system_rejects",
    "decision_used_as_effect_proof_count",
    "deny_with_committed_effect",
    "refuted_child_hidden_count",
    "url_held_local_read_p_url",
    "url_held_local_read_p_file_read",
    "url_held_local_read_p_exec",
    "url_held_local_read_p_system",
    "postmortem_independent_supported",
    "postmortem_independent_refuted",
    "postmortem_unresolved_properties",
    "conjunction_checks",
    "conjunction_checks_passed",
    "conservative_unresolved_gap",
    "incident_detection_claimed",
    "incident_prevention_claimed",
)


def publish(root: Path | None = None) -> dict:
    root = root or ROOT
    graph, fixtures, postmortem = load_inputs(root)
    summary = evaluate_manifest(graph=graph, fixtures=fixtures, postmortem=postmortem)
    observations = {key: summary[key] for key in SCALAR_KEYS}
    slot = root / "evidence" / "incident_property_graph"
    runs = slot / "runs"
    findings = slot / "findings"
    runs.mkdir(parents=True, exist_ok=True)
    findings.mkdir(parents=True, exist_ok=True)
    run = {
        "id": RUN_ID,
        "claim_id": CLAIM_ID,
        "protocol_id": SOURCE_PIN,
        "case_id": "aggregate",
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "observations": observations,
    }
    finding = {
        "id": FINDING_ID,
        "claim_id": CLAIM_ID,
        "run_ids": [RUN_ID],
        "proposition": (
            "On nine synthetic boundary fixtures, supported(P_url) does not "
            "yield supported(P_system) when another child is refuted or "
            "unresolved; the single-policy-pass baseline does so on the "
            "counted counterexamples. A deny decision is not recorded as "
            "proof the effect was prevented. The Hugging Face timeline case "
            "stays unresolved on every boundary property because only public "
            "narrative is in hand. This run does not claim the incident was "
            "detected or prevented."
        ),
        "scope": (
            "incident-property-graph-v1 synthetic model ledger plus one "
            "public-narrative case pinned to the 2026-07-27 Hugging Face "
            "technical timeline. Not live workers and not raw incident telemetry."
        ),
        "label": "reproduced",
        "basis": "computed",
        "conclusion_class": "supported",
        "evaluation_method": "synthetic_protocol_conformance",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.passed",
            f"{RUN_ID}.observations.graph_false_system_supports",
            f"{RUN_ID}.observations.baseline_false_system_supports",
            f"{RUN_ID}.observations.url_held_local_read_p_system",
            f"{RUN_ID}.observations.postmortem_independent_supported",
            f"{RUN_ID}.observations.postmortem_independent_refuted",
            f"{RUN_ID}.observations.decision_used_as_effect_proof_count",
        ],
    }
    (runs / f"{RUN_ID}.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (findings / f"{FINDING_ID}.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "schema_version": summary["schema_version"],
        "results": summary["results"],
        "postmortem": summary["postmortem"],
        "finite": summary["finite"],
    }
    (slot / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (slot / "summary.json").write_text(
        json.dumps(
            {
                "claim_id": CLAIM_ID,
                "label": "reproduced",
                "finding_id": FINDING_ID,
                **observations,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    result = {
        "claim_id": CLAIM_ID,
        "label": "reproduced",
        "authoritative": "finding",
        "finding_path": f"findings/{FINDING_ID}.json",
        "metrics": observations,
    }
    (slot / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )
    if root == ROOT:
        generate_and_write_index(root)
    return observations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    observations = publish(args.root)
    print(json.dumps({key: observations[key] for key in (
        "passed",
        "synthetic_case_count",
        "graph_false_system_supports",
        "baseline_false_system_supports",
        "baseline_false_system_rejects",
        "postmortem_unresolved_properties",
        "conjunction_checks",
        "incident_detection_claimed",
    )}))
    return 0 if observations["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
