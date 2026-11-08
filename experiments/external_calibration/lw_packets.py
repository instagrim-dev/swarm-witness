"""Translate retained LessWrong controlled-comparison claims into packets.

Scoring warrants come from warrants_v1.yaml (author adjudication key).
There is no independently specified LessWrong executable method in-repo; do
not present a copied warrant as a native external comparator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CMP = ROOT / "experiments" / "incident_audit" / "comparison"
CLAIMS = CMP / "claims_v1.yaml"
PACKETS = CMP / "packets_v1.yaml"
WARRANTS = CMP / "warrants_v1.yaml"
PROTOCOL = CMP / "protocol_v1.yaml"
SOURCE_REV = "399ef5d0b280f528ea66a30836f6111cf886ec85"

CLAIM_META = {
    "K-release": {
        "scenario": "reproduction_release",
        "family": "reproduction_scope",
        "assumptions": [
            "One public LessWrong record (post + appendix) is held.",
            "Release sentence refers to that reproduction, not the original incident.",
        ],
    },
    "K-certify": {
        "scenario": "incident_certification",
        "family": "reproduction_scope",
        "assumptions": [
            "Original OpenAI transcripts and Hugging Face platform logs are unavailable.",
            "Unavailable originals are listed and do not carry blocks_upgrade.",
            "Public narrative is not raw telemetry of the original compromise.",
        ],
    },
    "K-census": {
        "scenario": "reproduction_census",
        "family": "reproduction_scope",
        "assumptions": [
            "Held step-1 GLM 5.2 signature_rate extract is a reproduction count.",
            "Census does not upgrade to a claim about the original incident.",
        ],
    },
    "K-gate": {
        "scenario": "held_upgrade_slot",
        "family": "reproduction_scope",
        "assumptions": [
            "HELD-SLOT carries blocks_upgrade=true and is not the verifying observation.",
            "Release sentence alone cannot satisfy the upgrade slot.",
        ],
    },
}


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _remap_ids(values: list[Any] | None, native_id: str, packet_id: str) -> list[str]:
    out: list[str] = []
    for value in values or []:
        text = str(value)
        if text == native_id:
            out.append(packet_id)
        elif text.startswith("LW-"):
            out.append(text)
    return out


def _obs_for_claim(
    obs: dict[str, Any], *, native_id: str, packet_id: str
) -> dict[str, Any] | None:
    applies = obs.get("applies_to") or []
    if native_id not in applies:
        return None
    record = dict(obs)
    record["applies_to"] = [packet_id]
    if "literal_claims" in record:
        literals = _remap_ids(record.get("literal_claims"), native_id, packet_id)
        if literals:
            record["literal_claims"] = literals
        else:
            record.pop("literal_claims", None)
            record.pop("literal_polarity", None)
    if "naive_overread_supports" in record:
        overreads = _remap_ids(
            record.get("naive_overread_supports"), native_id, packet_id
        )
        if overreads:
            record["naive_overread_supports"] = overreads
        else:
            record.pop("naive_overread_supports", None)
    return record


def build_packets(
    claims_path: Path = CLAIMS,
    packets_path: Path = PACKETS,
    warrants_path: Path = WARRANTS,
    protocol_path: Path = PROTOCOL,
) -> list[dict[str, Any]]:
    claims_doc = _load(claims_path)
    packets_doc = _load(packets_path)
    warrants_doc = _load(warrants_path)
    protocol = _load(protocol_path)
    observations = packets_doc["observations"]
    warrants = warrants_doc["claims"]

    out: list[dict[str, Any]] = []
    for claim in claims_doc["claims"]:
        native_id = claim["id"]
        packet_id = f"LW-{native_id}"
        meta = CLAIM_META[native_id]
        warrant = warrants[native_id]
        claim_obs = [
            filtered
            for obs in observations
            if (
                filtered := _obs_for_claim(
                    obs, native_id=native_id, packet_id=packet_id
                )
            )
            is not None
        ]
        warranted = str(warrant["epistemic"])
        proposition_holds = warrant.get("proposition_holds")
        warrant_note = warrant.get("reason")
        # Ablation only: narrative overread. Not an external LessWrong method.
        overread_verdict = (
            "supported"
            if native_id in {"K-release", "K-certify", "K-census", "K-gate"}
            else "unresolved"
        )
        out.append(
            {
                "claim": {
                    "id": packet_id,
                    "kind": claim.get("kind") or "world_effect",
                    "proposition": " ".join(str(claim["proposition"]).split()),
                    "quantifier": "the held LessWrong reproduction record",
                    "required_observation_types": list(
                        claim.get("required_observation_types") or []
                    ),
                    "verifying_access_levels": list(
                        claim.get("verifying_access_levels") or []
                    ),
                    "source_revision": SOURCE_REV,
                    "scenario": meta["scenario"],
                    "family": meta["family"],
                    "certifies_original_incident": bool(
                        claim.get("certifies_original_incident")
                    ),
                },
                "assumptions": list(meta["assumptions"])
                + [
                    f"protocol.certifies_original_incident="
                    f"{protocol.get('certifies_original_incident')}",
                    f"protocol.one_public_record={protocol.get('one_public_record')}",
                    "No independently specified LessWrong executable method is "
                    "retained in-repo; warrants_v1 is the scoring key only.",
                ],
                "observations": claim_obs,
                "native_arms": {
                    "reconstructed_narrative_overread": {
                        "verdict": overread_verdict,
                        "note": (
                            "Author reconstruction / ablation: treats public "
                            "narrative as decisive for release, certification, "
                            "census, and upgrade-slot claims. Not a native "
                            "LessWrong method."
                        ),
                        "reconstruction": True,
                    },
                },
                # Documentation only — not scored as a method arm.
                "author_scope_reading": {
                    "status": warranted,
                    "source": "warrants_v1.yaml",
                    "reconstruction": True,
                    "note": (
                        "Author adjudication of the held record's scope. Same "
                        "artifact as warranted_conclusion; not an external "
                        "comparator."
                    ),
                    "reason": warrant_note,
                    "origin": warrant.get("origin"),
                },
                "warranted_conclusion": {
                    "status": warranted,
                    "basis": "author_warrants_v1_scoring_key",
                    "note": warrant_note,
                },
                "factual_outcome": {
                    "proposition_holds": proposition_holds,
                    "known": proposition_holds is not None,
                },
                "row_refs": {
                    "claims": str(claims_path.relative_to(ROOT)),
                    "packets": str(packets_path.relative_to(ROOT)),
                    "warrants": str(warrants_path.relative_to(ROOT)),
                    "native_claim_id": native_id,
                },
            }
        )

    # Object-level identity claim: disclosed differences refute identity.
    env_cid = "LW-K-env-scope"
    out.append(
        {
            "claim": {
                "id": env_cid,
                "kind": "world_effect",
                "proposition": (
                    "The held LessWrong reproduction environment is identical to "
                    "the original OpenAI–Hugging Face incident environment, "
                    "including peer composition."
                ),
                "quantifier": "the reproduction vs original environments",
                "required_observation_types": ["environment_difference"],
                "verifying_access_levels": ["public_bytes"],
                "source_revision": SOURCE_REV,
                "scenario": "environment_difference",
                "family": "reproduction_scope",
                "certifies_original_incident": False,
            },
            "assumptions": [
                "Released transcripts and scores are from the reproduction setup.",
                "The public post discloses a simpler environment and simulated peers.",
                "Under those disclosed differences, environment identity is false.",
            ],
            "observations": [
                {
                    "id": "LW-env-disclosed-difference",
                    "source_id": "lesswrong",
                    "stage": "A",
                    "publication_ordinal": 1,
                    "independence_group": "lesswrong-reproduction-2026-09",
                    "authenticity": "authentic_public_text",
                    "access_level": "public_bytes",
                    "anchor": "LessWrong reproduction: disclosed environment differences",
                    "quote": (
                        "The reproduction uses a simpler environment than the "
                        "original incident, including simulated peers."
                    ),
                    "applies_to": [env_cid],
                    "literal_claims": [env_cid],
                    "literal_polarity": "refutes",
                    "observation_types": [
                        "environment_difference",
                        "public_report_assertion",
                    ],
                    "time_basis": "source_stated",
                    "event_time": "lesswrong-reproduction-2026-09",
                },
                {
                    "id": "LW-env-naive-overread",
                    "source_id": "lesswrong",
                    "stage": "A",
                    "publication_ordinal": 1,
                    "independence_group": "lesswrong-reproduction-2026-09",
                    "authenticity": "authentic_public_text",
                    "access_level": "public_bytes",
                    "anchor": "LessWrong reproduction publicity",
                    "quote": "A public reproduction record was released.",
                    "applies_to": [env_cid],
                    "observation_types": ["public_report_assertion"],
                    "naive_overread_supports": [env_cid],
                },
            ],
            "native_arms": {
                "reconstructed_narrative_overread": {
                    "verdict": "supported",
                    "note": "Reconstruction: publicity overread as environment identity.",
                    "reconstruction": True,
                },
            },
            "author_scope_reading": {
                "status": "refuted",
                "source": "disclosed_environment_differences",
                "reconstruction": True,
                "note": (
                    "Author reading of the public post's disclosed differences; "
                    "not an external LessWrong method."
                ),
            },
            "warranted_conclusion": {
                "status": "refuted",
                "basis": "disclosed_environment_differences_refute_identity",
                "note": (
                    "Object-level identity is false given disclosed simpler "
                    "environment and simulated peers."
                ),
            },
            "factual_outcome": {
                "environments_identical": False,
                "known": True,
                "note": "Disclosed differences; identity claim does not hold.",
            },
            "row_refs": {
                "protocol": str(protocol_path.relative_to(ROOT)),
                "native_claim_id": "K-env-scope",
            },
        }
    )
    return out


if __name__ == "__main__":
    import json

    packets = build_packets()
    print(
        json.dumps(
            {
                "n": len(packets),
                "ids": [p["claim"]["id"] for p in packets],
                "warranted": {
                    p["claim"]["id"]: p["warranted_conclusion"]["status"] for p in packets
                },
                "scored_arms": {
                    p["claim"]["id"]: list(p["native_arms"]) for p in packets
                },
            },
            indent=2,
        )
    )
