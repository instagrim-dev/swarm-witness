"""Translate retained BMO L1 ledger comparison into shared packets.

Preserves the manuscript boundary: matched first-edit ledger properties are
not execution settlement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "evidence" / "r3_ledger_claim_v1" / "summary.json"
FINDING = (
    ROOT / "evidence" / "r3_ledger_claim_v1" / "findings" / "r3-ledger-claim-v1-comparison.json"
)
META = ROOT / "evidence" / "r3_ledger_claim_v1" / "runs" / "r3-ledger-meta.json"
SOURCE_REV = "4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe"


def _obs(
    *,
    obs_id: str,
    claim_id: str,
    polarity: str | None,
    observation_types: list[str],
    quote: str,
    **extra: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": obs_id,
        "source_id": "bmo-r3-l1",
        "stage": "A",
        "publication_ordinal": 1,
        "independence_group": f"bmo-l1-{claim_id}",
        "authenticity": "authentic_public_text",
        "access_level": "raw_telemetry_public",
        "anchor": f"r3-ledger-claim-v1 @ {SOURCE_REV}",
        "quote": quote,
        "applies_to": [claim_id],
        "observation_types": observation_types,
        "time_basis": "source_stated",
        "event_time": "retained-r3-l1",
    }
    if polarity is not None:
        record["literal_claims"] = [claim_id]
        record["literal_polarity"] = polarity
    record.update(extra)
    return record


def build_packets(
    summary_path: Path = SUMMARY,
    finding_path: Path = FINDING,
    meta_path: Path = META,
) -> list[dict[str, Any]]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    finding = json.loads(finding_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    pairs = summary.get("validity", {}).get("pairs") or []
    by_case: dict[str, list[dict[str, Any]]] = {}
    for pair in pairs:
        by_case.setdefault(pair["case_id"], []).append(pair)

    packets: list[dict[str, Any]] = []
    for case_id, case_pairs in sorted(by_case.items()):
        all_valid = all(p.get("valid") is True for p in case_pairs)
        ops = ",".join(f"{p['step']}:{p['op']}" for p in case_pairs)
        cid = f"BMO-L1-LEDGER-{case_id}"
        warranted = "supported" if all_valid else "unresolved"
        quote = (
            f"case={case_id}; steps={ops}; all_valid={all_valid}; "
            f"agreement={meta['observations']['agreement']['result']}; "
            f"scope={finding['scope']}"
        )
        packets.append(
            {
                "claim": {
                    "id": cid,
                    "kind": "world_effect",
                    "proposition": (
                        f"Case {case_id}: ClassicalLedgerGate and native BMO L1 "
                        "satisfy the declared first-edit ledger-claim trace "
                        "properties (dispositions and property-relevant state)."
                    ),
                    "quantifier": f"every retained step in {case_id}",
                    "required_observation_types": [
                        "ledger_disposition",
                        "property_projection",
                    ],
                    "verifying_access_levels": ["raw_telemetry_public"],
                    "source_revision": SOURCE_REV,
                    "scenario": case_id,
                    "family": "transaction_ledger",
                },
                "assumptions": [
                    "L1 first-edit claim/transfer under cold DB reopen and explicit rollback.",
                    "Not external execute/settle or process restart (finding scope).",
                ],
                "observations": [
                    _obs(
                        obs_id=f"{cid}-match",
                        claim_id=cid,
                        polarity="supports" if all_valid else None,
                        observation_types=[
                            "ledger_disposition",
                            "property_projection",
                            "matched_baseline",
                        ],
                        quote=quote,
                    )
                ],
                "native_arms": {
                    "bmo_l1_native": {
                        "verdict": "supported" if all_valid else "unresolved",
                        "present": all(p.get("bmo_present") for p in case_pairs),
                    },
                    "classical_ledger_gate": {
                        "verdict": "supported" if all_valid else "unresolved",
                        "present": all(p.get("classical_present") for p in case_pairs),
                    },
                    "r3_agreement": {
                        "verdict": (
                            "supported"
                            if meta["observations"]["agreement"]["result"] == "matched"
                            else "unresolved"
                        ),
                        "result": meta["observations"]["agreement"]["result"],
                    },
                },
                "warranted_conclusion": {
                    "status": warranted,
                    "basis": "native_r3_ledger_validity_pairs",
                    "note": finding["scope"],
                },
                "factual_outcome": {
                    "pairs": case_pairs,
                    "known": True,
                },
                "row_refs": {
                    "finding": "evidence/r3_ledger_claim_v1/findings/r3-ledger-claim-v1-comparison.json",
                    "case_id": case_id,
                },
            }
        )

    # Explicit non-settlement claim: matched L1 does not establish execution settlement.
    cid = "BMO-L1-NOT-EXECUTION-SETTLEMENT"
    packets.append(
        {
            "claim": {
                "id": cid,
                "kind": "world_effect",
                "proposition": (
                    "Matched Classical/BMO L1 first-edit ledger traces establish "
                    "external execution settlement of delegated effects."
                ),
                "quantifier": "the r3-ledger-claim-v1 declared scope",
                "required_observation_types": ["execution_settlement"],
                "verifying_access_levels": ["raw_telemetry_public"],
                "source_revision": SOURCE_REV,
                "scenario": "scope",
                "family": "transaction_ledger",
            },
            "assumptions": [
                "Finding scope explicitly excludes external execute/settle.",
                "Absence of settlement observations leaves the claim unresolved.",
            ],
            "observations": [
                _obs(
                    obs_id=f"{cid}-scope",
                    claim_id=cid,
                    polarity=None,
                    observation_types=["scope_boundary", "ledger_disposition"],
                    quote=(
                        f"finding.scope={finding['scope']}; "
                        "no execution_settlement observation retained"
                    ),
                )
            ],
            "native_arms": {
                "bmo_l1_native": {
                    "verdict": "unresolved",
                    "note": "L1 adapter does not claim execution settlement.",
                },
                "classical_ledger_gate": {
                    "verdict": "unresolved",
                    "note": "Classical ledger gate is not an execution settler here.",
                },
                "r3_agreement": {
                    "verdict": "unresolved",
                    "note": "Matched ledger traces ≠ settlement certification.",
                },
            },
            "warranted_conclusion": {
                "status": "unresolved",
                "basis": "declared_scope_excludes_settlement",
                "note": finding["scope"],
            },
            "factual_outcome": {"execution_settlement_observed": False, "known": True},
            "row_refs": {
                "finding": "evidence/r3_ledger_claim_v1/findings/r3-ledger-claim-v1-comparison.json"
            },
        }
    )
    return packets


if __name__ == "__main__":
    packets = build_packets()
    print(json.dumps({"n": len(packets), "ids": [p["claim"]["id"] for p in packets]}, indent=2))
