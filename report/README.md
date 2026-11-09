# Swarm Witness Evidence for Agent Authorization

The paper studies how observations warrant claims about agent authorization and committed effects. It develops an evidence qualification protocol, demonstrates an application-owned effect witness and compares conclusions under partial observation.

## Current paper

| Artifact | Role |
| --- | --- |
| [Final manuscript Markdown](Swarm_Witness_Final_Submission.md) | Canonical paper source |
| [Research PDF](Swarm_Witness_Final_Submission.pdf) and [DOCX](Swarm_Witness_Final_Submission.docx) | Research layout |
| [Official-template PDF](Swarm_Witness_Templated_Submission.pdf) and [DOCX](Swarm_Witness_Templated_Submission.docx) | Apart Research template layout |
| [Templated Markdown](Swarm_Witness_Templated_Submission.md) | Generated manuscript mirror |
| [Abstract](ABSTRACT.md), [body](body.md) and [limitations](LIMITATIONS_DUAL_USE.md) | Generated extracts from the canonical manuscript |
| [Slides](slides/Swarm_Witness_Slides.pdf) and [figures](slides/figures/) | Current deck. The guide figure is generated from the manuscript table. |

Edit `Swarm_Witness_Final_Submission.md` to change the paper. Install Pandoc and LibreOffice, then build both layouts and refresh the Markdown extracts from the repository root:

```bash
python -m pip install -e '.[paper]'
bash scripts/build_submission_variants.sh
```

The official-template layout uses the committed `official-template.docx`. Both layouts contain the same scientific text.

## Results and sources

- [Comparative tables](bounded_comparison_v1/TABLES.md) and [per-case ledger](bounded_comparison_v1/ledger.csv)
- [EvidenceGraph adapter conformance](external_calibration_v1/EVENT_CAPABILITY.md)
- [Sources and research artifacts](SOURCES.md)
- [Evidence access and reproduction](../evidence/ACCESS.md)
- [Prior work and preexisting code](../PREEXISTING.md)
- [Submission metadata](SUBMISSION_FORM.md) and [publication checklist](../CHECKLIST.md)

## Portable bundle

```bash
bash scripts/pack_review_bundle.sh
```

This generates `dist/swarm-witness-review-bundle.zip` containing the current paper, build inputs, study sources and retained evidence.

## Earlier material

[The archive index](archive/README.md) links to pinned earlier paper variants and slides. Use the current paper above for the present argument and results.
