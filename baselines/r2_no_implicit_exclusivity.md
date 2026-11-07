# Classical baseline: no implicit exclusivity / authenticity

## Mechanism class

Event attribution from a receipt is an instance of a classical evidence rule:

1. A ledger (or other independent log) can show that a mutation **happened**.
2. A transcript event that **possesses** a matching receipt shows that someone
   **held** those bytes — including after copy, forward, or relay.
3. Binding the mutation to that transcript event therefore requires an
   **explicit** declaration that the token could not have been copied
   (exclusivity) or that the recorder’s records cannot be fabricated
   (authenticity). Possession alone is not that binding.

The classical null is therefore: *no implicit exclusivity*. Matching tokens
remain ambiguous until exclusivity or authenticity is declared; a false
declaration must be able to restore a confident (and incorrect) attribution.

## Relation to R2 labels

- The **bug reproduction** (old rule implicitly treating a matching token as
  event binding under full-token relay) is a concrete defect: one wrong
  supported attribution among twelve registry mutations per seed.
- The **safer default** restores the classical ordering (declare exclusivity /
  authenticity, else abstain). When the safer relay view yields **0** supported
  attributions and the undeclared-exclusivity clean control withholds all
  twelve correct attributions, the claim may be labeled `reproduced` for the
  EvidenceGraph stress scope while the *repair rule* still matches
  `classical_baseline_matches`: refuse to promote possession to attribution
  without the declaration.

In short: `classical_baseline_matches` describes the **mechanism class** (no
implicit exclusivity). `reproduced` describes whether this pinned stress pack
restored that rule under the published paired conditions. Both can hold at once.
