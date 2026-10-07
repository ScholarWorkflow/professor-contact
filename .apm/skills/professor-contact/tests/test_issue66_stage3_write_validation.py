"""Regression for the fixed Stage 3 validation write entry point."""
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_issue66_validation_handoff import ValidationHandoffBase


RUNNER = Path(__file__).parents[1] / "scripts" / "contact_state.py"


def _entry(path, artifact="candidates"):
    return {
        "artifact": artifact,
        "blocking": 0,
        "file": str(path),
        "issues": [],
        "minor": 0,
        "verdict": "pass",
    }


def _result(*entries):
    return {
        "result": "ok",
        "files": list(entries),
        "notes": "完整校验结果",
        "extension": {"keep": True},
    }


def _run_writer(output_file, result_json, *, cwd=None):
    return subprocess.run(
        [sys.executable, str(RUNNER), "stage3-write-validation",
         "--output-file", str(output_file), "--result-json", result_json],
        capture_output=True, check=False, cwd=cwd)


def _run_batch_writer(output_map_json, result_json):
    return subprocess.run(
        [sys.executable, str(RUNNER), "stage3-write-validation",
         "--output-map-json", output_map_json, "--result-json", result_json],
        capture_output=True, check=False)


def _error_payload(process):
    if process.returncode == 0:
        raise AssertionError("invalid writer input unexpectedly succeeded")
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"expected structured rejection; stdout={process.stdout!r}; "
            f"stderr={process.stderr!r}; error={exc}") from exc
    if payload.get("status") != "error":
        raise AssertionError(f"expected status=error, got {payload!r}")
    return payload


class Stage3WriteValidationTests(unittest.TestCase):
    def test_single_write_preserves_complete_result_stdout_bytes_and_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analysis_path = root / "analysis.md"
            candidate_path = root / "candidate.md"
            output_file = root / "validation.json"
            result = _result(
                _entry(analysis_path, artifact="analysis"),
                _entry(candidate_path))
            result["notes"] = "完整结果；保留中文和 $(literal)"
            result["extension"] = {"keep": True, "items": [1, "two"]}

            process = _run_writer(
                output_file, json.dumps(result, ensure_ascii=False))

            self.assertEqual(process.returncode, 0, process.stderr.decode("utf-8", "replace"))
            written = output_file.read_bytes()
            self.assertTrue(written)
            self.assertEqual(process.stdout, written)
            self.assertEqual(json.loads(written), result)
            self.assertEqual(stat.S_IMODE(output_file.stat().st_mode), 0o600)
            self.assertFalse(analysis_path.exists())
            self.assertFalse(candidate_path.exists())

    def test_batch_map_writes_the_same_complete_result_to_every_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analysis_path = root / "analysis.md"
            candidate_a = root / "candidate-a.md"
            candidate_b = root / "candidate-b.md"
            output_a = root / "validation-a.json"
            output_b = root / "validation-b.json"
            result = _result(
                _entry(analysis_path, artifact="analysis"),
                _entry(candidate_a),
                _entry(candidate_b))
            mapping = [
                {"file": str(candidate_b), "output_file": str(output_b)},
                {"file": str(candidate_a), "output_file": str(output_a)},
            ]

            process = _run_batch_writer(
                json.dumps(mapping), json.dumps(result, ensure_ascii=False))

            self.assertEqual(process.returncode, 0, process.stderr.decode("utf-8", "replace"))
            self.assertTrue(process.stdout)
            for output in (output_a, output_b):
                with self.subTest(output=output.name):
                    written = output.read_bytes()
                    self.assertEqual(written, process.stdout)
                    self.assertEqual(json.loads(written), result)
                    self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

    def test_invalid_complete_result_json_is_rejected_without_output(self):
        invalid_results = {
            "empty": "",
            "duplicate key": '{"result":"ok","result":"ok","files":[],"notes":""}',
            "infinite number": '{"result":"ok","files":[],"notes":"","extra":Infinity}',
            "NaN number": '{"result":"ok","files":[],"notes":"","extra":NaN}',
            "top-level list": "[]",
            "missing notes": '{"result":"ok","files":[]}',
            "notes is not a string": json.dumps({
                "result": "ok", "files": [], "notes": 7}),
            "empty files": json.dumps({"result": "ok", "files": [], "notes": ""}),
            "missing candidates": json.dumps({
                "result": "ok", "files": [_entry("/tmp/analysis.md", "analysis")],
                "notes": ""}),
            "wrong result status": json.dumps({
                "result": "error", "files": [_entry("/tmp/candidate.md")],
                "notes": ""}),
            "files is not a list": json.dumps({
                "result": "ok", "files": {}, "notes": ""}),
            "file entry is not an object": json.dumps({
                "result": "ok", "files": [None], "notes": ""}),
            "relative file path": json.dumps({
                "result": "ok", "files": [_entry("candidate.md")],
                "notes": ""}),
            "unsupported artifact": json.dumps({
                "result": "ok", "files": [_entry("/tmp/candidate.md", "other")],
                "notes": ""}),
            "artifact is not a string": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "artifact": 7}],
                "notes": ""}),
            "unsupported verdict": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "verdict": "maybe"}],
                "notes": ""}),
            "verdict is not a string": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "verdict": 7}],
                "notes": ""}),
            "boolean blocking count": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "blocking": True}],
                "notes": ""}),
            "string blocking count": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "blocking": "0"}],
                "notes": ""}),
            "negative minor count": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "minor": -1}],
                "notes": ""}),
            "float minor count": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "minor": 0.5}],
                "notes": ""}),
            "issues is not a list": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "issues": {}}],
                "notes": ""}),
            "issue is not an object": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "issues": [None]}],
                "notes": ""}),
            "issue is missing suggestion": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "minor": 1,
                    "verdict": "pass_with_minor",
                    "issues": [{"rule": "B5", "severity": "minor",
                                "location": 1, "quote": "原文"}],
                }], "notes": ""}),
            "unsupported issue severity": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "minor": 1,
                    "verdict": "pass_with_minor",
                    "issues": [{"rule": "B5", "severity": "moderate",
                                "location": 1, "quote": "原文",
                                "suggestion": "补充说明。"}],
                }], "notes": ""}),
            "boolean issue location": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "minor": 1,
                    "verdict": "pass_with_minor",
                    "issues": [{"rule": "B5", "severity": "minor",
                                "location": True, "quote": "原文",
                                "suggestion": "补充说明。"}],
                }], "notes": ""}),
            "overlong issue quote": json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "minor": 1,
                    "verdict": "pass_with_minor",
                    "issues": [{"rule": "B5", "severity": "minor",
                                "location": 1, "quote": "字" * 41,
                                "suggestion": "补充说明。"}],
                }], "notes": ""}),
            "inconsistent counts": json.dumps({
                "result": "ok",
                "files": [{
                    **_entry("/tmp/candidate.md"),
                    "issues": [{
                        "rule": "R1", "severity": "minor", "location": 1,
                        "quote": "short", "suggestion": "revise"}],
                }],
                "notes": "",
            }),
        }
        valid_issue = {
            "rule": "B5", "severity": "minor", "location": 1,
            "quote": "原文", "suggestion": "补充说明。",
        }
        for field in ("rule", "severity", "quote", "suggestion"):
            invalid_issue = {**valid_issue, field: None}
            invalid_results[f"issue {field} has wrong type"] = json.dumps({
                "result": "ok", "files": [{
                    **_entry("/tmp/candidate.md"), "minor": 1,
                    "verdict": "pass_with_minor", "issues": [invalid_issue],
                }], "notes": ""})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, result_json in invalid_results.items():
                with self.subTest(case=label):
                    output_file = root / f"{label.replace(' ', '-')}.json"
                    process = _run_writer(output_file, result_json)
                    payload = _error_payload(process)
                    self.assertEqual(payload.get("reason_code"), "invalid_validation_json")
                    self.assertFalse(output_file.exists() or output_file.is_symlink())

    def test_batch_map_invalidities_are_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_a = root / "candidate-a.md"
            candidate_b = root / "candidate-b.md"
            result = _result(_entry(candidate_a), _entry(candidate_b))
            output_a = root / "validation-a.json"
            output_b = root / "validation-b.json"
            cases = {
                "missing candidate": [
                    {"file": str(candidate_a), "output_file": str(output_a)}],
                "duplicate candidate": [
                    {"file": str(candidate_a), "output_file": str(output_a)},
                    {"file": str(candidate_a), "output_file": str(output_b)}],
                "unrelated candidate": [
                    {"file": str(candidate_a), "output_file": str(output_a)},
                    {"file": str(root / "other.md"), "output_file": str(output_b)}],
                "duplicate output": [
                    {"file": str(candidate_a), "output_file": str(output_a)},
                    {"file": str(candidate_b), "output_file": str(output_a)}],
                "extra pair field": [
                    {"file": str(candidate_a), "output_file": str(output_a), "extra": True},
                    {"file": str(candidate_b), "output_file": str(output_b)}],
                "relative output": [
                    {"file": str(candidate_a), "output_file": "relative.json"},
                    {"file": str(candidate_b), "output_file": str(output_b)}],
            }

            for label, mapping in cases.items():
                with self.subTest(case=label):
                    output_a.unlink(missing_ok=True)
                    output_b.unlink(missing_ok=True)
                    process = _run_batch_writer(
                        json.dumps(mapping), json.dumps(result))
                    _error_payload(process)
                    self.assertFalse(output_a.exists() or output_a.is_symlink())
                    self.assertFalse(output_b.exists() or output_b.is_symlink())

    def test_single_output_path_must_be_absolute_and_parent_must_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.md"
            result_json = json.dumps(_result(_entry(candidate)))
            cases = (
                ("relative path", "relative-validation.json", "invalid_validation_json"),
                ("missing parent", str(root / "missing" / "validation.json"),
                 "invalid_output_path"),
            )

            for label, output_path, reason_code in cases:
                with self.subTest(case=label):
                    process = _run_writer(output_path, result_json, cwd=root)
                    payload = _error_payload(process)
                    self.assertEqual(payload.get("reason_code"), reason_code)
                    self.assertFalse((root / "relative-validation.json").exists())
                    self.assertFalse((root / "missing").exists())

    def test_existing_target_or_symlink_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.md"
            result_json = json.dumps(_result(_entry(candidate)))
            existing = root / "existing.json"
            sentinel = b"preserve existing bytes\x00"
            existing.write_bytes(sentinel)

            existing_result = _run_writer(existing, result_json)
            existing_error = _error_payload(existing_result)
            self.assertEqual(existing_error.get("reason_code"),
                             "validation_handoff_collision")
            self.assertEqual(existing.read_bytes(), sentinel)

            link_target = root / "link-target.json"
            link_target.write_bytes(b"link target")
            link_path = root / "link.json"
            link_path.symlink_to(link_target)
            link_result = _run_writer(link_path, result_json)
            link_error = _error_payload(link_result)
            self.assertEqual(link_error.get("reason_code"),
                             "validation_handoff_collision")
            self.assertTrue(link_path.is_symlink())
            self.assertEqual(link_target.read_bytes(), b"link target")

    def test_batch_target_conflict_leaves_all_targets_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_a = root / "candidate-a.md"
            candidate_b = root / "candidate-b.md"
            output_a = root / "validation-a.json"
            output_b = root / "validation-b.json"
            output_b.write_bytes(b"existing")
            mapping = [
                {"file": str(candidate_a), "output_file": str(output_a)},
                {"file": str(candidate_b), "output_file": str(output_b)},
            ]

            process = _run_batch_writer(
                json.dumps(mapping),
                json.dumps(_result(_entry(candidate_a), _entry(candidate_b))))

            payload = _error_payload(process)
            self.assertEqual(payload.get("reason_code"), "validation_handoff_collision")
            self.assertEqual(payload.get("completed_paths"), [])
            self.assertFalse(output_a.exists())
            self.assertEqual(output_b.read_bytes(), b"existing")

    def test_batch_write_error_keeps_completed_file_and_removes_own_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_a = root / "candidate-a.md"
            candidate_b = root / "candidate-b.md"
            output_a = root / "validation-a.json"
            output_b = root / "validation-b.json"
            mapping = [
                {"file": str(candidate_a), "output_file": str(output_a)},
                {"file": str(candidate_b), "output_file": str(output_b)},
            ]
            result_json = json.dumps(
                _result(_entry(candidate_a), _entry(candidate_b)),
                ensure_ascii=False)

            spec = importlib.util.spec_from_file_location(
                "_issue66_contact_state_writer_test", RUNNER)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            args = module.build_parser().parse_args([
                "stage3-write-validation",
                "--output-map-json", json.dumps(mapping),
                "--result-json", result_json,
            ])

            real_write = os.write
            write_count = 0

            def fail_during_second_file(fd, data):
                nonlocal write_count
                write_count += 1
                if write_count == 1:
                    return real_write(fd, data)
                if write_count == 2:
                    return real_write(fd, data[:1])
                raise OSError("injected partial write failure")

            stdout_bytes = io.BytesIO()
            stdout_text = io.TextIOWrapper(stdout_bytes, encoding="utf-8")
            with mock.patch.object(module.sys, "stdout", stdout_text):
                with mock.patch.object(module.os, "write", side_effect=fail_during_second_file):
                    with self.assertRaises(SystemExit) as caught:
                        args.func(args)
            stdout_text.flush()

            self.assertEqual(caught.exception.code, 1)
            payload = json.loads(stdout_bytes.getvalue())
            self.assertEqual(payload.get("reason_code"), "validation_write_failed")
            self.assertEqual(payload.get("completed_paths"), [str(output_a)])
            self.assertEqual(json.loads(output_a.read_bytes()),
                             json.loads(result_json))
            self.assertFalse(output_b.exists() or output_b.is_symlink())


class Stage3WriterPreparedPathTests(ValidationHandoffBase):
    def test_writer_uses_prepare_output_path_and_complete_result_argument(self):
        self.commit_first()
        prepared = self.prepare(1)
        self.assertEqual(prepared.get("status"), "ok",
                         msg=json.dumps(prepared, ensure_ascii=False))
        prepared_output = prepared["output_file"]
        candidate_path = self.prof_dir / "套磁想法候选.md"
        candidate_before = candidate_path.read_bytes()
        result = {
            "result": "ok",
            "files": [_entry(candidate_path)],
            "notes": "完整校验结果",
            "extension": {"keep": True, "source": "validator-return"},
        }
        validator_result_json = json.dumps(result, ensure_ascii=False)
        argv = [
            sys.executable, str(RUNNER), "stage3-write-validation",
            "--output-file", prepared_output,
            "--result-json", validator_result_json,
        ]

        process = subprocess.run(argv, capture_output=True, check=False)

        self.assertEqual(argv[argv.index("--output-file") + 1], prepared_output)
        self.assertEqual(argv[argv.index("--result-json") + 1],
                         validator_result_json)
        self.assertEqual(process.returncode, 0,
                         process.stderr.decode("utf-8", "replace"))
        output_path = Path(prepared_output)
        written = output_path.read_bytes()
        self.assertTrue(written)
        self.assertEqual(process.stdout, written)
        self.assertEqual(json.loads(written), result)
        self.assertEqual(stat.S_IMODE(output_path.stat().st_mode), 0o600)
        self.assertEqual(candidate_path.read_bytes(), candidate_before)


if __name__ == "__main__":
    unittest.main()
