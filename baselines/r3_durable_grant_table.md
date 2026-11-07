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

- This comparison shows **mechanism-class affinity via proxies**, not
  isomorphic ClassicalGate ↔ BMO decision contracts. The honest overall label
  is therefore `assumption_dependent`.
- Do **not** claim `classical_baseline_matches` unless an independent BMO
  observation supports the same allow/deny without hardcoding that decision
  from the ClassicalGate row.
- `rejected + restart + execute` in ClassicalGate means process-reload of a
  rejected map entry. `TestOrdinaryRetainedGrantLegacyWriterBoundary` is a
  competing-writer / transfer-tombstone race — related durability theme, **not**
  isomorphic to restart reload (`proxy_mismatch`).
- Other rows (spent/prior-consumer, owner-witness admit, wrong/altered grant)
  are deny/allow-shaped proxies for the mechanism class; disclose them as
  `mechanism_class_proxy`, not decision matches.

## Discriminating comparison (from latest run)

| Condition | ClassicalGate | BMO observed | Relation | Proxy evidence |
| --- | --- | --- | --- | --- |
| retained_start_claim + relaunch | deny | not_isomorphic | mechanism_class_proxy | yes |
| rejected + restart + execute | deny | not_isomorphic | proxy_mismatch | n/a |
| active_grant + execute | allow | not_isomorphic | mechanism_class_proxy | yes |
| stale grant copy vs current | deny | not_isomorphic | mechanism_class_proxy | yes |
