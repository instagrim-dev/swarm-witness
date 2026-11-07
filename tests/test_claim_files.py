from pathlib import Path

import yaml
from swarm_witness.schema import validate_claim

ROOT = Path(__file__).resolve().parents[1]


def test_all_claims_validate():
    paths = sorted((ROOT / "claims").glob("*.yaml"))
    assert paths, "expected claim YAML files"
    for path in paths:
        data = yaml.safe_load(path.read_text())
        claim = validate_claim(data)
        assert claim.id == data["id"].strip()

