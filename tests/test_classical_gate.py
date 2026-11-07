from swarm_witness.classical_gate import ClassicalGate


def test_retained_start_claim_is_not_relaunch_permission():
    g = ClassicalGate(grants={"spawn-1": "retained_start_claim"})
    assert g.decide("spawn-1", "relaunch") == "deny"


def test_rejection_survives_restart_reload():
    g = ClassicalGate(grants={"mail-1": "rejected"})
    g2 = ClassicalGate.load(g.dump())
    assert g2.decide("mail-1", "execute") == "deny"


def test_active_grant_allows_execute():
    g = ClassicalGate(grants={"edit-1": "active_grant"})
    assert g.decide("edit-1", "execute") == "allow"


def test_unknown_or_stale_defaults_to_deny():
    g = ClassicalGate(grants={"edit-1": "active_grant"})
    assert g.decide("missing", "execute") == "deny"
    stale = ClassicalGate.load({"edit-1": "rejected"})
    assert stale.decide("edit-1", "execute") == "deny"
