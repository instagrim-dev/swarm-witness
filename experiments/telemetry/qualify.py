"""Regenerate forensic-telemetry qualifications from public pins and synthetic rows.

The LessWrong post and appendix are the pins in the provenance fixture. This
writer does not retype them, does not copy Inspect .eval logs, and does not
certify the original incident.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

from swarm_witness.audit_diagnosis import attach_evaluation_method
from swarm_witness.provenance import content_sha256, normalize_lineage
from swarm_witness.telemetry import (
    TELEMETRY_VERSION,
    adapt_public_excerpts,
    assemble_graph,
    apply_conflicts,
    blinded_stage_summary,
    comparator_packet,
    load_origin_packet,
    qualify_telemetry_graph,
    read_rows,
    reconcile_events,
    unavailable_telemetry,
)

ROOT = Path(__file__).resolve().parents[2]
LINEAGE = ROOT / "experiments" / "provenance" / "incident_lineage.yaml"
TELEMETRY = ROOT / "experiments" / "telemetry"
PACKET = TELEMETRY / "packet"
EVIDENCE = ROOT / "evidence" / "telemetry"
SALT = "forensic-telemetry-v1"

PINNED_IDS = (
    "src-lw-reproduction-post",
    "src-lw-reproduction-appendix",
    "src-metr-command",
    "src-hf-correlation",
)
UNAVAILABLE_IDS = (
    "src-transcript-dump",
    "src-transcript-dump-copy",
    "src-execution-log",
    "src-board-dump",
    "src-hf-platform-logs",
    "src-hf-indicators",
    "src-launchpad-logs",
    "src-openai-blog",
    "src-other-channels",
)
NAMED_UNAVAILABLE = ("src-transcript-dump", "src-hf-platform-logs")
REPRODUCTION_CLAIM = "tel_reproduction_record"
ORIGINAL_CLAIM = "tel_original_logs"
METHOD_CLAIM = "forensic_telemetry_v1"


def _lineage_sources() -> dict[str, dict]:
    payload = yaml.safe_load(LINEAGE.read_text(encoding="utf-8"))
    graphs = payload.get("graphs") or []
    if len(graphs) != 1:
        raise ValueError("incident fixture must contain one graph")
    return {source["id"]: copy.deepcopy(source) for source in graphs[0]["source_records"]}


def _claims() -> list[dict]:
    payload = yaml.safe_load((TELEMETRY / "claims.yaml").read_text(encoding="utf-8"))
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("telemetry claims must be a non-empty list")
    return claims


def _public_events(pinned: dict[str, dict]) -> list[dict]:
    specs = read_rows(TELEMETRY / "public_excerpts.yaml", kind="excerpt")
    return adapt_public_excerpts(specs, pinned, salt=SALT)


def _events(pinned: dict[str, dict]) -> tuple[list[dict], list[dict], dict]:
    public = _public_events(pinned)
    packet = load_origin_packet(PACKET, salt=SALT)
    if packet["missing_origins"] or packet["truth_files_read"]:
        raise RuntimeError("the synthetic packet is missing an origin or read a truth file")
    synthetic = packet["events"]
    if any(not event["synthetic"] for event in synthetic):
        raise RuntimeError("packet rows must be labeled synthetic_control")
    if any(event["synthetic"] for event in public):
        raise RuntimeError("a pinned public excerpt was labeled synthetic")
    combined = apply_conflicts(
        public + synthetic, reconcile_events(public + synthetic)["links"]
    )
    reconciliation = reconcile_events(combined)
    return public, combined, reconciliation


def _graph(events: list[dict], sources: dict[str, dict], claims: list[dict], graph_id: str) -> dict:
    return assemble_graph(
        events,
        extra_sources=[sources[source_id] for source_id in UNAVAILABLE_IDS],
        claims=claims,
        pinned_sources={source_id: sources[source_id] for source_id in PINNED_IDS},
        graph_id=graph_id,
        notes=(
            "forensic-telemetry-v1. The LessWrong post and appendix are one "
            "public record. The OpenAI transcript dump and Hugging Face platform "
            "logs are unavailable and are not upgrade gates. Synthetic rows are "
            "synthetic_control. This graph does not certify the original incident."
        ),
    )


def _link(reconciliation: dict, left: str, right: str | None) -> dict:
    if right is None:
        wanted = f"link:{left}:-"
    else:
        ordered = tuple(sorted((left, right)))
        wanted = f"link:{ordered[0]}:{ordered[1]}"
    for link in reconciliation["links"]:
        if link["id"] == wanted:
            return link
    raise KeyError(wanted)


def _check(bundle: dict) -> None:
    qualified = bundle["qualified"]["claims"]
    reproduction = qualified[REPRODUCTION_CLAIM]
    original = qualified[ORIGINAL_CLAIM]
    if reproduction["finding_label"] != "reproduced":
        raise RuntimeError(reproduction["reason"])
    if reproduction["independent_observation_count"] != 1:
        raise RuntimeError("the post and appendix were counted as two records")
    keys = {item["corroboration_key"] for item in reproduction["lineage"]}
    if len(keys) != 1:
        raise RuntimeError(f"reproduction corroboration keys diverged: {sorted(keys)}")
    if "ev-lw-appendix" not in reproduction["duplicated_report_ids"]:
        raise RuntimeError("the appendix was not bound to the post's record")
    if reproduction["effect_status"] != "unobserved":
        raise RuntimeError("the reproduction record was treated as a committed effect")
    if reproduction["primary_upgrade_blocker"] is not None:
        raise RuntimeError("an unavailable original blocked the reproduction record")
    if original["finding_label"] != "unresolved":
        raise RuntimeError("the original-effect claim was qualified without a held log")
    if original["primary_upgrade_blocker"] is not None:
        raise RuntimeError("the original-effect claim was blocked by an impossible gate")
    if original["absence_of_sink_is_no_effect"] is not False:
        raise RuntimeError("a missing sink was treated as evidence of no effect")
    for claim in (reproduction, original):
        if claim["real_world_authenticity_certified"] is not False:
            raise RuntimeError("qualification certified the original incident")
        if claim["incident_detection_claimed"] or claim["incident_prevention_claimed"]:
            raise RuntimeError("qualification claimed detection or prevention")
        if any(item["digest_certifies_assertion"] for item in claim["lineage"]):
            raise RuntimeError("a digest certified an assertion")
    unavailable = {item["source_id"] for item in reproduction["unavailable_sources"]}
    if not set(NAMED_UNAVAILABLE) <= unavailable:
        raise RuntimeError("named originals are missing from the unavailable list")
    for claim in bundle["graph"]["claims"]:
        for slot in claim["evidence_slots"]:
            if slot["blocks_upgrade"]:
                raise RuntimeError(f"{slot['id']} is an upgrade gate on the saved claim")
    if any(event["event_kind"] == "committed_effect" for event in bundle["events"]):
        raise RuntimeError("a committed effect was invented")
    if any(link["confirmed_effect"] for link in bundle["reconciliation"]["links"]):
        raise RuntimeError("reconciliation confirmed an effect")
    stages = bundle["stage_summary"]
    for claim_id in (REPRODUCTION_CLAIM, ORIGINAL_CLAIM):
        if stages["stage_a"][claim_id] != stages["stage_b"][claim_id]:
            raise RuntimeError("synthetic rows changed the public qualification")
    secret = "super-secret-token"
    if secret in json.dumps(bundle["events"]):
        raise RuntimeError("a credential leaked into a normalized record")
    kinds = {event["id"]: event["event_kind"] for event in bundle["events"]}
    if kinds.get("pub-metr-command") != "narrative_report":
        raise RuntimeError("the METR excerpt was not ingested as a report")
    if kinds.get("pub-hf-correlation") != "narrative_report":
        raise RuntimeError("the Hugging Face excerpt was not ingested as a report")
    offered = set(bundle["graph"]["claims"][0]["event_ids"]) | set(
        bundle["graph"]["claims"][1]["event_ids"]
    )
    if {"ev-pub-metr-command", "ev-pub-hf-correlation"} & offered:
        raise RuntimeError("a postmortem sentence was offered as the reproduction record")


def build_bundle() -> dict:
    sources = _lineage_sources()
    missing = [source_id for source_id in (*PINNED_IDS, *UNAVAILABLE_IDS) if source_id not in sources]
    if missing:
        raise RuntimeError(f"lineage fixture is missing {missing}")
    pinned = {source_id: sources[source_id] for source_id in PINNED_IDS}
    for source_id, source in pinned.items():
        if source.get("content_digest") != content_sha256(source["public_bytes"]):
            raise RuntimeError(f"pinned digest mismatch: {source_id}")
    claims = _claims()
    public, events, reconciliation = _events(pinned)
    graph = _graph(events, sources, claims, "forensic-telemetry")
    qualified = qualify_telemetry_graph(graph)
    public_graph = _graph(public, sources, claims, "forensic-telemetry-stage-a")
    stage_a = qualify_telemetry_graph(public_graph)
    unavailable = unavailable_telemetry([sources[source_id] for source_id in UNAVAILABLE_IDS])
    unknowns = [
        *unavailable,
        {
            "source_id": "released-inspect-eval-logs",
            "event_time": None,
            "ingested_as_log": False,
            "blocks_upgrade": False,
            "note": "Released with the reproduction and not copied here.",
        },
        {
            "source_id": "issue-41-native-witness",
            "event_time": None,
            "ingested_as_log": False,
            "blocks_upgrade": False,
            "note": "Application export is not on this branch.",
        },
    ]
    packet = comparator_packet(events)
    encoded = json.dumps(packet, sort_keys=True, separators=(",", ":"))
    bundle = {
        "graph": graph,
        "events": events,
        "public_events": public,
        "reconciliation": reconciliation,
        "qualified": qualified,
        "stage_summary": blinded_stage_summary(stage_a, qualified, unknowns),
        "unavailable": unavailable,
        "unknowns": unknowns,
        "packet_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "naive_agent_row_count": sum(
            1 for event in events if event["adapter"] == "agent_tool_record"
        ),
        "lineage": normalize_lineage(graph),
    }
    _check(bundle)
    return bundle


def _run(claim_id: str, observations: dict) -> dict:
    return {
        "id": f"{claim_id.replace('_', '-')}-run",
        "claim_id": claim_id,
        "protocol_id": TELEMETRY_VERSION,
        "case_id": claim_id,
        "source_pin": TELEMETRY_VERSION,
        "execution_status": "completed",
        "observations": observations,
    }


def _finding(claim_id: str, proposition: str, scope: str, label: str, conclusion: str, method: str, refs: list[str]) -> dict:
    run_id = f"{claim_id.replace('_', '-')}-run"
    return attach_evaluation_method(
        {
            "id": f"{claim_id.replace('_', '-')}-f",
            "claim_id": claim_id,
            "run_ids": [run_id],
            "proposition": proposition,
            "scope": scope,
            "label": label,
            "basis": "computed",
            "supporting_observation_refs": [f"{run_id}.observations.{ref}" for ref in refs],
            "conclusion_class": conclusion,
        },
        method,
    )


def _claim_observations(qualification: dict) -> dict:
    return {
        "finding_label": qualification["finding_label"],
        "conclusion_class": qualification["conclusion_class"],
        "effect_status": qualification["effect_status"],
        "primary_upgrade_blocker": qualification["primary_upgrade_blocker"],
        "independent_observation_count": qualification["independent_observation_count"],
        "absence_of_sink_is_no_effect": qualification["absence_of_sink_is_no_effect"],
        "real_world_authenticity_certified": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "qualification": qualification,
    }


def build_artifacts(bundle: dict | None = None) -> dict:
    bundle = build_bundle() if bundle is None else bundle
    claims = bundle["qualified"]["claims"]
    reproduction = claims[REPRODUCTION_CLAIM]
    original = claims[ORIGINAL_CLAIM]
    method_observations = {
        "reproduction_finding_label": reproduction["finding_label"],
        "independent_observation_count": reproduction["independent_observation_count"],
        "original_finding_label": original["finding_label"],
        "confirmed_effect_count": 0,
        "blocks_upgrade_slot_count": 0,
        "unavailable_source_count": len(UNAVAILABLE_IDS),
        "real_world_authenticity_certified": False,
        "incident_detection_claimed": False,
        "incident_prevention_claimed": False,
        "comparator_packet_sha256": bundle["packet_sha256"],
        "naive_agent_row_count": bundle["naive_agent_row_count"],
        "eval_logs_copied": False,
        "native_witness_export_present": False,
        "stage_labels_match": True,
        "unknown_source_count": len(bundle["unknowns"]),
    }
    return {
        "bundle": bundle,
        "runs": {
            REPRODUCTION_CLAIM: _run(REPRODUCTION_CLAIM, _claim_observations(reproduction)),
            ORIGINAL_CLAIM: _run(ORIGINAL_CLAIM, _claim_observations(original)),
        },
        "findings": {
            REPRODUCTION_CLAIM: _finding(
                REPRODUCTION_CLAIM,
                reproduction["proposition"],
                (
                    "Pinned LessWrong post and appendix in the provenance fixture. "
                    "The OpenAI transcript dump and Hugging Face platform logs are "
                    "recorded unavailable and are not upgrade gates."
                ),
                "reproduced",
                "supported",
                "held_out_artifact_audit",
                [
                    "finding_label",
                    "independent_observation_count",
                    "effect_status",
                    "real_world_authenticity_certified",
                ],
            ),
            ORIGINAL_CLAIM: _finding(
                ORIGINAL_CLAIM,
                original["proposition"],
                (
                    "No committed-effect row is held. The missing platform logs and "
                    "transcript dump are not upgrade gates and are not evidence of no effect."
                ),
                "unresolved",
                "missing_evidence",
                "held_out_artifact_audit",
                ["finding_label", "effect_status"],
            ),
        },
        "method_run": _run(METHOD_CLAIM, method_observations),
        "method_finding": _finding(
            METHOD_CLAIM,
            (
                "Replaying forensic telemetry qualifies the LessWrong post and appendix "
                "as one public record, leaves the original-effect claim unresolved, and "
                "does not certify the incident."
            ),
            "forensic-telemetry-v1 fixture conformance",
            "reproduced",
            "supported",
            "synthetic_protocol_conformance",
            [
                "reproduction_finding_label",
                "independent_observation_count",
                "original_finding_label",
                "confirmed_effect_count",
                "blocks_upgrade_slot_count",
                "real_world_authenticity_certified",
                "incident_detection_claimed",
            ],
        ),
    }


def write_artifacts() -> None:
    artifacts = build_artifacts()
    runs = EVIDENCE / "runs"
    findings = EVIDENCE / "findings"
    runs.mkdir(parents=True, exist_ok=True)
    findings.mkdir(parents=True, exist_ok=True)
    for run in (*artifacts["runs"].values(), artifacts["method_run"]):
        (runs / f"{run['id']}.json").write_text(
            json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    for finding in (*artifacts["findings"].values(), artifacts["method_finding"]):
        (findings / f"{finding['id']}.json").write_text(
            json.dumps(finding, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    observations = artifacts["method_run"]["observations"]
    result = {
        "claim_id": METHOD_CLAIM,
        "label": "reproduced",
        "metrics": {
            "reproduction_finding_label": observations["reproduction_finding_label"],
            "independent_observation_count": observations["independent_observation_count"],
            "original_finding_label": observations["original_finding_label"],
            "confirmed_effect_count": observations["confirmed_effect_count"],
            "blocks_upgrade_slot_count": observations["blocks_upgrade_slot_count"],
            "unavailable_source_count": observations["unavailable_source_count"],
            "real_world_authenticity_certified": False,
            "incident_detection_claimed": False,
            "incident_prevention_claimed": False,
        },
        "notes": (
            "The LessWrong post and appendix qualify as one public record. "
            "The OpenAI transcript dump and Hugging Face platform logs stay "
            "unavailable and are not gates. The original incident is not certified."
        ),
    }
    (EVIDENCE / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )


if __name__ == "__main__":
    write_artifacts()
    print("wrote evidence/telemetry")
