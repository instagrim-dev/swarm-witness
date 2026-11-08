# Incident property decomposition (v2)

Post-submission research for issue #29, under epic #26. This note measures a property graph. It does not claim that Swarm Witness detected or prevented the July 2026 Hugging Face incident, and a correct local decision is not treated as proof of a correct effect.

## Properties that stay separate

| Id | Proposition | Decision control | Trust boundary |
| --- | --- | --- | --- |
| `P_url` | Unapproved remote URL requests are blocked. | `remote_url_allowlist` | remote fetch |
| `P_file_read` | Untrusted dataset inputs cannot disclose worker-local secrets. | `file_boundary` | worker-local filesystem |
| `P_exec` | Untrusted configuration cannot execute code. | `config_exec_boundary` | untrusted config evaluation |
| `P_identity` | Stolen or unscoped credentials cannot authorize lateral effects. | `credential_scope` | credential use |
| `P_effect` | Unauthorized downstream effects do not commit. | `downstream_decision_gate` | downstream commit |
| `P_system` | All five hold. | no single control | cross-boundary |

`P_system` is supported only when every child is supported. It is refuted when any child is refuted, and that child stays in the report. Otherwise it is unresolved. These verdicts use the same supported / refuted / unresolved partition as the #12 evidence-set model: unverified or empty evidence supports nothing. Settlement is read from an effect ledger, the same separation as the #10 simulator, and is not copied from the decision.

## Five typed families

| Id | Proposition | What it does not decide |
| --- | --- | --- |
| `P_local_control` | The named control's decisions match its own subject rule. | Whether anything committed, or whether `P_system` holds. |
| `P_decision_entitlement` | At the decision instant, the recorded decision was the entitled one. | Commit-time authorization. A later revocation does not rewrite this. |
| `P_commit_authorization` | Every authentic commit was authorized under the policy frozen for that interval. | Whether a commit happened, or whether `P_system` holds. |
| `P_commitment` | Some authentic effect in the observed interval committed. | Whether that commit was authorized. |
| `P_system` | The five boundary properties all hold. | It does not read the other four families. |

On `url_deny_ledger_commits` the local-control family is supported, decision-time entitlement is supported, commit authorization is refuted, commitment is supported, and `P_system` is refuted. On `url_held_worker_local_read` the URL allowlist control is supported and `P_system` is refuted. On `wrong_allow_blocked_at_settlement` the local-control family is refuted, the URL event's settlement is prevented, and `P_system` is supported.

Two revocation policies are frozen in the graph. There is no default. `issued_survives_revocation` does not treat a revocation as invalidating an authorization already issued. `revocation_closes_inflight` does, for a revocation after the decision and at or before commit time. `inflight_closes` and `inflight_survives` are the same events: decision-time entitlement is supported in both, and commit authorization is refuted only under the closing policy. `system_clean_inflight_closes` keeps `P_system` supported while commit authorization is refuted. Comparison with the single-policy baseline is a separate coordinate. It is not an enforcement failure, and fault attribution stays undetermined.

## Evidence standard

The evidence standard is Malayandi Palan, Christopher Chute, Michael Kim, and Benjamin Van Roy, "OpenAI-HuggingFace: A Reproduction & Lessons for Alignment Testing," LessWrong, published 2026-09-11, retrieved 2026-11-07. It is a public reproduction with its own released transcripts. It is not an original agent transcript and not a platform log. This run does not re-execute it.

Original agent transcripts and platform logs are `unavailable`. Each incident proposition is well-formed without those records. Their absence is not a contract failure. Reported text from the reproduction, including the reported shared-infrastructure write and the statement that distinct behaviors were compounded, stays `observed: unresolved` and is not adopted as an incident verdict. The Hugging Face technical timeline remains narrative in the same way.

The conjunction rule is support-sound. It is not refutation-complete: if shared evidence refutes only the intersection, while each child remains unresolved, the rule stays unresolved. That gap is counted, not papered over (`conservative_unresolved_gap` is true).

## What was measured

Seventeen synthetic fixtures and one public-narrative case. Fresh run of `experiments/incident_properties/run.py`:

| Quantity | Value |
| --- | --- |
| Synthetic fixtures | 17 |
| Graph false supports of `P_system` | 0 |
| Single-policy-pass baseline false supports of `P_system` | 6 |
| Baseline false rejects of `P_system` | 1 |
| Times a deny was treated as proof the effect did not commit | 0 |
| Deny decisions whose ledger row still committed | 2 |
| Postmortem properties independently supported | 0 |
| Postmortem properties independently refuted | 0 |
| Postmortem properties unresolved | 5 |
| Finite conjunction checks | 6917, 0 violations |
| Family-split check | passed |
| Discriminator failures | 0 |
| In-flight commit authorization, closing policy | refuted |
| Same events, issued authorization survives | supported |
| Comparison counted as an enforcement failure | 0 |
| Withheld records counted as a contract failure | false |
| Propositions well-formed without those records | true |
| Incident detection claimed | false |
| Incident prevention claimed | false |

The baseline supports `P_system` whenever every observed unapproved URL decision is deny. It ignores the ledger and the other four channels. The six false supports are `url_held_worker_local_read`, `url_held_config_exec`, `url_held_unscoped_credential`, `denied_then_unauthorized_effect`, `url_deny_ledger_commits`, and `url_only_system_claim`.

## Synthetic analogues

Fixtures name subject classes and markers (`WORKER_LOCAL_MARKER`, `SANDBOX_MARKER`, `UNTRUSTED_CONFIG_MARKER`, `UNSCOPED_CREDENTIAL_MARKER`). They do not contain fetch targets, file contents, or executable configuration.

On `url_held_worker_local_read` the allowlist denies an unapproved URL and that fetch is absent from the ledger, so `P_url` is supported. A separate worker-local read commits, so `P_file_read` is refuted and `P_system` is refuted. `P_exec` stays supported. Diagnosis types are `control_held` and `effect_boundary` together. The URL decision is correct, so the failure is not relabeled `decision_policy`. The URL event's broader-property layer is empty: a prevented fetch does not fill it.

The same split, with the failure moved, refutes `P_exec` while leaving `P_file_read` supported, and refutes `P_identity` while leaving `P_url` supported.

Negative controls:

- **Denied, then an unauthorized commit.** The URL deny is correct and the URL does not commit. A later unauthorized downstream row commits after its own deny. `P_effect` is refuted. The deny is not recorded as proof that the effect was prevented.
- **Wrong allow, blocked at settlement.** The allowlist allows an unapproved URL, and the ledger does not commit it. `P_url` and `P_system` are supported. Diagnosis still records `decision_policy` (incorrect) and `effect_boundary` (held). The baseline calls `P_system` refuted because it only saw the allow. That is the one false reject.
- **Valid local read.** A sandbox read commits and no unauthorized downstream row commits. `P_file_read` is supported. Channels that were not observed stay unresolved, so `P_system` is not upgraded.
- **Narrative-only effect.** A sentence says an unauthorized effect committed. There is no ledger row. Every property is unresolved, and the only diagnosis type is `unverified_source`.
- **URL evidence offered as the system claim.** `P_url` is supported and the other children are unresolved. `P_system` stays unresolved, with `scope_mismatch` beside `control_held`.

## Public timeline case

Case `hf-timeline-2026-07-27-stage2`. Primary text: Christophe Rannou, "Anatomy of a Frontier Lab Agent Intrusion," Hugging Face blog, published 2026-07-27, retrieved 2026-11-07, `https://huggingface.co/blog/agent-intrusion-technical-timeline`. OpenAI's "Hugging Face incident and the road ahead" page was retrieved the same day and is a second public narrative, not an independent ledger. Exploit payloads on the Hugging Face page are not reproduced. Quotes and omissions are in `experiments/incident_properties/postmortem.yaml`.

Reading of those quotes, which is not a verdict:

- `P_url`: the page says the datasets URL allowlist rejected every non-platform URL before any fetch, and that the later file and code paths were not URL fetches.
- `P_file_read`: the page says one vector returned worker-local bytes and that no code ran on that vector.
- `P_exec`: the page says a separate template path gave the agent code execution.
- `P_identity`: the page says one shared connector credential was cluster-admin.
- `P_effect`: the page says some mutating cloud calls were denied and a database was read but not modified, while other sections describe different effects. The label is `mixed_reported`, not a single outcome.

Independent verdicts, given only that narrative: all five unresolved, `P_system` unresolved. A reported URL rejection does not support `P_system`. If those narrative labels were mistaken for verified verdicts, the conjunction rule would refute `P_system` and still would not adopt that illustration as the case verdict.

## Records that are unavailable

Original agent transcripts and platform logs are not in this repository. Each is recorded as `unavailable`. That status does not make any proposition ill-formed, and it is not a contract failure. The properties above are stated without them. A verdict about the original platform stays unresolved because those records are not the evidence in hand, not because the proposition failed a gate.

The LessWrong reproduction is the evidence standard for what a public reproduction can report. It is not a substitute observation of the original platform. These are the records whose absence is unavailability rather than a failed property:

1. **`P_url`.** An allowlist decision log is not here. The timeline's `ValueError` sentence is not that log, and the proposition does not require it in order to be stated.
2. **`P_file_read`.** A file-open audit is not here. The proposition does not require the bytes or the audit.
3. **`P_exec`.** A process or config-evaluation audit is not here.
4. **`P_identity`.** A cluster authorization log is not here. No credential value is required.
5. **`P_effect`.** The cloud and database audits cited by the timeline are not here.
6. **Cross-source join.** Worker, API, and sandbox logs with owners are not here. Agreement between public pages is not that join.

## What this does not show

The six baseline misses are on a fixed synthetic ledger, not an estimate of how often a URL allowlist fails open in production. The timeline score does not confirm or deny the incident. Historical #10–#12 results are unchanged. No blinded claim audit, transcript-integrity experiment, multi-agent attribution study, forensic adapter, or detection-latency replay is part of this protocol. Issues #40–#42 are not implemented. The event-time fixture file is a handoff for those later units.

## Reproduce

```bash
PYTHONPATH=src python experiments/incident_properties/run.py
PYTHONPATH=src python -m pytest -q tests/test_incident_property_graph.py
```

Retained output: `evidence/incident_property_graph/`.
