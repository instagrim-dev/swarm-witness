"""Coordination labels stay on the provenance lineage."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from swarm_witness.coordination import (
    COORDINATION_VERSION,
    LABELS,
    attribute_stream,
    attribute_synthetic_scale,
    qualify_case,
    validate_case,
)
from swarm_witness.provenance import CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _bundle():
    qualify = _load("coordination_qualify", ROOT / "experiments" / "coordination" / "qualify.py")
    controls = _load("coordination_controls", ROOT / "experiments" / "coordination" / "controls.py")
    graph, cases = qualify.load_inputs()
    qualified = {case["id"]: qualify_case(case, graph) for case in cases}
    return graph, cases, qualified, controls


def test_labels_and_contract_versions():
    assert LABELS == {
        "communication_observed",
        "delegation_evidenced",
        "goal_adoption_inferred",
        "causal_contribution_unresolved",
    }
    assert COORDINATION_VERSION == "coordination-attribution-v1"
    assert CONTRACT_VERSION == "evidence-provenance-v1"


def test_incident_propositions_stay_unresolved():
    graph, _cases, qualified, controls = _bundle()
    controls.check_incident_blockers(graph, qualified)
    board = qualified["coord_board_participation"]
    work = qualified["coord_delegated_workstream"]
    impact = qualified["coord_collective_impact"]
    assert board["independence_groups"] == ["openai-artifactory-message-board-dump"]
    reported = next(row for row in board["populations"] if row["unit"] == "agents")
    assert reported["count"] == 1200
    assert reported["count_label"] == "investigator_reported"
    assert reported["held_by_audit"] is False
    assert reported["traced_causal_actors"] is False
    processed = next(row for row in board["populations"] if row["directly_processed"])
    assert processed["count"] == 2
    assert board["traced_causal_actor_count"] == 0
    assert "duplicate_report" in board["unsupported_seams"]
    assert "missing_agent_instances" in board["unsupported_seams"]
    assert work["edges"][0]["link_class"] == "investigator_inference"
    assert {row["source_id"] for row in work["unavailable_telemetry"]} >= {"src-transcript-dump"}
    assert impact["edges"][-1]["labels"] == ["causal_contribution_unresolved"]
    assert all(edge["event_time"] is None for edge in impact["edges"])
    assert "upgrade_blocker_remains" in impact["unsupported_seams"]
    for result in (board, work, impact):
        assert result["provenance_contract"] == CONTRACT_VERSION
        assert result["finding_label"] == "unresolved"
        assert result["supported_while_blocked"] is False
        assert result["added_claim_qualification_value"] is False


def test_foreign_log_does_not_clear_incident_blockers():
    graph, _cases, _qualified, controls = _bundle()
    foreign = controls.foreign_log_does_not_upgrade(graph)
    assert foreign["effect"]["primary_upgrade_blocker"] == "src-hf-platform-logs"
    assert foreign["effect"]["augmented_finding_label"] == "unresolved"
    assert foreign["effect"]["added"] is False
    assert foreign["spoof"]["primary_upgrade_blocker"] == "src-transcript-dump"
    assert foreign["spoof"]["augmented_finding_label"] == "unresolved"
    assert foreign["spoof"]["added"] is False
    assert foreign["effect"]["refused_blocked_support"] is False
    assert foreign["spoof"]["refused_blocked_support"] is False


def test_negative_controls_and_distinctions():
    _graph, _cases, _qualified, controls = _bundle()
    summary = controls.check_controls()
    assert summary["negative_controls_passed"] is True
    assert summary["negative_controls"] == 6
    assert summary["synthetic_added_value_detected"] is True
    assert summary["scale_pairs_considered"] == 1200
    assert summary["scale_messages"] == 70000
    assert summary["scale_all_pairs"] == 719400
    assert summary["scale_agent_pair_matrix_allocated"] is False
    handoff = controls._qualify(controls.traced_handoff_case)
    assert handoff["real_world_authenticity_certified"] is False
    assert handoff["incident_detection_claimed"] is False
    assert handoff["finding_label"] == "reproduced"
    assert handoff["primary_upgrade_blocker"] is None


def test_scale_stream_rejects_incident_ids_and_skips_all_pairs():
    small = attribute_synthetic_scale(n_agents=4, n_messages=10, n_handoffs=3, seed=1)
    assert small["records_visited"] == 10
    assert small["pairs_considered"] == 3
    assert small["all_pairs"] == 6
    assert small["population_label"] == "synthetic"
    with pytest.raises(ValueError):
        attribute_stream(
            [
                {
                    "record_label": "synthetic",
                    "incident_record": False,
                    "message_id": "src-board-dump",
                    "kind": "handoff",
                }
            ]
        )


def test_edges_must_cite_lineage_and_cannot_invent_a_clock():
    graph, cases, _qualified, _controls = _bundle()
    broken = yaml.safe_load(yaml.safe_dump(cases[0]))
    broken["edges"][0]["provenance_event_ids"] = ["ev-missing"]
    with pytest.raises(ValueError, match="dangling provenance event"):
        validate_case(broken, graph)
    clock = yaml.safe_load(yaml.safe_dump(cases[0]))
    clock["observed_times"][0]["event_time"] = "2026-07-01T00:00:00Z"
    with pytest.raises(ValueError, match="unknown observed_time field"):
        validate_case(clock, graph)


def test_regenerated_artifacts_match_the_fixture():
    qualify = _load("coordination_qualify_disk", ROOT / "experiments" / "coordination" / "qualify.py")
    artifacts = qualify.build_artifacts()
    for case_id, run in artifacts["runs"].items():
        on_disk = json.loads(
            (ROOT / "evidence" / "coordination" / "runs" / f"{run['id']}.json").read_text()
        )
        assert on_disk == run
        finding = artifacts["findings"][case_id]
        stored = json.loads(
            (ROOT / "evidence" / "coordination" / "findings" / f"{finding['id']}.json").read_text()
        )
        assert stored == finding
        assert stored["label"] == "unresolved"
        assert run["observations"]["supported_while_blocked"] is False
        assert run["observations"]["underlying_telemetry"] == "unavailable"
    method = json.loads(
        (
            ROOT / "evidence" / "coordination" / "runs" / "coordination-attribution-v1-run.json"
        ).read_text()
    )
    assert method == artifacts["method_run"]
    assert method["observations"]["incident_unresolved"] == 3
    assert method["observations"]["incident_detection_claimed"] is False
