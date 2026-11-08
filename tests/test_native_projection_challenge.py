"""Native projection must not launder an invalid premise into a bound readback.

The 48-packet warrant stays the published comparison. Challenge cases have
their own ledger and are not scored by agreement with Swarm Witness.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from swarm_witness.effect_witness.histories import HISTORY_BY_ID
from swarm_witness.native_comparison import competent_verdict, project_packet_observations

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

    def status(records: list[dict]) -> str:
        return competent_verdict(history_id, records)["epistemic_status"]

    cases: dict[str, list[dict]] = {"clean-positive": copy.deepcopy(base)}

    misbound = copy.deepcopy(base)
    sink = _sink(misbound)
    sink["record_id"] = sink["record_id"] + "-misbound"
    cases["sink-misbound"] = misbound

    spoofed = copy.deepcopy(base)
    _sink(spoofed)["authenticity"] = "spoofed_tool_line"
    cases["sink-spoofed"] = spoofed

    unauthenticated = copy.deepcopy(base)
    _sink(unauthenticated)["authenticity"] = "unauthenticated_tool_line"
    cases["sink-unauthenticated"] = unauthenticated

    stale = copy.deepcopy(base)
    _sink(stale)["freshness"] = "stale"
    cases["sink-stale"] = stale

    wrong_run = copy.deepcopy(base)
    _replace_body(_sink(wrong_run), run_id="aew-v1-run-other")
    cases["sink-run-mismatch"] = wrong_run

    wrong_actor = copy.deepcopy(base)
    _replace_body(_sink(wrong_actor), actor_id="aew-v1-actor-other")
    _sink(wrong_actor)["actor"] = "aew-v1-actor-other"
    _sink(wrong_actor)["parent_id"] = None
    cases["sink-actor-mismatch"] = wrong_actor

    wrong_object = copy.deepcopy(base)
    _replace_body(_sink(wrong_object), object_scope="aew-v1-object-other")
    _sink(wrong_object)["object"] = "aew-v1-object-other"
    _sink(wrong_object)["parent_id"] = None
    cases["sink-object-mismatch"] = wrong_object

    mapped_actor = copy.deepcopy(base)
    _replace_body(_sink(mapped_actor), actor_id="aew-v1-actor-other")
    _sink(mapped_actor)["actor"] = "aew-v1-actor-other"
    cases["sink-mapped-actor-mismatch"] = mapped_actor

    mixed = copy.deepcopy(base)
    extra = copy.deepcopy(_sink(mixed))
    extra["record_id"] = extra["record_id"] + "-unknown"
    extra["source_id"] = "src-" + extra["record_id"]
    _replace_body(extra, subject_class="unknown")
    _replace_body(_coverage(mixed), row_count="2")
    cases["mixed-unknown-authorization"] = mixed + [extra]
    reversed_mixed = [extra] + mixed
    assert status(cases["mixed-unknown-authorization"]) == status(reversed_mixed)

    conflict = copy.deepcopy(base)
    other = copy.deepcopy(_coverage(conflict))
    other["record_id"] = other["record_id"] + "-other"
    other["source_id"] = "src-" + other["record_id"]
    _replace_body(other, row_count="0")
    cases["coverage-conflict"] = conflict + [other]
    assert status(cases["coverage-conflict"]) == status([other] + conflict)

    duplicate = copy.deepcopy(base)
    copied = copy.deepcopy(_coverage(duplicate))
    copied["record_id"] = copied["record_id"] + "-copy"
    copied["source_id"] = "src-" + copied["record_id"]
    cases["coverage-duplicate"] = duplicate + [copied]

    unknown = copy.deepcopy(base)
    _replace_body(_sink(unknown), subject_class="unknown")
    cases["sink-unknown-subject"] = unknown

    wrong_operation = copy.deepcopy(base)
    _replace_body(_coverage(wrong_operation), operations="aew-v1-op-not-the-target")
    cases["coverage-operation-mismatch"] = wrong_operation

    outside = copy.deepcopy(base)
    _replace_body(
        _coverage(outside),
        interval_start="2030-01-01T00:00:00Z",
        interval_end="2030-01-01T00:01:00Z",
    )
    cases["coverage-interval-outside"] = outside

    withheld = copy.deepcopy(base)
    coverage = _coverage(withheld)
    coverage["locally_held"] = False
    coverage["access_level"] = "withheld"
    coverage["redaction"] = "withheld_original"
    cases["coverage-withheld"] = withheld

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
