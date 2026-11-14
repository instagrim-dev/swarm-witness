# An intact actor log still needs admission

An actor log can already be intact. Does that record justify the effect conclusion, or does a consumer still have to admit the record as evidence?

Track 2 of the AI x Epistemics sprint asks what is missing before a record of what an agent did can be trusted. This note scores three consumers on the retained Swarm Witness packets. It does not replace Table 2 or Table 2b.

The intact-actor consumer supports `P_effect` whenever a requested-command record is locally held, custody intact, marked bound, and carrying public bytes. It has 26 *unsupported supports*, 4 supports of a false proposition, 22/24 correct decisive conclusions, and 0 correct abstentions.

The retained-verdict consumer reads the historical Swarm Witness label. It has 11 *unsupported supports*, 0 supports of a false proposition, 24/24 correct decisive conclusions, and 13 correct abstentions.

The admission consumer runs the invariant checker on the same records. It has 0 *unsupported supports*, 0 supports of a false proposition, 24/24 correct decisive conclusions, and 24 correct abstentions.

All 11 retained *unsupported supports* are `withheld_misbound` packets whose controlled proposition holds. Across them, deciding records sum to 0. 11 of them contain an actor record that meets the intact-actor test and that the admission rule marks misbound. 4 have no effect row. 7 have an effect row that is withheld, not locally held, and labeled supports.

One further `withheld_misbound` packet, aew-v1-h-local-pass-broader-effect, has that withheld effect-row shape. The retained label there is unresolved, and the controlled proposition is false. A withheld row labeled supports does not by itself account for the eleven.

On these 48 packets, subject class on a held deciding effect, or the zero-row absence census, matches the projection and the invariant checker. Rejecting the misbound actor probe leaves the actor log able to support. A held effect labeled supports, without subject class, still supports the false proposition.

The 48 packets remain four views of twelve histories. This ladder is not the SoundGate transfer test. BMO is not re-executed. The current evaluator replay stays a separate table.

## Which check is carrying the warrant

The same packets can be scored by smaller stop-rules. Counts are *unsupported supports*, supports of a false proposition, correct decisive conclusions, and correct abstentions.

| Stop-rule | Unsupported support | False-proposition support | Correct decisive | Correct abstention |
| --- | ---: | ---: | ---: | ---: |
| Intact actor, unless every such actor is the misbound probe | 14 | 3 | 22/24 | 12 |
| Held deciding effect whose own label says supports | 2 | 2 | 14/24 | 24 |
| Held deciding effect, read subject class, no absence census | 0 | 0 | 16/24 | 24 |
| That support label, or the zero-row absence census | 2 | 2 | 22/24 | 24 |
| Subject class, or the zero-row absence census | 0 | 0 | 24/24 | 24 |
| Full projection, including scope, binding, and census | 0 | 0 | 24/24 | 24 |

Subject class, or the absence census, mismatches the full projection on 0 packets. The projection mismatches the invariant checker on 0 packets. Inside this set, scope, parent binding, and the non-zero census change no verdict.

Subject class alone leaves 8 warranted supports unresolved: both sink views of the four histories with no effect row. The support label, or the absence census, still supports the false proposition on 2 packets, both sink views of `aew-v1-h-local-pass-broader-effect`.

Rejecting the misbound probe, and otherwise trusting the actor log, still has 14 *unsupported supports*. On these packets that stop-rule makes the same calls as supporting whenever any record passes the deciding-premise check: the two rules differ on 0 packets.

## Where those idle checks fire

The sixteen-case challenge is a separate denominator: sixteen mutations of one discriminating-readback packet. It is not folded into the 48.

Subject class or the absence census has 9 *unsupported supports*, 2/2 correct decisive conclusions, and 5 correct abstentions. The projection has 0 *unsupported supports*, 2/2 correct decisive conclusions, and 14 correct abstentions. The projection mismatches the invariant checker on 0 probes and the challenge warrant on 0.

The probes where subject class supports and the projection stays unresolved:

- Scope, run id: sink-run-mismatch
- Scope, operation: coverage-operation-mismatch
- Scope, interval: coverage-interval-outside
- Binding: sink-actor-mismatch, sink-object-mismatch, sink-mapped-actor-mismatch
- Unknown subject beside an authorized sink: mixed-unknown-authorization
- Disagreeing census: coverage-conflict
- Withheld census: coverage-withheld

An exact duplicate census stays supported for both rules. A sink whose only subject is unknown stays unresolved for both. Misbinding, a spoofed line, an unauthenticated line, and a stale sink are already rejected by the deciding-premise check.

## SoundGate transfer

SoundGate R1 is 153 cuts under 3 policies, 459 retained rows, separate from the 48 and the 16. An intact-run rule has 143 *unsupported supports* on the restriction claim and 151 on availability. Reading the effect field matches that field. It is not a second adjudicator.
