# Swarm Witness Evidence for Agent Authorization

Swarm Witness is a research implementation for determining whether an authorization or effect claim follows from the observations available to an auditor. It binds a claim to its execution context, evidence and assumptions, then returns **supported**, **refuted** or **unresolved**.

The central example is a local application whose URL allowlist passes while its own storage records a prohibited effect. With actor-only evidence, the claim that no unauthorized downstream effect committed remains unresolved. The bound application readback refutes that claim. The local control and the broader system property concern different boundaries.

## Paper

[Read the paper](report/Swarm_Witness_Final_Submission.pdf) · [Editable DOCX](report/Swarm_Witness_Final_Submission.docx) · [Markdown source](report/Swarm_Witness_Final_Submission.md)

[Official-template PDF](report/Swarm_Witness_Templated_Submission.pdf) · [Report contents and build instructions](report/README.md) · [Evidence access](evidence/ACCESS.md)

## Method

Each claim specifies the property, relevant execution, required observations and assumptions. Evidence records carry source and scope information to make the premises of each conclusion explicit. Qualification distinguishes the system's behavior from what the available evidence warrants.

The application experiment separates the actor's transcript from a read-only observer of the application's SQLite sink. Controlled histories and evidence conditions make the consequences of withholding, duplicating or misbinding observations inspectable.

## Results

| Study | Result | Scope |
| --- | --- | --- |
| Application effect witness | Twelve histories and four evidence conditions separate a passing local control from authorization of a downstream effect. | Local controlled application with a SQLite sink and cold readback. |
| Native method comparison | Across 48 packets, Swarm Witness produces 11 unsupported supports and the invariant checker produces none. Both identify all 24 warranted decisive conclusions. | The same retained records, evaluated against separate evidence-stage warrants. |
| Public evidence comparison | Swarm Witness and the invariant checker agree on all 24 conditions: 22 warranted abstentions and two warranted decisive conclusions. | Twelve claims about the public reproduction record, each evaluated at two evidence stages. |

A true proposition can still be unsupported by the available evidence. The native comparison identifies that failure in the current Swarm Witness implementation; the experiments do not establish an advantage over the invariant checker.

[Comparative tables](report/bounded_comparison_v1/TABLES.md) retain the separate denominators and per-method results. [EvidenceGraph conformance results](report/external_calibration_v1/EVENT_CAPABILITY.md) describe the additional adapter study and its inference boundary.

## Reproduce

Python 3.11 or later is required. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py
python experiments/effect_witness/run.py /tmp/swarm-witness-effect
```

The application replay writes its observations and findings to the supplied directory. [Evidence access](evidence/ACCESS.md) describes the other studies and the pinned source access needed for native BMO re-execution.

Publication builds require Pandoc, LibreOffice, and the paper dependencies. Build the paper and a portable source-and-evidence bundle with:

```bash
python -m pip install -e '.[paper]'
bash scripts/build_submission_variants.sh
bash scripts/pack_review_bundle.sh
```

The bundle is generated at `dist/swarm-witness-review-bundle.zip`.

## Repository map

| Directory | Contents |
| --- | --- |
| `report/` | Current manuscript, exports and comparative tables |
| `src/swarm_witness/` | Evidence qualification and experimental implementation |
| `experiments/` | Study protocols, runners and controlled inputs |
| `evidence/` | Retained runs, summaries and findings |
| `claims/` | Claim definitions |
| `artifacts/` | Raw traces and source pins |
| `tests/` and `theory/` | Implementation checks and finite-model arguments |
| `report/archive/` | Pinned links to earlier papers and presentations |

## Attribution

Author: Jonathan Maye-Hobbs. Affiliation: Independent.

[Preexisting material](PREEXISTING.md) identifies the external mechanisms, source revisions and code used in the studies. [Sources](report/SOURCES.md) lists the research references and report template. The repository is distributed under the [MIT license](LICENSE).
