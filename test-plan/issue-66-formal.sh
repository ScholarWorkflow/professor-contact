#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "$BASH_SOURCE")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
cd -- "$repo_root"
exec uv run --no-project python -B \
  "$repo_root/.apm/skills/professor-contact/tests/runtime/issue66_execution.py" \
  --repository "$repo_root" "$@"
