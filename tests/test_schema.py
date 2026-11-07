import pytest
from swarm_witness.schema import validate_claim, validate_run, validate_finding


def test_claim_rejects_list_property():
    with pytest.raises(ValueError, match="property"):
        validate_claim(
            {
                "id": "r1",
                "source_ref": "paper://restart",
                "source_version": "6568403",
                "original_proposition": "ack rejection survives restart",
                "operational_interpretation": "barrier prohibited_effects==0",
                "scope": "SoundGate pinned",
                "quantifier": "each history",
                "success_criterion": "barrier prohibited_effects==0",
                "assumptions": ["intact records"],
                "property": ["not", "a", "string"],
            }
        )


def test_claim_rejects_bool_quantifier_and_whitespace():
    with pytest.raises(ValueError):
        validate_claim(
            {
                "id": "r1",
                "source_ref": "x",
                "source_version": "1",
                "original_proposition": "p",
                "operational_interpretation": "i",
                "scope": " ",
                "quantifier": True,
                "success_criterion": "c",
                "assumptions": ["a"],
                "property": "p",
            }
        )


def test_claim_rejects_string_assumptions():
    with pytest.raises(ValueError, match="assumptions"):
        validate_claim(
            {
                "id": "r1",
                "source_ref": "x",
                "source_version": "1",
                "original_proposition": "p",
                "operational_interpretation": "i",
                "scope": "s",
                "quantifier": "all",
                "success_criterion": "c",
                "assumptions": "durable",
                "property": "p",
            }
        )


def test_run_requires_status_and_pin():
    with pytest.raises(ValueError, match="execution_status"):
        validate_run({"id": "run1", "claim_id": "r1", "protocol_id": "r1", "case_id": "h0"})


def test_finding_rejects_unknown_label():
    with pytest.raises(ValueError, match="label"):
        validate_finding(
            {
                "id": "f1",
                "claim_id": "r1",
                "run_ids": ["run1"],
                "proposition": "x",
                "scope": "s",
                "label": "kinda_worked",
                "basis": "computed",
                "supporting_observation_refs": ["run1.obs.a"],
            }
        )


def test_valid_claim_run_finding_round_trip():
    claim = validate_claim(
        {
            "id": "r1",
            "source_ref": "apart://restart-is-not-permission",
            "source_version": "6568403",
            "original_proposition": "acknowledged rejection survives restart",
            "operational_interpretation": "barrier prohibited_effects==0 on pinned sweep",
            "property": "acknowledged rejection survives restart",
            "scope": "SoundGate 0.1.3 @ pinned rev",
            "quantifier": "for each constructed history",
            "success_criterion": "prohibited_effects == 0 under recovery barrier",
            "assumptions": ["intact acknowledged records"],
        }
    )
    run = validate_run(
        {
            "id": "r1-run-1",
            "claim_id": "r1",
            "protocol_id": "soundgate-recovery-barrier",
            "case_id": "policy-barrier",
            "source_pin": "6568403",
            "execution_status": "completed",
            "observations": {"prohibited_effects": 0, "histories": 153},
        }
    )
    finding = validate_finding(
        {
            "id": "r1-f-reproduced",
            "claim_id": "r1",
            "run_ids": ["r1-run-1"],
            "proposition": "barrier yields prohibited_effects==0",
            "scope": claim.scope,
            "label": "reproduced",
            "basis": "computed",
            "supporting_observation_refs": ["r1-run-1.observations.prohibited_effects"],
        }
    )
    assert claim.id == "r1" and run.execution_status == "completed" and finding.label == "reproduced"
