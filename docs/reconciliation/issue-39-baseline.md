# Issue #39 reconciliation baseline

Selected base: `3b138e4bd78cc7d1de4389a6415322e5d48a9002` (current `main`).
That commit is the merge of PR #45. It includes PR #33 at `8e8a093` and PR #36 at `e7a25eb`.

Integration route: PR #25, commit `1e0a08e2cd0b876b9faa6381985102edf3ffa792`, based on `08fca16`.
PR #25 described the pre-#33 corpora (causal 8/16, R5 v2 13/26). Those counts are stale.
This reconciliation keeps the post-#33 corpora.

PR #34 (`cursor/incident-property-graph-cf57`) was compared and not consumed.
It is the separate #29 property-graph protocol. It touches `artifacts/pins.yaml` and `evidence/index.yaml`, which this branch also edits for `multi_agent_sim` and `r5_v3`. #35, #37, and #40–#42 are not implemented here.

## Incident evidence standard

For the 2026 OpenAI–Hugging Face agent-swarm incident, the evidence standard is the public LessWrong reproduction:

Palan, M., Chute, C., Kim, M. and Van Roy, B. (2026). *OpenAI-HuggingFace: A Reproduction & Lessons for Alignment Testing*. https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment

Original agent transcripts and platform logs are unavailable. Acceptance and qualification use that reproduction and the executable protocols in this package. No criterion requires the withheld originals. Native BMO re-execution remains a separately stated access-dependent route and was not required for this replay.

## Historical protocols preserved

Claim ids and evidence trees below were not replaced.

| Protocol | Claim id | Identity kept |
| --- | --- | --- |
| Four-world checker | `taxonomy_theory` | `theory/check_taxonomy.py`, `evidence/taxonomy_theory/`. 4 worlds, 2,646 checks, zero violations. |
| Causal simulator | `causal_swarm` | `src/swarm_witness/causal_simulator.py` still commits when the policy allows. Evidence `evidence/causal_swarm/`. 9 schedules / 18 arms, including `foreign_receipt_replay` and `foreign_receipt_absent`. |
| R5 v2 causal matrix | `r5_v2` | `experiments/r5_v2/`, `evidence/r5_v2/`. 14 scenarios / 28 arms. Not registered as `r5_v3`. |
| R5 v1 | `r5` | `evidence/r5/`, source version `swarm-witness-r5-v1`. |
| R1, R2, R3, R3-L1, R4 | `r1`, `r2`, `r3`, `r3_ledger_claim_v1`, `r4` | Existing evidence trees. |

`report/Swarm_Witness_Final_Submission.pdf` is byte-identical to `main` (git blob `67431e9be2e632d6b2409c266eccbe14a190213b`). Editable submission markdown states the LessWrong evidence standard. PR #33's receipt isolation, R3-D worked example, semantic corrections, and `scripts/publish_followon_evidence.py` stay. PR #36's templated submission and slides stay. That helper mirrors only the historical causal and R5 v2 artifact summaries. It is not the generator for the eight-world checker, `multi_agent_sim`, or `r5_v3`.

Claim sentences in `claims/causal_swarm.yaml` and `claims/r5_v2.yaml` still said eight and thirteen schedules after PR #33 had already retained nine and fourteen. Those sentences now name the retained corpora. Claim ids, run ids, and per-arm observations were not relabeled.

## Protocols added beside the historical ones

- Eight-world checker: `src/swarm_witness/formal/`, `experiments/taxonomy_formal/`. 8 worlds. C7 keeps a supported decision property beside a refuted joint property. This does not replace `taxonomy_theory`.
- Settlement ledger: claim `multi_agent_sim`, protocol `multi-agent-sim-v1`. Reference `commit_effect` can refuse after allow. 13 cases; missing evidence 4, failed enforcement 5, supported 9.
- Wider R5: claim `r5_v3`, protocol `r5-swarm-audit-v3`. 40 cases, 7 coverage dimensions, 12 concurrency rows, 3 held-out rows. Concurrency pins come from this ledger (PR #23 semantics, source commit `28b3642`), not from the #15, #19, or #21 snapshots.

## What the regenerated runner changed

`experiments/causal_swarm/run.py` is shared with `experiments/r5_v2/run.py`. The fail-closed contract now requires the post-#33 ids. A fresh run matches the retained per-arm observations. Counts stay 9/18 and 14/28. The artifact summaries gained `expected_arm_count`, `declared_scenario_ids`, `errors`, and `denominators`. Evidence trees under `evidence/causal_swarm/` and `evidence/r5_v2/` were not rewritten.

Empty manifests, missing declared cases, and mismatched expected observations fail explicitly. The omitted id is named. The cases that were present stay in the result list. A wrong pinned-trace digest or a missing pin name fails the same way.

## Replay

Dependencies used for the clean-directory replay: Python 3.12.3, PyYAML 6.0.1, pytest 9.2.0. No private BMO tree.

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_research_followons.py tests/test_formal_epistemics.py tests/test_multi_agent_sim.py tests/test_r5_v3_swarm_audit.py tests/test_evidence_consistency.py
PYTHONPATH=src python3 experiments/causal_swarm/run.py --output /tmp/replay-causal
PYTHONPATH=src python3 experiments/r5_v2/run.py --output /tmp/replay-r5
python3 theory/check_taxonomy.py
PYTHONPATH=src python3 experiments/taxonomy_formal/run.py --json
PYTHONPATH=src python3 experiments/multi_agent_sim/run.py --evidence-dir /tmp/replay-mas
PYTHONPATH=src python3 experiments/swarm_r5_v3/run.py --evidence-dir /tmp/replay-r5v3
PYTHONPATH=src python3 scripts/check_evidence.py
```

Clean-directory replay of the packed bundle, 80 tests passed, then the runners above:

- causal `causal-swarm-v1`: 9 schedules, 18 arms, passed
- R5 v2 `r5-v2-causal-matrix`: 14 scenarios, 28 arms, passed
- four-world checker: 4 worlds, 2,646 checks, passed
- eight-world checker: 8 worlds, passed, including the C7 counterexample suite
- `multi_agent_sim`: 13 cases, passed; missing evidence 4, failed enforcement 5, supported 9
- `r5_v3`: 40 cases, passed
- `scripts/check_evidence.py`: OK
- `foreign_receipt_replay` broken-local: decision allow, receipt `receipt-a1`, 1 unauthorized effect
- `foreign_receipt_absent` broken-local: decision deny, no receipt, 0 unauthorized effects
- neither schedule delivers a qualifying local view to C

Replayed bundle sha256: `ebf7ff86a37686f34a42ce09b45e790cde5d8cedb832672a587084d863be0a09`.

That digest is the zip extracted for the commands above. The zip committed with this note is rebuilt afterward so the note is inside it. Recompute `sha256sum artifacts/swarm-witness-review-bundle.zip` for the committed digest. The pull request records that value.
