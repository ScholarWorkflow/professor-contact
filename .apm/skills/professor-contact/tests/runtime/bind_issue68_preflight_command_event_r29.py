#!/usr/bin/env python3
"""Bind a saved r25 synthetic capture to its actual Codex command event."""
import argparse
import copy
import hashlib
import json
import shlex
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[5]
PREFLIGHT_NAME = "preflight_issue68_owner_input_observation_r29.py"
EVENT_SCHEMA = "issue68-r29-codex-command-event-v1"


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _command_tokens(command):
    tokens = shlex.split(command)
    if len(tokens) == 3 and Path(tokens[0]).name in ("sh", "bash", "zsh") \
            and tokens[1] in ("-c", "-lc"):
        tokens = shlex.split(tokens[2])
    return tokens


def _preflight_command_matches(command, artifact_path, stdout_path):
    if not isinstance(command, str):
        return False
    try:
        tokens = _command_tokens(command)
    except ValueError:
        return False
    if any(token in (";", "&&", "||", "|") for token in tokens):
        return False
    script_positions = [index for index, token in enumerate(tokens)
                        if Path(token).name == PREFLIGHT_NAME]
    if len(script_positions) != 1:
        return False
    position = script_positions[0]
    if position == 0 or Path(tokens[position - 1]).name not in ("python", "python3"):
        return False
    if not any(tokens[index:index + 2] == ["uv", "run"]
               for index in range(max(0, position - 7), position - 1)):
        return False
    script_path = Path(tokens[position])
    expected_script = REPO_ROOT / ".apm/skills/professor-contact/tests/runtime" / PREFLIGHT_NAME
    resolved_script = script_path.resolve() if script_path.is_absolute() else (REPO_ROOT / script_path).resolve()
    if resolved_script != expected_script.resolve():
        return False
    args = tokens[position + 1:]
    if len(args) != 4 or args[0] != "--artifact" or args[2] != "--stdout-capture":
        return False
    paths = []
    for value in (args[1], args[3]):
        path = Path(value)
        paths.append(path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve())
    return paths == [artifact_path.resolve(), stdout_path.resolve()]


def validate_bound_event(artifact, stdout, artifact_path, stdout_path):
    """Check an actual commandExecution item copied from read_thread output."""
    bound = artifact.get("ordinary_command_event")
    if not isinstance(bound, dict) or bound.get("status") != "VERIFIED":
        return "ordinary_command_event_missing"
    event = bound.get("raw_event")
    if not isinstance(event, dict) or bound.get("source") != "mcp__codex_app__read_thread":
        return "ordinary_command_event_source_invalid"
    if bound.get("schema") != EVENT_SCHEMA or event.get("type") != "commandExecution" \
            or not isinstance(event.get("id"), str) or not event.get("id") \
            or event["id"].lower().startswith("synthetic") \
            or bound.get("commandExecution_id") != event.get("id"):
        return "ordinary_command_event_id_invalid"
    if event.get("status") != "completed" or event.get("exitCode") != 0 \
            or event.get("cwd") != "/__pc68_repo__":
        return "ordinary_command_event_state_invalid"
    if bound.get("command") != event.get("command") \
            or bound.get("exit_code") != event.get("exitCode"):
        return "ordinary_command_event_metadata_mismatch"
    if not _preflight_command_matches(event.get("command"), artifact_path, stdout_path):
        return "ordinary_command_event_command_mismatch"
    output = event.get("output", {})
    if output.get("truncated") is not False or output.get("text") != stdout \
            or bound.get("output_matches_saved_capture") is not True:
        return "ordinary_command_event_output_mismatch"
    digest = sha256(stdout.encode("utf-8"))
    if bound.get("output_sha256") != digest \
            or artifact.get("ordinary_command_output_sha256") != digest \
            or len(bound.get("raw_event_sha256_before_path_normalization", "")) != 64:
        return "ordinary_command_event_hash_invalid"
    if bound.get("path_normalization") != {
            "field": "cwd", "from": "repository absolute path",
            "to": "/__pc68_repo__", "output_text_unchanged": True}:
        return "ordinary_command_event_path_normalization_invalid"
    for field in ("thread_id", "turn_id"):
        if not isinstance(bound.get(field), str) or not bound[field]:
            return "ordinary_command_event_thread_binding_missing"
    for field in ("turn_index", "item_index"):
        if not isinstance(bound.get(field), int):
            return "ordinary_command_event_order_missing"
    try:
        emitted = json.loads(stdout)
    except (TypeError, ValueError):
        return "ordinary_command_event_output_not_json"
    if emitted.get("pc68_actual_input_observation", {}).get("object") != artifact.get("parsed_object") \
            or emitted.get("stage5_invocation", {}).get("argv") != artifact.get("producer_argv") \
            or emitted.get("stage5_plan") != artifact.get("producer_structured_output") \
            or emitted.get("return_code") != artifact.get("producer_return_code"):
        return "ordinary_command_event_output_content_mismatch"
    return None


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def bind(raw_event_path, artifact_path, stdout_path):
    raw_event_path = Path(raw_event_path).resolve()
    artifact_path = Path(artifact_path).resolve()
    stdout_path = Path(stdout_path).resolve()
    bundle = _read_json(raw_event_path)
    artifact = _read_json(artifact_path)
    stdout = stdout_path.read_text(encoding="utf-8")

    if artifact.get("schema") != "issue-68-r29-fixed-capture-preflight-v2" \
            or artifact.get("result") != "CAPTURED_SYNTHETIC_PENDING_COMMAND_EVENT":
        raise ValueError("synthetic_capture_artifact_not_pending_event_binding")
    if bundle.get("source") != "mcp__codex_app__read_thread" \
            or bundle.get("schema") != "issue68-r29-command-event-source-v1":
        raise ValueError("command_event_source_unrecognized")
    context = bundle.get("context", {})
    event = bundle.get("event", {})
    thread_id = context.get("thread_id")
    turn_id = context.get("turn_id")
    turn_index = context.get("turn_index")
    item_index = context.get("item_index")
    if not isinstance(thread_id, str) or not thread_id \
            or not isinstance(turn_id, str) or not turn_id \
            or not isinstance(turn_index, int) or not isinstance(item_index, int):
        raise ValueError("command_event_thread_or_order_missing")
    if event.get("type") != "commandExecution" \
            or not isinstance(event.get("id"), str) or not event.get("id") \
            or event.get("status") != "completed" or event.get("exitCode") != 0:
        raise ValueError("ordinary_command_event_invalid")
    if event["id"].lower().startswith("synthetic"):
        raise ValueError("synthetic_command_execution_id_rejected")
    if not isinstance(event.get("cwd"), str) or Path(event["cwd"]).resolve() != REPO_ROOT.resolve():
        raise ValueError("ordinary_command_event_working_directory_mismatch")
    if not _preflight_command_matches(event.get("command"), artifact_path, stdout_path):
        raise ValueError("ordinary_command_event_command_mismatch")
    output = event.get("output", {})
    if output.get("truncated") is not False or output.get("text") != stdout:
        raise ValueError("ordinary_command_event_output_mismatch")

    try:
        emitted = json.loads(output["text"])
    except (TypeError, ValueError):
        raise ValueError("ordinary_command_event_output_not_json")
    capture = emitted.get("pc68_fixed_capture", {})
    observation = emitted.get("pc68_actual_input_observation", {})
    invocation = emitted.get("stage5_invocation", {})
    process = emitted.get("stage5_process", {})
    if capture.get("owner_input_read_count") != 1 \
            or capture.get("capture_id") != invocation.get("capture_id") \
            or capture.get("capture_id") != process.get("capture_id") \
            or observation.get("object") is None \
            or emitted.get("stage5_plan") is None:
        raise ValueError("ordinary_command_event_same_object_linkage_missing")

    raw_event_sha256 = sha256(canonical_json(event).encode("utf-8"))
    portable_event = copy.deepcopy(event)
    portable_event["cwd"] = "/__pc68_repo__"
    artifact["result"] = "CAPTURED_SYNTHETIC_WITH_ACTUAL_COMMAND_EVENT"
    artifact["ordinary_command_event"] = {
        "schema": EVENT_SCHEMA,
        "source": bundle["source"],
        "status": "VERIFIED",
        "thread_id": thread_id,
        "turn_id": turn_id,
        "turn_index": turn_index,
        "item_index": item_index,
        "commandExecution_id": event["id"],
        "command": event["command"],
        "exit_code": event["exitCode"],
        "output_sha256": sha256(stdout.encode("utf-8")),
        "output_matches_saved_capture": True,
        "raw_event_sha256_before_path_normalization": raw_event_sha256,
        "raw_event": portable_event,
        "path_normalization": {
            "field": "cwd",
            "from": "repository absolute path",
            "to": "/__pc68_repo__",
            "output_text_unchanged": True,
        },
    }
    artifact["fixed_capture_verification"]["ordinary_command_event"] = "PASS"
    artifact["fixed_capture_verification"]["ordinary_commandExecution_output_proven"] = True
    artifact["ordinary_command_output_sha256"] = sha256(stdout.encode("utf-8"))
    artifact["limitations"] = [
        "The input business fixture is synthetic; this preflight does not execute PC68-R1.",
        "The actual ordinary command event proves capture output and same-object invocation linkage only.",
    ]
    problem = validate_bound_event(artifact, stdout, artifact_path, stdout_path)
    if problem:
        raise ValueError(problem)
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                             encoding="utf-8")
    return artifact


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-command-event", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--stdout-capture", type=Path, required=True)
    args = parser.parse_args(argv)
    bind(args.raw_command_event, args.artifact, args.stdout_capture)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
