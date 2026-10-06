#!/usr/bin/env python3
"""Run a synthetic-only check of the fixed PC68 owner capture wrapper."""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[5]
RUNTIME = SCRIPT.parent
CONTACT_STATE_SOURCE = REPO_ROOT / ".apm/skills/professor-contact/scripts/contact_state.py"
CAPTURE_SOURCE = RUNTIME / "capture_issue68_owner_stage5_plan_r1.py"
SCHEMA = "issue-68-test-plan-r25-owner-input-v2"
PREFLIGHT_SCHEMA = "issue-68-r29-fixed-capture-preflight-v1"

sys.path.insert(0, str(RUNTIME))
import verify_issue68_stage5_routing_r19 as verifier


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path):
    return sha256(Path(path).read_bytes())


def path_replacements(root):
    replacements = {
        str(REPO_ROOT.resolve()): "/__pc68_repo__",
        str(root): "/__pc68_synthetic__",
        str(root.resolve()): "/__pc68_synthetic__",
        str(Path(sys.executable).resolve()): "/__pc68_uv__/python",
        sys.executable: "/__pc68_uv__/python",
    }
    return sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)


def normalize_paths(value, replacements):
    if isinstance(value, dict):
        return {key: normalize_paths(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_paths(item, replacements) for item in value]
    if isinstance(value, str):
        for source, target in replacements:
            value = value.replace(source, target)
    return value


def portable_artifact_path(path):
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return "/__pc68_artifact__/" + resolved.name
    return "/__pc68_repo__/" + relative.as_posix()


def run(artifact_path, stdout_capture_path, command_record):
    artifact_path = Path(artifact_path).resolve()
    stdout_capture_path = Path(stdout_capture_path).resolve()
    with tempfile.TemporaryDirectory(prefix="pc68-r29-synthetic-") as temp:
        root = Path(temp)
        program_root = root / "program"
        professor_dir = program_root / "教授研究" / "合成教授"
        professor_dir.mkdir(parents=True)
        consumer = root / "consumer"
        consumer.mkdir()
        entrypoint = consumer / ".agents/skills/professor-contact/scripts/contact_state.py"
        entrypoint.parent.mkdir(parents=True)
        shutil.copy2(CONTACT_STATE_SOURCE, entrypoint)
        entrypoint = entrypoint.resolve()
        wrapper = consumer / ".pc68-test-support" / CAPTURE_SOURCE.name
        wrapper.parent.mkdir(parents=True)
        shutil.copy2(CAPTURE_SOURCE, wrapper)

        email_id = "合成教授::合成方向::合成构想"
        packet = {
            "program_root": str(program_root), "professor_dir": str(professor_dir),
            "email_pack": str(professor_dir / "邮件输入.json"), "email_id": email_id,
            "choices": [{"email_id": email_id, "first_choice": True}],
            "mode": "first", "template": str(root / "synthetic-template.md"),
            "result": str(root / "synthetic-result.json"),
        }
        email = {
            "email_id": email_id, "professor": "合成教授", "professor_dir": str(professor_dir),
            "idea": {"id": "合成构想", "title": "合成构想", "idea_zh": "只用于本地预检"},
            "direction_ids": ["合成方向"],
            "directions": [{"direction_id": "合成方向", "name_ja": "合成方向", "name_zh": "合成方向"}],
            "user_note": "", "papers": [], "gaps": [], "red_lines": [],
            "soft_materials": {"positioning": []}, "user_supplement": "",
            "allowed_sources": ["idea:合成构想"],
        }
        pack = {
            "schema": 3, "kind": "professor-contact-email-input",
            "program_root": str(program_root), "professor": "合成教授",
            "professor_dir": str(professor_dir), "emails": [email],
        }
        Path(packet["email_pack"]).write_text(
            json.dumps(pack, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        Path(packet["template"]).write_text("合成模板，仅用于只读预检。\n", encoding="utf-8")
        owner_input_file = root / "owner_input.json"
        owner_input_file.write_text(json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                    encoding="utf-8")

        capture_command = ["uv", "run", "--no-project", "python", str(wrapper.resolve()),
                           "--action", "stage5-plan", "--owner-input-file", str(owner_input_file),
                           "--contact-state", str(entrypoint)]
        env = os.environ.copy()
        env["UV_CACHE_DIR"] = str(root / "uv-cache")
        env["UV_OFFLINE"] = "1"
        completed = subprocess.run(capture_command, cwd=consumer, env=env,
                                   text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError("fixed_capture_command_failed:" + completed.stderr)
        envelope = json.loads(completed.stdout)
        if not isinstance(envelope, dict):
            raise ValueError("fixed_capture_output_not_object")

        manifest_path = root / "fixture-manifest.json"
        manifest = {
            "program_root": str(program_root),
            "owners": [{"professor": "合成教授", "professor_dir": str(professor_dir),
                        "email_pack": packet["email_pack"]}],
            "owner_capture": {
                "consumer_root": str(consumer.resolve()), "runtime_path": str(wrapper.resolve()),
                "installed_entrypoint": str(entrypoint),
                "entrypoint_sha256": sha256_file(entrypoint),
                "source_path": str(CAPTURE_SOURCE.resolve()),
                "source_sha256": verifier.OWNER_CAPTURE_SHA256,
                "runtime_sha256": sha256_file(wrapper),
                "manifest_path": str(manifest_path.resolve()),
            },
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        call = {
            "id": "synthetic-command-fixed-capture", "generation": "synthetic-r29-fixed-capture-preflight",
            "thread": "synthetic-professor-thread", "start": 1, "end": 2,
            "command": shlex.join(capture_command), "output": completed.stdout,
        }
        rows, problem = verifier.consumed_business_objects([call], manifest)
        if problem or len(rows) != 1:
            raise ValueError("fixed_capture_verifier_rejected:" + json.dumps(problem, ensure_ascii=False))
        row = rows[0]
        packet_from_capture = row["packet"]
        plan = row["plan"]
        replacements = path_replacements(root)
        captured_stdout_sha256 = sha256(completed.stdout.encode("utf-8"))
        captured_object_sha256 = envelope["pc68_fixed_capture"]["parsed_object_sha256"]
        portable_envelope = normalize_paths(envelope, replacements)
        portable_packet = portable_envelope["pc68_actual_input_observation"]["object"]
        portable_plan = portable_envelope["stage5_plan"]
        portable_product_stdout = json.dumps(
            portable_plan, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
        portable_envelope["stage5_raw_stdout"] = portable_product_stdout
        portable_envelope["stage5_process"]["stdout_sha256"] = sha256(
            portable_product_stdout.encode("utf-8"))
        portable_object_sha256 = sha256(canonical_json(portable_packet).encode("utf-8"))
        portable_envelope["pc68_fixed_capture"]["parsed_object_sha256"] = portable_object_sha256
        portable_stdout = json.dumps(
            portable_envelope, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
        portable_stdout_sha256 = sha256(portable_stdout.encode("utf-8"))
        portable_manifest = normalize_paths(manifest, replacements)
        portable_capture_command = normalize_paths(capture_command, replacements)
        portable_fixture = normalize_paths({
            "email_pack": packet["email_pack"], "email_id": email_id,
            "professor": "合成教授", "template": packet["template"],
            "email_pack_content": pack,
        }, replacements)
        stdout_capture_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_capture_path.write_text(portable_stdout, encoding="utf-8")
        artifact = {
            "schema": PREFLIGHT_SCHEMA, "result": "CAPTURED_SYNTHETIC_ONLY",
            "formal_case_started": False, "eval_service_called": False,
            "external_request_made": False, "producer_entrypoint": str(CONTACT_STATE_SOURCE.relative_to(REPO_ROOT)),
            "producer_argv": portable_envelope["stage5_invocation"]["argv"],
            "capture_command_argv": portable_capture_command,
            "runner_manifest": portable_manifest,
            "producer_return_code": row["return_code"], "producer_stderr": "",
            "producer_structured_output": portable_plan,
            "synthetic_fixture": portable_fixture,
            "owner_input_file": portable_envelope["pc68_fixed_capture"]["owner_input_file"],
            "owner_input_read_count": portable_envelope["pc68_fixed_capture"]["owner_input_read_count"],
            "parsed_object": portable_packet, "observation_object": portable_packet,
            "parsed_object_sha256": portable_object_sha256,
            "observation_object_sha256": portable_object_sha256,
            "captured_parsed_object_sha256": captured_object_sha256,
            "captured_stdout_sha256": captured_stdout_sha256,
            "stdout_sha256": portable_stdout_sha256,
            "stdout_capture_path": portable_artifact_path(stdout_capture_path),
            "stdout_capture_method": "fixed wrapper output verified before portable path normalization",
            "portable_path_normalization": {
                "state": "VERIFIED_THEN_NORMALIZED",
                "placeholders": {
                    "repository_root": "/__pc68_repo__",
                    "synthetic_run_root": "/__pc68_synthetic__",
                    "uv_python": "/__pc68_uv__/python",
                    "artifact_root": "/__pc68_artifact__",
                },
            },
            "command_record": command_record,
            "synthetic_correlation": normalize_paths({
                "runtime_generation": call["generation"], "thread_id": call["thread"],
                "commandExecution_id": call["id"], "professor_dir": packet["professor_dir"],
                "source_step": "owner_input_json_parse", "business_step": "stage5-plan",
                "is_synthetic": True,
            }, replacements),
            "fixed_capture_verification": {"state": "PASS", "verifier": "consumed_business_objects",
                                           "wrapper_sha256": verifier.OWNER_CAPTURE_SHA256},
            "raw_stdout": portable_stdout,
            "limitations": [
                "Synthetic IDs are test inputs, not Codex app_server event evidence.",
                "This preflight does not prove formal commandExecution.aggregatedOutput or PC68-R1 behavior.",
                "The current event adapter does not expose an independently attributable root-to-child owner_input_file path.",
            ],
        }
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                 encoding="utf-8")
        sys.stdout.write(portable_stdout)
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--stdout-capture", type=Path, required=True)
    parser.add_argument("--command-record", required=True)
    args = parser.parse_args(argv)
    return run(args.artifact, args.stdout_capture, args.command_record)


if __name__ == "__main__":
    raise SystemExit(main())
