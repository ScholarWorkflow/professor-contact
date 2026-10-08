"""Focused checks for the single-request transfer-location preflight."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import preflight_issue68_transfer_location_eval_r33 as preflight


class TestIssue68TransferLocationEvalPreflight(unittest.TestCase):
    def test_preflight_targets_the_r37_product_commit_used_by_formal_runner(self):
        self.assertEqual(preflight.PRODUCER_SHA,
                         "faab365d0be2bb66f2f285fdaa2927631dbf33f8")
        self.assertEqual(preflight.PRODUCER_SHA, preflight.runner.PRODUCER_REVISION)

    def setUp(self):
        self.run_directory = tempfile.TemporaryDirectory(
            prefix=preflight.RUN_ROOT_PREFIX, dir="/private/tmp")
        self.addCleanup(self.run_directory.cleanup)
        self.run_root = Path(self.run_directory.name)
        self.root = str(self.run_root / "transfer")
        Path(self.root).mkdir()
        self.command = "uv run --no-project python /private/tmp/probe.py"
        self.marker_sha = "a" * 64

    def request(self):
        return preflight.build_request(self.root, "synthetic marker preflight")

    def test_configuration_before_eval_response_is_not_claimed_as_undisclosed(self):
        facts = preflight.request_configuration(self.request(), {})

        self.assertEqual(facts["effective_model_status"], "NOT_OBSERVED_YET")
        self.assertEqual(facts["effective_reasoning_effort_status"], "NOT_OBSERVED_YET")
        self.assertEqual(facts["effective_configuration_source"]["status"],
                         "NOT_OBSERVED_YET")
        self.assertEqual(facts["effective_project_approval_configuration"]["status"],
                         "NOT_OBSERVED_YET")

    def test_marker_command_uses_a_run_scoped_uv_cache_outside_observed_roots(self):
        command = preflight.build_marker_command("/private/tmp/marker_probe.py", self.root)
        cache_dir = Path(self.root).resolve().parent / ".uv-cache"
        tokens = preflight.command_tokens(command)

        self.assertEqual(tokens[:5], [
            "uv", "--cache-dir", str(cache_dir), "run", "--no-project",
        ])
        self.assertEqual(cache_dir, self.run_root / ".uv-cache")
        self.assertNotEqual(cache_dir, Path(self.root).resolve())
        with tempfile.TemporaryDirectory(
                prefix=preflight.RUN_ROOT_PREFIX, dir="/private/tmp") as other:
            other_transfer = Path(other) / "transfer"
            other_transfer.mkdir()
            other_command = preflight.build_marker_command(
                "/private/tmp/marker_probe.py", other_transfer)
            other_cache = Path(preflight.command_tokens(other_command)[2])
            self.assertNotEqual(cache_dir, other_cache)

    def test_request_keeps_approval_values_in_project_file_and_trust_only_in_cli(self):
        request = self.request()

        facts = preflight.request_configuration(request, {})

        self.assertEqual(facts["requested_configs"], [
            'model_reasoning_effort="low"',
            "agents.max_concurrent_threads_per_session=2",
            'projects={"' + self.root + '"={trust_level="trusted"}}',
        ])
        self.assertIsNone(facts["project_approval_configuration"])
        request["command"] = request["command"].replace(
            "-- ", '--config approval_policy="on-request" -- ')
        with self.assertRaisesRegex(ValueError, "actual_request_configuration_mismatch"):
            preflight.request_configuration(request, {})
        for option in (
            "--approve-for-me",
            "--dangerously-bypass-approvals-and-sandbox",
        ):
            request = self.request()
            request["command"] = request["command"].replace(
                "-- ", f"{option} -- ")
            with self.subTest(option=option):
                with self.assertRaisesRegex(
                    ValueError, "per_request_approval_override_forbidden"):
                    preflight.request_configuration(request, {})

    def test_effective_project_approval_values_are_read_from_response(self):
        response = {"output": {"thread_start_effective": {
            "approvalPolicy": "on-request",
            "approvalsReviewer": "auto_review",
        }}}

        facts = preflight.request_configuration(self.request(), response)

        approval = facts["effective_project_approval_configuration"]
        self.assertEqual(approval["status"], "MATCH")
        self.assertEqual(approval["values"], {
            "approval_policy": "on-request",
            "approvals_reviewer": "auto_review",
        })
        self.assertEqual(approval["statuses"], {
            "approval_policy": "MATCH",
            "approvals_reviewer": "MATCH",
        })
        self.assertEqual(approval["field_paths"], {
            "approval_policy": "output.thread_start_effective.approvalPolicy",
            "approvals_reviewer": "output.thread_start_effective.approvalsReviewer",
        })

    def test_missing_or_mismatched_effective_project_values_are_not_inferred(self):
        response = {"output": {"thread_start_effective": {
            "approvalPolicy": "on-request",
            "approvalsReviewer": "user",
        }}}

        facts = preflight.request_configuration(self.request(), response)

        approval = facts["effective_project_approval_configuration"]
        self.assertEqual(approval["status"], "MISMATCH")
        self.assertEqual(approval["values"]["approvals_reviewer"], "user")
        missing = preflight.request_configuration(self.request(), {
            "output": {"thread_start_effective": {"approvalPolicy": "on-request"}},
        })["effective_project_approval_configuration"]
        self.assertIsNone(missing["values"]["approvals_reviewer"])
        self.assertEqual(missing["statuses"]["approvals_reviewer"],
                         "NOT_EXPOSED_BY_CURRENT_SERVICE")
        self.assertEqual(missing["status"], "NOT_EXPOSED_BY_CURRENT_SERVICE")

    def test_invalid_effective_project_value_is_preserved_as_invalid(self):
        response = {"output": {"thread_start_effective": {
            "approvalPolicy": "on-request",
            "approvalsReviewer": 3,
        }}}

        facts = preflight.request_configuration(self.request(), response)

        approval = facts["effective_project_approval_configuration"]
        self.assertEqual(approval["values"]["approvals_reviewer"], 3)
        self.assertEqual(approval["statuses"]["approvals_reviewer"],
                         "INVALID_SERVICE_REPORTED_VALUE")
        self.assertEqual(approval["status"], "INVALID_SERVICE_REPORTED_VALUE")

    def test_effective_values_come_from_unique_root_thread_started_event(self):
        response = {"version": "eval-test", "output": {
            "thread_id": "root-1", "runtime_generation": 4,
            "app_server_events": [{
                "runtime_seq": 7, "runtime_generation": 4,
                "message": {"method": "thread/started", "params": {
                    "thread": {"id": "root-1", "model": "gpt-5.6-luna",
                               "reasoningEffort": "medium"},
                }},
            }],
        }}

        facts = preflight.request_configuration(self.request(), response)

        self.assertEqual(facts["requested_model"], "gpt-6-luna")
        self.assertEqual(facts["requested_reasoning_effort"], "low")
        self.assertEqual(facts["service_reported_effective_model"], "gpt-5.6-luna")
        self.assertEqual(facts["effective_model_status"], "OBSERVED")
        self.assertEqual(facts["service_reported_effective_reasoning_effort"], "medium")
        self.assertEqual(facts["effective_reasoning_effort_status"], "OBSERVED")
        self.assertEqual(facts["effective_configuration_source"], {
            "path": "output.app_server_events",
            "method": "thread/started",
            "model_field": "message.params.thread.model",
            "reasoning_effort_field": "message.params.thread.reasoningEffort",
            "runtime_generation": 4,
            "matching_event_count": 1,
            "status": "UNIQUE_MATCH",
            "runtime_seq": 7,
        })

    def test_unmatched_thread_started_event_leaves_effective_values_unpublished(self):
        response = {"output": {
            "thread_id": "root-1", "runtime_generation": 4,
            "app_server_events": [
                {"runtime_seq": 1, "runtime_generation": 4,
                 "message": {"method": "thread/started", "params": {
                     "thread": {"id": "child-1", "model": "wrong-thread",
                                 "reasoningEffort": "high"},
                 }}},
                {"runtime_seq": 2, "runtime_generation": 3,
                 "message": {"method": "thread/started", "params": {
                     "thread": {"id": "root-1", "model": "stale-generation",
                                 "reasoningEffort": "high"},
                 }}},
            ],
        }}

        facts = preflight.request_configuration(self.request(), response)

        self.assertIsNone(facts["service_reported_effective_model"])
        self.assertEqual(facts["effective_model_status"], "NOT_EXPOSED_BY_CURRENT_SERVICE")
        self.assertIsNone(facts["service_reported_effective_reasoning_effort"])
        self.assertEqual(facts["effective_reasoning_effort_status"],
                         "NOT_EXPOSED_BY_CURRENT_SERVICE")
        self.assertEqual(facts["effective_configuration_source"]["matching_event_count"], 0)
        self.assertEqual(facts["effective_configuration_source"]["status"],
                         "NOT_EXPOSED_BY_CURRENT_SERVICE")

    def test_missing_effective_field_is_not_copied_from_requested_value(self):
        response = {"output": {
            "thread_id": "root-1", "runtime_generation": 4,
            "app_server_events": [{
                "runtime_seq": 7, "runtime_generation": 4,
                "message": {"method": "thread/started", "params": {
                    "thread": {"id": "root-1", "model": "gpt-5.6-luna"},
                }},
            }],
        }}

        facts = preflight.request_configuration(self.request(), response)

        self.assertEqual(facts["requested_model"], "gpt-6-luna")
        self.assertEqual(facts["service_reported_effective_model"], "gpt-5.6-luna")
        self.assertEqual(facts["effective_model_status"], "OBSERVED")
        self.assertEqual(facts["requested_reasoning_effort"], "low")
        self.assertIsNone(facts["service_reported_effective_reasoning_effort"])
        self.assertEqual(facts["effective_reasoning_effort_status"],
                         "NOT_EXPOSED_BY_CURRENT_SERVICE")

    def test_empty_or_non_string_effective_fields_are_marked_invalid(self):
        response = {"output": {
            "thread_id": "root-1", "runtime_generation": 4,
            "app_server_events": [{
                "runtime_seq": 7, "runtime_generation": 4,
                "message": {"method": "thread/started", "params": {
                    "thread": {"id": "root-1", "model": "",
                               "reasoningEffort": 2},
                }},
            }],
        }}

        facts = preflight.request_configuration(self.request(), response)

        self.assertEqual(facts["service_reported_effective_model"], "")
        self.assertEqual(facts["effective_model_status"],
                         "INVALID_SERVICE_REPORTED_VALUE")
        self.assertEqual(facts["service_reported_effective_reasoning_effort"], 2)
        self.assertEqual(facts["effective_reasoning_effort_status"],
                         "INVALID_SERVICE_REPORTED_VALUE")

    def test_duplicate_root_thread_started_events_are_not_treated_as_unique(self):
        thread_event = {
            "runtime_generation": 4,
            "message": {"method": "thread/started", "params": {
                "thread": {"id": "root-1", "model": "gpt-5.6-luna",
                            "reasoningEffort": "medium"},
            }},
        }
        response = {"output": {
            "thread_id": "root-1", "runtime_generation": 4,
            "app_server_events": [
                {"runtime_seq": 7, **thread_event},
                {"runtime_seq": 8, **thread_event},
            ],
        }}

        facts = preflight.request_configuration(self.request(), response)

        self.assertIsNone(facts["service_reported_effective_model"])
        self.assertEqual(facts["effective_model_status"],
                         "AMBIGUOUS_THREAD_STARTED_EVENT")
        self.assertIsNone(facts["service_reported_effective_reasoning_effort"])
        self.assertEqual(facts["effective_reasoning_effort_status"],
                         "AMBIGUOUS_THREAD_STARTED_EVENT")
        self.assertEqual(facts["effective_configuration_source"]["matching_event_count"], 2)
        self.assertEqual(facts["effective_configuration_source"]["status"],
                         "AMBIGUOUS_THREAD_STARTED_EVENT")

    def proof(self, **updates):
        result = {
            "schema": preflight.PROBE_SCHEMA,
            "state": "PASS",
            "transfer_root": self.root,
            "marker_name": preflight.MARKER_NAME,
            "operations": ["create", "read_and_verify", "delete", "confirm_absent"],
            "marker_sha256": self.marker_sha,
            "read_matches": True,
            "absent_after_delete": True,
        }
        result.update(updates)
        return result

    def response(self, emitted, *, command=None, exit_code=0, status="completed"):
        command = command or self.command
        events = [
            {
                "runtime_seq": 1,
                "runtime_generation": 4,
                "message": {
                    "method": "item/started",
                    "params": {"threadId": "root-1", "turnId": "turn-1",
                               "item": {"id": "cmd-1", "type": "commandExecution",
                                        "command": command}},
                },
            },
            {
                "runtime_seq": 2,
                "runtime_generation": 4,
                "message": {
                    "method": "item/completed",
                    "params": {"threadId": "root-1", "turnId": "turn-1",
                               "item": {"id": "cmd-1", "type": "commandExecution",
                                        "command": command, "status": status,
                                        "exitCode": exit_code,
                                        "aggregatedOutput": json.dumps(emitted)}},
                },
            },
        ]
        return {"output": {"thread_id": "root-1", "turn_id": "turn-1",
                           "runtime_generation": 4, "app_server_events": events}}

    def verify(self, response):
        return preflight.verify_probe(
            response, self.command, self.root, marker_sha256=self.marker_sha)

    def test_complete_marker_chain_passes_with_shell_wrapped_event(self):
        result = self.verify(self.response(
            self.proof(),
            command=f"/bin/zsh -lc '{self.command}'",
        ))
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["runtime"]["thread_id"], "root-1")
        self.assertEqual(result["command_event"]["start_seq"], 1)
        self.assertEqual(result["command_event"]["end_seq"], 2)

    def test_permission_observation_is_blocked_not_product_failure(self):
        result = self.verify(self.response({
            "schema": preflight.PROBE_SCHEMA,
            "state": "BLOCKED",
            "reason": "permission_observation_blocked",
        }))
        self.assertEqual(result["state"], "BLOCKED")

    def test_malformed_marker_proof_is_invalid(self):
        result = self.verify(self.response(self.proof(absent_after_delete=False)))
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "marker_proof_mismatch")

    def test_missing_runtime_event_stream_is_blocked(self):
        result = self.verify({"output": {"thread_id": "root-1", "turn_id": "turn-1",
                                         "runtime_generation": 4}})
        self.assertEqual(result["state"], "BLOCKED")

    def test_unobserved_marker_command_is_not_tested(self):
        response = self.response(self.proof())
        response["output"]["app_server_events"] = [{
            "runtime_seq": 1,
            "runtime_generation": 4,
            "message": {"method": "turn/started",
                        "params": {"threadId": "root-1", "turnId": "turn-1",
                                   "item": {}}},
        }]
        result = self.verify(response)
        self.assertEqual(result["state"], "NOT TESTED")

    def test_generation_type_confusion_is_invalid(self):
        response = self.response(self.proof())
        response["output"]["app_server_events"][0]["runtime_generation"] = True
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "event_order_or_generation_conflict")

    def test_non_string_runtime_identity_is_invalid(self):
        response = self.response(self.proof())
        response["output"]["turn_id"] = 1
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "runtime_identity_type_invalid")

    def test_extra_command_invalidates_marker_pass(self):
        response = self.response(self.proof())
        extra_start = json.loads(json.dumps(response["output"]["app_server_events"][0]))
        extra_start["runtime_seq"] = 3
        extra_start["message"]["params"]["item"].update(
            id="extra", command="true")
        response["output"]["app_server_events"].append(extra_start)
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "unexpected_command_observed")

    def test_child_thread_command_invalidates_marker_pass(self):
        response = self.response(self.proof())
        child = json.loads(json.dumps(response["output"]["app_server_events"][0]))
        child["runtime_seq"] = 3
        child["message"]["params"]["threadId"] = "child-1"
        response["output"]["app_server_events"].append(child)
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "non_root_thread_event_observed")

    def test_child_thread_event_invalidates_marker_pass(self):
        response = self.response(self.proof())
        response["output"]["app_server_events"].append({
            "runtime_seq": 3,
            "runtime_generation": 4,
            "message": {"method": "item/started",
                        "params": {"threadId": "child-1", "turnId": "child-turn",
                                   "item": {"type": "agentMessage"}}},
        })
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "non_root_thread_event_observed")

    def test_delegation_event_invalidates_marker_pass(self):
        response = self.response(self.proof())
        response["output"]["app_server_events"].append({
            "runtime_seq": 3,
            "runtime_generation": 4,
            "message": {"method": "item/completed",
                        "params": {"threadId": "root-1", "turnId": "turn-1",
                                   "item": {"type": "collabAgentToolCall",
                                            "senderThreadId": "root-1",
                                            "tool": "wait",
                                            "receiverThreadIds": ["child-1"]}}},
        })
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "agent_or_delegation_event_observed")

    def test_subagent_activity_event_invalidates_marker_pass(self):
        response = self.response(self.proof())
        response["output"]["app_server_events"].append({
            "runtime_seq": 3,
            "runtime_generation": 4,
            "message": {"method": "item/started",
                        "params": {"threadId": "root-1", "turnId": "turn-1",
                                   "item": {"type": "subAgentActivity",
                                            "agentThreadId": "child-1",
                                            "agentPath": "/agent/path"}}},
        })
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "agent_or_delegation_event_observed")

    def test_thread_relation_invalidates_marker_pass(self):
        response = self.response(self.proof())
        response["output"]["thread_relations"] = [{
            "tool": "spawnAgent", "sender_thread_id": "root-1",
            "receiver_thread_ids": ["child-1"],
        }]
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "thread_relation_observed")

    def test_normal_root_agent_message_does_not_count_as_delegation(self):
        response = self.response(self.proof())
        response["output"]["app_server_events"].append({
            "runtime_seq": 3,
            "runtime_generation": 4,
            "message": {"method": "item/started",
                        "params": {"threadId": "root-1", "turnId": "turn-1",
                                   "item": {"type": "agentMessage"}}},
        })
        response["output"]["app_server_events"].append({
            "runtime_seq": 4,
            "runtime_generation": 4,
            "message": {"method": "item/agentMessage/delta",
                        "params": {"threadId": "root-1", "turnId": "turn-1"}},
        })
        result = self.verify(response)
        self.assertEqual(result["state"], "PASS")

    def test_missing_after_directory_cannot_support_pass(self):
        before = {"root": self.root, "present": True, "complete": True, "entries": {}}
        after = {"root": self.root, "present": False, "complete": True, "entries": {}}
        self.assertFalse(preflight.snapshots_are_complete_empty_same_root(
            before, after, self.root))

    def test_snapshot_root_must_match(self):
        before = {"root": self.root, "present": True, "complete": True, "entries": {}}
        after = {"root": "/private/tmp/other", "present": True,
                 "complete": True, "entries": {}}
        self.assertFalse(preflight.snapshots_are_complete_empty_same_root(
            before, after, self.root))

    def test_transfer_root_requires_dedicated_private_tmp_run_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "transfer"
            root.mkdir()
            with self.assertRaisesRegex(ValueError, "dedicated_private_tmp"):
                preflight.validate_transfer_root(root, [])

    def test_run_directory_prefix_matches_r37_plan(self):
        self.assertEqual(preflight.RUN_ROOT_PREFIX,
                         "pc68-r37-transfer-eval-preflight-")

    def test_stale_r33_run_directory_prefix_is_rejected(self):
        with tempfile.TemporaryDirectory(
                prefix="pc68-r33-transfer-eval-preflight-", dir="/private/tmp") as temporary:
            root = Path(temporary) / "transfer"
            root.mkdir()
            with self.assertRaisesRegex(ValueError, "dedicated_private_tmp"):
                preflight.validate_transfer_root(root, [])

    def test_wrong_turn_is_invalid(self):
        response = self.response(self.proof())
        response["output"]["app_server_events"][0]["message"]["params"]["turnId"] = "other"
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "command_turn_mismatch")

    def test_duplicate_command_completion_is_invalid(self):
        response = self.response(self.proof())
        duplicate = json.loads(json.dumps(response["output"]["app_server_events"][1]))
        duplicate["runtime_seq"] = 3
        response["output"]["app_server_events"].append(duplicate)
        result = self.verify(response)
        self.assertEqual(result["state"], "INVALID_TEST_EXECUTION")
        self.assertEqual(result["reason"], "marker_command_not_unique")

    def test_embedded_probe_source_compiles(self):
        compile(preflight.marker_probe_source(), "marker_probe.py", "exec")


if __name__ == "__main__":
    unittest.main()
