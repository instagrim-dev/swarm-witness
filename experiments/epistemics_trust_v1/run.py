#!/usr/bin/env python3
"""Trust-infrastructure reading of the retained 48-packet comparison.

A consumer that treats the authentic historical support as its signal is
compared with a consumer that checks the evidence-stage warrant. Neither
consumer is a new experiment. The historical packets and warrants stay put.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "report" / "epistemics_trust_v1"


def _renderer():
    path = ROOT / "scripts" / "render_bounded_comparison.py"
    spec = importlib.util.spec_from_file_location("render_bounded_comparison", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the retained comparison renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fields(record: dict[str, Any], parse_body) -> dict[str, str]:
    text = record.get("public_bytes")
    if not isinstance(text, str):
        return {}
    return parse_body(text)


def _intact_actor(record: dict[str, Any]) -> bool:
    text = record.get("public_bytes")
    return (
        record.get("surface") == "requested_command"
        and record.get("locally_held") is True
        and record.get("custody") == "intact"
        and record.get("actor_binding") == "bound"
        and isinstance(text, str)
        and bool(text.strip())
    )


def _packet_anatomy(records: list[dict[str, Any]], parse_body, decides, misbound) -> dict[str, Any]:
    deciding = 0
    intact_misbound_actors = 0
    effect_rows = 0
    withheld_supports = 0
    for record in records:
        fields = _fields(record, parse_body)
        if decides(record, fields):
            deciding += 1
        if record.get("surface") == "committed_effect":
            effect_rows += 1
            if (
                record.get("locally_held") is False
                and record.get("access_level") == "withheld"
                and record.get("redaction") == "withheld_original"
                and record.get("polarity") == "supports"
                and not (isinstance(record.get("public_bytes"), str) and record["public_bytes"].strip())
            ):
                withheld_supports += 1
        if _intact_actor(record) and misbound(record, fields):
            intact_misbound_actors += 1
    if effect_rows:
        shape = "withheld_effect_row"
    elif intact_misbound_actors:
        shape = "misbound_actor_only"
    else:
        shape = "other"
    return {
        "deciding_records": deciding,
        "intact_misbound_actor_records": intact_misbound_actors,
        "effect_rows": effect_rows,
        "withheld_effect_rows_marked_supports": withheld_supports,
        "shape": shape,
    }


def _record_fields(record: dict[str, Any], parse_body) -> dict[str, str]:
    text = record.get("public_bytes")
    if isinstance(text, str) and text.strip():
        return parse_body(text)
    return {}


def _effect_buckets(history: str, records: list[dict[str, Any]], helpers: dict[str, Any]):
    actors = []
    commits = []
    coverage_rows = []
    held = []
    for record in records:
        fields = _record_fields(record, helpers["parse_body"])
        if record.get("surface") == "requested_command" and fields.get("history_id") == history:
            actors.append((record, fields))
        if (
            record.get("action") == "coverage_scan"
            and record.get("surface") == "service_log"
            and fields.get("history_id") == history
            and helpers["decides"](record, fields)
        ):
            coverage_rows.append((record, fields))
        if record.get("surface") == "committed_effect" and fields.get("history_id") == history:
            commits.append((record, fields))
            if helpers["held_sink"](record) and helpers["decides"](record, fields):
                held.append((record, fields))
    return actors, commits, helpers["agreed"](coverage_rows), held


def _projection_verdict(history: str, records: list[dict[str, Any]], helpers: dict[str, Any]) -> str:
    observations = helpers["project"](history, records)
    claim = helpers["claim_id"](history)
    polarities = [
        obs.get("literal_polarity")
        for obs in observations
        if claim in obs.get("literal_claims", [])
    ]
    if "refutes" in polarities:
        return "refuted"
    if "supports" in polarities:
        return "supported"
    return "unresolved"


def _ladder_verdicts(history: str, records: list[dict[str, Any]], helpers: dict[str, Any]) -> dict[str, str]:
    """Subsets of the retained admission rule. Each name is one stop-rule."""
    actors, commits, coverage, held = _effect_buckets(history, records, helpers)
    intact = [record for record in records if _intact_actor(record)]
    misbound_intact = [
        record
        for record in intact
        if helpers["misbound"](record, _record_fields(record, helpers["parse_body"]))
    ]
    any_decides = any(
        helpers["decides"](record, _record_fields(record, helpers["parse_body"])) for record in records
    )
    if any(fields.get("subject_class") == "unauthorized_effect" for _record, fields in held):
        subject = "refuted"
    elif any(fields.get("subject_class") == "authorized_effect" for _record, fields in held):
        subject = "supported"
    else:
        subject = "unresolved"
    absence = "supported" if helpers["absence"](coverage, actors, commits) else "unresolved"
    polarity = (
        "supported"
        if any(record.get("polarity") == "supports" for record, _fields in held)
        else "unresolved"
    )
    subject_or_absence = subject if subject != "unresolved" else absence
    polarity_or_absence = polarity if polarity != "unresolved" else absence
    if not intact:
        reject_misbound = "unresolved"
    elif len(misbound_intact) == len(intact):
        reject_misbound = "unresolved"
    else:
        reject_misbound = "supported"
    return {
        "intact_actor": "supported" if intact else "unresolved",
        "reject_misbound_actor": reject_misbound,
        "any_deciding_record": "supported" if any_decides else "unresolved",
        "held_effect_polarity": polarity,
        "subject_class": subject,
        "polarity_or_absence": polarity_or_absence,
        "subject_class_or_absence": subject_or_absence,
        "projection": _projection_verdict(history, records, helpers),
    }


def _scope_failure(fields: dict[str, str], coverage, actors, operations) -> str:
    if coverage is None:
        return "no_agreed_census"
    _record, covered = coverage
    actor_runs = {item[1].get("run_id") for item in actors if item[1].get("run_id")}
    if actor_runs and fields.get("run_id") not in actor_runs:
        return "run"
    if fields.get("run_id") != covered.get("run_id"):
        return "run"
    if fields.get("operation_id") not in operations(covered):
        return "operation"
    return "interval"


def _blocking_check(history: str, records: list[dict[str, Any]], helpers: dict[str, Any]) -> str:
    """Why subject-class-or-absence supports a probe the projection leaves unresolved."""
    from swarm_witness.native_comparison import (
        _binding_matches,
        _census_matches,
        _operations,
        _sink_in_scope,
    )

    actors, commits, coverage, held = _effect_buckets(history, records, helpers)
    authorized = [(record, fields) for record, fields in held if fields.get("subject_class") == "authorized_effect"]
    in_scope = [
        (record, fields)
        for record, fields in authorized
        if _sink_in_scope(record, fields, coverage, actors)
    ]
    bound = [
        (record, fields)
        for record, fields in in_scope
        if _binding_matches(record, fields, actors)
    ]
    unknown = [
        (record, fields)
        for record, fields in held
        if fields.get("subject_class") not in {"authorized_effect", "unauthorized_effect"}
        and _sink_in_scope(record, fields, coverage, actors)
    ]
    coverage_rows = [
        record
        for record in records
        if record.get("action") == "coverage_scan" and record.get("surface") == "service_log"
        and helpers["decides"](record, _record_fields(record, helpers["parse_body"]))
    ]
    if unknown and bound and _census_matches(coverage, held):
        return "unknown_subject_beside_authorized"
    if authorized and not in_scope:
        if len(coverage_rows) > 1 and coverage is None:
            return "disagreeing_census"
        if not coverage_rows:
            return "withheld_census"
        return "scope_" + _scope_failure(authorized[0][1], coverage, actors, _operations)
    if in_scope and not bound:
        return "binding"
    if bound and not _census_matches(coverage, held):
        return "census_count"
    return "other"


def _challenge_probes(helpers: dict[str, Any], summarize) -> dict[str, Any]:
    """Sixteen mutations of one source packet. Separate from the 48."""
    import importlib.util

    import yaml

    path = ROOT / "experiments" / "effect_witness" / "native_projection_challenge.py"
    spec = importlib.util.spec_from_file_location("native_projection_challenge_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the sixteen-case challenge")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    document = yaml.safe_load(module.CHALLENGE.read_text(encoding="utf-8"))
    history, _condition = document["source_packet"].split("/", 1)
    cases = module.build_cases(history)
    warrants = yaml.safe_load(
        (ROOT / "experiments" / "effect_witness" / "native_warrants_v1.yaml").read_text(encoding="utf-8")
    )
    holds = bool(warrants["histories"][history]["proposition_holds"])
    from swarm_witness.native_comparison import competent_verdict

    probes = []
    subject_rows = []
    projection_rows = []
    for case_id, case in document["cases"].items():
        records = cases[case_id]
        verdicts = _ladder_verdicts(history, records, helpers)
        checker = competent_verdict(history, records)["epistemic_status"]
        warrant = case["expected"]
        separated = verdicts["subject_class_or_absence"] != verdicts["projection"]
        probes.append(
            {
                "case_id": case_id,
                "warrant": warrant,
                "subject_class_or_absence": verdicts["subject_class_or_absence"],
                "projection": verdicts["projection"],
                "invariant_checker": checker,
                "separates_subject_from_projection": separated,
                "blocking_check": _blocking_check(history, records, helpers) if separated else None,
            }
        )
        base = {
            "proposition_holds": holds,
            "adjudicated": warrant,
            "attributed_origin": "undetermined",
            "warranted_origin": "undetermined",
        }
        subject_rows.append({**base, "predicted": verdicts["subject_class_or_absence"]})
        projection_rows.append({**base, "predicted": verdicts["projection"]})
    subject = summarize(subject_rows, truth_known=True)
    projection = summarize(projection_rows, truth_known=True)
    by_check: dict[str, list[str]] = {}
    for probe in probes:
        if probe["blocking_check"]:
            by_check.setdefault(probe["blocking_check"], []).append(probe["case_id"])
    return {
        "denominator": {
            "probes": len(probes),
            "source_packet": document["source_packet"],
            "dependence": "sixteen mutations of one discriminating-readback packet",
            "relation_to_48": "separate",
        },
        "subject_class_or_absence": {
            "unsupported_supports": subject["unsupported_support"],
            "false_proposition_supports": subject["false_proposition_support"],
            "correct_decisive": subject["correct_decisive"],
            "decisive_opportunities": subject["decisive_opportunities"],
            "correct_abstentions": subject["correct_abstention"],
        },
        "projection": {
            "unsupported_supports": projection["unsupported_support"],
            "false_proposition_supports": projection["false_proposition_support"],
            "correct_decisive": projection["correct_decisive"],
            "decisive_opportunities": projection["decisive_opportunities"],
            "correct_abstentions": projection["correct_abstention"],
        },
        "projection_mismatches_against_invariant_checker": sum(
            1 for probe in probes if probe["projection"] != probe["invariant_checker"]
        ),
        "projection_mismatches_against_warrant": sum(
            1 for probe in probes if probe["projection"] != probe["warrant"]
        ),
        "separating_cases": by_check,
        "probes": probes,
    }


def _score_named(retained_rows: list[dict[str, Any]], name: str, predicted: dict[tuple[str, str], str], summarize) -> dict[str, Any]:
    built = []
    for row in retained_rows:
        built.append({**row, "method": name, "predicted": predicted[(row["history"], row["stage"])]})
    summary = summarize(built, truth_known=True)
    misses = [
        {"history": row["history"], "stage": row["stage"], "predicted": row["predicted"], "warrant": row["adjudicated"]}
        for row in built
        if row["predicted"] != row["adjudicated"]
    ]
    return {
        "unsupported_supports": summary["unsupported_support"],
        "false_proposition_supports": summary["false_proposition_support"],
        "correct_decisive": summary["correct_decisive"],
        "decisive_opportunities": summary["decisive_opportunities"],
        "correct_abstentions": summary["correct_abstention"],
        "warrant_mismatches": misses,
    }


def measure(root: Path | None = None) -> dict[str, Any]:
    root = ROOT if root is None else Path(root)
    module = _renderer()
    from swarm_witness.comparison_score import summarize_method
    from swarm_witness.native_comparison import (
        _absence_bound,
        _agreed_coverage,
        _explicit_misbound,
        _held_sink,
        _parse_body,
        _premise_decides,
        p_effect_claim_id,
        project_packet_observations,
    )

    warrants = module.yaml.safe_load(
        (root / module.NATIVE_WARRANTS.relative_to(module.ROOT)).read_text(encoding="utf-8")
    )
    audit = module.yaml.safe_load(
        (root / module.AUDIT_PROTOCOL.relative_to(module.ROOT)).read_text(encoding="utf-8")
    )
    packets = module._load(root / module.HISTORICAL_PACKETS.relative_to(module.ROOT))
    rows = module._native_matched_rows(root, packets, warrants, audit)
    historical = module.score_native_method(rows, "swarm_witness")
    warrant = module.score_native_method(rows, "strong_invariant")
    retained_rows = [row for row in rows if row["method"] == "swarm_witness"]
    intact_rows = []
    for row in retained_rows:
        records = module._packet_records(root, row["history"], row["stage"])
        predicted = "supported" if any(_intact_actor(record) for record in records) else "unresolved"
        intact_rows.append({**row, "method": "intact_actor", "predicted": predicted})
    intact = summarize_method(intact_rows, truth_known=True)

    opened = []
    for row in retained_rows:
        if row["stage"] != "withheld_misbound":
            continue
        records = module._packet_records(root, row["history"], row["stage"])
        anatomy = _packet_anatomy(records, _parse_body, _premise_decides, _explicit_misbound)
        opened.append(
            {
                "history": row["history"],
                "stage": row["stage"],
                "retained_verdict": row["predicted"],
                "warrant": row["adjudicated"],
                "proposition_holds": row["proposition_holds"],
                **anatomy,
            }
        )
    supported = [item for item in opened if item["retained_verdict"] == "supported"]
    abstained = [item for item in opened if item["retained_verdict"] == "unresolved"]
    helpers = {
        "parse_body": _parse_body,
        "decides": _premise_decides,
        "misbound": _explicit_misbound,
        "held_sink": _held_sink,
        "agreed": _agreed_coverage,
        "absence": _absence_bound,
        "project": project_packet_observations,
        "claim_id": p_effect_claim_id,
    }
    by_rule: dict[str, dict[tuple[str, str], str]] = {}
    for row in retained_rows:
        verdicts = _ladder_verdicts(
            row["history"], module._packet_records(root, row["history"], row["stage"]), helpers
        )
        for name, predicted in verdicts.items():
            by_rule.setdefault(name, {})[(row["history"], row["stage"])] = predicted
    ladder = {
        name: _score_named(retained_rows, name, predicted, summarize_method)
        for name, predicted in by_rule.items()
    }
    strong_predicted = {
        (row["history"], row["stage"]): row["predicted"]
        for row in rows
        if row["method"] == "strong_invariant"
    }
    ladder_agreement = {
        name: sum(
            1
            for key, predicted in predicted_map.items()
            if predicted != by_rule["projection"][key]
        )
        for name, predicted_map in by_rule.items()
    }
    checker_mismatches = sum(
        1 for key, predicted in by_rule["projection"].items() if predicted != strong_predicted[key]
    )
    rule_disagreements = {
        "reject_misbound_actor_vs_any_deciding_record": sum(
            1
            for key, predicted in by_rule["reject_misbound_actor"].items()
            if predicted != by_rule["any_deciding_record"][key]
        )
    }
    challenge = _challenge_probes(helpers, summarize_method)
    return {
        "sprint": "AI x Epistemics Research Sprint",
        "sprint_url": "https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15",
        "track": "Track 2, Trust Infrastructure",
        "question": (
            "An actor log can already be intact. Does that record justify "
            "the effect conclusion, or does a consumer still have to admit "
            "the record as evidence?"
        ),
        "prior_work": "Swarm Witness Swarm Alignment submission",
        "denominator": {
            "histories": 12,
            "packets": historical["cell_count"],
            "dependence": "four views of twelve histories",
        },
        "intact_actor_consumer": {
            "signal": (
                "support P_effect when a requested-command record is locally "
                "held, custody intact, actor_binding bound, and has public bytes"
            ),
            "unsupported_supports": intact["unsupported_support"],
            "false_proposition_supports": intact["false_proposition_support"],
            "correct_decisive": intact["correct_decisive"],
            "decisive_opportunities": intact["decisive_opportunities"],
            "correct_abstentions": intact["correct_abstention"],
        },
        "retained_verdict_consumer": {
            "signal": "historical Swarm Witness P_effect verdict on the retained packet",
            "unsupported_supports": historical["unsupported_support"],
            "false_proposition_supports": historical["false_proposition_support"],
            "correct_decisive": historical["correct_decisive"],
            "decisive_opportunities": historical["decisive_opportunities"],
            "correct_abstentions": historical["correct_abstention"],
        },
        "admission_consumer": {
            "signal": "invariant checker on the same packet records, scored against the warrant",
            "unsupported_supports": warrant["unsupported_support"],
            "false_proposition_supports": warrant["false_proposition_support"],
            "correct_decisive": warrant["correct_decisive"],
            "decisive_opportunities": warrant["decisive_opportunities"],
            "correct_abstentions": warrant["correct_abstention"],
        },
        "retained_unsupported_supports": {
            "count": len(supported),
            "stage": "withheld_misbound",
            "deciding_records": sum(item["deciding_records"] for item in supported),
            "packets_with_intact_misbound_actor": sum(
                1 for item in supported if item["intact_misbound_actor_records"]
            ),
            "misbound_actor_only": [
                item["history"] for item in supported if item["shape"] == "misbound_actor_only"
            ],
            "withheld_effect_row": [
                item["history"] for item in supported if item["shape"] == "withheld_effect_row"
            ],
            "packets": supported,
        },
        "withheld_packet_where_retained_label_abstains": abstained,
        "admission_ladder": ladder,
        "ladder_mismatches_against_projection": ladder_agreement,
        "projection_mismatches_against_invariant_checker": checker_mismatches,
        "rule_disagreements": rule_disagreements,
        "challenge_probes": challenge,
        "reading": (
            "On these 48 packets, subject class on a held deciding effect, "
            "or the zero-row absence census, matches the projection and the "
            "invariant checker. Rejecting the misbound actor probe leaves the "
            "actor log able to support. A held effect labeled supports, "
            "without subject class, still supports the false proposition."
        ),
        "does_not_establish": [
            "that this 48-packet ladder is the SoundGate transfer test",
            "that the current evaluator replay replaces the historical count",
            "full-system equivalence of BMO and the SQLite gate",
            "that a withheld effect row labeled supports is why the retained verdict supports",
            "that scope, parent binding, and the non-zero census are idle outside these 48 packets",
            "that the sixteen challenge mutations are a new population",
        ],
    }


def _counts(block: dict[str, Any]) -> str:
    return (
        f"{block['unsupported_supports']} *unsupported supports*, "
        f"{block['false_proposition_supports']} supports of a false proposition, "
        f"{block['correct_decisive']}/{block['decisive_opportunities']} correct decisive conclusions, "
        f"and {block['correct_abstentions']} correct abstentions"
    )


def _note(result: dict[str, Any]) -> str:
    opened = result["retained_unsupported_supports"]
    abstained = result["withheld_packet_where_retained_label_abstains"]
    abstain_names = ", ".join(item["history"] for item in abstained)
    return "\n".join(
        [
            "# An intact actor log still needs admission",
            "",
            result["question"],
            "",
            "Track 2 of the AI x Epistemics sprint asks what is missing before a record of what an agent did can be trusted. This note scores three consumers on the retained Swarm Witness packets. It does not replace Table 2 or Table 2b.",
            "",
            "The intact-actor consumer supports `P_effect` whenever a requested-command record is locally held, custody intact, marked bound, and carrying public bytes. It has "
            + _counts(result["intact_actor_consumer"])
            + ".",
            "",
            "The retained-verdict consumer reads the historical Swarm Witness label. It has "
            + _counts(result["retained_verdict_consumer"])
            + ".",
            "",
            "The admission consumer runs the invariant checker on the same records. It has "
            + _counts(result["admission_consumer"])
            + ".",
            "",
            f"All {opened['count']} retained *unsupported supports* are `withheld_misbound` packets whose controlled proposition holds. Across them, deciding records sum to {opened['deciding_records']}. {opened['packets_with_intact_misbound_actor']} of them contain an actor record that meets the intact-actor test and that the admission rule marks misbound. {len(opened['misbound_actor_only'])} have no effect row. {len(opened['withheld_effect_row'])} have an effect row that is withheld, not locally held, and labeled supports.",
            "",
            f"One further `withheld_misbound` packet, {abstain_names}, has that withheld effect-row shape. The retained label there is unresolved, and the controlled proposition is false. A withheld row labeled supports does not by itself account for the eleven.",
            "",
            result["reading"],
            "",
            "The 48 packets remain four views of twelve histories. This ladder is not the SoundGate transfer test. BMO is not re-executed. The current evaluator replay stays a separate table.",
            "",
            "## Which check is carrying the warrant",
            "",
            "The same packets can be scored by smaller stop-rules. Counts are *unsupported supports*, supports of a false proposition, correct decisive conclusions, and correct abstentions.",
            "",
            "| Stop-rule | Unsupported support | False-proposition support | Correct decisive | Correct abstention |",
            "| --- | ---: | ---: | ---: | ---: |",
            _ladder_row(result, "reject_misbound_actor", "Intact actor, unless every such actor is the misbound probe"),
            _ladder_row(result, "held_effect_polarity", "Held deciding effect whose own label says supports"),
            _ladder_row(result, "subject_class", "Held deciding effect, read subject class, no absence census"),
            _ladder_row(result, "polarity_or_absence", "That support label, or the zero-row absence census"),
            _ladder_row(result, "subject_class_or_absence", "Subject class, or the zero-row absence census"),
            _ladder_row(result, "projection", "Full projection, including scope, binding, and census"),
            "",
            f"Subject class, or the absence census, mismatches the full projection on {result['ladder_mismatches_against_projection']['subject_class_or_absence']} packets. The projection mismatches the invariant checker on {result['projection_mismatches_against_invariant_checker']} packets. Inside this set, scope, parent binding, and the non-zero census change no verdict.",
            "",
            f"Subject class alone leaves {len(result['admission_ladder']['subject_class']['warrant_mismatches'])} warranted supports unresolved: both sink views of the four histories with no effect row. The support label, or the absence census, still supports the false proposition on {result['admission_ladder']['polarity_or_absence']['false_proposition_supports']} packets, both sink views of `aew-v1-h-local-pass-broader-effect`.",
            "",
            f"Rejecting the misbound probe, and otherwise trusting the actor log, still has {result['admission_ladder']['reject_misbound_actor']['unsupported_supports']} *unsupported supports*. On these packets that stop-rule makes the same calls as supporting whenever any record passes the deciding-premise check: the two rules differ on {result['rule_disagreements']['reject_misbound_actor_vs_any_deciding_record']} packets.",
            "",
            "## Where those idle checks fire",
            "",
            _challenge_paragraph(result),
            "",
            *_soundgate_lines(),
        ]
    )


def _soundgate_lines() -> list[str]:
    import importlib.util

    path = Path(__file__).resolve().parent / "transfer_soundgate.py"
    spec = importlib.util.spec_from_file_location("transfer_soundgate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the SoundGate transfer measurement")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    proof = module.protocol_transfer()
    by_policy = {row["policy"]: row for row in proof["claims"]}
    return [
        "## SoundGate representation probe",
        "",
        "Two SoundGate protocol claims are a separate denominator. Effect records are built from retained status, so this is a representation test, not independent external validation. The projection returns "
        f"{by_policy['barrier']['projection']} for the barrier and {by_policy['original']['projection']} for the original policy. "
        f"An intact-run rule has {proof['intact_run_unsupported_supports']} unsupported support on that pair. "
        "The strict policy is not in the warrant set.",
        "",
    ]


def _challenge_paragraph(result: dict[str, Any]) -> str:
    challenge = result["challenge_probes"]
    subject = challenge["subject_class_or_absence"]
    projection = challenge["projection"]
    groups = challenge["separating_cases"]
    lines = [
        f"The sixteen-case challenge is a separate denominator: {challenge['denominator']['dependence']}. It is not folded into the 48.",
        "",
        f"Subject class or the absence census has {subject['unsupported_supports']} *unsupported supports*, {subject['correct_decisive']}/{subject['decisive_opportunities']} correct decisive conclusions, and {subject['correct_abstentions']} correct abstentions. The projection has {projection['unsupported_supports']} *unsupported supports*, {projection['correct_decisive']}/{projection['decisive_opportunities']} correct decisive conclusions, and {projection['correct_abstentions']} correct abstentions. The projection mismatches the invariant checker on {challenge['projection_mismatches_against_invariant_checker']} probes and the challenge warrant on {challenge['projection_mismatches_against_warrant']}.",
        "",
        "The probes where subject class supports and the projection stays unresolved:",
        "",
    ]
    labels = {
        "scope_run": "Scope, run id",
        "scope_operation": "Scope, operation",
        "scope_interval": "Scope, interval",
        "binding": "Binding",
        "unknown_subject_beside_authorized": "Unknown subject beside an authorized sink",
        "disagreeing_census": "Disagreeing census",
        "withheld_census": "Withheld census",
    }
    for key, label in labels.items():
        names = ", ".join(groups.get(key, []))
        lines.append(f"- {label}: {names}")
    lines.extend(
        [
            "",
            "An exact duplicate census stays supported for both rules. A sink whose only subject is unknown stays unresolved for both. Misbinding, a spoofed line, an unauthenticated line, and a stale sink are already rejected by the deciding-premise check.",
        ]
    )
    return "\n".join(lines)


def _ladder_row(result: dict[str, Any], name: str, label: str) -> str:
    block = result["admission_ladder"][name]
    return (
        f"| {label} | {block['unsupported_supports']} | {block['false_proposition_supports']} | "
        f"{block['correct_decisive']}/{block['decisive_opportunities']} | {block['correct_abstentions']} |"
    )


def main() -> None:
    result = measure()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (OUT / "NOTE.md").write_text(_note(result), encoding="utf-8")
    print(json.dumps({
        "intact_actor_unsupported_supports": result["intact_actor_consumer"]["unsupported_supports"],
        "retained_unsupported_supports": result["retained_verdict_consumer"]["unsupported_supports"],
        "admission_unsupported_supports": result["admission_consumer"]["unsupported_supports"],
    }))


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    main()
