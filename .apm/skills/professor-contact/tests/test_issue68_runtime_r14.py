"""Gate-2 r14 regressions for formal eval-service provenance and isolation.

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

    def stable_storage(self, pid=40721):
        codex_home = self.root / "test-codex-home"
        codex_home.mkdir(exist_ok=True)
        return {
            "status": "ISOLATION_CONFIRMED",
            "service_pid": pid,
            "service_cwd": str(self.eval_root),
            "codex_home": str(codex_home),
            "production_default_codex_home": str((Path.home() / ".codex").resolve()),
            "config_path": str(codex_home / "config.toml"),
            "config_present": False,
            "sqlite": {
                "config_sqlite_home": None,
                "inherited_CODEX_SQLITE_HOME": None,
                "effective_path": str(codex_home),
                "source": "CODEX_HOME fallback",
                "inside_test_codex_home": True,
            },
            "log": {
                "config_log_dir": None,
                "effective_path": None,
                "source": "CODEX_HOME-derived default",
                "inside_test_codex_home": True,
            },
        }

    def service_provenance(self, pid=40721):
        return {
            "eval_server": {"sha": EVAL_SHA, "dirty": "no"},
            "service": self.stable_service(pid),
            "storage": self.stable_storage(pid),
        }

    def clean_revision(self, root, expected):
        return {"sha": expected, "dirty": "no", "root": str(Path(root))}

    def test_contract_binds_unique_r14_entry_and_splits_capability_from_isolation_preflight(self):
        contract = entry.load_contract()
        self.assertEqual(contract["fixture_sha"], FIXTURE_SHA)
        self.assertEqual(contract["eval_server_revision"], EVAL_SHA)
        self.assertEqual(
            contract["runner"],
            ".apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r14_codex.py",
        )
        self.assertEqual(
            contract["preflight"]["capability_entry"],
            ".apm/skills/professor-contact/tests/runtime/check_issue68_codex_final_source_r13.py",
        )
        self.assertEqual(
            contract["preflight"]["isolation_entry"],
            ".apm/skills/professor-contact/tests/runtime/check_issue68_eval_service_isolation_r14.py",
        )
        self.assertIn(
            "r14 changes only formal-run service provenance",
            contract["preflight"]["capability_reuse_rule"],
        )

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

    def test_storage_isolation_accepts_nonproduction_home_and_records_sqlite_and_log(self):
        codex_home = self.root / "test-codex-home"
        codex_home.mkdir()
        sqlite_home = codex_home / "sqlite"
        log_dir = codex_home / "logs"
        (codex_home / "config.toml").write_text(
            f'sqlite_home = "{sqlite_home}"\nlog_dir = "{log_dir}"\n', encoding="utf-8"
        )
        env = f"/usr/bin/python eval_server.py --port 17902 CODEX_HOME={codex_home}"
        with mock.patch.object(entry.isolation, "process_environment_text", return_value=env):
            observed = entry.isolation.capture_storage_isolation(self.stable_service())
        self.assertEqual(observed["status"], "ISOLATION_CONFIRMED")
        self.assertEqual(observed["sqlite"]["source"], "config.sqlite_home")
        self.assertEqual(observed["log"]["source"], "config.log_dir")
        self.assertTrue(observed["sqlite"]["inside_test_codex_home"])
        self.assertTrue(observed["log"]["inside_test_codex_home"])

    def test_storage_isolation_rejects_production_default_or_external_sqlite(self):
        default_home = (Path.home() / ".codex").resolve()
        env = f"/usr/bin/python eval_server.py --port 17902 CODEX_HOME={default_home}"
        with mock.patch.object(entry.isolation, "process_environment_text", return_value=env):
            with self.assertRaisesRegex(ValueError, "eval_service_uses_production_codex_home"):
                entry.isolation.capture_storage_isolation(self.stable_service())

        codex_home = self.root / "test-codex-home"
        codex_home.mkdir()
        external = self.root / "foreign-sqlite"
        env = (
            f"/usr/bin/python eval_server.py --port 17902 CODEX_HOME={codex_home} "
            f"CODEX_SQLITE_HOME={external}"
        )
        with mock.patch.object(entry.isolation, "process_environment_text", return_value=env):
            with self.assertRaisesRegex(ValueError, "eval_service_sqlite_env_not_test_only"):
                entry.isolation.capture_storage_isolation(self.stable_service())

    def test_formal_entry_archives_service_and_storage_before_request_and_rechecks_after(self):
        before = self.service_provenance()
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
        self.assertEqual(provenance["eval_storage_before"]["status"], "ISOLATION_CONFIRMED")

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

    def test_formal_entry_invalidates_if_service_or_storage_changes_during_request(self):
        before = self.service_provenance(40721)
        after = self.service_provenance(50000)

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
