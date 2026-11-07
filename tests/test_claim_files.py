from pathlib import Path

import yaml
from swarm_witness.schema import validate_claim_card

ROOT = Path(__file__).resolve().parents[1]


def test_all_claim_cards_validate():
    paths = sorted((ROOT / "claims").glob("*.yaml"))
    assert paths, "expected claim YAML files"
    for path in paths:
        data = yaml.safe_load(path.read_text())
        validate_claim_card(data)
