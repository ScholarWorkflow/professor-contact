"""Gate-2 r13 regressions for the Codex raw final-answer source.

Synthetic evidence characterizes the evaluator and recipe wiring. It is not a
real-host PC68-R1 acceptance PASS.
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


verify = load("verify_issue68_stage5_routing_r13")
bridge = load("run_issue68_stage5_routing_r13")
preflight = load("check_issue68_codex_final_source_r13")
build = importlib.import_module("build_issue68_codex_request_r12")

FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"


class TestIssue68RuntimeR13(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        owners = [
            {
                "professor": name,
                "professor_dir": str(self.root / name),
                "email_pack": str(self.root / name / "邮件输入.json"),
                "email_ids": ["X"],
                "expected_result": {"status": "needs_refresh", "reason_code": "verify_missing"},
            }
            for name in ("A", "B")
        ]
        self.manifest = {
            "owners": owners,
            "program_root": str(self.root),
            "invalid_pack": str(self.root / "C" / "邮件输入.json"),
            "expected_choices": [
                {"email_id": "X", "professor_dir": owner["professor_dir"], "sentinel": owner["professor"]}
                for owner in owners
            ],
            "expected_scope": {owner["professor_dir"]: ["X"] for owner in owners},
        }

    def payload(self, owner):
        return json.dumps(
            {
                "email_pack": owner["email_pack"],
                "choices": self.manifest["expected_choices"],
                "choices_scope": self.manifest["expected_scope"],
            }
        )

    def root_rows(self):
        return [
            dict(owner["expected_result"], professor_dir=owner["professor_dir"])
            for owner in self.manifest["owners"]
        ]

    def root_result(self, rows=None):
        return json.dumps(self.root_rows() if rows is None else rows)

    def history_conflict(self):
        owner = self.manifest["owners"][0]
        return json.dumps(
            [
                {
                    "professor_dir": owner["professor_dir"],
                    "status": "ok",
                    "reason_code": "invented_by_root",
                }
            ]
        )

    def discovery(self):
        return json.dumps(
            {
                "status": "ok",
                "inputs": [
                    *[
                        {"email_pack": owner["email_pack"], "status": "ok"}
                        for owner in self.manifest["owners"]
                    ],
                    {"email_pack": self.manifest["invalid_pack"], "status": "error"},
                ],
            }
        )

    def command(self, action):
        return shlex.join(
            ["python3", "/installed/contact_state.py", action, "--program-root", str(self.root)]
        )

    def codex_evidence(
        self,
        *,
        old_turn_final=None,
        current_text=None,
        current_phase="final_answer",
        include_current=True,
        child_final=None,
    ):
        current_text = self.root_result() if current_text is None else current_text
        events = []
        relations = []

        def event(seq, method, thread, item, turn="turn-current", generation="g"):
            events.append(
                {
                    "runtime_seq": seq,
                    "runtime_generation": generation,
                    "direction": "recv",
                    "message": {
                        "method": method,
                        "params": {"threadId": thread, "turnId": turn, "item": item},
                    },
                }
            )

        event(1, "item/started", "root", {"type": "commandExecution", "id": "discovery"})
        event(
            2,
            "item/completed",
            "root",
            {
                "type": "commandExecution",
                "id": "discovery",
                "command": self.command("stage5-list-inputs"),
                "aggregatedOutput": self.discovery(),
            },
        )
        for index, owner in enumerate(self.manifest["owners"]):
            child, seq = f"child-{index}", 3 + index * 3
            relations.append(
                {"tool": "spawnAgent", "sender_thread_id": "root", "receiver_thread_ids": [child]}
            )
            event(
                seq,
                "rawResponseItem/completed",
                child,
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": self.payload(owner)}],
                },
            )
            event(
                seq + 1,
                "item/completed",
                "root",
                {
                    "type": "collabAgentToolCall",
                    "tool": "wait",
                    "status": "completed",
                    "senderThreadId": "root",
                    "receiverThreadIds": [child],
                    "agentsStates": {
                        child: {
                            "status": "completed",
                            "message": json.dumps(
                                dict(owner["expected_result"], professor_dir=owner["professor_dir"])
                            ),
                        }
                    },
                },
            )

        seq = 9
        if old_turn_final is not None:
            event(
                seq,
                "rawResponseItem/completed",
                "root",
                {
                    "type": "message",
                    "role": "assistant",
                    "phase": "final_answer",
                    "content": [{"type": "output_text", "text": old_turn_final}],
                },
                turn="turn-old",
            )
            seq += 1
        if child_final is not None:
            event(
                seq,
                "rawResponseItem/completed",
                "child-0",
                {
                    "type": "message",
                    "role": "assistant",
                    "phase": "final_answer",
                    "content": [{"type": "output_text", "text": child_final}],
                },
            )
            seq += 1
        if include_current:
            event(
                seq,
                "rawResponseItem/completed",
                "root",
                {
                    "type": "message",
                    "role": "assistant",
                    "phase": current_phase,
                    "content": [{"type": "output_text", "text": current_text}],
                },
            )

        response = {
            "version": "codex-cli 0.159.0-alpha.12.1",
            "output": {
                "thread_id": "root",
                "turn_id": "turn-current",
                "runtime_generation": "g",
                "termination_reason": "completed",
                "app_server_events": events,
            },
        }
        adapter = {
            "fixture_status": "HARNESS_DISPATCH_UNCONFIRMED",
            "delegation": {
                "state": "confirmed",
                "formal_child_count": 2,
                "child_thread_ids": ["child-0", "child-1"],
                "basis": ["formal_spawn_relation"],
                "reason_code": None,
            },
            "dispatch": {"thread_relations": relations, "agent_identity": {}},
        }
        return response, adapter

    def test_current_root_turn_raw_final_is_the_only_business_source(self):
        response, adapter = self.codex_evidence(old_turn_final=self.history_conflict())
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS")

    def test_current_root_turn_product_violation_cannot_be_masked_by_old_final(self):
        rows = self.root_rows()
        rows.append(
            {
                "professor_dir": rows[0]["professor_dir"],
                "status": "ok",
                "reason_code": "invented_by_root",
            }
        )
        response, adapter = self.codex_evidence(
            old_turn_final=self.root_result(), current_text=self.root_result(rows)
        )
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(
            (result["verdict"], result["reason_code"]),
            ("FAIL_PRODUCT", "root_consumed_results_conflict"),
        )

    def test_commentary_prior_turn_and_child_final_cannot_substitute(self):
        response, adapter = self.codex_evidence(
            old_turn_final=self.root_result(),
            current_phase="commentary",
            child_final=self.root_result(),
        )
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(
            (result["verdict"], result["reason_code"]),
            ("BLOCKED_OBSERVABILITY", "root_final_message_unobservable"),
        )

    def test_missing_raw_final_blocks_without_root_thread_read(self):
        response, adapter = self.codex_evidence(include_current=False)
        self.assertNotIn("root_thread_read", response["output"])
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(
            (result["verdict"], result["reason_code"]),
            ("BLOCKED_OBSERVABILITY", "root_final_message_unobservable"),
        )

    def test_duplicate_current_final_is_invalid(self):
        response, adapter = self.codex_evidence()
        final = next(
            entry
            for entry in response["output"]["app_server_events"]
            if entry["message"]["method"] == "rawResponseItem/completed"
            and entry["message"]["params"]["threadId"] == "root"
            and entry["message"]["params"]["turnId"] == "turn-current"
            and entry["message"]["params"]["item"].get("phase") == "final_answer"
        )
        duplicate = json.loads(json.dumps(final))
        duplicate["runtime_seq"] = 99
        response["output"]["app_server_events"].append(duplicate)
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(
            (result["verdict"], result["reason_code"]),
            ("INVALID_EVIDENCE", "root_final_message_ambiguous"),
        )

    def test_malformed_selected_raw_message_is_invalid(self):
        response, adapter = self.codex_evidence()
        item = response["output"]["app_server_events"][-1]["message"]["params"]["item"]
        item["content"] = [{"type": "output_text", "text": {"bad": "type"}}]
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(
            (result["verdict"], result["reason_code"]),
            ("INVALID_EVIDENCE", "root_final_message_malformed"),
        )

    def test_raw_event_without_turn_attribution_is_invalid(self):
        response, adapter = self.codex_evidence()
        response["output"]["app_server_events"][-1]["message"]["params"].pop("turnId")
        result = verify.verify_codex(response, adapter, self.manifest)
        self.assertEqual(
            (result["verdict"], result["reason_code"]),
            ("INVALID_EVIDENCE", "root_raw_event_malformed"),
        )

    def test_multiple_output_text_parts_follow_codex_source_join_order(self):
        response, _adapter = self.codex_evidence()
        item = response["output"]["app_server_events"][-1]["message"]["params"]["item"]
        item["content"] = [
            {"type": "output_text", "text": "ab"},
            {"type": "output_text", "text": "cd"},
        ]
        text, problem = verify.codex_final_result_source(response)
        self.assertIsNone(problem)
        self.assertEqual(text, "abcd")

    def test_preflight_classifier_uses_the_same_final_source(self):
        response, _adapter = self.codex_evidence()
        result = preflight.classify(response)
        self.assertEqual(result["status"], "CAPABILITY_CONFIRMED")
        del response["output"]["app_server_events"][-1]["message"]["params"]["item"]["phase"]
        result = preflight.classify(response)
        self.assertEqual(
            (result["status"], result["reason_code"]),
            ("CAPABILITY_ABSENT", "root_final_message_unobservable"),
        )

    def test_bridge_pins_merged_fixture_and_keeps_shared_parser(self):
        base = importlib.import_module("run_issue68_stage5_routing")
        original = {
            "FIXTURE_SHA": base.FIXTURE_SHA,
            "build_request": base.build_request,
            "verify_codex": base.verify_codex,
            "verify_opencode": base.verify_opencode,
            "run": base.run,
        }
        self.addCleanup(lambda: [setattr(base, key, value) for key, value in original.items()])
        bridge.pin_base_runner()
        self.assertEqual(base.FIXTURE_SHA, FIXTURE_SHA)
        self.assertIs(base.run, original["run"])
        self.assertIs(base.verify_codex, verify.verify_codex)
        self.assertIs(base.verify_opencode, verify.verify_opencode)
        self.assertIs(base.build_request, build.build_request)

    def test_bridge_rebinds_opencode_verifier_away_from_the_frozen_base(self):
        base = importlib.import_module("run_issue68_stage5_routing")
        original = base.verify_opencode
        self.addCleanup(setattr, base, "verify_opencode", original)
        bridge.pin_base_runner()
        self.assertIsNot(base.verify_opencode, original)
        self.assertIs(base.verify_opencode, verify.verify_opencode)

    def test_request_keeps_current_consensus_model(self):
        request = build.build_request(self.root, "固定业务输入")
        tokens = shlex.split(request["command"])
        self.assertIn("gpt-6-luna", tokens)
        self.assertIn('model_reasoning_effort="low"', tokens)

    def test_contract_drops_root_history_and_eval_server_patch_dependency(self):
        contract = json.loads(
            (RUNTIME / "issue68-runtime-evidence-contract-r13.json").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["fixture_sha"], FIXTURE_SHA)
        self.assertEqual(contract["fixture_contract"], "skills-test-fixtures/codex-eval-adapter@16")
        self.assertFalse(contract["eval_server_additional_patch_required"])
        self.assertNotIn("root_thread_read", json.dumps(contract, ensure_ascii=False))

    def test_contract_freezes_eval_server_revision_and_archive_requirements(self):
        contract = json.loads(
            (RUNTIME / "issue68-runtime-evidence-contract-r13.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            contract["eval_server_revision"], "3fdfa9387140cfc2e2aa3af415f85015f79706d2"
        )
        self.assertIn(
            "direct build provenance for the actual instance",
            contract["eval_server_revision_role"],
        )
        self.assertEqual(
            contract["formal_run_archive_requirements"],
            [
                "direct build provenance of the actual eval server instance that serves the formal request",
                "isolation evidence required for this proof",
            ],
        )

    def test_codex_only_entry_binds_r13_contract(self):
        entry = load("run_issue68_stage5_routing_r13_codex")
        loaded = entry.load_contract()
        self.assertEqual(loaded["revision"], "issue-68-runtime-evidence-r13-2026-10-04")
        self.assertEqual(loaded["fixture_sha"], FIXTURE_SHA)
        self.assertEqual(
            loaded["runner"],
            ".apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r13_codex.py",
        )
        self.assertTrue(
            entry.check_entry_uniqueness(str(entry.HERE / "run_issue68_stage5_routing_r13_codex.py"))
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
