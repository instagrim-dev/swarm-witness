"""Independent multi-agent simulator with causal interleavings (issue #10).

Post-submission research harness. Preserves R5 sequential results; does not
relabel R5 v1 as concurrent. Explicitly excludes live BMO mesh equivalence,
production concurrency guarantees, and unbounded swarm safety.
"""

from swarm_witness.multi_agent_sim.protocol import (
    CLAIM_ID,
    PROTOCOL_ID,
    SOURCE_PIN,
    evaluate_protocol_success,
    replay_traces_match,
    run_protocol_cases,
    run_scenario,
)
from swarm_witness.multi_agent_sim.scheduler import Schedule, ScheduleStep, run_schedule

__all__ = [
    "CLAIM_ID",
    "PROTOCOL_ID",
    "SOURCE_PIN",
    "Schedule",
    "ScheduleStep",
    "evaluate_protocol_success",
    "replay_traces_match",
    "run_protocol_cases",
    "run_scenario",
    "run_schedule",
]
