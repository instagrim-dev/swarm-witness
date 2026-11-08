#!/usr/bin/env python3
"""Annotate Finding JSON with conclusion_class and evaluation_method."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.conclusion_classes import (  # noqa: E402
    assert_label_matches_conclusion,
    conclusion_class_for_label,
)

# Explicit overrides where label alone is ambiguous or method-scoped.
OVERRIDES: dict[str, str] = {
    "r4-f-evidence-sufficiency": "supported",
    "r5-f-swarm-audit": "supported",
}

# Conclusion says what was established; evaluation_method says how.
EVALUATION_METHODS: dict[str, str] = {
    "r1-f-primary": "pinned_reexecution",
    "r2-f-primary": "published_harness_confirmation",
    "r3-f-comparison": "matched_decision_model",
    "r3-ledger-claim-v1-comparison": "native_matched_baseline",
    "r4-f-evidence-sufficiency": "synthetic_protocol_conformance",
    "r5-f-swarm-audit": "synthetic_protocol_conformance",
    "incident-audit-v1-f-comparison": "public_postmortem_qualification",
}


def main() -> int:
    findings_dir = ROOT / "evidence"
    updated = 0
    for path in sorted(findings_dir.glob("*/findings/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        label = data["label"]
        cls = OVERRIDES.get(data["id"]) or conclusion_class_for_label(label)
        if cls is None:
            print(f"SKIP {path}: unknown label {label!r}", file=sys.stderr)
            return 1
        assert_label_matches_conclusion(label, cls)
        changed = False
        if data.get("conclusion_class") != cls:
            data["conclusion_class"] = cls
            changed = True
        method = EVALUATION_METHODS.get(data["id"])
        if method and data.get("evaluation_method") != method:
            data["evaluation_method"] = method
            changed = True
        if changed:
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            updated += 1
            print(
                f"updated {path} -> class={cls} method={data.get('evaluation_method')}"
            )
        else:
            print(f"ok {path} ({cls}, {data.get('evaluation_method')})")
    print(f"done; wrote {updated} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
