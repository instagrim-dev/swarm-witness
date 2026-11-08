# Evidence binding v1

**Version:** `evidence-binding-v1`
**Issue:** #40. Parent #26.
**Executable form:** `src/swarm_witness/evidence_binding.py`
**Reference:** `src/swarm_witness/formal/evidence_reference.py`
**Entrypoint:** `audit_entrypoint`, which reads a retained property-graph workflow and the native-witness packet. A property mask and an evidence mask are not inputs.

This protocol binds retained observations to the existing nonempty compatible-world rule. It reuses the property-family vocabulary and the conclusion classes. It does not add a second checker, and it does not build the SQLite application witness.

The formal reference encodes the same set rule with bit masks. It does not call the production verdict. Agreement is a check that the adapter's worlds and the mask rule describe one judgment. It is not a proof that the actual world is in the compatible set.

## Finite abstractions

Each supported family declares a proposition, a quantifier, an actor scope, a task scope, a target event, a target time, a finite world list, the worlds in which the proposition holds, and the observation constraints that may remove worlds. The families are `P_url`, `P_file_read`, `P_exec`, `P_identity`, `P_effect`, `P_local_control`, `P_decision_entitlement`, `P_commit_authorization`, `P_commitment`, `P_system`, `P_dec`, `P_eff`, and `comparison_equality`.

`P_system` is the conjunction of the five boundary properties. A supported URL allowlist does not support `P_system`.

Any other family, including population attribution and historical response latency, returns `unresolved` with the reason that no finite abstraction is declared.

## Observations

Normalized records come from three places:

- a retained property-graph case, using that case's channel scope, ledger, and frozen authority policy
- a provenance graph, after `normalize_lineage`
- the native-witness origin packet under `experiments/telemetry/packet`

Admissible public authenticity is the allowlist `authentic_public_text` and `released_reproduction_transcript`. `model_ledger` is admissible only as a synthetic channel. `spoofed_tool_line`, `unauthenticated_tool_line`, `unavailable`, and `not_checked` do not support or refute. `evidence_status` is the result of that check.

A shared `independence_group` is one origin. The same digest, a `duplicate_of` link, or a `depends_on` chain also collapses to one origin. Different digests do not split a shared group. The LessWrong reproduction post and appendix stay in `lesswrong-reproduction-2026-09`.

A missing observation leaves the unobserved alternatives compatible. Absence supports or refutes only when the claim declares a complete coverage premise for the operation being judged. An interval on that premise, when present, also marks records outside it as stale. Unavailable original transcripts and platform logs are recorded and are not upgrade gates. `blocks_upgrade` is rejected unless the audit holds the bytes, and a held gate that does not verify the claim blocks support.

An effect row confirms a commit only when the actor, object, and operation match the claim, or the record carries a verified mapping. `requires_event_time` applies to refuting records as well as supporting ones. Authentic stale evidence does not bind, and it is not fabricated evidence.

Fault attribution reads only records that verify the target proposition. Otherwise the actor stays `undetermined`.

Comparison divergence, a wrong decision, an unauthorized commit, and fault attribution are separate fields. A refuted sufficiency sentence stays `refuted`. It is `failed_enforcement` only when an exercised mechanism is shown to violate the property.

## Actual-world membership

The judgment is sound only if the actual world remains in the compatible set. That membership is an assumption of the adapter. A source hash does not prove it. A passing test does not prove it. Neither proves that the collection is complete. `real_world_authenticity_certified` and `detection_or_prevention_claimed` stay false.
