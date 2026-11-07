# Swarm Witness | Research follow-ons #10-#12 and revised submission

Delivered in the main Swarm Witness repository with versioned follow-on protocols. Existing R1/R2/R3/R4/R5 observations and findings remain unchanged. The revised official-submission-named PDF and DOCX are published under `report/`.

## Delivered research

- **#10, causal interleaving simulator:** `src/swarm_witness/causal_simulator.py`,
  `experiments/causal_swarm/scenarios.json`, `run.py`, nine deterministic
  schedules and eighteen policy traces. Agent-local snapshots, causal events and
  application effects are separate modeled stores. A second algorithm audits
  the effect log and reconstructs the permission invariant from event history.
- **#11, R5 v2 coverage:** `experiments/r5_v2/cases.json`, `run.py`, fourteen
  fixed cases across nine declared dimensions and twenty-eight policy arms, with
  a separately implemented oracle. Version 2 is additive, not a reinterpretation
  of R5 v1. Baseline policy: zero unauthorized effects; deliberately faulty local
  policy: nine unauthorized effects and ten incorrect decisions.
- **#12, formal evidence theory:** `theory/THREE_WAY_EVIDENCE_THEORY.md` states
  conditional soundness and refinement theorems with proofs and a countermodel.
  `theory/check_taxonomy.py` exhausts four possible worlds and yields 2,646
  checked finite instances, independent of the production conclusion classifier.

The final research manuscript is `report/Swarm_Witness_Final_Submission.pdf`,
with an editable DOCX and Markdown version. The PDF has six pages total,
including references and the mandatory limitations/dual-use appendix.

## Reproduce locally

Requires Python 3.11+ and pytest; PyYAML is used only by the publication helper.
From this delivery root:

```bash
PYTHONPATH=src python -m pytest -q tests/test_research_followons.py
PYTHONPATH=src python experiments/causal_swarm/run.py --output artifacts/causal_swarm_v1
PYTHONPATH=src python experiments/r5_v2/run.py --output artifacts/r5_v2
python theory/check_taxonomy.py
python scripts/publish_followon_evidence.py
```

Expected: seven tests passing; 9/18 and 14/28 case/arm counts; 2,646 finite checks
with zero violations. Files in `artifacts/` are retained outputs from these
commands; each trace contains actor observations, authority history and a
separate model effect ledger. The `claims/` and `evidence/` trees use the
Swarm Witness Claim/Run/Finding field contract for integration.

## Evaluation boundary

The simulator checks *specified event interleavings* on a modeled ledger. It is
not a real distributed-agent network or a proof that production BMO execution is
safe. The mathematics proves the proposition-verdict laws under authenticated,
compatible observation semantics, not authenticity of external evidence.

## Release integration

The new `src/`, `experiments/`, `tests/`, `theory/`, `claims/`, `evidence/`, `artifacts/` and `report/` entries are committed to main. `evidence/index.yaml` includes the new distinct finding slots. The review ZIP packer includes the research modules and their retained traces, and excludes its previous ZIP from staging.

**Submission gate:** Author: Jonathan Maye-Hobbs; Affiliation: Independent.
Ensure Apart judges can access the report and evidence. The new PDF uses the official
recommended section structure; importing it into the official Google Docs
presentation template, if enforced, is a separate formatting step.
