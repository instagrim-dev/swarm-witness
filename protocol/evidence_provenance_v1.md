# Evidence provenance contract v1

**Version:** `evidence-provenance-v1`
**Status:** Post-submission research for issue #28, under epic #26. This contract qualifies published incident claims. It does not say Swarm Witness detected or prevented the 2026 Artifactory / Hugging Face incident.
**Executable form:** `src/swarm_witness/provenance.py`
**Incident fixture:** `experiments/provenance/incident_lineage.yaml`

Later issues import this contract. #31 builds source records with these fields. #30 may cite event ids when it models coordination. #27 may consume the finding labels. #32 must not turn a missing timestamp into a chronology. Those issues are not implemented here. #10–#12 findings are unchanged.

Verdicts use `classify_conclusion` and `audit_diagnosis`. There is no second confidence score. `unknown` is a legal value of every enumerated field below.

## Graph

```text
source_record → extraction → observed_event → claim
```

| Edge | Meaning |
| --- | --- |
| `depends_on` | A record was derived from an upstream record. The derived record must use the upstream `independence_group`. |
| `duplicate_of` | A second handle for the same record. It is not an additional observation. |
| `extracted_by` | An analyst read one or more source records. |
| `yields` | That extraction produced an observed event. |
| `offered_to` | The event is offered to a claim. |

`validate_graph` rejects cycles, duplicate node ids, duplicate edges, dangling references, digest mismatches, and any input field that would certify real-world authenticity, detection, or prevention. Those flags are outputs, and they are always false.

## Fields

| Field | Node | Role |
| --- | --- | --- |
| `observation_origin` | source | Where the record came from. See the four situations below. |
| `independence_group` | source | Identity of the underlying observational corpus. This is not the analyst. |
| `analysis_origin` | extraction | `human`, `delegated_model`, `mixed`, or `unknown`. Delegated model analysis does not create a new source group. |
| `collection_boundary` | source | What population the record claims to cover. |
| `custody` | source | `intact` only means the pinned excerpt matches its digest. It is not upstream authenticity. |
| `redaction` | source | `none`, `partial`, `withheld_original`, or `unknown`. |
| `access_level` | source | `public_bytes`, `public_narrative`, `withheld`, `redacted`, `private_original`, `unobserved`, or `unknown`. |
| `actor_binding` | event | `bound`, `unverified_binding`, `conflicting`, `unknown`, or `not_applicable`. |
| `event_time` | event | When the event is alleged to have happened. Null stays null. |
| `observed_time` | event | When that event record was observed. A page retrieval time is not an event time. |
| `authenticity` | event | `asserted`, `disputed`, `forged`, `unknown`, or `not_checked`. An asserted value does not verify the event. |
| `verification_method` | event | The only verification input. `self_report` and `none` verify nothing. |

`content_digest` is SHA-256 over the UTF-8 bytes of `public_bytes`. `byte_offset` spans those pinned bytes. `retrieved_document_offset` is a locator into the retrieved document; this repository does not redistribute the full pages. Offsets are UTF-8 byte offsets.

## Four situations that are not equivalent

| Situation | `observation_origin` | How the fixture treats it |
| --- | --- | --- |
| Reused transcript dump | `reused_transcript_dump` | A duplicate handle, or a second publication of the same dump. Same `independence_group`. Not a new observation. |
| Released reproduction | `released_reproduction` | The public LessWrong reproduction post and the transcripts that post releases. A different record from the OpenAI dump and from Hugging Face platform logs. |
| Correlated analyses of one dataset | `correlated_analysis_of_single_dataset` | METR's page and another analysis that `depends_on` the same withheld dump. Analysts may differ. The group does not. |
| Independent provider telemetry | `independent_provider_telemetry` | Hugging Face platform logs are their own group. A public sentence about those logs is not the logs. |
| Unavailable private original | `unavailable_private_original` | Withheld transcript dump, withheld Artifactory dump, or private launchpad logs. Coverage status is withheld. |

`synthetic_control` and `unknown` are also legal origins. `unknown` is not available evidence.

A record that `depends_on` another record must copy that record's independence group. Republishing a dump cannot mint a new group. Two records with the same URL, document offset, and digest are a duplicate-content error; represent the second copy with `duplicate_of` instead.

## What can verify an event

`event_verified` is true only when all of the following hold:

- `authenticity` is not `forged`.
- `verification_method` is `excerpt_sha256` or `independent_log_digest`.
- Every necessary source has record integrity: `public_bytes`, matching digest, `access_level: public_bytes`, `custody: intact`, `redaction: none`, and `locally_held`.
- `excerpt_sha256` verifies a `narrative_report` only. It verifies that the pinned publication bytes match. It does not verify a world event.
- `independent_log_digest` verifies only `independent_service_log` or `committed_effect`, and only when the necessary sources are `independent_provider_telemetry` or `synthetic_control`.

A transcript-visible command, tool-call arguments, a narrative report, and a message-board sentence are insufficient for an executed-command or committed-effect claim. An independent service log is not itself a committed effect. Claims list `required_event_kinds` and `insufficient_event_kinds`; an unclassified kind is a validation error.

Support also requires enough distinct verified groups, a bound actor when the claim requires one, and `time_basis: source_stated` when the claim requires an event time. `reconstructed` and `missing` times are reported in `rejected_times` and are not copied into `chronology`. A narrative's stated window is not copied onto an unobserved effect.

`source_conflict` is true when offered events conflict or carry both supporting and contradicting polarities, including when neither side is verified. `unverified_binding` is true when an offered event's actor is `unverified_binding` or `conflicting`. Both remain visible on an unresolved claim.

If verified admissible evidence both supports and contradicts a claim, the claim stays `missing_evidence`. A verified contradiction with no verified support refutes the claim through the existing `failed_enforcement` projection (`contradicted_in_scope`) and sets `failure_origin` to `evidence`. That projection is the #12 verdict scale, not a new one.

## Coverage

Each claim lists evidence slots. Every slot is exactly one of `available`, `withheld`, `redacted`, or `unobserved`. Those four counts sum to `coverage.denominator`. The denominator is the slot count. It is not a reported message count or transcript count.

`qualify_claim` reads `normalize_lineage`. Each offered observation is bound to its producer, collection boundary, source reference or digest, subject, actor and task scope, event time, observation availability, and coverage interval. Unknown stays unknown. Authenticity, temporal applicability, scope binding, and collection completeness are separate fields. A content digest identifies pinned bytes. `digest_certifies_assertion` is false.

`public_report_assertion`, `synthetic_model_record`, and `application_readback` stay distinct in `evidence_type_counts`. Normalization does not rewrite one of those three into another.

Two reports of the same underlying record share a corroboration key. The key follows `duplicate_of` and `depends_on`, and identical pinned bytes collapse even when a graph mints a second independence group. `independent_observation_count` is the number of distinct keys on admissible supporting events. A duplicated report does not increase it. Analyst identity is `investigator_count` and is not that count.

An unavailable source (`withheld`, `private_original`, `unobserved`, `unknown`, or a redacted record that is not locally held) is listed on `unavailable_sources`. It is not an upgrade gate. `validate_graph` rejects `blocks_upgrade: true` on such a source. The original OpenAI transcript dump and the Hugging Face platform logs are recorded that way. The public LessWrong post and its released reproduction transcripts are a different record and can qualify a claim about that release. Missing records do not become a requirement that only those withheld originals can satisfy.

A `blocks_upgrade` slot on a held source still prevents `supported` until a verified supporting event uses that source. Another source's bytes do not clear it.

When a claim has unavailable records and no `coverage_assumption`, the result includes `missing_requirements` entry `coverage_assumption`. Absence of a sink row is evidence of no effect only when that assumption is declared `complete` for a named operation and closed interval, the collection is held, and no original on the claim is still unavailable. A partial assumption records the gap and does not treat absence as no effect. A complete assumption contradicted by an unavailable original is `invalid_requirements`, not a no-effect verdict and not a real-world certificate.

`reported_not_held` may echo a published approximate count. The qualifier forces `held_by_audit` false. A fixture cannot declare those counts held.

## Incident demonstration

Replaying the fixture yields three unresolved world claims:

| Claim | What the public record supports | What stays unavailable |
| --- | --- | --- |
| `prov_tool_call_spoof` | The displayed `echo REAL; sleep` example does not establish the executed command. METR and Redwood are one group. The return token conflicts with the displayed command. The actor is unbound. | `src-transcript-dump`, recorded, not a gate |
| `prov_message_board` | The two public sentences about the unsanctioned board are one group. Reported counts of about 70,000 messages and 1,200 agents are not held records. | `src-board-dump`, recorded, not a gate |
| `prov_hf_effect` | The Hugging Face timeline, OpenAI's outline, and METR's out-of-scope statement do not observe a committed effect. The stated July window is not promoted. | `src-hf-platform-logs`, recorded, not a gate |
| `prov_reproduction_transcripts` | The pinned LessWrong post sentence verifies the release statement. The appendix is a second report of that same release, so the independent count stays 1. | The OpenAI dump and Hugging Face platform logs stay on the claim and do not block this qualification |

Retrieval on 2026-11-07 pinned the METR page, the Redwood page, the Hugging Face timeline, and the OpenAI technical-report PDF by body SHA-256. The OpenAI HTML page returned HTTP 403; that URL is `access_level: unknown` and is not evidence. Full documents are not stored in the repository. No credentials or exploit procedures are included.

`real_world_authenticity_certified`, `incident_detection_claimed`, and `incident_prevention_claimed` are false on every qualification. A fixture that supplies its own log bytes can satisfy the internal rule and still does not certify a real-world event.

## Regeneration

```bash
PYTHONPATH=src python experiments/provenance/qualify.py
PYTHONPATH=src python -m pytest -q tests/test_provenance_contract.py
python scripts/validate_claims.py
python scripts/check_evidence.py
```

`experiments/provenance/qualify.py` rewrites `evidence/provenance/` from the fixture. It refuses to mark the method claim reproduced unless all three incident claims are unresolved and non-certifying.
