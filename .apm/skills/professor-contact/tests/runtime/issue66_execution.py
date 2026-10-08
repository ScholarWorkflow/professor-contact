#!/usr/bin/env python3
"""Issue 66 的待审安装、取证及执行接线；预检永不发送评测请求。"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shlex
import stat
import subprocess
import sys
import tempfile
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path, PureWindowsPath

PLAN = "issue-66-test-plan-r21-stage3-write-validation-r9-2026-10-08"
WRITER_EVIDENCE_SCHEMA = "issue66.writer-observation.v1"
STAGE3_HANDOFF_ROOT = "professor-contact-stage3-handoff"
MODEL = "gpt-6-luna"
REASONING_EFFORT = "low"
SANDBOX = "workspace-write"
HERE = Path(__file__).resolve().parent
PROFESSOR = Path("教授研究/X分野/Example Professor")
ARTIFACTS = {
    "套磁候选状态.json": PROFESSOR / "套磁候选状态.json",
    "套磁想法候选.md": PROFESSOR / "套磁想法候选.md",
    "套磁想法候选总览.md": Path("教授研究/套磁想法候选总览.md"),
    "套磁选择.json": Path("教授研究/套磁选择.json"),
    "邮件输入.json": Path("教授研究/邮件输入.json"),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _b64(raw):
    return base64.b64encode(raw).decode("ascii") if raw is not None else None


def _lexical_path(path, cwd=None):
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(cwd or Path.cwd()) / candidate
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return candidate.resolve(strict=False)


def _stage3_command(command, cwd=None):
    """Parse only actual contact_state.py argv tokens, never command prose."""
    if cwd is not None and (not isinstance(cwd, str) or not cwd.strip()):
        return None
    try:
        argv = shlex.split(command)
    except (TypeError, ValueError):
        return None
    matches = []
    for index, token in enumerate(argv[:-1]):
        if Path(token).name != "contact_state.py" \
                or not argv[index + 1].startswith("stage3-"):
            continue
        try:
            source = str(_lexical_path(token, cwd))
        except (OSError, RuntimeError, TypeError, ValueError):
            return None
        matches.append((argv[index + 1], source, argv))
    return matches[0] if len(matches) == 1 else None


def _flag_values(argv, flag):
    values = []
    for index, token in enumerate(argv):
        if token == flag:
            values.append(argv[index + 1] if index + 1 < len(argv)
                          and not argv[index + 1].startswith("--") else None)
        elif token.startswith(flag + "="):
            values.append(token[len(flag) + 1:])
    return values


def _strict_json_value(raw):
    """Parse one complete JSON value, rejecting duplicate keys and extensions."""
    if not isinstance(raw, (str, bytes)) or not raw:
        return None

    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def reject_constant(value):
        raise ValueError(f"invalid JSON constant: {value}")

    try:
        return json.loads(raw, object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError, ValueError):
        return None


def _complete_writer_result(value):
    """Check the complete Stage-3 write result envelope and entry semantics."""
    if not isinstance(value, dict) \
            or value.get("result") != "ok" \
            or not isinstance(value.get("files"), list) \
            or not value["files"] \
            or not isinstance(value.get("notes"), str):
        return False

    candidates = set()
    for entry in value["files"]:
        if not isinstance(entry, dict):
            return False
        file_path = entry.get("file")
        if not isinstance(file_path, str) or not file_path:
            return False
        candidate = Path(file_path)
        if not candidate.is_absolute():
            return False
        try:
            normalized_path = str(candidate.resolve(strict=False))
        except (OSError, RuntimeError, ValueError):
            return False

        artifact = entry.get("artifact")
        verdict = entry.get("verdict")
        blocking = entry.get("blocking")
        minor = entry.get("minor")
        issues = entry.get("issues")
        if artifact not in ("analysis", "candidates") \
                or verdict not in ("pass", "pass_with_minor", "fail") \
                or isinstance(blocking, bool) or not isinstance(blocking, int) \
                or blocking < 0 or isinstance(minor, bool) \
                or not isinstance(minor, int) or minor < 0 \
                or not isinstance(issues, list):
            return False

        blocking_issues = 0
        minor_issues = 0
        for issue in issues:
            if not isinstance(issue, dict):
                return False
            if any(not isinstance(issue.get(field), str)
                   or not issue[field].strip()
                   for field in ("rule", "severity", "quote", "suggestion")):
                return False
            location = issue.get("location")
            if isinstance(location, bool) or not (
                    isinstance(location, int) and location > 0
                    or isinstance(location, str) and location.strip()
                    and len(location) <= 20):
                return False
            if len(issue["quote"]) > 40:
                return False
            if issue["severity"] == "blocking":
                blocking_issues += 1
            elif issue["severity"] == "minor":
                minor_issues += 1
            else:
                return False
        if (blocking, minor) != (blocking_issues, minor_issues):
            return False
        if blocking_issues and verdict != "fail":
            return False
        if not blocking_issues and verdict == "fail":
            return False
        if not blocking_issues and minor_issues and verdict != "pass_with_minor":
            return False
        if not blocking_issues and not minor_issues and verdict != "pass":
            return False
        if artifact == "candidates":
            if normalized_path in candidates:
                return False
            candidates.add(normalized_path)
    return bool(candidates)


def _json_semantically_equal(left, right):
    """Compare parsed JSON values without Python's bool/int equality overlap."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _json_semantically_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _json_semantically_equal(a, b) for a, b in zip(left, right))
    return left == right


def _json_output(raw):
    if not isinstance(raw, str):
        return None
    start = raw.find("{")
    if start < 0:
        return None
    try:
        value = json.loads(raw[start:])
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _native_identity(params, item):
    values = (params.get("threadId"), params.get("turnId"), item.get("id"))
    if not all(isinstance(value, str) and value for value in values):
        return None
    return {"thread_id": values[0], "turn_id": values[1], "item_id": values[2]}


def validate_product_source_selector(value):
    """只接受远端 ref 选择器，拒绝本地路径和经过符号链接的路径。"""
    selector = str(value).strip()
    if not selector:
        raise RuntimeError("必须提供本轮实际产品来源")
    if selector.startswith(("~", "./", "../", ".\\", "..\\")) \
            or selector.lower().startswith(("file:", "git+file:")):
        raise RuntimeError("--product-source 不接受本地路径；请提供 APM 支持的远端来源选择器")
    if "\\" in selector:
        raise RuntimeError("--product-source 不接受本地路径；请提供 APM 支持的远端来源选择器")
    candidate = Path(selector).expanduser()
    windows_candidate = PureWindowsPath(selector)
    if candidate.is_absolute() or windows_candidate.drive or windows_candidate.root:
        raise RuntimeError("--product-source 不接受本地路径；请提供 APM 支持的远端来源选择器")
    if any(part in (".", "..") for part in candidate.parts) \
            or any(part in (".", "..") for part in windows_candidate.parts):
        raise RuntimeError("--product-source 不接受本地路径；请提供 APM 支持的远端来源选择器")

    base = Path.cwd()
    path = base
    for part in candidate.parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError("--product-source 不接受符号链接或本地路径；请提供 APM 支持的远端来源选择器")
    if path.exists():
        raise RuntimeError("--product-source 不接受本地路径；请提供 APM 支持的远端来源选择器")
    return selector


def write(path, value):
    """每份材料只能创建一次，禁止覆盖历史尝试。"""
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=1)
        stream.write("\n")


def jq(path, expression="."):
    # JSON 输入先通过指定结构解析器；不按序列化文本猜字段。
    result = subprocess.run(["jq", "-ce", expression, str(path)],
                            capture_output=True, check=True)
    return json.loads(result.stdout)


def check(name, ok, evidence):
    return {"name": name, "status": "pass" if ok else "fail", "detail": evidence}


def surface(identity, checks, **values):
    return {"evidence_set_id": identity, "status": "ok" if all(
        row["status"] == "pass" for row in checks) else "error",
        "checks": checks, **values}


def _uploaded_bytes(value):
    """解析 curl 的上传计数；无法确认时返回 None。"""
    try:
        count = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not count.is_finite() or count < 0 or count != count.to_integral_value():
        return None
    return int(count)


def _curl_write_out(raw):
    """解析状态码和上传字节；原始输出另行保留。"""
    try:
        value = raw.decode("ascii")
    except (AttributeError, UnicodeDecodeError):
        return {"http_status_raw": None, "http_status": None,
                "request_body_uploaded_bytes": None}
    status_raw, separator, uploaded_raw = value.partition("\t")
    status = int(status_raw) if len(status_raw) == 3 and status_raw.isdigit() \
        and status_raw != "000" else None
    uploaded = _uploaded_bytes(uploaded_raw) if separator else None
    return {"http_status_raw": status_raw or None, "http_status": status,
            "request_body_uploaded_bytes": uploaded}


def _transport_classification(exit_code, http_status, uploaded_bytes,
                              expected_bytes):
    """只在零上传且无响应时判用例未开始；其余传输失败均阻断。"""
    if http_status is not None and http_status != 200:
        return "BLOCKED"
    if http_status is None and uploaded_bytes == 0:
        return "CASE_NOT_STARTED"
    if http_status == 200 and exit_code == 0 \
            and uploaded_bytes == expected_bytes:
        return None
    return "BLOCKED"


class CommandNotStarted(OSError):
    """命令进程未启动，因此没有发出请求。"""


def snapshot(program):
    rows = {}
    for name, relative in ARTIFACTS.items():
        path = program / relative
        exists = path.exists() or path.is_symlink()
        rows[name] = {"exists": exists, "sha256": digest(path.read_bytes())
                      if path.is_file() and not path.is_symlink() else None}
    return rows


def request(consumer, program):
    """配置仅采用共识默认值；动态项目键使用服务支持的整表编码。"""
    prompt = (f"在 {program} 执行已安装 professor-contact 的正式 Stage 3，且只执行 Stage 3。\n"
              "直接消费现有 Stage 2 canonical input；不要进入 Stage 4。\n完成后正常结束。\n")
    trust = "projects={" + json.dumps(str(consumer), ensure_ascii=False) + \
        '={trust_level="trusted"}}'
    argv = ["--json", "--skip-git-repo-check", "--sandbox", SANDBOX,
            "--cd", str(consumer), "--model", MODEL, "--config",
            f'model_reasoning_effort="{REASONING_EFFORT}"', "--config", trust,
            "--config", "agents.max_concurrent_threads_per_session=5", "--", prompt]
    return {"command": shlex.join(argv), "timeout": 900}


def topology(identity, response, adapter, pre, post, current):
    """只消费正式关系；不提前检查失败前缀尚未到达的业务终态。"""
    root = response.get("output", {}).get("thread_id")
    delegation = adapter.get("delegation", {})
    rows = adapter.get("dispatch", {}).get("thread_relations")
    if not isinstance(rows, list) or not root:
        return {"evidence_set_id": identity, "status": "invalid", "checks": [],
                "reason": "正式关系字段缺失"}
    owners, direct, nested, conflicts = {}, set(), [], {}
    for row in rows:
        if row.get("tool") != "spawnAgent" or row.get("status") != "completed":
            continue
        sender = row.get("sender_thread_id")
        for child in row.get("receiver_thread_ids", []):
            if child in owners and owners[child] != sender:
                conflicts[child] = [owners[child], sender]
            owners[child] = sender
            if sender == root:
                direct.add(child)
        if sender != root:
            nested.append(row)
    checks = [check("formal_ownership", not conflicts, conflicts),
        check("no_nested_formal_spawn", not nested, nested),
        check("root_direct_spawn_child_count", len(direct) <= 4,
              {"observed": len(direct), "maximum": 4,
               "minimum_chain_roles": "由统一判定按实际到达阶段核对生成和校验，不要求失败前缀未来线程"}),
        check("pre_zero_write_snapshot", all(not v["exists"] for v in pre.values()), pre),
        check("post_matches_current", post == current, post)]
    value = surface(identity, checks, root_thread_id=root,
        root_direct_spawn_child_ids=sorted(direct), nested_formal_spawns=nested)
    value["classification"] = "INVALID_TEST_EXECUTION" if conflicts else \
        "PASS" if all(row["status"] == "pass" for row in checks) else "FAIL"
    return value


class Execution:
    def __init__(self, args):
        self.a = args
        self.repo = Path(args.repository).resolve()
        self.fixture = Path(args.fixture_root).resolve()
        self.out = Path(args.evidence_dir).resolve()
        self.product_source = validate_product_source_selector(args.product_source)
        if args.consumer:
            message = ("installation-check 必须创建全新消费者；不得传入 --consumer"
                       if args.mode == "installation-check" else "不支持复用消费者")
            raise RuntimeError(message)
        self.out.mkdir(parents=True, exist_ok=False)
        self.identity = self.out.name
        self.consumer = self.out / "consumer"
        if self.consumer.is_relative_to(self.repo):
            raise RuntimeError("消费者不得位于产品仓库内")
        self.program = self.consumer / "program"
        self.commands = self.out / "commands"
        self.commands.mkdir()
        self.counter = 0
        self.started = False
        self.formal_request_attempted = False
        self.formal_request_sent = False
        self.request_body_uploaded_bytes = None
        self.request_body_bytes_expected = None
        self.http_status = None
        self.http_status_raw = None
        self.transport_evidence = None
        self.writer_preexisting_paths = None
        self.writer_pre_snapshot_error = None

    def run(self, name, argv, *, cwd=None, required=True, private=False):
        self.counter += 1
        print(f"[{time.strftime('%H:%M:%S')}] {self.counter} {name}", flush=True)
        try:
            result = subprocess.run(argv, cwd=cwd or self.repo, capture_output=True,
                                    timeout=1200, check=False)
        except OSError as exc:
            if name == "eval-once":
                raise CommandNotStarted(str(exc)) from exc
            raise
        prefix = self.commands / f"{self.counter:03}-{name}"
        write(prefix.with_suffix(".json"), {
            "argv": argv, "cwd": str(cwd or self.repo),
            "exit_code": result.returncode,
            "stdout_sha256": digest(result.stdout),
            "stderr_sha256": digest(result.stderr),
            "sensitive_output_not_saved": private})
        if not private:
            prefix.with_suffix(".stdout").write_bytes(result.stdout)
            prefix.with_suffix(".stderr").write_bytes(result.stderr)
        if required and result.returncode:
            raise RuntimeError(f"{name} 退出码 {result.returncode}，原始原因见命令证据")
        return result

    def py(self, name, path, *argv, required=True):
        return self.run(name, ["uv", "run", "--no-project", "python", "-B",
                              str(path), *map(str, argv)], required=required)

    def versions(self):
        versions = {}
        for name, argv in (("uv", ["uv", "--version"]), ("apm", ["apm", "--version"]),
                           ("jq", ["jq", "--version"]), ("yq", ["yq", "--version"]),
                           ("direnv", ["direnv", "version"])):
            versions[name] = self.run(f"version-{name}", argv).stdout.decode().strip()
        versions["python"] = self.py("version-python", "-V").stdout.decode().strip()
        versions["git"] = self._git_fact("version-git", ["git", "--version"], self.repo)
        write(self.out / "versions.json", versions)

    def _git_fact(self, label, argv, cwd):
        """采集来源信息供定位；失败、修改或版本不同都不作运行门槛。"""
        try:
            result = self.run(label, argv, cwd=cwd, required=False)
        except OSError as exc:
            return {"value": None, "error": str(exc)}
        value = result.stdout.decode(errors="replace").strip() if result.returncode == 0 else None
        return {"value": value, "exit_code": result.returncode}

    def record_provenance(self):
        test_source = {
            "root": str(self.repo),
            "head": self._git_fact("test-source-head", ["git", "rev-parse", "HEAD"], self.repo),
            "worktree_status": self._git_fact("test-worktree-status",
                ["git", "status", "--porcelain", "--untracked-files=all"], self.repo),
        }
        fixture_source = {
            "root": str(self.fixture),
            "head": self._git_fact("fixture-source-head", ["git", "rev-parse", "HEAD"], self.fixture),
            "worktree_status": self._git_fact("fixture-worktree-status",
                ["git", "status", "--porcelain", "--untracked-files=all"], self.fixture),
        }
        adapter_files = {}
        for relative in ("scripts/parse_codex_eval_evidence.py",
                         "configs/codex-eval-adapter-contract.json"):
            path = self.fixture / relative
            adapter_files[relative] = {
                "path": str(path),
                "exists": path.is_file() and not path.is_symlink(),
                "sha256_for_location_only": digest(path.read_bytes())
                    if path.is_file() and not path.is_symlink() else None,
            }
        self.provenance = {
            "plan": PLAN,
            "product_source_input": self.product_source,
            "product_source_kind": "remote_selector",
            "test_source": test_source,
            "fixture_source": fixture_source,
            "adapter_source": {"root": str(self.fixture), "files": adapter_files},
            "tool_versions": jq(self.out / "versions.json"),
            "repository": str(self.repo),
            "invocation_directory": str(Path.cwd()),
            "evidence_set_id": self.identity,
            "worktree_status_is_informational": True,
            "software_file_hashes_are_informational": True,
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "sandbox": SANDBOX,
        }
        write(self.out / "provenance.json", self.provenance)

    def port(self):
        result = self.run("eval-port", ["direnv", "exec", ".", "printenv", "EVAL_PORT"])
        value = result.stdout.decode().strip()
        if not value.isdigit() or not 1 <= int(value) <= 65535:
            raise RuntimeError("项目环境未提供有效 EVAL_PORT")
        return value

    def credential_observation(self):
        captures = jq(self.out / "response-raw.json", '''[
          .output.app_server_events[] | select(.message.method=="item/completed")
          | .message.params.item | select(.type=="commandExecution")
          | select(.command | contains("--capture-invocation"))
          | (.aggregatedOutput | fromjson)
          | select(.status=="ok" and (.invocation_file|type)=="string")
          | {invocation_file,invocation_sha256}
        ]''')
        if len(captures) != 1:
            raise RuntimeError("实际捕获完成返回缺失或不是唯一一次")
        capture = captures[0]
        observed = Path(capture["invocation_file"])
        path = observed.resolve()
        if observed.is_symlink() or not path.is_relative_to(self.consumer) or not path.is_file():
            raise RuntimeError("捕获凭据不是本次消费者中的普通文件")
        raw = path.read_bytes()
        profile = self.program / "套磁邮件/套磁信息.md"
        relative = str(profile.relative_to(self.program))
        original = self.initial["input_hashes"].get(relative)
        actual = digest(profile.read_bytes())
        if original is None or actual != original:
            raise RuntimeError("资料实际字节不符合合法初态")
        return {**capture, "invocation_utf8": raw.decode("utf-8"),
                "observed_invocation_sha256": digest(raw),
                "profile_path": str(profile), "profile_sha256": actual,
                "profile_utf8": profile.read_bytes().decode("utf-8"),
                "profile_initial_sha256": original}

    def formal(self, port):
        request_path = self.out / "request.json"
        request_bytes = request_path.read_bytes()
        self.writer_preexisting_paths = self._snapshot_writer_handoff_paths()
        self.request_body_bytes_expected = len(request_bytes)
        self.formal_request_attempted = True
        write(self.out / "attempt.json", {"evidence_set_id": self.identity,
              "start_time_unix": time.time(), "request_sha256": digest(request_bytes),
              "request_body_bytes_expected": self.request_body_bytes_expected,
              "formal_request_attempted": True, "attempt_number": 1,
              "maximum_attempts": 1})
        argv = ["curl", "--silent", "--show-error", "--max-time", "930",
            "--request", "POST", f"http://127.0.0.1:{port}/eval",
            "--header", "Content-Type: application/json", "--data-binary",
            f"@{request_path}", "--output", str(self.out / "response-raw.json"),
            "--write-out", "%{http_code}\\t%{size_upload}"]
        curl_process_started = True
        try:
            result = self.run("eval-once", argv, required=False)
            write_out_raw = result.stdout
            exit_code = result.returncode
        except CommandNotStarted as exc:
            curl_process_started = False
            write_out_raw = b""
            exit_code = None
            transport_error = str(exc)
        except subprocess.SubprocessError as exc:
            # 超时等情形中进程已启动，但上传量和响应状态无法确认。
            write_out_raw = getattr(exc, "stdout", None) or b""
            exit_code = None
            transport_error = str(exc)
        parsed = _curl_write_out(write_out_raw)
        if not curl_process_started:
            parsed["request_body_uploaded_bytes"] = 0
        self.request_body_uploaded_bytes = parsed["request_body_uploaded_bytes"]
        self.formal_request_sent = None if self.request_body_uploaded_bytes is None \
            else self.request_body_uploaded_bytes > 0
        self.http_status = parsed["http_status"]
        self.http_status_raw = parsed["http_status_raw"]
        self.transport_evidence = {
            "evidence_set_id": self.identity,
            "formal_request_attempted": True,
            "formal_request_sent": self.formal_request_sent,
            "curl_process_started": curl_process_started,
            "exit_code": exit_code,
            "http_status_raw": self.http_status_raw,
            "http_status": self.http_status,
            "http_response_received": self.http_status is not None,
            "request_body_bytes_expected": self.request_body_bytes_expected,
            "request_body_uploaded_bytes": self.request_body_uploaded_bytes,
            "request_body_fully_uploaded": self.request_body_uploaded_bytes ==
                self.request_body_bytes_expected if self.request_body_uploaded_bytes is not None else None,
            "curl_write_out_raw": write_out_raw.decode("utf-8", errors="replace"),
        }
        if "transport_error" in locals():
            self.transport_evidence["transport_error"] = transport_error
        write(self.out / "transport.json", self.transport_evidence)
        classification = _transport_classification(exit_code, self.http_status,
            self.request_body_uploaded_bytes, self.request_body_bytes_expected)
        if classification:
            write(self.out / "writer.json", self._writer_evidence(
                native_calls=[], observations=[], gaps=[
                    "正式响应未进入可观察的 Stage 3 原生调用"], save_input=None))
            reason = ("正式请求体确认零字节上传且未收到 HTTP 响应；用例未进入被测启动边界"
                      if classification == "CASE_NOT_STARTED" else
                      "正式请求的传输失败或无法确认；按外部阻断处理，不重试")
            write(self.out / "verdict.json", {
                "classification": classification,
                "reason": reason,
                "formal_request_attempted": True,
                "formal_request_sent": self.formal_request_sent,
                "request_body_bytes_expected": self.request_body_bytes_expected,
                "request_body_uploaded_bytes": self.request_body_uploaded_bytes,
                "http_status_raw": self.http_status_raw,
                "http_status": self.http_status,
                "transport_evidence": "transport.json",
                "facts": [],
            })
            print(reason, file=sys.stderr)
            return 2
        try:
            response = jq(self.out / "response-raw.json")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            write(self.out / "writer.json", self._writer_evidence(
                native_calls=[], observations=[], gaps=[
                    f"正式原始响应无法解析；writer 观察未完成：{exc}"], save_input=None))
            raise
        write(self.out / "writer.json", self.collect_writer_evidence(response))
        self.started = bool(response.get("output", {}).get("thread_id")
                            and response.get("output", {}).get("turn_id"))
        self.py("adapter", self.fixture / "scripts/parse_codex_eval_evidence.py",
            "--contract", self.fixture / "configs/codex-eval-adapter-contract.json",
            "--eval-response", self.out / "response-raw.json", "--consumer-root", self.consumer,
            "--expected-agent", "professor-contact-idea-generator",
            "--expected-agent", "professor-contact-style-validator",
            "--output", self.out / "adapter-raw.json", required=False)
        adapter = jq(self.out / "adapter-raw.json")
        # 只向派生副本加入证据编号，原始响应与原始适配器输出永久保留。
        write(self.out / "response.json", {**response, "evidence_set_id": self.identity})
        write(self.out / "adapter.json", {**adapter, "evidence_set_id": self.identity})
        after = snapshot(self.program)
        write(self.out / "post.json", surface(self.identity, [
            check("post_matches_current", after == snapshot(self.program), after)], artifacts=after))
        write(self.out / "routing.json", topology(self.identity, response, adapter,
              self.before, after, snapshot(self.program)))
        fixture_value = jq(self.out / "fixture-pre.json")
        try:
            fixture_value["credential_observation"] = self.credential_observation()
        except (RuntimeError, OSError, UnicodeError, subprocess.CalledProcessError) as exc:
            fixture_value["credential_observation_gap"] = str(exc)
        write(self.out / "fixture.json", fixture_value)
        candidate = self.program / PROFESSOR / "套磁候选状态.json"
        self.py("unique-judge", HERE / "judge_issue66_stage3_runtime.py",
            "--eval-response", self.out / "response.json",
            "--adapter-output", self.out / "adapter.json",
            "--writer-evidence", self.out / "writer.json",
            "--candidate-state", candidate, "--program-root", self.program,
            "--install-evidence", self.out / "install.json",
            "--fixture-evidence", self.out / "fixture.json",
            "--routing-evidence", self.out / "routing.json",
            "--pre-snapshot", self.out / "pre.json", "--post-snapshot", self.out / "post.json",
            "--output", self.out / "judge-verdict.json",
            required=False)
        judge_verdict = jq(self.out / "judge-verdict.json")
        verdict = {**judge_verdict,
            "formal_request_attempted": True,
            "formal_request_sent": self.formal_request_sent,
            "request_body_bytes_expected": self.request_body_bytes_expected,
            "request_body_uploaded_bytes": self.request_body_uploaded_bytes,
            "http_status_raw": self.http_status_raw,
            "http_status": self.http_status,
            "transport_evidence": "transport.json",
            "judge_verdict_evidence": "judge-verdict.json"}
        write(self.out / "verdict.json", verdict)
        return 0 if verdict["classification"] == "PASS" else 1

    def execute(self):
        self.run("invocation-directory", ["pwd"])
        self.versions()
        self.record_provenance()
        if self.a.mode == "installation-check":
            if not self.install():
                return 2
            return 0 if self.installation_writer_check() == "PASS" else 2
        if self.a.mode == "preflight":
            self.install()
            self.prepare()
            write(self.out / "preflight.json", {"classification": "PREFLIGHT_ONLY",
                  "formal_request_attempted": False, "formal_request_sent": False,
                  "evidence_set_id": self.identity,
                  "prepared": ["installation", "initial_input", "request", "snapshot"],
                  "remaining": ["正式运行业务文件生产、保存及权限事实"]})
            return 0
        port = self.port()
        self.install()
        self.prepare()
        return self.formal(port)


    def _writer_evidence(self, observations=None, **values):
        return {"schema": WRITER_EVIDENCE_SCHEMA,
                "evidence_set_id": self.identity,
                "observations": observations or [], **values}

    def _write_installation_not_started(self, reason):
        value = self._writer_evidence(
            controlled_call=None, native_calls=[], gaps=[reason], save_input=None,
            classification="CASE_NOT_STARTED", reason=reason)
        write(self.out / "writer.json", value)
        write(self.out / "verdict.json", {
            "classification": "CASE_NOT_STARTED", "reason": reason,
            "formal_request_attempted": False, "formal_request_sent": False,
            "evidence_set_id": self.identity, "save_input": None,
            "writer_evidence": "writer.json"})
        write(self.out / "preflight.json", {
            "classification": "CASE_NOT_STARTED", "reason": reason,
            "formal_request_attempted": False, "formal_request_sent": False,
            "evidence_set_id": self.identity, "save_input": None,
            "prepared": ["installation attempt"],
            "remaining": ["安装成功后受控调用实际 Stage 3 writer"]})

    def installation_writer_check(self):
        """Call the installed writer on one isolated synthetic output only."""
        script = self.consumer / ".agents/skills/professor-contact/scripts/contact_state.py"
        try:
            installed_source = script.resolve(strict=True)
            source_is_owned = installed_source.is_relative_to(self.consumer.resolve())
        except (OSError, RuntimeError, ValueError):
            installed_source = None
            source_is_owned = False
        if script.is_symlink() or not script.is_file() or not source_is_owned:
            reason = "APM 安装成功但实际安装的 contact_state.py 缺失或不是普通文件"
            write(self.out / "writer.json", self._writer_evidence(
                controlled_call=None, native_calls=[], gaps=[reason], save_input=None,
                classification="BLOCKED", reason=reason))
            write(self.out / "verdict.json", {
                "classification": "BLOCKED", "reason": reason,
                "formal_request_attempted": False, "formal_request_sent": False,
                "evidence_set_id": self.identity, "save_input": None,
                "writer_evidence": "writer.json"})
            write(self.out / "preflight.json", {
                "classification": "BLOCKED", "reason": reason,
                "formal_request_attempted": False, "formal_request_sent": False,
                "evidence_set_id": self.identity,
                "prepared": ["installation"], "remaining": ["受控 writer 调用"]})
            return "BLOCKED"

        probe_dir = self.consumer / "issue66-writer-check"
        try:
            probe_dir.mkdir()
        except OSError as exc:
            reason = f"独占 writer 检查目录不可用：{exc}"
            write(self.out / "writer.json", self._writer_evidence(
                controlled_call=None, native_calls=[], gaps=[reason], save_input=None,
                classification="BLOCKED", reason=reason))
            write(self.out / "verdict.json", {
                "classification": "BLOCKED", "reason": reason,
                "formal_request_attempted": False, "formal_request_sent": False,
                "evidence_set_id": self.identity, "save_input": None,
                "writer_evidence": "writer.json"})
            write(self.out / "preflight.json", {
                "classification": "BLOCKED", "reason": reason,
                "formal_request_attempted": False, "formal_request_sent": False,
                "evidence_set_id": self.identity,
                "prepared": ["installation"], "remaining": ["受控 writer 调用"]})
            return "BLOCKED"

        target = probe_dir / "validation.json"
        result = {"result": "ok", "files": [{
            "file": str(self.program / PROFESSOR / "套磁想法候选.md"),
            "artifact": "candidates", "verdict": "pass",
            "blocking": 0, "minor": 0, "issues": []}],
            "notes": "独占安装检查的合成输入"}
        argv = ["python3", str(script), "stage3-write-validation",
                "--output-file", str(target), "--result-json",
                json.dumps(result, ensure_ascii=False)]
        exists_before = target.exists() or target.is_symlink()
        source_bytes = installed_source.read_bytes()
        call = {"source": str(installed_source),
                "source_sha256": digest(source_bytes),
                "argv": argv, "command": shlex.join(argv),
                "cwd": str(self.consumer), "exit_code": None,
                "stdout_b64": None, "stderr_b64": None,
                "output": {"path": str(target),
                           "exists_before": exists_before,
                           "exists_after": False, "mode": None,
                           "bytes_b64": None},
                "command_log": None}
        try:
            completed = self.run("installation-writer-check", argv,
                                 cwd=self.consumer, required=False)
            stdout, stderr = completed.stdout, completed.stderr
            call["exit_code"] = completed.returncode
            call["stdout_b64"] = _b64(stdout)
            call["stderr_b64"] = _b64(stderr)
            call["command_log"] = {
                "metadata": f"commands/{self.counter:03}-installation-writer-check.json",
                "stdout": f"commands/{self.counter:03}-installation-writer-check.stdout",
                "stderr": f"commands/{self.counter:03}-installation-writer-check.stderr"}
        except (OSError, subprocess.SubprocessError) as exc:
            stdout = getattr(exc, "stdout", None) or b""
            stderr = getattr(exc, "stderr", None) or b""
            call["stdout_b64"] = _b64(stdout)
            call["stderr_b64"] = _b64(stderr)
            call["error"] = str(exc)
            call["command_log"] = None

        exists_after = target.exists() or target.is_symlink()
        output_bytes = None
        mode = None
        if exists_after and target.is_file() and not target.is_symlink():
            output_bytes = target.read_bytes()
            mode = format(stat.S_IMODE(target.stat().st_mode), "04o")
        call["output"] = {"path": str(target),
                          "exists_before": exists_before,
                          "exists_after": exists_after, "mode": mode,
                          "bytes_b64": _b64(output_bytes)}
        result_json_values = _flag_values(argv, "--result-json")
        argument_result = (_strict_json_value(result_json_values[0])
                           if len(result_json_values) == 1 else None)
        stdout_result = _strict_json_value(stdout)
        argument_is_complete = _complete_writer_result(argument_result)
        stdout_is_complete = _complete_writer_result(stdout_result)
        semantic_match = argument_is_complete and stdout_is_complete \
            and _json_semantically_equal(argument_result, stdout_result)
        if call["exit_code"] is None or call["exit_code"] != 0:
            status = "BLOCKED"
            reason = "受控 writer 命令未能以零退出码完成"
        elif exists_before or not exists_after or mode != "0600" \
                or not stdout or not output_bytes \
                or not argument_is_complete or not stdout_is_complete \
                or not semantic_match or output_bytes != stdout:
            status = "FAIL"
            reason = "受控 writer 的完整 JSON、语义一致、独占路径、0600 权限或逐字节输出检查失败"
        else:
            status = "PASS"
            reason = "受控 writer 参数与输出是语义一致的完整 JSON；输出与新建文件逐字节一致且权限为 0600"
        writer = self._writer_evidence(
            controlled_call=call, native_calls=[], gaps=[], save_input=None,
            classification=status, reason=reason)
        write(self.out / "writer.json", writer)
        classification = "PREFLIGHT_ONLY" if status == "PASS" else status
        write(self.out / "verdict.json", {
            "classification": classification, "reason": reason,
            "formal_request_attempted": False, "formal_request_sent": False,
            "evidence_set_id": self.identity, "save_input": None,
            "writer_evidence": "writer.json"})
        write(self.out / "preflight.json", {
            "classification": classification, "reason": reason,
            "formal_request_attempted": False, "formal_request_sent": False,
            "evidence_set_id": self.identity, "save_input": None,
            "prepared": ["installation", "controlled installed-writer call"],
            "remaining": ["正式运行、原生委派、保存及记录事实"]})
        return status

    def _snapshot_writer_handoff_paths(self):
        root = Path(tempfile.gettempdir()) / STAGE3_HANDOFF_ROOT
        try:
            if not root.exists() and not root.is_symlink():
                return set()
            if root.is_symlink() or not root.is_dir():
                raise OSError("Stage 3 temporary handoff root is not a directory")
            return {str(path.absolute()) for path in root.rglob("*")}
        except OSError as exc:
            self.writer_pre_snapshot_error = str(exc)
            return None

    def collect_writer_evidence(self, response):
        """Bind native save output to the exact writer source bytes it digested.

        The post-response filesystem snapshot can corroborate bytes only when
        they match the digest emitted by the successful save command. It does
        not establish the source file's mode or state immediately before save.
        """
        gaps, native_calls, observations = [], [], []
        output = response.get("output") if isinstance(response, dict) else None
        raw_events = output.get("app_server_events") if isinstance(output, dict) else None
        if not isinstance(raw_events, list):
            return self._writer_evidence(native_calls=[], observations=[],
                gaps=["raw app_server_events 缺失；writer 观察未开始"], save_input=None)

        root_thread = output.get("thread_id")
        root_turn = output.get("turn_id")
        if not isinstance(root_thread, str) or not root_thread \
                or not isinstance(root_turn, str) or not root_turn:
            gaps.append("正式响应缺少根线程或轮次身份；无法绑定 prepare 与 save")

        def valid_sha256(value):
            return isinstance(value, str) and len(value) == 64 \
                and all(character in "0123456789abcdef" for character in value)

        def valid_absolute_path(value):
            if not isinstance(value, str) or not value:
                return False
            try:
                candidate = Path(value)
                return candidate.is_absolute() and candidate.resolve(strict=False).is_absolute()
            except (OSError, RuntimeError, ValueError):
                return False

        def valid_professor(value):
            return isinstance(value, str) and bool(value.strip())

        def stdout_object(call):
            encoded = call.get("stdout_b64")
            if not isinstance(encoded, str):
                return None
            try:
                return _strict_json_value(base64.b64decode(encoded, validate=True))
            except (ValueError, TypeError):
                return None

        def completed_successfully(call):
            exit_code = call.get("exit_code")
            return call.get("status") == "completed" \
                and type(exit_code) is int and exit_code == 0

        calls = []
        for event_index, event in enumerate(raw_events):
            if not isinstance(event, dict):
                continue
            message = event.get("message")
            params = message.get("params") if isinstance(message, dict) else None
            item = params.get("item") if isinstance(params, dict) else None
            if not isinstance(params, dict) or not isinstance(item, dict) \
                    or message.get("method") != "item/completed" \
                    or item.get("type") != "commandExecution":
                continue
            command = item.get("command")
            if not isinstance(command, str):
                continue
            event_cwd = item.get("cwd") if item.get("cwd") is not None \
                else params.get("cwd")
            parsed = _stage3_command(command, event_cwd)
            if parsed is None:
                if "contact_state.py" in command and "stage3-" in command:
                    gaps.append(f"event {event_index}: Stage 3 command argv is ambiguous")
                continue
            subcommand, source, argv = parsed
            if subcommand not in {"stage3-prepare-validation",
                                  "stage3-write-validation",
                                  "stage3-save-validation"}:
                continue
            identity = _native_identity(params, item)
            raw_stdout = item.get("aggregatedOutput")
            stdout_bytes = raw_stdout.encode("utf-8") if isinstance(raw_stdout, str) else None
            call = {"event_index": event_index, "thread_id": params.get("threadId"),
                    "turn_id": params.get("turnId"), "item_id": item.get("id"),
                    "call_id": item.get("call_id"), "subcommand": subcommand,
                    "source": source, "argv": argv, "command": command,
                    "cwd": item.get("cwd") or params.get("cwd"),
                    "status": item.get("status"), "exit_code": item.get("exitCode"),
                    "stdout_b64": _b64(stdout_bytes), "identity": identity}
            calls.append(call)
            if subcommand == "stage3-write-validation":
                native_calls.append({key: value for key, value in call.items()
                                     if key != "identity"})

        prepared = []
        for call in calls:
            if call["subcommand"] != "stage3-prepare-validation":
                continue
            payload = stdout_object(call)
            if call["thread_id"] != root_thread \
                    or call["turn_id"] != root_turn or call["identity"] is None:
                gaps.append(f"event {call['event_index']}: prepare 缺少根线程/轮次/命令身份绑定")
                continue
            if not completed_successfully(call):
                gaps.append(f"event {call['event_index']}: prepare command did not complete successfully")
                continue
            if not isinstance(payload, dict) or payload.get("status") != "ok":
                gaps.append(f"event {call['event_index']}: prepare stdout 不是完整成功对象")
                continue
            round_no = payload.get("round")
            output_file = payload.get("output_file")
            handoff_file = payload.get("handoff_file")
            validation_file = payload.get("validation_file")
            handoff_sha = payload.get("handoff_sha256")
            render_sha = payload.get("render_sha256")
            professor = payload.get("professor")
            professor_dir = payload.get("professor_dir")
            candidates_md = payload.get("candidates_md")
            if type(round_no) is not int or round_no < 1 \
                    or any(not valid_absolute_path(value)
                           for value in (output_file, handoff_file, validation_file,
                                         professor_dir, candidates_md)) \
                    or not valid_professor(professor) \
                    or output_file == validation_file \
                    or not valid_sha256(handoff_sha) or not valid_sha256(render_sha):
                gaps.append(f"event {call['event_index']}: prepare return misses valid paths, round, or digests")
                continue
            prepared.append({"round": round_no, "output_file": output_file,
                "validation_file": validation_file, "handoff_file": handoff_file,
                "handoff_sha256": handoff_sha, "render_sha256": render_sha,
                "professor": professor, "professor_dir": professor_dir,
                "event_index": call["event_index"], "identity": call["identity"]})

        def file_state(path_text):
            path = Path(path_text)
            lexical = str(path.absolute())
            if self.writer_preexisting_paths is None:
                return None, {"path": path_text, "exists_before": None,
                    "exists_after": path.exists() or path.is_symlink(),
                    "mode": None, "bytes_b64": None}
            root = Path(tempfile.gettempdir()) / STAGE3_HANDOFF_ROOT
            try:
                normalized = str(path.resolve(strict=False))
                inside_root = Path(normalized).is_relative_to(root.resolve(strict=False))
            except (OSError, RuntimeError, ValueError):
                inside_root = False
                normalized = lexical
            exists_before = lexical in self.writer_preexisting_paths
            exists_after = path.exists() or path.is_symlink()
            mode, raw = None, None
            if exists_after and path.is_file() and not path.is_symlink():
                try:
                    raw = path.read_bytes()
                    mode = format(stat.S_IMODE(path.stat().st_mode), "04o")
                except OSError:
                    raw = None
            state = {"path": path_text, "exists_before": exists_before,
                     "exists_after": exists_after, "mode": mode,
                     "bytes_b64": _b64(raw)}
            if not inside_root:
                return None, state
            return state, state

        for writer in calls:
            if writer["subcommand"] != "stage3-write-validation":
                continue
            values = _flag_values(writer["argv"], "--output-file")
            if len(values) != 1 or not isinstance(values[0], str) or not values[0]:
                gaps.append(f"event {writer['event_index']}: writer --output-file argv is missing or ambiguous")
                continue
            output_path = str(_lexical_path(values[0], writer["cwd"]))
            matches = [entry for entry in prepared
                       if str(_lexical_path(entry["output_file"])) == output_path
                       and entry["event_index"] < writer["event_index"]]
            if len(matches) != 1:
                gaps.append(f"event {writer['event_index']}: writer output path does not bind one prior prepare return")
                continue
            entry = matches[0]
            output_state, observed_state = file_state(entry["output_file"])
            native_call = next((row for row in native_calls
                                if row["event_index"] == writer["event_index"]), None)
            if native_call is not None:
                native_call["round"] = entry["round"]
                native_call["output"] = observed_state
            if output_state is None or not Path(output_state["path"]).is_absolute() \
                    or output_state["exists_after"] and (
                        output_state["bytes_b64"] is None) \
                    or writer["identity"] is None:
                gaps.append(f"round {entry['round']}: writer file or native output could not be observed reliably")
                continue
            if not completed_successfully(writer):
                gaps.append(f"round {entry['round']}: writer did not complete successfully; save input cannot be bound")

            writer_stdout_bytes = None
            try:
                if isinstance(writer["stdout_b64"], str):
                    writer_stdout_bytes = base64.b64decode(
                        writer["stdout_b64"], validate=True)
            except (ValueError, TypeError):
                writer_stdout_bytes = None
            if writer_stdout_bytes is None:
                gaps.append(f"round {entry['round']}: writer stdout bytes are missing or cannot be strictly decoded")

            save_matches = []
            for save in calls:
                if save["subcommand"] != "stage3-save-validation" \
                        or save["event_index"] <= writer["event_index"] \
                        or save["thread_id"] != root_thread:
                    continue
                handoff_values = _flag_values(save["argv"], "--handoff-file")
                if len(handoff_values) == 1 and handoff_values[0] \
                        and str(_lexical_path(handoff_values[0], save["cwd"])) == \
                            str(_lexical_path(entry["handoff_file"])):
                    save_matches.append(save)
            save_input = None
            if len(save_matches) == 1:
                save = save_matches[0]
                save_handoff_hash = _flag_values(save["argv"], "--handoff-sha256")
                save_payload = stdout_object(save)
                source_bytes = None
                if output_state and output_state.get("bytes_b64") is not None:
                    try:
                        source_bytes = base64.b64decode(
                            output_state["bytes_b64"], validate=True)
                    except (ValueError, TypeError):
                        source_bytes = None
                if source_bytes is not None and writer_stdout_bytes is not None \
                        and source_bytes != writer_stdout_bytes:
                    gaps.append(f"round {entry['round']}: post-response source bytes differ from native writer stdout; save input cannot be bound")
                complete_save = isinstance(save_payload, dict) and all(
                    field in save_payload for field in (
                        "status", "professor", "professor_dir", "round",
                        "render_sha256", "validation_file", "validation_sha256"))
                complete_save = complete_save and \
                    save_payload.get("status") == "ok" \
                    and valid_professor(save_payload.get("professor")) \
                    and valid_absolute_path(save_payload.get("professor_dir")) \
                    and type(save_payload.get("round")) is int \
                    and valid_sha256(save_payload.get("render_sha256")) \
                    and valid_absolute_path(save_payload.get("validation_file")) \
                    and valid_sha256(save_payload.get("validation_sha256"))
                save_bound = completed_successfully(save) \
                    and save["identity"] is not None \
                    and completed_successfully(writer) \
                    and save["turn_id"] == entry["identity"]["turn_id"] == root_turn \
                    and len(save_handoff_hash) == 1 \
                    and save_handoff_hash[0] == entry["handoff_sha256"] \
                    and complete_save \
                    and save_payload.get("round") == entry["round"] \
                    and save_payload.get("validation_file") == entry["validation_file"] \
                    and save_payload.get("render_sha256") == entry["render_sha256"] \
                    and save_payload.get("professor") == entry["professor"] \
                    and str(_lexical_path(save_payload["professor_dir"], save["cwd"])) \
                        == str(_lexical_path(entry["professor_dir"], save["cwd"])) \
                    and output_state is not None \
                    and output_state.get("exists_after") is True \
                    and source_bytes is not None \
                    and writer_stdout_bytes is not None \
                    and source_bytes == writer_stdout_bytes \
                    and digest(source_bytes) == save_payload.get("validation_sha256")
                if save_bound:
                    save_input = {**save["identity"], "path": entry["output_file"],
                                  "bytes_b64": _b64(source_bytes)}
                    gaps.append(f"round {entry['round']}: save success proves a regular source was read, but save-time mode/timing is unavailable; the post-response snapshot cannot establish it")
                else:
                    gaps.append(f"round {entry['round']}: save return, handoff, identity, or source-byte digest cannot be bound")
            if len(save_matches) > 1:
                gaps.append(f"round {entry['round']}: multiple native save calls match the writer handoff")
            elif not save_matches:
                gaps.append(f"round {entry['round']}: no unique native save command matches the writer handoff")

            observations.append({"round": entry["round"],
                "writer_call": writer["identity"], "command": writer["command"],
                "stdout_b64": writer["stdout_b64"], "output": output_state,
                "save_input": save_input})
        if self.writer_pre_snapshot_error:
            gaps.append(f"writer temporary-file pre-snapshot unavailable: {self.writer_pre_snapshot_error}")
        return self._writer_evidence(observations=observations,
            native_calls=native_calls, gaps=gaps)


    def install(self):
        argv = ["apm", "install", "--target", "codex", "--parallel-downloads", "1",
                f"ScholarWorkflow/professor-contact#{self.product_source}"]
        installation = {
            "method": "apm install --target codex --parallel-downloads 1",
            "source_mode": "remote_selector", "argv": argv,
            "command": shlex.join(argv), "cwd": str(self.consumer),
            "exit_code": None, "stdout_b64": None, "stderr_b64": None,
            "command_log": None}
        try:
            self.consumer.mkdir()
            result = self.run("install", argv, cwd=self.consumer, required=False)
            installation.update({
                "exit_code": result.returncode,
                "stdout_b64": _b64(result.stdout),
                "stderr_b64": _b64(result.stderr),
                "command_log": {
                    "metadata": f"commands/{self.counter:03}-install.json",
                    "stdout": f"commands/{self.counter:03}-install.stdout",
                    "stderr": f"commands/{self.counter:03}-install.stderr"}})
        except (OSError, subprocess.SubprocessError) as exc:
            installation["error"] = str(exc)
            installation["stdout_b64"] = _b64(getattr(exc, "stdout", None) or b"")
            installation["stderr_b64"] = _b64(getattr(exc, "stderr", None) or b"")
        lock = self.consumer / "apm.lock.yaml"
        installed_commits = None
        lock_observation = {"path": str(lock), "exists": lock.is_file(), "parse_status": "not_available"}
        if lock.is_file() and not lock.is_symlink():
            parsed_result = self.run("parse-lock-for-recording", ["yq", "-o=json", ".", str(lock)],
                                     required=False)
            lock_observation["exit_code"] = parsed_result.returncode
            if parsed_result.returncode == 0:
                parsed = self.out / "lock.json"
                parsed.write_bytes(parsed_result.stdout)
                try:
                    installed_commits = jq(parsed,
                        '[.dependencies[]? | select(.name=="professor-contact") | .resolved_commit]')
                    lock_observation["parse_status"] = "parsed_for_recording"
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    lock_observation["parse_status"] = "unavailable"
                    lock_observation["parse_error"] = str(exc)
            else:
                lock_observation["parse_status"] = "unavailable"
        install_available = installation["exit_code"] == 0
        value = surface(self.identity, [
            check("supported_install_entry_completed", install_available, installation)],
            requested_product_source=self.product_source,
            product_source_kind="remote_selector",
            installed_product_versions=installed_commits,
            lock_observation=lock_observation,
            consumer_root=str(self.consumer), newly_created=True,
            manual_patch="no")
        self.install_value = value
        write(self.out / "install.json", value)
        if value["status"] != "ok":
            if self.a.mode == "installation-check":
                self._write_installation_not_started(
                    "APM 安装未成功；Stage 3 writer 命令未运行，save_input 为 null")
                return False
            raise RuntimeError("支持的安装入口未完成或独占消费者不存在")
        return True

    def prepare(self):
        # 使用本轮测试工作区中的受支持夹具构造纯初态，只写独占消费者。
        builder_checks = []
        for name in ("prepare_issue55_stage3_fixture.py", "fixture_support.py"):
            asset = HERE / name
            exists = asset.is_file() and not asset.is_symlink()
            builder_checks.append(check(name, exists,
                {"path": str(asset), "exists": exists,
                 "sha256_for_location_only": digest(asset.read_bytes()) if exists else None}))
        verified = surface(self.identity, builder_checks,
                           test_source=self.provenance["test_source"])
        write(self.out / "initial-builder.json", verified)
        if verified["status"] != "ok":
            raise RuntimeError("初态构造程序或其直接辅助缺失或不是普通文件")
        self.py("build-initial-fixture", HERE / "prepare_issue55_stage3_fixture.py",
                "--program-root", self.program, "--output", self.out / "initial-input.json")
        initial = jq(self.out / "initial-input.json")
        hashes = initial.get("input_hashes", {})
        hash_checks = [check(relative,
            (self.program / relative).is_file()
            and digest((self.program / relative).read_bytes()) == expected,
            {"path": relative, "expected": expected}) for relative, expected in hashes.items()]
        before = snapshot(self.program)
        fixture_value = surface(self.identity, [
            check("frozen_initial_builder", verified["status"] == "ok", verified),
            check("no_manual_patch", initial.get("manual_patch") == "no", initial.get("manual_patch")),
            check("initial_input_digest", bool(hashes) and all(
                row["status"] == "pass" for row in hash_checks), hash_checks),
            check("forbidden_outputs_absent", all(not row["exists"] for row in before.values()), before)],
            manual_patch="no", fixture_source=self.provenance["fixture_source"], input_hashes=hashes)
        write(self.out / "fixture-pre.json", fixture_value)
        if fixture_value["status"] != "ok":
            raise RuntimeError("初始输入或禁止产物不满足正式前提")
        req = request(self.consumer, self.program)
        write(self.out / "request.json", req)
        (self.out / "prompt.txt").write_text(shlex.split(req["command"])[-1], encoding="utf-8")
        write(self.out / "pre.json", surface(self.identity, [
            check("pre_zero_write_snapshot", all(not row["exists"] for row in before.values()), before)],
            artifacts=before))
        self.initial = initial
        self.before = before
        write(self.out / "request-configuration.json", {
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "sandbox": SANDBOX,
            "command": req["command"],
        })

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "formal", "installation-check"))
    parser.add_argument("--repository", required=True)
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--product-source", required=True,
                         help="本轮实际要安装的 professor-contact 来源或版本选择器")
    parser.add_argument("--consumer")
    args = parser.parse_args(argv)
    execution = None
    try:
        execution = Execution(args)
        return execution.execute()
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        if execution and not (execution.out / "verdict.json").exists():
            write(execution.out / "verdict.json", {
                "classification": "INVALID_TEST_EXECUTION"
                    if execution.formal_request_attempted else "CASE_NOT_STARTED",
                "reason": str(exc),
                "formal_request_attempted": execution.formal_request_attempted,
                "formal_request_sent": execution.formal_request_sent,
                "request_body_bytes_expected": execution.request_body_bytes_expected,
                "request_body_uploaded_bytes": execution.request_body_uploaded_bytes,
                "http_status_raw": execution.http_status_raw,
                "http_status": execution.http_status,
                "evidence_set_id": execution.identity,
                "facts": [{"fact": "F-execution-wiring", "verdict": "gap", "evidence": str(exc)}]})
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
