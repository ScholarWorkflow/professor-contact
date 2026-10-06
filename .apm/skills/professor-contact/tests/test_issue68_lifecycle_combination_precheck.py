"""Plan r26 expected outcomes, independent of the lifecycle implementation."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "runtime"))
import preflight_issue68_lifecycle_combination_r31 as precheck


class CombinationPrecheckTests(unittest.TestCase):
    def test_main_without_history_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "new-attempt"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(precheck.main([str(output)]), 0)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["historical_source_reuse"], [])
            self.assertEqual(summary["state"], "COMBINATION_VERIFIER_READY")
            self.assertEqual(len(summary["cases"]), 6)
            before = {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in output.rglob("*") if path.is_file()}
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                precheck.main([str(output)])
            self.assertEqual(error.exception.code, 2)
            after = {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in output.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

    def test_explicit_history_records_source_without_modification(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "history.json"
            # A declared synthetic fixture checks the optional argument only;
            # it does not claim to be an original historical response.
            events = [{"runtime_seq": index, "runtime_generation": "fixture-1",
                "message": {"method": method, "params": {"threadId": "fixture-root",
                    "turnId": "fixture-turn", "item": {"type": "commandExecution",
                    "id": "fixture-command", "command": "fixture-command", "exitCode": 0,
                    "aggregatedOutput": "{}"}}}}
                for index, method in enumerate(("item/started", "item/completed"), 1)]
            source.write_text(json.dumps({"synthetic": True, "output": {
                "thread_id": "fixture-root", "turn_id": "fixture-turn",
                "runtime_generation": "fixture-1", "app_server_events": events}}))
            original = source.read_bytes()
            output = Path(root) / "new-attempt"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(precheck.main([str(output), "--historical-response-03", str(source)]), 0)
            reused = json.loads((output / "summary.json").read_text())["historical_source_reuse"]
            self.assertEqual(len(reused), 1)
            self.assertEqual(reused[0]["source_path"], str(source.resolve()))
            self.assertEqual(reused[0]["response_sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(source.read_bytes(), original)

    def test_missing_explicit_history_refuses_before_creating_output(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "new-attempt"
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                precheck.main([str(output), "--historical-response-04", str(Path(root) / "missing.json")])
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(output.exists())

    def test_plan_required_outcomes(self):
        expected = {"legal": "PASS", "residual": "FAIL_PRODUCT",
                    "protected_changed": "FAIL_PRODUCT", "wrong_request": "INVALID_EVIDENCE",
                    "missing_use": "BLOCKED_OBSERVABILITY", "incomplete_scan": "INVALID_EVIDENCE"}
        with tempfile.TemporaryDirectory() as root:
            for scenario, verdict in expected.items():
                with self.subTest(scenario=scenario):
                    result = precheck.run_case(Path(root) / scenario, scenario)
                    self.assertEqual(result["proof"]["verdict"], verdict)
                    self.assertEqual(result["mutation_operation_events"], 0)
                    self.assertTrue(result["same_parsed_object_used"])


if __name__ == "__main__":
    unittest.main()
