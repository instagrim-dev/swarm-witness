# Incident property graph (v2)

Post-submission check for issue #29. Local control, decision-time entitlement, commit-time authorization, commitment, and `P_system` are separate. A supported local control is not `P_system`. The LessWrong reproduction post is the evidence standard. Original transcripts and platform logs are unavailable and are not required for a proposition to be well-formed. The fixtures are labels and an in-model effect ledger. They do not fetch URLs, read worker files, or run untrusted configuration. Issues #40–#42 are not implemented here.

```bash
PYTHONPATH=src python experiments/incident_properties/run.py
PYTHONPATH=src python -m pytest -q tests/test_incident_property_graph.py
```

The research note is `docs/incident_property_decomposition.md`. The run does not claim that Swarm Witness detected or prevented the July 2026 incident.
