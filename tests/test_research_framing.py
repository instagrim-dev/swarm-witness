"""Architecture-backed framing: claim map, roles, and result versions."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs" / "research" / "claim_evidence_map.yaml"
DECISION = ROOT / "docs" / "research" / "FRAMING_DECISION.md"
MANUSCRIPT = ROOT / "report" / "Swarm_Witness_Final_Submission.md"
README = ROOT / "README.md"
PREEXISTING = ROOT / "PREEXISTING.md"
SHA = re.compile(r"^[0-9a-f]{40}$")
MEASURED = {"measured_contract", "measured_application"}


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, heading
    return match.group(1)


def _load_map() -> dict:
    document = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_claim_map_covers_architecture_and_measured_contracts():
    document = _load_map()
    claims = {entry["claim_id"]: entry for entry in document["claims"]}
    for hypothesis in ("H1", "H2", "H3", "H4"):
        entry = claims[hypothesis]
        assert entry["statement"]
        assert entry["status"] in {
            "preexisting_source",
            "measured_contract",
            "measured_application",
            "inference",
            "proposed",
        }
        assert entry["scope"]
        assert entry["not_established"]
        assert entry["sources"]
        for source in entry["sources"]:
            assert SHA.fullmatch(source["ref"])
            assert source["path"]
    supervisor = claims["bmo_subordinate_supervisor"]
    delegation = claims["bmo_signed_delegation"]
    for entry in (supervisor, delegation):
        assert entry["status"] == "preexisting_source"
        assert entry["status"] not in MEASURED
        assert "not measured by S01–S09" in entry["not_established"]
        assert all(source["ref"] == "e0038cc48872b274c22deaed8e24236530e9821e" for source in entry["sources"])
    ledger = claims["ledger_t01_t06"]
    settlement = claims["settlement_s01_s09"]
    assert ledger["status"] == "measured_contract"
    assert settlement["status"] == "measured_contract"
    assert ledger["sources"][0]["ref"] == "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe"
    assert settlement["sources"][0]["ref"] == "c8297333b3bf31ded96ca0e8b39c531d3bcea97f"
    assert claims["bounded_contract_portability"]["status"] == "demonstrated"
    assert claims["external_empirical_transfer"]["status"] == "not_tested"
    assert document["research_flags"] == {
        "bounded_contract_portability": "demonstrated",
        "external_empirical_transfer": "not_tested",
    }
    decision = DECISION.read_text(encoding="utf-8")
    assert "bounded_contract_portability = demonstrated" in decision
    assert "Track 4 evaluates transfer of authority and evidence obligations" in decision
    preexisting = PREEXISTING.read_text(encoding="utf-8")
    for needle in (
        "e0038cc48872b274c22deaed8e24236530e9821e",
        "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe",
        "c8297333b3bf31ded96ca0e8b39c531d3bcea97f",
        "not measured by S01–S09",
    ):
        assert needle in preexisting
        assert needle in decision or needle in preexisting


def test_manuscript_distinguishes_instrument_qualifier_and_versions():
    text = MANUSCRIPT.read_text(encoding="utf-8")
    assert text.startswith("# Swarm Witness Evidence for Agent Authorization\n")
    introduction = _section(text, "1 Introduction")
    results = _section(text, "4 Results")
    for role in (
        "BMO",
        "classical",
        "research instrument",
        "qualifier",
        "EvidenceGraph adapter",
    ):
        assert role in introduction
    assert "historical" in results.lower()
    assert "Table 2" in results
    assert "current evaluator" in results
    assert "does not replace Table 2" in results
    assert "sixteen-case" in results
    assert "eleven" in results
    assert "effect-applied" in results
    assert "P_effect" in text
    assert "P_commitment" in text or "Commitment" in text
    assert "P_system" in text
    assert "refutes only the effect-applied proposition" in results
    readme = README.read_text(encoding="utf-8")
    assert "historical" in readme.lower()
    assert "sixteen-case" in readme or "16-case" in readme
    assert "superiority" not in text.lower()
    assert "assessment score" not in text.lower()
