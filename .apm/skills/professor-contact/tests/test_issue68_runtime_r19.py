"""PC68-R1 r29 合成输入观察及运行入口预检。

这些用例验证旧命令文字和事后文件读取不会再被当作逐次输入证据，
并验证正式入口会在检查评估服务或发送请求前停止。它们不构成 PC68-R1 验收。
"""
import importlib.util
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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


verify = load("verify_issue68_stage5_routing_r19")
entry = load("run_issue68_stage5_routing_r19_codex")


class TestIssue68RuntimeR25Preflight(unittest.TestCase):
    def test_command_text_and_repeated_calls_do_not_prove_consumed_input(self):
        packet = '{"email_pack":"owner-A.json","choices":[{"email_id":"a1"}]}'
        command = "python3 contact_state.py stage5-plan --packet " + packet

        rows, problem = verify.consumed_business_objects([
            {"id": "call-1", "command": command, "generation": "run-1",
             "thread": "owner-thread", "start": 1, "end": 2, "output": ""},
            {"id": "call-2", "command": command, "generation": "run-1",
             "thread": "owner-thread", "start": 3, "end": 4, "output": ""},
        ])

        self.assertEqual(rows, [])
        self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(problem["reason_code"], "owner_actual_input_unobservable")
        self.assertEqual(problem["missing_call_ids"], ["call-1", "call-2"])

    def test_choices_path_is_not_reopened_after_its_call(self):
        parsed = {
            "id": "call-7",
            "command": "python3 contact_state.py stage5-plan --choices /tmp/choices.json",
            "flags": {"--email-pack": "owner-A.json", "--choices": "/tmp/choices.json"},
            "generation": "run-1", "thread": "owner-thread", "start": 1, "end": 2,
            "output": "",
        }
        with mock.patch.object(Path, "read_text", side_effect=AssertionError("事后读取文件")) as read_text:
            problem = verify._plan_checks(parsed, {"owners": []}, "owner-A.json")

        read_text.assert_not_called()
        self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(problem["reason_code"], "owner_actual_input_unobservable")
        self.assertEqual(problem["missing_call_ids"], ["call-7"])

    def test_observed_wrong_owner_flag_remains_a_product_failure(self):
        parsed = {"command": "stage5-plan --email-pack wrong.json",
                  "flags": {"--email-pack": "wrong.json"}}

        problem = verify._plan_checks(parsed, {"owners": []}, "owner-A.json")

        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_directory_changed")

    def test_observed_choices_scope_flag_remains_a_product_failure(self):
        parsed = {"flags": {"--email-pack": "owner-A.json", "--choices-scope": "all"}}

        problem = verify._plan_checks(parsed, {"owners": []}, "owner-A.json")

        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_carries_choices_scope")

    def test_contract_records_the_r25_source_and_keeps_gate_two_incomplete(self):
        contract = entry.load_contract()
        observation = contract["codex"]["owner_business_input_observation"]

        self.assertEqual(contract["revision"], "issue-68-runtime-evidence-r29-2026-10-06")
        self.assertEqual(observation["status"], "blocked")
        self.assertEqual(observation["schema"], verify.OWNER_OBSERVATION_SCHEMA)
        self.assertEqual(observation["source"],
                         "output.app_server_events.commandExecution.aggregatedOutput")
        self.assertEqual(observation["handoff_path_binding"]["status"], "blocked")
        self.assertEqual(observation["handoff_path_binding"]["reason_code"],
                         "owner_handoff_input_path_unobservable")
        envelope = observation["envelope"]
        self.assertEqual(set(envelope), {
            "pc68_fixed_capture", "pc68_actual_input_observation", "stage5_invocation",
            "stage5_raw_stdout", "stage5_process", "stage5_plan", "return_code"})
        self.assertIn("capture_id", envelope["stage5_invocation"])
        self.assertIn("capture_id", envelope["stage5_process"])
        self.assertIn("wrapper_sha256", envelope["pc68_fixed_capture"])
        self.assertIn("stdout_sha256", envelope["stage5_process"])
        self.assertIn("stderr_sha256", envelope["stage5_process"])
        self.assertIn("commandExecution.command", observation[
            "independent_command_event_validation"])
        requirements = json.dumps(observation["verdicts"], ensure_ascii=False) + json.dumps(
            observation["excluded_as_input_proof"], ensure_ascii=False)
        for field in ("FAIL_PRODUCT", "BLOCKED_OBSERVABILITY", "INVALID_EVIDENCE", "调用结束后的文件内容"):
            self.assertIn(field, requirements)
        gate = contract["preflight"]["input_observation_gate"]
        self.assertEqual(gate["status"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(gate["reason_code"], "owner_handoff_input_path_unobservable")
        self.assertFalse(gate["formal_run_allowed"])
        self.assertFalse(contract["preflight"]["input_observation_gate"]["formal_run_allowed"])
        self.assertEqual(contract["preflight"]["second_gate_status"], "INCOMPLETE")
        self.assertEqual(len(contract["pc68_r1_steps"]), 7)
        runtime = contract["formal_runtime_environment"]
        self.assertEqual(runtime["required_facts"], list(entry.REQUIRED_RUNTIME_FACTS))
        self.assertEqual(set(runtime["actual_values"]), set(entry.REQUIRED_RUNTIME_FACTS))
        self.assertTrue(all(value is None for value in runtime["actual_values"].values()))
        self.assertIn("不是实际环境证明", runtime["actual_values_note"])
        self.assertIn("active Codex dispatch branch", runtime["fact_sources"]["executor"])
        self.assertIn("not the eval-server process", runtime["validation"])

    def test_contract_claim_alone_cannot_enable_the_runner(self):
        contract = entry.load_contract()
        contract["codex"]["owner_business_input_observation"] = {
            "status": "supported", "source": "unverified-placeholder"
        }

        gate = entry.actual_input_observation_preflight(contract)

        self.assertFalse(gate["ready"])
        self.assertEqual(gate["state"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(gate["reason_code"], "owner_handoff_input_path_unobservable")
        self.assertFalse(gate["service_preflight_allowed"])

    def test_arbitrary_supported_handoff_source_cannot_open_gate(self):
        contract = entry.load_contract()
        contract["codex"]["owner_business_input_observation"]["status"] = "supported"
        contract["codex"]["owner_business_input_observation"]["handoff_path_binding"] = {
            "status": "supported", "source": "unverified-claim:root-handoff-path"
        }
        contract["preflight"]["second_gate_status"] = "COMPLETE"
        contract["preflight"]["input_observation_gate"]["formal_run_allowed"] = True

        gate = entry.actual_input_observation_preflight(contract)

        self.assertFalse(gate["ready"])
        self.assertEqual(gate["state"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(gate["reason_code"], "owner_handoff_input_path_unobservable")
        self.assertEqual(gate["formal_run_block_reason"],
                         "owner_handoff_input_path_unobservable")
        self.assertFalse(gate["service_preflight_allowed"])

    def test_r25_observation_support_does_not_complete_gate_two(self):
        contract = entry.load_contract()

        gate = entry.actual_input_observation_preflight(contract)

        self.assertFalse(gate["ready"])
        self.assertEqual(gate["state"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(gate["reason_code"], "owner_handoff_input_path_unobservable")
        self.assertFalse(gate["formal_run_allowed"])
        self.assertIn("owner_handoff_input_path_unobservable", gate["formal_run_block_reasons"])
        self.assertIn("second_gate_incomplete", gate["formal_run_block_reasons"])
        self.assertGreater(len(gate["runtime_environment_missing"]), 0)
        self.assertFalse(gate["service_preflight_allowed"])
        self.assertEqual(gate["synthetic_capture"]["result"], "CAPTURED_SYNTHETIC_ONLY")
        self.assertEqual(gate["synthetic_capture"]["verifier_parser"], "consumed_business_objects")
        self.assertFalse(gate["synthetic_capture"]["app_server_aggregatedOutput_proven"])

    def test_gate_two_approval_cannot_bypass_unobservable_handoff_path(self):
        contract = entry.load_contract()
        contract["preflight"]["second_gate_status"] = "COMPLETE"
        contract["preflight"]["input_observation_gate"]["formal_run_allowed"] = True
        contract["formal_runtime_environment"]["optional_diagnostics"] = {}

        gate = entry.actual_input_observation_preflight(contract)

        self.assertFalse(gate["ready"])
        self.assertFalse(gate["service_preflight_allowed"])
        self.assertFalse(gate["formal_run_allowed"])
        self.assertEqual(gate["state"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(gate["formal_run_block_reason"], "owner_handoff_input_path_unobservable")

    def test_runtime_facts_are_collected_from_this_run_before_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            codex = output / "codex"
            codex.mkdir()
            script = codex / "contact_state.py"
            script.write_text("synthetic entrypoint", encoding="utf-8")
            entrypoint = {"script": str(script), "cwd": str(codex)}
            (codex / "installed-entrypoint.json").write_text(
                json.dumps(entrypoint), encoding="utf-8")
            (codex / "apm.lock.yaml").write_text("synthetic lock", encoding="utf-8")
            request = {"command": "codex --model synthetic-model --timeout 900", "timeout": 900}
            (codex / "codex-request.json").write_text(json.dumps(request), encoding="utf-8")
            service = {
                "eval_server": {"sha": "synthetic-service-sha", "dirty": "no"},
                "service": {"command": "python eval_server.py --port 4812", "port": "4812",
                            "pid": 17, "start_time": "synthetic-start", "cwd": str(output)},
                "storage": {"status": "ISOLATION_CONFIRMED", "codex_home": str(output / "test-codex")},
            }
            (output / "eval-service-provenance.before.json").write_text(
                json.dumps(service), encoding="utf-8")
            preflight = {
                "service_preflight_allowed": True,
                "runtime_environment_facts": {key: None for key in entry.REQUIRED_RUNTIME_FACTS},
                "runtime_environment_evidence": {},
            }
            preflight = entry._record_service_runtime_facts(preflight, service)
            producer = {"sha": "synthetic-producer-sha", "dirty": "no"}
            fixture = {"sha": "synthetic-fixture-sha", "dirty": "no"}

            captured = entry._record_request_runtime_facts(
                preflight, output, request, service, producer, fixture)

            self.assertTrue(captured["formal_run_allowed"])
            facts = captured["runtime_environment_facts"]
            self.assertEqual(facts["model"], "synthetic-model")
            self.assertEqual(facts["service_version"], "synthetic-service-sha")
            self.assertEqual(facts["entrypoint"]["sha256"], entry._sha256_file(script))
            self.assertEqual(facts["shared_assets"]["fixture_revision"], "synthetic-fixture-sha")
            self.assertEqual(facts["isolation"], service["storage"])
            executor = facts["executor"]
            self.assertEqual(executor["execution_branch"], "codex")
            self.assertTrue(executor["dispatcher"].endswith(".codex_host"))
            self.assertTrue(executor["source_evidence"])
            self.assertNotIn("pid", executor)
            self.assertNotIn("command", executor)
            self.assertNotIn("port", executor)
            self.assertEqual(set(captured["runtime_environment_evidence"]),
                             set(entry.REQUIRED_RUNTIME_FACTS))

    def test_live_service_version_is_read_and_change_fails_before_service_inspection(self):
        root = Path("/synthetic/eval-server")
        service = {"sha": "synthetic-current-sha", "dirty": "no"}
        instance = {"command": "python eval_server.py --port 4812", "port": "4812",
                    "pid": 17, "start_time": "synthetic-start", "cwd": str(root)}
        storage = {"status": "ISOLATION_CONFIRMED"}
        with mock.patch.object(entry.subprocess, "check_output", return_value="synthetic-current-sha\n") as git, \
                mock.patch.object(entry.base, "clean_revision", return_value=service) as clean, \
                mock.patch.object(entry, "resolve_eval_port", return_value="4812"), \
                mock.patch.object(entry, "capture_service_instance", return_value=instance), \
                mock.patch.object(entry.isolation, "capture_storage_isolation", return_value=storage):
            snapshot = entry.capture_eval_service_provenance(root)
        self.assertEqual(snapshot["eval_server"]["sha"], "synthetic-current-sha")
        git.assert_called_once_with(["git", "rev-parse", "HEAD"], cwd=root, text=True)
        clean.assert_called_once_with(root, "synthetic-current-sha")

        with mock.patch.object(entry.subprocess, "check_output", return_value="synthetic-new-sha\n"), \
                mock.patch.object(entry.base, "clean_revision",
                                  side_effect=ValueError("wrong_revision_or_dirty_checkout")) as clean, \
                mock.patch.object(entry, "resolve_eval_port") as port:
            with self.assertRaisesRegex(ValueError, "wrong_revision_or_dirty_checkout"):
                entry.capture_eval_service_provenance(root, expected_revision="synthetic-old-sha")
        clean.assert_called_once_with(root, "synthetic-old-sha")
        port.assert_not_called()

    def test_synthetic_file_preflight_captures_stdout_and_verifier_reparses_it(self):
        script = RUNTIME / "preflight_issue68_owner_input_observation_r29.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "manifest.json"
            stdout_capture = root / "stdout.json"
            command_record = "uv run python synthetic-preflight.py | tee stdout.json"
            result = subprocess.run(
                ["uv", "--offline", "--cache-dir", "/private/tmp/issue68-uv-cache",
                 "run", "python", str(script), "--artifact", str(artifact),
                 "--stdout-capture", str(stdout_capture), "--command-record", command_record],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            stdout_capture.write_text(result.stdout, encoding="utf-8")
            manifest = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(manifest["owner_input_read_count"], 1)
            self.assertEqual(manifest["parsed_object"], manifest["observation_object"])
            self.assertEqual(manifest["fixed_capture_verification"]["state"], "PASS")
            self.assertEqual(manifest["portable_path_normalization"]["state"],
                             "VERIFIED_THEN_NORMALIZED")
            self.assertTrue(manifest["captured_stdout_sha256"])
            self.assertTrue(manifest["captured_parsed_object_sha256"])
            self.assertNotIn("/Users/", json.dumps(manifest, ensure_ascii=False))
            self.assertNotIn("/var/folders/", json.dumps(manifest, ensure_ascii=False))
            self.assertNotIn("/private/var/folders/", json.dumps(manifest, ensure_ascii=False))
            self.assertNotIn(".local/share/uv/python", json.dumps(manifest, ensure_ascii=False))
            self.assertIn("/__pc68_synthetic__/", json.dumps(manifest, ensure_ascii=False))
            self.assertEqual(manifest["fixed_capture_verification"]["verifier"],
                             "consumed_business_objects")
            self.assertEqual(manifest["capture_command_argv"][:4],
                             ["uv", "run", "--no-project", "python"])
            self.assertTrue(any(Path(token).name == verifier.OWNER_CAPTURE_NAME
                                for token in manifest["capture_command_argv"]))
            plan = manifest["producer_structured_output"]
            self.assertEqual(manifest["result"], "CAPTURED_SYNTHETIC_ONLY")
            self.assertEqual(manifest["producer_return_code"], 0)
            self.assertEqual(plan["status"], "ok")
            self.assertEqual(plan["email_pack"], manifest["parsed_object"]["email_pack"])
            self.assertEqual(plan["emails"], [manifest["parsed_object"]["email_id"]])
            self.assertEqual(plan["output_mode"], "first")
            self.assertEqual(plan["needs_recheck_professors"], ["合成教授"])
            self.assertTrue(plan["verify"]["合成教授"].startswith("needs_recheck:"))
            self.assertEqual(len(plan["jobs"]), 1)
            self.assertEqual(plan["jobs"][0]["job_id"], "email:" + plan["emails"][0])
            self.assertIsInstance(plan["jobs"][0]["model_input"], dict)
            with mock.patch.object(entry, "PREFLIGHT_MANIFEST", artifact), \
                    mock.patch.object(entry, "PREFLIGHT_STDOUT", stdout_capture):
                checked, problem = entry._synthetic_capture_preflight()
            self.assertIsNone(problem)
            self.assertEqual(checked["stdout_sha256"], manifest["stdout_sha256"])
            self.assertTrue(manifest["synthetic_correlation"]["is_synthetic"])

    def test_machine_terminal_mapping_covers_states_and_conflicts(self):
        contract = entry.load_contract()
        mapping = contract["machine_terminal_mapping"]
        aggregation = contract["terminal_aggregation"]
        for machine_state, expected_terminal in mapping.items():
            self.assertEqual(verify.formal_terminal(machine_state), expected_terminal,
                             machine_state)
        self.assertNotIn("conflict_priority", mapping)
        self.assertEqual(aggregation["confirmed_failure_machine_state"], "FAIL_PRODUCT")
        self.assertEqual(aggregation["confirmed_failure_formal_terminal"], "FAIL")
        self.assertEqual(verify.formal_terminal("unrecognized-status"), "INVALID_TEST_EXECUTION")
        mixed = verify.combine_formal_terminals({
            "教授甲": "BLOCKED_OBSERVABILITY",
            "教授乙": "INVALID_EVIDENCE",
            "教授丙": "CASE_NOT_STARTED",
        })
        self.assertIsNone(mixed["overall_terminal"])
        self.assertFalse(mixed["confirmed_product_failure"])
        self.assertEqual(mixed["children"], [
            {"child": "教授甲", "machine_state": "BLOCKED_OBSERVABILITY",
             "formal_terminal": "BLOCKED"},
            {"child": "教授乙", "machine_state": "INVALID_EVIDENCE",
             "formal_terminal": "INVALID_TEST_EXECUTION"},
            {"child": "教授丙", "machine_state": "CASE_NOT_STARTED",
             "formal_terminal": "CASE_NOT_STARTED"},
        ])
        early_stop = verify.combine_formal_terminals({
            "教授甲": "PASS", "教授乙": "NOT_TESTED",
        })
        self.assertIsNone(early_stop["overall_terminal"])
        self.assertEqual([row["formal_terminal"] for row in early_stop["children"]],
                         ["PASS", "NOT TESTED"])
        proven_failure = verify.combine_formal_terminals({
            "教授甲": "FAIL_PRODUCT", "教授乙": "BLOCKED_OBSERVABILITY",
            "教授丙": "INVALID_EVIDENCE",
        })
        self.assertEqual(proven_failure["overall_terminal"], "FAIL")
        self.assertTrue(proven_failure["confirmed_product_failure"])
        self.assertEqual([row["formal_terminal"] for row in proven_failure["children"]],
                         ["FAIL", "BLOCKED", "INVALID_TEST_EXECUTION"])

    def test_formal_entry_stops_before_service_inspection_or_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "output"
            args = SimpleNamespace(
                producer_root=root / "producer",
                fixture_root=root / "fixture",
                eval_direnv_root=root / "eval-server",
                output_dir=output,
                fixture_sha=entry.FIXTURE_SHA,
            )
            with mock.patch.object(entry, "pin"), \
                    mock.patch.object(entry, "parse_args", return_value=args), \
                    mock.patch.object(entry, "overlaps", return_value=False), \
                    mock.patch.object(entry, "check_entry_uniqueness", return_value=True), \
                    mock.patch.object(entry.signal, "signal"), \
                    mock.patch.object(entry.base, "stop_active"), \
                    mock.patch.object(entry.base, "progress"), \
                    mock.patch.object(entry.base, "clean_revision") as clean_revision, \
                    mock.patch.object(entry, "capture_eval_service_provenance") as service, \
                    mock.patch.object(entry.base, "codex_host") as codex_host:
                result = entry.main([])

            self.assertEqual(result, 1)
            self.assertEqual(json.loads((output / "final-verdict.json").read_text())["state"],
                             "CASE_NOT_STARTED")
            self.assertEqual(json.loads((output / "final-verdict.json").read_text())["reason_code"],
                             "owner_handoff_input_path_unobservable")
            self.assertFalse(json.loads((output / "input-evidence-preflight.json").read_text())["ready"])
            self.assertEqual(json.loads((output / "input-evidence-preflight.json").read_text())[
                "state"], "BLOCKED_OBSERVABILITY")
            self.assertFalse(json.loads((output / "input-evidence-preflight.json").read_text())["formal_run_allowed"])
            clean_revision.assert_not_called()
            service.assert_not_called()
            codex_host.assert_not_called()
#!/usr/bin/env python3
"""Synthetic r25 checks for PC68-R1 per-call input observation."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"
sys.path.insert(0, str(RUNTIME))
import verify_issue68_stage5_routing_r19 as verifier


class OwnerObservationTests(unittest.TestCase):
    """Synthetic evidence must execute the pinned wrapper through the real CLI."""
    def setUp(self):
        import shutil
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "program"
        self.prof = self.root / "教授研究" / "X分野" / "甲教授"
        self.prof.mkdir(parents=True)
        self.pack = self.prof / "邮件输入.json"
        self.template = self.root / "template.md"
        self.template.write_text("synthetic template", encoding="utf-8")
        self.email = {"email_id": "D001::I001", "professor": "甲教授",
                      "professor_dir": str(self.prof),
                      "idea": {"id": "D001_1", "text": "合成研究构想"},
                      "direction_ids": ["D001"], "directions": [{"id": "D001", "name": "合成方向"}],
                      "user_note": "用户输入", "papers": [{"item_key": "P001", "title": "合成论文"}],
                      "gaps": [], "red_lines": [{"text": "不得编造"}],
                      "soft_materials": {"positioning": [{"text": "定位事实"}]},
                      "user_supplement": "补充事实", "allowed_sources": ["idea:D001_1"]}
        self.pack.write_text(json.dumps({"schema": 3, "kind": "professor-contact-email-input",
                                         "professor": "甲教授", "professor_dir": str(self.prof),
                                         "emails": [self.email]}, ensure_ascii=False), encoding="utf-8")
        self.packet = {"program_root": str(self.root), "professor_dir": str(self.prof),
                       "email_pack": str(self.pack), "email_id": self.email["email_id"],
                       "choices": [{"email_id": self.email["email_id"], "first_choice": True}],
                       "mode": "first", "template": str(self.template),
                       "result": str(self.root / "raw.json")}
        self.handoff_file = self.root / "owner-input.json"
        self.handoff_file.write_text(json.dumps(self.packet, ensure_ascii=False), encoding="utf-8")
        self.consumer = Path(self.temp.name) / "consumer"
        self.consumer.mkdir()
        self.entrypoint = self.consumer / ".agents/skills/professor-contact/scripts/contact_state.py"
        self.entrypoint.parent.mkdir(parents=True)
        source_entrypoint = RUNTIME.parent.parent / "scripts/contact_state.py"
        shutil.copy2(source_entrypoint, self.entrypoint)
        self.entrypoint = self.entrypoint.resolve()
        self.wrapper = self.consumer / ".pc68-test-support" / verifier.OWNER_CAPTURE_NAME
        self.wrapper.parent.mkdir()
        shutil.copy2(verifier.OWNER_CAPTURE_SOURCE, self.wrapper)
        self.command_argv = ["uv", "run", "--no-project", "python", str(self.wrapper),
                             "--action", "stage5-plan", "--owner-input-file",
                             str(self.handoff_file), "--contact-state", str(self.entrypoint)]
        self.manifest = {"program_root": str(self.root), "owners": [{
            "professor": "甲教授", "professor_dir": str(self.prof), "email_pack": str(self.pack),
            "email_ids": [self.email["email_id"]], "result": str(self.root / "raw.json"),
            "expected_choices_rows": self.packet["choices"],
            "sibling_exclusions": ["乙教授", "sibling-pack", "choices_scope"],
        }], "pre_run_hashes": {str(self.pack): hashlib.sha256(self.pack.read_bytes()).hexdigest()}}
        artifact = Path(self.temp.name) / "fixture-manifest.json"
        self.manifest["owner_capture"] = {
            "consumer_root": str(self.consumer), "runtime_path": str(self.wrapper),
            "installed_entrypoint": str(self.entrypoint),
            "entrypoint_sha256": hashlib.sha256(self.entrypoint.read_bytes()).hexdigest(),
            "source_path": str(verifier.OWNER_CAPTURE_SOURCE),
            "source_sha256": verifier.OWNER_CAPTURE_SHA256,
            "runtime_sha256": hashlib.sha256(self.wrapper.read_bytes()).hexdigest(),
            "manifest_path": str(artifact),
        }
        artifact.write_text(json.dumps(self.manifest), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

    def call(self, *, call_id="cmd-1", command=None):
        completed = subprocess.run(self.command_argv, cwd=self.consumer, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return {"id": call_id, "generation": "synthetic-run", "thread": "synthetic-owner",
                "start": 1, "end": 2, "command": command or shlex.join(self.command_argv),
                "output": completed.stdout}

    def test_fixed_capture_executes_same_parse_and_cli_then_survives_handoff_cleanup(self):
        call = self.call()
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertIsNone(problem)
        self.assertEqual(rows[0]["packet"], self.packet)
        self.handoff_file.unlink()
        owner_pack, problem = verifier.owner_payload(rows, self.manifest)
        self.assertIsNone(problem)
        self.assertEqual(owner_pack, str(self.pack))

    def test_echoed_valid_envelope_without_fixed_capture_command_is_invalid(self):
        call = self.call()
        call["command"] = "echo stage5-plan " + shlex.quote(call["output"])
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertEqual(rows, [])
        self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")
        self.assertEqual(problem["reason_code"], "owner_fixed_capture_command_missing")

    def test_capture_call_binding_mismatch_is_invalid(self):
        call = self.call()
        envelope = json.loads(call["output"])
        envelope["stage5_process"]["capture_id"] = "00000000-0000-4000-8000-000000000000"
        call["output"] = json.dumps(envelope, ensure_ascii=False)
        _, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")

    def test_absent_invocation_is_blocked_but_present_bad_argv_is_invalid(self):
        call = self.call()
        envelope = json.loads(call["output"])
        del envelope["stage5_invocation"]
        call["output"] = json.dumps(envelope, ensure_ascii=False)
        _, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(problem["reason_code"], "owner_stage5_invocation_unobservable")

        call = self.call()
        envelope = json.loads(call["output"])
        envelope["stage5_invocation"] = {"capture_id": envelope["stage5_invocation"]["capture_id"]}
        call["output"] = json.dumps(envelope, ensure_ascii=False)
        _, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")
        self.assertEqual(problem["reason_code"], "owner_stage5_invocation_invalid")

    def test_null_email_pack_is_a_product_failure(self):
        rows, problem = verifier.consumed_business_objects([self.call()], self.manifest)
        self.assertIsNone(problem)
        rows[0]["plan"]["email_pack"] = None
        _, problem = verifier.owner_payload(rows, self.manifest)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_directory_changed")

    def test_first_plan_missing_jobs_or_status_is_a_product_failure(self):
        for field in ("jobs", "status"):
            with self.subTest(field=field):
                rows, problem = verifier.consumed_business_objects([self.call()], self.manifest)
                self.assertIsNone(problem)
                del rows[0]["plan"][field]
                _, problem = verifier.owner_payload(rows, self.manifest)
                self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
                self.assertEqual(problem["reason_code"], "owner_initial_plan_fields_missing")
                self.assertIn(field, problem["missing_fields"])


if __name__ == "__main__":
    unittest.main()
