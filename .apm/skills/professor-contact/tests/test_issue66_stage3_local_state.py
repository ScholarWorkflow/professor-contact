"""Focused Stage 3 professor-local commit and overview regressions for issue #66."""
import contextlib
import io
import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

from test_stage2_resolved_direction import parse, run_cli, write_json
from test_stage3_direction_groups import (
    PROFESSOR, QUOTES, SECOND_PROFESSOR, Stage3DirectionGroupBase,
    contact_state, result_file,
)

CANDIDATE_STATE = "套磁候选状态.json"
CANDIDATES_MD = "套磁想法候选.md"
CANDIDATES_OVERVIEW = "套磁想法候选总览.md"
CROSS_GROUPS = '[["dir_A","dir_B"]]'
CROSS_GID = contact_state.cross_group_id(["dir_A", "dir_B"])


def call_runner(*argv):
    """Invoke the real CLI dispatcher in-process for standard-library fault injection."""
    stdout = io.StringIO()
    old_argv = sys.argv
    code = 0
    try:
        sys.argv = ["contact_state.py", *[str(arg) for arg in argv]]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            try:
                contact_state.main()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = old_argv
    return json.loads(stdout.getvalue()), code


class Issue66LocalStateTests(Stage3DirectionGroupBase):
    def setUp(self):
        super().setUp()
        self.overview_path = self.root / "教授研究" / CANDIDATES_OVERVIEW

    def _overview_body(self):
        _header, body = contact_state.split_frontmatter(
            self.overview_path.read_text(encoding="utf-8"))
        return body

    @staticmethod
    def _overview_business_lines(body):
        """Compare the stable projection while excluding its render timestamp."""
        return [line for line in body.splitlines() if not line.startswith("> ")]

    def _write_two_professors_with_matching_ids(self):
        """Commit two isolated professor states with identical machine IDs."""
        results_a = self.write_results("issue66-a", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None]),
        })
        group_a = self.cross_candidate(
            "cross_a", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
            gap_owner={"P2": "dir_A", "P3": "dir_B"})
        group_a["title"] = "甲教授跨方向候选"
        write_json(results_a / result_file("candidates", CROSS_GID),
                   self.cross_doc(["dir_A", "dir_B"], [group_a]))
        out_a = self.stage3_finalize(
            results_a, "--cross-direction-groups", CROSS_GROUPS)
        self.assertEqual(out_a["status"], "ok", out_a)

        saved_dir, saved_professor = self.prof_dir, self.professor
        prof_b = self.root / "教授研究" / "Y分野" / SECOND_PROFESSOR
        (prof_b / "论文分析").mkdir(parents=True)
        self.prof_dir, self.professor = prof_b, SECOND_PROFESSOR
        try:
            papers = [
                self.make_paper("P1", "Shared Method Paper", ["method", "shared"],
                                [QUOTES["P1"]]),
                self.make_paper("P2", "Signal Robustness Paper", ["signal", "robust"],
                                [QUOTES["P2"]]),
                self.make_paper("P3", "Campus Sensor Paper", ["sensor", "network"],
                                [QUOTES["P3"]]),
            ]
            directions = [
                self.make_direction("dir_A", ["P1", "P2"], name_ja="信号処理",
                                    name_zh="信号处理", summary="信号处理方向"),
                self.make_direction("dir_B", ["P1", "P3"], name_ja="センサ網",
                                    name_zh="传感网络", summary="传感网络方向"),
            ]
            facts_path = self.write_facts(papers, directions, name="facts-b.json")
            self.run_resolve(facts_path, {})
            stage2 = self.run_stage2_finalize(facts_path)
            self.assertEqual(stage2["status"], "ok", stage2)
            results_b = self.write_results("issue66-b", {
                "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
                "dir_B": self.generated_doc("dir_B", ["P1", "P3", None]),
            })
            group_b1 = self.cross_candidate(
                "cross_b1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                gap_owner={"P2": "dir_A", "P3": "dir_B"})
            group_b1["title"] = "乙教授跨方向候选一"
            group_b2 = self.cross_candidate(
                "cross_b2", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                gap_owner={"P2": "dir_A", "P3": "dir_B"})
            group_b2["title"] = "乙教授跨方向候选二"
            write_json(results_b / result_file("candidates", CROSS_GID),
                       self.cross_doc(["dir_A", "dir_B"], [group_b1, group_b2]))
            out_b = parse(run_cli(
                "stage3-finalize", "--professor-dir", prof_b,
                "--results", results_b, "--program-root", self.root,
                "--cross-direction-groups", CROSS_GROUPS))
            self.assertEqual(out_b["status"], "ok", out_b)
        finally:
            self.prof_dir, self.professor = saved_dir, saved_professor
        return prof_b

    def test_local_finalize_restores_both_files_when_state_install_fails(self):
        old_results = self.write_results("issue66-commit-old", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None])})
        self.assertEqual(self.stage3_finalize(old_results, "--direction-id", "dir_A")["status"],
                         "ok")
        md_path = self.prof_dir / CANDIDATES_MD
        state_path = self.prof_dir / CANDIDATE_STATE
        old_md, old_state = md_path.read_bytes(), state_path.read_bytes()

        changed = self.generated_doc("dir_A", ["P1", "P2", None])
        changed["candidates"][0]["title"] = "提交失败前的新候选"
        results = self.write_results("issue66-commit-new", {"dir_A": changed})
        real_replace = os.replace
        state_attempts = 0

        def fail_one_state_install(source, target):
            nonlocal state_attempts
            if Path(target).resolve() == state_path.resolve() and state_attempts == 0:
                state_attempts += 1
                raise OSError("synthetic second-file installation failure")
            return real_replace(source, target)

        with mock.patch.object(contact_state.os, "replace",
                               side_effect=fail_one_state_install):
            payload, code = call_runner(
                "stage3-finalize", "--professor-dir", self.prof_dir,
                "--results", results, "--program-root", self.root,
                "--direction-id", "dir_A")

        self.assertEqual(code, 1)
        self.assertEqual(payload["reason_code"], "local_pair_commit_failed", payload)
        self.assertEqual(state_attempts, 1)
        self.assertEqual(md_path.read_bytes(), old_md)
        self.assertEqual(state_path.read_bytes(), old_state)

    def test_staged_pair_keeps_committed_files_when_cleanup_fails(self):
        old_results = self.write_results("issue66-cleanup-old", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None])})
        self.assertEqual(self.stage3_finalize(old_results, "--direction-id", "dir_A")["status"],
                         "ok")
        md_path = self.prof_dir / CANDIDATES_MD
        state_path = self.prof_dir / CANDIDATE_STATE
        old_md, old_state = md_path.read_bytes(), state_path.read_bytes()
        new_md = old_md.decode("utf-8") + "\n提交后的新候选\n"
        new_state = json.loads(old_state)
        new_state["cleanup_failure_test"] = "committed"
        new_state = json.dumps(new_state, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
        real_unlink = Path.unlink
        failed_cleanup = []
        staged_names = (f".{CANDIDATES_MD}.", f".{CANDIDATE_STATE}.")

        def fail_staged_cleanup(path, *args, **kwargs):
            path = Path(path)
            if path.parent == self.prof_dir and path.name.startswith(staged_names):
                failed_cleanup.append(path)
                raise OSError("synthetic post-commit cleanup failure")
            return real_unlink(path, *args, **kwargs)

        with mock.patch.object(Path, "unlink", autospec=True,
                               side_effect=fail_staged_cleanup):
            contact_state.staged_pair_commit([
                (md_path, new_md), (state_path, new_state)])

        self.assertEqual(len(failed_cleanup), 2)
        self.assertNotEqual(old_md, md_path.read_bytes())
        self.assertNotEqual(old_state, state_path.read_bytes())
        self.assertEqual(md_path.read_text(encoding="utf-8"), new_md)
        self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")),
                         json.loads(new_state))

    def test_local_candidate_manual_edit_refuses_overwrite(self):
        results = self.write_results("issue66-manual-edit", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None])})
        self.assertEqual(self.stage3_finalize(results, "--direction-id", "dir_A")["status"],
                         "ok")
        md_path = self.prof_dir / CANDIDATES_MD
        md_path.write_bytes(md_path.read_bytes() + "\n人工保留的一行\n".encode("utf-8"))
        manual_bytes = md_path.read_bytes()
        out = self.stage3_finalize(results, "--direction-id", "dir_A")
        self.assertEqual(out["status"], "needs_decision", out)
        self.assertEqual(out["reason_code"], "manual_markdown_changed")
        self.assertEqual(md_path.read_bytes(), manual_bytes)

    def test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection(self):
        prof_b = self._write_two_professors_with_matching_ids()
        md_a = self.prof_dir / CANDIDATES_MD
        md_b = prof_b / CANDIDATES_MD
        md_a.write_text("not a source of candidate rows\n", encoding="utf-8")
        md_b.write_text("also not a source of candidate rows\n", encoding="utf-8")
        state_a = self.prof_dir / CANDIDATE_STATE
        state_b = prof_b / CANDIDATE_STATE
        state_bytes = (state_a.read_bytes(), state_b.read_bytes())

        first = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(first["status"], "ok", first)
        self.assertEqual(first["professor_count"], 2)
        body = self._overview_body()
        link_a = f"X分野/{PROFESSOR}/{CANDIDATES_MD}"
        link_b = f"Y分野/{SECOND_PROFESSOR}/{CANDIDATES_MD}"
        self.assertIn(f"| {PROFESSOR} | 信号処理 | 3 | 主推 1 | [{CANDIDATES_MD}]({link_a}) |", body)
        self.assertIn(f"| {SECOND_PROFESSOR} | 信号処理 | 3 | 主推 1 | [{CANDIDATES_MD}]({link_b}) |", body)
        self.assertIn(f"| {PROFESSOR} | 跨方向：dir_A＋dir_B | 1 | 显式跨方向组（group_id {CROSS_GID}） | [{CANDIDATES_MD}]({link_a}) |", body)
        self.assertIn(f"| {SECOND_PROFESSOR} | 跨方向：dir_A＋dir_B | 2 | 显式跨方向组（group_id {CROSS_GID}） | [{CANDIDATES_MD}]({link_b}) |", body)
        self.assertLess(body.index(link_a), body.index(link_b))
        self.assertNotIn("not a source of candidate rows", body)
        self.assertNotIn("also not a source of candidate rows", body)
        self.assertEqual((state_a.read_bytes(), state_b.read_bytes()), state_bytes)

        self.overview_path.unlink()
        rebuilt = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(rebuilt["status"], "ok", rebuilt)
        self.assertEqual(
            self._overview_business_lines(self._overview_body()),
            self._overview_business_lines(body),
        )
        self.assertEqual((state_a.read_bytes(), state_b.read_bytes()), state_bytes)

    def test_rebuild_overview_keeps_old_bytes_when_a_discovered_state_is_malformed(self):
        prof_b = self.build_second_professor()
        self.assertEqual(parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))["status"],
                         "ok")
        old_overview = self.overview_path.read_bytes()
        state_b = prof_b / CANDIDATE_STATE
        state_b.write_bytes(b"{ malformed committed state")
        malformed = state_b.read_bytes()

        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "error", out)
        self.assertTrue(out["reason_code"].startswith("invalid:"), out)
        self.assertEqual(self.overview_path.read_bytes(), old_overview)
        self.assertEqual(state_b.read_bytes(), malformed)

    def test_rebuild_overview_only_migrates_a_unique_legacy_identity(self):
        prof_b = self.build_second_professor()
        b_state = prof_b / CANDIDATE_STATE
        b_pack = prof_b / "套磁候选输入.json"
        pack = json.loads(b_pack.read_text(encoding="utf-8"))
        collection_key = pack["directions"][0]["collection_key"]
        legacy_candidate = {
            "id": "legacy-1", "title": "旧候选", "one_liner": "一句话",
            "research_question": "旧问题", "points": [], "gap_ids": [],
            "papers": [], "fit": "high", "fit_note": "",
            "why_recommended": "旧理由", "tension_points": [],
        }

        def write_legacy(key):
            write_json(b_state, {
                "schema": 1,
                "professor": SECOND_PROFESSOR,
                "directions": [{"collection_key": key,
                                "name_ja": "对照", "name_zh": "对照",
                                "candidates": [legacy_candidate]}],
                "input_fingerprints": {key: "legacy-fingerprint"},
            })

        self.assertEqual(parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))["status"],
                         "ok")
        old_overview = self.overview_path.read_bytes()

        write_legacy("missing-identity")
        state_before = b_state.read_bytes()
        out_zero = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out_zero["reason_code"], "legacy_direction_identity", out_zero)
        self.assertEqual(self.overview_path.read_bytes(), old_overview)
        self.assertEqual(b_state.read_bytes(), state_before)

        write_legacy(collection_key)
        state_before = b_state.read_bytes()
        one_match = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(one_match["status"], "ok", one_match)
        self.assertEqual(b_state.read_bytes(), state_before)
        self.assertIn(
            f"| {SECOND_PROFESSOR} | 对照 | 1 | — | "
            f"[{CANDIDATES_MD}](Y分野/{SECOND_PROFESSOR}/{CANDIDATES_MD}) |",
            self._overview_body())

        duplicate = json.loads(json.dumps(pack["directions"][0]))
        duplicate["direction_id"] = "dir_D"
        duplicate["name_ja"] = "另一个方向"
        pack["directions"].append(duplicate)
        write_json(b_pack, pack)
        write_legacy(collection_key)
        state_before = b_state.read_bytes()
        overview_before = self.overview_path.read_bytes()
        multiple = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(multiple["reason_code"], "legacy_direction_identity", multiple)
        self.assertEqual(self.overview_path.read_bytes(), overview_before)
        self.assertEqual(b_state.read_bytes(), state_before)


if __name__ == "__main__":
    unittest.main()
