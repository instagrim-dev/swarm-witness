#!/usr/bin/env python3
"""Annotate Finding JSON with conclusion_class consistent with Finding.label."""

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
    "r4-f-evidence-sufficiency": "supported",  # method claim reproduced
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
        if data.get("conclusion_class") != cls:
            data["conclusion_class"] = cls
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            updated += 1
            print(f"updated {path} -> {cls}")
        else:
            print(f"ok {path} ({cls})")
    print(f"done; wrote {updated} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())