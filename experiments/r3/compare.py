#!/usr/bin/env python3
"""Compare ClassicalGate to BMO retained-grant proxies — without circular match.

ClassicalGate decisions are computed from the null model. BMO side records only
whether related preexisting tests passed (proxy evidence). Interpretive notes
describe mechanism-class affinity; they are never copied into an automated
allow/deny equality that would tautologically "match" ClassicalGate.
"""

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

# Each row: ClassicalGate inputs + related BMO proxy signals.
# relation:
#   mechanism_class_proxy — related deny/allow-shaped tests, not isomorphic
#   proxy_mismatch        — previously over-mapped; classical condition lacks
#                           an isomorphic BMO observation in this suite
# interpretive_note is human-authored disclosure only (never used as bmo_observed).
COMPARISON_ROWS = (
    {
        "condition": "retained_start_claim + relaunch",
        "action_id": "spawn-1",
        "request": "relaunch",
        "grant_state": "retained_start_claim",
        "relation": "mechanism_class_proxy",
        "interpretive_note": (
            "Spent / prior-consumer / missing-transfer refusals are deny-shaped "
            "proxies for 'retained metadata ≠ relaunch authority'; not an "
            "isomorphic retained_start_claim+relaunch API."
        ),
        "required_pass_tests": (
            "TestOrdinaryRetryRetainedGrantShapeControls",
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness",
        ),
        "log_substrings": (
            "TestOrdinaryRetryRetainedGrantShapeControls/spent",
            "TestOrdinaryRetryRetainedGrantShapeControls/prior_consumer",
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness/missing_transfer",
        ),
    },
    {
        "condition": "rejected + restart + execute",
        "action_id": "mail-1",
        "request": "execute",
        "grant_state": "rejected",
        # LegacyWriterBoundary is a competing-writer / tombstone race, not
        # process-restart map reload. Do not treat it as isomorphic evidence.
        "relation": "proxy_mismatch",
        "interpretive_note": (
            "ClassicalGate models rejected-state surviving process restart "
            "reload. BMO LegacyWriterBoundary / transfer races are a different "
            "contract (writer boundary after durable transfer), so this row "
            "is not claimed as a decision match."
        ),
        "required_pass_tests": (),
        "log_substrings": (),
        "related_but_not_isomorphic_tests": (
            "TestOrdinaryRetainedGrantLegacyWriterBoundary",
        ),
    },
    {
        "condition": "active_grant + execute",
        "action_id": "edit-1",
        "request": "execute",
        "grant_state": "active_grant",
        "relation": "mechanism_class_proxy",
        "interpretive_note": (
            "Owner-witness + post-edit PASS shows a valid grant admits work; "
            "related allow-shaped proxy, not a shared active_grant execute API."
        ),
        "required_pass_tests": (
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness",
            "TestOrdinaryRetryRetainedGrantSyntheticAppliedPostEdit",
        ),
        "log_substrings": (
            "--- PASS: TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness ",
            "--- PASS: TestOrdinaryRetryRetainedGrantSyntheticAppliedPostEdit ",
        ),
    },
    {
        "condition": "stale grant copy vs current",
        "action_id": "edit-1",
        "request": "execute",
        "grant_state": "rejected",  # classical: stale/rejected map entry → deny
        "relation": "mechanism_class_proxy",
        "interpretive_note": (
            "wrong_grant / altered_transfer / tampered_transfer are deny-shaped "
            "stale-or-foreign proxies; related to stale-copy denial, not "
            "isomorphic ClassicalGate.load(rejected) semantics."
        ),
        "required_pass_tests": (
            "TestOrdinaryRetryRetainedGrantShapeControls",
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness",
            "TestOrdinaryRetryRetainedGrantSyntheticAppliedPostEdit",
        ),
        "log_substrings": (
            "TestOrdinaryRetryRetainedGrantShapeControls/wrong_grant",
            "TestOrdinaryRetryRetainedGrantSyntheticOwnerWitness/altered_transfer",
            "TestOrdinaryRetryRetainedGrantSyntheticAppliedPostEdit/tampered_transfer",
        ),
    },
)


def _parse_go_test_log(text: str) -> dict:
    passed = re.findall(r"^--- PASS: (\S+)", text, re.M)
    failed = re.findall(r"^--- FAIL: (\S+)", text, re.M)
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


def _classical_decision(row: dict) -> str:
    gate = ClassicalGate(grants={row["action_id"]: row["grant_state"]})
    classical = gate.decide(row["action_id"], row["request"])
    if row["condition"].startswith("stale"):
        classical = ClassicalGate.load({row["action_id"]: "rejected"}).decide(
            row["action_id"], row["request"]
        )
    return classical


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
    proxy_rows_ok = 0
    isomorphic_matches = 0
    for row in COMPARISON_ROWS:
        classical = _classical_decision(row)
        tests_ok = all(t in passed_set for t in row["required_pass_tests"])
        signals_ok = all(_signal_present(log_text, s) for s in row["log_substrings"])
        # Automated evidence: proxy suite observed — never invents bmo allow/deny.
        proxy_evidence_ok = (
            row["relation"] == "mechanism_class_proxy"
            and signals_ok
            and tests_ok
            and parsed["package_ok"]
        )
        if proxy_evidence_ok:
            proxy_rows_ok += 1

        # No isomorphic decision match is claimed: interpretive notes stay separate
        # and are never copied into an automated classical == bmo equality.
        decision_match = False

        entry = {
            "condition": row["condition"],
            "classical": classical,
            "bmo_observed": "not_isomorphic",
            "relation": row["relation"],
            "interpretive_note": row["interpretive_note"],
            "decision_match": decision_match,
            "proxy_evidence_ok": proxy_evidence_ok,
            "signals_ok": signals_ok,
            "tests_ok": tests_ok,
        }
        if row.get("related_but_not_isomorphic_tests"):
            entry["related_but_not_isomorphic_tests"] = list(
                row["related_but_not_isomorphic_tests"]
            )
            entry["related_tests_present"] = all(
                t in passed_set for t in row["related_but_not_isomorphic_tests"]
            )
        comparison.append(entry)

    # Honest overall label: proxies show mechanism-class affinity under
    # assumptions, not isomorphic classical_baseline_matches contracts.
    if not parsed["package_ok"]:
        label = "unresolved"
    else:
        label = "assumption_dependent"

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
        "proxy_rows_ok": proxy_rows_ok,
        "proxy_rows_total": sum(
            1 for r in COMPARISON_ROWS if r["relation"] == "mechanism_class_proxy"
        ),
        "isomorphic_decision_matches": isomorphic_matches,
        "total_rows": len(comparison),
        "label": label,
        "preferred_tests": [
            "internal/sessioncompaction/ordinary_retry_retained_grant_owner_witness_test.go",
            "internal/sessioncompaction/ordinary_retry_retained_grant_test.go",
            "internal/sessioncompaction/ordinary_retry_retained_grant_race_test.go",
        ],
        "notes": (
            "assumption_dependent: ClassicalGate and BMO share mechanism-class "
            "affinity via related deny/allow-shaped proxies only. No isomorphic "
            "decision match is claimed (bmo_observed is not hardcoded from "
            "ClassicalGate). rejected+restart maps to process-reload in the "
            "null model; LegacyWriterBoundary is a writer-boundary race and is "
            "recorded as proxy_mismatch, not a match."
            if label == "assumption_dependent"
            else "BMO package did not pass; see comparison[] / bmo_go_test."
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    result = {
        "claim_id": "r3",
        "label": label,
        "metrics": {
            "proxy_rows_ok": summary["proxy_rows_ok"],
            "proxy_rows_total": summary["proxy_rows_total"],
            "isomorphic_decision_matches": summary["isomorphic_decision_matches"],
            "total_rows": summary["total_rows"],
            "bmo_pass_count": parsed["pass_count"],
            "bmo_fail_count": parsed["fail_count"],
        },
        "evidence_path": "evidence/r3/summary.json",
        "notes": summary["notes"],
    }
    validate_result_record(result)
    RESULT.write_text(yaml.safe_dump(result, sort_keys=False), encoding="utf-8")

    if BASELINE_MD.is_file():
        table_lines = [
            "| Condition | ClassicalGate | BMO observed | Relation | Proxy evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
        for c in comparison:
            table_lines.append(
                f"| {c['condition']} | {c['classical']} | {c['bmo_observed']} | "
                f"{c['relation']} | {'yes' if c['proxy_evidence_ok'] else 'n/a' if c['relation'] == 'proxy_mismatch' else 'no'} |"
            )
        body = BASELINE_MD.read_text(encoding="utf-8")
        marker = "## Discriminating comparison (from latest run)\n"
        if marker in body:
            head, _, rest = body.partition(marker)
            tail = ""
            if "\n## " in rest:
                _, tail = rest.split("\n## ", 1)
                tail = "\n## " + tail
            BASELINE_MD.write_text(
                head + marker + "\n" + "\n".join(table_lines) + "\n" + tail,
                encoding="utf-8",
            )

    ok = label == "assumption_dependent" and parsed["package_ok"]
    print(
        json.dumps(
            {
                "summary": str(SUMMARY),
                "result": str(RESULT),
                "label": label,
                "proxy": f"{summary['proxy_rows_ok']}/{summary['proxy_rows_total']}",
                "isomorphic_matches": isomorphic_matches,
            }
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
