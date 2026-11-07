# Swarm Witness: What Do Agent-Safety Mechanisms Actually Establish?

**Apart Research — Swarm Alignment sprint (weekend 2026-11-06 … 2026-11-08)**  
**Tracks:** 3 (Strengthening Agent Infrastructure) and 4 (Multi-Agent Oversight and Control)

After matching policy, observations, trust assumptions, durability, and
enforcement coverage, which claimed benefits of agent-safety mechanisms remain?
Swarm Witness is an executable claim-audit kit that pins third-party artifacts,
states claim cards, runs discriminating checks against classical baselines
(treated as questions under test), and records fail-closed labels. On three
pinned targets: SoundGate recovery-barrier (R1) **reproduced**; EvidenceGraph
receipt stress (R2) **reproduced**; BMO retained-grant vs ClassicalGate (R3)
**unresolved** (matched decision-model comparison incomplete). Claimed weekend
contributions are pinned replications (R1/R2) and the audit kit; a
methodological reduction finding is not claimed without matched comparison.

## Submission PDF

Apart-ready report: [`report/Swarm_Witness_Apart_Submission.pdf`](report/Swarm_Witness_Apart_Submission.pdf) (form field cheat sheet: [`report/SUBMISSION_FORM.md`](report/SUBMISSION_FORM.md)).

## Preexisting material

Scaffold, monitors, and the external BMO tree predate this sprint. Full disclosure: [`PREEXISTING.md`](PREEXISTING.md).

## Schema (v2)

Typed validators in `swarm_witness.schema`: `validate_claim` → `Claim`, `validate_run` → `Run`, `validate_finding` → `Finding`. Strings are nonblank; `assumptions` / `run_ids` / `supporting_observation_refs` are non-empty `list[str]` (strings are not coerced to character lists). `Finding.label` ∈ `CONCLUSION_LABELS`; `Run.execution_status` ∈ `assigned|attempted|completed|failed|unrun|missing`; `Finding.basis` ∈ `authored|computed`.

Evidence layout: `evidence/<rN>/runs/*.json`, `evidence/<rN>/findings/*.json`, convenience mirrors `summary.json` / `result.yaml`. Regenerate the index from findings:

```bash
python scripts/check_evidence.py --write-index
python scripts/check_evidence.py
```

## Quick verification (local kit)

```bash
cd /path/to/swarm-witness
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
python scripts/validate_claims.py
python scripts/check_evidence.py
wc -w report/ABSTRACT.md   # expect 150–250
```

Decisive acceptance probes covered by the suite include ClassicalGate
always-deny control and evidence-consistency negatives (reproduced cannot rest
on unresolved-only support).

## Reproduction experiments

Run from the repository root with dependencies installed (R1 needs `git`,
`curl`, `cargo`, `rustc`; R2 needs `uv`; R3 needs `go` and a checkout of BMO at
`BMO_ROOT`, default `/Users/user1/Documents/dev/bmo`).

| Experiment | Command | Output |
| --- | --- | --- |
| R1 SoundGate | `bash experiments/r1/run_r1.sh` | `evidence/r1/findings/`, `summary.json` |
| R1 inspect raw | `gzip -dc evidence/r1/raw.json.gz > evidence/r1/raw.json` | local `raw.json` (gitignored) |
| R2 EvidenceGraph | `bash experiments/r2/run_r2.sh` | `evidence/r2/findings/`, `summary.json` |
| R3 matched compare | `python3 experiments/r3/compare.py` | `evidence/r3/findings/r3-f-comparison.json` |
| R3 Go tests (metadata) | `bash experiments/r3/run_bmo_tests.sh` | `evidence/r3/bmo_go_test.log` |
| R3 ledger-claim-v1 | `python3 experiments/r3/ledger_claim_v1/run_matched.py --run-id <id>` | `evidence/r3/ledger_claim_v1/<id>/` |

Derived protocol **r3-ledger-claim-v1** (ClassicalLedgerGate vs BMO
`ClaimOrdinaryRetainedGrantFirstEditTx`) lives under
[`experiments/r3/ledger_claim_v1/`](experiments/r3/ledger_claim_v1/). Native pin
bridge evidence at `evidence/r3_ledger_claim_v1/` is labeled
**`classical_baseline_matches`**. Legacy decision-model R3 is unchanged
(`unresolved`). Offline L1 stand-in traces stay inspectable-only
(`native_bmo=false`).

Pre-submit checklist for the Apart form: [`CHECKLIST.md`](CHECKLIST.md).
