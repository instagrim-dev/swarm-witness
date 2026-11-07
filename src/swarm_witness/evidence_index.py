"""Derive evidence index and check Claim/Run/Finding consistency."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from swarm_witness.schema import Finding, Run, validate_claim, validate_finding, validate_run

SUCCESS_LABELS = frozenset(
    {
        "reproduced",
        "classical_baseline_matches",
        "contradicted_in_scope",
    }
)
# Labels that assert a completed comparison / replication need completed runs.
REQUIRE_COMPLETED = frozenset({"reproduced", "classical_baseline_matches"})
# Labels that may honestly cite missing/failed/unrun arms.
ALLOW_NON_COMPLETED = frozenset({"assumption_dependent", "unresolved", "contradicted_in_scope"})


@dataclass(frozen=True)
class EvidenceTree:
    claims: dict[str, Any]
    pins: dict[str, Any]
    runs: dict[str, Run]
    run_raw: dict[str, dict[str, Any]]
    findings: list[Finding]
    finding_raw: list[dict[str, Any]]
    finding_paths: list[Path]
    result_mirrors: dict[str, dict[str, Any]]
    summaries: dict[str, dict[str, Any]]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_evidence_tree(root: Path) -> EvidenceTree:
    claims: dict[str, Any] = {}
    claims_dir = root / "claims"
    if claims_dir.is_dir():
        for path in sorted(claims_dir.glob("*.yaml")):
            data = _read_yaml(path) or {}
            claim = validate_claim(data)
            if claim.id in claims:
                raise ValueError(f"duplicate claim id {claim.id!r} in {path}")
            claims[claim.id] = claim

    pins_path = root / "artifacts" / "pins.yaml"
    pins = _read_yaml(pins_path) if pins_path.is_file() else {}
    if pins is None:
        pins = {}
    if not isinstance(pins, dict):
        raise ValueError("artifacts/pins.yaml must be a mapping")

    runs: dict[str, Run] = {}
    run_raw: dict[str, dict[str, Any]] = {}
    evidence_dir = root / "evidence"
    if evidence_dir.is_dir():
        for path in sorted(evidence_dir.glob("*/runs/*.json")):
            raw = _read_json(path)
            run = validate_run(raw)
            if run.id in runs:
                raise ValueError(f"duplicate run id {run.id!r} in {path}")
            runs[run.id] = run
            run_raw[run.id] = raw if isinstance(raw, dict) else {}

    findings: list[Finding] = []
    finding_raw: list[dict[str, Any]] = []
    finding_paths: list[Path] = []
    if evidence_dir.is_dir():
        for path in sorted(evidence_dir.glob("*/findings/*.json")):
            raw = _read_json(path)
            finding = validate_finding(raw)
            findings.append(finding)
            finding_raw.append(raw if isinstance(raw, dict) else {})
            finding_paths.append(path)

    result_mirrors: dict[str, dict[str, Any]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    if evidence_dir.is_dir():
        for slot in sorted(p for p in evidence_dir.iterdir() if p.is_dir()):
            result_path = slot / "result.yaml"
            if result_path.is_file():
                data = _read_yaml(result_path) or {}
                if isinstance(data, dict):
                    result_mirrors[slot.name] = data
            summary_path = slot / "summary.json"
            if summary_path.is_file():
                data = _read_json(summary_path)
                if isinstance(data, dict):
                    summaries[slot.name] = data

    return EvidenceTree(
        claims=claims,
        pins=pins,
        runs=runs,
        run_raw=run_raw,
        findings=findings,
        finding_raw=finding_raw,
        finding_paths=finding_paths,
        result_mirrors=result_mirrors,
        summaries=summaries,
    )


def resolve_observation_ref(runs: dict[str, Run], ref: str) -> Any:
    """Resolve `{run_id}.observations.{dotted.path}` into a run observation value."""
    marker = ".observations."
    if marker not in ref:
        raise ValueError(f"observation ref must contain '.observations.': {ref!r}")
    run_id, path = ref.split(marker, 1)
    if not run_id or not path:
        raise ValueError(f"malformed observation ref: {ref!r}")
    if run_id not in runs:
        raise KeyError(f"unknown run_id in observation ref: {run_id!r}")
    cur: Any = runs[run_id].observations
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(f"observation path not found: {ref}")
        cur = cur[part]
    return cur


def _pin_ok(claim_id: str, source_pin: str, claim: Any, pins: dict[str, Any]) -> bool:
    pin = str(source_pin).strip()
    if not pin:
        return False
    versions = set()
    if claim is not None:
        versions.add(str(claim.source_version).strip())
    entry = pins.get(claim_id)
    if isinstance(entry, dict):
        for key in ("source_revision", "git_rev", "source_pin"):
            val = entry.get(key)
            if isinstance(val, str) and val.strip():
                versions.add(val.strip())
    if not versions:
        return True  # no pin registered; cannot refute
    for ver in versions:
        if pin == ver or ver.startswith(pin) or pin.startswith(ver):
            return True
    return False


def _is_unresolved_only_observations(obs: dict[str, Any]) -> bool:
    if not obs:
        return True
    status = obs.get("status")
    if status == "unresolved":
        return True
    if obs.get("unresolved") is True:
        return True
    # Only soft/notes fields with no concrete metric/decision payload.
    soft = {"notes", "partial_output", "status", "unresolved"}
    hard_keys = [k for k in obs if k not in soft]
    if not hard_keys:
        return True
    return all(obs.get(k) is None for k in hard_keys)


def _summary_is_unresolved_only(summary: dict[str, Any] | None) -> bool:
    if not summary:
        return False
    if summary.get("unresolved") is True:
        return True
    if summary.get("status") == "unresolved":
        return True
    return False


def expected_index_from_findings(findings: list[Finding]) -> dict[str, Any]:
    """Build index.yaml payload from findings (authoritative labels)."""
    by_claim: dict[str, Finding] = {}
    for finding in findings:
        prior = by_claim.get(finding.claim_id)
        if prior is not None and prior.label != finding.label:
            # Keep deterministic order: first finding wins for index; checker flags conflict.
            continue
        if prior is None:
            by_claim[finding.claim_id] = finding
    results = [
        {
            "claim_id": claim_id,
            "label": finding.label,
            "finding_id": finding.id,
        }
        for claim_id, finding in sorted(by_claim.items())
    ]
    return {"results": results}


def generate_and_write_index(root: Path) -> dict[str, Any]:
    tree = load_evidence_tree(root)
    payload = expected_index_from_findings(tree.findings)
    index_path = root / "evidence" / "index.yaml"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return payload


def _check_finding(
    finding: Finding,
    *,
    claims: dict[str, Any],
    pins: dict[str, Any],
    runs: dict[str, Run],
    summaries: dict[str, dict[str, Any]],
    finding_path: Path | None,
) -> list[str]:
    errors: list[str] = []
    where = finding.id if finding_path is None else f"{finding.id} ({finding_path})"

    claim = claims.get(finding.claim_id)
    if claim is None:
        errors.append(f"{where}: unregistered claim_id {finding.claim_id!r}")
    elif claim.id != finding.claim_id:
        errors.append(f"{where}: claim file id {claim.id!r} != finding.claim_id")

    for run_id in finding.run_ids:
        if run_id not in runs:
            errors.append(f"{where}: missing run_id {run_id!r}")
            continue
        run = runs[run_id]
        if claim is not None and run.claim_id != finding.claim_id:
            errors.append(
                f"{where}: run {run_id} claim_id {run.claim_id!r} != finding claim_id"
            )
        if finding.label in REQUIRE_COMPLETED and run.execution_status != "completed":
            errors.append(
                f"{where}: label {finding.label!r} requires completed run, "
                f"got {run.execution_status!r} for {run_id}"
            )
        elif finding.label == "contradicted_in_scope" and run.execution_status not in {
            "completed",
            "failed",
        }:
            errors.append(
                f"{where}: contradicted_in_scope run {run_id} status "
                f"{run.execution_status!r} not completed|failed"
            )
        elif (
            finding.label not in ALLOW_NON_COMPLETED
            and finding.label not in REQUIRE_COMPLETED
            and finding.label != "contradicted_in_scope"
            and run.execution_status
            not in {"completed", "missing", "failed", "unrun", "attempted"}
        ):
            errors.append(
                f"{where}: unexpected execution_status {run.execution_status!r} for {run_id}"
            )

        if not _pin_ok(finding.claim_id, run.source_pin, claim, pins):
            errors.append(
                f"{where}: run {run_id} source_pin {run.source_pin!r} "
                f"does not match claim/pins for {finding.claim_id}"
            )

    if finding.label != "unresolved":
        for ref in finding.supporting_observation_refs:
            try:
                value = resolve_observation_ref(runs, ref)
            except (KeyError, ValueError) as exc:
                errors.append(f"{where}: supporting ref {ref!r} unresolved: {exc}")
                continue
            if finding.label in SUCCESS_LABELS and value is None:
                errors.append(
                    f"{where}: supporting ref {ref!r} is null under label {finding.label!r}"
                )

    if finding.label in REQUIRE_COMPLETED:
        for run_id in finding.run_ids:
            run = runs.get(run_id)
            if run is None:
                continue
            if _is_unresolved_only_observations(run.observations):
                errors.append(
                    f"{where}: label reproduced/match cannot rest on unresolved-only "
                    f"observations in run {run_id}"
                )

        # Slot summary under evidence/<slot>/ if present.
        for slot_name, summary in summaries.items():
            # Heuristic: summary belongs to finding when claim_id matches slot or finding path.
            if finding.claim_id == slot_name or (
                finding_path is not None and slot_name in finding_path.parts
            ):
                if _summary_is_unresolved_only(summary):
                    errors.append(
                        f"{where}: label {finding.label!r} incompatible with "
                        f"unresolved-only summary in evidence/{slot_name}/summary.json"
                    )

    return errors


def _check_metrics_against_runs(
    *,
    claim_id: str,
    metrics: dict[str, Any],
    finding: Finding,
    runs: dict[str, Run],
    source: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(metrics, dict) or not metrics:
        return errors
    linked = [runs[rid] for rid in finding.run_ids if rid in runs]
    for key, reported in metrics.items():
        for run in linked:
            if key not in run.observations:
                continue
            observed = run.observations[key]
            if observed != reported:
                errors.append(
                    f"{source}: metric {key!r} for {claim_id} disagrees with "
                    f"run {run.id} observations ({reported!r} != {observed!r})"
                )
    # Also: supporting observation values must equal metrics when the leaf name matches.
    for ref in finding.supporting_observation_refs:
        leaf = ref.rsplit(".", 1)[-1]
        if leaf not in metrics:
            continue
        try:
            observed = resolve_observation_ref(runs, ref)
        except (KeyError, ValueError):
            continue
        if observed != metrics[leaf]:
            errors.append(
                f"{source}: metric {leaf!r} for {claim_id} disagrees with "
                f"observation ref {ref} ({metrics[leaf]!r} != {observed!r})"
            )
    return errors


def check_consistency(root: Path) -> list[str]:
    """Return human-readable consistency errors (empty ⇒ pass)."""
    errors: list[str] = []
    try:
        tree = load_evidence_tree(root)
    except Exception as exc:
        return [f"failed to load evidence tree: {exc}"]

    if not tree.findings:
        errors.append("no findings under evidence/*/findings/")

    # Conflicting labels for same claim_id.
    labels_by_claim: dict[str, set[str]] = {}
    for finding in tree.findings:
        labels_by_claim.setdefault(finding.claim_id, set()).add(finding.label)
    for claim_id, labels in labels_by_claim.items():
        if len(labels) > 1:
            errors.append(
                f"claim_id {claim_id}: conflicting finding labels {sorted(labels)}"
            )

    for finding, path in zip(tree.findings, tree.finding_paths, strict=True):
        errors.extend(
            _check_finding(
                finding,
                claims=tree.claims,
                pins=tree.pins,
                runs=tree.runs,
                summaries=tree.summaries,
                finding_path=path,
            )
        )

    # result.yaml / summary metrics vs observations for findings of that claim.
    findings_by_claim: dict[str, list[Finding]] = {}
    for finding in tree.findings:
        findings_by_claim.setdefault(finding.claim_id, []).append(finding)

    for slot, mirror in tree.result_mirrors.items():
        claim_id = str(mirror.get("claim_id") or slot)
        metrics = mirror.get("metrics") or {}
        label = mirror.get("label")
        for finding in findings_by_claim.get(claim_id, []):
            if label is not None and label != finding.label:
                errors.append(
                    f"evidence/{slot}/result.yaml: label {label!r} != "
                    f"finding {finding.id} label {finding.label!r}"
                )
            if finding.label != "unresolved":
                errors.extend(
                    _check_metrics_against_runs(
                        claim_id=claim_id,
                        metrics=metrics if isinstance(metrics, dict) else {},
                        finding=finding,
                        runs=tree.runs,
                        source=f"evidence/{slot}/result.yaml",
                    )
                )

    for slot, summary in tree.summaries.items():
        claim_id = str(summary.get("claim_id") or slot)
        # Treat overlapping metric-like keys in summary against runs.
        metric_keys = {
            k: v
            for k, v in summary.items()
            if k
            not in {
                "notes",
                "status",
                "unresolved",
                "authoritative_finding",
                "fresh_run",
                "source_revision",
                "denominator_source",
                "pairs",
                "finding_id",
                "label",
                "claim_id",
                "protocol_id",
                "bmo_git_rev",
                "cases_path",
            }
            and not isinstance(v, (dict, list))
        }
        for finding in findings_by_claim.get(claim_id, []):
            if finding.label == "unresolved":
                continue
            errors.extend(
                _check_metrics_against_runs(
                    claim_id=claim_id,
                    metrics=metric_keys,
                    finding=finding,
                    runs=tree.runs,
                    source=f"evidence/{slot}/summary.json",
                )
            )

    # Index must be generated from findings (no hand-maintained authority).
    expected = expected_index_from_findings(tree.findings)
    index_path = root / "evidence" / "index.yaml"
    if not index_path.is_file():
        errors.append(f"missing {index_path} (generate from findings)")
    else:
        try:
            loaded = _read_yaml(index_path) or {}
        except Exception as exc:
            errors.append(f"invalid index.yaml: {exc}")
            loaded = None
        if loaded is not None and loaded != expected:
            errors.append(
                "evidence/index.yaml disagrees with findings-derived index "
                "(regenerate; do not hand-edit labels)"
            )

    return errors
