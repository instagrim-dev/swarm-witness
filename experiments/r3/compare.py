#!/usr/bin/env python3
"""Compare ClassicalGate decisions to BMO retained-grant witness observations."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

from swarm_witness.classical_gate import ClassicalGate
from swarm_witness.schema import validate_result_record

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "evidence" / "r3"
LOG = EV / "bmo_go_test.log"
SUMMARY = EV / "summary.json"
RESULT = EV / "result.yaml"
BASELINE_MD = ROOT / "baselines" / "r3_durable_grant_table.md"

# Conditions aligned with claims/r3_bmo.yaml and the task-5 comparison table.
# Signals are substrings that appear in a *passing* `go test -v` log (test /
# subtest PASS lines). Assertion message text is not emitted on success, so we
# do not require it. BMO allow/deny is the contract those passed tests enforce.
COMPARISON_ROWS = (
    {
        "condition": "retained_start_claim + relaunch",
        "action_id": "spawn-1",
        "request": "relaunch",
        "grant_state": "retained_start_claim",
        # Spent / prior-consumer shape refusals: retained metadata ≠ relaunch.
        "required_pass_tests": (
            "TestOrdinaryRetryRetainedGrantShapeControls",
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness",
        ),
        "log_substrings": (
            "TestOrdinaryRetryRetainedGrantShapeControls/spent",
            "TestOrdinaryRetryRetainedGrantShapeControls/prior_consumer",
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness/missing_transfer",
        ),
        "bmo_decision_if_pass": "deny",
    },
    {
        "condition": "rejected + restart + execute",
        "action_id": "mail-1",
        "request": "execute",
        "grant_state": "rejected",
        # Durable transfer/legacy tombstone: competing claim after winner commits.
        "required_pass_tests": (
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness",
            "TestOrdinaryRetainedGrantLegacyWriterBoundary",
        ),
        "log_substrings": (
            "TestOrdinaryRetainedGrantLegacyWriterBoundary/transfer_first",
            "TestOrdinaryRetainedGrantLegacyWriterBoundary/legacy_first",
        ),
        "bmo_decision_if_pass": "deny",
    },
    {
        "condition": "active_grant + execute",
        "action_id": "edit-1",
        "request": "execute",
        "grant_state": "active_grant",
        # Valid owner-verified grant admits first-edit / post-edit path.
        "required_pass_tests": (
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness",
            "TestOrdinaryRetryRetainedGrantSyntheticAppliedPostEdit",
        ),
        "log_substrings": (
            "--- PASS: TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness ",
            "--- PASS: TestOrdinaryRetryRetainedGrantSyntheticAppliedPostEdit ",
        ),
        "bmo_decision_if_pass": "allow",
    },
    {
        "condition": "stale grant copy vs current",
        "action_id": "edit-1",
        "request": "execute",
        "grant_state": "rejected",  # classical: stale/rejected map entry → deny
        "required_pass_tests": (
            "TestOrdinaryRetryRetainedGrantShapeControls",
            "TestOrdinaryRetainedGrantLegacyWriterBoundary",
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness",
        ),
        "log_substrings": (
            "TestOrdinaryRetryRetainedGrantShapeControls/wrong_grant",
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness/altered_transfer",
            "TestOrdinaryRetryRetainedGrantSyntheticAppliedPostEdit/tampered_transfer",
        ),
        "bmo_decision_if_pass": "deny",
    },
)


def _parse_go_test_log(text: str) -> dict:
    # --- PASS: TestFoo (0.01s)  /  --- FAIL: TestFoo
    passed = re.findall(r"^--- PASS: (\S+)", text, re.M)
    failed = re.findall(r"^--- FAIL: (\S+)", text, re.M)
    # Package summary: ok / FAIL
    pkg_ok = bool(re.search(r"^ok\s+\S+/sessioncompaction\b", text, re.M))
    pkg_fail = bool(re.search(r"^FAIL\s+\S+/sessioncompaction\b", text, re.M))
    return {
        "passed_tests": passed,
        "failed_tests": failed,
        "pass_count": len(passed),
        "fail_count": len(failed),
        "package_ok": pkg_ok and not pkg_fail and len(failed) == 0,
        "log_bytes": len(text.encode("utf-8")),
    }


def _signal_present(text: str, signal: str) -> bool:
    return signal in text


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    if not LOG.is_file():
        summary = {
            "unresolved": True,
            "notes": f"missing BMO log: {LOG.relative_to(ROOT)}",
            "comparison": [],
        }
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        result = {
            "claim_id": "r3",
            "label": "unresolved",
            "metrics": {},
            "evidence_path": "evidence/r3/summary.json",
            "notes": summary["notes"],
        }
        RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")
        print(json.dumps({"summary": str(SUMMARY), "result": str(RESULT), "label": "unresolved"}))
        return 1

    log_text = LOG.read_text(encoding="utf-8", errors="replace")
    parsed = _parse_go_test_log(log_text)
    passed_set = set(parsed["passed_tests"])

    comparison: list[dict] = []
    mismatches = 0
    for row in COMPARISON_ROWS:
        gate = ClassicalGate(grants={row["action_id"]: row["grant_state"]})
        classical = gate.decide(row["action_id"], row["request"])
        # For stale-copy row, classical uses a reloaded rejected map (same deny).
        if row["condition"].startswith("stale"):
            classical = ClassicalGate.load({row["action_id"]: "rejected"}).decide(
                row["action_id"], row["request"]
            )

        tests_ok = all(t in passed_set for t in row["required_pass_tests"])
        signals_ok = all(_signal_present(log_text, s) for s in row["log_substrings"])
        observed_ok = signals_ok and tests_ok and parsed["package_ok"]
        bmo = row["bmo_decision_if_pass"] if observed_ok else "unobserved"
        match = observed_ok and classical == bmo
        if not match:
            mismatches += 1
        comparison.append(
            {
                "condition": row["condition"],
                "classical": classical,
                "bmo_observed": bmo,
                "match": match,
                "signals_ok": signals_ok,
                "tests_ok": tests_ok,
            }
        )

    all_match = mismatches == 0 and parsed["package_ok"]
    label = "classical_baseline_matches" if all_match else (
        "assumption_dependent" if parsed["package_ok"] else "unresolved"
    )

    summary = {
        "claim_id": "r3",
        "bmo_go_test": {
            "pass_count": parsed["pass_count"],
            "fail_count": parsed["fail_count"],
            "package_ok": parsed["package_ok"],
            "passed_tests": parsed["passed_tests"],
            "failed_tests": parsed["failed_tests"],
            "log": str(LOG.relative_to(ROOT)),
        },
        "comparison": comparison,
        "matched_rows": sum(1 for c in comparison if c["match"]),
        "total_rows": len(comparison),
        "label": label,
        "preferred_tests": [
            "internal/sessioncompaction/ordinary_retry_retained_grant_owner_witness_test.go",
            "internal/sessioncompaction/ordinary_retry_retained_grant_test.go",
            "internal/sessioncompaction/ordinary_retry_retained_grant_race_test.go",
        ],
        "notes": (
            "ClassicalGate durable-grant map decisions match BMO retained-grant "
            "owner-witness observations under matched conditions (deny retained "
            "relaunch / rejected reload / stale copy; allow only active grant)."
            if all_match
            else "One or more comparison rows did not match; see comparison[]."
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    result = {
        "claim_id": "r3",
        "label": label,
        "metrics": {
            "matched_rows": summary["matched_rows"],
            "total_rows": summary["total_rows"],
            "bmo_pass_count": parsed["pass_count"],
            "bmo_fail_count": parsed["fail_count"],
        },
        "evidence_path": "evidence/r3/summary.json",
        "notes": summary["notes"],
    }
    validate_result_record(result)
    RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")

    # Refresh markdown table in the baseline note if present.
    if BASELINE_MD.is_file():
        table_lines = [
            "| Condition | ClassicalGate | BMO observed | Match |",
            "| --- | --- | --- | --- |",
        ]
        for c in comparison:
            table_lines.append(
                f"| {c['condition']} | {c['classical']} | {c['bmo_observed']} | "
                f"{'yes' if c['match'] else 'no'} |"
            )
        body = BASELINE_MD.read_text(encoding="utf-8")
        marker = "## Discriminating comparison (from latest run)\n"
        if marker in body:
            head, _, rest = body.partition(marker)
            # Drop old table until next ## or EOF
            tail = ""
            if "\n## " in rest:
                _, tail = rest.split("\n## ", 1)
                tail = "\n## " + tail
            BASELINE_MD.write_text(
                head + marker + "\n" + "\n".join(table_lines) + "\n" + tail,
                encoding="utf-8",
            )

    print(
        json.dumps(
            {
                "summary": str(SUMMARY),
                "result": str(RESULT),
                "label": label,
                "matched": f"{summary['matched_rows']}/{summary['total_rows']}",
            }
        )
    )
    return 0 if all_match else 1


if __name__ == "__main__":
    sys.exit(main())
