#!/usr/bin/env python3
"""Issue 66 的待审安装、取证及执行接线；预检永不发送评测请求。"""
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path, PureWindowsPath

PLAN = "issue-66-test-plan-r20-stage3-write-validation-r8-2026-10-08"
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
        self.out.mkdir(parents=True, exist_ok=False)
        self.identity = self.out.name
        self.consumer = self.out / "consumer"
        if args.consumer:
            if args.mode != "installation-check":
                raise RuntimeError("复用消费者只允许用于安装预检")
            self.consumer = Path(args.consumer).resolve()
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
        response = jq(self.out / "response-raw.json")
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
            self.install()
            self.prepare()
            write(self.out / "preflight.json", {"classification": "PREFLIGHT_ONLY",
                  "formal_request_attempted": False, "formal_request_sent": False,
                  "evidence_set_id": self.identity,
                  "prepared": ["installation", "initial_input", "request", "snapshot"],
                  "remaining": ["正式运行业务生产、保存及权限事实"]})
            return 0
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


    def install(self):
        installation = {"method": "existing-consumer-installation-check", "exit_code": None}
        if not self.a.consumer:
            self.consumer.mkdir()
            result = self.run("install", ["apm", "install", "--target", "codex",
                "--parallel-downloads", "1",
                f"ScholarWorkflow/professor-contact#{self.product_source}"], cwd=self.consumer)
            installation = {"method": "apm install --target codex --parallel-downloads 1",
                            "source_mode": "remote_selector", "exit_code": result.returncode}
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
        install_available = installation["exit_code"] == 0 if installation["exit_code"] is not None \
            else self.consumer.is_dir()
        value = surface(self.identity, [
            check("supported_install_entry_completed", install_available, installation)],
            requested_product_source=self.product_source,
            product_source_kind="remote_selector",
            installed_product_versions=installed_commits,
            lock_observation=lock_observation,
            consumer_root=str(self.consumer), newly_created=not bool(self.a.consumer),
            manual_patch="no")
        self.install_value = value
        write(self.out / "install.json", value)
        if value["status"] != "ok":
            raise RuntimeError("支持的安装入口未完成或独占消费者不存在")

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
