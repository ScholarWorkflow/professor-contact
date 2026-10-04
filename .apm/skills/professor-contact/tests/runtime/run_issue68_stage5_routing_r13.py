#!/usr/bin/env python3
"""PC68 Gate-2 r13 bridge.

The base runner stays authoritative. r13 pins the merged shared fixture from
skills-test-fixtures #33, keeps its normal shared parser unchanged, and rebinds
only the request builder plus Codex final-source verifier. No root-history
wrapper or eval-server patch is part of this recipe.
"""
import build_issue68_codex_request_r12 as builder
import run_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r13 as verifier


FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"


def pin_base_runner():
    base.FIXTURE_SHA = FIXTURE_SHA
    base.build_request = builder.build_request
    base.verify_codex = verifier.verify_codex
    return base


def main():
    pin_base_runner()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
