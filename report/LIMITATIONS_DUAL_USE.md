# Appendix A. Limitations and dual-use / ethical considerations

**Evidence and domain limits.** Claims are bounded to specified artifacts, synthetic schedules and formal assumptions. The BMO result covers an L1 transactional owner and selected projections, not full execution safety. Simulator principals share deterministic scheduling and modeled state; they are not live agents and do not establish emergent coordination. Proofs assume authenticated compatible-world evidence with the actual world inside the compatible set. Falsified observations or an unsound compatibility model can invalidate those premises. Incomplete evidence leaves more worlds compatible and may require an unresolved conclusion. Neither the taxonomy nor the finite checker proves those premises for external datasets. The proofs apply to the specified set semantics; the audit evaluator is assessed on the declared scenario corpus.

**Possible adversarial use.** Audits that expose stale-authority, receipt-replay or delegation errors could help an attacker find where a system trusts old evidence. We release bounded schedules, retained artifacts and counterexamples—not production credentials, exploit code or secret access paths. Synthetic failing-policy modes are isolated from production BMO.

**Prior-work disclosure.** BMO and prior SoundGate/EvidenceGraph mechanisms are preexisting; this sprint's novel artifacts are the typed audit, classical comparison harness, causal simulation and formalized evidence-verdict program.

**LLM usage statement.** AI assistants contributed to brainstorming, implementation, validation and drafting. Reported counts come from retained outputs and tests; authors remain responsible for verifying released artifacts and the manuscript.
