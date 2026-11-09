## Appendix A Limitations and dual use

**Observation and trust boundaries.** The application experiment uses a real local worker and SQLite sink under a controlled harness. Its observer reads committed state separately from the actor transcript, but shares an operating-system user with the worker. Direct database modification by a process with that user's privileges is outside the declared boundary. The experiment establishes the retained local executions; it does not establish adversarial isolation of telemetry or observation authenticity in an external service.

**Inference and generalization.** The finite semantics assumes a valid abstraction and an actual world compatible with admitted observations. Neither a digest nor a finite check proves these assumptions for new records. Authored schedules, public-record warrants, and retrospective adapter cases cover specified behaviors rather than a representative sample of agent deployments. The application histories, public-record comparison, and EvidenceGraph translation use separate denominators. Agreement among methods is not an independent validation of their shared premises.

**Incident scope.** The public reproduction [8] is distinct from the application witness. The original incident's transcripts and platform logs are not available in this package. The study makes no detection or prevention claim about that incident. Supplemental synthetic studies and label replays remain evidence about their declared inputs, rather than observations of emergent agent coordination or successful behavior in an external deployment.

**Potential misuse.** Descriptions of stale authority, receipt reuse, and incomplete evidence could help identify weak audit boundaries. The application experiments use controlled records and local effects. They contain no production credentials or secret access paths. Their purpose is to make incorrect authorization conclusions observable and reproducible.

**Prior material.** SoundGate, EvidenceGraph, and BMO predate this protocol. Their mechanisms and retained source revisions are attributed in the repository's preexisting-material record. The protocol, controlled comparison, and evidence representations are distinguished from those underlying systems.

### Sprint contribution and prior work

Before the November 6–8, 2026 sprint, Swarm Witness consisted of an October 26 UTC repository scaffold and a preliminary paired-oversight research direction. Its README, license, setup check, and placeholder research directories contained no runnable experiment, implemented research protocol, retained measurement, or manuscript. The sprint produced the evidence-sufficiency protocol and qualifier, application-owned SQLite effect witness, separate classical contract reference, native BMO ledger and settlement comparisons, adversarial and representation studies, formal checks, retained results, and paper. BMO's underlying authority and settlement implementation, SoundGate, and EvidenceGraph are prior work, not sprint inventions. The contribution claimed here is the new contract extraction, experimental comparisons, and analysis of observations sufficient to warrant authorization conclusions. Bounded contract portability does not establish full-system equivalence or external empirical transfer.

## LLM Usage Statement

The operator developed the preexisting BMO authority and settlement implementation and orchestrated the comparisons, the retained measurements, and which conclusions the evidence was allowed to support. AI assistants contributed counterfactual challenge of the claims, research design, implementation, validation scripts, and manuscript drafting. The author is responsible for the claims, interpretation, and released artifacts.
