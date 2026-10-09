"""Frozen-shape preflight for the issue #66 runtime classifier."""

import copy
import json
import shlex
import tempfile
import unittest
from pathlib import Path

from runtime.verify_issue66_stage3_runtime import classify, GENERATOR, VALIDATOR


def envelope(sequence, method, params):
    return {"runtime_seq": sequence, "message": {"method": method, "params": params}}


def command(sequence, thread_id, name, arguments=None, payload=None, exit_code=0):
    arguments = arguments or []
    item = {
        "type": "commandExecution", "status": "completed", "exitCode": exit_code,
        "command": "/bin/zsh -lc " + json.dumps(
            "python3 .agents/skills/professor-contact/scripts/contact_state.py "
            + name + " " + shlex.join(arguments), ensure_ascii=False),
        "aggregatedOutput": json.dumps(payload or {"status": "ok"}),
        "cwd": "/tmp",
    }
    return envelope(sequence, "item/completed", {"threadId": thread_id, "item": item})


def completed_turn(sequence, thread_id, payload):
    turn = {"status": "completed", "error": None, "items": [{
        "type": "agentMessage", "phase": "final_answer", "text": json.dumps(payload),
    }]}
    return envelope(sequence, "turn/completed", {"threadId": thread_id, "turn": turn})


def completed_text_turn(sequence, thread_id, value):
    turn = {"status": "completed", "error": None, "items": [{
        "type": "agentMessage", "phase": "final_answer", "text": value,
    }]}
    return envelope(sequence, "turn/completed", {"threadId": thread_id, "turn": turn})


def command_event(response, name):
    return next(event for event in response["output"]["app_server_events"]
                if event["message"]["method"] == "item/completed"
                and f"contact_state.py {name}" in
                event["message"]["params"].get("item", {}).get("command", ""))


def fixture_manifest():
    return {
        "schema_version": 1,
        "builder": "tests/runtime/prepare_issue55_stage3_fixture.py",
        "fixture_kind": "issue55-stage3-pre",
        "program_root": "/tmp/program",
        "professor": "Example Professor",
        "direction_id": "DIR00001",
        "input_hashes": {"套磁邮件/套磁信息.md": "profile-sha"},
    }


def generator_report(program_root, professor_dir, invocation_file, invocation_sha):
    return {
        "result": "ok", "program_root": program_root,
        "profile_path": program_root + "/套磁邮件/套磁信息.md",
        "refresh_scope": "flagged",
        "invocations": [{"professor_dir": professor_dir,
                         "invocation_file": invocation_file,
                         "invocation_sha256": invocation_sha}],
        "directions": [{"professor": "Example Professor",
                        "direction_id": "DIR00001"}],
    }


def valid_documents():
    root = "root-thread"
    generator = "generator-1"
    validator = "validator-1"
    output_file = "/tmp/validator-output.json"
    handoff_file = "/tmp/handoff.json"
    invocation_file = "/tmp/invocation/stage3-invocation.json"
    invocation_sha = "invocation-sha"
    program_root = "/tmp/program"
    professor_dir = program_root + "/教授研究/X分野/Example Professor"
    validation_file = "/tmp/validation-result.json"
    response = {"output": {
        "thread_id": root, "turn_id": "root-turn", "events": [{"type": "thread.started"}],
        "termination_reason": "completed", "exit_code": 0,
        "app_server_events": [
            envelope(1, "thread/started", {"thread": {
                "id": root, "model": "gpt-5.6-luna", "reasoningEffort": "low",
                "cliVersion": "test-version",
            }}),
            command(10, generator, "stage3-plan",
                    ["--capture-invocation", "/tmp/invocation",
                     "--professor-dir", professor_dir,
                     "--profile", program_root + "/套磁邮件/套磁信息.md",
                     "--program-root", program_root, "--refresh-scope", "flagged"],
                    {"status": "ok", "invocation_file": invocation_file,
                     "invocation_sha256": invocation_sha, "professor": "Example Professor",
                     "professor_dir": professor_dir, "refresh_scope": "flagged",
                     "profile_fingerprint": "profile-sha"}),
            command(20, generator, "stage3-finalize",
                    ["--invocation-file", invocation_file,
                     "--invocation-sha256", invocation_sha]),
            completed_turn(25, generator, generator_report(
                program_root, professor_dir, invocation_file, invocation_sha)),
            command(30, root, "stage3-prepare-validation",
                    ["--invocation-file", invocation_file,
                     "--invocation-sha256", invocation_sha, "--round", "1"], payload={
                "status": "ok", "round": 1, "handoff_file": handoff_file,
                "handoff_sha256": "handoff-sha", "output_file": output_file,
                "validation_file": validation_file, "professor_dir": professor_dir,
            }),
            command(40, validator, "stage3-write-validation",
                    ["--output-file", output_file], {"result": "ok"}),
            completed_turn(45, validator, {"result": "ok", "write_status": "written",
                                           "output_files": [output_file]}),
            command(50, root, "stage3-save-validation",
                    ["--handoff-file", handoff_file, "--handoff-sha256", "handoff-sha"],
                    {"status": "ok", "round": 1, "validation_sha256": "validation-sha",
                     "validation_file": validation_file}),
            command(60, root, "stage3-record-validation",
                    ["--handoff-file", handoff_file, "--handoff-sha256", "handoff-sha",
                     "--expected-validation-sha256", "validation-sha"],
                    {"status": "ok", "round": 1, "terminal": True,
                     "needs_correction": False,
                     "validation_input_sha256": "validation-sha",
                     "state_path": professor_dir + "/套磁候选状态.json",
                     "scopes": [{"scope": "direction:DIR00001", "result": "pass",
                                 "rounds": 1}]}),
            command(70, root, "stage3-rebuild-overview",
                    ["--program-root", program_root],
                    {"status": "ok", "overview_md": program_root +
                     "/教授研究/套磁想法候选总览.md"}),
            completed_text_turn(80, root, "已完成：" + program_root +
                                "/教授研究/套磁想法候选总览.md"),
        ],
    }}
    adapter = {
        "fixture_status": "FIXTURE_READY",
        "delegation": {"formal_child_count": 2,
                       "child_thread_ids": [generator, validator]},
        "dispatch": {"thread_relations": [
            {"tool": "spawnAgent", "sender_thread_id": root, "status": "completed",
             "runtime_seq": 5,
             "receiver_thread_ids": [generator]},
            {"tool": "spawnAgent", "sender_thread_id": root, "status": "completed",
             "runtime_seq": 35,
             "receiver_thread_ids": [validator]},
        ]},
        "child_thread_reads": {"entries": [
            {"thread_id": generator, "identity_eligible": True, "outcome": "success",
             "effective_role": GENERATOR},
            {"thread_id": validator, "identity_eligible": True, "outcome": "success",
             "effective_role": VALIDATOR},
        ]},
    }
    return response, adapter


def valid_two_round_documents():
    root = "root-thread"
    children = ["generator-1", "validator-1", "generator-2", "validator-2"]
    invocation_file = "/tmp/invocation/stage3-invocation.json"
    invocation_sha = "invocation-sha"
    program_root = "/tmp/program"
    professor_dir = program_root + "/教授研究/X分野/Example Professor"
    events = [envelope(1, "thread/started", {"thread": {
        "id": root, "model": "gpt-5.6-luna", "reasoningEffort": "low",
        "cliVersion": "test-version",
    }})]
    relations = []
    reads = []
    for round_number, (generator, validator) in enumerate(
            ((children[0], children[1]), (children[2], children[3])), start=1):
        base = (round_number - 1) * 60
        round_dir = f"/tmp/round-{round_number}"
        output_file = f"{round_dir}/validator-output.json"
        handoff_file = f"{round_dir}/handoff.json"
        handoff_sha = f"handoff-sha-{round_number}"
        validation_sha = f"validation-sha-{round_number}"
        validation_file = f"{round_dir}/validation-result.json"
        if round_number == 1:
            plan_arguments = ["--capture-invocation", "/tmp/invocation",
                              "--professor-dir", professor_dir,
                              "--profile", program_root + "/套磁邮件/套磁信息.md",
                              "--program-root", program_root,
                              "--refresh-scope", "flagged"]
            plan_payload = {"status": "ok", "invocation_file": invocation_file,
                            "invocation_sha256": invocation_sha,
                            "professor": "Example Professor",
                            "professor_dir": professor_dir,
                            "refresh_scope": "flagged",
                            "profile_fingerprint": "profile-sha"}
            finalize_arguments = ["--invocation-file", invocation_file,
                                  "--invocation-sha256", invocation_sha]
        else:
            previous_validation = f"/tmp/round-{round_number - 1}/validation-result.json"
            plan_arguments = ["--invocation-file", invocation_file,
                              "--invocation-sha256", invocation_sha,
                              "--validation-file", previous_validation]
            plan_payload = {"status": "ok"}
            finalize_arguments = plan_arguments.copy()
        events.extend([
            command(base + 10, generator, "stage3-plan", plan_arguments, plan_payload),
            command(base + 20, generator, "stage3-finalize", finalize_arguments),
            completed_turn(base + 25, generator, generator_report(
                program_root, professor_dir, invocation_file, invocation_sha)),
            command(base + 30, root, "stage3-prepare-validation",
                    ["--invocation-file", invocation_file,
                     "--invocation-sha256", invocation_sha,
                     "--round", str(round_number)], payload={
                "status": "ok", "round": round_number, "handoff_file": handoff_file,
                "handoff_sha256": handoff_sha, "output_file": output_file,
                "validation_file": validation_file, "professor_dir": professor_dir,
            }),
            command(base + 40, validator, "stage3-write-validation",
                    ["--output-file", output_file], {"result": "ok"}),
            completed_turn(base + 45, validator, {
                "result": "ok", "write_status": "written", "output_files": [output_file]}),
            command(base + 50, root, "stage3-save-validation",
                    ["--handoff-file", handoff_file, "--handoff-sha256", handoff_sha],
                    {"status": "ok", "round": round_number,
                     "validation_sha256": validation_sha,
                     "validation_file": validation_file}),
            command(base + 60, root, "stage3-record-validation",
                    ["--handoff-file", handoff_file, "--handoff-sha256", handoff_sha,
                     "--expected-validation-sha256", validation_sha],
                    {"status": "ok", "round": round_number,
                     "terminal": round_number == 2,
                     "needs_correction": round_number == 1,
                     "validation_input_sha256": validation_sha,
                     "state_path": professor_dir + "/套磁候选状态.json",
                     "scopes": [{"scope": "direction:DIR00001",
                                 "result": "fail" if round_number == 1 else "pass",
                                 "rounds": round_number}]}),
        ])
        relations.extend([
            {"tool": "spawnAgent", "sender_thread_id": root, "status": "completed",
             "runtime_seq": base + 5, "receiver_thread_ids": [generator]},
            {"tool": "spawnAgent", "sender_thread_id": root, "status": "completed",
             "runtime_seq": base + 35, "receiver_thread_ids": [validator]},
        ])
        reads.extend([
            {"thread_id": generator, "identity_eligible": True, "outcome": "success",
             "effective_role": GENERATOR},
            {"thread_id": validator, "identity_eligible": True, "outcome": "success",
             "effective_role": VALIDATOR},
        ])
    overview_path = program_root + "/教授研究/套磁想法候选总览.md"
    events.append(command(130, root, "stage3-rebuild-overview",
                          ["--program-root", program_root],
                          {"status": "ok", "overview_md": overview_path}))
    events.append(completed_text_turn(140, root, "已完成：" + overview_path))
    response = {"output": {
        "thread_id": root, "turn_id": "root-turn", "events": [{"type": "thread.started"}],
        "termination_reason": "completed", "exit_code": 0, "app_server_events": events,
    }}
    adapter = {
        "fixture_status": "FIXTURE_READY",
        "delegation": {"formal_child_count": 4, "child_thread_ids": children},
        "dispatch": {"thread_relations": relations},
        "child_thread_reads": {"entries": reads},
    }
    return response, adapter


class Issue66RuntimeClassifierPreflight(unittest.TestCase):
    def classify(self, response, adapter, **overrides):
        return classify(response, adapter, fixture_manifest(), inspect_files=False,
                        **overrides)["classification"]

    def test_valid_frozen_shape_passes(self):
        response, adapter = valid_documents()
        self.assertEqual(self.classify(response, adapter), "PASS")

    def test_complete_evidence_with_missing_action_fails(self):
        response, adapter = valid_documents()
        response["output"]["app_server_events"].remove(
            command_event(response, "stage3-rebuild-overview"))
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_unconfirmed_fixture_is_invalid_evidence(self):
        response, adapter = valid_documents()
        adapter["fixture_status"] = "HARNESS_DISPATCH_UNCONFIRMED"
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_request_failure_is_case_not_started(self):
        response, adapter = valid_documents()
        self.assertEqual(self.classify(response, adapter, http_status=504), "CASE_NOT_STARTED")

    def test_incomplete_run_without_action_failure_is_blocked(self):
        response, adapter = valid_documents()
        response["output"]["termination_reason"] = "timeout"
        self.assertEqual(self.classify(response, adapter), "BLOCKED")

    def test_completed_required_action_failure_is_product_failure(self):
        response, adapter = valid_documents()
        command_event(response, "stage3-prepare-validation")["message"]["params"]["item"]["exitCode"] = 1
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_incomplete_run_precedes_action_failure(self):
        response, adapter = valid_documents()
        response["output"]["termination_reason"] = "timeout"
        command_event(response, "stage3-prepare-validation")["message"]["params"]["item"]["exitCode"] = 1
        self.assertEqual(self.classify(response, adapter), "BLOCKED")

    def test_invalid_fixture_precedes_action_failure(self):
        response, adapter = valid_documents()
        adapter["fixture_status"] = "HARNESS_DISPATCH_UNCONFIRMED"
        command_event(response, "stage3-prepare-validation")["message"]["params"]["item"]["exitCode"] = 1
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_wrong_action_owner_fails(self):
        response, adapter = valid_documents()
        response["output"]["app_server_events"][1]["message"]["params"]["threadId"] = "root-thread"
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_successful_read_without_completed_turn_is_invalid(self):
        response, adapter = valid_documents()
        response["output"]["app_server_events"] = [
            event for event in response["output"]["app_server_events"]
            if not (event["message"]["method"] == "turn/completed"
                    and event["message"]["params"]["threadId"] == "validator-1")]
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_script_text_mentioning_subcommand_is_not_an_action(self):
        response, adapter = valid_documents()
        helper = copy.deepcopy(response["output"]["app_server_events"][1])
        helper["runtime_seq"] = 5
        helper["message"]["params"]["item"]["command"] = \
            "/bin/zsh -lc 'echo contact_state.py stage3-plan'"
        response["output"]["app_server_events"].insert(1, helper)
        self.assertEqual(self.classify(response, adapter), "PASS")
        response, adapter = valid_documents()
        plan_item = command_event(response, "stage3-plan")["message"]["params"]["item"]
        plan_item["command"] = plan_item["command"].replace(
            ".agents/skills/professor-contact/scripts/contact_state.py",
            "/tmp/contact_state.py")
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_wrong_handoff_binding_fails(self):
        response, adapter = valid_documents()
        save_item = command_event(response, "stage3-save-validation")["message"]["params"]["item"]
        save_item["command"] = save_item["command"].replace("handoff-sha", "wrong-sha")
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_missing_handoff_or_validation_digest_fails(self):
        for action, field, removals in (
                ("stage3-prepare-validation", "handoff_sha256", (
                    ("stage3-save-validation", " --handoff-sha256 handoff-sha"),
                    ("stage3-record-validation", " --handoff-sha256 handoff-sha"))),
                ("stage3-save-validation", "validation_sha256", (
                    ("stage3-record-validation",
                     " --expected-validation-sha256 validation-sha"),))):
            with self.subTest(field=field):
                response, adapter = valid_documents()
                item = command_event(response, action)["message"]["params"]["item"]
                payload = json.loads(item["aggregatedOutput"])
                payload.pop(field)
                item["aggregatedOutput"] = json.dumps(payload)
                for consumer, fragment in removals:
                    consumer_item = command_event(response, consumer)["message"]["params"]["item"]
                    consumer_item["command"] = consumer_item["command"].replace(fragment, "")
                if field == "validation_sha256":
                    record_item = command_event(
                        response, "stage3-record-validation")["message"]["params"]["item"]
                    record_payload = json.loads(record_item["aggregatedOutput"])
                    record_payload.pop("validation_input_sha256")
                    record_item["aggregatedOutput"] = json.dumps(record_payload)
                self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_wrong_invocation_binding_fails(self):
        response, adapter = valid_documents()
        finalize_item = command_event(response, "stage3-finalize")["message"]["params"]["item"]
        finalize_item["command"] = finalize_item["command"].replace(
            "invocation-sha", "wrong-invocation-sha")
        self.assertEqual(self.classify(response, adapter), "FAIL")
        cases = (
            ("stage3-plan", "--profile", "/tmp/other-profile.md", False),
            ("stage3-plan", "--profile", "/tmp/other-profile.md", True),
            ("stage3-finalize", "--invocation-file", "/tmp/other-invocation.json", False),
            ("stage3-record-validation", "--expected-validation-sha256", "other-sha", False),
        )
        for action, option_name, value, use_equals in cases:
            with self.subTest(action=action, option=option_name):
                response, adapter = valid_documents()
                item = command_event(response, action)["message"]["params"]["item"]
                repeated = f"{option_name}={value}" if use_equals \
                    else f"{option_name} {shlex.quote(value)}"
                item["command"] = item["command"][:-1] + f" {repeated}\""
                self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_initial_profile_source_tuple_is_required(self):
        for mutation in ("missing-profile", "empty-profile-fingerprint"):
            with self.subTest(mutation=mutation):
                response, adapter = valid_documents()
                plan_item = command_event(response, "stage3-plan")["message"]["params"]["item"]
                if mutation == "missing-profile":
                    plan_item["command"] = plan_item["command"].replace(
                        " --profile '/tmp/program/套磁邮件/套磁信息.md'", "")
                else:
                    payload = json.loads(plan_item["aggregatedOutput"])
                    payload["profile_fingerprint"] = ""
                    plan_item["aggregatedOutput"] = json.dumps(payload)
                self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_empty_record_scopes_fail(self):
        response, adapter = valid_documents()
        record_item = command_event(response, "stage3-record-validation")["message"]["params"]["item"]
        payload = json.loads(record_item["aggregatedOutput"])
        payload["scopes"] = []
        record_item["aggregatedOutput"] = json.dumps(payload)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_validator_must_have_one_final_report(self):
        response, adapter = valid_documents()
        validator_turn = next(event for event in response["output"]["app_server_events"]
                              if event["message"]["method"] == "turn/completed"
                              and event["message"]["params"]["threadId"] == "validator-1")
        validator_turn["message"]["params"]["turn"]["items"].insert(0, {
            "type": "agentMessage", "phase": "final_answer",
            "text": json.dumps({"full_validation": "must not be returned"}),
        })
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_each_child_must_have_one_assistant_message(self):
        for child in ("generator-1", "validator-1"):
            with self.subTest(child=child):
                response, adapter = valid_documents()
                child_turn = next(event for event in response["output"]["app_server_events"]
                                  if event["message"]["method"] == "turn/completed"
                                  and event["message"]["params"]["threadId"] == child)
                child_turn["message"]["params"]["turn"]["items"].insert(0, {
                    "type": "agentMessage", "phase": "commentary", "text": "progress",
                })
                self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_resolved_model_mismatch_is_invalid_evidence(self):
        response, adapter = valid_documents()
        response["output"]["app_server_events"][0]["message"]["params"]["thread"]["model"] = "other"
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_child_completion_after_root_save_fails(self):
        response, adapter = valid_documents()
        validator_turn = next(event for event in response["output"]["app_server_events"]
                              if event["message"]["method"] == "turn/completed"
                              and event["message"]["params"]["threadId"] == "validator-1")
        validator_turn["runtime_seq"] = 55
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_missing_record_action_fails(self):
        response, adapter = valid_documents()
        response["output"]["app_server_events"] = [
            event for event in response["output"]["app_server_events"]
            if not (event["message"]["method"] == "item/completed"
                    and "stage3-record-validation"
                    in event["message"]["params"].get("item", {}).get("command", ""))]
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_valid_two_round_topology_passes(self):
        response, adapter = valid_two_round_documents()
        self.assertEqual(self.classify(response, adapter), "PASS")

    def test_single_round_failed_scope_cannot_be_terminal(self):
        response, adapter = valid_documents()
        record_item = command_event(response, "stage3-record-validation")["message"]["params"]["item"]
        payload = json.loads(record_item["aggregatedOutput"])
        payload["scopes"][0]["result"] = "fail"
        record_item["aggregatedOutput"] = json.dumps(payload)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_two_round_first_scope_must_fail(self):
        response, adapter = valid_two_round_documents()
        records = [event for event in response["output"]["app_server_events"]
                   if event["message"]["method"] == "item/completed"
                   and "contact_state.py stage3-record-validation" in
                   event["message"]["params"].get("item", {}).get("command", "")]
        first_item = records[0]["message"]["params"]["item"]
        payload = json.loads(first_item["aggregatedOutput"])
        payload["scopes"][0]["result"] = "pass"
        first_item["aggregatedOutput"] = json.dumps(payload)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_two_rounds_cannot_reuse_first_round_children(self):
        response, adapter = valid_two_round_documents()
        second_plan = [event for event in response["output"]["app_server_events"]
                       if event["message"]["method"] == "item/completed"
                       and "contact_state.py stage3-plan" in
                       event["message"]["params"].get("item", {}).get("command", "")][1]
        second_finalize = [event for event in response["output"]["app_server_events"]
                           if event["message"]["method"] == "item/completed"
                           and "contact_state.py stage3-finalize" in
                           event["message"]["params"].get("item", {}).get("command", "")][1]
        second_write = [event for event in response["output"]["app_server_events"]
                        if event["message"]["method"] == "item/completed"
                        and "contact_state.py stage3-write-validation" in
                        event["message"]["params"].get("item", {}).get("command", "")][1]
        second_plan["message"]["params"]["threadId"] = "generator-1"
        second_finalize["message"]["params"]["threadId"] = "generator-1"
        second_write["message"]["params"]["threadId"] = "validator-1"
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_generator_report_must_return_the_consumed_invocation(self):
        response, adapter = valid_documents()
        generator_turn = next(event for event in response["output"]["app_server_events"]
                              if event["message"]["method"] == "turn/completed"
                              and event["message"]["params"]["threadId"] == "generator-1")
        report = json.loads(generator_turn["message"]["params"]["turn"]["items"][0]["text"])
        report["invocations"][0]["invocation_sha256"] = "wrong-sha"
        generator_turn["message"]["params"]["turn"]["items"][0]["text"] = json.dumps(report)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_malformed_generator_directions_do_not_crash(self):
        response, adapter = valid_documents()
        generator_turn = next(event for event in response["output"]["app_server_events"]
                              if event["message"]["method"] == "turn/completed"
                              and event["message"]["params"]["threadId"] == "generator-1")
        report = json.loads(generator_turn["message"]["params"]["turn"]["items"][0]["text"])
        report["directions"] = [None]
        generator_turn["message"]["params"]["turn"]["items"][0]["text"] = json.dumps(report)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_fixture_professor_cannot_drift(self):
        response, adapter = valid_documents()
        prepare_item = command_event(response, "stage3-prepare-validation")["message"]["params"]["item"]
        payload = json.loads(prepare_item["aggregatedOutput"])
        payload["professor_dir"] = "/tmp/program/教授研究/X分野/Other Professor"
        prepare_item["aggregatedOutput"] = json.dumps(payload)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_save_must_report_the_prepared_validation_path(self):
        response, adapter = valid_documents()
        save_item = command_event(response, "stage3-save-validation")["message"]["params"]["item"]
        payload = json.loads(save_item["aggregatedOutput"])
        payload["validation_file"] = "/tmp/other-validation.json"
        save_item["aggregatedOutput"] = json.dumps(payload)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_two_rounds_cannot_reuse_the_same_handoff_directory(self):
        response, adapter = valid_two_round_documents()
        events = response["output"]["app_server_events"]
        def selected(name, position):
            return [event for event in events
                    if event["message"]["method"] == "item/completed"
                    and f"contact_state.py {name}" in
                    event["message"]["params"].get("item", {}).get("command", "")][position]
        first_prepare = selected("stage3-prepare-validation", 0)["message"]["params"]["item"]
        second_prepare = selected("stage3-prepare-validation", 1)["message"]["params"]["item"]
        first_paths = json.loads(first_prepare["aggregatedOutput"])
        second_paths = json.loads(second_prepare["aggregatedOutput"])
        replacements = {
            second_paths["handoff_file"]: first_paths["handoff_file"],
            second_paths["output_file"]: first_paths["output_file"],
            second_paths["validation_file"]: first_paths["validation_file"],
        }
        second_paths.update({key: first_paths[key]
                             for key in ("handoff_file", "output_file", "validation_file")})
        second_prepare["aggregatedOutput"] = json.dumps(second_paths)
        for name in ("stage3-write-validation", "stage3-save-validation",
                     "stage3-record-validation"):
            item = selected(name, 1)["message"]["params"]["item"]
            for old, new in replacements.items():
                item["command"] = item["command"].replace(old, new)
            if name == "stage3-save-validation":
                payload = json.loads(item["aggregatedOutput"])
                payload["validation_file"] = first_paths["validation_file"]
                item["aggregatedOutput"] = json.dumps(payload)
        validator_turn = next(event for event in events
                              if event["message"]["method"] == "turn/completed"
                              and event["message"]["params"]["threadId"] == "validator-2")
        report = json.loads(validator_turn["message"]["params"]["turn"]["items"][0]["text"])
        report["output_files"] = [first_paths["output_file"]]
        validator_turn["message"]["params"]["turn"]["items"][0]["text"] = json.dumps(report)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_stage4_action_after_stage3_fails(self):
        response, adapter = valid_documents()
        response["output"]["app_server_events"].append(
            command(75, "root-thread", "stage4-build-email"))
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_missing_formal_sender_is_invalid_evidence(self):
        response, adapter = valid_documents()
        adapter["dispatch"]["thread_relations"][0].pop("sender_thread_id")
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_malformed_formal_receiver_is_invalid_evidence(self):
        response, adapter = valid_documents()
        adapter["dispatch"]["thread_relations"][0]["receiver_thread_ids"] = [{}]
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_traversal_cannot_escape_fixture_program(self):
        response, adapter = valid_documents()
        prepare_item = command_event(response, "stage3-prepare-validation")["message"]["params"]["item"]
        payload = json.loads(prepare_item["aggregatedOutput"])
        payload["professor_dir"] = "/tmp/program/../outside/Example Professor"
        prepare_item["aggregatedOutput"] = json.dumps(payload)
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_malformed_command_runtime_sequence_is_invalid_evidence(self):
        response, adapter = valid_documents()
        command_event(response, "stage3-record-validation")["runtime_seq"] = "60"
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_extra_failed_child_turn_is_invalid_evidence(self):
        response, adapter = valid_documents()
        extra = completed_turn(24, "generator-1", {"result": "error"})
        extra["message"]["params"]["turn"]["status"] = "failed"
        extra["message"]["params"]["turn"]["error"] = {"message": "failed"}
        response["output"]["app_server_events"].append(extra)
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")

    def test_structured_action_error_fails_even_with_zero_exit(self):
        response, adapter = valid_documents()
        finalize_item = command_event(response, "stage3-finalize")["message"]["params"]["item"]
        finalize_item["aggregatedOutput"] = json.dumps(
            {"status": "error", "reason_code": "needs_refresh"})
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_root_report_must_include_rebuilt_overview(self):
        response, adapter = valid_documents()
        root_turn = next(event for event in response["output"]["app_server_events"]
                         if event["message"]["method"] == "turn/completed"
                         and event["message"]["params"]["threadId"] == "root-thread")
        root_turn["message"]["params"]["turn"]["items"][0]["text"] = "已完成"
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_rebuilt_overview_must_be_the_fixture_overview(self):
        response, adapter = valid_documents()
        rebuild_item = command_event(response, "stage3-rebuild-overview")["message"]["params"]["item"]
        payload = json.loads(rebuild_item["aggregatedOutput"])
        old_path = payload["overview_md"]
        payload["overview_md"] = "/tmp/other-overview.md"
        rebuild_item["aggregatedOutput"] = json.dumps(payload)
        root_turn = next(event for event in response["output"]["app_server_events"]
                         if event["message"]["method"] == "turn/completed"
                         and event["message"]["params"]["threadId"] == "root-thread")
        root_turn["message"]["params"]["turn"]["items"][0]["text"] = \
            root_turn["message"]["params"]["turn"]["items"][0]["text"].replace(
                old_path, payload["overview_md"])
        self.assertEqual(self.classify(response, adapter), "FAIL")

    def test_final_state_rejects_extra_direction_group_or_global_results(self):
        for mutation in ("direction", "group", "global"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                response, adapter = valid_documents()
                program_root = Path(temporary) / "program"
                round_dir = Path(temporary) / "round-1"
                replacements = {
                    "/tmp/program": str(program_root),
                    "/tmp/handoff.json": str(round_dir / "handoff.json"),
                    "/tmp/validator-output.json": str(round_dir / "validator-output.json"),
                    "/tmp/validation-result.json": str(round_dir / "validation-result.json"),
                }
                encoded = json.dumps(response)
                for old, new in replacements.items():
                    encoded = encoded.replace(old, new)
                response = json.loads(encoded)
                for event in response["output"]["app_server_events"]:
                    item = event.get("message", {}).get("params", {}).get("item")
                    if isinstance(item, dict) and item.get("type") == "commandExecution":
                        item["cwd"] = temporary
                professor_dir = program_root / "教授研究" / "X分野" / "Example Professor"
                professor_dir.mkdir(parents=True)
                round_dir.mkdir(parents=True)
                validation_bytes = json.dumps({"result": "ok"}).encode("utf-8")
                (round_dir / "validator-output.json").write_bytes(validation_bytes)
                (round_dir / "validation-result.json").write_bytes(validation_bytes)
                results = {"DIR00001": {"result": "pass", "rounds": 1}}
                groups = {}
                global_issues = []
                if mutation == "direction":
                    results["DIR99999"] = {"result": "pass", "rounds": 1}
                elif mutation == "group":
                    groups["GROUP99999"] = {"result": "pass", "rounds": 1}
                else:
                    global_issues = [{"code": "fake", "message": "fake"}]
                state = {"profile_fingerprint": "profile-sha",
                         "profile_path": str(program_root / "套磁邮件" / "套磁信息.md"),
                         "validator": {"pending": {}, "results": results,
                                       "groups": groups, "global": global_issues}}
                (professor_dir / "套磁候选状态.json").write_text(
                    json.dumps(state), encoding="utf-8")
                overview = program_root / "教授研究" / "套磁想法候选总览.md"
                overview.write_text("ok", encoding="utf-8")
                manifest = fixture_manifest()
                manifest["program_root"] = str(program_root)
                result = classify(response, adapter, manifest, inspect_files=True)
                self.assertEqual(result["classification"], "FAIL")

    def test_malformed_root_items_are_invalid_evidence(self):
        response, adapter = valid_documents()
        root_turn = next(event for event in response["output"]["app_server_events"]
                         if event["message"]["method"] == "turn/completed"
                         and event["message"]["params"]["threadId"] == "root-thread")
        root_turn["message"]["params"]["turn"]["items"] = None
        self.assertEqual(self.classify(response, adapter), "INVALID_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
