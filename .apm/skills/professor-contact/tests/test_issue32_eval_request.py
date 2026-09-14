"""Issue #40: canonical eval requests are Chrome-free and network-enabled.

Regression coverage (#10/#11): the canonical R1–R4 request must carry
``--sandbox workspace-write`` with ``sandbox_workspace_write.network_access=true``
and string-valued Zotero env overrides, must never discover or inject
Chrome MCP / CHROME_PROFILE_DIR / CHROME_CDP_PORT / NPM_CONFIG_CACHE, and
the ``--enable-chrome`` opt-in must stay fully isolated from the canonical
path.
"""
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

HTTP_URL = "http://127.0.0.1:21001"
MCP_URL = "http://127.0.0.1:21002/mcp"


def consumer_with_chrome(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".codex").mkdir(parents=True)
    (root / ".codex/config.toml").write_text(
        '[mcp_servers."actual.browser.server"]\n'
        'command = "npx"\n'
        '[mcp_servers."actual.browser.server".env]\n'
        'CHROME_PROFILE_DIR = "/tmp/profile"\n'
        'CHROME_CDP_PORT = "9222"\n', encoding="utf-8")
    return root


class Issue32EvalRequestTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.directory = Path(self.holder.name)

    def prompt(self) -> Path:
        prompt = self.directory / "prompt.txt"
        prompt.write_text("Run Stage 1", encoding="utf-8")
        return prompt

    def assignments(self, request) -> list[dict]:
        argv = shlex.split(request["command"])
        self.assertEqual(argv[:2], ["--json", "--ephemeral"])
        self.assertNotIn("codex", argv[:2])
        self.assertNotIn("exec", argv[:2])
        flags = [argv[index + 1] for index, value in enumerate(argv[:-1])
                 if value == "--config"]
        return [tomllib.loads(f"{flag}\n") for flag in flags]

    def test_canonical_request_is_chrome_free_with_network_and_zotero_env(self):
        root = consumer_with_chrome(self.directory / "consumer")
        output = self.directory / "request.json"
        request = module.build_request(
            consumer_root=root, prompt_file=self.prompt(), output=output,
            zotero_http_url=HTTP_URL, zotero_mcp_url=MCP_URL)
        self.assertEqual(request["timeout"], 1800)
        argv = shlex.split(request["command"])
        self.assertIn("workspace-write", argv)
        parsed = self.assignments(request)
        self.assertEqual(len(parsed), 4)
        self.assertEqual(parsed[0]["model_reasoning_effort"], "low")
        self.assertEqual(parsed[1]["shell_environment_policy"]["set"]["ZOTERO_HTTP_URL"], HTTP_URL)
        self.assertEqual(parsed[2]["shell_environment_policy"]["set"]["ZOTERO_MCP_URL"], MCP_URL)
        self.assertIs(parsed[3]["sandbox_workspace_write"]["network_access"], True)
        serialized = request["command"]
        self.assertNotIn("chrome", serialized.lower())
        self.assertNotIn("CHROME_PROFILE_DIR", serialized)
        self.assertNotIn("CHROME_CDP_PORT", serialized)
        self.assertNotIn("NPM_CONFIG_CACHE", serialized)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["command"],
                         request["command"])

    def test_canonical_request_ignores_installed_chrome_servers(self):
        # An ambiguous Chrome set would make discovery raise; the canonical
        # path must never even scan for it.
        root = self.directory / "consumer"
        root.mkdir()
        (root / "a.toml").write_text('[mcp_servers."chrome-a"]\ncommand = "a"\n', encoding="utf-8")
        (root / "b.toml").write_text('[mcp_servers."chrome-b"]\ncommand = "b"\n', encoding="utf-8")
        request = module.build_request(
            consumer_root=root, prompt_file=self.prompt(),
            output=self.directory / "request.json",
            zotero_http_url=HTTP_URL, zotero_mcp_url=MCP_URL)
        self.assertNotIn("chrome", request["command"].lower())

    def test_zotero_urls_are_required_and_stay_strings(self):
        root = self.directory / "consumer"
        root.mkdir()
        with self.assertRaises(module.RequestBuildError):
            module.build_request(consumer_root=root, prompt_file=self.prompt(),
                                 output=self.directory / "request.json",
                                 zotero_http_url="", zotero_mcp_url=MCP_URL)
        with self.assertRaises(module.RequestBuildError):
            module.build_request(consumer_root=root, prompt_file=self.prompt(),
                                 output=self.directory / "request.json",
                                 zotero_http_url=HTTP_URL, zotero_mcp_url="")
        root = consumer_with_chrome(self.directory / "consumer2")
        request = module.build_request(
            consumer_root=root, prompt_file=self.prompt(),
            output=self.directory / "request2.json",
            zotero_http_url="http://127.0.0.1:21001", zotero_mcp_url="http://127.0.0.1:21002/mcp")
        parsed = self.assignments(request)
        for entry in parsed[1:3]:
            value = entry["shell_environment_policy"]["set"]
            for name in ("ZOTERO_HTTP_URL", "ZOTERO_MCP_URL"):
                if name in value:
                    self.assertIs(type(value[name]), str)

    def test_enable_chrome_opt_in_restores_legacy_wiring(self):
        root = consumer_with_chrome(self.directory / "consumer")
        request = module.build_request(
            consumer_root=root, prompt_file=self.prompt(),
            output=self.directory / "chrome-request.json",
            zotero_http_url=HTTP_URL, zotero_mcp_url=MCP_URL,
            chrome_profile_dir='/tmp/chrome "profile"', chrome_cdp_port="9333",
            npm_cache='/tmp/npm "cache"', enable_chrome=True)
        parsed = self.assignments(request)
        self.assertEqual(len(parsed), 7)
        self.assertEqual(parsed[0]["model_reasoning_effort"], "low")
        self.assertEqual(parsed[1]["shell_environment_policy"]["set"]["ZOTERO_HTTP_URL"], HTTP_URL)
        self.assertEqual(parsed[2]["shell_environment_policy"]["set"]["ZOTERO_MCP_URL"], MCP_URL)
        self.assertIs(parsed[3]["sandbox_workspace_write"]["network_access"], True)
        self.assertEqual(parsed[4]["shell_environment_policy"]["set"]["NPM_CONFIG_CACHE"],
                         '/tmp/npm "cache"')
        self.assertEqual(parsed[5]["mcp_servers"]["actual.browser.server"]["env"]["CHROME_PROFILE_DIR"],
                         '/tmp/chrome "profile"')
        self.assertIs(type(parsed[6]["mcp_servers"]["actual.browser.server"]["env"]["CHROME_CDP_PORT"]), str)
        self.assertEqual(parsed[6]["mcp_servers"]["actual.browser.server"]["env"]["CHROME_CDP_PORT"], "9333")

    def test_ambiguous_chrome_configuration_is_blocked(self):
        root = self.directory / "consumer"
        root.mkdir()
        (root / "a.toml").write_text('[mcp_servers."chrome-a"]\ncommand = "a"\n', encoding="utf-8")
        (root / "b.toml").write_text('[mcp_servers."chrome-b"]\ncommand = "b"\n', encoding="utf-8")
        with self.assertRaises(module.RequestBuildError):
            module.discover_chrome_server_id(root)

    def test_selects_page_scoped_server_from_generated_chrome_set(self):
        root = self.directory / "consumer"
        root.mkdir()
        (root / "config.toml").write_text(
            '[mcp_servers."chrome-devtools"]\n'
            'args = ["--scan"]\n'
            '[mcp_servers."pdf-chrome"]\n'
            'args = ["--page-id"]\n'
            '[mcp_servers."sd-chrome"]\n'
            'args = ["--output-mode=compact"]\n', encoding="utf-8")
        self.assertEqual(module.discover_chrome_server_id(root), "pdf-chrome")

    def test_cli_requires_zotero_urls_and_defaults_to_canonical_path(self):
        parser = module._parser()
        args = parser.parse_args([
            "--consumer-root", "consumer", "--prompt-file", "prompt.txt",
            "--output", "request.json",
            "--zotero-http-url", HTTP_URL, "--zotero-mcp-url", MCP_URL])
        self.assertFalse(args.enable_chrome)
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "--consumer-root", "consumer", "--prompt-file", "prompt.txt",
                "--output", "request.json"])


if __name__ == "__main__":
    unittest.main()
