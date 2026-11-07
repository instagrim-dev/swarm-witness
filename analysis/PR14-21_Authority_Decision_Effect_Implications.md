# Swarm Witness: adversarial implications of PRs #14–#21

**Basis:** main research submission at `08fca16`. The terminal tips are integrated beside the historical protocols, not by merging PRs #14–#21: taxonomy #22 (`fdb2386`), settlement ledger #23 (`28b3642`), and the wider R5 protocol as claim `r5_v3` rather than `r5_v2` (#24, `12d9c08`). Historical claim ids `taxonomy_theory`, `causal_swarm`, and `r5_v2` (13 scenarios / 26 arms) stay in place. The #15 / #19 / #21 concurrency snapshots are not the current pin.

## Central result worth carrying into the submission

**Evidence, decisions, and effects are three distinct objects of assurance.** A receipt or cached owner snapshot may justify a locally consistent choice while failing to justify an effect after revocation, grant consumption, or scope change. Conversely, a wrong local allow can be prevented by a second authoritative check at effect settlement. That is a *defensible mechanical finding*, not a claim of a novel authorization primitive.

The corresponding formal statement is **property-scoped**:
- `P_dec`: the authorization decision matches the required policy under verified current authority.
- `P_eff`: no effect is committed when the authoritative permission rule requires denial.
- Mechanism-wide safety must test `P_dec ∧ P_eff` (or report the two claims independently). `support(P_dec)` does **not** imply `support(P_eff)`. An audit claiming both from decision-only evidence is unsound.

The formal follow-on (#20) gives a finite eight-world permission fragment (grant × decision × effect), theorems T1–T6 and counterexamples C1–C7. C7 shows that a correct deny can remain `supported` for the **decision** property while a committed unauthorized effect refutes the **joint** property. A single three-way label is consequently a lossy projection; retain evidence, decision, effect and failure-origin coordinates.

## Specific experimental counterexamples from the corrected simulator (#19)

| Scenario | Decision-level observation | Authoritative effect observation | Finding |
| --- | --- | --- | --- |
| Dual-observe-then-claim | Two actors may both have locally favorable evidence / `allow` | Reference settles one effect and refuses the second; mutant double-commits | One-use must be measured at settlement, not just through a decision trace |
| Revocation with delayed active snapshot | Agent B decides `allow` after authoritative revocation | Reference refuses settlement, with a recorded refusal reason; no unauthorized effect | Wrong decision and successful effect enforcement coexist |
| Forged assignee / stale binding | A non-assignee attempts a claim | Correct reference refuses `agent_not_assignee`; mutant admits the forged scope | Current grant activity alone is insufficient: scope binding matters |
| Paired worlds and irrelevant facts | Old receipt/visible evidence can match across active and revoked worlds | Fresh, independently delivered grant state distinguishes permission | Additional data is useful only if it discriminates the claim and has verified provenance |

**Observation freshness denominators:** `current_grant_observation` must not be filled from a stale snapshot. Effect `refused` is distinct from `not_attempted` and from `committed`.

**Source anchors:** [#19](https://github.com/instagrim-dev/swarm-witness/pull/19) head `c23f295`; [#20](https://github.com/instagrim-dev/swarm-witness/pull/20) head `79edb7c`.

## Expanded R5 (#21): important coverage, one blocking provenance mismatch

The R5-v2 review branch reports **36 case rows, seven coverage dimensions, eight paired-input groups, ten concurrency-derived rows and three held-out rows**. Those values refer to a different versioned protocol from main's previously delivered **13 scenarios / 26 policy-arm runs over nine tags**. They are **not additive replications or interchangeable denominators**. R5-v2 distinguishes authority, delegation, receipt provenance, delivery, decision/effect separation, mechanism arms and causal interleaving, with tested/untested seams explicitly enumerated.

**Blocking mismatch:** #21 pins `mas-revocation_late_observation_reference.json` from the *pre-remediation* simulator, in which the reference arm reports `b-late.committed_effect=true` after revocation. The corrected #19 `revocation_late_observation_reference` trace reports `effect_settlement=refused`, `committed_effect=false` and `authoritative_spent_or_revoked`. A recorded SHA authenticates which bytes were used; it does not validate the old mechanism. Re-pin from the integrated #19 head, regenerate the concurrency-derived R5 rows, refresh hashes, and re-evaluate findings before treating the 36-row score as a publication result.

**Source:** [#21](https://github.com/instagrim-dev/swarm-witness/pull/21) head `31d8862`; [#19](https://github.com/instagrim-dev/swarm-witness/pull/19) head `c23f295`.

## Integration and publication order

1. Integrate the terminal **formal** chain #14/#17/#20 into current main after reconciling its independent eight-world formal oracle with the already delivered four-world checker. Preserve both model scopes and the C7 property-scoped demonstration.
2. Integrate the terminal **simulator** chain #15/#18/#19 into current main, preserving existing `experiments/causal_swarm/` as a separate versioned protocol; require TOCTOU one-use, stale-revocation denial at effect settlement and forged-assignee denial to pass with native modeled effect readback.
3. **Only then** regenerate R5-v2's pinned concurrency evidence and integrate #16/#21; the copied pre-remediation run files must not remain authoritative.
4. Regenerate the evidence index, clean review ZIP, report tables and final PDF from one coherent source revision. Do not replace retained runs in place, and do not silently sum overlapping simulations. Compare planned, executed and inspectable denominators.
5. Keep the original R3-D unresolved comparison and bounded R3-L1 classical match separate.

## Strongest submission framing after integration

**Swarm Witness: A Testable Evidence Standard for Agent Safety Claims**

> A correct permission decision is not proof of a permitted effect. Swarm Witness measures what an agent knew, what its gate decided and what the authoritative effect boundary actually committed; independently qualified observations determine which security claims survive.

The currently delivered main-branch paper already supports this research direction through its own bounded causal model and formal checks. The additional terminal-branch counterexamples refine the mechanism and theorem scope. **Until integrated and source-aligned, they are reviewed branch findings rather than released final results.**

## Explicit exclusions

Neither controlled event scheduling nor the conditional possible-world theorems prove production BMO correctness, live distributed-agent safety, cryptographic authenticity, or unbounded multi-agent behavior. Those properties require new experiments at their respective boundaries.
