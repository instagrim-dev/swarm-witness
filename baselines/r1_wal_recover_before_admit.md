# Authored mechanism interpretation: recover / validate before admit

> **Not an empirical finding.** This note is an **authored mechanism
> interpretation**. It does **not** establish, and must not be read as, a
> Finding with label `classical_baseline_matches`. Empirical classical-match
> labels are reserved for declared matched comparisons (R3). R1’s authoritative
> experimental label lives only in `evidence/r1/findings/*.json`.

## Mechanism class (interpretation)

SoundGate’s recovery barrier is *interpreted here* as an instance of a classical
durable-log pattern:

1. Keep admissions (releases, rejections, cancellations) in an append-only log.
2. On restart, **exclusively lock** the log, **validate** every complete record,
   and **repair** only an unfinished final fragment (truncate or complete a
   missing newline) under stated storage assumptions.
3. **fsync** the repair, **replay** acknowledged decisions into memory, then
   open the listener / admit new requests.

The classical null hypothesis for this *class* is: *durable auth/decision log +
repair/validate before admit*. Ephemeral in-memory acknowledgement stores fail
this class because a restart forgets prior refusals unless they were persisted
and replayed before serving.

## Classical references (recover-before-admit)

Mechanism-class framing only — not evidence that this R1 sweep matched a
separately evaluated classical baseline arm:

- Durable write-ahead / redo logging with recovery before serving new work
  (classical DB recovery ordering: analyze → redo → undo / admit).
- Auth and capability systems that persist denials or grants and reload them
  before accepting requests after restart.
- Crash-safe append-only ledgers that truncate or repair a torn tail, fsync,
  then reopen for appends.

## Limits of this note

- No matched classical decision-model arm was executed for R1.
- No per-case classical vs SoundGate comparison records exist under
  `evidence/r1/`.
- Therefore this file **must not** be cited as supporting
  `classical_baseline_matches`.
- If the barrier sweep’s computed Finding is `reproduced`, that speaks only to
  the pinned SoundGate recovery-barrier claim scope—not to empirical classical
  parity.

## Relation to R1 Finding labels

- The **bug reproduction** (original 0.1.3 recovery losing an acknowledged
  decision across restarts under torn-tail + append) is a defect in one
  implementation of the durable-log class.
- The **barrier policy** restores recover-before-admit ordering. Whether the
  pinned sweep yields `prohibited_effects == 0` is recorded as a **computed**
  Finding (`reproduced` / `contradicted_in_scope` / `unresolved`) from counted
  case records—not from this Markdown.
