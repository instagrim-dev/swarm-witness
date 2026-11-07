#!/usr/bin/env python3
"""Three-stage comparator for r3-ledger-claim-v1.

1. Pair validity
2. Property outcome (per backend)
3. Cross-backend agreement
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))

from protocol import (  # noqa: E402
    CLAIM_ID,
    PROTOCOL_ID,
    evaluate_case_property,
    load_cases,
    project_state,
    validate_step_observation,
)
from swarm_witness.conclusion_classes import classify_matched_comparison  # noqa: E402
from swarm_witness.schema import validate_finding  # noqa: E402


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(obj)
    return rows


def pair_validity(
    *,
    cases: list[Any],
    classical_steps: list[dict[str, Any]],
    bmo_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    pairs: list[dict[str, Any]] = []

    def index(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
        out: dict[tuple[str, int], dict[str, Any]] = {}
        for row in rows:
            try:
                obs = validate_step_observation(row)
            except ValueError as exc:
                errors.append(f"invalid observation: {exc}")
                continue
            key = (obs.case_id, obs.step)
            if key in out:
                errors.append(f"duplicate observation for {key}")
            out[key] = obs.to_dict()
        return out

    c_idx = index(classical_steps)
    b_idx = index(bmo_steps)

    declared: set[tuple[str, int]] = set()
    for case in cases:
        for action in case.actions:
            declared.add((case.case_id, action.step))

    # Reject undeclared / unexpected steps on either arm.
    for source, idx in (("classical", c_idx), ("bmo", b_idx)):
        for key in idx:
            if key not in declared:
                errors.append(
                    f"undeclared extra {source} observation for {key[0]} step {key[1]}"
                )

    shared_keys = (
        "call_id",
        "task_id",
        "grant_id",
        "owner_revision",
        "retry_epoch",
        "transaction_completion",
    )

    for case in cases:
        for action in case.actions:
            key = (case.case_id, action.step)
            c = c_idx.get(key)
            b = b_idx.get(key)
            pair: dict[str, Any] = {
                "case_id": case.case_id,
                "step": action.step,
                "op": action.op,
                "classical_present": c is not None,
                "bmo_present": b is not None,
                "valid": True,
                "notes": [],
            }
            if c is None or b is None:
                pair["valid"] = False
                pair["notes"].append("missing arm observation")
                errors.append(f"{case.case_id} step {action.step}: missing arm")
            else:
                if c.get("execution_status") != "completed" or b.get("execution_status") != "completed":
                    pair["valid"] = False
                    pair["notes"].append("incomplete execution_status")
                    errors.append(
                        f"{case.case_id} step {action.step}: incomplete execution_status"
                    )
                if c.get("op") != action.op or b.get("op") != action.op:
                    pair["valid"] = False
                    pair["notes"].append("op mismatch vs case manifest")
                    errors.append(
                        f"{case.case_id} step {action.step}: op mismatch vs manifest"
                    )
                # Bind each arm to the declared action — not only cross-arm equality.
                # Identical wrong inputs on both arms must fail validity.
                if action.op == "claim_first_edit":
                    expected = {
                        "call_id": action.call_id,
                        "task_id": action.task_id,
                        "grant_id": action.grant_id,
                        "owner_revision": action.owner_revision,
                        "retry_epoch": action.retry_epoch,
                        "transaction_completion": action.transaction_completion,
                    }
                    for arm_name, arm in (("classical", c), ("bmo", b)):
                        arm_in = arm.get("inputs") or {}
                        for sk in shared_keys:
                            exp_v = expected.get(sk)
                            if exp_v is None:
                                continue
                            if arm_in.get(sk) != exp_v:
                                pair["valid"] = False
                                pair["notes"].append(
                                    f"{arm_name} input {sk} != case manifest"
                                )
                                errors.append(
                                    f"{case.case_id} step {action.step}: "
                                    f"{arm_name} input {sk} != case manifest"
                                )
                    c_in = c.get("inputs") or {}
                    b_in = b.get("inputs") or {}
                    for sk in shared_keys:
                        if c_in.get(sk) != b_in.get(sk):
                            pair["valid"] = False
                            pair["notes"].append(f"input mismatch on {sk}")
                            errors.append(
                                f"{case.case_id} step {action.step}: input mismatch {sk}"
                            )
            pairs.append(pair)

    return {
        "valid": not errors and all(p["valid"] for p in pairs),
        "errors": errors,
        "pairs": pairs,
    }


def property_outcomes(
    cases: list[Any],
    *,
    classical_steps: list[dict[str, Any]],
    bmo_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    def by_case(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            out.setdefault(str(row.get("case_id")), []).append(row)
        for cid in out:
            out[cid].sort(key=lambda r: int(r.get("step") or 0))
        return out

    c_by = by_case(classical_steps)
    b_by = by_case(bmo_steps)
    results: dict[str, Any] = {"classical": {}, "bmo": {}}
    for case in cases:
        results["classical"][case.case_id] = evaluate_case_property(
            case, c_by.get(case.case_id, [])
        )
        results["bmo"][case.case_id] = evaluate_case_property(
            case, b_by.get(case.case_id, [])
        )
    return results


def agreement(
    cases: list[Any],
    *,
    classical_steps: list[dict[str, Any]],
    bmo_steps: list[dict[str, Any]],
    validity: dict[str, Any],
) -> dict[str, Any]:
    if not validity.get("valid"):
        return {
            "result": "unresolved",
            "reason": "pair validity failed",
            "case_results": {},
        }

    def index(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
        out: dict[tuple[str, int], dict[str, Any]] = {}
        for row in rows:
            key = (str(row.get("case_id")), int(row.get("step") or 0))
            out[key] = row
        return out

    c_idx = index(classical_steps)
    b_idx = index(bmo_steps)

    case_results: dict[str, Any] = {}
    equal_all = True
    for case in cases:
        step_results: list[dict[str, Any]] = []
        case_equal = True
        for action in case.actions:
            key = (case.case_id, action.step)
            c = c_idx.get(key)
            b = b_idx.get(key)
            c_disp = None if c is None else c.get("disposition")
            b_disp = None if b is None else b.get("disposition")
            c_state = None if c is None else project_state(c.get("state"))
            b_state = None if b is None else project_state(b.get("state"))
            equal = (
                c is not None
                and b is not None
                and c_disp == b_disp
                and c_state is not None
                and c_state == b_state
            )
            if not equal:
                case_equal = False
                equal_all = False
            step_results.append(
                {
                    "step": action.step,
                    "op": action.op,
                    "equal": equal,
                    "classical_disposition": c_disp,
                    "bmo_disposition": b_disp,
                    "classical": c_state,
                    "bmo": b_state,
                }
            )
        case_results[case.case_id] = {
            "equal": case_equal,
            "steps": step_results,
        }

    if equal_all:
        return {
            "result": "matched",
            "reason": "equal dispositions and projections at every step",
            "case_results": case_results,
        }
    return {
        "result": "divergent",
        "reason": "disposition or property-relevant projection differs at a step",
        "case_results": case_results,
    }


EXPECTED_BMO_ADAPTER_ID = "bmo_l1_first_edit"
EXPECTED_PIN_PREFIX = "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe"


def qualify_native_bmo(
    *,
    run_dir: Path,
    bmo_steps: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Fail-closed native qualification.

    Defaults to false. Requires a readable source_manifest.json with
    native_bmo=true, successful process exit, expected adapter identity,
    and pinned source identity. All BMO observations must be completed
    under the expected adapter_id.
    """
    manifest_path = Path(run_dir) / "source_manifest.json"
    if not manifest_path.is_file():
        return False, "source_manifest.json missing"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"source_manifest unreadable: {exc}"
    bmo = manifest.get("bmo") if isinstance(manifest, dict) else None
    if not isinstance(bmo, dict):
        return False, "manifest.bmo missing"
    if not bmo.get("native_bmo"):
        return False, "manifest.bmo.native_bmo is not true"
    if bmo.get("exit_code") != 0:
        return False, f"manifest.bmo.exit_code={bmo.get('exit_code')!r} (require 0)"
    adapter_id = bmo.get("adapter_id")
    if adapter_id != EXPECTED_BMO_ADAPTER_ID:
        return False, f"manifest adapter_id={adapter_id!r}"
    pin = str(bmo.get("pin") or manifest.get("bmo_pin") or "")
    if not pin.startswith(EXPECTED_PIN_PREFIX[:12]):
        return False, f"manifest pin {pin!r} does not match {EXPECTED_PIN_PREFIX}"
    bridge = bmo.get("bridge")
    if not isinstance(bridge, dict) or not bridge:
        return False, "manifest.bmo.bridge hashes missing"
    for name in ("bmo_adapter_test.go", "bmo_adapter_fixture.go"):
        digest = bridge.get(name)
        if not isinstance(digest, str) or len(digest) != 64:
            return False, f"manifest.bmo.bridge[{name!r}] missing or not sha256"
    inventory = bmo.get("source_inventory")
    if not isinstance(inventory, dict):
        return False, "manifest.bmo.source_inventory missing"
    if inventory.get("materialization") != "git_archive+bridge_inject":
        return False, (
            f"source_inventory.materialization={inventory.get('materialization')!r} "
            "(require git_archive+bridge_inject)"
        )
    if not isinstance(inventory.get("git_archive_sha256"), str) or len(
        inventory["git_archive_sha256"]
    ) != 64:
        return False, "source_inventory.git_archive_sha256 missing"
    if not bmo_steps:
        return False, "no BMO observations"
    for row in bmo_steps:
        if row.get("adapter_id") != EXPECTED_BMO_ADAPTER_ID:
            return False, f"observation adapter_id={row.get('adapter_id')!r}"
        if row.get("execution_status") != "completed":
            return False, f"observation execution_status={row.get('execution_status')!r}"
    # Portable log must be archived beside the selected run when present.
    log_rel = bmo.get("log_relpath") or "bmo_go_test.log"
    log_path = Path(run_dir) / str(log_rel)
    if not log_path.is_file():
        # Accept nested work-dir log only as transitional; prefer archived root log.
        nested = Path(run_dir) / "bmo_work" / "bmo_go_test.log"
        if not nested.is_file():
            return False, f"native bridge log missing ({log_rel} or bmo_work/bmo_go_test.log)"
    return True, "native qualification ok"


def _ledger_conclusion(
    *,
    validity: dict[str, Any],
    properties: dict[str, Any],
    agree: dict[str, Any],
    native_bmo: bool,
) -> dict[str, Any]:
    """Map ledger comparator stages onto the three-way conclusion taxonomy."""
    if not native_bmo or not validity.get("valid") or agree.get("result") == "unresolved":
        return classify_matched_comparison(
            evidence_complete=False, arms_agree=None, property_holds=None
        )
    arms_agree = agree.get("result") == "matched"
    both_pass = bool(properties.get("classical")) and all(
        properties["classical"][cid]["passed"] and properties["bmo"][cid]["passed"]
        for cid in properties["classical"]
    )
    return classify_matched_comparison(
        evidence_complete=True,
        arms_agree=arms_agree,
        property_holds=both_pass if arms_agree else False,
    )


def classify_finding(
    *,
    validity: dict[str, Any],
    properties: dict[str, Any],
    agree: dict[str, Any],
    run_ids: list[str],
    native_bmo: bool = False,
) -> dict[str, Any]:
    """Map comparator stages onto Finding labels via three-way conclusions.

    missing_evidence → unresolved; failed_enforcement → contradicted_in_scope;
    supported → classical_baseline_matches. Agreement without property success
    is failed_enforcement (not a successful comparison Finding).
    """
    classified = _ledger_conclusion(
        validity=validity,
        properties=properties,
        agree=agree,
        native_bmo=native_bmo,
    )
    label = classified["finding_label"]
    cls = classified["conclusion_class"]

    if cls == "missing_evidence":
        if not native_bmo:
            proposition = (
                "Native BMO ClaimOrdinaryRetainedGrantFirstEditTx was not measured "
                "under fail-closed qualification (missing/invalid manifest, non-zero "
                "exit, wrong adapter, or non-native observations); ledger-claim "
                "comparison remains missing_evidence for the BMO pin"
            )
        else:
            proposition = (
                "Matched ledger-claim comparison incomplete: required paired "
                "observations missing, corrupt, or input-mismatched "
                "(missing_evidence)"
            )
    elif cls == "failed_enforcement":
        if agree.get("result") == "divergent":
            proposition = (
                "Backends disagree on disposition or property-relevant projection "
                "at one or more r3-ledger-claim-v1 steps (failed_enforcement)"
            )
        else:
            proposition = (
                "Backends agree on step-wise dispositions/projections, but one or "
                "both arms fail the claim success criterion (failed_enforcement); "
                "not a successful property-comparison Finding"
            )
    else:
        proposition = (
            "Across declared synthetic cases, ClassicalLedgerGate and native "
            "BMO L1 emitted equal dispositions and property-relevant "
            "projections at every step and both satisfied the one-use "
            "ledger-claim trace properties (supported)"
        )

    finding = {
        "id": "r3-ledger-claim-v1-comparison",
        "claim_id": CLAIM_ID,
        "run_ids": run_ids or ["r3-ledger-claim-v1-no-runs"],
        "proposition": proposition,
        "scope": (
            "r3-ledger-claim-v1 L1 first-edit claim/transfer under cold DB reopen "
            "and explicit rollback; not external execute/settle or process restart"
        ),
        "label": label,
        "basis": "computed",
        "supporting_observation_refs": [
            "r3-ledger-meta.observations.agreement.result",
            "r3-ledger-meta.observations.validity.valid",
        ],
    }
    # Schema requires resolvable refs for non-unresolved labels. Runner may
    # rewrite these after meta observations are finalized.
    validate_finding(finding)
    finding["conclusion_class"] = cls
    return finding


def compare_run(run_dir: Path, cases_path: Path | None = None) -> dict[str, Any]:
    run_dir = Path(run_dir)
    cases_path = cases_path or (Path(__file__).resolve().parent / "cases.yaml")
    bundle = load_cases(cases_path)
    cases = bundle["cases"]

    classical_path = run_dir / "classical.ndjson"
    bmo_path = run_dir / "bmo.ndjson"
    classical_steps = load_ndjson(classical_path)
    bmo_steps = load_ndjson(bmo_path)

    # Truncated / stale / package-log-only must not succeed.
    if not classical_steps and not bmo_steps:
        validity = {
            "valid": False,
            "errors": ["no observations on either arm"],
            "pairs": [],
        }
    else:
        validity = pair_validity(
            cases=cases, classical_steps=classical_steps, bmo_steps=bmo_steps
        )

    properties = property_outcomes(
        cases, classical_steps=classical_steps, bmo_steps=bmo_steps
    )
    agree = agreement(
        cases,
        classical_steps=classical_steps,
        bmo_steps=bmo_steps,
        validity=validity,
    )

    run_ids: list[str] = []
    runs_dir = run_dir / "runs"
    if runs_dir.is_dir():
        run_ids = sorted(p.stem for p in runs_dir.glob("*.json"))

    native_bmo, native_note = qualify_native_bmo(run_dir=run_dir, bmo_steps=bmo_steps)

    finding = classify_finding(
        validity=validity,
        properties=properties,
        agree=agree,
        run_ids=run_ids,
        native_bmo=native_bmo,
    )

    summary = {
        "protocol_id": PROTOCOL_ID,
        "claim_id": CLAIM_ID,
        "run_dir": str(run_dir),
        "validity": validity,
        "properties": properties,
        "agreement": agree,
        "native_bmo": native_bmo,
        "native_qualification": native_note,
        "conclusion_class": finding.get("conclusion_class"),
        "finding": finding,
    }
    return summary


def write_compare_artifacts(run_dir: Path, summary: dict[str, Any]) -> None:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    findings_dir = run_dir / "findings"
    findings_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    finding = summary["finding"]
    (findings_dir / f"{finding['id']}.json").write_text(
        json.dumps(finding, indent=2) + "\n", encoding="utf-8"
    )
    result = {
        "claim_id": CLAIM_ID,
        "label": finding["label"],
        "authoritative": "finding",
        "finding_path": f"findings/{finding['id']}.json",
        # Avoid metric keys that collide with r3-ledger-meta observation names
        # (evidence_index requires exact equality when names overlap).
        "metrics": {
            "classical_pass_count": sum(
                1 for v in summary["properties"]["classical"].values() if v["passed"]
            ),
            "bmo_pass_count": sum(
                1 for v in summary["properties"]["bmo"].values() if v["passed"]
            ),
            "native_bmo": bool(summary.get("native_bmo")),
        },
        "notes": summary["agreement"].get("reason"),
    }
    (run_dir / "result.yaml").write_text(
        yaml.safe_dump(result, sort_keys=False), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).resolve().parent / "cases.yaml",
    )
    args = parser.parse_args(argv)
    summary = compare_run(args.run_dir, cases_path=args.cases)
    write_compare_artifacts(args.run_dir, summary)
    print(
        json.dumps(
            {
                "label": summary["finding"]["label"],
                "agreement": summary["agreement"]["result"],
                "validity": summary["validity"]["valid"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
