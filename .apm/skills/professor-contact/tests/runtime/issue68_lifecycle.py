"""Read-only filesystem evidence for r25 R1-7.

Snapshots prove preserved bytes and final absence, not a write/delete history.
Completed bounded root file operations and the installed partition command
can prove mutations. Unsupported or ambiguous root programs leave a gap.
"""
import hashlib
import json
import shlex
import time
import uuid
from pathlib import Path

SCHEMA = "issue68-r30-lifecycle-v1"


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
        return {"root": str(root), "present": False, "entries": entries}
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
    return {"root": str(root), "present": True, "entries": entries}


def collect_before(manifest, consumer):
    return {"schema": SCHEMA, "phase": "before_request",
            "program": snapshot_tree(manifest["program_root"]),
            "consumer": snapshot_tree(consumer)}


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
    reads, partitions, problems, operations = [], [], [], []
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
        if action.get("owner_capture"):
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
            try:
                returned = json.loads(call.get("output") or "")
            except (TypeError, ValueError):
                returned = None
            partitions.append({"command_id": call["id"], "thread": call["thread"],
                               "generation": call["generation"],
                               "start": call["start"], "end": call["end"],
                               "actual_return": returned,
                               "choices_path": action.get("flags", {}).get("--choices"),
                               "out_path": action.get("flags", {}).get("--out"),
                               "exit_code": call.get("exit_code")})
            if returned and returned.get("status") == "ok" and type(call.get("exit_code")) is int and call["exit_code"] == 0:
                # Fixed product cmd_stage5_partition_choices reads choices
                # before emitting this object and writes --out before emit.
                flags = action.get("flags", {})
                for op, key in (("read", "--choices"), ("write", "--out")):
                    if flags.get(key):
                        operations.append({"operation": op, "paths": [flags[key]],
                            **{k: call[k] for k in ("id", "thread", "generation", "start", "end")},
                            "source": "installed_partition_read_write_before_emit"})
    after = after if after is not None else {"phase": "after_request", "program": snapshot_tree(manifest["program_root"]),
             "consumer": snapshot_tree(consumer)}
    if "request_boundary" in before and "request_boundary" not in after:
        after["request_boundary"] = {**before["request_boundary"], "sequence": 2,
            "response_sha256": _response_digest(response), "monotonic_ns": time.monotonic_ns()}
    evidence = {"schema": SCHEMA, "before": before, "after": after,
            "response_sha256": _response_digest(response),
            "root_turn": response.get("output", {}).get("turn_id"),
            "root_thread": root,
            "runtime_generation": response.get("output", {}).get("runtime_generation"),
            "reads": reads, "partition_returns": partitions,
            "input_problems": problems, "file_operations": operations,
            "lifecycle_capability": {"state": "INCOMPLETE",
                "missing_facts": ["root_transfer_file_creation_observation",
                                  "root_original_choices_file_read_observation",
                                  "root_complete_partition_transfer_read_observation",
                                  "request_owned_cleanup_operation_observation"],
                "reason": "bounded_successful_root_file_operations_are_required"}}
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
        for key in ("reads", "partition_returns", "input_problems", "file_operations"):
            if evidence.get(key) != rebuilt[key]:
                return invalid("lifecycle_raw_fact_mismatch")
        children = {child for edge in adapter.get("dispatch", {}).get("thread_relations", [])
                    if edge.get("tool") == "spawnAgent" and edge.get("sender_thread_id") == raw["thread_id"]
                    for child in edge.get("receiver_thread_ids", [])}
        if any(read["thread"] not in children for read in rebuilt["reads"]):
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
    """Validate snapshots and directly attributable mutation/read chains."""
    def result(kind, reason, **extra):
        return {"verdict": kind, "reason_code": reason, **extra}
    try:
        if evidence.get("schema") != SCHEMA or evidence["before"].get("schema") != SCHEMA:
            raise ValueError("schema")
        before, after = evidence["before"], evidence["after"]
        if before.get("phase") != "before_request" or after.get("phase") != "after_request":
            raise ValueError("phase")
        for scope in ("program", "consumer"):
            if before[scope]["root"] != after[scope]["root"] or before[scope]["present"] is not True \
                    or type(after[scope]["present"]) is not bool or not Path(before[scope]["root"]).is_absolute():
                raise ValueError("roots")
            if not after[scope]["present"]:
                return result("FAIL_PRODUCT", "protected_request_tree_deleted", scope=scope)
            for snapshot in (before[scope], after[scope]):
                if not isinstance(snapshot["entries"], dict):
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
            relative = str(Path(path).relative_to(Path(before["program"]["root"])))
            original = before["program"]["entries"].get(relative)
            if original is None:
                raise ValueError("other_request_fixture_missing")
            if after["program"]["entries"].get(relative) != original:
                return result("FAIL_PRODUCT", "other_request_file_changed_or_deleted", path=path)
        for read in evidence["reads"]:
            if read.get("professor_dir") not in {o["professor_dir"] for o in manifest["owners"]}:
                return result("INVALID_EVIDENCE", "transfer_owner_association_invalid")
            if not isinstance(read.get("command_id"), str) or not read["command_id"] \
                    or not isinstance(read.get("thread"), str) or not read["thread"] \
                    or not isinstance(read.get("start"), int) or not isinstance(read.get("end"), int) \
                    or read["start"] >= read["end"]:
                raise ValueError("read_association")
            path = Path(read["path"])
            scope = "program" if path.is_relative_to(Path(after["program"]["root"])) else "consumer"
            relative = str(path.relative_to(Path(after[scope]["root"])))
            if relative in before[scope]["entries"]:
                return result("FAIL_PRODUCT", "handoff_reused_preexisting_file", path=str(path))
            if relative in after[scope]["entries"]:
                return result("FAIL_PRODUCT", "request_transfer_file_remains", path=str(path))
    except (KeyError, TypeError, ValueError, AttributeError):
        return result("INVALID_EVIDENCE", "lifecycle_snapshot_or_association_invalid")
    try:
        partitions = evidence.get("partition_returns", [])
        if len(partitions) != 1 or len(evidence["reads"]) != len(manifest["owners"]):
            return result("BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable")
        partition = partitions[0]
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
        refs = [(read["path"], read["start"], read["end"], False) for read in evidence["reads"]]
        if partition.get("choices_path"):
            refs.append((partition["choices_path"], partition["start"], partition["end"], False))
        if partition.get("out_path"):
            # The command writes --out before emitting its actual return.
            # Consuming that return does not require a second cat operation.
            refs.append((partition["out_path"], partition["start"], partition["end"], True))
        for path_string, read_start, read_end, same_partition_write in refs:
            path = Path(path_string)
            scope = "program" if path.is_relative_to(Path(after["program"]["root"])) else "consumer"
            relative = str(path.relative_to(Path(after[scope]["root"])))
            if relative in before[scope]["entries"]:
                return result("FAIL_PRODUCT", "transfer_overwrites_preexisting_request_data", path=path_string)
            if relative in after[scope]["entries"]:
                return result("FAIL_PRODUCT", "request_transfer_file_remains", path=path_string)
            writes = [op for op in operations if op["operation"] == "write" and path_string in op["paths"]
                      and (op["end"] < read_start or (same_partition_write and
                           op["source"] == "installed_partition_read_write_before_emit" and
                           op["start"] == read_start and op["end"] == read_end))]
            removes = [op for op in operations if op["operation"] == "remove" and path_string in op["paths"]
                       and op["start"] > read_end]
            if not writes or not removes:
                return result("BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable",
                              path=path_string)
        return result("PASS", "request_lifecycle_and_state_preservation_proven")
    except (KeyError, TypeError, ValueError, AttributeError):
        return result("INVALID_EVIDENCE", "lifecycle_operation_association_invalid")
