# Sources and research artifacts

## Research references

The [canonical manuscript](Swarm_Witness_Final_Submission.md) contains the paper's bibliography. The following source records connect those references to the retained experiments.

| Source | Retained use | Repository record |
| --- | --- | --- |
| SoundGate, *A Restart Is Not Permission* | Recovery-barrier re-execution | [Source pins](../artifacts/pins.yaml), [R1 evidence](../evidence/r1/) |
| EvidenceGraph, *Receipt Possession Is Not Event Attribution* | Stress-harness confirmation and adapter conformance | [Source pins](../artifacts/pins.yaml), [R2 evidence](../evidence/r2/), [event-level results](external_calibration_v1/EVENT_CAPABILITY.md) |
| BMO retained-grant implementation | Selected decision-model and first-edit ledger comparisons | [Preexisting material](../PREEXISTING.md), [R3 evidence](../evidence/r3/) |
| Palan, Chute, Kim and Van Roy, *OpenAI-HuggingFace A Reproduction and Lessons for Alignment Testing* | Public reproduction evidence and claim qualification | [Public source](https://www.lesswrong.com/posts/fMnC6ZD37qrnZAFYz/openai-huggingface-a-reproduction-and-lessons-for-alignment), [comparison tables](bounded_comparison_v1/TABLES.md) |

The LessWrong reproduction post and its appendix belong to one public source record. The released reproduction provides evidence about its own setup and observations. Original incident transcripts and platform logs are not present in this repository.

## Current experiment records

| Study | Protocol or inputs | Results |
| --- | --- | --- |
| Application effect witness | [Experiment](../experiments/effect_witness/), [evidence-stage warrants](../experiments/effect_witness/native_warrants_v1.yaml) | [Retained evidence](../evidence/effect_witness_v1/), [comparative tables](bounded_comparison_v1/TABLES.md) |
| Public claim comparison | [Incident audit](../experiments/incident_audit/), [claim definitions](../claims/incident_claims_v1.yaml) | [Retained comparison](../evidence/incident_comparison_v1/), [per-case ledger](bounded_comparison_v1/ledger.csv) |
| EvidenceGraph adapter conformance | [Calibration implementation](../experiments/external_calibration/) | [Event-level results](external_calibration_v1/EVENT_CAPABILITY.md), [retained outputs](../evidence/external_calibration_v1/) |
| Finite evidence semantics | [Four-world checker](../theory/), [eight-world checker](../experiments/taxonomy_formal/) | [Four-world evidence](../evidence/taxonomy_theory/), [formal implementation](../src/swarm_witness/formal/) |
| Earlier controlled studies | [Experiments](../experiments/) | [Evidence index](../evidence/index.yaml) |

The comparison reports preserve each study's denominator. Source hashes and revisions are retained in [the artifact pins](../artifacts/pins.yaml) and the study-specific manifests.

## Report template

The official Apart Research template is available from its [Google Docs copy link](https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy?usp=sharing). The committed [DOCX template](official-template.docx) is the input to the official-template export.

The [Swarm Alignment 2026 page](https://apartresearch.com/sprints/swarm-alignment-2026) provides the venue instructions. [Report contents](README.md) identifies the manuscript, generated layouts and build command.
