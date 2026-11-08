#!/usr/bin/env python3
"""Run the blinded incident-audit comparison and write versioned evidence.

The adjudication file is applied only after qualifiers return. Rewriting it
does not change naive, checklist, or Swarm Witness verdicts.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.evidence_index import generate_and_write_index  # noqa: E402
from swarm_witness.incident_audit import (  # noqa: E402
    evaluate,
    observations_for_stage,
    prepare_observations,
    summarize,
    swarm_witness_verdict,
)
from swarm_witness.schema import validate_finding, validate_run  # noqa: E402

CLAIM_ID = "incident_claims_v1"
PROTOCOL_ID = "incident-audit-v1"
SOURCE_PIN = "incident-audit-v1"
RUN_ID = "incident-audit-v1-comparison"


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cell(rows: list[dict], claim_id: str, stage: str, method: str) -> dict:
    for row in rows:
        if (
            row["claim_id"] == claim_id
            and row["stage"] == stage
            and row["method"] == method
        ):
            return row
    raise KeyError((claim_id, stage, method))


def _public_rows(rows: list[dict]) -> list[dict]:
    published = []
    for row in rows:
        item = {
            "claim_id": row["claim_id"],
            "stage": row["stage"],
            "method": row["method"],
            "predicted": row["predicted"],
            "adjudicated": row["adjudicated"],
            "category": row["category"],
            "prompt_sha256": row["prompt_sha256"],
            "observation_ids": row["observation_ids"],
        }
        if row["method"] == "swarm_witness":
            swarm = row["swarm"]
            item["assertion_status"] = swarm["assertion_status"]
            item["verification_status"] = swarm["verification_status"]
            item["conclusion_class"] = swarm["conclusion_class"]
            item["support_group_count"] = swarm["support_group_count"]
            item["withheld_dependent_count"] = swarm["withheld_dependent_count"]
            item["document_count"] = swarm["document_count"]
            item["reason"] = swarm["reason"]
        published.append(item)
    return published


def run(root: Path = ROOT) -> dict:
    claim_path = root / "claims" / "incident_claims_v1.yaml"
    protocol_path = root / "experiments" / "incident_audit" / "protocol_v1.yaml"
    excerpt_path = root / "experiments" / "incident_audit" / "excerpts_v1.yaml"
    warrant_path = root / "experiments" / "incident_audit" / "adjudication_v1.yaml"
    manifest_path = root / "experiments" / "incident_audit" / "corpus_manifest.yaml"
    passage_path = root / "experiments" / "incident_audit" / "pinned_passages.yaml"
    claim_doc = _load(claim_path)
    protocol = _load(protocol_path)
    excerpts = _load(excerpt_path)
    adjudication = _load(warrant_path)
    claims = claim_doc["frozen_propositions"]
    observations = prepare_observations(excerpts["observations"])
    rows = evaluate(claims, observations, adjudication, protocol)
    totals = summarize(rows, protocol)
    text_rows = evaluate(
        claims,
        observations,
        adjudication,
        protocol,
        ignore_independence=True,
        count_derived_as_independent=True,
        public_text_verifies_world_effects=True,
    )
    text_totals = summarize(text_rows, protocol)
    scope_rows = evaluate(
        claims, observations, adjudication, protocol, scope_collapse=True
    )
    stage_a_only = observations_for_stage(observations, "A")
    withheld = {
        claim_id: swarm_witness_verdict(claim, stage_a_only)["epistemic_status"]
        for claim in claims
        for claim_id in (claim["id"],)
        if claim_id in {"C03", "C05"}
    }
    c12_dependent = swarm_witness_verdict(
        next(claim for claim in claims if claim["id"] == "C12"),
        observations_for_stage(observations, "B"),
        ignore_independence=True,
        count_derived_as_independent=True,
    )
    c05_collapsed = _cell(scope_rows, "C05", "A", "swarm_witness")
    c04b = _cell(rows, "C04", "B", "swarm_witness")
    c03b = _cell(rows, "C03", "B", "swarm_witness")
    c05b = _cell(rows, "C05", "B", "swarm_witness")
    c06b = _cell(rows, "C06", "B", "swarm_witness")
    control_ids = {
        claim["id"]
        for claim in claims
        if claim.get("control")
    }
    control_false = sum(
        1
        for row in rows
        if row["method"] == "swarm_witness"
        and row["claim_id"] in control_ids
        and row["category"].startswith("false_support")
    )
    observations_out = {
        "claim_count": len(claims),
        "stage_count": 2,
        "cell_count_per_method": totals["cell_count_per_method"],
        "naive_unsupported": totals["naive_unsupported"],
        "checklist_unsupported": totals["checklist_unsupported"],
        "swarm_witness_unsupported": totals["swarm_witness_unsupported"],
        "swarm_witness_correct_refusal": totals["swarm_witness_correct_refusal"],
        "swarm_witness_warranted_refutation": totals[
            "swarm_witness_warranted_refutation"
        ],
        "swarm_witness_warranted_support": totals["swarm_witness_warranted_support"],
        "primary_endpoint_passed": totals["primary_endpoint_passed"],
        "detection_or_prevention_claimed": False,
        "control_false_supports": control_false,
        "ambiguous_c04_stage_b": c04b["predicted"],
        "update_c03_stage_b": c03b["predicted"],
        "update_c05_stage_b": c05b["predicted"],
        "c06_stage_b_epistemic": c06b["predicted"],
        "c06_stage_b_assertion": c06b["swarm"]["assertion_status"],
        "ablation_text_trust_unsupported": text_totals["swarm_witness_unsupported"],
        "ablation_stage_a_c03": withheld["C03"],
        "ablation_stage_a_c05": withheld["C05"],
        "ablation_scope_collapse_c05_a": c05_collapsed["predicted"],
        "ablation_dependency_c12_groups": c12_dependent["support_group_count"],
    }
    passed = bool(observations_out["primary_endpoint_passed"])
    label = "reproduced" if passed else "contradicted_in_scope"
    ev = root / "evidence" / "incident_audit_v1"
    runs = ev / "runs"
    findings = ev / "findings"
    runs.mkdir(parents=True, exist_ok=True)
    findings.mkdir(parents=True, exist_ok=True)
    run = {
        "id": RUN_ID,
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "blinded-postmortem-comparison",
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "observations": observations_out,
    }
    validate_run(run)
    finding = {
        "id": "incident-audit-v1-f-comparison",
        "claim_id": CLAIM_ID,
        "run_ids": [RUN_ID],
        "proposition": (
            "On the frozen public postmortem corpus, Swarm Witness records "
            "strictly fewer unsupported security conclusions than both matched "
            "baselines. This is a postmortem qualification, not incident "
            "detection or prevention."
            if passed
            else "The pre-registered unsupported-conclusion comparison did not pass."
        ),
        "scope": (
            "Twelve public incident propositions at two evidence stages under "
            "incident-audit-v1. Raw telemetry listed as unavailable in the "
            "corpus manifest is not treated as verified."
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.primary_endpoint_passed",
            f"{RUN_ID}.observations.swarm_witness_unsupported",
            f"{RUN_ID}.observations.naive_unsupported",
            f"{RUN_ID}.observations.checklist_unsupported",
            f"{RUN_ID}.observations.cell_count_per_method",
            f"{RUN_ID}.observations.detection_or_prevention_claimed",
        ],
        "conclusion_class": "supported" if passed else "failed_enforcement",
        "evaluation_method": "public_postmortem_qualification",
    }
    validate_finding(finding)
    (runs / f"{RUN_ID}.json").write_text(
        json.dumps(run, indent=2) + "\n", encoding="utf-8"
    )
    (findings / "incident-audit-v1-f-comparison.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )
    metrics = {
        "claim_count": observations_out["claim_count"],
        "cell_count_per_method": observations_out["cell_count_per_method"],
        "naive_unsupported": observations_out["naive_unsupported"],
        "checklist_unsupported": observations_out["checklist_unsupported"],
        "swarm_witness_unsupported": observations_out["swarm_witness_unsupported"],
        "primary_endpoint_passed": observations_out["primary_endpoint_passed"],
        "detection_or_prevention_claimed": False,
        "control_false_supports": control_false,
    }
    result = {
        "claim_id": CLAIM_ID,
        "label": label,
        "authoritative": "finding",
        "finding_path": "findings/incident-audit-v1-f-comparison.json",
        "metrics": metrics,
        "notes": (
            "Postmortem qualification of public Artifactory / Hugging Face "
            "reports. Not a detection or prevention result."
        ),
    }
    (ev / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )
    summary = {
        "claim_id": CLAIM_ID,
        "label": label,
        "protocol_id": PROTOCOL_ID,
        "authoritative_finding": "evidence/incident_audit_v1/findings/incident-audit-v1-f-comparison.json",
        **metrics,
        "swarm_witness_correct_refusal": observations_out[
            "swarm_witness_correct_refusal"
        ],
        "swarm_witness_warranted_refutation": observations_out[
            "swarm_witness_warranted_refutation"
        ],
        "swarm_witness_warranted_support": observations_out[
            "swarm_witness_warranted_support"
        ],
        "ambiguous_c04_stage_b": observations_out["ambiguous_c04_stage_b"],
        "update_c03_stage_b": observations_out["update_c03_stage_b"],
        "update_c05_stage_b": observations_out["update_c05_stage_b"],
        "c06_stage_b_epistemic": observations_out["c06_stage_b_epistemic"],
        "c06_stage_b_assertion": observations_out["c06_stage_b_assertion"],
        "ablation_text_trust_unsupported": observations_out[
            "ablation_text_trust_unsupported"
        ],
        "ablation_stage_a_c03": observations_out["ablation_stage_a_c03"],
        "ablation_stage_a_c05": observations_out["ablation_stage_a_c05"],
        "ablation_scope_collapse_c05_a": observations_out[
            "ablation_scope_collapse_c05_a"
        ],
        "ablation_dependency_c12_groups": observations_out[
            "ablation_dependency_c12_groups"
        ],
    }
    (ev / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    matrix = {
        "protocol_id": PROTOCOL_ID,
        "rows": _public_rows(rows),
    }
    (ev / "matrix.json").write_text(
        json.dumps(matrix, indent=2) + "\n", encoding="utf-8"
    )
    artifact_dir = root / "artifacts" / "incident_audit_v1"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    inputs = {
        "claim": _sha256(claim_path),
        "protocol": _sha256(protocol_path),
        "excerpts": _sha256(excerpt_path),
        "adjudication": _sha256(warrant_path),
        "corpus_manifest": _sha256(manifest_path),
        "pinned_passages": _sha256(passage_path),
    }
    (artifact_dir / "input_sha256.json").write_text(
        json.dumps(inputs, indent=2) + "\n", encoding="utf-8"
    )
    (artifact_dir / "matrix.json").write_text(
        json.dumps(matrix, indent=2) + "\n", encoding="utf-8"
    )
    generate_and_write_index(root)
    return {"summary": summary, "label": label}


def main() -> int:
    result = run()
    print(json.dumps(result["summary"], indent=2))
    return 0 if result["summary"]["primary_endpoint_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
