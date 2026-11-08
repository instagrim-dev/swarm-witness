# Coordination attribution contract v1

**Version:** `coordination-attribution-v1`
**Status:** Post-submission research for issue #30, under epic #26. This qualifies coordination and causal-contribution claims. It does not say Swarm Witness detected or prevented the 2026 Artifactory / Hugging Face incident.
**Executable form:** `src/swarm_witness/coordination.py`
**Provenance:** `protocol/evidence_provenance_v1.md` (`evidence-provenance-v1`). This contract does not redefine that graph.
**Incident fixture:** `experiments/coordination/incident_cases.yaml`

#31 and #32 are not implemented here. #10–#12 findings are unchanged.

Verdicts call `qualify_claim` and `classify_conclusion`. There is no second confidence score. A `blocks_upgrade` slot prevents an upgrade to `supported` only for evidence this audit holds. The original OpenAI transcript dump and the Hugging Face platform logs stay unavailable and are not gates. A verified log from another held source does not clear a held gate. The LessWrong reproduction post and its appendix are one public record. `supported_while_blocked` stays false.

## Records

Coordination records cite provenance ids. They do not carry their own clock, digest, or independence group.

| Record | Role |
| --- | --- |
| `agent_instance` | A speaker or delegate. `identifier_status: lineage` must match the cited event's `actor_ref`. `copied` and `forged` never count as that actor. |
| `task` | The work the edge is about. |
| `message` | A message or artifact. `relation_to_content` is `original`, `relay`, `repetition`, `reused_file`, `investigator_aggregate`, or `unknown`. |
| `delegation` | A claimed handoff: both agents, one task, one original message. |
| `adoption` | A claimed goal adoption. It is an inference when only a narrative supports it. |
| `effect` | A claimed committed effect. It cites provenance events; it does not create one. |
| `observed_time` | One record per cited event. `event_time`, `observed_time`, and `time_basis` are copied from that event. A missing or reconstructed time stays out of the chronology. |
| `source_citation` | The provenance `source_record` an edge is allowed to use. |
| `edge` | The claimed relation. Every edge keeps `provenance_event_ids`, `provenance_source_ids`, and `source_citation_ids`. |

An edge may cite a withheld, redacted, or unobserved source so that unavailable telemetry stays explicit. It may not cite an available source outside the cited events' lineage.

## Labels

| Label | When it is applied |
| --- | --- |
| `communication_observed` | The edge is `communication`, the message is `original`, and a verified `independent_service_log` binds the speaker. A `narrative_report` does not qualify. |
| `delegation_evidenced` | Both agents are lineage-bound by verified service logs, the message is original, the task is present, and every support log has `time_basis: source_stated`. |
| `goal_adoption_inferred` | The edge is `adoption` or `shared_vocabulary` and a verified narrative is the basis. This is not intent, goal contagion, or causal contribution. |
| `causal_contribution_unresolved` | A contribution is alleged and there is no `delegation_evidenced` path to a verified `committed_effect` that uses every held `blocks_upgrade` source on the cited provenance claim. |

Other relations stay non-causal: `temporal_correlation`, `shared_vocabulary`, `reused_file`, `relay`, `duplicate_report`, `possession`, and `investigator_inference`. Possession or repetition of board content is not authorship and is not causal contribution. A second publication in the same independence group is one observation.

`investigator_reported` populations are read from provenance `reported_not_held` and forced `held_by_audit: false`. They are not traced causal actors. `directly_processed` counts records in the case. The reported figure of about 1,200 agents is not a denominator of traced actors. A Hugging Face participation count that is not on the provenance lineage is not adopted.

## Incident propositions

Replaying the fixture leaves three world propositions unresolved:

| Case | Why the public excerpts do not verify it | Unavailable original, not a gate |
| --- | --- | --- |
| `coord_board_participation` | The METR and Redwood sentences are one group. The LessWrong post and its appendix are a second, single public record. No agent instance is held. | `src-board-dump` |
| `coord_delegated_workstream` | The OpenAI outline is investigator inference. No delegation is evidenced. | `src-transcript-dump` |
| `coord_collective_impact` | Narratives and a reported population do not reach a committed effect. The narrative window is not promoted. | `src-hf-platform-logs` |

None of the three has a primary upgrade blocker. Coordination does not change those provenance verdicts. `added_claim_qualification_value` is false on each incident case.

Synthetic controls in `experiments/coordination/controls.py` are labeled synthetic. They are not incident records. A fixture whose own held log is the blocking source can satisfy the internal rule once that source is used, and still does not certify a real-world event. A log from a different held source does not clear that gate. An unavailable original cannot be marked `blocks_upgrade`.

The scale stream uses 1,200 synthetic agents and 70,000 synthetic messages, attributes only explicit handoffs, and does not allocate an agent-pair matrix.

## Regeneration

```bash
PYTHONPATH=src python experiments/coordination/qualify.py
PYTHONPATH=src python -m pytest -q tests/test_coordination_attribution.py
python scripts/validate_claims.py
python scripts/check_evidence.py
```
