"""Local synthetic check for issue 68's selected transfer-location wiring.

This entrypoint performs real local filesystem writes, reads, and removals in
synthetic fixtures. Its request, runtime, thread, and agent-event records are
synthetic and do not constitute formal runtime evidence.
"""
import argparse
import hashlib
import json
import shlex
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_issue68_codex_request_r12 as request_builder
import issue68_lifecycle as lifecycle
import issue68_transfer_location as transfer_location


SCENARIOS = {
    "success": ("PASS", "request_lifecycle_and_state_preservation_proven"),
    "valid_remnant": ("FAIL_PRODUCT", "request_transfer_file_remains"),
    "protected_data_changed": ("FAIL_PRODUCT", "other_request_file_changed_or_deleted"),
    "wrong_request": ("INVALID_EVIDENCE", "lifecycle_request_boundary_invalid"),
    "omitted_scan": ("BLOCKED_OBSERVABILITY", "transfer_path_outside_observation_scope"),
    "missing_use": ("BLOCKED_OBSERVABILITY", "transfer_creation_and_cleanup_unobservable"),
    "outside_scope": ("BLOCKED_OBSERVABILITY", "transfer_path_outside_observation_scope"),
}


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _event(sequence, method, thread, turn, item_id, command, output="", exit_code=0):
    return {
        "runtime_seq": sequence,
        "runtime_generation": "synthetic-local-r32",
        "message": {
            "method": method,
            "params": {
                "threadId": thread,
                "turnId": turn,
                "item": {
                    "type": "commandExecution",
                    "id": item_id,
                    "command": command,
                    "exitCode": exit_code,
                    "aggregatedOutput": output,
                },
            },
        },
    }


def _emit_command(events, command_id, thread, turn, command, output):
    start = len(events) + 1
    events.append(_event(start, "item/started", thread, turn, command_id, command))
    events.append(_event(start + 1, "item/completed", thread, turn, command_id,
                         command, output, 0))


def _run_case(output, workspace, scenario):
    case_output = output / scenario
    case_output.mkdir()
    case_workspace = workspace / scenario
    consumer = case_workspace / "consumer"
    program_root = consumer / "program"
    professor_dir = program_root / "synthetic-owner"
    transfer_root = case_workspace / "selected-transfer"
    outside_root = case_workspace / "unobserved-transfer"
    consumer.mkdir(parents=True)
    professor_dir.mkdir(parents=True)
    transfer_root.mkdir()
    pack_path = professor_dir / "email-pack.json"
    other_request_path = consumer / "other-request.json"
    _write_json(pack_path, {"synthetic_business_pack": True, "emails": []})
    _write_json(other_request_path, {"protected_synthetic_request": True})

    declared_root = transfer_root.resolve()
    transfer_location.validate_location_root(
        declared_root,
        {"consumer": consumer, "program": program_root, "evidence_output": output},
    )
    declaration = transfer_location.location_declaration(declared_root)
    business_prompt = "只处理本次合成输入并保留其他请求数据。"
    combined_prompt = transfer_location.compose_prompt(declaration, business_prompt)
    actual_request = request_builder.build_request(consumer, combined_prompt)
    command_words = shlex.split(actual_request["command"])
    request_prompt_bound = bool(command_words and command_words[-1] == combined_prompt)
    request = {
        "schema": "issue-68-transfer-location-preflight-r32",
        "execution_kind": "synthetic_local_preflight",
        "transfer_location_root": str(declared_root),
        "declaration": declaration,
        "business_prompt": business_prompt,
        "combined_prompt_sha256": _digest(combined_prompt.encode("utf-8")),
        "serialized_request": actual_request,
        "formal_case_started": False,
        "runtime_events_synthetic": True,
    }

    manifest = {
        "program_root": str(program_root.resolve()),
        "owners": [{
            "professor_dir": str(professor_dir.resolve()),
            "email_pack": str(pack_path.resolve()),
        }],
        "protected_other_request_files": [str(other_request_path.resolve())],
        "owner_capture": {"consumer_root": str(consumer.resolve())},
        "synthetic_test_layout_only": True,
    }
    transfer_location.bind_lifecycle_observation(manifest, declared_root)
    if scenario == "omitted_scan":
        manifest["lifecycle_extra_observation_roots"] = []

    before = lifecycle.bind_before(
        lifecycle.collect_before(manifest, consumer), request)
    if scenario == "wrong_request":
        # Change the serialized request only after the before boundary was
        # bound, so the verifier must reject this request association.
        request["serialized_request"]["command"] = "codex exec -- prompt without declaration"
    request_path = case_output / "request.json"
    manifest_path = case_output / "manifest.json"
    before_path = case_output / "before.json"
    _write_json(request_path, request)
    _write_json(before_path, before)

    actual_root = outside_root if scenario == "outside_scope" else transfer_root
    if actual_root == outside_root:
        actual_root.mkdir()
    choices_path = actual_root / "synthetic-choices.json"
    partition_path = actual_root / "synthetic-partition.json"
    handoff_path = actual_root / "synthetic-handoff.json"
    packet = {
        "professor_dir": str(professor_dir.resolve()),
        "email_pack": str(pack_path.resolve()),
        "email_id": "synthetic-id",
        "choices": [{"key": "synthetic-choice", "value": "synthetic-value"}],
    }
    actions = []
    for path, value in ((choices_path, packet["choices"]),
                        (partition_path, {"status": "ok", "owners": [packet]}),
                        (handoff_path, packet)):
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        path.write_bytes(raw)
        actions.append({"operation": "real_local_synthetic_write", "path": str(path.resolve()),
                        "sha256": _digest(raw), "size": len(raw)})

    actual_use = None
    if scenario != "missing_use":
        raw_handoff = handoff_path.read_bytes()
        parsed_object = json.loads(raw_handoff.decode("utf-8"))
        actual_use = {
            "operation": "real_local_synthetic_read",
            "path": str(handoff_path.resolve()),
            "sha256": _digest(raw_handoff),
            "size": len(raw_handoff),
            "parsed_object": parsed_object,
            "same_parsed_object_use": {
                key: parsed_object[key] for key in ("email_pack", "email_id", "choices")
            },
            "capture_id": "synthetic-local-capture-r32",
            "runtime_thread_and_agent_attribution": "synthetic_records_only",
        }

    if scenario == "valid_remnant":
        cleanup_paths = (choices_path, partition_path)
    else:
        cleanup_paths = (choices_path, partition_path, handoff_path)
    for path in cleanup_paths:
        raw = path.read_bytes()
        path.unlink()
        actions.append({"operation": "real_local_synthetic_remove", "path": str(path.resolve()),
                        "sha256": _digest(raw), "size": len(raw)})

    if scenario == "protected_data_changed":
        changed = b'{"protected_synthetic_request": false}\n'
        other_request_path.write_bytes(changed)
        actions.append({"operation": "real_local_synthetic_protected_data_change",
                        "path": str(other_request_path.resolve()), "sha256": _digest(changed),
                        "size": len(changed)})

    actual_use_artifact = {
        "execution_kind": "synthetic_local_preflight",
        "filesystem_operations": actions,
        "actual_use": actual_use,
        "selected_transfer_root": str(declared_root),
        "actual_transfer_root": str(actual_root.resolve()),
        "test_layout_is_not_a_product_filename_requirement": True,
    }
    actual_use_path = case_output / "actual-use.json"
    _write_json(actual_use_path, actual_use_artifact)

    partition_command = "synthetic-root partition choices"
    owner_command = "synthetic-professor read handoff"
    command_actions = {
        partition_command: {
            "action": "stage5-partition-choices",
            "flags": {"--choices": str(choices_path.resolve()),
                      "--out": str(partition_path.resolve())},
        }
    }
    if actual_use is not None:
        command_actions[owner_command] = {
            "owner_capture": {"owner_input_file": str(handoff_path.resolve())}
        }

    partition_return = {"status": "ok", "owners": [packet]}
    events = []
    _emit_command(events, "synthetic-partition-command", "synthetic-root-thread",
                  "synthetic-root-turn", partition_command,
                  json.dumps(partition_return, ensure_ascii=False))
    if actual_use is not None:
        capture = {
            "owner_input_file": str(handoff_path.resolve()),
            "owner_input_sha256": actual_use["sha256"],
            "capture_id": actual_use["capture_id"],
            "parsed_object": actual_use["parsed_object"],
        }
        owner_envelope = {
            "pc68_fixed_capture": capture,
            "same_object_use": actual_use["same_parsed_object_use"],
        }
        _emit_command(events, "synthetic-owner-use-command", "synthetic-owner-thread",
                      "synthetic-owner-turn", owner_command,
                      json.dumps(owner_envelope, ensure_ascii=False))
    response = {
        "execution_kind": "synthetic_response_envelope",
        "output": {
            "thread_id": "synthetic-root-thread",
            "turn_id": "synthetic-root-turn",
            "runtime_generation": "synthetic-local-r32",
            "app_server_events": events,
        },
    }

    def command_action(command, _manifest):
        return command_actions.get(command)

    def consumed_business_objects(calls, _manifest):
        envelope = json.loads(calls[0]["output"])
        return [{"packet": envelope["pc68_fixed_capture"]["parsed_object"]}], None

    verifier = SimpleNamespace(command_action=command_action,
                               consumed_business_objects=consumed_business_objects)
    after = lifecycle.collect_before(manifest, consumer)
    after["phase"] = "after_request"
    evidence = lifecycle.collect_lifecycle(
        before, manifest, consumer, response, verifier, after=after)
    manifest["lifecycle_boundary"] = {
        "request_artifact": str(request_path.resolve()),
        "before_artifact": str(before_path.resolve()),
        "run_id": before["request_boundary"]["run_id"],
        "before_sha256": lifecycle._response_digest(before),
        "after_sha256": lifecycle._response_digest(evidence["after"]),
    }
    adapter = {"dispatch": {"thread_relations": [{
        "tool": "spawnAgent",
        "sender_thread_id": "synthetic-root-thread",
        "receiver_thread_ids": ["synthetic-owner-thread"],
    }]}}
    proof = lifecycle.verify_bound_lifecycle(evidence, manifest, response, adapter, verifier)

    before_transfer = before.get("extra_0", {})
    after_transfer = evidence["after"].get("extra_0", {})
    same_transfer_snapshot_root = (
        before_transfer.get("root") == str(declared_root)
        and after_transfer.get("root") == str(declared_root)
    )
    actual_read_bound = bool(actual_use and evidence.get("reads")
        and evidence["reads"][0].get("path") == actual_use["path"]
        and evidence["reads"][0].get("sha256") == actual_use["sha256"]
        and evidence["reads"][0].get("thread") == "synthetic-owner-thread")
    result = {
        "scenario": scenario,
        "expected": {"verdict": SCENARIOS[scenario][0], "reason_code": SCENARIOS[scenario][1]},
        "observed": {"verdict": proof["verdict"], "reason_code": proof["reason_code"]},
        "request_declaration_in_serialized_prompt": request_prompt_bound,
        "declaration_relays_root_and_leaves_layout_to_product": all(
            phrase in declaration for phrase in ("根任务必须将此位置转告负责该教授的代理",
                                                  "文件名和目录布局由产品自行选择")),
        "selected_root_is_absolute_and_exclusive_at_start": (
            declared_root.is_absolute() and not before_transfer.get("entries")
        ),
        "same_selected_root_in_before_and_after": same_transfer_snapshot_root,
        "actual_read_attributed_to_synthetic_professor_thread": actual_read_bound,
        "all_filesystem_actions_are_real_local_synthetic_operations": True,
        "runtime_thread_and_agent_events_are_synthetic": True,
        "formal_case_started": False,
    }
    _write_json(manifest_path, manifest)
    _write_json(case_output / "response.json", response)
    _write_json(case_output / "after.json", evidence["after"])
    _write_json(case_output / "lifecycle-evidence.json", evidence)
    _write_json(case_output / "result.json", result)
    matches = (proof["verdict"], proof["reason_code"]) == SCENARIOS[scenario]
    if scenario == "success":
        matches = matches and all((request_prompt_bound, same_transfer_snapshot_root,
                                   actual_read_bound, result["selected_root_is_absolute_and_exclusive_at_start"],
                                   result["declaration_relays_root_and_leaves_layout_to_product"]))
    return result, matches


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path,
                        help="new, empty evidence directory; existing directories are rejected")
    args = parser.parse_args(argv)
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error("output directory already exists; preflight evidence will not be overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=False, exist_ok=False)
    workspace = output.parent / (output.name + "-synthetic-workspace-" + uuid.uuid4().hex)
    workspace.mkdir()

    cases, all_matched = [], True
    for scenario in SCENARIOS:
        result, matched = _run_case(output, workspace, scenario)
        cases.append({"scenario": scenario, "verdict": result["observed"]["verdict"],
                      "reason_code": result["observed"]["reason_code"],
                      "expected_match": matched})
        all_matched = all_matched and matched
    summary = {
        "schema": "issue-68-transfer-location-preflight-summary-r32",
        "execution_kind": "synthetic_local_preflight",
        "state": "PRECHECK_CASES_MATCHED" if all_matched else "PREFLIGHT_INCOMPLETE",
        "plan_revision": "issue-68-test-plan-r27-2026-10-07",
        "output_directory": str(output),
        "synthetic_workspace": str(workspace),
        "filesystem_actions": "real local synthetic writes, reads, and removals",
        "runtime_thread_agent_events": "synthetic records; not formal runtime evidence",
        "eval_service_called": False,
        "formal_PC68_R1_started": False,
        "source_sha256": {
            "lifecycle": _digest(Path(lifecycle.__file__).read_bytes()),
            "transfer_location": _digest(Path(transfer_location.__file__).read_bytes()),
            "preflight": _digest(Path(__file__).read_bytes()),
        },
        "cases": cases,
        "uncompleted": ["formal_PC68_R1_execution", "Gate_2_approval"],
    }
    _write_json(output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if all_matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
