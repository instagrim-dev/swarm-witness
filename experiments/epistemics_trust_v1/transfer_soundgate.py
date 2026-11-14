"""Empirical transfer onto SoundGate R1, a platform outside the twelve histories.

The effect-field consumer reads the same SoundGate field the warrant uses.
Its match is fidelity to that field, not a second adjudicator. The intact-run
consumer does not read the field. That difference is the measurement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "evidence" / "r1" / "local-run-analysis.json"
SOURCE_REVISION = "656840348dcf9660f8db7add9f3ca9f794a55926"


def _score(rows: list[dict[str, Any]], predicted_key: str) -> dict[str, int]:
    unsupported = 0
    false_support = 0
    correct_decisive = 0
    decisive = 0
    for row in rows:
        predicted = row[predicted_key]
        warrant = row["warrant"]
        if warrant in {"supported", "refuted"}:
            decisive += 1
            if predicted == warrant:
                correct_decisive += 1
        if predicted == "supported" and warrant != "supported":
            unsupported += 1
        if predicted == "supported" and row["proposition_holds"] is False:
            false_support += 1
    return {
        "rows": len(rows),
        "unsupported_supports": unsupported,
        "false_proposition_supports": false_support,
        "correct_decisive": correct_decisive,
        "decisive_opportunities": decisive,
    }


PROTOCOL_WARRANTS = {
    "barrier": {
        "warrant": "supported",
        "source": "experiments/r1/README.md",
        "quote": "prohibited_effects == 0` under the **recovery barrier** policy",
    },
    "original": {
        "warrant": "refuted",
        "source": "baselines/r1_wal_recover_before_admit.md",
        "quote": "original 0.1.3 recovery losing an acknowledged",
    },
}


def _bytes(kind: str, history: str, fields: dict[str, str]) -> str:
    lines = [f"sg-r1 {kind}", "record_class=soundgate_r1", f"history_id={history}"]
    lines.extend(f"{key}={value}" for key, value in fields.items())
    return "\n".join(lines) + "\n"


def _project_policy(policy: str, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Effect records for one policy. The protocol warrant is not copied in."""
    history = f"sg-r1-{policy}"
    run = f"sg-run-{policy}"
    operation = f"sg-op-{policy}"
    actor_body = _bytes(
        "actor",
        history,
        {
            "run_id": run,
            "operation_id": operation,
            "event_id": f"sg-event-{policy}",
            "call_id": f"sg-call-{policy}",
            "actor_id": "sg-actor",
            "object_scope": f"sg-object-{policy}",
        },
    )
    records = [
        {
            "record_id": f"sg-actor-{policy}",
            "surface": "requested_command",
            "action": "commit_marker",
            "locally_held": True,
            "custody": "intact",
            "actor_binding": "bound",
            "access_level": "public_bytes",
            "redaction": "none",
            "authenticity": "not_checked",
            "event_time": "2026-04-01T00:01:42Z",
            "public_bytes": actor_body,
        }
    ]
    prohibited = [row for row in cases if row["policy"] == policy and row["status"] == "prohibited_effect"]
    coverage_body = _bytes(
        "coverage",
        history,
        {
            "run_id": run,
            "operations": operation,
            "interval_start": "2026-04-01T00:01:40Z",
            "interval_end": "2026-04-01T00:03:20Z",
            "row_count": "0" if not prohibited else str(len(prohibited)),
        },
    )
    records.append(
        {
            "record_id": f"sg-cov-{policy}",
            "surface": "service_log",
            "action": "coverage_scan",
            "locally_held": True,
            "custody": "intact",
            "access_level": "public_bytes",
            "redaction": "none",
            "authenticity": "not_checked",
            "public_bytes": coverage_body,
        }
    )
    for index, _row in enumerate(prohibited):
        sink_body = _bytes(
            "sink",
            history,
            {
                "run_id": run,
                "operation_id": operation,
                "event_id": f"sg-event-{policy}",
                "call_id": f"sg-call-{policy}",
                "actor_id": "sg-actor",
                "object_scope": f"sg-object-{policy}",
                "subject_class": "unauthorized_effect",
            },
        )
        records.append(
            {
                "record_id": f"sg-sink-{policy}-{index}",
                "surface": "committed_effect",
                "action": "commit_marker",
                "locally_held": True,
                "custody": "intact",
                "actor_binding": "bound",
                "access_level": "public_bytes",
                "redaction": "none",
                "authenticity": "not_checked",
                "event_time": "2026-04-01T00:01:50Z",
                "parent_id": f"sg-actor-{policy}",
                "public_bytes": sink_body,
            }
        )
    return records


def _projection_verdict(history: str, records: list[dict[str, Any]]) -> str:
    from swarm_witness.native_comparison import p_effect_claim_id, project_packet_observations

    observations = project_packet_observations(history, records)
    claim = p_effect_claim_id(history)
    polarities = [
        obs.get("literal_polarity")
        for obs in observations
        if claim in (obs.get("literal_claims") or [])
    ]
    if "refutes" in polarities:
        return "refuted"
    if "supports" in polarities:
        return "supported"
    return "unresolved"


def protocol_transfer(root: Path | None = None) -> dict[str, Any]:
    """Score the existing projection against SoundGate's protocol sentences.

    The warrant text is the README success criterion and the stated original-policy
    bug. Case status is used only to build effect records.
    """
    base = ROOT if root is None else Path(root)
    data = json.loads((base / "evidence" / "r1" / "local-run-analysis.json").read_text(encoding="utf-8"))
    claims = []
    for policy, spec in PROTOCOL_WARRANTS.items():
        source = (base / spec["source"]).read_text(encoding="utf-8")
        if spec["quote"] not in source:
            raise RuntimeError(f"protocol warrant missing from {spec['source']}")
        records = _project_policy(policy, data["cases"])
        history = f"sg-r1-{policy}"
        projection = _projection_verdict(history, records)
        intact = "supported" if any(
            record.get("surface") == "requested_command" and record.get("public_bytes")
            for record in records
        ) else "unresolved"
        claims.append(
            {
                "policy": policy,
                "history": history,
                "warrant": spec["warrant"],
                "warrant_source": spec["source"],
                "projection": projection,
                "intact_run": intact,
                "matches_projection": projection == spec["warrant"],
                "intact_run_unsupported_support": intact == "supported" and spec["warrant"] != "supported",
                "prohibited_records": sum(
                    1 for row in data["cases"] if row["policy"] == policy and row["status"] == "prohibited_effect"
                ),
            }
        )
    return {
        "external_empirical_transfer": "soundgate_protocol_claims",
        "platform": "SoundGate",
        "source_revision": SOURCE_REVISION,
        "claims": claims,
        "projection_matches": all(row["matches_projection"] for row in claims),
        "intact_run_unsupported_supports": sum(row["intact_run_unsupported_support"] for row in claims),
        "relation_to_48": "separate",
        "relation_to_16": "separate",
        "does_not_establish": [
            "full-platform equivalence",
            "a protocol warrant for the strict policy",
            "that the November experiments change from not_tested",
        ],
    }


def measure(root: Path | None = None) -> dict[str, Any]:
    path = (ROOT if root is None else Path(root)) / "evidence" / "r1" / "local-run-analysis.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data["cases"]
    cuts = {(row["family"], row["cut"]) for row in cases}
    policies = {row["policy"] for row in cases}
    if any(str(row.get("id", "")).startswith("aew-v1-") for row in cases):
        raise RuntimeError("SoundGate analysis contains an application-history id")
    restriction: list[dict[str, Any]] = []
    availability: list[dict[str, Any]] = []
    for row in cases:
        status = row["status"]
        restriction.append(
            {
                "id": row["id"],
                "policy": row["policy"],
                "intact_run": "supported" if row["record_bytes"] > 0 and row["policy"] else "unresolved",
                "effect_field": "refuted" if status == "prohibited_effect" else "supported",
                "warrant": "refuted" if status == "prohibited_effect" else "supported",
                "proposition_holds": status != "prohibited_effect",
            }
        )
        fresh = bool(row["fresh_work"])
        availability.append(
            {
                "id": row["id"],
                "policy": row["policy"],
                "intact_run": "supported" if row["record_bytes"] > 0 and row["policy"] else "unresolved",
                "effect_field": "supported" if fresh else "refuted",
                "warrant": "supported" if fresh else "refuted",
                "proposition_holds": fresh,
            }
        )
    return {
        "external_empirical_transfer": "tested_on_soundgate_r1",
        "platform": "SoundGate",
        "source_revision": SOURCE_REVISION,
        "analysis": "evidence/r1/local-run-analysis.json",
        "dependence": f"{len(cuts)} cuts under {len(policies)} policies",
        "rows": len(cases),
        "relation_to_48": "separate",
        "relation_to_16": "separate",
        "restriction": {
            "proposition": "no prohibited effect on this retained row",
            "intact_run": _score(restriction, "intact_run"),
            "effect_field": _score(restriction, "effect_field"),
        },
        "availability": {
            "proposition": "permitted work still runs on this retained row",
            "intact_run": _score(availability, "intact_run"),
            "effect_field": _score(availability, "effect_field"),
        },
        "does_not_establish": [
            "that the effect-field match is an independent adjudicator",
            "full-platform equivalence",
            "that the November experiments change from not_tested",
        ],
    }
