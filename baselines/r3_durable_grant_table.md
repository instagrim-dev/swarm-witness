# Classical baseline: decision-model grant table (R3)

## Claim level

**Decision-model only.** `ClassicalGate` consults an in-memory map of
`action_id → {state, version}` and returns allow/deny from
`(state, request, grant_version)`.

- `dump` / `load` are **in-process fixture copies** for test convenience.
- They are **not** restart durability evidence and must not be read as
  fresh-process recovery claims.
- Stale vs current is distinguished by `grant_version` (epistemic extension
  home for this comparison).

## Mechanism class (authored interpretation)

1. A grant row is identified by action id and carries an explicit version.
2. On every admit attempt, consult the **current** row version — a stale
   `grant_version` cannot authorize execute even when state is `active_grant`.
3. A **retained start claim** is history metadata, never relaunch authority.
4. A **rejected** row denies execute under the decision model (no process
   restart required to state that rule).
5. Only `active_grant` + matching `grant_version` + `execute` allows.

## Relation to R3 labels

- Empirical `classical_baseline_matches` requires per-case records on **both**
  arms with matching inputs and isomorphic BMO observations.
- Package pass/fail counts are **not** BMO decisions.
- When BMO cannot supply isomorphic observations for a shared case, that case
  is `execution_status=missing` and the overall comparison Finding cannot be
  `classical_baseline_matches` (honest label: `unresolved` — incomplete
  comparative audit, not assumption-dependent affinity).

## Discriminating comparison (from latest run)

| Case | Classical | BMO | Match | BMO status |
| --- | --- | --- | --- | --- |
| retained_start_claim_relaunch | deny | None | False | missing |
| rejected_execute | deny | None | False | missing |
| active_grant_execute | allow | None | False | missing |
| stale_grant_version | deny | None | False | missing |

Overall finding label: `unresolved`.
