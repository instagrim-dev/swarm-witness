"""Regenerate provenance qualifications from the incident fixture.

Writes Claim/Run/Finding artifacts under evidence/provenance/. The writer
does not fetch the public pages again and does not certify the incident.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from swarm_witness.audit_diagnosis import attach_evaluation_method
from swarm_witness.provenance import CONTRACT_VERSION, qualify_graph

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "experiments" / "provenance" / "incident_lineage.yaml"
EVIDENCE = ROOT / "evidence" / "provenance"

INCIDENT_CLAIMS = (
    "prov_tool_call_spoof",
    "prov_message_board",
    "prov_hf_effect",
)
REPRODUCTION_CLAIM = "prov_reproduction_transcripts"


def load_incident_graph() -> dict:
    payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    if payload.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("incident fixture contract_version mismatch")
    graphs = payload.get("graphs") or []
    if len(graphs) != 1 or graphs[0].get("id") != "incident-lineage":
        raise ValueError("incident fixture must contain incident-lineage")
    return graphs[0]


def _run(claim_id: str, qualification: dict) -> dict:
    return {
        "id": f"{claim_id.replace('_', '-')}-run",
        "claim_id": claim_id,
        "protocol_id": CONTRACT_VERSION,
        "case_id": claim_id,
        "source_pin": CONTRACT_VERSION,
        "execution_status": "completed",
        "observations": {
            "finding_label": qualification["finding_label"],
            "conclusion_class": qualification["conclusion_class"],
            "underlying_telemetry": "unavailable",
            "primary_upgrade_blocker": qualification["primary_upgrade_blocker"],
            "independent_observation_count": qualification[
                "independent_observation_count"
            ],
            "missing_requirements": qualification["missing_requirements"],
            "invalid_requirements": qualification["invalid_requirements"],
            "unavailable_sources": [
                item["source_id"] for item in qualification["unavailable_sources"]
            ],
            "real_world_authenticity_certified": False,
            "incident_detection_claimed": False,
            "incident_prevention_claimed": False,
            "qualification": qualification,
        },
    }


def _finding(claim_id: str, qualification: dict) -> dict:
    run_id = f"{claim_id.replace('_', '-')}-run"
    finding = {
        "id": f"{claim_id.replace('_', '-')}-f",
        "claim_id": claim_id,
        "run_ids": [run_id],
        "proposition": qualification["proposition"],
        "label": qualification["finding_label"],
        "scope": (
            "Public LessWrong reproduction post and appendix. The OpenAI transcript "
            "dump and Hugging Face platform logs are recorded unavailable and do "
            "not block this qualification."
            if claim_id == "prov_reproduction_transcripts"
            else (
                "Public excerpts in experiments/provenance/incident_lineage.yaml. "
                "The OpenAI transcript dump and Hugging Face platform logs are "
                "recorded unavailable and are not upgrade gates."
            )
        ),
        "basis": "computed",
        "supporting_observation_refs": [f"{run_id}.observations.finding_label"],
        "conclusion_class": qualification["conclusion_class"],
    }
    return attach_evaluation_method(finding, "held_out_artifact_audit")


def build_artifacts(graph: dict | None = None) -> dict:
    graph = load_incident_graph() if graph is None else graph
    qualified = qualify_graph(graph)
    claims = qualified["claims"]
    unresolved = [
        claim_id
        for claim_id in INCIDENT_CLAIMS
        if claims[claim_id]["finding_label"] == "unresolved"
        and claims[claim_id]["real_world_authenticity_certified"] is False
        and claims[claim_id]["incident_detection_claimed"] is False
        and claims[claim_id]["incident_prevention_claimed"] is False
    ]
    if unresolved != list(INCIDENT_CLAIMS):
        raise RuntimeError(
            "incident fixture no longer qualifies as three unresolved, "
            "non-certifying claims"
        )
    reproduction = claims[REPRODUCTION_CLAIM]
    if reproduction["finding_label"] != "reproduced":
        raise RuntimeError("reproduction release claim was not qualified from the public post")
    if reproduction["real_world_authenticity_certified"] is not False:
        raise RuntimeError("reproduction qualification certified real-world authenticity")
    if reproduction["primary_upgrade_blocker"] is not None:
        raise RuntimeError("an unavailable original blocked the reproduction qualification")
    method_observations = {
        "contract_version": CONTRACT_VERSION,
        "incident_claims": len(INCIDENT_CLAIMS),
        "incident_unresolved": len(unresolved),
        "real_world_authenticity_certified": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "unavailable_originals_are_upgrade_gates": False,
        "graph_id": graph["id"],
    }
    return {
        "qualified": qualified,
        "runs": {
            claim_id: _run(claim_id, claims[claim_id])
            for claim_id in (*INCIDENT_CLAIMS, REPRODUCTION_CLAIM)
        },
        "findings": {
            claim_id: _finding(claim_id, claims[claim_id])
            for claim_id in (*INCIDENT_CLAIMS, REPRODUCTION_CLAIM)
        },
        "method_run": {
            "id": "provenance-contract-v1-run",
            "claim_id": "provenance_contract_v1",
            "protocol_id": CONTRACT_VERSION,
            "case_id": "incident-lineage",
            "source_pin": CONTRACT_VERSION,
            "execution_status": "completed",
            "observations": method_observations,
        },
        "method_finding": attach_evaluation_method(
            {
                "id": "provenance-contract-v1-f",
                "claim_id": "provenance_contract_v1",
                "run_ids": ["provenance-contract-v1-run"],
                "proposition": (
                    "Replaying the incident lineage fixture leaves all three "
                    "incident claims unresolved and certifies neither detection "
                    "nor prevention."
                ),
                "scope": "evidence-provenance-v1 fixture conformance",
                "label": "reproduced",
                "basis": "computed",
                "supporting_observation_refs": [
                    "provenance-contract-v1-run.observations.incident_unresolved",
                    "provenance-contract-v1-run.observations.real_world_authenticity_certified",
                    "provenance-contract-v1-run.observations.incident_detection_claimed",
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
    for claim_id, run in artifacts["runs"].items():
        (runs / f"{run['id']}.json").write_text(
            json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        finding = artifacts["findings"][claim_id]
        (findings / f"{finding['id']}.json").write_text(
            json.dumps(finding, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    method_run = artifacts["method_run"]
    (runs / f"{method_run['id']}.json").write_text(
        json.dumps(method_run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    method_finding = artifacts["method_finding"]
    (findings / f"{method_finding['id']}.json").write_text(
        json.dumps(method_finding, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = {
        "claim_id": "provenance_contract_v1",
        "label": "reproduced",
        "metrics": {
            "incident_claims": 3,
            "incident_unresolved": 3,
            "real_world_authenticity_certified": False,
            "incident_detection_claimed": False,
            "incident_prevention_claimed": False,
        },
        "notes": (
            "Fixture conformance for evidence-provenance-v1. The three world "
            "claims stay unresolved because the public excerpts do not verify "
            "them. The OpenAI transcript dump and Hugging Face platform logs "
            "are recorded unavailable and are not upgrade gates. The LessWrong "
            "reproduction release qualifies from its public post. This is not "
            "an incident detection or prevention result."
        ),
    }
    (EVIDENCE / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )


if __name__ == "__main__":
    write_artifacts()
    print("wrote evidence/provenance from experiments/provenance/incident_lineage.yaml")
