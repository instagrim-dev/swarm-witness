from pathlib import Path
import sys

import yaml

from swarm_witness.schema import validate_claim_card

root = Path(__file__).resolve().parents[1]
ok = True
for path in sorted((root / "claims").glob("*.yaml")):
    try:
        validate_claim_card(yaml.safe_load(path.read_text()))
        print(f"OK {path.name}")
    except Exception as exc:
        ok = False
        print(f"FAIL {path.name}: {exc}")
sys.exit(0 if ok else 1)
