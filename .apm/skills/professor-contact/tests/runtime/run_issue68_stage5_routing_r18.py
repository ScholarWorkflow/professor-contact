#!/usr/bin/env python3
"""PC68 Gate-2 r18 bridge.

The base runner stays authoritative. r18 keeps the merged shared fixture from
skills-test-fixtures #33, the r12 request builder and the r13 root final-source
channel, and rebinds the Codex verifier to the r18 owner business-input source:
the formal child's own ``commandExecution`` payload instead of the plaintext
child user message. The normal shared fixture parser is used unchanged; no
root-history wrapper or eval-server patch is part of this recipe.
"""
import build_issue68_codex_request_r12 as builder
import run_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r18 as verifier


FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"


def pin_base_runner():
    base.FIXTURE_SHA = FIXTURE_SHA
    base.build_request = builder.build_request
    base.verify_codex = verifier.verify_codex
    base.verify_opencode = verifier.verify_opencode
    return base


def main():
    pin_base_runner()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
