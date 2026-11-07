"""Independent formal epistemics for the Swarm Witness taxonomy.

This package deliberately does **not** import ``swarm_witness.conclusion_classes``.
Finite-model checks treat the definitions here as the oracle; production
classifiers are compared only in optional consistency tests.
"""

from swarm_witness.formal.epistemic_model import (
    ArmObservation,
    EpistemicStatus,
    EvaluationObject,
    FormalDiagnosis,
    Observation,
    Property,
    TrustAssumptions,
    World,
    compatible_worlds,
    diagnose,
    epistemic_status,
    project_three_way,
    required_decision,
)
from swarm_witness.formal.finite_models import (
    FiniteModelReport,
    check_core_invariants,
    enumerate_permission_worlds,
    run_counterexample_suite,
)

__all__ = [
    "ArmObservation",
    "EpistemicStatus",
    "EvaluationObject",
    "FiniteModelReport",
    "FormalDiagnosis",
    "Observation",
    "Property",
    "TrustAssumptions",
    "World",
    "check_core_invariants",
    "compatible_worlds",
    "diagnose",
    "enumerate_permission_worlds",
    "epistemic_status",
    "project_three_way",
    "required_decision",
    "run_counterexample_suite",
]
