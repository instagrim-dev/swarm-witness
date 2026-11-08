#!/usr/bin/env python3
"""Render the bounded comparison tables from retained evidence.

This script does not rescore qualifiers and does not replace frozen runs.
Headline counts are copied from the retained summaries and matrices.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.incident_audit import score_category  # noqa: E402
from swarm_witness.native_comparison import (  # noqa: E402
    competent_verdict,
    conclusion_class_for_verdict,
    score_native_method,
)
OUT = ROOT / "report" / "bounded_comparison_v1"

FROZEN_SUMMARY = ROOT / "evidence" / "incident_comparison_v1" / "summary.json"
FROZEN_MATRIX = ROOT / "evidence" / "incident_comparison_v1" / "matrix.json"
FROZEN_DIGESTS = ROOT / "artifacts" / "incident_comparison_v1" / "input_sha256.json"
STAGED_SUMMARY = ROOT / "evidence" / "incident_audit_v1" / "summary.json"
STAGED_MATRIX = ROOT / "evidence" / "incident_audit_v1" / "matrix.json"
EFFECT_SUMMARY = ROOT / "evidence" / "effect_witness_v1" / "summary.json"
EFFECT_WITNESS = ROOT / "evidence" / "effect_witness_v1" / "witness.json"
EFFECT_PACKETS = ROOT / "evidence" / "effect_witness_v1" / "qualification" / "packets.json"
# Table N reads this frozen qualification. Replay may rewrite packets.json.
HISTORICAL_PACKETS = (
    ROOT / "experiments" / "effect_witness" / "historical_qualification_packets_v1.json"
)
BINDING_SUMMARY = ROOT / "evidence" / "evidence_binding_v1" / "summary.json"
NATIVE_WARRANTS = ROOT / "experiments" / "effect_witness" / "native_warrants_v1.yaml"
HARNESS_TRUTH = ROOT / "evidence" / "effect_witness_v1" / "harness_truth" / "truth.json"
PACKET_ROOT = ROOT / "evidence" / "effect_witness_v1" / "packets"
AUDIT_PROTOCOL = ROOT / "experiments" / "incident_audit" / "protocol_v1.yaml"
NATIVE_METHODS = ("swarm_witness", "always_unresolved", "strong_invariant")

WITNESS_ID = "aew-v1-local-control-pass-broader-effect"
HISTORY_ID = "aew-v1-h-local-pass-broader-effect"
CLEAN_HISTORY = "aew-v1-h-authority-current"

SUMMARY_FIELDS = (
    "cell_count",
    "unsupported_support",
    "unsupported_refutation",
    "correct_abstention",
    "correct_decisive",
    "decisive_opportunities",
    "correct_decisive_coverage",
    "false_proposition_support",
    "false_proposition_refutation",
    "unsupported_attribution",
    "unique_origin_cases",
    "correct_concrete_origin",
    "correct_attribution_coverage",
    "attribution_abstentions",
    "concrete_assignments",
    "accuracy_among_concrete_assignments",
    "record_requests",
    "processing_time_seconds",
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rate(value: Any, numerator: int, denominator: int) -> str:
    if value is None or denominator == 0:
        return f"not applicable ({numerator}/{denominator})"
    return f"{numerator}/{denominator}"


def _cell(row: dict[str, Any], field: str) -> str:
    value = row.get(field)
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _summary_lines(layer: str, methods: dict[str, Any]) -> list[str]:
    header = (
        "| Method | Cells | Unsupported support | Unsupported refutation | "
        "Correct abstention | Correct decisive | Decisive coverage | "
        "False-proposition support | Unsupported attribution | "
        "Attribution coverage | Attribution abstentions | "
        "Accuracy among concrete assignments | Record requests | Processing seconds |"
    )
    rule = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    body = [header, rule]
    for name, row in methods.items():
        if not isinstance(row, dict) or "cell_count" not in row:
            continue
        body.append(
            "| {name} | {cells} | {us} | {ur} | {abs_} | {cd} | {cov} | {fps} | "
            "{ua} | {acov} | {aabs} | {acc} | {req} | {sec} |".format(
                name=name,
                cells=row["cell_count"],
                us=row["unsupported_support"],
                ur=row["unsupported_refutation"],
                abs_=row["correct_abstention"],
                cd=f"{row['correct_decisive']}/{row['decisive_opportunities']}",
                cov=_rate(
                    row["correct_decisive_coverage"],
                    row["correct_decisive"],
                    row["decisive_opportunities"],
                ),
                fps="" if row["false_proposition_support"] is None else row["false_proposition_support"],
                ua=row["unsupported_attribution"],
                acov=_rate(
                    row["correct_attribution_coverage"],
                    row["correct_concrete_origin"],
                    row["unique_origin_cases"],
                ),
                aabs=row["attribution_abstentions"],
                acc=_rate(
                    row["accuracy_among_concrete_assignments"],
                    row["correct_concrete_origin"],
                    row["concrete_assignments"],
                ),
                req=row["record_requests"],
                sec=f"{row['processing_time_seconds']:.6g}",
            )
        )
    return body


def _pair_status(rows: list[dict[str, Any]], left: str, right: str) -> dict[str, Any]:
    keyed: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        keyed.setdefault((row["claim_id"], row["stage"]), {})[row["method"]] = row["predicted"]
    mismatches = []
    for key, methods in sorted(keyed.items()):
        if methods.get(left) != methods.get(right):
            mismatches.append(
                {"claim_id": key[0], "stage": key[1], left: methods.get(left), right: methods.get(right)}
            )
    return {"cells": len(keyed), "mismatches": mismatches}


def _ledger_rows(layer: str, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    published = []
    for row in rows:
        published.append(
            {
                "layer": layer,
                "claim_id": _cell(row, "claim_id"),
                "history": _cell(row, "history"),
                "stage": _cell(row, "stage"),
                "method": _cell(row, "method"),
                "predicted": _cell(row, "predicted"),
                "adjudicated": _cell(row, "adjudicated"),
                "category": _cell(row, "category"),
                "attributed_origin": _cell(row, "attributed_origin"),
                "warranted_origin": _cell(row, "warranted_origin"),
                "proposition_holds": _cell(row, "proposition_holds"),
                "observation_ids": " ".join(row.get("observation_ids") or []),
                "certifies_original_incident": _cell(row, "certifies_original_incident"),
                "conclusion_class": _cell(row, "conclusion_class"),
                "prompt_sha256": _cell(row, "prompt_sha256"),
            }
        )
    return published


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _packet_records(root: Path, history_id: str, condition: str) -> list[dict[str, Any]]:
    directory = root / PACKET_ROOT.relative_to(ROOT) / history_id / condition
    return _load_jsonl(directory / "actor_records.jsonl") + _load_jsonl(
        directory / "service_records.jsonl"
    )


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(path for path in root.rglob("*.jsonl") if path.is_file())
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _check_native_warrants(warrants: dict[str, Any], truth: dict[str, Any], packets: dict[str, Any]) -> None:
    """The warrant file is the specification. Harness commits only check it."""
    by_history = {row["history_id"]: row for row in truth["histories"]}
    if set(warrants["histories"]) != set(packets):
        raise SystemExit("native warrants do not cover the retained histories")
    for history_id, spec in warrants["histories"].items():
        commits = by_history[history_id]["commits"]
        unauthorized = any(row["subject_class"] == "unauthorized_effect" for row in commits)
        if bool(spec["proposition_holds"]) == unauthorized:
            raise SystemExit(f"{history_id}: controlled truth disagrees with harness commits")
        stages = spec["stages"]
        if stages["actor_only"] != "unresolved" or stages["withheld_misbound"] != "unresolved":
            raise SystemExit(f"{history_id}: incomplete evidence was given a decisive warrant")
        expected = "supported" if spec["proposition_holds"] else "refuted"
        if stages["discriminating_readback"] != expected or stages["duplicate_irrelevant"] != expected:
            raise SystemExit(f"{history_id}: sink stages do not warrant the controlled truth")


def _native_matched_rows(
    root: Path,
    packets: dict[str, Any],
    warrants: dict[str, Any],
    protocol: dict[str, Any],
) -> list[dict[str, Any]]:
    """Score retained packets against specified warrants.

    Swarm Witness contributes its retained P_effect verdict. The competent
    comparator is run on the same packet records. Neither side is the warrant.
    """
    rows: list[dict[str, Any]] = []
    for history_id, conditions in sorted(packets.items()):
        spec = warrants["histories"][history_id]
        for condition, packet in sorted(conditions.items()):
            warrant = spec["stages"][condition]
            holds = bool(spec["proposition_holds"])
            prop = packet.get("property") or {}
            predicted_sw = prop.get("child_verdicts", {}).get("P_effect", "unresolved")
            records = _packet_records(root, history_id, condition)
            strong = competent_verdict(history_id, records)
            observation_ids = list(strong["observation_ids"])
            for method in NATIVE_METHODS:
                if method == "swarm_witness":
                    predicted = predicted_sw
                elif method == "always_unresolved":
                    predicted = "unresolved"
                else:
                    predicted = strong["epistemic_status"]
                rows.append(
                    {
                        "claim_id": f"{history_id}:{condition}:P_effect",
                        "history": history_id,
                        "stage": condition,
                        "method": method,
                        "predicted": predicted,
                        "adjudicated": warrant,
                        "category": score_category(predicted, warrant, protocol),
                        "attributed_origin": "undetermined",
                        "warranted_origin": "undetermined",
                        "proposition_holds": holds,
                        "observation_ids": observation_ids,
                        "certifies_original_incident": False,
                        "conclusion_class": conclusion_class_for_verdict(predicted),
                        "prompt_sha256": "",
                    }
                )
    return rows


def _native_method_summary(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Table N. Native matched-method comparison",
        "",
        "Denominator: twelve application-owned histories × four evidence conditions "
        "(`actor_only`, `discriminating_readback`, `duplicate_irrelevant`, "
        "`withheld_misbound`), scored for `P_effect`. Evidence-stage warrants and "
        "controlled truth are `experiments/effect_witness/native_warrants_v1.yaml`. "
        "They are not Swarm Witness verdicts. `actor_only` and `withheld_misbound` "
        "warrant unresolved. The two stages that still contain the application sink "
        "warrant the controlled-truth status. `strong_invariant` is run on the "
        "retained packet records. Swarm Witness contributes its retained `P_effect` "
        "verdict from `experiments/effect_witness/historical_qualification_packets_v1.json`. "
        "Replaying the witness does not rewrite that file. This layer is separate from Tables P, C, S, and A. "
        "`superiority_claim` remains false. `external_empirical_transfer` is not tested, and the retained `transfer_claim` flag records that scope limit. "
        "Classifier–adapter agreement on retained EvidenceGraph packets is not "
        "scored here and is not a set of independently correct judgments.",
        "",
        "| Method | Cells | Unsupported support | Correct decisive | Decisive coverage | Correct abstention |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method in NATIVE_METHODS:
        summary = score_native_method(rows, method)
        lines.append(
            "| {method} | {cells} | {us} | {cd}/{opp} | {cov} | {abs_} |".format(
                method=method,
                cells=summary["cell_count"],
                us=summary["unsupported_support"],
                cd=summary["correct_decisive"],
                opp=summary["decisive_opportunities"],
                cov=_rate(
                    summary["correct_decisive_coverage"],
                    summary["correct_decisive"],
                    summary["decisive_opportunities"],
                ),
                abs_=summary["correct_abstention"],
            )
        )
    swarm = [row for row in rows if row["method"] == "swarm_witness"]
    strong = {
        row["claim_id"]: row["predicted"]
        for row in rows
        if row["method"] == "strong_invariant"
    }
    mismatches = sum(1 for row in swarm if strong.get(row["claim_id"]) != row["predicted"])
    readback = [row for row in swarm if row["stage"] == "discriminating_readback"]
    swarm_readback = sum(1 for row in readback if row["predicted"] == row["adjudicated"])
    strong_readback = sum(
        1
        for row in rows
        if row["method"] == "strong_invariant"
        and row["stage"] == "discriminating_readback"
        and row["predicted"] == row["adjudicated"]
    )
    lines.extend(
        [
            "",
            f"Swarm Witness vs strong invariant: {len(swarm)} cells, "
            f"{mismatches} predicted-status mismatches. On the discriminating-readback "
            f"stage, Swarm Witness matches the specified warrant on "
            f"{swarm_readback}/{len(readback)} and the competent comparator matches it on "
            f"{strong_readback}/{len(readback)}. Those counts are measured against the "
            "warrant file. They are not copied from one method to the other. "
            "Predicting support on `actor_only` does not add a verifying observation, "
            "so that prediction is unsupported support. "
            "`superiority_claim` remains false.",
            "",
        ]
    )
    return lines


def _current_evaluator_rows(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Score the packet files with the current evaluator.

    Table N keeps the retained verdicts. This replay does not replace them.
    """
    import time

    from swarm_witness.effect_witness.histories import HISTORY_BY_ID
    from swarm_witness.effect_witness.qualify import evaluate_packet

    warrants = yaml.safe_load(
        (root / NATIVE_WARRANTS.relative_to(ROOT)).read_text(encoding="utf-8")
    )
    protocol = yaml.safe_load(
        (root / AUDIT_PROTOCOL.relative_to(ROOT)).read_text(encoding="utf-8")
    )
    packets = _load(root / HISTORICAL_PACKETS.relative_to(ROOT))
    rows: list[dict[str, Any]] = []
    prevented_retained = 0
    prevented_current = 0
    supplied_records = 0
    consumed_records = 0
    started = time.perf_counter()
    for history_id, conditions in sorted(packets.items()):
        history = HISTORY_BY_ID[history_id]
        spec = warrants["histories"][history_id]
        holds = bool(spec["proposition_holds"])
        for condition in sorted(conditions):
            directory = root / PACKET_ROOT.relative_to(ROOT) / history_id / condition
            for name in ("actor_records.jsonl", "service_records.jsonl"):
                path = directory / name
                if path.is_file():
                    supplied_records += sum(
                        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
                    )
            result = evaluate_packet(directory, history)
            consumed_records += int(result.get("event_count") or 0)
            retained_labels = (
                ((conditions[condition].get("property") or {}).get("commitment_by_event")) or {}
            )
            current_labels = (result.get("property") or {}).get("commitment_by_event") or {}
            if condition == "actor_only" and "prevented" in retained_labels.values():
                prevented_retained += 1
            if condition == "actor_only" and "prevented" in current_labels.values():
                prevented_current += 1
            warrant = spec["stages"][condition]
            predicted_sw = result["property"]["child_verdicts"]["P_effect"]
            records = _packet_records(root, history_id, condition)
            strong = competent_verdict(history_id, records)
            for method in NATIVE_METHODS:
                if method == "swarm_witness":
                    predicted = predicted_sw
                elif method == "always_unresolved":
                    predicted = "unresolved"
                else:
                    predicted = strong["epistemic_status"]
                rows.append(
                    {
                        "claim_id": f"{history_id}:{condition}:P_effect",
                        "history": history_id,
                        "stage": condition,
                        "method": method,
                        "predicted": predicted,
                        "adjudicated": warrant,
                        "category": score_category(predicted, warrant, protocol),
                        "attributed_origin": "undetermined",
                        "warranted_origin": "undetermined",
                        "proposition_holds": holds,
                        "observation_ids": list(strong["observation_ids"]),
                        "certifies_original_incident": False,
                        "conclusion_class": conclusion_class_for_verdict(predicted),
                        "prompt_sha256": "",
                    }
                )
    elapsed = time.perf_counter() - started
    meta = {
        "protocol_id": "native-evaluator-replay-v2",
        "replaces_table_n": False,
        "histories": 12,
        "packets": 48,
        "method_rows": len(rows),
        "actor_only_prevented_in_retained_packets": prevented_retained,
        "actor_only_prevented_under_current_evaluator": prevented_current,
        "supplied_records": supplied_records,
        "consumed_records": consumed_records,
        "additional_source_requests": 0,
        "processing_time_seconds": elapsed,
        "attribution": "not_evaluated",
        "attribution_denominator": "not_applicable",
        "packet_tree_sha256": _tree_sha256(root / PACKET_ROOT.relative_to(ROOT)),
        "warrant_sha256": hashlib.sha256(
            (root / NATIVE_WARRANTS.relative_to(ROOT)).read_bytes()
        ).hexdigest(),
        "evaluator_sha256": {
            name: hashlib.sha256((root / "src" / "swarm_witness" / name).read_bytes()).hexdigest()
            for name in (
                "effect_witness/qualify.py",
                "native_comparison.py",
                "evidence_binding.py",
            )
        },
    }
    return rows, meta


def _current_replay_section(rows: list[dict[str, Any]], meta: dict[str, Any]) -> list[str]:
    lines = [
        "## Table N2. Current evaluator replay",
        "",
        "This replay scores the same 48 packet files with the current evaluator. "
        "It does not replace Table N. Table N remains the retained comparison: "
        "Swarm Witness 11 unsupported supports, 24/24 correct decisive. "
        "Denominators are 12 histories, 48 packets, and 144 method rows. "
        "Status, abstention, coverage, and factual error stay separate columns. "
        "Attribution is not evaluated on this native layer, so an attribution "
        "denominator is not applicable. The replay reads the supplied packet "
        f"records ({meta['supplied_records']} supplied, {meta['consumed_records']} "
        "consumed) and makes 0 additional source requests. "
        f"The retained actor-only diagnostics label commitment prevented in "
        f"{meta['actor_only_prevented_in_retained_packets']}/12 packets. The current "
        f"evaluator labels prevented in "
        f"{meta['actor_only_prevented_under_current_evaluator']}/12 of those packets; "
        "an incomplete observation is unobserved. "
        "`superiority_claim` remains false. `external_empirical_transfer` is not tested, and the retained `transfer_claim` flag records that scope limit.",
        "",
        "| Method | Cells | Unsupported support | Unsupported refutation | Correct decisive | Decisive coverage | Correct abstention | False proposition support |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method in NATIVE_METHODS:
        summary = score_native_method(rows, method)
        lines.append(
            "| {method} | {cells} | {us} | {ur} | {cd}/{opp} | {cov} | {abs_} | {false_s} |".format(
                method=method,
                cells=summary["cell_count"],
                us=summary["unsupported_support"],
                ur=summary["unsupported_refutation"],
                cd=summary["correct_decisive"],
                opp=summary["decisive_opportunities"],
                cov=_rate(
                    summary["correct_decisive_coverage"],
                    summary["correct_decisive"],
                    summary["decisive_opportunities"],
                ),
                abs_=summary["correct_abstention"],
                false_s=summary["false_proposition_support"],
            )
        )
    lines.extend(
        [
            "",
            "Processing time and the pinned packet, warrant, and evaluator digests "
            "are `report/bounded_comparison_v1/evaluator_replay_v2.json`.",
            "",
        ]
    )
    return lines


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "layer",
        "claim_id",
        "history",
        "stage",
        "method",
        "predicted",
        "adjudicated",
        "category",
        "attributed_origin",
        "warranted_origin",
        "proposition_holds",
        "observation_ids",
        "certifies_original_incident",
        "conclusion_class",
        "prompt_sha256",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _effect_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| History | P_url | P_effect | System | URL allowlist | Commits |",
        "|---|---|---|---|---|---|",
    ]
    for row in summary["properties"]:
        commits = ", ".join(
            f"{event.removeprefix('aew-v1-event-')}:{status}"
            for event, status in row["commitment_by_event"].items()
        )
        lines.append(
            "| {case} | {url} | {effect} | {system} | {allow} | {commits} |".format(
                case=row["case_id"],
                url=row["child_verdicts"]["P_url"],
                effect=row["child_verdicts"]["P_effect"],
                system=row["system_verdict"],
                allow=row["local_control_verdicts"]["remote_url_allowlist"],
                commits=commits,
            )
        )
    return lines


def _public_prediction(rows: list[dict[str, Any]], claim_id: str, stage: str, method: str) -> str:
    for row in rows:
        if row["claim_id"] == claim_id and row["stage"] == stage and row["method"] == method:
            return str(row["predicted"])
    raise KeyError((claim_id, stage, method))


def _worked_example(
    packets: dict[str, Any], witness: dict[str, Any], public_rows: list[dict[str, Any]]
) -> list[str]:
    history = packets[HISTORY_ID]
    before = history["actor_only"]["property"]
    after = history["discriminating_readback"]["property"]
    clean = packets[CLEAN_HISTORY]["discriminating_readback"]["property"]
    c04_strong = _public_prediction(public_rows, "C04", "B", "strong_invariant")
    c04_swarm = _public_prediction(public_rows, "C04", "B", "swarm_witness")
    c04_warrant = next(
        row["adjudicated"]
        for row in public_rows
        if row["claim_id"] == "C04" and row["stage"] == "B" and row["method"] == "swarm_witness"
    )
    if c04_strong != "unresolved" or c04_swarm != "unresolved" or c04_warrant != "unresolved":
        raise SystemExit("C04 stage B is adjudicated; refusing to publish it as unresolved")
    lines = [
        "The discriminating source on the named witness is the application-owned sink readback. "
        "The actor transcript is the before packet. The readback is the after packet. "
        "No other source is required for the `P_effect` change.",
        "",
        "| Example | Packet | Comparator | Swarm Witness `P_effect` | `P_url` / allowlist | `P_system` | Adjudication retained in the packet |",
        "|---|---|---|---|---|---|---|",
        (
            f"| Clean success `{CLEAN_HISTORY}` | application readback | "
            f"local control is not the system claim | {clean['child_verdicts']['P_effect']} | "
            f"{clean['child_verdicts']['P_url']} / {clean['local_control_verdicts']['remote_url_allowlist']} | "
            f"{clean['system_verdict']} | effect supported on the covered commit; system stays unresolved |"
        ),
        (
            f"| Contaminated before `{witness['witness_id']}` | actor-only | "
            f"baseline system {before['baseline_system']} (false system support {str(before['baseline_false_system_support']).lower()}) | "
            f"{before['child_verdicts']['P_effect']} | {before['child_verdicts']['P_url']} / "
            f"{before['local_control_verdicts']['remote_url_allowlist']} | {before['system_verdict']} | "
            "actor-only `P_effect` unresolved; allowlist pass is not `P_system` |"
        ),
        (
            f"| Contaminated after `{witness['witness_id']}` | application readback | "
            f"baseline system {after['baseline_system']} (false system support {str(after['baseline_false_system_support']).lower()}) | "
            f"{after['child_verdicts']['P_effect']} | {after['child_verdicts']['P_url']} / "
            f"{after['local_control_verdicts']['remote_url_allowlist']} | {after['system_verdict']} | "
            "readback refutes `P_effect`; allowlist stays supported |"
        ),
        (
            "| Unresolved public `C04` stage B | public excerpts, stage B | "
            f"strong checker {c04_strong}; Swarm Witness {c04_swarm} | "
            f"{c04_swarm} | not a URL cell | {c04_swarm} | "
            f"adjudicated {c04_warrant}; not upgraded |"
        ),
    ]
    return lines


def render(root: Path = ROOT) -> dict[str, Any]:
    frozen = _load(root / FROZEN_SUMMARY.relative_to(ROOT))
    matrix = _load(root / FROZEN_MATRIX.relative_to(ROOT))
    digests = _load(root / FROZEN_DIGESTS.relative_to(ROOT))
    staged = _load(root / STAGED_SUMMARY.relative_to(ROOT))
    staged_matrix = _load(root / STAGED_MATRIX.relative_to(ROOT))
    effect = _load(root / EFFECT_SUMMARY.relative_to(ROOT))
    witness = _load(root / EFFECT_WITNESS.relative_to(ROOT))
    packets = _load(root / EFFECT_PACKETS.relative_to(ROOT))
    binding = _load(root / BINDING_SUMMARY.relative_to(ROOT))
    warrants = yaml.safe_load((root / NATIVE_WARRANTS.relative_to(ROOT)).read_text(encoding="utf-8"))
    harness_truth = _load(root / HARNESS_TRUTH.relative_to(ROOT))
    audit_protocol = yaml.safe_load((root / AUDIT_PROTOCOL.relative_to(ROOT)).read_text(encoding="utf-8"))
    _check_native_warrants(warrants, harness_truth, packets)

    public_tie = _pair_status(matrix["public"], "strong_invariant", "swarm_witness")
    controlled_tie = _pair_status(matrix["controlled"], "strong_invariant", "swarm_witness")
    if public_tie["mismatches"] or controlled_tie["mismatches"]:
        raise SystemExit("retained matrix does not tie Swarm Witness to the strong checker")
    if witness["witness_id"] != WITNESS_ID:
        raise SystemExit("named witness id changed")
    if effect["witness"]["actor_only_verdict"] != "unresolved":
        raise SystemExit("actor-only witness verdict is not unresolved")
    if effect["witness"]["application_owned_verdict"] != "refuted":
        raise SystemExit("application readback does not refute the named witness")
    if binding["retained_p_system_epistemic"] != "refuted":
        raise SystemExit("url_held_worker_local_read does not refute P_system")
    if binding["retained_p_url_epistemic"] != "supported":
        raise SystemExit("URL allowlist on the retained workflow is not supported")
    if binding["native_epistemic"] != "unresolved":
        raise SystemExit("native telemetry packet is not unresolved")

    out = root / OUT.relative_to(ROOT)
    out.mkdir(parents=True, exist_ok=True)
    ledger = _ledger_rows("public_warrants", matrix["public"])
    ledger.extend(_ledger_rows("controlled_comparison", matrix["controlled"]))
    ledger.extend(_ledger_rows("staged_author_curated", staged_matrix["rows"]))
    historical_packets = _load(root / HISTORICAL_PACKETS.relative_to(ROOT))
    native_rows = _native_matched_rows(root, historical_packets, warrants, audit_protocol)
    current_rows, current_meta = _current_evaluator_rows(root)
    if current_meta["method_rows"] != 144:
        raise SystemExit("current evaluator replay did not score 144 method rows")
    if current_meta["actor_only_prevented_in_retained_packets"] != 12:
        raise SystemExit("retained actor-only prevented diagnostics are not the historical twelve")
    if current_meta["actor_only_prevented_under_current_evaluator"] != 0:
        raise SystemExit("current evaluator still labels an actor-only commitment prevented")
    ledger.extend(_ledger_rows("native_matched_methods", native_rows))
    ledger.extend(_ledger_rows("native_evaluator_replay_v2", current_rows))
    (out / "evaluator_replay_v2.json").write_text(
        json.dumps({"meta": current_meta, "rows": current_rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    if not native_rows:
        raise SystemExit("native matched-method layer produced zero rows")
    _write_csv(out / "ledger.csv", ledger)
    native_meta = {
        "layer": "native_matched_methods",
        "row_count": len(native_rows),
        "methods": sorted({row["method"] for row in native_rows}),
        "history_count": len({row["history"] for row in native_rows}),
        "condition_count": len({row["stage"] for row in native_rows}),
        "note": (
            "Retained P_effect verdicts and strong_invariant on the same packet "
            "records, scored against experiments/effect_witness/native_warrants_v1.yaml. "
            "superiority_claim is false. external_empirical_transfer is not_tested. "
            "transfer_claim records that scope limit."
        ),
        "superiority_claim": False,
        "transfer_claim": False,
        "external_empirical_transfer": "not_tested",
    }
    (out / "native_matched_methods.json").write_text(
        json.dumps(native_meta, indent=2) + "\n",
        encoding="utf-8",
    )

    sources = {
        "frozen_summary": _sha256(root / FROZEN_SUMMARY.relative_to(ROOT)),
        "frozen_matrix": _sha256(root / FROZEN_MATRIX.relative_to(ROOT)),
        "staged_summary": _sha256(root / STAGED_SUMMARY.relative_to(ROOT)),
        "staged_matrix": _sha256(root / STAGED_MATRIX.relative_to(ROOT)),
        "effect_summary": _sha256(root / EFFECT_SUMMARY.relative_to(ROOT)),
        "effect_witness": _sha256(root / EFFECT_WITNESS.relative_to(ROOT)),
        "effect_packets": _sha256(root / EFFECT_PACKETS.relative_to(ROOT)),
        "historical_qualification_packets": _sha256(
            root / HISTORICAL_PACKETS.relative_to(ROOT)
        ),
        "binding_summary": _sha256(root / BINDING_SUMMARY.relative_to(ROOT)),
        "frozen_input_sha256": _sha256(root / FROZEN_DIGESTS.relative_to(ROOT)),
        "native_warrants": _sha256(root / NATIVE_WARRANTS.relative_to(ROOT)),
        "native_packet_records": _tree_sha256(root / PACKET_ROOT.relative_to(ROOT)),
    }
    (out / "source_sha256.json").write_text(
        json.dumps({"retained_files": sources, "frozen_inputs": digests}, indent=2) + "\n",
        encoding="utf-8",
    )

    public = frozen["layers"]["public"]
    controlled = frozen["layers"]["controlled"]
    naive_public = public["naive"]["unsupported_support"]
    strong_public = public["strong_invariant"]["unsupported_support"]
    swarm_public = public["swarm_witness"]["unsupported_support"]
    lines = [
        "# Bounded comparative study tables",
        "",
        "Generated by `scripts/render_bounded_comparison.py`. Public and controlled "
        "layers use retained outputs; native methods evaluate the retained packets. "
        "Frozen processing times are preserved.",
        "",
        "Public warrants, the controlled comparison, and the application-owned "
        "twelve-history witness are separate tables and separate denominators. "
        "The LessWrong reproduction post and its appendix are one public record. "
        "They are not the original incident and not the twelve-history experiment. "
        "Unavailable original transcripts and platform logs are recorded in the "
        "lineage block and are not qualification gates.",
        "",
        f"Frozen public finding: Swarm Witness matches the strong checker on all "
        f"{public_tie['cells']} public cells. Unsupported supports are naive PASS "
        f"{naive_public}, strong checker {strong_public}, Swarm Witness {swarm_public}. "
        "The comparison does not establish superiority.",
        "",
        "Unsupported attribution is counted over every scored cell, including cells "
        "whose warranted origin is undetermined. A concrete origin that is not the "
        "warranted origin counts. An undetermined assignment is an abstention. "
        "Correct attribution coverage is correct concrete-origin assignments divided "
        "by cells whose warranted origin is uniquely determined. An always-undetermined "
        "method scores 0 when that denominator is positive. A zero denominator is "
        "not applicable, and the raw counts are kept.",
        "",
        "The earlier staged comparison remains in its own table. It is author-curated. "
        "Mechanical withholding of later-stage evidence is not independent curation. "
        "That table is not replaced by the strong-checker tie.",
        "",
        "## Table P. Public warrants",
        "",
        "Denominator: twelve public claims at two stages. Truth of the world-effect "
        "propositions is not known from the public record, so false-proposition "
        "support is not applicable. Protocol `experiments/incident_audit/comparison` "
        "is not used for this layer; the integrated evaluator reads "
        "`claims/incident_claims_v1.yaml`, `experiments/incident_audit/excerpts_v1.yaml`, "
        "and `experiments/incident_audit/adjudication_v1.yaml`.",
        "",
        *_summary_lines("public", public),
        "",
        f"Strong-checker tie: {public_tie['cells']} cells, 0 predicted-status mismatches. "
        f"Record requests are {public['swarm_witness']['record_requests']}.",
        "",
        "## Table C. Controlled comparison",
        "",
        "Denominator: four claims about the held LessWrong record and the released "
        "step-1 signature extract, over three histories. This is not the twelve-claim "
        "public layer and not the twelve-history application witness. Protocol "
        "`experiments/incident_audit/comparison/protocol_v1.yaml`. Warrants "
        "`experiments/incident_audit/comparison/warrants_v1.yaml`, applied only after "
        "the qualifiers return.",
        "",
        *_summary_lines("controlled", controlled),
        "",
        f"Strong-checker tie: {controlled_tie['cells']} cells, 0 predicted-status mismatches. "
        "Strong checker and Swarm Witness abstain on `K-certify` and on the held "
        "`blocks_upgrade` slot `K-gate`.",
        "",
        "## Table S. Earlier author-curated staged comparison",
        "",
        "Denominator: the same twelve public claims at two stages, scored against "
        "naive PASS and a weak checklist. The strong checker is not in this table. "
        "Retained finding `evidence/incident_audit_v1/findings/incident-audit-v1-f-comparison.json` "
        "still records fewer unsupported conclusions than those two baselines. "
        "That sentence is this earlier comparison, not a superiority claim over the strong checker.",
        "",
        "| Method | Unsupported conclusions / 24 |",
        "|---|---:|",
        f"| Naive PASS | {staged['naive_unsupported']} |",
        f"| Weak checklist | {staged['checklist_unsupported']} |",
        f"| Swarm Witness | {staged['swarm_witness_unsupported']} |",
        "",
        "Declared ablations, retained rather than dropped:",
        "",
        "| Ablation | Retained result |",
        "|---|---|",
        f"| Treating dependent public text as telemetry | unsupported conclusions {staged['ablation_text_trust_unsupported']} |",
        f"| Withholding stage B on C03 | {staged['ablation_stage_a_c03']} |",
        f"| Withholding stage B on C05 | {staged['ablation_stage_a_c05']} |",
        f"| Collapsing the allowlist into the whole-worker property at stage A | {staged['ablation_scope_collapse_c05_a']} |",
        f"| Counting the synthetic blurb as its own support group on C12 | {staged['ablation_dependency_c12_groups']} groups |",
        "",
        f"C04 stage B stays {staged['ambiguous_c04_stage_b']}. "
        f"C06 stage B stays {staged['c06_stage_b_epistemic']}. "
        "Public propositions that the warrants do not adjudicate stay unresolved.",
        "",
        "## Table A. Application-owned twelve-history witness",
        "",
        "Denominator: twelve histories, one execution each, on a SQLite sink the "
        "application owns. These rows are not public warrants and not the controlled "
        "LessWrong layer. `audit_conformance_passed` is not this witness.",
        "",
        *_effect_table(effect),
        "",
        f"Named same-run witness `{witness['witness_id']}` on `{witness['run_id']}`: "
        f"ordinary test `{witness['ordinary_local_control_test']}` "
        f"{witness['local_control_result']}; actor-only `P_effect` "
        f"{witness['actor_only_verdict']}; application readback "
        f"{witness['application_owned_verdict']}. "
        "`url_allowlist_pass_supports_system` is false. "
        "A passing allowlist does not support `P_system`.",
        "",
        "## Worked examples",
        "",
        *_worked_example(packets, witness, matrix["public"]),
        "",
        *_native_method_summary(native_rows),
        *_current_replay_section(current_rows, current_meta),
        "## Table E. Retained workflow and native telemetry",
        "",
        "These two rows are not the twelve-history witness and not the 24-cell public layer.",
        "",
        "| Case | Verdict |",
        "|---|---|",
        (
            f"| `{binding['retained_case_id']}` `P_system` | {binding['retained_p_system_epistemic']} "
            f"({binding['retained_p_system_conclusion']}) |"
        ),
        f"| `{binding['retained_case_id']}` `P_url` | {binding['retained_p_url_epistemic']} |",
        (
            f"| native telemetry packet | {binding['native_epistemic']} "
            f"({binding['native_evidence_status']}); events {binding['native_packet_event_count']}; "
            "truth files read 0 |"
        ),
        "",
        "`url_held_worker_local_read` refutes `P_system` while the URL allowlist stays supported. "
        "The native telemetry packet stays unresolved.",
        "",
        "## Lineage exclusions",
        "",
        "The frozen lineage records one independent observation for the reproduction "
        "release and zero supported original-incident claims. Duplicated report "
        f"`{frozen['layers']['lineage']['reproduction_duplicated_reports'][0]}` stays inside "
        "that one record. Unavailable sources: "
        + ", ".join(frozen["layers"]["lineage"]["reproduction_unavailable"])
        + ". They are not upgrade gates. `real_world_authenticity_certified` is false. "
        "`detection_or_prevention_claimed` is false.",
        "",
        "Post-freeze note: this renderer reads the retained summaries. It does not "
        "overwrite an unfavorable tie, and it does not drop the staged ablations.",
        "",
        "## Source digests",
        "",
        "Frozen comparison inputs (`artifacts/incident_comparison_v1/input_sha256.json`):",
        "",
    ]
    for name, digest in digests.items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.extend(["", "Retained files hashed at render time:", ""])
    for name, digest in sources.items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.extend(
        [
            "",
            "Per-case outputs for every method, including the staged rows and the "
            "native matched-method layer, are "
            "`report/bounded_comparison_v1/ledger.csv`. "
            f"Ledger rows: {len(ledger)} "
            f"(native matched-method rows: {len(native_rows)}).",
            "",
        ]
    )
    text = "\n".join(lines)
    (out / "TABLES.md").write_text(text, encoding="utf-8")
    return {
        "ledger_rows": len(ledger),
        "native_matched_rows": len(native_rows),
        "public_tie_cells": public_tie["cells"],
        "public_naive_unsupported_support": naive_public,
        "public_strong_unsupported_support": strong_public,
        "public_swarm_unsupported_support": swarm_public,
        "witness_id": witness["witness_id"],
        "tables": str(out / "TABLES.md"),
        "native_rows": native_rows,
        "native_swarm_unsupported_support": score_native_method(native_rows, "swarm_witness")[
            "unsupported_support"
        ],
        "native_swarm_correct_decisive": score_native_method(native_rows, "swarm_witness")[
            "correct_decisive"
        ],
        "native_strong_unsupported_support": score_native_method(native_rows, "strong_invariant")[
            "unsupported_support"
        ],
        "native_strong_correct_decisive": score_native_method(native_rows, "strong_invariant")[
            "correct_decisive"
        ],
    }


def main() -> int:
    result = render()
    hidden = {"tables", "native_rows"}
    print(json.dumps({key: result[key] for key in result if key not in hidden}, indent=2))
    print(f"wrote {result['tables']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
