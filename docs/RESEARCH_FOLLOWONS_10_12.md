# Swarm Witness | Research follow-ons #10-#12 and revised submission

Delivered in the main Swarm Witness repository with versioned follow-on protocols. Existing R1/R2/R3/R4/R5 observations and findings remain unchanged. The revised official-submission-named PDF and DOCX are published under `report/`.

## Delivered research

- **#10, causal interleaving simulator:** `src/swarm_witness/causal_simulator.py`,
  `experiments/causal_swarm/scenarios.json`, `run.py`, eight deterministic
  schedules and sixteen policy traces. Agent-local snapshots, causal events and
  application effects are separate modeled stores. A second algorithm audits
  the effect log and reconstructs the permission invariant from event history.
- **#11, R5 v2 coverage:** `experiments/r5_v2/cases.json`, `run.py`, thirteen
  fixed cases across nine declared dimensions and twenty-six policy arms, with
  a separately implemented oracle. Version 2 is additive, not a reinterpretation
  of R5 v1. Baseline policy: zero unauthorized effects; deliberately faulty local
  policy: nine unauthorized effects and ten incorrect decisions.
- **#12, formal evidence theory:** `theory/THREE_WAY_EVIDENCE_THEORY.md` states
  conditional soundness and refinement theorems with proofs and a countermodel.
  `theory/check_taxonomy.py` exhausts four possible worlds and yields 2,646
  checked finite instances, independent of the production conclusion classifier.

The final research manuscript is `report/Swarm_Witness_Final_Submission.pdf`,
with an editable DOCX and Markdown version. The PDF has six pages total,
including references and the mandatory limitations/dual-use appendix. That PDF
is unchanged by the later protocol integration below.

## Later protocols, kept separate

Three later protocols sit beside the historical follow-ons. They do not reuse
their claim ids or evidence directories.

- **Eight-world formal checker** (`src/swarm_witness/formal/`,
  `experiments/taxonomy_formal/`). The four-world checker
  `theory/check_taxonomy.py`, claim `taxonomy_theory`, and
  `evidence/taxonomy_theory/` stay as the historical protocol.
- **Settlement-ledger simulator** (`src/swarm_witness/multi_agent_sim/`,
  claim `multi_agent_sim`). A reference allow can still be refused at
  `commit_effect`. The historical `causal_simulator.py` has no such gate: an
  allow commits. Claim `causal_swarm` and `evidence/causal_swarm/` stay.
- **R5-v3** (`experiments/swarm_r5_v3/`, claim `r5_v3`, `evidence/r5_v3/`).
  This is not the historical `r5_v2` causal matrix (13 scenarios / 26 arms).
  Concurrency rows are pinned to the integrated settlement ledger. The #15,
  #19, and #21 snapshots are not current.

## Reproduce locally

Requires Python 3.11+ and pytest. PyYAML is the `pyyaml` project dependency
used by `scripts/check_evidence.py`. From this delivery root:

```bash
PYTHONPATH=src python -m pytest -q tests/test_research_followons.py
PYTHONPATH=src python experiments/causal_swarm/run.py --output artifacts/causal_swarm_v1
PYTHONPATH=src python experiments/r5_v2/run.py --output artifacts/r5_v2
python theory/check_taxonomy.py
PYTHONPATH=src python experiments/taxonomy_formal/run.py
PYTHONPATH=src python experiments/multi_agent_sim/run.py
PYTHONPATH=src python experiments/swarm_r5_v3/run.py
PYTHONPATH=src python scripts/check_evidence.py
```

Expected: the historical follow-on tests passing; 8/16 and 13/26 case/arm
counts; 2,646 four-world checks with zero violations; the eight-world checker
passing; the settlement-ledger protocol passing; the r5_v3 protocol passing;
evidence consistency OK. `scripts/publish_followon_evidence.py` is not part of
this tree. The historical `claims/` and `evidence/` records are the published
follow-on results; `scripts/check_evidence.py` is the command that checks them.
Files in `artifacts/causal_swarm_v1/` and `artifacts/r5_v2/` are retained
outputs of the historical protocols. The `claims/` and `evidence/` trees use
the Swarm Witness Claim/Run/Finding field contract.

## Evaluation boundary

The simulator checks *specified event interleavings* on a modeled ledger. It is
not a real distributed-agent network or a proof that production BMO execution is
safe. The mathematics proves the proposition-verdict laws under authenticated,
compatible observation semantics, not authenticity of external evidence.

## Release integration

The new `src/`, `experiments/`, `tests/`, `theory/`, `claims/`, `evidence/`, `artifacts/` and `report/` entries are committed to main. `evidence/index.yaml` includes the new distinct finding slots. The review ZIP packer includes the research modules and their retained traces, and excludes its previous ZIP from staging.

**Submission gate:** Fill the real author names/affiliations and ensure Apart
judges can access the report and evidence. The new PDF uses the official
recommended section structure; importing it into the official Google Docs
presentation template, if enforced, is a separate formatting step.
