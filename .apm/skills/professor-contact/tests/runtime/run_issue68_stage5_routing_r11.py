#!/usr/bin/env python3
"""PC68 Gate-2 r11 entrypoint with formal Codex root-history evidence.

This keeps the r10 runner and product oracle unchanged.  The only override is
shared test infrastructure: pin the fixture revision that can consume
``output.root_thread_read`` and route the Codex adapter invocation through its
root-history wrapper.  Identity diagnostics remain non-gating.
"""
from pathlib import Path

import run_issue68_stage5_routing as base

FIXTURE_SHA = "cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04"
_ORIGINAL_RUN = base.run


def run(argv, cwd, prefix, *, env=None, timeout=180):
    command = list(argv)
    if len(command) >= 2 and Path(command[1]).name == "parse_codex_eval_evidence.py":
        fixture_root = Path(command[1]).resolve().parents[1]
        command[1] = str(fixture_root / "scripts" / "parse_codex_eval_evidence_with_root_history.py")
        command.extend(
            [
                "--root-history-contract",
                str(fixture_root / "configs" / "codex-root-thread-read-contract.json"),
            ]
        )
    return _ORIGINAL_RUN(command, cwd, prefix, env=env, timeout=timeout)


def main():
    base.FIXTURE_SHA = FIXTURE_SHA
    base.run = run
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
