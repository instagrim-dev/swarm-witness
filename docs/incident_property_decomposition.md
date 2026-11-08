# Incident property decomposition (v1)

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

The conjunction rule is support-sound. It is not refutation-complete: if shared evidence refutes only the intersection, while each child remains unresolved, the rule stays unresolved. That gap is counted, not papered over (`conservative_unresolved_gap` is true).

## What was measured

Nine synthetic fixtures and one public-narrative case. Fresh run of `experiments/incident_properties/run.py`:

| Quantity | Value |
| --- | --- |
| Synthetic fixtures | 9 |
| Graph false supports of `P_system` | 0 |
| Single-policy-pass baseline false supports of `P_system` | 6 |
| Baseline false rejects of `P_system` | 1 |
| Times a deny was treated as proof the effect did not commit | 0 |
| Deny decisions whose ledger row still committed | 2 |
| Postmortem properties independently supported | 0 |
| Postmortem properties independently refuted | 0 |
| Postmortem properties unresolved | 5 |
| Finite conjunction checks | 6905, 0 violations |
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

## Telemetry required for a stronger claim

Each item is necessary for the named property. None of these records are in this repository.

1. **`P_url`.** Allowlist decisions with timestamp, worker id, URL class (platform or non-platform), decision, and whether a fetch client ran. The blog's `ValueError` sentence is not that log.
2. **`P_file_read`.** File-open audit with path class (dataset sandbox or worker-local), dataset revision, and whether bytes were returned. Not the bytes. The file-read sentence is not this audit.
3. **`P_exec`.** A boolean that untrusted configuration was evaluated as code, with workload id and timestamp, from a process or config-evaluation audit that is not the file-open record. Not a template and not a payload.
4. **`P_identity`.** Credential identifier (not the secret), intended scope, API called, and allow or deny. The cluster-admin sentence needs the cluster authorization decision for that identity.
5. **`P_effect`.** A mutating-call ledger with commit or deny, actor, and timestamp, kept separate from file-read and code-execution rows. The cloud-policy and database-audit sentences cite logs that are not here, and they do not settle the other effect classes the page also describes.
6. **Cross-source join.** A key across the worker log, the Hugging Face API dataset commit, and the external sandbox log, each with its owner. Agreement between the two public pages is not that join.

## What this does not show

The six baseline misses are on a fixed synthetic ledger, not an estimate of how often a URL allowlist fails open in production. The timeline score does not confirm or deny the incident. Historical #10–#12 results are unchanged. No blinded claim audit, transcript-integrity experiment, multi-agent attribution study, forensic adapter, or detection-latency replay is part of this protocol.

## Reproduce

```bash
PYTHONPATH=src python experiments/incident_properties/run.py
PYTHONPATH=src python -m pytest -q tests/test_incident_property_graph.py
```

Retained output: `evidence/incident_property_graph/`.
