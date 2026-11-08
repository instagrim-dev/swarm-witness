# Frozen comparison

The public layer is the twelve incident claims at two stages. The controlled layer is four claims about the held LessWrong record and the released step-1 signature extract. Lineage qualifications are a third denominator.

The LessWrong post and its appendix are one public record. Original OpenAI transcripts and Hugging Face platform logs are listed as unavailable. They are not upgrade gates, and they do not make this comparison fail. A `blocks_upgrade` slot prevents support only when the audit holds that slot and the slot is not the verifying observation.

Naive PASS accepts report assertions, including an overread that treats the reproduction post as certification of the original compromise. The strong checker and Swarm Witness do not. The reproduction release statement is supported as one record. The original incident is not certified. Beating the naive baseline is not a superiority claim.

On the public layer the naive baseline has 24 unsupported supports and decisive coverage 0 (0 of 2). The strong checker has 0 unsupported supports and decisive coverage 1 (2 of 2). Swarm Witness matches the strong checker on every public cell. The always-unresolved reference also has decisive coverage 0. On the controlled layer the naive baseline has 2 unsupported supports and 2 supports of false propositions. The strong checker and Swarm Witness have 0 of each, and they abstain on the certification claim and on the held `blocks_upgrade` slot. Record requests are 0. Processing time is the measured duration of the scoring pass stored with the run.

C03 and C05 stay refuted. Their Swarm Witness conclusion class is `refuted`, not `failed_enforcement`. The effect stays unobserved, and enforcement and effect origin stay undetermined. The unauthenticated displayed command on C03 is withheld, so stage A does not count it as an admitted support. The rate scalars above did not change.

```bash
PYTHONPATH=src python3 experiments/incident_audit/compare.py
PYTHONPATH=src python3 -m pytest -q tests/test_comparison_freeze.py tests/test_incident_audit.py tests/test_provenance_contract.py
```
