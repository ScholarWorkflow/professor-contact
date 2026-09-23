import importlib.util
import json
import shlex
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
MODULE_PATH = TESTS_DIR / "runtime/build_issue32_eval_request.py"
R1_PROMPT = TESTS_DIR / "runtime/prompts/issue40-r1.txt"
R2_PROMPT = TESTS_DIR / "runtime/prompts/issue40-r2.txt"
spec = importlib.util.spec_from_file_location("issue32_eval_request", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FIXTURE_HTTP = "http://127.0.0.1:24121"
FIXTURE_MCP = "http://127.0.0.1:24122/mcp"
ENDPOINT_KEYS = ("shell_environment_policy.set.ZOTERO_HTTP_URL",
                 "shell_environment_policy.set.ZOTERO_MCP_URL")
NETWORK_KEY = "sandbox_workspace_write.network_access"
RECIPE_CEILING = 7
CEILING_KEY = "agents.max_concurrent_threads_per_session"
CEILING_MISSING = "max_agent_threads has no default"


def _flatten(value: dict, prefix: str = "") -> dict:
    flat: dict[str, object] = {}
    for key, item in value.items():
        path = f"{prefix}{key}"
        if isinstance(item, dict):
            flat.update(_flatten(item, path + "."))
        else:
            flat[path] = item
    return flat


class Issue32EvalRequestTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name) / "consumer"
        self.root.mkdir()
        self.prompt = Path(self.holder.name) / "prompt.md"
        self.prompt.write_text("Run the canonical case", encoding="utf-8")

    def build(self, case, **overrides):
        values = {
            "case": case,
            "consumer_root": self.root,
            "prompt_file": self.prompt,
            "output": Path(self.holder.name) / f"{case}-request.json",
            "zotero_http_url": FIXTURE_HTTP,
            "zotero_mcp_url": FIXTURE_MCP,
            # Every case passes its own ceiling; this is only a stand-in for the
            # value the owning recipe freezes, and the sibling test below checks
            # that omitting it fails closed.
            "max_agent_threads": RECIPE_CEILING,
        }
        values.update(overrides)
        return module.build_request(**values)

    def configs(self, request):
        """Return every config override flattened to dotted keys, parsed as TOML."""
        argv = shlex.split(request["command"])
        assignments = [argv[index + 1] for index, value in enumerate(argv[:-1])
                       if value == "--config"]
        flat: dict[str, object] = {}
        for assignment in assignments:
            flat.update(_flatten(tomllib.loads(f"{assignment}\n")))
        return assignments, flat

    def test_case_is_always_required(self):
        with self.assertRaises(module.RequestBuildError):
            self.build("")
        with self.assertRaises(module.RequestBuildError):
            self.build("R1")
        with self.assertRaises(module.RequestBuildError):
            self.build("stage5")
        self.assertEqual(module.CANONICAL_CASES,
                         ("r1", "r2", "r3a", "r3b", "r4a", "r4b"))

    def test_r1_and_r2_inject_exact_fixture_endpoints_and_network(self):
        for case in ("r1", "r2"):
            with self.subTest(case=case):
                _, configs = self.configs(self.build(case))
                self.assertEqual(configs.get(ENDPOINT_KEYS[0]), FIXTURE_HTTP)
                self.assertEqual(configs.get(ENDPOINT_KEYS[1]), FIXTURE_MCP)
                self.assertIs(type(configs.get(ENDPOINT_KEYS[0])), str)
                self.assertIs(type(configs.get(ENDPOINT_KEYS[1])), str)
                self.assertIs(configs.get(NETWORK_KEY), True)

    def test_r1_and_r2_fail_closed_without_fixture_endpoints(self):
        for case in ("r1", "r2"):
            for overrides in (
                {"zotero_http_url": ""},
                {"zotero_mcp_url": ""},
                {"zotero_http_url": "   ", "zotero_mcp_url": ""},
            ):
                with self.subTest(case=case, overrides=overrides):
                    with self.assertRaises(module.RequestBuildError) as ctx:
                        self.build(case, **overrides)
                    self.assertIn("requires fixture Zotero endpoints", str(ctx.exception))

    def test_isolated_cases_inject_no_zotero_endpoint_or_network_override(self):
        for case in ("r3a", "r3b", "r4a", "r4b"):
            with self.subTest(case=case):
                _, configs = self.configs(self.build(
                    case, zotero_http_url="", zotero_mcp_url=""))
                for key in (*ENDPOINT_KEYS, NETWORK_KEY):
                    self.assertNotIn(key, configs)
                self.assertNotIn("ZOTERO", " ".join(configs))

    def test_isolated_cases_reject_supplied_zotero_endpoints(self):
        for case in ("r3a", "r3b", "r4a", "r4b"):
            with self.subTest(case=case):
                with self.assertRaises(module.RequestBuildError) as ctx:
                    self.build(case)
                self.assertIn("does not use Zotero", str(ctx.exception))
                with self.assertRaises(module.RequestBuildError):
                    self.build(case, zotero_http_url="", zotero_mcp_url=FIXTURE_MCP)
                with self.assertRaises(module.RequestBuildError):
                    self.build(case, zotero_http_url=FIXTURE_HTTP, zotero_mcp_url="")

    def test_no_canonical_case_emits_an_empty_string_override(self):
        for case in module.CANONICAL_CASES:
            isolated = case in module.ISOLATED_CASES
            with self.subTest(case=case):
                _, configs = self.configs(self.build(
                    case,
                    **({"zotero_http_url": "", "zotero_mcp_url": ""} if isolated else {})))
                blank = [key for key, value in configs.items()
                         if isinstance(value, str) and not value.strip()]
                self.assertEqual(blank, [])

    def test_every_canonical_case_keeps_model_and_trust_overrides(self):
        for case in module.CANONICAL_CASES:
            isolated = case in module.ISOLATED_CASES
            with self.subTest(case=case):
                _, configs = self.configs(self.build(
                    case,
                    **({"zotero_http_url": "", "zotero_mcp_url": ""} if isolated else {})))
                self.assertEqual(configs.get("model_reasoning_effort"), "low")
                self.assertEqual(configs.get(
                    f"projects.{self.root.resolve()}.trust_level"), "trusted")
                argv = shlex.split(self.build(
                    case,
                    **({"zotero_http_url": "", "zotero_mcp_url": ""} if isolated else {})
                )["command"])
                self.assertEqual(argv[:2], ["--json", "--ephemeral"])
                self.assertNotIn("codex", argv[:2])
                self.assertNotIn("exec", argv[:2])
                self.assertEqual(argv[argv.index("--sandbox") + 1], "workspace-write")
                self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.6-luna")

    def test_case_without_a_recipe_ceiling_fails_closed(self):
        # The ceiling is a per-case resource setting owned by the recipe that
        # runs the case, so the builder must not fall back to any default.
        for case in module.CANONICAL_CASES + (module.BROWSER_CASE,):
            with self.subTest(case=case):
                with self.assertRaises(module.RequestBuildError) as ctx:
                    self.build(case, max_agent_threads=None)
                self.assertIn(CEILING_MISSING, str(ctx.exception))

    def test_chrome_npm_wiring_absent_from_every_canonical_case(self):
        for case in module.CANONICAL_CASES:
            isolated = case in module.ISOLATED_CASES
            with self.subTest(case=case):
                _, configs = self.configs(self.build(
                    case,
                    **({"zotero_http_url": "", "zotero_mcp_url": ""} if isolated else {})))
                rendered = " ".join(configs)
                for forbidden in ("NPM_CONFIG_CACHE", "CHROME_PROFILE_DIR", "CHROME_CDP_PORT",
                                  "mcp_servers", "chrome", "cdp"):
                    self.assertNotIn(forbidden, rendered)

    def test_canonical_cases_reject_browser_arguments_instead_of_opting_in(self):
        for case in module.CANONICAL_CASES:
            isolated = case in module.ISOLATED_CASES
            for overrides in (
                {"chrome_profile_dir": "/tmp/chrome"},
                {"chrome_cdp_port": "9333"},
                {"npm_cache": "/tmp/npm"},
            ):
                with self.subTest(case=case, overrides=overrides):
                    with self.assertRaises(module.RequestBuildError) as ctx:
                        self.build(case,
                                   **({"zotero_http_url": "", "zotero_mcp_url": ""}
                                      if isolated else {}), **overrides)
                    self.assertIn("Chrome/NPM", str(ctx.exception))

    def test_browser_case_is_the_only_explicit_chrome_mode(self):
        (self.root / ".codex").mkdir(parents=True)
        (self.root / ".codex/config.toml").write_text(
            '[mcp_servers."actual-browser-server"]\n'
            'command = "npx"\n'
            '[mcp_servers."actual-browser-server".env]\n'
            'CHROME_PROFILE_DIR = "/tmp/profile"\n'
            'CHROME_CDP_PORT = "9222"\n', encoding="utf-8")
        _, configs = self.configs(self.build(
            module.BROWSER_CASE,
            chrome_profile_dir='/tmp/chrome "profile"',
            chrome_cdp_port="9333",
            npm_cache='/tmp/npm "cache"',
        ))
        self.assertEqual(configs.get("shell_environment_policy.set.NPM_CONFIG_CACHE"),
                         '/tmp/npm "cache"')
        self.assertEqual(
            configs.get("mcp_servers.actual-browser-server.env.CHROME_PROFILE_DIR"),
            '/tmp/chrome "profile"')
        self.assertIs(type(
            configs.get("mcp_servers.actual-browser-server.env.CHROME_CDP_PORT")), str)
        self.assertEqual(configs.get("mcp_servers.actual-browser-server.env.CHROME_CDP_PORT"),
                         "9333")
        self.assertEqual(configs.get(ENDPOINT_KEYS[0]), FIXTURE_HTTP)
        self.assertIs(configs.get(NETWORK_KEY), True)

    def test_browser_case_requires_every_browser_value(self):
        for overrides in (
            {"chrome_profile_dir": ""},
            {"chrome_cdp_port": ""},
            {"npm_cache": ""},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(module.RequestBuildError) as ctx:
                    self.build(module.BROWSER_CASE, **overrides)
                self.assertIn("browser-specific mode", str(ctx.exception))

    def test_explicit_agent_thread_override_is_recorded_as_integer_config(self):
        _, configs = self.configs(self.build("r1", max_agent_threads=20))
        self.assertEqual(configs.get(CEILING_KEY), 20)

    def test_nonpositive_agent_thread_override_is_rejected(self):
        with self.assertRaises(module.RequestBuildError):
            self.build("r1", max_agent_threads=0)

    def test_missing_consumer_root_is_rejected(self):
        with self.assertRaises(module.RequestBuildError):
            self.build("r1", consumer_root=self.root.parent / "absent")

    def test_ambiguous_chrome_configuration_is_blocked(self):
        (self.root / "a.toml").write_text(
            '[mcp_servers."chrome-a"]\ncommand = "a"\n', encoding="utf-8")
        (self.root / "b.toml").write_text(
            '[mcp_servers."chrome-b"]\ncommand = "b"\n', encoding="utf-8")
        with self.assertRaises(module.RequestBuildError):
            module.discover_chrome_server_id(self.root)

    def test_selects_page_scoped_server_from_generated_chrome_set(self):
        (self.root / "config.toml").write_text(
            '[mcp_servers."chrome-devtools"]\n'
            'args = ["--scan"]\n'
            '[mcp_servers."pdf-chrome"]\n'
            'args = ["--page-id"]\n'
            '[mcp_servers."sd-chrome"]\n'
            'args = ["--output-mode=compact"]\n', encoding="utf-8")
        self.assertEqual(module.discover_chrome_server_id(self.root), "pdf-chrome")

    def test_cli_requires_case_and_rejects_unknown_values(self):
        output = Path(self.holder.name) / "cli-request.json"
        missing = subprocess.run(
            ["python3", str(MODULE_PATH), "--consumer-root", str(self.root),
             "--prompt-file", str(self.prompt), "--output", str(output)],
            capture_output=True, text=True, check=False)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--case", missing.stderr)
        unknown = subprocess.run(
            ["python3", str(MODULE_PATH), "--case", "r7",
             "--consumer-root", str(self.root), "--prompt-file", str(self.prompt),
             "--output", str(output)],
            capture_output=True, text=True, check=False)
        self.assertEqual(unknown.returncode, 2)
        self.assertFalse(output.exists())

    def test_cli_writes_isolated_case_without_endpoint_keys(self):
        output = Path(self.holder.name) / "r4b-request.json"
        completed = subprocess.run(
            ["python3", str(MODULE_PATH), "--case", "r4b",
             "--max-agent-threads", str(RECIPE_CEILING),
             "--consumer-root", str(self.root), "--prompt-file", str(self.prompt),
             "--output", str(output)],
            capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["case"], "r4b")
        _, configs = self.configs(json.loads(output.read_text(encoding="utf-8")))
        for key in (*ENDPOINT_KEYS, NETWORK_KEY):
            self.assertNotIn(key, configs)
        self.assertEqual(configs.get(CEILING_KEY), RECIPE_CEILING)

    def test_r1_prompt_forces_single_root_dispatch_to_downloader(self):
        """R1 measures nested delegation, not ambiguous caller-convention routing."""
        text = R1_PROMPT.read_text(encoding="utf-8")
        self.assertIn("仅一次直接委派", text)
        self.assertIn("`professor-contact-downloader`", text)
        self.assertIn("不要再次委派 `professor-contact-downloader`", text)
        self.assertIn("folder_path: ${PROGRAM_ROOT}", text)
        self.assertIn("access_mode: oa_only", text)
        self.assertIn("不要内联执行 Stage 1", text)
        self.assertIn("child 按其已安装正式 contract 继续下游委派", text)
        self.assertNotIn("按已安装 professor-contact 的正式 Codex 工作流执行 Stage 1", text)

    def test_r2_prompt_forces_single_root_dispatch_to_analyzer(self):
        """R2 must enter the analyzer before measuring deeper nested delegation."""
        text = R2_PROMPT.read_text(encoding="utf-8")
        self.assertIn("仅一次直接委派", text)
        self.assertIn("`professor-contact-analyzer`", text)
        self.assertIn("不要再次委派 `professor-contact-analyzer`", text)
        self.assertIn("folder_path: ${PROGRAM_ROOT}", text)
        self.assertIn("paper_analysis: all", text)
        self.assertIn("不要在 root 内联执行 Stage 2", text)
        for forbidden_root_call in (
            "`contact_targets.py`",
            "`contact_stage1.py`",
            "`contact_state.py`",
            "`paper-analysis`",
        ):
            self.assertIn(forbidden_root_call, text)
        self.assertIn("child 按其已安装正式 contract 继续下游委派", text)
        self.assertNotIn("继续 ${PROGRAM_ROOT} 的正式 professor-contact 工作流，只执行 Stage 2", text)


if __name__ == "__main__":
    unittest.main()
