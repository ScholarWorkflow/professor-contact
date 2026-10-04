#!/usr/bin/env python3
"""PC68 Gate-2 r12 entrypoint.

The base runner remains frozen. This bridge pins the approved fixture, obtains
formal Codex root history, routes final-result judging through the r12 verifier,
and builds the Codex request from the current project-consensus model profile.
"""
from pathlib import Path

import run_issue68_stage5_routing as base

FIXTURE_SHA = "cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04"
_ORIGINAL_RUN = base.run


def run(argv, cwd, prefix, *, env=None, timeout=180):
    command = list(argv)
    if len(command) >= 2:
        name = Path(command[1]).name
        runtime_dir = Path(__file__).resolve().parent
        if name == "parse_codex_eval_evidence.py":
            fixture_root = Path(command[1]).resolve().parents[1]
            command[1] = str(fixture_root / "scripts" / "parse_codex_eval_evidence_with_root_history.py")
            command.extend([
                "--root-history-contract",
                str(fixture_root / "configs" / "codex-root-thread-read-contract.json"),
            ])
        elif name == "verify_issue68_stage5_routing.py":
            command[1] = str(runtime_dir / "verify_issue68_stage5_routing_r12.py")
        elif name == "build_issue68_codex_request.py":
            command[1] = str(runtime_dir / "build_issue68_codex_request_r12.py")
    return _ORIGINAL_RUN(command, cwd, prefix, env=env, timeout=timeout)


def main():
    base.FIXTURE_SHA = FIXTURE_SHA
    base.run = run
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
