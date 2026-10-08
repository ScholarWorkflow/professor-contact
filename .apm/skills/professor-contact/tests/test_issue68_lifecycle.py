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
                "root_thread": "root", "runtime_generation": 1,
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

    def collect_partition_output(self, output):
        events = []
        item = {"type": "commandExecution", "id": "partition-call",
                "command": "partition actual"}
        for seq, method in enumerate(("item/started", "item/completed"), 1):
            completed = dict(item)
            if method == "item/completed":
                completed.update(aggregatedOutput=output, exitCode=0)
            events.append({"runtime_seq": seq, "runtime_generation": 1,
                "message": {"method": method, "params": {"threadId": "root",
                    "turnId": "turn", "item": completed}}})
        response = {"output": {"thread_id": "root", "turn_id": "turn",
                    "runtime_generation": 1, "app_server_events": events}}
        action = {"action": "stage5-partition-choices", "flags": {
            "--choices": str(self.consumer / "choices.json"),
            "--out": str(self.consumer / "partition.json")}}
        verifier = SimpleNamespace(command_action=lambda command, manifest: action,
            consumed_business_objects=lambda calls, manifest: ([], None))
        return subject.collect_lifecycle(self.before, self.manifest, self.consumer,
                                         response, verifier)

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

    def test_declared_business_output_cannot_exempt_existing_other_request_data(self):
        for declaration in ("overview", "owner_result"):
            for kind in ("file", "directory"):
                for mutation in ("rewrite", "delete"):
                    with self.subTest(declaration=declaration, kind=kind, mutation=mutation):
                        path = self.program / (declaration + "-" + kind + "-" + mutation)
                        if kind == "directory":
                            path.mkdir()
                        else:
                            path.write_text("other request")
                        self.before = subject.collect_before(self.manifest, self.consumer)
                        if kind == "directory":
                            path.rmdir()
                        else:
                            path.unlink()
                        if mutation == "rewrite":
                            path.write_text("claimed output")
                        evidence = self.complete_evidence()
                        if declaration == "overview":
                            evidence["business_outputs"] = [str(path)]
                        else:
                            self.manifest["owners"][0]["result"] = str(path)
                        self.check(evidence, "FAIL_PRODUCT", "other_request_file_changed_or_deleted")

    def test_failed_partition_cannot_exempt_existing_other_request_data(self):
        for key in ("choices_path", "out_path"):
            with self.subTest(key=key):
                path = self.program / (key + "-other-request.json")
                path.write_text("other request")
                self.before = subject.collect_before(self.manifest, self.consumer)
                path.write_text("overwritten by failed partition")
                evidence = self.complete_evidence()
                evidence["partition_returns"][0].update({key: str(path),
                    "actual_return": {"status": "error"}, "exit_code": 1})
                self.check(evidence, "FAIL_PRODUCT", "other_request_file_changed_or_deleted")

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
            "actual_return": returned, "start": 4, "end": 5, "exit_code": 0,
            "command_id": "partition-call", "thread": "root", "generation": 1}]
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

    def test_absent_used_file_without_cleanup_command_is_proof(self):
        evidence = self.complete_evidence()
        evidence["file_operations"].pop()
        self.check(evidence, "PASS", "request_lifecycle_and_state_preservation_proven")

    def test_auxiliary_remove_order_does_not_replace_real_read(self):
        evidence = self.complete_evidence()
        evidence["file_operations"][-1].update(start=10, end=11)
        self.check(evidence, "PASS", "request_lifecycle_and_state_preservation_proven")

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

    def test_collector_distinguishes_unparseable_partition_output_from_json_null(self):
        malformed = self.collect_partition_output("{malformed")
        malformed_return = malformed["partition_returns"][0]
        self.assertIsNone(malformed_return["actual_return"])
        self.assertEqual(malformed_return["actual_return_parse_state"], "invalid_json")
        self.assertEqual(malformed["lifecycle_capability"]["proof"], {
            "verdict": "INVALID_EVIDENCE",
            "reason_code": "lifecycle_partition_return_unparseable"})

        null_result = self.collect_partition_output("null")
        null_return = null_result["partition_returns"][0]
        self.assertIsNone(null_return["actual_return"])
        self.assertEqual(null_return["actual_return_parse_state"], "parsed")
        self.assertEqual(null_result["lifecycle_capability"]["proof"], {
            "verdict": "BLOCKED_OBSERVABILITY",
            "reason_code": "transfer_creation_and_cleanup_unobservable"})

    def test_partition_stdout_does_not_require_extra_cat(self):
        evidence = self.complete_evidence()
        evidence["file_operations"] = [op for op in evidence["file_operations"]
                                       if op["operation"] != "read"]
        self.check(evidence, "PASS", "request_lifecycle_and_state_preservation_proven")

    def test_programmatic_creation_cleanup_needs_no_mutation_commands(self):
        evidence = self.complete_evidence()
        evidence["file_operations"] = []
        self.check(evidence, "PASS", "request_lifecycle_and_state_preservation_proven")

    def test_successful_partition_remnant_without_owner_read_fails(self):
        evidence = self.complete_evidence()
        evidence["reads"] = []
        path = Path(evidence["partition_returns"][0]["out_path"])
        path.write_text("{}")
        evidence["after"]["consumer"] = subject.snapshot_tree(self.consumer)
        self.check(evidence, "FAIL_PRODUCT", "request_transfer_file_remains")

    def test_incomplete_directory_record_cannot_pass(self):
        evidence = self.complete_evidence()
        evidence["before"]["consumer"]["complete"] = False
        self.check(evidence, "INVALID_EVIDENCE", "lifecycle_snapshot_or_association_invalid")

    def test_unobserved_legal_location_is_observation_gap(self):
        evidence = self.complete_evidence()
        evidence["reads"][0]["path"] = str(Path(self.temp.name) / "outside.json")
        self.check(evidence, "BLOCKED_OBSERVABILITY", "transfer_path_outside_observation_scope")

    def test_missing_middle_use_cannot_pass(self):
        evidence = self.complete_evidence()
        evidence["reads"] = []
        evidence["file_operations"] = []
        self.check(evidence, "BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable")

    def test_failed_handoff_attempt_with_formed_file_is_failure(self):
        evidence = self.complete_evidence()
        evidence["reads"] = []
        evidence["file_operations"] = []
        path = self.consumer / "failed-handoff.json"
        path.write_text("invalid JSON but actual request handoff")
        evidence["attempted_handoffs"] = [{"path": str(path), "thread": "child-1",
            "generation": 1, "command_id": "failed-delivery", "start": 12, "end": 13}]
        evidence["after"]["consumer"] = subject.snapshot_tree(self.consumer)
        self.check(evidence, "FAIL_PRODUCT", "request_transfer_file_remains")

    def test_unattributed_new_file_prevents_complete_cleanup_claim(self):
        evidence = self.complete_evidence()
        (self.consumer / "unconsumed-transfer.json").write_text("{}")
        evidence["after"]["consumer"] = subject.snapshot_tree(self.consumer)
        self.check(evidence, "BLOCKED_OBSERVABILITY", "new_file_request_ownership_unresolved")

    def test_extra_predeclared_isolated_location_is_supported(self):
        extra = Path(self.temp.name) / "isolated-transfer"
        extra.mkdir()
        self.manifest["lifecycle_extra_observation_roots"] = [str(extra)]
        self.before = subject.collect_before(self.manifest, self.consumer)
        evidence = self.complete_evidence()
        evidence["after"]["extra_0"] = subject.snapshot_tree(extra)
        evidence["reads"][0]["path"] = str(extra / "handoff.json")
        evidence["file_operations"] = []
        self.check(evidence, "PASS", "request_lifecycle_and_state_preservation_proven")

    def test_unlisted_other_request_file_is_protected(self):
        protected = self.consumer / "another-request.data"
        protected.write_text("preserve these bytes")
        self.before = subject.collect_before(self.manifest, self.consumer)
        evidence = self.complete_evidence()
        protected.write_text("changed")
        evidence["after"]["consumer"] = subject.snapshot_tree(self.consumer)
        self.check(evidence, "FAIL_PRODUCT", "other_request_file_changed_or_deleted")

    def test_other_request_empty_directory_is_protected(self):
        protected = self.consumer / "another-request-directory"
        protected.mkdir()
        self.before = subject.collect_before(self.manifest, self.consumer)
        evidence = self.complete_evidence()
        protected.rmdir()
        evidence["after"]["consumer"] = subject.snapshot_tree(self.consumer)
        self.check(evidence, "FAIL_PRODUCT", "other_request_file_changed_or_deleted")

    def test_symlink_destination_was_not_scanned(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.consumer / "link").symlink_to(outside)
        self.before = subject.collect_before(self.manifest, self.consumer)
        evidence = self.complete_evidence()
        evidence["reads"][0]["path"] = str(self.consumer / "link" / "handoff.json")
        self.check(evidence, "BLOCKED_OBSERVABILITY", "transfer_path_outside_observation_scope")

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
