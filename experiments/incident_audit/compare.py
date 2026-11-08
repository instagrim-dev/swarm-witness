#!/usr/bin/env python3
"""Frozen comparison of the public claims and the held reproduction record.

The LessWrong post and appendix are one record. Original transcripts and
Hugging Face platform logs are scored as unavailable, not as gates. A
blocks_upgrade slot prevents support only when this audit holds it. Nothing
here certifies the original incident or claims detection or prevention.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.comparison_score import (  # noqa: E402
    always_unresolved_origin,
    layer_summary,
    naive_origin,
)
from swarm_witness.evidence_index import generate_and_write_index  # noqa: E402
from swarm_witness.incident_audit import (  # noqa: E402
    checklist_verdict,
    evaluate,
    naive_verdict,
    observations_for_stage,
    prepare_observations,
    score_category,
    swarm_witness_verdict,
)
from swarm_witness.provenance import qualify_graph  # noqa: E402
from swarm_witness.schema import validate_finding, validate_run  # noqa: E402
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402

CLAIM_ID = "incident_comparison_v1"
PROTOCOL_ID = "incident-comparison-v1"
SOURCE_PIN = "incident-comparison-v1"
RUN_ID = "incident-comparison-v1-run"
CENSUS_SENTENCE = (
    "Run 260905_step1_xlsx_glm52_n64 signature_rate is 1.0 on {ones} files "
    "and 0.0 on {zeros} files."
)
SCORED = ("naive", "strong_invariant", "swarm_witness")
REFERENCE = "always_unresolved"


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _census_sentence(census: dict[str, Any]) -> str:
    files = census["files"]
    ones = sum(1 for row in files if row["signature_rate"] == 1.0)
    zeros = sum(1 for row in files if row["signature_rate"] == 0.0)
    if ones + zeros != len(files):
        raise ValueError("step-1 census signature rates are not partitioned")
    return CENSUS_SENTENCE.format(ones=ones, zeros=zeros)


def _origin(method: str, claim: dict[str, Any], observations: list[dict[str, Any]], detail: dict) -> str:
    if method == "naive":
        return naive_origin(claim, observations)
    if method == REFERENCE:
        return always_unresolved_origin()
    if method == "weak_checklist":
        return always_unresolved_origin()
    return str(detail.get("attributed_origin") or "undetermined")


def _predict(
    method: str, claim: dict[str, Any], observations: list[dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    if method == "naive":
        return naive_verdict(claim, observations), {}
    if method == "weak_checklist":
        return checklist_verdict(claim, observations), {}
    if method == "strong_invariant":
        detail = strong_invariant_verdict(claim, observations)
        return detail["epistemic_status"], detail
    if method == "swarm_witness":
        detail = swarm_witness_verdict(claim, observations)
        return detail["epistemic_status"], detail
    if method == REFERENCE:
        return "unresolved", {"attributed_origin": "undetermined"}
    raise ValueError(method)


def _score_claims(
    claims: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    warrants: dict[str, Any],
    categories: dict[str, Any],
    methods: tuple[str, ...],
    *,
    truth_known: bool,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    protocol = {"categories": categories}
    rows: list[dict[str, Any]] = []
    timings: dict[str, float] = {}
    selected = observations_for_stage(observations, "A")
    # Public callers pass both stages through evaluate(). This helper is the
    # single-packet controlled layer: every observation is stage A.
    for method in methods:
        started = time.perf_counter()
        built: list[dict[str, Any]] = []
        for claim in claims:
            predicted, detail = _predict(method, claim, selected)
            warrant = warrants[claim["id"]]
            built.append(
                {
                    "claim_id": claim["id"],
                    "history": claim.get("history"),
                    "stage": "A",
                    "method": method,
                    "predicted": predicted,
                    "adjudicated": warrant["epistemic"],
                    "warranted_origin": warrant["origin"],
                    "proposition_holds": warrant["proposition_holds"] if truth_known else None,
                    "category": score_category(predicted, warrant["epistemic"], protocol),
                    "attributed_origin": _origin(method, claim, selected, detail),
                    "observation_ids": [
                        obs["id"]
                        for obs in selected
                        if claim["id"] in obs.get("applies_to", [])
                    ],
                    "certifies_original_incident": bool(
                        claim.get("certifies_original_incident")
                    ),
                    "detail": detail,
                }
            )
        timings[method] = time.perf_counter() - started
        rows.extend(built)
    return rows, timings


def _public_rows(root: Path) -> tuple[list[dict[str, Any]], dict[str, float], Any]:
    claim_doc = _load(root / "claims" / "incident_claims_v1.yaml")
    claims = claim_doc["frozen_propositions"]
    observations = prepare_observations(
        _load(root / "experiments" / "incident_audit" / "excerpts_v1.yaml")["observations"]
    )
    protocol = _load(root / "experiments" / "incident_audit" / "protocol_v1.yaml")
    adjudication = _load(root / "experiments" / "incident_audit" / "adjudication_v1.yaml")
    base = evaluate(claims, observations, adjudication, protocol)
    timings: dict[str, float] = {}
    for method in ("naive", "weak_checklist", "strong_invariant", "swarm_witness", REFERENCE):
        started = time.perf_counter()
        for stage in ("A", "B"):
            selected = observations_for_stage(observations, stage)
            for claim in claims:
                _predict(method, claim, selected)
        timings[method] = time.perf_counter() - started
    for row in base:
        if row["method"] == "checklist":
            row["method"] = "weak_checklist"
        row["warranted_origin"] = "undetermined"
        row["proposition_holds"] = None
        row["history"] = row["claim_id"]
        row["certifies_original_incident"] = False
        detail = row.get("swarm") or {}
        if row["method"] == "swarm_witness":
            row["attributed_origin"] = detail.get("attributed_origin", "undetermined")
        elif row["method"] == "naive":
            stage_obs = observations_for_stage(observations, row["stage"])
            claim = next(item for item in claims if item["id"] == row["claim_id"])
            row["attributed_origin"] = naive_origin(claim, stage_obs)
        else:
            row["attributed_origin"] = "undetermined"
    extra: list[dict[str, Any]] = []
    for stage in ("A", "B"):
        selected = observations_for_stage(observations, stage)
        for claim in claims:
            warrant = adjudication["claims"][claim["id"]][stage]["epistemic"]
            for method in ("strong_invariant", REFERENCE):
                predicted, detail = _predict(method, claim, selected)
                extra.append(
                    {
                        "claim_id": claim["id"],
                        "history": claim["id"],
                        "stage": stage,
                        "method": method,
                        "predicted": predicted,
                        "adjudicated": warrant,
                        "warranted_origin": "undetermined",
                        "proposition_holds": None,
                        "category": score_category(predicted, warrant, protocol),
                        "attributed_origin": _origin(method, claim, selected, detail),
                        "observation_ids": [
                            obs["id"]
                            for obs in selected
                            if claim["id"] in obs.get("applies_to", [])
                        ],
                        "certifies_original_incident": False,
                        "detail": detail,
                    }
                )
    return base + extra, timings, claims


def _lineage(root: Path) -> dict[str, Any]:
    payload = _load(root / "experiments" / "provenance" / "incident_lineage.yaml")
    graph = payload["graphs"][0]
    qualified = qualify_graph(graph)["claims"]
    incident = ("prov_tool_call_spoof", "prov_message_board", "prov_hf_effect")
    release = qualified["prov_reproduction_transcripts"]
    return {
        "claim_count": len(qualified),
        "incident_unresolved": sum(
            1 for name in incident if qualified[name]["conclusion_class"] != "supported"
        ),
        "incident_supported": sum(
            1 for name in incident if qualified[name]["conclusion_class"] == "supported"
        ),
        "reproduction_conclusion": release["conclusion_class"],
        "reproduction_independent_observations": release["independent_observation_count"],
        "reproduction_duplicated_reports": release["duplicated_report_ids"],
        "reproduction_unavailable": [
            item["source_id"] for item in release["unavailable_sources"]
        ],
        "reproduction_upgrade_blocker": release["primary_upgrade_blocker"],
        "real_world_authenticity_certified": release["real_world_authenticity_certified"],
        "unavailable_are_upgrade_gates": False,
    }


def _strip(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    published = []
    for row in rows:
        item = {
            key: row[key]
            for key in (
                "claim_id",
                "history",
                "stage",
                "method",
                "predicted",
                "adjudicated",
                "category",
                "attributed_origin",
                "warranted_origin",
                "observation_ids",
                "certifies_original_incident",
            )
            if key in row
        }
        published.append(item)
    return published


def run(root: Path = ROOT) -> dict[str, Any]:
    comp = root / "experiments" / "incident_audit" / "comparison"
    census = json.loads((comp / "step1_glm52_n64_census.json").read_text(encoding="utf-8"))
    sentence = _census_sentence(census)
    packets = prepare_observations(_load(comp / "packets_v1.yaml")["observations"])
    census_quote = next(obs["quote"] for obs in packets if obs["id"] == "CENSUS")
    if census_quote != sentence:
        raise ValueError("census observation does not match the released score extract")
    claims = _load(comp / "claims_v1.yaml")["claims"]
    warrants = _load(comp / "warrants_v1.yaml")["claims"]
    categories = _load(root / "experiments" / "incident_audit" / "protocol_v1.yaml")[
        "categories"
    ]
    public_rows, public_times, public_claims = _public_rows(root)
    controlled_rows, controlled_times = _score_claims(
        claims,
        packets,
        warrants,
        categories,
        SCORED + (REFERENCE,),
        truth_known=True,
    )
    lineage = _lineage(root)
    public_methods = ["naive", "weak_checklist", "strong_invariant", "swarm_witness", REFERENCE]
    controlled_methods = list(SCORED) + [REFERENCE]
    public_summary = layer_summary(public_rows, public_methods, truth_known=False)
    controlled_summary = layer_summary(
        controlled_rows, controlled_methods, truth_known=True
    )
    for method, seconds in public_times.items():
        if method in public_summary:
            public_summary[method]["processing_time_seconds"] = seconds
    for method, seconds in controlled_times.items():
        controlled_summary[method]["processing_time_seconds"] = seconds

    release = next(row for row in controlled_rows if row["claim_id"] == "K-release" and row["method"] == "swarm_witness")
    strong_release = next(
        row for row in controlled_rows if row["claim_id"] == "K-release" and row["method"] == "strong_invariant"
    )
    certify_supported = [
        row
        for row in controlled_rows
        if row["claim_id"] == "K-certify"
        and row["method"] in {"strong_invariant", "swarm_witness"}
        and row["predicted"] == "supported"
    ]
    public_world = {
        claim["id"] for claim in public_claims if claim["kind"] == "world_effect"
    }
    public_world_supported = [
        row
        for row in public_rows
        if row["claim_id"] in public_world
        and row["method"] in {"strong_invariant", "swarm_witness"}
        and row["predicted"] == "supported"
    ]
    completed = (
        lineage["reproduction_conclusion"] == "supported"
        and lineage["reproduction_independent_observations"] == 1
        and lineage["incident_supported"] == 0
        and lineage["real_world_authenticity_certified"] is False
        and lineage["reproduction_upgrade_blocker"] is None
        and set(lineage["reproduction_unavailable"])
        == {"src-transcript-dump", "src-hf-platform-logs"}
        and not certify_supported
        and not public_world_supported
        and release["detail"].get("support_group_count") == 1
        and strong_release["predicted"] == "supported"
        and public_summary["naive"]["cell_count"] == len(public_claims) * 2
        and controlled_summary["naive"]["cell_count"] == len(claims)
    )
    observations = {
        "comparison_completed": completed,
        "superiority_claim": False,
        "real_world_authenticity_certified": False,
        "unavailable_blocks_comparison": False,
        "unavailable_are_upgrade_gates": False,
        "detection_or_prevention_claimed": False,
        "public_claim_count": len(public_claims),
        "public_cell_count": public_summary["naive"]["cell_count"],
        "public_naive_unsupported_support": public_summary["naive"]["unsupported_support"],
        "public_strong_unsupported_support": public_summary["strong_invariant"][
            "unsupported_support"
        ],
        "public_swarm_unsupported_support": public_summary["swarm_witness"][
            "unsupported_support"
        ],
        "public_naive_correct_decisive": public_summary["naive"]["correct_decisive"],
        "public_strong_correct_decisive": public_summary["strong_invariant"][
            "correct_decisive"
        ],
        "public_strong_decisive_opportunities": public_summary["strong_invariant"][
            "decisive_opportunities"
        ],
        "public_always_unresolved_correct_decisive": public_summary[REFERENCE][
            "correct_decisive"
        ],
        "controlled_claim_count": len(claims),
        "controlled_history_count": len({claim["history"] for claim in claims}),
        "controlled_cell_count": controlled_summary["naive"]["cell_count"],
        "controlled_naive_unsupported_support": controlled_summary["naive"][
            "unsupported_support"
        ],
        "controlled_strong_unsupported_support": controlled_summary["strong_invariant"][
            "unsupported_support"
        ],
        "controlled_naive_false_proposition_support": controlled_summary["naive"][
            "false_proposition_support"
        ],
        "controlled_strong_false_proposition_support": controlled_summary[
            "strong_invariant"
        ]["false_proposition_support"],
        "lineage_claim_count": lineage["claim_count"],
        "lineage_incident_supported": lineage["incident_supported"],
        "lineage_reproduction_independent_observations": lineage[
            "reproduction_independent_observations"
        ],
        "one_public_record": True,
    }
    passed = bool(observations["comparison_completed"])
    label = "reproduced" if passed else "contradicted_in_scope"
    ev = root / "evidence" / "incident_comparison_v1"
    (ev / "runs").mkdir(parents=True, exist_ok=True)
    (ev / "findings").mkdir(parents=True, exist_ok=True)
    run_doc = {
        "id": RUN_ID,
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "frozen-public-and-reproduction-comparison",
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "observations": {
            **observations,
            "layers": {
                "public": public_summary,
                "controlled": controlled_summary,
                "lineage": lineage,
            },
            "processing_time_seconds": {
                "public": public_times,
                "controlled": controlled_times,
            },
            "record_requests": 0,
        },
    }
    validate_run(run_doc)
    finding = {
        "id": "incident-comparison-v1-f",
        "claim_id": CLAIM_ID,
        "run_ids": [RUN_ID],
        "proposition": (
            "The frozen comparison completed on the public claims and the held "
            "LessWrong reproduction record. Original transcripts and Hugging Face "
            "platform logs stayed unavailable and were not gates. The original "
            "incident was not certified, and beating the naive baseline is not "
            "a superiority claim."
            if passed
            else "The frozen comparison did not complete under the recorded rules."
        ),
        "scope": (
            "Twelve public claim-stage cells, four controlled claims, and the "
            "lineage qualifications. The LessWrong post and appendix are one record."
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.comparison_completed",
            f"{RUN_ID}.observations.superiority_claim",
            f"{RUN_ID}.observations.real_world_authenticity_certified",
            f"{RUN_ID}.observations.unavailable_blocks_comparison",
            f"{RUN_ID}.observations.public_naive_unsupported_support",
            f"{RUN_ID}.observations.public_strong_unsupported_support",
            f"{RUN_ID}.observations.lineage_incident_supported",
        ],
        "conclusion_class": "supported" if passed else "failed_enforcement",
        "evaluation_method": "public_postmortem_qualification",
    }
    validate_finding(finding)
    (ev / "runs" / f"{RUN_ID}.json").write_text(
        json.dumps(run_doc, indent=2) + "\n", encoding="utf-8"
    )
    (ev / "findings" / "incident-comparison-v1-f.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "claim_id": CLAIM_ID,
        "label": label,
        "protocol_id": PROTOCOL_ID,
        "authoritative_finding": "evidence/incident_comparison_v1/findings/incident-comparison-v1-f.json",
        **observations,
        "layers": {
            "public": public_summary,
            "controlled": controlled_summary,
            "lineage": lineage,
        },
    }
    (ev / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (ev / "matrix.json").write_text(
        json.dumps(
            {
                "public": _strip(public_rows),
                "controlled": _strip(controlled_rows),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    result = {
        "claim_id": CLAIM_ID,
        "label": label,
        "authoritative": "finding",
        "finding_path": "findings/incident-comparison-v1-f.json",
        "metrics": observations,
        "notes": (
            "Post and appendix are one record. Unavailable originals are not "
            "gates. The original incident is not certified."
        ),
    }
    (ev / "result.yaml").write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")
    artifact = root / "artifacts" / "incident_comparison_v1"
    artifact.mkdir(parents=True, exist_ok=True)
    inputs = {
        "census": _sha256(comp / "step1_glm52_n64_census.json"),
        "packets": _sha256(comp / "packets_v1.yaml"),
        "claims": _sha256(comp / "claims_v1.yaml"),
        "warrants": _sha256(comp / "warrants_v1.yaml"),
        "protocol": _sha256(comp / "protocol_v1.yaml"),
        "lineage": _sha256(root / "experiments" / "provenance" / "incident_lineage.yaml"),
    }
    (artifact / "input_sha256.json").write_text(
        json.dumps(inputs, indent=2) + "\n", encoding="utf-8"
    )
    generate_and_write_index(root)
    return {"summary": summary, "label": label, "completed": completed}


def main() -> int:
    result = run()
    summary = result["summary"]
    print(json.dumps({key: summary[key] for key in summary if key != "layers"}, indent=2))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
