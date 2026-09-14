import importlib.util
import json
import shlex
import tempfile
import tomllib
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
MODULE_PATH = TESTS_DIR / "runtime/build_issue32_eval_request.py"
spec = importlib.util.spec_from_file_location("issue32_eval_request", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def assignments_of(argv):
    return [argv[index + 1] for index, value in enumerate(argv[:-1])
            if value == "--config"]


class Issue32EvalRequestTests(unittest.TestCase):
    def test_default_request_needs_no_chrome_and_keeps_official_network_config(self):
        with tempfile.TemporaryDirectory() as directory:
            # No TOML at all in the consumer: Chrome discovery must not run.
            root = Path(directory) / "consumer"
            root.mkdir()
            prompt = Path(directory) / "prompt.md"
            prompt.write_text("Run R1", encoding="utf-8")
            output = Path(directory) / "request.json"
            request = module.build_request(
                consumer_root=root, prompt_file=prompt, output=output,
                zotero_http_url="http://127.0.0.1:9000",
                zotero_mcp_url="http://127.0.0.1:9001/mcp")
            self.assertEqual(request["timeout"], 1800)
            command = request["command"]
            argv = shlex.split(command)
            self.assertEqual(argv[:2], ["--json", "--ephemeral"])
            self.assertNotIn("codex", argv[:2])
            self.assertNotIn("exec", argv[:2])
            self.assertNotIn("--enable-chrome", argv)
            self.assertNotIn("CHROME_PROFILE_DIR", command)
            self.assertNotIn("CHROME_CDP_PORT", command)
            self.assertNotIn("NPM_CONFIG_CACHE", command)
            self.assertNotIn("mcp_servers", command)
            # R1–R4 canonical config set (issue #40 §5.1) as TOML assignments.
            assignments = assignments_of(argv)
            self.assertEqual(len(assignments), 4)
            parsed = [tomllib.loads(f"{assignment}\n") for assignment in assignments]
            self.assertEqual(parsed[0]["model_reasoning_effort"], "low")
            self.assertEqual(parsed[1]["shell_environment_policy"]["set"]["ZOTERO_HTTP_URL"],
                             "http://127.0.0.1:9000")
            self.assertIs(type(parsed[1]["shell_environment_policy"]["set"]["ZOTERO_HTTP_URL"]), str)
            self.assertEqual(parsed[2]["shell_environment_policy"]["set"]["ZOTERO_MCP_URL"],
                             "http://127.0.0.1:9001/mcp")
            self.assertIs(type(parsed[2]["shell_environment_policy"]["set"]["ZOTERO_MCP_URL"]), str)
            network_access = parsed[3]["sandbox_workspace_write"]["network_access"]
            self.assertIs(type(network_access), bool)
            self.assertIs(network_access, True)
            self.assertEqual(json.loads(output.read_text())["command"], command)

    def test_enable_chrome_discovers_server_and_requires_chrome_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            (root / ".codex").mkdir(parents=True)
            (root / ".codex/config.toml").write_text(
                '[mcp_servers."actual.browser.server"]\n'
                'command = "npx"\n'
                '[mcp_servers."actual.browser.server".env]\n'
                'CHROME_PROFILE_DIR = "/tmp/profile"\n'
                'CHROME_CDP_PORT = "9222"\n', encoding="utf-8")
            prompt = Path(directory) / "prompt.md"
            prompt.write_text("Run Stage 0–5", encoding="utf-8")
            output = Path(directory) / "request.json"
            request = module.build_request(
                consumer_root=root, prompt_file=prompt, output=output,
                zotero_http_url="http://127.0.0.1:9000",
                zotero_mcp_url="http://127.0.0.1:9001",
                chrome_profile_dir='/tmp/chrome "profile"', chrome_cdp_port="9333",
                npm_cache='/tmp/npm "cache"', enable_chrome=True)
            argv = shlex.split(request["command"])
            assignments = assignments_of(argv)
            self.assertEqual(len(assignments), 7)
            parsed = [tomllib.loads(f"{assignment}\n") for assignment in assignments]
            self.assertEqual(parsed[4]["shell_environment_policy"]["set"]["NPM_CONFIG_CACHE"],
                             '/tmp/npm "cache"')
            self.assertEqual(parsed[5]["mcp_servers"]["actual.browser.server"]["env"]["CHROME_PROFILE_DIR"],
                             '/tmp/chrome "profile"')
            self.assertIs(type(parsed[6]["mcp_servers"]["actual.browser.server"]["env"]["CHROME_CDP_PORT"]), str)
            self.assertEqual(parsed[6]["mcp_servers"]["actual.browser.server"]["env"]["CHROME_CDP_PORT"], "9333")
            self.assertEqual(json.loads(output.read_text())["command"], request["command"])

    def test_enable_chrome_requires_non_empty_chrome_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            root.mkdir()
            prompt = Path(directory) / "prompt.md"
            prompt.write_text("Run", encoding="utf-8")
            with self.assertRaises(module.RequestBuildError):
                module.build_request(consumer_root=root, prompt_file=prompt,
                                     output=Path(directory) / "r.json", enable_chrome=True)

    def test_chrome_parameters_without_opt_in_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            root.mkdir()
            prompt = Path(directory) / "prompt.md"
            prompt.write_text("Run", encoding="utf-8")
            with self.assertRaises(module.RequestBuildError):
                module.build_request(consumer_root=root, prompt_file=prompt,
                                     output=Path(directory) / "r.json",
                                     chrome_profile_dir="/tmp/profile", chrome_cdp_port="9333")

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


if __name__ == "__main__":
    unittest.main()
