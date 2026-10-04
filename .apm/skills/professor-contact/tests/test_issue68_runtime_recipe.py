"""PC68-R1 oracle/preflight regressions. Synthetic evidence is not host PASS."""
import copy
import importlib.util
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"


def load(name):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = load("verify_issue68_stage5_routing")
build = load("build_issue68_codex_request")
prepare = load("prepare_issue68_stage5_routing")


class TestIssue68RuntimeRecipe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        owners = [{"professor": name, "professor_dir": str(self.root / name),
                   "email_pack": str(self.root / name / "邮件输入.json"), "email_ids": ["X"],
                   "expected_result": {"status": "needs_refresh", "reason_code": "verify_missing"}}
                  for name in ("A", "B")]
        self.manifest = {"owners": owners, "program_root": str(self.root),
                         "invalid_pack": str(self.root / "C" / "邮件输入.json"),
                         "expected_choices": [{"email_id": "X", "professor_dir": owner["professor_dir"],
                                               "sentinel": owner["professor"]} for owner in owners],
                         "expected_scope": {owner["professor_dir"]: ["X"] for owner in owners}}
        self.choices = self.root / "choices.json"
        self.scope = self.root / "scope.json"
        self.choices.write_text(json.dumps(self.manifest["expected_choices"]))
        self.scope.write_text(json.dumps(self.manifest["expected_scope"]))

    def payload(self, owner):
        return json.dumps({"email_pack": owner["email_pack"], "choices": self.manifest["expected_choices"],
                           "choices_scope": self.manifest["expected_scope"]})

    def root_result(self):
        return json.dumps([dict(owner["expected_result"], professor_dir=owner["professor_dir"])
                           for owner in self.manifest["owners"]])

    def command(self, action, extra=()):
        return shlex.join(["python3", "/installed/contact_state.py", action,
                           "--program-root", str(self.root), *extra])

    def discovery(self):
        return json.dumps({"status": "ok", "inputs": [
            *[{"email_pack": owner["email_pack"], "status": "ok"} for owner in self.manifest["owners"]],
            {"email_pack": self.manifest["invalid_pack"], "status": "error"}]})

    def codex_evidence(self):
        events, relations = [], []

        def event(seq, method, thread, item):
            events.append({"runtime_seq": seq, "runtime_generation": "g", "direction": "notification",
                           "message": {"method": method, "params": {"threadId": thread, "item": item}}})

        event(1, "item/started", "root", {"type": "commandExecution", "id": "discovery"})
        event(2, "item/completed", "root", {"type": "commandExecution", "id": "discovery",
              "command": self.command("stage5-list-inputs"), "aggregatedOutput": self.discovery()})
        for index, owner in enumerate(self.manifest["owners"]):
            child, seq = f"child-{index}", 3 + index * 3
            relations.append({"tool": "spawnAgent", "sender_thread_id": "root", "receiver_thread_ids": [child]})
            event(seq, "rawResponseItem/completed", child, {"type": "message", "role": "user",
                  "content": [{"type": "input_text", "text": self.payload(owner)}]})
            event(seq + 1, "item/completed", "root", {"type": "collabAgentToolCall", "tool": "wait",
                  "status": "completed", "senderThreadId": "root", "receiverThreadIds": [child],
                  "agentsStates": {child: {"status": "completed", "message": json.dumps(
                      dict(owner["expected_result"], professor_dir=owner["professor_dir"]))}}})
        event(9, "item/started", "root", {"type": "commandExecution", "id": "rebuild"})
        event(10, "item/completed", "root", {"type": "commandExecution", "id": "rebuild",
              "command": self.command("stage5-rebuild-overview"), "aggregatedOutput": "{}"})
        event(11, "rawResponseItem/completed", "root", {"type": "message", "role": "assistant",
              "content": [{"type": "output_text", "text": self.root_result()}]})
        return {"output": {"thread_id": "root", "runtime_generation": "g", "termination_reason": "completed",
                            "app_server_events": events}}, {
            "fixture_status": "HARNESS_DISPATCH_UNCONFIRMED", "dispatch": {"thread_relations": relations,
            "agent_identity": {"child-0": {"loaded_identity": {"state": "unobservable"}}}}}

    def opencode_evidence(self):
        def tool(call, name, inputs, start, end, output):
            return {"type": "tool_use", "sessionID": "root", "timestamp": end,
                    "part": {"callID": call, "tool": name, "state": {"status": "completed", "input": inputs,
                              "time": {"start": start, "end": end}, "output": output, "metadata": {}}}}
        events = [tool("discovery", "bash", {"command": self.command("stage5-list-inputs")}, 1, 2, self.discovery())]
        for index, owner in enumerate(self.manifest["owners"]):
            events.append(tool(f"task-{index}", "task", {"subagent_type": verify.AGENT, "prompt": self.payload(owner)},
                               3 + index * 3, 5 + index * 3,
                               '<task id="child" state="completed"><task_result>' +
                               json.dumps(dict(owner["expected_result"], professor_dir=owner["professor_dir"])) + '</task_result></task>'))
        events += [tool("rebuild", "bash", {"command": self.command("stage5-rebuild-overview")}, 9, 10, "{}"),
                   {"type": "text", "sessionID": "root", "part": {"text": self.root_result()}}]
        return events, {"fixture_status": "FIXTURE_READY"}

    def test_codex_pass_uses_formal_ownership_and_wait_results_without_identity_gate(self):
        response, adapter = self.codex_evidence()
        events = response["output"]["app_server_events"]
        bootstrap = copy.deepcopy(events[2])
        bootstrap["message"]["params"]["item"]["content"][0]["text"] = '<environment_context>{"cwd":"/consumer"}</environment_context>'
        events.insert(2, bootstrap)
        for seq, event in enumerate(events, 1):
            event["runtime_seq"] = seq
        command = events[1]["message"]["params"]["item"]
        command["command"] = shlex.join(["/bin/zsh", "-lc", command["command"]])
        self.assertEqual(verify.verify_codex(response, adapter, self.manifest)["verdict"], "PASS")

    def test_opencode_pass_uses_foreground_task_completion_and_execution_times(self):
        events, shared = self.opencode_evidence()
        self.assertEqual(verify.verify_opencode(events, shared, self.manifest)["verdict"], "PASS")

    def test_wrong_owner_and_mutated_transport_are_product_failures(self):
        for field, value in (("email_pack", self.manifest["invalid_pack"]),
                             ("email_pack", "DISCOVERED_BY_WORKFLOW"),
                             ("choices", []), ("choices_scope", {}), ("choices_scope", "DERIVE_FROM_DISCOVERED_PACK")):
            with self.subTest(field=field):
                response, adapter = self.codex_evidence()
                content = response["output"]["app_server_events"][2]["message"]["params"]["item"]["content"][0]
                payload = json.loads(content["text"])
                payload[field] = value
                content["text"] = json.dumps(payload)
                self.assertEqual(verify.verify_codex(response, adapter, self.manifest)["verdict"], "FAIL_PRODUCT")
        owner = self.manifest["owners"][0]
        row = json.loads(self.payload(owner))
        packet = self.root / "owner-0.json"
        packet.write_text(json.dumps(row))
        row["owner_input_file"] = str(packet)
        self.assertIsNone(verify.business_payload(json.dumps(row), self.manifest)[1])
        packet.unlink()
        self.assertIsNone(verify.business_payload(json.dumps(row), self.manifest)[1])

    def test_observed_wrong_directory_or_success_is_failure_not_missing_evidence(self):
        for changed in ({"professor_dir": str(self.root / "translated")},
                        {"status": "ok", "reason_code": None}):
            with self.subTest(changed=changed):
                response, adapter = self.codex_evidence()
                state = response["output"]["app_server_events"][3]["message"]["params"]["item"]["agentsStates"]["child-0"]
                state["message"] = json.dumps(dict(json.loads(state["message"]), **changed))
                self.assertEqual(verify.verify_codex(response, adapter, self.manifest)["verdict"], "FAIL_PRODUCT")
                events, shared = self.opencode_evidence()
                row = dict(self.manifest["owners"][0]["expected_result"], professor_dir=self.manifest["owners"][0]["professor_dir"])
                events[1]["part"]["state"]["output"] = '<task state="completed"><task_result>' + json.dumps(dict(row, **changed)) + '</task_result></task>'
                self.assertEqual(verify.verify_opencode(events, shared, self.manifest)["verdict"], "FAIL_PRODUCT")
        calls = [{"start": 1, "end": 2, "thread": "root",
                  "command": self.command("stage5-list-inputs"), "output": self.discovery()},
                 {"start": 3, "end": 4, "thread": "child-0",
                  "command": self.command("stage5-plan", ["--email-pack", str(self.root / "translated" / "邮件输入.json")]),
                  "output": json.dumps({"status": "needs_refresh", "reason_code": "missing_email_pack"})}]
        result = verify.runtime_checks(calls, self.manifest, [4, 8], [self.root_result()], root="root",
                                       owner_threads={"child-0": self.manifest["owners"][0]["email_pack"]})
        self.assertEqual(result["reason_code"], "owner_plan_directory_changed")

    def test_unfinished_input_result_is_consumed_exactly_without_inventing_reason_enum(self):
        response, adapter = self.codex_evidence()
        state = response["output"]["app_server_events"][3]["message"]["params"]["item"]["agentsStates"]["child-0"]
        actual = dict(json.loads(state["message"]), status="needs_input", reason_code="verify_missing_contact_email")
        state["message"] = json.dumps(actual)
        root_item = response["output"]["app_server_events"][-1]["message"]["params"]["item"]["content"][0]
        rows = json.loads(root_item["text"])
        rows[0] = actual
        root_item["text"] = json.dumps(rows)
        self.assertEqual(verify.verify_codex(response, adapter, self.manifest)["verdict"], "PASS")
        rows[0]["reason_code"] = "invented_by_root"
        root_item["text"] = json.dumps(rows)
        self.assertEqual(verify.verify_codex(response, adapter, self.manifest)["verdict"], "FAIL_PRODUCT")

    def test_early_or_multiple_rebuild_is_a_product_failure(self):
        events, shared = self.opencode_evidence()
        events[3]["part"]["state"]["time"]["start"] = 7
        self.assertEqual(verify.verify_opencode(events, shared, self.manifest)["verdict"], "FAIL_PRODUCT")
        events, shared = self.opencode_evidence()
        second = copy.deepcopy(events[3])
        second["part"]["callID"] = "second-rebuild"
        events.insert(4, second)
        self.assertEqual(verify.verify_opencode(events, shared, self.manifest)["verdict"], "FAIL_PRODUCT")

    def test_missing_terminal_surface_blocks_and_corrupt_event_order_is_invalid(self):
        events, shared = self.opencode_evidence()
        del events[1]["part"]["state"]["time"]
        self.assertEqual(verify.verify_opencode(events, shared, self.manifest)["verdict"], "BLOCKED_OBSERVABILITY")
        response, adapter = self.codex_evidence()
        response["output"]["app_server_events"][1]["runtime_seq"] = 1
        self.assertEqual(verify.verify_codex(response, adapter, self.manifest)["verdict"], "INVALID_EVIDENCE")

    def test_background_task_and_missing_scope_flag_are_not_pass(self):
        events, shared = self.opencode_evidence()
        events[1]["part"]["state"]["input"]["background"] = True
        self.assertEqual(verify.verify_opencode(events, shared, self.manifest)["verdict"], "FAIL_PRODUCT")
        owner = self.manifest["owners"][0]
        calls = [{"start": 1, "end": 2, "command": self.command("stage5-list-inputs"), "output": self.discovery()},
                 {"start": 3, "end": 4, "command": self.command("stage5-plan", ["--email-pack", owner["email_pack"],
                   "--choices", str(self.choices)]), "output": json.dumps(owner["expected_result"])}]
        self.assertEqual(verify.runtime_checks(calls, self.manifest, [4, 8], [self.root_result()])["verdict"], "FAIL_PRODUCT")

    def test_request_tokens_freeze_workdir_trust_and_thread_limit(self):
        request = build.build_request(self.root, "固定业务输入")
        tokens = shlex.split(request["command"])
        self.assertEqual(tokens, ["--json", "--skip-git-repo-check", "--sandbox", "workspace-write", "--cd", str(self.root),
                         "--model", "gpt-5.6-luna", "--config", 'model_reasoning_effort="low"', "--config",
                         "agents.max_concurrent_threads_per_session=2", "--config",
                         'projects={' + json.dumps(str(self.root)) + '={trust_level="trusted"}}', "--", "固定业务输入"])

    def test_fixture_precheck_uses_the_actual_producer_plan(self):
        script = RUNTIME.parent.parent / "scripts" / "contact_state.py"
        manifest = prepare.prepare(self.root / "program", script, self.root / "evidence")
        self.assertEqual(len(manifest["owners"]), 2)
        self.assertTrue(all(owner["expected_result"]["status"] == "needs_refresh" for owner in manifest["owners"]))
        self.assertEqual(manifest["manual_patch"], "no")

    def test_combined_verdict_requires_both_pass_and_keeps_invalid_and_blocked(self):
        self.assertEqual(verify.combine([verify.verdict("PASS"), verify.verdict("PASS")])["verdict"], "PASS")
        for status in ("FAIL_PRODUCT", "INVALID_EVIDENCE", "INVALID_TEST_FIXTURE", "BLOCKED_OBSERVABILITY", "BLOCKED_DEPENDENCY"):
            self.assertEqual(verify.combine([verify.verdict("PASS"), verify.verdict(status)])["verdict"], status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
