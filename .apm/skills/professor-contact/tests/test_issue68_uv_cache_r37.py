"""Regression coverage for request-local uv-cache binding in PC68-R1."""
import hashlib
import importlib.util
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

RUNTIME = Path(__file__).resolve().parent / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import verify_issue68_stage5_routing_r19 as verifier
import run_issue68_stage5_routing_r19_codex as runner


def load_capture():
    path = RUNTIME / "capture_issue68_owner_stage5_plan_r1.py"
    spec = importlib.util.spec_from_file_location("capture_issue68_owner_stage5_plan_r1_r37", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


capture = load_capture()
ROOT_PROMPT = RUNTIME / "prompts" / "issue68-stage5-root.txt"


class TestIssue68UvCacheR37(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cache = self.root / "uv-cache"
        self.cache.mkdir()
        self.consumer = self.root / "consumer"
        self.wrapper = self.consumer / ".pc68-test-support" / verifier.OWNER_CAPTURE_NAME
        self.wrapper.parent.mkdir(parents=True)
        self.wrapper.write_bytes(verifier.OWNER_CAPTURE_SOURCE.read_bytes())
        self.entrypoint = self.consumer / ".agents/skills/professor-contact/scripts/contact_state.py"
        self.entrypoint.parent.mkdir(parents=True)
        self.entrypoint.write_text("# synthetic installed entrypoint\n", encoding="utf-8")
        self.packet = {
            "program_root": str(self.root / "program"),
            "email_pack": str(self.root / "program" / "owner" / "邮件输入.json"),
            "template": str(self.root / "template.json"),
            "mode": "first",
        }
        self.owner_input = self.root / "owner-input.json"
        self.owner_input.write_text(json.dumps(self.packet, ensure_ascii=False), encoding="utf-8")
        self.manifest_path = self.root / "fixture-manifest.request.json"
        self.manifest = {
            "program_root": self.packet["program_root"],
            "uv_cache_dir": str(self.cache),
            "owner_capture": {
                "consumer_root": str(self.consumer),
                "runtime_path": str(self.wrapper),
                "installed_entrypoint": str(self.entrypoint),
                "entrypoint_sha256": self.sha256(self.entrypoint.read_bytes()),
                "source_path": str(verifier.OWNER_CAPTURE_SOURCE),
                "source_sha256": verifier.OWNER_CAPTURE_SHA256,
                "runtime_sha256": self.sha256(self.wrapper.read_bytes()),
                "manifest_path": str(self.manifest_path),
            },
        }
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    @staticmethod
    def sha256(value):
        return hashlib.sha256(value).hexdigest()

    def owner_command(self, cache_dir=None):
        tokens = []
        if cache_dir is not None:
            tokens.append("UV_CACHE_DIR=" + str(cache_dir))
        tokens += ["uv", "run", "--no-project", "python", str(self.wrapper),
                   "--action", "stage5-plan", "--owner-input-file", str(self.owner_input),
                   "--contact-state", str(self.entrypoint)]
        return shlex.join(tokens)

    def execute_capture(self, *, inherited_cache):
        arguments = ["--action", "stage5-plan", "--owner-input-file", str(self.owner_input),
                     "--contact-state", str(self.entrypoint)]
        plan = {"status": "ok", "email_pack": self.packet["email_pack"]}
        completed = subprocess.CompletedProcess([], 0,
                                                stdout=json.dumps(plan).encode("utf-8"),
                                                stderr=b"")
        output = io.StringIO()
        with patch.object(capture, "__file__", str(self.wrapper)), \
                patch.object(capture, "_installed_entrypoint", return_value=self.entrypoint), \
                patch.object(capture, "subprocess") as mocked_subprocess, \
                patch.object(capture.sys, "argv", [str(self.wrapper), *arguments]), \
                patch.dict(os.environ, {}, clear=False), \
                redirect_stdout(output):
            if inherited_cache is None:
                os.environ.pop("UV_CACHE_DIR", None)
            else:
                os.environ["UV_CACHE_DIR"] = inherited_cache
            mocked_subprocess.run.return_value = completed
            self.assertEqual(capture.run(self.owner_input, self.entrypoint, "stage5-plan"), 0)
        envelope = json.loads(output.getvalue())
        return envelope, {"id": "owner-call", "command": self.owner_command(self.cache)}

    def validate_capture(self, inherited_cache):
        envelope, call = self.execute_capture(inherited_cache=inherited_cache)
        command_proof = verifier.command_action(call["command"], self.manifest)
        problem = verifier._validate_fixed_capture(
            call, envelope, command_proof["owner_capture"], self.packet, self.manifest)
        return envelope, problem

    def test_root_prompt_binds_fixed_capture_to_request_cache_without_business_steps(self):
        prompt = ROOT_PROMPT.read_text(encoding="utf-8")
        prefix = "UV_CACHE_DIR='{{UV_CACHE_DIR}}' uv run"
        self.assertIn(prefix, prompt)
        self.assertIn("--no-project python '{{CAPTURE_SCRIPT}}' --action stage5-plan", prompt)
        self.assertIn("--contact-state '{{CONTACT_STATE}}'", prompt)
        for business_instruction in (
                "Every root and professor", "stage5-list-inputs",
                "stage5-partition-choices", "raw_results_by_professor_dir",
                "choices_rows", "stage5-rebuild-overview", "professor_results",
                "Keep every `commandExecution`", "remove only this request"):
            with self.subTest(business_instruction=business_instruction):
                self.assertNotIn(business_instruction, prompt)
        bound = prompt.replace("{{UV_CACHE_DIR}}", "/tmp/pc68-request/uv-cache")
        self.assertNotIn("{{UV_CACHE_DIR}}", bound)
        self.assertIn("UV_CACHE_DIR='/tmp/pc68-request/uv-cache' uv run", bound)

    def test_owner_capture_records_and_verifies_inherited_cache_directory(self):
        envelope, problem = self.validate_capture(str(self.cache))
        self.assertEqual(envelope["pc68_fixed_capture"]["uv_cache_dir"], str(self.cache))
        self.assertIsNone(problem)

    def test_owner_capture_with_missing_or_different_inherited_cache_is_invalid(self):
        for inherited in (None, str(self.root / "other-cache")):
            with self.subTest(inherited=inherited):
                envelope, problem = self.validate_capture(inherited)
                self.assertEqual(envelope["pc68_fixed_capture"]["uv_cache_dir"], inherited)
                self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")
                self.assertEqual(problem["reason_code"], "owner_capture_uv_cache_binding_mismatch")

    def test_owner_command_requires_exact_declared_cache_prefix(self):
        expected = verifier.command_action(self.owner_command(self.cache), self.manifest)
        self.assertEqual(expected["owner_capture"]["uv_cache_dir"], str(self.cache))
        for command in (self.owner_command(), self.owner_command(self.root / "other-cache")):
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError, "uv_cache_dir_binding_mismatch"):
                    verifier.command_action(command, self.manifest)

    def run_main_with_cleanup_failure(self, host_result):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "output"
            args = SimpleNamespace(
                producer_root=root / "producer",
                producer_sha="frozen-producer-revision",
                fixture_root=root / "fixture",
                fixture_sha=runner.FIXTURE_SHA,
                eval_direnv_root=root / "eval-service",
                output_dir=output,
                transfer_location_root=root / "transfer-location",
            )
            contract = {
                "revision": "synthetic-r37-contract",
                "producer_revision": args.producer_sha,
            }
            preflight = {
                "ready": True,
                "technical_preflight_ready": True,
                "technical_preflight_block_reasons": [],
                "runtime_environment_facts": {},
                "runtime_environment_evidence": {},
            }
            service = {
                "eval_server": {"sha": "frozen-service-revision"},
                "service": {"port": 4321, "pid": 12345, "start_time": "synthetic"},
                "storage": {"status": "ISOLATION_CONFIRMED"},
            }
            with patch.object(runner, "pin"), \
                    patch.object(runner, "parse_args", return_value=args), \
                    patch.object(runner.transfer_location, "validate_location_root",
                                 return_value=args.transfer_location_root), \
                    patch.object(runner, "overlaps", return_value=False), \
                    patch.object(runner, "check_entry_uniqueness"), \
                    patch.object(runner, "load_contract", return_value=contract), \
                    patch.object(runner, "actual_input_observation_preflight",
                                 return_value=preflight), \
                    patch.object(runner, "_record_service_runtime_facts",
                                 return_value=preflight), \
                    patch.object(runner, "capture_eval_service_provenance",
                                 return_value=service), \
                    patch.object(runner, "_codex_host_with_runtime_capture",
                                 return_value=host_result), \
                    patch.object(runner.signal, "signal"), \
                    patch.object(runner.base, "stop_active"), \
                    patch.object(runner.base, "progress"), \
                    patch.object(runner.base, "clean_revision",
                                 return_value={"sha": "synthetic-revision", "dirty": "no"}), \
                    patch.object(runner.shutil, "rmtree",
                                 side_effect=PermissionError("synthetic cleanup denied")):
                exit_code = runner.main([])

            final = json.loads((output / "final-verdict.json").read_text(encoding="utf-8"))
            evidence = json.loads(
                (output / "codex" / "uv-cache-binding.json").read_text(encoding="utf-8"))
            return exit_code, final, evidence

    def test_cleanup_failure_keeps_confirmed_product_failure_and_records_cleanup_error(self):
        product_failure = {
            "state": "CASE_STARTED",
            "verdict": "FAIL_PRODUCT",
            "reason_code": "owner_business_result_changed",
            "professor_dir": "/synthetic/教授甲",
        }

        exit_code, final, evidence = self.run_main_with_cleanup_failure(product_failure)

        self.assertEqual(exit_code, 1)
        self.assertEqual(final["verdict"], "FAIL_PRODUCT")
        self.assertEqual(final["reason_code"], "owner_business_result_changed")
        self.assertEqual(final["professor_dir"], "/synthetic/教授甲")
        self.assertEqual(final["uv_cache_cleanup"], evidence["cleanup"])
        self.assertFalse(evidence["cleanup"]["confirmed_absent"])
        self.assertEqual(evidence["cleanup"]["error"], "synthetic cleanup denied")

    def test_cleanup_failure_invalidates_non_product_terminal_result(self):
        blocked_result = {
            "state": "CASE_STARTED",
            "verdict": "BLOCKED_OBSERVABILITY",
            "reason_code": "owner_result_unobservable",
        }

        exit_code, final, evidence = self.run_main_with_cleanup_failure(blocked_result)

        self.assertEqual(exit_code, 1)
        self.assertEqual(final["verdict"], "INVALID_TEST_EXECUTION")
        self.assertEqual(final["reason_code"], "uv_cache_cleanup_unconfirmed")
        self.assertEqual(final["uv_cache_cleanup"], evidence["cleanup"])
        self.assertFalse(evidence["cleanup"]["confirmed_absent"])
        self.assertEqual(evidence["cleanup"]["error"], "synthetic cleanup denied")


if __name__ == "__main__":
    unittest.main(verbosity=2)
