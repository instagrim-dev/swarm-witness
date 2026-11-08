# Auditor integrity v1

**Version:** `auditor-integrity-v1`
**Issue:** #51. Parent #26.
**Executable form:** `src/swarm_witness/auditor_integrity.py`
**Entrypoint:** `experiments/auditor_integrity/run.py`

Controlled audit of Swarm Witness itself under deliberate evidence
manipulation. Packets are synthetic and local. They are not the 2026
incident telemetry, not the LessWrong reproduction corpus (#50), and not a
detection or prevention claim.

## Separation

- `experiments/auditor_integrity/truth/` holds hidden fixture truth and is
  imported only by the adjudicator and tests that check expected labels.
- `experiments/auditor_integrity/packets/` holds the admissible visible
  evidence. Classifier methods import packets only.
- The adjudicator does not import classifier helpers. Classifier methods do
  not import truth files.

## Methods (identical evidence budget)

1. `naive_pass` — assertion / PASS shortcut over surface support literals.
2. `strong_checklist` — `strong_invariant_verdict` (may abstain).
3. `swarm_witness` — `swarm_witness_verdict` with ablation flags off.

Original-author tags and hidden truth are adjudication material, not method
input.

## Mechanisms

1. Evaluator-source leakage (grader exposure before scored behavior).
2. Transcript / effect divergence.
3. Source laundering (duplicate origin vs distinct provider readback).
4. Property laundering (narrow local control vs broader system property).

## Scoring axes

- Epistemic: `supported` / `refuted` / `unresolved` by exact property.
- Attribution: expected origin is pre-registered per case. Concrete
  assignments, abstentions, unsupported attributions, and correct-origin
  coverage use that denominator. A zero denominator is null.
- Labels: evidence insufficiency, ground-truth property false, and
  evaluation-contaminated are distinct adjudication fields.

## Limits

A null or worse comparison is a valid result. Conclusions are **controlled
audit integrity** unless separately confirmed on external traces (#50).
