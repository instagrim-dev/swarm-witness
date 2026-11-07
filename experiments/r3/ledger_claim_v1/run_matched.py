#!/usr/bin/env python3
"""Execute r3-ledger-claim-v1 matched run (classical + BMO bridge)."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))

from bmo_adapter import PIN_REV, run_bmo_probe  # noqa: E402
from classical_adapter import ADAPTER_ID as CLASSICAL_ID  # noqa: E402
from classical_adapter import ClassicalAdapter  # noqa: E402
from compare import compare_run, write_compare_artifacts  # noqa: E402
from protocol import CLAIM_ID, PROTOCOL_ID, load_cases  # noqa: E402
from swarm_witness.schema import validate_run  # noqa: E402

EVIDENCE_ROOT = ROOT / "evidence" / "r3" / "ledger_claim_v1"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, sort_keys=False) + "\n" for r in rows),
        encoding="utf-8",
    )


def run_classical(cases: list[Any], work_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        case_dir = work_dir / case.case_id
        if case_dir.exists():
            shutil.rmtree(case_dir)
        adapter = ClassicalAdapter(case_dir)
        try:
            adapter.open_case(case)
            for action in case.actions:
                rows.append(adapter.apply(action))
        finally:
            adapter.close()
    return rows


def materialize_runs(
    run_dir: Path,
    *,
    classical_rows: list[dict[str, Any]],
    bmo_rows: list[dict[str, Any]],
    bmo_manifest: dict[str, Any],
    cases_hash: str,
) -> list[str]:
    runs_dir = run_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_ids: list[str] = []

    meta_run = {
        "id": "r3-ledger-meta",
        "claim_id": CLAIM_ID,
        "protocol_id": PROTOCOL_ID,
        "case_id": "meta",
        "source_pin": PIN_REV,
        "execution_status": "completed",
        "observations": {
            "agreement": {"result": None},
            "validity": {"valid": None},
            "bmo_manifest": bmo_manifest,
            "cases_hash": cases_hash,
            "bridge_hashes": bmo_manifest.get("bridge"),
        },
    }
    # Placeholder; compare will rewrite finding; meta updated after compare.
    validate_run(meta_run)
    (runs_dir / "r3-ledger-meta.json").write_text(
        json.dumps(meta_run, indent=2) + "\n", encoding="utf-8"
    )
    run_ids.append("r3-ledger-meta")

    for arm, rows in (("classical", classical_rows), ("bmo", bmo_rows)):
        by_case: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_case.setdefault(str(row.get("case_id")), []).append(row)
        for case_id, case_rows in sorted(by_case.items()):
            status = "completed"
            if any(r.get("execution_status") == "missing" for r in case_rows):
                status = "missing"
            elif any(r.get("execution_status") == "failed" for r in case_rows):
                status = "failed"
            run = {
                "id": f"{arm}-{case_id}",
                "claim_id": CLAIM_ID,
                "protocol_id": PROTOCOL_ID,
                "case_id": case_id,
                "source_pin": PIN_REV,
                "execution_status": status,
                "observations": {
                    "arm": arm,
                    "steps": case_rows,
                    "step_count": len(case_rows),
                },
            }
            validate_run(run)
            (runs_dir / f"{run['id']}.json").write_text(
                json.dumps(run, indent=2) + "\n", encoding="utf-8"
            )
            run_ids.append(run["id"])
    return run_ids


def patch_finding_refs(run_dir: Path, summary: dict[str, Any]) -> None:
    """Ensure Finding supporting refs resolve for evidence consistency."""
    runs_dir = run_dir / "runs"
    meta_path = runs_dir / "r3-ledger-meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["observations"]["agreement"] = {
        "result": summary["agreement"]["result"],
        "reason": summary["agreement"].get("reason"),
    }
    meta["observations"]["validity"] = {
        "valid": summary["validity"]["valid"],
        "errors": summary["validity"].get("errors"),
    }
    validate_run(meta)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    finding = summary["finding"]
    finding["run_ids"] = sorted(
        p.stem for p in runs_dir.glob("*.json")
    ) or ["r3-ledger-meta"]
    finding["supporting_observation_refs"] = [
        "r3-ledger-meta.observations.agreement.result",
        "r3-ledger-meta.observations.validity.valid",
    ]
    from swarm_witness.schema import validate_finding

    validate_finding(finding)
    summary["finding"] = finding
    findings_dir = run_dir / "findings"
    findings_dir.mkdir(parents=True, exist_ok=True)
    (findings_dir / f"{finding['id']}.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )


def mirror_for_index(run_dir: Path, finding: dict[str, Any]) -> None:
    """Copy authoritative finding into evidence/r3_ledger_claim_v1 for index glob."""
    slot = ROOT / "evidence" / "r3_ledger_claim_v1"
    findings = slot / "findings"
    runs = slot / "runs"
    findings.mkdir(parents=True, exist_ok=True)
    runs.mkdir(parents=True, exist_ok=True)
    # Clear prior mirrors for this claim slot.
    for path in findings.glob("*.json"):
        path.unlink()
    for path in runs.glob("*.json"):
        path.unlink()
    src_runs = run_dir / "runs"
    for path in src_runs.glob("*.json"):
        shutil.copy2(path, runs / path.name)
    (findings / f"{finding['id']}.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )
    (slot / "summary.json").write_text(
        (run_dir / "summary.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    if (run_dir / "result.yaml").is_file():
        shutil.copy2(run_dir / "result.yaml", slot / "result.yaml")


def execute_run(
    *,
    run_id: str,
    bmo_root: Path | None,
    cases_path: Path,
    case_filter: set[str] | None = None,
) -> Path:
    bundle = load_cases(cases_path)
    cases = list(bundle["cases"])
    if case_filter:
        cases = [c for c in cases if c.case_id in case_filter]
        if not cases:
            raise ValueError(f"no cases matched filter {sorted(case_filter)}")

    run_dir = EVIDENCE_ROOT / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    classical_work = run_dir / "classical_work"
    bmo_work = run_dir / "bmo_work"
    classical_rows = run_classical(cases, classical_work)
    bmo_rows, bmo_manifest = run_bmo_probe(
        cases=cases, work_dir=bmo_work, bmo_root=bmo_root
    )

    write_ndjson(run_dir / "classical.ndjson", classical_rows)
    write_ndjson(run_dir / "bmo.ndjson", bmo_rows)
    (run_dir / "source_manifest.json").write_text(
        json.dumps(
            {
                "protocol_id": PROTOCOL_ID,
                "claim_id": CLAIM_ID,
                "run_id": run_id,
                "bmo_pin": PIN_REV,
                "bmo": bmo_manifest,
                "cases_path": str(cases_path),
                "cases_sha256": _sha256_text(cases_path.read_text(encoding="utf-8")),
                "created_unix": int(time.time()),
                "swarm_witness_root": str(ROOT),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cases_hash = _sha256_text(cases_path.read_text(encoding="utf-8"))
    materialize_runs(
        run_dir,
        classical_rows=classical_rows,
        bmo_rows=bmo_rows,
        bmo_manifest=bmo_manifest,
        cases_hash=cases_hash,
    )

    # Compare only the selected cases: write a filtered cases file if needed.
    compare_cases = cases_path
    if case_filter:
        import yaml

        raw = yaml.safe_load(cases_path.read_text(encoding="utf-8"))
        raw["cases"] = [c for c in raw["cases"] if c["case_id"] in case_filter]
        compare_cases = run_dir / "cases.filtered.yaml"
        compare_cases.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    summary = compare_run(run_dir, cases_path=compare_cases)
    write_compare_artifacts(run_dir, summary)
    patch_finding_refs(run_dir, summary)
    write_compare_artifacts(run_dir, summary)
    mirror_for_index(run_dir, summary["finding"])
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bmo-root", type=Path, default=None)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).resolve().parent / "cases.yaml",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Optional case_id filter (e.g. T02 T03 T04)",
    )
    args = parser.parse_args(argv)
    case_filter = set(args.only) if args.only else None
    run_dir = execute_run(
        run_id=args.run_id,
        bmo_root=args.bmo_root,
        cases_path=args.cases,
        case_filter=case_filter,
    )
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "label": summary["finding"]["label"],
                "agreement": summary["agreement"]["result"],
                "validity": summary["validity"]["valid"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
