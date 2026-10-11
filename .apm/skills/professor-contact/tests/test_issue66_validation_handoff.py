"""Focused fixed-write, save and record checks for Stage 3 validation handoff."""
import contextlib
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from test_stage2_resolved_direction import parse, run_cli, write_json
from test_stage3_direction_groups import (
    Stage3DirectionGroupBase, contact_state,
)

CANDIDATE_STATE = "套磁候选状态.json"
CANDIDATES_MD = "套磁想法候选.md"


class Issue66ValidationHandoffTests(Stage3DirectionGroupBase):
    def setUp(self):
        super().setUp()
        self.cap = self._capture_invocation(self.prof_dir, "invocation-a")
        results = self.write_results("issue66-handoff-a", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None]),
        })
        committed = parse(run_cli(
            "stage3-finalize", "--invocation-file", self.cap["invocation_file"],
            "--invocation-sha256", self.cap["invocation_sha256"],
            "--results", results))
        self.assertEqual(committed["status"], "ok", committed)

    def _capture_invocation(self, professor_dir, name):
        out = parse(run_cli(
            "stage3-plan", "--professor-dir", professor_dir,
            "--program-root", self.root,
            "--capture-invocation", self.root / name))
        self.assertEqual(out["status"], "ok", out)
        return out

    def _prepare(self, cap, round_no=1):
        out = parse(run_cli(
            "stage3-prepare-validation",
            "--invocation-file", cap["invocation_file"],
            "--invocation-sha256", cap["invocation_sha256"],
            "--round", str(round_no)))
        self.assertEqual(out["status"], "ok", out)
        handoff_dir = contact_state._stage3_handoff_directory(
            Path(out["professor_dir"]), cap["invocation_file"], round_no)
        self.addCleanup(shutil.rmtree, handoff_dir, ignore_errors=True)
        return out

    @staticmethod
    def _entry(candidate_path, verdict, issues=()):
        blocking = sum(issue["severity"] == "blocking" for issue in issues)
        minor = sum(issue["severity"] == "minor" for issue in issues)
        return {
            "file": str(Path(candidate_path).resolve()),
            "artifact": "candidates", "verdict": verdict,
            "blocking": blocking, "minor": minor, "issues": list(issues),
        }

    @staticmethod
    def _finding(severity="blocking", quote="候选 dir_A_1"):
        return {
            "rule": "B5", "severity": severity, "location": "候选标题",
            "quote": quote, "suggestion": "首次出现时用日常语言解释。",
        }

    def _fixed_write(self, result, output_file=None, output_map=None):
        args = [sys.executable, str(Path(contact_state.__file__)),
                "stage3-write-validation"]
        if output_file is not None:
            args.extend(["--output-file", str(output_file)])
        if output_map is not None:
            args.extend(["--output-map-json", json.dumps(output_map, ensure_ascii=False)])
        args.extend(["--result-json", json.dumps(result, ensure_ascii=False)])
        return subprocess.run(args, capture_output=True, check=False)

    def _save(self, prepared):
        return parse(run_cli(
            "stage3-save-validation", "--handoff-file", prepared["handoff_file"],
            "--handoff-sha256", prepared["handoff_sha256"]))

    def _record(self, prepared, validation_sha):
        return parse(run_cli(
            "stage3-record-validation", "--handoff-file", prepared["handoff_file"],
            "--handoff-sha256", prepared["handoff_sha256"],
            "--expected-validation-sha256", validation_sha))

    def _full_batch_output(self):
        prof_b = self.build_second_professor()
        cap_b = self._capture_invocation(prof_b, "invocation-b")
        prepared_a = self._prepare(self.cap)
        prepared_b = self._prepare(cap_b)
        path_a = (self.prof_dir / CANDIDATES_MD).resolve()
        path_b = (prof_b / CANDIDATES_MD).resolve()
        issue_b = self._finding(quote="候选 dir_C_1")
        result = {
            "result": "ok",
            "files": [
                self._entry(path_a, "pass"),
                self._entry(path_b, "fail", [issue_b]),
            ],
            "notes": "批量原文：特殊字符 λ、研究室 🧪",
        }
        output_dir = self.root / "batch-output"
        output_dir.mkdir()
        mapping = [
            {"file": str(path_a), "output_file": prepared_a["output_file"]},
            {"file": str(path_b), "output_file": prepared_b["output_file"]},
        ]
        written = self._fixed_write(result, output_map=mapping)
        self.assertEqual(written.returncode, 0, written.stderr.decode("utf-8", "replace"))
        raw = Path(prepared_a["output_file"]).read_bytes()
        self.assertEqual(written.stdout, raw)
        self.assertEqual(Path(prepared_b["output_file"]).read_bytes(), raw)
        self.assertEqual(json.loads(raw), result)
        self.assertEqual(stat.S_IMODE(Path(prepared_a["output_file"]).stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(Path(prepared_b["output_file"]).stat().st_mode), 0o600)
        return prof_b, prepared_a, prepared_b, result, raw

    def test_fixed_writer_save_and_record_preserve_pass_bytes(self):
        prepared = self._prepare(self.cap)
        result = {
            "result": "ok",
            "files": [self._entry(self.prof_dir / CANDIDATES_MD, "pass")],
            "notes": "特殊字符：研究室 🧪 / lambda λ",
        }
        written = self._fixed_write(result, output_file=prepared["output_file"])
        self.assertEqual(written.returncode, 0, written.stderr.decode("utf-8", "replace"))
        source = Path(prepared["output_file"])
        raw = source.read_bytes()
        self.assertEqual(written.stdout, raw)
        self.assertEqual(json.loads(raw), result)
        self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o600)

        saved = self._save(prepared)
        self.assertEqual(saved["status"], "ok", saved)
        target = Path(saved["validation_file"])
        self.assertEqual(target.read_bytes(), raw)
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(saved["validation_sha256"], digest)
        recorded = self._record(prepared, digest)
        self.assertEqual(recorded["status"], "ok", recorded)
        self.assertEqual(recorded["validation_input_sha256"], digest)
        self.assertFalse(recorded["needs_correction"])
        self.assertTrue(recorded["terminal"])
        self.assertEqual(target.read_bytes(), raw)

    def test_fixed_writer_save_and_record_preserve_minor_result(self):
        prepared = self._prepare(self.cap)
        issue = self._finding("minor")
        result = {
            "result": "ok",
            "files": [self._entry(self.prof_dir / CANDIDATES_MD,
                                  "pass_with_minor", [issue])],
            "notes": "次要问题记录",
        }
        written = self._fixed_write(result, output_file=prepared["output_file"])
        self.assertEqual(written.returncode, 0, written.stderr.decode("utf-8", "replace"))
        raw = Path(prepared["output_file"]).read_bytes()
        self.assertEqual(written.stdout, raw)
        saved = self._save(prepared)
        self.assertEqual(Path(saved["validation_file"]).read_bytes(), raw)
        recorded = self._record(prepared, saved["validation_sha256"])
        self.assertEqual(recorded["status"], "ok", recorded)
        self.assertEqual(recorded["raw_verdict"], "pass_with_minor")
        self.assertFalse(recorded["needs_correction"])
        self.assertTrue(recorded["terminal"])

    def test_fixed_writer_save_and_record_preserve_fail_result(self):
        prepared = self._prepare(self.cap)
        issue = self._finding("blocking")
        result = {
            "result": "ok",
            "files": [self._entry(self.prof_dir / CANDIDATES_MD, "fail", [issue])],
            "notes": "需按记录的问题修正",
        }
        written = self._fixed_write(result, output_file=prepared["output_file"])
        self.assertEqual(written.returncode, 0, written.stderr.decode("utf-8", "replace"))
        raw = Path(prepared["output_file"]).read_bytes()
        self.assertEqual(written.stdout, raw)
        saved = self._save(prepared)
        self.assertEqual(Path(saved["validation_file"]).read_bytes(), raw)
        recorded = self._record(prepared, saved["validation_sha256"])
        self.assertEqual(recorded["status"], "ok", recorded)
        self.assertEqual(recorded["raw_verdict"], "fail")
        self.assertTrue(recorded["needs_correction"])
        self.assertFalse(recorded["terminal"])
        self.assertEqual(recorded["scopes"], [
            {"scope": "direction:dir_A", "result": "fail", "rounds": 1,
             "blocking": 1},
            {"scope": "direction:dir_B", "result": "pass", "rounds": 1,
             "blocking": 0},
        ])

    def test_save_copies_noncanonical_utf8_bytes_and_bad_digest_does_not_advance(self):
        prepared = self._prepare(self.cap)
        result = {
            "notes": "非标准空格与顺序：λ",
            "files": [self._entry(self.prof_dir / CANDIDATES_MD, "pass")],
            "result": "ok",
        }
        raw = (json.dumps(result, ensure_ascii=False, indent=3) + " \n").encode("utf-8")
        source = Path(prepared["output_file"])
        fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
        saved = self._save(prepared)
        self.assertEqual(saved["status"], "ok", saved)
        target = Path(saved["validation_file"])
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(target.read_bytes(), raw)
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(saved["validation_sha256"], digest)

        state_path = self.prof_dir / CANDIDATE_STATE
        before = state_path.read_bytes()
        rejected = self._record(prepared, "0" * 64)
        self.assertEqual(rejected["reason_code"], "validation_sha256_mismatch", rejected)
        self.assertEqual(state_path.read_bytes(), before)
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(target.read_bytes(), raw)

        recorded = self._record(prepared, digest)
        self.assertEqual(recorded["status"], "ok", recorded)
        self.assertEqual(recorded["validation_input_sha256"], digest)
        self.assertFalse(recorded["needs_correction"])

    def test_batch_full_result_is_saved_and_recorded_for_each_professor(self):
        prof_b, prepared_a, prepared_b, result, raw = self._full_batch_output()
        self.assertEqual(json.loads(raw), result)
        saved_a = self._save(prepared_a)
        saved_b = self._save(prepared_b)
        self.assertEqual(Path(saved_a["validation_file"]).read_bytes(), raw)
        self.assertEqual(Path(saved_b["validation_file"]).read_bytes(), raw)
        self.assertEqual(saved_a["validation_sha256"], saved_b["validation_sha256"])

        recorded_a = self._record(prepared_a, saved_a["validation_sha256"])
        recorded_b = self._record(prepared_b, saved_b["validation_sha256"])
        self.assertFalse(recorded_a["needs_correction"])
        self.assertTrue(recorded_a["terminal"])
        self.assertTrue(recorded_b["needs_correction"])
        self.assertFalse(recorded_b["terminal"])
        state_a = json.loads((self.prof_dir / CANDIDATE_STATE).read_text(encoding="utf-8"))
        state_b = json.loads((prof_b / CANDIDATE_STATE).read_text(encoding="utf-8"))
        self.assertEqual(state_a["validator"]["results"]["dir_A"]["result"], "pass")
        self.assertEqual(state_b["validator"]["pending"]["direction:dir_C"]
                         ["issues"][0]["quote"], "候选 dir_C_1")

    def test_second_professor_save_error_does_not_block_first_record(self):
        prof_b, prepared_a, prepared_b, _result, raw = self._full_batch_output()
        state_b = prof_b / CANDIDATE_STATE
        state_b.write_bytes(b"{ malformed peer state")
        malformed_b = state_b.read_bytes()

        saved_a = self._save(prepared_a)
        self.assertEqual(saved_a["status"], "ok", saved_a)
        recorded_a = self._record(prepared_a, saved_a["validation_sha256"])
        self.assertEqual(recorded_a["status"], "ok", recorded_a)
        self.assertFalse(recorded_a["needs_correction"])

        rejected_b = self._save(prepared_b)
        self.assertEqual(rejected_b["reason_code"], "missing_candidate_state", rejected_b)
        self.assertEqual(Path(prepared_b["output_file"]).read_bytes(), raw)
        self.assertEqual(state_b.read_bytes(), malformed_b)
        state_a = json.loads((self.prof_dir / CANDIDATE_STATE).read_text(encoding="utf-8"))
        self.assertFalse(state_a["validator"]["results"]["dir_A"]["result"] == "fail")

    def test_writer_refuses_existing_output_without_replacing_it(self):
        prepared = self._prepare(self.cap)
        source = Path(prepared["output_file"])
        marker = b"keep existing bytes\n"
        source.write_bytes(marker)
        result = {
            "result": "ok",
            "files": [self._entry(self.prof_dir / CANDIDATES_MD, "pass")],
            "notes": "complete",
        }
        rejected = self._fixed_write(result, output_file=source)
        self.assertEqual(rejected.returncode, 1)
        payload = parse(rejected)
        self.assertEqual(payload["reason_code"], "validation_handoff_collision", payload)
        self.assertEqual(source.read_bytes(), marker)

    def test_writer_refuses_symlink_output_without_replacing_target(self):
        prepared = self._prepare(self.cap)
        output = self.root / "writer-symlink.json"
        marker_path = self.root / "writer-symlink-target.json"
        marker = b"keep symlink target bytes\n"
        marker_path.write_bytes(marker)
        output.symlink_to(marker_path)
        result = {
            "result": "ok",
            "files": [self._entry(self.prof_dir / CANDIDATES_MD, "pass")],
            "notes": "complete",
        }

        rejected = self._fixed_write(result, output_file=output)
        self.assertEqual(rejected.returncode, 1)
        payload = parse(rejected)
        self.assertEqual(payload["reason_code"], "validation_handoff_collision", payload)
        self.assertTrue(output.is_symlink())
        self.assertEqual(marker_path.read_bytes(), marker)

    def test_save_refuses_existing_regular_and_symlink_targets(self):
        prepared = self._prepare(self.cap)
        source = Path(prepared["output_file"])
        result = {
            "result": "ok",
            "files": [self._entry(self.prof_dir / CANDIDATES_MD, "pass")],
            "notes": "complete",
        }
        written = self._fixed_write(result, output_file=source)
        self.assertEqual(written.returncode, 0, written.stderr.decode("utf-8", "replace"))
        source_before = source.read_bytes()
        target = Path(prepared["validation_file"])
        state_path = self.prof_dir / CANDIDATE_STATE
        state_before = state_path.read_bytes()
        marker = b"keep saved target bytes\n"

        for kind in ("regular", "symlink"):
            with self.subTest(kind=kind):
                marker_path = self.root / f"save-{kind}-marker.json"
                marker_path.write_bytes(marker)
                if kind == "regular":
                    target.write_bytes(marker)
                else:
                    target.symlink_to(marker_path)

                rejected = self._save(prepared)
                self.assertEqual(rejected["reason_code"],
                                 "validation_handoff_collision", rejected)
                self.assertEqual(source.read_bytes(), source_before)
                self.assertEqual(state_path.read_bytes(), state_before)
                self.assertEqual(marker_path.read_bytes(), marker)
                if kind == "regular":
                    self.assertFalse(target.is_symlink())
                    self.assertEqual(target.read_bytes(), marker)
                else:
                    self.assertTrue(target.is_symlink())
                    self.assertEqual(target.resolve(), marker_path.resolve())
                target.unlink()

    def test_incomplete_batch_mapping_writes_no_output(self):
        prof_b = self.build_second_professor()
        path_a = (self.prof_dir / CANDIDATES_MD).resolve()
        path_b = (prof_b / CANDIDATES_MD).resolve()
        output_a = self.root / "incomplete-map-a.json"
        output_b = self.root / "incomplete-map-b.json"
        result = {
            "result": "ok",
            "files": [self._entry(path_a, "pass"), self._entry(path_b, "pass")],
            "notes": "完整批量正文",
        }
        rejected = self._fixed_write(result, output_map=[
            {"file": str(path_a), "output_file": str(output_a)},
        ])
        self.assertEqual(rejected.returncode, 1)
        payload = parse(rejected)
        self.assertEqual(payload["reason_code"], "invalid_params", payload)
        self.assertFalse(output_a.exists())
        self.assertFalse(output_b.exists())

    def _call_writer_with_os_fault(self, result, mapping, failed_target, operation):
        """Use real file calls, failing exactly one selected write or read."""
        stdout_bytes = io.BytesIO()
        stdout = io.TextIOWrapper(stdout_bytes, encoding="utf-8")
        output_targets = {Path(item["output_file"]).resolve() for item in mapping}
        tracked_fds = {}
        injected = []
        real_open, real_write, real_read = os.open, os.write, os.read

        def track_open(path, flags, mode=0o777):
            fd = real_open(path, flags, mode)
            resolved = Path(path).resolve()
            if resolved in output_targets:
                tracked_fds[fd] = resolved
            return fd

        def fault_write(fd, data):
            if operation == "write" and tracked_fds.get(fd) == failed_target and not injected:
                injected.append(operation)
                raise OSError("synthetic batch file write failure")
            return real_write(fd, data)

        def fault_read(fd, size):
            if operation == "read" and tracked_fds.get(fd) == failed_target and not injected:
                injected.append(operation)
                return b""
            return real_read(fd, size)

        args = type("WriterArgs", (), {
            "output_file": None,
            "output_map_json": json.dumps(mapping, ensure_ascii=False),
            "result_json": json.dumps(result, ensure_ascii=False),
        })()
        code = 0
        try:
            with contextlib.redirect_stdout(stdout), \
                    mock.patch.object(contact_state.os, "open", side_effect=track_open), \
                    mock.patch.object(contact_state.os, "write", side_effect=fault_write), \
                    mock.patch.object(contact_state.os, "read", side_effect=fault_read):
                try:
                    contact_state.cmd_stage3_write_validation(args)
                except SystemExit as exc:
                    code = exc.code if isinstance(exc.code, int) else 1
        finally:
            stdout.flush()
        return stdout_bytes.getvalue(), code, injected

    def _batch_writer_fixture(self):
        prof_b = self.build_second_professor()
        path_a = (self.prof_dir / CANDIDATES_MD).resolve()
        path_b = (prof_b / CANDIDATES_MD).resolve()
        output_a = self.root / "batch-fault-a.json"
        output_b = self.root / "batch-fault-b.json"
        result = {
            "result": "ok",
            "files": [self._entry(path_a, "pass"), self._entry(path_b, "pass")],
            "notes": "两位教授的完整批量正文",
        }
        mapping = [
            {"file": str(path_a), "output_file": str(output_a)},
            {"file": str(path_b), "output_file": str(output_b)},
        ]
        return output_a, output_b, result, mapping

    def test_batch_write_failure_keeps_completed_file_and_removes_incomplete_file(self):
        output_a, output_b, result, mapping = self._batch_writer_fixture()
        stdout, code, injected = self._call_writer_with_os_fault(
            result, mapping, output_b.resolve(), "write")
        payload = json.loads(stdout)
        self.assertEqual(code, 1)
        self.assertEqual(injected, ["write"])
        self.assertEqual(payload["reason_code"], "validation_write_failed", payload)
        expected = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=1)
                    + "\n").encode("utf-8")
        self.assertEqual(output_a.read_bytes(), expected)
        self.assertFalse(output_b.exists())
        self.assertEqual(payload["completed_paths"], [str(output_a)])

    def test_batch_readback_failure_removes_only_incomplete_file(self):
        output_a, output_b, result, mapping = self._batch_writer_fixture()
        stdout, code, injected = self._call_writer_with_os_fault(
            result, mapping, output_b.resolve(), "read")
        payload = json.loads(stdout)
        self.assertEqual(code, 1)
        self.assertEqual(injected, ["read"])
        self.assertEqual(payload["reason_code"], "validation_write_failed", payload)
        expected = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=1)
                    + "\n").encode("utf-8")
        self.assertEqual(output_a.read_bytes(), expected)
        self.assertFalse(output_b.exists())
        self.assertEqual(payload["completed_paths"], [str(output_a)])


if __name__ == "__main__":
    unittest.main()
