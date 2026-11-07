"""Unit tests for three-way conclusion taxonomy."""

from __future__ import annotations

import pytest

from swarm_witness.conclusion_classes import (
    CONCLUSION_TO_FINDING_LABEL,
    classify_conclusion,
)


def test_missing_evidence_maps_to_unresolved():
    out = classify_conclusion(evidence_complete=False, property_holds=None)
    assert out["conclusion_class"] == "missing_evidence"
    assert out["finding_label"] == "unresolved"
    assert out["property_holds"] is None


def test_supported_maps_to_reproduced():
    out = classify_conclusion(evidence_complete=True, property_holds=True)
    assert out["conclusion_class"] == "supported"
    assert out["finding_label"] == "reproduced"


def test_failed_enforcement_maps_to_contradicted():
    out = classify_conclusion(evidence_complete=True, property_holds=False)
    assert out["conclusion_class"] == "failed_enforcement"
    assert out["finding_label"] == "contradicted_in_scope"


def test_complete_evidence_requires_bool_property():
    with pytest.raises(ValueError):
        classify_conclusion(evidence_complete=True, property_holds=None)


def test_label_map_covers_three_classes():
    assert set(CONCLUSION_TO_FINDING_LABEL) == {
        "missing_evidence",
        "failed_enforcement",
        "supported",
    }
