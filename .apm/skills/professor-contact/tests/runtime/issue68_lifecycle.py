"""Same-request snapshots and actual use prove r26 R1-7 lifecycle.

Bounded command operations remain diagnostics, not mandatory mutation evidence.
"""
import hashlib
import json
import shlex
import time
import uuid
from pathlib import Path

SCHEMA = "issue68-r31-lifecycle-v1"
DIRENV_UNLOADING_PREFIX = "\x1b[0mdirenv: unloading\n"


def _strict_json_command_output(text):
    """Parse one command JSON value, allowing only the observed direnv prefix."""
    if not isinstance(text, str):
        raise TypeError("command_output_not_text")
    if text.startswith(DIRENV_UNLOADING_PREFIX):
        text = text[len(DIRENV_UNLOADING_PREFIX):]

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=unique_pairs)


class MissingEventObservation(ValueError):
    """The original stream cannot establish this root request boundary."""


def _single_shell_word(token):
    words = shlex.split(token)
    return words[0] if len(words) == 1 and words[0] else None


def file_operation(command):
    """A bounded shell operation parser, never an input-content parser.

    Accept only direct absolute-path operations whose completed exit status
    establishes the operation. Arbitrary Python, pipelines, expansions and
    compound shell programs remain unobserved.
    """
    try:
        wrapper = shlex.split(command)
        if len(wrapper) == 3 and wrapper[0] in ("sh", "bash", "zsh", "/bin/sh", "/bin/bash", "/bin/zsh") and wrapper[1] in ("-c", "-lc"):
            command = wrapper[2]
        lexer = shlex.shlex(command, posix=False, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except (ValueError, TypeError):
        return None
    if not tokens or any(t and all(c in ";&|<>" for c in t) and t != ">" for t in tokens):
        return None
    if tokens[0] not in ("rm", "unlink", "printf", "cat", "/bin/rm", "/bin/cat",
                          "/usr/bin/unlink", "/usr/bin/printf"):
        return None
    if any(any(c in token for c in ("$", "`", "\\", "\n", "\r", "(", ")")) for token in tokens):
        return None
    head = Path(tokens[0]).name
    if head in ("rm", "unlink"):
        paths = [_single_shell_word(t) for t in tokens[1:] if t not in ("--", "-f")]
        if paths and all(paths) and (head != "unlink" or len(paths) == 1) and all(Path(p).is_absolute() and
                not any(char in p for char in ("*", "?", "$", "`")) for p in paths):
            return {"operation": "remove", "paths": paths}
    target = _single_shell_word(tokens[-1])
    if target is None:
        return None
    if head in ("printf", "cat") and len(tokens) >= 4 and tokens[-2] == ">" \
            and tokens.count(">") == 1 and Path(target).is_absolute():
        # Do not decode printf arguments or heredoc contents as business input.
        if not any(char in target for char in ("*", "?", "$", "`")):
            return {"operation": "write", "paths": [target]}
    if head == "cat" and len(tokens) == 2 and Path(target).is_absolute():
        return {"operation": "read", "paths": [target]}
    return None


def snapshot_tree(root):
    """Record every entry, including empty directories, without following links."""
    root = Path(root).absolute()
    entries = {}
    if not root.exists():
        return {"root": str(root), "present": False, "complete": True, "entries": entries}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            entries[relative] = {"kind": "symlink", "target": str(path.readlink())}
        elif path.is_file():
            raw = path.read_bytes()
            entries[relative] = {"kind": "file", "sha256": hashlib.sha256(raw).hexdigest(),
                                 "size": len(raw)}
        elif path.is_dir():
            entries[relative] = {"kind": "directory"}
        else:
            entries[relative] = {"kind": "other"}
    return {"root": str(root), "present": True, "complete": True, "entries": entries}


def collect_before(manifest, consumer):
    record = {"schema": SCHEMA, "phase": "before_request",
            "program": snapshot_tree(manifest["program_root"]),
            "consumer": snapshot_tree(consumer)}
    for index, root in enumerate(manifest.get("lifecycle_extra_observation_roots", [])):
        record["extra_" + str(index)] = snapshot_tree(root)
    return record


def bind_before(before, request):
    before["request_boundary"] = {"run_id": str(uuid.uuid4()), "sequence": 1,
        "request_sha256": _response_digest(request), "monotonic_ns": time.monotonic_ns()}
    return before


def _commands(response):
    raw = response.get("output", {})
    starts, commands = {}, []
    events = raw.get("app_server_events")
    generation, root_turn, root_thread = raw.get("runtime_generation"), raw.get("turn_id"), raw.get("thread_id")
    if type(generation) not in (int, str) or generation == "" or \
            not all(isinstance(value, str) and value for value in (root_turn, root_thread)):
        raise ValueError("runtime_identity")
    if events is None and "app_server_events" not in raw:
        raise MissingEventObservation("missing_original_event_stream")
    if not isinstance(events, list):
        raise ValueError("event_stream_type")
    if not events:
        raise MissingEventObservation("empty_original_event_stream")
    previous = -1
    root_observed = False
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("event_type")
        seq = event.get("runtime_seq")
        if type(seq) is not int or seq <= previous or not _same_generation(event.get("runtime_generation"), generation):
            raise ValueError("event_identity")
        previous = seq
        message = event.get("message", {})
        if not isinstance(message, dict):
            raise ValueError("event_message")
        params = message.get("params", {})
        if not isinstance(params, dict):
            raise ValueError("event_params")
        if params.get("threadId") == root_thread and params.get("turnId") is not None:
            if params["turnId"] != root_turn:
                raise ValueError("root_turn")
            root_observed = True
        item = params.get("item", {})
        if not isinstance(item, dict):
            raise ValueError("event_item")
        if item.get("type") != "commandExecution":
            continue
        key = (params.get("threadId"), item.get("id"))
        turn = params.get("turnId")
        if not all(isinstance(v, str) and v for v in (*key, turn)):
            raise ValueError("command_identity")
        if key[0] == raw.get("thread_id") and turn != root_turn:
            raise ValueError("root_turn")
        if message.get("method") == "item/started":
            if key in starts:
                raise ValueError("duplicate_start")
            starts[key] = (seq, turn)
        elif message.get("method") == "item/completed":
            if key not in starts or starts[key][1] != turn:
                raise ValueError("command_pair")
            commands.append({"id": item.get("id"), "thread": params.get("threadId"),
                             "generation": event.get("runtime_generation"),
                             "start": starts.pop(key)[0], "end": seq,
                             "command": item.get("command"),
                             "output": item.get("aggregatedOutput"),
                             "exit_code": item.get("exitCode")})
    if not root_observed:
        raise MissingEventObservation("root_current_turn_unobserved")
    return commands


def _same_generation(left, right):
    return type(left) in (int, str) and type(left) is type(right) and left == right and left != ""


def _response_digest(response):
    return hashlib.sha256(json.dumps(response, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def collect_lifecycle(before, manifest, consumer, response, input_verifier, after=None):
    """Bind only validated same-call reads; never infer writes from shell text."""
    reads, partitions, problems, operations, business_outputs, attempted_handoffs = [], [], [], [], [], []
    root = response.get("output", {}).get("thread_id")
    try:
        commands = _commands(response)
    except MissingEventObservation:
        commands = []
        problems.append({"verdict": "BLOCKED_OBSERVABILITY", "reason_code": "lifecycle_original_root_event_stream_missing"})
    except (KeyError, TypeError, ValueError, AttributeError):
        commands = []
        problems.append({"verdict": "INVALID_EVIDENCE", "reason_code": "lifecycle_raw_command_association_invalid"})
    for call in commands:
        operation = file_operation(call.get("command")) if call["thread"] == root else None
        if operation and type(call.get("exit_code")) is int and call["exit_code"] == 0:
            operations.append({**operation, **{key: call[key] for key in
                ("id", "thread", "generation", "start", "end", "output")},
                "source": "completed_command_with_successful_exit"})
        try:
            action = input_verifier.command_action(call.get("command") or "", manifest)
        except (TypeError, ValueError):
            continue
        if not action:
            continue
        if action.get("action") == "stage5-rebuild-overview" and call["thread"] == root:
            try:
                returned_overview = json.loads(call.get("output") or "")
                if returned_overview.get("overview_md"):
                    business_outputs.append(returned_overview["overview_md"])
            except (TypeError, ValueError, AttributeError):
                pass
        if action.get("owner_capture"):
            if action["owner_capture"].get("owner_input_file"):
                attempted_handoffs.append({"path": action["owner_capture"]["owner_input_file"],
                    **{key: call[key] for key in ("thread", "generation", "start", "end")},
                    "command_id": call["id"]})
            rows, problem = input_verifier.consumed_business_objects([call], manifest)
            if problem:
                problems.append(problem)
            else:
                envelope = json.loads(call["output"])
                capture = envelope["pc68_fixed_capture"]
                reads.append({"path": capture["owner_input_file"],
                              "sha256": capture["owner_input_sha256"],
                              "professor_dir": rows[0]["packet"].get("professor_dir") or
                                  str(Path(rows[0]["packet"]["email_pack"]).parent),
                              "command_id": call["id"], "thread": call["thread"],
                              "generation": call["generation"],
                              "start": call["start"], "end": call["end"],
                              "capture_id": capture["capture_id"],
                              "source": "fixed_owner_parse_output"})
        elif action.get("action") == "stage5-partition-choices" and call["thread"] == root:
            # Keep the actual complete return. Command arguments may identify
            # a source path, but are never used as evidence of its contents.
            raw_return = call.get("output")
            if not isinstance(raw_return, str) or not raw_return.strip():
                returned = None
                return_parse_state = "unobservable"
            else:
                try:
                    returned = _strict_json_command_output(raw_return)
                    return_parse_state = "parsed"
                except (TypeError, ValueError):
                    returned = None
                    return_parse_state = "invalid_json"
            partitions.append({"command_id": call["id"], "thread": call["thread"],
                               "generation": call["generation"],
                               "start": call["start"], "end": call["end"],
                               "actual_return": returned,
                               "actual_return_parse_state": return_parse_state,
                               "choices_path": action.get("flags", {}).get("--choices"),
                               "out_path": action.get("flags", {}).get("--out"),
                               "exit_code": call.get("exit_code")})
            if isinstance(returned, dict) and returned.get("status") == "ok" \
                    and type(call.get("exit_code")) is int and call["exit_code"] == 0:
                # Fixed product cmd_stage5_partition_choices reads choices
                # before emitting this object and writes --out before emit.
                flags = action.get("flags", {})
                for op, key in (("read", "--choices"), ("write", "--out")):
                    if flags.get(key):
                        operations.append({"operation": op, "paths": [flags[key]],
                            **{k: call[k] for k in ("id", "thread", "generation", "start", "end")},
                            "source": "installed_partition_read_write_before_emit"})
    if after is None:
        after = collect_before(manifest, consumer)
        after["phase"] = "after_request"
    if "request_boundary" in before and "request_boundary" not in after:
        after["request_boundary"] = {**before["request_boundary"], "sequence": 2,
            "response_sha256": _response_digest(response), "monotonic_ns": time.monotonic_ns()}
    evidence = {"schema": SCHEMA, "before": before, "after": after,
            "response_sha256": _response_digest(response),
            "root_turn": response.get("output", {}).get("turn_id"),
            "root_thread": root,
            "runtime_generation": response.get("output", {}).get("runtime_generation"),
            "reads": reads, "partition_returns": partitions,
            "business_outputs": business_outputs,
            "attempted_handoffs": attempted_handoffs,
            "input_problems": problems, "file_operations": operations,
            "lifecycle_capability": {"state": "INCOMPLETE",
                "missing_facts": ["same_request_complete_directory_records",
                                  "actual_transfer_formation_or_use",
                                  "final_absence_and_protected_data_preservation"],
                "reason": "same_request_complete_snapshots_and_actual_use_are_required"}}
    # Missing or damaged original events cannot attribute filesystem differences
    # to the root request, even if the recorded snapshots differ.
    boundary_problem = next((problem for problem in problems if problem["reason_code"] in
        ("lifecycle_original_root_event_stream_missing", "lifecycle_raw_command_association_invalid")), None)
    proof = boundary_problem or verify_lifecycle(evidence, manifest)
    evidence["lifecycle_capability"]["state"] = "SUPPORTED_FOR_OBSERVED_CHAIN" if proof["verdict"] == "PASS" else "INCOMPLETE"
    evidence["lifecycle_capability"]["proof"] = proof
    if proof["verdict"] == "PASS":
        evidence["lifecycle_capability"]["missing_facts"] = []
    else:
        evidence["lifecycle_capability"]["missing_facts"] = [proof["reason_code"]]
    return evidence


def verify_bound_lifecycle(evidence, manifest, response, adapter, input_verifier):
    """Rebuild call facts from the original stream; a ledger is not authority."""
    def invalid(reason):
        return {"verdict": "INVALID_EVIDENCE", "reason_code": reason}
    try:
        _commands(response)  # Verify every event identity before any filesystem FAIL.
        raw = response["output"]
        if evidence.get("response_sha256") != _response_digest(response) or \
                evidence.get("root_thread") != raw.get("thread_id") or \
                evidence.get("root_turn") != raw.get("turn_id") or \
                not _same_generation(evidence.get("runtime_generation"), raw.get("runtime_generation")):
            return invalid("lifecycle_response_association_invalid")
        before, after = evidence["before"], evidence["after"]
        first, last = before["request_boundary"], after["request_boundary"]
        bound = manifest["lifecycle_boundary"]
        request = json.loads(Path(bound["request_artifact"]).read_text())
        saved_before = json.loads(Path(bound["before_artifact"]).read_text())
        if saved_before != before or bound["before_sha256"] != _response_digest(before) or \
                bound["after_sha256"] != _response_digest(after) or \
                bound["run_id"] != first["run_id"] or last["run_id"] != first["run_id"] or \
                not first["run_id"] or first["sequence"] != 1 or last["sequence"] != 2 or \
                first["request_sha256"] != _response_digest(request) or \
                last["request_sha256"] != first["request_sha256"] or \
                last["response_sha256"] != _response_digest(response) or \
                type(first["monotonic_ns"]) is not int or type(last["monotonic_ns"]) is not int or \
                first["monotonic_ns"] >= last["monotonic_ns"]:
            return invalid("lifecycle_request_boundary_invalid")
        if before["consumer"]["root"] != manifest["owner_capture"]["consumer_root"]:
            return invalid("lifecycle_consumer_association_invalid")
        rebuilt = collect_lifecycle(before, manifest, before["consumer"]["root"], response,
                                    input_verifier, after=after)
        for key in ("reads", "partition_returns", "input_problems", "file_operations", "business_outputs", "attempted_handoffs"):
            if evidence.get(key) != rebuilt[key]:
                return invalid("lifecycle_raw_fact_mismatch")
        children = {child for edge in adapter.get("dispatch", {}).get("thread_relations", [])
                    if edge.get("tool") == "spawnAgent" and edge.get("sender_thread_id") == raw["thread_id"]
                    for child in edge.get("receiver_thread_ids", [])}
        if any(read["thread"] not in children for read in rebuilt["reads"]):
            return invalid("lifecycle_owner_thread_association_invalid")
        if any(attempt["thread"] not in children for attempt in rebuilt["attempted_handoffs"]):
            return invalid("lifecycle_owner_thread_association_invalid")
        proof = verify_lifecycle(evidence, manifest)
        if proof["verdict"] == "FAIL_PRODUCT":
            return proof
        if rebuilt["input_problems"]:
            return rebuilt["input_problems"][0]
        return proof
    except MissingEventObservation:
        return {"verdict": "BLOCKED_OBSERVABILITY", "reason_code": "lifecycle_original_root_event_stream_missing"}
    except (OSError, KeyError, TypeError, ValueError, AttributeError):
        return invalid("lifecycle_request_boundary_or_raw_association_invalid")


def _subtree(snapshot, directory):
    root = Path(snapshot["root"])
    relative = str(Path(directory).relative_to(root))
    return {name: value for name, value in snapshot["entries"].items()
            if name == relative or name.startswith(relative + "/")}


def verify_lifecycle(evidence, manifest):
    """Validate complete snapshots and directly attributable formation/use."""
    missing_fact = object()
    def result(kind, reason, **extra):
        return {"verdict": kind, "reason_code": reason, **extra}
    try:
        if evidence.get("schema") != SCHEMA or evidence["before"].get("schema") != SCHEMA:
            raise ValueError("schema")
        before, after = evidence["before"], evidence["after"]
        if before.get("phase") != "before_request" or after.get("phase") != "after_request":
            raise ValueError("phase")
        scopes = ["program", "consumer"] + ["extra_" + str(index) for index, _ in
                  enumerate(manifest.get("lifecycle_extra_observation_roots", []))]
        for index, root in enumerate(manifest.get("lifecycle_extra_observation_roots", [])):
            if before["extra_" + str(index)]["root"] != root:
                raise ValueError("extra_root_association")
        # These declarations classify newly created business output only;
        # they never authorize changing a preexisting observed entry.
        allowed_outputs = set(evidence.get("business_outputs", []))
        allowed_outputs.update(owner["result"] for owner in manifest["owners"] if owner.get("result"))
        actual_read_paths = {read["path"] for read in evidence["reads"]}
        successful_transfer_paths = {partition[key]
            for partition in evidence.get("partition_returns", [])
            if isinstance(partition, dict)
            if isinstance(partition.get("actual_return"), dict)
            and partition["actual_return"].get("status") == "ok"
            and type(partition.get("exit_code")) is int and partition["exit_code"] == 0
            for key in ("choices_path", "out_path") if partition.get(key)}
        def location(path_string):
            path = Path(path_string)
            if not path.is_absolute() or ".." in path.parts:
                raise ValueError("relative_transfer")
            for scope in scopes:
                if path.is_relative_to(Path(before[scope]["root"])):
                    relative = path.relative_to(Path(before[scope]["root"]))
                    if any(before[scope]["entries"].get(str(parent), {}).get("kind") == "symlink"
                           for parent in relative.parents if str(parent) != "."):
                        continue
                    return scope, str(relative)
            return None
        for scope in scopes:
            if before[scope]["root"] != after[scope]["root"] or before[scope]["present"] is not True \
                    or type(after[scope]["present"]) is not bool or not Path(before[scope]["root"]).is_absolute():
                raise ValueError("roots")
            if not after[scope]["present"]:
                return result("FAIL_PRODUCT", "protected_request_tree_deleted", scope=scope)
            for snapshot in (before[scope], after[scope]):
                if snapshot.get("complete") is not True or not isinstance(snapshot["entries"], dict):
                    raise ValueError("entries")
                for name, entry in snapshot["entries"].items():
                    if not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts:
                        raise ValueError("entry_path")
                    if entry.get("kind") not in ("file", "directory", "symlink", "other"):
                        raise ValueError("entry_kind")
                    if entry["kind"] == "file":
                        digest = entry.get("sha256")
                        if not isinstance(digest, str) or len(digest) != 64 or int(digest, 16) < 0 \
                                or type(entry.get("size")) is not int or entry["size"] < 0:
                            raise ValueError("file_digest")
        if before["program"]["root"] != manifest["program_root"]:
            raise ValueError("program_root")
        for owner in manifest["owners"]:
            pack_relative = str(Path(owner["email_pack"]).relative_to(Path(before["program"]["root"])))
            if before["program"]["entries"].get(pack_relative, {}).get("kind") != "file":
                raise ValueError("owner_pack_missing_before")
            if _subtree(before["program"], owner["professor_dir"]) != \
                    _subtree(after["program"], owner["professor_dir"]):
                return result("FAIL_PRODUCT", "professor_state_or_output_changed",
                              professor_dir=owner["professor_dir"])
        if not manifest.get("protected_other_request_files"):
            raise ValueError("other_request_fixture_missing")
        for path in manifest["protected_other_request_files"]:
            found = location(path)
            if found is None:
                raise ValueError("protected_location_unobserved")
            scope, relative = found
            original = before[scope]["entries"].get(relative)
            if original is None:
                raise ValueError("other_request_fixture_missing")
            if after[scope]["entries"].get(relative) != original:
                return result("FAIL_PRODUCT", "other_request_file_changed_or_deleted", path=path)
        # Preserve every preexisting observed entry, including empty directories
        # and other-request files not named individually in the sentinel list.
        for scope in scopes:
            for name, original in before[scope]["entries"].items():
                path_string = str(Path(before[scope]["root"]) / name)
                if after[scope]["entries"].get(name) != original:
                    # Runtime output/transfer declarations cannot grant access
                    # to another request's preexisting data. Preserve the prior
                    # failure labels for successfully used transfer paths.
                    if path_string in actual_read_paths:
                        return result("FAIL_PRODUCT", "handoff_reused_preexisting_file", path=path_string)
                    if path_string in successful_transfer_paths:
                        return result("FAIL_PRODUCT", "transfer_overwrites_preexisting_request_data", path=path_string)
                    return result("FAIL_PRODUCT", "other_request_file_changed_or_deleted", path=path_string)
        for read in evidence["reads"]:
            if read.get("professor_dir") not in {o["professor_dir"] for o in manifest["owners"]}:
                return result("INVALID_EVIDENCE", "transfer_owner_association_invalid")
            if not isinstance(read.get("command_id"), str) or not read["command_id"] \
                    or not isinstance(read.get("thread"), str) or not read["thread"] \
                    or not isinstance(read.get("start"), int) or not isinstance(read.get("end"), int) \
                    or read["start"] >= read["end"]:
                raise ValueError("read_association")
            path = Path(read["path"])
            found = location(str(path))
            if found is None:
                return result("BLOCKED_OBSERVABILITY", "transfer_path_outside_observation_scope", path=str(path))
            scope, relative = found
            if relative in before[scope]["entries"]:
                return result("FAIL_PRODUCT", "handoff_reused_preexisting_file", path=str(path))
            if relative in after[scope]["entries"]:
                return result("FAIL_PRODUCT", "request_transfer_file_remains", path=str(path))
    except (KeyError, TypeError, ValueError, AttributeError):
        return result("INVALID_EVIDENCE", "lifecycle_snapshot_or_association_invalid")
    try:
        partitions = evidence.get("partition_returns", [])
        operations = evidence.get("file_operations", [])
        generation = evidence.get("runtime_generation")
        if isinstance(generation, bool) or not isinstance(generation, (str, int)) or str(generation) == "":
            raise ValueError("runtime_generation")
        for operation in operations:
            if operation["thread"] != evidence["root_thread"] or not isinstance(operation["start"], int) \
                    or not isinstance(operation["end"], int) or operation["start"] >= operation["end"] \
                    or isinstance(operation.get("generation"), bool) \
                    or not _same_generation(operation.get("generation"), generation):
                raise ValueError("operation_association")
        if any(not _same_generation(read.get("generation"), generation)
               for read in evidence["reads"]):
            raise ValueError("read_generation")
        refs = [read["path"] for read in evidence["reads"]]
        for attempt in evidence.get("attempted_handoffs", []):
            if not _same_generation(attempt.get("generation"), generation) or \
                    not attempt.get("command_id") or type(attempt.get("start")) is not int or \
                    type(attempt.get("end")) is not int or attempt["start"] >= attempt["end"]:
                raise ValueError("handoff_attempt_association")
            # Only presence after the attributable delivery attempt establishes
            # an undelivered remnant. An absent attempted path proves no use.
            found = location(attempt["path"])
            if found is None:
                return result("BLOCKED_OBSERVABILITY", "transfer_path_outside_observation_scope", path=attempt["path"])
            scope, relative = found
            if relative in after[scope]["entries"]:
                refs.append(attempt["path"])
        successful = []
        for partition in partitions:
            if not isinstance(partition, dict):
                raise ValueError("partition_return_record")
            parse_state = partition.get("actual_return_parse_state")
            actual_return = partition.get("actual_return", missing_fact)
            if parse_state == "invalid_json":
                return result("INVALID_EVIDENCE", "lifecycle_partition_return_unparseable")
            if parse_state == "unobservable":
                return result("BLOCKED_OBSERVABILITY", "lifecycle_partition_return_unobservable")
            if parse_state not in (None, "parsed"):
                raise ValueError("partition_return_parse_state")
            if actual_return is missing_fact:
                raise ValueError("partition_return_missing")
            if actual_return is None and parse_state is None:
                return result("INVALID_EVIDENCE", "lifecycle_partition_return_parse_state_missing")
            if not isinstance(actual_return, dict) or actual_return.get("status") != "ok" or \
                    type(partition.get("exit_code")) is not int or partition["exit_code"] != 0:
                continue
            if partition.get("thread") != evidence["root_thread"] or \
                    not _same_generation(partition.get("generation"), generation) or \
                    type(partition.get("start")) is not int or type(partition.get("end")) is not int or \
                    partition["start"] >= partition["end"] or not partition.get("command_id"):
                raise ValueError("partition_association")
            successful.append(partition)
            refs.extend(partition[key] for key in ("choices_path", "out_path") if partition.get(key))
        for path_string in refs:
            found = location(path_string)
            if found is None:
                return result("BLOCKED_OBSERVABILITY", "transfer_path_outside_observation_scope", path=path_string)
            scope, relative = found
            if relative in before[scope]["entries"]:
                return result("FAIL_PRODUCT", "transfer_overwrites_preexisting_request_data", path=path_string)
            if relative in after[scope]["entries"]:
                return result("FAIL_PRODUCT", "request_transfer_file_remains", path=path_string)
        if len(successful) != 1 or not successful[0].get("choices_path") or \
                {read["professor_dir"] for read in evidence["reads"]} != \
                {owner["professor_dir"] for owner in manifest["owners"]} or \
                len(evidence["reads"]) != len(manifest["owners"]):
            return result("BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable")
        allowed = set(allowed_outputs)
        allowed.update(manifest.get("lifecycle_boundary", {}).get(key) for key in
                       ("request_artifact", "before_artifact"))
        for scope in scopes:
            for name, entry in after[scope]["entries"].items():
                path_string = str(Path(after[scope]["root"]) / name)
                if name not in before[scope]["entries"] and entry["kind"] != "directory" and \
                        path_string not in allowed:
                    return result("BLOCKED_OBSERVABILITY", "new_file_request_ownership_unresolved", path=path_string)
        return result("PASS", "request_lifecycle_and_state_preservation_proven")
    except (KeyError, TypeError, ValueError, AttributeError):
        return result("INVALID_EVIDENCE", "lifecycle_operation_association_invalid")
