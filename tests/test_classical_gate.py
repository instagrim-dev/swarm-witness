from swarm_witness.classical_gate import ClassicalGate


def test_retained_start_claim_denies_relaunch():
    g = ClassicalGate.from_grants(
        {"spawn-1": {"state": "retained_start_claim", "version": 1}}
    )
    assert g.decide(action_id="spawn-1", request="relaunch", grant_version=1) == "deny"


def test_active_grant_allows_execute():
    g = ClassicalGate.from_grants({"edit-1": {"state": "active_grant", "version": 2}})
    assert g.decide(action_id="edit-1", request="execute", grant_version=2) == "allow"


def test_stale_version_denies_execute():
    g = ClassicalGate.from_grants({"edit-1": {"state": "active_grant", "version": 2}})
    assert g.decide(action_id="edit-1", request="execute", grant_version=1) == "deny"


def test_always_deny_mutation_fails_useful_operation_control():
    """Acceptance probe: replacing decide with unconditional deny must break allow case."""
    g = ClassicalGate.from_grants({"edit-1": {"state": "active_grant", "version": 2}})
    # Production decide must allow; a monkeypatched always-deny must not satisfy this test.
    assert g.decide(action_id="edit-1", request="execute", grant_version=2) == "allow"


def test_rejected_execute_denies():
    g = ClassicalGate.from_grants({"mail-1": {"state": "rejected", "version": 1}})
    assert g.decide(action_id="mail-1", request="execute", grant_version=1) == "deny"


def test_dump_load_are_in_process_copies_only():
    """dump/load copy fixture state; they are not restart-durability evidence."""
    g = ClassicalGate.from_grants({"edit-1": {"state": "active_grant", "version": 2}})
    g2 = ClassicalGate.load(g.dump())
    assert g2.decide(action_id="edit-1", request="execute", grant_version=2) == "allow"
    assert g2.decide(action_id="edit-1", request="execute", grant_version=1) == "deny"
