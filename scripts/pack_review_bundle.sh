#!/usr/bin/env bash
# Package the current paper, evidence, and reproduction sources.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 - "${ROOT}" <<'PY'
import re
import shlex
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

root = Path(sys.argv[1])
bundle_name = "swarm-witness-review-bundle"
out_dir = root / "dist"
output = out_dir / f"{bundle_name}.zip"

trees = (
    "artifacts", "baselines", "claims", "docs", "evidence", "experiments",
    "protocol", "report", "scenarios", "scripts", "src", "tests", "theory",
)
root_files = ("README.md", "pyproject.toml", "LICENSE", "PREEXISTING.md", "CHECKLIST.md")
required_files = (
    *root_files,
    "evidence/ACCESS.md",
    "report/ABSTRACT.md",
    "report/body.md",
    "report/LIMITATIONS_DUAL_USE.md",
    "report/SOURCES.md",
    "report/official-template.docx",
    "report/fonts/OldStandardTT-regular.ttf",
    "report/fonts/OldStandardTT-bold.ttf",
    "report/fonts/OldStandardTT-italic.ttf",
    *(f"report/{stem}.{extension}"
      for stem in ("Swarm_Witness_Final_Submission", "Swarm_Witness_Templated_Submission")
      for extension in ("md", "docx", "pdf")),
)
missing = [path for path in trees if not (root / path).is_dir()]
missing += [path for path in required_files if not (root / path).is_file()]
if missing:
    sys.exit("Missing required bundle inputs:\n" + "\n".join(f"  {path}" for path in missing))

excluded_names = {
    ".git", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "__pycache__", ".DS_Store", ".bmo-session-fences", "node_modules",
    ".worktrees", "worktrees",
    "bmo_work", "classical_work", "tree", "REASSESSMENT.md",
    f"{bundle_name}.zip",
}


def excluded(directory, names):
    omitted = []
    for name in names:
        relative = (Path(directory) / name).relative_to(root)
        if (
            name in excluded_names
            or name.endswith((".pyc", ".pyo"))
            or name == ".env"
            or (name.startswith(".env.") and name != ".env.example")
            or (relative.parts[0] == "report" and (
                name in {"archive", "alternatives", "slides"}
                or name.startswith(("Swarm_Witness_Apart_Submission.", "Swarm_Witness_Slides."))
                or name.startswith(("_build", "_templated_build", "_slides_build"))
            ))
        ):
            omitted.append(name)
    return omitted


def validate_advertised_paths(staging):
    text = (root / "evidence/ACCESS.md").read_text(encoding="utf-8")
    boundary = re.search(r"^## Pack a portable review bundle\s*$", text, re.M)
    if boundary is None:
        sys.exit("evidence/ACCESS.md is missing the portable review-bundle section")
    section = text[:boundary.start()]
    paths = set()
    last = None

    def add_path(token):
        token = token.strip("'\"")
        if (
            not token or token.startswith(("<", "/", ".venv", "dist/", "-"))
            or "://" in token or token.endswith(".zip")
            or any(char.isspace() for char in token)
        ):
            return
        if "/" in token or (root / token).exists():
            paths.add(token.rstrip("/"))

    for token in re.findall(r"`([^`]+)`", section):
        token = token.strip()
        if re.fullmatch(r"\.[A-Za-z0-9]+", token) and last and "." in Path(last).name:
            token = str(Path(last).with_suffix(token))
        add_path(token)
        if token in paths:
            last = token

    # Local Markdown links are relative to evidence/ACCESS.md.
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", section):
        target = target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("/"):
            continue
        resolved = (root / "evidence" / target).resolve()
        if resolved.is_relative_to(root):
            add_path(resolved.relative_to(root).as_posix())

    for fence in re.findall(r"```(?:bash|sh)?\n(.*?)```", section, re.S):
        for line in fence.replace("\\\n", " ").splitlines():
            for token in shlex.split(line, comments=True):
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
                    token = token.split("=", 1)[1]
                if "/" in token or token == "src":
                    add_path(token)

    if not paths:
        sys.exit("No advertised paths parsed from evidence/ACCESS.md")
    missing = sorted(path for path in paths if not (staging / path).exists())
    if missing:
        sys.exit("Advertised paths missing from bundle:\n" + "\n".join(f"  {path}" for path in missing))
    return len(paths)


out_dir.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix=".review-bundle-", dir=out_dir) as temporary:
    staging = Path(temporary) / bundle_name
    staging.mkdir()
    for tree in trees:
        shutil.copytree(root / tree, staging / tree, ignore=excluded, symlinks=True)
    archive_index = root / "report/archive/README.md"
    if archive_index.is_file():
        (staging / "report/archive").mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive_index, staging / "report/archive/README.md")
    for filename in root_files:
        shutil.copy2(root / filename, staging / filename)
    for filename in ("CITATION.cff", "CITATION.md", "NOTICE", ".gitignore"):
        if (root / filename).is_file():
            shutil.copy2(root / filename, staging / filename)

    advertised_count = validate_advertised_paths(staging)
    archive = Path(temporary) / output.name
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(staging.rglob("*")):
            if path.is_symlink():
                sys.exit(f"Bundle input is a symbolic link: {path.relative_to(staging)}")
            bundle.write(path, Path(bundle_name) / path.relative_to(staging))
    archive.replace(output)

print(f"Wrote {output}")
print(f"Validated {advertised_count} advertised paths")
PY
