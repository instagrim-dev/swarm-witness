# Reproducing the bounded comparison

The comparison keeps public-record warrants, controlled histories, and application executions separate. The native layer evaluates evidence packets over twelve retained application histories; each history has four observation conditions.

## Inputs and outputs

| Layer | Inputs | Unit |
| --- | --- | --- |
| Public record | `claims/incident_claims_v1.yaml`, `experiments/incident_audit/excerpts_v1.yaml`, `experiments/incident_audit/adjudication_v1.yaml` | Twelve claims at two evidence stages |
| Controlled comparison | `experiments/incident_audit/comparison/` | Four claims over three histories |
| Native application | `evidence/effect_witness_v1/packets/`, `experiments/effect_witness/native_warrants_v1.yaml` | Forty-eight packets over twelve executions |

`TABLES.md` presents each denominator. `ledger.csv` retains method outputs, warrants, and available controlled truth. `source_sha256.json` identifies the retained inputs. `native_matched_methods.json` identifies the native methods and packet count.

## Retained evidence comparison

From the repository root:

```bash
python scripts/render_bounded_comparison.py
```

The public and controlled layers read retained comparison results. The native layer evaluates the current invariant checker on the same packet records as the retained Swarm Witness outputs. Rendering does not turn those records into additional application executions.

## Fresh application execution

```bash
PYTHONPATH=src python experiments/effect_witness/run.py /tmp/swarm-witness-effect
```

The output directory contains actor and service records, cold readback, evidence packets, qualifications, and the named witness. The comparison renderer reads the published evidence tree by default. A fresh replay in a separate directory is an inspectable replication; it does not replace that tree automatically.

## Public and controlled evaluation

```bash
PYTHONPATH=src python experiments/incident_audit/compare.py
python scripts/render_bounded_comparison.py
```

These commands regenerate comparison outputs in the checkout. Use a disposable checkout to compare them with the retained publication files. Processing time can vary without changing the discrete conclusions.

## Interpretation

The native layer distinguishes *unsupported support* from support of a false proposition. The retained comparison has eleven Swarm Witness outputs that exceed their incomplete-evidence warrants even though the underlying controlled propositions are true. The current evaluator replay does not replace that result. The invariant checker has no *unsupported supports* in this layer, and both methods recover all twenty-four warranted decisive conclusions. Unconditional abstention avoids *unsupported support* but recovers none of those decisive conclusions.

Public-record warrants establish what the available material supports. Where the underlying event cannot be verified, they are not substituted for hidden truth. The EvidenceGraph composition has a separate protocol and denominator in `report/external_calibration_v1/EVENT_CAPABILITY.md`.

## Later evaluator replay

On 2026-11-08 the retained native comparison was separated from the current evaluator. Table N reads `experiments/effect_witness/historical_qualification_packets_v1.json` and still reports Swarm Witness *unsupported support* 11 and correct decisive 24/24. Table N2 scores the same packet files with the current evaluator. After `experiments/effect_witness/run.py` in an extracted bundle, `render_bounded_comparison.py` still reported those retained counts.

The advertised local commands were run in `/tmp/sw-review-extract-g5c/swarm-witness-review-bundle` with `PYTHONPATH=src` and the source checkout's existing virtualenv. No new virtualenv was created. Private access was not used. Every advertised command exited 0, including `pytest -q` with 376 passed. The witness replay did not change the retained 11 or the 24 correct decisive conclusions. `check_evidence.py --write-index` and comparison processing times stayed in the extract.

## Clean extract of 33715e5

`dist/swarm-witness-review-bundle.zip` was built from commit `33715e5c790437261c25f0559016928f43ed9baf` and extracted to `/tmp/sw-review-extract-g56/swarm-witness-review-bundle`. A new virtualenv was created there. Private access was not used. The command log is `clean_extract_2026-11-08.log`.

Pytest reported 386 passed. The fresh effect-witness run wrote to `/tmp/swarm-witness-effect-g56` and did not replace the retained packets. After `render_bounded_comparison.py`, Table N still showed Swarm Witness *unsupported support* 11 and correct decisive 24/24. The six-case ledger compare and both settlement compares, including S01–S09, exited 0 with `agreement: matched`. The other advertised runners exited 0.

`scripts/build_submission_variants.sh` exited 0 in that extract. An earlier invocation, whose `python3` was outside a virtualenv and had no `python-docx`, exited 1. That failure is an interpreter mismatch, not a second paper. The LibreOffice render from the activated extract is 9 pages for the research PDF, with references on page 8, and 10 pages for the templated PDF, with references on page 9. Both contain the seven-negative-controls paragraph.

## Clean extract of fa8d215

The source is commit `fa8d215b09c99292b0cb2e4e924fcb7c9c9e27f3`, packed from `git archive` of that commit. The archive digest is `3e83785dbe8a0e5bc5442741b4a2a2f279378c3c05b162c42a3724e422c89887`. The review bundle digest is `513544dfc1a577b28e67aa3680ff74387f5ae548f8791305900e2325babd2d63`. Both are recorded in `clean_extract_fa8d215.json`, and the command log is `clean_extract_fa8d215.log`.

Every advertised command exited 0. Pytest reported 386 passed. Table N still showed Swarm Witness *unsupported support* 11 and correct decisive 24/24. The six-case ledger compare and both settlement compares exited 0 with `agreement: matched`. The LibreOffice build produced a 9-page research PDF, with references on page 8, and a 10-page templated PDF, with references on page 9. Both contain the seven-negative-controls paragraph.

## Clean extract of fde17ab

This section records a replay of commit `fde17ab15cbb92e23b93513a8a5c9486379f17c7`. It was added after that commit. It does not claim to have tested the commit that contains this paragraph.

The source archive digest is `3a29508cd299460470bc11183452d6b4dc343b7c1a0167443636d13de2a5c627`. The review-bundle digest is `47ac53340afb0cb611433f31f23e8862e56b9cfc94e23e5590f5ec772e29c658`. The archive contained no workbench directory, sqlite file, or `bmo_work` tree. The command log is `clean_extract_fde17ab.log`, and the digests are in `clean_extract_fde17ab.json`.

In `/tmp/sw-review-extract-fde17ab/swarm-witness-review-bundle`, a new virtualenv ran the advertised commands and the contract, challenge, and representation commands. Pytest reported 403 passed. That count is the count for this commit. It does not reuse the historical 386. Table N still showed Swarm Witness *unsupported support* 11 and correct decisive 24/24. Table N2 still showed 0 *unsupported supports*. The historical qualification packets, the v1 challenge ledger, and `heldout_v1/result.json` kept the same digests.

The six-case ledger compare exited 0 with `agreement: matched` and `validity: true`, and its printed label was `unresolved`. It rewrote the extract's `summary.json`: `native_bmo` became false and the qualification note was `bridge hash mismatch for bmo_adapter_test.go: file≠manifest`. That is a compare-only requalification of retained records, not a native Go re-execution. Native Go re-execution was not run. The two settlement compares exited 0 with `agreement: matched` and did not change their summary files. The contract report, challenge v2, and representation study wrote only under the temporary run directory.

The LibreOffice build in the extract produced a 9-page research PDF, with references on page 8, and a 10-page templated PDF, with references on page 9. The source commit was not pushed.

## Clean extract of b7319d8

This section records a replay of commit `b7319d89279c93648eca1cecb7032b618cd79498`. It was added after that commit. It does not claim to have tested the commit that contains this paragraph. It does not replace the `fde17ab` extract, and it does not reuse that extract's 403 passing tests. The earlier uncommitted notes about `9d3f2c5` were discarded. That pass stopped on page-inspection and slide-packaging setup, which is not an experimental result.

The source archive digest is `acd2b175f08969ceb0601e6e6912b4f17c449b2ceba3e956724786eaa20e42bf`. The review-bundle digest is `bf7e711a324ad8df6e9a6a3955ee54fa29d411b01450a53e9e223ec68b32f18d`. The archive contained no workbench directory, sqlite file, or `bmo_work` tree. The command log is `clean_extract_b7319d8.log`, and the digests are in `clean_extract_b7319d8.json`.

In `/tmp/sw-review-extract-b7319d8/swarm-witness-review-bundle`, a new virtualenv installed the declared `dev` and `paper` extras, including `pypdf`. Pytest reported 411 passed. The 48 packets remain four dependent views of twelve histories. This extract does not make those views independent. Table N still showed Swarm Witness *unsupported support* 11 and correct decisive 24/24. Table N2 still showed 0 *unsupported supports*, 0 unsupported refutations, 24/24 correct decisive, and 24 correct abstentions. The historical qualification packets, the v1 challenge ledger, and `heldout_v1/result.json` kept the same digests.

The six-case ledger compare exited 0 with `agreement: matched`, `validity: true`, and printed label `unresolved`. It rewrote the extract's `summary.json`: `native_bmo` became false and the qualification note was `bridge hash mismatch for bmo_adapter_test.go: file≠manifest`. That is a compare-only requalification of retained records, not a native Go re-execution. Native Go re-execution was not run. The two settlement compares exited 0 with `agreement: matched` and did not change their summary files. The contract report, challenge v2, and representation study wrote only under the temporary run directory. `heldout_pipeline_v1.py` was not run, because it rewrites the retained pipeline file.

The LibreOffice build in the extract produced a 9-page research PDF, with references on page 8, and a 10-page templated PDF, with references on page 9.
