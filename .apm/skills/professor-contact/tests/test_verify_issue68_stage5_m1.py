"""M1 regression: the final business result source must be unique per directory.

Formal review `pr72-test-review-r1-2026-10-04` M1: the runtime judge accepted a
final root array that kept the real unfinished owner results and appended an
invented ok row for the same directory. The judge must pin the final business
result source, require per-directory uniqueness and consistency inside that
source, and never treat historical references or nested diagnostics as final
results. Synthetic regressions characterize the oracle; they are not host PASS.
"""
import importlib.util
import json
import shlex
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


class TestVerifyIssue68Stage5FinalResultSource(unittest.TestCase):
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

    def payload(self, owner):
        return json.dumps({"email_pack": owner["email_pack"], "choices": self.manifest["expected_choices"],
                           "choices_scope": self.manifest["expected_scope"]})

    def root_result(self, extra=()):
        rows = [dict(owner["expected_result"], professor_dir=owner["professor_dir"])
                for owner in self.manifest["owners"]]
        rows.extend(extra)
        return json.dumps(rows)

    def invented_ok(self, owner):
        return {"professor_dir": owner["professor_dir"], "status": "ok", "reason_code": "invented_by_root"}

    def discovery(self):
        return json.dumps({"status": "ok", "inputs": [
            *[{"email_pack": owner["email_pack"], "status": "ok"} for owner in self.manifest["owners"]],
            {"email_pack": self.manifest["invalid_pack"], "status": "error"}]})

    def command(self, action):
        return shlex.join(["python3", "/installed/contact_state.py", action, "--program-root", str(self.root)])

    def discovery_calls(self):
        return [{"start": 1, "end": 2, "thread": "root",
                 "command": self.command("stage5-list-inputs"), "output": self.discovery()}]

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
        event(9, "rawResponseItem/completed", "root", {"type": "message", "role": "assistant",
              "content": [{"type": "output_text", "text": self.root_result()}]})
        return {"output": {"thread_id": "root", "runtime_generation": "g", "termination_reason": "completed",
                           "app_server_events": events}}, {
            "fixture_status": "HARNESS_DISPATCH_UNCONFIRMED",
            "dispatch": {"thread_relations": relations, "agent_identity": {}}}

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
                               json.dumps(dict(owner["expected_result"], professor_dir=owner["professor_dir"])) +
                               '</task_result></task>'))
        events.append({"type": "text", "sessionID": "root", "part": {"text": self.root_result()}})
        return events, {"fixture_status": "FIXTURE_READY"}

    def test_confirmation_1_legal_final_results_pass(self):
        result = verify.runtime_checks(self.discovery_calls(), self.manifest, [4, 8],
                                       ["两个 owner 的结果已按教授目录原样收到，未改写。", self.root_result()])
        self.assertEqual(result["verdict"], "PASS")
        response, adapter = self.codex_evidence()
        self.assertEqual(verify.verify_codex(response, adapter, self.manifest)["verdict"], "PASS")
        events, shared = self.opencode_evidence()
        self.assertEqual(verify.verify_opencode(events, shared, self.manifest)["verdict"], "PASS")

    def test_confirmation_2_contradictory_final_result_is_product_failure(self):
        owner = self.manifest["owners"][0]
        extra = self.invented_ok(owner)
        result = verify.runtime_checks(self.discovery_calls(), self.manifest, [4, 8],
                                       [self.root_result(extra=(extra,))])
        self.assertEqual(result["verdict"], "FAIL_PRODUCT")
        self.assertEqual(result["reason_code"], "root_consumed_results_conflict")
        response, adapter = self.codex_evidence()
        item = response["output"]["app_server_events"][-1]["message"]["params"]["item"]["content"][0]
        item["text"] = self.root_result(extra=(extra,))
        verdict_codex = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(verdict_codex["verdict"], "FAIL_PRODUCT")
        self.assertEqual(verdict_codex["reason_code"], "root_consumed_results_conflict")
        events, shared = self.opencode_evidence()
        events[-1]["part"]["text"] = self.root_result(extra=(extra,))
        verdict_opencode = verify.verify_opencode(events, shared, self.manifest)
        self.assertEqual(verdict_opencode["verdict"], "FAIL_PRODUCT")
        self.assertEqual(verdict_opencode["reason_code"], "root_consumed_results_conflict")

    def test_confirmation_3_missing_final_source_still_blocks(self):
        result = verify.runtime_checks(self.discovery_calls(), self.manifest, [4, 8],
                                       ["两个 owner 的结果已收到，稍后汇总。"])
        self.assertEqual(result["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(result["reason_code"], "root_consumed_result_unobservable")
        response, adapter = self.codex_evidence()
        response["output"]["app_server_events"].pop()
        result_codex = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result_codex["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(result_codex["reason_code"], "root_consumed_result_unobservable")

    def test_confirmation_4_damaged_final_source_is_invalid_evidence(self):
        damaged = "最终业务数组 " + self.root_result()[:-3]
        with self.assertRaises(json.JSONDecodeError):
            json.loads(damaged[len("最终业务数组 "):])
        result = verify.runtime_checks(self.discovery_calls(), self.manifest, [4, 8], [damaged])
        self.assertEqual(result["verdict"], "INVALID_EVIDENCE")
        response, adapter = self.codex_evidence()
        item = response["output"]["app_server_events"][-1]["message"]["params"]["item"]["content"][0]
        item["text"] = damaged
        result_codex = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result_codex["verdict"], "INVALID_EVIDENCE")

    def test_nested_diagnostics_are_not_the_final_result_source(self):
        first, second = self.manifest["owners"]
        nested = json.dumps({"diagnostics": {"consumed": [
            dict(first["expected_result"], professor_dir=first["professor_dir"]),
            dict(second["expected_result"], professor_dir=second["professor_dir"])]}})
        result = verify.runtime_checks(self.discovery_calls(), self.manifest, [4, 8], [nested])
        self.assertEqual(result["verdict"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(result["reason_code"], "root_consumed_result_unobservable")

    def test_single_rewritten_result_row_stays_a_product_failure(self):
        owner = self.manifest["owners"][0]
        rewritten = [dict(owner["expected_result"], professor_dir=owner["professor_dir"],
                          status="ok", reason_code="verify_missing")]
        result = verify.runtime_checks(self.discovery_calls(), self.manifest, [4, 8],
                                       [json.dumps(rewritten)])
        self.assertEqual(result["verdict"], "FAIL_PRODUCT")
        self.assertEqual(result["reason_code"], "root_changed_owner_result")


if __name__ == "__main__":
    unittest.main(verbosity=2)
