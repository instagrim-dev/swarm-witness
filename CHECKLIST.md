# Publication checklist

Title: **Swarm Witness Evidence for Agent Authorization**  
Author: **Jonathan Maye-Hobbs**  
Affiliation: **Independent**

The [canonical manuscript](report/Swarm_Witness_Final_Submission.md) supplies both the research and official-template layouts. [Report contents](report/README.md) identifies the current artifacts.

## Manuscript requirements

| Item | Requirement |
| --- | --- |
| Abstract | 150–250 words |
| Body | No more than eight pages before references and appendices in the submission layout |
| Front matter | Consistent title, author and affiliation in every current export |
| Results | Separate public, application and calibration denominators; quantitative statements agree with retained evidence |
| References | Research sources and reused mechanisms attributed |
| Appendix | Limitations and dual-use considerations included |
| Disclosures | Prior work and the required LLM usage statement included |

The [Apart Swarm Alignment 2026 submission page](https://apartresearch.com/sprints/swarm-alignment-2026) provides the venue instructions.

## Artifact checks

- [ ] The research and official-template PDF and DOCX files contain the same manuscript.
- [ ] The abstract and other Markdown extracts agree with the canonical source.
- [ ] Tables, headings, links and page breaks are readable in both PDF layouts.
- [ ] The report index links to current artifacts and identifies earlier material as archived.
- [ ] A fresh portable bundle contains the current paper, its build inputs and the evidence referenced by the paper.
- [ ] The intended readers can access the repository or the generated portable bundle.

## Validation commands

Run from the repository root after installing the development and paper dependencies, Pandoc, and LibreOffice as described in [README.md](README.md):

```bash
python -m pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py
bash scripts/build_submission_variants.sh
bash scripts/pack_review_bundle.sh
```

The generated bundle is `dist/swarm-witness-review-bundle.zip`. [Evidence access](evidence/ACCESS.md) describes the retained studies and any additional sources required for re-execution.
