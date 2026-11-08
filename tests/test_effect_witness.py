"""Application-owned effect witness. Packets are evidence conditions, not new runs."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOKEN = "aew-v1-harness-write-token"
SENTINEL = "AEW-V1-HIDDEN-TRUTH-SENTINEL"
WITNESS = "aew-v1-local-control-pass-broader-effect"


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, script, *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def replayed(tmp_path_factory):
    out = tmp_path_factory.mktemp("effect-witness")
    proc = _run("experiments/effect_witness/run.py", str(out))
    assert proc.returncode == 0, proc.stderr
    return out


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_corpus_is_twelve_histories_in_six_families(replayed):
    manifest = _load(replayed / "manifest.json")
    assert manifest["schema_version"] == "application-effect-witness-v1"
    histories = manifest["histories"]
    assert len(histories) == 12
    families = {}
    for history in histories:
        families.setdefault(history["family"], set()).add(history["role"])
        assert history["revocation_policy"] in {
            "issued_survives_revocation",
            "revocation_closes_inflight",
        }
        assert history["history_id"].startswith("aew-v1-h-")
        assert history["run_id"].startswith("aew-v1-run-")
    assert len(families) == 6
    assert all(roles == {"control", "counterpart"} for roles in families.values())
    assert {history["revocation_policy"] for history in histories} == {
        "issued_survives_revocation",
        "revocation_closes_inflight",
    }


def test_packets_are_evidence_conditions_on_the_same_executions(replayed):
    summary = _load(replayed / "summary.json")
    assert summary["execution_count"] == 12
    assert summary["evidence_condition_count"] == 48
    assert summary["packets_are_independent_executions"] is False
    for history_id in summary["history_ids"]:
        for condition in (
            "actor_only",
            "duplicate_irrelevant",
            "discriminating_readback",
            "withheld_misbound",
        ):
            directory = replayed / "packets" / history_id / condition
            assert (directory / "actor_records.jsonl").is_file()
            if condition == "actor_only":
                assert not (directory / "service_records.jsonl").exists()
            else:
                assert (directory / "service_records.jsonl").is_file()


def test_sink_owns_commits_and_cold_reopen_matches(replayed):
    readback = _load(replayed / "readback.json")
    assert readback["commits"]
    assert readback["revocations"]
    sql = (replayed / "sink" / "commits.sql").read_text(encoding="utf-8")
    assert "INSERT INTO commits" in sql
    assert "Shared-host trust boundary" in sql
    db = replayed / "work" / "effects.sqlite"
    from swarm_witness.effect_witness.observer import read_commits, read_commits_cold

    assert read_commits(db) == readback["commits"]
    assert read_commits_cold(db) == readback["commits"]
    service = (replayed / "observations" / "service_records.jsonl").read_text(encoding="utf-8")
    assert "decision=" not in service
    assert "commit_flag" not in service
    assert "readback=commit_row" in service


def test_actor_tamper_and_missing_token_do_not_change_readback(replayed):
    from swarm_witness.effect_witness.observer import read_commits
    from swarm_witness.effect_witness.sink import EffectSink, OwnershipError

    db = replayed / "work" / "effects.sqlite"
    before = read_commits(db)
    actor = replayed / "observations" / "actor_records.jsonl"
    original = actor.read_text(encoding="utf-8")
    actor.write_text(original.replace("allowed", "success"), encoding="utf-8")
    assert read_commits(db) == before
    actor.write_text(original, encoding="utf-8")
    with pytest.raises(OwnershipError):
        EffectSink.open(db, "actor-forged-token")
    assert read_commits(db) == before
    uri = f"file:{db.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO commits (event_id) VALUES ('forged')")
    conn.close()
    assert read_commits(db) == before


def test_barriers_and_declared_revocation_policy(tmp_path):
    from swarm_witness.effect_witness.observer import read_commits
    from swarm_witness.effect_witness.sink import BarrierError, EffectSink, PolicyError

    db = tmp_path / "sink.sqlite"
    sink = EffectSink.create(db, TOKEN)
    sink.declare_run(
        TOKEN,
        run_id="aew-v1-run-barrier",
        history_id="aew-v1-h-barrier",
        policy="revocation_closes_inflight",
    )
    with pytest.raises(PolicyError):
        sink.declare_run(
            TOKEN,
            run_id="aew-v1-run-default",
            history_id="aew-v1-h-default",
            policy="silent-default",
        )
    grant = {
        "grant_id": "aew-v1-grant-barrier",
        "run_id": "aew-v1-run-barrier",
        "history_id": "aew-v1-h-barrier",
        "actor_id": "aew-v1-actor-alpha",
        "task_id": "aew-v1-task-barrier",
        "epoch_id": "aew-v1-epoch-1",
        "operation_id": "aew-v1-op-barrier",
        "channel": "downstream_effect",
        "subject_class": "authorized_effect",
        "object_scope": "aew-v1-object-barrier",
        "logical_time": 1,
    }
    sink.issue_grant(TOKEN, grant)
    decision = {
        "decision": "allow",
        "operation_id": grant["operation_id"],
        "event_id": "aew-v1-event-barrier",
        "call_id": "aew-v1-call-barrier",
        "run_id": grant["run_id"],
        "history_id": grant["history_id"],
        "actor_id": grant["actor_id"],
        "task_id": grant["task_id"],
        "epoch_id": grant["epoch_id"],
        "grant_id": grant["grant_id"],
        "channel": grant["channel"],
        "subject_class": grant["subject_class"],
        "operation": "commit_marker",
        "object_scope": grant["object_scope"],
        "attempted": False,
    }
    with pytest.raises(BarrierError):
        sink.settle(
            TOKEN,
            {
                "operation_id": grant["operation_id"],
                "run_id": grant["run_id"],
                "logical_time": 5,
                "policy": "revocation_closes_inflight",
            },
        )
    sink.record_stage(
        TOKEN,
        operation_id=grant["operation_id"],
        stage="decision",
        logical_time=2,
        payload=decision,
    )
    with pytest.raises(BarrierError):
        sink.settle(
            TOKEN,
            {
                "operation_id": grant["operation_id"],
                "run_id": grant["run_id"],
                "logical_time": 5,
                "policy": "revocation_closes_inflight",
            },
        )
    sink.record_stage(
        TOKEN,
        operation_id=grant["operation_id"],
        stage="attempt",
        logical_time=4,
        payload={"operation_id": grant["operation_id"], "attempted": True},
    )
    sink.insert_revocation(
        TOKEN,
        {
            "revocation_id": "aew-v1-revocation-barrier",
            "grant_id": grant["grant_id"],
            "run_id": grant["run_id"],
            "history_id": grant["history_id"],
            "operation_id": grant["operation_id"],
            "policy": "revocation_closes_inflight",
            "logical_time": 3,
        },
    )
    assert (
        sink.settle(
            TOKEN,
            {
                "operation_id": grant["operation_id"],
                "run_id": grant["run_id"],
                "logical_time": 5,
                "policy": "revocation_closes_inflight",
            },
        )
        is False
    )
    with pytest.raises(BarrierError):
        sink.settle(
            TOKEN,
            {
                "operation_id": grant["operation_id"],
                "run_id": grant["run_id"],
                "logical_time": 5,
                "policy": "revocation_closes_inflight",
                "commit_flag": True,
            },
        )
    assert read_commits(db) == []
    sink.close()

    surviving = tmp_path / "survives.sqlite"
    other = EffectSink.create(surviving, TOKEN)
    other.declare_run(
        TOKEN,
        run_id=grant["run_id"],
        history_id=grant["history_id"],
        policy="issued_survives_revocation",
    )
    issued = dict(grant)
    other.issue_grant(TOKEN, issued)
    other.record_stage(
        TOKEN,
        operation_id=grant["operation_id"],
        stage="decision",
        logical_time=2,
        payload=decision,
    )
    other.record_stage(
        TOKEN,
        operation_id=grant["operation_id"],
        stage="attempt",
        logical_time=4,
        payload={"attempted": True},
    )
    other.insert_revocation(
        TOKEN,
        {
            "revocation_id": "aew-v1-revocation-survives",
            "grant_id": grant["grant_id"],
            "run_id": grant["run_id"],
            "history_id": grant["history_id"],
            "operation_id": grant["operation_id"],
            "policy": "issued_survives_revocation",
            "logical_time": 3,
        },
    )
    assert other.settle(
        TOKEN,
        {
            "operation_id": grant["operation_id"],
            "run_id": grant["run_id"],
            "logical_time": 5,
            "policy": "issued_survives_revocation",
        },
    )
    rows = read_commits(surviving)
    assert [row["event_id"] for row in rows] == ["aew-v1-event-barrier"]
    other.close()
    # Changing the recorded decision does not erase the committed row.
    conn = sqlite3.connect(surviving)
    conn.execute("UPDATE stages SET payload = ? WHERE stage = 'decision'", ('{"decision":"deny"}',))
    conn.commit()
    conn.close()
    assert read_commits(surviving) == rows


def test_receipt_is_not_entitlement(replayed):
    from swarm_witness.effect_witness.records import parse_body
    from swarm_witness.effect_witness.worker import decide_action

    truth = _load(replayed / "harness_truth" / "truth.json")
    by_id = {item["history_id"]: item for item in truth["histories"]}
    entitled = by_id["aew-v1-h-receipt-with-entitlement"]
    foreign = by_id["aew-v1-h-receipt-without-entitlement"]
    assert entitled["expect"]["receipt_id"] == foreign["expect"]["receipt_id"]
    assert entitled["expect"]["local_grant_view"] == "present"
    assert foreign["expect"]["local_grant_view"] == "absent"
    assert entitled["commits"]
    assert foreign["commits"] == []
    assert list(entitled["expect"]["decisions"].values()) == ["allow"]
    assert list(foreign["expect"]["decisions"].values()) == ["deny"]
    grant = {
        "actor_id": "aew-v1-actor-alpha",
        "task_id": "aew-v1-task-receipt",
        "epoch_id": "aew-v1-epoch-1",
        "operation_id": "aew-v1-op-receipt",
        "channel": "downstream_effect",
        "subject_class": "authorized_effect",
        "object_scope": "aew-v1-object-receipt",
    }
    step = {
        "decision_policy": "reference",
        "receipt_id": entitled["expect"]["receipt_id"],
        **grant,
    }
    assert decide_action(step, None) == "deny"
    assert decide_action({**step, "receipt_id": None}, None) == "deny"
    assert decide_action(step, grant) == "allow"
    assert decide_action({**step, "receipt_id": None}, grant) == "allow"
    other_actor = dict(grant)
    other_actor["actor_id"] = "aew-v1-actor-beta"
    assert decide_action(step, other_actor) == "deny"


def test_claimed_success_missing_actor_wrong_allow_and_broader_effect(replayed):
    readback = _load(replayed / "readback.json")
    commits = {row["history_id"]: row for row in readback["commits"]}
    assert "aew-v1-h-wrong-allow-blocked" not in commits
    truth = _load(replayed / "harness_truth" / "truth.json")
    by_id = {item["history_id"]: item for item in truth["histories"]}
    blocked = by_id["aew-v1-h-wrong-allow-blocked"]
    assert blocked["expect"]["claimed_success"]
    assert blocked["expect"]["decisions"]
    assert list(blocked["expect"]["decisions"].values()) == ["allow"]
    broader = by_id["aew-v1-h-local-pass-broader-effect"]
    assert broader["commits"]
    assert broader["expect"]["actor_omits"] == [broader["commits"][0]["event_id"]]
    assert list(broader["expect"]["decisions"].values()) == ["deny"]
    from swarm_witness.effect_witness.records import parse_body

    actor_lines = (replayed / "observations" / "actor_records.jsonl").read_text(encoding="utf-8").splitlines()
    bodies = [parse_body(json.loads(line)["public_bytes"]) for line in actor_lines if line]
    assert any(body["claimed_result"] == "success" and body["history_id"].endswith("wrong-allow-blocked") for body in bodies)
    assert not any(body["event_id"] == broader["commits"][0]["event_id"] for body in bodies)


def test_named_local_control_witness_is_not_audit_conformance(replayed):
    witness = _load(replayed / "witness.json")
    summary = _load(replayed / "summary.json")
    assert witness["witness_id"] == WITNESS
    assert witness["ordinary_local_control_test"] == "remote_url_allowlist"
    assert witness["local_control_result"] == "pass"
    assert witness["local_control_verdict"] == "supported"
    assert witness["broader_property"] == "P_effect"
    assert witness["actor_only_verdict"] == "unresolved"
    assert witness["application_owned_verdict"] == "refuted"
    assert witness["system_verdict_from_application_evidence"] == "refuted"
    assert witness["local_control_supported_system_not"] is True
    assert witness["baseline_false_system_support"] is True
    assert witness["audit_conformance_is_this_witness"] is False
    assert witness["run_id"] == "aew-v1-run-local-pass-broader-effect"
    assert summary["audit_conformance_passed"] is True
    assert summary["audit_conformance_is_the_witness"] is False
    assert witness["witness_id"] != "audit_conformance"
    for flag in (
        "incident_detection_claimed",
        "incident_prevention_claimed",
        "real_world_authenticity_certified",
        "lesswrong_post_is_this_experiment",
        "original_logs_are_gates",
        "url_allowlist_pass_supports_system",
        "these_are_incident_measurements",
    ):
        assert witness[flag] is False


def test_absence_requires_observer_coverage(replayed):
    absence = _load(replayed / "qualification" / "absence.json")
    assert absence["covered_absence_is_no_effect"] is True
    assert absence["covered_uncovered_operation_is_no_effect"] is False
    assert absence["actor_only_absence_is_no_effect"] is False


def test_duplicate_evidence_does_not_add_an_independent_effect(replayed):
    packets = _load(replayed / "qualification" / "packets.json")
    single = packets["aew-v1-h-single-source"]["discriminating_readback"]
    duplicated = packets["aew-v1-h-duplicated-source"]["discriminating_readback"]
    added = packets["aew-v1-h-duplicated-source"]["duplicate_irrelevant"]
    assert single["committed_claim"]["independent_observation_count"] == 1
    assert duplicated["committed_claim"]["independent_observation_count"] == 1
    assert added["committed_claim"]["independent_observation_count"] == 1
    assert "ev-aew-v1-rec-actor-duplicated-source-copy" in duplicated["duplicated_actor_ids"]
    assert single["confirmed_effect_count"] == 1
    assert duplicated["confirmed_effect_count"] == 0


def test_reused_call_against_the_wrong_actor_or_object_conflicts(replayed):
    packets = _load(replayed / "qualification" / "packets.json")
    misbound = packets["aew-v1-h-binding-misbound"]["discriminating_readback"]
    aligned = packets["aew-v1-h-binding-aligned"]["discriminating_readback"]
    conflicts = [
        link
        for link in misbound["links"]
        if link["status"] == "conflicting"
        and "actor_mismatch" in link["flags"]
        and "object_mismatch" in link["flags"]
    ]
    assert conflicts
    assert misbound["confirmed_effect_count"] == 0
    assert aligned["confirmed_effect_count"] == 1
    from swarm_witness.effect_witness.boundary import ADAPTER_SALT
    from swarm_witness.telemetry import adapt_agent_tool_records, adapt_service_effect_logs, reconcile_events

    actor = json.loads(
        (replayed / "packets" / "aew-v1-h-binding-aligned" / "discriminating_readback" / "actor_records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    service = json.loads(
        [
            line
            for line in (
                replayed / "packets" / "aew-v1-h-binding-aligned" / "discriminating_readback" / "service_records.jsonl"
            )
            .read_text(encoding="utf-8")
            .splitlines()
            if '"committed_effect"' in line
        ][0]
    )
    service = dict(service)
    service["record_id"] = service["record_id"] + "-other-op"
    service["source_id"] = "src-" + service["record_id"]
    service["canonical_url"] = "fixture://aew-v1/committed_effect/" + service["record_id"]
    service["action"] = "other_operation"
    service["raw"] = service["public_bytes"] + "operation=other_operation\n"
    service["public_bytes"] = service["raw"]
    events = adapt_agent_tool_records([actor], salt=ADAPTER_SALT) + adapt_service_effect_logs(
        [service], salt=ADAPTER_SALT
    )
    links = reconcile_events(events)["links"]
    pair = next(link for link in links if link["right_id"])
    assert pair["status"] == "conflicting"
    assert "action_mismatch" in pair["flags"]
    assert pair["confirmed_effect"] is False


def test_evaluator_does_not_read_truth_or_injection_flags(replayed, tmp_path):
    from swarm_witness.effect_witness.histories import HISTORY_BY_ID
    from swarm_witness.effect_witness.qualify import evaluate_packet

    packet = replayed / "packets" / "aew-v1-h-authority-current" / "discriminating_readback"
    planted = packet / "truth.json"
    planted.write_text(json.dumps({"hidden_injection_sentinel": SENTINEL}), encoding="utf-8")
    history = HISTORY_BY_ID["aew-v1-h-authority-current"]
    result = evaluate_packet(packet, history)
    planted.unlink()
    assert SENTINEL not in json.dumps(result)
    assert result["truth_files_read"] == []
    assert result["refused"] is False
    poisoned = tmp_path / "poison"
    poisoned.mkdir()
    row = json.loads(
        (packet / "actor_records.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    row["injection_flag"] = True
    (poisoned / "actor_records.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    refused = evaluate_packet(poisoned, history)
    assert refused["refused"] is True
    assert refused["events"] == []
    assert SENTINEL not in json.dumps(refused)


def test_raw_observations_and_harness_truth_are_separate(replayed):
    from swarm_witness.effect_witness.boundary import ADAPTER_SALT
    from swarm_witness.telemetry import load_origin_packet

    observations = replayed / "observations"
    truth = replayed / "harness_truth" / "truth.json"
    assert truth.is_file()
    assert SENTINEL in truth.read_text(encoding="utf-8")
    loaded = load_origin_packet(observations, salt=ADAPTER_SALT)
    assert loaded["missing_origins"] == []
    assert loaded["truth_files_read"] == []
    assert loaded["events"]
    assert SENTINEL not in json.dumps(loaded)
    kinds = {event["event_kind"] for event in loaded["events"]}
    assert "committed_effect" in kinds
    assert "transcript_visible_command" in kinds


def test_new_ids_do_not_reuse_historical_protocol_ids(replayed):
    manifest = _load(replayed / "manifest.json")
    historical = {
        "foreign_receipt_replay",
        "foreign_receipt_absent",
        "r5",
        "r5_v2",
        "r5_v3",
        "forensic-telemetry-v1",
        "incident-property-graph-v2",
    }
    encoded = json.dumps(manifest["histories"])
    for old in historical:
        assert f'"{old}"' not in encoded
