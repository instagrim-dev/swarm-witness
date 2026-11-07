from __future__ import annotations

from pathlib import Path
import sys

import yaml

from swarm_witness.schema import validate_result_record

ROOT = Path(__file__).resolve().parents[1]
CLAIM_IDS = ("r1", "r2", "r3")


def check_results(root: Path) -> list[str]:
    errors: list[str] = []
    for claim_id in CLAIM_IDS:
        result_path = root / "evidence" / claim_id / "result.yaml"
        summary_path = root / "evidence" / claim_id / "summary.json"
        if not result_path.is_file():
            errors.append(f"missing {result_path}")
            continue
        if not summary_path.is_file():
            errors.append(f"missing {summary_path}")
        try:
            rec = validate_result_record(yaml.safe_load(result_path.read_text(encoding="utf-8")))
        except Exception as exc:
            errors.append(f"invalid {result_path}: {exc}")
            continue
        if rec.claim_id != claim_id:
            errors.append(f"{result_path}: claim_id {rec.claim_id!r} != {claim_id!r}")
        evidence = root / rec.evidence_path
        if not evidence.is_file():
            errors.append(f"missing evidence file {evidence} (from {result_path})")
    return errors


def check_index_matches_results(root: Path) -> list[str]:
    errors: list[str] = []
    index_path = root / "evidence" / "index.yaml"
    if not index_path.is_file():
        return [f"missing {index_path}"]
    index = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    entries = index.get("results")
    if not isinstance(entries, list) or not entries:
        return [f"{index_path}: expected non-empty results list"]
    indexed: dict[str, str] = {}
    for row in entries:
        if not isinstance(row, dict):
            errors.append(f"{index_path}: each result entry must be a mapping")
            continue
        claim_id = row.get("claim_id")
        label = row.get("label")
        if not claim_id or not label:
            errors.append(f"{index_path}: entry missing claim_id or label: {row!r}")
            continue
        indexed[str(claim_id)] = str(label)
    for claim_id in CLAIM_IDS:
        result_path = root / "evidence" / claim_id / "result.yaml"
        if not result_path.is_file():
            continue
        rec = validate_result_record(yaml.safe_load(result_path.read_text(encoding="utf-8")))
        if claim_id not in indexed:
            errors.append(f"{index_path}: no entry for {claim_id}")
            continue
        if indexed[claim_id] != rec.label:
            errors.append(
                f"{index_path}: {claim_id} label {indexed[claim_id]!r} "
                f"!= result.yaml {rec.label!r} (no fabrication)"
            )
    if set(indexed) != set(CLAIM_IDS):
        extra = set(indexed) - set(CLAIM_IDS)
        missing = set(CLAIM_IDS) - set(indexed)
        if extra:
            errors.append(f"{index_path}: unexpected claim_ids: {sorted(extra)}")
        if missing:
            errors.append(f"{index_path}: missing claim_ids: {sorted(missing)}")
    return errors


def main() -> int:
    errors = check_results(ROOT) + check_index_matches_results(ROOT)
    if errors:
        for err in errors:
            print(f"FAIL {err}", file=sys.stderr)
        return 1
    print("OK evidence index and result records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
