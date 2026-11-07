import importlib.util
import io
import shutil
from contextlib import redirect_stderr
from pathlib import Path

import yaml

from swarm_witness.schema import validate_result_record

ROOT = Path(__file__).resolve().parents[1]


def _load_check_evidence():
    spec = importlib.util.spec_from_file_location(
        "check_evidence", ROOT / "scripts" / "check_evidence.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_all_results_present_and_valid():
    for claim_id in ("r1", "r2", "r3"):
        path = ROOT / "evidence" / claim_id / "result.yaml"
        assert path.is_file(), f"missing {path}"
        rec = validate_result_record(yaml.safe_load(path.read_text(encoding="utf-8")))
        assert (ROOT / rec.evidence_path).is_file()


def test_summary_json_present_for_each_claim():
    for claim_id in ("r1", "r2", "r3"):
        summary = ROOT / "evidence" / claim_id / "summary.json"
        assert summary.is_file(), f"missing {summary}"


def test_index_labels_match_result_yaml():
    index_path = ROOT / "evidence" / "index.yaml"
    assert index_path.is_file()
    rows = yaml.safe_load(index_path.read_text(encoding="utf-8"))["results"]
    by_id = {str(r["claim_id"]): str(r["label"]) for r in rows}
    assert set(by_id) == {"r1", "r2", "r3"}
    for claim_id in ("r1", "r2", "r3"):
        result_path = ROOT / "evidence" / claim_id / "result.yaml"
        rec = validate_result_record(yaml.safe_load(result_path.read_text(encoding="utf-8")))
        assert by_id[claim_id] == rec.label, (
            f"index fabricates label for {claim_id}: index={by_id[claim_id]!r} "
            f"result={rec.label!r}"
        )


def test_invalid_result_does_not_crash_main(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "evidence", tmp_path / "evidence")
    (tmp_path / "evidence" / "r1" / "result.yaml").write_text(
        "not: valid: yaml: [[", encoding="utf-8"
    )
    ce = _load_check_evidence()
    monkeypatch.setattr(ce, "ROOT", tmp_path)
    err = io.StringIO()
    with redirect_stderr(err):
        code = ce.main()
    assert code == 1
    out = err.getvalue()
    assert "FAIL" in out
    assert "r1" in out and "result.yaml" in out
