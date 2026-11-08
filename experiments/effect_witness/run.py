"""Replay the application effect witness from a cold process.

    PYTHONPATH=src python experiments/effect_witness/run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swarm_witness.effect_witness.replay import replay  # noqa: E402


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "evidence" / "effect_witness_v1"
    summary = replay(output)
    witness = summary["witness"]["witness_id"]
    print(f"wrote {output}")
    print(f"witness {witness}")
    print(f"executions {summary['execution_count']}")
    print(f"evidence conditions {summary['evidence_condition_count']}")


if __name__ == "__main__":
    main()
