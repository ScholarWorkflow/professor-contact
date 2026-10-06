#!/usr/bin/env python3
"""Issue 66 的待审安装、取证及执行接线；预检永不发送评测请求。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

TARGET = "dfe430560b6e4d9d85c30b71b8c84bc621da7549"
FIXTURE = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
ADAPTER = "skills-test-fixtures/codex-eval-adapter@16"
PLAN = "issue-66-test-plan-r19-clarification-r4-2026-10-05"
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
    argv = ["--json", "--skip-git-repo-check", "--sandbox", "workspace-write",
            "--cd", str(consumer), "--model", "gpt-6-luna", "--config",
            'model_reasoning_effort="low"', "--config", trust,
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
        self.request_sent = False

    def run(self, name, argv, *, cwd=None, required=True, private=False):
        self.counter += 1
        print(f"[{time.strftime('%H:%M:%S')}] {self.counter} {name}", flush=True)
        result = subprocess.run(argv, cwd=cwd or self.repo, capture_output=True,
                                timeout=1200, check=False)
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
        return self.run(name, ["uv", "run", "--no-project", "--python", "3.14.6",
                              "python", "-B", str(path), *map(str, argv)], required=required)

    def versions(self):
        versions = {}
        for name, argv in (("uv", ["uv", "--version"]), ("apm", ["apm", "--version"]),
                           ("jq", ["jq", "--version"]), ("yq", ["yq", "--version"]),
                           ("direnv", ["direnv", "version"])):
            versions[name] = self.run(f"version-{name}", argv).stdout.decode().strip()
        versions["python"] = self.py("version-python", "-V").stdout.decode().strip()
        write(self.out / "versions.json", versions)

    def verify_versions(self):
        head = self.run("test-commit", ["git", "rev-parse", "HEAD"]).stdout.decode().strip()
        dirty = self.run("test-dirty", ["git", "status", "--porcelain", "--untracked-files=all"])
        fhead = self.run("fixture-commit", ["git", "rev-parse", "HEAD"], cwd=self.fixture)
        fdirty = self.run("fixture-dirty", ["git", "status", "--porcelain"], cwd=self.fixture)
        if fhead.stdout.decode().strip() != FIXTURE or fdirty.stdout.strip():
            raise RuntimeError("共享环境提交不符或存在修改")
        if self.a.mode == "formal" and dirty.stdout.strip():
            raise RuntimeError("正式执行必须使用无修改的冻结测试提交")
        self.head = head
        write(self.out / "provenance.json", {"plan": PLAN, "product_commit": TARGET,
              "test_commit": head, "fixture_commit": FIXTURE, "adapter": ADAPTER,
              "repository": str(self.repo), "invocation_directory": str(Path.cwd()),
              "evidence_set_id": self.identity, "manual_patch": "no"})

    def unlock(self):
        """只在正式模式检查批准；预检从不依赖批准。"""
        if not self.a.frozen_manifest:
            raise RuntimeError("正式执行缺少冻结材料")
        frozen = jq(self.a.frozen_manifest)
        if frozen.get("test_commit") != self.head or frozen.get("product_commit") != TARGET \
                or frozen.get("fixture_commit") != FIXTURE or frozen.get("plan") != PLAN:
            raise RuntimeError("冻结版本与实际版本不符")
        pinned = frozen.get("files", {})
        required = [str(Path(__file__).relative_to(self.repo)),
                    "test-plan/issue-66-formal.sh", "test-plan/issue-66-execution.md",
                    str((HERE / "judge_issue66_stage3_runtime.py").relative_to(self.repo))]
        if any(name not in pinned for name in required):
            raise RuntimeError("冻结材料未覆盖全部执行及判定文件")
        if not self.a.service_contract or frozen.get("service_contract_sha256") != \
                digest(Path(self.a.service_contract).read_bytes()):
            raise RuntimeError("共享服务隔离来源未由同一冻结材料固定")
        for relative, expected in pinned.items():
            path = (self.repo / relative).resolve()
            if not path.is_relative_to(self.repo) or digest(path.read_bytes()) != expected:
                raise RuntimeError(f"冻结文件摘要不符：{relative}")
        comment_id = frozen.get("gate2_comment_id")
        if not isinstance(comment_id, int) or comment_id <= 0:
            raise RuntimeError("冻结材料未给出真实批准评论编号")
        approval = self.out / "gate2-approval.json"
        result = self.run("gate2-remote-comment", ["gh", "api",
            f"repos/ScholarWorkflow/professor-contact/issues/comments/{comment_id}"])
        approval.write_bytes(result.stdout)
        record = jq(approval)
        body = record.get("body", "")
        if record.get("user", {}).get("login") != frozen.get("gate2_reviewer") \
                or "Test Engineer Gate 2: PASS" not in body or self.head not in body \
                or PLAN not in body:
            raise RuntimeError("远端评论未明确批准本计划及当前完整测试提交")

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
        # 外部故障不重试；在任何网络调用之前占用本次唯一执行编号。
        write(self.out / "attempt.json", {"evidence_set_id": self.identity,
              "start_time_unix": time.time(), "request_sha256": digest(
                  (self.out / "request.json").read_bytes()), "maximum_attempts": 1})
        self.request_sent = True
        result = self.run("eval-once", ["curl", "--silent", "--show-error",
            "--max-time", "930", "--request", "POST", f"http://127.0.0.1:{port}/eval",
            "--header", "Content-Type: application/json", "--data-binary",
            f"@{self.out / 'request.json'}", "--output", str(self.out / "response-raw.json"),
            "--write-out", "%{http_code}"], required=False)
        write(self.out / "transport.json", {"exit_code": result.returncode,
              "http_status": result.stdout.decode().strip()})
        if result.returncode or result.stdout.decode().strip() != "200":
            raise RuntimeError("本次唯一评测请求的传输未成功；禁止自动重试")
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
        try:
            self.service(port, response, adapter)
        except (RuntimeError, OSError, KeyError, ValueError, sqlite3.Error) as exc:
            if not (self.out / "storage.json").exists():
                write(self.out / "storage.json", {"evidence_set_id": self.identity,
                      "status": "error", "checks": [], "gap": str(exc),
                      "actual_observation_failed": True})
        candidate = self.program / PROFESSOR / "套磁候选状态.json"
        self.py("unique-judge", HERE / "judge_issue66_stage3_runtime.py",
            "--eval-response", self.out / "response.json",
            "--adapter-output", self.out / "adapter.json",
            "--candidate-state", candidate, "--program-root", self.program,
            "--install-evidence", self.out / "install.json",
            "--fixture-evidence", self.out / "fixture.json",
            "--routing-evidence", self.out / "routing.json",
            "--pre-snapshot", self.out / "pre.json", "--post-snapshot", self.out / "post.json",
            "--storage-evidence", self.out / "storage.json", "--output", self.out / "verdict.json",
            required=False)
        verdict = jq(self.out / "verdict.json")
        return 0 if verdict["classification"] == "PASS" else 1

    def execute(self):
        self.run("invocation-directory", ["pwd"])
        self.versions()
        self.verify_versions()
        if self.a.mode == "installation-check":
            self.install()
            self.prepare()
            write(self.out / "preflight.json", {"classification": "PREFLIGHT_ONLY",
                  "formal_request_sent": False, "evidence_set_id": self.identity,
                  "prepared": ["installation", "initial_input", "request", "snapshot"],
                  "remaining": ["实际服务配置与存储归属", "真实业务生产/权限证据"]})
            return 0
        if self.a.mode == "formal":
            self.unlock()
        port = self.port()
        self.service(port)
        self.install()
        self.prepare()
        if self.a.mode == "preflight":
            write(self.out / "preflight.json", {"classification": "PREFLIGHT_ONLY",
                  "formal_request_sent": False, "evidence_set_id": self.identity,
                  "prepared": ["installation", "initial_input", "request", "snapshot", "storage"],
                  "remaining": ["本轮业务文件生产及权限按正式运行实际事件判读", "正式运行存储线程归属"]})
            return 0
        return self.formal(port)


    def install(self):
        if not self.a.consumer:
            self.consumer.mkdir()
            self.run("install", ["apm", "install", "--target", "codex",
                f"ScholarWorkflow/professor-contact#{TARGET}"], cwd=self.consumer)
        lock = self.consumer / "apm.lock.yaml"
        result = self.run("parse-lock", ["yq", "-o=json", ".", str(lock)])
        parsed = self.out / "lock.json"
        parsed.write_bytes(result.stdout)
        commits = jq(parsed, '[.dependencies[] | select(.name=="professor-contact") | .resolved_commit]')
        projection = []
        skill = self.consumer / ".agents/skills/professor-contact"
        for relative in ("SKILL.md", "scripts/contact_state.py"):
            original = self.run(f"source-{Path(relative).stem}", ["git", "show",
                f"{TARGET}:.apm/skills/professor-contact/{relative}"]).stdout
            installed = skill / relative
            projection.append(check(f"projection:{relative}", installed.is_file()
                and not installed.is_symlink() and installed.read_bytes() == original,
                {"installed": str(installed), "source_sha256": digest(original)}))
        for agent in ("professor-contact", "professor-contact-idea-generator",
                      "professor-contact-style-validator"):
            original = self.run(f"source-{agent}", ["git", "show",
                f"{TARGET}:.apm/agents/{agent}.agent.md"]).stdout.decode()
            if original.startswith("---\n"):
                original = original.split("---", 2)[2].strip()
            installed = self.consumer / f".codex/agents/{agent}.toml"
            projected = self.run(f"parse-agent-{agent}", ["yq", "-p=toml", "-o=json", ".", str(installed)])
            parsed = self.out / f"{agent}.json"
            parsed.write_bytes(projected.stdout)
            body = jq(parsed, '.developer_instructions')
            projection.append(check(f"projection:{agent}", isinstance(body, str)
                and body.strip() == original.strip(), str(installed)))
        value = surface(self.identity, [
            check("locked_target_commit", commits == [TARGET], commits),
            check("source_install_projection", all(row["status"] == "pass"
                  for row in projection), projection)], target_commit=TARGET,
            installed_commit=commits[0] if len(commits) == 1 else None,
            consumer_root=str(self.consumer), newly_created=not bool(self.a.consumer), manual_patch="no")
        self.install_value = value
        if value["status"] != "ok":
            write(self.out / "install.json", value)
            raise RuntimeError("正式安装版本或源与安装投影不符")

    def prepare(self):
        # 安装投影中的辅助会把消费者判作生产仓库；从冻结生产测试资产
        # 构造纯初态，仍只写消费者内的程序目录，不修补安装产物。
        builder_checks = []
        for name in ("prepare_issue55_stage3_fixture.py", "fixture_support.py"):
            asset = HERE / name
            relative = str(asset.relative_to(self.repo))
            original = self.run(f"initial-source-{asset.stem}",
                ["git", "show", f"{TARGET}:{relative}"]).stdout
            builder_checks.append(check(name, asset.is_file() and not asset.is_symlink()
                and asset.read_bytes() == original,
                {"source_commit": TARGET, "source_path": relative,
                 "source_sha256": digest(original)}))
        verified = surface(self.identity, builder_checks, source_commit=TARGET)
        write(self.out / "initial-builder.json", verified)
        if verified["status"] != "ok":
            raise RuntimeError("初态构造程序或直接辅助与固定目标提交不符")
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
            manual_patch="no", fixture_commit=FIXTURE, input_hashes=hashes)
        write(self.out / "fixture-pre.json", fixture_value)
        if fixture_value["status"] != "ok":
            raise RuntimeError("初始输入或禁止产物不满足正式前提")
        req = request(self.consumer, self.program)
        write(self.out / "request.json", req)
        (self.out / "prompt.txt").write_text(shlex.split(req["command"])[-1], encoding="utf-8")
        config_check = check("request_config_matches_consensus",
            shlex.split(req["command"])[3] == "workspace-write"
            and shlex.split(req["command"])[7] == "gpt-6-luna",
            {"request_sha256": digest((self.out / "request.json").read_bytes()),
             "source": "PROJECT_CONSENSUS.md / Smoke Tests / 运行配置的唯一来源"})
        self.install_value["checks"].append(config_check)
        if config_check["status"] != "pass":
            self.install_value["status"] = "error"
        write(self.out / "install.json", self.install_value)
        write(self.out / "pre.json", surface(self.identity, [
            check("pre_zero_write_snapshot", all(not row["exists"] for row in before.values()), before)],
            artifacts=before))
        self.initial = initial
        self.before = before

    def service(self, port, response=None, adapter=None):
        """仅查询现有进程及只读存储，不配置或管理服务生命周期。"""
        if not self.a.service_contract:
            raise RuntimeError("缺少共享环境已指定的服务专用存储根及来源文件")
        contract = jq(self.a.service_contract)
        root = Path(contract["service_isolation_root"]).resolve()
        if not root.is_absolute() or root == Path("/") or not contract.get("authority"):
            raise RuntimeError("共享环境服务隔离来源无效")
        listener = self.run("service-listener", ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"])
        ids = set(listener.stdout.decode().split())
        if len(ids) != 1:
            raise RuntimeError("评测端口不能唯一归属既有进程")
        service_pid = next(iter(ids))
        process = self.run("process-tree", ["ps", "-axo", "pid=,ppid=,command="], private=True)
        rows = [line.strip().split(None, 2) for line in process.stdout.decode().splitlines()]
        descendants = {service_pid}
        for _ in range(len(rows)):
            old = len(descendants)
            descendants.update(row[0] for row in rows if len(row) == 3 and row[1] in descendants)
            if len(descendants) == old:
                break
        candidates = [row[0] for row in rows if len(row) == 3 and row[0] in descendants
                      and "app-server" in shlex.split(row[2])]
        if len(candidates) != 1:
            raise RuntimeError("既有服务未唯一关联实际应用服务进程")
        pid = candidates[0]
        actual_argv = next(shlex.split(row[2]) for row in rows if row[0] == pid)
        if any(token in {"-c", "--config"} or token.startswith("--config=")
               for token in actual_argv):
            raise RuntimeError("实际进程带配置覆盖，当前采集未核清覆盖后的存储目录，停止且保留缺口")
        env_result = self.run("actual-process-environment", ["ps", "eww", "-p", pid,
                              "-o", "command="], private=True)
        # 进程环境不是结构文档，只保留负责隔离证明的变量；不落凭据。
        observed = {}
        for token in shlex.split(env_result.stdout.decode()):
            if "=" in token:
                key, value = token.split("=", 1)
                if key in {"CODEX_HOME", "CODEX_SQLITE_HOME", "XDG_STATE_HOME",
                           "XDG_DATA_HOME", "XDG_CACHE_HOME"}:
                    observed[key] = value
        write(self.out / ("process-env-post.json" if response else "process-env-pre.json"), observed)
        if not observed.get("CODEX_HOME"):
            raise RuntimeError("实际应用服务未提供测试专用 CODEX_HOME；不回退用户目录")
        home = Path(observed["CODEX_HOME"]).resolve()
        config = home / "config.toml"
        config_result = self.run("actual-config", ["yq", "-p=toml", "-o=json", ".", str(config)], private=True)
        # 仅落必要目录覆盖；配置其余内容可能有凭据。
        values = json.loads(config_result.stdout)
        config_db = values.get("sqlite_home")
        sqlhome = Path(config_db or observed.get("CODEX_SQLITE_HOME") or str(home)).resolve()
        files = self.run("actual-open-storage", ["lsof", "-p", pid, "-Fn"])
        paths = [Path(line[1:]).resolve() for line in files.stdout.decode().splitlines()
                 if line.startswith("n/")]
        databases = sorted(set(path for path in paths if path.suffix in {".sqlite", ".db"}))
        logs = sorted(set(path for path in paths if path.suffix == ".log"))
        if len(databases) != 1 or not logs:
            raise RuntimeError("实际打开的数据库或日志路径不能按已知接口唯一核实")
        database = databases[0]
        rollout = home / "sessions"
        actual_ids = []
        records = []
        if response is not None:
            runtime_root = response.get("output", {}).get("thread_id")
            wanted = {runtime_root, *adapter.get("delegation", {}).get("child_thread_ids", [])}
            if None in wanted or not runtime_root:
                raise RuntimeError("运行根线程证据缺失")
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
                connection.execute("PRAGMA query_only=ON")
                columns = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
                if not {"id", "rollout_path"} <= columns:
                    raise RuntimeError("实际数据库缺少受支持线程归属字段")
                for thread in sorted(wanted):
                    found = connection.execute("SELECT id,rollout_path FROM threads WHERE id=?", (thread,)).fetchall()
                    records.extend({"id": row[0], "rollout_path": row[1]} for row in found)
                    if len(found) == 1 and Path(found[0][1]).resolve().is_relative_to(root):
                        actual_ids.append(thread)
            matched = set(actual_ids) == wanted
        else:
            runtime_root, matched = None, False
        contained = lambda path: path.is_relative_to(root)
        checks = [check("process_is_test_only", contained(home), observed),
                  check("config_is_test_only", contained(config), str(config)),
                  check("database_is_test_only", contained(database), str(database)),
                  check("logs_are_test_only", all(contained(path) for path in logs), list(map(str, logs))),
                  check("database_path_resolved", database.parent == sqlhome,
                        {"config_sqlite_home": config_db, "inherited_CODEX_SQLITE_HOME": observed.get("CODEX_SQLITE_HOME"),
                         "actual_database": str(database), "resolved_directory": str(sqlhome)}),
                  check("run_records_match_case", matched, records),
                  check("read_only", True, "sqlite mode=ro，query_only=ON；仅查询进程和打开文件")]
        value = surface(self.identity, checks, process_id=int(pid), service_process_id=int(service_pid),
                        config_path=str(config), database_path=str(database), log_path=str(logs[0]),
                        rollout_dir=str(rollout), root_thread_id=runtime_root, thread_ids=actual_ids,
                        service_contract_sha256=digest(Path(self.a.service_contract).read_bytes()))
        write(self.out / ("storage.json" if response else "storage-preflight.json"), value)
        prerequisites = [row for row in checks if row["name"] != "run_records_match_case"]
        if any(row["status"] != "pass" for row in prerequisites):
            raise RuntimeError("实际服务或存储隔离前提未核实")
        return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "formal", "installation-check"))
    parser.add_argument("--repository", required=True)
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--service-contract")
    parser.add_argument("--frozen-manifest")
    parser.add_argument("--consumer")
    args = parser.parse_args(argv)
    execution = None
    try:
        execution = Execution(args)
        return execution.execute()
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        if execution and not (execution.out / "verdict.json").exists():
            write(execution.out / "verdict.json", {
                "classification": "INVALID_TEST_EXECUTION" if execution.request_sent else "CASE_NOT_STARTED",
                "reason": str(exc), "formal_request_sent": execution.request_sent,
                "evidence_set_id": execution.identity,
                "facts": [{"fact": "F-execution-wiring", "verdict": "gap", "evidence": str(exc)}]})
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
