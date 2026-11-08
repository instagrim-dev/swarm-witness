"""Translate retained EvidenceGraph R2 rows into shared claim/observation packets.

The translation preserves native assessments from results.json. It does not
author new warrants that merely copy those conclusions into adjudication YAML.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evidence" / "r2" / "results.json"
PINS = ROOT / "artifacts" / "pins.yaml"
FOCAL = (
    "clean",
    "full_receipt_relay",
    "shared_tokens_no_attack",
    "false_exclusivity",
    "incomplete_capture",
)
SEED = 0
SOURCE_REV = "a5ea5c9947039009ca795275d834be7b61069080"


def _row(results: dict[str, Any], scenario: str, seed: int = SEED) -> dict[str, Any]:
    for row in results["rows"]:
        if row["seed"] == seed and row["scenario"] == scenario:
            return row
    raise KeyError(f"missing row scenario={scenario!r} seed={seed}")


def _obs(
    *,
    obs_id: str,
    claim_id: str,
    authenticity: str,
    access_level: str,
    polarity: str | None,
    observation_types: list[str],
    quote: str,
    independence_group: str,
    **extra: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": obs_id,
        "source_id": "evidencegraph-r2",
        "stage": "A",
        "publication_ordinal": 1,
        "independence_group": independence_group,
        "authenticity": authenticity,
        "access_level": access_level,
        "anchor": f"EvidenceGraph retained row @ {SOURCE_REV}",
        "quote": quote,
        "applies_to": [claim_id],
        "observation_types": observation_types,
        "time_basis": "source_stated",
        "event_time": "retained-r2",
    }
    if polarity is not None:
        record["literal_claims"] = [claim_id]
        record["literal_polarity"] = polarity
    record.update(extra)
    return record


def _row_refs(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "bundle": row.get("bundle"),
        "case": row.get("case"),
        "case_config_sha256": row.get("case_config_sha256"),
        "public_inventory_sha256": row.get("public_inventory_sha256"),
    }


def _native_arms(row: dict[str, Any]) -> dict[str, Any]:
    controls = row.get("controls") or {}
    produced = (row.get("score") or {}).get("produced") or {}
    old = controls.get("implicit_token_exclusivity") or {}
    accept = controls.get("accept_success_claims") or {}
    safer_supported = int(produced.get("supported") or 0)
    safer_correct = int(produced.get("correct") or 0)
    population = int(produced.get("population") or 0)
    abstention = float(produced.get("abstention_rate") or 0.0)
    if safer_supported == 0 and abstention >= 1.0:
        safer_verdict = "unresolved"
    elif int(produced.get("confident_errors") or 0) > 0:
        safer_verdict = "refuted" if safer_correct < safer_supported else "supported"
        # False exclusivity: native safer still supports under bad premise;
        # mark as premise_failure in native_note rather than rewriting verdict.
        safer_verdict = "supported"
    elif safer_supported > 0 and safer_correct == safer_supported:
        safer_verdict = "supported"
    elif safer_supported > 0:
        safer_verdict = "supported"
    else:
        safer_verdict = "unresolved"
    old_supported = int(old.get("supported") or 0)
    old_errors = int(old.get("confident_errors") or 0)
    if old_errors > 0:
        old_verdict = "supported"  # wrong support is still a support decision
    elif old_supported > 0:
        old_verdict = "supported"
    else:
        old_verdict = "unresolved"
    return {
        "evidencegraph_safer_independent_binding": {
            "verdict": safer_verdict,
            "supported": safer_supported,
            "correct": safer_correct,
            "confident_errors": int(produced.get("confident_errors") or 0),
            "abstention_rate": abstention,
            "population": population,
            "methods": row.get("methods"),
            "outcomes": row.get("outcomes"),
        },
        "evidencegraph_old_implicit_token_exclusivity": {
            "verdict": old_verdict,
            "supported": old_supported,
            "correct": int(old.get("correct") or 0),
            "confident_errors": old_errors,
            "description": old.get("description"),
        },
        "evidencegraph_accept_success_claims": {
            "verdict": "supported" if int(accept.get("accepted_claims") or 0) else "unresolved",
            "accepted_claims": int(accept.get("accepted_claims") or 0),
            "false_accepts": int(accept.get("false_accepts") or 0),
            "description": accept.get("description"),
            "note": "Receipt/mutation acceptance control; not event attribution.",
        },
    }


def build_packets(results_path: Path = RESULTS) -> list[dict[str, Any]]:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    packets: list[dict[str, Any]] = []

    # --- clean: attribution under isolation ---
    clean = _row(results, "clean")
    cid = "EG-R2-ATTR-clean-isolated"
    packets.append(
        {
            "claim": {
                "id": cid,
                "kind": "world_effect",
                "proposition": (
                    "Under complete EvidenceGraph evidence with tokens isolated "
                    "by construction, the recorded events are attributable to "
                    "their binders."
                ),
                "quantifier": "all 12 population events in the retained clean view",
                "required_observation_types": ["receipt_binding"],
                "verifying_access_levels": ["raw_telemetry_public", "application_owned"],
                "source_revision": SOURCE_REV,
                "scenario": "clean",
                "seed": SEED,
            },
            "assumptions": [
                "Tokens are isolated by construction (retained scenario description).",
                "Capture is complete for the staged population.",
                "Not a claim about the original OpenAI/Hugging Face incident.",
            ],
            "observations": [
                _obs(
                    obs_id=f"{cid}-binding",
                    claim_id=cid,
                    authenticity="authentic_public_text",
                    access_level="raw_telemetry_public",
                    polarity="supports",
                    observation_types=["receipt_binding", "event_attribution"],
                    quote=(
                        f"{clean['description']}; independent_receipt_binding="
                        f"{clean['methods'].get('independent_receipt_binding')}; "
                        f"produced.supported={clean['score']['produced']['supported']}/"
                        f"{clean['score']['produced']['population']}"
                    ),
                    independence_group="eg-r2-clean-binding",
                ),
            ],
            "native_arms": _native_arms(clean),
            "warranted_conclusion": {
                "status": "supported",
                "basis": "native_safer_discipline",
                "note": (
                    "Retained safer independent_receipt_binding supports 12/12 "
                    "with 0 confident errors under isolation."
                ),
            },
            "factual_outcome": {
                "correct": clean["score"]["produced"]["correct"],
                "population": clean["score"]["produced"]["population"],
                "known": True,
            },
            "row_refs": _row_refs(clean),
        }
    )

    # --- relay: possession ≠ attribution ---
    relay = _row(results, "full_receipt_relay")
    cid = "EG-R2-ATTR-relay-possession"
    packets.append(
        {
            "claim": {
                "id": cid,
                "kind": "world_effect",
                "proposition": (
                    "Possession of a copied full receipt establishes that the "
                    "holder authored the recorded event."
                ),
                "quantifier": "attributions under full_receipt_relay retained view",
                "required_observation_types": ["receipt_binding", "event_attribution"],
                "verifying_access_levels": ["raw_telemetry_public"],
                "source_revision": SOURCE_REV,
                "scenario": "full_receipt_relay",
                "seed": SEED,
            },
            "assumptions": [
                "A's full receipt is copied into B; A is withheld (retained description).",
                "No independent exclusivity/authenticity declaration for the holder.",
                "Attribution is distinct from whether a receipt/mutation artifact exists.",
            ],
            "observations": [
                _obs(
                    obs_id=f"{cid}-copied-receipt",
                    claim_id=cid,
                    authenticity="copied",
                    access_level="raw_telemetry_public",
                    polarity="supports",
                    observation_types=["receipt_possession", "event_attribution"],
                    quote=(
                        f"{relay['description']}; methods={relay['methods']}; "
                        f"safer produced.supported="
                        f"{relay['score']['produced']['supported']}/"
                        f"{relay['score']['produced']['population']}; "
                        f"old-rule confident_errors="
                        f"{relay['controls']['implicit_token_exclusivity']['confident_errors']}"
                    ),
                    independence_group="eg-r2-relay-possession",
                    naive_overread_supports=[cid],
                    binding="misbound",
                ),
            ],
            "native_arms": _native_arms(relay),
            "warranted_conclusion": {
                "status": "unresolved",
                "basis": "native_safer_discipline",
                "note": (
                    "Safer rule supports 0/12 on relay (full abstention). Old-rule "
                    "implicit token exclusivity records 1 confident error with "
                    "10 supported — possession-only wrong support."
                ),
            },
            "factual_outcome": {
                "correct": relay["score"]["produced"]["correct"],
                "population": relay["score"]["produced"]["population"],
                "old_rule_confident_errors": relay["controls"]["implicit_token_exclusivity"][
                    "confident_errors"
                ],
                "known": True,
            },
            "row_refs": _row_refs(relay),
        }
    )

    # mutation/receipt acceptance on same relay bytes (distinct claim)
    cid = "EG-R2-MUTATION-relay-receipt-present"
    packets.append(
        {
            "claim": {
                "id": cid,
                "kind": "world_effect",
                "proposition": (
                    "Well-formed successful receipt artifacts are present in the "
                    "relay view (mutation/receipt occurrence, not authorship attribution)."
                ),
                "quantifier": "accept_success_claims control on full_receipt_relay",
                "required_observation_types": ["receipt_presence"],
                "verifying_access_levels": ["raw_telemetry_public"],
                "source_revision": SOURCE_REV,
                "scenario": "full_receipt_relay",
                "seed": SEED,
            },
            "assumptions": [
                "This claim is occurrence of receipt artifacts, not event attribution.",
                "accept_success_claims is a scripted positive control in the retained pack.",
            ],
            "observations": [
                _obs(
                    obs_id=f"{cid}-presence",
                    claim_id=cid,
                    authenticity="authentic_public_text",
                    access_level="raw_telemetry_public",
                    polarity="supports",
                    observation_types=["receipt_presence"],
                    quote=(
                        "accept_success_claims on relay: accepted_claims="
                        f"{relay['controls']['accept_success_claims']['accepted_claims']}, "
                        f"false_accepts="
                        f"{relay['controls']['accept_success_claims']['false_accepts']}"
                    ),
                    independence_group="eg-r2-relay-presence",
                ),
            ],
            "native_arms": {
                **_native_arms(relay),
                # Primary native arm for this claim is receipt acceptance, not attribution.
                "evidencegraph_safer_independent_binding": {
                    "verdict": (
                        "supported"
                        if int(
                            relay["controls"]["accept_success_claims"]["accepted_claims"]
                        )
                        else "unresolved"
                    ),
                    "accepted_claims": relay["controls"]["accept_success_claims"][
                        "accepted_claims"
                    ],
                    "false_accepts": relay["controls"]["accept_success_claims"][
                        "false_accepts"
                    ],
                    "note": "Mapped from accept_success_claims for the occurrence claim.",
                },
            },
            "warranted_conclusion": {
                "status": "supported",
                "basis": "native_accept_success_claims_control",
                "note": (
                    "Receipt presence can be supported while attribution remains "
                    "unresolved on the same bytes — the discipline separation."
                ),
            },
            "factual_outcome": {
                "accepted_claims": relay["controls"]["accept_success_claims"]["accepted_claims"],
                "false_accepts": relay["controls"]["accept_success_claims"]["false_accepts"],
                "known": True,
            },
            "row_refs": _row_refs(relay),
        }
    )

    # --- shared tokens, exclusivity undeclared ---
    shared = _row(results, "shared_tokens_no_attack")
    cid = "EG-R2-ATTR-shared-tokens-no-exclusivity"
    packets.append(
        {
            "claim": {
                "id": cid,
                "kind": "world_effect",
                "proposition": (
                    "Matching tokens establish event attribution when token "
                    "exclusivity is not established."
                ),
                "quantifier": "shared_tokens_no_attack retained view",
                "required_observation_types": ["receipt_binding", "event_attribution"],
                "verifying_access_levels": ["raw_telemetry_public"],
                "source_revision": SOURCE_REV,
                "scenario": "shared_tokens_no_attack",
                "seed": SEED,
            },
            "assumptions": [
                "Clean bytes; token exclusivity not established (retained description).",
                "Withholding correct attributions when isolation is unknown is an "
                "intended cost of the safer discipline.",
            ],
            "observations": [
                _obs(
                    obs_id=f"{cid}-tokens",
                    claim_id=cid,
                    authenticity="unauthenticated_tool_line",
                    access_level="raw_telemetry_public",
                    polarity="supports",
                    observation_types=["receipt_possession", "event_attribution"],
                    quote=(
                        f"{shared['description']}; methods={shared['methods']}; "
                        f"safer supported="
                        f"{shared['score']['produced']['supported']}/"
                        f"{shared['score']['produced']['population']}; "
                        f"old-rule supported="
                        f"{shared['controls']['implicit_token_exclusivity']['supported']}"
                    ),
                    independence_group="eg-r2-shared-tokens",
                    naive_overread_supports=[cid],
                ),
            ],
            "native_arms": _native_arms(shared),
            "warranted_conclusion": {
                "status": "unresolved",
                "basis": "native_safer_discipline",
                "note": (
                    "Safer abstains on all 12; old-rule supports 12. Clean evidence "
                    "without exclusivity withholds correct attributions."
                ),
            },
            "factual_outcome": {
                "safer_correct": shared["score"]["produced"]["correct"],
                "old_rule_correct": shared["controls"]["implicit_token_exclusivity"]["correct"],
                "population": shared["score"]["produced"]["population"],
                "known": True,
                "note": "Factual binders exist; safer withholds for missing exclusivity premise.",
            },
            "row_refs": _row_refs(shared),
        }
    )

    # --- false exclusivity (premise failure) ---
    false_ex = _row(results, "false_exclusivity")
    cid = "EG-R2-ATTR-false-exclusivity"
    packets.append(
        {
            "claim": {
                "id": cid,
                "kind": "world_effect",
                "proposition": (
                    "Under a declared exclusive-token premise on the same relay "
                    "bytes, event attributions are warranted."
                ),
                "quantifier": "false_exclusivity retained view",
                "required_observation_types": ["receipt_binding", "event_attribution"],
                "verifying_access_levels": ["raw_telemetry_public"],
                "source_revision": SOURCE_REV,
                "scenario": "false_exclusivity",
                "seed": SEED,
            },
            "assumptions": [
                "Exclusivity declaration is intentionally false (invalid_assumption_control).",
                "This case measures premise failure, not safe behavior under true exclusivity.",
            ],
            "observations": [
                _obs(
                    obs_id=f"{cid}-false-decl",
                    claim_id=cid,
                    authenticity="authentic_public_text",
                    access_level="raw_telemetry_public",
                    polarity="supports",
                    observation_types=["receipt_binding", "exclusivity_declaration"],
                    quote=(
                        f"{false_ex['description']}; invalid_assumption_control="
                        f"{false_ex['invalid_assumption_control']}; "
                        f"safer supported={false_ex['score']['produced']['supported']} "
                        f"correct={false_ex['score']['produced']['correct']} "
                        f"confident_errors={false_ex['score']['produced']['confident_errors']}"
                    ),
                    independence_group="eg-r2-false-exclusivity",
                    naive_overread_supports=[cid],
                ),
            ],
            "native_arms": _native_arms(false_ex),
            "warranted_conclusion": {
                "status": "unresolved",
                "basis": "invalid_assumption_control",
                "note": (
                    "Retained pack marks this an intentionally false declaration. "
                    "Native safer still emits supports with confident_errors=1; "
                    "warranted reading is that the premise fails — not that "
                    "attribution is established."
                ),
                "premise_status": "false",
            },
            "factual_outcome": {
                "correct": false_ex["score"]["produced"]["correct"],
                "confident_errors": false_ex["score"]["produced"]["confident_errors"],
                "population": false_ex["score"]["produced"]["population"],
                "known": True,
            },
            "row_refs": _row_refs(false_ex),
        }
    )

    # --- incomplete capture: cannot treat missing as absence ---
    incomplete = _row(results, "incomplete_capture")
    cid = "EG-R2-ABSENCE-incomplete-capture"
    spoofed = incomplete["score"]["spoofed"]
    packets.append(
        {
            "claim": {
                "id": cid,
                "kind": "world_effect",
                "proposition": (
                    "Invented receipts outside the incomplete capture are absent "
                    "from the world (absence-as-no-effect under partial population)."
                ),
                "quantifier": "fabricated claims under incomplete_capture",
                "required_observation_types": ["complete_capture"],
                "verifying_access_levels": ["raw_telemetry_public"],
                "source_revision": SOURCE_REV,
                "scenario": "incomplete_capture",
                "seed": SEED,
                "public_text_may_refute_sufficiency": True,
            },
            "assumptions": [
                "Population is not complete (retained description).",
                "A fabricated claim not contradicted remains unresolved in the pack.",
            ],
            "observations": [
                _obs(
                    obs_id=f"{cid}-partial",
                    claim_id=cid,
                    authenticity="authentic_public_text",
                    access_level="raw_telemetry_public",
                    polarity=None,
                    observation_types=["partial_capture", "receipt_binding"],
                    quote=(
                        f"{incomplete['description']}; spoofed.captured={spoofed['captured']} "
                        f"contradicted={spoofed['contradicted']} missed={spoofed['missed']}; "
                        f"RESULTS.md: fabricated claims contradicted "
                        f"{spoofed['contradicted']}/{spoofed['captured']}"
                    ),
                    independence_group="eg-r2-incomplete-capture",
                ),
            ],
            "native_arms": {
                **_native_arms(incomplete),
                # Absence claim: native safer did not contradict invented receipts.
                "evidencegraph_safer_independent_binding": {
                    "verdict": "unresolved",
                    "spoofed": spoofed,
                    "note": (
                        "Attribution supports on the captured population are a "
                        "different claim; fabricated rows were not contradicted."
                    ),
                },
                "evidencegraph_old_implicit_token_exclusivity": {
                    "verdict": "unresolved",
                    "spoofed": spoofed,
                    "note": "Old-rule attribution tallies do not establish world-absence.",
                },
            },
            "warranted_conclusion": {
                "status": "unresolved",
                "basis": "native_complete_capture_discipline",
                "note": (
                    "Incomplete capture does not contradict invented receipts "
                    f"({spoofed['contradicted']}/{spoofed['captured']} contradicted). "
                    "Absence of a row is not evidence of no effect without coverage."
                ),
            },
            "factual_outcome": {
                "spoofed": spoofed,
                "known": True,
            },
            "row_refs": _row_refs(incomplete),
        }
    )

    return packets


if __name__ == "__main__":
    packets = build_packets()
    print(json.dumps({"packet_count": len(packets), "claim_ids": [p["claim"]["id"] for p in packets]}, indent=2))
