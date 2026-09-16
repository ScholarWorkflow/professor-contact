import importlib.util
import json
import shlex
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


class Issue32EvalRequestTests(unittest.TestCase):
    def test_default_request_omits_chrome_and_npm_wiring(self):
        """#40 R1-R4 must not require or inject browser-specific runtime state."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            root.mkdir()
            prompt = Path(directory) / "prompt.md"
            prompt.write_text("Run Stage 1", encoding="utf-8")
            output = Path(directory) / "request.json"
            request = module.build_request(
                consumer_root=root,
                prompt_file=prompt,
                output=output,
                zotero_http_url="http://127.0.0.1:9000",
                zotero_mcp_url="http://127.0.0.1:9001",
                # Passing browser values without the explicit opt-in must not
                # make the canonical R1-R4 matrix discover or inject Chrome.
                chrome_profile_dir='/tmp/chrome "profile"',
                chrome_cdp_port="9333",
                npm_cache='/tmp/npm "cache"',
            )
            self.assertEqual(request["timeout"], 1800)
            command = request["command"]
            argv = shlex.split(command)
            self.assertEqual(argv[:2], ["--json", "--ephemeral"])
            self.assertNotIn("codex", argv[:2])
            self.assertNotIn("exec", argv[:2])
            assignments = [argv[index + 1] for index, value in enumerate(argv[:-1])
                           if value == "--config"]
            self.assertEqual(len(assignments), 5)
            parsed = [tomllib.loads(f"{assignment}\n") for assignment in assignments]
            self.assertEqual(parsed[0]["model_reasoning_effort"], "low")
            project_trust = parsed[1]["projects"][str(root.resolve())]
            self.assertEqual(project_trust["trust_level"], "trusted")
            self.assertEqual(parsed[2]["shell_environment_policy"]["set"]["ZOTERO_HTTP_URL"],
                             "http://127.0.0.1:9000")
            self.assertIs(type(parsed[2]["shell_environment_policy"]["set"]["ZOTERO_HTTP_URL"]), str)
            self.assertEqual(parsed[3]["shell_environment_policy"]["set"]["ZOTERO_MCP_URL"],
                             "http://127.0.0.1:9001")
            self.assertIs(type(parsed[3]["shell_environment_policy"]["set"]["ZOTERO_MCP_URL"]), str)
            network_access = parsed[4]["sandbox_workspace_write"]["network_access"]
            self.assertIs(type(network_access), bool)
            self.assertIs(network_access, True)
            self.assertFalse(any("NPM_CONFIG_CACHE" in value for value in assignments))
            self.assertFalse(any("CHROME_PROFILE_DIR" in value for value in assignments))
            self.assertFalse(any("CHROME_CDP_PORT" in value for value in assignments))
            self.assertFalse(any("mcp_servers." in value for value in assignments))
            self.assertEqual(json.loads(output.read_text())["command"], command)

    def test_enable_chrome_discovers_actual_server_and_injects_browser_wiring(self):
        """A separate browser-specific recipe may opt into the legacy wiring."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            (root / ".codex").mkdir(parents=True)
            (root / ".codex/config.toml").write_text(
                '[mcp_servers."actual-browser-server"]\n'
                'command = "npx"\n'
                '[mcp_servers."actual-browser-server".env]\n'
                'CHROME_PROFILE_DIR = "/tmp/profile"\n'
                'CHROME_CDP_PORT = "9222"\n', encoding="utf-8")
            prompt = Path(directory) / "prompt.md"
            prompt.write_text("Run browser-specific case", encoding="utf-8")
            output = Path(directory) / "request.json"
            request = module.build_request(
                consumer_root=root,
                prompt_file=prompt,
                output=output,
                zotero_http_url="http://127.0.0.1:9000",
                zotero_mcp_url="http://127.0.0.1:9001",
                enable_chrome=True,
                chrome_profile_dir='/tmp/chrome "profile"',
                chrome_cdp_port="9333",
                npm_cache='/tmp/npm "cache"',
            )
            argv = shlex.split(request["command"])
            assignments = [argv[index + 1] for index, value in enumerate(argv[:-1])
                           if value == "--config"]
            self.assertEqual(len(assignments), 8)
            parsed = [tomllib.loads(f"{assignment}\n") for assignment in assignments]
            self.assertEqual(parsed[5]["shell_environment_policy"]["set"]["NPM_CONFIG_CACHE"],
                             '/tmp/npm "cache"')
            self.assertEqual(parsed[6]["mcp_servers"]["actual-browser-server"]["env"]["CHROME_PROFILE_DIR"],
                             '/tmp/chrome "profile"')
            self.assertIs(type(parsed[7]["mcp_servers"]["actual-browser-server"]["env"]["CHROME_CDP_PORT"]), str)
            self.assertEqual(parsed[7]["mcp_servers"]["actual-browser-server"]["env"]["CHROME_CDP_PORT"], "9333")

    def test_ambiguous_chrome_configuration_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            root.mkdir()
            (root / "a.toml").write_text(
                '[mcp_servers."chrome-a"]\ncommand = "a"\n', encoding="utf-8")
            (root / "b.toml").write_text(
                '[mcp_servers."chrome-b"]\ncommand = "b"\n', encoding="utf-8")
            with self.assertRaises(module.RequestBuildError):
                module.discover_chrome_server_id(root)

    def test_selects_page_scoped_server_from_generated_chrome_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            root.mkdir()
            (root / "config.toml").write_text(
                '[mcp_servers."chrome-devtools"]\n'
                'args = ["--scan"]\n'
                '[mcp_servers."pdf-chrome"]\n'
                'args = ["--page-id"]\n'
                '[mcp_servers."sd-chrome"]\n'
                'args = ["--output-mode=compact"]\n', encoding="utf-8")
            self.assertEqual(module.discover_chrome_server_id(root), "pdf-chrome")

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
