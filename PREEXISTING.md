# Preexisting material

Swarm Witness builds on established authorization mechanisms, external research artifacts and an existing repository scaffold. This document identifies those inputs and the scope of the code used in the experiments.

## External research and mechanisms

| Input | Source | Use in Swarm Witness |
| --- | --- | --- |
| SoundGate recovery barrier | [SoundGate paper and code](https://github.com/sajjadanwar0/soundgate-paper), revision `656840348dcf9660f8db7add9f3ca9f794a55926` | Pinned re-execution of the recovery-barrier study and structured Claim, Run and Finding records |
| EvidenceGraph receipt attribution | [EvidenceGraph](https://github.com/crashlabsai/evidencegraph), stress-harness revision `a5ea5c9947039009ca795275d834be7b61069080` | Confirmation of the published stress behavior and evidence-adapter experiments |
| BMO retained-grant implementation | [BMO](https://github.com/instagrim-dev/bmo), revision `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe` | Selected decision-model observations and a native first-edit ledger comparison |
| Classical access-control mechanisms | Reference-monitor, recovery-before-admission and durable grant-table designs | Explicit comparison baselines |
| Evidence semantics | Possible-world reasoning under compatible observations | A three-way qualification rule and bounded formal checks |

[Source pins](artifacts/pins.yaml) retain revisions, content digests and artifact locations. EvidenceGraph's cited baseline is `efbd4192767672e2ca3634c9ebe9d9a3c98fcddd`; the runnable stress harness uses the later revision shown above. These mechanisms and their published failure modes originate in the cited work.

## BMO comparison scope

The decision-model protocol in `experiments/r3/cases.yaml` requires matching observations from both systems. BMO package-level test counts do not supply per-case decisions. Missing matching observations leave the comparative finding unresolved.

The separate `r3-ledger-claim-v1` protocol compares the preexisting BMO method `ClaimOrdinaryRetainedGrantFirstEditTx` with the in-repository SQLite `ClassicalLedgerGate`. Its test bridge is stored under `experiments/r3/ledger_claim_v1/` and runs against a disposable copy of the pinned BMO tree. The bridge does not modify production BMO authorization behavior.

The comparison covers selected transactional claim, rollback and reopen properties. An offline SQLite stand-in can emit inspectable traces, but cannot establish a native BMO result. Native re-execution requires access to the pinned BMO source; retained evidence is available through [the evidence access guide](evidence/ACCESS.md).

### BMO source surfaces

The consulted implementation and test surfaces include:

- `internal/sessioncompaction/ordinary_retry_retained_grant_owner_witness_test.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_test.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_race_test.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_census.go`
- `internal/sessioncompaction/ordinary_retry_retained_grant_post_chain.go`
- `internal/agent/ordinary_retry_retained_grant_projection.go`
- `internal/agent/ordinary_retry_retained_grant_projection_test.go`
- `internal/app/ordinary_retry_retained_grant_early.go`
- `internal/app/ordinary_retry_retained_grant_projection.go`
- `internal/db/migrations/20261101033000_ordinary_retry_retained_grant_transfers.sql`

## Repository scaffold

The October 25 scaffold supplied `protocol/`, `scenarios/`, `agents/`, `monitors/`, `analysis/`, `paper/`, `scripts/check.sh`, the MIT license, CI configuration and initial repository documentation.

The claim schema, evidence qualification implementation, application witness, comparison harnesses and synthetic evidence-sufficiency protocols are maintained in this repository. The synthetic protocols use authored inputs; they are distinct from the external source re-executions above.
