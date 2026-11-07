#!/usr/bin/env python3
"""Emit classical-arm Run records for every shared R3 case."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Reuse compare helpers so both arms share one cases.yaml loader.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare import emit_classical_runs, load_bmo_git_rev, write_runs  # noqa: E402


def main() -> int:
    pin = load_bmo_git_rev()
    runs = emit_classical_runs(source_pin=pin)
    write_runs(runs)
    print(json.dumps({"arm": "classical", "runs": len(runs), "source_pin": pin}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
