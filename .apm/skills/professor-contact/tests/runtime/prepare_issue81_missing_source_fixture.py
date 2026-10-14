"""Prepare the isolated synthetic consumer inputs for Issue 81 target D."""

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))
spec = importlib.util.spec_from_file_location(
    "issue81_fixture_helpers", TESTS_DIR / "test_contact_state.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

PROFESSOR = helpers.ISSUE59_PROFESSOR


def run_plan(runner, program_root, email_pack, template):
    result = subprocess.run(
        [sys.executable, str(runner), "stage5-plan",
         "--program-root", str(program_root), "--email-pack", str(email_pack),
         "--template", str(template), "--mode", "first"],
        text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"stage5-plan returned invalid JSON: {exc}") from exc


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--consumer-root", required=True, type=Path)
    parser.add_argument("--program-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    consumer_root = args.consumer_root.resolve()
    program_root = args.program_root.resolve()
    output_dir = args.output_dir.resolve()
    runner = (consumer_root / ".agents" / "skills" / "professor-contact"
              / "scripts" / "contact_state.py")
    if not runner.is_file():
        raise RuntimeError(f"installed runner not found: {runner}")
    if not consumer_root.is_dir() or not program_root.is_relative_to(consumer_root):
        raise RuntimeError("synthetic program root must be inside the clean consumer")
    output_dir.mkdir(parents=True, exist_ok=True)
    previous_tempdir = tempfile.tempdir
    tempfile.tempdir = str(output_dir)
    email_templates = consumer_root / "套磁邮件"
    email_templates.mkdir(parents=True, exist_ok=True)
    template, _ = helpers.stage5_templates(email_templates)

    test_case = unittest.TestCase()
    try:
        fixture = helpers.write_issue59_stage5_fixture(program_root, case=test_case)
        verify_path = fixture["verify"][PROFESSOR]
        cached = json.loads(verify_path.read_text(encoding="utf-8"))
        verify_path.unlink()

        first_plan = run_plan(runner, program_root, fixture["pack"], template)
        if first_plan["verify"].get(PROFESSOR) != "needs_recheck:missing":
            raise RuntimeError("complete-source setup did not start with a missing verify cache")
        hint = first_plan["verify_write_hints"][PROFESSOR]
        if not hint or set(hint["source_fingerprints"]) != {
                "info_json", "boshu_analysis"}:
            raise RuntimeError("complete-source plan did not provide both write hints")
        if not all(hint["source_fingerprints"].values()):
            raise RuntimeError("complete-source plan returned an incomplete write hint")

        cached["verified_at"] = helpers.contact_state.now_utc()
        cached["source_fingerprints"] = hint["source_fingerprints"]
        write_json(verify_path, cached)
        valid_plan = run_plan(runner, program_root, fixture["pack"], template)
        if valid_plan["verify"].get(PROFESSOR) != "ok":
            raise RuntimeError("synthetic complete cache was not reusable")

        boshu_path = program_root / "boshu_analysis.json"
        boshu_path.unlink()
        missing_source_plan = run_plan(runner, program_root, fixture["pack"], template)
        if missing_source_plan["verify"].get(PROFESSOR) != \
                "needs_recheck:missing_source":
            raise RuntimeError("missing source did not produce needs_recheck:missing_source")
        if missing_source_plan["verify_write_hints"].get(PROFESSOR) is not None:
            raise RuntimeError("missing source unexpectedly produced a write hint")
        diagnostic = missing_source_plan["verify_diagnostics"][PROFESSOR]
        if diagnostic != {
                "reason": "missing_source",
                "failed_field": "source_fingerprints.boshu_analysis",
                "diagnostic_kind": "source_unavailable"}:
            raise RuntimeError(f"missing source diagnostic differed: {diagnostic!r}")

        write_json(output_dir / "complete-source-initial-plan.json", first_plan)
        write_json(output_dir / "complete-cache-plan.json", valid_plan)
        write_json(output_dir / "missing-source-initial-plan.json",
                   missing_source_plan)
        write_json(output_dir / "fixture-manifest.json", {
            "program_root": str(program_root),
            "email_pack": str(fixture["pack"]),
            "professor_dir": str(fixture["dirs"][PROFESSOR]),
            "template": str(template),
            "verify_cache": str(verify_path),
            "missing_source": str(boshu_path),
            "missing_source_plan": str(
                output_dir / "missing-source-initial-plan.json"),
        })
    finally:
        test_case.doCleanups()
        tempfile.tempdir = previous_tempdir


if __name__ == "__main__":
    main()
