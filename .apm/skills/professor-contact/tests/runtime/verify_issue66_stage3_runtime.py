#!/usr/bin/env python3
"""Classify issue #66 Stage 3 evidence from the frozen @15 event surface."""

import argparse
import json
import re
import shlex
from pathlib import Path


GENERATOR = "professor-contact-idea-generator"
VALIDATOR = "professor-contact-style-validator"
ROOT_ACTIONS = {
    "stage3-prepare-validation", "stage3-save-validation",
    "stage3-record-validation", "stage3-rebuild-overview",
}
SENSITIVE_OPTIONS = {
    "--capture-invocation", "--program-root", "--professor-dir", "--profile",
    "--refresh-scope", "--invocation-file", "--invocation-sha256",
    "--validation-file", "--round", "--handoff-file", "--handoff-sha256",
    "--expected-validation-sha256", "--output-file",
}


def verdict(classification, reason, **details):
    return {"classification": classification, "reason": reason, **details}


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__


def unwrap_command(command):
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if tokens and Path(tokens[0]).name in {"sh", "bash", "zsh"}:
        command_options = [index for index, token in enumerate(tokens)
                           if token == "--command"
                           or (token.startswith("-") and not token.startswith("--")
                               and "c" in token[1:])]
        if len(command_options) != 1:
            return None
        position = command_options[0]
        if position + 1 >= len(tokens):
            return None
        try:
            tokens = shlex.split(tokens[position + 1])
        except ValueError:
            return None
    if not tokens:
        return None
    executable = Path(tokens[0]).name
    if re.fullmatch(r"python(?:3(?:\.\d+)?)?", executable):
        script_index = 1
    elif executable == "contact_state.py":
        script_index = 0
    else:
        return None
    if script_index + 1 >= len(tokens) \
            or Path(tokens[script_index]).name != "contact_state.py":
        return None
    return tokens[script_index], tokens[script_index + 1], tokens[script_index + 2:]


def option(arguments, name):
    values = []
    for index, token in enumerate(arguments):
        if token == name:
            if index + 1 >= len(arguments):
                return None
            values.append(arguments[index + 1])
        elif token.startswith(name + "="):
            values.append(token.split("=", 1)[1])
    return values[0] if len(values) == 1 else None


def parse_object(text):
    if not isinstance(text, str):
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def normalize_events(response):
    app_events = response["output"].get("app_server_events")
    if not isinstance(app_events, list):
        return None, None, None, False
    commands = []
    completions = []
    starts = []
    malformed = False
    for envelope in app_events:
        if not isinstance(envelope, dict):
            continue
        message = envelope.get("message")
        if not isinstance(message, dict):
            continue
        method = message.get("method")
        if method in {"thread/started", "turn/completed", "item/completed"} \
                and not isinstance(envelope.get("runtime_seq"), int):
            malformed = True
            continue
        params = message.get("params")
        if not isinstance(params, dict):
            continue
        if method == "thread/started":
            thread = params.get("thread")
            if isinstance(thread, dict):
                starts.append({"seq": envelope["runtime_seq"], "thread": thread})
        elif method == "turn/completed":
            turn = params.get("turn")
            if isinstance(turn, dict):
                completions.append({"seq": envelope["runtime_seq"],
                                    "thread_id": params.get("threadId"), "turn": turn})
        elif method == "item/completed":
            item = params.get("item")
            if not isinstance(item, dict) or item.get("type") != "commandExecution":
                continue
            parsed = unwrap_command(item.get("command", ""))
            if parsed is None:
                continue
            script, name, arguments = parsed
            commands.append({"seq": envelope["runtime_seq"],
                             "thread_id": params.get("threadId"), "name": name,
                             "script": script, "arguments": arguments, "item": item,
                             "cwd": item.get("cwd"),
                             "output": parse_object(item.get("aggregatedOutput"))})
    return sorted(commands, key=lambda item: item["seq"]), completions, starts, malformed


def final_object(completion):
    turn = completion.get("turn")
    if not isinstance(turn, dict) or turn.get("status") != "completed" or turn.get("error") is not None:
        return None
    items = turn.get("items")
    if not isinstance(items, list):
        return None
    messages = [item for item in items
                if isinstance(item, dict) and item.get("type") == "agentMessage"]
    if len(messages) != 1 or messages[0].get("phase") != "final_answer":
        return None
    return parse_object(messages[0].get("text"))


def classify(response, adapter, fixture, http_status=200, curl_exit=0, inspect_files=True):
    if curl_exit != 0 or http_status != 200:
        return verdict("CASE_NOT_STARTED", "request_not_accepted",
                       http_status=http_status, curl_exit=curl_exit)
    output = response.get("output") if isinstance(response, dict) else None
    if not isinstance(output, dict):
        return verdict("CASE_NOT_STARTED", "invalid_response")
    if not all(isinstance(output.get(key), str) and output[key]
               for key in ("thread_id", "turn_id")):
        return verdict("CASE_NOT_STARTED", "missing_root_identity")
    if not isinstance(output.get("events"), list) or not output["events"]:
        return verdict("CASE_NOT_STARTED", "missing_run_events")

    if output.get("termination_reason") != "completed" or output.get("exit_code") != 0:
        return verdict("BLOCKED", "run_not_completed")
    commands, completions, starts, malformed_events = normalize_events(response)
    if commands is None:
        return verdict("INVALID_EVIDENCE", "missing_app_server_events")
    if malformed_events:
        return verdict("INVALID_EVIDENCE", "malformed_runtime_sequence")
    if not isinstance(adapter, dict) or adapter.get("fixture_status") != "FIXTURE_READY":
        return verdict("INVALID_EVIDENCE", "fixture_not_ready",
                       fixture_status=adapter.get("fixture_status") if isinstance(adapter, dict) else None)
    if not isinstance(fixture, dict) \
            or fixture.get("fixture_kind") != "issue55-stage3-pre" \
            or fixture.get("builder") != "tests/runtime/prepare_issue55_stage3_fixture.py" \
            or not isinstance(fixture.get("program_root"), str) \
            or not isinstance(fixture.get("professor"), str) \
            or not isinstance(fixture.get("direction_id"), str):
        return verdict("INVALID_EVIDENCE", "fixture_manifest_invalid")
    input_hashes = fixture.get("input_hashes")
    profile_relative = "套磁邮件/套磁信息.md"
    if not isinstance(input_hashes, dict) \
            or not isinstance(input_hashes.get(profile_relative), str) \
            or not input_hashes[profile_relative]:
        return verdict("INVALID_EVIDENCE", "fixture_profile_unobservable")
    expected_program_root = Path(fixture["program_root"]).resolve()
    expected_professor_dir = (expected_program_root / "教授研究" / "X分野"
                              / fixture["professor"]).resolve()
    expected_scope = "direction:" + fixture["direction_id"]
    expected_profile = (expected_program_root / profile_relative).resolve()
    expected_profile_sha = input_hashes[profile_relative]
    expected_consumer = expected_program_root.parent.resolve()
    expected_script = (expected_consumer / ".agents" / "skills" / "professor-contact"
                       / "scripts" / "contact_state.py").resolve()

    for command in commands:
        cwd = command.get("cwd")
        if not isinstance(cwd, str) or not cwd:
            return verdict("INVALID_EVIDENCE", "command_cwd_unobservable")
        resolved_cwd = Path(cwd).resolve()
        if resolved_cwd != expected_consumer and expected_consumer not in resolved_cwd.parents:
            return verdict("FAIL", "command_outside_consumer", action=command["name"])
        script_path = Path(command["script"])
        resolved_script = (resolved_cwd / script_path).resolve() \
            if not script_path.is_absolute() else script_path.resolve()
        if resolved_script != expected_script:
            return verdict("FAIL", "wrong_runner_script", action=command["name"])
        duplicates = [name for name in SENSITIVE_OPTIONS
                      if sum(token == name or token.startswith(name + "=")
                             for token in command["arguments"]) > 1]
        if duplicates:
            return verdict("FAIL", "duplicate_sensitive_option",
                           action=command["name"], options=sorted(duplicates))

    root = output["thread_id"]
    root_starts = [entry for entry in starts if entry["thread"].get("id") == root]
    if len(root_starts) != 1:
        return verdict("INVALID_EVIDENCE", "root_config_unobservable")
    actual_model = root_starts[0]["thread"].get("model")
    actual_reasoning = root_starts[0]["thread"].get("reasoningEffort")
    if actual_model != "gpt-5.6-luna" or actual_reasoning != "low":
        return verdict("INVALID_EVIDENCE", "resolved_config_mismatch",
                       model=actual_model, reasoning=actual_reasoning)

    dispatch = adapter.get("dispatch")
    delegation = adapter.get("delegation")
    reads = adapter.get("child_thread_reads")
    if not all(isinstance(value, dict) for value in (dispatch, delegation, reads)):
        return verdict("INVALID_EVIDENCE", "missing_adapter_sections")
    relations = dispatch.get("thread_relations")
    children = delegation.get("child_thread_ids")
    read_entries = reads.get("entries")
    if not isinstance(relations, list) or not isinstance(children, list) or not isinstance(read_entries, list):
        return verdict("INVALID_EVIDENCE", "invalid_adapter_sections")
    if any(not isinstance(child, str) or not child for child in children):
        return verdict("INVALID_EVIDENCE", "invalid_formal_child_summary")
    formal = [relation for relation in relations
              if isinstance(relation, dict) and relation.get("tool") == "spawnAgent"]
    if any(not isinstance(relation.get("sender_thread_id"), str)
           or not relation.get("sender_thread_id") for relation in formal):
        return verdict("INVALID_EVIDENCE", "formal_owner_unobservable")
    if any(relation.get("sender_thread_id") != root for relation in formal):
        return verdict("FAIL", "non_root_formal_owner")
    if any(relation.get("status") != "completed"
           or not isinstance(relation.get("runtime_seq"), int)
           or not isinstance(relation.get("receiver_thread_ids"), list)
           or len(relation["receiver_thread_ids"]) != 1
           or not isinstance(relation["receiver_thread_ids"][0], str)
           or not relation["receiver_thread_ids"][0] for relation in formal):
        return verdict("INVALID_EVIDENCE", "invalid_formal_attempt")
    formal.sort(key=lambda relation: relation["runtime_seq"])
    attempted_children = [relation["receiver_thread_ids"][0] for relation in formal]
    if len(set(attempted_children)) != len(attempted_children):
        return verdict("INVALID_EVIDENCE", "duplicate_formal_child")
    if set(attempted_children) != set(children) \
            or delegation.get("formal_child_count") != len(children):
        return verdict("INVALID_EVIDENCE", "delegation_summary_mismatch")

    role_by_child = {}
    for entry in read_entries:
        if not isinstance(entry, dict):
            continue
        entry_thread = entry.get("thread_id")
        if not isinstance(entry_thread, str) or entry_thread not in children:
            continue
        if entry.get("identity_eligible") is not True or entry.get("outcome") != "success":
            return verdict("INVALID_EVIDENCE", "child_identity_unobservable")
        role_by_child[entry_thread] = entry.get("effective_role")
    if set(role_by_child) != set(children) or any(
            role not in (GENERATOR, VALIDATOR) for role in role_by_child.values()):
        return verdict("INVALID_EVIDENCE", "child_role_unobservable")

    completion_by_child = {}
    for entry in completions:
        if entry.get("thread_id") not in children:
            continue
        completion_by_child.setdefault(entry["thread_id"], []).append(entry)
    if set(completion_by_child) != set(children) \
            or any(len(entries) != 1 for entries in completion_by_child.values()):
        return verdict("INVALID_EVIDENCE", "child_completion_unobservable")
    completion_by_child = {child: entries[0]
                           for child, entries in completion_by_child.items()}
    failed_children = [child for child, entry in completion_by_child.items()
                       if not isinstance(entry.get("turn"), dict)
                       or entry["turn"].get("status") != "completed"
                       or entry["turn"].get("error") is not None]
    if failed_children:
        return verdict("FAIL", "child_turn_failed", children=failed_children)

    failed_actions = [command for command in commands
                      if command["item"].get("status") != "completed"
                      or command["item"].get("exitCode") != 0]
    if failed_actions:
        return verdict("FAIL", "required_action_failed",
                       actions=[item["name"] for item in failed_actions])
    unsuccessful_outputs = [command for command in commands
                            if command["name"] != "stage3-write-validation"
                            and isinstance(command["output"], dict)
                            and command["output"].get("status") != "ok"]
    if unsuccessful_outputs:
        return verdict("FAIL", "required_action_unsuccessful",
                       actions=[item["name"] for item in unsuccessful_outputs])

    records = [command for command in commands if command["name"] == "stage3-record-validation"]
    if not records:
        return verdict("FAIL", "required_action_missing", action="stage3-record-validation")
    if any(command["output"] is None for command in records):
        return verdict("INVALID_EVIDENCE", "record_output_unreadable")
    rounds = len(records)
    if rounds not in (1, 2):
        return verdict("FAIL", "invalid_round_count", rounds=rounds)
    expected_children = rounds * 2
    role_counts = {GENERATOR: list(role_by_child.values()).count(GENERATOR),
                   VALIDATOR: list(role_by_child.values()).count(VALIDATOR)}
    if len(formal) != expected_children or len(completion_by_child) != expected_children:
        return verdict("FAIL", "topology_count_mismatch", attempts=len(formal),
                       completed=len(completion_by_child), expected=expected_children)
    if role_counts != {GENERATOR: rounds, VALIDATOR: rounds}:
        return verdict("FAIL", "topology_role_mismatch", roles=role_counts)
    owner_role = {"stage3-plan": GENERATOR, "stage3-finalize": GENERATOR,
                  "stage3-write-validation": VALIDATOR}
    for command in commands:
        if command["name"] in ROOT_ACTIONS and command["thread_id"] != root:
            return verdict("FAIL", "root_action_wrong_owner", action=command["name"])
        expected_role = owner_role.get(command["name"])
        if expected_role and role_by_child.get(command["thread_id"]) != expected_role:
            return verdict("FAIL", "child_action_wrong_owner", action=command["name"])
    expected_sequence = []
    for _ in range(rounds):
        expected_sequence.extend(("stage3-plan", "stage3-finalize",
                                  "stage3-prepare-validation", "stage3-write-validation",
                                  "stage3-save-validation", "stage3-record-validation"))
    expected_sequence.append("stage3-rebuild-overview")
    actual_sequence = [command["name"] for command in commands]
    if actual_sequence != expected_sequence:
        return verdict("FAIL", "action_sequence_mismatch", actions=actual_sequence,
                       expected_actions=expected_sequence)

    initial_plan = commands[0]
    if initial_plan["output"] is None:
        return verdict("INVALID_EVIDENCE", "initial_plan_output_unreadable")
    invocation_file = initial_plan["output"].get("invocation_file")
    invocation_sha = initial_plan["output"].get("invocation_sha256")
    capture_dir = option(initial_plan["arguments"], "--capture-invocation")
    if not all(isinstance(value, str) and value
               for value in (invocation_file, invocation_sha, capture_dir)):
        return verdict("FAIL", "initial_invocation_missing")
    if Path(invocation_file).parent != Path(capture_dir):
        return verdict("FAIL", "initial_invocation_path_mismatch")
    initial_program_root = option(initial_plan["arguments"], "--program-root")
    initial_professor_dir = option(initial_plan["arguments"], "--professor-dir")
    initial_profile = option(initial_plan["arguments"], "--profile")
    initial_refresh_scope = option(initial_plan["arguments"], "--refresh-scope")
    rebuild_program_root = option(commands[-1]["arguments"], "--program-root")
    if not all(isinstance(value, str) and value for value in (
            initial_program_root, initial_professor_dir, initial_profile,
            initial_refresh_scope, rebuild_program_root)):
        return verdict("FAIL", "overview_program_root_missing")
    if Path(initial_program_root).resolve() != expected_program_root \
            or Path(initial_professor_dir).resolve() != expected_professor_dir \
            or Path(initial_profile).resolve() != expected_profile \
            or initial_refresh_scope != "flagged" \
            or Path(rebuild_program_root).resolve() != expected_program_root:
        return verdict("FAIL", "fixture_source_tuple_mismatch")
    if initial_plan["output"].get("professor") != fixture["professor"] \
            or Path(str(initial_plan["output"].get("professor_dir", ""))).resolve() \
            != expected_professor_dir \
            or initial_plan["output"].get("refresh_scope") != "flagged" \
            or initial_plan["output"].get("profile_fingerprint") != expected_profile_sha:
        return verdict("FAIL", "initial_plan_source_binding_mismatch")

    round_records = []
    used_generators = []
    used_validators = []
    previous_validation_file = None
    handoff_paths = set()
    output_paths = set()
    validation_paths = set()
    round_directories = set()
    for round_number in range(1, rounds + 1):
        offset = (round_number - 1) * 6
        plan, finalize, prepare, write, save, record = commands[offset:offset + 6]
        if plan["thread_id"] != finalize["thread_id"]:
            return verdict("FAIL", "generator_round_owner_mismatch", round=round_number)
        generator_completion = completion_by_child[plan["thread_id"]]
        validator_completion = completion_by_child[write["thread_id"]]
        previous_record_seq = commands[offset - 1]["seq"] if round_number > 1 else -1
        if not (previous_record_seq < plan["seq"] < finalize["seq"]
                < generator_completion["seq"] < prepare["seq"]):
            return verdict("FAIL", "generator_completion_order_mismatch", round=round_number)
        if not (prepare["seq"] < write["seq"] < validator_completion["seq"]
                < save["seq"]):
            return verdict("FAIL", "validator_completion_order_mismatch", round=round_number)
        used_generators.append(plan["thread_id"])
        used_validators.append(write["thread_id"])
        generator_report = final_object(generator_completion)
        if generator_report is None:
            return verdict("INVALID_EVIDENCE", "generator_completion_report_unreadable",
                           round=round_number)
        invocations = generator_report.get("invocations")
        directions = generator_report.get("directions")
        if generator_report.get("result") != "ok" \
                or Path(str(generator_report.get("program_root", ""))).resolve() \
                != expected_program_root \
                or Path(str(generator_report.get("profile_path", ""))).resolve() \
                != expected_profile \
                or generator_report.get("refresh_scope") != "flagged" \
                or not isinstance(invocations, list) or len(invocations) != 1 \
                or not isinstance(invocations[0], dict) \
                or Path(str(invocations[0].get("professor_dir", ""))).resolve() \
                != expected_professor_dir \
                or invocations[0].get("invocation_file") != invocation_file \
                or invocations[0].get("invocation_sha256") != invocation_sha \
                or not isinstance(directions, list) or len(directions) != 1 \
                or not isinstance(directions[0], dict) \
                or directions[0].get("professor") != fixture["professor"] \
                or directions[0].get("direction_id") != fixture["direction_id"]:
            return verdict("FAIL", "generator_completion_report_mismatch",
                           round=round_number)
        if any(command["output"] is None
               for command in (plan, finalize, prepare, write, save, record)):
            return verdict("INVALID_EVIDENCE", "round_output_unreadable", round=round_number)
        invocation_consumers = [finalize, prepare]
        if round_number > 1:
            invocation_consumers.append(plan)
        if any(option(command["arguments"], "--invocation-file") != invocation_file
               or option(command["arguments"], "--invocation-sha256") != invocation_sha
               for command in invocation_consumers):
            return verdict("FAIL", "invocation_binding_mismatch", round=round_number)
        if option(prepare["arguments"], "--round") != str(round_number):
            return verdict("FAIL", "prepare_round_argument_mismatch", round=round_number)
        if round_number > 1:
            if option(plan["arguments"], "--validation-file") != previous_validation_file \
                    or option(finalize["arguments"], "--validation-file") != previous_validation_file:
                return verdict("FAIL", "correction_validation_binding_mismatch",
                               round=round_number)
        if prepare["output"].get("round") != round_number \
                or save["output"].get("round") != round_number \
                or record["output"].get("round") != round_number:
            return verdict("FAIL", "round_binding_mismatch", round=round_number)
        handoff = prepare["output"].get("handoff_file")
        handoff_sha = prepare["output"].get("handoff_sha256")
        validation_sha = save["output"].get("validation_sha256")
        validation_file = prepare["output"].get("validation_file")
        output_file = prepare["output"].get("output_file")
        if not all(isinstance(value, str) and value
                   for value in (handoff, handoff_sha, output_file,
                                 validation_file, validation_sha)):
            return verdict("FAIL", "round_paths_missing", round=round_number)
        resolved_handoff = Path(handoff).resolve()
        resolved_output = Path(output_file).resolve()
        resolved_validation = Path(validation_file).resolve()
        if not (resolved_handoff.parent == resolved_output.parent
                == resolved_validation.parent) \
                or resolved_handoff.parent in round_directories:
            return verdict("FAIL", "round_directory_not_exclusive", round=round_number)
        if resolved_handoff in handoff_paths or resolved_output in output_paths \
                or resolved_validation in validation_paths:
            return verdict("FAIL", "round_path_reused", round=round_number)
        handoff_paths.add(resolved_handoff)
        output_paths.add(resolved_output)
        validation_paths.add(resolved_validation)
        round_directories.add(resolved_handoff.parent)
        if option(save["arguments"], "--handoff-file") != handoff \
                or option(save["arguments"], "--handoff-sha256") != handoff_sha:
            return verdict("FAIL", "save_handoff_mismatch", round=round_number)
        if option(record["arguments"], "--handoff-file") != handoff \
                or option(record["arguments"], "--handoff-sha256") != handoff_sha \
                or option(record["arguments"], "--expected-validation-sha256") != validation_sha:
            return verdict("FAIL", "record_handoff_mismatch", round=round_number)
        if option(write["arguments"], "--output-file") != output_file:
            return verdict("FAIL", "writer_output_path_mismatch", round=round_number)
        report = final_object(completion_by_child[write["thread_id"]])
        if report is None:
            return verdict("INVALID_EVIDENCE", "completion_report_unreadable", round=round_number)
        if set(report) != {"result", "write_status", "output_files"} \
                or report.get("result") != "ok" or report.get("write_status") != "written" \
                or report.get("output_files") != [output_file]:
            return verdict("FAIL", "completion_report_mismatch", round=round_number)
        if inspect_files:
            output_path = Path(str(output_file))
            validation_path = Path(str(prepare["output"].get("validation_file", "")))
            if not output_path.is_file() or not validation_path.is_file():
                return verdict("INVALID_EVIDENCE", "validation_file_missing", round=round_number)
            stdout = write["item"].get("aggregatedOutput")
            if not isinstance(stdout, str):
                return verdict("INVALID_EVIDENCE", "writer_stdout_unreadable", round=round_number)
            if stdout.encode("utf-8") != output_path.read_bytes():
                return verdict("FAIL", "writer_stdout_bytes_changed", round=round_number)
            if output_path.read_bytes() != validation_path.read_bytes():
                return verdict("FAIL", "saved_validation_bytes_changed", round=round_number)
        scopes = record["output"].get("scopes")
        if not isinstance(scopes, list) or len(scopes) != 1 \
                or not isinstance(scopes[0], dict) \
                or scopes[0].get("scope") != expected_scope \
                or scopes[0].get("rounds") != round_number:
            return verdict("FAIL", "record_scopes_missing", round=round_number)
        if record["output"].get("validation_input_sha256") != validation_sha:
            return verdict("FAIL", "record_validation_digest_mismatch", round=round_number)
        professor_dir = prepare["output"].get("professor_dir")
        state_path = record["output"].get("state_path")
        if not all(isinstance(value, str) and value
                   for value in (professor_dir, state_path)) \
                or Path(professor_dir).resolve() != expected_professor_dir \
                or Path(state_path).resolve() != expected_professor_dir / "套磁候选状态.json":
            return verdict("FAIL", "state_professor_binding_mismatch", round=round_number)
        if save["output"].get("validation_file") != validation_file:
            return verdict("FAIL", "saved_validation_path_mismatch", round=round_number)
        previous_validation_file = save["output"].get("validation_file")
        round_records.append(record["output"])

    if len(set(used_generators)) != rounds or len(set(used_validators)) != rounds:
        return verdict("FAIL", "child_reused_across_rounds")

    if rounds == 1:
        if round_records[0].get("terminal") is not True \
                or round_records[0].get("needs_correction") is not False \
                or round_records[0]["scopes"][0].get("result") != "pass":
            return verdict("FAIL", "single_round_not_terminal")
    else:
        if round_records[0].get("terminal") is not False \
                or round_records[0].get("needs_correction") is not True \
                or round_records[0]["scopes"][0].get("result") != "fail":
            return verdict("FAIL", "round_one_not_correction")
        if round_records[1].get("terminal") is not True \
                or round_records[1].get("needs_correction") is not False \
                or round_records[1]["scopes"][0].get("result") \
                not in ("pass", "fail_after_2_rounds"):
            return verdict("FAIL", "round_two_not_terminal")

    if inspect_files:
        state_path = Path(str(round_records[-1].get("state_path", "")))
        state, state_error = load_json(state_path)
        if state_error or not isinstance(state, dict):
            return verdict("INVALID_EVIDENCE", "final_state_unreadable")
        validator = state.get("validator")
        if not isinstance(validator, dict) or validator.get("pending") != {}:
            return verdict("FAIL", "final_state_not_terminal")
        results = validator.get("results")
        if not isinstance(results, dict) or set(results) != {fixture["direction_id"]}:
            return verdict("FAIL", "final_results_missing")
        if validator.get("groups") != {} or validator.get("global") != []:
            return verdict("FAIL", "final_out_of_scope_results_present")
        if state.get("profile_fingerprint") != expected_profile_sha \
                or Path(str(state.get("profile_path", ""))).resolve() != expected_profile:
            return verdict("FAIL", "final_profile_binding_mismatch")
        for scope in round_records[-1].get("scopes", []):
            if not isinstance(scope, dict) or not str(scope.get("scope", "")).startswith("direction:"):
                return verdict("INVALID_EVIDENCE", "final_scope_unreadable")
            direction_id = scope["scope"].split(":", 1)[1]
            result = results.get(direction_id)
            if not isinstance(result, dict) or result.get("rounds") != rounds:
                return verdict("FAIL", "final_state_round_mismatch", direction_id=direction_id)
            expected_result = "fail_after_2_rounds" if scope.get("result") == "fail" else scope.get("result")
            if result.get("result") != expected_result:
                return verdict("FAIL", "final_state_result_mismatch", direction_id=direction_id)
        forbidden_stage4 = (
            expected_professor_dir / "套磁选择.json",
            expected_professor_dir / "邮件输入.json",
            expected_program_root / "教授研究/套磁选择.json",
            expected_program_root / "教授研究/邮件输入.json",
        )
        for path in forbidden_stage4:
            if path.exists():
                return verdict("FAIL", "forbidden_stage4_output_present", path=str(path))

    rebuild = commands[-1]
    overview_path = rebuild["output"].get("overview_md") if rebuild["output"] else None
    expected_overview = expected_program_root / "教授研究" / "套磁想法候选总览.md"
    root_completions = [entry for entry in completions if entry.get("thread_id") == root]
    if len(root_completions) != 1 or not isinstance(overview_path, str) or not overview_path:
        return verdict("INVALID_EVIDENCE", "root_completion_unobservable")
    if Path(overview_path).resolve() != expected_overview:
        return verdict("FAIL", "rebuilt_overview_path_mismatch")
    if inspect_files and not expected_overview.is_file():
        return verdict("INVALID_EVIDENCE", "rebuilt_overview_missing")
    root_completion = root_completions[0]
    root_turn = root_completion.get("turn")
    if not isinstance(root_turn, dict) or root_turn.get("status") != "completed" \
            or root_turn.get("error") is not None:
        return verdict("FAIL", "root_turn_failed")
    root_items = root_turn.get("items")
    if not isinstance(root_items, list):
        return verdict("INVALID_EVIDENCE", "root_report_unreadable")
    root_finals = [item for item in root_items
                   if isinstance(item, dict) and item.get("type") == "agentMessage"
                   and item.get("phase") == "final_answer"]
    if len(root_finals) != 1 or not isinstance(root_finals[0].get("text"), str):
        return verdict("INVALID_EVIDENCE", "root_report_unreadable")
    if root_completion["seq"] <= rebuild["seq"] \
            or overview_path not in root_finals[0]["text"]:
        return verdict("FAIL", "root_report_mismatch")

    return verdict("PASS", "all_checks_passed", rounds=rounds,
                   attempts=len(formal), completed=len(completion_by_child),
                   roles=role_counts, model=actual_model, reasoning=actual_reasoning,
                   cli_version=root_starts[0]["thread"].get("cliVersion"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--fixture-manifest", type=Path, required=True)
    parser.add_argument("--http-status-file", type=Path, required=True)
    parser.add_argument("--curl-exit-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        http_status = int(args.http_status_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        http_status = 0
    try:
        curl_exit = int(args.curl_exit_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        curl_exit = 1
    response, _ = load_json(args.response)
    adapter, _ = load_json(args.adapter)
    fixture, _ = load_json(args.fixture_manifest)
    result = classify(response, adapter, fixture, http_status=http_status,
                      curl_exit=curl_exit)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    return 0 if result["classification"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
