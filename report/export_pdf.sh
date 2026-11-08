#!/usr/bin/env bash
# Compatibility entrypoint for the canonical manuscript build.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${REPO_ROOT}/scripts/build_submission_variants.sh" "$@"
