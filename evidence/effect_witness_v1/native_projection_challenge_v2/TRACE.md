# Challenge v2 before and after

The v1 ledger is not rewritten. A rejection is not an epistemic verdict.

| Case | Historical Swarm Witness | Current Swarm Witness | Comparator | Reason |
| --- | --- | --- | --- | --- |
| sink-misbound | supported | unresolved | unresolved | misbound_id |
| sink-spoofed | supported | unresolved | unresolved | rejected_authenticity |
| sink-unauthenticated | supported | unresolved | unresolved | rejected_authenticity |
| sink-stale | unresolved | unresolved | unresolved | none |
| sink-run-mismatch | supported | unresolved | unresolved | run_mismatch |
| sink-actor-mismatch | supported | unresolved | unresolved | partial_identity |
| sink-object-mismatch | supported | unresolved | unresolved | partial_identity |
| sink-mapped-actor-mismatch | supported | unresolved | unresolved | partial_identity |
| mixed-unknown-authorization | entrypoint_rejected:aew-v1-h-authority-current:mixed-unknown-authorization: duplicate or blank ledger event | rejected: aew-v1-h-authority-current:mixed-unknown-authorization: duplicate or blank ledger event | unresolved | none |
| coverage-conflict | unresolved | unresolved | unresolved | none |
| coverage-duplicate | entrypoint_rejected:duplicate content identity: src-aew-v1-rec-coverage-authority-current-copy | supported | supported | exact_duplicate_not_independent |
| sink-unknown-subject | entrypoint_rejected:aew-v1-h-authority-current:sink-unknown-subject: ledger/event subject_class mismatch on aew-v1-event-authority-current | rejected: aew-v1-h-authority-current:sink-unknown-subject: ledger/event subject_class mismatch on aew-v1-event-authority-current | unresolved | none |
| coverage-operation-mismatch | unresolved | unresolved | unresolved | none |
| coverage-interval-outside | unresolved | unresolved | unresolved | none |
| coverage-withheld | entrypoint_rejected:src-aew-v1-rec-coverage-authority-current: pinned bytes require access_level public_bytes | rejected: src-aew-v1-rec-coverage-authority-current: pinned bytes require access_level public_bytes | unresolved | none |
| clean-positive | supported | supported | supported | none |
