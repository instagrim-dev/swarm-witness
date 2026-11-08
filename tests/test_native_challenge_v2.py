"""The v2 challenge keeps v1 frozen and separates rejection from a verdict."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "experiments" / "effect_witness" / "native_projection_challenge_v2.py"
V1_LEDGER = (
    ROOT
    / "evidence"
    / "effect_witness_v1"
    / "native_projection_challenge_v1"
    / "ledger.json"
)
INVALID = (
    "sink-misbound",
    "sink-spoofed",
    "sink-unauthenticated",
    "sink-run-mismatch",
    "sink-actor-mismatch",
    "sink-object-mismatch",
    "sink-mapped-actor-mismatch",
)
MALFORMED = (
    "mixed-unknown-authorization",
    "sink-unknown-subject",
    "coverage-withheld",
)


def _runner():
    spec = importlib.util.spec_from_file_location("native_projection_challenge_v2", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_invalid_sink_premises_are_not_decisive(tmp_path: Path):
    document = _runner().evaluate_challenge_v2(ROOT, tmp_path)
    rows = {row["case_id"]: row for row in document["rows"]}
    assert document["case_count"] == 16
    assert set(rows) == {row["case_id"] for row in json.loads(V1_LEDGER.read_text())["rows"]}
    for case_id in INVALID:
        row = rows[case_id]
        assert row["execution_status"] == "completed"
        assert row["epistemic_status"] == "unresolved"
        assert row["epistemic_status"] not in {"supported", "refuted"}
        assert row["rejected_ids"]
        assert row["reasons"]
    assert rows["clean-positive"]["epistemic_status"] == "supported"
    assert rows["clean-positive"]["matches_warrant"] is True


def test_duplicate_is_not_a_verdict_and_malformed_input_stays_rejected(tmp_path: Path):
    before = V1_LEDGER.read_bytes()
    document = _runner().evaluate_challenge_v2(ROOT, tmp_path)
    assert V1_LEDGER.read_bytes() == before
    rows = {row["case_id"]: row for row in document["rows"]}
    duplicate = rows["coverage-duplicate"]
    assert duplicate["execution_status"] == "completed"
    assert duplicate["epistemic_status"] == "supported"
    assert "exact_duplicate_not_independent" in duplicate["reasons"]
    for case_id in MALFORMED:
        row = rows[case_id]
        assert row["execution_status"] == "rejected"
        assert row["epistemic_status"] is None
        assert row["raw_error"]
        assert row["matches_warrant"] is False
        assert row["admission"] == "not_evaluated"
        assert row["admitted_ids"] == []
        assert row["rejected_ids"] == []


def test_unverified_sink_binding_cannot_support_safety(tmp_path: Path):
    challenge = importlib.util.spec_from_file_location(
        "native_projection_challenge_v1",
        ROOT / "experiments" / "effect_witness" / "native_projection_challenge.py",
    )
    assert challenge and challenge.loader
    module = importlib.util.module_from_spec(challenge)
    challenge.loader.exec_module(module)
    history_id, _condition = module.yaml.safe_load(module.CHALLENGE.read_text())[
        "source_packet"
    ].split("/", 1)
    base = module.build_cases(history_id)["clean-positive"]
    from swarm_witness.effect_witness.histories import HISTORY_BY_ID
    from swarm_witness.effect_witness.qualify import evaluate_packet

    mutations = {
        "call": ({"call_id": "aew-v1-call-unbound"}, "unbound_call"),
        "tuple": (
            {
                "actor_id": "aew-v1-actor-other",
                "object_scope": "aew-v1-object-other",
                "event_id": "aew-v1-event-other",
            },
            "identity_mismatch",
        ),
        "operation": ({"operation": "other_operation"}, "operation_mismatch"),
    }
    for name, (updates, reason) in mutations.items():
        records = copy.deepcopy(base)
        module._replace_body(module._sink(records), **updates)
        directory = tmp_path / name
        module.swarm_witness_status(history_id, records, directory)
        result = evaluate_packet(directory, HISTORY_BY_ID[history_id])
        assert result["property"]["child_verdicts"]["P_effect"] != "supported"
        assert [item["reason"] for item in result["sink_rejections"]] == [reason]
