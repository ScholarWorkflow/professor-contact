#!/usr/bin/env python3
"""Stage 5 compatibility runner that keeps user templates immutable.

The existing contact_state.py still owns validation, state updates and rendering.
For stage5-finalize this wrapper first asks contact_state.py for the deterministic
draft, then feeds that exact draft through the legacy finalize compatibility
boundary. Full-body humanized inputs are ignored. Optional humanizer use is
limited to model-generated dynamic fields before this wrapper is called.

The legacy runner hard-codes a full-body humanizer provenance label. Rather than
forking the large state runner, immutable finalization executes a temporary copy
whose only source change is that audit label. The caller declares whether no
polish happened or dynamic fields alone were polished.

Issue #68 does not give this wrapper a pack authority of its own: the caller's
professor-local ``--email-pack`` is forwarded unchanged to the internal
``stage5-plan`` and to the temporary finalize runner, so the wrapper never scans
professor directories from an ``email_id`` and no program-level default exists to
fall back on. Plan r13 keeps the wrapper inside one owner's transaction: it
inherits only the current owner's ``email_pack``, the unchanged JSON file path
in ``--choices`` and optional ``email_id``. The internal plan and final runner
receive that same owner-local file path; this wrapper does not parse or
partition raw multi-professor choices. It never discovers sibling professors and never
rebuilds any cross-professor attribution data.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "contact_state.py"
UPSTREAM_SCRIPT_ENV = "PROFESSOR_CONTACT_EVIDENCE_SCRIPT"

_PLAN_OPTIONS = {
    "--program-root", "--email-pack", "--email-id", "--profile", "--template",
    "--followup-template", "--mode", "--result", "--choices",
}
_VALUE_OPTIONS = _PLAN_OPTIONS | {"--decision-file"}
_POLISH_MODES = {"none", "dynamic-fields-only"}
_PROVENANCE_NEEDLE = " ｜ 过稿: humanizer-ja(business)"


def _delegate(args: list[str]) -> int:
    proc = subprocess.run([sys.executable, str(RUNNER), *args], text=True)
    return proc.returncode


def _wrapper_options(args: list[str]) -> tuple[str, list[str]]:
    """Remove wrapper/legacy-only options and return the declared polish mode."""
    out: list[str] = []
    polish_mode = "none"
    seen_polish = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in {"--humanized", "--humanized-map"}:
            if i + 1 >= len(args):
                raise SystemExit(f"missing value for {arg}")
            i += 2
            continue
        if arg == "--polish-mode":
            if i + 1 >= len(args):
                raise SystemExit("missing value for --polish-mode")
            if seen_polish:
                raise SystemExit("--polish-mode may be supplied only once")
            polish_mode = args[i + 1]
            if polish_mode not in _POLISH_MODES:
                raise SystemExit(
                    "--polish-mode must be one of: none, dynamic-fields-only")
            seen_polish = True
            i += 2
            continue
        out.append(arg)
        i += 1
    return polish_mode, out


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


def _provenance_label(polish_mode: str) -> str:
    if polish_mode == "none":
        return "none"
    return "humanizer-ja(dynamic-fields-only)"


def _runner_with_provenance(root: Path, polish_mode: str) -> Path:
    source = RUNNER.read_text(encoding="utf-8")
    if source.count(_PROVENANCE_NEEDLE) != 1:
        raise RuntimeError(
            "contact_state.py provenance marker changed; refusing an unverified patch")
    source = source.replace(
        _PROVENANCE_NEEDLE,
        f" ｜ 过稿: {_provenance_label(polish_mode)}",
        1,
    )
    path = root / "contact_state_stage5_immutable.py"
    path.write_text(source, encoding="utf-8")
    return path


def _child_env_with_checker() -> dict[str, str] | None:
    """Env for the temporary finalize-runner copy. The copy's __file__ lives
    in a scratch directory, so the installed-layout checker locator cannot
    resolve from there; pin the checker resolved from the real runner's own
    location via the documented injection point. Returns None (no change)
    when an explicit locator is already set or none can be resolved."""
    if os.environ.get(UPSTREAM_SCRIPT_ENV, "").strip():
        return None
    spec = importlib.util.spec_from_file_location(
        "contact_state_locator_for_stage5_wrapper", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checker = module.upstream_check_script()
    if checker is None:
        return None
    return {**os.environ, UPSTREAM_SCRIPT_ENV: str(checker)}


def _immutable_finalize(args: list[str]) -> int:
    polish_mode, clean = _wrapper_options(args)
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
        try:
            finalize_runner = _runner_with_provenance(root, polish_mode)
        except RuntimeError as exc:
            print(json.dumps({
                "status": "error", "reason_code": "stage5_provenance_patch_failed",
                "message": str(exc),
            }, ensure_ascii=False))
            return 1
        proc = subprocess.run(
            [sys.executable, str(finalize_runner), *clean,
             "--humanized-map", str(map_path.resolve())],
            text=True, capture_output=True, check=False,
            env=_child_env_with_checker() or os.environ,
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
