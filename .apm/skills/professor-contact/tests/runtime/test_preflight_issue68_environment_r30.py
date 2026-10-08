"""Synthetic counterexamples for the pre-Gate-2 environment check."""
import copy
import json
import unittest

import preflight_issue68_environment_r30 as preflight


class EnvironmentPreflightTests(unittest.TestCase):
    def test_preflight_targets_the_r37_product_commit_used_by_formal_runner(self):
        self.assertEqual(preflight.PRODUCER_SHA,
                         "faab365d0be2bb66f2f285fdaa2927631dbf33f8")
        self.assertEqual(preflight.PRODUCER_SHA, preflight.runner.PRODUCER_REVISION)

    def test_preflight_targets_the_r37_shared_asset_commit_used_by_formal_runner(self):
        self.assertEqual(preflight.FIXTURE_SHA,
                         "d160ecb403c0f9e9c153f4b8383302a4b67664ab")
        self.assertEqual(preflight.FIXTURE_SHA, preflight.runner.FIXTURE_SHA)

    def setUp(self):
        self.expected = {"marker": "synthetic", "value": "原编号"}
        self.command = "uv run --no-project python /private/tmp/synthetic/read.py"
        self.envelope = {"schema": preflight.OBSERVATION_SCHEMA, "read_count": 1,
                         "object": self.expected, "forwarded": self.expected,
                         "child_return_code": 0}
        self.response = {"output": {"thread_id": "root", "turn_id": "turn",
                                    "runtime_generation": 1, "app_server_events": []}}
        for seq, method in enumerate(("item/started", "item/completed"), 1):
            self.response["output"]["app_server_events"].append({
                "runtime_seq": seq, "runtime_generation": 1,
                "message": {"method": method, "params": {"threadId": "root", "turnId": "turn",
                    "item": {"type": "commandExecution", "id": "call", "command": self.command,
                             "status": "completed", "exitCode": 0,
                             "aggregatedOutput": json.dumps(self.envelope)}}}})

    def verify(self):
        return preflight.verify_observation(self.response, self.expected, self.command)

    def test_valid_read_output_is_accepted(self):
        self.assertEqual(self.verify()["status"], "OBSERVATION_VERIFIED")

    def test_correct_command_text_cannot_replace_output(self):
        self.response["output"]["app_server_events"][-1]["message"]["params"]["item"]["aggregatedOutput"] = ""
        self.assertEqual(self.verify()["status"], "INVALID_TEST_EXECUTION")

    def test_missing_external_observation_is_not_product_failure(self):
        del self.response["output"]["app_server_events"]
        self.assertEqual(self.verify()["status"], "OBSERVATION_UNAVAILABLE")

    def test_corrupt_sequence_is_invalid(self):
        self.response["output"]["app_server_events"][-1]["runtime_seq"] = 1
        self.assertEqual(self.verify()["status"], "INVALID_TEST_EXECUTION")

    def test_other_thread_cannot_supply_observation(self):
        self.response["output"]["app_server_events"][-1]["message"]["params"]["threadId"] = "other"
        self.assertEqual(self.verify()["status"], "OBSERVATION_UNAVAILABLE")

    def test_missing_started_event_is_invalid(self):
        self.response["output"]["app_server_events"].pop(0)
        self.assertEqual(self.verify()["status"], "INVALID_TEST_EXECUTION")

    def test_duplicate_completion_is_invalid(self):
        event = copy.deepcopy(self.response["output"]["app_server_events"][-1])
        event["runtime_seq"] = 3
        self.response["output"]["app_server_events"].append(event)
        self.assertEqual(self.verify()["status"], "INVALID_TEST_EXECUTION")

    def test_changed_forwarding_is_rejected(self):
        self.envelope["forwarded"] = {"marker": "other", "value": "改写"}
        self.response["output"]["app_server_events"][-1]["message"]["params"]["item"]["aggregatedOutput"] = json.dumps(self.envelope)
        self.assertEqual(self.verify()["status"], "INVALID_TEST_EXECUTION")

    def test_output_overlaps_source_is_rejected_before_creation(self):
        with self.assertRaises(ValueError):
            preflight.validate_output("/private/tmp/source/out", ["/private/tmp/source"])

    def test_output_outside_private_tmp_is_rejected(self):
        with self.assertRaises(ValueError):
            preflight.validate_output("/Users/synthetic/out", [])

    def test_request_model_is_recorded_without_claiming_resolved_model(self):
        request = preflight.build_request("/private/tmp/synthetic-consumer", "合成请求")
        facts = preflight.request_configuration(request, {
            "version": "synthetic-executor-version",
            "output": {"thread_start_effective": {"sandbox": "workspace-write"}}})
        self.assertEqual(facts["requested_model"], "gpt-6-luna")
        self.assertEqual(facts["effective_model_status"], "NOT_EXPOSED_BY_CURRENT_SERVICE")
        self.assertEqual(facts["service_reported_executor_version"], "synthetic-executor-version")

    def test_changed_actual_request_model_is_rejected(self):
        request = preflight.build_request("/private/tmp/synthetic-consumer", "合成请求")
        request["command"] = request["command"].replace("gpt-6-luna", "another-model")
        with self.assertRaises(ValueError):
            preflight.request_configuration(request, {})


if __name__ == "__main__":
    unittest.main()
