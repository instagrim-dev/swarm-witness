# Detection and response-latency replay v1

Protocol `detection-latency-replay-v1`. Seed `32` with `0` draws. Alert budget `1` for every detector.

This is an offline replay of authored synthetic controls and source-pinned public milestones. It is a separate research note from the hackathon submission. The evidence-index label `reproduced` means this protocol claim held, including the withheld historical latencies.

## Non-claims

- No incident-detection result is stated.
- No incident-prevention result is stated.
- Swarm Witness is not described as deployed on the incident.
- Synthetic durations are replay-clock measurements of this protocol.

## Latency claims withheld

Forensic telemetry was executed for the 2026 Artifactory / Hugging Face incident. Trustworthy source-stated event times on held incident evidence: 0. The OpenAI pages named in the issue returned HTTP 403. Hugging Face and METR supply publication dates and reconstructed narrative bounds. Those bounds are pinned and are not used as detector, acknowledgement, or enforcement times.

- `historical_time_to_first_warranted_alert`: withheld, seconds = null
- `historical_detection_to_intervention_gap`: withheld, seconds = null
- `historical_effect_before_alert_ordering`: withheld, seconds = null
- `hugging_face_narrative_window_duration`: withheld, seconds = null
- `hugging_face_day5_activity_to_cut_access`: withheld, seconds = null
- `metr_reconstructed_event_clocks`: withheld, seconds = null
- `may_signal_latency`: withheld, seconds = null
- `openai_post_timestamps`: withheld, seconds = null

Published historical latency results: 0.
The narrative window and the Day 5 activity notes stay withheld. The Hugging Face text says access was cut after the last meaningful activity and gives that cut no clock time, so `enforcement_at` is null.
No May timestamp was present in the retrieved sources.

## Incident detection latency

This result is computed from the executed forensic telemetry graph. The replay protocol above stays independently defined. A detection latency for the original incident is emitted only when held evidence supplies a trustworthy source-stated event time for both endpoints. Missing clocks are not subtracted.

The LessWrong reproduction post (`src-lw-reproduction-post`) and its appendix (`src-lw-reproduction-appendix`) are one public record. Independent observations: 1. Effect status `unobserved`. Event time null, time basis `missing`.

Unavailable originals on the executed graph. A row or an effect time is recorded when one is held. blocks_upgrade is read from the claim slots:

- `src-transcript-dump` (OpenAI transcript dump): rows 0, effect time null, blocks_upgrade false.
- `src-execution-log` (independent execution log): rows 0, effect time null, blocks_upgrade false.
- `src-board-dump` (Artifactory message-board dump): rows 0, effect time null, blocks_upgrade false.
- `src-hf-platform-logs` (Hugging Face platform logs): rows 0, effect time null, blocks_upgrade false.
- `src-hf-indicators` (redacted indicators): rows 0, effect time null, blocks_upgrade false.
- `src-launchpad-logs` (private launchpad logs): rows 0, effect time null, blocks_upgrade false.

Incident detection latency: absent, seconds = null.
Trustworthy event times on held incident evidence: 0.
Reason: `no_trustworthy_event_time_on_held_evidence`.
Detector alert time null. Effect commit time null.

A blocks_upgrade slot on held source `src-metr-command` prevents supported (probe finding `unresolved`). The probe is not an incident clock and is not written into the saved telemetry graph. An unavailable source is rejected as a gate.

Synthetic control durations elsewhere in this report are protocol-authored replay intervals. They are not this incident result. This replay does not certify the original incident.

## What the synthetic controls measure

Synthetic timestamps are protocol-authored. A published synthetic duration is the replay-clock interval of an instantaneous rule, or an authored enforcement time on that control. It is not an incident measurement.

- Detectable-stage denominator: 5.
- Historical stages excluded from that denominator: 4.
- Evidence-qualified audit true alerts: 5; false alerts: 0; synthetic abstentions: 3 of 10 stages.
- All 4 historical stages abstain because event telemetry is unavailable.
- Rule baseline true alerts: 3; false alerts: 0; misses: 2.
- Higher-threshold baseline at 2 true alerts: 1; misses: 4.
- Same baseline at threshold 1 true alerts: 4; false alerts: 0.
- Weak-indicator false alerts: 2.
- Primary-detector ties: 6. Disagreements: 4.
- Alerts suppressed by the shared budget: 3.
- Qualified alerts on the hindsight-document stage: 0.

Warranted synthetic alerts from the evidence-qualified audit:

- `syn-comms-incomplete-actors/actors-observed` (`synthetic_control`): time-to-first-warranted-alert 0 seconds; detection-to-intervention gap withheld; effect-before-alert `no_effect`.
- `syn-transcript-mismatch/effect-observed` (`synthetic_control`): time-to-first-warranted-alert 0 seconds; detection-to-intervention gap withheld; effect-before-alert `effect_before_alert`.
- `syn-local-ok-downstream/effect-observed` (`synthetic_control`): time-to-first-warranted-alert 0 seconds; detection-to-intervention gap 3600 seconds; effect-before-alert `effect_before_alert`.
- `syn-local-broken/decision-observed` (`synthetic_control`): time-to-first-warranted-alert 0 seconds; detection-to-intervention gap withheld; effect-before-alert `no_effect`.
- `syn-stacked-signals/both-observed` (`synthetic_control`): time-to-first-warranted-alert 0 seconds; detection-to-intervention gap withheld; effect-before-alert `effect_before_alert`.

Threshold 2 of the higher-threshold baseline misses every single-signal detectable stage and ties the audit on the stacked two-signal stage. Threshold 1 alerts on the communication, mismatch, downstream, and stacked stages. It misses the local-decision stage, which is outside its rule set. The weak indicator false-alerts when a channel is labeled unsanctioned and an actor id is missing. Those ties and failures are retained.

The rule baseline uses unsanctioned communication and command/effect mismatch. On the local-control case it misses the unauthorized downstream effect. The audit reports the local decision as supported and alerts on the downstream property.

## Availability ablation

A record is visible only when its own `observation_available_at` admits the protocol clock. Day-precision publication dates become visible on the next UTC date, because the pages do not give an hour. At the June 26 scope coordinate and at the July 13 narrative-date coordinate, the July 27 Hugging Face page and the August 26 METR page are excluded. A document, once visible, still does not satisfy a telemetry evidence requirement.

## Sources

- `hf-technical-timeline`: HTTP 200, article_available=true, operational_timestamps_admitted=0.
- `metr-investigation`: HTTP 200, article_available=true, operational_timestamps_admitted=0.
- `openai-index`: HTTP 403, article_available=false, operational_timestamps_admitted=0.
- `openai-misalignment`: HTTP 403, article_available=false, operational_timestamps_admitted=0.

Pinned stated bounds: 8. Latency-eligible bounds: 0. The 13:37 UTC and 14:14 UTC notes are stored with the Day 5 section date attached by this protocol, because those sentences do not repeat the calendar date. They are still withheld. `operational_timestamps_admitted` counts values copied into the six operational fields. None were copied.

The historical arm abstains. Incident detection latency is the telemetry binding above: an absence, not a duration.

## Reproduce

```bash
PYTHONPATH=src python experiments/detection_latency/run.py
```
