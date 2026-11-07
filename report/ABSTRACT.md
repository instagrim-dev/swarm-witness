When agent-safety controls produce apparently valid evidence, what additional
observations, assumptions, and comparisons are required before we can justify
claims about their behavior? We introduce Swarm Witness, an executable
claim-audit method that makes those distinctions explicit through source-pinned
experiments, conventional reference monitors, and fail-closed findings.
Classical authorization is the null hypothesis—not a new primitive we invent.
We reproduce two established safety findings (R1 restart-safe authorization; R2
receipt-attribution ambiguity), compare a bounded BMO ledger property against a
classical reference monitor (R3-L1), and test a three-way evidence classification
on synthetic authorization and multi-principal scenarios (R4/R5). R4 separates
missing evidence, failed enforcement, and supported conclusions, including a
negative control that known-false grant observations cannot yield unqualified
support. R5 transfers that taxonomy to a sequential three-principal shared-grant
model (contention, A→B then B→C assignee hops, ledger-bound receipt misuse)—not
concurrent live swarm execution. The contribution is reusable audit discipline,
not a swarm authorization architecture or general BMO equivalence.
