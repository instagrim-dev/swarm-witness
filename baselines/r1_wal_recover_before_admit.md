# Classical baseline: recover / validate the durable log before admit

## Mechanism class

SoundGate’s recovery barrier is an instance of a classical durable-log pattern:

1. Keep admissions (releases, rejections, cancellations) in an append-only log.
2. On restart, **exclusively lock** the log, **validate** every complete record,
   and **repair** only an unfinished final fragment (truncate or complete a
   missing newline) under stated storage assumptions.
3. **fsync** the repair, **replay** acknowledged decisions into memory, then
   open the listener / admit new requests.

The classical null is therefore: *durable auth/decision log + repair/validate
before admit*. Ephemeral in-memory acknowledgement stores fail this class
because a restart forgets prior refusals unless they were persisted and
replayed before serving.

## Relation to R1 labels

- The **bug reproduction** (original 0.1.3 recovery losing an acknowledged
  decision across two restarts under torn-tail + append) is a concrete defect
  in one implementation of that class.
- The **barrier policy** restores the classical ordering (normalize → sync →
  replay → admit). When the barrier sweep yields `prohibited_effects == 0`,
  the claim may be labeled `reproduced` for the SoundGate scope while the
  *mechanism class* still matches `classical_baseline_matches`: a correctly
  ordered durable log with recover-before-admit is the expected control, and
  the barrier is that control re-asserted inside the service.

In short: `classical_baseline_matches` describes the **mechanism class**
(durable log checked before admit). `reproduced` describes whether this
pinned SoundGate barrier experiment restored acknowledged restrictions under
the published histories. Both can hold at once.
