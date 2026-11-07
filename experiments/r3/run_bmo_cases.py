#!/usr/bin/env python3
"""Emit BMO-arm Run records via the narrow instrumented harness.

Pin: artifacts/pins.yaml r3.git_rev (recorded on every run).
Does not fill decisions from package pass/fail counts. Cases without an
isomorphic observation are emitted as execution_status=missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare import (  # noqa: E402
    emit_bmo_runs,
    load_bmo_git_rev,
    write_runs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-pass-count",
        type=int,
        default=None,
        help="Optional metadata only; never used as a decision source",
    )
    args = parser.parse_args(argv)
    pin = load_bmo_git_rev()
    runs = emit_bmo_runs(bmo_git_rev=pin, package_pass_count=args.package_pass_count)
    write_runs(runs)
    missing = sum(1 for r in runs if r["execution_status"] == "missing")
    print(
        json.dumps(
            {
                "arm": "bmo",
                "runs": len(runs),
                "missing": missing,
                "bmo_git_rev": pin,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
