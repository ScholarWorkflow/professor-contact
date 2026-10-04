"""Gate-2 r18 regressions for the formal child business-input source.

Synthetic evidence characterizes the evaluator and the recipe wiring. It is not
a real-host PC68-R1 acceptance PASS.
"""
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
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verify = load("verify_issue68_stage5_routing_r18")
bridge = load("run_issue68_stage5_routing_r18")
entry = load("run_issue68_stage5_routing_r18_codex")

FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
CANONICAL_SPELLING = "試験"
REWRITTEN_SPELLING = "试验"


def python_literal(value):
    """The Python-literal payload form a recorded command can carry."""
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(key) + ":" + python_literal(member) for key, member in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(python_literal(member) for member in value) + "]"
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return "None"
    return json.dumps(value, ensure_ascii=False)


class TestIssue68RuntimeR18(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        owners = [
            {
                "professor": f"{CANONICAL_SPELLING} {name}",
                "professor_dir": str(self.root / f"{CANONICAL_SPELLING} {name}"),
                "email_pack": str(self.root / f"{CANONICAL_SPELLING} {name}" / "邮件输入.json"),
                "email_ids": ["X"],
                "expected_result": {"status": "needs_input", "reason_code": "verify_missing"},
            }
            for name in ("A", "B")
        ]
        self.manifest = {
            "owners": owners,
            "program_root": str(self.root),
            "invalid_pack": str(self.root / "C" / "邮件输入.json"),
            "expected_choices": [
                {"email_id": "X", "first_choice": False,
                 "professor_dir": owner["professor_dir"], "sentinel": owner["professor"]}
                for owner in owners
            ],
            "expected_scope": {owner["professor_dir"]: ["X"] for owner in owners},
        }

    # ---- fixture pieces ---------------------------------------------------

    def scope_list(self, rewritten=False):
        entries = []
        for index, owner in enumerate(self.manifest["owners"]):
            directory = owner["professor_dir"]
            if rewritten and index == 0:
                directory = directory.replace(CANONICAL_SPELLING, REWRITTEN_SPELLING)
            entries.append({"professor_dir": directory, "email_ids": list(owner["email_ids"])})
        return entries

    def payload(self, owner, scope=None, choices=None):
        return {
            "email_pack": owner["email_pack"],
            "choices": self.manifest["expected_choices"] if choices is None else choices,
            "choices_scope": self.scope_list() if scope is None else scope,
        }

    def recorded_command(self, inner):
        return '/bin/zsh -lc "' + inner.replace('"', '\\"') + '"'

    def json_form_command(self, payload):
        argument = json.dumps(payload, ensure_ascii=False)
        inner = ("python3 -c 'import sys,json; packet=json.loads(sys.argv[1]); print(packet[\"email_pack\"])' '"
                 + argument + "'")
        return self.recorded_command(inner)

    def literal_form_command(self, payload):
        inner = ("python3 -c 'import json\npacket = " + python_literal(payload)
                 + "\nprint(packet[\"email_pack\"])'")
        return self.recorded_command(inner)

    def root_result(self):
        return json.dumps([dict(owner["expected_result"], professor_dir=owner["professor_dir"])
                           for owner in self.manifest["owners"]])

    def discovery(self):
        return json.dumps({"status": "ok", "inputs": [
            *[{"email_pack": owner["email_pack"], "status": "ok"} for owner in self.manifest["owners"]],
            {"email_pack": self.manifest["invalid_pack"], "status": "error"},
        ]})

    def discovery_command(self):
        return shlex.join(["python3", "/installed/contact_state.py", "stage5-list-inputs",
                           "--program-root", self.manifest["program_root"]])

    def evidence(self, *, scope=None, choices=None, form="json", child_command=True, child_message=False,
                 wait=True, wait_before_completion=False, old_turn_final=None, current_phase="final_answer",
                 child_payloads=None):
        """One faithful r18 baseline: the real V2 child task shape plus the
        plaintext business object the owner consumed in its own command."""
        events, relations, seq = [], [], 0

        def event(method, thread, item, turn="turn-current", generation="g", turn_status=None):
            nonlocal seq
            seq += 1
            params = {"threadId": thread, "turnId": turn, "item": item}
            if turn_status is not None:
                params["turn"] = {"id": turn, "status": turn_status}
            events.append({
                "runtime_seq": seq,
                "runtime_generation": generation,
                "direction": "recv",
                "message": {"method": method, "params": params},
            })

        event("item/started", "root", {"type": "commandExecution", "id": "discovery"})
        event("item/completed", "root", {"type": "commandExecution", "id": "discovery",
                                         "command": self.discovery_command(), "aggregatedOutput": self.discovery()})
        for index, owner in enumerate(self.manifest["owners"]):
            child = f"child-{index}"
            relations.append({"tool": "spawnAgent", "sender_thread_id": "root", "receiver_thread_ids": [child]})
            event("rawResponseItem/completed", child, {
                "type": "agent_message",
                "id": f"amsg-{index}",
                "author": "/root",
                "recipient": f"/root/stage5_{index}",
                "content": [
                    {"type": "input_text",
                     "text": f"Message Type: NEW_TASK\nTask name: /root/stage5_{index}\nSender: /root\nPayload:\n"},
                    {"type": "encrypted_content", "encrypted_content": "gAAAAA-encrypted-task-payload"},
                ],
            })
            if child_message:
                event("rawResponseItem/completed", child, {
                    "type": "message", "role": "user", "phase": None,
                    "content": [{"type": "input_text", "text": json.dumps(self.payload(owner))}],
                })
            if child_command:
                payloads = [self.payload(owner, scope=scope, choices=choices)] if child_payloads is None \
                    else child_payloads(owner)
                for offset, payload in enumerate(payloads):
                    item_id = f"exec-{index}-{offset}"
                    command = self.literal_form_command(payload) if form == "python_literal" \
                        else self.json_form_command(payload)
                    event("item/started", child, {"type": "commandExecution", "id": item_id, "command": command})
                    event("item/completed", child, {"type": "commandExecution", "id": item_id, "command": command,
                                                    "exitCode": 0,
                                                    "aggregatedOutput": json.dumps(owner["expected_result"])})
            event("rawResponseItem/completed", child, {
                "type": "message", "role": "assistant", "phase": "final_answer",
                "content": [{"type": "output_text",
                             "text": json.dumps(dict(owner["expected_result"],
                                                     professor_dir=owner["professor_dir"]))}],
            })
            if wait and wait_before_completion:
                self._wait_event(events, seq, child, owner)
                seq = events[-1]["runtime_seq"]
            event("turn/completed", child, {"type": "turn", "id": f"turn-{index}"},
                  turn=f"turn-{index}", turn_status="completed")
            if wait and not wait_before_completion:
                self._wait_event(events, seq, child, owner)
                seq = events[-1]["runtime_seq"]
        if old_turn_final is not None:
            event("rawResponseItem/completed", "root", {
                "type": "message", "role": "assistant", "phase": "final_answer",
                "content": [{"type": "output_text", "text": old_turn_final}],
            }, turn="turn-old")
        event("rawResponseItem/completed", "root", {
            "type": "message", "role": "assistant", "phase": current_phase,
            "content": [{"type": "output_text", "text": self.root_result()}],
        })
        response = {"version": "codex-cli 0.159.0-alpha.12.1",
                    "output": {"thread_id": "root", "turn_id": "turn-current", "runtime_generation": "g",
                               "termination_reason": "completed", "app_server_events": events}}
        adapter = {"fixture_status": "FIXTURE_READY",
                   "delegation": {"state": "confirmed", "formal_child_count": 2, "basis": ["formal_spawn_relation"]},
                   "dispatch": {"thread_relations": relations, "agent_identity": {}}}
        return response, adapter

    def _wait_event(self, events, seq, child, owner):
        events.append({
            "runtime_seq": seq + 1,
            "runtime_generation": "g",
            "direction": "recv",
            "message": {"method": "item/completed", "params": {"threadId": "root", "turnId": "turn-current", "item": {
                "type": "collabAgentToolCall", "id": f"wait-{child}", "tool": "wait", "status": "completed",
                "senderThreadId": "root", "receiverThreadIds": [child],
                "agentsStates": {child: {"status": "completed", "message": json.dumps(
                    dict(owner["expected_result"], professor_dir=owner["professor_dir"]))}},
            }}},
        })

    def child_commands(self, response, child):
        return [event["message"]["params"]["item"] for event in response["output"]["app_server_events"]
                if event["message"]["method"] == "item/completed"
                and event["message"]["params"].get("threadId") == child
                and event["message"]["params"].get("item", {}).get("type") == "commandExecution"]

    def child_agent_messages(self, response, child):
        return [event for event in response["output"]["app_server_events"]
                if event["message"]["params"].get("threadId") == child
                and event["message"]["params"].get("item", {}).get("type") == "agent_message"]

    # ---- the real shape ---------------------------------------------------

    def test_real_v2_child_shape_reads_the_consumed_command_payload(self):
        response, adapter = self.evidence()
        for child in ("child-0", "child-1"):
            message = self.child_agent_messages(response, child)[0]["message"]["params"]["item"]
            self.assertEqual(message["type"], "agent_message")
            self.assertEqual([part["type"] for part in message["content"]], ["input_text", "encrypted_content"])
            self.assertNotIn("role", message)
            self.assertIn("encrypted_content", message["content"][1])
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    def test_python_literal_command_payload_form_is_supported(self):
        response, adapter = self.evidence(form="python_literal")
        self.assertIn("False", self.child_commands(response, "child-0")[0]["command"])
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    def test_object_scope_form_is_equivalent_to_the_entry_list_form(self):
        response, adapter = self.evidence(scope=self.manifest["expected_scope"])
        self.assertIn("choices_scope", self.child_commands(response, "child-1")[0]["command"])
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    def test_plaintext_child_message_payload_remains_the_delivery_fallback(self):
        response, adapter = self.evidence(child_command=False, child_message=True)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    # ---- product violations are never observability blockers --------------

    def test_rewritten_scope_directory_is_product_failure_not_observability(self):
        rewritten = self.scope_list(rewritten=True)
        self.assertEqual(rewritten[0]["professor_dir"],
                         self.manifest["owners"][0]["professor_dir"].replace(CANONICAL_SPELLING, REWRITTEN_SPELLING))
        response, adapter = self.evidence(scope=rewritten)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "choices_scope_transport_changed"))
        self.assertEqual(result["observed_pack"], self.manifest["owners"][0]["email_pack"])

    def test_choices_rewrite_is_product_failure(self):
        rewritten = json.loads(json.dumps(self.manifest["expected_choices"]))
        rewritten[0]["sentinel"] = "rewritten"
        response, adapter = self.evidence(choices=rewritten)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "choices_transport_changed"))

    def test_missing_consumed_choices_is_product_failure(self):
        def payloads(owner):
            payload = self.payload(owner)
            payload.pop("choices")
            return [payload]
        response, adapter = self.evidence(child_payloads=payloads)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "choices_transport_missing"))

    def test_unexpected_owner_pack_is_product_failure(self):
        def payloads(owner):
            payload = self.payload(owner)
            payload["email_pack"] = self.manifest["invalid_pack"]
            return [payload]
        response, adapter = self.evidence(child_payloads=payloads)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "unexpected_owner_pack"))

    def test_product_failure_is_not_masked_by_the_other_child_blocker(self):
        def payloads(owner):
            if owner is self.manifest["owners"][0]:
                return [{"mode": "first"}]  # consumed command exposes no business object
            return [self.payload(owner, scope=self.scope_list(rewritten=True))]

        response, adapter = self.evidence(child_payloads=payloads)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "choices_scope_transport_changed"))

    # ---- frozen blocked and invalid channels ------------------------------

    def test_missing_consumed_payload_is_observability_blocker(self):
        response, adapter = self.evidence(child_payloads=lambda owner: [{"mode": "first"}])
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable"))

    def test_no_plaintext_payload_surface_keeps_the_frozen_delivery_blocker(self):
        response, adapter = self.evidence(child_command=False)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("BLOCKED_OBSERVABILITY", "completed_user_payload_unobservable"))

    def test_two_distinct_consumed_payloads_are_invalid_evidence(self):
        def payloads(owner):
            return [self.payload(owner), self.payload(owner, scope=self.scope_list(rewritten=True))]
        response, adapter = self.evidence(child_payloads=payloads)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("INVALID_EVIDENCE", "owner_business_object_ambiguous"))

    def test_wait_before_owner_completion_is_product_failure(self):
        response, adapter = self.evidence(wait_before_completion=True)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "wait_precedes_owner_completion"))

    def test_wrong_owner_count_is_product_failure(self):
        response, adapter = self.evidence()
        adapter["dispatch"]["thread_relations"] = adapter["dispatch"]["thread_relations"][:1]
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]), ("FAIL_PRODUCT", "wrong_owner_count"))

    def test_event_order_or_generation_is_invalid_evidence(self):
        response, adapter = self.evidence()
        response["output"]["app_server_events"][3]["runtime_seq"] = 1
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("INVALID_EVIDENCE", "event_order_or_generation_invalid"))

    def test_root_final_source_is_still_the_current_turn_selector(self):
        response, adapter = self.evidence(old_turn_final=json.dumps([{"professor_dir": "stale",
                                                                     "status": "ok", "reason_code": "invented"}]))
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    # ---- wiring and contract ---------------------------------------------

    def test_bridge_pins_r18_verifier_and_r12_builder(self):
        base = importlib.import_module("run_issue68_stage5_routing")
        build = importlib.import_module("build_issue68_codex_request_r12")
        original = {"FIXTURE_SHA": base.FIXTURE_SHA, "build_request": base.build_request,
                    "verify_codex": base.verify_codex, "verify_opencode": base.verify_opencode}
        self.addCleanup(lambda: [setattr(base, key, value) for key, value in original.items()])
        bridge.pin_base_runner()
        self.assertEqual(base.FIXTURE_SHA, FIXTURE_SHA)
        self.assertIs(base.build_request, build.build_request)
        self.assertIs(base.verify_codex, verify.verify_codex)
        self.assertIs(base.verify_opencode, verify.verify_opencode)

    def test_contract_freezes_the_owner_business_input_source(self):
        contract = json.loads((RUNTIME / "issue68-runtime-evidence-contract-r18.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["revision"], "issue-68-runtime-evidence-r18-2026-10-04")
        self.assertEqual(contract["fixture_sha"], FIXTURE_SHA)
        self.assertEqual(contract["eval_server_revision"], "3fdfa9387140cfc2e2aa3af415f85015f79706d2")
        self.assertEqual(contract["runner"], ".apm/skills/professor-contact/tests/runtime/"
                         + "run_issue68_stage5_routing_r18_codex.py")
        source = contract["codex"]["owner_business_input_source"]
        self.assertIn("commandExecution", source)
        self.assertIn("exactly one attributable object per formal child", source)
        self.assertIn("agent_message", " ".join(contract["codex"]["owner_business_input_exclusions"]))
        self.assertIn("mapping", contract["codex"]["choices_scope_equivalence"])
        self.assertIn("never downgraded", contract["codex"]["terminal_precedence"])
        self.assertEqual(contract["codex"]["missing_observation"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(contract["codex"]["malformed_or_ambiguous_observation"], "INVALID_EVIDENCE")

    def test_codex_only_entry_binds_the_r18_contract(self):
        self.assertEqual(entry.CONTRACT.name, "issue68-runtime-evidence-contract-r18.json")
        self.assertEqual(entry.FIXTURE_SHA, FIXTURE_SHA)
        self.assertEqual(entry.HOST, "codex")
        self.assertEqual(entry.CASE, "PC68-R1")
        self.assertEqual(entry.load_contract()["revision"], entry.CONTRACT_REVISION)
        self.assertTrue(entry.check_entry_uniqueness(str(RUNTIME / "run_issue68_stage5_routing_r18_codex.py")))
        with self.assertRaises(ValueError):
            entry.check_entry_uniqueness(str(RUNTIME / "run_issue68_stage5_routing_r14_codex.py"))

    def test_no_scope_entry_is_needed_for_an_object_form_payload(self):
        payload = {"email_pack": self.manifest["owners"][0]["email_pack"],
                   "choices": self.manifest["expected_choices"],
                   "choices_scope": self.manifest["expected_scope"]}
        self.assertEqual(verify.scope_mapping(payload["choices_scope"]),
                         {entry["professor_dir"]: entry["email_ids"] for entry in self.scope_list()})
        self.assertIsNone(verify.scope_mapping([{"professor_dir": "x"}]))
        self.assertIsNone(verify.scope_mapping("not-a-scope"))


if __name__ == "__main__":
    unittest.main()
