## Appendix A Limitations and dual use

**Observation and trust boundaries.** The application experiment uses a real local worker and SQLite sink under a controlled harness. Its observer reads committed state separately from the actor transcript, but shares an operating-system user with the worker. Direct database modification by a process with that user's privileges is outside the declared boundary. The experiment establishes the retained local executions; it does not establish adversarial isolation of telemetry or observation authenticity in an external service.

**Inference and generalization.** The finite semantics assumes a valid abstraction and an actual world compatible with admitted observations. Neither a digest nor a finite check proves these assumptions for new records. Authored schedules, public-record warrants, and retrospective adapter cases cover specified behaviors rather than a representative sample of agent deployments. The application histories, public-record comparison, and EvidenceGraph translation use separate denominators. Agreement among methods is not an independent validation of their shared premises.

**Incident scope.** The public reproduction [8] is distinct from the application witness. The original incident's transcripts and platform logs are not available in this package. The study makes no detection or prevention claim about that incident. Supplemental synthetic studies and label replays remain evidence about their declared inputs, rather than observations of emergent agent coordination or successful behavior in an external deployment.

**Potential misuse.** Descriptions of stale authority, receipt reuse, and incomplete evidence could help identify weak audit boundaries. The application experiments use controlled records and local effects. They contain no production credentials or secret access paths. Their purpose is to make incorrect authorization conclusions observable and reproducible.

**Prior material.** SoundGate, EvidenceGraph, and BMO predate this protocol. Their mechanisms and retained source revisions are attributed in the repository's preexisting-material record. The protocol, controlled comparison, and evidence representations are distinguished from those underlying systems.

## LLM Usage Statement

AI assistants contributed to research design, implementation, validation scripts, and manuscript drafting. The author is responsible for the claims, interpretation, and released artifacts.
