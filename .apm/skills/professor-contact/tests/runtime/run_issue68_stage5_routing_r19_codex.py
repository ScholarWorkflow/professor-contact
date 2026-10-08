#!/usr/bin/env python3
"""PC68-R1 Codex entrypoint with the r25 per-call observation gate."""
import argparse
import hashlib
import json
import os
import shlex
import signal
import shutil
import subprocess
import sys
import tempfile
import tomllib
from functools import lru_cache
from pathlib import Path

import issue68_eval_service_isolation_r14 as isolation
import run_issue68_stage5_routing as base
import run_issue68_stage5_routing_r19 as bridge
import verify_issue68_stage5_routing_r19 as input_verifier
import bind_issue68_preflight_command_event_r29 as command_event_binder
import issue68_lifecycle as lifecycle
import issue68_transfer_location as transfer_location


HERE = Path(__file__).resolve().parent
FIXTURE_SHA = bridge.FIXTURE_SHA
PRODUCER_REVISION = "faab365d0be2bb66f2f285fdaa2927631dbf33f8"
CONTRACT = HERE / "issue68-runtime-evidence-contract-r19.json"
CONTRACT_REVISION = "issue-68-runtime-evidence-r37-2026-10-08"
UV_CACHE_DIR_NAME = "uv-cache"
UV_CACHE_PROMPT_PLACEHOLDER = "{{UV_CACHE_DIR}}"
UV_CACHE_BINDING_SCHEMA = "issue-68-uv-cache-binding-r37-v1"
OWNER_OBSERVATION_SCHEMA = "issue-68-test-plan-r25-owner-input-v2"
SYNTHETIC_PREFLIGHT_SCHEMA = "issue-68-r29-fixed-capture-preflight-v2"
HISTORICAL_R29_CAPTURE_SCHEMA = "issue-68-test-plan-r25-fixed-owner-capture-v1"
HISTORICAL_R29_CAPTURE_SHA256 = "7e534f76b7ba837a415b9b9a38ecda4a0fb1fe62fbf6d5b2575119319ff4eaa9"
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
    "codex/project-approval-config-setup.json",
    "codex/project-approval-config-install-check.json",
    "codex/effective-project-approval-configuration.json",
    "codex/uv-cache-binding.json",
    "eval-service-provenance.before.json",
    "eval-service-provenance.after.json",
    "runtime-environment-evidence.json",
)
PROJECT_CONFIG_SOURCE_COMMIT = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
PROJECT_CONFIG_SOURCE_DOCUMENT = "docs/codex-opencode-smoke-wiring.md"
PROJECT_CONFIG_SOURCE_DOCUMENT_SHA256 = "3388463b78473039f6497a9b2a5d564dd54443d7f5254dc35e3e1deb9d5f1955"
PROJECT_CONFIG_HELPER_SHA256 = "4bd798a8c29ae93e1c65a261d85b21302422a4a7b0089ec6c62a974d5b6f9032"
PROJECT_CONFIG_VALUES = {
    "approval_policy": "on-request",
    "approvals_reviewer": "auto_review",
}


def load_contract():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("revision") != CONTRACT_REVISION:
        raise ValueError("contract_revision_mismatch")
    uv_cache_policy = contract.get("uv_cache_policy")
    if (not isinstance(uv_cache_policy, dict)
            or uv_cache_policy.get("schema") != UV_CACHE_BINDING_SCHEMA
            or uv_cache_policy.get("directory") != f"PC68_OUTPUT_ROOT/{UV_CACHE_DIR_NAME}"
            or uv_cache_policy.get("manifest_key") != "uv_cache_dir"
            or uv_cache_policy.get("root_prompt_placeholder") != UV_CACHE_PROMPT_PLACEHOLDER
            or uv_cache_policy.get("binding_artifact") != "codex/uv-cache-binding.json"
            or "HTTP" not in uv_cache_policy.get("environment_boundary", "")):
        raise ValueError("contract_uv_cache_policy_mismatch")
    if contract.get("fixture_sha") != FIXTURE_SHA:
        raise ValueError("contract_fixture_mismatch")
    environment = contract.get("formal_runtime_environment")
    fixed_inputs = environment.get("fixed_plan_inputs", {}) if isinstance(environment, dict) else {}
    if fixed_inputs.get("producer_revision") != PRODUCER_REVISION:
        raise ValueError("contract_fixed_producer_revision_mismatch")
    if fixed_inputs.get("shared_environment_revision") != FIXTURE_SHA:
        raise ValueError("contract_shared_environment_revision_mismatch")
    approval_config = contract.get("project_approval_configuration")
    if (not isinstance(approval_config, dict)
            or approval_config.get("preparation_status") != "SUPPORTED_SHARED_HELPER"
            or approval_config.get("helper_path") != "scripts/prepare_codex_project_config.py"
            or approval_config.get("helper_revision") != FIXTURE_SHA
            or approval_config.get("helper_sha256") != PROJECT_CONFIG_HELPER_SHA256
            or approval_config.get("normative_source") != {
                "commit": PROJECT_CONFIG_SOURCE_COMMIT,
                "document": PROJECT_CONFIG_SOURCE_DOCUMENT,
                "sha256": PROJECT_CONFIG_SOURCE_DOCUMENT_SHA256,
                "section": "7.7",
            }
            or approval_config.get("project_config_path") != ".codex/config.toml"
            or approval_config.get("values") != PROJECT_CONFIG_VALUES
            or approval_config.get("effective_value_source") != (
                "output.thread_start_effective.approvalPolicy and "
                "output.thread_start_effective.approvalsReviewer")
            or approval_config.get("trust_bootstrap") != (
                "The only project-scoped command-line override sets trust_level=trusted "
                "for the installed consumer.")
            or approval_config.get("approval_command_line_override") != "none"
            or "normal uv cache" not in approval_config.get("cache_policy", "")):
        raise ValueError("contract_project_approval_configuration_mismatch")
    if contract.get("producer_revision") != PRODUCER_REVISION:
        raise ValueError("contract_producer_revision_mismatch")
    historical_install = contract.get("preflight", {}).get("r31_install_retry_results", {})
    if (historical_install.get("record_scope") != "historical_r31_install_preflight_only"
            or historical_install.get("resolved_product_commit_is_historical") is not True):
        raise ValueError("historical_install_revision_not_marked")
    historical_environment = contract.get("preflight", {}).get(
        "r31_environment_preflight_attempts", {})
    if historical_environment.get("record_scope") != "historical_r31_environment_preflight_only":
        raise ValueError("historical_environment_preflight_scope_not_marked")
    capture_gate = contract.get("preflight", {}).get("input_observation_gate", {})
    if (capture_gate.get("saved_capture_record_scope") != "historical_r29_r25_capture_only"
            or capture_gate.get("current_cache_capture_schema") != input_verifier.OWNER_CAPTURE_SCHEMA
            or capture_gate.get("current_cache_capture_sha256") != input_verifier.OWNER_CAPTURE_SHA256):
        raise ValueError("contract_current_capture_preflight_not_pinned")
    if contract.get("runner") != CONTRACT_RUNNER:
        raise ValueError("contract_runner_is_not_this_entry")
    if contract.get("manual_patch") != "no":
        raise ValueError("contract_manual_patch_forbidden")
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


@lru_cache(maxsize=1)
def _current_r37_cache_capture_preflight():
    """Execute the current pinned capture wrapper with a disposable cache."""
    source = input_verifier.OWNER_CAPTURE_SOURCE
    if not source.is_file() or _sha256_file(source) != input_verifier.OWNER_CAPTURE_SHA256:
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "r37_capture_source_not_pinned"}
    cache_path = None
    proof = None
    try:
        with tempfile.TemporaryDirectory(prefix="pc68-r37-cache-capture-") as temporary:
            root = Path(temporary)
            program = root / "program"
            professor_dir = program / "教授研究" / "X分野" / "甲教授"
            professor_dir.mkdir(parents=True)
            email_pack = professor_dir / "邮件输入.json"
            template = program / "template.md"
            template.write_text("synthetic template", encoding="utf-8")
            email = {
                "email_id": "D001::I001", "professor": "甲教授",
                "professor_dir": str(professor_dir),
                "idea": {"id": "D001_1", "text": "合成研究构想"},
                "direction_ids": ["D001"],
                "directions": [{"id": "D001", "name": "合成方向"}],
                "user_note": "用户输入", "papers": [{"item_key": "P001", "title": "合成论文"}],
                "gaps": [], "red_lines": [{"text": "不得编造"}],
                "soft_materials": {"positioning": [{"text": "定位事实"}]},
                "user_supplement": "补充事实", "allowed_sources": ["idea:D001_1"],
            }
            pack = {"schema": 3, "kind": "professor-contact-email-input",
                    "professor": "甲教授", "professor_dir": str(professor_dir),
                    "emails": [email]}
            email_pack.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
            packet = {
                "program_root": str(program), "professor_dir": str(professor_dir),
                "email_pack": str(email_pack), "email_id": email["email_id"],
                "choices": [{"email_id": email["email_id"], "first_choice": True}],
                "mode": "first", "template": str(template),
                "result": str(program / "raw.json"),
            }
            owner_input = root / "owner-input.json"
            owner_input.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")

            consumer = root / "consumer"
            consumer.mkdir()
            entrypoint_source = source.parents[2] / "scripts" / "contact_state.py"
            if not entrypoint_source.is_file():
                return None, {"state": "INVALID_TEST_EXECUTION",
                              "reason_code": "r37_synthetic_entrypoint_missing"}
            entrypoint = consumer / ".agents" / "skills" / "professor-contact" / "scripts" / "contact_state.py"
            entrypoint.parent.mkdir(parents=True)
            shutil.copy2(entrypoint_source, entrypoint)
            entrypoint = entrypoint.resolve()
            runtime_path = consumer / ".pc68-test-support" / input_verifier.OWNER_CAPTURE_NAME
            runtime_path.parent.mkdir(parents=True)
            shutil.copy2(source, runtime_path)
            runtime_path = runtime_path.resolve()

            cache = root / UV_CACHE_DIR_NAME
            cache.mkdir(mode=0o700)
            cache_path = cache.resolve()
            if list(cache.iterdir()):
                return None, {"state": "INVALID_TEST_EXECUTION",
                              "reason_code": "r37_synthetic_cache_not_empty"}
            probe = cache / ".pc68-write-probe"
            probe.write_text("writable", encoding="utf-8")
            probe.unlink()

            argv = [
                "uv", "run", "--no-project", "python", str(runtime_path),
                "--action", "stage5-plan", "--owner-input-file", str(owner_input),
                "--contact-state", str(entrypoint),
            ]
            command = shlex.join([f"UV_CACHE_DIR={cache_path}", *argv])
            completed = subprocess.run(
                argv, cwd=consumer, capture_output=True, text=True, check=False,
                timeout=90, env={**os.environ, "UV_CACHE_DIR": str(cache_path)},
            )
            if completed.returncode != 0:
                return None, {"state": "INVALID_TEST_EXECUTION",
                              "reason_code": "r37_synthetic_capture_command_failed",
                              "exit_code": completed.returncode}
            envelope = json.loads(completed.stdout)
            capture = envelope.get("pc68_fixed_capture")
            if not isinstance(capture, dict) \
                    or capture.get("schema") != input_verifier.OWNER_CAPTURE_SCHEMA \
                    or capture.get("wrapper_sha256") != input_verifier.OWNER_CAPTURE_SHA256 \
                    or capture.get("uv_cache_dir") != str(cache_path):
                return None, {"state": "INVALID_TEST_EXECUTION",
                              "reason_code": "r37_synthetic_capture_cache_binding_invalid"}

            manifest_path = root / "manifest.json"
            manifest = {
                "program_root": str(program), "uv_cache_dir": str(cache_path),
                "owners": [{"professor": "甲教授", "professor_dir": str(professor_dir),
                            "email_pack": str(email_pack), "email_ids": [email["email_id"]],
                            "result": str(program / "raw.json"),
                            "expected_choices_rows": packet["choices"]}],
                "owner_capture": {
                    "consumer_root": str(consumer), "runtime_path": str(runtime_path),
                    "installed_entrypoint": str(entrypoint),
                    "entrypoint_sha256": _sha256_file(entrypoint),
                    "source_path": str(source),
                    "source_sha256": input_verifier.OWNER_CAPTURE_SHA256,
                    "runtime_sha256": _sha256_file(runtime_path),
                    "manifest_path": str(manifest_path),
                },
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            command_proof = input_verifier.command_action(command, manifest)
            call = {
                "id": "synthetic-r37-cache-capture", "thread": "synthetic-owner",
                "generation": "synthetic-r37", "start": 1, "end": 2,
                "command": command, "output": completed.stdout,
            }
            fixed_problem = input_verifier._validate_fixed_capture(
                call, envelope, command_proof["owner_capture"], packet, manifest)
            if fixed_problem:
                return None, {"state": "INVALID_TEST_EXECUTION",
                              "reason_code": "r37_synthetic_capture_verification_failed",
                              "detail": fixed_problem.get("reason_code")}
            proof = {
                "state": "PASS", "capture_schema": capture["schema"],
                "wrapper_sha256": capture["wrapper_sha256"],
                "uv_cache_dir": str(cache_path),
                "manifest_cache_path_matches": manifest["uv_cache_dir"] == str(cache_path),
                "command_cache_prefix_matches": command_proof.get("uv_cache_dir") == str(cache_path),
                "capture_field_matches_manifest": capture["uv_cache_dir"] == manifest["uv_cache_dir"],
                "fixed_capture_verifier": "verify_issue68_stage5_routing_r19._validate_fixed_capture",
                "formal_case_started": False, "eval_service_called": False,
                "external_request_made": False,
            }
    except subprocess.TimeoutExpired:
        return None, {"state": "INVALID_TEST_EXECUTION",
                      "reason_code": "r37_synthetic_capture_command_timeout"}
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return None, {"state": "INVALID_TEST_EXECUTION",
                      "reason_code": "r37_synthetic_capture_preflight_invalid",
                      "detail": str(exc)}
    if proof is None or cache_path is None or cache_path.exists():
        return None, {"state": "INVALID_TEST_EXECUTION",
                      "reason_code": "r37_synthetic_capture_cleanup_unconfirmed"}
    proof["temporary_cache_removed"] = True
    return proof, None


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
    owner_capture_record = manifest.get("owner_capture", {})
    source_sha = owner_capture_record.get("source_sha256")
    if source_sha not in (HISTORICAL_R29_CAPTURE_SHA256, input_verifier.OWNER_CAPTURE_SHA256):
        return None, {"state": "INVALID_TEST_EXECUTION", "reason_code": "synthetic_capture_source_revision_unrecognized"}
    if artifact.get("fixed_capture_verification") != {
            "state": "PASS", "verifier": "same_object_invocation_and_plan",
            "wrapper_sha256": source_sha,
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
    expected_capture_schema = (HISTORICAL_R29_CAPTURE_SCHEMA
                               if source_sha == HISTORICAL_R29_CAPTURE_SHA256
                               else input_verifier.OWNER_CAPTURE_SCHEMA)
    if not isinstance(command_proof, dict) or not isinstance(command_proof.get("owner_capture"), dict) \
            or capture.get("schema") != expected_capture_schema \
            or capture.get("wrapper_sha256") != source_sha \
            or capture.get("owner_input_read_count") != 1 \
            or capture.get("parsed_object_sha256") != artifact.get("parsed_object_sha256") \
            or manifest.get("uv_cache_dir") is not None \
            or (source_sha == HISTORICAL_R29_CAPTURE_SHA256
                and capture.get("uv_cache_dir") is not None) \
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
    verified = dict(artifact)
    verified["_r29_capture_record_scope"] = (
        "historical_r29_r25_capture_only"
        if source_sha == HISTORICAL_R29_CAPTURE_SHA256
        else "synthetic_r29_command_event_only_without_cache_proof"
    )
    verified["_r29_capture_schema"] = capture.get("schema")
    verified["_r29_capture_sha256"] = source_sha
    verified["_r29_capture_uv_cache_dir"] = capture.get("uv_cache_dir")
    return verified, None


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
    current_capture, current_capture_problem = (None, None)
    if artifact is not None and capture_problem is None:
        current_capture, current_capture_problem = _current_r37_cache_capture_preflight()
        if current_capture_problem is not None:
            capture_problem = current_capture_problem
    capture_supported = (artifact is not None and capture_problem is None
                         and current_capture is not None)
    technical_preflight_ready = source_supported and capture_supported
    runtime_values = {key: None for key in REQUIRED_RUNTIME_FACTS}
    missing_runtime_values = list(REQUIRED_RUNTIME_FACTS)
    block_reasons = []
    if not source_supported:
        block_reasons.append("actual_input_evidence_source_unavailable")
    if not capture_supported:
        block_reasons.append((capture_problem or {}).get("reason_code", "synthetic_capture_preflight_missing"))
    return {
        "ready": source_supported and capture_supported,
        "state": ("OBSERVATION_SOURCE_SUPPORTED" if source_supported and capture_supported else
                  ((capture_problem or {}).get("state", "CASE_NOT_STARTED") if not capture_supported else
                   "BLOCKED_OBSERVABILITY")),
        "reason_code": (None if source_supported and capture_supported else
                        ((capture_problem or {}).get("reason_code") if not capture_supported
                         else "actual_input_evidence_source_unavailable")),
        "technical_preflight_ready": technical_preflight_ready,
        "technical_preflight_block_reasons": block_reasons,
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
            "historical_capture_record_scope": artifact["_r29_capture_record_scope"],
            "historical_capture_schema": artifact["_r29_capture_schema"],
            "historical_capture_sha256": artifact["_r29_capture_sha256"],
            "historical_capture_uv_cache_dir": artifact["_r29_capture_uv_cache_dir"],
            "r37_cache_capture_verification": current_capture,
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
    parser.add_argument("--transfer-location-root", type=Path, required=True)
    args = parser.parse_args(argv)
    args.producer_root = args.producer_root.resolve()
    args.fixture_root = args.fixture_root.resolve()
    args.eval_direnv_root = args.eval_direnv_root.resolve()
    return args


def overlaps(left, right):
    left, right = Path(left).resolve(), Path(right).resolve()
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _prepare_run_uv_cache(output):
    """Create and prove the empty request-local cache directory before setup."""
    output = Path(output).resolve()
    if output.is_symlink() or not output.is_dir():
        raise ValueError("uv_cache_output_directory_invalid")
    cache = output / UV_CACHE_DIR_NAME
    try:
        cache.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError as exc:
        raise ValueError("uv_cache_directory_already_exists") from exc
    if cache.is_symlink() or not cache.is_dir() or list(cache.iterdir()):
        raise ValueError("uv_cache_directory_not_fresh_and_empty")
    probe = cache / ".pc68-write-probe"
    try:
        with probe.open("x", encoding="utf-8") as stream:
            stream.write("writable")
        probe.unlink()
    except OSError as exc:
        raise ValueError("uv_cache_directory_not_writable") from exc
    return cache.resolve()


def _bind_uv_cache_prompt(manifest, prompt, cache_path):
    """Bind the run cache to its manifest and every prompt placeholder."""
    cache = Path(cache_path)
    if cache.is_symlink() or not cache.is_dir():
        raise ValueError("uv_cache_directory_invalid")
    cache = cache.resolve()
    if not cache.is_absolute():
        raise ValueError("uv_cache_directory_not_absolute")
    bound = str(cache)
    recorded = manifest.get("uv_cache_dir")
    if recorded not in (None, bound):
        raise ValueError("uv_cache_manifest_binding_mismatch")
    if not isinstance(prompt, str) or UV_CACHE_PROMPT_PLACEHOLDER not in prompt:
        raise ValueError("uv_cache_prompt_placeholder_missing")
    manifest["uv_cache_dir"] = bound
    bound_prompt = prompt.replace(UV_CACHE_PROMPT_PLACEHOLDER, bound)
    if UV_CACHE_PROMPT_PLACEHOLDER in bound_prompt:
        raise ValueError("uv_cache_prompt_binding_incomplete")
    return bound_prompt


def _validate_uv_cache_request(request, prompt, cache_path):
    """Prove that the HTTP request itself carries the bound prompt/path."""
    command = request.get("command") if isinstance(request, dict) else None
    if not isinstance(command, str):
        raise ValueError("uv_cache_request_command_missing")
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise ValueError("uv_cache_request_command_invalid") from exc
    cache_text = str(Path(cache_path).resolve())
    if (not argv or argv[-1] != prompt or cache_text not in prompt
            or UV_CACHE_PROMPT_PLACEHOLDER in command):
        raise ValueError("uv_cache_request_binding_mismatch")
    return argv


def _uv_cache_inventory(cache_path):
    """Summarize a cache tree without following or hashing its contents."""
    cache = Path(cache_path)
    if cache.is_symlink():
        raise ValueError("uv_cache_directory_replaced_by_symlink")
    if not cache.exists():
        return {"state": "ABSENT", "entry_count": 0, "file_count": 0,
                "directory_count": 0, "other_count": 0, "total_file_bytes": 0,
                "entries_sha256": hashlib.sha256(b"[]").hexdigest()}
    if not cache.is_dir():
        raise ValueError("uv_cache_path_not_directory")
    entries = []
    for path in sorted(cache.rglob("*"), key=lambda item: item.relative_to(cache).as_posix()):
        relative = path.relative_to(cache).as_posix()
        if path.is_symlink():
            entry = {"path": relative, "kind": "symlink"}
        elif path.is_dir():
            entry = {"path": relative, "kind": "directory"}
        elif path.is_file():
            entry = {"path": relative, "kind": "file", "size": path.stat().st_size}
        else:
            entry = {"path": relative, "kind": "other"}
        entries.append(entry)
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    files = [item for item in entries if item["kind"] == "file"]
    directories = [item for item in entries if item["kind"] == "directory"]
    other = [item for item in entries if item["kind"] in ("symlink", "other")]
    return {
        "state": "EMPTY" if not entries else "POPULATED",
        "entry_count": len(entries),
        "file_count": len(files),
        "directory_count": len(directories),
        "other_count": len(other),
        "total_file_bytes": sum(item.get("size", 0) for item in files),
        "entries_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _write_uv_cache_evidence(output, evidence):
    output = Path(output)
    directory = output / "codex"
    path = directory / "uv-cache-binding.json"
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError("uv_cache_evidence_directory_invalid")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("uv_cache_evidence_artifact_invalid")
    if not path.is_file():
        path = output / "uv-cache-binding.pending.json"
    base.write_json(path, evidence)
    return path


def _publish_uv_cache_evidence(output):
    output = Path(output)
    directory = output / "codex"
    pending = output / "uv-cache-binding.pending.json"
    target = directory / "uv-cache-binding.json"
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError("uv_cache_evidence_directory_invalid")
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError("uv_cache_evidence_artifact_invalid")
    if target.is_file():
        if pending.exists() or pending.is_symlink():
            raise ValueError("uv_cache_evidence_pending_and_published")
        return target
    if pending.is_symlink() or not pending.is_file():
        raise ValueError("uv_cache_evidence_pending_missing")
    directory.mkdir(exist_ok=True)
    pending.replace(target)
    return target


def _finalize_run_uv_cache(output, evidence):
    """Record the final cache inventory, remove only this run's directory, and prove absence."""
    output = Path(output).resolve()
    cache = Path(evidence["cache_dir"])
    expected = output / UV_CACHE_DIR_NAME
    result = dict(evidence)
    result["after_run"] = {"state": "UNAVAILABLE"}
    error = None
    deleted = False
    if cache != expected or cache.is_symlink():
        error = "uv_cache_cleanup_path_mismatch" if cache != expected else "uv_cache_directory_replaced_by_symlink"
    else:
        try:
            result["after_run"] = _uv_cache_inventory(cache)
            if cache.exists():
                shutil.rmtree(cache)
                deleted = True
        except (OSError, ValueError) as exc:
            error = str(exc)
    confirmed_absent = not cache.exists() and not cache.is_symlink()
    result["cleanup"] = {
        "attempted": True,
        "deleted": deleted,
        "confirmed_absent": confirmed_absent,
        "error": error,
    }
    _write_uv_cache_evidence(output, result)
    _publish_uv_cache_evidence(output)
    return result


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


def prepare_project_approval_configuration(consumer, fixture_root, evidence_path):
    """Use the pinned shared helper to create and verify project-scoped settings."""
    consumer = Path(consumer).resolve()
    fixture_root = Path(fixture_root).resolve()
    helper = fixture_root / "scripts" / "prepare_codex_project_config.py"
    if helper.is_symlink() or not helper.is_file():
        raise ValueError("project_approval_configuration_helper_missing")
    helper_sha256 = _sha256_file(helper)
    command = [
        "uv", "run", "--no-project", "python", str(helper),
        "--consumer-root", str(consumer),
    ]
    evidence = {
        "schema": "issue-68-project-approval-config-setup-v1",
        "status": "NOT_STARTED",
        "shared_assets_revision": FIXTURE_SHA,
        "helper": "scripts/prepare_codex_project_config.py",
        "helper_sha256": helper_sha256,
        "command_argv": command,
        "command_cwd": str(fixture_root),
        "requested_values": PROJECT_CONFIG_VALUES,
    }
    if helper_sha256 != PROJECT_CONFIG_HELPER_SHA256:
        evidence.update({"status": "SOURCE_MISMATCH"})
        base.write_json(evidence_path, evidence)
        raise ValueError("project_approval_configuration_helper_hash_mismatch")
    try:
        completed = subprocess.run(
            command, cwd=fixture_root, capture_output=True, text=True,
            timeout=120, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        evidence.update({"status": "FAILED", "error_type": type(exc).__name__})
        base.write_json(evidence_path, evidence)
        raise ValueError("project_approval_configuration_setup_failed") from exc
    evidence.update({
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    })
    if completed.returncode != 0:
        evidence["status"] = "FAILED"
        base.write_json(evidence_path, evidence)
        raise ValueError("project_approval_configuration_setup_failed")
    try:
        helper_result = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        evidence["status"] = "INVALID_HELPER_OUTPUT"
        base.write_json(evidence_path, evidence)
        raise ValueError("project_approval_configuration_helper_output_invalid") from exc
    expected_source = {
        "commit": PROJECT_CONFIG_SOURCE_COMMIT,
        "document": PROJECT_CONFIG_SOURCE_DOCUMENT,
        "sha256": PROJECT_CONFIG_SOURCE_DOCUMENT_SHA256,
    }
    if (not isinstance(helper_result, dict)
            or not isinstance(helper_result.get("project_config"), dict)
            or helper_result.get("schema") != 1
            or helper_result.get("status") != "PREPARED"
            or helper_result.get("source") != expected_source
            or helper_result["project_config"].get("values") != PROJECT_CONFIG_VALUES):
        evidence.update({"status": "INVALID_HELPER_OUTPUT", "helper_result": helper_result})
        base.write_json(evidence_path, evidence)
        raise ValueError("project_approval_configuration_helper_output_invalid")
    config_path = consumer / ".codex" / "config.toml"
    try:
        config_resolved = config_path.resolve(strict=True)
        config_bytes = config_resolved.read_bytes()
    except OSError as exc:
        evidence.update({"status": "INVALID_HELPER_OUTPUT", "helper_result": helper_result})
        base.write_json(evidence_path, evidence)
        raise ValueError("project_approval_configuration_readback_missing") from exc
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    helper_config = helper_result.get("project_config", {})
    if (str(config_resolved) != helper_config.get("path")
            or config_sha256 != helper_config.get("sha256")):
        evidence.update({"status": "INVALID_HELPER_OUTPUT", "helper_result": helper_result})
        base.write_json(evidence_path, evidence)
        raise ValueError("project_approval_configuration_readback_mismatch")
    evidence.update({
        "status": "PREPARED",
        "source": expected_source,
        "project_config": {
            "path": str(config_resolved),
            "sha256": config_sha256,
            "values": PROJECT_CONFIG_VALUES,
        },
        "helper_result": helper_result,
    })
    base.write_json(evidence_path, evidence)
    return evidence


def _project_approval_configuration_facts(
    setup_evidence, artifact_path="codex/project-approval-config-setup.json"
):
    if not isinstance(setup_evidence, dict):
        setup_evidence = {}
    project_config = setup_evidence.get("project_config", {})
    if not isinstance(project_config, dict):
        project_config = {}
    return {
        "status": setup_evidence.get("status"),
        "shared_assets_revision": setup_evidence.get("shared_assets_revision"),
        "helper": setup_evidence.get("helper"),
        "helper_sha256": setup_evidence.get("helper_sha256"),
        "source": setup_evidence.get("source"),
        "project_config": {
            "path": project_config.get("path"),
            "sha256": project_config.get("sha256"),
            "values": project_config.get("values"),
        },
        "setup_evidence_artifact": artifact_path,
    }


def verify_project_approval_configuration_after_install(
    consumer, setup_evidence_path, evidence_path,
    setup_evidence_artifact="project-approval-config-setup.json",
):
    """Verify APM preserved the shared helper's project-scoped approval values."""
    consumer = Path(consumer).resolve()
    setup_evidence_path = Path(setup_evidence_path)
    evidence_path = Path(evidence_path)
    config_path = consumer / ".codex" / "config.toml"
    evidence = {
        "schema": "issue-68-project-approval-config-install-check-v1",
        "status": "INVALID_EVIDENCE",
        "reason_code": None,
        "setup_evidence_artifact": setup_evidence_artifact,
        "setup_evidence_sha256": None,
        "setup_status": None,
        "shared_assets_revision": None,
        "helper": None,
        "helper_sha256": None,
        "source": None,
        "configuration_path": str(config_path),
        "config_sha256_before_install": None,
        "config_sha256_after_install": None,
        "requested_values": dict(PROJECT_CONFIG_VALUES),
        "observed_values": {key: None for key in PROJECT_CONFIG_VALUES},
        "statuses": {key: "NOT_CHECKED" for key in PROJECT_CONFIG_VALUES},
    }

    def finish(status, reason_code=None):
        evidence["status"] = status
        evidence["reason_code"] = reason_code
        base.write_json(evidence_path, evidence)
        return evidence

    try:
        setup_bytes = setup_evidence_path.read_bytes()
        evidence["setup_evidence_sha256"] = hashlib.sha256(setup_bytes).hexdigest()
        setup = json.loads(setup_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return finish("INVALID_EVIDENCE", "project_approval_setup_evidence_unreadable")

    setup_config = setup.get("project_config") if isinstance(setup, dict) else None
    if not isinstance(setup_config, dict):
        return finish("INVALID_EVIDENCE", "project_approval_setup_evidence_invalid")
    evidence.update({
        "setup_status": setup.get("status"),
        "shared_assets_revision": setup.get("shared_assets_revision"),
        "helper": setup.get("helper"),
        "helper_sha256": setup.get("helper_sha256"),
        "source": setup.get("source"),
        "config_sha256_before_install": setup_config.get("sha256"),
    })

    try:
        if ((consumer / ".codex").is_symlink() or config_path.is_symlink()):
            return finish("INVALID_EVIDENCE", "project_approval_config_path_is_symlink")
        resolved_config = config_path.resolve(strict=True)
        config_bytes = resolved_config.read_bytes()
        parsed_config = tomllib.loads(config_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return finish("INVALID_EVIDENCE", "installed_project_approval_config_unreadable")

    evidence["configuration_path"] = str(resolved_config)
    evidence["config_sha256_after_install"] = hashlib.sha256(config_bytes).hexdigest()
    for key, expected_value in PROJECT_CONFIG_VALUES.items():
        if key not in parsed_config:
            evidence["statuses"][key] = "MISSING"
        elif parsed_config[key] != expected_value:
            evidence["statuses"][key] = "MISMATCH"
        else:
            evidence["statuses"][key] = "MATCH"
        evidence["observed_values"][key] = parsed_config.get(key)

    expected_source = {
        "commit": PROJECT_CONFIG_SOURCE_COMMIT,
        "document": PROJECT_CONFIG_SOURCE_DOCUMENT,
        "sha256": PROJECT_CONFIG_SOURCE_DOCUMENT_SHA256,
    }
    setup_path = setup_config.get("path")
    setup_sha = setup_config.get("sha256")
    setup_valid = (
        setup.get("status") == "PREPARED"
        and setup.get("shared_assets_revision") == FIXTURE_SHA
        and setup.get("helper") == "scripts/prepare_codex_project_config.py"
        and setup.get("helper_sha256") == PROJECT_CONFIG_HELPER_SHA256
        and setup.get("source") == expected_source
        and setup_config.get("values") == PROJECT_CONFIG_VALUES
        and isinstance(setup_path, str)
        and Path(setup_path) == resolved_config
        and isinstance(setup_sha, str)
        and len(setup_sha) == 64
        and all(char in "0123456789abcdef" for char in setup_sha)
    )
    if not setup_valid:
        return finish("INVALID_EVIDENCE", "project_approval_setup_evidence_mismatch")
    if not all(value == "MATCH" for value in evidence["statuses"].values()):
        return finish("NOT_PRESERVED", "project_approval_values_not_preserved")
    return finish("PRESERVED")


def require_project_approval_configuration_preserved(install_check):
    """Stop before request construction unless the installed file kept both keys."""
    if (not isinstance(install_check, dict)
            or install_check.get("status") != "PRESERVED"
            or install_check.get("requested_values") != PROJECT_CONFIG_VALUES
            or install_check.get("observed_values") != PROJECT_CONFIG_VALUES
            or any(status != "MATCH"
                   for status in install_check.get("statuses", {}).values())
            or not install_check.get("config_sha256_after_install")):
        raise ValueError("project_approval_configuration_not_preserved")
    return install_check


def _request_approval_configuration(response, effective):
    response_received = bool(response)
    statuses = {}
    values = {}
    paths = {
        "approval_policy": "output.thread_start_effective.approvalPolicy",
        "approvals_reviewer": "output.thread_start_effective.approvalsReviewer",
    }
    fields = {
        "approval_policy": "approvalPolicy",
        "approvals_reviewer": "approvalsReviewer",
    }
    for key, field in fields.items():
        if effective is None:
            statuses[key] = "NOT_EXPOSED_BY_CURRENT_SERVICE" if response_received else "NOT_OBSERVED_YET"
            values[key] = None
        elif not isinstance(effective, dict):
            statuses[key] = "INVALID_SERVICE_REPORTED_VALUE"
            values[key] = None
        elif field not in effective:
            statuses[key] = "NOT_EXPOSED_BY_CURRENT_SERVICE"
            values[key] = None
        else:
            value = effective[field]
            values[key] = value
            if not isinstance(value, str) or not value.strip():
                statuses[key] = "INVALID_SERVICE_REPORTED_VALUE"
            elif value != PROJECT_CONFIG_VALUES[key]:
                statuses[key] = "MISMATCH"
            else:
                statuses[key] = "MATCH"
    if all(statuses[key] == "MATCH" for key in fields):
        combined = "MATCH"
    elif "INVALID_SERVICE_REPORTED_VALUE" in statuses.values():
        combined = "INVALID_SERVICE_REPORTED_VALUE"
    elif "MISMATCH" in statuses.values():
        combined = "MISMATCH"
    elif not response_received:
        combined = "NOT_OBSERVED_YET"
    else:
        combined = "NOT_EXPOSED_BY_CURRENT_SERVICE"
    return {
        "source": "output.thread_start_effective",
        "values": values,
        "statuses": statuses,
        "field_paths": paths,
        "status": combined,
    }


def _formal_approval_configuration_record(response, setup_evidence,
                                         install_check_evidence=None):
    response_output = response.get("output") if isinstance(response, dict) else None
    effective = (response_output.get("thread_start_effective")
                 if isinstance(response_output, dict) else None)
    record = _request_approval_configuration(response, effective)
    setup_config = setup_evidence.get("project_config") if isinstance(setup_evidence, dict) else None
    setup_ok = (
        isinstance(setup_evidence, dict)
        and setup_evidence.get("status") == "PREPARED"
        and isinstance(setup_config, dict)
        and setup_config.get("values") == PROJECT_CONFIG_VALUES
    )
    install_check_ok = (
        isinstance(install_check_evidence, dict)
        and install_check_evidence.get("status") == "PRESERVED"
        and install_check_evidence.get("requested_values") == PROJECT_CONFIG_VALUES
        and install_check_evidence.get("observed_values") == PROJECT_CONFIG_VALUES
        and all(status == "MATCH" for status in
                install_check_evidence.get("statuses", {}).values())
    )
    record["effective_status"] = record["status"]
    record["setup_status"] = "PREPARED" if setup_ok else "INVALID_SETUP_EVIDENCE"
    record["install_preservation_status"] = (
        "PRESERVED" if install_check_ok else "INVALID_INSTALL_PRESERVATION_EVIDENCE")
    record["status"] = (
        record["effective_status"] if setup_ok and install_check_ok
        else "INVALID_SETUP_EVIDENCE" if not setup_ok
        else "INVALID_INSTALL_PRESERVATION_EVIDENCE")
    record["setup"] = _project_approval_configuration_facts(setup_evidence)
    record["install_preservation"] = {
        "status": install_check_evidence.get("status")
        if isinstance(install_check_evidence, dict) else None,
        "config_sha256_before_install": install_check_evidence.get(
            "config_sha256_before_install")
        if isinstance(install_check_evidence, dict) else None,
        "config_sha256_after_install": install_check_evidence.get(
            "config_sha256_after_install")
        if isinstance(install_check_evidence, dict) else None,
    }
    return record


def _constrain_with_formal_approval_configuration(result, approval_configuration):
    business_result = dict(result)
    result = {**business_result, "effective_approval_configuration": approval_configuration}
    if business_result.get("verdict") != "PASS" or approval_configuration.get("status") == "MATCH":
        return result

    status = approval_configuration.get("status")
    if status in ("NOT_OBSERVED_YET", "NOT_EXPOSED_BY_CURRENT_SERVICE"):
        verdict, reason = "BLOCKED_OBSERVABILITY", "effective_approval_configuration_unobservable"
    elif status == "MISMATCH":
        verdict, reason = "BLOCKED_DEPENDENCY", "effective_approval_configuration_mismatch"
    else:
        verdict, reason = "INVALID_EVIDENCE", "effective_approval_configuration_invalid"
    return {
        **result,
        "verdict": verdict,
        "reason_code": reason,
        "business_result": business_result,
    }


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
    approval_config_path = codex_dir / "project-approval-config-setup.json"
    approval_install_check_path = codex_dir / "project-approval-config-install-check.json"
    for path in (request_path, install_path, lock_path, approval_config_path,
                 approval_install_check_path):
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
    approval_setup = json.loads(approval_config_path.read_text(encoding="utf-8"))
    approval_install_check = json.loads(
        approval_install_check_path.read_text(encoding="utf-8"))
    if approval_setup.get("status") != "PREPARED":
        raise ValueError("project_approval_configuration_not_prepared")
    approval_configuration = _project_approval_configuration_facts(approval_setup)
    recorded_config_path_value = approval_configuration["project_config"].get("path")
    install_cwd = install.get("cwd")
    if not isinstance(recorded_config_path_value, str) or not isinstance(install_cwd, str):
        raise ValueError("project_approval_configuration_readback_mismatch")
    recorded_config_path = Path(recorded_config_path_value)
    try:
        config_path_matches = (
            not recorded_config_path.is_symlink()
            and recorded_config_path.resolve(strict=True)
            == (Path(install_cwd) / ".codex" / "config.toml").resolve(strict=True)
        )
    except OSError:
        config_path_matches = False
    if not config_path_matches:
        raise ValueError("project_approval_configuration_readback_mismatch")
    try:
        installed_config_bytes = recorded_config_path.read_bytes()
        installed_config = tomllib.loads(installed_config_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("project_approval_configuration_readback_mismatch") from exc
    installed_config_sha256 = hashlib.sha256(installed_config_bytes).hexdigest()
    if (approval_install_check.get("status") != "PRESERVED"
            or approval_install_check.get("configuration_path") != str(recorded_config_path.resolve())
            or approval_install_check.get("setup_evidence_sha256")
            != _sha256_file(approval_config_path)
            or approval_install_check.get("config_sha256_after_install")
            != installed_config_sha256
            or approval_install_check.get("requested_values") != PROJECT_CONFIG_VALUES
            or approval_install_check.get("observed_values") != PROJECT_CONFIG_VALUES
            or any(installed_config.get(key) != value
                   for key, value in PROJECT_CONFIG_VALUES.items())):
        raise ValueError("project_approval_configuration_not_preserved")
    if (approval_configuration["project_config"]["values"] != PROJECT_CONFIG_VALUES
            or approval_configuration["shared_assets_revision"] != fixture.get("sha")
            or approval_configuration["source"].get("commit") != PROJECT_CONFIG_SOURCE_COMMIT
            or approval_configuration["source"].get("sha256") != PROJECT_CONFIG_SOURCE_DOCUMENT_SHA256):
        raise ValueError("project_approval_configuration_source_mismatch")
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
    if updated.get("technical_preflight_ready") is not True:
        raise ValueError("technical_preflight_incomplete")
    updated["request_artifact"] = {
        "path": "codex/codex-request.json",
        "sha256": _sha256_file(request_path),
    }
    updated["project_approval_configuration"] = {
        **approval_configuration,
        "setup_evidence_sha256": _sha256_file(approval_config_path),
        "install_preservation": {
            "status": approval_install_check["status"],
            "artifact": "codex/project-approval-config-install-check.json",
            "sha256": _sha256_file(approval_install_check_path),
            "config_sha256_after_install": installed_config_sha256,
        },
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
    binding_path = Path(output) / "codex" / "transfer-location-binding.json"
    request_built = False
    lifecycle_context = {}
    location_context = {}

    def record_approval_configuration(response):
        directory = lifecycle_context["directory"]
        setup_path = directory / "project-approval-config-setup.json"
        install_check_path = directory / "project-approval-config-install-check.json"
        response_path = directory / "codex-response.json"
        record_path = directory / "effective-project-approval-configuration.json"
        try:
            setup_evidence = json.loads(setup_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            setup_evidence = {}
        try:
            install_check_evidence = json.loads(install_check_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            install_check_evidence = {}
        record = _formal_approval_configuration_record(
            response, setup_evidence, install_check_evidence)
        record.update({
            "schema": "issue-68-formal-approval-configuration-v1",
            "artifact": "codex/effective-project-approval-configuration.json",
            "response_artifact": "codex/codex-response.json",
            "response_sha256": _sha256_file(response_path) if response_path.is_file() else None,
            "setup_evidence_artifact": "codex/project-approval-config-setup.json",
            "setup_evidence_sha256": _sha256_file(setup_path) if setup_path.is_file() else None,
            "install_preservation_artifact": "codex/project-approval-config-install-check.json",
            "install_preservation_sha256": (
                _sha256_file(install_check_path) if install_check_path.is_file() else None),
        })
        base.write_json(record_path, record)
        return record

    def install_host_with_capture(*install_args, **install_kwargs):
        host = install_args[2]
        if host != "codex":
            return original_install_host(*install_args, **install_kwargs)

        def prepare_approval_config(consumer, directory):
            approval_setup = prepare_project_approval_configuration(
                consumer, args.fixture_root, directory / "project-approval-config-setup.json")
            lifecycle_context["approval_setup"] = approval_setup

        def verify_approval_config(consumer, directory):
            install_check = verify_project_approval_configuration_after_install(
                consumer,
                directory / "project-approval-config-setup.json",
                directory / "project-approval-config-install-check.json",
                "codex/project-approval-config-setup.json",
            )
            lifecycle_context["approval_install_check"] = (
                require_project_approval_configuration_preserved(install_check))

        directory, consumer, manifest = original_install_host(
            *install_args,
            before_codex_install=prepare_approval_config,
            after_codex_install=verify_approval_config,
            **install_kwargs,
        )
        _publish_uv_cache_evidence(output)
        program_root = manifest.get("program_root")
        if not isinstance(program_root, (str, Path)) or not str(program_root):
            raise ValueError("installed_program_root_missing")
        location_context["root"] = transfer_location.validate_location_root(
            args.transfer_location_root,
            {"consumer": consumer, "program": program_root, "evidence_output": output},
        )
        args.transfer_location_root = location_context["root"]
        approval_setup = lifecycle_context["approval_setup"]
        approval_install_check = lifecycle_context["approval_install_check"]
        base.archive_config(consumer, directory, "before")
        provenance["project_approval_configuration_setup"] = {
            **_project_approval_configuration_facts(approval_setup),
            "setup_evidence_sha256": _sha256_file(
                directory / "project-approval-config-setup.json"),
        }
        provenance["project_approval_configuration_install_check"] = {
            "artifact": "codex/project-approval-config-install-check.json",
            "status": approval_install_check["status"],
            "sha256": _sha256_file(
                directory / "project-approval-config-install-check.json"),
            "config_sha256_after_install": approval_install_check[
                "config_sha256_after_install"],
        }
        base.write_json(Path(output) / "provenance.json", provenance)
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
        manifest_snapshot_path = directory / "fixture-manifest.request.json"
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
        transfer_location.bind_lifecycle_observation(
            manifest, args.transfer_location_root)
        manifest["transfer_location_manifest_snapshot"] = str(manifest_snapshot_path.resolve())
        prompt_path = directory / "root-prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        prompt = prompt.replace("{{CAPTURE_SCRIPT}}", str(runtime_script.resolve()))
        prompt = prompt.replace("{{CONTACT_STATE}}", str(entrypoint))
        if "{{CAPTURE_SCRIPT}}" in prompt or "{{CONTACT_STATE}}" in prompt:
            raise ValueError("owner_capture_prompt_binding_failed")
        business_prompt = _bind_uv_cache_prompt(
            manifest, prompt, args.uv_cache_dir)
        lifecycle_context.update(directory=directory, consumer=consumer, manifest=manifest)
        base.write_json(manifest_path, manifest)
        manifest_snapshot_path.write_bytes(manifest_path.read_bytes())
        request_prompts = transfer_location.save_request_prompts(
            args.transfer_location_root, business_prompt, directory)
        location_context.update(root=args.transfer_location_root,
                                declaration=request_prompts["declaration"],
                                business_prompt=request_prompts["business_prompt"])
        prompt_path.write_text(request_prompts["combined_prompt"], encoding="utf-8")
        cache_evidence = args.uv_cache_evidence
        cache_evidence["manifest_binding"] = {
            "artifact": "codex/fixture-manifest.request.json",
            "path": str(manifest_snapshot_path.resolve()),
            "sha256": _sha256_file(manifest_snapshot_path),
            "uv_cache_dir": manifest.get("uv_cache_dir"),
        }
        cache_evidence["root_prompt_binding"] = {
            "artifact": "root-prompt.txt",
            "path": str(prompt_path.resolve()),
            "sha256": _sha256_file(prompt_path),
            "placeholder_resolved": UV_CACHE_PROMPT_PLACEHOLDER not in prompt_path.read_text(
                encoding="utf-8"),
        }
        _write_uv_cache_evidence(output, cache_evidence)
        return directory, consumer, manifest

    def build_request_with_evidence(consumer, prompt):
        nonlocal request_built
        request = original_build_request(consumer, prompt)
        command_argv = _validate_uv_cache_request(
            request, prompt, args.uv_cache_dir)
        cache_state = _uv_cache_inventory(args.uv_cache_dir)
        if cache_state["state"] != "EMPTY":
            raise ValueError("uv_cache_not_empty_before_request")
        base.write_json(request_path, request)
        cache_evidence = args.uv_cache_evidence
        cache_evidence["request_binding"] = {
            "artifact": "codex/codex-request.json",
            "command_sha256": hashlib.sha256(request["command"].encode("utf-8")).hexdigest(),
            "command_argument_count": len(command_argv),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "cache_state_before_request": cache_state,
            "dispatch_attempted": False,
            "remote_cache_proof_from_local_launcher_environment": False,
        }
        _write_uv_cache_evidence(output, cache_evidence)
        binding = transfer_location.request_binding_record(
            location_context["root"], location_context["declaration"],
            location_context["business_prompt"], request_path,
            Path(output) / "codex" / "fixture-manifest.request.json")
        base.write_json(binding_path, binding)
        updated = _record_request_runtime_facts(
            preflight, output, request, service_snapshot, producer, fixture
        )
        updated["transfer_location_binding"] = binding
        updated["uv_cache_binding_artifact"] = "codex/uv-cache-binding.json"
        evidence = {
            "schema": "issue-68-r29-runtime-environment-evidence-v1",
            "runtime_environment_facts": updated["runtime_environment_facts"],
            "runtime_environment_evidence": updated["runtime_environment_evidence"],
            "request_artifact": updated["request_artifact"],
            "transfer_location_binding": binding,
            "service_snapshot_artifact": "eval-service-provenance.before.json",
        }
        base.write_json(evidence_path, evidence)
        preflight.clear()
        preflight.update(updated)
        base.write_json(Path(output) / "input-evidence-preflight.json", preflight)
        provenance["runtime_environment_facts"] = preflight["runtime_environment_facts"]
        provenance["runtime_environment_evidence"] = preflight["runtime_environment_evidence"]
        provenance["runtime_environment_evidence_artifact"] = "runtime-environment-evidence.json"
        provenance["transfer_location_binding"] = binding
        provenance["uv_cache_binding_artifact"] = "codex/uv-cache-binding.json"
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
        root_prompt = (lifecycle_context["directory"] / "root-prompt.txt").read_text(
            encoding="utf-8")
        outgoing_argv = _validate_uv_cache_request(sent, root_prompt, args.uv_cache_dir)
        request_manifest = json.loads((Path(output) / "codex" /
                                       "fixture-manifest.request.json").read_text(encoding="utf-8"))
        if request_manifest.get("uv_cache_dir") != str(args.uv_cache_dir):
            raise ValueError("uv_cache_manifest_binding_mismatch")
        if _uv_cache_inventory(args.uv_cache_dir)["state"] != "EMPTY":
            raise ValueError("uv_cache_not_empty_at_dispatch")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        request_body_sha256 = hashlib.sha256(request.data).hexdigest()
        binding = transfer_location.request_binding_record(
            location_context["root"], location_context["declaration"],
            location_context["business_prompt"], request_path,
            Path(output) / "codex" / "fixture-manifest.request.json",
            request_body_sha256=request_body_sha256)
        recorded_binding = evidence.get("transfer_location_binding")
        if not isinstance(recorded_binding, dict) or {
                key: value for key, value in binding.items() if key != "request_body_sha256"
        } != recorded_binding:
            raise ValueError("transfer_location_binding_changed_before_request")
        base.write_json(binding_path, binding)
        evidence["transfer_location_binding"] = binding
        evidence["outgoing_request_body_sha256"] = request_body_sha256
        base.write_json(evidence_path, evidence)
        preflight["request_body_sha256"] = request_body_sha256
        preflight["transfer_location_binding"] = binding
        base.write_json(Path(output) / "input-evidence-preflight.json", preflight)
        provenance["request_body_sha256"] = request_body_sha256
        provenance["transfer_location_binding"] = binding
        base.write_json(Path(output) / "provenance.json", provenance)
        cache_evidence = args.uv_cache_evidence
        cache_evidence["request_binding"]["request_body_sha256"] = request_body_sha256
        cache_evidence["request_binding"]["dispatch_attempted"] = True
        cache_evidence["request_binding"]["request_prompt_matches_saved_root_prompt"] = (
            outgoing_argv[-1] == root_prompt)
        _write_uv_cache_evidence(output, cache_evidence)
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
        approval_configuration = record_approval_configuration(response)
        manifest["effective_project_approval_configuration"] = {
            "artifact": "codex/effective-project-approval-configuration.json",
            "sha256": _sha256_file(
                lifecycle_context["directory"] / "effective-project-approval-configuration.json"),
            "status": approval_configuration["status"],
        }
        base.write_json(lifecycle_context["directory"] / "fixture-manifest.json", manifest)
        lifecycle_context["collected"] = True
        result = original_verify_codex(response, adapter, manifest)
        return _constrain_with_formal_approval_configuration(result, approval_configuration)

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
                approval_configuration = record_approval_configuration(response)
                evidence = lifecycle.collect_lifecycle(
                    lifecycle_context["before"], lifecycle_context["manifest"],
                    lifecycle_context["consumer"], response, input_verifier)
                base.write_json(lifecycle_context["directory"] / "lifecycle-evidence.json", evidence)
                lifecycle_context["manifest"]["effective_project_approval_configuration"] = {
                    "artifact": "codex/effective-project-approval-configuration.json",
                    "sha256": _sha256_file(
                        lifecycle_context["directory"] / "effective-project-approval-configuration.json"),
                    "status": approval_configuration["status"],
                }
                base.write_json(lifecycle_context["directory"] / "fixture-manifest.json",
                                lifecycle_context["manifest"])
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
    if getattr(args, "transfer_location_root", None) is not None:
        try:
            args.transfer_location_root = transfer_location.validate_location_root(
                args.transfer_location_root,
                {
                    "product": args.producer_root,
                    "shared_assets": args.fixture_root,
                    "service": args.eval_direnv_root,
                    "evidence_output": output,
                    "runner_evidence": PREFLIGHT_DIR,
                },
            )
        except ValueError as exc:
            print(json.dumps({"state": "CASE_NOT_STARTED", "reason_code": str(exc)}))
            return 2
    else:
        # 真实命令行入口要求提供此目录；这里仅兼容被替换解析器的旧测试。
        args.transfer_location_root = None
    result = {"state": "CASE_NOT_STARTED", "reason_code": "bootstrap_failed"}
    if output.exists() and any(output.iterdir()):
        print(json.dumps({"state": "CASE_NOT_STARTED", "reason_code": "output_directory_not_empty"}))
        return 2
    output.mkdir(parents=True, exist_ok=True)
    args.uv_cache_evidence = None
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, base.stop_active)
    try:
        for source in (args.producer_root, args.fixture_root, args.eval_direnv_root):
            if overlaps(output, source):
                raise ValueError("output_must_be_outside_source_roots")
        args.uv_cache_dir = _prepare_run_uv_cache(output)
        initial_cache_state = _uv_cache_inventory(args.uv_cache_dir)
        if initial_cache_state["state"] != "EMPTY":
            raise ValueError("uv_cache_not_empty_at_creation")
        args.uv_cache_evidence = {
            "schema": UV_CACHE_BINDING_SCHEMA,
            "cache_dir": str(args.uv_cache_dir),
            "creation": {
                "state": "CREATED_EMPTY_WRITABLE",
                "inventory": initial_cache_state,
                "writability_probe": "created_and_removed_before_request",
            },
            "manifest_binding": None,
            "root_prompt_binding": None,
            "request_binding": None,
            "cleanup": {"state": "PENDING"},
            "remote_cache_proof_from_local_launcher_environment": False,
        }
        _write_uv_cache_evidence(output, args.uv_cache_evidence)
        check_entry_uniqueness()
        contract = load_contract()
        input_preflight = actual_input_observation_preflight(contract)
        base.write_json(output / "input-evidence-preflight.json", input_preflight)
        if not input_preflight["ready"]:
            raise ValueError(input_preflight["reason_code"])
        if not input_preflight["technical_preflight_ready"]:
            reasons = input_preflight["technical_preflight_block_reasons"]
            raise ValueError(reasons[0] if reasons else "technical_preflight_incomplete")
        if args.transfer_location_root is None:
            raise ValueError("transfer_location_root_required")
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
        if args.uv_cache_evidence is not None:
            cache_evidence = _finalize_run_uv_cache(output, args.uv_cache_evidence)
            args.uv_cache_evidence = cache_evidence
            if not cache_evidence["cleanup"]["confirmed_absent"]:
                result = base.verdict(
                    "INVALID_TEST_EXECUTION",
                    "uv_cache_cleanup_unconfirmed",
                    uv_cache_cleanup=cache_evidence["cleanup"],
                )
        base.write_json(output / "final-verdict.json", result)
    base.progress("结束：" + (result.get("verdict") or result.get("state", "UNKNOWN")))
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
