# Authored mechanism interpretation: no implicit exclusivity / authenticity

> **Not an empirical finding.** This note is an **authored mechanism
> interpretation**. It does **not** establish, and must not be read as, a
> Finding with label `classical_baseline_matches`. Empirical classical-match
> labels are reserved for declared matched comparisons (R3). R2’s authoritative
> experimental label lives only in `evidence/r2/findings/*.json`.

## Mechanism class (interpretation)

Event attribution from a receipt is *interpreted here* as an instance of a
classical evidence rule:

1. A ledger (or other independent log) can show that a mutation **happened**.
2. A transcript event that **possesses** a matching receipt shows that someone
   **held** those bytes — including after copy, forward, or relay.
3. Binding the mutation to that transcript event therefore requires an
   **explicit** declaration that the token could not have been copied
   (exclusivity) or that the recorder’s records cannot be fabricated
   (authenticity). Possession alone is not that binding.

The classical null for this *class* is: *no implicit exclusivity*. Matching
tokens remain ambiguous until exclusivity or authenticity is declared; a false
declaration must be able to restore a confident (and incorrect) attribution.

## Classical references (no implicit exclusivity)

Mechanism-class framing only — not evidence that this R2 stress pack matched a
separately evaluated classical baseline arm:

- Evidence / capability systems that refuse to promote possession or presentation
  of a token to actor-binding without an exclusivity or authenticity assertion.
- Classical log / audit designs that treat copied receipts as transferable
  artifacts, not exclusive event witnesses.
- Security folklore: “possession of a ticket ≠ proof you were the originator”
  unless the protocol declares single-holder or authenticated issuance.

## Limits of this note

- No matched classical decision-model arm was executed for R2.
- No per-case classical vs EvidenceGraph comparison records exist under
  `evidence/r2/`.
- Therefore this file **must not** be cited as supporting
  `classical_baseline_matches`.
- If the stress pack’s computed Finding is `reproduced`, that speaks only to the
  pinned EvidenceGraph incident-stress claim scope—not to empirical classical
  parity.

## Relation to R2 Finding labels

- The **bug reproduction** (old rule implicitly treating a matching token as
  event binding under full-token relay) is a defect in one implementation of the
  no-implicit-exclusivity class.
- The **safer default** restores declare-exclusivity-or-abstain ordering.
  Whether the pinned stress yields zero possession-only supported attributions
  is recorded as a **computed** Finding (`reproduced` /
  `contradicted_in_scope` / `unresolved`) from counted row records—not from this
  Markdown.
