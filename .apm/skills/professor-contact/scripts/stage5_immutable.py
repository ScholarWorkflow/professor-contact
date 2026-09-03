#!/usr/bin/env python3
"""Stage 5 compatibility runner that keeps user templates immutable.

The existing contact_state.py still owns validation, state updates and rendering.
This wrapper removes the workflow's full-body humanizer boundary: for
stage5-finalize it first asks contact_state.py for the deterministic draft,
then feeds that exact draft back through the legacy --humanized-map input.
Therefore no model/humanizer can rewrite fixed template text. Optional prose
polish must happen earlier by editing only model-generated result JSON fields.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "contact_state.py"

_PLAN_OPTIONS = {
    "--program-root", "--email-pack", "--email-id", "--profile", "--template",
    "--followup-template", "--mode", "--result", "--choices",
}
_VALUE_OPTIONS = _PLAN_OPTIONS | {"--decision-file", "--humanized", "--humanized-map"}


def _delegate(args: list[str]) -> int:
    proc = subprocess.run([sys.executable, str(RUNNER), *args], text=True)
    return proc.returncode


def _strip_legacy_humanized(args: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(args):
        if args[i] in {"--humanized", "--humanized-map"}:
            i += 2
            continue
        out.append(args[i])
        i += 1
    return out


def _plan_args(finalize_args: list[str]) -> list[str]:
    out = ["stage5-plan"]
    i = 1
    while i < len(finalize_args):
        arg = finalize_args[i]
        if arg in _VALUE_OPTIONS:
            if i + 1 >= len(finalize_args):
                raise SystemExit(f"missing value for {arg}")
            if arg in _PLAN_OPTIONS:
                out.extend([arg, finalize_args[i + 1]])
            i += 2
            continue
        i += 1
    return out


def _immutable_finalize(args: list[str]) -> int:
    clean = _strip_legacy_humanized(args)
    plan = subprocess.run(
        [sys.executable, str(RUNNER), *_plan_args(clean)],
        text=True, capture_output=True, check=False,
    )
    if plan.returncode != 0:
        sys.stdout.write(plan.stdout)
        sys.stderr.write(plan.stderr)
        return plan.returncode
    try:
        payload = json.loads(plan.stdout)
    except json.JSONDecodeError:
        sys.stderr.write(plan.stderr)
        sys.stderr.write("stage5-plan did not return JSON\n")
        return 1
    drafts = payload.get("drafts")
    if payload.get("status") != "ok" or not isinstance(drafts, list) or not drafts:
        sys.stdout.write(plan.stdout)
        return 1

    with tempfile.TemporaryDirectory(prefix="professor-contact-stage5-") as temp:
        root = Path(temp)
        mapping: dict[str, str] = {}
        for index, row in enumerate(drafts):
            output_id = row.get("output_id")
            draft = row.get("draft")
            if not isinstance(output_id, str) or not isinstance(draft, str):
                print(json.dumps({
                    "status": "error", "reason_code": "invalid_stage5_draft",
                    "message": "stage5-plan returned malformed draft",
                }, ensure_ascii=False))
                return 1
            path = root / f"draft-{index}.txt"
            path.write_text(draft, encoding="utf-8")
            mapping[output_id] = str(path.resolve())
        map_path = root / "immutable-map.json"
        map_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(RUNNER), *clean, "--humanized-map", str(map_path.resolve())],
            text=True, capture_output=True, check=False,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return _delegate(args)
    if args[0] == "stage5-finalize":
        return _immutable_finalize(args)
    return _delegate(args)


if __name__ == "__main__":
    raise SystemExit(main())
