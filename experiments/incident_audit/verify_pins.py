#!/usr/bin/env python3
"""Check corpus pins against the committed manifest and, with --fetch, the web.

Full Hugging Face HTML responses are not a content pin: they embed a rotating
window.requestId. The pin is the response after that assignment is replaced
with a fixed token. OpenAI's readability digest is not rechecked: a direct
GET is HTTP 403 and those bytes are not in the repo. Quotes for that blog are
bound to passage windows instead.

--fetch uses the network. The unit tests call the pure checks only.
"""

from __future__ import annotations

import hashlib
import html
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

EXP = Path(__file__).resolve().parent

# Digests reproduced by GET on 2026-11-07. Hugging Face is request-id-normalized.
REPRODUCED_PINS = {
    "metr_html": "37ec7c48dc11ba00e048e079b161e99d4cdf7c279ed6d0290a0494c81d9a740f",
    "metr_pdf": "f7e87133833363da6eee661df0c86926ef852f8b202ad87695ea6596b92d3c73",
    "huggingface_request_id_normalized": (
        "56e032289828592741ab7721130c6fe47d1e54f463d81917c8a1905d3b679012"
    ),
    "apart_html": "4a63ccdc3efe69a12e9c51aa25882199b3c8c7bead9be1635e987db987328247",
}

REQUIRED_SOURCE_FIELDS = (
    "url",
    "publication_date",
    "retrieval_date",
    "redaction_scope",
    "provenance",
    "access",
)

UNAVAILABLE_TELEMETRY = (
    "artifactory_message_board_dump",
    "agent_transcripts",
    "huggingface_platform_logs",
)

_REQUEST_ID = re.compile(br'window\.requestId = "[^"]*"')
_NORMALIZED_REQUEST_ID = b'window.requestId = "NORMALIZED"'


def normalize_huggingface_html(data: bytes) -> bytes:
    """Replace the per-response request id so two GETs of the same page agree."""
    found = _REQUEST_ID.findall(data)
    if len(found) != 1:
        raise ValueError(f"expected one window.requestId, found {len(found)}")
    return _REQUEST_ID.sub(_NORMALIZED_REQUEST_ID, data, count=1)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quote_in_unescaped(quote: str, raw: bytes) -> bool:
    """True when quote is a contiguous substring of the entity-decoded text."""
    text = html.unescape(raw.decode("utf-8", errors="replace"))
    return quote in text


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _source(manifest: dict, source_id: str) -> dict:
    for source in manifest["sources"]:
        if source["id"] == source_id:
            return source
    raise KeyError(source_id)


def recorded_pin_errors(manifest: dict) -> list[str]:
    """The committed digests must be the ones a same-day GET reproduced."""
    errors: list[str] = []
    metr = _source(manifest, "metr")
    hf = _source(manifest, "huggingface")
    apart = _source(manifest, "apart")
    checks = {
        "metr_html": metr["html"]["sha256"],
        "metr_pdf": metr["pdf_not_parsed"]["sha256"],
        "huggingface_request_id_normalized": hf["html"]["request_id_normalized_sha256"],
        "apart_html": apart["html"]["sha256"],
    }
    for name, digest in checks.items():
        if digest != REPRODUCED_PINS[name]:
            errors.append(f"{name} digest {digest} != reproduced {REPRODUCED_PINS[name]}")
    html_pin = hf["html"]
    if html_pin.get("full_response_sha256_reproducible") is not False:
        errors.append("huggingface full-response digest is marked reproducible")
    if html_pin.get("sha256"):
        errors.append("huggingface still publishes an unstable full-response sha256 as sha256")
    openai = _source(manifest, "openai")
    retrieval = openai["readability_retrieval"]
    if retrieval.get("bytes_in_repo") is not False or retrieval.get("live_recheck") is not False:
        errors.append("openai readability digest is marked as bytes we can recheck")
    if openai["direct_get"]["status"] != 403:
        errors.append("openai direct_get status is not 403")
    return errors


def passage_errors(excerpts: dict, passages: dict) -> list[str]:
    errors: list[str] = []
    by_id = {item["id"]: item for item in passages["passages"]}
    seen: set[str] = set()
    for obs in excerpts["observations"]:
        seen.add(obs["id"])
        passage = by_id.get(obs["id"])
        if passage is None:
            errors.append(f"{obs['id']} has no passage pin")
            continue
        if passage.get("source_id") != obs["source_id"]:
            errors.append(f"{obs['id']} passage source {passage.get('source_id')}")
        synthetic = bool(obs.get("synthetic"))
        if bool(passage.get("synthetic")) != synthetic:
            errors.append(f"{obs['id']} synthetic flag disagrees with the passage pin")
            continue
        if synthetic:
            continue
        text = passage["text"]
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != passage["sha256"]:
            errors.append(f"{obs['id']} passage sha256 does not match its text")
        if obs["quote"] not in text:
            errors.append(f"{obs['id']} quote is not a substring of its passage")
    extra = sorted(set(by_id) - seen)
    if extra:
        errors.append(f"passage pins without observations: {extra}")
    return errors


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def manifest_errors(manifest: dict, excerpts: dict) -> list[str]:
    errors: list[str] = []
    for source in manifest["sources"]:
        for field in REQUIRED_SOURCE_FIELDS:
            if not _present(source.get(field)):
                errors.append(f"{source.get('id')} missing {field}")
    unavailable = {item["id"] for item in manifest.get("unavailable", [])}
    for telemetry_id in UNAVAILABLE_TELEMETRY:
        if telemetry_id not in unavailable:
            errors.append(f"unavailable telemetry {telemetry_id} is not recorded")
    for obs in excerpts["observations"]:
        if obs.get("access_level") == "raw_telemetry_public":
            errors.append(f"{obs['id']} claims raw_telemetry_public")
        if obs.get("synthetic") and obs["source_id"] not in {
            item["id"] for item in manifest.get("synthetic_fixtures", [])
        }:
            errors.append(f"{obs['id']} synthetic source is not declared")
    errors.extend(recorded_pin_errors(manifest))
    return errors


def _get(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "swarm-witness-corpus-pin/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def fetch_errors(manifest: dict, excerpts: dict) -> list[str]:
    """Re-GET the stable pins. Does not treat an OpenAI 403 as a retrieved body."""
    errors: list[str] = []
    metr = _source(manifest, "metr")
    status, body = _get(metr["url"])
    if status != 200 or sha256(body) != metr["html"]["sha256"]:
        errors.append(
            f"metr html status {status} sha256 {sha256(body)} != {metr['html']['sha256']}"
        )
    else:
        _quotes(errors, "metr", body, excerpts)
    pdf = metr["pdf_not_parsed"]
    status, body = _get(pdf["url"])
    if status != 200 or sha256(body) != pdf["sha256"]:
        errors.append(f"metr pdf status {status} sha256 {sha256(body)} != {pdf['sha256']}")
    hf = _source(manifest, "huggingface")
    status, body = _get(hf["url"])
    if status != 200:
        errors.append(f"huggingface status {status}")
    else:
        normalized = normalize_huggingface_html(body)
        digest = sha256(normalized)
        expected = hf["html"]["request_id_normalized_sha256"]
        if digest != expected:
            errors.append(f"huggingface normalized sha256 {digest} != {expected}")
        else:
            _quotes(errors, "huggingface", body, excerpts)
    apart = _source(manifest, "apart")
    status, body = _get(apart["url"])
    if status != 200 or sha256(body) != apart["html"]["sha256"]:
        errors.append(
            f"apart html status {status} sha256 {sha256(body)} != {apart['html']['sha256']}"
        )
    openai = _source(manifest, "openai")
    status, _body = _get(openai["url"])
    if status != openai["direct_get"]["status"]:
        errors.append(f"openai direct GET status {status} != recorded {openai['direct_get']['status']}")
    return errors


def _quotes(errors: list[str], source_id: str, body: bytes, excerpts: dict) -> None:
    for obs in excerpts["observations"]:
        if obs["source_id"] != source_id or obs.get("synthetic"):
            continue
        if not quote_in_unescaped(obs["quote"], body):
            errors.append(f"{obs['id']} quote is not in the unescaped {source_id} retrieval")


def main(argv: list[str]) -> int:
    manifest = _load(EXP / "corpus_manifest.yaml")
    excerpts = _load(EXP / "excerpts_v1.yaml")
    passages = _load(EXP / "pinned_passages.yaml")
    errors = manifest_errors(manifest, excerpts)
    errors.extend(passage_errors(excerpts, passages))
    if "--fetch" in argv:
        errors.extend(fetch_errors(manifest, excerpts))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("corpus pins ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
