"""Issue #39: the dedicated PC39 eval request builder contract.

PC39-R1 tests only the Stage 2 Zotero endpoint override.  Its request must
therefore stay minimal: model/reasoning, exact clean-consumer trust,
workspace-write network access, and the two resolved Zotero endpoints.  Any
Chrome MCP, Chrome env, or npm cache wiring belongs to other issues and must
never re-enter this request.
"""
import importlib.util
import json
import shlex
import tempfile
import tomllib
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
MODULE_PATH = TESTS_DIR / "runtime" / "build_issue39_eval_request.py"
spec = importlib.util.spec_from_file_location("issue39_eval_request", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FIXED_PROMPT = (
    "Delegate this task to the installed custom agent `professor-contact-analyzer`"
    " and wait for its result before continuing.\n"
    "folder_path: /tmp/program\n"
    "professors: Example Professor\n"
    "paper_analysis: relevant\n"
    "gap_scope: selected_direction\n"
    "freshness_scope: shortlist\n"
    "chatgpt_handoff: continue\n"
)


def build(tmp: str, prompt: str = FIXED_PROMPT, **overrides):
    root = overrides.pop("consumer_root", None) or Path(tmp) / "consumer"
    root.mkdir(parents=True, exist_ok=True)
    prompt_file = Path(tmp) / "prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    output = Path(tmp) / "request.json"
    arguments = dict(
        consumer_root=root,
        prompt_file=prompt_file,
        output=output,
        zotero_http_url="http://127.0.0.1:24119",
        zotero_mcp_url="http://127.0.0.1:24122/mcp",
    )
    arguments.update(overrides)
    request = module.build_request(**arguments)
    return request, output, root


def config_assignments(argv):
    return [argv[index + 1] for index, value in enumerate(argv[:-1])
            if value == "--config"]


class Issue39EvalRequestTests(unittest.TestCase):
    def test_builds_minimal_endpoint_only_command(self):
        with tempfile.TemporaryDirectory() as directory:
            request, output, root = build(directory)
            self.assertEqual(request["timeout"], 1800)
            argv = shlex.split(request["command"])
            self.assertEqual(argv[:5],
                             ["--json", "--ephemeral", "--skip-git-repo-check",
                              "--sandbox", "workspace-write"])
            self.assertNotIn("codex", argv)
            self.assertNotIn("exec", argv)
            self.assertEqual(argv[argv.index("--cd") + 1], str(root.resolve()))
            self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.6-luna")

            assignments = config_assignments(argv)
            self.assertEqual(len(assignments), 5)
            parsed = [tomllib.loads(f"{assignment}\n") for assignment in assignments]
            self.assertEqual(parsed[0]["model_reasoning_effort"], "low")
            trust = parsed[1]["projects"][str(root.resolve())]
            self.assertEqual(trust, {"trust_level": "trusted"})
            network = parsed[2]["sandbox_workspace_write"]["network_access"]
            self.assertIs(type(network), bool)
            self.assertIs(network, True)
            self.assertEqual(
                parsed[3]["shell_environment_policy"]["set"]["ZOTERO_HTTP_URL"],
                "http://127.0.0.1:24119")
            self.assertIs(type(
                parsed[3]["shell_environment_policy"]["set"]["ZOTERO_HTTP_URL"]), str)
            self.assertEqual(
                parsed[4]["shell_environment_policy"]["set"]["ZOTERO_MCP_URL"],
                "http://127.0.0.1:24122/mcp")
            self.assertIs(type(
                parsed[4]["shell_environment_policy"]["set"]["ZOTERO_MCP_URL"]), str)

            prompt_argument = argv[argv.index("--", 5) + 1]
            self.assertEqual(prompt_argument, FIXED_PROMPT)
            self.assertNotIn("profile_path", prompt_argument)
            self.assertEqual(json.loads(output.read_text())["command"],
                             request["command"])

    def test_request_stays_free_of_chrome_mcp_and_npm_wiring(self):
        with tempfile.TemporaryDirectory() as directory:
            request, _, _ = build(directory)
            argv = shlex.split(request["command"])
            for assignment in config_assignments(argv):
                parsed = tomllib.loads(f"{assignment}\n")
                self.assertNotIn("mcp_servers", parsed)
                for key in parsed:
                    self.assertFalse(key.startswith("mcp_servers."), key)
                    self.assertFalse(key.startswith("shell_environment_policy.set.CHROME"), key)
                self.assertNotIn("NPM_CONFIG_CACHE", assignment)
                self.assertNotIn("CHROME_", assignment)
            self.assertNotIn("NPM_CONFIG_CACHE", request["command"])
            self.assertNotIn("CHROME_", request["command"])
            self.assertNotIn("mcp_servers", request["command"])
            self.assertNotIn("agents.max_depth", request["command"])

    def test_toml_encoding_survives_quotes_and_spaces_in_paths_and_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            request, _, root = build(
                directory,
                consumer_root=Path(directory) / "consumer root",
                zotero_http_url="http://127.0.0.1:24119",
                zotero_mcp_url='http://127.0.0.1:24122/mcp',
                model='gpt-5.6 "luna"')
            argv = shlex.split(request["command"])
            assignments = config_assignments(argv)
            parsed = [tomllib.loads(f"{assignment}\n") for assignment in assignments]
            # A space-bearing consumer path and a quote-bearing model value
            # must survive the inline-table TOML encoding untouched.
            self.assertEqual(parsed[1]["projects"][str(root.resolve())],
                             {"trust_level": "trusted"})
            self.assertEqual(argv[argv.index("--model") + 1], 'gpt-5.6 "luna"')
            self.assertEqual(parsed[0]["model_reasoning_effort"], "low")

    def test_rejects_production_zotero_ports(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(module.RequestBuildError):
                build(directory, zotero_http_url="http://127.0.0.1:23119")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(module.RequestBuildError):
                build(directory, zotero_mcp_url="http://127.0.0.1:23120/mcp")

    def test_rejects_default_free_endpoints_and_incomplete_mcp_url(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(module.RequestBuildError):
                build(directory, zotero_http_url="")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(module.RequestBuildError):
                build(directory, zotero_mcp_url="http://127.0.0.1:24122")

    def test_rejects_prompt_leaking_chrome_profile_path(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(module.RequestBuildError):
                build(directory, prompt=FIXED_PROMPT + "\nprofile_path: /tmp/x\n")

    def test_rejects_missing_consumer_root(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(module.RequestBuildError):
                module.build_request(
                    consumer_root=Path(directory) / "absent",
                    prompt_file=Path(directory) / "prompt.txt",
                    output=Path(directory) / "request.json",
                    zotero_http_url="http://127.0.0.1:24119",
                    zotero_mcp_url="http://127.0.0.1:24122/mcp")


if __name__ == "__main__":
    unittest.main()
