from __future__ import annotations

import argparse
import sys
from pathlib import Path

from swarm_witness.evidence_index import check_consistency, generate_and_write_index

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed Claim/Run/Finding evidence-consistency guard."
    )
    parser.add_argument(
        "--write-index",
        action="store_true",
        help="Regenerate evidence/index.yaml from findings, then check consistency.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (defaults to package parent).",
    )
    args = parser.parse_args([] if argv is None else argv)
    root = args.root if args.root is not None else ROOT

    if args.write_index:
        generate_and_write_index(root)

    errors = check_consistency(root)
    if errors:
        for err in errors:
            print(f"FAIL {err}", file=sys.stderr)
        return 1

    if args.write_index:
        print("OK evidence consistency; wrote evidence/index.yaml from findings")
    else:
        print("OK evidence consistency (index matches findings-derived labels)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
