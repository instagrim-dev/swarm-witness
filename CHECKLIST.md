# Apart pre-submission checklist (v2)

Sprint: Swarm Alignment 2026 — weekend **2026-11-06 … 2026-11-08**  
Form: https://apartresearch.com/sprints/swarm-alignment-2026 (user submits; agent does not)

| Item | Status | Notes |
| --- | --- | --- |
| Official template PDF | Done | `report/Swarm_Witness_Apart_Submission.pdf`; Google Docs copy URL in `report/SOURCES.md` if judges require exact chrome |
| ≤8 pages before refs/appendices | Done | PDF ~6 pages incl. appendix; body through Discussion under 8 |
| Abstract 150–250 words | Done | `report/ABSTRACT.md` — verify with `wc -w report/ABSTRACT.md` |
| Authors + affiliations | **User** | Left blank in `report/SUBMISSION_FORM.md` — do not invent; confirm before submit |
| Judge evidence access | **User** | Repo is private; attach `dist/swarm-witness-review-bundle.zip` (R4/R5 re-runnable) or grant read access — see `evidence/ACCESS.md` |
| Limitations / Dual-Use appendix | Done | `report/LIMITATIONS_DUAL_USE.md` included in PDF |
| Preexisting marked | Done | `PREEXISTING.md` + README pointer |
| No fabricated numbers | Done | Metrics from `evidence/r*/`; `validate_claims.py` + `check_evidence.py` |
| Labels honest (v2) | Done | R1/R2/R4/R5 `reproduced`; R3 decision-model `unresolved`; R3-L1 `classical_baseline_matches` (bounded) |
| R1 raw inspectability | Done | `evidence/r1/raw.json.gz` committed; `raw.json` gitignored |
| Links work | Verify at submit | Template copy URL, pinned git remotes, local PDF path |

## Verification commands (run before submit)

```bash
source .venv/bin/activate
pytest -v
python scripts/validate_claims.py
python scripts/check_evidence.py --write-index
python scripts/check_evidence.py
wc -w report/ABSTRACT.md
ls -la report/Swarm_Witness_Apart_Submission.pdf evidence/r1/raw.json.gz
```

Decisive probes already in `pytest`: ClassicalGate always-deny mutation control;
evidence-consistency negatives (reproduced + unresolved-only support must fail).
