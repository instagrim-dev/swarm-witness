import pytest
from swarm_witness.schema import validate_claim_card, validate_result_record


def test_claim_card_requires_precise_fields():
    with pytest.raises(ValueError, match="property"):
        validate_claim_card({"id": "r1", "assumptions": [], "baseline": "wal"})


def test_valid_claim_card_round_trips():
    card = validate_claim_card(
        {
            "id": "r1",
            "property": "acknowledged rejection survives restart",
            "scope": "SoundGate 0.1.3 @ pinned rev under intact acknowledged records",
            "quantifier": "for each constructed history in the published sweep",
            "success_criterion": "prohibited_effects == 0 under recovery barrier",
            "assumptions": ["intact acknowledged records", "stable protected log path"],
            "baseline": "durable auth log + recover-before-admit",
            "discriminating_checks": ["durable_vs_ephemeral"],
        }
    )
    assert card.id == "r1"


def test_result_rejects_unknown_label():
    with pytest.raises(ValueError, match="label"):
        validate_result_record(
            {
                "claim_id": "r1",
                "label": "kinda_worked",
                "metrics": {},
                "evidence_path": "evidence/r1/summary.json",
                "notes": "no",
            }
        )


def test_valid_result_record():
    rec = validate_result_record(
        {
            "claim_id": "r1",
            "label": "reproduced",
            "metrics": {"prohibited_effects_original": 143},
            "evidence_path": "evidence/r1/summary.json",
            "notes": "matched published table within stated scope",
        }
    )
    assert rec.label == "reproduced"
