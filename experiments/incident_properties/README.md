# Incident property graph (v1)

Post-submission check for issue #29. A passing URL allowlist is not the conjunction of file-read, execution, credential, and downstream-effect properties. The fixtures are labels and an in-model effect ledger. They do not fetch URLs, read worker files, or run untrusted configuration.

```bash
PYTHONPATH=src python experiments/incident_properties/run.py
PYTHONPATH=src python -m pytest -q tests/test_incident_property_graph.py
```

The research note is `docs/incident_property_decomposition.md`. The run does not claim that Swarm Witness detected or prevented the July 2026 incident.
