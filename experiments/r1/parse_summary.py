#!/usr/bin/env python3
"""Derive R1 Run + Finding records from retained local analysis cases.

Denominators (histories_per_policy, prohibited counts) are counted from the
``cases`` array in ``evidence/r1/local-run-analysis.json``. Planned constants
such as 153 are never seeded. Finding is authoritative for labels; summary.json
and result.yaml are retained as convenience mirrors only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.schema import validate_finding, validate_run  # noqa: E402

EV = ROOT / "evidence" / "r1"
ANALYSIS = EV / "local-run-analysis.json"
SUMMARY = EV / "summary.json"
RESULT = EV / "result.yaml"
RAW = EV / "raw.json"
CARGO_LOG = EV / "cargo-wal-recovery-barrier.log"
RUNS_DIR = EV / "runs"
FINDINGS_DIR = EV / "findings"

RUN_ID = "r1-run-barrier-sweep"
FINDING_ID = "r1-f-primary"
SOURCE_PIN = "6568403"
PROTOCOL_ID = "soundgate-recovery-barrier"
CASE_ID = "policy-barrier-sweep"
CLAIM_SCOPE = (
    "SoundGate 0.1.3 @ source revision 6568403 under intact acknowledged records"
)


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _cargo_ok() -> bool | None:
    if not CARGO_LOG.is_file():
        return None
    text = CARGO_LOG.read_text(encoding="utf-8", errors="replace")
    if "test result: ok. 3 passed" in text:
        return True
    if "FAILED" in text or "error:" in text.lower():
        return False
    return None


def count_from_case_records(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Count histories and status tallies from retained case records only."""
    if not isinstance(cases, list) or not cases:
        raise ValueError("analysis cases must be a non-empty list")

    per_policy_cases: dict[str, int] = Counter()
    per_policy_status: dict[str, Counter[str]] = {}
    for row in cases:
        if not isinstance(row, dict):
            raise ValueError("each case record must be a dict")
        policy = row.get("policy")
        status = row.get("status")
        if not isinstance(policy, str) or not policy.strip():
            raise ValueError("case record missing policy")
        if not isinstance(status, str) or not status.strip():
            raise ValueError("case record missing status")
        per_policy_cases[policy] += 1
        per_policy_status.setdefault(policy, Counter())[status] += 1

    counts = {p: int(n) for p, n in sorted(per_policy_cases.items())}
    unique = set(counts.values())
    if len(unique) != 1:
        raise ValueError(
            f"histories_per_policy inconsistent across policies: {counts}"
        )
    histories_per_policy = next(iter(unique))

    prohibited: dict[str, int] = {}
    refused_before_ack: dict[str, int] = {}
    supported: dict[str, int] = {}
    for policy, statuses in per_policy_status.items():
        prohibited[policy] = int(statuses.get("prohibited_effect", 0))
        refused_before_ack[policy] = int(statuses.get("refused_before_ack", 0))
        supported[policy] = int(statuses.get("supported", 0))

    return {
        "histories_per_policy": histories_per_policy,
        "case_record_count": len(cases),
        "cases_per_policy": counts,
        "prohibited_effects_by_policy": prohibited,
        "refused_before_ack_by_policy": refused_before_ack,
        "supported_by_policy": supported,
        "status_tallies_by_policy": {
            p: dict(sorted(c.items())) for p, c in sorted(per_policy_status.items())
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_result_mirror(
    *,
    label: str,
    metrics: dict[str, Any],
    notes: str,
    finding_path: str,
) -> None:
    # Convenience mirror for older tooling; Finding JSON is authoritative.
    import yaml

    result = {
        "claim_id": "r1",
        "label": label,
        "metrics": metrics,
        "evidence_path": "evidence/r1/summary.json",
        "finding_path": finding_path,
        "notes": notes,
        "authoritative": "finding",
    }
    RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")


def write_unresolved(
    *,
    execution_status: str,
    notes: str,
    command: str | None = None,
    cwd: str | None = None,
    exit_status: int | None = None,
    stdout_path: str | None = None,
    stderr_path: str | None = None,
    partial_output: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if execution_status not in {"unrun", "failed", "missing", "attempted"}:
        raise ValueError(f"unresolved path requires honest status, got {execution_status!r}")

    run: dict[str, Any] = {
        "id": RUN_ID,
        "claim_id": "r1",
        "protocol_id": PROTOCOL_ID,
        "case_id": CASE_ID,
        "source_pin": SOURCE_PIN,
        "execution_status": execution_status,
        "command": command
        or "experiments/r1/run_r1.sh (no completed sweep; see notes)",
        "cwd": cwd or str(ROOT),
        "exit_status": exit_status,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "observations": {
            "notes": notes,
            "partial_output": partial_output,
            "histories_per_policy": None,
            "prohibited_effects_barrier": None,
            "case_record_count": 0,
        },
    }
    validate_run(run)
    finding: dict[str, Any] = {
        "id": FINDING_ID,
        "claim_id": "r1",
        "run_ids": [RUN_ID],
        "proposition": (
            "Barrier prohibited_effects==0 on pinned SoundGate recovery-barrier sweep"
        ),
        "scope": CLAIM_SCOPE,
        "label": "unresolved",
        "basis": "computed",
        "supporting_observation_refs": [f"{RUN_ID}.observations.notes"],
    }
    validate_finding(finding)

    run_path = RUNS_DIR / f"{RUN_ID}.json"
    finding_path = FINDINGS_DIR / f"{FINDING_ID}.json"
    _write_json(run_path, run)
    _write_json(finding_path, finding)

    summary = {
        "histories_per_policy": None,
        "prohibited_effects_original": None,
        "prohibited_effects_barrier": None,
        "strict_refusal_startup_refusals": None,
        "source_revision": SOURCE_PIN,
        "unresolved": True,
        "notes": notes,
        "authoritative_finding": str(finding_path.relative_to(ROOT)),
    }
    EV.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_result_mirror(
        label="unresolved",
        metrics={},
        notes=notes,
        finding_path=str(finding_path.relative_to(ROOT)),
    )
    return run, finding


def derive_from_analysis(analysis_path: Path = ANALYSIS) -> tuple[dict[str, Any], dict[str, Any]]:
    data = json.loads(analysis_path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    counted = count_from_case_records(cases)

    prohibited = counted["prohibited_effects_by_policy"]
    refused = counted["refused_before_ack_by_policy"]
    supported = counted["supported_by_policy"]
    histories = counted["histories_per_policy"]

    barrier_prohibited = int(prohibited.get("barrier", -1))
    original_prohibited = int(prohibited.get("original", -1))
    strict_refusals = int(refused.get("strict", -1))
    barrier_supported = int(supported.get("barrier", -1))

    all_checks = bool(data.get("all_checks_pass"))
    raw_sha = data.get("raw_sha256") or _sha256(RAW)
    cargo = _cargo_ok()

    observations: dict[str, Any] = {
        "analysis_path": str(analysis_path.relative_to(ROOT)),
        "histories_per_policy": histories,
        "case_record_count": counted["case_record_count"],
        "cases_per_policy": counted["cases_per_policy"],
        "prohibited_effects_by_policy": prohibited,
        "refused_before_ack_by_policy": refused,
        "supported_by_policy": supported,
        "status_tallies_by_policy": counted["status_tallies_by_policy"],
        "prohibited_effects_original": original_prohibited,
        "prohibited_effects_barrier": barrier_prohibited,
        "strict_refusal_startup_refusals": strict_refusals,
        "barrier_supported": barrier_supported,
        "all_checks_pass": all_checks,
        "raw_sha256": raw_sha,
        "analyzer_sha256": data.get("analyzer_sha256"),
        "cargo_wal_recovery_barrier_ok": cargo,
        "denominator_source": "counted_from_cases",
    }

    run: dict[str, Any] = {
        "id": RUN_ID,
        "claim_id": "r1",
        "protocol_id": PROTOCOL_ID,
        "case_id": CASE_ID,
        "source_pin": SOURCE_PIN,
        "execution_status": "completed",
        "command": (
            "python3 -B experiment.py --build local-build --output local-run; "
            "python3 -B analyze.py --raw local-run/raw.json"
        ),
        "cwd": "third_party/r1/incident-sprint-artifact/recovery-barrier",
        "exit_status": 0,
        "stdout_path": "evidence/r1/experiment.log",
        "stderr_path": "evidence/r1/analyze-local.log",
        "observations": observations,
    }
    validate_run(run)

    barrier_ok = (
        barrier_prohibited == 0
        and barrier_supported == histories
        and all_checks
        and histories > 0
    )
    label = "reproduced" if barrier_ok else "contradicted_in_scope"
    finding: dict[str, Any] = {
        "id": FINDING_ID,
        "claim_id": "r1",
        "run_ids": [RUN_ID],
        "proposition": (
            "Barrier prohibited_effects==0 on pinned SoundGate recovery-barrier sweep"
        ),
        "scope": CLAIM_SCOPE,
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            f"{RUN_ID}.observations.prohibited_effects_barrier",
            f"{RUN_ID}.observations.histories_per_policy",
            f"{RUN_ID}.observations.case_record_count",
            f"{RUN_ID}.observations.all_checks_pass",
        ],
    }
    validate_finding(finding)

    run_path = RUNS_DIR / f"{RUN_ID}.json"
    finding_path = FINDINGS_DIR / f"{FINDING_ID}.json"
    _write_json(run_path, run)
    _write_json(finding_path, finding)

    notes = (
        "Derived from retained case records in local-run-analysis.json "
        f"(source {SOURCE_PIN}); counted histories_per_policy={histories}; "
        f"barrier prohibited_effects={barrier_prohibited}; "
        f"original={original_prohibited}; strict refusals={strict_refusals}. "
        f"raw_sha256={raw_sha}."
    )
    if cargo is True:
        notes += " Supplemental cargo test wal_recovery_barrier on 0.1.4: 3 passed."
    elif cargo is False:
        notes += " Supplemental cargo test wal_recovery_barrier on 0.1.4: FAILED."

    summary = {
        "histories_per_policy": histories,
        "prohibited_effects_original": original_prohibited,
        "prohibited_effects_barrier": barrier_prohibited,
        "strict_refusal_startup_refusals": strict_refusals,
        "source_revision": SOURCE_PIN,
        "denominator_source": "counted_from_cases",
        "authoritative_finding": str(finding_path.relative_to(ROOT)),
        "fresh_run": {
            "all_checks_pass": all_checks,
            "raw_sha256": raw_sha,
            "analyzer_sha256": data.get("analyzer_sha256"),
            "cases_per_policy": counted["cases_per_policy"],
            "status_tallies_by_policy": counted["status_tallies_by_policy"],
            "cargo_wal_recovery_barrier_ok": cargo,
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_result_mirror(
        label=label,
        metrics={
            "histories_per_policy": histories,
            "prohibited_effects_original": original_prohibited,
            "prohibited_effects_barrier": barrier_prohibited,
            "strict_refusal_startup_refusals": strict_refusals,
            "barrier_supported": barrier_supported,
        },
        notes=notes,
        finding_path=str(finding_path.relative_to(ROOT)),
    )
    return run, finding


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status",
        choices=("unrun", "failed", "missing", "attempted"),
        help="Write honest unresolved Run/Finding without requiring analysis",
    )
    parser.add_argument("--notes", default="", help="Notes for unresolved path")
    parser.add_argument("--command", default=None)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--exit-status", type=int, default=None)
    parser.add_argument("--stdout-path", default=None)
    parser.add_argument("--stderr-path", default=None)
    parser.add_argument("--partial-output", default=None)
    parser.add_argument(
        "--analysis",
        type=Path,
        default=ANALYSIS,
        help="Path to local-run-analysis.json",
    )
    args = parser.parse_args(argv)

    EV.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)

    if args.status:
        notes = args.notes or f"execution_status={args.status}"
        run, finding = write_unresolved(
            execution_status=args.status,
            notes=notes,
            command=args.command,
            cwd=args.cwd,
            exit_status=args.exit_status,
            stdout_path=args.stdout_path,
            stderr_path=args.stderr_path,
            partial_output=args.partial_output,
        )
        print(
            json.dumps(
                {
                    "run": str((RUNS_DIR / f"{RUN_ID}.json").relative_to(ROOT)),
                    "finding": str((FINDINGS_DIR / f"{FINDING_ID}.json").relative_to(ROOT)),
                    "label": finding["label"],
                    "execution_status": run["execution_status"],
                }
            )
        )
        return 1

    if not args.analysis.is_file():
        notes = f"missing analysis file: {args.analysis.relative_to(ROOT)}"
        run, finding = write_unresolved(execution_status="unrun", notes=notes)
        print(
            json.dumps(
                {
                    "run": str((RUNS_DIR / f"{RUN_ID}.json").relative_to(ROOT)),
                    "finding": str((FINDINGS_DIR / f"{FINDING_ID}.json").relative_to(ROOT)),
                    "label": finding["label"],
                    "execution_status": run["execution_status"],
                    "notes": notes,
                }
            )
        )
        return 1

    run, finding = derive_from_analysis(args.analysis)
    print(
        json.dumps(
            {
                "run": str((RUNS_DIR / f"{RUN_ID}.json").relative_to(ROOT)),
                "finding": str((FINDINGS_DIR / f"{FINDING_ID}.json").relative_to(ROOT)),
                "summary": str(SUMMARY.relative_to(ROOT)),
                "label": finding["label"],
                "execution_status": run["execution_status"],
                "histories_per_policy": run["observations"]["histories_per_policy"],
                "denominator_source": "counted_from_cases",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
