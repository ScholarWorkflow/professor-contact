"""Gate-2 r11 bridge regressions. These tests do not constitute host PASS."""
import importlib
import sys
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
bridge = importlib.import_module("run_issue68_stage5_routing_r11")


class TestIssue68RuntimeR11Bridge(unittest.TestCase):
    def test_codex_shared_parser_is_rewritten_to_root_history_wrapper(self):
        seen = {}

        def fake_run(argv, cwd, prefix, *, env=None, timeout=180):
            seen["argv"] = list(argv)
            seen["timeout"] = timeout
            return 0

        old = bridge._ORIGINAL_RUN
        bridge._ORIGINAL_RUN = fake_run
        self.addCleanup(setattr, bridge, "_ORIGINAL_RUN", old)
        with tempfile.TemporaryDirectory() as root:
            fixture = Path(root) / "fixture"
            parser = fixture / "scripts" / "parse_codex_eval_evidence.py"
            bridge.run([sys.executable, str(parser), "--output", "adapter.json"], Path(root), Path(root) / "run")

        self.assertEqual(
            Path(seen["argv"][1]).name,
            "parse_codex_eval_evidence_with_root_history.py",
        )
        contract_index = seen["argv"].index("--root-history-contract")
        self.assertEqual(
            Path(seen["argv"][contract_index + 1]).name,
            "codex-root-thread-read-contract.json",
        )

    def test_non_codex_parser_command_is_unchanged(self):
        seen = {}

        def fake_run(argv, cwd, prefix, *, env=None, timeout=180):
            seen["argv"] = list(argv)
            return 0

        old = bridge._ORIGINAL_RUN
        bridge._ORIGINAL_RUN = fake_run
        self.addCleanup(setattr, bridge, "_ORIGINAL_RUN", old)
        argv = ["opencode", "run", "prompt"]
        bridge.run(argv, Path("."), Path("run"))
        self.assertEqual(seen["argv"], argv)

    def test_fixture_sha_is_the_gate2_r11_fixture(self):
        self.assertEqual(
            bridge.FIXTURE_SHA,
            "cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
