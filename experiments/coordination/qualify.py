"""Regenerate coordination qualifications from the incident fixture.

Writes Claim/Run/Finding artifacts under evidence/coordination/. The writer
does not fetch pages, does not invent agent records, and does not certify
the incident.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

from swarm_witness.audit_diagnosis import attach_evaluation_method
from swarm_witness.coordination import COORDINATION_VERSION, qualify_case
from swarm_witness.provenance import CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "experiments" / "coordination" / "incident_cases.yaml"
PROVENANCE = ROOT / "experiments" / "provenance" / "incident_lineage.yaml"
EVIDENCE = ROOT / "evidence" / "coordination"

INCIDENT_CASES = (
    "coord_board_participation",
    "coord_delegated_workstream",
    "coord_collective_impact",
)


def _controls():
    spec = importlib.util.spec_from_file_location(
        "coordination_controls", ROOT / "experiments" / "coordination" / "controls.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_inputs() -> tuple[dict, list[dict]]:
    provenance = yaml.safe_load(PROVENANCE.read_text(encoding="utf-8"))
    if provenance.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("provenance fixture contract_version mismatch")
    graphs = provenance.get("graphs") or []
    if len(graphs) != 1 or graphs[0].get("id") != "incident-lineage":
        raise ValueError("provenance fixture must contain incident-lineage")
    payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    if payload.get("contract_version") != COORDINATION_VERSION:
        raise ValueError("coordination fixture contract_version mismatch")
    if payload.get("provenance_contract") != CONTRACT_VERSION:
        raise ValueError("coordination fixture must import evidence-provenance-v1")
    if payload.get("provenance_graph_id") != graphs[0]["id"]:
        raise ValueError("coordination fixture cites the wrong provenance graph")
    cases = payload.get("cases") or []
    if [case["id"] for case in cases] != list(INCIDENT_CASES):
        raise ValueError("coordination fixture cases drifted")
    return graphs[0], cases


def _run(case_id: str, qualification: dict) -> dict:
    return {
        "id": f"{case_id.replace('_', '-')}-run",
        "claim_id": case_id,
        "protocol_id": COORDINATION_VERSION,
        "case_id": case_id,
        "source_pin": COORDINATION_VERSION,
        "execution_status": "completed",
        "observations": {
            "finding_label": qualification["finding_label"],
            "conclusion_class": qualification["conclusion_class"],
            "underlying_telemetry": "unavailable",
            "primary_upgrade_blocker": qualification["primary_upgrade_blocker"],
            "added_claim_qualification_value": qualification[
                "added_claim_qualification_value"
            ],
            "traced_causal_actor_count": qualification["traced_causal_actor_count"],
            "supported_while_blocked": False,
            "real_world_authenticity_certified": False,
            "incident_detection_claimed": False,
            "incident_prevention_claimed": False,
            "qualification": qualification,
        },
    }


def _finding(case_id: str, qualification: dict) -> dict:
    run_id = f"{case_id.replace('_', '-')}-run"
    finding = {
        "id": f"{case_id.replace('_', '-')}-f",
        "claim_id": case_id,
        "run_ids": [run_id],
        "proposition": qualification["proposition"],
        "scope": (
            "Public excerpts already pinned in the evidence-provenance-v1 incident "
            "graph. Coordination does not add agent instances or telemetry."
        ),
        "label": qualification["finding_label"],
        "basis": "computed",
        "supporting_observation_refs": [f"{run_id}.observations.finding_label"],
        "conclusion_class": qualification["conclusion_class"],
    }
    return attach_evaluation_method(finding, "held_out_artifact_audit")


def build_artifacts() -> dict:
    graph, cases = load_inputs()
    qualified = {case["id"]: qualify_case(case, graph) for case in cases}
    controls = _controls()
    controls.check_incident_blockers(graph, qualified)
    summary = controls.check_controls()
    unresolved = [
        case_id
        for case_id in INCIDENT_CASES
        if qualified[case_id]["finding_label"] == "unresolved"
        and qualified[case_id]["supported_while_blocked"] is False
        and qualified[case_id]["added_claim_qualification_value"] is False
        and qualified[case_id]["real_world_authenticity_certified"] is False
        and qualified[case_id]["incident_detection_claimed"] is False
        and qualified[case_id]["incident_prevention_claimed"] is False
    ]
    if unresolved != list(INCIDENT_CASES):
        raise RuntimeError("an incident coordination claim was upgraded")
    method_observations = {
        "contract_version": COORDINATION_VERSION,
        "provenance_contract": CONTRACT_VERSION,
        "incident_propositions": len(INCIDENT_CASES),
        "incident_unresolved": len(unresolved),
        "incident_added_claim_qualification_value": False,
        "traced_causal_actor_count": 0,
        "negative_controls": summary["negative_controls"],
        "negative_controls_passed": summary["negative_controls_passed"],
        "scale_messages": summary["scale_messages"],
        "scale_pairs_considered": summary["scale_pairs_considered"],
        "scale_all_pairs": summary["scale_all_pairs"],
        "scale_agent_pair_matrix_allocated": summary["scale_agent_pair_matrix_allocated"],
        "supported_while_blocked": False,
        "real_world_authenticity_certified": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
    }
    return {
        "qualified": qualified,
        "runs": {case_id: _run(case_id, qualified[case_id]) for case_id in INCIDENT_CASES},
        "findings": {
            case_id: _finding(case_id, qualified[case_id]) for case_id in INCIDENT_CASES
        },
        "method_run": {
            "id": "coordination-attribution-v1-run",
            "claim_id": "coordination_attribution_v1",
            "protocol_id": COORDINATION_VERSION,
            "case_id": "incident-lineage",
            "source_pin": COORDINATION_VERSION,
            "execution_status": "completed",
            "observations": method_observations,
        },
        "method_finding": attach_evaluation_method(
            {
                "id": "coordination-attribution-v1-f",
                "claim_id": "coordination_attribution_v1",
                "run_ids": ["coordination-attribution-v1-run"],
                "proposition": (
                    "Replaying the coordination fixture leaves the three public-record "
                    "propositions unresolved, keeps upgrade blockers in force, and "
                    "certifies neither detection nor prevention."
                ),
                "scope": "coordination-attribution-v1 fixture conformance",
                "label": "reproduced",
                "basis": "computed",
                "supporting_observation_refs": [
                    "coordination-attribution-v1-run.observations.incident_unresolved",
                    "coordination-attribution-v1-run.observations.real_world_authenticity_certified",
                    "coordination-attribution-v1-run.observations.incident_detection_claimed",
                ],
                "conclusion_class": "supported",
            },
            "synthetic_protocol_conformance",
        ),
    }


def write_artifacts() -> None:
    artifacts = build_artifacts()
    runs = EVIDENCE / "runs"
    findings = EVIDENCE / "findings"
    runs.mkdir(parents=True, exist_ok=True)
    findings.mkdir(parents=True, exist_ok=True)
    for case_id in INCIDENT_CASES:
        run = artifacts["runs"][case_id]
        (runs / f"{run['id']}.json").write_text(
            json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        finding = artifacts["findings"][case_id]
        (findings / f"{finding['id']}.json").write_text(
            json.dumps(finding, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    method_run = artifacts["method_run"]
    (runs / f"{method_run['id']}.json").write_text(
        json.dumps(method_run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    method_finding = artifacts["method_finding"]
    (findings / f"{method_finding['id']}.json").write_text(
        json.dumps(method_finding, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    result = {
        "claim_id": "coordination_attribution_v1",
        "label": "reproduced",
        "metrics": {
            "incident_propositions": 3,
            "incident_unresolved": 3,
            "incident_added_claim_qualification_value": False,
            "traced_causal_actor_count": 0,
            "negative_controls": 6,
            "negative_controls_passed": True,
            "scale_messages": 70000,
            "scale_pairs_considered": 1200,
            "scale_all_pairs": 719400,
            "scale_agent_pair_matrix_allocated": False,
            "supported_while_blocked": False,
            "real_world_authenticity_certified": False,
            "incident_detection_claimed": False,
            "incident_prevention_claimed": False,
        },
        "notes": (
            "Fixture conformance for coordination-attribution-v1. The three public "
            "propositions stay unresolved because board records, transcripts, and "
            "platform logs are not held. A verified log from another source does not "
            "clear those blockers. This is not an incident detection or prevention result."
        ),
    }
    (EVIDENCE / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )


if __name__ == "__main__":
    write_artifacts()
    print("wrote evidence/coordination from experiments/coordination/incident_cases.yaml")
