"""Gate-2 r14 regressions for formal eval-service provenance.

These tests validate Recipe wiring only. They do not execute PC68-R1 acceptance.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RUNTIME = Path(__file__).resolve().parent / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))


def load(name):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


entry = load("run_issue68_stage5_routing_r14_codex")
FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
EVAL_SHA = "3fdfa9387140cfc2e2aa3af415f85015f79706d2"


class TestIssue68RuntimeR14(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.producer = self.root / "producer"
        self.fixture = self.root / "fixture"
        self.eval_root = self.root / "eval-server"
        self.output = self.root / "output"
        for path in (self.producer, self.fixture, self.eval_root):
            path.mkdir()

    def argv(self):
        return [
            "--producer-root", str(self.producer),
            "--producer-sha", "producer-sha",
            "--fixture-root", str(self.fixture),
            "--fixture-sha", FIXTURE_SHA,
            "--eval-direnv-root", str(self.eval_root),
            "--output-dir", str(self.output),
        ]

    def stable_service(self, pid=40721):
        return {
            "port": "17902",
            "pid": pid,
            "start_time": "Sat Oct  3 19:04:39 2026",
            "command": "/usr/bin/python3 eval_server.py --port 17902",
            "cwd": str(self.eval_root),
        }

    def clean_revision(self, root, expected):
        return {"sha": expected, "dirty": "no", "root": str(Path(root))}

    def test_contract_binds_unique_r14_entry_and_reuses_r13_preflight_only_by_dependency(self):
        contract = entry.load_contract()
        self.assertEqual(contract["fixture_sha"], FIXTURE_SHA)
        self.assertEqual(contract["eval_server_revision"], EVAL_SHA)
        self.assertEqual(
            contract["runner"],
            ".apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r14_codex.py",
        )
        self.assertEqual(
            contract["preflight"]["entry"],
            ".apm/skills/professor-contact/tests/runtime/check_issue68_codex_final_source_r13.py",
        )
        self.assertIn("r14 changes only formal-run service provenance", contract["preflight"]["reuse_rule"])

    def test_capture_service_instance_binds_listener_to_checkout_port_and_start_time(self):
        responses = {
            ("lsof", "-nP", "-iTCP:17902", "-sTCP:LISTEN", "-Fp"): "p40721\n",
            ("lsof", "-a", "-p", "40721", "-d", "cwd", "-Fn"): f"p40721\nfcwd\nn{self.eval_root}\n",
            ("ps", "-p", "40721", "-o", "lstart="): "Sat Oct  3 19:04:39 2026\n",
            ("ps", "-p", "40721", "-o", "command="): "/usr/bin/python3 eval_server.py --port 17902\n",
        }

        def fake_check_output(argv, **kwargs):
            return responses[tuple(str(part) for part in argv)]

        with mock.patch.object(entry.subprocess, "check_output", side_effect=fake_check_output):
            observed = entry.capture_service_instance(self.eval_root, "17902")
        self.assertEqual(observed, self.stable_service())

    def test_capture_service_instance_rejects_listener_from_another_checkout(self):
        other = self.root / "other"
        other.mkdir()

        def fake_check_output(argv, **kwargs):
            key = tuple(str(part) for part in argv)
            if key[:2] == ("lsof", "-nP"):
                return "p40721\n"
            if key[:2] == ("lsof", "-a"):
                return f"p40721\nfcwd\nn{other}\n"
            raise AssertionError(key)

        with mock.patch.object(entry.subprocess, "check_output", side_effect=fake_check_output):
            with self.assertRaisesRegex(ValueError, "eval_service_cwd_mismatch"):
                entry.capture_service_instance(self.eval_root, "17902")

    def test_formal_entry_archives_service_before_request_and_rechecks_after(self):
        before = {"eval_server": {"sha": EVAL_SHA, "dirty": "no"}, "service": self.stable_service()}
        host_calls = []

        def fake_host(args, output):
            host_calls.append(True)
            self.assertTrue((output / "eval-service-provenance.before.json").is_file())
            self.assertTrue((output / "provenance.json").is_file())
            return {"verdict": "PASS", "reason_code": None}

        with mock.patch.object(entry, "pin", return_value=None), \
             mock.patch.object(entry, "check_entry_uniqueness", return_value=True), \
             mock.patch.object(entry.base, "clean_revision", side_effect=self.clean_revision), \
             mock.patch.object(entry, "capture_eval_service_provenance", side_effect=[before, before]), \
             mock.patch.object(entry.base, "codex_host", side_effect=fake_host):
            rc = entry.main(self.argv())

        self.assertEqual(rc, 0)
        self.assertEqual(len(host_calls), 1)
        after = json.loads((self.output / "eval-service-provenance.after.json").read_text(encoding="utf-8"))
        final = json.loads((self.output / "final-verdict.json").read_text(encoding="utf-8"))
        provenance = json.loads((self.output / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(after, before)
        self.assertEqual(final["verdict"], "PASS")
        self.assertEqual(provenance["eval_server"]["sha"], EVAL_SHA)
        self.assertEqual(provenance["eval_service_before"]["pid"], 40721)

    def test_formal_entry_stops_before_acceptance_when_eval_revision_is_wrong(self):
        host = mock.Mock()

        def clean(root, expected):
            if Path(root).resolve() == self.eval_root:
                raise ValueError("wrong_revision_or_dirty_checkout")
            return self.clean_revision(root, expected)

        with mock.patch.object(entry, "pin", return_value=None), \
             mock.patch.object(entry, "check_entry_uniqueness", return_value=True), \
             mock.patch.object(entry.base, "clean_revision", side_effect=clean), \
             mock.patch.object(entry, "resolve_eval_port", return_value="17902"), \
             mock.patch.object(entry.base, "codex_host", host):
            rc = entry.main(self.argv())

        self.assertEqual(rc, 1)
        host.assert_not_called()
        final = json.loads((self.output / "final-verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(
            (final["state"], final["reason_code"]),
            ("CASE_NOT_STARTED", "wrong_revision_or_dirty_checkout"),
        )

    def test_formal_entry_invalidates_if_service_instance_changes_during_request(self):
        before = {"eval_server": {"sha": EVAL_SHA, "dirty": "no"}, "service": self.stable_service(40721)}
        after = {"eval_server": {"sha": EVAL_SHA, "dirty": "no"}, "service": self.stable_service(50000)}

        with mock.patch.object(entry, "pin", return_value=None), \
             mock.patch.object(entry, "check_entry_uniqueness", return_value=True), \
             mock.patch.object(entry.base, "clean_revision", side_effect=self.clean_revision), \
             mock.patch.object(entry, "capture_eval_service_provenance", side_effect=[before, after]), \
             mock.patch.object(entry.base, "codex_host", return_value={"verdict": "PASS", "reason_code": None}):
            rc = entry.main(self.argv())

        self.assertEqual(rc, 1)
        final = json.loads((self.output / "final-verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(
            (final["verdict"], final["reason_code"]),
            ("INVALID_TEST_EXECUTION", "eval_service_changed_during_execution"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
