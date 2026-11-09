# Incident audit v1: blinded postmortem qualification

**Question.** On a frozen set of public claims about the 2026 OpenAI Artifactory / Hugging Face incident, does the Swarm Witness three-way projection produce fewer unsupported security conclusions than two baselines that see the same excerpts?

**What this is.** A postmortem audit of published reports. Stage A shows one narration or a surface tool line. Stage B adds a withheld excerpt. Human warrants live in `adjudication_v1.yaml` and are applied only after the qualifiers return.

**What this is not.** Swarm Witness did not detect this incident and this study does not measure whether it could have prevented it. World effects are not treated as verified just because a postmortem asserts them. No exploit was reenacted and no private log was invented. The Apart sprint reconstruction was retrieved as an abstract and kept out of scoring.

## Corpus

Quotes were checked on 2026-11-07 against the retrievals in `corpus_manifest.yaml`.

| Source | Publication | In scoring | Bytes pinned |
| --- | --- | --- | --- |
| [OpenAI blog](https://openai.com/index/hugging-face-incident-and-the-road-ahead/) | 2026-08-26 | yes, via readability text | readability sha256 `db566386c305210c…` is not rechecked; direct GET returned HTTP 403 and those bytes are not in the repo |
| [METR / Redwood](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/) | 2026-08-26 | yes, HTML quotes | HTML sha256 `37ec7c48dc11ba00…` |
| [Hugging Face timeline](https://huggingface.co/blog/agent-intrusion-technical-timeline) | 2026-07-27 | yes | request-id-normalized sha256 `56e0322898285927…`; a full-response digest is not stable |
| [Apart sprint page](https://apartresearch.com/sprints/projects/what-happened-and-what-breaks-next-a-defenderusable-reconstruction-of-the-summer2026-agentswarm-incidents-tfn2) | 2026-09-12 | no | HTML sha256 `4a63ccdc3efe69a1…`; PDF not retrieved |

The METR PDF (`f7e87133833363da…`, 7,443,085 bytes) was hashed and not parsed.

**Unavailable for verification.** The Artifactory message-board dump, the roughly 1,300 raw transcripts, per-action transcript timestamps, and Hugging Face platform and audit logs. OpenAI's technical report URL returned HTTP 403 here and was not scored. The July Hugging Face disclosure and the AISI note were reachable and were not added to the frozen corpus.

## Rules

Twelve propositions, four adversarial controls, two stages, 24 cells per method. Abstentions stay in the denominator. Unsupported conclusions are false support plus wrong refutation.

- **Naive.** Any literal support or pre-registered overread accepts the claim. A support is not withdrawn when another sentence in the package conflicts.
- **Checklist.** Same package, but only the earliest pre-registered source. Abstain on a counterfactual, an imprecise estimate, or an in-source contradiction. No independence, telemetry, or scope check.
- **Swarm Witness.** R4 projection of the #12 rule: no support or refutation of a world effect without public raw telemetry; a copy or same-origin derivative is not a new observation; an allowlist hit or an unauthenticated tool line does not establish a broader property. Retrieved sentences can refute a sufficiency claim because those sentences are the object being checked.

## Result

| Method | Unsupported / 24 | Correct refusals | Warranted refutations | Warranted supports |
| --- | ---: | ---: | ---: | ---: |
| Naive | 24 | 0 | 0 | 0 |
| Checklist | 12 | 10 | 1 | 0 |
| Swarm Witness | 0 | 22 | 2 | 0 |

This table is the earlier author-curated staged comparison against naive PASS and a weak checklist. It is not a comparison with the strong checker. Mechanical withholding of later-stage evidence is not independent curation. The frozen public comparison, regenerated in `report/bounded_comparison_v1/TABLES.md`, puts the strong-checker tie beside it: Swarm Witness and the strong checker both have 0 *unsupported supports*, and naive PASS has 24. `superiority_claim` stays false. The zero warranted supports are part of the staged result: with raw telemetry absent, the difference from the weak baselines is refusing unsupported upgrades, not confirming the intrusion.

The two warranted refutations are sufficiency claims, and only after stage B:

- `C03` tool line `echo REAL; sleep`. Stage A stays unresolved. Stage B's published return token contradicts sufficiency. Failure origin is evidence, the R4 misbinding case.
- `C05` URL allowlist. Stage A stays unresolved. Stage B's Hugging Face sentence says the local file read and the code execution were not URL fetches. That refutes the whole-worker reading. It does not verify the worker logs.

`C04` (the handle `JAN183411` as a verified unique directing instance) stays unresolved at both stages. `C06` moves from a single OpenAI assertion to a cross-source assertion once Hugging Face's platform narration is added, and the world effect stays unresolved. `C09` stays unresolved even after Hugging Face's sentence that the database was not written: that sentence is not the audit log. The checklist treats it as a refutation, which is a wrong refutation under this warrant. `C10` stays unresolved because it is a counterfactual. METR's out-of-scope note does not verify it.

## Controls and ablations

| Control | Claim | Stage B Swarm Witness result |
| --- | --- | --- |
| Spoofed tool line | C03 | not supported; refuted only once the mismatch token is visible |
| Copied receipt | C11 | one support group; the copy is withheld |
| Same-origin count | C12 | unresolved; the synthetic blurb does not add a group |
| Allowlist as whole-system security | C05 | unresolved, then refuted; never supported |

Withholding stage B leaves `C03` and `C05` unresolved, so the update depends on the withheld sentences. Treating dependent public text as telemetry raises Swarm Witness unsupported conclusions from 0 to 13. Collapsing the allowlist into the whole-worker property supports `C05` at stage A. Counting the synthetic blurb as its own group raises `C12` from one support group to two, and the primary rule still does not verify the count.

## Reproduce

```bash
PYTHONPATH=src python3 experiments/incident_audit/run.py
PYTHONPATH=src python3 experiments/incident_audit/verify_pins.py
PYTHONPATH=src python3 experiments/incident_audit/verify_pins.py --fetch
pytest -q tests/test_incident_audit.py
```

Inputs are hashed in `artifacts/incident_audit_v1/input_sha256.json`. The matrix is `evidence/incident_audit_v1/matrix.json`. Issues #28–#32 are not implemented here.

**Limit.** One author coded the excerpts, the warrants, and the rules. Stage B text is mechanically absent from stage A prompts; that is the blindness this repository can enforce. It is not a separately staffed jury. Naive acceptance is harsh on purpose: a positive sentence is not withdrawn when a later sentence conflicts, which is why that baseline is unsupported on all 24 cells. The checklist is the informative comparison.
