# Swarm Witness: What Do Agent-Safety Mechanisms Actually Establish?

**Apart Research — Swarm Alignment sprint (weekend 2026-11-06 … 2026-11-08)**  
**Tracks:** 3 (Strengthening Agent Infrastructure) and 4 (Multi-Agent Oversight and Control)

Multi-agent safety mechanisms are often described as novel when they implement durable authorization, crash-consistent recovery, or evidence packaging. We ask: after matching policy, observations, trust assumptions, durability, and enforcement coverage, which claimed benefits remain? We contribute Swarm Witness, an executable claim-audit method that pins third-party artifacts, states precise claim cards, runs discriminating checks against classical baselines, and records fail-closed conclusion labels. On three pinned targets we obtain: SoundGate recovery-barrier (R1) reproduced; EvidenceGraph receipt stress (R2) reproduced; BMO retained-grant vs ClassicalGate (R3) assumption_dependent. Auditors should publish matched baselines and labels, not treat branding as establishment.

## Submission PDF

Apart-ready report: [`report/Swarm_Witness_Apart_Submission.pdf`](report/Swarm_Witness_Apart_Submission.pdf) (form field cheat sheet: [`report/SUBMISSION_FORM.md`](report/SUBMISSION_FORM.md)).

## Preexisting material

Scaffold, monitors, and the external BMO tree predate this sprint. Full disclosure: [`PREEXISTING.md`](PREEXISTING.md).

## Schema (v2)

Typed validators in `swarm_witness.schema`: `validate_claim` → `Claim`, `validate_run` → `Run`, `validate_finding` → `Finding`. Strings are nonblank; `assumptions` / `run_ids` / `supporting_observation_refs` are non-empty `list[str]` (strings are not coerced to character lists). `Finding.label` ∈ `CONCLUSION_LABELS`; `Run.execution_status` ∈ `assigned|attempted|completed|failed|unrun|missing`; `Finding.basis` ∈ `authored|computed`.

## Quick verification (local kit)

```bash
cd /path/to/swarm-witness
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # or requirements as documented in pyproject
pytest tests/test_schema.py -v
# Full suite / claim+evidence scripts migrate in later tasks
```

## Reproduction experiments

Run from the repository root with dependencies installed (R1 needs `git`, `curl`, `cargo`, `rustc`; R2 needs `uv`; R3 needs `go` and a checkout of BMO at `BMO_ROOT`, default `/Users/user1/Documents/dev/bmo`).

| Experiment | Command | Output |
| --- | --- | --- |
| R1 SoundGate | `bash experiments/r1/run_r1.sh` | `evidence/r1/summary.json`, `result.yaml` |
| R2 EvidenceGraph | `bash experiments/r2/run_r2.sh` | `evidence/r2/summary.json`, `result.yaml` |
| R3 BMO Go tests | `bash experiments/r3/run_bmo_tests.sh` | `evidence/r3/bmo_go_test.log` |

Pre-submit checklist for the Apart form: [`CHECKLIST.md`](CHECKLIST.md).
