#!/usr/bin/env python3
"""Stage 5 compatibility runner that keeps user templates immutable.

The existing contact_state.py still owns validation, state updates and rendering.
For stage5-finalize this wrapper first asks contact_state.py for the deterministic
draft, then feeds that exact draft through the legacy finalize compatibility
boundary. Full-body humanized inputs are ignored. Optional humanizer use is
limited to model-generated dynamic fields before this wrapper is called.

The legacy runner hard-codes a full-body humanizer provenance label. Rather than
forking the large state runner, immutable finalization declares the audit source
through the runner's internal ``--audit-provenance`` input, so the finalize child
is always the real ``contact_state.py`` in its own install location. The caller
declares whether no polish happened or dynamic fields alone were polished.

Issue #68 does not give this wrapper a pack authority of its own: the caller's
professor-local ``--email-pack`` is forwarded unchanged to the internal
``stage5-plan`` and to the finalize runner, so the wrapper never scans
professor directories from an ``email_id`` and no program-level default exists to
fall back on. Plan r13 keeps the wrapper inside one owner's transaction: it
inherits only the current owner's ``email_pack``, the unchanged JSON file path
in ``--choices`` and optional ``email_id``. The internal plan and final runner
receive that same owner-local file path; this wrapper does not parse or
partition raw multi-professor choices. It never discovers sibling professors and never
rebuilds any cross-professor attribution data.
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
        if arg in {"--humanized", "--humanized-map", "--audit-provenance"}:
            # Legacy full-body inputs and the runner's internal audit-source
            # input are never caller inputs of this wrapper; drop them and its
            # own declared polish mode below decides the rendered label.
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


def _verify_provenance_needle() -> None:
    """Fail closed when the runner's audit-label contract changed.

    The wrapper no longer patches a source copy; it declares the audit source
    through the runner's own ``--audit-provenance`` input. This read-only check
    keeps the previous guard: the legacy business label must still be the one
    literal the runner renders when no polish mode is declared.
    """
    source = RUNNER.read_text(encoding="utf-8")
    if source.count(_PROVENANCE_NEEDLE) != 1:
        raise RuntimeError(
            "contact_state.py provenance marker changed; refusing to declare "
            "an unverified audit label")


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
            _verify_provenance_needle()
        except RuntimeError as exc:
            print(json.dumps({
                "status": "error", "reason_code": "stage5_provenance_patch_failed",
                "message": str(exc),
            }, ensure_ascii=False))
            return 1
        proc = subprocess.run(
            [sys.executable, str(RUNNER), *clean,
             "--humanized-map", str(map_path.resolve()),
             "--audit-provenance", polish_mode],
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
