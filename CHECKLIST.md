# Apart final submission checklist

Sprint: Swarm Alignment 2026 — weekend **2026-11-06 … 2026-11-08**  
Form: https://apartresearch.com/sprints/swarm-alignment-2026 (user submits; agent does not)

| Item | Status | Notes |
| --- | --- | --- |
| Official template PDF | Done | `report/Swarm_Witness_Templated_Submission.pdf` (+ filled `.docx`); research layout still at `Final_Submission.*` |
| Slides | Done | `report/Swarm_Witness_Slides.pdf` (8 slides) for form Slides field |
| ≤8 pages before refs/appendices | Done | Templated/research PDFs within budget; body through Discussion under 8 |
| Abstract 150–250 words | Done | `report/ABSTRACT.md` — 213 words |
| Author and affiliation | Done | Jonathan Maye-Hobbs; Affiliation: Independent |
| Judge evidence access | **User** | Repo is **private**; either grant judge read access, publish a mirror, or attach `artifacts/swarm-witness-review-bundle.zip` |
| Limitations / Dual-Use appendix | Done | `report/LIMITATIONS_DUAL_USE.md` included in PDF |
| Preexisting marked | Done | `PREEXISTING.md` + README pointer |
| Evidence-backed results | Done | Original R1–R5 plus 9/18 causal-simulator, 14/28 R5-v2 and 2,646 finite-model checks; inspect retained traces |
| Labels honest (v2) | Done | R1 external re-execution, R2 later-harness confirmation, R3-D unresolved, R3-L1 bounded match; R4/R5 synthetic, R5-v2 independent trace check, formal results conditional |
| R1 raw inspectability | Done | `evidence/r1/raw.json.gz` committed; `raw.json` gitignored |
| Review ZIP self-consistent | Done | `bash scripts/pack_review_bundle.sh`; clean extract runs `pytest` + ACCESS commands |
| Links work | Verify at submit | Template copy URL, GitHub URL, local PDF / zip path |

## Remaining author-controlled steps

1. **Judge access** — attach `artifacts/swarm-witness-review-bundle.zip` on the form, **or** grant temporary read on `instagrim-dev/swarm-witness`, **or** publish a public mirror.
2. **Submit** — upload PDF via Apart form before AoE deadline; optional 3–5 min video.

## Verification commands (run before submit)

```bash
source .venv/bin/activate
pytest -q
python scripts/validate_claims.py
python scripts/check_evidence.py --write-index
python scripts/check_evidence.py
wc -w report/ABSTRACT.md
bash scripts/pack_review_bundle.sh
ls -la report/Swarm_Witness_Final_Submission.pdf \
  artifacts/swarm-witness-review-bundle.zip evidence/r1/raw.json.gz
```

Decisive probes already in `pytest`: ClassicalGate always-deny mutation control;
evidence-consistency negatives; R4 misbound cannot be supported; R3 identical-wrong
input / undeclared-step controls; R5 broken-allow does not commit effects.

Research follow-ons #10–#12 have published source, traces and tests under `experiments/`, `theory/`, `claims/`, `evidence/` and `docs/`; the six core acceptance probes are in `tests/test_research_followons.py`.
