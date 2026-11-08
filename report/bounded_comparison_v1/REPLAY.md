# Replay record

This file records what this environment actually reran on 2026-11-08. It is not a separate reviewer. Assistant agreement is not independent verification. Nothing was filed or resubmitted to Apart, Hugging Face, or any other external site. Private BMO access was not used. Original transcripts and platform logs were not fetched, and they were not treated as gates.

The extract contained the incident audit, provenance, telemetry, coordination, detection latency, effect witness, and evidence binding trees before any command ran. It was unpacked from `dist/swarm-witness-review-bundle.zip` to `/tmp/sw-review-extract-fad5/swarm-witness-review-bundle`. Commands ran in that directory, not in the source checkout. This machine did not have `python3-venv` until `python3.12-venv` was installed so the advertised virtualenv could be created. The venv then ran `pip install -e '.[dev]'`.

A source-tree run of `tests/test_comparison_freeze.py` rewrites `processing_time_seconds` because the comparison writer stores the measured scoring pass. That rewrite was restored from the frozen summary before the published tables were rendered again. The committed processing times are that restored pass. The headline counts did not change.

Every command below exited 0.

```bash
pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py
python3 experiments/r3/ledger_claim_v1/compare.py --run-dir evidence/r3/ledger_claim_v1/2026-11-07-ledger-v1-repair2
python3 experiments/evidence_sufficiency/run.py
python3 experiments/swarm_r5/run.py
PYTHONPATH=src python3 experiments/causal_swarm/run.py --output /tmp/causal-swarm-recheck
PYTHONPATH=src python3 experiments/r5_v2/run.py --output /tmp/r5-v2-recheck
python3 theory/check_taxonomy.py
PYTHONPATH=src python3 experiments/incident_audit/run.py
PYTHONPATH=src python3 experiments/incident_audit/compare.py
PYTHONPATH=src python3 experiments/provenance/qualify.py
PYTHONPATH=src python3 experiments/telemetry/qualify.py
PYTHONPATH=src python3 experiments/coordination/qualify.py
PYTHONPATH=src python3 experiments/detection_latency/run.py
PYTHONPATH=src python3 experiments/effect_witness/run.py
PYTHONPATH=src python3 experiments/evidence_binding/run.py
python3 scripts/render_bounded_comparison.py
PYTHONPATH=src python3 experiments/taxonomy_formal/run.py
PYTHONPATH=src python3 experiments/multi_agent_sim/run.py
PYTHONPATH=src python3 experiments/swarm_r5_v3/run.py
python scripts/check_evidence.py --write-index
python scripts/check_evidence.py
```

`pytest -q` reported 304 passed in 3.25s. The frozen comparison in the extract stayed `comparison_completed: true` and `superiority_claim: false`, with public unsupported supports naive 24, strong checker 0, and Swarm Witness 0. Controlled unsupported supports stayed naive 2 and strong checker 0. The extract's new processing times were not copied back. The effect-witness replay printed `aew-v1-local-control-pass-broader-effect`. Evidence binding printed `passed: true`. Provenance, telemetry, and coordination writers completed. Detection latency passed with `historical_latency_result_count` 0 and `withheld_latency_claim_count` 8. The four-world checker passed. The extract's table render exited 0 and still reported 24, 0, and 0. `check_evidence.py --write-index` ran only inside the extract.

The templated PDF built here is 8 pages, with References on page 7 and one Appendix A on page 8. The research PDF regenerated from `report/Swarm_Witness_Final_Submission.md` is 7 pages, with References on page 6 and one Appendix A on page 7. The templated DOCX and the templated Markdown each have one Appendix A heading and the same LessWrong reference.

A later pack of the review bundle includes this note. The commands above were not rerun after that pack. This note was not an input to them.

A later reconciliation, still on 2026-11-08, regenerated the bounded-comparison tables and the external-calibration reports from the current evaluators, shortened the abstract to 224 words, and rebuilt the research and templated DOCX and PDF. Nothing was filed or uploaded to Apart. Public unsupported supports stayed naive PASS 24, strong checker 0, and Swarm Witness 0. Native Table N stayed Swarm Witness 11 unsupported supports and correct decisive 24/24, strong invariant 0 and 24/24, and always-unresolved 0 and 0/24. Composed classifier–adapter agreement stayed 130/130. Incomplete population-detail rows are recorded as incomplete evidence, not as absence. The research PDF is 7 pages, with References and the Appendix A heading on page 6. The templated PDF is 9 pages, with References on page 7 and Appendix A starting on page 8.

```bash
python3 scripts/render_bounded_comparison.py
PYTHONPATH=src python3 experiments/external_calibration/run.py
python3 scripts/build_templated_submission.py
pandoc report/Swarm_Witness_Final_Submission.md -o report/Swarm_Witness_Final_Submission.docx
python3 -m pytest -q tests/test_bounded_comparison_publication.py tests/test_external_calibration_r2.py tests/test_comparison_freeze.py tests/test_incident_audit.py tests/test_evidence_binding.py tests/test_adapter_admission_uncertainty.py tests/test_provenance_contract.py tests/test_forensic_telemetry.py tests/test_latency_evidence.py tests/test_coordination_attribution.py tests/test_effect_witness.py tests/test_formal_epistemics.py
```

Those commands exited 0. The publication file reported its cases inside the 153 passed. The research and templated PDFs were printed from the regenerated HTML with headless Chrome.
