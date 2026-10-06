#!/usr/bin/env python3
"""PC68-R1 verifier: professor-local business consumption and root orchestration."""
import argparse
import hashlib
import json
import shlex
import uuid
from pathlib import Path

import verify_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r13 as final_source


AGENT = base.AGENT
verdict = base.verdict
combine = base.combine
owner_outcome = base.owner_outcome
codex_final_result_source = final_source.codex_final_result_source


ACTIONS = {"stage5-list-inputs", "stage5-partition-choices", "stage5-plan",
           "stage5-rebuild-overview"}
OWNER_OBSERVATION_SCHEMA = "issue-68-test-plan-r25-owner-input-v2"
OWNER_CAPTURE_SCHEMA = "issue-68-test-plan-r25-fixed-owner-capture-v1"
OWNER_CAPTURE_NAME = "capture_issue68_owner_stage5_plan_r1.py"
OWNER_CAPTURE_SOURCE = Path(__file__).resolve().parent / OWNER_CAPTURE_NAME
# This digest is pinned to the fixed, repository-owned capture implementation.
OWNER_CAPTURE_SHA256 = "7e534f76b7ba837a415b9b9a38ecda4a0fb1fe62fbf6d5b2575119319ff4eaa9"
OWNER_CAPTURE_COMMAND_PREFIX = ["uv", "run", "--no-project", "python"]


def _valid_generation(value):
    # Current service generations are JSON integers. Keep historical string
    # identifiers, but Python's True == 1 must never establish attribution.
    return type(value) is int or (type(value) is str and bool(value))


def _same_generation(left, right):
    return _valid_generation(left) and type(left) is type(right) and left == right


def _terminal_contract():
    """Load the single machine-to-formal mapping from the runtime contract."""
    contract_path = Path(__file__).resolve().parent / "issue68-runtime-evidence-contract-r19.json"
    value = json.loads(contract_path.read_text(encoding="utf-8"))
    mapping = value.get("machine_terminal_mapping")
    if not isinstance(mapping, dict) or not isinstance(mapping.get("unknown_machine_state"), str):
        raise ValueError("machine_terminal_mapping_invalid")
    return mapping


def formal_terminal(machine_state):
    """Map every recognized verifier/adapter state using the runtime contract."""
    try:
        mapping = _terminal_contract()
    except (OSError, ValueError, TypeError):
        return "INVALID_TEST_EXECUTION"
    return mapping.get(machine_state, mapping.get("unknown_machine_state", "INVALID_TEST_EXECUTION"))


def combine_formal_terminals(machine_states):
    """Keep each owner's terminal; only a confirmed product failure rolls up.

    ``machine_states`` may be a mapping from owner identity to raw machine
    state, or an ordered iterable of raw states. All non-failure states stay
    attached to their owner and are never ranked against one another.
    """
    try:
        mapping = _terminal_contract()
    except (OSError, ValueError, TypeError):
        return {"children": [], "overall_terminal": "INVALID_TEST_EXECUTION",
                "confirmed_product_failure": False}
    entries = machine_states.items() if isinstance(machine_states, dict) else enumerate(machine_states)
    children = []
    for child, state in entries:
        machine_state = state if isinstance(state, str) else "unknown_machine_state"
        terminal = mapping.get(machine_state, mapping["unknown_machine_state"])
        children.append({"child": child, "machine_state": machine_state,
                         "formal_terminal": terminal})
    confirmed_product_failure = any(
        row["machine_state"] == "FAIL_PRODUCT" and row["formal_terminal"] == "FAIL"
        for row in children
    )
    return {
        "children": children,
        "confirmed_product_failure": confirmed_product_failure,
        "overall_terminal": "FAIL" if confirmed_product_failure else None,
    }


def command_action(command, manifest):
    """Only a structured executed shell item can supply a stage5 CLI invocation.

    Same structural gate as the base parser. r19 adds
    ``stage5-partition-choices`` to the supported actions, lets ``--owner``
    repeat on the partition call (values accumulate into a list) and pins
    ``--program-root`` to the manifest program root.
    """
    tokens = shlex.split(command)
    capture = _owner_capture_command(tokens, manifest)
    if capture is not None:
        return {"action": "stage5-plan", "flags": {}, "owner_capture": capture}
    if len(tokens) == 3 and Path(tokens[0]).name in ("sh", "bash", "zsh") and tokens[1] in ("-c", "-lc"):
        tokens = shlex.split(tokens[2])
    found = [token for token in tokens if token in ACTIONS]
    if not found:
        return None
    # Compound shell/code expressions are outside this parser's frozen
    # command grammar. Missing observation is never inferred as no call.
    if len(found) != 1 or any(token in (";", "&&", "||", "|") for token in tokens):
        raise ValueError("compound_or_multiple_stage5_commands")
    action = found[0]
    index = tokens.index(action)
    if index == 0 or Path(tokens[index - 1]).name != "contact_state.py":
        raise ValueError("stage5_invocation_script_unobservable")
    tail = tokens[index + 1:]
    if "--help" in tail or "-h" in tail:
        return None
    if len(tail) % 2:
        raise ValueError("stage5_invocation_arguments_unobservable")
    flags = {}
    for offset in range(0, len(tail), 2):
        flag, value = tail[offset], tail[offset + 1]
        if not flag.startswith("--"):
            raise ValueError("stage5_invocation_arguments_unobservable")
        if flag == "--owner":
            flags.setdefault(flag, []).append(value)
            continue
        if flag in flags:
            raise ValueError("stage5_invocation_arguments_unobservable")
        flags[flag] = value
    if flags.get("--program-root") != manifest["program_root"]:
        return {"action": action, "problem": "wrong_program_root"}
    return {"action": action, "flags": flags}


def _owner_capture_command(tokens, manifest):
    """Parse only the fixed direct wrapper invocation from command metadata."""
    if not any(Path(token).name == OWNER_CAPTURE_NAME for token in tokens):
        return None
    record = (manifest or {}).get("owner_capture", {})
    if not isinstance(record, dict):
        raise ValueError("owner_capture_manifest_missing")
    runtime_path = record.get("runtime_path")
    entrypoint = record.get("installed_entrypoint")
    expected_prefix = OWNER_CAPTURE_COMMAND_PREFIX + [runtime_path]
    if not isinstance(runtime_path, str) or not isinstance(entrypoint, str) \
            or tokens[:len(expected_prefix)] != expected_prefix:
        raise ValueError("owner_capture_command_prefix_mismatch")
    expected_tail_prefix = ["--action", "stage5-plan", "--owner-input-file"]
    offset = len(expected_prefix)
    if tokens[offset:offset + len(expected_tail_prefix)] != expected_tail_prefix \
            or len(tokens) != offset + 6 \
            or tokens[offset + 4] != "--contact-state" \
            or tokens[offset + 5] != entrypoint:
        raise ValueError("owner_capture_command_shape_invalid")
    input_path = tokens[offset + 3]
    if not Path(input_path).is_absolute():
        raise ValueError("owner_capture_input_path_not_absolute")
    return {"owner_input_file": input_path, "runtime_path": runtime_path,
            "installed_entrypoint": entrypoint, "argv": list(tokens)}


def is_business_surface(text):
    """Loose business-surface recognition over one command text.

    A command text is a consumption or orchestration candidate when it
    references the producer CLI (``contact_state.py``) and any supported
    stage5 action word. Real Codex hosts wrap both inside ``python3 -c`` and
    wrapper compound expressions — the action word then lives inside a quoted
    string, never a standalone token — so this check only decides whether a
    text is worth extracting business objects or output facts from; it never
    parses flags. Strict ``command_action`` parsing stays the only source for
    flag facts.
    """
    if not isinstance(text, str):
        return False
    return OWNER_CAPTURE_NAME in text or (
        "contact_state.py" in text and any(action in text for action in ACTIONS))


def is_owner_business_surface(text):
    """Only professor business commands supply consumed-input evidence."""
    return is_business_surface(text) and any(
        action in text for action in ("stage5-partition-choices", "stage5-plan"))


def consumed_business_objects(stage5_calls, manifest=None):
    """Read one r25 observation and plan result from each actual plan call.

    The only accepted source is the strict JSON envelope emitted by the
    existing owner-input parse action and the original ``stage5-plan`` call
    in the *same* commandExecution. Command text, standalone stdout objects,
    unrelated reads and later file contents are not substitutes. Each call is
    kept as its own row so repeated invocations cannot collapse together.
    """
    rows, seen_call_ids, missing_call_ids = [], set(), []
    plan_calls = []
    for call in stage5_calls:
        if not isinstance(call, dict):
            continue
        command = call.get("command", "")
        try:
            parsed = command_action(command, manifest or {"program_root": _packet_program_root(call)})
        except (ValueError, KeyError, TypeError):
            parsed = None
        action = parsed.get("action") if isinstance(parsed, dict) else _compound_action(command)
        if action == "stage5-plan":
            plan_calls.append(call)
    if not plan_calls:
        return [], verdict("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable")

    for call in sorted(plan_calls, key=lambda row: (row.get("start", -1), row.get("end", -1))):
        call_id = call.get("id")
        thread = call.get("thread")
        generation = call.get("generation")
        if not isinstance(call_id, str) or not call_id or call_id in seen_call_ids \
                or not isinstance(thread, str) or not thread \
                or not _valid_generation(generation):
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_association_invalid",
                               observed_call_id=call_id, observed_thread=thread,
                               observed_generation=generation)
        seen_call_ids.add(call_id)
        command = call.get("command", "")
        try:
            parsed = command_action(command, manifest or {"program_root": _packet_program_root(call)})
        except (ValueError, KeyError, TypeError):
            parsed = None
        action = parsed.get("action") if isinstance(parsed, dict) else _compound_action(command)
        if action != "stage5-plan":
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_step_ambiguous",
                               observed_call_id=call_id)
        output = call.get("output")
        if not isinstance(output, str) or not output.strip():
            missing_call_ids.append(call_id)
            continue
        try:
            envelope = _strict_json_object(output)
        except (ValueError, TypeError):
            # Output with unrelated diagnostics/reads or damaged JSON cannot
            # be interpreted as an input observation.
            if "pc68_actual_input_observation" not in output:
                missing_call_ids.append(call_id)
                continue
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_malformed",
                               observed_call_id=call_id)
        if "stage5_invocation" not in envelope:
            if "pc68_actual_input_observation" in envelope:
                return [], verdict("BLOCKED_OBSERVABILITY", "owner_stage5_invocation_unobservable",
                                   observed_call_id=call_id)
            missing_call_ids.append(call_id)
            continue
        if set(envelope) != {"pc68_fixed_capture", "pc68_actual_input_observation",
                             "stage5_invocation", "stage5_raw_stdout", "stage5_process",
                             "stage5_plan", "return_code"}:
            if "pc68_actual_input_observation" not in envelope:
                missing_call_ids.append(call_id)
                continue
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_shape_invalid",
                               observed_call_id=call_id)
        observation = envelope.get("pc68_actual_input_observation")
        plan = envelope.get("stage5_plan")
        if not isinstance(observation, dict) or observation.get("schema") != OWNER_OBSERVATION_SCHEMA \
                or observation.get("source_step") != "owner_input_json_parse" \
                or observation.get("business_step") != "stage5-plan" \
                or not isinstance(observation.get("object"), dict) \
                or not isinstance(plan, dict) or not isinstance(envelope.get("return_code"), int):
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_shape_invalid",
                               observed_call_id=call_id)
        packet = observation["object"]
        try:
            invocation = _structured_stage5_invocation(envelope["stage5_invocation"])
        except (ValueError, TypeError):
            return [], verdict("INVALID_EVIDENCE", "owner_stage5_invocation_invalid",
                               observed_call_id=call_id)
        try:
            command_proof = command_action(command, manifest or {})
        except (ValueError, TypeError):
            command_proof = None
        if not isinstance(command_proof, dict) or not isinstance(command_proof.get("owner_capture"), dict):
            return [], verdict("INVALID_EVIDENCE", "owner_fixed_capture_command_missing",
                               observed_call_id=call_id)
        capture_problem = _validate_fixed_capture(call, envelope, command_proof["owner_capture"],
                                                  packet, manifest or {})
        if capture_problem:
            return [], capture_problem
        if invocation["action"] != "stage5-plan":
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_step_ambiguous",
                               observed_call_id=call_id)
        pack = packet.get("email_pack")
        program_root = packet.get("program_root")
        if not isinstance(pack, str) or not pack or not isinstance(program_root, str) or not program_root:
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_identity_missing",
                               observed_call_id=call_id)
        if plan.get("email_pack") != pack:
            return [], verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                               observed_call_id=call_id, observed_pack=plan.get("email_pack"),
                               observed_input_pack=pack)
        rows.append({"packet": packet, "plan": plan, "invocation": invocation, "call_id": call_id,
                     "thread": thread, "generation": generation,
                     "command": command, "return_code": envelope["return_code"],
                     "start": call.get("start"), "end": call.get("end")})
    if missing_call_ids:
        return [], verdict("BLOCKED_OBSERVABILITY", "owner_actual_input_unobservable",
                           missing_call_ids=missing_call_ids)
    return rows, None


def _packet_program_root(call):
    """Only used to structurally parse direct commands without guessing flags."""
    command = call.get("command", "") if isinstance(call, dict) else ""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return ""
    for index, token in enumerate(tokens[:-1]):
        if token == "--program-root":
            return tokens[index + 1]
    # Compound wrappers have no strict flag facts; their output still needs
    # the observation envelope before it can be accepted.
    return ""


def _strict_json_object(text):
    """Parse exactly one JSON object, rejecting duplicate keys and extra text."""
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    value = json.loads(text, object_pairs_hook=unique_pairs)
    if not isinstance(value, dict):
        raise ValueError("json_top_level_not_object")
    return value


def _is_sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value)


def _validate_fixed_capture(call, envelope, command_capture, packet, manifest):
    """Bind output to the fixed wrapper and the independent command event."""
    record = manifest.get("owner_capture", {})
    if not isinstance(record, dict) or not OWNER_CAPTURE_SOURCE.is_file() \
            or _sha256_file(OWNER_CAPTURE_SOURCE) != OWNER_CAPTURE_SHA256:
        return verdict("INVALID_EVIDENCE", "owner_capture_source_not_pinned",
                       observed_call_id=call.get("id"))
    consumer_root = record.get("consumer_root")
    expected_runtime = (Path(consumer_root) / ".pc68-test-support" / OWNER_CAPTURE_NAME
                        if isinstance(consumer_root, str) else None)
    runtime_path = record.get("runtime_path")
    entrypoint = record.get("installed_entrypoint")
    try:
        manifest_artifact_matches = isinstance(record.get("manifest_path"), str) and \
            json.loads(Path(record["manifest_path"]).read_text(encoding="utf-8")) == manifest
    except (OSError, ValueError, TypeError):
        manifest_artifact_matches = False
    if expected_runtime is None or not isinstance(runtime_path, str) \
            or Path(runtime_path).resolve() != expected_runtime.resolve() \
            or Path(record.get("source_path", "")).resolve() != OWNER_CAPTURE_SOURCE.resolve() \
            or record.get("source_sha256") != OWNER_CAPTURE_SHA256 \
            or record.get("runtime_sha256") != OWNER_CAPTURE_SHA256 \
            or not manifest_artifact_matches \
            or not Path(runtime_path).is_file() or Path(runtime_path).is_symlink() \
            or _sha256_file(runtime_path) != OWNER_CAPTURE_SHA256 \
            or not isinstance(entrypoint, str) or not Path(entrypoint).is_file() \
            or Path(entrypoint).is_symlink() \
            or _sha256_file(entrypoint) != record.get("entrypoint_sha256"):
        return verdict("INVALID_EVIDENCE", "owner_capture_manifest_mismatch",
                       observed_call_id=call.get("id"))
    if command_capture.get("runtime_path") != runtime_path \
            or command_capture.get("installed_entrypoint") != entrypoint:
        return verdict("INVALID_EVIDENCE", "owner_capture_command_binding_mismatch",
                       observed_call_id=call.get("id"))

    capture = envelope.get("pc68_fixed_capture")
    invocation = envelope.get("stage5_invocation")
    process = envelope.get("stage5_process")
    raw_stdout = envelope.get("stage5_raw_stdout")
    return_code = envelope.get("return_code")
    if not isinstance(capture, dict) or set(capture) != {
            "schema", "capture_id", "wrapper_sha256", "wrapper_arguments",
            "owner_input_file", "owner_input_sha256", "owner_input_read_count",
            "parsed_object_sha256"}:
        return verdict("INVALID_EVIDENCE", "owner_capture_record_malformed",
                       observed_call_id=call.get("id"))
    capture_id = capture.get("capture_id")
    try:
        canonical_id = str(uuid.UUID(capture_id))
    except (ValueError, TypeError, AttributeError):
        canonical_id = None
    if capture.get("schema") != OWNER_CAPTURE_SCHEMA or canonical_id != capture_id \
            or capture.get("wrapper_sha256") != OWNER_CAPTURE_SHA256 \
            or capture.get("owner_input_file") != command_capture.get("owner_input_file") \
            or capture.get("owner_input_read_count") != 1 \
            or not _is_sha256(capture.get("owner_input_sha256")) \
            or capture.get("parsed_object_sha256") != _sha256_bytes(_canonical_json(packet).encode("utf-8")):
        return verdict("INVALID_EVIDENCE", "owner_capture_output_binding_mismatch",
                       observed_call_id=call.get("id"))
    expected_wrapper_arguments = [
        "--action", "stage5-plan", "--owner-input-file", command_capture["owner_input_file"],
        "--contact-state", entrypoint,
    ]
    if capture.get("wrapper_arguments") != expected_wrapper_arguments:
        return verdict("INVALID_EVIDENCE", "owner_capture_invocation_binding_mismatch",
                       observed_call_id=call.get("id"))
    if not isinstance(invocation, dict) or set(invocation) != {"capture_id", "argv"} \
            or invocation.get("capture_id") != capture_id \
            or not isinstance(process, dict) \
            or set(process) != {"capture_id", "stdout_sha256", "stderr_sha256"} \
            or process.get("capture_id") != capture_id \
            or not _is_sha256(process.get("stdout_sha256")) \
            or not _is_sha256(process.get("stderr_sha256")) \
            or not isinstance(raw_stdout, str) or type(return_code) is not int:
        return verdict("INVALID_EVIDENCE", "owner_capture_process_binding_mismatch",
                       observed_call_id=call.get("id"))
    stdout_bytes = raw_stdout.encode("utf-8")
    if process["stdout_sha256"] != _sha256_bytes(stdout_bytes):
        return verdict("INVALID_EVIDENCE", "owner_capture_stdout_hash_mismatch",
                       observed_call_id=call.get("id"))
    try:
        parsed_stdout = _strict_json_object(raw_stdout)
    except (ValueError, TypeError):
        return verdict("INVALID_EVIDENCE", "owner_capture_raw_stdout_invalid",
                       observed_call_id=call.get("id"))
    if parsed_stdout != envelope.get("stage5_plan"):
        return verdict("INVALID_EVIDENCE", "owner_capture_structured_output_mismatch",
                       observed_call_id=call.get("id"))
    try:
        invocation_parsed = _structured_stage5_invocation(invocation)
    except (ValueError, TypeError):
        return verdict("INVALID_EVIDENCE", "owner_stage5_invocation_invalid",
                       observed_call_id=call.get("id"))
    argv = invocation_parsed["argv"]
    if not argv or not Path(argv[0]).is_absolute() or len(argv) < 3 \
            or str(Path(argv[1]).resolve()) != entrypoint or argv[2] != "stage5-plan":
        return verdict("INVALID_EVIDENCE", "owner_capture_child_argv_mismatch",
                       observed_call_id=call.get("id"))
    expected_child_tail = ["stage5-plan", "--program-root", packet.get("program_root"),
                           "--email-pack", packet.get("email_pack")]
    if packet.get("email_id") is not None:
        expected_child_tail.extend(["--email-id", packet.get("email_id")])
    expected_child_tail.extend(["--template", packet.get("template"), "--mode", packet.get("mode")])
    if argv[2:] != expected_child_tail:
        return verdict("INVALID_EVIDENCE", "owner_capture_child_argv_binding_mismatch",
                       observed_call_id=call.get("id"))
    return None


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path):
    return _sha256_bytes(Path(path).read_bytes())


def _structured_stage5_invocation(value):
    """Parse the exact argv vector recorded at the installed CLI boundary.

    The vector is emitted by the same command wrapper that passes it to the
    existing contact_state.py process. Never recover these facts from the
    shell command string: wrappers and ``python -c`` calls do not expose their
    actual child argv there.
    """
    if not isinstance(value, dict) or set(value) != {"capture_id", "argv"}:
        raise ValueError("stage5_invocation_shape_invalid")
    try:
        if str(uuid.UUID(value.get("capture_id"))) != value.get("capture_id"):
            raise ValueError("stage5_invocation_capture_id_invalid")
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("stage5_invocation_capture_id_invalid") from exc
    argv = value.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) for arg in argv):
        raise ValueError("stage5_invocation_argv_invalid")
    scripts = [index for index, arg in enumerate(argv)
               if Path(arg).name == "contact_state.py"]
    if len(scripts) != 1:
        raise ValueError("stage5_invocation_script_ambiguous")
    action_index = scripts[0] + 1
    if action_index >= len(argv) or argv[action_index] not in ACTIONS:
        raise ValueError("stage5_invocation_action_invalid")
    action = argv[action_index]
    tail = argv[action_index + 1:]
    if len(tail) % 2:
        raise ValueError("stage5_invocation_arguments_invalid")
    flags = {}
    for offset in range(0, len(tail), 2):
        flag, item = tail[offset], tail[offset + 1]
        if not flag.startswith("--"):
            raise ValueError("stage5_invocation_arguments_invalid")
        if flag == "--owner":
            flags.setdefault(flag, []).append(item)
            continue
        if flag in flags:
            raise ValueError("stage5_invocation_arguments_invalid")
        flags[flag] = item
    return {"action": action, "flags": flags, "argv": list(argv),
            "capture_id": value.get("capture_id")}


def _choices_summary(observed, expected):
    """Compact machine-readable summary of how consumed choices deviate."""
    summary = {"observed_rows": len(observed) if isinstance(observed, list) else None,
               "expected_rows": len(expected) if isinstance(expected, list) else None}
    if isinstance(observed, list) and isinstance(expected, list):
        summary["changed_row_indexes"] = [index for index in range(max(len(observed), len(expected)))
                                          if index >= len(observed) or index >= len(expected)
                                          or observed[index] != expected[index]]
    else:
        summary["observed_type"] = type(observed).__name__
    return summary


def _owner_invocation_argument_problem(row, packet):
    """Require actual argv business arguments to come from this parse object."""
    invocation = row.get("invocation")
    if not isinstance(invocation, dict) or invocation.get("action") != "stage5-plan":
        return verdict("INVALID_EVIDENCE", "owner_stage5_invocation_invalid",
                       observed_call_id=row.get("call_id"))
    flags = invocation.get("flags")
    if not isinstance(flags, dict):
        return verdict("INVALID_EVIDENCE", "owner_stage5_invocation_invalid",
                       observed_call_id=row.get("call_id"))

    required_arguments = (
        ("--program-root", "program_root"),
        ("--email-pack", "email_pack"),
        ("--template", "template"),
        ("--mode", "mode"),
    )
    for flag, field in required_arguments:
        expected = packet.get(field)
        if not isinstance(expected, str) or not expected:
            return verdict("FAIL_PRODUCT", "owner_handoff_argument_missing",
                           observed_call_id=row.get("call_id"), argument=flag,
                           source_field=field)
        if flags.get(flag) != expected:
            return verdict("FAIL_PRODUCT", "owner_stage5_invocation_argument_changed",
                           observed_call_id=row.get("call_id"), argument=flag,
                           expected=expected, observed=flags.get(flag))

    expected_email_id = packet.get("email_id")
    has_email_id = "--email-id" in flags
    if (expected_email_id is None and has_email_id) or (
            expected_email_id is not None and
            (not has_email_id or flags.get("--email-id") != expected_email_id)):
        return verdict("FAIL_PRODUCT", "owner_stage5_invocation_argument_changed",
                       observed_call_id=row.get("call_id"), argument="--email-id",
                       expected=expected_email_id, observed=flags.get("--email-id"),
                       observed_present=has_email_id)
    return None


def owner_payload(rows, manifest, actual_partition=None):
    """Validate every same-call packet and its directly associated plan result."""
    if not rows:
        return None, verdict("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable")
    first = rows[0]
    packet = first["packet"]
    pack = packet["email_pack"]
    owner = next((candidate for candidate in manifest["owners"]
                  if candidate["email_pack"] == pack), None)
    if owner is None:
        return None, verdict("FAIL_PRODUCT", "unexpected_owner_pack", observed_pack=pack)
    if first.get("generation") is None or first.get("thread") is None:
        return None, verdict("INVALID_EVIDENCE", "owner_input_observation_association_invalid")
    if actual_partition is None:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_partition_result_unobservable")
    sources = [entry for entry in actual_partition
               if entry.get("professor_dir") == owner["professor_dir"]]
    if len(sources) != 1:
        return None, verdict("INVALID_EVIDENCE", "owner_partition_source_ambiguous")
    source = sources[0]
    if source.get("status") != "ok":
        return None, verdict("FAIL_PRODUCT", "owner_handoff_from_failed_partition")
    if packet.get("email_pack") != source.get("email_pack"):
        return None, verdict("FAIL_PRODUCT", "owner_pack_changed_from_partition", observed_pack=pack)
    if packet.get("email_id") != source.get("email_id"):
        return None, verdict("FAIL_PRODUCT", "owner_target_changed_from_partition", observed_pack=pack)
    if packet.get("program_root") != manifest.get("program_root"):
        return None, verdict("FAIL_PRODUCT", "owner_program_root_changed", observed_pack=pack)
    if str(Path(pack).parent) != owner["professor_dir"]:
        return None, verdict("FAIL_PRODUCT", "owner_professor_directory_changed",
                             observed_pack=pack, observed_professor_dir=str(Path(pack).parent))
    if "professor_dir" in packet and packet["professor_dir"] != owner["professor_dir"]:
        return None, verdict("FAIL_PRODUCT", "owner_professor_directory_changed",
                             observed_pack=pack, observed_professor_dir=packet["professor_dir"])
    if "choices_scope" in packet:
        return None, verdict("FAIL_PRODUCT", "owner_input_carries_choices_scope", observed_pack=pack)
    if "choices" not in packet:
        return None, verdict("FAIL_PRODUCT", "choices_transport_missing", observed_pack=pack)
    if packet["choices"] != source.get("choices_rows"):
        return None, verdict("FAIL_PRODUCT", "owner_bundle_choices_changed", observed_pack=pack,
                             choices_summary=_choices_summary(packet["choices"], source.get("choices_rows")))
    if "email_id" in packet and packet["email_id"] not in owner["email_ids"]:
        return None, verdict("FAIL_PRODUCT", "owner_target_mismatch", observed_pack=pack,
                             observed_email_id=packet["email_id"])
    if packet.get("result") != owner.get("result"):
        return None, verdict("FAIL_PRODUCT", "owner_result_path_changed", observed_pack=pack,
                             observed_result=packet.get("result"))
    if packet.get("mode") != "first":
        return None, verdict("FAIL_PRODUCT", "owner_mode_changed", observed_pack=pack,
                             observed_mode=packet.get("mode"))
    first_invocation = first.get("invocation")
    if not isinstance(first_invocation, dict) or first_invocation.get("action") != "stage5-plan":
        return None, verdict("INVALID_EVIDENCE", "owner_stage5_invocation_invalid",
                             observed_call_id=first.get("call_id"))
    if any(flag in first_invocation.get("flags", {}) for flag in ("--result", "--choices")):
        return None, verdict("FAIL_PRODUCT", "owner_initial_plan_carries_result_or_choices",
                             observed_call_id=first.get("call_id"))
    for row in rows:
        flags = row.get("invocation", {}).get("flags", {})
        invocation_problem = _owner_invocation_argument_problem(row, row["packet"])
        if invocation_problem:
            return None, invocation_problem
        if "--choices-scope" in flags:
            return None, verdict("FAIL_PRODUCT", "owner_plan_carries_choices_scope",
                                 observed_call_id=row.get("call_id"))
        if row["packet"] != packet:
            return None, verdict("FAIL_PRODUCT", "owner_input_changed_between_calls",
                                 observed_call_id=row.get("call_id"))
        if row["thread"] != first["thread"] or row["generation"] != first["generation"]:
            return None, verdict("INVALID_EVIDENCE", "owner_input_observation_association_ambiguous",
                                 observed_call_id=row.get("call_id"))
    text = json.dumps([row["packet"] for row in rows] + [row["plan"] for row in rows],
                      ensure_ascii=False)
    markers = [marker for marker in owner["sibling_exclusions"] if marker in text]
    if markers:
        return None, verdict("FAIL_PRODUCT", "owner_input_contains_sibling_data", observed_pack=pack,
                             observed_markers=markers)
    problem = _verify_owner_plan_package(rows, owner, manifest)
    if problem:
        return None, problem
    return pack, None


def _truncated(value, maximum):
    value = value or ""
    if not isinstance(value, str) or len(value) <= maximum:
        return value
    return value[:maximum] + "…"


def _expected_model_input(email):
    gaps = []
    for gap in email.get("gaps", []):
        gaps.append({
            "gap_id": gap["gap_id"], "item_key": gap["item_key"],
            "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
            "quote": _truncated(gap.get("quote"), 300),
            "translation_zh": _truncated(gap.get("translation_zh"), 200),
            "page": gap.get("page"), "status": gap.get("status"),
            "email_use": gap.get("email_use"), "remaining_gap": gap.get("remaining_gap"),
            "completed_part": gap.get("completed_part")
                if gap.get("email_use") == "extension_context_only" else None,
            "evidence": gap.get("evidence"), "confidence": gap.get("confidence"),
        })
    return {
        "idea": email.get("idea"), "direction_ids": email.get("direction_ids") or [],
        "directions": email.get("directions") or [],
        "user_note": _truncated(email.get("user_note"), 800),
        "papers": email.get("papers"), "gaps": gaps,
        "red_lines": email.get("red_lines"),
        "soft_materials": {"positioning": email.get("soft_materials", {}).get("positioning", [])},
        "user_supplement": email.get("user_supplement") or "",
        "allowed_sources": email.get("allowed_sources"),
    }


def _verify_owner_plan_package(rows, owner, manifest):
    """Compare actual structured plan fields with the pre-run owner pack facts."""
    pack_path = owner["email_pack"]
    try:
        raw = Path(pack_path).read_bytes()
        expected_hash = manifest.get("pre_run_hashes", {}).get(pack_path)
        if expected_hash and hashlib.sha256(raw).hexdigest() != expected_hash:
            return verdict("INVALID_EVIDENCE", "owner_fixture_pack_changed", observed_pack=pack_path)
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        return verdict("INVALID_EVIDENCE", "owner_fixture_pack_unreadable", observed_pack=pack_path)
    emails = payload.get("emails")
    if not isinstance(emails, list) or any(not isinstance(email, dict) for email in emails):
        return verdict("INVALID_EVIDENCE", "owner_fixture_pack_malformed", observed_pack=pack_path)
    ids = [email.get("email_id") for email in emails]
    if any(not isinstance(email_id, str) or not email_id for email_id in ids) or len(set(ids)) != len(ids):
        return verdict("INVALID_EVIDENCE", "owner_fixture_pack_malformed", observed_pack=pack_path)
    by_id = {email["email_id"]: email for email in emails}
    for index, observed in enumerate(rows):
        target_id = observed["packet"].get("email_id")
        if target_id is not None and target_id not in by_id:
            return verdict("FAIL_PRODUCT", "owner_target_mismatch", observed_pack=pack_path,
                           observed_email_id=target_id)
        selected_emails = [by_id[target_id]] if target_id is not None else emails
        expected_ids = [email.get("email_id") for email in selected_emails]
        plan = observed["plan"]
        if index == 0:
            required_fields = {
                "status", "email_pack", "emails", "template", "output_mode",
                "verify", "needs_recheck_professors", "jobs",
            }
            missing_fields = sorted(required_fields - set(plan))
            if missing_fields:
                return verdict("FAIL_PRODUCT", "owner_initial_plan_fields_missing",
                               observed_call_id=observed.get("call_id"),
                               missing_fields=missing_fields)
        if plan.get("email_pack") != pack_path:
            return verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                           observed_call_id=observed.get("call_id"), observed_pack=plan.get("email_pack"))
        if "emails" in plan and plan.get("emails") != expected_ids:
            return verdict("FAIL_PRODUCT", "owner_plan_email_ids_changed",
                           observed_call_id=observed.get("call_id"), observed_emails=plan.get("emails"))
        jobs = plan.get("jobs")
        if index == 0 and (plan.get("status") != "ok" or not isinstance(jobs, list)
                           or observed.get("return_code") != 0):
            return verdict("FAIL_PRODUCT", "owner_initial_plan_changed",
                           observed_call_id=observed.get("call_id"), observed_status=plan.get("status"))
        if index == 0 and (plan.get("template") != observed["packet"].get("template")
                           or plan.get("output_mode") != observed["packet"].get("mode")):
            return verdict("FAIL_PRODUCT", "owner_initial_plan_business_data_changed",
                           observed_call_id=observed.get("call_id"))
        if index == 0:
            professor = owner.get("professor")
            expected_verify = {professor: "needs_recheck:missing"}
            if professor is None or plan.get("verify") != expected_verify \
                    or plan.get("needs_recheck_professors") != [professor]:
                return verdict("FAIL_PRODUCT", "owner_initial_plan_verification_changed",
                               observed_call_id=observed.get("call_id"),
                               observed_verify=plan.get("verify"))
        if jobs is None:
            # Later calls may stop legally at the existing verification gate.
            if plan.get("status") not in {"needs_input", "needs_refresh", "ok"}:
                return verdict("FAIL_PRODUCT", "owner_plan_status_changed",
                               observed_call_id=observed.get("call_id"), observed_status=plan.get("status"))
            continue
        if not isinstance(jobs, list) or len(jobs) != len(selected_emails):
            return verdict("FAIL_PRODUCT", "owner_plan_email_ids_changed",
                           observed_call_id=observed.get("call_id"))
        job_ids = [job.get("job_id") if isinstance(job, dict) else None for job in jobs]
        expected_job_ids = {"email:" + email_id for email_id in expected_ids}
        if any(not isinstance(job_id, str) for job_id in job_ids) or \
                len(set(job_ids)) != len(job_ids) or set(job_ids) != expected_job_ids:
            return verdict("FAIL_PRODUCT", "owner_plan_email_ids_changed",
                           observed_call_id=observed.get("call_id"), observed_job_ids=job_ids)
        for job in jobs:
            if not isinstance(job, dict) or job.get("kind") != "email":
                return verdict("FAIL_PRODUCT", "owner_plan_business_data_changed",
                               observed_call_id=observed.get("call_id"))
            email_id = job.get("job_id", "").removeprefix("email:")
            email = {row.get("email_id"): row for row in selected_emails}.get(email_id)
            if email is None or job.get("job_id") != "email:" + str(email.get("email_id")):
                return verdict("FAIL_PRODUCT", "owner_plan_email_ids_changed",
                               observed_call_id=observed.get("call_id"), observed_job_id=job.get("job_id"))
            expected = _expected_model_input(email)
            actual = job.get("model_input")
            if not isinstance(actual, dict) or any(key not in actual or actual.get(key) != value
                                                   for key, value in expected.items()):
                return verdict("FAIL_PRODUCT", "owner_plan_business_data_changed",
                               observed_call_id=observed.get("call_id"), observed_email_id=email_id)
    return None


def final_result_rows(texts):
    """Professor rows from the pinned final message's direct report values."""
    return [row for row in _final_report_candidates(texts)
            if "professor_dir" in row and "status" in row and "reason_code" in row]


def _is_overview_result(value):
    """Recognize producer rebuild results from their actual structured shape."""
    if not isinstance(value, dict) or not isinstance(value.get("status"), str):
        return False
    if value["status"] == "ok":
        return {"overview_md", "professors", "emails"} <= set(value)
    return value["status"] in {"needs_decision", "error"} \
        and isinstance(value.get("reason_code"), str) and bool(value["reason_code"])


def _final_report_candidates(texts):
    """Read direct result values; never recurse into history or diagnostics.

    A top-level array contributes its direct objects. A report object may put
    professor rows and the overview result side by side under arbitrary keys.
    One single-object envelope is allowed; grouping key names are not pinned.
    """
    candidates = []
    for text in texts:
        for value in base.json_values(text):
            if isinstance(value, list):
                candidates.extend(row for row in value if isinstance(row, dict))
                continue
            if not isinstance(value, dict):
                continue
            if "professor_dir" in value or _is_overview_result(value):
                candidates.append(value)
                continue
            report = value
            if len(report) == 1:
                nested = next(iter(report.values()))
                if isinstance(nested, dict):
                    report = nested
            for member in report.values():
                if isinstance(member, dict):
                    candidates.append(member)
                elif isinstance(member, list):
                    candidates.extend(row for row in member if isinstance(row, dict))
    return candidates


def _overview_call_result(call):
    """Resolve exactly one result from this call's aggregatedOutput."""
    output = call.get("output")
    if not isinstance(output, str) or not output.strip():
        return None, verdict("BLOCKED_OBSERVABILITY", "root_overview_call_result_unobservable")
    if base.source_malformed([output]):
        return None, verdict("INVALID_EVIDENCE", "root_overview_call_result_malformed")
    values = base.json_values(output)
    if not values:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_overview_call_result_unobservable")
    results = [value for value in values if _is_overview_result(value)]
    if len(results) > 1:
        return None, verdict("INVALID_EVIDENCE", "root_overview_call_result_ambiguous")
    if len(results) != 1:
        return None, verdict("INVALID_EVIDENCE", "root_overview_call_result_unattributable")
    return results[0], None


def _receipt_body(item):
    """The frozen receipt body: only the item's ``input_text`` content parts."""
    content = item.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(part["text"] for part in content if isinstance(part, dict)
                     and part.get("type") == "input_text"
                     and isinstance(part.get("text"), str))


def _final_answer_payload(text, author_path):
    """The strictly shaped Codex child completion payload of one receipt body.

    The frozen receipt body is the three header lines ``Message Type:
    FINAL_ANSWER``, ``Task name: /root`` and ``Sender: <author_path>`` (each
    checked line by line, trailing whitespace tolerated), then the
    ``Payload:`` marker, then exactly one JSON object carrying the result.
    Any other shape — a different message type, a Sender line naming another
    agent, a missing marker or a body that does not parse into one JSON
    object — returns None: such a text is never a consumption receipt.
    """
    if not isinstance(text, str) or not isinstance(author_path, str):
        return None
    lines = text.splitlines()
    expected = ["Message Type: FINAL_ANSWER", "Task name: /root",
                "Sender: " + author_path, "Payload:"]
    if len(lines) <= len(expected):
        return None
    if any(line.rstrip() != want for line, want in zip(expected, lines)):
        return None
    try:
        payload = json.loads("\n".join(lines[len(expected):]).strip())
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def receipt_payload_outcomes(receipt, professor_dir):
    """The one outcome triple one receipt's Payload top level names for one owner.

    Only the strictly shaped FINAL_ANSWER body counts, and the ``Sender:``
    header must equal the receipt's own ``author``. The parsed Payload JSON is
    read at its top level only and never recursively: the object must carry
    ``professor_dir`` equal to this owner's directory as a top-level field and
    the outcome triple comes from the top-level fields alone. A payload whose
    top level names this owner but lacks ``status`` or ``reason_code`` is
    malformed evidence: it contributes no triple and the second return value
    reports the missing field names, so a missing field is never read as a
    ``None`` outcome. A receipt whose top level carries only a nested object
    (a diagnostic wrapper, for example), whose body fails the shape check or
    which names another professor_dir contributes nothing and is never this
    owner's consumption evidence.
    """
    payload = _final_answer_payload(receipt["text"], receipt["author"])
    if payload is None or payload.get("professor_dir") != professor_dir:
        return [], []
    missing = sorted(field for field in ("status", "reason_code") if field not in payload)
    if missing:
        return [], missing
    return [{key: payload[key] for key in ("professor_dir", "status", "reason_code")}], []


def _plan_checks(parsed, manifest, expected_pack):
    flags = parsed["flags"]
    if expected_pack is not None and flags.get("--email-pack") not in (None, expected_pack):
        return verdict("FAIL_PRODUCT", "owner_plan_directory_changed", observed_call=parsed.get("command"))
    if "--choices-scope" in flags:
        return verdict("FAIL_PRODUCT", "owner_plan_carries_choices_scope")
    if expected_pack is None:
        return None
    rows, problem = consumed_business_objects([parsed], manifest)
    if problem:
        return problem
    observed_pack = rows[0]["packet"].get("email_pack")
    if observed_pack != expected_pack:
        return verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                       observed_call_id=parsed.get("id"), observed_pack=observed_pack)
    if flags.get("--email-pack") not in (None, observed_pack):
        return verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                       observed_call_id=parsed.get("id"), observed_pack=flags.get("--email-pack"))
    return None


def _partition_payload(output):
    for value in base.json_values(output):
        if isinstance(value, dict) and value.get("status") == "ok":
            return value
    return None


def _owner_projection(entry):
    """Project every frozen owner identity and complete allocated choices.

    The supported output form carries the status nested under ``partition``;
    the flat form describes the same value, so both project identically.
    """
    if not isinstance(entry, dict):
        return {"professor_dir": None, "email_pack": None, "email_id": None,
                "status": None, "choices_rows": None}
    status = entry.get("status")
    if status is None and isinstance(entry.get("partition"), dict):
        status = entry["partition"].get("status")
    return {"professor_dir": entry.get("professor_dir"), "status": status,
            "email_pack": entry.get("email_pack"), "email_id": entry.get("email_id"),
            "choices_rows": entry.get("choices_rows")}


def _partition_rows(payload):
    owners = payload.get("owners")
    if not isinstance(owners, list):
        return None
    return [_owner_projection(entry) for entry in owners]


def _dir_key(row):
    return str(row.get("professor_dir"))


def _actual_root_partition(calls, manifest, root):
    """Resolve this run's root return before relating any professor input.

    Preparation expectations only check this actual return; they never serve
    as the source of the professor handoff comparison.
    """
    partitions, call_ids = [], set()
    for call in calls:
        if call.get("thread") != root:
            continue
        try:
            parsed = command_action(call.get("command", ""), manifest)
        except (ValueError, TypeError):
            parsed = None
        action = parsed.get("action") if parsed else _compound_action(call.get("command", ""))
        if action != "stage5-partition-choices":
            continue
        call_id = call.get("id")
        if not isinstance(call_id, str) or not call_id or call_id in call_ids \
                or not _valid_generation(call.get("generation")) \
                or not isinstance(call.get("start"), int) or not isinstance(call.get("end"), int) \
                or call["end"] <= call["start"]:
            return None, verdict("INVALID_EVIDENCE", "root_partition_call_association_invalid")
        call_ids.add(call_id)
        if parsed and parsed.get("problem"):
            return None, verdict("FAIL_PRODUCT", parsed["problem"])
        output = call.get("output")
        if not isinstance(output, str) or not output.strip():
            return None, verdict("BLOCKED_OBSERVABILITY", "root_partition_result_unobservable")
        try:
            payload = _strict_json_object(output)
        except (ValueError, TypeError):
            return None, verdict("INVALID_EVIDENCE", "root_partition_result_malformed")
        if payload.get("status") == "ok":
            rows = _partition_rows(payload)
            if rows is None or any(not isinstance(entry, dict) for entry in payload["owners"]):
                return None, verdict("INVALID_EVIDENCE", "root_partition_result_malformed")
            dirs = [row["professor_dir"] for row in rows]
            if any(not isinstance(directory, str) for directory in dirs) or len(set(dirs)) != len(dirs):
                return None, verdict("INVALID_EVIDENCE", "root_partition_owner_association_conflict")
            partitions.append((call, rows))
    if not partitions:
        if call_ids:
            return None, verdict("FAIL_PRODUCT", "root_partition_not_deterministic",
                                 partition_commands=len(call_ids))
        return None, verdict("BLOCKED_OBSERVABILITY", "root_partition_result_unobservable")
    if len(partitions) != 1:
        return None, verdict("FAIL_PRODUCT", "multiple_root_partitions")
    call, observed = partitions[0]
    expected = [_owner_projection(entry) for entry in manifest["partition"]["owners"]]
    if sorted(observed, key=_dir_key) != sorted(expected, key=_dir_key):
        return None, verdict("FAIL_PRODUCT", "root_partition_changed", observed_owners=observed)
    return {"call": call, "owners": observed}, None


def _compound_action(command):
    """The single supported stage5 action word in a compound command text.

    Compound host expressions carry action words inside quoted strings, so
    strict parsing cannot attribute them; the loose text scan does. Returns
    None when several action words appear — such a text cannot be attributed
    to one orchestration step.
    """
    actions = [action for action in ACTIONS if action in command]
    return actions[0] if len(actions) == 1 else None


def _final_result_role_ambiguity(source_matches, manifest, outcomes=None):
    """Reject one final object that is both the rebuild result and an owner row."""
    for row in source_matches:
        if not isinstance(row, dict):
            continue
        for owner in manifest["owners"]:
            expected = (outcomes or {}).get(owner["email_pack"],
                        dict(owner["expected_result"], professor_dir=owner["professor_dir"]))
            if row.get("professor_dir") != owner["professor_dir"] or \
                    any(field not in row for field in ("status", "reason_code")):
                continue
            reported_owner = {key: row[key] for key in
                              ("professor_dir", "status", "reason_code")}
            if reported_owner == expected:
                return verdict("INVALID_EVIDENCE", "root_final_result_role_ambiguous",
                               observed_result=row, professor_dir=owner["professor_dir"])
    return None


def _early_final_result_role_ambiguity(calls, root, root_texts, manifest, outcomes=None):
    """Find a role collision before invalid owner-status results short-circuit."""
    if base.source_malformed(root_texts):
        return None
    rebuilds = []
    for call in calls:
        if call.get("thread") != root:
            continue
        command = call.get("command", "")
        try:
            parsed = command_action(command, manifest)
        except ValueError:
            if not is_business_surface(command):
                continue
            parsed = None
        if parsed is None:
            if not is_business_surface(command) or "--help" in command:
                continue
            action = _compound_action(command)
        else:
            if parsed.get("problem"):
                continue
            action = parsed.get("action")
        if action == "stage5-rebuild-overview":
            rebuilds.append(call)
    if len(rebuilds) != 1:
        return None
    overview_result, problem = _overview_call_result(rebuilds[0])
    if problem:
        return None
    source_matches = [row for row in _final_report_candidates(root_texts)
                      if row == overview_result]
    return _final_result_role_ambiguity(source_matches, manifest, outcomes)


def runtime_checks(calls, manifest, consumption_points, root_texts, root=None, outcomes=None, owner_threads=None):
    """The r21 root orchestration oracle over executed stage5 calls.

    Discovery must report exactly the fixture owner set and must not emit a
    choices scope; the root must succeed at exactly one partition whose
    per-owner bundles match the manifest partition record and whose
    completion precedes every owner business call; owner plans stay
    bound to their own pack and bundle file and never carry a choices scope;
    exactly one rebuild must run after every owner result was consumed
    (``consumption_points`` are the root's per-child result-consumption
    points, the earliest matching root-thread receipt seqs). The rebuild's
    ``aggregatedOutput`` is the result source, and the pinned final source must
    report that result separately while preserving one consistent consumed
    outcome per owner directory.

    A supported call is recognized on two surfaces. A call whose command
    parses strictly under ``command_action`` keeps every flag fact: only such
    a call can prove the ``--emit-choices-scope``/``--choices-scope``/
    ``--program-root`` facts. A compound command (a ``python3 -c``/wrapper
    preparation whose action words are quoted string fragments, never
    standalone tokens) is recognized by ``is_business_surface`` plus its
    single action word and contributes only its thread attribution and its
    ``aggregatedOutput``: discovery and partition success are judged from the
    output JSON alone. A compound root text carrying several action words
    cannot be attributed to one orchestration step and stays
    BLOCKED_OBSERVABILITY/root_orchestration_ambiguous. A child's compound
    consumption is judged by the packet oracle; on a child thread only a
    strictly parsed partition, or a compound text whose single action word is
    ``stage5-partition-choices``, proves ``partition_executed_by_owner``.
    """
    discovery, partitions, plans, rebuilds = [], [], [], []
    owner_threads = owner_threads or {}
    for call in calls:
        command, thread = call["command"], call.get("thread")
        if root is not None and thread != root and _compound_action(command) == "stage5-rebuild-overview":
            continue
        try:
            parsed = command_action(command, manifest)
        except ValueError as exc:
            if not is_business_surface(command):
                return verdict("BLOCKED_OBSERVABILITY", str(exc))
            parsed = None
        if parsed is None:
            if not is_business_surface(command):
                continue
            if "--help" in command:
                # Help output stays non-evidence, mirroring the strict
                # grammar's --help exclusion for compound texts too.
                continue
            action = _compound_action(command)
            if action is None:
                if root is None or thread == root:
                    return verdict("BLOCKED_OBSERVABILITY", "root_orchestration_ambiguous",
                                   detail=command[:200])
                continue
            if root is not None and thread != root:
                # A child's compound consumption is judged by the packet
                # oracle, never by orchestration flag facts.
                if action == "stage5-partition-choices":
                    return verdict("FAIL_PRODUCT", "partition_executed_by_owner")
                continue
            parsed = {"action": action, "flags": {}, "compound": True}
        if parsed.get("problem"):
            return verdict("FAIL_PRODUCT", parsed["problem"])
        parsed.update(call)
        action, thread = parsed["action"], call.get("thread")
        # Compound calls carry empty flags, so this scope check can only ever
        # fire for a strictly parsed discovery call.
        if action == "stage5-list-inputs" and "--emit-choices-scope" in parsed["flags"]:
            return verdict("FAIL_PRODUCT", "discovery_emits_choices_scope")
        if action == "stage5-plan":
            problem = _plan_checks(parsed, manifest, owner_threads.get(thread))
            if problem:
                return problem
        if root is not None and thread != root:
            if action == "stage5-rebuild-overview":
                continue
            if action == "stage5-partition-choices":
                return verdict("FAIL_PRODUCT", "partition_executed_by_owner")
            if action == "stage5-list-inputs":
                continue
            plans.append(parsed)
            continue
        if action == "stage5-list-inputs":
            discovery.append(parsed)
        elif action == "stage5-partition-choices":
            partitions.append(parsed)
        elif action == "stage5-plan":
            plans.append(parsed)
        else:
            rebuilds.append(parsed)
    if not discovery:
        return verdict("BLOCKED_OBSERVABILITY", "executed_discovery_unobservable")
    expected_packs = {owner["email_pack"] for owner in manifest["owners"]}
    discovered = None
    for call in discovery:
        for value in base.json_values(call.get("output")):
            if isinstance(value, dict) and value.get("status") == "ok" and isinstance(value.get("inputs"), list):
                discovered = {row.get("email_pack"): row.get("status") for row in value["inputs"]}
    if discovered is None:
        return verdict("BLOCKED_OBSERVABILITY", "discovery_result_unobservable")
    if discovered != {**{pack: "ok" for pack in expected_packs}, manifest["invalid_pack"]: "error"}:
        return verdict("FAIL_PRODUCT", "discovery_owner_set_changed")
    successful = [(call, payload) for call in partitions
                  for payload in [_partition_payload(call.get("output"))] if payload is not None]
    if not successful:
        return verdict("FAIL_PRODUCT", "root_partition_not_deterministic", partition_commands=len(partitions))
    if len(successful) > 1:
        return verdict("FAIL_PRODUCT", "multiple_root_partitions")
    partition_call, partition_payload = successful[0]
    observed = _partition_rows(partition_payload)
    expected = [_owner_projection(entry) for entry in manifest["partition"]["owners"]]
    if observed is None or sorted(observed, key=_dir_key) != sorted(expected, key=_dir_key):
        return verdict("FAIL_PRODUCT", "root_partition_changed", observed_owners=observed)
    # r20 ordering fact: the successful root partition must complete before
    # any owner business call starts on a child thread. On a child thread a
    # strictly parsed stage5-list-inputs stays outside the business surface;
    # plan and partition commands count as owner business calls.
    partition_end = partition_call["end"]
    for call in calls:
        if root is None or call.get("thread") == root:
            continue
        command = call.get("command", "")
        try:
            parsed = command_action(command, manifest)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed["action"] in {"stage5-list-inputs", "stage5-rebuild-overview"}:
                continue
        elif not is_owner_business_surface(command):
            continue
        if call["start"] < partition_end:
            return verdict("FAIL_PRODUCT", "owner_business_precedes_partition",
                           observed_call=command[:200])
    if len(rebuilds) > 1:
        return verdict("FAIL_PRODUCT", "multiple_aggregate_rebuilds")
    if not rebuilds:
        return verdict("FAIL_PRODUCT", "aggregate_rebuild_missing")
    if rebuilds[0]["start"] <= max(consumption_points):
        return verdict("FAIL_PRODUCT", "aggregate_precedes_result_consumption")
    overview_result, problem = _overview_call_result(rebuilds[0])
    if problem:
        return problem
    # The pinned final business result source is root's own final message.
    # Grouping names in that source are not part of the result contract; rows
    # and the overview result are associated by their direct object shapes.
    if base.source_malformed(root_texts):
        return verdict("INVALID_EVIDENCE", "root_final_result_malformed")
    candidates = _final_report_candidates(root_texts)
    source_matches = [row for row in candidates if row == overview_result]
    for row in source_matches:
        for owner in manifest["owners"]:
            expected = (outcomes or {}).get(owner["email_pack"],
                        dict(owner["expected_result"], professor_dir=owner["professor_dir"]))
            if row.get("professor_dir") != owner["professor_dir"] or \
                    "status" not in row or "reason_code" not in row:
                continue
            reported_owner = {key: row[key] for key in
                              ("professor_dir", "status", "reason_code")}
            if reported_owner == expected:
                return verdict("INVALID_EVIDENCE", "root_final_result_role_ambiguous",
                               observed_result=row, professor_dir=owner["professor_dir"])
    if len(source_matches) > 1:
        return verdict("INVALID_EVIDENCE", "root_overview_result_ambiguous",
                       observed_candidates=len(source_matches))
    source_match = source_matches[0] if source_matches else None
    owner_candidates = [row for row in candidates if row is not source_match]
    for owner in manifest["owners"]:
        expected = (outcomes or {}).get(owner["email_pack"],
                    dict(owner["expected_result"], professor_dir=owner["professor_dir"]))
        consumed = [row for row in owner_candidates
                    if row.get("professor_dir") == owner["professor_dir"]]
        if not consumed:
            return verdict("BLOCKED_OBSERVABILITY", "root_consumed_result_unobservable")
        if any("status" not in row or "reason_code" not in row for row in consumed):
            return verdict("INVALID_EVIDENCE", "root_final_result_malformed",
                           observed_professor_dir=owner["professor_dir"])
        seen = []
        for row in consumed:
            outcome = {key: row[key] for key in ("professor_dir", "status", "reason_code")}
            if outcome not in seen:
                seen.append(outcome)
        if len(seen) != 1:
            return verdict("FAIL_PRODUCT", "root_consumed_results_conflict", observed_results=seen)
        if seen[0] != expected:
            return verdict("FAIL_PRODUCT", "root_changed_owner_result", observed_result=seen[0])
    reported_overviews = [source_match] if source_match is not None else [
        row for row in owner_candidates
        if _is_overview_result(row) and (
            row.get("status") == "ok"
            or row.get("professor_dir") not in
               {owner["professor_dir"] for owner in manifest["owners"]}
            or any(field in row for field in ("overview_md", "professors", "emails"))
        )
    ]
    if not reported_overviews:
        return verdict("FAIL_PRODUCT", "root_overview_result_unreported")
    if len(reported_overviews) != 1:
        return verdict("INVALID_EVIDENCE", "root_overview_result_ambiguous",
                       observed_candidates=len(reported_overviews))
    if reported_overviews[0] != overview_result:
        return verdict("FAIL_PRODUCT", "root_overview_result_changed",
                       observed_result=reported_overviews[0], expected_result=overview_result)
    return verdict("PASS", owner_pack_set=sorted(expected_packs), rebuild_count=len(rebuilds),
                   partition_executions=1)


def _classify(problem, failures, invalids, blockers):
    bucket = problem.get("verdict")
    if bucket == "FAIL_PRODUCT":
        failures.append(problem)
    elif bucket == "INVALID_EVIDENCE":
        invalids.append(problem)
    else:
        blockers.append(problem)


def _independent_root_return_failure(calls, manifest, root, turn):
    """Positive current-turn facts independent of child and final observations.

    Missing calls or unusable returns prove nothing here. Count only distinct,
    paired calls; discovery and successful partitions require their complete
    actual structured returns, never command text or preparation expectations.
    """
    if not isinstance(turn, str) or not turn:
        return None
    attributed = [call for call in calls if call.get("thread") == root
                  and call.get("start_turn") == turn and call.get("end_turn") == turn
                  and isinstance(call.get("id"), str) and call["id"]
                  and call.get("start_command") == call.get("command")]
    ids = [call["id"] for call in attributed]
    # Repeated identifiers damage pairing and cannot prove two executions.
    attributed = [call for call in attributed if ids.count(call["id"]) == 1]
    rebuilds, partitions = [], []
    for call in attributed:
        command = call.get("command", "")
        try:
            parsed = command_action(command, manifest)
        except (ValueError, TypeError):
            parsed = None
        if parsed:
            action = parsed["action"]
        elif is_business_surface(command) and "--help" not in command:
            action = _compound_action(command)
        else:
            continue
        if action == "stage5-rebuild-overview":
            rebuilds.append(call)
            continue
        if type(call.get("exit_code")) is not int or call["exit_code"] != 0:
            continue
        try:
            payload = _strict_json_object(call.get("output"))
        except (ValueError, TypeError):
            continue
        if payload.get("status") != "ok":
            continue
        if action == "stage5-partition-choices":
            rows = _partition_rows(payload)
            if rows is None or any(not isinstance(entry, dict) for entry in payload["owners"]):
                continue
            dirs = [row["professor_dir"] for row in rows]
            if any(not isinstance(directory, str) for directory in dirs) \
                    or len(set(dirs)) != len(dirs):
                continue
            partitions.append(call)
        elif action == "stage5-list-inputs":
            inputs = payload.get("inputs")
            if not isinstance(inputs, list) or any(not isinstance(row, dict)
                    or not isinstance(row.get("email_pack"), str)
                    or not isinstance(row.get("status"), str) for row in inputs):
                continue
            packs = [row["email_pack"] for row in inputs]
            if len(set(packs)) != len(packs) or "invalid_pack" not in manifest:
                continue
            observed = {row["email_pack"]: row["status"] for row in inputs}
            expected = {owner["email_pack"]: "ok" for owner in manifest["owners"]}
            expected[manifest["invalid_pack"]] = "error"
            if observed != expected:
                return verdict("FAIL_PRODUCT", "discovery_owner_set_changed")
    if len(rebuilds) > 1:
        return verdict("FAIL_PRODUCT", "multiple_aggregate_rebuilds")
    if len(partitions) > 1:
        return verdict("FAIL_PRODUCT", "multiple_root_partitions")
    return None


def _verify_codex_events(response, adapter, manifest, final_problem=None):
    status = adapter.get("fixture_status")
    if status in ("INVALID_EVIDENCE", "HARNESS_ERROR", "HARNESS_CONTAMINATION"):
        return verdict("INVALID_EVIDENCE", "shared_adapter_rejected")
    if status == "BLOCKED_DEPENDENCY":
        return verdict("BLOCKED_DEPENDENCY", "shared_adapter_dependency_unavailable")
    if status not in ("FIXTURE_READY", "HARNESS_DISPATCH_UNCONFIRMED", "HARNESS_DISPATCH_MISMATCH"):
        return verdict("INVALID_EVIDENCE", "unknown_shared_adapter_status")
    raw = response.get("output", {})
    root, generation = raw.get("thread_id"), raw.get("runtime_generation")
    if not _valid_generation(generation):
        return verdict("INVALID_EVIDENCE", "event_order_or_generation_invalid")
    events = raw.get("app_server_events")
    if not isinstance(events, list) or not root:
        return verdict("BLOCKED_OBSERVABILITY", "app_server_events_unobservable")
    relations = adapter.get("dispatch", {}).get("thread_relations", [])
    children = {child for edge in relations if edge.get("tool") == "spawnAgent"
                and edge.get("sender_thread_id") == root
                for child in edge.get("receiver_thread_ids", [])}
    results = {}
    agent_paths, receipts = {}, []
    command_starts, calls, root_texts, business_calls = {}, [], [], {}
    observability_gaps = []
    previous_seq = -1
    for event in events:
        seq = event.get("runtime_seq")
        if not isinstance(seq, int) or seq <= previous_seq \
                or not _same_generation(event.get("runtime_generation"), generation):
            return verdict("INVALID_EVIDENCE", "event_order_or_generation_invalid")
        previous_seq = seq
        message = event.get("message", {})
        method, params = message.get("method"), message.get("params", {})
        thread, item = params.get("threadId"), params.get("item", {})
        if item.get("type") == "subAgentActivity":
            # The child_thread_id -> child_agent_path association from the
            # same run's subAgentActivity items (item/started and
            # item/completed both carry it). agentPath is an association key
            # only and never creates formal ownership.
            child_thread, agent_path = item.get("agentThreadId"), item.get("agentPath")
            if isinstance(child_thread, str) and isinstance(agent_path, str):
                known = agent_paths.setdefault(child_thread, [])
                if agent_path not in known:
                    known.append(agent_path)
        if method == "rawResponseItem/completed" and item.get("type") == "message":
            text = base.message_text(item)
            if thread in children and item.get("role") == "assistant":
                results.setdefault(thread, []).append(text)
            elif thread == root and item.get("role") == "assistant":
                root_texts.append(text)
        if method == "rawResponseItem/completed" and item.get("type") == "agent_message" \
                and thread == root and item.get("recipient") == "/root" \
                and params.get("turnId") == raw.get("turn_id"):
            # The only root result-consumption surface: a current-turn
            # root-thread agent_message receipt. The official V2 wait item's
            # pairing fields are always empty and its message is only wait
            # status text, so collabAgentToolCall wait items are never parsed
            # as consumption evidence; each receipt body must still parse as
            # the frozen FINAL_ANSWER shape before it counts.
            receipts.append({"seq": seq, "author": item.get("author"),
                             "text": _receipt_body(item)})
        if thread in children | {root} and item.get("type") == "commandExecution":
            item_id = (thread, item.get("id"))
            if method == "item/started":
                command_starts[item_id] = (seq, params.get("turnId"), item.get("command", ""))
            elif method == "item/completed":
                if item_id not in command_starts:
                    # r24: a completed commandExecution without a started
                    # record is an observability gap, not an early terminal.
                    # The command yields no call and the scan continues, so a
                    # sibling child's proven failure keeps its precedence.
                    observability_gaps.append(("command_start_unobservable", thread, seq))
                    continue
                start_seq, start_turn, start_command = command_starts[item_id]
                call = {"id": item.get("id"), "start": start_seq, "end": seq,
                        "command": item.get("command", ""), "output": item.get("aggregatedOutput", ""),
                        "thread": thread, "generation": generation,
                        "start_turn": start_turn, "end_turn": params.get("turnId"),
                        "start_command": start_command, "exit_code": item.get("exitCode")}
                calls.append(call)
                if thread in children:
                    business_calls.setdefault(thread, []).append(call)
    failures, invalids, blockers = [], [], []
    # Inspect attributable positive command facts before missing child
    # observations can terminate the run. Do not call the whole orchestration
    # oracle here: absence of partition/rebuild/receipt events cannot prove
    # a product failure while those observation surfaces are incomplete.
    for call in calls:
        try:
            parsed = command_action(call.get("command", ""), manifest)
        except (ValueError, TypeError):
            continue
        if not parsed:
            continue
        reason = parsed.get("problem")
        if parsed["action"] == "stage5-list-inputs" \
                and "--emit-choices-scope" in parsed.get("flags", {}):
            reason = "discovery_emits_choices_scope"
        elif parsed["action"] == "stage5-partition-choices" and call["thread"] != root:
            reason = "partition_executed_by_owner"
        if reason:
            # Root commands must belong to the current root turn. A formally
            # owned child has its own turn: the current-generation event pair
            # must agree on that child's nonempty turn, not the root's turn.
            # Only formal children or the root enter this calls collection.
            turn = raw.get("turn_id") if call["thread"] == root else call["start_turn"]
            if not isinstance(turn, str) or not turn \
                    or call["start_turn"] != turn or call["end_turn"] != turn \
                    or not isinstance(call["id"], str) or not call["id"]:
                return verdict("INVALID_EVIDENCE", "command_turn_association_invalid")
            failures.append(verdict("FAIL_PRODUCT", reason))
    if failures:
        return failures[0]
    independent_problem = _independent_root_return_failure(calls, manifest, root, raw.get("turn_id"))
    if independent_problem:
        return independent_problem
    if final_problem:
        return final_problem
    if not children:
        return verdict("BLOCKED_OBSERVABILITY", "formal_delegation_unobservable")
    if len(children) != 2:
        return verdict("FAIL_PRODUCT", "wrong_owner_count", formal_children=sorted(children))
    assigned, outcomes, consume_points = {}, {}, {}
    partition, partition_problem = _actual_root_partition(calls, manifest, root)
    if partition_problem:
        _classify(partition_problem, failures, invalids, blockers)
    for child in sorted(children):
        stage5_calls = [call for call in business_calls.get(child, [])
                        if is_owner_business_surface(call.get("command", ""))]
        rows, problem = consumed_business_objects(stage5_calls, manifest)
        if not problem:
            pack, problem = owner_payload(rows, manifest,
                                          partition["owners"] if partition else None)
        if not problem and any(row["start"] < partition["call"]["end"] for row in rows):
            problem = verdict("FAIL_PRODUCT", "owner_business_precedes_partition")
        if problem:
            _classify(problem, failures, invalids, blockers)
            continue
        if pack in assigned:
            failures.append(verdict("FAIL_PRODUCT", "duplicate_owner_pack"))
            continue
        assigned[pack] = child
        owner = next(owner for owner in manifest["owners"] if owner["email_pack"] == pack)
        outcome, problem = base.owner_outcome(results.get(child, []), owner)
        if problem:
            _classify(problem, failures, invalids, blockers)
            continue
        # The child_thread_id -> agent_path mapping must be unique before any
        # receipt can be attributed: with no agent path the child can never be
        # bound to a receipt author, and with more than one distinct agentPath
        # the formal child to author association is ambiguous, so the evidence
        # itself is damaged no matter how correct one surviving path's own
        # receipt looks. Only a unique mapping may bind receipts to that one
        # agent path author.
        paths = agent_paths.get(child, [])
        if len(paths) != 1:
            if not paths:
                blockers.append(verdict("BLOCKED_OBSERVABILITY",
                                        "root_result_consumption_unobservable",
                                        detail="missing_agent_path_mapping"))
            else:
                invalids.append(verdict("INVALID_EVIDENCE",
                                        "child_agent_path_mapping_ambiguous",
                                        detail=list(paths)))
            continue
        matched, malformed = [], []
        for receipt in receipts:
            if receipt["author"] != paths[0]:
                continue
            receipt_own, missing_fields = receipt_payload_outcomes(receipt, owner["professor_dir"])
            if missing_fields:
                # A receipt naming this owner whose Payload top level lacks
                # status/reason_code is malformed evidence, never a changed
                # payload: it counts as no legal receipt.
                malformed.append(missing_fields)
                continue
            if receipt_own:
                matched.append((receipt["seq"], receipt_own))
        if not matched:
            if malformed:
                blockers.append(verdict("BLOCKED_OBSERVABILITY",
                                        "root_result_receipt_malformed",
                                        detail=sorted({field for fields in malformed
                                                       for field in fields})))
            else:
                blockers.append(verdict("BLOCKED_OBSERVABILITY",
                                        "root_result_consumption_unobservable"))
            continue
        observed = []
        for _, receipt_own in matched:
            for candidate in receipt_own:
                if candidate not in observed:
                    observed.append(candidate)
        if len(observed) != 1:
            invalids.append(verdict("INVALID_EVIDENCE", "root_result_receipt_ambiguous",
                                    observed_outcomes=observed))
            continue
        if observed[0] != outcome:
            failures.append(verdict("FAIL_PRODUCT", "root_receipt_payload_changed",
                                    observed_result=observed[0], expected_result=outcome))
            continue
        consume_points[child] = min(seq for seq, _ in matched)
        outcomes[pack] = outcome
    if failures and not invalids and not blockers and all(
            problem.get("reason_code") == "owner_verification_boundary_bypassed"
            for problem in failures):
        role_problem = _early_final_result_role_ambiguity(
            calls, root, root_texts, manifest, outcomes)
        if role_problem:
            return role_problem
    for bucket in (failures, invalids, blockers):
        if bucket:
            return bucket[0]
    if raw.get("termination_reason") != "completed":
        return verdict("BLOCKED_DEPENDENCY", "root_turn_not_completed")
    result = runtime_checks(calls, manifest, list(consume_points.values()), root_texts, root=root,
                            outcomes=outcomes,
                            owner_threads={child: pack for pack, child in assigned.items()})
    result["identity_diagnostics"] = adapter.get("dispatch", {}).get("agent_identity", {})
    # Unified terminal precedence: a proven FAIL/INVALID keeps its precedence
    # over collected observability gaps, which affect only otherwise-clean runs.
    if result.get("verdict") in ("FAIL_PRODUCT", "INVALID_EVIDENCE"):
        return result
    if observability_gaps:
        return verdict("BLOCKED_OBSERVABILITY", "command_start_unobservable",
                       detail=[list(gap) for gap in observability_gaps])
    return result


def _judge_with_final_source(judge, final_text, *args):
    """Run the frozen r19 orchestration oracle with one machine-selected root text."""
    original = runtime_checks

    def pinned(calls, manifest, consumption_points, _root_texts, **kwargs):
        return original(calls, manifest, consumption_points, [final_text], **kwargs)

    globals()["runtime_checks"] = pinned
    try:
        return judge(*args)
    finally:
        globals()["runtime_checks"] = original


def _verify_codex_business(response, adapter, manifest):
    # A dependency rejection can precede any service events. Missing event
    # generations at that boundary do not damage a stream that never existed.
    if adapter.get("fixture_status") in ("INVALID_EVIDENCE", "HARNESS_ERROR", "HARNESS_CONTAMINATION"):
        return _verify_codex_events(response, adapter, manifest)
    if adapter.get("fixture_status") == "BLOCKED_DEPENDENCY":
        raw = response.get("output") if isinstance(response, dict) else None
        events = raw.get("app_server_events") if isinstance(raw, dict) else None
        if events is not None and not isinstance(events, list):
            return verdict("INVALID_EVIDENCE", "root_raw_events_malformed")
        if events:
            generation, previous_seq = raw.get("runtime_generation"), -1
            for event in events:
                seq = event.get("runtime_seq") if isinstance(event, dict) else None
                if not isinstance(seq, int) or seq <= previous_seq \
                        or not _same_generation(event.get("runtime_generation"), generation):
                    return verdict("INVALID_EVIDENCE", "event_order_or_generation_invalid")
                previous_seq = seq
        return _verify_codex_events(response, adapter, manifest)
    if isinstance(response, dict) and isinstance(response.get("output"), dict) \
            and not _valid_generation(response["output"].get("runtime_generation")):
        return verdict("INVALID_EVIDENCE", "event_order_or_generation_invalid")
    final_text, problem = codex_final_result_source(response)
    if problem:
        if problem.get("verdict") != "BLOCKED_OBSERVABILITY" \
                and problem.get("reason_code") != "root_final_message_ambiguous":
            return problem
        # Missing or duplicate final messages do not invalidate independent
        # command facts. The event scan still validates generation, order and
        # command attribution before collecting positive failures, then returns
        # this source problem before any final-result or absence checks.
        return _verify_codex_events(response, adapter, manifest, final_problem=problem)
    return _judge_with_final_source(_verify_codex_events, final_text, response, adapter, manifest)


def verify_codex(response, adapter, manifest):
    result = _verify_codex_business(response, adapter, manifest)
    if result.get("verdict") == "FAIL_PRODUCT":
        return result
    evidence = manifest.get("lifecycle_evidence")
    if evidence is None:
        if result.get("verdict") == "PASS":
            return verdict("BLOCKED_OBSERVABILITY", "request_lifecycle_evidence_missing")
        return result
    import issue68_lifecycle as lifecycle
    import sys
    proof = lifecycle.verify_bound_lifecycle(evidence, manifest, response, adapter, sys.modules[__name__])
    if proof.get("verdict") == "FAIL_PRODUCT":
        return proof
    if result.get("verdict") in ("INVALID_EVIDENCE", "BLOCKED_DEPENDENCY"):
        return result
    if proof.get("verdict") != "PASS":
        return proof
    result["request_lifecycle"] = proof
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--shared-verdict", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.host != "codex":
        parser.error("r19 verifies the codex host only")
    try:
        manifest = json.loads(args.manifest.read_text())
        shared = json.loads(args.shared_verdict.read_text())
        result = verify_codex(json.loads(args.events.read_text()), shared, manifest)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = verdict("INVALID_EVIDENCE", "unreadable_or_malformed_evidence", detail=str(exc))
    result["formal_terminal"] = formal_terminal(result.get("verdict"))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
