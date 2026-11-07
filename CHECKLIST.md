# Apart pre-submission checklist (v2)

Sprint: Swarm Alignment 2026 — weekend **2026-11-06 … 2026-11-08**  
Form: https://apartresearch.com/sprints/swarm-alignment-2026 (user submits; agent does not)

| Item | Status | Notes |
| --- | --- | --- |
| Official template PDF | Done | `report/Swarm_Witness_Apart_Submission.pdf`; Google Docs copy URL in `report/SOURCES.md` if judges require exact chrome |
| ≤8 pages before refs/appendices | Done | PDF 7 pages incl. appendix; body through Discussion under 8 |
| Abstract 150–250 words | Done | `report/ABSTRACT.md` — 152 words |
| Authors + affiliations | **User** | Left blank — do not invent; paste into form + report header before submit |
| Judge evidence access | **User** | Repo is **private**; either grant judge read access, publish a mirror, or attach `artifacts/swarm-witness-review-bundle.zip` |
| Limitations / Dual-Use appendix | Done | `report/LIMITATIONS_DUAL_USE.md` included in PDF |
| Preexisting marked | Done | `PREEXISTING.md` + README pointer |
| No fabricated numbers | Done | Metrics from `evidence/r*/`; `validate_claims.py` + `check_evidence.py` |
| Labels honest (v2) | Done | R1/R2 `reproduced` = pinned replication; R4/R5 `reproduced` = synthetic conformance; R3 decision-model `unresolved`; R3-L1 `classical_baseline_matches` (bounded) |
| R1 raw inspectability | Done | `evidence/r1/raw.json.gz` committed; `raw.json` gitignored |
| Review ZIP self-consistent | Done | `bash scripts/pack_review_bundle.sh`; clean extract runs `pytest` + ACCESS commands |
| Links work | Verify at submit | Template copy URL, GitHub URL, local PDF / zip path |

## Remaining user-only steps (agent cannot finish)

1. **Authors + affiliations** — confirm names; fill submission form and report header (`*[to be provided]*`).
2. **Judge access** — attach `artifacts/swarm-witness-review-bundle.zip` on the form, **or** grant temporary read on `instagrim-dev/swarm-witness`, **or** publish a public mirror.
3. **Submit** — upload PDF via Apart form before AoE deadline; optional 3–5 min video.

## Verification commands (run before submit)

```bash
source .venv/bin/activate
pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py --write-index
python scripts/check_evidence.py
wc -w report/ABSTRACT.md
bash scripts/pack_review_bundle.sh
ls -la report/Swarm_Witness_Apart_Submission.pdf \
  artifacts/swarm-witness-review-bundle.zip evidence/r1/raw.json.gz
```

Decisive probes already in `pytest`: ClassicalGate always-deny mutation control;
evidence-consistency negatives; R4 misbound cannot be supported; R3 identical-wrong
input / undeclared-step controls; R5 broken-allow does not commit effects.
