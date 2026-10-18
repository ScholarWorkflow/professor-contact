"""Prepare the isolated synthetic consumer inputs for Issue 81 target D."""

import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))
spec = importlib.util.spec_from_file_location(
    "issue81_stage5_issue59_test_support",
    TESTS_DIR / "_stage5_issue59_test_support.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

PROFESSOR = helpers.ISSUE59_PROFESSOR


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
        expected_fingerprints = {
            "info_json": (
                f"{program_root / 'info.json'}:"
                f"{int((program_root / 'info.json').stat().st_mtime)}"),
            "boshu_analysis": (
                f"{program_root / 'boshu_analysis.json'}:"
                f"{int((program_root / 'boshu_analysis.json').stat().st_mtime)}"),
        }
        if set(cached.get("items", {})) != {
                "email", "roster", "season", "header", "subject_batch",
                "schedule", "consent", "warnings"}:
            raise RuntimeError("synthetic verify cache does not contain all eight items")
        if cached.get("source_fingerprints") != expected_fingerprints:
            raise RuntimeError("synthetic verify cache does not match source path/mtime")
        if not cached.get("verified_at", "").endswith("Z"):
            raise RuntimeError("synthetic verify cache timestamp is not canonical UTC")

        boshu_path = program_root / "boshu_analysis.json"
        boshu_path.unlink()
        if (boshu_path.exists() or not verify_path.is_file()
                or not Path(fixture["pack"]).is_file()
                or not (program_root / "info.json").is_file()):
            raise RuntimeError(
                "fixture did not retain the cache, email pack, and other source after removal")
        write_json(output_dir / "fixture-manifest.json", {
            "program_root": str(program_root),
            "email_pack": str(fixture["pack"]),
            "professor_dir": str(fixture["dirs"][PROFESSOR]),
            "template": str(template),
            "verify_cache": str(verify_path),
            "missing_source": str(boshu_path),
        })
    finally:
        test_case.doCleanups()
        tempfile.tempdir = previous_tempdir


if __name__ == "__main__":
    main()
