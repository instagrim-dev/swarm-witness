# Appendix A. Limitations and dual-use / ethical considerations

**Evidence and domain limits.** The study makes bounded claims about the specified artifacts, synthetic schedules and formal assumptions. The BMO result evaluates an L1 transactional owner and selected projections, not full execution or BMO runtime safety. The simulator's principals share deterministic event scheduling and modeled state; they are not live model agents, and they do not establish emergent coordination. The general proofs assume authenticated compatible-world evidence and an actual world within the compatible set. Incomplete or falsified evidence invalidates those premises. Neither the qualitative taxonomy nor the finite exhaustive checker proves those premises for external datasets.

**Possible adversarial use.** The same audits that expose stale-authority, receipt-replay or delegation errors could help an attacker discover where a system trusts old evidence. We release bounded test schedules, retained artifacts and explanatory counterexamples, rather than production credentials, exploit code against deployed agents, or secret access paths. Synthetic failing-policy modes are deliberately isolated from production BMO. Reviewers can reproduce the modeled outcomes without interacting with external systems.

**Prior-work disclosure.** The existing BMO engine and prior SoundGate/EvidenceGraph mechanisms are preexisting contributions; this sprint's novel artifacts are the typed audit, classical comparison harness, causal simulation and formalized evidence-verdict program. The publication does not claim ownership of the third-party repairs.

**LLM usage statement.** AI assistants contributed to research brainstorming, implementation, validation scripts and draft writing. The reported experimental counts are taken from retained program outputs and tests; the submitting authors remain responsible for verifying the released artifacts and manuscript.

