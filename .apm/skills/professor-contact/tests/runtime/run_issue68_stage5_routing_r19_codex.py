#!/usr/bin/env python3
"""PC68-R1 Codex-only formal entrypoint (Gate-2 r19).

r19 keeps the r13 request, the r12 request builder, the merged shared fixture
adapter, the r13 root final-source selector and the r14 service/storage
isolation enforcement. It rebinds the Codex verifier to the r19 owner-local
consumption and root partition oracle: every formal child must consume exactly
its own one-professor packet (its own email_pack and choices rows, never a
sibling marker or a choices_scope field) through its own stage5 command
surface, and the root must run the deterministic stage5-partition-choices
entry exactly once with bundles that match the manifest partition record. The
contract freezes these conditions as owner_input_isolation,
canonical_preservation and partition_evidence. Before the acceptance request
the entry proves that the listening eval service comes from the frozen clean
checkout and uses test-only persistent Codex storage, then verifies that the
same service and storage boundary remain in place after the request. These
checks are Recipe evidence, not product acceptance.
"""
import argparse
import json
import shlex
import signal
import subprocess
import sys
from pathlib import Path

import issue68_eval_service_isolation_r14 as isolation
import run_issue68_stage5_routing as base
import run_issue68_stage5_routing_r19 as bridge


HERE = Path(__file__).resolve().parent
FIXTURE_SHA = bridge.FIXTURE_SHA
CONTRACT = HERE / "issue68-runtime-evidence-contract-r19.json"
CONTRACT_REVISION = "issue-68-runtime-evidence-r19-2026-10-05"
CONTRACT_RUNNER = ".apm/skills/professor-contact/tests/runtime/" + Path(__file__).name
EXECUTION_KIND = "acceptance"
HOST = "codex"
CASE = "PC68-R1"


def load_contract():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("revision") != CONTRACT_REVISION:
        raise ValueError("contract_revision_mismatch")
    if contract.get("fixture_sha") != FIXTURE_SHA:
        raise ValueError("contract_fixture_mismatch")
    if contract.get("runner") != CONTRACT_RUNNER:
        raise ValueError("contract_runner_is_not_this_entry")
    if contract.get("manual_patch") != "no":
        raise ValueError("contract_manual_patch_forbidden")
    if not contract.get("eval_server_revision"):
        raise ValueError("contract_eval_server_revision_missing")
    codex = contract.get("codex", {})
    if not codex.get("owner_business_input_source"):
        raise ValueError("contract_owner_business_input_source_missing")
    if not codex.get("owner_input_isolation"):
        raise ValueError("contract_owner_input_isolation_missing")
    if not codex.get("canonical_preservation"):
        raise ValueError("contract_canonical_preservation_missing")
    if not codex.get("partition_evidence"):
        raise ValueError("contract_partition_evidence_missing")
    return contract


def check_entry_uniqueness(argv0=None):
    invoked = Path(argv0 if argv0 is not None else sys.argv[0]).resolve()
    if invoked != Path(__file__).resolve():
        raise ValueError("entrypoint_uniqueness_violated")
    return True


def pin():
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
    args.fixture_root = args.fixture_root.resolve()
    args.eval_direnv_root = args.eval_direnv_root.resolve()
    return args


def overlaps(left, right):
    left, right = Path(left).resolve(), Path(right).resolve()
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def resolve_eval_port(eval_root):
    """Resolve the listening eval service port.

    direnv is the formal source: ``direnv exec <eval_root> printenv
    EVAL_PORT``. When direnv is unavailable or its output is unusable, the
    entry falls back to the unique ``eval_server.py`` listener that passes
    the frozen-checkout verification of ``capture_service_instance``, and the
    resolved service (port, pid, command, cwd, start time) is recorded in the
    captured provenance files.
    """
    try:
        port = subprocess.check_output(
            ["direnv", "exec", str(eval_root), "printenv", "EVAL_PORT"],
            cwd=eval_root,
            text=True,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        port = ""
    if port.isdecimal() and 1 <= int(port) <= 65535:
        return port
    candidates = []
    pid = None
    for line in subprocess.check_output(
        ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-Fpn"],
        text=True,
    ).splitlines():
        if line.startswith("p") and line[1:].isdigit():
            pid = line[1:]
        elif line.startswith("n") and pid:
            port = line[1:].rsplit(":", 1)[-1]
            if port.isdecimal() and 1 <= int(port) <= 65535 and port not in candidates:
                candidates.append(port)
    verified = []
    for candidate in candidates:
        try:
            capture_service_instance(eval_root, candidate)
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
        verified.append(candidate)
    if len(verified) != 1:
        raise ValueError("eval_port_unavailable")
    return verified[0]


def capture_service_instance(eval_root, port):
    raw_pids = subprocess.check_output(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fp"],
        text=True,
    )
    pids = sorted({line[1:] for line in raw_pids.splitlines() if line.startswith("p") and line[1:].isdigit()})
    if len(pids) != 1:
        raise ValueError("eval_service_listener_not_unique")
    pid = pids[0]

    raw_cwd = subprocess.check_output(
        ["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"],
        text=True,
    )
    cwd_rows = [line[1:] for line in raw_cwd.splitlines() if line.startswith("n") and line[1:]]
    if len(cwd_rows) != 1:
        raise ValueError("eval_service_cwd_unobservable")
    cwd = Path(cwd_rows[0]).resolve()
    if cwd != Path(eval_root).resolve():
        raise ValueError("eval_service_cwd_mismatch")

    start_time = subprocess.check_output(["ps", "-p", pid, "-o", "lstart="], text=True).strip()
    command = subprocess.check_output(["ps", "-p", pid, "-o", "command="], text=True).strip()
    if not start_time or not command:
        raise ValueError("eval_service_process_unobservable")
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise ValueError("eval_service_command_malformed") from exc
    if not any(Path(token).name == "eval_server.py" for token in tokens):
        raise ValueError("eval_service_command_mismatch")
    has_port = any(token == f"--port={port}" for token in tokens)
    has_port = has_port or any(
        tokens[index] == "--port" and tokens[index + 1] == port
        for index in range(len(tokens) - 1)
    )
    if not has_port:
        raise ValueError("eval_service_port_mismatch")

    return {
        "port": port,
        "pid": int(pid),
        "start_time": start_time,
        "command": command,
        "cwd": str(cwd),
    }


def capture_eval_service_provenance(eval_root, expected_revision):
    revision = base.clean_revision(eval_root, expected_revision)
    port = resolve_eval_port(eval_root)
    service = capture_service_instance(eval_root, port)
    storage = isolation.capture_storage_isolation(service)
    return {"eval_server": revision, "service": service, "storage": storage}


def same_service(before, after):
    return (
        before.get("eval_server") == after.get("eval_server")
        and before.get("service", {}).get("port") == after.get("service", {}).get("port")
        and before.get("service", {}).get("pid") == after.get("service", {}).get("pid")
        and before.get("service", {}).get("start_time") == after.get("service", {}).get("start_time")
        and before.get("service", {}).get("cwd") == after.get("service", {}).get("cwd")
        and before.get("service", {}).get("command") == after.get("service", {}).get("command")
        and before.get("storage") == after.get("storage")
    )


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
        for source in (args.producer_root, args.fixture_root, args.eval_direnv_root):
            if overlaps(output, source):
                raise ValueError("output_must_be_outside_source_roots")
        check_entry_uniqueness()
        contract = load_contract()
        if args.fixture_sha != FIXTURE_SHA:
            raise ValueError("missing_or_wrong_frozen_fixture_arguments")

        producer = base.clean_revision(args.producer_root, args.producer_sha)
        fixture = base.clean_revision(args.fixture_root, FIXTURE_SHA)
        service_before = capture_eval_service_provenance(
            args.eval_direnv_root, contract["eval_server_revision"]
        )
        base.write_json(output / "eval-service-provenance.before.json", service_before)
        provenance = {
            "producer": producer,
            "fixture": fixture,
            "eval_server": service_before["eval_server"],
            "eval_service_before": service_before["service"],
            "eval_storage_before": service_before["storage"],
            "manual_patch": "no",
            "execution_kind": EXECUTION_KIND,
            "case": CASE,
            "host": HOST,
            "entrypoint": Path(__file__).name,
            "single_request_no_retry": "yes",
            "contract_revision": contract["revision"],
        }
        base.write_json(output / "provenance.json", provenance)

        base.progress("只执行 Codex；服务来源和隔离已归档；单次正式请求，失败不重试、不换服务、不换模型、不改断言")
        host = base.codex_host(args, output)
        base.write_json(output / "codex-verdict.json", host)

        service_after = capture_eval_service_provenance(
            args.eval_direnv_root, contract["eval_server_revision"]
        )
        base.write_json(output / "eval-service-provenance.after.json", service_after)
        if not same_service(service_before, service_after):
            result = base.verdict(
                "INVALID_TEST_EXECUTION",
                "eval_service_changed_during_execution",
                before=service_before,
                after=service_after,
            )
        else:
            result = host

        base.clean_revision(args.producer_root, args.producer_sha)
        base.clean_revision(args.fixture_root, FIXTURE_SHA)
        base.clean_revision(args.eval_direnv_root, contract["eval_server_revision"])
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result = (
            {"state": "CASE_NOT_STARTED", "reason_code": str(exc)}
            if not base.started_evidence(output)
            else base.verdict("INVALID_TEST_EXECUTION", "revision_or_execution_changed", detail=str(exc))
        )
    except SystemExit as exc:
        result = (
            base.verdict("INVALID_TEST_EXECUTION", "execution_cancelled", exit_code=exc.code)
            if base.started_evidence(output)
            else {"state": "CASE_NOT_STARTED", "reason_code": "bootstrap_cancelled"}
        )
    finally:
        base.stop_active()
        base.write_json(output / "final-verdict.json", result)
    base.progress("结束：" + (result.get("verdict") or result.get("state", "UNKNOWN")))
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
