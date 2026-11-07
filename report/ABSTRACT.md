When agent-safety controls produce apparently valid evidence, what additional
observations, assumptions, and comparisons are required before we can justify
claims about their behavior? We introduce Swarm Witness, an executable
claim-audit method that makes those distinctions explicit through source-pinned
experiments, conventional reference monitors, and fail-closed findings.
Classical authorization is the null hypothesis—not a new primitive we invent.
We apply the method to two prior agent-safety projects, reproducing bounded
results on restart-safe authorization (R1: 153 histories/policy; barrier
prohibited effects 0 vs original 143) and receipt-attribution ambiguity (R2:
36/36 condition-by-seed checks). Separately, a new matched experiment compares
BMO’s transactional first-edit admission with an independent SQLite gate across
six synthetic cases; retained observations agree on the tested one-use
properties under a fail-closed native pin (`classical_baseline_matches`), while
the legacy decision-model R3 comparison remains unresolved. A fourth protocol
makes the audit method’s three-way distinction executable: missing evidence
(identical old receipts leave valid vs revoked worlds indistinguishable),
failed enforcement (revoked grant observed but a broken gate still allows),
and supported conclusions (correct allow/deny once discriminating evidence is
present) (R4 reproduced). Our contribution is that reusable distinction—not a
swarm-authorization architecture or a proof of general BMO equivalence.
