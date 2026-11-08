"""Translate retained LessWrong controlled-comparison claims into packets.

Preserves the public-record scope discipline: a reproduction result, its
scoring procedure, and a claim about the original incident are distinct.
Warranted conclusions come from warrants_v1.yaml (native assessment of the
held record), not from newly authored local warrants.
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
        native_note = warrant.get("reason")
        # Narrative overread: treat publicity as decisive even for certification
        # and unsatisfied upgrade slots. Marked reconstruction, not native LW.
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
                ],
                "observations": claim_obs,
                "native_arms": {
                    "lesswrong_scope_discipline": {
                        "verdict": warranted,
                        "note": native_note,
                        "origin": warrant.get("origin"),
                        "reconstruction": False,
                    },
                    "reconstructed_narrative_overread": {
                        "verdict": overread_verdict,
                        "note": (
                            "Reconstruction: accepts public narrative as decisive "
                            "for release, certification, census, and upgrade-slot "
                            "claims; not a native LessWrong method."
                        ),
                        "reconstruction": True,
                    },
                },
                "warranted_conclusion": {
                    "status": warranted,
                    "basis": "lesswrong_warrants_v1_native_scope",
                    "note": native_note,
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

    # Explicit environment-scope claim: released reproduction ≠ original env.
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
                "required_observation_types": ["environment_identity"],
                "verifying_access_levels": ["raw_telemetry_public"],
                "source_revision": SOURCE_REV,
                "scenario": "environment_difference",
                "family": "reproduction_scope",
                "certifies_original_incident": False,
            },
            "assumptions": [
                "Released transcripts and scores are from the reproduction setup.",
                "Post discloses differences from the original environment "
                "(including simulated peers).",
                "Identity of environments is not established by publicity alone.",
            ],
            "observations": [
                {
                    "id": "LW-env-scope-boundary",
                    "source_id": "lesswrong",
                    "stage": "A",
                    "publication_ordinal": 1,
                    "independence_group": "lesswrong-reproduction-2026-09",
                    "authenticity": "authentic_public_text",
                    "access_level": "public_bytes",
                    "anchor": "LessWrong reproduction scope / environment differences",
                    "quote": (
                        "Released evidence is a reproduction under disclosed "
                        "conditions (including simulated peers); it is not an "
                        "identity claim about the original incident environment."
                    ),
                    "applies_to": [env_cid],
                    "observation_types": ["scope_boundary", "public_report_assertion"],
                    "time_basis": "source_stated",
                    "event_time": "lesswrong-reproduction-2026-09",
                    "naive_overread_supports": [env_cid],
                },
                {
                    "id": "UNAVAIL-original-env",
                    "source_id": "openai-transcript-dump",
                    "stage": "A",
                    "publication_ordinal": 9,
                    "independence_group": "openai-supplied-transcript-dump",
                    "authenticity": "unavailable",
                    "access_level": "withheld",
                    "locally_held": False,
                    "blocks_upgrade": False,
                    "anchor": "original environment telemetry, not held",
                    "quote": "Original environment telemetry is not held by this audit.",
                    "applies_to": [env_cid],
                    "observation_types": ["unavailable_original", "environment_identity"],
                },
            ],
            "native_arms": {
                "lesswrong_scope_discipline": {
                    "verdict": "unresolved",
                    "note": (
                        "Scope discipline: evaluate reproduction evidence at its "
                        "stated scope; do not equate environments."
                    ),
                    "reconstruction": False,
                },
                "reconstructed_narrative_overread": {
                    "verdict": "supported",
                    "note": "Reconstruction: publicity overread as environment identity.",
                    "reconstruction": True,
                },
            },
            "warranted_conclusion": {
                "status": "unresolved",
                "basis": "reproduction_scope_excludes_environment_identity",
                "note": (
                    "Released reproduction evidence does not establish identity "
                    "with the original incident environment."
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
            },
            indent=2,
        )
    )
