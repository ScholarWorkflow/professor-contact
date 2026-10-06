"""Non-acceptance checks for r25 R1-7 filesystem evidence boundaries."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent / "runtime"))
import issue68_lifecycle as subject


class LifecycleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.consumer = Path(self.temp.name) / "consumer"
        self.program = self.consumer / "program"
        self.owner = self.program / "professors" / "owner-a"
        self.owner.mkdir(parents=True)
        self.pack = self.owner / "email-pack.json"
        self.pack.write_text('{"emails": []}\n')
        self.other = self.program / "other-request.json"
        self.other.write_text('{"request":"other"}\n')
        self.manifest = {"program_root": str(self.program),
                         "owners": [{"professor_dir": str(self.owner), "email_pack": str(self.pack)}],
                         "protected_other_request_files": [str(self.other)]}
        self.before = subject.collect_before(self.manifest, self.consumer)

    def evidence(self, reads=None):
        return {"schema": subject.SCHEMA, "before": copy.deepcopy(self.before),
                "after": {"phase": "after_request", "program": subject.snapshot_tree(self.program),
                          "consumer": subject.snapshot_tree(self.consumer)},
                "reads": reads or [], "lifecycle_capability": {"state": "INCOMPLETE",
                    "missing_facts": ["request_owned_cleanup_operation_observation"]}}

    def read(self, path=None, owner=None):
        return {"path": str(path or self.consumer / "handoff.json"),
                "professor_dir": str(owner or self.owner), "command_id": "command-1",
                "thread": "child-1", "generation": 1, "start": 2, "end": 3,
                "sha256": "a" * 64, "capture_id": "capture-1"}

    def check(self, evidence, verdict, reason):
        actual = subject.verify_lifecycle(evidence, self.manifest)
        self.assertEqual(actual["verdict"], verdict)
        self.assertEqual(actual["reason_code"], reason)

    def test_unchanged_files_and_absent_transfer_do_not_prove_lifecycle(self):
        self.check(self.evidence([self.read()]), "BLOCKED_OBSERVABILITY",
                   "transfer_creation_and_cleanup_unobservable")

    def test_professor_state_creation_is_product_failure(self):
        (self.owner / "email-state.json").write_text("{}")
        self.check(self.evidence(), "FAIL_PRODUCT", "professor_state_or_output_changed")

    def test_professor_output_deletion_is_product_failure(self):
        self.pack.unlink()
        self.check(self.evidence(), "FAIL_PRODUCT", "professor_state_or_output_changed")

    def test_aggregate_own_output_does_not_change_professor_claim(self):
        (self.program / "overview.md").write_text("aggregate only")
        self.check(self.evidence(), "BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable")

    def test_remnant_is_product_failure(self):
        path = self.consumer / "handoff.json"
        path.write_text("{}")
        self.check(self.evidence([self.read(path)]), "FAIL_PRODUCT", "request_transfer_file_remains")

    def test_wrong_owner_is_invalid_association(self):
        self.check(self.evidence([self.read(owner=self.program / "wrong")]),
                   "INVALID_EVIDENCE", "transfer_owner_association_invalid")

    def test_unrelated_request_deletion_is_product_failure(self):
        self.other.unlink()
        self.check(self.evidence(), "FAIL_PRODUCT", "other_request_file_changed_or_deleted")

    def test_unrelated_request_rewrite_is_product_failure(self):
        self.other.write_text("changed")
        self.check(self.evidence(), "FAIL_PRODUCT", "other_request_file_changed_or_deleted")

    def test_preexisting_handoff_is_not_this_request_creation(self):
        path = self.consumer / "handoff.json"
        path.write_text("{}")
        self.before = subject.collect_before(self.manifest, self.consumer)
        path.unlink()
        self.check(self.evidence([self.read(path)]), "FAIL_PRODUCT", "handoff_reused_preexisting_file")

    def test_missing_snapshot_is_invalid(self):
        evidence = self.evidence()
        del evidence["before"]
        self.check(evidence, "INVALID_EVIDENCE", "lifecycle_snapshot_or_association_invalid")

    def test_missing_read_order_is_invalid(self):
        read = self.read()
        read["start"] = None
        self.check(self.evidence([read]), "INVALID_EVIDENCE", "lifecycle_snapshot_or_association_invalid")

    def complete_evidence(self):
        handoff, choices, partition = [str(self.consumer / name) for name in
                                      ("handoff.json", "choices.json", "partition.json")]
        read = self.read()
        read.update(start=12, end=13)
        evidence = self.evidence([read])
        evidence["root_thread"] = "root"
        evidence["runtime_generation"] = 1
        returned = {"status": "ok", "owners": [{"professor_dir": str(self.owner)}]}
        evidence["partition_returns"] = [{"out_path": partition, "choices_path": choices,
            "actual_return": returned, "start": 4, "end": 5}]
        def op(kind, paths, start, output="", source="completed_command_with_successful_exit"):
            return {"operation": kind, "paths": paths, "thread": "root", "generation": 1,
                    "id": f"command-{start}", "start": start, "end": start + 1,
                    "output": output, "source": source}
        evidence["file_operations"] = [op("write", [choices], 1),
            op("write", [partition], 4, source="installed_partition_read_write_before_emit"),
            op("read", [partition], 6, json.dumps(returned)), op("write", [handoff], 9),
            op("remove", [handoff, partition, choices], 15)]
        return evidence

    def test_complete_attributable_chain_is_accepted(self):
        self.check(self.complete_evidence(), "PASS", "request_lifecycle_and_state_preservation_proven")

    def test_absent_file_without_successful_cleanup_is_not_proof(self):
        evidence = self.complete_evidence()
        evidence["file_operations"].pop()
        self.check(evidence, "BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable")

    def test_cleanup_before_read_is_not_proof(self):
        evidence = self.complete_evidence()
        evidence["file_operations"][-1].update(start=10, end=11)
        self.check(evidence, "BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable")

    def test_wrong_root_operation_is_invalid(self):
        evidence = self.complete_evidence()
        evidence["file_operations"][-1]["thread"] = "another-root"
        self.check(evidence, "INVALID_EVIDENCE", "lifecycle_operation_association_invalid")

    def test_wrong_generation_is_invalid(self):
        evidence = self.complete_evidence()
        evidence["file_operations"][-1]["generation"] = 2
        self.check(evidence, "INVALID_EVIDENCE", "lifecycle_operation_association_invalid")

    def test_integer_generation_rejects_string_generation(self):
        evidence = self.complete_evidence()
        evidence["file_operations"][-1]["generation"] = "1"
        self.check(evidence, "INVALID_EVIDENCE", "lifecycle_operation_association_invalid")

    def test_bounded_parser_does_not_evaluate_input_or_arbitrary_code(self):
        path = str(self.consumer / "handoff.json")
        self.assertEqual(subject.file_operation(f"printf '%s' '{{}}' > {path}"),
                         {"operation": "write", "paths": [path]})
        self.assertEqual(subject.file_operation(f"rm -f -- {path}"),
                         {"operation": "remove", "paths": [path]})
        self.assertIsNone(subject.file_operation(f"uv run python -c 'open(\"{path}\",\"w\")'"))
        self.assertIsNone(subject.file_operation(f"rm -f {path} && echo ok"))
        self.assertIsNone(subject.file_operation("rm -f /tmp/*"))
        self.assertIsNone(subject.file_operation("printf 'x > /tmp/handoff.json'"))
        self.assertIsNone(subject.file_operation("printf '%s' '>' /tmp/handoff.json"))
        self.assertIsNone(subject.file_operation("printf x >/tmp/handoff.json; rm /tmp/y"))
        self.assertIsNone(subject.file_operation("/tmp/fake/bash -c 'rm -f /tmp/handoff.json'"))

    def test_collector_uses_real_output_not_shell_json(self):
        envelope = {"pc68_fixed_capture": {"owner_input_file": str(self.consumer / "handoff.json"),
                    "owner_input_sha256": "a" * 64, "capture_id": "capture-1"}}
        returned = {"status": "ok", "owners": [{"professor_dir": str(self.owner)}]}
        events = []
        for index, (thread, command, output) in enumerate([
                ("root", "partition actual", returned),
                ("child", "capture actual", envelope)]):
            for offset, method in enumerate(["item/started", "item/completed"]):
                events.append({"runtime_seq": index * 2 + offset + 1, "runtime_generation": 1,
                    "message": {"method": method, "params": {"threadId": thread, "turnId": "turn",
                        "item": {"type": "commandExecution", "id": f"command-{index}",
                                 "command": command, "exitCode": 0,
                                 "aggregatedOutput": json.dumps(output)}}}})
        verifier = SimpleNamespace(command_action=lambda command, manifest:
            {"owner_capture": {}} if command == "capture actual" else
            {"action": "stage5-partition-choices"},
            consumed_business_objects=lambda calls, manifest:
            ([{"packet": {"email_pack": str(self.pack)}}], None))
        # A non-empty bound capture record matches the production parser shape.
        verifier.command_action = lambda command, manifest: (
            {"owner_capture": {"bound": True}} if command == "capture actual" else
            {"action": "stage5-partition-choices"})
        evidence = subject.collect_lifecycle(self.before, self.manifest, self.consumer,
            {"output": {"thread_id": "root", "turn_id": "turn", "runtime_generation": 1,
                        "app_server_events": events}}, verifier)
        self.assertEqual(evidence["reads"][0]["path"], envelope["pc68_fixed_capture"]["owner_input_file"])
        self.assertEqual(evidence["reads"][0]["generation"], 1)
        self.assertEqual(evidence["partition_returns"][0]["actual_return"], returned)
        self.check(evidence, "BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable")

    def test_partition_stdout_does_not_require_extra_cat(self):
        evidence = self.complete_evidence()
        evidence["file_operations"] = [op for op in evidence["file_operations"]
                                       if op["operation"] != "read"]
        self.check(evidence, "PASS", "request_lifecycle_and_state_preservation_proven")

    def test_unused_partition_out_path_is_not_mandatory(self):
        evidence = self.complete_evidence()
        evidence["partition_returns"][0]["out_path"] = None
        self.check(evidence, "PASS", "request_lifecycle_and_state_preservation_proven")

    def test_empty_quoted_file_operations_are_unobserved(self):
        for command in ("printf '' > ''", "rm ''", "cat ''", "unlink ''"):
            with self.subTest(command=command):
                self.assertIsNone(subject.file_operation(command))

    def bound_changed_state(self, events):
        request = {"input": "synthetic boundary"}
        before = subject.bind_before(copy.deepcopy(self.before), request)
        (self.owner / "email-state.json").write_text("{}")
        response = {"output": {"thread_id": "root", "turn_id": "turn",
                               "runtime_generation": 1}}
        if events != "absent":
            response["output"]["app_server_events"] = events
        verifier = SimpleNamespace(command_action=lambda command, manifest: None)
        evidence = subject.collect_lifecycle(before, self.manifest, self.consumer, response, verifier)
        request_path, before_path = self.consumer / "request.json", self.consumer / "before.json"
        request_path.write_text(json.dumps(request))
        before_path.write_text(json.dumps(before))
        manifest = {**self.manifest, "owner_capture": {"consumer_root": str(self.consumer)},
            "lifecycle_boundary": {"request_artifact": str(request_path),
                "before_artifact": str(before_path), "run_id": before["request_boundary"]["run_id"],
                "before_sha256": subject._response_digest(before),
                "after_sha256": subject._response_digest(evidence["after"])}}
        return subject.verify_bound_lifecycle(evidence, manifest, response, {}, verifier)

    def test_missing_original_events_cannot_attribute_state_failure(self):
        for events in ("absent", []):
            with self.subTest(events=events):
                actual = self.bound_changed_state(events)
                self.assertEqual(actual["verdict"], "BLOCKED_OBSERVABILITY")

    def test_malformed_original_event_stream_is_invalid(self):
        for events in ({}, [None], [{"runtime_seq": 1, "runtime_generation": 1, "message": []}]):
            with self.subTest(events=events):
                actual = self.bound_changed_state(events)
                self.assertEqual(actual["verdict"], "INVALID_EVIDENCE")

    def test_real_root_turn_proves_state_failure_without_owner_parse(self):
        events = [{"runtime_seq": 1, "runtime_generation": 1,
            "message": {"method": "turn/completed", "params": {"threadId": "root", "turnId": "turn"}}}]
        actual = self.bound_changed_state(events)
        self.assertEqual(actual["verdict"], "FAIL_PRODUCT")
        self.assertEqual(actual["reason_code"], "professor_state_or_output_changed")

    def test_child_only_stream_cannot_attribute_root_request_failure(self):
        events = [{"runtime_seq": 1, "runtime_generation": 1,
            "message": {"method": "turn/completed", "params": {"threadId": "child", "turnId": "other"}}}]
        self.assertEqual(self.bound_changed_state(events)["verdict"], "BLOCKED_OBSERVABILITY")

    def test_missing_events_do_not_hide_damaged_runtime_identity(self):
        for output in ({}, {"thread_id": "root", "turn_id": "turn", "runtime_generation": True},
                       {"thread_id": "", "turn_id": "turn", "runtime_generation": 1}):
            with self.subTest(output=output):
                with self.assertRaises(ValueError) as raised:
                    subject._commands({"output": output})
                self.assertNotIsInstance(raised.exception, subject.MissingEventObservation)

    def test_wrong_root_turn_is_invalid_before_state_attribution(self):
        events = [{"runtime_seq": 1, "runtime_generation": 1,
            "message": {"method": "turn/completed", "params": {"threadId": "root", "turnId": "old-turn"}}}]
        self.assertEqual(self.bound_changed_state(events)["verdict"], "INVALID_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
