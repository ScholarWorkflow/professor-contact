#!/usr/bin/env python3
"""Capture one real owner handoff parse and its original installed CLI call.

This test-only wrapper does not create or edit the handoff, allocate choices,
or alter product decisions. It reads the supplied handoff once, uses that
decoded object to construct the existing initial stage5-plan argv, executes
the installed contact_state.py, and returns one bound JSON envelope.
"""
import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path
import subprocess


SCHEMA = "issue-68-test-plan-r25-owner-input-v2"
CAPTURE_SCHEMA = "issue-68-test-plan-r25-fixed-owner-capture-v1"
CAPTURE_NAME = "capture_issue68_owner_stage5_plan_r1.py"
TARGETS = (".agents", ".codex", ".opencode", ".apm")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _installed_entrypoint(consumer_root):
    found = []
    for target in TARGETS:
        candidate = (consumer_root / target / "skills" / "professor-contact"
                     / "scripts" / "contact_state.py")
        if candidate.is_file():
            if candidate.is_symlink():
                raise ValueError("installed_entrypoint_symlink")
            found.append(candidate.resolve())
    if len(found) != 1:
        raise ValueError("installed_entrypoint_not_unique")
    return found[0]


def _build_argv(packet, entrypoint):
    required = ("program_root", "email_pack", "template", "mode")
    for key in required:
        value = packet.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError("owner_input_missing_string:" + key)
    argv = [
        sys.executable,
        str(entrypoint),
        "stage5-plan",
        "--program-root", packet["program_root"],
        "--email-pack", packet["email_pack"],
    ]
    email_id = packet.get("email_id")
    if email_id is not None:
        if not isinstance(email_id, str) or not email_id:
            raise ValueError("owner_input_invalid_email_id")
        argv.extend(["--email-id", email_id])
    argv.extend(["--template", packet["template"], "--mode", packet["mode"]])
    return argv


def run(owner_input_file, contact_state, action):
    if action != "stage5-plan":
        raise ValueError("unsupported_capture_action")
    capture_source = Path(__file__).resolve()
    if capture_source.name != CAPTURE_NAME:
        raise ValueError("capture_source_name_mismatch")
    consumer_root = capture_source.parent.parent.resolve()
    entrypoint = _installed_entrypoint(consumer_root)
    requested_entrypoint_source = Path(contact_state)
    if requested_entrypoint_source.is_symlink():
        raise ValueError("installed_entrypoint_symlink")
    requested_entrypoint = requested_entrypoint_source.resolve()
    if requested_entrypoint != entrypoint:
        raise ValueError("installed_entrypoint_argument_mismatch")

    input_path_source = Path(owner_input_file)
    if input_path_source.is_symlink():
        raise ValueError("owner_input_file_symlink")
    input_path = input_path_source.resolve(strict=True)
    if not input_path.is_file():
        raise ValueError("owner_input_file_not_regular")
    raw_input = input_path.read_bytes()
    packet = json.loads(raw_input.decode("utf-8"), object_pairs_hook=_unique_pairs)
    if not isinstance(packet, dict):
        raise ValueError("owner_input_not_object")

    # Keep this object unchanged: both the observation and CLI argv are derived
    # from this one parse result; choices/results are not injected or rewritten.
    observed_packet = packet
    argv = _build_argv(packet, entrypoint)
    completed = subprocess.run(
        argv, cwd=consumer_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    stdout_text = completed.stdout.decode("utf-8")
    plan = json.loads(stdout_text, object_pairs_hook=_unique_pairs)
    if not isinstance(plan, dict):
        raise ValueError("stage5_plan_stdout_not_object")

    capture_id = str(uuid.uuid4())
    source_sha256 = _sha256(capture_source.read_bytes())
    envelope = {
        "pc68_fixed_capture": {
            "schema": CAPTURE_SCHEMA,
            "capture_id": capture_id,
            "wrapper_sha256": source_sha256,
            "wrapper_arguments": list(sys.argv[1:]),
            "owner_input_file": str(input_path_source),
            "owner_input_sha256": _sha256(raw_input),
            "owner_input_read_count": 1,
            "parsed_object_sha256": _sha256(_canonical(packet)),
        },
        "pc68_actual_input_observation": {
            "schema": SCHEMA,
            "source_step": "owner_input_json_parse",
            "business_step": "stage5-plan",
            "object": observed_packet,
        },
        "stage5_invocation": {"capture_id": capture_id, "argv": argv},
        "stage5_raw_stdout": stdout_text,
        "stage5_process": {
            "capture_id": capture_id,
            "stdout_sha256": _sha256(completed.stdout),
            "stderr_sha256": _sha256(completed.stderr),
        },
        "stage5_plan": plan,
        "return_code": completed.returncode,
    }
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True)
    parser.add_argument("--owner-input-file", required=True, type=Path)
    parser.add_argument("--contact-state", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        return run(args.owner_input_file, args.contact_state, args.action)
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print("pc68_capture_error:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
