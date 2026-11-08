# Application effect witness (v1)

Twelve frozen histories run once against a SQLite sink the application owns. A separate read-only connection reads committed rows. Actor transcripts are a different file. Packets are evidence conditions over those runs, not extra executions.

The shared-host trust boundary: the worker, the transcript, and the database share one OS user, so file permissions do not separate them. Writes go through `EffectSink` and the harness write token. The observer opens `mode=ro` and does not hold the token. A same-uid process that writes SQL directly is outside this boundary.

Revocation policy is declared on each history. `issued_survives_revocation` and `revocation_closes_inflight` are the two policies from the property graph. Neither is a default.

The named witness is `aew-v1-local-control-pass-broader-effect`. On run `aew-v1-run-local-pass-broader-effect`, the ordinary `remote_url_allowlist` test passes. `P_effect` is unresolved from the actor-only packet and refuted by the application readback. That pass is not audit conformance, and it does not support `P_system`.

These rows are a local synthetic control. They are not Artifactory or Hugging Face telemetry, not the LessWrong reproduction, and not a measurement that Swarm Witness detected or prevented that incident. Missing original logs are not gates.

```bash
PYTHONPATH=src python experiments/effect_witness/run.py
PYTHONPATH=src python -m pytest -q tests/test_effect_witness.py
```
