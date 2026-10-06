"""PC68-R1 r25 合成输入观察及运行入口预检。

这些用例验证旧命令文字和事后文件读取不会再被当作逐次输入证据，
并验证正式入口会在检查评估服务或发送请求前停止。它们不构成 PC68-R1 验收。
"""
import importlib.util
import json
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

        self.assertEqual(contract["revision"], "issue-68-runtime-evidence-r25-2026-10-06")
        self.assertEqual(observation["status"], "supported")
        self.assertEqual(observation["schema"], verify.OWNER_OBSERVATION_SCHEMA)
        self.assertEqual(observation["source"],
                         "output.app_server_events.commandExecution.aggregatedOutput")
        requirements = json.dumps(observation["verdicts"], ensure_ascii=False) + json.dumps(
            observation["excluded_as_input_proof"], ensure_ascii=False)
        for field in ("FAIL_PRODUCT", "BLOCKED_OBSERVABILITY", "INVALID_EVIDENCE", "调用结束后的文件内容"):
            self.assertIn(field, requirements)
        self.assertFalse(contract["preflight"]["input_observation_gate"]["formal_run_allowed"])
        self.assertEqual(contract["preflight"]["second_gate_status"], "INCOMPLETE")

    def test_contract_claim_alone_cannot_enable_the_runner(self):
        contract = entry.load_contract()
        contract["codex"]["owner_business_input_observation"] = {
            "status": "supported", "source": "unverified-placeholder"
        }

        gate = entry.actual_input_observation_preflight(contract)

        self.assertFalse(gate["ready"])
        self.assertEqual(gate["state"], "CASE_NOT_STARTED")
        self.assertEqual(gate["reason_code"], "actual_input_evidence_source_unavailable")

    def test_r25_observation_support_does_not_complete_gate_two(self):
        contract = entry.load_contract()

        gate = entry.actual_input_observation_preflight(contract)

        self.assertTrue(gate["ready"])
        self.assertFalse(gate["formal_run_allowed"])
        self.assertEqual(gate["formal_run_block_reason"], "second_gate_incomplete")

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
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "program"
        self.prof = self.root / "教授研究" / "X分野" / "甲教授"
        self.prof.mkdir(parents=True)
        self.pack = self.prof / "邮件输入.json"
        self.template = self.root / "template.md"
        self.template.write_text("synthetic template", encoding="utf-8")
        self.email = {
            "email_id": "D001::I001", "professor": "甲教授",
            "idea": {"id": "D001_1", "text": "合成研究构想"},
            "direction_ids": ["D001"], "directions": [{"id": "D001", "name": "合成方向"}],
            "user_note": "用户输入", "papers": [{"item_key": "P001", "title": "合成论文"}],
            "gaps": [], "red_lines": [{"text": "不得编造"}],
            "soft_materials": {"positioning": [{"text": "定位事实"}]},
            "user_supplement": "补充事实", "allowed_sources": ["idea:D001_1"],
        }
        self.pack.write_text(json.dumps({"emails": [self.email]}, ensure_ascii=False), encoding="utf-8")
        self.packet = {
            "program_root": str(self.root), "professor_dir": str(self.prof),
            "email_pack": str(self.pack), "email_id": self.email["email_id"],
            "choices": [{"email_id": self.email["email_id"], "first_choice": True}],
            "mode": "first", "template": str(self.template), "result": str(self.root / "raw.json"),
        }
        self.manifest = {"program_root": str(self.root), "owners": [{
            "professor": "甲教授",
            "professor_dir": str(self.prof), "email_pack": str(self.pack),
            "email_ids": [self.email["email_id"]],
            "result": str(self.root / "raw.json"),
            "expected_choices_rows": self.packet["choices"],
            "sibling_exclusions": ["乙教授", "sibling-pack", "choices_scope"],
        }], "pre_run_hashes": {str(self.pack): hashlib.sha256(self.pack.read_bytes()).hexdigest()}}
        self.handoff_file = self.root / "owner-input.json"
        self.handoff_file.parent.mkdir(parents=True, exist_ok=True)
        self.handoff_file.write_text(json.dumps(self.packet, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def plan(self, **changes):
        model_input = {
            "idea": self.email["idea"], "direction_ids": self.email["direction_ids"],
            "directions": self.email["directions"], "user_note": self.email["user_note"],
            "papers": self.email["papers"], "gaps": [], "red_lines": self.email["red_lines"],
            "soft_materials": {"positioning": self.email["soft_materials"]["positioning"]},
            "user_supplement": self.email["user_supplement"],
            "allowed_sources": self.email["allowed_sources"],
        }
        value = {"status": "ok", "email_pack": str(self.pack),
                 "emails": [self.email["email_id"]],
                 "template": str(self.template), "output_mode": "first",
                 "verify": {"甲教授": "needs_recheck:missing"},
                 "needs_recheck_professors": ["甲教授"],
                 "jobs": [{"job_id": "email:" + self.email["email_id"],
                           "kind": "email", "model_input": model_input}]}
        value.update(changes)
        return value

    def call(self, observation=None, plan=None, *, call_id="cmd-1", output=None, return_code=0,
             invocation_argv=None, command=None):
        argv = invocation_argv or [
            "python3", "/producer/scripts/contact_state.py", "stage5-plan",
            "--program-root", str(self.root), "--email-pack", str(self.pack),
            "--template", str(self.template), "--mode", "first",
        ]
        envelope = {
            "pc68_actual_input_observation": {
                "schema": verifier.OWNER_OBSERVATION_SCHEMA,
                "source_step": "owner_input_json_parse", "business_step": "stage5-plan",
                "object": self.packet if observation is None else observation,
            },
            "stage5_invocation": {"argv": argv},
            "stage5_plan": self.plan() if plan is None else plan,
            "return_code": return_code,
        }
        command = command or ("python3 /producer/scripts/contact_state.py stage5-plan"
                              f" --program-root {self.root} --email-pack {self.pack}"
                              f" --template {self.template} --mode first")
        return {"id": call_id, "generation": "run-1", "thread": "owner-thread-1",
                "start": 10, "end": 11, "command": command,
                "output": json.dumps(envelope, ensure_ascii=False) if output is None else output}

    def test_same_parse_observation_is_accepted_after_handoff_file_cleanup(self):
        rows, problem = verifier.consumed_business_objects([self.call()])
        self.assertIsNone(problem)
        self.assertEqual(rows[0]["packet"], self.packet)
        self.assertEqual(rows[0]["plan"]["email_pack"], str(self.pack))
        # The serialized handoff source is deliberately gone before
        # attribution; evidence comes from this call's captured parse object.
        self.handoff_file.unlink()
        owner_pack, problem = verifier.owner_payload(rows, self.manifest)
        self.assertIsNone(problem)
        self.assertEqual(owner_pack, str(self.pack))

    def test_mismatch_to_assigned_partition_rows_is_product_failure(self):
        changed = dict(self.packet, choices=[{"email_id": "D-other::I-other"}])
        rows, problem = verifier.consumed_business_objects([self.call(observation=changed)])
        self.assertIsNone(problem)
        owner_pack, problem = verifier.owner_payload(rows, self.manifest)
        self.assertIsNone(owner_pack)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_bundle_choices_changed")

    def test_wrong_plan_pack_or_business_fields_is_product_failure(self):
        wrong_pack = self.plan(email_pack=str(self.root / "sibling-pack.json"))
        rows, problem = verifier.consumed_business_objects([self.call(plan=wrong_pack)])
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_directory_changed")

        wrong_job = self.plan()
        wrong_job["jobs"][0]["job_id"] = "email:sibling-id"
        rows, problem = verifier.consumed_business_objects([self.call(plan=wrong_job)])
        self.assertIsNone(problem)
        _, problem = verifier.owner_payload(rows, self.manifest)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_email_ids_changed")

        wrong_model = self.plan()
        wrong_model["jobs"][0]["model_input"]["idea"] = {"id": "sibling-id"}
        rows, problem = verifier.consumed_business_objects([self.call(plan=wrong_model)])
        self.assertIsNone(problem)
        _, problem = verifier.owner_payload(rows, self.manifest)
        self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
        self.assertEqual(problem["reason_code"], "owner_plan_business_data_changed")

    def test_missing_observation_and_unrelated_output_block(self):
        plain_plan = json.dumps(self.plan(), ensure_ascii=False)
        _, problem = verifier.consumed_business_objects([self.call(output=plain_plan)])
        self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(problem["reason_code"], "owner_actual_input_unobservable")

        unrelated = json.dumps({"read_file": str(self.pack), "value": self.packet}, ensure_ascii=False)
        _, problem = verifier.consumed_business_objects([self.call(output=unrelated)])
        self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")

    def test_damaged_or_ambiguous_observation_is_invalid(self):
        _, problem = verifier.consumed_business_objects([self.call(output='{"pc68_actual_input_observation":')])
        self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")

        duplicate_key = ('{"pc68_actual_input_observation":{},'
                         '"pc68_actual_input_observation":{},"stage5_plan":{},"return_code":0}')
        _, problem = verifier.consumed_business_objects([self.call(output=duplicate_key)])
        self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")

    def test_repeated_calls_remain_separately_associated(self):
        rows, problem = verifier.consumed_business_objects([
            self.call(call_id="cmd-1"), self.call(call_id="cmd-2")])
        self.assertIsNone(problem)
        self.assertEqual([row["call_id"] for row in rows], ["cmd-1", "cmd-2"])

        _, problem = verifier.consumed_business_objects([
            self.call(call_id="same"), self.call(call_id="same")])
        self.assertEqual(problem["verdict"], "INVALID_EVIDENCE")
        self.assertEqual(problem["reason_code"], "owner_input_observation_association_invalid")

    def test_legal_verification_early_stop_keeps_each_call_observed(self):
        later = {"status": "needs_refresh", "reason_code": "verify_missing"}
        rows, problem = verifier.consumed_business_objects([
            self.call(call_id="cmd-1"),
            self.call(plan=later, call_id="cmd-2", return_code=2),
        ])
        self.assertIsNone(problem)
        self.assertEqual(len(rows), 2)
        owner_pack, problem = verifier.owner_payload(rows, self.manifest)
        self.assertIsNone(problem)
        self.assertEqual(owner_pack, str(self.pack))

    def test_compound_initial_argv_rejects_result_or_choices(self):
        compound = "python3 -c 'run contact_state.py stage5-plan through the existing wrapper'"
        base_argv = ["python3", "/producer/scripts/contact_state.py", "stage5-plan",
                     "--program-root", str(self.root), "--email-pack", str(self.pack),
                     "--template", str(self.template), "--mode", "first"]
        for forbidden_flag in ("--result", "--choices"):
            with self.subTest(forbidden_flag=forbidden_flag):
                call = self.call(command=compound,
                                 invocation_argv=base_argv + [forbidden_flag, "/tmp/synthetic.json"])
                rows, problem = verifier.consumed_business_objects([call])
                self.assertIsNone(problem)
                self.assertEqual(rows[0]["invocation"]["flags"][forbidden_flag],
                                 "/tmp/synthetic.json")
                _, problem = verifier.owner_payload(rows, self.manifest)
                self.assertEqual(problem["verdict"], "FAIL_PRODUCT")
                self.assertEqual(problem["reason_code"],
                                 "owner_initial_plan_carries_result_or_choices")

    def test_command_text_arguments_do_not_replace_structured_invocation_evidence(self):
        call = self.call(
            command="python3 -c 'contact_state.py stage5-plan --result fake --choices fake'",
            output="",
        )

        rows, problem = verifier.consumed_business_objects([call])

        self.assertEqual(rows, [])
        self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(problem["reason_code"], "owner_actual_input_unobservable")

        envelope_call = self.call(command=call["command"])
        envelope = json.loads(envelope_call["output"])
        del envelope["stage5_invocation"]
        envelope_call["output"] = json.dumps(envelope, ensure_ascii=False)
        rows, problem = verifier.consumed_business_objects([envelope_call])

        self.assertEqual(rows, [])
        self.assertEqual(problem["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(problem["reason_code"], "owner_stage5_invocation_unobservable")


if __name__ == "__main__":
    unittest.main()
