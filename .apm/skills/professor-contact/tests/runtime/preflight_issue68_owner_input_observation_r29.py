#!/usr/bin/env python3
"""Run the bounded synthetic-file capture check for PC68-R1 r29.

This is a test preflight, not the PC68-R1 business entrypoint. It creates a
temporary synthetic owner handoff, reads it once, copies the decoded object,
and invokes the repository's existing contact_state.py stage5-plan command
with arguments built from that same in-memory object. Standard output is the
strict owner-observation envelope and is intended to be captured unchanged by
the ordinary command tool (for example with tee).
"""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[5]
CONTACT_STATE = REPO_ROOT / ".apm/skills/professor-contact/scripts/contact_state.py"
SCHEMA = "issue-68-test-plan-r25-owner-input-v2"
PREFLIGHT_SCHEMA = "issue-68-r29-synthetic-capture-preflight-v1"


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_cli_stdout(text):
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("stage5_plan_stdout_not_object")
    return value


def run(artifact_path, stdout_capture_path, command_record):
    artifact_path = Path(artifact_path).resolve()
    stdout_capture_path = Path(stdout_capture_path).resolve()
    with tempfile.TemporaryDirectory(prefix="pc68-r29-synthetic-") as temp:
        root = Path(temp)
        program_root = root / "program"
        professor_dir = program_root / "教授研究" / "合成教授"
        professor_dir.mkdir(parents=True)
        # Build a minimal, valid local pack and template. The existing CLI
        # must return its complete structured stage5-plan without contacting
        # a service or writing business output.
        packet = {
            "program_root": str(program_root),
            "professor_dir": str(professor_dir),
            "email_pack": str(professor_dir / "邮件输入.json"),
            "email_id": "合成教授::合成方向::合成构想",
            "choices": [{"email_id": "SYNTHETIC-EMAIL-1", "first_choice": True}],
            "mode": "first",
            "template": str(root / "synthetic-template.md"),
            "result": str(root / "synthetic-result.json"),
        }
        email_id = packet["email_id"]
        packet["choices"] = [{"email_id": email_id, "first_choice": True}]
        email = {
            "email_id": email_id,
            "professor": "合成教授",
            "professor_dir": str(professor_dir),
            "idea": {"id": "合成构想", "title": "合成构想", "idea_zh": "只用于本地预检"},
            "direction_ids": ["合成方向"],
            "directions": [{"direction_id": "合成方向", "name_ja": "合成方向", "name_zh": "合成方向"}],
            "user_note": "",
            "papers": [],
            "gaps": [],
            "red_lines": [],
            "soft_materials": {"positioning": []},
            "user_supplement": "",
            "allowed_sources": ["idea:合成构想"],
        }
        pack = {
            "schema": 3,
            "kind": "professor-contact-email-input",
            "program_root": str(program_root),
            "professor": "合成教授",
            "professor_dir": str(professor_dir),
            "emails": [email],
        }
        Path(packet["email_pack"]).write_text(
            json.dumps(pack, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
            encoding="utf-8")
        Path(packet["template"]).write_text("合成模板，仅用于只读预检。\n", encoding="utf-8")
        owner_input_file = root / "owner_input.json"
        raw_input = (json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
        owner_input_file.write_bytes(raw_input)

        # This is the only read of owner_input_file in this preflight.
        parsed_packet = json.loads(owner_input_file.read_bytes().decode("utf-8"))
        read_count = 1
        observed_copy = copy.deepcopy(parsed_packet)

        argv = [
            sys.executable,
            str(CONTACT_STATE),
            "stage5-plan",
            "--program-root", parsed_packet["program_root"],
            "--email-pack", parsed_packet["email_pack"],
            "--email-id", parsed_packet["email_id"],
            "--template", parsed_packet["template"],
            "--mode", parsed_packet["mode"],
        ]
        completed = subprocess.run(
            argv, cwd=REPO_ROOT, text=True, capture_output=True, check=False
        )
        plan = parse_cli_stdout(completed.stdout)
        envelope = {
            "pc68_actual_input_observation": {
                "schema": SCHEMA,
                "source_step": "owner_input_json_parse",
                "business_step": "stage5-plan",
                "object": observed_copy,
            },
            "stage5_invocation": {"argv": argv},
            "stage5_plan": plan,
            "return_code": completed.returncode,
        }
        raw_stdout = json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
        stdout_sha256 = hashlib.sha256(raw_stdout.encode("utf-8")).hexdigest()
        artifact = {
            "schema": PREFLIGHT_SCHEMA,
            "result": "CAPTURED_SYNTHETIC_ONLY",
            "formal_case_started": False,
            "eval_service_called": False,
            "external_request_made": False,
            "producer_entrypoint": str(CONTACT_STATE.relative_to(REPO_ROOT)),
            "producer_argv": argv,
            "producer_return_code": completed.returncode,
            "producer_stderr": completed.stderr,
            "producer_structured_output": plan,
            "synthetic_fixture": {
                "email_pack": str(Path(packet["email_pack"])),
                "email_id": email_id,
                "professor": "合成教授",
                "template": str(Path(packet["template"])),
                "email_pack_content": pack,
            },
            "owner_input_file": str(owner_input_file),
            "owner_input_file_raw": raw_input.decode("utf-8"),
            "owner_input_read_count": read_count,
            "parsed_object": parsed_packet,
            "observation_object": observed_copy,
            "parsed_object_sha256": hashlib.sha256(canonical_json(parsed_packet).encode("utf-8")).hexdigest(),
            "observation_object_sha256": hashlib.sha256(canonical_json(observed_copy).encode("utf-8")).hexdigest(),
            "stdout_sha256": stdout_sha256,
            "stdout_capture_path": str(stdout_capture_path),
            "stdout_capture_method": "ordinary command output piped unchanged through tee",
            "command_record": command_record,
            "synthetic_correlation": {
                "runtime_generation": "synthetic-r29-capture-preflight",
                "thread_id": "synthetic-professor-thread",
                "commandExecution_id": "synthetic-command-1",
                "professor_dir": parsed_packet["professor_dir"],
                "source_step": "owner_input_json_parse",
                "business_step": "stage5-plan",
                "is_synthetic": True,
            },
            "raw_stdout": raw_stdout,
            "limitations": [
                "Synthetic correlation fields are test inputs, not Codex app_server event evidence.",
                "This preflight does not prove formal commandExecution.aggregatedOutput, model, host, executor, service identity, or PC68-R1 behavior.",
            ],
        }
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                 encoding="utf-8")
        sys.stdout.write(raw_stdout)
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--stdout-capture", type=Path, required=True)
    parser.add_argument("--command-record", required=True,
                        help="literal invocation used for this synthetic preflight record")
    args = parser.parse_args(argv)
    return run(args.artifact, args.stdout_capture, args.command_record)


if __name__ == "__main__":
    raise SystemExit(main())
