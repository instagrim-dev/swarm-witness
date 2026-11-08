"""Native projection must not launder an invalid premise into a bound readback.

The 48-packet warrant stays the published comparison. Challenge cases have
their own ledger and are not scored by agreement with Swarm Witness.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import yaml

from swarm_witness.effect_witness.histories import HISTORY_BY_ID
from swarm_witness.native_comparison import competent_verdict, project_packet_observations

_CHALLENGE_PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "effect_witness"
    / "native_projection_challenge.py"
)
_spec = importlib.util.spec_from_file_location("native_projection_challenge", _CHALLENGE_PATH)
assert _spec and _spec.loader
_challenge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_challenge)
build_cases = _challenge.build_cases
paired_ledger = _challenge.paired_ledger
LEDGER = _challenge.LEDGER

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "evidence" / "effect_witness_v1" / "packets"
WARRANTS = ROOT / "experiments" / "effect_witness" / "native_warrants_v1.yaml"
CHALLENGE = ROOT / "experiments" / "effect_witness" / "native_projection_challenge_v1.yaml"
CONDITIONS = (
    "actor_only",
    "discriminating_readback",
    "duplicate_irrelevant",
    "withheld_misbound",
)


def _records(history_id: str, condition: str) -> list[dict]:
    directory = PACKETS / history_id / condition
    rows = []
    for name in ("actor_records.jsonl", "service_records.jsonl"):
        path = directory / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _sink(records: list[dict]) -> dict:
    return next(row for row in records if row.get("surface") == "committed_effect")


def _coverage(records: list[dict]) -> dict:
    return next(row for row in records if row.get("action") == "coverage_scan")


def _replace_body(record: dict, **updates: str) -> None:
    fields = {}
    for line in str(record["public_bytes"]).splitlines():
        if "=" in line and not line.startswith("aew-v1 "):
            key, value = line.split("=", 1)
            fields[key] = value
    fields.update(updates)
    header = str(record["public_bytes"]).splitlines()[0]
    rendered = header + "\n" + "".join(f"{key}={value}\n" for key, value in fields.items())
    record["public_bytes"] = rendered
    record["raw"] = rendered


def test_unchanged_corpus_keeps_the_strong_warrant():
    warrants = yaml.safe_load(WARRANTS.read_text(encoding="utf-8"))
    unsupported_support = 0
    unsupported_refutation = 0
    correct_decisive = 0
    correct_abstention = 0
    for history_id in sorted(HISTORY_BY_ID):
        spec = warrants["histories"][history_id]
        for condition in CONDITIONS:
            predicted = competent_verdict(history_id, _records(history_id, condition))[
                "epistemic_status"
            ]
            warrant = spec["stages"][condition]
            if predicted != warrant:
                raise AssertionError(f"{history_id} {condition}: {predicted} != {warrant}")
            if predicted == "supported" and warrant != "supported":
                unsupported_support += 1
            if predicted == "refuted" and warrant != "refuted":
                unsupported_refutation += 1
            if predicted == warrant and predicted in {"supported", "refuted"}:
                correct_decisive += 1
            if predicted == warrant == "unresolved":
                correct_abstention += 1
    assert unsupported_support == 0
    assert unsupported_refutation == 0
    assert correct_decisive == 24
    assert correct_abstention == 24


def test_projection_challenge_uses_its_own_warrants():
    ledger = yaml.safe_load(CHALLENGE.read_text(encoding="utf-8"))
    history_id, _condition = ledger["source_packet"].split("/", 1)
    base = _records(history_id, "discriminating_readback")
    expected = {case_id: case["expected"] for case_id, case in ledger["cases"].items()}
    cases = build_cases(history_id)

    def status(records: list[dict]) -> str:
        return competent_verdict(history_id, records)["epistemic_status"]

    assert _sink(cases["sink-mapped-actor-mismatch"]).get("parent_id")
    coherent = copy.deepcopy(base)
    _replace_body(
        _sink(coherent),
        actor_id="aew-v1-actor-other",
        object_scope="aew-v1-object-other",
        event_id="aew-v1-event-other",
    )
    _sink(coherent)["actor"] = "aew-v1-actor-other"
    _sink(coherent)["object"] = "aew-v1-object-other"
    assert status(coherent) == "supported"

    mixed = cases["mixed-unknown-authorization"]
    extra = next(row for row in mixed if str(row.get("record_id", "")).endswith("-unknown"))
    without_extra = [row for row in mixed if row is not extra]
    assert status(mixed) == status([extra] + without_extra)

    conflict = cases["coverage-conflict"]
    other = next(row for row in conflict if str(row.get("record_id", "")).endswith("-other"))
    without_other = [row for row in conflict if row is not other]
    assert status(conflict) == status([other] + without_other)

    assert set(cases) == set(expected)
    for case_id, records in cases.items():
        predicted = status(records)
        assert predicted == expected[case_id], case_id
        if case_id == "sink-misbound":
            projected = project_packet_observations(history_id, records)
            sink_obs = next(obs for obs in projected if obs["id"].endswith("-misbound"))
            assert sink_obs["binding"] == "misbound"
            assert sink_obs["literal_polarity"] != "supports"
        if case_id == "sink-spoofed":
            projected = project_packet_observations(history_id, records)
            sink_obs = next(obs for obs in projected if obs["id"] == _sink(records)["record_id"])
            assert sink_obs["authenticity"] == "spoofed_tool_line"
            assert sink_obs["authenticity"] != "application_owned_readback"


def test_retained_challenge_ledger_scores_both_methods(tmp_path: Path):
    retained = json.loads(LEDGER.read_text(encoding="utf-8"))
    fresh = paired_ledger(tmp_path)
    assert fresh["agreement_is_not_the_label"] is True
    assert fresh["case_count"] == 16
    assert fresh == retained
    assert all(row["competent_matches_warrant"] for row in fresh["rows"])
