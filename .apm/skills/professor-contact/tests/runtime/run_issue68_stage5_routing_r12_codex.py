#!/usr/bin/env python3
"""PC68-R1 codex-only formal entrypoint (Gate-2 r12, 2026-10-04 scope).

Per the authoritative record `issue-68-gate2-r12-2026-10-04` (2026-10-04
scope adjustment), the current formal `PC68-R1` run keeps only the Codex
host: no multi-host execution and no combined verdict. The final verdict
is the Codex host verdict passed through unchanged. The generic two-host
runner commands are no longer execution instructions, and a
`--preflight-host` run is a pre-execution check, never formal acceptance.

The frozen base pipeline stays authoritative. This entrypoint rebinds it
in-process to the r12 assets exactly like the r12 bridge (consensus
request builder, last-message final-source verifier, fixture root-history
parser wrapper, frozen fixture), then executes `codex_host` once. A
minimal capability check is a separate precondition step; it is not part
of this formal entry and never counts as acceptance.
"""
import argparse
import json
import signal
import subprocess
import sys
from pathlib import Path

import run_issue68_stage5_routing as base
import run_issue68_stage5_routing_r12 as bridge

HERE = Path(__file__).resolve().parent
FIXTURE_SHA = bridge.FIXTURE_SHA
CONTRACT = HERE / "issue68-runtime-evidence-contract-r12.json"
CONTRACT_REVISION = "issue-68-runtime-evidence-r12-2026-10-04"
CONTRACT_RUNNER = ".apm/skills/professor-contact/tests/runtime/" + Path(__file__).name
EXECUTION_KIND = "acceptance"
HOST = "codex"
CASE = "PC68-R1"


def load_contract():
    """Validate the frozen r12 evidence contract names this unique entry."""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("revision") != CONTRACT_REVISION:
        raise ValueError("contract_revision_mismatch")
    if contract.get("fixture_sha") != FIXTURE_SHA:
        raise ValueError("contract_fixture_mismatch")
    if contract.get("runner") != CONTRACT_RUNNER:
        raise ValueError("contract_runner_is_not_this_entry")
    if contract.get("manual_patch") != "no":
        raise ValueError("contract_manual_patch_forbidden")
    return contract


def check_entry_uniqueness(argv0=None):
    """The formal run must be invoked through this entrypoint only."""
    invoked = Path(argv0 if argv0 is not None else sys.argv[0]).resolve()
    if invoked != Path(__file__).resolve():
        raise ValueError("entrypoint_uniqueness_violated")
    return True


def pin():
    """Bind the frozen pipeline to the r12 assets (same bridge as r12)."""
    return bridge.pin_base_runner()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--producer-sha", required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--fixture-sha", required=True)
    parser.add_argument("--eval-direnv-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    args.producer_root = args.producer_root.resolve()
    return args


def main(argv=None):
    pin()
    args = parse_args(argv)
    output = args.output_dir.resolve()
    result = {"state": "CASE_NOT_STARTED", "reason_code": "bootstrap_failed"}
    if output.exists() and any(output.iterdir()):
        print(json.dumps({"state": "CASE_NOT_STARTED", "reason_code": "output_directory_not_empty"}))
        return 2
    output.mkdir(parents=True, exist_ok=True)
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, base.stop_active)
    try:
        if output.is_relative_to(args.producer_root) or args.producer_root.is_relative_to(output):
            raise ValueError("output_must_be_outside_producer")
        check_entry_uniqueness()
        contract = load_contract()
        if args.fixture_sha != FIXTURE_SHA:
            raise ValueError("missing_or_wrong_frozen_fixture_arguments")
        args.fixture_root = args.fixture_root.resolve()
        args.eval_direnv_root = args.eval_direnv_root.resolve()
        provenance = {"producer": base.clean_revision(args.producer_root, args.producer_sha),
                      "manual_patch": "no", "execution_kind": EXECUTION_KIND, "case": CASE,
                      "host": HOST, "entrypoint": Path(__file__).name,
                      "single_request_no_retry": "yes", "contract_revision": contract["revision"]}
        provenance["fixture"] = base.clean_revision(args.fixture_root, FIXTURE_SHA)
        base.write_json(output / "provenance.json", provenance)
        base.progress("只执行 Codex 宿主；单次正式请求，失败不重试、不换服务、不换模型、不改断言")
        host = base.codex_host(args, output)
        base.write_json(output / "codex-verdict.json", host)
        result = host
        base.clean_revision(args.producer_root, args.producer_sha)
        base.clean_revision(args.fixture_root, FIXTURE_SHA)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result = ({"state": "CASE_NOT_STARTED", "reason_code": str(exc)} if not base.started_evidence(output)
                  else base.verdict("INVALID_TEST_EXECUTION", "revision_or_execution_changed", detail=str(exc)))
    except SystemExit as exc:
        result = (base.verdict("INVALID_TEST_EXECUTION", "execution_cancelled", exit_code=exc.code)
                  if base.started_evidence(output)
                  else {"state": "CASE_NOT_STARTED", "reason_code": "bootstrap_cancelled"})
    finally:
        base.stop_active()
        base.write_json(output / "final-verdict.json", result)
    base.progress("结束：" + result.get("verdict", result["state"]))
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
