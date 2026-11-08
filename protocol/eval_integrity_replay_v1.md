# Eval integrity replay v1

**Version:** `eval-integrity-replay-v1`
**Issue:** #50. Parent #26. Complements #51.
**Executable form:** `src/swarm_witness/eval_integrity_replay.py`
**Entrypoint:** `experiments/eval_integrity_replay/run.py`

Re-audit of **released** OpenAI–Hugging Face *reproduction* traces for
evaluator / scoring-source compromise. This is not the original private
incident telemetry.

## Primary property

`P_clean_elicitation`: target behavior was elicited **without**
grader/scoring-source exposure before the scored action.

Verified contamination requires authenticated Stage-B evidence of
grader/scoring-source exposure **before** scored behavior. The pinned envsrc
judge records `gets_source` and a short evidence string. It does not order
that access against scored behavior and does not verify target success.
Those cases stay `unresolved`. `headline_eligible` stays false until a
public trajectory supplies the order and an independent positive outcome.

## Stages

| Stage | Content | May enter production evaluator? |
| --- | --- | --- |
| A | Transcript / claimed outcome | yes |
| B | Command/tool readback with source-access evidence | yes |
| C | Independent evaluator/runner record | yes when held |
| Author tags | Original exclusion / success labels | adjudication only |

## Sources (read-only)

- Git reproduction: `msp895/oai-hf-incident-reproduction` @ pinned commit
- Hub dataset: `stewy33/oai-hf-incident-replication` @ pinned revision
- Published envsrc judge labels under `analysis/step2_envsrc_judge.json`

Unavailable original OpenAI/HF private logs are recorded and are not upgrade
gates.

## Methods

Identical evidence budget: `naive_pass`, `strong_checklist`, `swarm_witness`.

## Limits

A bounded null result closes the experiment. Headline promotion requires a
trace-backed conclusion correction **and** at least one verified valid
success retained. `transfer_claim` / detection / prevention stay false.
