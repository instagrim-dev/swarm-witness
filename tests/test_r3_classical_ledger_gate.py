"""ClassicalLedgerGate one-use ledger property tests."""

from __future__ import annotations

from pathlib import Path

from swarm_witness.classical_ledger_gate import ClassicalLedgerGate


def _fixture(**overrides):
    base = {
        "task_id": "task-alpha",
        "grant_id": "grant-alpha",
        "owner_revision": 1,
        "retry_epoch": "epoch-1",
        "initial_spent": False,
    }
    base.update(overrides)
    return base


def test_t02_spent_persists_across_reopen(tmp_path: Path):
    gate = ClassicalLedgerGate(tmp_path / "g.sqlite")
    gate.open_case(_fixture())
    r1 = gate.claim_first_edit(
        call_id="a",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert r1["disposition"] == "committed"
    gate.reopen()
    r2 = gate.claim_first_edit(
        call_id="b",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert r2["disposition"] == "refused"
    state = gate.inspect()
    assert state["grant_spent"] is True
    assert state["claim_count"] == 1
    assert state["claim_call_ids"] == ["a"]
    gate.close()


def test_t03_unspent_after_reopen_can_commit(tmp_path: Path):
    gate = ClassicalLedgerGate(tmp_path / "g.sqlite")
    gate.open_case(_fixture())
    gate.reopen()
    r = gate.claim_first_edit(
        call_id="a",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert r["disposition"] == "committed"
    gate.close()


def test_t04_rollback_preserves_progress(tmp_path: Path):
    gate = ClassicalLedgerGate(tmp_path / "g.sqlite")
    gate.open_case(_fixture())
    r1 = gate.claim_first_edit(
        call_id="rolled",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
        transaction_completion="rollback_after_native_success",
    )
    assert r1["disposition"] == "rolled_back"
    assert gate.inspect()["claim_count"] == 0
    r2 = gate.claim_first_edit(
        call_id="a",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert r2["disposition"] == "committed"
    assert gate.inspect()["claim_call_ids"] == ["a"]
    gate.close()


def test_wrong_task_does_not_consume(tmp_path: Path):
    gate = ClassicalLedgerGate(tmp_path / "g.sqlite")
    gate.open_case(_fixture())
    bad = gate.claim_first_edit(
        call_id="bad",
        task_id="task-foreign",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert bad["disposition"] == "refused"
    assert gate.inspect()["grant_spent"] is False
    ok = gate.claim_first_edit(
        call_id="a",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert ok["disposition"] == "committed"
    gate.close()


def test_wrong_owner_revision_does_not_consume(tmp_path: Path):
    gate = ClassicalLedgerGate(tmp_path / "g.sqlite")
    gate.open_case(_fixture())
    bad = gate.claim_first_edit(
        call_id="bad",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=0,
        retry_epoch="epoch-1",
    )
    assert bad["disposition"] == "refused"
    assert gate.inspect()["grant_spent"] is False
    gate.close()


def test_always_deny_fails_t03_semantics(tmp_path: Path):
    """Control: a gate that always refuses must not look like T03 success."""
    gate = ClassicalLedgerGate(tmp_path / "g.sqlite")
    gate.open_case(_fixture())
    # Simulate always-deny by presenting wrong revision forever.
    gate.reopen()
    r = gate.claim_first_edit(
        call_id="a",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=99,
        retry_epoch="epoch-1",
    )
    assert r["disposition"] == "refused"
    assert gate.inspect()["claim_count"] == 0
    gate.close()


def test_decisions_not_selected_by_call_id_label(tmp_path: Path):
    gate = ClassicalLedgerGate(tmp_path / "g.sqlite")
    gate.open_case(_fixture())
    # Same inputs with different call ids must not change allow/refuse policy
    # except uniqueness after spend.
    r1 = gate.claim_first_edit(
        call_id="label-does-not-matter",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert r1["disposition"] == "committed"
    r2 = gate.claim_first_edit(
        call_id="also-irrelevant",
        task_id="task-alpha",
        grant_id="grant-alpha",
        owner_revision=1,
        retry_epoch="epoch-1",
    )
    assert r2["disposition"] == "refused"
    gate.close()
