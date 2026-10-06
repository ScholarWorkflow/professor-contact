"""Pure synthetic r26 combination check; never a professor or eval request.

Real local command returns and complete snapshots exercise the fixed bound
lifecycle verifier. Runtime envelopes and topology are explicitly synthetic;
historical eval responses only establish the field convention, not this run.
"""
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import issue68_lifecycle as lifecycle

EXPECTED = {"legal": "PASS", "residual": "FAIL_PRODUCT",
            "protected_changed": "FAIL_PRODUCT", "wrong_request": "INVALID_EVIDENCE",
            "missing_use": "BLOCKED_OBSERVABILITY", "incomplete_scan": "INVALID_EVIDENCE"}


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def worker(phase, root, scenario):
    root = Path(root)
    choices, partition, handoff = [root / name for name in
                                  ("choices.json", "partition.json", "handoff.json")]
    if phase == "form":
        packet = {"professor_dir": str(root / "program" / "synthetic-owner"),
                  "email_pack": str(root / "program" / "synthetic-owner" / "email-pack.json"),
                  "email_id": "原编号::空 格", "choices": [{"value": "合成值", "order": [2, 1, 2]}]}
        write(choices, packet["choices"])
        selection = json.loads(choices.read_text())
        returned = {"status": "ok", "owners": [{**packet, "choices": selection}]}
        write(partition, returned)
        write(handoff, returned["owners"][0])
        print(json.dumps(returned, ensure_ascii=False))
    elif phase == "use":
        raw = handoff.read_bytes()
        parsed = json.loads(raw)
        # One parse only; both capture and use refer to this same object.
        used = {"email_pack": parsed["email_pack"], "email_id": parsed["email_id"],
                "choices": parsed["choices"]}
        print(json.dumps({"pc68_fixed_capture": {"owner_input_file": str(handoff),
            "owner_input_sha256": hashlib.sha256(raw).hexdigest(),
            "capture_id": "synthetic-local-capture", "parsed_object": parsed},
            "same_object_use": used}, ensure_ascii=False))
    elif phase == "clean":
        for path in (choices, partition, handoff):
            if scenario != "residual" or path != handoff:
                path.unlink()
        if scenario == "protected_changed":
            (root / "other-request.json").write_text("changed synthetic data\n")
        print(json.dumps({"finished": True}))


def run_case(output, scenario):
    output.mkdir(parents=True)
    consumer = output / "consumer"
    owner = consumer / "program" / "synthetic-owner"
    owner.mkdir(parents=True)
    write(owner / "email-pack.json", {"synthetic": True, "emails": []})
    write(consumer / "other-request.json", {"synthetic_other_request": True})
    manifest = {"program_root": str(consumer / "program"),
        "owners": [{"professor_dir": str(owner), "email_pack": str(owner / "email-pack.json")}],
        "protected_other_request_files": [str(consumer / "other-request.json")],
        "owner_capture": {"consumer_root": str(consumer)}}
    request = {"kind": "synthetic_local_combination", "scenario": scenario,
               "consumer": str(consumer), "formal_case_started": False}
    write(output / "request.json", request)
    before = lifecycle.bind_before(lifecycle.collect_before(manifest, consumer), request)
    write(output / "before.json", before)
    events, records, command_actions = [], [], {}
    for phase in ("form", "use", "clean"):
        argv = ["uv", "run", str(Path(__file__).resolve()), "--worker", phase, str(consumer), scenario]
        command = shlex.join(argv)
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=30,
            env={**os.environ, "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", "/private/tmp/pc68-r31-uv-cache")})
        records.append({"argv": argv, "exit_code": completed.returncode,
                        "stdout": completed.stdout, "stderr": completed.stderr})
        if completed.returncode:
            raise RuntimeError("synthetic_worker_failed:" + phase)
        thread = "synthetic-owner-thread" if phase == "use" else "synthetic-root-thread"
        for method in ("item/started", "item/completed"):
            events.append({"runtime_seq": len(events) + 1, "runtime_generation": "synthetic-local-1",
                "message": {"method": method, "params": {"threadId": thread,
                    "turnId": "synthetic-local-turn", "item": {"type": "commandExecution",
                    "id": "synthetic-command-" + phase, "command": command,
                    "exitCode": completed.returncode, "aggregatedOutput": completed.stdout}}}})
        if phase == "form":
            command_actions[command] = {"action": "stage5-partition-choices", "flags": {
                "--choices": str(consumer / "choices.json"), "--out": str(consumer / "partition.json")}}
        elif phase == "use":
            command_actions[command] = {"owner_capture": {"synthetic": True}}
    write(output / "commands.json", records)
    response = {"synthetic_runtime_envelope": True, "output": {
        "thread_id": "synthetic-root-thread", "turn_id": "synthetic-local-turn",
        "runtime_generation": "synthetic-local-1", "app_server_events": events}}
    if scenario == "missing_use":
        response["output"]["app_server_events"] = [event for event in events
            if event["message"]["params"]["item"]["id"] != "synthetic-command-use"]
    verifier = SimpleNamespace(command_action=lambda command, _: command_actions.get(command),
        consumed_business_objects=lambda calls, _: ([{"packet": json.loads(calls[0]["output"])
            ["pc68_fixed_capture"]["parsed_object"]}], None))
    after = lifecycle.collect_before(manifest, consumer)
    after["phase"] = "after_request"
    evidence = lifecycle.collect_lifecycle(before, manifest, consumer, response, verifier, after=after)
    if scenario == "wrong_request":
        evidence["after"]["request_boundary"]["run_id"] = "different-synthetic-request"
    if scenario == "incomplete_scan":
        evidence["after"]["consumer"]["complete"] = False
    manifest["lifecycle_boundary"] = {"request_artifact": str(output / "request.json"),
        "before_artifact": str(output / "before.json"), "run_id": before["request_boundary"]["run_id"],
        "before_sha256": lifecycle._response_digest(before),
        "after_sha256": lifecycle._response_digest(evidence["after"])}
    adapter = {"dispatch": {"thread_relations": [{"tool": "spawnAgent",
        "sender_thread_id": "synthetic-root-thread", "receiver_thread_ids": ["synthetic-owner-thread"]}]}}
    proof = lifecycle.verify_bound_lifecycle(evidence, manifest, response, adapter, verifier)
    use = json.loads(records[1]["stdout"])
    parsed = use["pc68_fixed_capture"]["parsed_object"]
    same = use["same_object_use"] == {key: parsed[key] for key in ("email_pack", "email_id", "choices")}
    result = {"scenario": scenario, "proof": proof, "same_parsed_object_used": same,
              "mutation_operation_events": len([op for op in evidence["file_operations"]
                  if op["source"] == "completed_command_with_successful_exit"]),
              "command_exit_codes": [record["exit_code"] for record in records]}
    for name, value in (("response", response), ("manifest", manifest), ("evidence", evidence), ("result", result)):
        write(output / (name + ".json"), value)
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--worker":
        worker(*argv[1:])
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    for label in ("03", "04"):
        parser.add_argument("--historical-response-" + label, type=Path,
                            help="Optional original response; field convention only")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        parser.error("output directory already exists; evidence will not be overwritten")
    historical_sources = []
    for label in ("03", "04"):
        source = getattr(args, "historical_response_" + label)
        if source is None:
            continue
        source = source.resolve()
        try:
            raw = source.read_bytes()
            calls = lifecycle._commands(json.loads(raw))
        except (OSError, ValueError) as error:
            parser.error("cannot read historical response " + label + ": " + str(error))
        historical_sources.append({"attempt": label, "source_path": str(source),
            "response_sha256": hashlib.sha256(raw).hexdigest(), "command_count": len(calls),
            "reused_fact": "command_id_output_thread_generation_and_sequence_field_convention_only"})
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output directory already exists; evidence will not be overwritten")
    results = [run_case(output / scenario, scenario) for scenario in EXPECTED]
    all_passed = all(result["proof"]["verdict"] == EXPECTED[result["scenario"]]
                     and result["same_parsed_object_used"] for result in results)
    summary = {"execution_kind": "synthetic_combination_preflight", "formal_case_started": False,
        "state": "COMBINATION_VERIFIER_READY" if all_passed else "PREFLIGHT_INCOMPLETE",
        "plan_revision": "issue-68-test-plan-r26-2026-10-07",
        "expected_verdict_source": "r26_lifecycle_minimum_validation_conditions",
        "expected_verdicts": EXPECTED,
        "fixed_entrypoint": "UV_CACHE_DIR=<private-cache> uv run tests/runtime/preflight_issue68_lifecycle_combination_r31.py <new-private-evidence-directory>",
        "runtime_envelopes_and_topology": "synthetic_not_eval_or_professor_evidence",
        "commands_and_filesystem": "actual_local_subprocess_results_and_complete_snapshots",
        "lifecycle_source_sha256": hashlib.sha256(Path(lifecycle.__file__).read_bytes()).hexdigest(),
        "entrypoint_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cases": [{**result, "proof": {key: result["proof"][key] for key in ("verdict", "reason_code")}}
                  for result in results],
        "uncompleted": ["formal_allowed_transfer_location_coverage", "formal_PC68_R1_execution",
                        "second_gate_complete_approval"],
        "historical_source_reuse": historical_sources}
    write(output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
