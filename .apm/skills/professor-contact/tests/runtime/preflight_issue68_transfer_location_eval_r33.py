#!/usr/bin/env python3
"""One live, non-business Gate-2 preflight of the selected transfer directory."""
import argparse
import hashlib
import json
import shlex
import signal
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import issue68_lifecycle as lifecycle
import run_issue68_stage5_routing_r19_codex as runner
from build_issue68_codex_request_r12 import build_request

PRODUCER_SHA = "b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d"
FIXTURE_SHA = "d160ecb403c0f9e9c153f4b8383302a4b67664ab"
PROBE_SCHEMA = "issue68-r33-transfer-marker-v1"
MARKER_NAME = ".issue68-r33-preflight-marker"
MARKER_BYTES = b"issue68-r33-nonbusiness-transfer-marker\n"
REQUEST_TIMEOUT_SECONDS = 900
HERE = Path(__file__).resolve().parent


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    return digest_bytes(Path(path).read_bytes())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def request_configuration(request, response, project_configuration=None):
    if not isinstance(response, dict):
        response = {}
    response_output = response.get("output")
    effective = (response_output.get("thread_start_effective")
                 if isinstance(response_output, dict) else None)
    command = request.get("command") if isinstance(request, dict) else None
    if not isinstance(command, str):
        raise ValueError("actual_request_command_unobservable")
    argv = shlex.split(command)
    if argv.count("--") != 1:
        raise ValueError("actual_request_option_boundary_invalid")
    option_argv = argv[:argv.index("--")]
    if (option_argv.count("--cd") != 1 or option_argv.count("--sandbox") != 1
            or option_argv.count("--model") != 1):
        raise ValueError("actual_request_configuration_mismatch")
    models = [option_argv[index + 1] for index, token in enumerate(option_argv[:-1])
              if token == "--model"]
    configs = [option_argv[index + 1] for index, token in enumerate(option_argv[:-1])
               if token == "--config"]
    consumer = str(Path(option_argv[option_argv.index("--cd") + 1]).resolve())
    trust_override = 'projects={' + json.dumps(consumer) + '={trust_level="trusted"}}'
    expected_configs = [
        'model_reasoning_effort="low"',
        "agents.max_concurrent_threads_per_session=2",
        trust_override,
    ]
    forbidden_approval_flags = {
        "--ask-for-approval", "--approval-policy", "--approvals-reviewer",
        "--approve-for-me", "--dangerously-bypass-approvals-and-sandbox",
    }
    if (any(token in forbidden_approval_flags for token in option_argv)
            or any(token.startswith(flag + "=") for token in option_argv
                   for flag in forbidden_approval_flags)
            or "-c" in option_argv
            or any(token.startswith("--config=") for token in option_argv)):
        raise ValueError("per_request_approval_override_forbidden")
    if (models != ["gpt-6-luna"] or configs != expected_configs
            or any("approval_policy" in config or "approvals_reviewer" in config
                   for config in configs)):
        raise ValueError("actual_request_configuration_mismatch")
    sandbox = option_argv[option_argv.index("--sandbox") + 1]
    if sandbox != "workspace-write":
        raise ValueError("actual_request_sandbox_mismatch")

    approval_configuration = runner._request_approval_configuration(response, effective)

    root_thread = (response_output.get("thread_id")
                   if isinstance(response_output, dict) else None)
    generation = (response_output.get("runtime_generation")
                  if isinstance(response_output, dict) else None)
    events = (response_output.get("app_server_events")
              if isinstance(response_output, dict) else None)
    source = {
        "path": "output.app_server_events",
        "method": "thread/started",
        "model_field": "message.params.thread.model",
        "reasoning_effort_field": "message.params.thread.reasoningEffort",
        "runtime_generation": generation,
        "matching_event_count": 0,
        "status": "NOT_OBSERVED_YET" if not response else
                  "NOT_EXPOSED_BY_CURRENT_SERVICE",
    }
    matches = []
    if isinstance(root_thread, str) and root_thread and generation is not None \
            and isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            event_generation = event.get("runtime_generation")
            if (type(event_generation) is not type(generation)
                    or event_generation != generation):
                continue
            message = event.get("message")
            if not isinstance(message, dict) or message.get("method") != "thread/started":
                continue
            params = message.get("params")
            thread = params.get("thread") if isinstance(params, dict) else None
            if isinstance(thread, dict) and thread.get("id") == root_thread:
                matches.append((event, thread))

    source["matching_event_count"] = len(matches)
    model = None
    reasoning_effort = None
    if len(matches) == 1:
        event, thread = matches[0]
        source.update({
            "status": "UNIQUE_MATCH",
            "runtime_seq": event.get("runtime_seq"),
        })
        if "model" in thread:
            model = thread["model"]
            model_status = ("OBSERVED" if isinstance(model, str) and model.strip()
                            else "INVALID_SERVICE_REPORTED_VALUE")
        else:
            model_status = "NOT_EXPOSED_BY_CURRENT_SERVICE"
        if "reasoningEffort" in thread:
            reasoning_effort = thread["reasoningEffort"]
            reasoning_status = (
                "OBSERVED" if isinstance(reasoning_effort, str)
                and reasoning_effort.strip() else "INVALID_SERVICE_REPORTED_VALUE")
        else:
            reasoning_status = "NOT_EXPOSED_BY_CURRENT_SERVICE"
    else:
        if len(matches) > 1:
            source["status"] = "AMBIGUOUS_THREAD_STARTED_EVENT"
            model_status = "AMBIGUOUS_THREAD_STARTED_EVENT"
            reasoning_status = "AMBIGUOUS_THREAD_STARTED_EVENT"
        else:
            unavailable_status = ("NOT_OBSERVED_YET" if not response else
                                  "NOT_EXPOSED_BY_CURRENT_SERVICE")
            model_status = unavailable_status
            reasoning_status = unavailable_status

    return {
        "request_argv": argv,
        "requested_model": models[0],
        "requested_configs": configs,
        "requested_reasoning_effort": "low",
        "requested_sandbox": sandbox,
        "consumer_root": consumer,
        "request_timeout_seconds": request.get("timeout"),
        "source": "serialized request sent once to the current eval service",
        "service_reported_executor_version": response.get("version"),
        "thread_start_effective": effective,
        "service_reported_effective_model": model,
        "effective_model_status": model_status,
        "service_reported_effective_reasoning_effort": reasoning_effort,
        "effective_reasoning_effort_status": reasoning_status,
        "effective_configuration_source": source,
        "project_approval_configuration": project_configuration,
        "effective_project_approval_configuration": approval_configuration,
    }


def _result(state, reason, **details):
    return {"state": state, "reason": reason, **details}


def command_tokens(command):
    tokens = shlex.split(command)
    if len(tokens) == 3 and Path(tokens[0]).name in ("sh", "bash", "zsh") \
            and tokens[1] in ("-c", "-lc"):
        return shlex.split(tokens[2])
    return tokens


def build_marker_command(marker_script, transfer_root):
    return shlex.join([
        "uv", "run", "--no-project", "python", str(marker_script),
        str(transfer_root), MARKER_NAME, MARKER_BYTES.hex(),
    ])


def verify_probe(response, command, transfer_root, marker_name=MARKER_NAME,
                 marker_sha256=None):
    """Verify one paired command event and the marker proof emitted by that command."""
    if not isinstance(response, dict):
        return _result("INVALID_TEST_EXECUTION", "response_not_object")
    raw = response.get("output")
    if not isinstance(raw, dict):
        return _result("BLOCKED", "response_output_unavailable")
    events = raw.get("app_server_events")
    root_thread, root_turn, generation = (
        raw.get("thread_id"), raw.get("turn_id"), raw.get("runtime_generation"))
    if not isinstance(events, list) or not root_thread or not root_turn or generation is None:
        return _result("BLOCKED", "runtime_event_observation_unavailable")
    for relation_key in ("thread_relations", "threadRelations"):
        relations = raw.get(relation_key)
        if relations is not None and relations not in ([], {}):
            return _result("INVALID_TEST_EXECUTION", "thread_relation_observed")
    valid_generation = (type(generation) is int and generation >= 0) or (
        isinstance(generation, str) and bool(generation))
    if (not isinstance(root_thread, str) or not isinstance(root_turn, str)
            or not valid_generation):
        return _result("INVALID_TEST_EXECUTION", "runtime_identity_type_invalid")
    if not events:
        return _result("BLOCKED", "runtime_event_observation_empty")

    starts = {}
    completed = []
    previous = -1
    for event in events:
        if not isinstance(event, dict):
            return _result("INVALID_TEST_EXECUTION", "event_not_object")
        seq = event.get("runtime_seq")
        event_generation = event.get("runtime_generation")
        if (type(seq) is not int or seq <= previous
                or type(event_generation) is not type(generation)
                or event_generation != generation):
            return _result("INVALID_TEST_EXECUTION", "event_order_or_generation_conflict")
        previous = seq
        message = event.get("message")
        if not isinstance(message, dict):
            return _result("INVALID_TEST_EXECUTION", "event_message_invalid")
        method = message.get("method")
        params = message.get("params")
        if not isinstance(params, dict):
            return _result("INVALID_TEST_EXECUTION", "event_params_invalid")
        event_thread = params.get("threadId")
        if event_thread is not None and event_thread != root_thread:
            return _result("INVALID_TEST_EXECUTION", "non_root_thread_event_observed")
        item = params.get("item", {})
        if not isinstance(item, dict):
            return _result("INVALID_TEST_EXECUTION", "event_item_invalid")
        method_text = method.lower() if isinstance(method, str) else ""
        item_type = item.get("type")
        item_label = " ".join(
            str(item.get(key, "")) for key in ("name", "toolName")).lower()
        agent_path_fields = any(
            isinstance(item.get(key), str) and item.get(key)
            for key in ("agentThreadId", "agentPath"))
        is_delegation = (
            "collab" in method_text or "delegat" in method_text
            or "spawnagent" in method_text or "subagentactivity" in method_text
            or str(item_type).lower() in {"collabagenttoolcall", "subagentactivity"}
            or any(token in item_label for token in (
                "collab", "delegat", "spawnagent", "spawn_agent", "subagent"))
            or agent_path_fields)
        if is_delegation:
            return _result("INVALID_TEST_EXECUTION", "agent_or_delegation_event_observed")
        if item_type == "commandExecution":
            if params.get("threadId") != root_thread:
                return _result("INVALID_TEST_EXECUTION", "non_root_command_observed")
            if params.get("turnId") != root_turn:
                return _result("INVALID_TEST_EXECUTION", "command_turn_mismatch")
            try:
                matches = command_tokens(item.get("command", "")) == command_tokens(command)
            except (TypeError, ValueError):
                return _result("INVALID_TEST_EXECUTION", "command_malformed")
            if not matches:
                return _result("INVALID_TEST_EXECUTION", "unexpected_command_observed")
        if params.get("threadId") != root_thread or item_type != "commandExecution":
            continue
        identity = item.get("id")
        if not isinstance(identity, str) or not identity:
            return _result("INVALID_TEST_EXECUTION", "command_identity_missing")
        if method == "item/started":
            if identity in starts:
                return _result("INVALID_TEST_EXECUTION", "duplicate_command_start")
            starts[identity] = seq
        elif method == "item/completed":
            if identity not in starts or starts[identity] >= seq:
                return _result("INVALID_TEST_EXECUTION", "command_completion_unpaired")
            try:
                emitted = json.loads(item.get("aggregatedOutput", ""))
            except (TypeError, ValueError):
                emitted = None
            completed.append({
                "command_id": identity,
                "start_seq": starts[identity],
                "end_seq": seq,
                "status": item.get("status"),
                "exit_code": item.get("exitCode"),
                "emitted": emitted,
                "raw_event": event,
            })
        else:
            return _result("INVALID_TEST_EXECUTION", "matching_command_method_invalid")
    if len(completed) != 1:
        if not completed:
            return _result("NOT TESTED", "marker_command_not_observed")
        return _result("INVALID_TEST_EXECUTION", "marker_command_not_unique")
    item = completed[0]
    emitted = item["emitted"]
    if item["status"] != "completed":
        return _result("BLOCKED", "marker_command_did_not_complete", command_event=item)
    if not isinstance(emitted, dict) or emitted.get("schema") != PROBE_SCHEMA:
        return _result("BLOCKED", "marker_command_result_unavailable", command_event=item)
    if emitted.get("state") == "INVALID_TEST_EXECUTION":
        return _result("INVALID_TEST_EXECUTION",
                       emitted.get("reason", "marker_probe_invalid"),
                       command_event=item, probe=emitted)
    if emitted.get("state") == "BLOCKED":
        return _result("BLOCKED", emitted.get("reason", "marker_operation_blocked"),
                       command_event=item, probe=emitted)
    if item["exit_code"] != 0:
        return _result("BLOCKED", "marker_command_nonzero_exit", command_event=item,
                       probe=emitted)
    expected_root = str(Path(transfer_root).resolve())
    expected = {
        "schema": PROBE_SCHEMA,
        "state": "PASS",
        "transfer_root": expected_root,
        "marker_name": marker_name,
        "operations": ["create", "read_and_verify", "delete", "confirm_absent"],
        "marker_sha256": marker_sha256,
        "read_matches": True,
        "absent_after_delete": True,
    }
    if emitted != expected:
        return _result("INVALID_TEST_EXECUTION", "marker_proof_mismatch",
                       command_event=item, probe=emitted, expected=expected)
    return _result("PASS", "single_request_marker_lifecycle_verified",
                   command_event=item, probe=emitted, runtime={
                       "thread_id": root_thread, "turn_id": root_turn,
                       "runtime_generation": generation})


def marker_probe_source():
    return r'''import hashlib, json, os, sys
from pathlib import Path

SCHEMA = "issue68-r33-transfer-marker-v1"
root = Path(sys.argv[1])
name = sys.argv[2]
payload = bytes.fromhex(sys.argv[3])
if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
    print(json.dumps({"schema": SCHEMA, "state": "INVALID_TEST_EXECUTION",
                      "reason": "selected_root_not_empty_directory"}))
    raise SystemExit(2)
marker = root / name
try:
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    actual = marker.read_bytes()
    if actual != payload:
        print(json.dumps({"schema": SCHEMA, "state": "INVALID_TEST_EXECUTION",
                          "reason": "marker_readback_mismatch"}))
        raise SystemExit(2)
    marker.unlink()
    if marker.exists():
        print(json.dumps({"schema": SCHEMA, "state": "INVALID_TEST_EXECUTION",
                          "reason": "marker_still_exists"}))
        raise SystemExit(2)
    proof = {"schema": SCHEMA, "state": "PASS", "transfer_root": str(root.resolve()),
             "marker_name": name,
             "operations": ["create", "read_and_verify", "delete", "confirm_absent"],
             "marker_sha256": hashlib.sha256(actual).hexdigest(),
             "read_matches": True, "absent_after_delete": True}
    print(json.dumps(proof, ensure_ascii=False, sort_keys=True))
except PermissionError as exc:
    print(json.dumps({"schema": SCHEMA, "state": "BLOCKED",
                      "reason": "permission_observation_blocked",
                      "error": type(exc).__name__}, sort_keys=True))
except OSError as exc:
    print(json.dumps({"schema": SCHEMA, "state": "BLOCKED",
                      "reason": "filesystem_observation_blocked",
                      "error": type(exc).__name__}, sort_keys=True))
'''


def validate_output(path, sources, transfer_root):
    output = Path(path).resolve()
    if not output.is_relative_to(Path("/private/tmp")):
        raise ValueError("preflight_output_requires_private_tmp")
    if output.parent != transfer_root.parent or output.name != "evidence":
        raise ValueError("preflight_output_must_share_run_root")
    if any(runner.overlaps(output, source) for source in sources):
        raise ValueError("preflight_output_overlaps_source")
    if output.exists():
        raise ValueError("preflight_output_must_be_new")
    return output


def validate_transfer_root(path, protected_roots):
    root = Path(path)
    if not root.is_absolute() or root.is_symlink():
        raise ValueError("transfer_root_must_be_absolute_non_symlink")
    try:
        root = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("transfer_root_missing") from exc
    if not root.is_dir() or any(root.iterdir()):
        raise ValueError("transfer_root_must_be_empty_directory")
    private_tmp = Path("/private/tmp").resolve()
    if (root.parent.parent != private_tmp
            or not root.parent.name.startswith("pc68-r33-transfer-eval-preflight-")
            or root.name != "transfer"):
        raise ValueError("transfer_root_requires_dedicated_private_tmp_run_directory")
    if any(runner.overlaps(root, other) for other in protected_roots):
        raise ValueError("transfer_root_overlaps_protected_root")
    return root


def snapshots_are_complete_empty_same_root(before, after, expected_root):
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    root = str(Path(expected_root).resolve())
    return all(
        snapshot.get("root") == root
        and snapshot.get("present") is True
        and snapshot.get("complete") is True
        and snapshot.get("entries") == {}
        for snapshot in (before, after)
    )


def installed_tree(root):
    root = Path(root)
    return {
        str(path.relative_to(root)): (
            {"symlink": str(path.readlink())} if path.is_symlink()
            else {"sha256": digest(path)} if path.is_file()
            else {"directory": True} if path.is_dir()
            else {"other": True}
        )
        for path in sorted(root.rglob("*"))
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--eval-direnv-root", type=Path, required=True)
    parser.add_argument("--transfer-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    sources = [p.resolve() for p in (
        args.producer_root, args.fixture_root, args.eval_direnv_root)]
    try:
        transfer_root = validate_transfer_root(args.transfer_root, sources)
        output = validate_output(args.output_dir, sources, transfer_root)
        if sorted(path.name for path in transfer_root.parent.iterdir()) != ["transfer"]:
            raise ValueError("preflight_run_directory_must_be_exclusive")
    except ValueError as exc:
        print(json.dumps({"state": "CASE_NOT_STARTED", "reason": str(exc)}))
        return 2

    output.mkdir(parents=True)
    result = {
        "schema": "issue68-r33-transfer-location-eval-preflight-v1",
        "state": "CASE_NOT_STARTED",
        "execution_kind": "preflight",
        "run_id": str(uuid.uuid4()),
        "formal_case_started": False,
        "formal_PC68_R1_started": False,
        "second_gate_status": "INCOMPLETE",
        "request_attempted": False,
    }
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, runner.base.stop_active)
    before = after = None
    request_bytes = None
    try:
        runner.base.progress("核对固定产品、共享资产及现有评估服务")
        result["producer"] = runner.base.clean_revision(sources[0], PRODUCER_SHA)
        result["shared_assets"] = runner.base.clean_revision(sources[1], FIXTURE_SHA)
        result["fixture"] = {
            "fixture_repo_sha": result["shared_assets"]["sha"],
            "fixture_repo_dirty": result["shared_assets"]["dirty"],
            "fixture_run_id": result["run_id"],
            "fixture_type": "existing_loopback_eval_service",
            "manifest_evidence": "service.before.json",
            "manual_patch": "no",
        }
        before = runner.capture_eval_service_provenance(sources[2])
        write_json(output / "service.before.json", before)
        result["service_revision"] = before["eval_server"]
        if before["storage"].get("status") != "ISOLATION_CONFIRMED":
            raise ValueError("eval_service_isolation_unconfirmed")
        result["implementation_sources"] = {
            path.name: digest(path) for path in (
                Path(__file__).resolve(),
                HERE / "build_issue68_codex_request_r12.py",
                HERE / "run_issue68_stage5_routing_r19_codex.py",
                HERE / "issue68_lifecycle.py",
                HERE / "issue68_transfer_location.py",
                HERE / "issue68_eval_service_isolation_r14.py",
            )
        }
        result["implementation_sources"]["eval_server_docs"] = {
            name: digest(sources[2] / name) for name in (
                "README.md", "docs/appserver-migration.md", "codex_appserver/evals.py")
        }
        result["implementation_sources"]["official_cli_documentation"] = [
            "https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex",
            "https://developers.openai.com/zh-Hans/docs/config-file/config-basic",
        ]
        versions = {}
        for tool in ("apm", "uv", "codex"):
            completed = subprocess.run(
                [tool, "--version"], capture_output=True, text=True,
                timeout=15, check=True)
            versions[tool] = completed.stdout.strip() or completed.stderr.strip()
            if not versions[tool]:
                raise ValueError("tool_version_missing:" + tool)
        write_json(output / "tool-versions.json", versions)

        directory, consumer = output / "install", output / "consumer"
        directory.mkdir()
        consumer.mkdir()
        install = [
            "apm", "install",
            f"https://github.com/ScholarWorkflow/professor-contact.git#{PRODUCER_SHA}",
            "--target", "codex", "--trust-transitive-mcp",
        ]
        write_json(directory / "command.json", {
            "argv": install, "cwd": str(consumer), "timeout_seconds": 600})
        runner.base.progress("通过受支持安装路径建立独立干净消费者")
        if runner.base.run(install, consumer, directory / "apm-install", timeout=600):
            raise ValueError("supported_install_failed")
        entrypoint = runner.base.installed_script(consumer)
        source = sources[0] / ".apm/skills/professor-contact/scripts/contact_state.py"
        if digest(entrypoint) != digest(source):
            raise ValueError("installed_product_revision_mismatch")
        result["installation"] = {
            "script_sha256": digest(entrypoint),
            "lock_sha256": digest(consumer / "apm.lock.yaml"),
        }
        if runner.base.run(
                ["uv", "run", "--no-project", "python", str(entrypoint), "--help"],
                consumer, directory / "entry-help", timeout=30):
            raise ValueError("installed_entry_not_executable")
        project_config_setup_path = output / "project-approval-config-setup.json"
        project_config_setup = runner.prepare_project_approval_configuration(
            consumer, sources[1], project_config_setup_path)
        project_config_facts = runner._project_approval_configuration_facts(
            project_config_setup, "project-approval-config-setup.json")
        result["project_approval_configuration_setup"] = project_config_facts
        consumer_before = installed_tree(consumer)

        transfer_root = validate_transfer_root(
            transfer_root, [*sources, output, consumer])
        before_location = lifecycle.snapshot_tree(transfer_root)
        if (before_location.get("present") is not True
                or before_location.get("root") != str(transfer_root)
                or not before_location["complete"] or before_location["entries"]):
            raise ValueError("transfer_root_before_snapshot_invalid")
        marker_script = output / "marker_probe.py"
        marker_script.write_text(marker_probe_source(), encoding="utf-8")
        marker_sha = digest_bytes(MARKER_BYTES)
        command = build_marker_command(marker_script, transfer_root)
        prompt = (
            "这是一次无业务的传递目录预检。只执行下面这一条完整命令一次，不要修改或读取其他文件，"
            "不要委派代理、调用业务技能或处理教授数据。命令会在本次指定的独占目录中创建一个无业务含义的标记，"
            "读取并核对内容，删除标记并确认它已不存在。不得重试。命令：\n" + command
        )
        (output / "prompt.txt").write_text(prompt, encoding="utf-8")
        request = build_request(consumer, prompt)
        if request.get("timeout") != REQUEST_TIMEOUT_SECONDS:
            raise ValueError("request_timeout_changed")
        request_bytes = json.dumps(
            request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        write_json(output / "request.json", request)
        (output / "request.body.json").write_bytes(request_bytes)
        config = request_configuration(request, {}, project_config_facts)
        config["request_body_sha256"] = digest_bytes(request_bytes)
        write_json(output / "actual-request-configuration.json", config)
        write_json(output / "transfer.before.json", before_location)
        write_json(output / "consumer.before.json", consumer_before)
        write_json(output / "request-boundary.json", {
            "run_id": result["run_id"],
            "request_sha256": digest_bytes(request_bytes),
            "transfer_root": str(transfer_root),
            "transfer_snapshot_sha256": digest_bytes(
                (output / "transfer.before.json").read_bytes()),
            "consumer_snapshot_sha256": digest_bytes(
                (output / "consumer.before.json").read_bytes()),
        })

        # Exactly one HTTP attempt is made from this point; there is no retry path.
        runner.base.progress("通过现有服务发送唯一一次无业务预检请求")
        result["request_attempted"] = True
        result["request_body_sha256"] = digest_bytes(request_bytes)
        result["request_configuration"] = config
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{before['service']['port']}/eval",
                request_bytes, {"Content-Type": "application/json"})
            with urllib.request.urlopen(
                    req, timeout=REQUEST_TIMEOUT_SECONDS + 30) as response:
                response_bytes = response.read()
            (output / "response.json").write_bytes(response_bytes)
            parsed = json.loads(response_bytes)
            result["response_body_sha256"] = digest_bytes(response_bytes)
            actual_configuration = request_configuration(
                request, parsed, project_config_facts)
            actual_configuration["request_body_sha256"] = digest_bytes(request_bytes)
            write_json(output / "actual-request-configuration.json", actual_configuration)
            result["request_configuration"] = actual_configuration
            response_output = parsed.get("output", {})
            if isinstance(response_output, dict):
                result["runtime_identity"] = {
                    "thread_id": response_output.get("thread_id"),
                    "turn_id": response_output.get("turn_id"),
                    "runtime_generation": response_output.get("runtime_generation"),
                }
            observation = verify_probe(
                parsed, command, transfer_root, marker_name=MARKER_NAME,
                marker_sha256=marker_sha)
            result["observation"] = observation
            raw_events = parsed.get("output", {}).get("app_server_events")
            write_json(output / "command-events.json", raw_events)
            result["state"] = observation["state"]
        except (OSError, TimeoutError, urllib.error.URLError,
                urllib.error.HTTPError, json.JSONDecodeError) as exc:
            result["state"] = "BLOCKED"
            result["reason"] = "single_eval_request_unavailable"
            result["error_type"] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError):
                body = exc.read()
                (output / "response.error-body.bin").write_bytes(body)
                result["error_body_sha256"] = digest_bytes(body)
        after_location = lifecycle.snapshot_tree(transfer_root)
        after = runner.capture_eval_service_provenance(
            sources[2], before["eval_server"]["sha"])
        write_json(output / "service.after.json", after)
        consumer_after = installed_tree(consumer)
        write_json(output / "transfer.after.json", after_location)
        write_json(output / "consumer.after.json", consumer_after)
        result["integrity"] = {
            "service_unchanged": runner.same_service(before, after),
            "consumer_unchanged": consumer_before == consumer_after,
            "transfer_before": before_location,
            "transfer_after": after_location,
            "transfer_after_empty": (
                after_location.get("root") == str(transfer_root)
                and after_location.get("present") is True
                and after_location.get("complete") is True
                and after_location.get("entries") == {}),
        }
        if not runner.same_service(before, after):
            result["state"] = "INVALID_TEST_EXECUTION"
            result["reason"] = "eval_service_or_storage_changed_during_request"
        elif consumer_before != consumer_after:
            result["state"] = "INVALID_TEST_EXECUTION"
            result["reason"] = "clean_consumer_changed_during_preflight"
        elif result["state"] == "PASS" and not snapshots_are_complete_empty_same_root(
                before_location, after_location, transfer_root):
            result["state"] = "INVALID_TEST_EXECUTION"
            result["reason"] = "transfer_root_snapshots_not_complete_and_empty"
        elif (result["state"] == "PASS"
              and result.get("request_configuration", {}).get(
                  "effective_project_approval_configuration", {}).get("status") != "MATCH"):
            result["state"] = "BLOCKED"
            result["reason"] = "effective_project_approval_configuration_not_verified"
        result["raw_evidence_directory"] = str(output)
        result["transfer_root"] = str(transfer_root)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result["reason"] = str(exc)
        result["error_type"] = type(exc).__name__
        if result["request_attempted"]:
            result["state"] = "BLOCKED"
    finally:
        runner.base.stop_active()
        write_json(output / "preflight-result.json", result)
    return 0 if result["state"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
