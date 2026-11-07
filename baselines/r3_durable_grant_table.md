# Classical baseline: durable grant table before admit

## Mechanism class

BMO’s ordinary-retry retained-grant owner path is an instance of a classical
admit barrier:

1. Persist grant / transfer / rejection state in a durable table (or equivalent
   log) keyed by action / grant identity.
2. On every admit or relaunch attempt, **consult the current durable row** —
   not ephemeral in-memory “we were mid-recovery” flags alone.
3. Treat a **retained start claim** (metadata that a prior episode existed) as
   description of history, never as standing launch authority.
4. After restart or process reopen, **reload** the durable map before serving;
   a recorded rejection or spent/tombstoned grant continues to deny.
5. A **stale copy** of an old grant row must not outrank the current owner row.

The classical null is therefore: *durable grant table checked before admit;
retained state alone never authorizes relaunch*.

## Relation to R3 labels

- When BMO’s preexisting retained-grant witness tests and the `ClassicalGate`
  null produce the **same allow/deny decisions** under the matched conditions
  below, the honest label is `classical_baseline_matches`.
- This is **not** a novel BMO-only mechanism: it is the expected control class
  for “restart / retain ≠ permission.”
- Use `assumption_dependent` only if BMO exposes an observation classical
  lacked under the same inputs; investigate before claiming novelty if
  decisions diverge while observations match.

## Discriminating comparison (from latest run)

| Condition | ClassicalGate | BMO observed | Match |
| --- | --- | --- | --- |
| retained_start_claim + relaunch | deny | deny | yes |
| rejected + restart + execute | deny | deny | yes |
| active_grant + execute | allow | allow | yes |
| stale grant copy vs current | deny | deny | yes |
