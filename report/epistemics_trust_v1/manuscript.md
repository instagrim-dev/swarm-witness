# An Intact Actor Log Is Not an Effect Warrant

**Author:** Jonathan Maye-Hobbs
**Affiliation:** Independent

With Apart Research

## Abstract

Delegated agents leave logs of what they were allowed to do. This report asks whether an intact actor log warrants the conclusion that an unauthorized effect did not commit. The packets, warrants, invariant checker, and sixteen-case challenge are preexisting Swarm Witness material. The sprint-new work scores alternate stop-rules on those retained records. It does not replace Table 2 or Table 2b of the November submission. On 48 packets, four views of twelve histories, subject class on a held deciding effect, or a zero-row absence census, matches the projection and the invariant checker. Both arms already keep the deciding-premise screen. Subject class alone leaves 8 warranted supports unresolved. A support label plus that census still supports a false proposition on 2 packets. The intact-actor predicate holds on every packet, so supporting from it supports all 48. On a separate challenge of 16 mutations of one source packet, subject class supports 9 probes the projection leaves unresolved. Those are unsupported supports inside the sixteen, not a new denominator. The nine are scope, binding, an unknown subject beside an authorized sink, and the census. A bounded SoundGate probe maps retained statuses into this representation. The projection matches two protocol warrants, and the intact-run rule supports the warrant that is refuted.

## 1 Introduction

An actor log can already be intact. Does that record justify the effect conclusion, or does a consumer still have to admit the record as evidence?

Track 2 of the AI x Epistemics Research Sprint [2] asks what is missing before a record of what an agent did can be trusted. A tamper-evident copy would preserve the bytes the actor already wrote. Preservation is a copy. The open question is which check has to succeed before those bytes support the effect claim. In this experiment, intact is an operational predicate over retained record metadata, not a cryptographic guarantee of origin, completeness, or correct binding to a committed effect.

The measurement uses retained records from the Swarm Alignment submission [1]. It does not re-execute BMO, and it does not replace Table 2 or Table 2b of that submission. The historical label's 11 unsupported supports remain Table 2.

## 2 Preexisting work and sprint-new work

Preexisting, relative to November 13–15, 2026: BMO, the SQLite gate, the twelve application histories, the 48 packets, the evidence-stage warrants, the historical Swarm Witness labels, the invariant checker, and the sixteen-case projection challenge. The challenge ledger is not rewritten.

Sprint-new: the consumer ladder in `experiments/epistemics_trust_v1/run.py`, the record-level reading of the eleven, and this report. The ladder calls the preexisting admission predicates. It does not add a packet to the 48.

C2PA specifies provenance metadata for media [3]. OpenTelemetry's GenAI semantic conventions specify spans, metrics, and events for generative-AI clients [4]. The sprint proposes a signed log on those conventions [2]. This experiment implements neither. It scores which retained check has to succeed before an actor record supports an effect conclusion.

## 3 Method

The first denominator is 48 packets: four views of twelve histories. Each packet is scored for `P_effect` against the evidence-stage warrant. An unsupported support is a supported output whose warrant is refuted or unresolved. A correct decisive conclusion agrees with a supported or refuted warrant. A correct abstention returns unresolved where the warrant is unresolved. Supports of a false proposition are counted separately, using the controlled truth already stored with the warrants.

Five alternate stop-rules are scored on those packets. The full projection is scored beside them as the reference row, so the later table has five alternates and that reference.

The intact-actor rule supports `P_effect` when a requested-command record is locally held, custody intact, marked bound, and carrying public bytes. On this corpus that predicate holds on every packet, so the rule supports every packet. That predicate reads retained metadata. It does not verify a signed log or a completeness proof. The historical-label rule reads the retained Swarm Witness verdict. It is not one of the five alternates.

A held deciding effect is a committed-effect row that is locally held, carries public bytes, and passes the preexisting deciding-premise check: not misbound, not withheld, not rejected for authenticity, and not stale. The zero-row absence census is preexisting too. It passes that premise check, declares no commit rows, and every actor event sits inside its run, operation, and interval. The table names the read that happens after the checks that row keeps. Subject class or the census is not a bare two-field evaluator.

| Stop-rule | Checks it keeps | Checks it does not read |
| --- | --- | --- |
| Intact actor, unless every such actor is the misbound probe | Intact-actor metadata, then withhold support when every such actor is the misbound probe | Deciding-premise check, scope, binding, census |
| Held deciding effect whose own label says supports | Held deciding effect whose polarity says supports | Subject class, sink scope, binding, census count |
| Subject class, no absence census | Held deciding effect's authorized or unauthorized class | Sink scope, binding, census count, absence |
| Support label, or the zero-row absence census | That support label, otherwise the zero-row absence census | Subject class, sink scope, binding |
| Subject class, or the zero-row absence census | Subject class, otherwise the zero-row absence census | Sink scope, binding, non-zero census count |
| Full projection | Deciding premise, then sink scope, binding, and census |  |

The projection is the preexisting observation rule. The invariant checker scores that projection, so their agreement is agreement inside one pipeline.

The second denominator is the preexisting sixteen-case challenge: sixteen mutations of one discriminating-readback packet. Its source packet is `aew-v1-h-authority-current/discriminating_readback`. Those sixteen probes are not added to the 48.

Public commit `ea58c7d` of https://github.com/instagrim-dev/swarm-witness contains the measurement runner. The commands below reproduce the counts.

```bash
python experiments/epistemics_trust_v1/run.py
python -m pytest tests/test_epistemics_trust_v1.py tests/test_epistemics_trust_report.py -q
```

## 4 Results

The consumer table scores the 48 packets. Correct abstention uses the 24 unresolved warrants as its denominator. Correct decisive uses the 24 warranted decisive conclusions. The intact-actor predicate holds on every packet.

| Consumer | Unsupported support | False-proposition support | Correct decisive | Correct abstention |
| --- | ---: | ---: | ---: | ---: |
| Intact actor record | 26 | 4 | 22/24 | 0/24 |
| Historical Swarm Witness label | 11 | 0 | 24/24 | 13/24 |
| Invariant checker | 0 | 0 | 24/24 | 24/24 |

The historical 11 and the checker's 0 are November Table 2, with Table 2b the later replay of the same files. This table adds the intact-actor row. It does not replace those two.

All 11 historical unsupported supports are `withheld_misbound` packets whose controlled proposition holds. Deciding records across them sum to 0. All 11 packets contain an actor record that meets the intact-actor test and that admission marks misbound: 13 records, with 2 packets holding two. 4 have no effect row, so a withheld row labeled supports does not explain the set. This note does not establish why the retained verdict supported the other 7. One further withheld packet, `aew-v1-h-local-pass-broader-effect`, has that withheld effect row. The historical label there is unresolved, and the controlled proposition is false.

The next five rows are alternate stop-rules on the same packets. The last row is the full projection, the reference those five are compared with. A later row is not the previous row with one check removed.

| Stop-rule | Unsupported support | False-proposition support | Correct decisive | Correct abstention |
| --- | ---: | ---: | ---: | ---: |
| Intact actor, unless every such actor is the misbound probe | 14 | 3 | 22/24 | 12/24 |
| Held deciding effect whose own label says supports | 2 | 2 | 14/24 | 24/24 |
| Subject class, no absence census | 0 | 0 | 16/24 | 24/24 |
| Support label, or the zero-row absence census | 2 | 2 | 22/24 | 24/24 |
| Subject class, or the zero-row absence census | 0 | 0 | 24/24 | 24/24 |
| Full projection | 0 | 0 | 24/24 | 24/24 |

Subject class, or the zero-row absence census, mismatches the projection on 0 of these packets. The projection and the invariant checker differ on 0 packets. That agreement is inside one pipeline. Subject class alone leaves 8 warranted supports unresolved: both sink views of the four histories with no effect row. The support label, or the absence census, still supports the false proposition on 2 packets, both sink views of `aew-v1-h-local-pass-broader-effect`. Rejecting the misbound probe and otherwise trusting the actor log still has 14 unsupported supports.

The sixteen-case challenge is a separate denominator. Its cases are the preexisting mutations in `experiments/effect_witness/native_projection_challenge_v1.yaml`. Subject class or the absence census has 9 unsupported supports, 2/2 correct decisive conclusions, and 5/14 correct abstentions. The projection has 0 unsupported supports, 2/2 correct decisive conclusions, and 14/14 correct abstentions. The projection mismatches the challenge warrant on 0 probes. Its agreement with the invariant checker, 0 mismatches, is the same pipeline. The 16-case results measure direct evidence projection over mutated records. Three cases rejected by the ordinary packet entrypoint are counted as unresolved by this direct projection: `mixed-unknown-authorization`, `sink-unknown-subject`, and `coverage-withheld`. A fourth entrypoint rejection, `coverage-duplicate`, is supported by this projection. These are projection-level results, not 16 successful end-to-end packet admissions.

The probes where subject class supports and the projection stays unresolved are unsupported supports inside the sixteen: scope, run id (sink-run-mismatch); scope, operation (coverage-operation-mismatch); scope, interval (coverage-interval-outside); binding (sink-actor-mismatch, sink-object-mismatch, sink-mapped-actor-mismatch); an unknown subject beside an authorized sink (mixed-unknown-authorization); a disagreeing census (coverage-conflict); a withheld census (coverage-withheld).

An exact duplicate census stays supported for both rules. A sink whose only subject is unknown stays unresolved for both. A misbound sink, a spoofed line, an unauthenticated line, and a stale sink fail the deciding-premise check here. The historical challenge label for the spoofed sink stays supported in the v1 ledger. That ledger is not rewritten.

## 5 Discussion

Subject class on a held deciding effect, or the zero-row absence census, matches the full projection on all 48 retained packets. Both arms already keep the deciding-premise screen, so the match is which further checks are idle on these packets. It is not evidence that subject class and a census, read alone, are sufficient trust infrastructure. On the sixteen mutations the same rule still supports nine probes the projection leaves unresolved. Those nine are discriminating counterexamples inside one source packet, not a deployment failure rate.

An intact copy of the actor log preserves the record the first consumer trusts. On these 48 packets, admission does not treat that intact actor record as the effect warrant. The record is still present on packets the checker supports. Subject class alone misses the eight absence supports. The support-label-or-census rule still has two supports of a false proposition.

Those nine are a count inside the sixteen: three scope checks, three binding checks, an unknown subject beside an authorized sink, and two census checks. Only the mapped-actor probe keeps a parent link. A withheld census is not a non-zero census count. Scope, parent binding, and the non-zero census do not cover the nine. The two denominators stay apart.

A bounded cross-system transfer probe maps retained SoundGate outcomes into the existing evidence representation, revision `656840348dcf9660f8db7add9f3ca9f794a55926`. The barrier warrant is the README success criterion, supported. The original-policy warrant is the stated bug, refuted. The projection returns supported for the barrier and refuted for the original policy. The intact-run rule supports both, so it overclaims 1. Because effect records are constructed from retained status fields, this is a representation and contract-consistency test, not independent external validation. The strict policy has no protocol warrant and is not in this score. A same-field tally on the 459 rows still shows 143 and 151 intact-run unsupported supports; that tally is not this probe. The 48 and the 16 stay separate. The November experiments stay not tested.

## References

1. Maye-Hobbs, J. Swarm Witness: evidence for agent authorization. Swarm Alignment submission, November 2026. Repository: https://github.com/instagrim-dev/swarm-witness
2. Apart Research. AI x Epistemics Research Sprint, 13–15 November 2026. https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15
3. Coalition for Content Provenance and Authenticity. C2PA Technical Specification, section 1.1. https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html. Retrieved 2026-11-15.
4. OpenTelemetry. Semantic conventions for generative AI, including spans, metrics, and events. https://github.com/open-telemetry/semantic-conventions-genai. Retrieved 2026-11-15.

## Appendix A Limitations and dual use

The 48 packets are four views of twelve histories. They are not a population rate and not an estimate of deployment reliability. The sixteen challenge rows are mutations of `aew-v1-h-authority-current/discriminating_readback`, so they are one source packet under sixteen edits. Warrants and controlled truth are author specified. The two SoundGate claims encode case status into effect records, leave out the strict policy, and do not change the November experiments. The current evaluator replay of the 48 remains a separate table and does not replace the historical 11. The SoundGate paragraph is a representation test on two protocol claims. It is not an independent reading of unfamiliar telemetry.

Subject class, or the zero-row absence census, matches the projection on these 48 packets. The same stop-rule still returns support on nine preexisting probes in the sixteen. Scope, parent binding, and a non-zero census do not describe all nine. A later packet can separate checks that agree on the 48.

The records are synthetic controls on one host. No personal data is used. The dual-use of the result is the sufficiency claim itself: a consumer who stops at subject class or a zero-row census will match the checker on these 48 and will still support the nine probes. The probes are the preexisting challenge, retained so the checks can be rerun.

## LLM Usage Statement

The author set the question, the denominators, and which conclusions the retained records were allowed to support. AI assistants contributed research design, the consumer ladder, validation scripts, and drafting of this report. The counts are produced by `experiments/epistemics_trust_v1/run.py`. The author is responsible for the claims, interpretation, and released artifacts.
