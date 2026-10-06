#!/usr/bin/env python3
"""PC68-R1 Codex entrypoint with the r25 per-call observation gate."""
import argparse
import hashlib
import json
import shlex
import signal
import shutil
import subprocess
import sys
from pathlib import Path

import issue68_eval_service_isolation_r14 as isolation
import run_issue68_stage5_routing as base
import run_issue68_stage5_routing_r19 as bridge
import verify_issue68_stage5_routing_r19 as input_verifier
import bind_issue68_preflight_command_event_r29 as command_event_binder
import issue68_lifecycle as lifecycle


HERE = Path(__file__).resolve().parent
FIXTURE_SHA = bridge.FIXTURE_SHA
CONTRACT = HERE / "issue68-runtime-evidence-contract-r19.json"
CONTRACT_REVISION = "issue-68-runtime-evidence-r30-2026-10-06"
OWNER_OBSERVATION_SCHEMA = "issue-68-test-plan-r25-owner-input-v2"
SYNTHETIC_PREFLIGHT_SCHEMA = "issue-68-r29-fixed-capture-preflight-v2"
CONTRACT_RUNNER = ".apm/skills/professor-contact/tests/runtime/" + Path(__file__).name
EXECUTION_KIND = "acceptance"
HOST = "codex"
CASE = "PC68-R1"
PREFLIGHT_DIR = HERE / "evidence"
PREFLIGHT_MANIFEST = PREFLIGHT_DIR / "issue68-r29-command-event-preflight.json"
PREFLIGHT_STDOUT = PREFLIGHT_DIR / "issue68-r29-command-event-stdout.json"
REQUIRED_RUNTIME_FACTS = (
    "model", "executor", "entrypoint", "isolation", "shared_assets", "service_version",
)
PRE_SERVICE_RUNTIME_FACTS = tuple(
    fact for fact in REQUIRED_RUNTIME_FACTS if fact != "service_version"
)
RUNTIME_BINDING_ARTIFACTS = (
    "input-evidence-preflight.json",
    "provenance.json",
    "codex/codex-request.json",
    "codex/installed-entrypoint.json",
    "codex/apm.lock.yaml",
    "eval-service-provenance.before.json",
    "eval-service-provenance.after.json",
    "runtime-environment-evidence.json",
)


def load_contract():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("revision") != CONTRACT_REVISION:
        raise ValueError("contract_revision_mismatch")
    if contract.get("fixture_sha") != FIXTURE_SHA:
        raise ValueError("contract_fixture_mismatch")
    if contract.get("producer_revision") != "b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d":
        raise ValueError("contract_producer_revision_mismatch")
    if contract.get("runner") != CONTRACT_RUNNER:
        raise ValueError("contract_runner_is_not_this_entry")
    if contract.get("manual_patch") != "no":
        raise ValueError("contract_manual_patch_forbidden")
    environment = contract.get("formal_runtime_environment")
    if not isinstance(environment, dict) or not isinstance(environment.get("actual_values"), dict):
        raise ValueError("contract_runtime_environment_fields_missing")
    actual_values = environment["actual_values"]
    if environment.get("required_facts") != list(REQUIRED_RUNTIME_FACTS) \
            or set(actual_values) != set(REQUIRED_RUNTIME_FACTS):
        raise ValueError("contract_runtime_environment_fields_incomplete")
    codex = contract.get("codex", {})
    observation = codex.get("owner_business_input_observation")
    if not isinstance(observation, dict) or observation.get("status") not in ("supported", "blocked"):
        raise ValueError("contract_actual_input_observation_status_missing")
    if observation.get("schema") != OWNER_OBSERVATION_SCHEMA \
            or observation.get("source") != "output.app_server_events.commandExecution.aggregatedOutput":
        raise ValueError("contract_actual_input_observation_source_mismatch")
    if observation.get("status") != "supported":
        raise ValueError("contract_actual_input_observation_status_unsupported")
    second_gate_status = contract.get("preflight", {}).get("second_gate_status")
    if second_gate_status not in ("INCOMPLETE", "COMPLETE"):
        raise ValueError("contract_second_gate_status_mismatch")
    gate_allowed = contract.get("preflight", {}).get("input_observation_gate", {}).get(
        "formal_run_allowed") is True
    if (second_gate_status == "COMPLETE") != gate_allowed:
        raise ValueError("contract_second_gate_decision_mismatch")
    if not codex.get("owner_input_isolation"):
        raise ValueError("contract_owner_input_isolation_missing")
    if not codex.get("canonical_preservation"):
        raise ValueError("contract_canonical_preservation_missing")
    if not codex.get("partition_evidence"):
        raise ValueError("contract_partition_evidence_missing")
    steps = contract.get("pc68_r1_steps")
    expected_steps = [
        "R1-1-discover-and-partition", "R1-2-formal-delegation",
        "R1-3-handoff-and-single-parse", "R1-4-first-stage5-plan",
        "R1-5-child-result-consumption", "R1-6-root-overview-and-final-report",
        "R1-7-isolation-and-cleanup",
    ]
    if not isinstance(steps, list) or [step.get("step") for step in steps] != expected_steps:
        raise ValueError("contract_pc68_r1_steps_incomplete")
    terminal_mapping = contract.get("machine_terminal_mapping", {})
    required_terminal_states = {
        "PASS", "FAIL_PRODUCT", "INVALID_TEST_EXECUTION", "INVALID_EVIDENCE", "UNKNOWN",
        "BLOCKED_OBSERVABILITY",
        "BLOCKED_DEPENDENCY", "CASE_NOT_STARTED", "NOT_TESTED", "unknown_machine_state",
        "FIXTURE_READY", "HARNESS_DISPATCH_UNCONFIRMED", "HARNESS_DISPATCH_MISMATCH",
        "OBSERVATION_SOURCE_SUPPORTED",
    }
    if not required_terminal_states.issubset(terminal_mapping) or "conflict_priority" in terminal_mapping:
        raise ValueError("contract_machine_terminal_mapping_incomplete")
    if terminal_mapping != input_verifier._terminal_contract():
        raise ValueError("contract_verifier_terminal_mapping_mismatch")
    aggregation = contract.get("terminal_aggregation", {})
    if aggregation.get("confirmed_failure_machine_state") != "FAIL_PRODUCT" \
            or aggregation.get("confirmed_failure_formal_terminal") != "FAIL" \
            or not isinstance(aggregation.get("rule"), str):
        raise ValueError("contract_terminal_aggregation_rule_missing")
    return contract


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_recorded(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list, tuple)):
        return bool(value)
    return True


def _runtime_environment_missing(facts):
    return [key for key in REQUIRED_RUNTIME_FACTS if not _is_recorded(facts.get(key))]


def _register_runtime_fact(preflight, key, value, source_artifacts, **details):
    if key not in REQUIRED_RUNTIME_FACTS or not _is_recorded(value):
        raise ValueError("runtime_environment_fact_unobservable:" + key)
    updated = dict(preflight)
    facts = dict(updated.get("runtime_environment_facts", {}))
    evidence = dict(updated.get("runtime_environment_evidence", {}))
    facts[key] = value
    evidence[key] = {"source_artifacts": list(source_artifacts), **details}
    updated["runtime_environment_facts"] = facts
    updated["runtime_environment_evidence"] = evidence
    updated["runtime_environment_missing"] = _runtime_environment_missing(facts)
    updated["formal_run_allowed"] = (
        updated.get("service_preflight_allowed") is True
        and not updated["runtime_environment_missing"]
    )
    return updated


def _record_service_runtime_facts(preflight, service_snapshot):
    version = service_snapshot.get("eval_server", {}).get("sha")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("eval_service_version_unobservable")
    if service_snapshot.get("storage", {}).get("status") != "ISOLATION_CONFIRMED":
        raise ValueError("eval_service_isolation_unconfirmed")
    updated = _register_runtime_fact(
        preflight, "service_version", version, ["eval-service-provenance.before.json"],
        collection="read-only current clean checkout revision",
    )
    return _register_runtime_fact(
        updated, "isolation", service_snapshot["storage"],
        ["eval-service-provenance.before.json"],
        collection="read-only service storage isolation inspection",
    )


def _record_codex_executor_fact(preflight):
    dispatcher = base.codex_host
    if getattr(dispatcher, "__name__", None) != "codex_host":
        raise ValueError("codex_executor_branch_unverified")
    dispatcher_source = Path(dispatcher.__code__.co_filename).resolve()
    runner_source = Path(__file__).resolve()
    executor = {
        "execution_branch": "codex",
        "dispatcher": dispatcher.__module__ + "." + dispatcher.__qualname__,
        "source_evidence": [
            {"path": str(dispatcher_source), "sha256": _sha256_file(dispatcher_source)},
            {"path": str(runner_source), "sha256": _sha256_file(runner_source)},
        ],
        "version": None,
        "version_note": "No separate runtime executor version is exposed by this runner; source hashes identify the executed branch.",
    }
    return _register_runtime_fact(
        preflight, "executor", executor,
        [str(dispatcher_source), str(runner_source)],
        collection="active Codex dispatch branch and source hashes",
    )


def _portable_artifact_path(path):
    resolved = Path(path).resolve()
    repo_root = input_verifier.OWNER_CAPTURE_SOURCE.parents[5].resolve()
    try:
        relative = resolved.relative_to(repo_root)
    except ValueError:
        return "/__pc68_artifact__/" + resolved.name
    return "/__pc68_repo__/" + relative.as_posix()


def _synthetic_capture_preflight():
    """Verify the saved synthetic output came from a passing fixed-wrapper preflight."""
    try:
        artifact = json.loads(PREFLIGHT_MANIFEST.read_text(encoding="utf-8"))
        stdout_bytes = PREFLIGHT_STDOUT.read_bytes()
        stdout = stdout_bytes.decode("utf-8")
    except (OSError, UnicodeError, ValueError):
        return None, {"state": "CASE_NOT_STARTED", "reason_code": "synthetic_capture_preflight_missing"}
    if artifact.get("schema") != SYNTHETIC_PREFLIGHT_SCHEMA \
            or artifact.get("formal_case_started") is not False \
            or artifact.get("eval_service_called") is not False \
            or artifact.get("external_request_made") is not False:
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_preflight_record_invalid"}
    if artifact.get("result") == "CAPTURED_SYNTHETIC_PENDING_COMMAND_EVENT":
        return None, {"state": "BLOCKED_OBSERVABILITY", "reason_code": "ordinary_command_event_missing"}
    if artifact.get("result") != "CAPTURED_SYNTHETIC_WITH_ACTUAL_COMMAND_EVENT":
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_preflight_record_invalid"}
    if artifact.get("owner_input_read_count") != 1 \
            or artifact.get("parsed_object") != artifact.get("observation_object"):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_parse_copy_invalid"}
    if artifact.get("stdout_capture_path") != _portable_artifact_path(PREFLIGHT_STDOUT):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_path_mismatch"}
    normalization = artifact.get("portable_path_normalization", {})
    if normalization.get("state") != "VERIFIED_THEN_NORMALIZED" \
            or normalization.get("placeholders") != {
                "repository_root": "/__pc68_repo__",
                "synthetic_run_root": "/__pc68_synthetic__",
                "uv_python": "/__pc68_uv__/python",
                "artifact_root": "/__pc68_artifact__",
            }:
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_path_normalization_missing"}
    if artifact.get("parsed_object_sha256") != hashlib.sha256(
            _canonical_json(artifact.get("parsed_object")).encode("utf-8")).hexdigest() \
            or artifact.get("observation_object_sha256") != hashlib.sha256(
                _canonical_json(artifact.get("observation_object")).encode("utf-8")).hexdigest():
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_object_hash_invalid"}
    if not isinstance(artifact.get("captured_parsed_object_sha256"), str) \
            or len(artifact["captured_parsed_object_sha256"]) != 64 \
            or not isinstance(artifact.get("captured_stdout_sha256"), str) \
            or len(artifact["captured_stdout_sha256"]) != 64:
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_original_hash_missing"}
    if hashlib.sha256(stdout_bytes).hexdigest() != artifact.get("stdout_sha256") \
            or stdout != artifact.get("raw_stdout"):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_stdout_changed"}
    argv = artifact.get("producer_argv")
    capture_argv = artifact.get("capture_command_argv")
    manifest = artifact.get("runner_manifest")
    if not isinstance(argv, list) or not argv or "--result" in argv or "--choices" in argv \
            or not isinstance(capture_argv, list) or not isinstance(manifest, dict):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_argv_invalid"}
    plan_output = artifact.get("producer_structured_output", {})
    packet = artifact.get("parsed_object", {})
    fixture = artifact.get("synthetic_fixture", {})
    fixture_pack = fixture.get("email_pack_content", {})
    fixture_emails = fixture_pack.get("emails")
    expected_id = packet.get("email_id")
    if artifact.get("producer_return_code") != 0 \
            or plan_output.get("status") != "ok" \
            or plan_output.get("email_pack") != packet.get("email_pack") \
            or plan_output.get("emails") != [expected_id] \
            or plan_output.get("output_mode") != packet.get("mode") \
            or not isinstance(fixture_emails, list) or len(fixture_emails) != 1:
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_producer_result_unexpected"}
    email = fixture_emails[0]
    verify_map = plan_output.get("verify")
    jobs = plan_output.get("jobs")
    if email.get("email_id") != expected_id \
            or email.get("professor") != fixture.get("professor") \
            or plan_output.get("needs_recheck_professors") != [fixture.get("professor")] \
            or not isinstance(verify_map, dict) or not isinstance(verify_map.get(fixture.get("professor")), str) \
            or not verify_map[fixture.get("professor")].startswith("needs_recheck:") \
            or not isinstance(jobs, list) or len(jobs) != 1 \
            or jobs[0].get("job_id") != "email:" + str(expected_id) \
            or jobs[0].get("kind") != "email" or not isinstance(jobs[0].get("model_input"), dict):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_plan_shape_unexpected"}
    expected_model_input = input_verifier._expected_model_input(email)
    actual_model_input = jobs[0]["model_input"]
    if any(actual_model_input.get(key) != value for key, value in expected_model_input.items()):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_plan_business_fields_mismatch"}
    # The wrapper result is locally checked first, then bound to the actual
    # ordinary commandExecution output captured from the Codex app thread.
    if artifact.get("fixed_capture_verification") != {
            "state": "PASS", "verifier": "same_object_invocation_and_plan",
            "wrapper_sha256": input_verifier.OWNER_CAPTURE_SHA256,
            "ordinary_command_event": "PASS",
            "ordinary_commandExecution_output_proven": True}:
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_fixed_capture_verification_missing"}
    preflight_script = HERE / "preflight_issue68_owner_input_observation_r29.py"
    if artifact.get("preflight_script") != _portable_artifact_path(preflight_script) \
            or artifact.get("preflight_script_sha256") != hashlib.sha256(
                preflight_script.read_bytes()).hexdigest():
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_preflight_script_binding_invalid"}
    try:
        output_envelope = json.loads(stdout)
        command_proof = input_verifier.command_action(shlex.join(capture_argv), manifest)
        invocation = input_verifier._structured_stage5_invocation(output_envelope.get("stage5_invocation"))
    except (ValueError, TypeError, AttributeError):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_envelope_invalid"}
    capture = output_envelope.get("pc68_fixed_capture", {})
    process = output_envelope.get("stage5_process", {})
    if not isinstance(command_proof, dict) or not isinstance(command_proof.get("owner_capture"), dict) \
            or capture.get("schema") != input_verifier.OWNER_CAPTURE_SCHEMA \
            or capture.get("wrapper_sha256") != input_verifier.OWNER_CAPTURE_SHA256 \
            or capture.get("owner_input_read_count") != 1 \
            or capture.get("parsed_object_sha256") != artifact.get("parsed_object_sha256") \
            or output_envelope.get("pc68_actual_input_observation", {}).get("object") != packet \
            or invocation.get("argv") != argv \
            or invocation.get("capture_id") != capture.get("capture_id") \
            or process.get("capture_id") != capture.get("capture_id") \
            or output_envelope.get("stage5_plan") != plan_output \
            or output_envelope.get("return_code") != artifact.get("producer_return_code"):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_association_mismatch"}
    invocation_flags = invocation.get("flags", {})
    expected_flags = {
        "--program-root": packet.get("program_root"),
        "--email-pack": packet.get("email_pack"),
        "--email-id": packet.get("email_id"),
        "--template": packet.get("template"),
        "--mode": packet.get("mode"),
    }
    if packet != artifact.get("parsed_object") \
            or invocation.get("action") != "stage5-plan" \
            or any(invocation_flags.get(flag) != value for flag, value in expected_flags.items()) \
            or any(flag in invocation_flags for flag in ("--result", "--choices")) \
            or output_envelope.get("stage5_plan") != artifact.get("producer_structured_output") \
            or output_envelope.get("return_code") != artifact.get("producer_return_code"):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_verifier_association_mismatch"}
    event_problem = command_event_binder.validate_bound_event(
        artifact, stdout, PREFLIGHT_MANIFEST, PREFLIGHT_STDOUT)
    if event_problem:
        state = "BLOCKED_OBSERVABILITY" if event_problem == "ordinary_command_event_missing" else "INVALID_TEST_EXECUTION"
        return None, {"state": state, "reason_code": event_problem}
    return artifact, None


def actual_input_observation_preflight(contract):
    """Check the installed source and bind synthetic output to a real tool event.

    The saved capture proves the ordinary commandExecution event and local
    same-object route only. It does not establish formal PC68-R1 association,
    runtime identity, or a formal run.
    """
    observation = contract.get("codex", {}).get("owner_business_input_observation", {})
    prompt = HERE / "prompts" / "issue68-stage5-root.txt"
    prompt_supported = prompt.is_file() and OWNER_OBSERVATION_SCHEMA in prompt.read_text(encoding="utf-8")
    source_supported = (
        observation.get("status") == "supported"
        and observation.get("schema") == OWNER_OBSERVATION_SCHEMA
        and observation.get("source") == "output.app_server_events.commandExecution.aggregatedOutput"
        and prompt_supported
    )
    artifact, capture_problem = _synthetic_capture_preflight()
    capture_supported = artifact is not None and capture_problem is None
    second_gate_complete = contract.get("preflight", {}).get("second_gate_status") == "COMPLETE"
    gate_allowed = contract.get("preflight", {}).get("input_observation_gate", {}).get(
        "formal_run_allowed") is True
    service_preflight_allowed = (
        source_supported and capture_supported and second_gate_complete and gate_allowed
    )
    runtime_values = {key: None for key in REQUIRED_RUNTIME_FACTS}
    missing_runtime_values = list(REQUIRED_RUNTIME_FACTS)
    block_reasons = []
    if not source_supported:
        block_reasons.append("actual_input_evidence_source_unavailable")
    if not capture_supported:
        block_reasons.append((capture_problem or {}).get("reason_code", "synthetic_capture_preflight_missing"))
    if not second_gate_complete:
        block_reasons.append("second_gate_incomplete")
    elif not gate_allowed:
        block_reasons.append("second_gate_decision_missing")
    return {
        "ready": source_supported and capture_supported,
        "state": ("OBSERVATION_SOURCE_SUPPORTED" if source_supported and capture_supported else
                  ((capture_problem or {}).get("state", "CASE_NOT_STARTED") if not capture_supported else
                   "BLOCKED_OBSERVABILITY")),
        "reason_code": (None if source_supported and capture_supported else
                        ((capture_problem or {}).get("reason_code") if not capture_supported
                         else "actual_input_evidence_source_unavailable")),
        "formal_run_allowed": False,
        "formal_run_block_reason": ("second_gate_incomplete" if not second_gate_complete else
                                    ("second_gate_decision_missing" if not gate_allowed else
                                     "runtime_environment_capture_pending")),
        "formal_run_block_reasons": block_reasons,
        "service_preflight_allowed": service_preflight_allowed,
        "runtime_environment_missing": missing_runtime_values,
        "runtime_environment_facts": runtime_values,
        "runtime_environment_evidence": {},
        "synthetic_capture": ({
            "result": artifact.get("result"),
            "stdout_sha256": artifact.get("stdout_sha256"),
            "owner_input_read_count": artifact.get("owner_input_read_count"),
            "same_object_used_for_argv_and_observation": True,
            "verifier_parser": "same_object_invocation_and_plan",
            "commandExecution_id": artifact["ordinary_command_event"]["commandExecution_id"],
            "thread_id": artifact["ordinary_command_event"]["thread_id"],
            "turn_id": artifact["ordinary_command_event"]["turn_id"],
            "turn_index": artifact["ordinary_command_event"]["turn_index"],
            "item_index": artifact["ordinary_command_event"]["item_index"],
            "ordinary_commandExecution_output_proven": True,
        } if artifact else None),
        "contract_revision": contract.get("revision"),
        "source_status": observation.get("status"),
        "source": observation.get("source"),
        "schema": observation.get("schema"),
        "detail": ("Synthetic output is bound to an actual Codex commandExecution event; formal PC68-R1 association and runtime values remain unproven."
                   if source_supported and capture_supported else
                   "Observation source or synthetic capture preflight is not fully installed."),
    }


def check_entry_uniqueness(argv0=None):
    invoked = Path(argv0 if argv0 is not None else sys.argv[0]).resolve()
    if invoked != Path(__file__).resolve():
        raise ValueError("entrypoint_uniqueness_violated")
    return True


def pin():
    return bridge.pin_base_runner()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--producer-sha", required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--fixture-sha", required=True)
    parser.add_argument("--eval-direnv-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    args.producer_root = args.producer_root.resolve()
    args.fixture_root = args.fixture_root.resolve()
    args.eval_direnv_root = args.eval_direnv_root.resolve()
    return args


def overlaps(left, right):
    left, right = Path(left).resolve(), Path(right).resolve()
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def resolve_eval_port(eval_root):
    """Resolve the listening eval service port.

    Per the r20 Project Consensus, EVAL_PORT has exactly one formal source:
    ``direnv exec <eval_root> printenv EVAL_PORT``. When direnv is missing the
    Executable precondition is unsatisfied and the entry refuses to start;
    the same holds when direnv runs but its output is not a decimal port in
    1-65535. There is no listener-scan fallback; the resolved port is only
    re-verified against the listening process by ``capture_service_instance``
    when the provenance is recorded.
    """
    try:
        port = subprocess.check_output(
            ["direnv", "exec", str(eval_root), "printenv", "EVAL_PORT"],
            cwd=eval_root,
            text=True,
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("eval_port_unavailable") from exc
    if port.isdecimal() and 1 <= int(port) <= 65535:
        return port
    raise ValueError("eval_port_unavailable")


def capture_service_instance(eval_root, port):
    raw_pids = subprocess.check_output(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fp"],
        text=True,
    )
    pids = sorted({line[1:] for line in raw_pids.splitlines() if line.startswith("p") and line[1:].isdigit()})
    if len(pids) != 1:
        raise ValueError("eval_service_listener_not_unique")
    pid = pids[0]

    raw_cwd = subprocess.check_output(
        ["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"],
        text=True,
    )
    cwd_rows = [line[1:] for line in raw_cwd.splitlines() if line.startswith("n") and line[1:]]
    if len(cwd_rows) != 1:
        raise ValueError("eval_service_cwd_unobservable")
    cwd = Path(cwd_rows[0]).resolve()
    if cwd != Path(eval_root).resolve():
        raise ValueError("eval_service_cwd_mismatch")

    start_time = subprocess.check_output(["ps", "-p", pid, "-o", "lstart="], text=True).strip()
    command = subprocess.check_output(["ps", "-p", pid, "-o", "command="], text=True).strip()
    if not start_time or not command:
        raise ValueError("eval_service_process_unobservable")
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise ValueError("eval_service_command_malformed") from exc
    if not any(Path(token).name == "eval_server.py" for token in tokens):
        raise ValueError("eval_service_command_mismatch")
    has_port = any(token == f"--port={port}" for token in tokens)
    has_port = has_port or any(
        tokens[index] == "--port" and tokens[index + 1] == port
        for index in range(len(tokens) - 1)
    )
    if not has_port:
        raise ValueError("eval_service_port_mismatch")

    return {
        "port": port,
        "pid": int(pid),
        "start_time": start_time,
        "command": command,
        "cwd": str(cwd),
    }


def capture_eval_service_provenance(eval_root, expected_revision=None):
    """Read and validate the current clean service revision, then inspect it read-only."""
    if expected_revision is None:
        expected_revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=eval_root, text=True
        ).strip()
    if not expected_revision:
        raise ValueError("eval_service_version_unobservable")
    revision = base.clean_revision(eval_root, expected_revision)
    port = resolve_eval_port(eval_root)
    service = capture_service_instance(eval_root, port)
    storage = isolation.capture_storage_isolation(service)
    return {"eval_server": revision, "service": service, "storage": storage}


def _sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _request_model(request):
    command = request.get("command")
    if not isinstance(command, str):
        raise ValueError("codex_request_command_unobservable")
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise ValueError("codex_request_command_malformed") from exc
    models = [argv[index + 1] for index, token in enumerate(argv[:-1]) if token == "--model"]
    if len(models) != 1 or not models[0].strip():
        raise ValueError("codex_request_model_unobservable")
    return models[0]


def _record_request_runtime_facts(preflight, output, request, service_snapshot, producer, fixture):
    codex_dir = Path(output) / "codex"
    request_path = codex_dir / "codex-request.json"
    install_path = codex_dir / "installed-entrypoint.json"
    lock_path = codex_dir / "apm.lock.yaml"
    for path in (request_path, install_path, lock_path):
        if not path.is_file():
            raise ValueError("runtime_source_artifact_missing:" + path.name)

    request_model = _request_model(request)
    install = json.loads(install_path.read_text(encoding="utf-8"))
    script = Path(install.get("script", "")).resolve()
    if not script.is_file() or script.is_symlink():
        raise ValueError("installed_entrypoint_unobservable")
    entrypoint = {
        "script": str(script),
        "sha256": _sha256_file(script),
        "cwd": install.get("cwd"),
    }
    if not _is_recorded(entrypoint["cwd"]):
        raise ValueError("installed_entrypoint_cwd_unobservable")
    shared_assets = {
        "producer_revision": producer["sha"],
        "fixture_revision": fixture["sha"],
        "apm_lock_sha256": _sha256_file(lock_path),
    }

    service_sha = service_snapshot.get("eval_server", {}).get("sha")
    before_path = Path(output) / "eval-service-provenance.before.json"
    if not before_path.is_file() or not _is_recorded(service_sha):
        raise ValueError("service_provenance_source_missing")

    updated = _record_codex_executor_fact(preflight)
    updated = _register_runtime_fact(
        updated, "model", request_model, ["codex/codex-request.json"],
        sha256=_sha256_file(request_path), collection="actual built Codex request",
    )
    updated = _register_runtime_fact(
        updated, "entrypoint", entrypoint,
        ["codex/installed-entrypoint.json", str(script)],
        installed_entrypoint_sha256=_sha256_file(install_path),
        collection="installed entrypoint and file bytes",
    )
    updated = _register_runtime_fact(
        updated, "shared_assets", shared_assets,
        ["provenance.json", "codex/apm.lock.yaml"],
        apm_lock_sha256=shared_assets["apm_lock_sha256"],
        collection="clean producer/fixture revisions and installed lockfile",
    )
    missing = _runtime_environment_missing(updated["runtime_environment_facts"])
    if missing:
        raise ValueError("runtime_environment_unrecorded:" + ",".join(missing))
    if updated.get("service_preflight_allowed") is not True:
        raise ValueError("second_gate_incomplete")
    updated["formal_run_allowed"] = True
    updated["request_artifact"] = {
        "path": "codex/codex-request.json",
        "sha256": _sha256_file(request_path),
    }
    updated["runtime_environment_evidence"]["isolation"] = {
        **updated["runtime_environment_evidence"]["isolation"],
        "sha256": _sha256_file(before_path),
    }
    updated["runtime_environment_evidence"]["service_version"] = {
        **updated["runtime_environment_evidence"]["service_version"],
        "sha256": _sha256_file(before_path),
    }
    return updated


def _codex_host_with_runtime_capture(args, output, preflight, provenance,
                                     service_snapshot, producer, fixture):
    """Capture all six r25 runtime facts from this run before the request is sent."""
    original_build_request = base.build_request
    original_urlopen = base.urllib.request.urlopen
    original_install_host = base.install_host
    original_verify_codex = base.verify_codex
    request_path = Path(output) / "codex" / "codex-request.json"
    evidence_path = Path(output) / "runtime-environment-evidence.json"
    request_built = False
    lifecycle_context = {}

    def install_host_with_capture(*install_args, **install_kwargs):
        directory, consumer, manifest = original_install_host(*install_args, **install_kwargs)
        if install_args[2] != "codex":
            return directory, consumer, manifest
        source = input_verifier.OWNER_CAPTURE_SOURCE
        source_sha = _sha256_file(source)
        if source_sha != input_verifier.OWNER_CAPTURE_SHA256:
            raise ValueError("owner_capture_source_hash_mismatch")
        runtime_dir = consumer / ".pc68-test-support"
        runtime_dir.mkdir()
        runtime_script = runtime_dir / input_verifier.OWNER_CAPTURE_NAME
        shutil.copy2(source, runtime_script)
        entrypoint = base.installed_script(consumer).resolve()
        if entrypoint.is_symlink() or not entrypoint.is_file():
            raise ValueError("owner_capture_installed_entrypoint_invalid")
        manifest_path = directory / "fixture-manifest.json"
        capture_record = {
            "consumer_root": str(consumer.resolve()),
            "runtime_path": str(runtime_script.resolve()),
            "installed_entrypoint": str(entrypoint),
            "entrypoint_sha256": _sha256_file(entrypoint),
            "source_path": str(source.resolve()),
            "source_sha256": source_sha,
            "runtime_sha256": _sha256_file(runtime_script),
            "manifest_path": str(manifest_path.resolve()),
        }
        manifest["owner_capture"] = capture_record
        lifecycle_context.update(directory=directory, consumer=consumer, manifest=manifest)
        base.write_json(manifest_path, manifest)
        prompt_path = directory / "root-prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        prompt = prompt.replace("{{CAPTURE_SCRIPT}}", str(runtime_script.resolve()))
        prompt = prompt.replace("{{CONTACT_STATE}}", str(entrypoint))
        if "{{CAPTURE_SCRIPT}}" in prompt or "{{CONTACT_STATE}}" in prompt:
            raise ValueError("owner_capture_prompt_binding_failed")
        prompt_path.write_text(prompt, encoding="utf-8")
        return directory, consumer, manifest

    def build_request_with_evidence(consumer, prompt):
        nonlocal request_built
        request = original_build_request(consumer, prompt)
        base.write_json(request_path, request)
        updated = _record_request_runtime_facts(
            preflight, output, request, service_snapshot, producer, fixture
        )
        evidence = {
            "schema": "issue-68-r29-runtime-environment-evidence-v1",
            "runtime_environment_facts": updated["runtime_environment_facts"],
            "runtime_environment_evidence": updated["runtime_environment_evidence"],
            "request_artifact": updated["request_artifact"],
            "service_snapshot_artifact": "eval-service-provenance.before.json",
        }
        base.write_json(evidence_path, evidence)
        preflight.clear()
        preflight.update(updated)
        base.write_json(Path(output) / "input-evidence-preflight.json", preflight)
        provenance["runtime_environment_facts"] = preflight["runtime_environment_facts"]
        provenance["runtime_environment_evidence"] = preflight["runtime_environment_evidence"]
        provenance["runtime_environment_evidence_artifact"] = "runtime-environment-evidence.json"
        base.write_json(Path(output) / "provenance.json", provenance)
        request_built = True
        return request

    def verify_outgoing_request(request, timeout=None):
        if not request_built:
            raise ValueError("runtime_environment_not_recorded_before_request")
        try:
            sent = json.loads(request.data.decode("utf-8"))
            saved = json.loads(request_path.read_text(encoding="utf-8"))
        except (AttributeError, UnicodeError, ValueError, OSError) as exc:
            raise ValueError("outgoing_request_evidence_unreadable") from exc
        if sent != saved:
            raise ValueError("outgoing_request_changed_after_capture")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["outgoing_request_body_sha256"] = hashlib.sha256(request.data).hexdigest()
        base.write_json(evidence_path, evidence)
        preflight["request_body_sha256"] = evidence["outgoing_request_body_sha256"]
        base.write_json(Path(output) / "input-evidence-preflight.json", preflight)
        provenance["request_body_sha256"] = evidence["outgoing_request_body_sha256"]
        base.write_json(Path(output) / "provenance.json", provenance)
        # Last read-only snapshot before the one actual request. The support
        # script and installed consumer already exist at this boundary.
        before = lifecycle.collect_before(lifecycle_context["manifest"], lifecycle_context["consumer"])
        lifecycle.bind_before(before, saved)
        lifecycle_context["before"] = before
        base.write_json(lifecycle_context["directory"] / "lifecycle.before.json", before)
        return original_urlopen(request, timeout=timeout)

    def verify_with_lifecycle(response, adapter, manifest):
        evidence = lifecycle.collect_lifecycle(
            lifecycle_context["before"], manifest, lifecycle_context["consumer"],
            response, input_verifier)
        manifest["lifecycle_boundary"] = {
            "run_id": evidence["before"]["request_boundary"]["run_id"],
            "request_artifact": str(request_path),
            "before_artifact": str(lifecycle_context["directory"] / "lifecycle.before.json"),
            "before_sha256": lifecycle._response_digest(evidence["before"]),
            "after_sha256": lifecycle._response_digest(evidence["after"]),
        }
        base.write_json(lifecycle_context["directory"] / "lifecycle-evidence.json", evidence)
        manifest["lifecycle_evidence"] = evidence
        base.write_json(lifecycle_context["directory"] / "fixture-manifest.json", manifest)
        lifecycle_context["collected"] = True
        return original_verify_codex(response, adapter, manifest)

    base.build_request = build_request_with_evidence
    base.urllib.request.urlopen = verify_outgoing_request
    base.install_host = install_host_with_capture
    base.verify_codex = verify_with_lifecycle
    try:
        return base.codex_host(args, output)
    finally:
        try:
            if "before" in lifecycle_context and not lifecycle_context.get("collected"):
                response_path = lifecycle_context["directory"] / "codex-response.json"
                try:
                    response = json.loads(response_path.read_text()) if response_path.is_file() else {}
                except (OSError, ValueError):
                    response = {}
                evidence = lifecycle.collect_lifecycle(
                    lifecycle_context["before"], lifecycle_context["manifest"],
                    lifecycle_context["consumer"], response, input_verifier)
                base.write_json(lifecycle_context["directory"] / "lifecycle-evidence.json", evidence)
        finally:
            base.build_request = original_build_request
            base.urllib.request.urlopen = original_urlopen
            base.install_host = original_install_host
            base.verify_codex = original_verify_codex


def same_service(before, after):
    return (
        before.get("eval_server") == after.get("eval_server")
        and before.get("service", {}).get("port") == after.get("service", {}).get("port")
        and before.get("service", {}).get("pid") == after.get("service", {}).get("pid")
        and before.get("service", {}).get("start_time") == after.get("service", {}).get("start_time")
        and before.get("service", {}).get("cwd") == after.get("service", {}).get("cwd")
        and before.get("service", {}).get("command") == after.get("service", {}).get("command")
        and before.get("storage") == after.get("storage")
    )


def main(argv=None):
    pin()
    args = parse_args(argv)
    output = args.output_dir.resolve()
    result = {"state": "CASE_NOT_STARTED", "reason_code": "bootstrap_failed"}
    if output.exists() and any(output.iterdir()):
        print(json.dumps({"state": "CASE_NOT_STARTED", "reason_code": "output_directory_not_empty"}))
        return 2
    output.mkdir(parents=True, exist_ok=True)
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, base.stop_active)
    try:
        for source in (args.producer_root, args.fixture_root, args.eval_direnv_root):
            if overlaps(output, source):
                raise ValueError("output_must_be_outside_source_roots")
        check_entry_uniqueness()
        contract = load_contract()
        input_preflight = actual_input_observation_preflight(contract)
        base.write_json(output / "input-evidence-preflight.json", input_preflight)
        if not input_preflight["ready"]:
            raise ValueError(input_preflight["reason_code"])
        if not input_preflight["service_preflight_allowed"]:
            raise ValueError(input_preflight["formal_run_block_reason"])
        if args.fixture_sha != FIXTURE_SHA:
            raise ValueError("missing_or_wrong_frozen_fixture_arguments")
        if args.producer_sha != contract["producer_revision"]:
            raise ValueError("missing_or_wrong_frozen_producer_arguments")

        producer = base.clean_revision(args.producer_root, args.producer_sha)
        fixture = base.clean_revision(args.fixture_root, FIXTURE_SHA)
        service_before = capture_eval_service_provenance(args.eval_direnv_root)
        base.write_json(output / "eval-service-provenance.before.json", service_before)
        input_preflight = _record_service_runtime_facts(input_preflight, service_before)
        base.write_json(output / "input-evidence-preflight.json", input_preflight)
        service_version = service_before["eval_server"]["sha"]
        provenance = {
            "producer": producer,
            "fixture": fixture,
            "eval_server": service_before["eval_server"],
            "eval_service_before": service_before["service"],
            "eval_storage_before": service_before["storage"],
            "manual_patch": "no",
            "execution_kind": EXECUTION_KIND,
            "case": CASE,
            "host": HOST,
            "entrypoint": Path(__file__).name,
            "single_request_no_retry": "yes",
            "contract_revision": contract["revision"],
            "runtime_environment_facts": input_preflight["runtime_environment_facts"],
            "runtime_environment_evidence": input_preflight["runtime_environment_evidence"],
        }
        base.write_json(output / "provenance.json", provenance)

        base.progress("只执行 Codex；服务来源和隔离已归档；单次正式请求，失败不重试、不换服务、不换模型、不改断言")
        host = _codex_host_with_runtime_capture(
            args, output, input_preflight, provenance, service_before, producer, fixture
        )
        base.write_json(output / "codex-verdict.json", host)

        service_after = capture_eval_service_provenance(
            args.eval_direnv_root, service_version
        )
        base.write_json(output / "eval-service-provenance.after.json", service_after)
        if not same_service(service_before, service_after):
            result = base.verdict(
                "INVALID_TEST_EXECUTION",
                "eval_service_changed_during_execution",
                before=service_before,
                after=service_after,
            )
        else:
            result = host

        base.clean_revision(args.producer_root, args.producer_sha)
        base.clean_revision(args.fixture_root, FIXTURE_SHA)
        base.clean_revision(args.eval_direnv_root, service_version)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result = (
            {"state": "CASE_NOT_STARTED", "reason_code": str(exc)}
            if not base.started_evidence(output)
            else base.verdict("INVALID_TEST_EXECUTION", "revision_or_execution_changed", detail=str(exc))
        )
    except SystemExit as exc:
        result = (
            base.verdict("INVALID_TEST_EXECUTION", "execution_cancelled", exit_code=exc.code)
            if base.started_evidence(output)
            else {"state": "CASE_NOT_STARTED", "reason_code": "bootstrap_cancelled"}
        )
    finally:
        base.stop_active()
        base.write_json(output / "final-verdict.json", result)
    base.progress("结束：" + (result.get("verdict") or result.get("state", "UNKNOWN")))
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
