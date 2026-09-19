"""Deterministic asset contract for issue #57: fixtures, builder, install gate.

Covers PC57-D1's asset minimum: the Stage-2 fixture (disposable Zotero HTTP/MCP
usage, real runner-built Stage-0/1 state, new-analysis preconditions), the
Stage-4 non-PC53 sentinel fixture, the frozen PC57-R1 request surface (no
UV/Chrome/NPM override, no prompt/model/reasoning/config drift), and the
extended install checkpoint surface.
"""
import importlib.util
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"
FIXTURE57_STAGE4_SCRIPT = RUNTIME_DIR / "prepare_issue57_stage4_fixture.py"
FIXTURE57_STAGE2_SCRIPT = RUNTIME_DIR / "prepare_issue57_stage2_fixture.py"
REQUEST57_SCRIPT = RUNTIME_DIR / "build_issue57_stage2_eval_request.py"
PROMPT57_TEMPLATE = RUNTIME_DIR / "prompts/issue57-stage2-routing.txt"
VERIFIER_SCRIPT = RUNTIME_DIR / "verify_issue32_e2e.py"
PRODUCER_ROOT = Path(__file__).resolve().parents[4]

DISPOSABLE_HTTP = "http://127.0.0.1:28119"
DISPOSABLE_MCP = "http://127.0.0.1:28120/mcp"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage4_fixture = load_module("issue57_stage4_fixture_for_tests", FIXTURE57_STAGE4_SCRIPT)
stage2_fixture = load_module("issue57_stage2_fixture_for_tests", FIXTURE57_STAGE2_SCRIPT)
request_builder = load_module("issue57_request_for_tests", REQUEST57_SCRIPT)
verifier = load_module("issue57_assets_verifier_for_tests", VERIFIER_SCRIPT)


def _fake_rpc(item_key: str):
    """Fake MCP transport: initialize handshake then one write_item create."""
    state = {"initialized": False}

    def http_post(url, payload_bytes, headers):
        payload = json.loads(payload_bytes.decode("utf-8"))
        method = payload.get("method")
        if method == "initialize":
            state["initialized"] = True
            return 200, {"mcp-session-id": "sess-57"}, json.dumps({
                "jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18"},
            })
        if method == "notifications/initialized":
            return 202, {}, ""
        if method == "tools/call" and state["initialized"]:
            name = payload.get("params", {}).get("name")
            if name != "write_item":
                return 200, {}, json.dumps({
                    "jsonrpc": "2.0", "id": payload.get("id"),
                    "error": {"code": -32601, "message": f"unknown tool {name}"},
                })
            return 200, {}, json.dumps({
                "jsonrpc": "2.0", "id": payload.get("id"),
                "result": {"content": [{"type": "text", "text": json.dumps({
                    "itemKey": item_key,
                })}]},
            })
        return 200, {}, json.dumps({
            "jsonrpc": "2.0", "id": payload.get("id", 0),
            "error": {"code": -32601, "message": f"unexpected {method}"},
        })

    return http_post


class Issue57Stage4FixtureTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)

    def test_fixture_uses_the_non_pc53_sentinel_and_stays_canonical(self):
        program = self.root / "program"
        profile = self.root / "profile"
        manifest = stage4_fixture.build_fixture(program, profile,
                                                output=self.root / "setup.json")
        self.assertEqual(manifest["professor"], "Issue57 Route Professor")
        self.assertEqual(manifest["direction_id"], "DIR57ROUTE")
        self.assertEqual(manifest["candidate_ids"],
                         ["issue57-route-a", "issue57-route-b"])
        self.assertNotEqual(manifest["professor"], "Example Professor")
        state = json.loads(
            (program / f"教授研究/X分野/{manifest['professor']}/套磁候选状态.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(state["schema"], 2)
        self.assertEqual(state["kind"], "professor-contact-stage3-state")
        candidate_ids = [row["id"] for row in state["directions"][0]["candidates"]]
        self.assertEqual(candidate_ids, ["issue57-route-a", "issue57-route-b"])
        self.assertFalse((program / "教授研究/套磁选择.json").exists())
        self.assertFalse((program / "教授研究/邮件输入.json").exists())
        self.assertEqual(manifest["manual_patch"], "no")

    def test_fixture_refuses_foreign_and_producer_owned_roots(self):
        foreign = self.root / "foreign"
        foreign.mkdir()
        (foreign / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(stage4_fixture.FixtureBuildError):
            stage4_fixture.build_fixture(foreign, self.root / "profile",
                                         output=self.root / "setup.json")
        with self.assertRaises(stage4_fixture.FixtureBuildError):
            stage4_fixture.build_fixture(
                stage4_fixture._producer_root() / ".issue57-fixture-forbidden",
                self.root / "profile", output=self.root / "setup.json")

    def test_fixture_cli_success_and_failure_paths(self):
        cli_program = self.root / "cli-program"
        result = subprocess.run(
            [sys.executable, "-B", str(FIXTURE57_STAGE4_SCRIPT),
             "--program-root", str(cli_program),
             "--profile-root", str(self.root / "cli-profile"),
             "--output", str(self.root / "cli-setup.json")],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ok")

        foreign = self.root / "foreign-cli"
        foreign.mkdir()
        (foreign / "keep.txt").write_text("keep", encoding="utf-8")
        failure = subprocess.run(
            [sys.executable, "-B", str(FIXTURE57_STAGE4_SCRIPT),
             "--program-root", str(foreign),
             "--profile-root", str(self.root / "cli-profile"),
             "--output", str(self.root / "cli-failure.json")],
            capture_output=True, text=True, check=False)
        self.assertNotEqual(failure.returncode, 0)
        self.assertEqual(json.loads(failure.stdout)["status"], "error")


class Issue57Stage2FixtureTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.consumer = self.root / "consumer"
        scripts = self.consumer / ".agents/skills/professor-contact/scripts"
        scripts.mkdir(parents=True)
        for runner in ("contact_targets.py", "contact_stage1.py"):
            (scripts / runner).write_bytes(
                (PRODUCER_ROOT / ".apm/skills/professor-contact/scripts" / runner)
                .read_bytes())

    def test_endpoint_validation_rejects_production_and_malformed_surfaces(self):
        with self.assertRaises(stage2_fixture.SetupError):
            stage2_fixture.validate_runtime_endpoints(
                "http://127.0.0.1:23119", DISPOSABLE_MCP)
        with self.assertRaises(stage2_fixture.SetupError):
            stage2_fixture.validate_runtime_endpoints(
                DISPOSABLE_HTTP, "http://127.0.0.1:28121")
        with self.assertRaises(stage2_fixture.SetupError):
            stage2_fixture.validate_runtime_endpoints(DISPOSABLE_HTTP, "")
        stage2_fixture.validate_runtime_endpoints(DISPOSABLE_HTTP, DISPOSABLE_MCP)

    def test_seed_uses_the_actually_returned_item_key(self):
        key = stage2_fixture.seed_zotero_paper(
            zotero_mcp_url=DISPOSABLE_MCP, http_post=_fake_rpc("Z57REAL01"))
        self.assertEqual(key, "Z57REAL01")
        with self.assertRaises(stage2_fixture.SetupError):
            stage2_fixture.seed_zotero_paper(
                zotero_mcp_url=DISPOSABLE_MCP, http_post=_fake_rpc("AAAA1111"))

    def test_build_fixture_materializes_runner_state_and_new_analysis_preconditions(self):
        program = self.root / "program"
        profile = self.root / "profile"
        evidence = stage2_fixture.prepare_stage2_fixture(
            program_root=program, profile_root=profile, consumer_root=self.consumer,
            zotero_http_url=DISPOSABLE_HTTP, zotero_mcp_url=DISPOSABLE_MCP,
            output=self.root / "setup.json", fixture_run_id="run-57",
            http_post=_fake_rpc("Z57REAL01"),
            http_get=lambda url: 200,
        )
        self.assertEqual(evidence["fixture_run_id"], "run-57")
        self.assertEqual(evidence["item_keys"], ["Z57REAL01"])
        self.assertEqual(evidence["attachment_keys"], [])
        self.assertEqual(evidence["manual_patch"], "no")
        self.assertEqual(evidence["program_root"], str(program.resolve()))
        self.assertEqual(evidence["profile_root"], str(profile.resolve()))
        self.assertIn("Z57REAL01", json.dumps(evidence["input_hashes"]))
        # Canonical Stage-0/Stage-1 state came from the producer runners.
        target = json.loads(
            (program / "教授研究/套磁目标.json").read_text(encoding="utf-8"))
        target_row = target["targets"][0]
        self.assertEqual(target_row["professor"], stage2_fixture.PROFESSOR)
        self.assertEqual(target_row["selected_direction_ids"],
                         [stage2_fixture.DIRECTION_ID])
        snapshot = json.loads(
            (program / "教授研究/套磁阶段1候选.json").read_text(encoding="utf-8"))
        direction = snapshot["professors"][0]["directions"][0]
        self.assertEqual(direction["candidate_keys"], ["Z57REAL01"])
        # A new Stage-2 delegated analysis is still required.
        professor_dir = program / f"教授研究/X分野/{stage2_fixture.PROFESSOR}"
        self.assertFalse((professor_dir / "套磁候选输入.json").exists())
        self.assertFalse((professor_dir / "论文分析/_resolved_directions.json").exists())
        self.assertFalse((professor_dir / "论文分析/_index.json").exists())
        self.assertFalse(list((professor_dir / "论文分析").glob("*.md")))
        self.assertTrue((professor_dir / "论文分析/Z57REAL01.pdf").is_file())
        self.assertTrue((self.root / "setup.json").is_file())

    def test_build_fixture_requires_run_id_and_installed_skill_dir(self):
        with self.assertRaises(stage2_fixture.SetupError):
            stage2_fixture.prepare_stage2_fixture(
                program_root=self.root / "p1", profile_root=self.root / "pr1",
                consumer_root=self.consumer, zotero_http_url=DISPOSABLE_HTTP,
                zotero_mcp_url=DISPOSABLE_MCP, output=self.root / "s1.json",
                fixture_run_id="", http_post=_fake_rpc("Z57REAL01"),
                http_get=lambda url: 200)
        with self.assertRaises(stage2_fixture.SetupError):
            stage2_fixture.prepare_stage2_fixture(
                program_root=self.root / "p2", profile_root=self.root / "pr2",
                consumer_root=self.root / "no-consumer",
                zotero_http_url=DISPOSABLE_HTTP, zotero_mcp_url=DISPOSABLE_MCP,
                output=self.root / "s2.json", fixture_run_id="run-57",
                http_post=_fake_rpc("Z57REAL01"), http_get=lambda url: 200)

    def test_build_fixture_refuses_dead_http_fixture_and_foreign_roots(self):
        def dead_probe(url):
            raise OSError("connection refused")

        with self.assertRaises(stage2_fixture.SetupError):
            stage2_fixture.prepare_stage2_fixture(
                program_root=self.root / "p3", profile_root=self.root / "pr3",
                consumer_root=self.consumer, zotero_http_url=DISPOSABLE_HTTP,
                zotero_mcp_url=DISPOSABLE_MCP, output=self.root / "s3.json",
                fixture_run_id="run-57", http_post=_fake_rpc("Z57REAL01"),
                http_get=dead_probe)

        foreign = self.root / "foreign"
        foreign.mkdir()
        (foreign / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(stage2_fixture.SetupError):
            stage2_fixture.prepare_stage2_fixture(
                program_root=foreign, profile_root=self.root / "pr4",
                consumer_root=self.consumer, zotero_http_url=DISPOSABLE_HTTP,
                zotero_mcp_url=DISPOSABLE_MCP, output=self.root / "s4.json",
                fixture_run_id="run-57", http_post=_fake_rpc("Z57REAL01"),
                http_get=lambda url: 200)


class Issue57RequestBuilderTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.consumer = self.root / "consumer"
        self.program = self.root / "program"
        self.consumer.mkdir()
        self.program.mkdir()

    def _build(self, *, model="gpt-5.6-luna", reasoning="low", timeout=900,
               prompt_template=None, http_url=DISPOSABLE_HTTP, mcp_url=DISPOSABLE_MCP):
        return request_builder.build_request(
            consumer_root=self.consumer, program_root=self.program,
            prompt_template=prompt_template or PROMPT57_TEMPLATE,
            rendered_prompt=self.root / "prompt.txt",
            zotero_http_url=http_url, zotero_mcp_url=mcp_url,
            output=self.root / "request.json",
            model=model, reasoning=reasoning, timeout=timeout)

    def test_request_surface_is_exactly_the_frozen_pc57_command(self):
        request = self._build()
        argv = shlex.split(request["command"])
        self.assertEqual(argv[:7], [
            "--json", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "workspace-write", "--cd", str(self.consumer.resolve()),
        ])
        self.assertEqual(argv[7:12], [
            "--model", "gpt-5.6-luna", "--config",
            'model_reasoning_effort="low"', "--config",
        ])
        self.assertIn(f'projects."{self.consumer.resolve()}".trust_level="trusted"', argv)
        self.assertIn("agents.max_concurrent_threads_per_session=16", argv)
        self.assertIn("sandbox_workspace_write.network_access=true", argv)
        self.assertIn(f'shell_environment_policy.set.ZOTERO_HTTP_URL="{DISPOSABLE_HTTP}"',
                      argv)
        self.assertIn(f'shell_environment_policy.set.ZOTERO_MCP_URL="{DISPOSABLE_MCP}"',
                      argv)
        self.assertEqual(argv[-2], "--")
        rendered = (self.root / "prompt.txt").read_text(encoding="utf-8")
        self.assertEqual(argv[-1], rendered)
        self.assertNotIn("<PROGRAM_ROOT>", rendered)
        self.assertEqual(
            rendered,
            PROMPT57_TEMPLATE.read_text(encoding="utf-8").replace(
                "<PROGRAM_ROOT>", str(self.program.resolve())))

    def test_no_uv_chrome_npm_or_home_override_is_introduced(self):
        request = self._build()
        for forbidden in ("UV_TOOL_DIR", "XDG_DATA_HOME", "npm", "NPM",
                          "chrome", "CHROME", "CDP", "HOME=", "uv_tool"):
            self.assertNotIn(forbidden, request["command"])
        self.assertIn("sandbox_workspace_write.network_access=true", request["command"])
        # The frozen prompt must not mention routing hints, tools, or issues.
        prompt = PROMPT57_TEMPLATE.read_text(encoding="utf-8")
        for forbidden in ("analyzer", "paper-analysis", "spawn", "delegate", "委派",
                          "adapter", "#47", "#55", "#57", "expected topology"):
            self.assertNotIn(forbidden, prompt)

    def test_builder_rejects_prompt_model_reasoning_timeout_and_endpoint_drift(self):
        with self.assertRaises(request_builder.RequestBuildError):
            self._build(model="gpt-5.5")
        with self.assertRaises(request_builder.RequestBuildError):
            self._build(reasoning="high")
        with self.assertRaises(request_builder.RequestBuildError):
            self._build(timeout=600)
        drifted = self.root / "drifted-prompt.txt"
        drifted.write_text(
            PROMPT57_TEMPLATE.read_text(encoding="utf-8") + "drift\n",
            encoding="utf-8")
        with self.assertRaises(request_builder.RequestBuildError):
            self._build(prompt_template=drifted)
        with self.assertRaises(request_builder.RequestBuildError):
            self._build(http_url="http://127.0.0.1:23119")
        with self.assertRaises(request_builder.RequestBuildError):
            self._build(mcp_url="http://127.0.0.1:28121")

    def test_builder_cli_success_and_failure_paths(self):
        rendered = self.root / "cli-prompt.txt"
        result = subprocess.run(
            [sys.executable, "-B", str(REQUEST57_SCRIPT),
             "--consumer-root", str(self.consumer),
             "--program-root", str(self.program),
             "--prompt-template", str(PROMPT57_TEMPLATE),
             "--rendered-prompt", str(rendered),
             "--zotero-http-url", DISPOSABLE_HTTP,
             "--zotero-mcp-url", DISPOSABLE_MCP,
             "--output", str(self.root / "cli-request.json")],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ok")

        failure = subprocess.run(
            [sys.executable, "-B", str(REQUEST57_SCRIPT),
             "--consumer-root", str(self.consumer),
             "--program-root", str(self.program),
             "--prompt-template", str(PROMPT57_TEMPLATE),
             "--rendered-prompt", str(rendered),
             "--zotero-http-url", DISPOSABLE_HTTP,
             "--zotero-mcp-url", DISPOSABLE_MCP,
             "--model", "gpt-5.5",
             "--output", str(self.root / "cli-request.json")],
            capture_output=True, text=True, check=False)
        self.assertNotEqual(failure.returncode, 0)
        self.assertEqual(json.loads(failure.stdout)["status"], "error")


class Issue57InstallSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)

    def args(self, **overrides):
        values = {
            "program_root": None,
            "consumer_root": None,
            "eval_response": None,
            "adapter_output": None,
            "producer_sha": "",
            "output": None,
            "min_edges": 1,
            "required_depth": 1,
            "pre_snapshot": None,
            "post_snapshot": None,
        }
        values.update(overrides)
        return Namespace(**values)

    def _consumer_with_all_files(self):
        consumer = self.root / "consumer"
        for relative in verifier.INSTALL_REQUIRED_FILES:
            path = consumer / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("installed", encoding="utf-8")
        return consumer

    def test_install_requires_every_issue57_runtime_asset(self):
        required = {
            ".agents/skills/professor-contact/tests/runtime/prepare_issue57_stage2_fixture.py",
            ".agents/skills/professor-contact/tests/runtime/build_issue57_stage2_eval_request.py",
            ".agents/skills/professor-contact/tests/runtime/prepare_issue57_stage4_fixture.py",
            ".agents/skills/professor-contact/tests/runtime/prompts/issue57-stage2-routing.txt",
        }
        self.assertTrue(required.issubset(set(verifier.INSTALL_REQUIRED_FILES)))
        consumer = self._consumer_with_all_files()
        payload = verifier._checkpoint_install(
            self.args(consumer_root=consumer, producer_sha=""))
        self.assertEqual(payload["status"], "pass", payload)

        missing = consumer / ".agents/skills/professor-contact/tests/runtime/prompts/issue57-stage2-routing.txt"
        missing.unlink()
        payload = verifier._checkpoint_install(
            self.args(consumer_root=consumer, producer_sha=""))
        self.assertEqual(payload["status"], "fail", payload)
        self.assertTrue(any(
            row["name"].endswith("issue57-stage2-routing.txt") and row["status"] == "fail"
            for row in payload["checks"]))

    def test_stage2_routing_checkpoint_is_registered(self):
        self.assertIn("stage2-routing", verifier.CHECKPOINTS)
        parser = verifier._parser()
        args = parser.parse_args([
            "stage2-routing", "--program-root", "/tmp/program",
            "--eval-response", "/tmp/response.json",
            "--adapter-output", "/tmp/adapter.json",
        ])
        self.assertEqual(args.checkpoint, "stage2-routing")


if __name__ == "__main__":
    unittest.main()
