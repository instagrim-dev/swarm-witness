"""The epistemics sprint reads the retained comparison as a trust signal."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _measure():
    path = ROOT / "experiments" / "epistemics_trust_v1" / "run.py"
    spec = importlib.util.spec_from_file_location("epistemics_trust_v1", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.measure(ROOT)


def test_intact_actor_log_still_needs_admission():
    result = _measure()
    assert result["track"] == "Track 2, Trust Infrastructure"
    intact = result["intact_actor_consumer"]
    retained = result["retained_verdict_consumer"]
    admission = result["admission_consumer"]
    assert intact["unsupported_supports"] == 26
    assert intact["false_proposition_supports"] == 4
    assert intact["correct_decisive"] == 22
    assert intact["correct_abstentions"] == 0
    assert retained["unsupported_supports"] == 11
    assert retained["false_proposition_supports"] == 0
    assert retained["correct_decisive"] == 24
    assert retained["decisive_opportunities"] == 24
    assert admission["unsupported_supports"] == 0
    assert admission["false_proposition_supports"] == 0
    assert admission["correct_decisive"] == 24
    assert admission["correct_abstentions"] == 24
    assert result["denominator"]["packets"] == 48

    opened = result["retained_unsupported_supports"]
    assert opened["count"] == 11
    assert opened["deciding_records"] == 0
    assert opened["packets_with_intact_misbound_actor"] == 11
    assert {item.removeprefix("aew-v1-h-") for item in opened["misbound_actor_only"]} == {
        "authority-revoked-inflight",
        "local-control-held",
        "receipt-without-entitlement",
        "wrong-allow-blocked",
    }
    assert {item.removeprefix("aew-v1-h-") for item in opened["withheld_effect_row"]} == {
        "authority-current",
        "binding-aligned",
        "binding-misbound",
        "duplicated-source",
        "entitled-allow-settles",
        "receipt-with-entitlement",
        "single-source",
    }
    abstained = result["withheld_packet_where_retained_label_abstains"]
    assert [item["history"] for item in abstained] == ["aew-v1-h-local-pass-broader-effect"]
    assert abstained[0]["proposition_holds"] is False
    assert abstained[0]["shape"] == "withheld_effect_row"
    assert abstained[0]["deciding_records"] == 0
    assert "that this 48-packet ladder is the SoundGate transfer test" in result["does_not_establish"]


def test_subject_class_and_absence_carry_the_warrant_here():
    result = _measure()
    ladder = result["admission_ladder"]
    assert ladder["reject_misbound_actor"]["unsupported_supports"] == 14
    assert ladder["reject_misbound_actor"]["false_proposition_supports"] == 3
    assert ladder["reject_misbound_actor"]["correct_decisive"] == 22
    assert ladder["reject_misbound_actor"]["correct_abstentions"] == 12
    assert ladder["held_effect_polarity"]["unsupported_supports"] == 2
    assert ladder["held_effect_polarity"]["false_proposition_supports"] == 2
    assert ladder["held_effect_polarity"]["correct_decisive"] == 14
    assert ladder["subject_class"]["unsupported_supports"] == 0
    assert ladder["subject_class"]["correct_decisive"] == 16
    assert ladder["subject_class"]["correct_abstentions"] == 24
    assert ladder["polarity_or_absence"]["unsupported_supports"] == 2
    assert ladder["polarity_or_absence"]["false_proposition_supports"] == 2
    assert ladder["polarity_or_absence"]["correct_decisive"] == 22
    assert ladder["subject_class_or_absence"]["unsupported_supports"] == 0
    assert ladder["subject_class_or_absence"]["false_proposition_supports"] == 0
    assert ladder["subject_class_or_absence"]["correct_decisive"] == 24
    assert ladder["subject_class_or_absence"]["correct_abstentions"] == 24
    assert ladder["projection"]["correct_decisive"] == 24
    assert result["ladder_mismatches_against_projection"]["subject_class_or_absence"] == 0
    assert result["projection_mismatches_against_invariant_checker"] == 0
    assert result["rule_disagreements"]["reject_misbound_actor_vs_any_deciding_record"] == 0
    assert result["intact_actor_consumer"]["unsupported_supports"] == ladder["intact_actor"]["unsupported_supports"]

    absence = {
        (item["history"].removeprefix("aew-v1-h-"), item["stage"])
        for item in ladder["subject_class"]["warrant_mismatches"]
    }
    assert absence == {
        ("authority-revoked-inflight", "discriminating_readback"),
        ("authority-revoked-inflight", "duplicate_irrelevant"),
        ("local-control-held", "discriminating_readback"),
        ("local-control-held", "duplicate_irrelevant"),
        ("receipt-without-entitlement", "discriminating_readback"),
        ("receipt-without-entitlement", "duplicate_irrelevant"),
        ("wrong-allow-blocked", "discriminating_readback"),
        ("wrong-allow-blocked", "duplicate_irrelevant"),
    }
    polarity = {
        (item["history"], item["stage"], item["predicted"], item["warrant"])
        for item in ladder["polarity_or_absence"]["warrant_mismatches"]
    }
    assert polarity == {
        ("aew-v1-h-local-pass-broader-effect", "discriminating_readback", "supported", "refuted"),
        ("aew-v1-h-local-pass-broader-effect", "duplicate_irrelevant", "supported", "refuted"),
    }


def test_sixteen_challenge_probes_separate_scope_binding_and_census():
    challenge = _measure()["challenge_probes"]
    assert challenge["denominator"]["probes"] == 16
    assert challenge["denominator"]["source_packet"] == "aew-v1-h-authority-current/discriminating_readback"
    assert challenge["denominator"]["relation_to_48"] == "separate"
    subject = challenge["subject_class_or_absence"]
    projection = challenge["projection"]
    assert subject["unsupported_supports"] == 9
    assert subject["false_proposition_supports"] == 0
    assert subject["correct_decisive"] == 2
    assert subject["decisive_opportunities"] == 2
    assert subject["correct_abstentions"] == 5
    assert projection["unsupported_supports"] == 0
    assert projection["correct_decisive"] == 2
    assert projection["correct_abstentions"] == 14
    assert challenge["projection_mismatches_against_invariant_checker"] == 0
    assert challenge["projection_mismatches_against_warrant"] == 0
    assert challenge["separating_cases"] == {
        "scope_run": ["sink-run-mismatch"],
        "binding": [
            "sink-actor-mismatch",
            "sink-object-mismatch",
            "sink-mapped-actor-mismatch",
        ],
        "unknown_subject_beside_authorized": ["mixed-unknown-authorization"],
        "disagreeing_census": ["coverage-conflict"],
        "scope_operation": ["coverage-operation-mismatch"],
        "scope_interval": ["coverage-interval-outside"],
        "withheld_census": ["coverage-withheld"],
    }
