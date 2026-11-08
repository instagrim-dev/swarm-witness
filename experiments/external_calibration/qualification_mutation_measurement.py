"""Measured qualification matrix: raw mutations, projections, and both methods.

The expected-outcome file is not this record. Each row keeps the observations
that were scored and the verdicts those observations produced.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))

from eg_adapter_projector import composed_observations, project_checks  # noqa: E402
from r2_event_packets import build_packets  # noqa: E402
from swarm_witness.incident_audit import swarm_witness_verdict  # noqa: E402
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402

MATRIX = ROOT / "experiments" / "external_calibration" / "qualification_mutation_matrix_v1.json"
MEASUREMENT = (
    ROOT / "evidence" / "external_calibration_v1" / "qualification_mutation_matrix_v1.json"
)


def _packet() -> dict[str, Any]:
    def natural_key(packet: dict[str, Any]) -> str | None:
        for obs in packet["observations"]:
            if "registry_mutation_record" in (obs.get("observation_types") or []):
                return (obs.get("entity") or {}).get("natural_key")
        return None

    return next(
        packet
        for packet in build_packets()
        if packet["claim"]["scenario"] == "clean"
        and packet["claim"]["family"] == "event_attribution"
        and natural_key(packet) == "event-000007"
    )


def _score(claim: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    assessment, projected = composed_observations(claim, observations)
    composed = list(observations) + projected
    return {
        "assessment": assessment["verdict"],
        "reason": assessment.get("reason"),
        "strong": strong_invariant_verdict(claim, composed)["epistemic_status"],
        "swarm": swarm_witness_verdict(claim, composed)["epistemic_status"],
        "projected": projected,
        "forced_projection_empty": project_checks(
            claim,
            observations,
            {"verdict": "supported", "reason": "laundered", "predicates": {}},
        )
        == [],
    }


def _mark(observations: list[dict[str, Any]], field: str, value: Any) -> list[dict[str, Any]]:
    copied = copy.deepcopy(observations)
    marked = False
    for row in copied:
        if "registry_mutation_record" in (row.get("observation_types") or []):
            row[field] = value
            marked = True
    if not marked:
        raise ValueError(field)
    return copied


def measure() -> dict[str, Any]:
    packet = _packet()
    claim = packet["claim"]
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    mutations = {
        "none": packet["observations"],
        "binding=misbound": _mark(packet["observations"], "binding", "misbound"),
        "freshness=stale": _mark(packet["observations"], "freshness", "stale"),
        "locally_held=false": _mark(packet["observations"], "locally_held", False),
        "derivation=copied": _mark(packet["observations"], "derivation", "copied"),
    }
    rows = []
    for spec in matrix["rows"]:
        name = spec["mutation"]
        observations = (
            packet["observations"]
            if name.endswith("restored") or name == "none"
            else mutations[name]
        )
        scored = _score(claim, observations)
        rows.append(
            {
                "mutation": name,
                "raw_observations": observations,
                "projected_observations": scored["projected"],
                "assessment": scored["assessment"],
                "reason": scored["reason"],
                "strong": scored["strong"],
                "swarm": scored["swarm"],
                "forced_projection_empty": scored["forced_projection_empty"],
            }
        )
    return {
        "protocol_id": "eg-qualification-mutation-v1",
        "claim_id": claim["id"],
        "family": claim["family"],
        "note": (
            "Measured raw observations, projected observations, and both "
            "composed-method outputs. The expected-outcome matrix is a separate file."
        ),
        "rows": rows,
    }


def main() -> None:
    document = measure()
    MEASUREMENT.parent.mkdir(parents=True, exist_ok=True)
    MEASUREMENT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(MEASUREMENT)


if __name__ == "__main__":
    main()
