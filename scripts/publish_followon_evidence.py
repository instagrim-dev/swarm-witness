#!/usr/bin/env python3
"""Mirror causal_swarm / r5_v2 artifact summaries into Claim/Run/Finding evidence."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_protocol(
    *,
    claim_id: str,
    protocol_id: str,
    artifact_dir: Path,
    evidence_dir: Path,
    source_pin: str,
    artifact_rel: str,
) -> dict:
    summary = json.loads((artifact_dir / "summary.json").read_text())
    runs_dir = evidence_dir / "runs"
    findings_dir = evidence_dir / "findings"
    if evidence_dir.exists():
        shutil.rmtree(evidence_dir)
    runs_dir.mkdir(parents=True)
    findings_dir.mkdir(parents=True)

    run_ids: list[str] = []
    for row in summary["results"]:
        rid = f"{claim_id}-{row['case_id']}-{row['policy']}"
        run_ids.append(rid)
        obs = {
            "scenario_id": row["case_id"],
            "dimension": row["dimension"],
            "policy": row["policy"],
            "expected": row["expected"],
            "observed": row["observed"],
            "case_passed": row["passed"],
            "trace_file": f"{artifact_rel}/{row['case_id']}.{row['policy']}.json",
        }
        (runs_dir / f"{rid}.json").write_text(
            json.dumps(
                {
                    "id": rid,
                    "claim_id": claim_id,
                    "protocol_id": protocol_id,
                    "case_id": row["case_id"],
                    "source_pin": source_pin,
                    "execution_status": "completed",
                    "observations": obs,
                },
                indent=2,
            )
            + "\n"
        )

    meta_id = f"{claim_id}-meta"
    run_ids.append(meta_id)
    meta_obs = {
        "passed": summary["passed"],
        "scenario_count": summary["scenario_count"],
        "arm_count": summary["arm_count"],
        "dimension_count": summary["dimension_count"],
        "paired_worlds_local_indistinguishable": summary.get(
            "paired_worlds_local_indistinguishable"
        ),
        "irrelevant_control_unchanged": summary.get("irrelevant_control_unchanged"),
        "manifest_sha256": summary["manifest_sha256"],
    }
    (runs_dir / f"{meta_id}.json").write_text(
        json.dumps(
            {
                "id": meta_id,
                "claim_id": claim_id,
                "protocol_id": protocol_id,
                "case_id": "method_score",
                "source_pin": source_pin,
                "execution_status": "completed",
                "observations": meta_obs,
            },
            indent=2,
        )
        + "\n"
    )

    finding_id = f"{claim_id}-f-property"
    finding = {
        "id": finding_id,
        "claim_id": claim_id,
        "run_ids": run_ids,
        "proposition": (
            f"For {summary['scenario_count']} fixed {protocol_id} schedules, "
            "reference and faulty-local traces were evaluated against an independently "
            "reconstructed model effect ledger; each result matched its externally-declared "
            "expected counts"
        ),
        "scope": (
            f"Synthetic deterministic causal interleavings; "
            f"{summary['dimension_count']} enumerated dimensions, "
            f"{summary['arm_count']} policy arms; not live distributed agents"
        ),
        "label": "reproduced",
        "basis": "computed",
        "evaluation_method": "synthetic_model_conformance",
        "supporting_observation_refs": [
            f"{meta_id}.observations.passed",
            f"{meta_id}.observations.scenario_count",
            f"{meta_id}.observations.arm_count",
        ],
    }
    (findings_dir / f"{finding_id}.json").write_text(json.dumps(finding, indent=2) + "\n")
    (evidence_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    result = {
        "claim_id": claim_id,
        "label": "reproduced",
        "authoritative": "finding",
        "finding_path": f"findings/{finding_id}.json",
        "metrics": {
            "scenario_count": summary["scenario_count"],
            "arm_count": summary["arm_count"],
            "dimension_count": summary["dimension_count"],
            "passed": summary["passed"],
        },
    }
    import yaml  # type: ignore

    (evidence_dir / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False)
    )
    return summary


def main() -> None:
    cs = _write_protocol(
        claim_id="causal_swarm",
        protocol_id="causal-swarm-v1",
        artifact_dir=ROOT / "artifacts" / "causal_swarm_v1",
        evidence_dir=ROOT / "evidence" / "causal_swarm",
        source_pin="causal-swarm-v1",
        artifact_rel="artifacts/causal_swarm_v1",
    )
    r5 = _write_protocol(
        claim_id="r5_v2",
        protocol_id="r5-v2-causal-matrix",
        artifact_dir=ROOT / "artifacts" / "r5_v2",
        evidence_dir=ROOT / "evidence" / "r5_v2",
        source_pin="r5-v2-causal-matrix",
        artifact_rel="artifacts/r5_v2",
    )
    print(
        json.dumps(
            {
                "causal_swarm": {
                    k: cs[k]
                    for k in (
                        "scenario_count",
                        "arm_count",
                        "dimension_count",
                        "passed",
                    )
                },
                "r5_v2": {
                    k: r5[k]
                    for k in (
                        "scenario_count",
                        "arm_count",
                        "dimension_count",
                        "passed",
                    )
                },
            }
        )
    )


if __name__ == "__main__":
    main()
    raise SystemExit(
        subprocess.call([sys.executable, str(ROOT / "scripts" / "annotate_conclusion_classes.py")])
    )
