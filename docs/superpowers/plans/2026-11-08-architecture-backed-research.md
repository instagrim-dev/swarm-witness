# Architecture-backed Swarm Witness research implementation plan

> **For agentic workers:** use this plan task-by-task. If your CLI has an execution-plans or subagent-development workflow, use it without changing the approved scope or asking for another design selection. Each checkbox is a verifiable action; no new approval ceremony is required by this handoff.

**Goal:** make the implemented BMO architecture and the bounded portability of its measured contracts central to the paper, while completing narrowly scoped qualifier and representation follow-through.

**Architecture:** retain the current Python research package, native Go bridges and separately implemented SQLite comparator. Generate new reports from existing versioned evidence, add only the targeted qualifier corrections and a four-arm representation study, and regenerate publication outputs from one canonical manuscript.

**Tech stack:** existing Python 3.11+ project, pytest, PyYAML; existing Go only for optional native re-execution; existing Pandoc/LibreOffice publication path.

**Spec:** `01_FRAMING_DECISION.md` and `acceptance_criteria.json`. On adoption, place the decision at `docs/research/FRAMING_DECISION.md` and this plan at `docs/superpowers/plans/2026-11-08-architecture-backed-research.md`.

## Global constraints

Preserve the historical corpus and result versions. Keep the registered/current publication title. No method needs to win. No preexisting BMO mechanism becomes a new sprint invention. Architectural reuse, bounded contract portability and external empirical transfer remain separate. BMO is read-only in the default scope. Native result pins are `4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe` and `c8297333b3bf31ded96ca0e8b39c531d3bcea97f`, not the architecture-context pin `e0038cc48872b274c22deaed8e24236530e9821e`.

All new paths below are **proposed implementation destinations**, not a claim that they already exist. Existing paths are identified explicitly. Verify local deltas against `7468d2795d9c6500c68c5daf6a970ed765903885` before editing. Do not force-push, reset main, remove branches or overwrite unrelated changes.

## Review focus

1. Historical/current evaluator ambiguity: F1 and P1 must identify the result version beside every salient comparison.
2. Correctly rejected malformed input: Q1 must keep rejection distinct from epistemic abstention or refutation.
3. Label coupling: E1 must not call shared-adapter agreement independent correctness or held-out transfer.
4. Transfer scope inflation: C1 must distinguish measured settlement transactions from unmeasured broader BMO paths and live edits.
5. Reproduction scope: P1 must not convert retained-log comparison into a new Go execution or a prior receipt into certification of new code.

## Task F1 — Adopt the framing and evidence map

**Modify existing:** `report/Swarm_Witness_Final_Submission.md`, `README.md`, `PREEXISTING.md`.  
**Create:** `docs/research/FRAMING_DECISION.md`, `docs/research/claim_evidence_map.yaml`, `tests/test_research_framing.py`.

**Consumes:** this framing decision and the pinned sources in `source_manifest.json`.  
**Produces:** a stable claim map. Each entry has `claim_id`, `statement`, `status` (`preexisting_source`, `measured_contract`, `measured_application`, `inference`, `proposed`), `sources`, `scope`, and `not_established`. This is a documentation manifest, not a new runtime authority schema.

- [ ] Write `test_claim_map_covers_architecture_and_measured_contracts`: all H1–H4 appear; sources have exact refs; the broader supervisor/delegation entry is source-backed, not falsely tagged as measured by S01–S09.
- [ ] Write `test_manuscript_distinguishes_instrument_qualifier_and_versions`: the historical table is identified by evaluator/result version; the repair is a separate result; exact preexisting attribution is retained. Check the actual sections, not only keywords.
- [ ] Run `python -m pytest -q tests/test_research_framing.py`; confirm failures correspond to absent new documentation or stale prose, not environment errors.
- [ ] Adopt the thesis and roles from `01_FRAMING_DECISION.md`; use `MANUSCRIPT_INSERTS.md` as the editing starting point, not an additional independent manuscript. Make BMO's positive settlement result visible before discussing the evaluated qualifier's historical failure.
- [ ] Run the new tests and `tests/test_bounded_comparison_publication.py`, rebuild derived extracts when necessary, and commit only F1's intended delta under the workspace's integration instructions.

**Acceptance:** F1.1–F1.5. A human-readable narrative review is required in addition to automated text checks.

## Task C1 — Render the portable contract and evidence progression

**Read existing:** `experiments/r3/ledger_claim_v1/`, `experiments/r3/ledger_settlement_v1/`, `src/swarm_witness/classical_ledger_gate.py`, the two settlement run directories and ledger repair2.  
**Create:** `scripts/render_contract_portability.py`, `tests/test_contract_portability_report.py`, `report/architecture_contracts_v1/CONTRACT_MAP.md`, `report/architecture_contracts_v1/cases.json`.

**Consumes:** retained action/observation rows, each run's own cases and manifest, F1's claim map.  
**Produces:** `build_contract_report(repo_root: Path) -> dict[str, Any]`. Use existing settlement `load_cases`, `settlement_projection`, `contract_conformant`, `effect_verdict`, and `compare.evidence_stages` where appropriate; do not copy or rebuild the settlement runtime. Return metadata and per-case rows containing `protocol_id`, `run_id`, `case_id`, `arm`, `stage`, `contract_disposition`, `effect_applied_verdict`, `resolving_observation`, `scope` and `source_refs`.

- [ ] Write `test_report_preserves_protocol_and_run_identity`, `test_settlement_stage_is_the_discriminator`, and `test_refusal_has_no_settlement_and_keeps_claim`. Include missing/duplicate/cross-case rows as rejected report inputs.
- [ ] Run `python -m pytest -q tests/test_contract_portability_report.py tests/test_r3_ledger_settlement.py` and inspect the expected new-report failures.
- [ ] Implement the small report renderer from retained rows. Generate one stage table and one implementation map, not another simulator or authority abstraction.
- [ ] Include each adapter obligation: identity/scope binding, one-use claim, transactional failure behavior, terminal record qualification, refusal state, and unresolved outcome handling. Explain that another implementation can adopt the contract, while the present measurement does not certify an unrelated deployment.
- [ ] Run the tests and all three retained compare commands from `05_VERIFICATION.md`. Retain the generated source-pinned report and commit C1's delta.

**Acceptance:** C1.1–C1.5. Running these compare commands does not mean the Go bridge was re-executed.

## Task Q1 — Correct the qualifier on the separately published challenge

**Modify existing, only where the failing path requires it:** `src/swarm_witness/effect_witness/qualify.py`, directly related telemetry/property projection code, and narrowly relevant tests. Preserve the separately implemented comparator.  
**Create:** `experiments/effect_witness/native_projection_challenge_v2.py`, `tests/test_native_challenge_v2.py`, `evidence/effect_witness_v1/native_projection_challenge_v2/`.

**Consumes:** existing v1 `build_cases` and its sixteen warrants; v1 paired ledger; ordinary `evaluate_packet`.  
**Produces:** `evaluate_challenge_v2(repo_root: Path, output_dir: Path) -> dict[str, Any]`, with immutable input/warrant references and per-method `execution_status`, `epistemic_status` (nullable on invalid input), `raw_error`, `warrant`, `matches_warrant`, `admitted_ids`, `rejected_ids` and reasons. Do not silently map exceptions to correct abstentions.

- [ ] Write parametrized ordinary-entrypoint tests for the existing spoiled sink records. Assert that invalid supporting premises cannot produce decisive conclusions and that the clean case remains decisive.
- [ ] Write duplicate-versus-conflict and malformed-record tests. Keep the original 16 cases unchanged; any corrected well-formed control is a separately identified new test, not a hidden replacement.
- [ ] Run `python -m pytest -q tests/test_native_challenge_v2.py` and inspect actual failures.
- [ ] Repair the smallest admission/projection path that loses the relevant qualification. Do not use fixture IDs, expected outputs or comparator predictions as the implementation's oracle. Add a versioned v2 runner with explicit output path and no overwrite of v1.
- [ ] Run Q1's tests, the existing native coverage/projection/formal tests and the full 48-packet assertions. Publish both methods' complete challenge outcomes and the before/after causal traces. Commit the targeted delta.

**Acceptance:** Q1.1–Q1.5. A successful study may retain errors; an engineering closure may not claim those errors fixed merely because they were measured. Unresolved remaining defects must be reported explicitly rather than hidden by a test-suite pass.

## Task E1 — Measure raw and composed interfaces without circular claims

**Read existing:** `experiments/external_calibration/heldout_v1.py`, `heldout_v1.yaml`, `eg_evidence_adapter.py`, `eg_adapter_projector.py`, `r2_event_packets.py`, retained 70-row result and 130-packet capability report.  
**Create:** `experiments/external_calibration/representation_v2.py`, `representation_v2.yaml`, `tests/test_representation_v2.py`, `evidence/external_calibration_v1/representation_v2/`, `report/external_calibration_v1/REPRESENTATION.md`.

**Consumes:** exactly the retained 70 IDs/raw observations and baseline visible-assessor labels; the existing `composed_observations(claim, raw_observations)` API and both frozen classifier functions.  
**Produces:** `run_representation_study(repo_root: Path, output_dir: Path) -> dict[str, Any]` and a CLI accepting `--output`. Include four arms, original assessor labels, any available separately qualified warrant and its dependency disclosure, controlled truth, raw/projected records, per-arm cost and interventions. Do not feed labels or truth into the methods.

- [ ] Write `test_membership_preserves_the_seventy_case_slice`, `test_truth_or_scoring_label_changes_do_not_change_predictions`, and `test_projection_is_not_counted_as_an_independent_source`.
- [ ] Write `test_controls_preserve_historical_nominee_and_record_actual_status`. The original named refutation remains unresolved in its historical result. A v2 supplementary refuted representative must have a declared selection rule and be labelled as an inspected representative, not new held-out evidence.
- [ ] Run `python -m pytest -q tests/test_representation_v2.py` and inspect expected absent-runner failures.
- [ ] Add only the missing four-arm measurement, reusing the qualified adapter. Keep raw baselines intact. Count adapter cost within each composed arm; record supplied records and zero additional requests separately. Preserve known false-exclusivity assumptions.
- [ ] Run the study and tests; retain all 70 rows and intervention records. The two raw arms should reproduce their unchanged baseline. Treat composed recovery of the same adapter's labels as fidelity/representation recovery; disagreement is retained. Commit the full result without a win criterion.

**Acceptance:** E1.1–E1.5. This is a versioned extension of an already examined corpus, not a claim of independent external validation.

## Task P1 — Synthesize, export and replay the exact release

**Modify existing:** canonical manuscript, `README.md`, `PREEXISTING.md`, `evidence/ACCESS.md`, `tests/test_bounded_comparison_publication.py`; relevant existing report builders only as needed.  
**Create:** `tests/test_research_release_consistency.py` and an immutable replay receipt/log for the selected source revision.

**Consumes:** F1/C1 plus the actual completed Q1/E1 records; all historical result versions.  
**Produces:** canonical publication, generated Markdown extracts, two PDF/DOCX exports, selected result manifests, review ZIP and a complete AC delivery record.

- [ ] Write tests that distinguish historical/current/challenge rows, do not sum overlapping denominators, and keep native comparison versus re-execution language accurate.
- [ ] Integrate results using the question → observation → result → implication sequence. Complete at least two substantive conclusion paragraphs: the positive BMO contract result, then how the other studies qualify downstream conclusions and translation. No assessment grades or self-review prose in the paper.
- [ ] Run full tests, claim/evidence checks and report generation, then `bash scripts/build_submission_variants.sh`. Inspect both actual rendered PDFs for clipping, table readability, references, body limit and coherent continuity.
- [ ] Commit the selected source, pack from an archive of that exact revision, extract elsewhere and run all advertised local commands plus C1/Q1/E1. Preserve immutable source/bundle hashes and logs. Add the replay receipt in a later documentation-only commit that names the exact tested parent; do not imply it tested itself.
- [ ] Fill `delivery_record.template.json` with per-AC actual evidence. Report research outcome, engineering status, publication status and integration/push status separately.

**Acceptance:** P1.1–P1.5. A publication-only cut can omit uncompleted Q1/E1 implementation, but must identify them as uncompleted instead of claiming this full plan passed.

## Optional X1 — Actual transfer beyond the current measured boundary

Use the four X1 criteria only when the user elects a new empirical-transfer claim. Select one real executor/application integration, reuse BMO's existing ownership and settlement machinery, and obtain independent effect readback. Do not start a framework migration or a new simulator to satisfy the current framing. Native BMO access or execution failures are disclosed; they do not erase the retained comparison.

## Delivery sequence and integration ownership

F1 establishes terminology and evidence identity. C1, Q1 and E1 can run independently on that base. P1 integrates them. Only the integrator edits canonical manuscript and exports; only Q1 changes the native qualifier; E1 keeps its own runner/output tree. Use focused commits and the local repository's current instructions. Do not recreate superseded branch stacks.
