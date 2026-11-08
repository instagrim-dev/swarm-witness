# Portable transaction and settlement contract

This report is generated from retained rows. The comparison commands are compare-only. They do not re-execute BMO, and the fixture-authored settlement rows are not a live model edit.

The same author implemented both arms. That is a separate implementation, not independent adjudication. Agreement on these cases is bounded conformance. It is not full-system equivalence, and it does not measure the subordinate supervisor or signed delegation at the architecture-context pin.

| Pin | Role | Revision |
| --- | --- | --- |
| Architecture context | Supervisor and delegation surfaces, not measured by S01–S09 | `e0038cc48872b274c22deaed8e24236530e9821e` |
| Ledger measurement | T01–T06 claim contract | `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe` |
| Settlement measurement | S01–S09 terminal-record contract | `c8297333b3bf31ded96ca0e8b39c531d3bcea97f` |

Another implementation can adopt the contract below. This measurement does not certify an unrelated deployment.

## Obligations

- Identity and scope binding: a terminal record names the claim's call. A call that belongs to another case is a cross-case input and is rejected.
- One-use claim: the six-case ledger consumes the retained-grant claim. A later claim on the spent grant is outside this settlement table.
- Transactional failure: a refused settlement does not insert a settlement row.
- Terminal-record qualification: applied evidence binds the tool, mutation, and artifact. Definite no-effect binds the tool and a source receipt.
- Refusal state: the committed claim remains, and effect-applied stays unresolved.
- Unresolved outcome: a missing, misordered, misbound, or contradictory terminal record does not become definite no-effect.

## Stage table

The initial settlement run contains S01 and S02. The controls run contains nine cases, including those two. Do not add the denominators. The ledger run contains six cases and 22 paired steps. A fresh compare of those retained rows still matches. Re-qualifying native BMO from the bridge files beside the comparator does not: bridge hash mismatch for bmo_adapter_test.go: file≠manifest. The retained receipt is not rewritten by this report.

| Run | Case | Arm | Stage | Contract disposition | Effect-applied | Resolving record |
| --- | --- | --- | --- | --- | --- | --- |
| controls | S01 | classical | claim | committed | unresolved | step 3 unresolved to supported |
| controls | S01 | classical | settlement | applied | supported | step 3 unresolved to supported |
| controls | S01 | bmo | claim | committed | unresolved | step 3 unresolved to supported |
| controls | S01 | bmo | settlement | applied | supported | step 3 unresolved to supported |
| controls | S02 | classical | claim | committed | unresolved | step 3 unresolved to refuted |
| controls | S02 | classical | settlement | not_entered | refuted | step 3 unresolved to refuted |
| controls | S02 | bmo | claim | committed | unresolved | step 3 unresolved to refuted |
| controls | S02 | bmo | settlement | not_entered | refuted | step 3 unresolved to refuted |
| controls | S03 | classical | claim | committed | unresolved | none |
| controls | S03 | classical | settlement | refused | unresolved | none |
| controls | S03 | bmo | claim | committed | unresolved | none |
| controls | S03 | bmo | settlement | refused | unresolved | none |
| controls | S04 | classical | claim | committed | unresolved | none |
| controls | S04 | classical | settlement | refused | unresolved | none |
| controls | S04 | bmo | claim | committed | unresolved | none |
| controls | S04 | bmo | settlement | refused | unresolved | none |
| controls | S05 | classical | claim | committed | unresolved | none |
| controls | S05 | classical | settlement | refused | unresolved | none |
| controls | S05 | bmo | claim | committed | unresolved | none |
| controls | S05 | bmo | settlement | refused | unresolved | none |
| controls | S06 | classical | claim | committed | unresolved | none |
| controls | S06 | classical | settlement | refused | unresolved | none |
| controls | S06 | bmo | claim | committed | unresolved | none |
| controls | S06 | bmo | settlement | refused | unresolved | none |
| controls | S07 | classical | claim | committed | unresolved | none |
| controls | S07 | classical | settlement | refused | unresolved | none |
| controls | S07 | bmo | claim | committed | unresolved | none |
| controls | S07 | bmo | settlement | refused | unresolved | none |
| controls | S08 | classical | claim | committed | unresolved | none |
| controls | S08 | classical | settlement | refused | unresolved | none |
| controls | S08 | bmo | claim | committed | unresolved | none |
| controls | S08 | bmo | settlement | refused | unresolved | none |
| controls | S09 | classical | claim | committed | unresolved | none |
| controls | S09 | classical | settlement | refused | unresolved | none |
| controls | S09 | bmo | claim | committed | unresolved | none |
| controls | S09 | bmo | settlement | refused | unresolved | none |

S02 refutes only the effect-applied proposition. Refusal leaves that proposition unresolved and leaves the committed claim in place.
