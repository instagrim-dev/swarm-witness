"""Formal native coverage is a census, and a report is not an attribution."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from swarm_witness.evidence_binding import audit_native_packet, bind_family

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "evidence" / "effect_witness_v1" / "packets"
CLEAN = PACKETS / "aew-v1-h-authority-current" / "discriminating_readback"


def _copy(tmp_path: Path) -> Path:
    dest = tmp_path / "packet"
    shutil.copytree(CLEAN, dest)
    return dest


def _rewrite_coverage(packet: Path, render) -> None:
    path = packet / "service_records.jsonl"
    kept = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = row.get("public_bytes") or ""
        if str(text).startswith("aew-v1 observer coverage"):
            row = render(row)
            if row is None:
                continue
        kept.append(json.dumps(row, separators=(",", ":")))
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def test_unrelated_service_log_does_not_complete_effect_coverage(tmp_path: Path):
    packet = _copy(tmp_path)

    def heartbeat(row):
        row["action"] = "service_heartbeat"
        row["public_bytes"] = "aew-v1 service heartbeat\nstatus=up\n"
        row["raw"] = row["public_bytes"]
        return row

    _rewrite_coverage(packet, heartbeat)
    effect = audit_native_packet(ROOT, family="P_effect", directory=packet)
    commitment = audit_native_packet(ROOT, family="P_commitment", directory=packet)
    assert effect["epistemic_status"] == "unresolved"
    assert commitment["epistemic_status"] == "supported"


def test_count_mismatch_does_not_support_effect_absence_or_presence(tmp_path: Path):
    packet = _copy(tmp_path)

    def mismatch(row):
        text = row["public_bytes"].replace("row_count=1", "row_count=2")
        row["public_bytes"] = text
        row["raw"] = text
        return row

    _rewrite_coverage(packet, mismatch)
    effect = audit_native_packet(ROOT, family="P_effect", directory=packet)
    commitment = audit_native_packet(ROOT, family="P_commitment", directory=packet)
    assert effect["epistemic_status"] == "unresolved"
    assert commitment["epistemic_status"] == "supported"


def test_commit_without_census_supports_commitment_only(tmp_path: Path):
    packet = _copy(tmp_path)
    _rewrite_coverage(packet, lambda _row: None)
    effect = audit_native_packet(ROOT, family="P_effect", directory=packet)
    commitment = audit_native_packet(ROOT, family="P_commitment", directory=packet)
    system = audit_native_packet(ROOT, family="P_system", directory=packet)
    assert effect["epistemic_status"] == "unresolved"
    assert system["epistemic_status"] == "unresolved"
    assert commitment["epistemic_status"] == "supported"
    assert commitment["verified"] is True


def test_reports_only_fault_is_undetermined_and_support_still_attributes():
    report = {
        "id": "bob-report",
        "kind": "public",
        "authenticity": "authentic_public_text",
        "family": "P_url",
        "channel": "remote_url",
        "polarity": "reports",
        "attribute_fault": True,
        "actor_binding": "bound",
        "binding": "bound",
        "actor_ref": "Bob",
        "named_origin": "Bob",
        "coverage": "complete",
        "independence_group": "bob-report",
        "event_time": "2026-01-01T00:00:00Z",
        "time_basis": "source_stated",
        "locally_held": True,
        "access_level": "public_bytes",
    }
    result = bind_family([report], family="P_url", claim={})
    assert result["epistemic_status"] == "unresolved"
    assert result["verified"] is False
    assert result["reason"] == "no_binding_record"
    assert result["fault_attribution"] == "undetermined"
    supported = dict(report)
    supported["id"] = "bob-support"
    supported["polarity"] = "supports"
    named = bind_family([supported], family="P_url", claim={})
    assert named["epistemic_status"] == "supported"
    assert named["fault_attribution"] == "Bob"
