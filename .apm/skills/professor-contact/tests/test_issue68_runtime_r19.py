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
command_event_binder = load("bind_issue68_preflight_command_event_r29")


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

        self.assertEqual(contract["revision"], entry.CONTRACT_REVISION)
        self.assertEqual(observation["status"], "supported")
        self.assertEqual(observation["schema"], verify.OWNER_OBSERVATION_SCHEMA)
        self.assertEqual(observation["source"],
                         "output.app_server_events.commandExecution.aggregatedOutput")
        self.assertNotIn("handoff_path_binding", observation)
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
        self.assertEqual(gate["status"], "READY_FOR_GATE2_REVIEW")
        self.assertEqual(gate["reason_code"], "second_gate_incomplete")
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
        self.assertIn("执行器取实际编码分支及源摘要", runtime["validation"])
        self.assertIn("不取监听进程或主机编号", runtime["validation"])

    def test_contract_claim_alone_cannot_enable_the_runner(self):
        contract = entry.load_contract()
        contract["codex"]["owner_business_input_observation"] = {
            "status": "supported", "source": "unverified-placeholder"
        }

        gate = entry.actual_input_observation_preflight(contract)

        self.assertFalse(gate["ready"])
        self.assertEqual(gate["state"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(gate["reason_code"], "actual_input_evidence_source_unavailable")
        self.assertFalse(gate["service_preflight_allowed"])

    def test_observation_support_does_not_complete_gate_two(self):
        contract = entry.load_contract()

        gate = entry.actual_input_observation_preflight(contract)

        self.assertTrue(gate["ready"])
        self.assertEqual(gate["state"], "OBSERVATION_SOURCE_SUPPORTED")
        self.assertIsNone(gate["reason_code"])
        self.assertEqual(gate["formal_run_block_reason"], "second_gate_incomplete")
        self.assertIn("second_gate_incomplete", gate["formal_run_block_reasons"])
        self.assertFalse(gate["service_preflight_allowed"])

    def test_r25_observation_support_does_not_complete_gate_two(self):
        contract = entry.load_contract()

        gate = entry.actual_input_observation_preflight(contract)

        self.assertTrue(gate["ready"])
        self.assertEqual(gate["state"], "OBSERVATION_SOURCE_SUPPORTED")
        self.assertIsNone(gate["reason_code"])
        self.assertFalse(gate["formal_run_allowed"])
        self.assertIn("second_gate_incomplete", gate["formal_run_block_reasons"])
        self.assertGreater(len(gate["runtime_environment_missing"]), 0)
        self.assertFalse(gate["service_preflight_allowed"])
        capture = gate["synthetic_capture"]
        self.assertEqual(capture["result"], "CAPTURED_SYNTHETIC_WITH_ACTUAL_COMMAND_EVENT")
        self.assertEqual(capture["verifier_parser"], "same_object_invocation_and_plan")
        self.assertTrue(capture["ordinary_commandExecution_output_proven"])
        self.assertTrue(capture["commandExecution_id"])
        self.assertTrue(capture["thread_id"])
        self.assertIsInstance(capture["turn_index"], int)
        self.assertIsInstance(capture["item_index"], int)

    def test_gate_two_approval_allows_next_preflight_after_observation_check(self):
        contract = entry.load_contract()
        contract["preflight"]["second_gate_status"] = "COMPLETE"
        contract["preflight"]["input_observation_gate"]["formal_run_allowed"] = True

        gate = entry.actual_input_observation_preflight(contract)

        self.assertTrue(gate["ready"])
        self.assertTrue(gate["service_preflight_allowed"])
        self.assertFalse(gate["formal_run_allowed"])
        self.assertEqual(gate["state"], "OBSERVATION_SOURCE_SUPPORTED")
        self.assertEqual(gate["formal_run_block_reason"], "runtime_environment_capture_pending")

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

    def test_synthetic_file_preflight_waits_for_an_ordinary_command_event(self):
        script = RUNTIME / "preflight_issue68_owner_input_observation_r29.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "manifest.json"
            stdout_capture = root / "stdout.json"
            result = subprocess.run(
                ["uv", "--offline", "--cache-dir", "/private/tmp/issue68-uv-cache",
                 "run", "python", str(script), "--artifact", str(artifact),
                 "--stdout-capture", str(stdout_capture)],
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
                             "same_object_invocation_and_plan")
            self.assertEqual(manifest["capture_command_argv"][:4],
                             ["uv", "run", "--no-project", "python"])
            self.assertTrue(any(Path(token).name == verifier.OWNER_CAPTURE_NAME
                                for token in manifest["capture_command_argv"]))
            plan = manifest["producer_structured_output"]
            self.assertEqual(manifest["result"], "CAPTURED_SYNTHETIC_PENDING_COMMAND_EVENT")
            self.assertEqual(manifest["ordinary_command_event"]["state"], "PENDING_EXTERNAL_CAPTURE")
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
            self.assertIsNone(checked)
            self.assertEqual(problem["state"], "BLOCKED_OBSERVABILITY")
            self.assertEqual(problem["reason_code"], "ordinary_command_event_missing")

    def test_actual_command_event_binding_supplies_gate_evidence(self):
        script = RUNTIME / "preflight_issue68_owner_input_observation_r29.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "manifest.json"
            stdout_capture = root / "stdout.json"
            result = subprocess.run(
                ["uv", "--offline", "--cache-dir", "/private/tmp/issue68-uv-cache",
                 "run", "python", str(script), "--artifact", str(artifact),
                 "--stdout-capture", str(stdout_capture)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            stdout_capture.write_text(result.stdout, encoding="utf-8")
            command = shlex.join(["uv", "run", "python", str(script), "--artifact", str(artifact),
                                  "--stdout-capture", str(stdout_capture)])
            bundle = {
                "schema": "issue68-r29-command-event-source-v1",
                "source": "mcp__codex_app__read_thread",
                "context": {"thread_id": "test-thread", "turn_id": "test-turn",
                            "turn_index": 0, "item_index": 1},
                "event": {"type": "commandExecution", "id": "unit-command-event",
                          "command": command, "cwd": str(command_event_binder.REPO_ROOT),
                          "status": "completed", "exitCode": 0,
                          "output": {"text": result.stdout, "truncated": False}},
            }
            raw_event = root / "raw-command-event.json"
            raw_event.write_text(json.dumps(bundle), encoding="utf-8")
            command_event_binder.bind(raw_event, artifact, stdout_capture)
            manifest = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(manifest["ordinary_command_event"]["status"], "VERIFIED")
            self.assertEqual(manifest["ordinary_command_event"]["source"], "mcp__codex_app__read_thread")
            with mock.patch.object(entry, "PREFLIGHT_MANIFEST", artifact), \
                    mock.patch.object(entry, "PREFLIGHT_STDOUT", stdout_capture):
                checked, problem = entry._synthetic_capture_preflight()
            self.assertIsNone(problem)
            self.assertEqual(checked["result"], "CAPTURED_SYNTHETIC_WITH_ACTUAL_COMMAND_EVENT")
            self.assertEqual(checked["ordinary_command_event"]["commandExecution_id"],
                             "unit-command-event")

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
                             "second_gate_incomplete")
            self.assertTrue(json.loads((output / "input-evidence-preflight.json").read_text())["ready"])
            self.assertEqual(json.loads((output / "input-evidence-preflight.json").read_text())[
                "state"], "OBSERVATION_SOURCE_SUPPORTED")
            self.assertFalse(json.loads((output / "input-evidence-preflight.json").read_text())["formal_run_allowed"])
            clean_revision.assert_not_called()
            service.assert_not_called()
            codex_host.assert_not_called()
#!/usr/bin/env python3
"""Synthetic r25 checks for PC68-R1 per-call input observation."""
import hashlib
import copy
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
        # Independent expectations and synthetic current-run root return are
        # separate objects; neither is reconstructed from the professor read.
        expected = {"professor_dir": str(self.prof), "email_pack": str(self.pack),
                    "email_id": self.email["email_id"], "status": "ok",
                    "choices_rows": copy.deepcopy(self.packet["choices"])}
        self.manifest["partition"] = {"owners": [expected]}
        self.actual_partition = copy.deepcopy([expected])
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

    def rewrite_plan(self, call, update):
        envelope = json.loads(call["output"])
        plan = envelope["stage5_plan"]
        update(plan)
        raw_stdout = json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
        envelope["stage5_raw_stdout"] = raw_stdout
        envelope["stage5_process"]["stdout_sha256"] = hashlib.sha256(
            raw_stdout.encode("utf-8")).hexdigest()
        call["output"] = json.dumps(envelope, ensure_ascii=False)
        return call

    def write_packet(self, update):
        packet = json.loads(self.handoff_file.read_text(encoding="utf-8"))
        update(packet)
        self.handoff_file.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
        return self.call()

    def judge_owner(self, rows):
        return verifier.owner_payload(rows, self.manifest, self.actual_partition)

    def add_second_email(self):
        second = copy.deepcopy(self.email)
        second["email_id"] = "D002::I002"
        second["idea"] = {"id": "D002_2", "text": "第二封构想"}
        value = json.loads(self.pack.read_text(encoding="utf-8"))
        value["emails"].append(second)
        self.pack.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        self.manifest["owners"][0]["email_ids"].append(second["email_id"])
        self.manifest["pre_run_hashes"][str(self.pack)] = hashlib.sha256(self.pack.read_bytes()).hexdigest()
        Path(self.manifest["owner_capture"]["manifest_path"]).write_text(
            json.dumps(self.manifest), encoding="utf-8")
        return second

    def test_partition_comparison_includes_pack_and_optional_target(self):
        expected = {"professor_dir": str(self.prof), "status": "ok",
                    "email_pack": str(self.pack), "choices_rows": self.packet["choices"]}
        for field, value in (("email_pack", "wrong-pack"), ("email_id", "different-id")):
            changed = dict(expected, **{field: value})
            with self.subTest(field=field):
                self.assertNotEqual(verifier._owner_projection(expected),
                                    verifier._owner_projection(changed))

    def test_targeted_plan_jobs_only_cover_selected_email(self):
        self.add_second_email()
        rows, problem = verifier.consumed_business_objects([self.call()], self.manifest)
        self.assertIsNone(problem)
        self.assertIsNone(verifier._verify_owner_plan_package(rows, self.manifest["owners"][0],
                                                            self.manifest))

    def test_duplicate_jobs_cannot_hide_missing_batch_email(self):
        self.add_second_email()
        call = self.write_packet(lambda packet: packet.pop("email_id"))
        call = self.rewrite_plan(call, lambda plan: plan["jobs"].__setitem__(
            1, copy.deepcopy(plan["jobs"][0])))
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertIsNone(problem)
        problem = verifier._verify_owner_plan_package(rows, self.manifest["owners"][0], self.manifest)
        self.assertIsNotNone(problem)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_email_ids_changed")

    def partition_call(self, owners=None):
        return {"id": "partition-1", "generation": "synthetic-run", "thread": "synthetic-root",
                "start": 0, "end": 1,
                "command": shlex.join(["uv", "run", "python", str(self.entrypoint),
                                       "stage5-partition-choices", "--program-root", str(self.root),
                                       "--owner", str(self.pack), "--choices", str(self.root / "choices.json")]),
                "output": json.dumps({"status": "ok", "owners": owners if owners is not None
                                      else self.actual_partition}, ensure_ascii=False)}

    def test_current_root_return_is_the_source_of_owner_comparison(self):
        actual, problem = verifier._actual_root_partition([self.partition_call()], self.manifest,
                                                         "synthetic-root")
        self.assertIsNone(problem)
        call = self.call()
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertIsNone(problem)
        self.handoff_file.unlink()
        pack, problem = verifier.owner_payload(rows, self.manifest, actual["owners"])
        self.assertIsNone(problem)
        self.assertEqual(pack, str(self.pack))
        # The packet still equals preparation expectations, but contradicts
        # the previous actual step. This must never be accepted on that basis.
        for field, value, reason in (
                ("choices_rows", [{"email_id": self.email["email_id"], "first_choice": False}],
                 "owner_bundle_choices_changed"),
                ("email_pack", str(self.prof / "different-pack.json"), "owner_pack_changed_from_partition"),
                ("email_id", None, "owner_target_changed_from_partition")):
            changed = copy.deepcopy(actual["owners"])
            changed[0][field] = value
            with self.subTest(field=field):
                _, problem = verifier.owner_payload(rows, self.manifest, changed)
                self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
                self.assertEqual(problem["reason_code"], reason)

    def test_root_actual_return_compares_complete_independent_expectations(self):
        for field, value in (("email_pack", "wrong-pack"), ("email_id", "wrong-id"),
                             ("choices_rows", [])):
            changed = copy.deepcopy(self.actual_partition)
            changed[0][field] = value
            with self.subTest(field=field):
                _, problem = verifier._actual_root_partition([self.partition_call(changed)],
                                                             self.manifest, "synthetic-root")
                self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
                self.assertEqual(problem["reason_code"], "root_partition_changed")

    def test_missing_damaged_and_conflicting_root_returns_have_distinct_terminals(self):
        cases = [("", "BLOCKED_OBSERVABILITY", "root_partition_result_unobservable"),
                 ('{"status":', "INVALID_EVIDENCE", "root_partition_result_malformed"),
                 (json.dumps({"status": "ok", "owners": self.actual_partition * 2}),
                  "INVALID_EVIDENCE", "root_partition_owner_association_conflict")]
        for output, terminal, reason in cases:
            call = self.partition_call()
            call["output"] = output
            with self.subTest(reason=reason):
                actual, problem = verifier._actual_root_partition([call], self.manifest, "synthetic-root")
                self.assertIsNone(actual)
                self.assertEqual(problem["verdict"], terminal)
                self.assertEqual(problem["reason_code"], reason)
        rows, problem = verifier.consumed_business_objects([self.call()], self.manifest)
        self.assertIsNone(problem)
        _, problem = verifier.owner_payload(rows, self.manifest)
        self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")

    def test_repeated_partition_call_ids_are_invalid_not_multiple_business_calls(self):
        call = self.partition_call()
        _, problem = verifier._actual_root_partition([call, copy.deepcopy(call)], self.manifest,
                                                     "synthetic-root")
        self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")
        self.assertEqual(problem["reason_code"], "root_partition_call_association_invalid")
        second = copy.deepcopy(call)
        second.update(id="partition-2", start=2, end=3)
        _, problem = verifier._actual_root_partition([call, second], self.manifest, "synthetic-root")
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "multiple_root_partitions")

    def test_attributable_failed_partition_is_product_failure(self):
        call = self.partition_call()
        call["output"] = json.dumps({"status": "error", "reason_code": "synthetic-error"})
        _, problem = verifier._actual_root_partition([call], self.manifest, "synthetic-root")
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "root_partition_not_deterministic")

    def test_real_cli_output_wrong_pack_is_product_failure_but_forged_argv_is_invalid(self):
        # Same valid observed input and capture metadata; an inconsistent
        # business return is attributable to the product output.
        call = self.rewrite_plan(self.call(), lambda plan: plan.__setitem__(
            "email_pack", str(self.prof / "other-pack.json")))
        _, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_directory_changed")
        # The pinned wrapper constructs argv from the same parse. Altering
        # only this record cannot be a valid execution of that wrapper.
        for flag, value in (("--email-pack", "other-pack.json"), ("--email-id", "changed-id")):
            call = self.call()
            envelope = json.loads(call["output"])
            argv = envelope["stage5_invocation"]["argv"]
            argv[argv.index(flag) + 1] = value
            call["output"] = json.dumps(envelope)
            with self.subTest(flag=flag):
                _, problem = verifier.consumed_business_objects([call], self.manifest)
                self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")
                self.assertEqual(problem["reason_code"], "owner_capture_child_argv_binding_mismatch")

    def test_fixed_capture_executes_same_parse_and_cli_then_survives_handoff_cleanup(self):
        call = self.call()
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertIsNone(problem)
        self.assertEqual(rows[0]["packet"], self.packet)
        self.handoff_file.unlink()
        owner_pack, problem = self.judge_owner(rows)
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
        _, problem = self.judge_owner(rows)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_directory_changed")

    def test_observed_input_choices_different_from_allocation_are_a_product_failure(self):
        call = self.write_packet(lambda packet: packet["choices"].__setitem__(
            0, {"email_id": self.email["email_id"], "first_choice": False}))
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertIsNone(problem)
        _, problem = self.judge_owner(rows)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_bundle_choices_changed")

    def test_wrong_initial_plan_email_ids_are_a_product_failure(self):
        call = self.rewrite_plan(self.call(), lambda plan: plan.__setitem__("emails", ["D999::I999"]))
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertIsNone(problem)
        _, problem = self.judge_owner(rows)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_email_ids_changed")

    def test_wrong_initial_plan_business_data_are_a_product_failure(self):
        def change_idea(plan):
            plan["jobs"][0]["model_input"]["idea"]["text"] = "不属于该邮件包的构想"

        call = self.rewrite_plan(self.call(), change_idea)
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertIsNone(problem)
        _, problem = self.judge_owner(rows)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_business_data_changed")

    def test_sibling_business_data_in_the_observed_input_are_a_product_failure(self):
        call = self.write_packet(lambda packet: packet.__setitem__("sibling_data", "乙教授"))
        rows, problem = verifier.consumed_business_objects([call], self.manifest)
        self.assertIsNone(problem)
        _, problem = self.judge_owner(rows)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_input_contains_sibling_data")

    def test_first_plan_missing_jobs_or_status_is_a_product_failure(self):
        for field in ("jobs", "status"):
            with self.subTest(field=field):
                rows, problem = verifier.consumed_business_objects([self.call()], self.manifest)
                self.assertIsNone(problem)
                del rows[0]["plan"][field]
                _, problem = self.judge_owner(rows)
                self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
                self.assertEqual(problem["reason_code"], "owner_initial_plan_fields_missing")
                self.assertIn(field, problem["missing_fields"])


if __name__ == "__main__":
    unittest.main()
