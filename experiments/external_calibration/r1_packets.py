"""Translate retained SoundGate R1 analysis into shared claim/observation packets.

Keeps restriction-survival and useful-operation as separate claims so a
no-prohibited-effects-only standard cannot collapse them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "evidence" / "r1" / "local-run-analysis.json"
SOURCE_REV = "656840348dcf9660f8db7add9f3ca9f794a55926"


def _obs(
    *,
    obs_id: str,
    claim_id: str,
    authenticity: str,
    polarity: str | None,
    observation_types: list[str],
    quote: str,
    **extra: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": obs_id,
        "source_id": "soundgate-r1",
        "stage": "A",
        "publication_ordinal": 1,
        "independence_group": f"sg-r1-{claim_id}",
        "authenticity": authenticity,
        "access_level": "raw_telemetry_public",
        "anchor": f"SoundGate local-run-analysis @ {SOURCE_REV}",
        "quote": quote,
        "applies_to": [claim_id],
        "observation_types": observation_types,
        "time_basis": "source_stated",
        "event_time": "retained-r1",
    }
    if polarity is not None:
        record["literal_claims"] = [claim_id]
        record["literal_polarity"] = polarity
    record.update(extra)
    return record


def build_packets(analysis_path: Path = ANALYSIS) -> list[dict[str, Any]]:
    data = json.loads(analysis_path.read_text(encoding="utf-8"))
    policies = data["policies"]
    packets: list[dict[str, Any]] = []

    def policy_packet(
        *,
        claim_id: str,
        policy: str,
        kind_label: str,
        proposition: str,
        required_types: list[str],
        warranted: str,
        warrant_note: str,
        polarity_obs: str | None,
        obs_types: list[str],
        naive_overread: bool = False,
    ) -> dict[str, Any]:
        tallies = policies[policy]
        quote = (
            f"policy={policy}; cases={tallies['cases']}; "
            f"supported={tallies['supported']}; "
            f"prohibited_effect={tallies['prohibited_effect']}; "
            f"refused_before_ack={tallies['refused_before_ack']}; "
            f"fresh_work={tallies['fresh_work']}; "
            f"prefix_controls={tallies['prefix_controls']}"
        )
        extra: dict[str, Any] = {}
        if naive_overread and polarity_obs == "supports":
            extra["naive_overread_supports"] = [claim_id]
        obs = _obs(
            obs_id=f"{claim_id}-tally",
            claim_id=claim_id,
            authenticity="authentic_public_text",
            polarity=polarity_obs,
            observation_types=obs_types,
            quote=quote,
            **extra,
        )
        # Native arms: each SoundGate policy as a gate profile on this claim family.
        native = {}
        for name, tallies_n in policies.items():
            if kind_label == "restriction":
                # Restriction holds iff no prohibited effects in retained tallies.
                if tallies_n["prohibited_effect"] == 0 and tallies_n["cases"] > 0:
                    verdict = "supported"
                elif tallies_n["prohibited_effect"] > 0:
                    verdict = "refuted"
                else:
                    verdict = "unresolved"
            else:
                # Availability: fresh_work on all (or nearly all) histories.
                if tallies_n["fresh_work"] == tallies_n["cases"]:
                    verdict = "supported"
                elif tallies_n["fresh_work"] == 0:
                    verdict = "refuted"
                elif tallies_n["fresh_work"] < tallies_n["cases"] / 2:
                    verdict = "refuted"
                else:
                    verdict = "unresolved"
            native[f"soundgate_policy_{name}"] = {
                "verdict": verdict,
                "tallies": tallies_n,
            }
        return {
            "claim": {
                "id": claim_id,
                "kind": "world_effect",
                "proposition": proposition,
                "quantifier": f"all {tallies['cases']} retained histories under policy={policy}",
                "required_observation_types": required_types,
                "verifying_access_levels": ["raw_telemetry_public"],
                "source_revision": SOURCE_REV,
                "scenario": policy,
                "seed": None,
                "family": kind_label,
            },
            "assumptions": [
                "Tallies counted from evidence/r1/local-run-analysis.json.",
                "Restriction survival and useful fresh work are distinct claims.",
                "Not a claim about the Artifactory / Hugging Face incident.",
            ],
            "observations": [obs],
            "native_arms": native,
            # Align primary native scoring key used by the runner.
            "native_primary": f"soundgate_policy_{policy}",
            "warranted_conclusion": {
                "status": warranted,
                "basis": "native_soundgate_policy_tallies",
                "note": warrant_note,
            },
            "factual_outcome": {"tallies": tallies, "known": True},
            "row_refs": {
                "analysis": "evidence/r1/local-run-analysis.json",
                "policy": policy,
            },
        }

    packets.append(
        policy_packet(
            claim_id="SG-R1-RESTRICT-original",
            policy="original",
            kind_label="restriction",
            proposition=(
                "Under the original SoundGate policy, the acknowledged restriction "
                "remains effective after the recovery sequence (no prohibited effects)."
            ),
            required_types=["restriction_effect", "recovery_outcome"],
            warranted="refuted",
            warrant_note="Original policy: 143/153 prohibited_effect in retained tallies.",
            polarity_obs="refutes",
            obs_types=["restriction_effect", "recovery_outcome", "prohibited_effect"],
        )
    )
    packets.append(
        policy_packet(
            claim_id="SG-R1-RESTRICT-strict",
            policy="strict",
            kind_label="restriction",
            proposition=(
                "Under the strict-refusal SoundGate policy, the acknowledged "
                "restriction remains effective after recovery (no prohibited effects)."
            ),
            required_types=["restriction_effect", "recovery_outcome"],
            warranted="supported",
            warrant_note="Strict policy: 0 prohibited_effect; 147/153 refused_before_ack.",
            polarity_obs="supports",
            obs_types=["restriction_effect", "recovery_outcome"],
            naive_overread=True,
        )
    )
    packets.append(
        policy_packet(
            claim_id="SG-R1-AVAIL-strict",
            policy="strict",
            kind_label="availability",
            proposition=(
                "Under the strict-refusal SoundGate policy, unrelated permitted "
                "work remains executable after recovery."
            ),
            required_types=["fresh_work", "availability"],
            warranted="refuted",
            warrant_note="Strict policy: fresh_work only 6/153 — mass startup refusal.",
            polarity_obs="refutes",
            obs_types=["fresh_work", "availability", "startup_refusal"],
        )
    )
    packets.append(
        policy_packet(
            claim_id="SG-R1-RESTRICT-barrier",
            policy="barrier",
            kind_label="restriction",
            proposition=(
                "Under the recovery-barrier SoundGate policy, the acknowledged "
                "restriction remains effective after recovery (no prohibited effects)."
            ),
            required_types=["restriction_effect", "recovery_outcome"],
            warranted="supported",
            warrant_note="Barrier policy: 0 prohibited_effect across 153 histories.",
            polarity_obs="supports",
            obs_types=["restriction_effect", "recovery_outcome"],
        )
    )
    packets.append(
        policy_packet(
            claim_id="SG-R1-AVAIL-barrier",
            policy="barrier",
            kind_label="availability",
            proposition=(
                "Under the recovery-barrier SoundGate policy, unrelated permitted "
                "work remains executable after recovery."
            ),
            required_types=["fresh_work", "availability"],
            warranted="supported",
            warrant_note="Barrier policy: fresh_work 153/153 with restrictions preserved.",
            polarity_obs="supports",
            obs_types=["fresh_work", "availability"],
        )
    )
    return packets


if __name__ == "__main__":
    packets = build_packets()
    print(json.dumps({"n": len(packets), "ids": [p["claim"]["id"] for p in packets]}, indent=2))
