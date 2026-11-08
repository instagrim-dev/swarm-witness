"""Application-owned effect witness (application-effect-witness-v1).

A local worker commits rows into a SQLite sink. A separate read-only
observer reads those rows back. This is a benign synthetic control. It is
not the Artifactory / Hugging Face incident, and it does not certify
detection or prevention.
"""

from swarm_witness.effect_witness.boundary import (
    TRUST_BOUNDARY,
    WITNESS_ID,
    WITNESS_VERSION,
)
from swarm_witness.effect_witness.replay import replay

__all__ = [
    "TRUST_BOUNDARY",
    "WITNESS_ID",
    "WITNESS_VERSION",
    "replay",
]
