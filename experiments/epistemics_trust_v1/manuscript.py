"""Sprint report rendered from the retained trust measurement.

The prose is fixed. The counts are read from the measurement so a changed
packet changes the report instead of leaving a stale number.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

TITLE = "An Intact Actor Log Is Not an Effect Warrant"

CHECK_LABELS = {
    "scope_run": "scope, run id",
    "scope_operation": "scope, operation",
    "scope_interval": "scope, interval",
    "binding": "binding",
    "unknown_subject_beside_authorized": "an unknown subject beside an authorized sink",
    "disagreeing_census": "a disagreeing census",
    "withheld_census": "a withheld census",
}


def _score(block: dict[str, Any], abstentions: int) -> str:
    return (
        f"{block['unsupported_supports']} | {block['false_proposition_supports']} | "
        f"{block['correct_decisive']}/{block['decisive_opportunities']} | "
        f"{block['correct_abstentions']}/{abstentions}"
    )


def _row(label: str, block: dict[str, Any], abstentions: int) -> str:
    return f"| {label} | {_score(block, abstentions)} |"


def abstract_text(manuscript: str) -> str:
    match = re.search(r"^## Abstract\n\n(.+?)\n\n## ", manuscript, re.M | re.S)
    if match is None:
        raise ValueError("the manuscript has no Abstract section")
    return match.group(1).strip()


def word_count(text: str) -> int:
    return len(text.split())


def _transfer_paragraph() -> str:
    import importlib.util

    path = Path(__file__).resolve().parent / "transfer_soundgate.py"
    spec = importlib.util.spec_from_file_location("transfer_soundgate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the SoundGate transfer measurement")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    transfer = module.protocol_transfer()
    tally = module.measure()
    by_policy = {row["policy"]: row for row in transfer["claims"]}
    return (
        f"Empirical transfer uses two SoundGate protocol claims, revision `{transfer['source_revision']}`. "
        "The barrier warrant is the README success criterion, supported. The original-policy warrant is the stated bug, refuted. "
        "Case status is used only to build effect records. The existing projection returns "
        f"{by_policy['barrier']['projection']} for the barrier and {by_policy['original']['projection']} for the original policy. "
        f"An intact-run rule supports both, so it has {transfer['intact_run_unsupported_supports']} unsupported support. "
        "The strict policy has no protocol warrant and is not in this score. "
        f"A same-field tally on the {tally['rows']} rows still shows {tally['restriction']['intact_run']['unsupported_supports']} "
        f"and {tally['availability']['intact_run']['unsupported_supports']} intact-run unsupported supports; "
        "that tally is not the two-claim comparison. The 48 and the 16 stay separate. The November experiments stay not tested."
    )


def render_manuscript(result: dict[str, Any]) -> str:
    intact = result["intact_actor_consumer"]
    retained = result["retained_verdict_consumer"]
    admission = result["admission_consumer"]
    opened = result["retained_unsupported_supports"]
    ladder = result["admission_ladder"]
    challenge = result["challenge_probes"]
    subject = challenge["subject_class_or_absence"]
    projection = challenge["projection"]
    groups = challenge["separating_cases"]
    separations = []
    for key, label in CHECK_LABELS.items():
        names = groups.get(key) or []
        if names:
            separations.append(f"{label} ({', '.join(names)})")
    separation_sentence = "; ".join(separations)
    unresolved_48 = result["denominator"]["packets"] - intact["decisive_opportunities"]
    unresolved_16 = challenge["denominator"]["probes"] - subject["decisive_opportunities"]
    actor_records = sum(item["intact_misbound_actor_records"] for item in opened["packets"])
    packets_with_two = sum(1 for item in opened["packets"] if item["intact_misbound_actor_records"] > 1)
    abstract = (
        "Delegated agents leave logs of what they were allowed to do. This report asks whether an intact actor log "
        "warrants the conclusion that an unauthorized effect did not commit. The packets, warrants, invariant checker, "
        "and sixteen-case challenge are preexisting Swarm Witness material. The sprint-new work scores alternate "
        "stop-rules on those retained records. It does not replace Table 2 or Table 2b of the November submission. "
        f"On {result['denominator']['packets']} packets, {result['denominator']['dependence']}, subject class on a held "
        "deciding effect, or a zero-row absence census, matches the projection and the invariant checker. Subject class "
        f"alone leaves {len(ladder['subject_class']['warrant_mismatches'])} warranted supports unresolved. A support label "
        f"plus that census still supports a false proposition on {ladder['polarity_or_absence']['false_proposition_supports']} "
        "packets. The intact-actor predicate holds on every packet, so supporting from it supports all "
        f"{result['denominator']['packets']}. On a separate challenge of {challenge['denominator']['probes']} mutations of "
        f"one source packet, subject class supports {subject['unsupported_supports']} probes the projection leaves unresolved. "
        "Those are unsupported supports inside the sixteen, not a new denominator. The nine are scope, binding, an unknown "
        "subject beside an authorized sink, and the census. On two SoundGate protocol claims, the existing projection matches the protocol warrant, and an intact-run rule supports the claim that warrant refutes."
    )
    return "\n".join(
        [
            f"# {TITLE}",
            "",
            "**Author:** Jonathan Maye-Hobbs",
            "**Affiliation:** Independent",
            "",
            "With Apart Research",
            "",
            "## Abstract",
            "",
            abstract,
            "",
            "## 1 Introduction",
            "",
            result["question"],
            "",
            "Track 2 of the AI x Epistemics Research Sprint [2] asks what is missing before a record of what an agent did can be trusted. A tamper-evident copy of an actor log preserves the bytes the actor already wrote. Preservation is a copy. The open question is which check has to succeed before those bytes support the effect claim.",
            "",
            "The measurement uses retained records from the Swarm Alignment submission [1]. It does not re-execute BMO, and it does not replace Table 2 or Table 2b of that submission. The historical label's "
            f"{retained['unsupported_supports']} unsupported supports remain Table 2.",
            "",
            "## 2 Preexisting work and sprint-new work",
            "",
            "Preexisting, relative to November 13–15, 2026: BMO, the SQLite gate, the twelve application histories, the 48 packets, the evidence-stage warrants, the historical Swarm Witness labels, the invariant checker, and the sixteen-case projection challenge. The challenge ledger is not rewritten.",
            "",
            "Sprint-new: the consumer ladder in `experiments/epistemics_trust_v1/run.py`, the record-level reading of the eleven, and this report. The ladder calls the preexisting admission predicates. It does not add a packet to the 48.",
            "",
            "## 3 Method",
            "",
            f"The first denominator is {result['denominator']['packets']} packets: {result['denominator']['dependence']}. Each packet is scored for `P_effect` against the evidence-stage warrant. An unsupported support is a supported output whose warrant is refuted or unresolved. A correct decisive conclusion agrees with a supported or refuted warrant. A correct abstention returns unresolved where the warrant is unresolved. Supports of a false proposition are counted separately, using the controlled truth already stored with the warrants.",
            "",
            "Five stop-rules are scored on those packets.",
            "",
            "The intact-actor rule supports `P_effect` when a requested-command record is locally held, custody intact, marked bound, and carrying public bytes. On this corpus that predicate holds on every packet, so the rule supports every packet. The historical-label rule reads the retained Swarm Witness verdict. The misbound-probe rule uses the intact-actor test and withholds support when every such actor record is the misbound probe. The subject-class rule reads a held deciding effect: unauthorized refutes, authorized supports, and anything else stays unresolved. When subject class is unresolved, the zero-row absence census can still support the claim if it covers the actor events and no commit row is held. Those two checks are alternatives in one stop-rule. The projection is the preexisting observation rule. The invariant checker scores that projection, so their agreement is agreement inside one pipeline.",
            "",
            f"The second denominator is the preexisting sixteen-case challenge: {challenge['denominator']['dependence']}. Its source packet is `{challenge['denominator']['source_packet']}`. Those sixteen probes are not added to the {result['denominator']['packets']}.",
            "",
            "The commands below run in the working tree that produced this report. Public commit `d406f4e` of https://github.com/instagrim-dev/swarm-witness does not yet contain `experiments/epistemics_trust_v1/`.",
            "",
            "```bash",
            "python experiments/epistemics_trust_v1/run.py",
            "python -m pytest tests/test_epistemics_trust_v1.py tests/test_epistemics_trust_report.py -q",
            "```",
            "",
            "## 4 Results",
            "",
            f"The consumer table scores the {result['denominator']['packets']} packets. Correct abstention uses the {unresolved_48} unresolved warrants as its denominator. Correct decisive uses the {intact['decisive_opportunities']} warranted decisive conclusions. The intact-actor predicate holds on every packet.",
            "",
            "| Consumer | Unsupported support | False-proposition support | Correct decisive | Correct abstention |",
            "| --- | ---: | ---: | ---: | ---: |",
            _row("Intact actor record", intact, unresolved_48),
            _row("Historical Swarm Witness label", retained, unresolved_48),
            _row("Invariant checker", admission, unresolved_48),
            "",
            f"The historical {retained['unsupported_supports']} and the checker's {admission['unsupported_supports']} are November Table 2, with Table 2b the later replay of the same files. This table adds the intact-actor row. It does not replace those two.",
            "",
            f"All {opened['count']} historical unsupported supports are `{opened['stage']}` packets whose controlled proposition holds. Deciding records across them sum to {opened['deciding_records']}. "
            f"All {opened['packets_with_intact_misbound_actor']} packets contain an actor record that meets the intact-actor test and that admission marks misbound: {actor_records} records, with {packets_with_two} packets holding two. "
            f"{len(opened['misbound_actor_only'])} have no effect row, so a withheld row labeled supports does not explain the set. This note does not establish why the retained verdict supported the other {len(opened['withheld_effect_row'])}. "
            "One further withheld packet, `aew-v1-h-local-pass-broader-effect`, has that withheld effect row. The historical label there is unresolved, and the controlled proposition is false.",
            "",
            "The next rows are alternate stop-rules on the same packets. A later row is not the previous row with one check removed.",
            "",
            "| Stop-rule | Unsupported support | False-proposition support | Correct decisive | Correct abstention |",
            "| --- | ---: | ---: | ---: | ---: |",
            _row("Intact actor, unless every such actor is the misbound probe", ladder["reject_misbound_actor"], unresolved_48),
            _row("Held deciding effect whose own label says supports", ladder["held_effect_polarity"], unresolved_48),
            _row("Subject class, no absence census", ladder["subject_class"], unresolved_48),
            _row("Support label, or the zero-row absence census", ladder["polarity_or_absence"], unresolved_48),
            _row("Subject class, or the zero-row absence census", ladder["subject_class_or_absence"], unresolved_48),
            _row("Full projection", ladder["projection"], unresolved_48),
            "",
            f"Subject class, or the zero-row absence census, mismatches the projection on {result['ladder_mismatches_against_projection']['subject_class_or_absence']} of these packets. The projection and the invariant checker differ on {result['projection_mismatches_against_invariant_checker']} packets. That agreement is inside one pipeline. "
            f"Subject class alone leaves {len(ladder['subject_class']['warrant_mismatches'])} warranted supports unresolved: both sink views of the four histories with no effect row. "
            f"The support label, or the absence census, still supports the false proposition on {ladder['polarity_or_absence']['false_proposition_supports']} packets, both sink views of `aew-v1-h-local-pass-broader-effect`. "
            f"Rejecting the misbound probe and otherwise trusting the actor log still has {ladder['reject_misbound_actor']['unsupported_supports']} unsupported supports.",
            "",
            f"The sixteen-case challenge is a separate denominator. Its cases are the preexisting mutations in `experiments/effect_witness/native_projection_challenge_v1.yaml`. Subject class or the absence census has {subject['unsupported_supports']} unsupported supports, {subject['correct_decisive']}/{subject['decisive_opportunities']} correct decisive conclusions, and {subject['correct_abstentions']}/{unresolved_16} correct abstentions. "
            f"The projection has {projection['unsupported_supports']} unsupported supports, {projection['correct_decisive']}/{projection['decisive_opportunities']} correct decisive conclusions, and {projection['correct_abstentions']}/{unresolved_16} correct abstentions. "
            f"The projection mismatches the challenge warrant on {challenge['projection_mismatches_against_warrant']} probes. Its agreement with the invariant checker, {challenge['projection_mismatches_against_invariant_checker']} mismatches, is the same pipeline.",
            "",
            f"The probes where subject class supports and the projection stays unresolved are unsupported supports inside the sixteen: {separation_sentence}.",
            "",
            "An exact duplicate census stays supported for both rules. A sink whose only subject is unknown stays unresolved for both. A misbound sink, a spoofed line, an unauthenticated line, and a stale sink fail the deciding-premise check here. The historical challenge label for the spoofed sink stays supported in the v1 ledger. That ledger is not rewritten.",
            "",
            "## 5 Discussion",
            "",
            "An intact copy of the actor log preserves the record the first consumer trusts. On these 48 packets, admission does not treat that intact actor record as the effect warrant. The record is still present on packets the checker supports. Subject class on a held deciding effect, or the zero-row absence census, matches the projection and the warrant on all 48. Subject class alone misses the eight absence supports. The support-label-or-census rule still has two supports of a false proposition.",
            "",
            "The sixteen-case challenge is a different question. Subject class supports nine probes the projection leaves unresolved. Those nine are a count inside the sixteen: three scope checks, three binding checks, an unknown subject beside an authorized sink, and two census checks. Only the mapped-actor probe keeps a parent link. A withheld census is not a non-zero census count. Scope, parent binding, and the non-zero census do not cover the nine. The two denominators stay apart.",
            "",
            _transfer_paragraph(),
            "",
            "## References",
            "",
            "1. Maye-Hobbs, J. Swarm Witness: evidence for agent authorization. Swarm Alignment submission, November 2026. Repository: https://github.com/instagrim-dev/swarm-witness",
            "2. Apart Research. AI x Epistemics Research Sprint, 13–15 November 2026. https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15",
            "",
            "## Appendix A Limitations and dual use",
            "",
            f"The {result['denominator']['packets']} packets are {result['denominator']['dependence']}. They are not a population rate and not an estimate of deployment reliability. The sixteen challenge rows are mutations of `{challenge['denominator']['source_packet']}`, so they are one source packet under sixteen edits. Warrants and controlled truth are author specified. The two SoundGate claims encode case status into effect records, leave out the strict policy, and do not change the November experiments. The current evaluator replay of the 48 remains a separate table and does not replace the historical "
            f"{retained['unsupported_supports']}.",
            "",
            "Subject class, or the zero-row absence census, matches the projection on these 48 packets. The same stop-rule still returns support on nine preexisting probes in the sixteen. Scope, parent binding, and a non-zero census do not describe all nine. A later packet can separate checks that agree on the 48.",
            "",
            "The records are synthetic controls on one host. No personal data is used. The dual-use of the result is the sufficiency claim itself: a consumer who stops at subject class or a zero-row census will match the checker on these 48 and will still support the nine probes. The probes are the preexisting challenge, retained so the checks can be rerun.",
            "",
            "## LLM Usage Statement",
            "",
            "The author set the question, the denominators, and which conclusions the retained records were allowed to support. AI assistants contributed research design, the consumer ladder, validation scripts, and drafting of this report. The counts are produced by `experiments/epistemics_trust_v1/run.py`. The author is responsible for the claims, interpretation, and released artifacts.",
            "",
        ]
    )
