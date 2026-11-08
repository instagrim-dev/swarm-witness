"""Required EvidenceGraph premises keep binding, holding, freshness, and derivation."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "external_calibration"))

from eg_adapter_projector import composed_observations, project_checks  # noqa: E402
from r2_event_packets import build_packets  # noqa: E402
from swarm_witness.incident_audit import swarm_witness_verdict  # noqa: E402
from swarm_witness.strong_invariant import strong_invariant_verdict  # noqa: E402

MATRIX = ROOT / "experiments" / "external_calibration" / "qualification_mutation_matrix_v1.json"


def _packet():
    def natural_key(packet):
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


def _score(claim, observations):
    assessment, projected = composed_observations(claim, observations)
    composed = list(observations) + projected
    return {
        "assessment": assessment["verdict"],
        "reason": assessment.get("reason"),
        "strong": strong_invariant_verdict(claim, composed)["epistemic_status"],
        "swarm": swarm_witness_verdict(claim, composed)["epistemic_status"],
        "projected": projected,
    }


def _mark(observations, field, value):
    copied = copy.deepcopy(observations)
    marked = False
    for row in copied:
        if "registry_mutation_record" in (row.get("observation_types") or []):
            row[field] = value
            marked = True
    assert marked
    return copied


def test_qualification_mutation_matrix_matches_both_classifiers():
    packet = _packet()
    claim = packet["claim"]
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert matrix["claim_id"] == claim["id"]
    mutations = {
        "none": packet["observations"],
        "binding=misbound": _mark(packet["observations"], "binding", "misbound"),
        "freshness=stale": _mark(packet["observations"], "freshness", "stale"),
        "locally_held=false": _mark(packet["observations"], "locally_held", False),
        "derivation=copied": _mark(packet["observations"], "derivation", "copied"),
    }
    restored = packet["observations"]
    measured = []
    for row in matrix["rows"]:
        name = row["mutation"]
        observations = restored if name.endswith("restored") or name == "none" else mutations[name]
        result = _score(claim, observations)
        assert result["assessment"] == row["assessment"], name
        assert result["strong"] == row["strong"], name
        assert result["swarm"] == row["swarm"], name
        if row["assessment"] == "unresolved":
            assert result["reason"] == row["reason"]
            assert project_checks(
                claim,
                observations,
                {"verdict": "supported", "reason": "laundered", "predicates": {}},
            ) == []
        measured.append(
            {
                "mutation": name,
                "assessment": result["assessment"],
                "strong": result["strong"],
                "swarm": result["swarm"],
            }
        )
    assert [item["mutation"] for item in measured] == [row["mutation"] for row in matrix["rows"]]
    clean = _score(claim, packet["observations"])
    qualifications = clean["projected"][0]["premise_qualifications"]
    assert qualifications
    for qual in qualifications:
        assert "binding" in qual
        assert "freshness" in qual
        assert "locally_held" in qual
        assert "derivation" in qual


def _registry_mutation(observations):
    return next(
        row
        for row in observations
        if "registry_mutation_record" in (row.get("observation_types") or [])
    )


def test_exact_duplicate_premise_keeps_the_supported_judgment():
    packet = _packet()
    claim = packet["claim"]
    original = _registry_mutation(packet["observations"])
    duplicate = copy.deepcopy(original)
    duplicate["id"] = original["id"] + "-copy"
    alone = _score(claim, packet["observations"])
    forward = _score(claim, packet["observations"] + [duplicate])
    reverse = _score(claim, [duplicate] + packet["observations"])
    assert alone["assessment"] == "supported"
    for result in (forward, reverse):
        assert result["assessment"] == "supported"
        assert result["strong"] == "supported"
        assert result["swarm"] == "supported"
        groups = {
            qual.get("independence_group")
            for qual in result["projected"][0]["premise_qualifications"]
            if "registry_mutation_record" in (qual.get("observation_types") or [])
        }
        assert groups == {original.get("independence_group")}


def test_distinct_premises_for_one_entity_conflict_independent_of_order():
    packet = _packet()
    claim = packet["claim"]
    original = _registry_mutation(packet["observations"])
    other = copy.deepcopy(original)
    other["id"] = original["id"] + "-other"
    other["independence_group"] = "other-independence-group"
    forward = _score(claim, packet["observations"] + [other])
    reverse = _score(claim, [other] + packet["observations"])
    assert forward["assessment"] == reverse["assessment"] == "unresolved"
    assert forward["reason"] == reverse["reason"] == "conflicting_premises"
    assert forward["strong"] == reverse["strong"] == "unresolved"
    assert forward["swarm"] == reverse["swarm"] == "unresolved"
