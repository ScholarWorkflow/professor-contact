#!/usr/bin/env python3
"""PC68 Gate-2 r19 bridge.

The base runner stays authoritative. r19 keeps the merged shared fixture from
skills-test-fixtures #33, the r12 request builder, the r13 root final-source
channel and the r18 stage5 command-surface reader, and rebinds the Codex
verifier to the r19 owner-local consumption and root partition oracle: the
formal child's own stage5 command texts carry the one-professor packet it
consumed, and the root must partition deterministically exactly once. There
is no r19 opencode verifier, so the rebound ``verify_opencode`` refuses to
run: r19 verifies the codex host only. The normal shared fixture parser is
used unchanged; no root-history wrapper or eval-server patch is part of this
recipe.
"""
import build_issue68_codex_request_r12 as builder
import run_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r19 as verifier


FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"


def verify_opencode(*args, **kwargs):
    raise ValueError("r19 verifies the codex host only")


def pin_base_runner():
    base.FIXTURE_SHA = FIXTURE_SHA
    base.build_request = builder.build_request
    base.verify_codex = verifier.verify_codex
    base.verify_opencode = verify_opencode
    return base


def main():
    pin_base_runner()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
