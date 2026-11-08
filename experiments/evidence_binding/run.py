#!/usr/bin/env python3
"""Write the evidence-binding Claim/Run/Finding from retained inputs.

The entrypoint reads the property-graph fixture and the native-witness packet.
It does not accept bitmasks, and it does not build the SQLite witness.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.evidence_binding import (  # noqa: E402
    PROTOCOL_ID,
    SOURCE_PIN,
    audit_entrypoint,
)
from swarm_witness.evidence_binding_conformance import run_conformance  # noqa: E402
from swarm_witness.evidence_index import generate_and_write_index  # noqa: E402

CLAIM_ID = "evidence_binding_v1"
RUN_ID = "evidence-binding-v1-run"
FINDING_ID = "evidence-binding-v1-f"


def observations(root: Path | None = None) -> dict:
    root = root or ROOT
    entry = audit_entrypoint(root)
    report = run_conformance(root)
    system = entry["retained_system"]
    if not report["passed"]:
        raise RuntimeError(f"evidence binding conformance failed: {report}")
    return {
        "passed": True,
        "retained_case_id": system["case_id"],
        "retained_p_system_epistemic": system["epistemic_status"],
        "retained_p_system_conclusion": system["conclusion_class"],
        "retained_failure_origin": system["failure_origin"],
        "retained_decision_status": system["decision_status"],
        "retained_effect_status": system["effect_status"],
        "retained_fault_attribution": system["fault_attribution"],
        "retained_p_url_epistemic": entry["retained_url"]["epistemic_status"],
        "url_allowlist_supports_p_system": entry["url_allowlist_supports_p_system"],
        "native_packet_event_count": entry["native"]["event_count"],
        "native_epistemic": entry["native"]["epistemic_status"],
        "native_evidence_status": entry["native"]["evidence_status"],
        "native_truth_files_read": len(entry["native"]["truth_files_read"]),
        "reference_agreement": (
            report["entrypoint_agreement"]
            and report["domain"]["passed"]
            and report["records"]["passed"]
        ),
        "domain_cases_compared": report["domain"]["compared"],
        "mutation_verification_caught": report["mutations"]["verification"],
        "mutation_empty_set_caught": report["mutations"]["empty_set"],
        "mutation_property_kind_caught": report["mutations"]["property_kind"],
        "mutation_temporal_binding_caught": report["mutations"]["temporal_binding"],
        "real_world_authenticity_certified": entry["real_world_authenticity_certified"],
        "detection_or_prevention_claimed": entry["detection_or_prevention_claimed"],
        "source_digest_proves_authenticity": False,
        "passing_tests_prove_completeness": False,
        "actual_world_membership_certified": False,
        "sqlite_witness_built": False,
    }


def publish(root: Path | None = None) -> dict:
    root = root or ROOT
    observed = observations(root)
    slot = root / "evidence" / "evidence_binding_v1"
    runs = slot / "runs"
    findings = slot / "findings"
    runs.mkdir(parents=True, exist_ok=True)
    findings.mkdir(parents=True, exist_ok=True)
    run = {
        "id": RUN_ID,
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "url_held_worker_local_read",
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "observations": observed,
    }
    finding = {
        "id": FINDING_ID,
        "claim_id": CLAIM_ID,
        "run_ids": [RUN_ID],
        "proposition": (
            "The production verdict and the mask reference agree on the retained "
            "workflow and the native-witness packet. P_system is not a URL allowlist. "
            "Hashes and passing tests do not certify the actual world."
        ),
        "scope": (
            "evidence-binding-v1 on the retained url_held_worker_local_read case "
            "and the forensic telemetry origin packet. Not live workers and not "
            "the SQLite application witness."
        ),
        "label": "reproduced",
        "basis": "computed",
        "conclusion_class": "supported",
        "evaluation_method": "synthetic_protocol_conformance",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.passed",
            f"{RUN_ID}.observations.reference_agreement",
            f"{RUN_ID}.observations.retained_p_system_epistemic",
            f"{RUN_ID}.observations.retained_p_url_epistemic",
            f"{RUN_ID}.observations.native_epistemic",
            f"{RUN_ID}.observations.real_world_authenticity_certified",
        ],
    }
    (runs / f"{RUN_ID}.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (findings / f"{FINDING_ID}.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "label": "reproduced",
        "finding_id": FINDING_ID,
        **observed,
    }
    (slot / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    result = {
        "claim_id": CLAIM_ID,
        "label": "reproduced",
        "authoritative": "finding",
        "finding_path": f"findings/{FINDING_ID}.json",
        "metrics": observed,
    }
    (slot / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )
    generate_and_write_index(root)
    return observed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    observed = publish(args.root)
    print(json.dumps({"passed": observed["passed"], "protocol_id": PROTOCOL_ID}))


if __name__ == "__main__":
    main()
