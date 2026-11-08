"""Export per-mutation native produced relations from retained EvidenceGraph cases.

Writes scoring-only private truth separately from public assessor observables.
Requires the EvidenceGraph tree under third_party/r2/evidencegraph (pinned a5ea5c9).

    third_party/r2/evidencegraph/.venv/bin/python \\
      experiments/external_calibration/eg_native_export.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EG_SRC = ROOT / "third_party" / "r2" / "evidencegraph" / "src"
REPRO = ROOT / "third_party" / "r2" / "reproduction"
OUT = ROOT / "evidence" / "external_calibration_v1" / "eg_native_relations_seed0.json"
SOURCE_REV = "a5ea5c9947039009ca795275d834be7b61069080"

# Focal scenarios for expanded native conformance (seed 0).
SCENARIO_VIEWS = {
    "clean": "clean",
    "fabricated": "fabricated",
    "full_receipt_relay": "full-copy",
    "false_exclusivity": "full-copy",
    "shared_tokens_no_attack": "clean",
    "missing_tokens": "no-tokens",
    "missing_clock_bound": "clean",
    "dependent_witnesses": "fabricated",
    "capture_window_edge": "window-edge",
    "incomplete_capture": "incomplete",
}

SEED = 0


def _public_entity(entity: dict[str, Any]) -> dict[str, Any]:
    attrs = dict(entity.get("attrs") or {})
    # Keep receipt / commitment fields; drop nothing private beyond host bindings.
    return {
        "entity_id": entity["entity_id"],
        "kind": entity["kind"],
        "subkind": entity.get("subkind"),
        "natural_key": entity.get("natural_key"),
        "witness_id": entity.get("witness_id"),
        "time_lower": entity.get("time_lower"),
        "time_upper": entity.get("time_upper"),
        "winning_clock_id": entity.get("winning_clock_id"),
        "attrs": {
            k: attrs.get(k)
            for k in (
                "id",
                "name",
                "namespace",
                "path",
                "operation",
                "sha256",
                "previous_sha256",
                "receipt_token_sha256",
                "ts",
                "event_uuid",
                "function",
                "error",
                "receipt",
                "arguments",
            )
            if k in attrs
        },
    }


def _relation_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": row.get("kind"),
        "outcome": row.get("outcome"),
        "method": row.get("method"),
        "rationale": row.get("rationale"),
        "subject_id": row.get("subject_id"),
        "object_id": row.get("object_id"),
        "candidates": list(row.get("candidates") or []),
        "witness_ids": list(row.get("witness_ids") or []),
    }


def export_scenario(seed: int, scenario: str, view: str) -> dict[str, Any]:
    sys.path.insert(0, str(EG_SRC))
    from evidencegraph.case import read_manifest
    from evidencegraph.manifest import read_manifest as read_manifest_alt
    from evidencegraph.reconcile.engine import reconcile_registry
    from evidencegraph.schema import CaseConfig
    from evidencegraph.store import Store
    from evidencegraph.validate.truth_store import host_key

    # Prefer case.read_manifest used by stress harness.
    try:
        from evidencegraph.case import read_manifest as _rm

        read_manifest_fn = _rm
    except Exception:
        read_manifest_fn = read_manifest_alt

    case = REPRO / "cases" / f"{seed}-{scenario}"
    truth = REPRO / "views" / str(seed) / view / "private"
    manifest = read_manifest_fn(case)
    case_cfg = json.loads((case / "case.json").read_text(encoding="utf-8"))

    with Store(case, manifest) as store:
        mutations = [_public_entity(e) for e in store.entities("registry_mutation")]
        events = [_public_entity(e) for e in store.entities("tool_event")]
        safer = [
            _relation_row(r)
            for r in store.query(
                "SELECT kind, outcome, method, rationale, subject_id, object_id, "
                "candidates, witness_ids FROM relations WHERE kind='produced'"
            )
        ]
        executed = [
            _relation_row(r)
            for r in store.query(
                "SELECT kind, outcome, method, rationale, subject_id, object_id, "
                "candidates, witness_ids FROM relations WHERE kind='executed'"
            )
        ]
        # Legacy rule: exclusive receipt tokens forced true (stress score_controls).
        config = CaseConfig.model_validate(case_cfg)
        legacy_cfg = config.model_copy(
            update={
                "trust_domains": tuple(
                    d.model_copy(update={"exclusive_receipt_tokens": True})
                    for d in config.trust_domains
                )
            }
        )
        legacy = [
            _relation_row(r.model_dump() if hasattr(r, "model_dump") else dict(r))
            for _, r in reconcile_registry(store, legacy_cfg, manifest, None)
            if getattr(r, "kind", None) == "produced"
            or (isinstance(r, dict) and r.get("kind") == "produced")
        ]

    # Normalize legacy relation objects (Edge models).
    legacy_norm: list[dict[str, Any]] = []
    for item in legacy:
        if hasattr(item, "model_dump"):
            legacy_norm.append(_relation_row(item.model_dump()))
        elif isinstance(item, dict) and "outcome" in item:
            legacy_norm.append(_relation_row(item))
        else:
            # reconcile_registry yields (store_id, Edge)
            pass

    # Re-run legacy extraction more carefully.
    legacy_norm = []
    with Store(case, manifest) as store:
        config = CaseConfig.model_validate(case_cfg)
        legacy_cfg = config.model_copy(
            update={
                "trust_domains": tuple(
                    d.model_copy(update={"exclusive_receipt_tokens": True})
                    for d in config.trust_domains
                )
            }
        )
        for _, edge in reconcile_registry(store, legacy_cfg, manifest, None):
            if edge.kind != "produced":
                continue
            legacy_norm.append(
                {
                    "kind": edge.kind,
                    "outcome": edge.outcome,
                    "method": edge.method,
                    "rationale": edge.rationale,
                    "subject_id": edge.subject_id,
                    "object_id": edge.object_id,
                    "candidates": list(edge.candidates or []),
                    "witness_ids": list(edge.witness_ids or []),
                }
            )

    private = host_key(truth)
    populations = _load_populations(case)
    return {
        "seed": seed,
        "scenario": scenario,
        "view": view,
        "case": str(case.relative_to(ROOT)),
        "source_revision": SOURCE_REV,
        "declared_assumptions": {
            "clock_bounds": case_cfg.get("clock_bounds") or [],
            "trust_domains": case_cfg.get("trust_domains") or [],
            "title": case_cfg.get("title"),
        },
        "public_entities": {
            "registry_mutations": mutations,
            "tool_events": events,
            "populations": populations,
        },
        "native_relations": {
            "safer_produced": safer,
            "legacy_produced": legacy_norm,
            "executed": executed,
        },
        # Scoring-only: never copy into classifier observation packets.
        "private_truth": {
            "produced": private.get("produced") or {},
            "spoofed": private.get("spoofed") or [],
        },
    }


def _load_populations(case: Path) -> list[dict[str, Any]]:
    """Public capture declarations from population.json under evidence/."""
    rows: list[dict[str, Any]] = []
    for path in sorted((case / "evidence").glob("*/population.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "witness_id": path.parent.name,
                "complete": bool(doc.get("complete")),
                "started_at": doc.get("started_at"),
                "stopped_at": doc.get("stopped_at"),
                "namespace": doc.get("namespace"),
                "count": doc.get("count"),
                "definition": doc.get("definition"),
                "event_ids": list(doc.get("event_ids") or []),
            }
        )
    return rows


def main() -> int:
    if not EG_SRC.is_dir():
        raise SystemExit(f"missing EvidenceGraph source at {EG_SRC}")
    scenarios = []
    for scenario, view in SCENARIO_VIEWS.items():
        print(f"export {SEED}-{scenario}...", flush=True)
        scenarios.append(export_scenario(SEED, scenario, view))
    payload = {
        "schema_version": 1,
        "role": "expanded_native_conformance",
        "transfer_claim": False,
        "seed": SEED,
        "source_revision": SOURCE_REV,
        "scenarios": scenarios,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(scenarios)} scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
