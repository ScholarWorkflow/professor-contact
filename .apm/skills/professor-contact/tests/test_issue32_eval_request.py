import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
MODULE_PATH = TESTS_DIR / "runtime/build_issue32_eval_request.py"
spec = importlib.util.spec_from_file_location("issue32_eval_request", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Issue32EvalRequestTests(unittest.TestCase):
    def test_discovers_actual_chrome_server_and_builds_quoted_command(self):
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
            prompt.write_text("Run Stage 0–5", encoding="utf-8")
            output = Path(directory) / "request.json"
            request = module.build_request(
                consumer_root=root, prompt_file=prompt, output=output,
                zotero_http_url="http://127.0.0.1:9000", zotero_mcp_url="http://127.0.0.1:9001",
                chrome_profile_dir="/tmp/chrome profile", chrome_cdp_port="9333",
                npm_cache="/tmp/npm cache")
            self.assertEqual(request["timeout"], 1800)
            command = request["command"]
            self.assertIn("codex exec --json --ephemeral --skip-git-repo-check", command)
            self.assertIn("mcp_servers.actual-browser-server.env.CHROME_CDP_PORT=9333", command)
            self.assertIn("shell_environment_policy.set.ZOTERO_HTTP_URL=http://127.0.0.1:9000", command)
            self.assertIn("--cd", command)
            self.assertEqual(json.loads(output.read_text())["command"], command)

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


if __name__ == "__main__":
    unittest.main()
