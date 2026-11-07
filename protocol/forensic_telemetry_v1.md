# Forensic telemetry ingestion v1

**Version:** `forensic-telemetry-v1`
**Status:** Post-submission research for issue #31, under epic #26. This does not say Swarm Witness detected or prevented the 2026 Artifactory / Hugging Face incident, and it does not certify that incident.
**Provenance contract:** `evidence-provenance-v1` (`protocol/evidence_provenance_v1.md`, `src/swarm_witness/provenance.py`), including the lineage rules on `cursor/operational-lineage-coverage-e62a`. This document does not redefine that contract.
**Executable form:** `src/swarm_witness/telemetry.py`

Verdicts are `qualify_graph`. `normalize_lineage` binds each observation. A content digest identifies pinned bytes. `digest_certifies_assertion` stays false.

## One public reproduction record

The LessWrong reproduction post and its appendix are one release. The telemetry graph uses the pins already in `experiments/provenance/incident_lineage.yaml`:

| Source | Role |
| --- | --- |
| `src-lw-reproduction-post` | Pinned release sentence. |
| `src-lw-reproduction-appendix` | Second report of that same release. It `depends_on` the post, so the corroboration key does not increase. |

`tel_reproduction_record` can be `reproduced` from those bytes. `independent_observation_count` stays 1. `effect_status` stays `unobserved`. The OpenAI transcript dump and the Hugging Face platform logs are on the claim, recorded unavailable, and are not gates.

The Inspect `.eval` files released with that post are not copied here.

## Public postmortem text

The METR `echo REAL; sleep` excerpt and the Hugging Face correlation sentence are ingested as `narrative_report` with polarity `reports`. They are not original telemetry and they are not offered as a committed effect.

## What stays unavailable

These origins have no rows and no effect times. `blocks_upgrade` is false. The contract rejects `blocks_upgrade: true` on a source this audit does not hold.

- OpenAI transcript dump, and the independent execution log for the published command example
- Artifactory message-board dump
- Hugging Face dataset-processor, API, and pod logs (`src-hf-platform-logs`)
- Redacted Hugging Face indicators
- Private launchpad / external sandbox logs
- OpenAI HTML page (retrieval HTTP 403)
- Other Artifactory side channels
- Issue #41's application-owned witness export (not in this branch)

`tel_original_logs` stays `unresolved` because no committed-effect event is held. The coverage assumption is `partial`, so a missing sink row is not treated as evidence of no effect. `primary_upgrade_blocker` stays empty.

A `blocks_upgrade` slot on a source this audit holds still prevents `supported` until a verified supporting event uses that source. That rule is probed on a copy. It is not how the unit keeps the original-incident claim unresolved.

## Adapters

`agent_tool_record` accepts `requested_command`, `displayed_tool_call`, and `tool_response`.
`service_effect_log` accepts `api_event`, `service_log`, and `committed_effect`.
`public_excerpt` accepts a pinned public sentence and emits `narrative_report` only.

JSONL and CSV are the row formats. Any other attachment type raises `UnsupportedAttachment` and emits no rows. Privileged fields are refused. Redacted credentials are salted SHA-256 strings. The salt does not add the record id.

The readback packet under `experiments/telemetry/packet/` is `synthetic_control`. It is not an incident log and not the LessWrong release. Reconciliation may corroborate two synthetic service rows. `confirmed_effect` stays false: a tool call is not a committed effect, and a credential match is not an actor.

## Qualification

`forensic_telemetry_v1` checks the replay: the reproduction record qualifies, the original-effect claim does not, unavailable originals are not gates, and no flag certifies the incident. This issue does not implement #30, #32, or #42.

## Regeneration

```bash
PYTHONPATH=src python experiments/telemetry/qualify.py
PYTHONPATH=src python -m pytest -q tests/test_forensic_telemetry.py tests/test_provenance_contract.py
python scripts/validate_claims.py
python scripts/check_evidence.py
```
