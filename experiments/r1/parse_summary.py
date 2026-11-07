#!/usr/bin/env python3
"""Parse local R1 analysis into evidence/r1/summary.json and result.yaml."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "evidence" / "r1"
ANALYSIS = EV / "local-run-analysis.json"
SUMMARY = EV / "summary.json"
RESULT = EV / "result.yaml"
RAW = EV / "raw.json"
CARGO_LOG = EV / "cargo-wal-recovery-barrier.log"

SOURCE_REVISION = "6568403"


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


def main() -> int:
    if not ANALYSIS.is_file():
        # Honest unresolved path: write null metrics and stop.
        summary = {
            "histories_per_policy": 153,
            "prohibited_effects_original": None,
            "prohibited_effects_barrier": None,
            "strict_refusal_startup_refusals": None,
            "source_revision": SOURCE_REVISION,
            "unresolved": True,
            "notes": f"missing analysis file: {ANALYSIS.relative_to(ROOT)}",
        }
        EV.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        result = {
            "claim_id": "r1",
            "label": "unresolved",
            "metrics": {},
            "evidence_path": "evidence/r1/summary.json",
            "notes": summary["notes"],
        }
        RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")
        print(SUMMARY)
        return 1

    data = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    policies = data["policies"]
    original = policies["original"]
    barrier = policies["barrier"]
    strict = policies["strict"]

    summary = {
        "histories_per_policy": int(data["histories_per_policy"]),
        "prohibited_effects_original": int(original["prohibited_effect"]),
        "prohibited_effects_barrier": int(barrier["prohibited_effect"]),
        "strict_refusal_startup_refusals": int(strict["refused_before_ack"]),
        "source_revision": SOURCE_REVISION,
        "fresh_run": {
            "all_checks_pass": bool(data.get("all_checks_pass")),
            "raw_sha256": data.get("raw_sha256") or _sha256(RAW),
            "analyzer_sha256": data.get("analyzer_sha256"),
            "policies": {
                "original": original,
                "strict": strict,
                "barrier": barrier,
            },
            "cargo_wal_recovery_barrier_ok": _cargo_ok(),
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    barrier_ok = (
        summary["prohibited_effects_barrier"] == 0
        and barrier.get("cases") == 153
        and bool(data.get("all_checks_pass"))
    )
    label = "reproduced" if barrier_ok else "contradicted_in_scope"
    notes = (
        "Fresh local rebuild+sweep via paper recovery-barrier harness "
        f"(source {SOURCE_REVISION}); barrier prohibited_effects="
        f"{summary['prohibited_effects_barrier']}; original="
        f"{summary['prohibited_effects_original']}; strict refusals="
        f"{summary['strict_refusal_startup_refusals']}. "
        f"raw_sha256={summary['fresh_run']['raw_sha256']}."
    )
    cargo = summary["fresh_run"]["cargo_wal_recovery_barrier_ok"]
    if cargo is True:
        notes += " Supplemental cargo test wal_recovery_barrier on 0.1.4: 3 passed."
    elif cargo is False:
        notes += " Supplemental cargo test wal_recovery_barrier on 0.1.4: FAILED."

    result = {
        "claim_id": "r1",
        "label": label,
        "metrics": {
            "histories_per_policy": summary["histories_per_policy"],
            "prohibited_effects_original": summary["prohibited_effects_original"],
            "prohibited_effects_barrier": summary["prohibited_effects_barrier"],
            "strict_refusal_startup_refusals": summary[
                "strict_refusal_startup_refusals"
            ],
            "barrier_supported": int(barrier["supported"]),
            "barrier_fresh_work": int(barrier["fresh_work"]),
        },
        "evidence_path": "evidence/r1/summary.json",
        "notes": notes,
    }
    RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")

    sys.path.insert(0, str(ROOT / "src"))
    from swarm_witness.schema import validate_result_record

    validate_result_record(yaml.safe_load(RESULT.read_text(encoding="utf-8")))
    print(json.dumps({"summary": str(SUMMARY), "result": str(RESULT), "label": label}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
