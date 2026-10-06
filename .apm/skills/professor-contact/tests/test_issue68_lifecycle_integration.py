"""Synthetic integration checks; these never send a formal business request."""
import copy
import json
import hashlib
import shlex
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent / "runtime"))
import issue68_lifecycle as lifecycle
import verify_issue68_stage5_routing_r19 as verifier
import test_issue68_lifecycle as snapshot_tests
import test_issue68_runtime_r19 as business_tests


class BoundLifecycleTests(unittest.TestCase):
    setUp = snapshot_tests.LifecycleEvidenceTests.setUp
    def bound_fixture(self):
        root, child, turn = "root", "child", "root-turn"
        paths = {name: str(self.consumer / (name + ".json"))
                 for name in ("choices", "partition", "handoff")}
        returned = {"status": "ok", "owners": [{"professor_dir": str(self.owner)}]}
        envelope = {"pc68_fixed_capture": {"owner_input_file": paths["handoff"],
            "owner_input_sha256": "a" * 64, "capture_id": "capture"}}
        events = []
        def call(command, output="", thread=root):
            identifier = "call-" + str(len(events))
            for method in ("item/started", "item/completed"):
                events.append({"runtime_seq": len(events) + 1, "runtime_generation": 1,
                    "message": {"method": method, "params": {"threadId": thread,
                        "turnId": turn if thread == root else "child-turn",
                        "item": {"type": "commandExecution", "id": identifier,
                            "command": command, "aggregatedOutput": output, "exitCode": 0}}}})
        call("printf '{}' > " + paths["choices"])
        call("partition actual", json.dumps(returned))
        call("cat " + paths["partition"], json.dumps(returned))
        call("printf '{}' > " + paths["handoff"])
        call("capture actual", json.dumps(envelope), child)
        call("rm -f -- " + " ".join(paths.values()))
        response = {"output": {"thread_id": root, "turn_id": turn,
                               "runtime_generation": 1, "app_server_events": events}}
        adapter = {"fixture_status": "FIXTURE_READY", "dispatch": {"thread_relations": [
            {"tool": "spawnAgent", "sender_thread_id": root, "receiver_thread_ids": [child]}]}}
        def action(command, manifest):
            if command == "capture actual":
                return {"owner_capture": {"bound": True}}
            if command == "partition actual":
                return {"action": "stage5-partition-choices", "flags": {
                    "--choices": paths["choices"], "--out": paths["partition"]}}
            return None
        oracle = SimpleNamespace(command_action=action,
            consumed_business_objects=lambda calls, manifest: ([{"packet": {
                "professor_dir": str(self.owner), "email_pack": str(self.pack)}}], None))
        request = {"input": "synthetic lifecycle", "cwd": str(self.consumer)}
        before = lifecycle.bind_before(copy.deepcopy(self.before), request)
        request_path, before_path = self.consumer / "request.json", self.consumer / "before.json"
        request_path.write_text(json.dumps(request))
        before_path.write_text(json.dumps(before))
        evidence = lifecycle.collect_lifecycle(before, self.manifest, self.consumer, response, oracle)
        self.manifest["owner_capture"] = {"consumer_root": str(self.consumer)}
        self.manifest["lifecycle_boundary"] = {"run_id": before["request_boundary"]["run_id"],
            "request_artifact": str(request_path), "before_artifact": str(before_path),
            "before_sha256": lifecycle._response_digest(before),
            "after_sha256": lifecycle._response_digest(evidence["after"])}
        return evidence, response, adapter, oracle

    def bound_check(self, evidence, response, adapter, oracle):
        return lifecycle.verify_bound_lifecycle(evidence, self.manifest, response, adapter, oracle)

    def test_original_events_and_complete_chain_pass(self):
        self.assertEqual(self.bound_check(*self.bound_fixture())["verdict"], "PASS")

    def test_fabricated_ledger_operation_is_invalid(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        evidence["file_operations"][0]["end"] += 1
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "INVALID_EVIDENCE")

    def test_changed_response_is_invalid_before_snapshot_failure(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        response["output"]["runtime_generation"] = "1"
        evidence["after"]["program"]["entries"].pop("other-request.json")
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "INVALID_EVIDENCE")

    def test_same_call_requires_matching_child_turn(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        response["output"]["app_server_events"][9]["message"]["params"]["turnId"] = "wrong-turn"
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "INVALID_EVIDENCE")

    def test_null_call_id_is_invalid(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        response["output"]["app_server_events"][0]["message"]["params"]["item"]["id"] = None
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "INVALID_EVIDENCE")

    def test_owner_capture_requires_formal_child_relation(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        adapter["dispatch"]["thread_relations"] = []
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "INVALID_EVIDENCE")

    def test_snapshot_failure_with_valid_boundary_is_product_failure(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        evidence["after"]["program"]["entries"].pop("other-request.json")
        self.manifest["lifecycle_boundary"]["after_sha256"] = lifecycle._response_digest(evidence["after"])
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "FAIL_PRODUCT")

    def test_request_mismatch_is_invalid(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        Path(self.manifest["lifecycle_boundary"]["request_artifact"]).write_text("{}")
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "INVALID_EVIDENCE")

    def test_formal_entry_cannot_pass_without_lifecycle(self):
        with mock.patch.object(verifier, "_verify_codex_business", return_value={"verdict": "PASS"}):
            result = verifier.verify_codex({}, {}, {})
        self.assertEqual(result["verdict"], "BLOCKED_OBSERVABILITY")

    def test_formal_entry_preserves_proven_root_failure(self):
        with mock.patch.object(verifier, "_verify_codex_business", return_value={
                "verdict": "FAIL_PRODUCT", "reason_code": "discovery_emits_choices_scope"}):
            result = verifier.verify_codex({}, {}, {"lifecycle_evidence": {}})
        self.assertEqual(result["reason_code"], "discovery_emits_choices_scope")

    def test_formal_entry_invokes_bound_verifier_before_acceptance(self):
        with mock.patch.object(verifier, "_verify_codex_business", return_value={"verdict": "PASS"}), \
                mock.patch.object(lifecycle, "verify_bound_lifecycle", return_value={
                    "verdict": "FAIL_PRODUCT", "reason_code": "request_transfer_file_remains"}) as judge:
            result = verifier.verify_codex({}, {}, {"lifecycle_evidence": {}})
        judge.assert_called_once()
        self.assertEqual(result["verdict"], "FAIL_PRODUCT")

    def test_independent_bound_state_failure_survives_business_invalidity(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        evidence["after"]["program"]["entries"].pop("other-request.json")
        self.manifest["lifecycle_boundary"]["after_sha256"] = lifecycle._response_digest(evidence["after"])
        self.manifest["lifecycle_evidence"] = evidence
        # The business fixture reloads the module through importlib. Bind the
        # synthetic parser and entrypoint to the same current module that the
        # lifecycle entry retrieves from sys.modules for raw-fact rebuilding.
        current_verifier = sys.modules[verifier.__name__]
        with mock.patch.object(current_verifier, "_verify_codex_business", return_value={
                "verdict": "INVALID_EVIDENCE", "reason_code": "root_final_source_ambiguous"}), \
                mock.patch.object(current_verifier, "command_action", side_effect=oracle.command_action), \
                mock.patch.object(current_verifier, "consumed_business_objects", side_effect=oracle.consumed_business_objects):
            result = current_verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "other_request_file_changed_or_deleted"))

    def test_invalid_lifecycle_cannot_invent_failure_over_business_invalidity(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        evidence["after"]["program"]["entries"].pop("other-request.json")
        self.manifest["lifecycle_evidence"] = evidence
        with mock.patch.object(verifier, "_verify_codex_business", return_value={
                "verdict": "INVALID_EVIDENCE", "reason_code": "root_final_source_ambiguous"}):
            result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["reason_code"], "root_final_source_ambiguous")

    def test_quoted_redirection_does_not_invalidate_successful_actual_use(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        for event in response["output"]["app_server_events"][:2]:
            event["message"]["params"]["item"]["command"] = "printf 'x > /tmp/handoff.json'"
        evidence = lifecycle.collect_lifecycle(evidence["before"], self.manifest, self.consumer,
                                             response, oracle)
        self.manifest["lifecycle_boundary"]["after_sha256"] = lifecycle._response_digest(evidence["after"])
        result = self.bound_check(evidence, response, adapter, oracle)
        self.assertEqual(result["verdict"], "PASS")

    def test_unrelated_false_exit_does_not_invalidate_actual_use(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        response["output"]["app_server_events"][1]["message"]["params"]["item"]["exitCode"] = False
        evidence = lifecycle.collect_lifecycle(evidence["before"], self.manifest, self.consumer,
                                             response, oracle)
        self.manifest["lifecycle_boundary"]["after_sha256"] = lifecycle._response_digest(evidence["after"])
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "PASS")

    def test_deleted_program_with_valid_boundary_is_product_failure(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        evidence["after"]["program"].update(present=False, entries={})
        self.manifest["lifecycle_boundary"]["after_sha256"] = lifecycle._response_digest(evidence["after"])
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "FAIL_PRODUCT")

    def test_independent_state_failure_survives_unobservable_owner_parse(self):
        evidence, response, adapter, oracle = self.bound_fixture()
        oracle.consumed_business_objects = lambda calls, manifest: ([], {
            "verdict": "BLOCKED_OBSERVABILITY", "reason_code": "owner_actual_input_unobservable"})
        evidence = lifecycle.collect_lifecycle(evidence["before"], self.manifest, self.consumer,
                                             response, oracle)
        evidence["after"]["program"]["entries"].pop("other-request.json")
        self.manifest["lifecycle_boundary"]["after_sha256"] = lifecycle._response_digest(evidence["after"])
        self.assertEqual(self.bound_check(evidence, response, adapter, oracle)["verdict"], "FAIL_PRODUCT")


class ComposedEntryTests(unittest.TestCase):
    """Exercise both real oracles; only service event transport is synthetic.

    The pinned capture actually parses each handoff and invokes the installed
    product CLI. Expectations are prepared before those invocations. No oracle,
    command parser, input parser, or lifecycle collector is replaced.
    """
    def setUp(self):
        self.fixture = business_tests.OwnerObservationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        f = self.fixture
        self.manifest = f.manifest
        self.packets = [copy.deepcopy(f.packet)]
        self.handoffs = [f.handoff_file]
        second_dir = f.prof.parent / "丙教授"
        second_dir.mkdir()
        second_pack = second_dir / "邮件输入.json"
        email = copy.deepcopy(f.email)
        email.update(professor="丙教授", professor_dir=str(second_dir), email_id="D002::I002")
        second_pack.write_text(json.dumps({"schema": 3,
            "kind": "professor-contact-email-input", "professor": "丙教授",
            "professor_dir": str(second_dir), "emails": [email]}, ensure_ascii=False))
        packet = copy.deepcopy(f.packet)
        packet.update(professor_dir=str(second_dir), email_pack=str(second_pack),
            email_id=email["email_id"], result=str(f.root / "second-result.json"),
            choices=[{"email_id": email["email_id"], "first_choice": True}])
        self.packets.append(packet)
        self.handoffs.append(f.root / "second-input.json")
        owner = copy.deepcopy(self.manifest["owners"][0])
        owner.update(professor="丙教授", professor_dir=str(second_dir), email_pack=str(second_pack),
                     email_ids=[email["email_id"]], result=packet["result"],
                     expected_choices_rows=packet["choices"])
        self.manifest["owners"].append(owner)
        self.manifest["pre_run_hashes"][str(second_pack)] = hashlib.sha256(second_pack.read_bytes()).hexdigest()
        self.manifest["partition"]["owners"].append({"professor_dir": str(second_dir),
            "email_pack": str(second_pack), "email_id": email["email_id"], "status": "ok",
            "choices_rows": copy.deepcopy(packet["choices"])})
        self.manifest["invalid_pack"] = str(f.root / "invalid-pack.json")
        self.other = f.root / "other-request.json"
        self.other.write_text('{"request":"other"}')
        self.manifest["protected_other_request_files"] = [str(self.other)]
        for owner in self.manifest["owners"]:
            owner["expected_result"] = {"status": "needs_refresh", "reason_code": "needs_recheck"}
        for packet in self.packets:
            packet.pop("email_id")
        for owner in self.manifest["partition"]["owners"]:
            owner["email_id"] = None
        # Product partition identity is canonical. macOS may expose /var as
        # an alias of /private/var; establish canonical expectations beforehand.
        def canonical(value):
            if isinstance(value, dict):
                return {key: canonical(member) for key, member in value.items()}
            if isinstance(value, list):
                return [canonical(member) for member in value]
            return str(Path(value).resolve()) if isinstance(value, str) and value.startswith("/") else value
        self.manifest = canonical(self.manifest)
        self.packets = canonical(self.packets)
        for name in ("root", "prof", "pack", "template", "handoff_file", "consumer"):
            setattr(f, name, getattr(f, name).resolve())
        f.command_argv = canonical(f.command_argv)
        self.handoffs = [path.resolve() for path in self.handoffs]
        self.other = self.other.resolve()
        self.manifest["pre_run_hashes"] = {}
        for owner in self.manifest["owners"]:
            pack_path = Path(owner["email_pack"])
            pack_path.write_text(json.dumps(canonical(json.loads(pack_path.read_text())), ensure_ascii=False))
            self.manifest["pre_run_hashes"][str(pack_path)] = hashlib.sha256(pack_path.read_bytes()).hexdigest()
        f.handoff_file.unlink()
        Path(self.manifest["owner_capture"]["manifest_path"]).write_text(json.dumps(self.manifest))

    def composed_fixture(self, *, cleanup=True, mutation=None):
        f = self.fixture
        claimed_output = f.root / "unlisted-other-request-output"
        if mutation in ("overview_rewrite", "owner_result_rewrite", "overview_directory_delete"):
            if mutation == "overview_directory_delete":
                claimed_output.mkdir()
            else:
                claimed_output.write_text("other request original bytes")
            if mutation == "owner_result_rewrite":
                self.manifest["owners"][0]["result"] = str(claimed_output)
                self.packets[0]["result"] = str(claimed_output)
                Path(self.manifest["owner_capture"]["manifest_path"]).write_text(json.dumps(self.manifest))
        request = {"input": "synthetic composed entry", "cwd": str(f.consumer)}
        before = lifecycle.bind_before(lifecycle.collect_before(self.manifest, f.consumer), request)
        # Boundary artifacts are outside the observed consumer/program trees.
        artifact_dir = Path(f.temp.name)
        request_path, before_path = artifact_dir / "request.json", artifact_dir / "before.json"
        request_path.write_text(json.dumps(request))
        before_path.write_text(json.dumps(before))
        events = []
        root = "synthetic-root"
        def event(method, item, thread=root):
            events.append({"runtime_seq": len(events) + 1, "runtime_generation": 1,
                "message": {"method": method, "params": {"threadId": thread,
                    "turnId": "root-turn" if thread == root else thread + "-turn", "item": item}}})
        def command(text, output="", thread=root, execute=False):
            if execute:
                completed = subprocess.run(text, shell=True, cwd=f.consumer,
                                           capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                output = completed.stdout
            item = {"type": "commandExecution", "id": "call-" + str(len(events)), "command": text}
            event("item/started", item, thread)
            event("item/completed", dict(item, aggregatedOutput=output, exitCode=0), thread)
        def product(action, *flags):
            return shlex.join(["uv", "run", "python", str(f.entrypoint), action,
                               "--program-root", str(f.root), *flags])
        choices_path = f.root / "original-choices.json"
        partition_path = f.root / "partition.json"
        original_choices = [row for packet in self.packets for row in packet["choices"]]
        original_choices.append({"email_id": "unselected::noise", "transport_sentinel": "noise"})
        choices_path.write_text(json.dumps(original_choices))
        discovered = [{"email_pack": owner["email_pack"], "status": "ok"}
                      for owner in self.manifest["owners"]]
        discovered.append({"email_pack": self.manifest["invalid_pack"], "status": "error"})
        command(product("stage5-list-inputs"), json.dumps({"status": "ok", "inputs": discovered}))
        owner_flags = [token for owner in self.manifest["owners"]
                       for token in ("--owner", owner["email_pack"])]
        command(product("stage5-partition-choices", "--choices", str(choices_path),
                        "--out", str(partition_path), *owner_flags), execute=True)
        command("cat " + shlex.quote(str(partition_path)), execute=True)
        outcomes = []
        for index, (packet, handoff, owner) in enumerate(zip(
                self.packets, self.handoffs, self.manifest["owners"])):
            child, path = "child-" + str(index), "/root/owner-" + str(index)
            handoff.write_text(json.dumps(packet, ensure_ascii=False))
            argv = list(f.command_argv)
            argv[argv.index("--owner-input-file") + 1] = str(handoff)
            command(shlex.join(argv), thread=child, execute=True)
            outcome = dict(owner["expected_result"], professor_dir=owner["professor_dir"])
            outcomes.append(outcome)
            event("item/completed", {"type": "subAgentActivity", "agentThreadId": child,
                                      "agentPath": path})
            event("rawResponseItem/completed", {"type": "message", "role": "assistant",
                "phase": "final_answer", "content": [{"type": "output_text", "text": json.dumps(outcome)}]}, child)
            body = "Message Type: FINAL_ANSWER\nTask name: /root\nSender: " + path + "\nPayload:\n" + json.dumps(outcome)
            event("rawResponseItem/completed", {"type": "agent_message", "recipient": "/root",
                "author": path, "content": [{"type": "input_text", "text": body}]})
        overview = {"status": "ok", "overview_md": str(f.root / "overview.md"),
                    "professors": 2, "emails": 0}
        if mutation in ("overview_rewrite", "overview_directory_delete"):
            overview["overview_md"] = str(claimed_output)
        command(product("stage5-rebuild-overview"), json.dumps(overview))
        if cleanup:
            for path in [choices_path, partition_path, *self.handoffs]:
                path.unlink()
        if mutation == "other":
            self.other.write_text("changed by synthetic request")
        if mutation in ("overview_rewrite", "owner_result_rewrite"):
            claimed_output.write_text("claimed output replaced other request")
        if mutation == "overview_directory_delete":
            claimed_output.rmdir()
        event("rawResponseItem/completed", {"type": "message", "role": "assistant",
            "phase": "final_answer", "content": [{"type": "output_text", "text": json.dumps([*outcomes, overview])}]})
        response = {"output": {"thread_id": root, "turn_id": "root-turn", "runtime_generation": 1,
                    "termination_reason": "completed", "app_server_events": events}}
        adapter = {"fixture_status": "FIXTURE_READY", "dispatch": {"thread_relations": [
            {"tool": "spawnAgent", "sender_thread_id": root, "receiver_thread_ids": ["child-0", "child-1"]}]}}
        evidence = lifecycle.collect_lifecycle(before, self.manifest, f.consumer, response, verifier)
        self.manifest["lifecycle_evidence"] = evidence
        self.manifest["lifecycle_boundary"] = {"run_id": before["request_boundary"]["run_id"],
            "request_artifact": str(request_path), "before_artifact": str(before_path),
            "before_sha256": lifecycle._response_digest(before),
            "after_sha256": lifecycle._response_digest(evidence["after"])}
        Path(self.manifest["owner_capture"]["manifest_path"]).write_text(json.dumps(self.manifest))
        return response, adapter

    def test_complete_unmocked_formal_entry_passes(self):
        response, adapter = self.composed_fixture()
        result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS", result)
        self.assertEqual(result["request_lifecycle"]["verdict"], "PASS")

    def test_unmocked_entry_without_mutation_commands_still_passes(self):
        response, adapter = self.composed_fixture()
        events = response["output"]["app_server_events"]
        events[:] = [event for event in events if not event["message"]["params"]["item"].get("command", "").startswith("rm -f --")]
        # Recollect the altered synthetic stream instead of forging a ledger.
        before = self.manifest["lifecycle_evidence"]["before"]
        evidence = lifecycle.collect_lifecycle(before, self.manifest, self.fixture.consumer, response, verifier)
        self.manifest["lifecycle_evidence"] = evidence
        self.manifest["lifecycle_boundary"]["after_sha256"] = lifecycle._response_digest(evidence["after"])
        Path(self.manifest["owner_capture"]["manifest_path"]).write_text(json.dumps(self.manifest))
        result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "PASS", result)

    def test_unmocked_entry_actual_handoff_remnant_fails(self):
        response, adapter = self.composed_fixture(cleanup=False)
        result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "request_transfer_file_remains"), result)

    def test_unmocked_entry_actual_other_request_rewrite_fails(self):
        response, adapter = self.composed_fixture(mutation="other")
        result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "other_request_file_changed_or_deleted"), result)

    def test_unmocked_entry_overview_cannot_authorize_existing_file_rewrite(self):
        response, adapter = self.composed_fixture(mutation="overview_rewrite")
        result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "other_request_file_changed_or_deleted"), result)

    def test_unmocked_entry_overview_cannot_authorize_existing_directory_deletion(self):
        response, adapter = self.composed_fixture(mutation="overview_directory_delete")
        result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "other_request_file_changed_or_deleted"), result)

    def test_unmocked_entry_owner_result_cannot_authorize_existing_file_rewrite(self):
        response, adapter = self.composed_fixture(mutation="owner_result_rewrite")
        result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual((result["verdict"], result["reason_code"]),
                         ("FAIL_PRODUCT", "other_request_file_changed_or_deleted"), result)

    def test_unmocked_entry_damaged_request_boundary_is_invalid(self):
        response, adapter = self.composed_fixture()
        self.manifest["lifecycle_boundary"]["run_id"] = "unrelated-request"
        Path(self.manifest["owner_capture"]["manifest_path"]).write_text(json.dumps(self.manifest))
        result = verifier.verify_codex(response, adapter, self.manifest)
        self.assertEqual(result["verdict"], "INVALID_EVIDENCE", result)


if __name__ == "__main__":
    unittest.main()
