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

The native layer distinguishes unsupported support from support of a false proposition. The retained comparison has eleven Swarm Witness outputs that exceed their incomplete-evidence warrants even though the underlying controlled propositions are true. The current evaluator replay does not replace that result. The invariant checker has no unsupported supports in this layer, and both methods recover all twenty-four warranted decisive conclusions. Unconditional abstention avoids unsupported support but recovers none of those decisive conclusions.

Public-record warrants establish what the available material supports. Where the underlying event cannot be verified, they are not substituted for hidden truth. The EvidenceGraph composition has a separate protocol and denominator in `report/external_calibration_v1/EVENT_CAPABILITY.md`.

## Later evaluator replay

On 2026-11-08 the retained native comparison was separated from the current evaluator. Table N reads `experiments/effect_witness/historical_qualification_packets_v1.json` and still reports Swarm Witness unsupported support 11 and correct decisive 24/24. Table N2 scores the same packet files with the current evaluator. After `experiments/effect_witness/run.py` in an extracted bundle, `render_bounded_comparison.py` still reported those retained counts.

The advertised local commands were run in `/tmp/sw-review-extract-g5c/swarm-witness-review-bundle` with `PYTHONPATH=src` and the source checkout's existing virtualenv. No new virtualenv was created. Private access was not used. Every advertised command exited 0, including `pytest -q` with 376 passed. The witness replay did not change the retained 11 or the 24 correct decisive conclusions. `check_evidence.py --write-index` and comparison processing times stayed in the extract.

## Clean extract of 33715e5

`dist/swarm-witness-review-bundle.zip` was built from commit `33715e5c790437261c25f0559016928f43ed9baf` and extracted to `/tmp/sw-review-extract-g56/swarm-witness-review-bundle`. A new virtualenv was created there. Private access was not used. The command log is `clean_extract_2026-11-08.log`.

Pytest reported 386 passed. The fresh effect-witness run wrote to `/tmp/swarm-witness-effect-g56` and did not replace the retained packets. After `render_bounded_comparison.py`, Table N still showed Swarm Witness unsupported support 11 and correct decisive 24/24. The six-case ledger compare and both settlement compares, including S01–S09, exited 0 with `agreement: matched`. The other advertised runners exited 0.

`scripts/build_submission_variants.sh` exited 0 in that extract. An earlier invocation, whose `python3` was outside a virtualenv and had no `python-docx`, exited 1. That failure is an interpreter mismatch, not a second paper. The LibreOffice render from the activated extract is 9 pages for the research PDF, with references on page 8, and 10 pages for the templated PDF, with references on page 9. Both contain the seven-negative-controls paragraph.

## Clean extract of fa8d215

The source is commit `fa8d215b09c99292b0cb2e4e924fcb7c9c9e27f3`, packed from `git archive` of that commit. The archive digest is `3e83785dbe8a0e5bc5442741b4a2a2f279378c3c05b162c42a3724e422c89887`. The review bundle digest is `513544dfc1a577b28e67aa3680ff74387f5ae548f8791305900e2325babd2d63`. Both are recorded in `clean_extract_fa8d215.json`, and the command log is `clean_extract_fa8d215.log`.

Every advertised command exited 0. Pytest reported 386 passed. Table N still showed Swarm Witness unsupported support 11 and correct decisive 24/24. The six-case ledger compare and both settlement compares exited 0 with `agreement: matched`. The LibreOffice build produced a 9-page research PDF, with references on page 8, and a 10-page templated PDF, with references on page 9. Both contain the seven-negative-controls paragraph.
