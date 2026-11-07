"""Comparator stage tests for r3-ledger-claim-v1."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "r3" / "ledger_claim_v1"


def _load(name: str, path: Path):
    sys.path.insert(0, str(PKG))
    sys.path.insert(0, str(ROOT / "src"))
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _step(
    case_id: str,
    step: int,
    op: str,
    *,
    adapter: str,
    disposition: str | None,
    state: dict | None,
    inputs: dict | None = None,
    execution_status: str = "completed",
) -> dict:
    return {
        "protocol_id": "r3-ledger-claim-v1",
        "case_id": case_id,
        "step": step,
        "op": op,
        "adapter_id": adapter,
        "execution_status": execution_status,
        "disposition": disposition,
        "inputs": inputs or {},
        "native_result": {},
        "state": state,
        "notes": "",
    }


def _t03_happy(adapter: str) -> list[dict]:
    spent = {
        "grant_spent": True,
        "claim_count": 1,
        "transfer_count": 1,
        "claims": [
            {
                "call_id": "call-t03-a",
                "task_id": "task-alpha",
                "grant_id": "grant-alpha",
                "owner_revision": 1,
                "retry_epoch": "epoch-1",
            }
        ],
        "transfers": [
            {
                "call_id": "call-t03-a",
                "task_id": "task-alpha",
                "grant_id": "grant-alpha",
                "owner_revision": 1,
                "retry_epoch": "epoch-1",
            }
        ],
        "claim_call_ids": ["call-t03-a"],
        "transfer_call_ids": ["call-t03-a"],
    }
    claim_inputs = {
        "call_id": "call-t03-a",
        "task_id": "task-alpha",
        "grant_id": "grant-alpha",
        "owner_revision": 1,
        "retry_epoch": "epoch-1",
        "transaction_completion": "commit",
    }
    return [
        _step("T03", 1, "reopen", adapter=adapter, disposition="observed", state={
            "grant_spent": False,
            "claim_count": 0,
            "transfer_count": 0,
            "claims": [],
            "transfers": [],
            "claim_call_ids": [],
            "transfer_call_ids": [],
        }),
        _step(
            "T03",
            2,
            "claim_first_edit",
            adapter=adapter,
            disposition="committed",
            state=spent,
            inputs=claim_inputs,
        ),
        _step("T03", 3, "inspect", adapter=adapter, disposition="observed", state=spent),
    ]


def test_equal_and_correct_is_matched(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    # Build minimal cases bundle with only T03 for focused fixture.
    all_cases = proto.load_cases(PKG / "cases.yaml")
    t03 = next(c for c in all_cases["cases"] if c.case_id == "T03")

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    c_steps = _t03_happy("classical_ledger_gate")
    b_steps = _t03_happy("bmo")
    (run_dir / "classical.ndjson").write_text(
        "\n".join(json.dumps(s) for s in c_steps) + "\n", encoding="utf-8"
    )
    (run_dir / "bmo.ndjson").write_text(
        "\n".join(json.dumps(s) for s in b_steps) + "\n", encoding="utf-8"
    )

    validity = compare.pair_validity(
        cases=[t03], classical_steps=c_steps, bmo_steps=b_steps
    )
    assert validity["valid"] is True
    props = compare.property_outcomes(
        [t03], classical_steps=c_steps, bmo_steps=b_steps
    )
    assert props["classical"]["T03"]["passed"]
    assert props["bmo"]["T03"]["passed"]
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "matched"


def test_equal_but_wrong_preserves_agreement_without_success_finding():
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    t03 = next(c for c in proto.load_cases(PKG / "cases.yaml")["cases"] if c.case_id == "T03")
    wrong = {
        "grant_spent": False,
        "claim_count": 0,
        "transfer_count": 0,
        "claims": [],
        "transfers": [],
        "claim_call_ids": [],
        "transfer_call_ids": [],
    }
    claim_inputs = {
        "call_id": "call-t03-a",
        "task_id": "task-alpha",
        "grant_id": "grant-alpha",
        "owner_revision": 1,
        "retry_epoch": "epoch-1",
        "transaction_completion": "commit",
    }
    # Both refuse first claim — equal projections, both fail T03 property.
    c_steps = [
        _step("T03", 1, "reopen", adapter="c", disposition="observed", state=wrong),
        _step(
            "T03",
            2,
            "claim_first_edit",
            adapter="c",
            disposition="refused",
            state=wrong,
            inputs=claim_inputs,
        ),
        _step("T03", 3, "inspect", adapter="c", disposition="observed", state=wrong),
    ]
    b_steps = [
        _step("T03", 1, "reopen", adapter="b", disposition="observed", state=wrong),
        _step(
            "T03",
            2,
            "claim_first_edit",
            adapter="b",
            disposition="refused",
            state=wrong,
            inputs=claim_inputs,
        ),
        _step("T03", 3, "inspect", adapter="b", disposition="observed", state=wrong),
    ]
    validity = compare.pair_validity(cases=[t03], classical_steps=c_steps, bmo_steps=b_steps)
    props = compare.property_outcomes([t03], classical_steps=c_steps, bmo_steps=b_steps)
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "matched"
    assert props["classical"]["T03"]["passed"] is False
    finding = compare.classify_finding(
        validity=validity,
        properties=props,
        agree=agree,
        run_ids=["r1"],
        native_bmo=True,
    )
    # Agreement is preserved in comparator observations, but complete evidence
    # with failed properties is failed_enforcement — not a success Finding.
    assert finding["label"] == "contradicted_in_scope"
    assert finding.get("conclusion_class") == "failed_enforcement"
    assert "fail" in finding["proposition"].lower()


def test_agreement_compares_every_step_not_only_final_state():
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    t03 = next(c for c in proto.load_cases(PKG / "cases.yaml")["cases"] if c.case_id == "T03")
    c_steps = _t03_happy("classical_ledger_gate")
    b_steps = _t03_happy("bmo_l1_first_edit")
    # Intermediate reopen states diverge; finals still match.
    empty = {
        "grant_spent": False,
        "claim_count": 0,
        "transfer_count": 0,
        "claims": [],
        "transfers": [],
        "claim_call_ids": [],
        "transfer_call_ids": [],
    }
    mid = dict(empty)
    mid["grant_spent"] = True
    b_steps[0]["state"] = mid
    validity = compare.pair_validity(cases=[t03], classical_steps=c_steps, bmo_steps=b_steps)
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "divergent"
    assert agree["case_results"]["T03"]["equal"] is False


def test_duplicate_classical_as_bmo_without_manifest_is_unresolved(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    c_steps = _t03_happy("classical_ledger_gate")
    # Adversarial: copy classical rows into bmo.ndjson; omit source_manifest.
    payload = "\n".join(json.dumps(s) for s in c_steps) + "\n"
    (run_dir / "classical.ndjson").write_text(payload, encoding="utf-8")
    (run_dir / "bmo.ndjson").write_text(payload, encoding="utf-8")
    summary = compare.compare_run(run_dir, cases_path=PKG / "cases.yaml")
    assert summary["native_bmo"] is False
    assert summary["finding"]["label"] == "unresolved"


def _native_manifest(*, exit_code: int = 0) -> dict:
    return {
        "bmo": {
            "native_bmo": True,
            "exit_code": exit_code,
            "adapter_id": "bmo_l1_first_edit",
            "pin": "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe",
            "mode": "go_test_bridge_native",
            "bridge": {
                "bmo_adapter_test.go": "a" * 64,
                "bmo_adapter_fixture.go": "b" * 64,
            },
            "source_inventory": {
                "materialization": "git_archive+bridge_inject",
                "git_archive_sha256": "c" * 64,
            },
            "log_relpath": "bmo_go_test.log",
        }
    }


def test_manifest_native_requires_exit_zero_and_adapter_identity(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    c_steps = _t03_happy("classical_ledger_gate")
    b_steps = _t03_happy("bmo_l1_first_edit")
    (run_dir / "classical.ndjson").write_text(
        "\n".join(json.dumps(s) for s in c_steps) + "\n", encoding="utf-8"
    )
    (run_dir / "bmo.ndjson").write_text(
        "\n".join(json.dumps(s) for s in b_steps) + "\n", encoding="utf-8"
    )
    (run_dir / "bmo_go_test.log").write_text("ok\n", encoding="utf-8")
    (run_dir / "source_manifest.json").write_text(
        json.dumps(_native_manifest(exit_code=1)) + "\n",
        encoding="utf-8",
    )
    summary = compare.compare_run(run_dir, cases_path=PKG / "cases.yaml")
    assert summary["native_bmo"] is False
    assert summary["finding"]["label"] == "unresolved"


def test_manifest_without_source_inventory_is_unresolved(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    c_steps = _t03_happy("classical_ledger_gate")
    b_steps = _t03_happy("bmo_l1_first_edit")
    (run_dir / "classical.ndjson").write_text(
        "\n".join(json.dumps(s) for s in c_steps) + "\n", encoding="utf-8"
    )
    (run_dir / "bmo.ndjson").write_text(
        "\n".join(json.dumps(s) for s in b_steps) + "\n", encoding="utf-8"
    )
    (run_dir / "bmo_go_test.log").write_text("ok\n", encoding="utf-8")
    bad = _native_manifest()
    del bad["bmo"]["source_inventory"]
    (run_dir / "source_manifest.json").write_text(json.dumps(bad) + "\n", encoding="utf-8")
    summary = compare.compare_run(run_dir, cases_path=PKG / "cases.yaml")
    assert summary["native_bmo"] is False
    assert "source_inventory" in summary["native_qualification"]


def test_project_state_ignores_grant_epoch_identity_mismatch():
    """Negative control: grant/epoch are not part of L1 equality without alias map."""
    proto = _load("ledger_protocol", PKG / "protocol.py")
    classical = {
        "grant_spent": True,
        "claim_count": 1,
        "transfer_count": 1,
        "claims": [
            {
                "call_id": "call-a",
                "task_id": "task-alpha",
                "grant_id": "grant-alpha",
                "retry_epoch": "epoch-1",
                "owner_revision": 1,
            }
        ],
        "transfers": [
            {
                "call_id": "call-a",
                "task_id": "task-alpha",
                "grant_id": "grant-alpha",
                "retry_epoch": "epoch-1",
                "owner_revision": 1,
            }
        ],
    }
    # Native arm uses hashed durable identities — must not break call_id equality.
    native = {
        "grant_spent": True,
        "claim_count": 1,
        "transfer_count": 1,
        "claims": [
            {
                "call_id": "call-a",
                "task_id": "deadbeef",
                "grant_id": "cafebabe" * 4,
                "retry_epoch": "episode-hash",
                "owner_revision": 99,
            }
        ],
        "transfers": [
            {
                "call_id": "call-a",
                "task_id": "deadbeef",
                "grant_id": "cafebabe" * 4,
                "retry_epoch": "episode-hash",
                "owner_revision": 99,
            }
        ],
    }
    assert proto.project_state(classical) == proto.project_state(native)
    # If grant_id were compared, these would diverge — document that we do not.
    assert classical["claims"][0]["grant_id"] != native["claims"][0]["grant_id"]


def test_mismatched_call_id_still_diverges():
    proto = _load("ledger_protocol", PKG / "protocol.py")
    a = proto.project_state(
        {
            "grant_spent": True,
            "claim_count": 1,
            "transfer_count": 0,
            "claims": [{"call_id": "a"}],
            "transfers": [],
        }
    )
    b = proto.project_state(
        {
            "grant_spent": True,
            "claim_count": 1,
            "transfer_count": 0,
            "claims": [{"call_id": "b"}],
            "transfers": [],
        }
    )
    assert a != b


def test_valid_divergence():
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    t03 = next(c for c in proto.load_cases(PKG / "cases.yaml")["cases"] if c.case_id == "T03")
    c_steps = _t03_happy("classical")
    b_steps = _t03_happy("bmo")
    # Mutate BMO final state claim identity while keeping counts — identity-bound diverge.
    for s in b_steps:
        if s.get("state") and s["state"].get("claims"):
            s["state"]["claims"][0]["call_id"] = "other"
            s["state"]["claim_call_ids"] = ["other"]
            s["state"]["transfers"][0]["call_id"] = "other"
            s["state"]["transfer_call_ids"] = ["other"]
    validity = compare.pair_validity(cases=[t03], classical_steps=c_steps, bmo_steps=b_steps)
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "divergent"


def test_truncated_ndjson_unresolved(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "classical.ndjson").write_text("{}\n", encoding="utf-8")
    (run_dir / "bmo.ndjson").write_text("", encoding="utf-8")
    summary = compare.compare_run(run_dir, cases_path=PKG / "cases.yaml")
    assert summary["finding"]["label"] == "unresolved"
    assert summary["validity"]["valid"] is False


def test_input_mismatch_not_policy_disagreement():
    compare = _load("ledger_compare", PKG / "compare.py")
    proto = _load("ledger_protocol", PKG / "protocol.py")
    t03 = next(c for c in proto.load_cases(PKG / "cases.yaml")["cases"] if c.case_id == "T03")
    c_steps = _t03_happy("c")
    b_steps = _t03_happy("b")
    for s in b_steps:
        if s["op"] == "claim_first_edit":
            s["inputs"]["task_id"] = "task-OTHER"
    validity = compare.pair_validity(cases=[t03], classical_steps=c_steps, bmo_steps=b_steps)
    assert validity["valid"] is False
    assert any("input mismatch" in e for e in validity["errors"])
    agree = compare.agreement(
        [t03], classical_steps=c_steps, bmo_steps=b_steps, validity=validity
    )
    assert agree["result"] == "unresolved"


def test_green_package_log_cannot_fill_observations(tmp_path: Path):
    compare = _load("ledger_compare", PKG / "compare.py")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "bmo_go_test.log").write_text("PASS ok\n", encoding="utf-8")
    # No NDJSON — package log alone must not yield matched.
    summary = compare.compare_run(run_dir, cases_path=PKG / "cases.yaml")
    assert summary["finding"]["label"] == "unresolved"
