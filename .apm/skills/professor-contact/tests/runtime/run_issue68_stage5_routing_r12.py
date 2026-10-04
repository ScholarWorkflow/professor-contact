#!/usr/bin/env python3
"""PC68 Gate-2 r12 entrypoint.

The base runner remains frozen. This entrypoint pins the approved fixture,
rewrites the pipeline's only subprocess judging dependency (the Codex shared
parser) to the fixture root-history wrapper, and rebinds the base runner's
in-process request builder and final-source verifiers to the r12
implementations, so formal execution actually builds the request from the
current project-consensus model and judges the final business source fixed to
the last message.
"""
from pathlib import Path

import build_issue68_codex_request_r12 as builder
import run_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r12 as verifier

FIXTURE_SHA = "cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04"
_ORIGINAL_RUN = base.run


def run(argv, cwd, prefix, *, env=None, timeout=180):
    command = list(argv)
    if len(command) >= 2 and Path(command[1]).name == "parse_codex_eval_evidence.py":
        fixture_root = Path(command[1]).resolve().parents[1]
        command[1] = str(fixture_root / "scripts" / "parse_codex_eval_evidence_with_root_history.py")
        command.extend([
            "--root-history-contract",
            str(fixture_root / "configs" / "codex-root-thread-read-contract.json"),
        ])
    return _ORIGINAL_RUN(command, cwd, prefix, env=env, timeout=timeout)


def pin_base_runner():
    """Rebind the frozen base runner's in-process calls to the r12 assets.

    codex_host()/opencode_host() call build_request, verify_codex and
    verify_opencode as base-runner module attributes without any subprocess
    hop, so argv rewriting cannot reach them. The OpenCode evidence parser is
    the host's only subprocess judging dependency and passes through run()
    unchanged. Formal execution must observe the consensus request builder and
    the last-message final-source verifiers, therefore the base runner module
    attributes are rebound before base.main() runs.
    """
    base.FIXTURE_SHA = FIXTURE_SHA
    base.run = run
    base.build_request = builder.build_request
    base.verify_codex = verifier.verify_codex
    base.verify_opencode = verifier.verify_opencode
    return base


def main():
    pin_base_runner()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
