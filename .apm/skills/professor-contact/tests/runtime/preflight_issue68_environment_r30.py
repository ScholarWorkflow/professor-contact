#!/usr/bin/env python3
"""Pre-Gate-2 installation and synthetic ordinary-command observation only.

Never calls the formal PC68-R1 runner, stage5 business, or service lifecycle.
The result is preparation evidence, never a Gate-2 approval or case verdict.
Run using uv run --no-project python.
"""
import argparse
import hashlib
import json
import shlex
import signal
import subprocess
import sys
import urllib.request
from pathlib import Path

import run_issue68_stage5_routing_r19_codex as runner
from build_issue68_codex_request_r12 import build_request

PRODUCER_SHA = "b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d"
FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
OBSERVATION_SCHEMA = "issue68-r30-synthetic-read-v1"
INSTALL_TIMEOUT_SECONDS = 600
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_output(output, sources):
    output = Path(output).resolve()
    if not output.is_relative_to(Path("/private/tmp")):
        raise ValueError("preflight_output_requires_private_tmp")
    if any(runner.overlaps(output, source) for source in sources):
        raise ValueError("preflight_output_overlaps_source")
    if output.exists():
        raise ValueError("preflight_output_must_be_new")
    return output


def command_tokens(command):
    tokens = shlex.split(command)
    if len(tokens) == 3 and Path(tokens[0]).name in ("sh", "bash", "zsh") and tokens[1] in ("-c", "-lc"):
        tokens = shlex.split(tokens[2])
    return tokens


def verify_observation(response, expected, command):
    """Accept only an actual current root command's structured output."""
    def result(status, reason, **details):
        return {"status": status, "reason": reason, **details}
    raw = response.get("output", {})
    events = raw.get("app_server_events")
    root, generation, turn = raw.get("thread_id"), raw.get("runtime_generation"), raw.get("turn_id")
    if not isinstance(events, list) or not root or not turn or generation is None:
        return result("OBSERVATION_UNAVAILABLE", "ordinary_events_unavailable")
    starts, matches, previous = {}, [], -1
    for event in events:
        if not isinstance(event, dict):
            return result("INVALID_TEST_EXECUTION", "event_not_object")
        seq = event.get("runtime_seq")
        if type(seq) is not int or seq <= previous or event.get("runtime_generation") != generation:
            return result("INVALID_TEST_EXECUTION", "event_order_or_generation_invalid")
        previous = seq
        message = event.get("message", {})
        params, method = message.get("params", {}), message.get("method")
        item = params.get("item", {})
        if params.get("threadId") != root or item.get("type") != "commandExecution":
            continue
        if params.get("turnId") != turn:
            return result("INVALID_TEST_EXECUTION", "command_turn_mismatch")
        identity = item.get("id")
        if not isinstance(identity, str) or not identity:
            return result("INVALID_TEST_EXECUTION", "command_id_missing")
        try:
            matches_command = command_tokens(item.get("command", "")) == command_tokens(command)
        except (ValueError, TypeError):
            return result("INVALID_TEST_EXECUTION", "command_malformed")
        if not matches_command:
            continue
        if method == "item/started":
            if identity in starts:
                return result("INVALID_TEST_EXECUTION", "duplicate_command_start")
            starts[identity] = seq
        elif method == "item/completed":
            if identity not in starts or item.get("status") != "completed" or item.get("exitCode") != 0:
                return result("INVALID_TEST_EXECUTION", "command_not_successfully_paired")
            try:
                emitted = json.loads(item.get("aggregatedOutput", ""))
            except (ValueError, TypeError):
                return result("INVALID_TEST_EXECUTION", "ordinary_output_invalid")
            if emitted != {"schema": OBSERVATION_SCHEMA, "read_count": 1, "object": expected,
                           "forwarded": expected, "child_return_code": 0}:
                return result("INVALID_TEST_EXECUTION", "actual_parse_or_forwarding_mismatch")
            matches.append({"command_id": identity, "thread_id": root, "turn_id": turn,
                            "start_seq": starts[identity], "end_seq": seq,
                            "runtime_generation": generation, "raw_event": event,
                            "parsed_output": emitted})
    if len(matches) != 1:
        return result("INVALID_TEST_EXECUTION" if matches else "OBSERVATION_UNAVAILABLE",
                      "ordinary_command_not_unique" if matches else "ordinary_command_missing")
    return result("OBSERVATION_VERIFIED", "actual_parse_and_same_object_forwarding", **matches[0])


def create_synthetic(output):
    root = output / "synthetic"
    root.mkdir()
    expected = {"marker": "PC68环境预检合成输入", "value": "原编号::空 格", "choices": [2, 1, 2]}
    input_path = root / "input.json"
    write(input_path, expected)
    child = root / "echo_argument.py"
    child.write_text("import json, sys\nprint(json.dumps(json.loads(sys.argv[1]), ensure_ascii=False))\n", encoding="utf-8")
    observer = root / "read_once.py"
    observer.write_text(
        "import json, subprocess, sys\n"
        "from pathlib import Path\n"
        f"obj = json.loads(Path({str(input_path)!r}).read_text(encoding='utf-8'))\n"
        f"child = subprocess.run(['uv', 'run', '--no-project', '--cache-dir', {str(output / 'uv-cache')!r}, 'python', {str(child)!r}, json.dumps(obj, ensure_ascii=False)], text=True, capture_output=True, check=True)\n"
        f"print(json.dumps({{'schema': {OBSERVATION_SCHEMA!r}, 'read_count': 1, 'object': obj, 'forwarded': json.loads(child.stdout), 'child_return_code': child.returncode}}, ensure_ascii=False))\n",
        encoding="utf-8")
    command = shlex.join(["uv", "run", "--no-project", "--cache-dir", str(output / "uv-cache"), "python", str(observer)])
    return expected, command, input_path, observer, child


def installed_tree(consumer):
    return {str(path.relative_to(consumer)):
            ({"symlink": str(path.readlink())} if path.is_symlink() else
             {"sha256": digest(path)} if path.is_file() else {"directory": True})
            for path in sorted(consumer.rglob("*"))}


def request_configuration(request, response):
    """Distinguish actual requested configuration from effective service fields."""
    argv = shlex.split(request["command"])
    models = [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "--model"]
    configs = [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "--config"]
    if models != ["gpt-6-luna"] or 'model_reasoning_effort="low"' not in configs:
        raise ValueError("actual_request_configuration_mismatch")
    return {"request_argv": argv, "requested_model": models[0], "requested_configs": configs,
            "source": "request.json actual serialized request before send",
            "service_reported_executor_version": response.get("version"),
            "thread_start_effective": response.get("output", {}).get("thread_start_effective"),
            "effective_model_status": "NOT_EXPOSED_BY_CURRENT_SERVICE",
            "effective_model_source": "evals.py thread_start_effective exposes approvalPolicy, approvalsReviewer, sandbox only"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--eval-direnv-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    sources = [p.resolve() for p in (args.producer_root, args.fixture_root, args.eval_direnv_root)]
    try:
        output = validate_output(args.output_dir, sources)
    except ValueError as exc:
        print(json.dumps({"state": "PREFLIGHT_NOT_STARTED", "reason": str(exc)}))
        return 2
    output.mkdir(parents=True)
    result = {"schema": "issue68-r30-environment-preflight-v1", "state": "PREFLIGHT_INCOMPLETE",
              "execution_kind": "preflight", "formal_case_started": False,
              "second_gate_status": "INCOMPLETE", "formal_run_allowed": False,
              "entrypoint": str(Path(__file__).resolve()), "entrypoint_sha256": digest(__file__)}
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, runner.base.stop_active)
    before = None
    try:
        runner.base.progress("检查固定版本与服务隔离")
        result["producer"] = runner.base.clean_revision(sources[0], PRODUCER_SHA)
        result["shared_assets"] = runner.base.clean_revision(sources[1], FIXTURE_SHA)
        before = runner.capture_eval_service_provenance(sources[2])
        write(output / "service.before.json", before)
        result["service_revision"] = before["eval_server"]
        write(output / "implementation-sources.json", {
            "official_cli_documentation": "https://learn.chatgpt.com/docs/developer-commands?surface=cli",
            "service_sources": {name: digest(sources[2] / name) for name in
                                ("eval_server.py", "codex_appserver/evals.py")},
            "preflight_sources": {path.name: digest(path) for path in
                                  (Path(__file__).resolve(), HERE / "build_issue68_codex_request_r12.py",
                                   HERE / "run_issue68_stage5_routing_r19_codex.py",
                                   HERE / "issue68_eval_service_isolation_r14.py")}})
        versions = {}
        for tool in ("apm", "uv", "codex"):
            completed = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=15, check=True)
            versions[tool] = completed.stdout.strip() or completed.stderr.strip()
            if not versions[tool]:
                raise ValueError("tool_version_missing:" + tool)
        write(output / "tool-versions.json", versions)
        directory, consumer = output / "install", output / "consumer"
        directory.mkdir()
        consumer.mkdir()
        install = ["apm", "install", f"https://github.com/ScholarWorkflow/professor-contact.git#{PRODUCER_SHA}",
                   "--target", "codex", "--trust-transitive-mcp"]
        write(directory / "command.json", {"argv": install, "cwd": str(consumer),
                                           "timeout_seconds": INSTALL_TIMEOUT_SECONDS})
        runner.base.progress(f"执行支持安装，最长{INSTALL_TIMEOUT_SECONDS}秒")
        if runner.base.run(install, consumer, directory / "apm-install", timeout=INSTALL_TIMEOUT_SECONDS):
            raise ValueError("supported_install_failed")
        entrypoint = runner.base.installed_script(consumer)
        source = sources[0] / ".apm/skills/professor-contact/scripts/contact_state.py"
        if digest(entrypoint) != digest(source):
            raise ValueError("installed_product_revision_mismatch")
        result["installation"] = {"script": str(entrypoint), "sha256": digest(entrypoint),
                                  "lock_sha256": digest(consumer / "apm.lock.yaml")}
        before_tree = installed_tree(consumer)
        if runner.base.run(["uv", "run", "--no-project", "python", str(entrypoint), "--help"],
                           consumer, directory / "entry-help", timeout=30):
            raise ValueError("installed_entry_not_executable")
        expected, command, input_path, observer, child = create_synthetic(output)
        before_input = digest(input_path)
        fixed_scripts = {str(path): digest(path) for path in (observer, child)}
        prompt = ("这是环境预检。只执行下列完整命令一次，输出由命令保存。禁止其他命令、业务技能、代理委派、教授业务及任何文件修改。"
                  "无需读取或改写脚本，不要打印预期对象代替命令。命令：\n" + command)
        (output / "prompt.txt").write_text(prompt, encoding="utf-8")
        request = build_request(consumer, prompt)
        request["timeout"] = 180
        write(output / "actual-request-configuration.json", request_configuration(request, {}))
        write(output / "request.json", request)
        write(output / "synthetic-manifest.json", {"input": str(input_path), "input_sha256": before_input,
              "observer": str(observer), "observer_sha256": digest(observer), "child": str(child),
              "child_sha256": digest(child), "expected": expected, "command": command,
              "model": "gpt-6-luna", "reasoning_effort": "low"})
        runner.base.progress("执行一次合成普通命令观察，最长180秒")
        req = urllib.request.Request(f"http://127.0.0.1:{before['service']['port']}/eval",
              json.dumps(request).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=210) as response:
            response_bytes = response.read()
        (output / "response.json").write_bytes(response_bytes)
        parsed = json.loads(response_bytes)
        write(output / "actual-request-configuration.json", request_configuration(request, parsed))
        observation = verify_observation(parsed, expected, command)
        write(output / "observation.json", observation)
        after = runner.capture_eval_service_provenance(sources[2], before["eval_server"]["sha"])
        write(output / "service.after.json", after)
        if not runner.same_service(before, after):
            raise ValueError("service_instance_or_storage_changed")
        if before_tree != installed_tree(consumer):
            raise ValueError("installed_consumer_changed")
        after_scripts = {str(path): digest(path) for path in (observer, child)}
        if fixed_scripts != after_scripts:
            raise ValueError("fixed_observation_scripts_changed")
        if before_input != digest(input_path):
            raise ValueError("synthetic_input_changed")
        write(output / "integrity.json", {"consumer_before": before_tree, "consumer_after": installed_tree(consumer),
              "input_before": before_input, "input_after": digest(input_path), "service_unchanged": True,
              "fixed_scripts_before": fixed_scripts, "fixed_scripts_after": after_scripts})
        runner.base.clean_revision(sources[0], PRODUCER_SHA)
        runner.base.clean_revision(sources[1], FIXTURE_SHA)
        result["observation"] = observation
        result["state"] = "PRECHECK_READY" if observation["status"] == "OBSERVATION_VERIFIED" else "PREFLIGHT_INCOMPLETE"
        result["scope"] = "supported installation, read-only service isolation, synthetic command output only"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result["reason"] = str(exc)
        result["error_type"] = type(exc).__name__
    finally:
        runner.base.stop_active()
        write(output / "preflight-result.json", result)
    runner.base.progress("环境预检结束：" + result["state"])
    return 0 if result["state"] == "PRECHECK_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
