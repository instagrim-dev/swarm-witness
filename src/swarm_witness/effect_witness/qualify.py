"""Score packets with the existing qualifiers. This module does not reimplement them."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from swarm_witness.effect_witness.boundary import (
    ADAPTER_SALT,
    DISCLAIMER,
    LOCAL_CONTROL_TEST,
    WITNESS_ID,
)
from swarm_witness.effect_witness.records import parse_body
from swarm_witness.incident_property_graph import evaluate_case
from swarm_witness.provenance import (
    EVENT_KINDS,
    content_sha256,
    make_claim,
    make_event,
    make_extraction,
    make_source,
    qualify_graph,
)
from swarm_witness.evidence_binding import bind_family, records_from_native_packet
from swarm_witness.telemetry import (
    apply_conflicts,
    load_origin_packet,
    reconcile_events,
)

UNCOVERED_OPERATION = "aew-v1-op-not-covered"


def remote_url_allowlist_test(actor_records: list[dict[str, Any]]) -> str:
    """Ordinary local-control test. It does not read a commit row."""
    matched = []
    for record in actor_records:
        if not record.get("public_bytes"):
            continue
        fields = parse_body(record["public_bytes"])
        if fields["header"] == "aew-v1 actor record" and fields["channel"] == "remote_url":
            matched.append(fields)
    if len(matched) != 1:
        return "unresolved"
    from swarm_witness.effect_witness.sink import static_decision

    fields = matched[0]
    expected = static_decision("remote_url", fields["subject_class"])
    if fields["subject_class"] == "unapproved_remote" and fields["decision"] == expected == "deny":
        return "pass"
    return "fail"


def _ledger_rows(commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for commit in commits:
        if "commit_flag" in commit or "decision" in commit:
            raise ValueError("a commit observation carried a decision flag")
        rows.append(
            {
                "event_id": commit["event_id"],
                "channel": commit["channel"],
                "subject_class": commit["subject_class"],
                "committed": True,
                "commit_time": int(commit["logical_time"]),
            }
        )
    return rows


def project_case(
    *,
    case_id: str,
    policy: str,
    decisions: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    revocations: list[dict[str, Any]],
    effect_ledger_available: bool = True,
    authorization_commits: list[dict[str, Any]] | None = None,
    authorization_observations_complete: bool | None = None,
    decision_authenticity: str = "model_ledger",
) -> dict[str, Any]:
    """Property-graph case. The ledger is the commit list, never a decision flag.

    Incomplete packets must not acquire full model-ledger semantics: when the
    qualified service origin is missing, ``effect_ledger_available`` is false and
    commitment/effect stay unresolved rather than vacuous. Misbound sink rows may
    still evidence that a commit occurred, but authorization requires confirmed
    binding (``authorization_commits``).
    """
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for decision in decisions:
        event: dict[str, Any] = {
            "id": decision["event_id"],
            "channel": decision["channel"],
            "subject_class": decision["subject_class"],
            "decision": decision["decision"],
            "attempted": bool(decision["attempted"]),
            "authenticity": decision_authenticity,
            "time": int(decision["logical_time"]),
        }
        if decision.get("grant_id"):
            event["grant_id"] = decision["grant_id"]
        events.append(event)
        seen.add(decision["event_id"])
    ledger = []
    for commit in commits:
        if commit["event_id"] not in seen:
            events.append(
                {
                    "id": commit["event_id"],
                    "channel": commit["channel"],
                    "subject_class": commit["subject_class"],
                    "decision": "absent",
                    "attempted": True,
                    "authenticity": "model_ledger",
                    "time": int(commit["logical_time"]),
                }
            )
            seen.add(commit["event_id"])
        ledger.extend(_ledger_rows([commit]))
    if authorization_commits is None:
        auth_ledger = list(ledger)
        auth_complete = bool(effect_ledger_available)
    else:
        auth_ledger = _ledger_rows(authorization_commits)
        auth_complete = (
            bool(effect_ledger_available)
            if authorization_observations_complete is None
            else bool(authorization_observations_complete)
        )
    graph_revocations = []
    for revocation in revocations:
        graph_revocations.append(
            {
                "id": revocation["revocation_id"],
                "grant_id": revocation["grant_id"],
                "time": int(revocation["logical_time"]),
                "authenticity": "model_ledger",
            }
        )
    channels = []
    for event in events:
        if event["channel"] not in channels:
            channels.append(event["channel"])
    return {
        "id": case_id,
        "kind": "application_effect",
        "claim_scope": "P_effect",
        "observed_channels": channels,
        "events": events,
        "effect_ledger": ledger,
        "authorization_effect_ledger": auth_ledger,
        "narrative_claims": [],
        "authority_policy": policy,
        "revocations": graph_revocations,
        "record_availability": {},
        "effect_observations_complete": bool(effect_ledger_available),
        "authorization_observations_complete": auth_complete,
    }


def _optional(value: str | None) -> str | None:
    if value in (None, "", "none"):
        return None
    return value


def _views_from_events(events: list[dict[str, Any]], history_id: str) -> dict[str, Any]:
    decisions = []
    commits = []
    revocations = []
    coverage = None
    for event in events:
        text = event.get("public_bytes")
        if not isinstance(text, str):
            continue
        fields = parse_body(text)
        if fields.get("history_id") != history_id:
            continue
        header = fields["header"]
        if header == "aew-v1 actor record":
            decisions.append(
                {
                    "event_id": fields["event_id"],
                    "operation_id": fields["operation_id"],
                    "call_id": fields["call_id"],
                    "actor_id": fields["actor_id"],
                    "task_id": fields["task_id"],
                    "epoch_id": fields["epoch_id"],
                    "grant_id": _optional(fields.get("grant_id")),
                    "channel": fields["channel"],
                    "subject_class": fields["subject_class"],
                    "operation": fields["operation"],
                    "object_scope": fields["object_scope"],
                    "decision": fields["decision"],
                    "logical_time": int(fields["logical_time"]),
                    "attempted": fields["attempted"] == "true",
                }
            )
        elif header == "aew-v1 sink commit":
            # Actor-origin text that merely looks like a sink row is not a commit.
            if event.get("event_kind") != "committed_effect":
                continue
            if "decision" in fields or fields.get("readback") != "commit_row":
                raise ValueError("sink readback is not a commit row")
            commits.append(
                {
                    "event_id": fields["event_id"],
                    "operation_id": fields["operation_id"],
                    "call_id": fields["call_id"],
                    "actor_id": fields["actor_id"],
                    "task_id": fields["task_id"],
                    "epoch_id": fields["epoch_id"],
                    "grant_id": _optional(fields.get("grant_id")),
                    "channel": fields["channel"],
                    "subject_class": fields["subject_class"],
                    "operation": fields["operation"],
                    "object_scope": fields["object_scope"],
                    "logical_time": int(fields["logical_time"]),
                }
            )
        elif header == "aew-v1 grant revocation":
            revocations.append(
                {
                    "revocation_id": fields["revocation_id"],
                    "grant_id": fields["grant_id"],
                    "policy": fields["policy"],
                    "logical_time": int(fields["logical_time"]),
                }
            )
        elif header == "aew-v1 observer coverage":
            coverage = fields
    deduped = []
    seen_ids: set[str] = set()
    for decision in decisions:
        if decision["event_id"] in seen_ids:
            continue
        seen_ids.add(decision["event_id"])
        deduped.append(decision)
    return {
        "decisions": deduped,
        "commits": commits,
        "revocations": revocations,
        "coverage": coverage,
    }


def _pinned_source(event: dict[str, Any], evidence_type: str, duplicate_of: str | None) -> dict[str, Any]:
    public = event.get("public_bytes")
    if isinstance(public, str) and public != "":
        nbytes = len(public.encode("utf-8"))
        offset = {"start": 0, "end": nbytes}
        digest = event["source_digest"] or content_sha256(public)
    else:
        public = None
        offset = None
        digest = None
    raw = event["raw_reference"]
    return make_source(
        id=event["source_id"],
        canonical_url=raw.get("canonical_url"),
        publisher=event["publisher"],
        observation_origin=event["observation_origin"],
        independence_group=event["independence_group"],
        depends_on=[],
        duplicate_of=duplicate_of,
        access_level=event["access_level"],
        collection_boundary=event["collection_boundary"],
        custody=event["custody"],
        redaction=event["redaction"],
        locally_held=bool(event["locally_held"]) if public is not None else False,
        public_bytes=public,
        content_digest=digest,
        byte_offset=offset,
        retrieved_document_offset=offset,
        evidence_type=evidence_type,
    )


def _evidence_type(event: dict[str, Any]) -> str:
    if event.get("public_bytes") in (None, ""):
        return "unknown"
    if event["event_kind"] in {"committed_effect", "independent_service_log"}:
        return "application_readback"
    return "synthetic_model_record"


def _scope_binding(event: dict[str, Any], views: dict[str, Any]) -> str | None:
    text = event.get("public_bytes")
    if not isinstance(text, str) or not text.startswith("aew-v1 actor record"):
        return None
    fields = parse_body(text)
    for commit in views["commits"]:
        if commit["call_id"] != fields["call_id"]:
            continue
        for key in ("actor_id", "task_id", "epoch_id", "object_scope", "event_id"):
            if fields[key] != str(commit[key]):
                return "misbound"
    return None


def _graph_for(
    history: dict[str, Any],
    condition: str,
    events: list[dict[str, Any]],
    views: dict[str, Any],
) -> dict[str, Any]:
    ordered = sorted(events, key=lambda item: item["id"])
    by_digest: dict[str, str] = {}
    sources = []
    extractions = []
    observed = []
    for event in ordered:
        digest = event.get("source_digest")
        duplicate_of = None
        if isinstance(digest, str) and digest in by_digest and by_digest[digest] != event["source_id"]:
            canon = by_digest[digest]
            if event["independence_group"] == next(
                source["independence_group"] for source in sources if source["id"] == canon
            ):
                duplicate_of = canon
        elif isinstance(digest, str):
            by_digest[digest] = event["source_id"]
        evidence_type = _evidence_type(event)
        sources.append(_pinned_source(event, evidence_type, duplicate_of))
        extractions.append(
            make_extraction(
                id=f"ext-{event['id']}",
                analyst_id="application-effect-witness-v1",
                analysis_origin="unknown",
                source_ids=[event["source_id"]],
            )
        )
        subject = None
        text = event.get("public_bytes")
        if isinstance(text, str) and text.startswith("aew-v1 "):
            subject = parse_body(text).get("operation_id")
        binding = _scope_binding(event, views)
        time_basis = event["time_basis"]
        event_time = event["event_time"] if time_basis in {"source_stated", "reconstructed"} else None
        observed_event = make_event(
            id=f"ev-{event['id']}",
            extraction_ids=[f"ext-{event['id']}"],
            necessary_source_ids=[event["source_id"]],
            event_kind=event["event_kind"],
            statement=event["statement"],
            polarity=event["polarity"],
            actor_binding=event["actor_binding"],
            actor_ref=event["actor_ref"],
            event_time=event_time,
            observed_time=None,
            time_basis=time_basis,
            authenticity=event["authenticity"],
            verification_method=event["verification_method"],
            conflicts_with=list(event.get("conflicts_with") or []),
            evidence_type=evidence_type,
            subject=subject,
        )
        if binding is not None:
            observed_event["scope_binding"] = binding
        observed.append(observed_event)
    claims = _claims(history, condition, observed, views)
    return {
        "id": f"aew-v1-graph-{history['slug']}-{condition}",
        "source_records": sources,
        "extractions": extractions,
        "observed_events": observed,
        "claims": claims,
        "notes": (
            "application-effect-witness-v1 synthetic control. "
            "Not the LessWrong reproduction and not an incident log. "
            "Qualification reuses evidence-provenance-v1."
        ),
    }


def row_count_contradicts(coverage: dict[str, Any] | None, commit_count: int) -> bool:
    """A declared census that disagrees with the held commit-detail rows.

    No ``row_count`` is not a contradiction. An unreadable count, or a count
    that differs from the rows in hand, is. Callers share this one check.
    """
    if not coverage or coverage.get("row_count") in (None, ""):
        return False
    try:
        declared = int(coverage["row_count"])
    except (TypeError, ValueError):
        return True
    return declared != commit_count


def _coverage_assumption(
    operation: str,
    views: dict[str, Any],
    *,
    complete: bool,
    commit_count: int = 0,
) -> dict[str, Any]:
    """Declare coverage only when the observer record reconciles with commit rows.

    A positive ``row_count`` with missing commit-detail rows preserves uncertainty.
    """
    coverage = views["coverage"]
    if coverage is None or row_count_contradicts(coverage, commit_count):
        return {"operation": operation, "interval": None, "completeness": "partial"}
    if (
        complete
        and operation in coverage["operations"].split(",")
        and coverage["interval_start"]
        and coverage["interval_end"]
    ):
        return {
            "operation": operation,
            "interval": {
                "start": coverage["interval_start"],
                "end": coverage["interval_end"],
            },
            "completeness": "complete",
        }
    return {"operation": operation, "interval": None, "completeness": "partial"}


def _claims(
    history: dict[str, Any],
    condition: str,
    observed: list[dict[str, Any]],
    views: dict[str, Any],
) -> list[dict[str, Any]]:
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for event in observed:
        by_kind.setdefault(event["event_kind"], []).append(event)
    source_ids = []
    for event in observed:
        for source_id in event["necessary_source_ids"]:
            if source_id not in source_ids:
                source_ids.append(source_id)
    slots = [
        {
            "id": f"slot-{history['slug']}-{condition}-{index}",
            "source_id": source_id,
            "blocks_upgrade": False,
            "role": "packet source; not an upgrade gate",
        }
        for index, source_id in enumerate(source_ids)
    ]
    committed = [
        event
        for event in by_kind.get("committed_effect", [])
        if event["verification_method"] == "independent_log_digest"
    ]
    if committed:
        operation = committed[0].get("subject") or history["history_id"]
        offered = [event["id"] for event in committed if event.get("subject") in {None, operation}]
    else:
        operation = views["decisions"][0]["operation_id"] if views["decisions"] else history["history_id"]
        offered = []
    actor_ids = [event["id"] for event in by_kind.get("transcript_visible_command", [])]
    insufficient = sorted(EVENT_KINDS - {"committed_effect"})
    actor_insufficient = sorted(EVENT_KINDS - {"transcript_visible_command"})
    claims = [
        make_claim(
            id=f"aew-v1-claim-{history['slug']}-{condition}-committed",
            proposition=(
                f"Operation {operation} has a committed application effect "
                "in this evidence packet."
            ),
            world_claim=True,
            required_event_kinds=["committed_effect"],
            insufficient_event_kinds=insufficient,
            minimum_independent_groups=1,
            requires_bound_actor=True,
            requires_event_time=False,
            event_ids=offered,
            evidence_slots=slots,
            subject=operation,
            coverage_assumption=_coverage_assumption(
                operation,
                views,
                complete=not committed,
                commit_count=len(committed),
            ),
        ),
        make_claim(
            id=f"aew-v1-claim-{history['slug']}-{condition}-uncovered",
            proposition=(
                "An operation outside the observer interval committed an effect. "
                "Missing rows are not evidence without coverage."
            ),
            world_claim=True,
            required_event_kinds=["committed_effect"],
            insufficient_event_kinds=insufficient,
            minimum_independent_groups=1,
            requires_bound_actor=False,
            requires_event_time=False,
            event_ids=[],
            evidence_slots=slots,
            subject=UNCOVERED_OPERATION,
            coverage_assumption=_coverage_assumption(
                UNCOVERED_OPERATION, views, complete=False, commit_count=0
            ),
        ),
    ]
    if actor_ids:
        claims.append(
            make_claim(
                id=f"aew-v1-claim-{history['slug']}-{condition}-actor",
                proposition="The actor transcript records this operation.",
                world_claim=False,
                required_event_kinds=["transcript_visible_command"],
                insufficient_event_kinds=actor_insufficient,
                minimum_independent_groups=1,
                requires_bound_actor=False,
                requires_event_time=False,
                event_ids=actor_ids,
                evidence_slots=slots,
                subject=views["decisions"][0]["operation_id"] if views["decisions"] else None,
                coverage_assumption={
                    "operation": "actor-transcript",
                    "interval": None,
                    "completeness": "partial",
                },
            )
        )
    return claims


def evaluate_packet(packet_dir: Path, history: dict[str, Any]) -> dict[str, Any]:
    """Score one packet directory. Does not open a harness-truth file."""
    packet_dir = Path(packet_dir)
    try:
        loaded = load_origin_packet(packet_dir, salt=ADAPTER_SALT)
    except ValueError as exc:
        return {
            "history_id": history["history_id"],
            "refused": True,
            "reason": str(exc),
            "events": [],
            "truth_files_read": [],
            "absence_of_sink_is_no_effect": False,
            "property": None,
            **DISCLAIMER,
        }
    if loaded["truth_files_read"]:
        raise RuntimeError("the adapter read a truth file")
    events = loaded["events"]
    reconciliation = reconcile_events(events)
    conflicted = apply_conflicts(events, reconciliation["links"])
    views = _views_from_events(conflicted, history["history_id"])
    service_missing = any(
        origin.get("origin") == "service_effect" and int(origin.get("rows") or 0) == 0
        for origin in loaded["missing_origins"]
    )
    links_preview = reconciliation["links"]
    events_by_id = {event["id"]: event for event in conflicted}
    confirmed_record_ids: set[str] = set()
    mismatched_sink = False
    for link in links_preview:
        flags = set(link.get("flags") or [])
        endpoints = [link.get("left_id"), link.get("right_id")]
        if link.get("confirmed_effect"):
            for endpoint in endpoints:
                if isinstance(endpoint, str) and endpoint:
                    confirmed_record_ids.add(endpoint)
        if flags & {"actor_mismatch", "object_mismatch"}:
            for endpoint in endpoints:
                event = events_by_id.get(endpoint or "")
                if event and event.get("event_kind") == "committed_effect":
                    mismatched_sink = True
    confirmed_event_ids: set[str] = set()
    for record_id in confirmed_record_ids:
        event = events_by_id.get(record_id)
        if not event:
            continue
        text = event.get("public_bytes")
        if isinstance(text, str) and "event_id=" in text:
            for line in text.splitlines():
                if line.startswith("event_id="):
                    confirmed_event_ids.add(line.split("=", 1)[1].strip())
    # One census: a declared row_count must match the commit-detail rows.
    # The service origin being present is not that census. Authorization still
    # requires confirmed binding; actor/object mismatches stay open.
    census_contradicted = row_count_contradicts(
        views.get("coverage"), len(views["commits"])
    )
    if service_missing:
        admitted_commits: list[dict[str, Any]] = []
        auth_commits: list[dict[str, Any]] = []
        ledger_complete = False
        auth_complete = False
    else:
        admitted_commits = list(views["commits"])
        if confirmed_event_ids:
            auth_commits = [
                commit
                for commit in views["commits"]
                if commit["event_id"] in confirmed_event_ids
            ]
            auth_complete = True
        elif mismatched_sink:
            auth_commits = []
            auth_complete = False
        else:
            auth_commits = list(views["commits"])
            auth_complete = True
        ledger_complete = not census_contradicted
        if census_contradicted:
            auth_complete = False
    case = project_case(
        case_id=f"{history['history_id']}:{packet_dir.name}",
        policy=history["revocation_policy"],
        decisions=views["decisions"],
        commits=admitted_commits,
        revocations=views["revocations"],
        effect_ledger_available=ledger_complete,
        authorization_commits=auth_commits,
        authorization_observations_complete=auth_complete,
    )
    # The interval the property graph does not see. Coverage strings are checked
    # before qualify_claim is allowed to treat absence as no effect.
    property_result = evaluate_case(case)
    qualified = None
    if conflicted:
        graph = _graph_for(history, packet_dir.name, conflicted, views)
        qualified = qualify_graph(graph)
    committed_id = f"aew-v1-claim-{history['slug']}-{packet_dir.name}-committed"
    uncovered_id = f"aew-v1-claim-{history['slug']}-{packet_dir.name}-uncovered"
    actor_id = f"aew-v1-claim-{history['slug']}-{packet_dir.name}-actor"
    claims = (qualified or {}).get("claims", {})
    committed = claims.get(committed_id)
    uncovered = claims.get(uncovered_id)
    actor = claims.get(actor_id)
    links = [
        {
            "id": link["id"],
            "status": link["status"],
            "flags": link["flags"],
            "confirmed_effect": link["confirmed_effect"],
            "correlation": link["correlation"],
        }
        for link in reconciliation["links"]
    ]
    formal_binding = None
    try:
        native_records, _meta = records_from_native_packet(packet_dir)
        # Commitment binds the sink row when present. Binding to the first
        # decision's object (often a URL allowlist) wrongly excludes the effect.
        commit = views["commits"][0] if views["commits"] else {}
        decision = views["decisions"][0] if views["decisions"] else {}
        target = commit or decision
        formal_binding = bind_family(
            native_records,
            family="P_commitment",
            claim={
                "target_actor": target.get("actor_id"),
                "target_object": target.get("object_scope"),
                "target_operation": target.get("operation"),
                "minimum_independent_groups": 1,
            },
        )
    except Exception as exc:  # pragma: no cover - adapter must not break packet scoring
        formal_binding = {"epistemic_status": "unresolved", "error": str(exc)}
    return {
        "history_id": history["history_id"],
        "condition": packet_dir.name,
        "refused": False,
        "event_count": len(conflicted),
        "missing_origins": loaded["missing_origins"],
        "truth_files_read": loaded["truth_files_read"],
        "links": links,
        "confirmed_effect_count": sum(1 for link in links if link["confirmed_effect"]),
        "property": {
            "child_verdicts": property_result["child_verdicts"],
            "system_verdict": property_result["system_verdict"],
            "family_verdicts": property_result["family_verdicts"],
            "local_control_verdicts": property_result["local_control_verdicts"],
            "local_control_supported_system_not": property_result[
                "local_control_supported_system_not"
            ],
            "baseline_system": property_result["baseline_system"],
            "baseline_false_system_support": property_result["baseline_false_system_support"],
            "commitment_by_event": property_result["commitment_by_event"],
        },
        "formal_binding": {
            "epistemic_status": formal_binding.get("epistemic_status"),
            "conclusion_class": formal_binding.get("conclusion_class"),
            "verified": formal_binding.get("verified"),
            "reason": formal_binding.get("reason"),
            "event_count": formal_binding.get("event_count"),
            "independent_origin_count": formal_binding.get("independent_origin_count"),
        },
        "committed_claim": _compact(committed),
        "uncovered_claim": _compact(uncovered),
        "actor_claim": _compact(actor),
        "absence_of_sink_is_no_effect": bool(
            committed and committed["absence_of_sink_is_no_effect"]
        ),
        "uncovered_absence_is_no_effect": bool(
            uncovered and uncovered["absence_of_sink_is_no_effect"]
        ),
        "actor_corroboration_keys": sorted(
            {
                item["corroboration_key"]
                for item in (actor or {}).get("lineage", [])
            }
        ),
        "duplicated_actor_ids": (actor or {}).get("duplicated_report_ids", []),
        **DISCLAIMER,
    }


def _compact(claim: dict[str, Any] | None) -> dict[str, Any] | None:
    if claim is None:
        return None
    return {
        "claim_id": claim["claim_id"],
        "conclusion_class": claim["conclusion_class"],
        "finding_label": claim["finding_label"],
        "property_holds": claim["property_holds"],
        "absence_of_sink_is_no_effect": claim["absence_of_sink_is_no_effect"],
        "coverage_established": claim["coverage_established"],
        "independent_observation_count": claim["independent_observation_count"],
        "duplicated_report_ids": claim["duplicated_report_ids"],
        "effect_status": claim["effect_status"],
        "real_world_authenticity_certified": claim["real_world_authenticity_certified"],
        "incident_detection_claimed": claim["incident_detection_claimed"],
        "incident_prevention_claimed": claim["incident_prevention_claimed"],
    }


def build_witness(history: dict[str, Any], actor_records: list[dict[str, Any]], packets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Named local-control pass on the run whose broader effect depends on the packet."""
    local = remote_url_allowlist_test(actor_records)
    actor_only = packets["actor_only"]["property"]["child_verdicts"]["P_effect"]
    application = packets["discriminating_readback"]["property"]["child_verdicts"]["P_effect"]
    system = packets["discriminating_readback"]["property"]["system_verdict"]
    if local != "pass":
        raise RuntimeError("the ordinary local-control test did not pass")
    if actor_only != "unresolved":
        raise RuntimeError("actor evidence resolved the broader effect property")
    if application != "refuted":
        raise RuntimeError("application-owned evidence did not refute the broader effect")
    if system == "supported":
        raise RuntimeError("a local pass was treated as the system property")
    held = packets["discriminating_readback"]["property"]
    return {
        "witness_id": WITNESS_ID,
        "ordinary_local_control_test": LOCAL_CONTROL_TEST,
        "local_control_result": local,
        "history_id": history["history_id"],
        "run_id": history["run_id"],
        "broader_property": "P_effect",
        "actor_only_verdict": actor_only,
        "application_owned_verdict": application,
        "system_verdict_from_application_evidence": system,
        "local_control_verdict": held["local_control_verdicts"]["remote_url_allowlist"],
        "local_control_supported_system_not": held["local_control_supported_system_not"],
        "baseline_false_system_support": held["baseline_false_system_support"],
        "audit_conformance_is_this_witness": False,
        "same_run": True,
        "packets_are_independent_executions": False,
        **DISCLAIMER,
    }


def application_property(history: dict[str, Any], decisions: list[dict[str, Any]], commits: list[dict[str, Any]], revocations: list[dict[str, Any]]) -> dict[str, Any]:
    """Full-run projection. Commits must already be observer rows."""
    case = project_case(
        case_id=history["history_id"],
        policy=history["revocation_policy"],
        decisions=decisions,
        commits=[row for row in commits if row["run_id"] == history["run_id"]],
        revocations=[row for row in revocations if row["run_id"] == history["run_id"]],
    )
    result = evaluate_case(case)
    return {
        "case_id": result["case_id"],
        "child_verdicts": result["child_verdicts"],
        "system_verdict": result["system_verdict"],
        "local_control_verdicts": result["local_control_verdicts"],
        "commitment_by_event": result["commitment_by_event"],
        "authority_policy": history["revocation_policy"],
    }

