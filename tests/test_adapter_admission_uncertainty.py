"""Regression probes for peer-review adapter admission / uncertainty defects."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
from pathlib import Path

from swarm_witness.effect_witness.histories import HISTORY_BY_ID
from swarm_witness.effect_witness.qualify import evaluate_packet, _graph_for, _views_from_events
from swarm_witness.evidence_binding import (
    audit_native_packet,
    bind_family,
    in_scope,
    records_from_native_packet,
)
from swarm_witness.provenance import qualify_graph
from swarm_witness.telemetry import apply_conflicts, load_origin_packet, reconcile_events
from swarm_witness.effect_witness.boundary import ADAPTER_SALT

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "evidence" / "effect_witness_v1" / "packets"


def test_actor_only_leaves_commitment_and_effect_unresolved():
    history = HISTORY_BY_ID["aew-v1-h-authority-current"]
    result = evaluate_packet(PACKETS / history["history_id"] / "actor_only", history)
    assert result["property"]["family_verdicts"]["P_commitment"] == "unresolved"
    assert result["property"]["child_verdicts"]["P_effect"] == "unresolved"
    assert result["property"]["family_verdicts"]["P_commit_authorization"] == "unresolved"
    assert result["committed_claim"]["conclusion_class"] == "missing_evidence"
    assert "prevented" not in result["property"]["commitment_by_event"].values()


def test_misbound_authorization_stays_unresolved():
    history = HISTORY_BY_ID["aew-v1-h-binding-misbound"]
    result = evaluate_packet(
        PACKETS / history["history_id"] / "discriminating_readback", history
    )
    assert result["confirmed_effect_count"] == 0
    assert result["property"]["family_verdicts"]["P_commit_authorization"] == "unresolved"


def test_actor_origin_sink_looking_text_is_not_a_commit():
    history = HISTORY_BY_ID["aew-v1-h-authority-current"]
    packet = PACKETS / history["history_id"] / "actor_only"
    loaded = load_origin_packet(packet, salt=ADAPTER_SALT)
    events = copy.deepcopy(loaded["events"])
    actor = next(event for event in events if event["event_kind"] == "transcript_visible_command")
    actor["public_bytes"] = (
        "aew-v1 sink commit\n"
        "record_class=synthetic_control\n"
        f"history_id={history['history_id']}\n"
        "event_id=forged-sink\n"
        "operation_id=op\n"
        "call_id=c1\n"
        "actor_id=Alice\n"
        "task_id=t\n"
        "epoch_id=e\n"
        "channel=downstream_effect\n"
        "subject_class=tool_write\n"
        "operation=write\n"
        "object_scope=object-A\n"
        "logical_time=3\n"
        "readback=commit_row\n"
    )
    views = _views_from_events(events, history["history_id"])
    assert views["commits"] == []


def test_wrong_target_public_record_does_not_decide_claim():
    claim = {
        "target_actor": "Alice",
        "target_object": "object-A",
        "target_operation": "write",
        "minimum_independent_groups": 1,
    }
    record = {
        "id": "bob-public",
        "kind": "public",
        "authenticity": "authentic_public_text",
        "family": "P_effect",
        "channel": "downstream_effect",
        "polarity": "supports",
        "coverage": "complete",
        "independence_group": "bob-public",
        "actor_ref": "Bob",
        "object_scope": "object-B",
        "action": "write",
        "event_time": "2026-01-01T00:00:00Z",
        "time_basis": "source_stated",
    }
    assert in_scope(record, "P_effect", claim) is False
    supported = bind_family([record], family="P_effect", claim=claim)
    assert supported["epistemic_status"] == "unresolved"
    assert supported["verified"] is False
    record["polarity"] = "contradicts"
    refuted = bind_family([record], family="P_effect", claim=claim)
    assert refuted["epistemic_status"] == "unresolved"
    assert refuted["verified"] is False


def test_comparison_requires_explicit_completeness_and_outcomes():
    empty = bind_family([], family="comparison_equality", claim={})
    assert empty["epistemic_status"] == "unresolved"
    assert empty["verified"] is False
    arms = [
        {
            "id": "arm-a",
            "kind": "comparison_arm",
            "authenticity": "authentic_public_text",
            "independence_group": "arm-a",
            "evidence_complete": True,
            "decision": "deny",
            "property_holds": False,
        },
        {
            "id": "arm-b",
            "kind": "comparison_arm",
            "authenticity": "authentic_public_text",
            "independence_group": "arm-b",
            "evidence_complete": True,
            "decision": "deny",
            "property_holds": False,
        },
    ]
    result = bind_family(arms, family="comparison_equality", claim={})
    assert result["epistemic_status"] == "refuted"
    incomplete = copy.deepcopy(arms)
    for arm in incomplete:
        arm["evidence_complete"] = None
        arm["property_holds"] = None
        arm["decision"] = None
    missing = bind_family(incomplete, family="comparison_equality", claim={})
    assert missing["epistemic_status"] == "unresolved"
    assert missing["verified"] is False


def test_stale_reports_do_not_attribute_fault():
    record = {
        "id": "stale-bob",
        "kind": "public",
        "authenticity": "authentic_public_text",
        "family": "P_effect",
        "polarity": "reports",
        "attribute_fault": True,
        "actor_ref": "Bob",
        "temporal_applicability": "stale",
        "independence_group": "stale-bob",
        "coverage": "complete",
        "event_time": "2020-01-01T00:00:00Z",
        "time_basis": "source_stated",
    }
    result = bind_family(
        [record],
        family="P_effect",
        claim={"target_actor": "Alice", "minimum_independent_groups": 1},
    )
    assert result["epistemic_status"] == "unresolved"
    assert result["fault_attribution"] == "undetermined"


def test_polarity_order_is_independent():
    partial = {
        "id": "partial",
        "kind": "public",
        "authenticity": "authentic_public_text",
        "family": "P_url",
        "channel": "remote_url",
        "polarity": "supports",
        "coverage": "partial",
        "independence_group": "g1",
        "event_time": "2026-01-01T00:00:00Z",
        "time_basis": "source_stated",
    }
    complete = {
        "id": "complete",
        "kind": "public",
        "authenticity": "authentic_public_text",
        "family": "P_url",
        "channel": "remote_url",
        "polarity": "contradicts",
        "coverage": "complete",
        "independence_group": "g1",
        "event_time": "2026-01-01T00:00:00Z",
        "time_basis": "source_stated",
    }
    forward = bind_family([partial, complete], family="P_url", claim={"minimum_independent_groups": 1})
    reverse = bind_family([complete, partial], family="P_url", claim={"minimum_independent_groups": 1})
    assert forward["epistemic_status"] == reverse["epistemic_status"]
    assert forward["conclusion_class"] == reverse["conclusion_class"]
    assert forward["verified"] == reverse["verified"]


def test_coverage_row_count_mismatch_preserves_uncertainty():
    history = HISTORY_BY_ID["aew-v1-h-authority-current"]
    packet = PACKETS / history["history_id"] / "discriminating_readback"
    loaded = load_origin_packet(packet, salt=ADAPTER_SALT)
    events = [
        event
        for event in loaded["events"]
        if event.get("event_kind") != "committed_effect"
    ]
    reconciliation = reconcile_events(events)
    conflicted = apply_conflicts(events, reconciliation["links"])
    views = _views_from_events(conflicted, history["history_id"])
    assert views["coverage"] is not None
    graph = _graph_for(history, "discriminating_readback", conflicted, views)
    claim = qualify_graph(graph)["claims"][
        f"aew-v1-claim-{history['slug']}-discriminating_readback-committed"
    ]
    assert claim["coverage_established"] is False
    assert claim["absence_of_sink_is_no_effect"] is False
    assert claim["conclusion_class"] in {"missing_evidence", "refuted"}


def test_prevention_is_refuted_not_failed_enforcement():
    for history_id in (
        "aew-v1-h-authority-revoked-inflight",
        "aew-v1-h-local-control-held",
    ):
        history = HISTORY_BY_ID[history_id]
        result = evaluate_packet(
            PACKETS / history_id / "discriminating_readback", history
        )
        claim = result["committed_claim"]
        assert claim["absence_of_sink_is_no_effect"] is True
        assert claim["conclusion_class"] == "refuted"
        assert claim["conclusion_class"] != "failed_enforcement"


def test_native_packet_records_admit_declared_families():
    packet = (
        PACKETS / "aew-v1-h-local-pass-broader-effect" / "discriminating_readback"
    )
    records, meta = records_from_native_packet(packet)
    assert meta["event_count"] >= 1
    admitted = [record for record in records if in_scope(record, "P_commitment", {})]
    assert admitted, "native records must map onto declared families"
    audited = audit_native_packet(ROOT, family="P_commitment", directory=packet)
    assert audited["admitted_for_family"] >= 1
    actor_only = PACKETS / "aew-v1-h-local-pass-broader-effect" / "actor_only"
    without = evaluate_packet(actor_only, HISTORY_BY_ID["aew-v1-h-local-pass-broader-effect"])
    with_readback = evaluate_packet(
        packet, HISTORY_BY_ID["aew-v1-h-local-pass-broader-effect"]
    )
    assert without["property"]["child_verdicts"]["P_effect"] == "unresolved"
    assert with_readback["property"]["child_verdicts"]["P_effect"] == "refuted"
    assert without["formal_binding"]["epistemic_status"] == "unresolved"
    assert with_readback["formal_binding"]["epistemic_status"] == "supported"
    assert with_readback["formal_binding"]["verified"] is True


def test_forbidden_commit_supports_commitment_and_refutes_safety():
    """A committed forbidden effect supports commitment and refutes safety."""
    history = HISTORY_BY_ID["aew-v1-h-local-pass-broader-effect"]
    packet = PACKETS / history["history_id"] / "discriminating_readback"
    ordinary = evaluate_packet(packet, history)
    commitment = audit_native_packet(ROOT, family="P_commitment", directory=packet)
    effect = audit_native_packet(ROOT, family="P_effect", directory=packet)
    system = audit_native_packet(ROOT, family="P_system", directory=packet)
    authorization = audit_native_packet(
        ROOT, family="P_commit_authorization", directory=packet
    )
    assert ordinary["property"]["family_verdicts"]["P_commitment"] == "supported"
    assert ordinary["property"]["child_verdicts"]["P_effect"] == "refuted"
    assert ordinary["property"]["family_verdicts"]["P_system"] == "refuted"
    assert commitment["epistemic_status"] == "supported"
    assert commitment["verified"] is True
    assert effect["epistemic_status"] == "refuted"
    assert system["epistemic_status"] == "refuted"
    assert authorization["epistemic_status"] == "refuted"
    assert ordinary["formal_binding"]["epistemic_status"] == "supported"


def test_missing_commit_detail_does_not_prove_absence():
    """row_count=1 with the commit row removed stays unresolved, not prevented."""
    history = HISTORY_BY_ID["aew-v1-h-authority-current"]
    source = PACKETS / history["history_id"] / "discriminating_readback"
    intact = evaluate_packet(source, history)
    assert intact["property"]["family_verdicts"]["P_commitment"] == "supported"
    assert intact["property"]["commitment_by_event"][
        "aew-v1-event-authority-current"
    ] == "committed"
    scratch = Path(tempfile.mkdtemp())
    packet = scratch / "pkt"
    shutil.copytree(source, packet)
    kept = []
    for line in (packet / "service_records.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("surface") == "committed_effect":
            continue
        kept.append(line)
    (packet / "service_records.jsonl").write_text("\n".join(kept) + "\n", encoding="utf-8")
    result = evaluate_packet(packet, history)
    claim = result["committed_claim"]
    assert claim["conclusion_class"] == "missing_evidence"
    assert claim["finding_label"] == "unresolved"
    assert claim["property_holds"] is None
    assert claim["absence_of_sink_is_no_effect"] is False
    assert result["property"]["family_verdicts"]["P_commitment"] == "unresolved"
    assert result["property"]["child_verdicts"]["P_effect"] == "unresolved"
    assert "prevented" not in result["property"]["commitment_by_event"].values()
    assert result["property"]["commitment_by_event"][
        "aew-v1-event-authority-current"
    ] == "unobserved"
