#!/usr/bin/env python3
"""Execute PC68-D1 or the two-host PC68-R1 once, with local evidence.

Run through uv run. Never starts/restarts eval, edits installed consumers,
retries a model request, or substitutes model prose for formal delegation.
"""
import argparse
import contextlib
import importlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

from build_issue68_codex_request import build_request
from prepare_issue68_stage5_routing import prepare, write_json
from verify_issue68_stage5_routing import combine, verdict, verify_codex, verify_opencode

HERE = Path(__file__).resolve().parent
FIXTURE_SHA = "a96c239cca0e1e07eb142089e4d379baf4072277"
ACTIVE = None


def progress(phase):
    print(f"[{time.strftime('%H:%M:%S')}] {phase}", flush=True)


def stop_active(signum=None, frame=None):
    if ACTIVE is not None and ACTIVE.poll() is None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(ACTIVE.pid, signal.SIGTERM)
        try:
            ACTIVE.wait(timeout=5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(ACTIVE.pid, signal.SIGKILL)
            ACTIVE.wait()
    if signum is not None:
        raise SystemExit(128 + signum)


def run(argv, cwd, prefix, *, env=None, timeout=180):
    global ACTIVE
    progress("执行 " + Path(argv[0]).name)
    with prefix.with_suffix(".stdout.txt").open("w") as stdout, prefix.with_suffix(".stderr.txt").open("w") as stderr:
        ACTIVE = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            rc = ACTIVE.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_active()
            rc = 124
        finally:
            ACTIVE = None
    prefix.with_suffix(".exit-code.txt").write_text(str(rc) + "\n")
    return rc


def clean_revision(root, expected):
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=root, text=True)
    if actual != expected or dirty:
        raise ValueError("wrong_revision_or_dirty_checkout")
    return {"sha": actual, "dirty": "no"}


def started_evidence(output):
    return any(output.glob("**/case-started.json"))


def archive_config(consumer, directory, phase):
    for config in (consumer / ".codex" / "config.toml", consumer / "opencode.json"):
        if config.is_file():
            shutil.copy2(config, directory / (config.name + "." + phase))


def installed_script(consumer):
    roots = [consumer / name / "skills" / "professor-contact" for name in
             (".agents", ".codex", ".opencode", ".apm")]
    paths = [root / "scripts" / "contact_state.py" for root in roots
             if (root / "scripts" / "contact_state.py").is_file()]
    if len(paths) != 1 or paths[0].is_symlink():
        raise ValueError("installed_script_resolution_failed")
    return paths[0]


def deterministic(args, output):
    sys.path.insert(0, str(HERE.parent))
    asset = importlib.import_module("test_issue68_stage5_local_state")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(asset.TestIssue68Stage5LocalState)
    cases = list(suite)
    names = unittest.defaultTestLoader.getTestCaseNames(asset.TestIssue68Stage5LocalState)
    expected = {
        "test_stage5_local_pack_is_authoritative_and_global_fallback_is_forbidden",
        "test_stage5_email_id_scope_is_local_and_unrelated_local_rows_are_noise",
        "test_stage5_batch_without_email_id_never_crosses_professor_owner",
        "test_stage5_multi_professor_partial_results_keep_owner_state_isolated",
        "test_stage5_rebuild_overview_reads_owner_outputs_only_and_is_idempotent",
        "test_stage5_list_inputs_discovers_local_packs_independently",
        "test_stage5_choices_attribution_uses_canonical_directory_and_email_id"}
    if set(names) != expected or suite.countTestCases() != 7:
        return verdict("INVALID_TEST_EXECUTION", "unexpected_test_set")
    write_json(output / "case-started.json", {"state": "CASE_STARTED", "case": "PC68-D1"})
    progress("开始七项确定性证明")
    with (output / "unittest.txt").open("w") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    write_json(output / "proofs.json", [getattr(case, "proof_evidence", {"missing": case.id()}) for case in cases])
    details = {"tests_run": result.testsRun, "skipped": len(result.skipped),
               "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
               "failures": len(result.failures), "errors": len(result.errors), "discovered_methods": names}
    if result.testsRun != 7 or result.skipped or result.expectedFailures or result.unexpectedSuccesses or result.errors:
        return verdict("INVALID_TEST_EXECUTION", "incomplete_or_nonordinary_execution", **details)
    if result.failures:
        return verdict("FAIL_PRODUCT", "product_assertion_failed", **details)
    return verdict("PASS", **details)


def install_host(args, output, host, *, before_codex_install=None,
                after_codex_install=None):
    directory = output / host
    directory.mkdir()
    consumer = output / "consumers" / host
    consumer.mkdir(parents=True)
    if host == "codex" and before_codex_install is not None:
        before_codex_install(consumer, directory)
    command = ["apm", "install", f"https://github.com/ScholarWorkflow/professor-contact.git#{args.producer_sha}",
               "--target", host, "--trust-transitive-mcp"]
    write_json(directory / "install.json", {"command": command, "consumer": str(consumer),
                                            "newly_created": True, "manual_patch": "no"})
    if run(command, consumer, directory / "install", timeout=240):
        raise ValueError("consumer_install_failed")
    if host == "codex" and after_codex_install is not None:
        after_codex_install(consumer, directory)
    shutil.copy2(consumer / "apm.lock.yaml", directory / "apm.lock.yaml")
    script = installed_script(consumer)
    manifest = prepare(consumer / "program", script, directory)
    write_json(directory / "installed-entrypoint.json", {"script": str(script), "cwd": str(consumer)})
    archive_config(consumer, directory, "before")
    return directory, consumer, manifest


def codex_host(args, output):
    started, consumer, directory = False, None, None
    try:
        directory, consumer, manifest = install_host(args, output, "codex")
        request = build_request(consumer, (directory / "root-prompt.txt").read_text())
        write_json(directory / "codex-request.json", request)
        port = subprocess.check_output(["direnv", "exec", str(args.eval_direnv_root), "printenv", "EVAL_PORT"],
                                       cwd=args.eval_direnv_root, text=True).strip()
        if not port.isdecimal() or not 1 <= int(port) <= 65535:
            raise ValueError("eval_port_unavailable")
        started = True
        write_json(directory / "case-started.json", {"state": "CASE_STARTED", "host": "codex"})
        progress("Codex 唯一一次正式请求，最长 900 秒")
        body = json.dumps(request).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/eval", body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=930) as response:
                (directory / "codex-response.json").write_bytes(response.read())
        except (OSError, TimeoutError) as exc:
            return verdict("BLOCKED_DEPENDENCY", "eval_transport_unavailable", detail=type(exc).__name__)
        parser = args.fixture_root / "scripts" / "parse_codex_eval_evidence.py"
        rc = run([sys.executable, str(parser), "--contract", str(args.fixture_root / "configs" / "codex-eval-adapter-contract.json"),
                  "--eval-response", str(directory / "codex-response.json"), "--consumer-root", str(consumer),
                  "--expected-agent", "professor-contact-email-generator", "--output", str(directory / "codex-adapter.json")],
                 consumer, directory / "shared-parser")
        if rc or not (directory / "codex-adapter.json").is_file():
            return verdict("INVALID_EVIDENCE", "shared_adapter_failed")
        return verify_codex(json.loads((directory / "codex-response.json").read_text()),
                            json.loads((directory / "codex-adapter.json").read_text()), manifest)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return verdict("INVALID_TEST_EXECUTION", "codex_execution_failed", detail=str(exc)) if started else {
            "state": "CASE_NOT_STARTED", "reason_code": str(exc)}
    finally:
        if consumer is not None:
            archive_config(consumer, directory, "after")


def fixture_environment(env_file):
    names = ["FIXTURE_RUN_ID", "FIXTURE_EVIDENCE_FILE", "OPENCODE_TEST_HOME", "OPENCODE_TEST_CONFIG_HOME",
             "OPENCODE_TEST_DATA_HOME", "OPENCODE_TEST_CACHE_HOME", "OPENCODE_TEST_STATE_HOME",
             "OPENCODE_TEST_TMPDIR", "OPENCODE_TEST_BIN", "OPENCODE_TEST_VERSION"]
    command = 'source "$1"; shift; for name in "$@"; do printf "%s\\0%s\\0" "$name" "${!name}"; done'
    raw = subprocess.check_output(["bash", "-c", command, "fixture-env", str(env_file), *names])
    fields = raw.decode().split("\0")[:-1]
    return dict(zip(fields[::2], fields[1::2]))


def opencode_host(args, output):
    started, env_file, directory, consumer = False, None, output / "opencode", None
    fixture = args.fixture_root / "scripts" / "start_opencode_test_fixture_macos.sh"
    try:
        directory, consumer, manifest = install_host(args, output, "opencode")
        environment = dict(os.environ, SCHOLAR_TEST_FIXTURE_ROOT=str(output / "opencode-fixture"))
        if run([str(fixture), "--consumer", str(consumer)], consumer, directory / "fixture-start", env=environment):
            raise ValueError("fixture_start_failed")
        env_file = Path((directory / "fixture-start.stdout.txt").read_text().strip())
        fields = fixture_environment(env_file)
        shutil.copy2(fields["FIXTURE_EVIDENCE_FILE"], directory / "fixture-evidence.json")
        isolated = {"HOME": fields["OPENCODE_TEST_HOME"], "XDG_CONFIG_HOME": fields["OPENCODE_TEST_CONFIG_HOME"],
                    "XDG_DATA_HOME": fields["OPENCODE_TEST_DATA_HOME"], "XDG_CACHE_HOME": fields["OPENCODE_TEST_CACHE_HOME"],
                    "XDG_STATE_HOME": fields["OPENCODE_TEST_STATE_HOME"], "TMPDIR": fields["OPENCODE_TEST_TMPDIR"],
                    "PATH": str(Path(fields["OPENCODE_TEST_BIN"]).parent) + ":/usr/bin:/bin:/usr/sbin:/sbin"}
        write_json(directory / "runtime-environment.json", isolated)
        for name, command in (("skills", ["debug", "skill"]),
                              ("agent", ["debug", "agent", "professor-contact-email-generator"])):
            if run([fields["OPENCODE_TEST_BIN"], *command], consumer, directory / name, env=isolated):
                raise ValueError("installed_resolution_failed")
        started = True
        write_json(directory / "case-started.json", {"state": "CASE_STARTED", "host": "opencode", "cwd": str(consumer)})
        progress("OpenCode 唯一一次正式请求，最长 900 秒")
        rc = run([fields["OPENCODE_TEST_BIN"], "run", "--format", "json", "--model", "opencode/big-pickle",
                  (directory / "root-prompt.txt").read_text()], consumer, directory / "run", env=isolated, timeout=900)
        shutil.copy2(directory / "run.stdout.txt", directory / "opencode-run.ndjson")
        shared_path = directory / "opencode-fixture-verdict.json"
        parse_rc = run([sys.executable, str(args.fixture_root / "scripts" / "parse_opencode_evidence.py"),
                       "--characterization", str(args.fixture_root / "configs" / "opencode-runtime-characterization.json"),
                       "--fixture-evidence", str(directory / "fixture-evidence.json"),
                       "--runtime-version", fields["OPENCODE_TEST_VERSION"], "--invocation-mode", "producer_entrypoint",
                       "--expected-skill", "professor-contact", "--allowed-source-root", str(consumer),
                       "--skill-record", str(directory / "skills.stdout.txt"), "--events", str(directory / "opencode-run.ndjson"),
                       "--run-exit-code", str(rc), "--expect-fixture-run-id", fields["FIXTURE_RUN_ID"],
                       "--output", str(shared_path)], consumer, directory / "shared-parser")
        if parse_rc or not shared_path.is_file():
            return verdict("INVALID_EVIDENCE", "shared_parser_failed")
        shared = json.loads(shared_path.read_text())
        if rc:
            return verdict("BLOCKED_DEPENDENCY", "opencode_runtime_failed", exit_code=rc)
        events = [json.loads(line) for line in (directory / "opencode-run.ndjson").read_text().splitlines() if line.strip()]
        return verify_opencode(events, shared, manifest)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return verdict("INVALID_TEST_EXECUTION", "opencode_execution_failed", detail=str(exc)) if started else {
            "state": "CASE_NOT_STARTED", "reason_code": str(exc)}
    finally:
        if env_file is not None:
            rc = run([str(fixture), "stop", str(env_file)], args.fixture_root, directory / "fixture-stop")
            if rc:
                raise ValueError("fixture_cleanup_failed")
        if consumer is not None:
            archive_config(consumer, directory, "after")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("PC68-D1", "PC68-R1"), default="PC68-R1")
    parser.add_argument("--execution-kind", choices=("preflight", "acceptance"), default="preflight")
    parser.add_argument("--preflight-host", choices=("codex", "opencode"))
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--producer-sha", required=True)
    parser.add_argument("--fixture-root", type=Path)
    parser.add_argument("--fixture-sha", default=FIXTURE_SHA)
    parser.add_argument("--eval-direnv-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.producer_root = args.producer_root.resolve()
    output = args.output_dir.resolve()
    result = {"state": "CASE_NOT_STARTED", "reason_code": "bootstrap_failed"}
    if output.exists() and any(output.iterdir()):
        print(json.dumps({"state": "CASE_NOT_STARTED", "reason_code": "output_directory_not_empty"}))
        return 2
    output.mkdir(parents=True, exist_ok=True)
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, stop_active)
    try:
        if output.is_relative_to(args.producer_root) or args.producer_root.is_relative_to(output):
            raise ValueError("output_must_be_outside_producer")
        provenance = {"producer": clean_revision(args.producer_root, args.producer_sha), "manual_patch": "no",
                      "execution_kind": args.execution_kind}
        if args.preflight_host and (args.execution_kind != "preflight" or args.case != "PC68-R1"):
            raise ValueError("partial_host_is_preflight_only")
        if args.case == "PC68-R1":
            if args.fixture_root is None or args.eval_direnv_root is None or args.fixture_sha != FIXTURE_SHA:
                raise ValueError("missing_or_wrong_frozen_fixture_arguments")
            args.fixture_root = args.fixture_root.resolve()
            provenance["fixture"] = clean_revision(args.fixture_root, FIXTURE_SHA)
            write_json(output / "provenance.json", provenance)
            hosts = []
            for name, execute in (("codex", codex_host), ("opencode", opencode_host)):
                if args.preflight_host and args.preflight_host != name:
                    continue
                host = execute(args, output)
                write_json(output / f"{name}-verdict.json", host)
                hosts.append(host)
                progress(name + " 结束：" + host.get("verdict", host["state"]))
            result = combine(hosts) if not args.preflight_host else verdict(
                "NOT_TESTED", "partial_preflight_only", host=args.preflight_host, hosts=hosts)
        else:
            write_json(output / "provenance.json", provenance)
            result = deterministic(args, output)
        clean_revision(args.producer_root, args.producer_sha)
        if args.case == "PC68-R1":
            clean_revision(args.fixture_root, FIXTURE_SHA)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result = {"state": "CASE_NOT_STARTED", "reason_code": str(exc)} if not started_evidence(output) else verdict(
            "INVALID_TEST_EXECUTION", "revision_or_execution_changed", detail=str(exc))
    except SystemExit as exc:
        result = verdict("INVALID_TEST_EXECUTION", "execution_cancelled", exit_code=exc.code) if started_evidence(output) else {
            "state": "CASE_NOT_STARTED", "reason_code": "bootstrap_cancelled"}
    finally:
        stop_active()
        write_json(output / "final-verdict.json", result)
    progress("结束：" + result.get("verdict", result["state"]))
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
