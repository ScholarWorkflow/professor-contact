"""Gate-2 r12 regressions. Synthetic evidence is not host acceptance PASS."""
import importlib
import importlib.util
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))


def load(name):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = load("verify_issue68_stage5_routing_r12")
build = load("build_issue68_codex_request_r12")
bridge = importlib.import_module("run_issue68_stage5_routing_r12")


class TestIssue68RuntimeR12(unittest.TestCase):
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

    def root_rows(self):
        return [dict(owner["expected_result"], professor_dir=owner["professor_dir"])
                for owner in self.manifest["owners"]]

    def root_result(self, rows=None):
        return json.dumps(self.root_rows() if rows is None else rows)

    def history_conflict(self):
        owner = self.manifest["owners"][0]
        return json.dumps([{"professor_dir": owner["professor_dir"], "status": "ok",
                            "reason_code": "invented_by_root"}])

    def discovery(self):
        return json.dumps({"status": "ok", "inputs": [
            *[{"email_pack": owner["email_pack"], "status": "ok"} for owner in self.manifest["owners"]],
            {"email_pack": self.manifest["invalid_pack"], "status": "error"}]})

    def command(self, action):
        return shlex.join(["python3", "/installed/contact_state.py", action, "--program-root", str(self.root)])

    def root_read(self, final_text, history=(), phase="final_answer"):
        items = [{"type": "agentMessage", "id": f"history-{i}", "text": text, "phase": "commentary"}
                 for i, text in enumerate(history)]
        if final_text is not None:
            items.append({"type": "agentMessage", "id": "final", "text": final_text, "phase": phase})
        return {"thread_id": "root", "runtime_generation": "g",
                "request": {"method": "thread/read", "params": {"threadId": "root", "includeTurns": True}},
                "error": None, "result": {"thread": {"id": "root", "turns": [{"items": items}]}}}

    def codex_evidence(self, history=(), final_text=None, phase="final_answer"):
        final_text = self.root_result() if final_text is None else final_text
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
        seq = 9
        for text in history:
            event(seq, "rawResponseItem/completed", "root", {"type": "message", "role": "assistant",
                  "content": [{"type": "output_text", "text": text}]})
            seq += 1
        event(seq, "rawResponseItem/completed", "root", {"type": "message", "role": "assistant",
              "content": [{"type": "output_text", "text": final_text}]})
        response = {"output": {"thread_id": "root", "runtime_generation": "g",
                               "termination_reason": "completed", "app_server_events": events,
                               "root_thread_read": self.root_read(final_text, history, phase)}}
        adapter = {"fixture_status": "HARNESS_DISPATCH_UNCONFIRMED",
                   "dispatch": {"thread_relations": relations, "agent_identity": {}}}
        return response, adapter

    def text_event(self, text, index):
        return {"type": "text", "sessionID": "root", "timestamp": 20 + index,
                "part": {"id": f"prt-{index}", "sessionID": "root", "messageID": f"msg-{index}",
                         "type": "text", "text": text, "time": {"start": 20 + index, "end": 21 + index}}}

    def opencode_evidence(self, history=(), final_text=None):
        final_text = self.root_result() if final_text is None else final_text

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
        for index, text in enumerate(history):
            events.append(self.text_event(text, index))
        events.append(self.text_event(final_text, len(history) + 1))
        return events, {"fixture_status": "FIXTURE_READY"}

    def test_conflicting_history_does_not_reject_legal_final_result(self):
        history = self.history_conflict()
        response, adapter = self.codex_evidence(history=(history,))
        self.assertEqual(verify.verify_codex(response, adapter, self.manifest)["verdict"], "PASS")
        events, shared = self.opencode_evidence(history=(history,))
        self.assertEqual(verify.verify_opencode(events, shared, self.manifest)["verdict"], "PASS")

    def test_correct_history_cannot_mask_conflicting_final_result(self):
        rows = self.root_rows()
        rows.append({"professor_dir": rows[0]["professor_dir"], "status": "ok",
                     "reason_code": "invented_by_root"})
        wrong = self.root_result(rows)
        response, adapter = self.codex_evidence(history=(self.root_result(),), final_text=wrong)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "root_consumed_results_conflict"))
        events, shared = self.opencode_evidence(history=(self.root_result(),), final_text=wrong)
        result = verify.verify_opencode(events, shared, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "root_consumed_results_conflict"))

    def test_missing_or_unknown_codex_terminal_source_blocks(self):
        response, adapter = self.codex_evidence()
        del response["output"]["root_thread_read"]
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_final_message_unobservable"))
        response, adapter = self.codex_evidence(phase=None)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_final_message_unobservable"))

    def test_stale_prior_codex_final_cannot_replace_last_turn_terminal_source(self):
        response, adapter = self.codex_evidence()
        response["output"]["root_thread_read"]["result"]["thread"]["turns"] = [
            {"items": [{"type": "agentMessage", "id": "prior-final", "text": self.root_result(),
                        "phase": "final_answer"}]},
            {"items": [{"type": "agentMessage", "id": "current-unknown", "text": self.history_conflict(),
                        "phase": None}]},
        ]
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_final_message_unobservable"))

    def test_missing_opencode_final_text_after_tasks_blocks(self):
        events, shared = self.opencode_evidence()
        events.pop()
        result = verify.verify_opencode(events, shared, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "root_final_message_unobservable"))

    def test_malformed_selected_source_is_invalid(self):
        response, adapter = self.codex_evidence()
        item = response["output"]["root_thread_read"]["result"]["thread"]["turns"][0]["items"][-1]
        item["text"] = {"bad": "type"}
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("INVALID_EVIDENCE", "root_final_message_malformed"))
        events, shared = self.opencode_evidence()
        del events[-1]["part"]["messageID"]
        result = verify.verify_opencode(events, shared, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("INVALID_EVIDENCE", "root_text_part_malformed"))

    def test_request_uses_current_consensus_model(self):
        request = build.build_request(self.root, "固定业务输入")
        tokens = shlex.split(request["command"])
        self.assertIn("gpt-6-luna", tokens)
        self.assertIn('model_reasoning_effort="low"', tokens)
        self.assertNotIn("gpt-5.6-luna", tokens)

    def test_bridge_pins_r12_parser_verifier_request_builder_and_fixture(self):
        seen = []

        def fake_run(argv, cwd, prefix, *, env=None, timeout=180):
            seen.append(list(argv))
            return 0

        old = bridge._ORIGINAL_RUN
        bridge._ORIGINAL_RUN = fake_run
        self.addCleanup(setattr, bridge, "_ORIGINAL_RUN", old)
        with tempfile.TemporaryDirectory() as root:
            fixture = Path(root) / "fixture"
            parser = fixture / "scripts" / "parse_codex_eval_evidence.py"
            bridge.run([sys.executable, str(parser)], Path(root), Path(root) / "a")
            bridge.run([sys.executable, str(RUNTIME / "verify_issue68_stage5_routing.py")], Path(root), Path(root) / "b")
            bridge.run([sys.executable, str(RUNTIME / "build_issue68_codex_request.py")], Path(root), Path(root) / "c")
        self.assertEqual(Path(seen[0][1]).name, "parse_codex_eval_evidence_with_root_history.py")
        self.assertIn("--root-history-contract", seen[0])
        self.assertEqual(Path(seen[1][1]).name, "verify_issue68_stage5_routing_r12.py")
        self.assertEqual(Path(seen[2][1]).name, "build_issue68_codex_request_r12.py")
        self.assertEqual(bridge.FIXTURE_SHA, "cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04")


if __name__ == "__main__":
    unittest.main(verbosity=2)
