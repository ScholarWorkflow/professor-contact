"""Issue #66 deterministic product-behavior acceptance cases.

Stage 3 must give every professor an independent formal state: stage3-finalize
commits only the current professor (local Markdown installed first, candidate
state last as the single commit marker) and never touches program-level
state; the program overview is a derived projection rebuilt by
stage3-rebuild-overview from committed states alone, with projection-local
manual-edit protection and strict legacy identity migration owned by the
candidate-state compatibility layer.

Proof conventions (per the frozen Gate 2 record): no-write / rollback /
bytes / absence claims read the target files directly; low-level open and
os.replace wrappers only record or gate real calls and never replace return
values or mock the owner under test; synchronization uses events, never
sleeps.  Reused fixtures: the repo BaseEnv pipeline and the cross-direction
group builder from test_stage3_direction_groups.
"""
import builtins
import contextlib
import io
import itertools
import json
import os
import shutil
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

from test_stage2_resolved_direction import (
    parse, quote_id, run_cli, write_json)
from test_stage3_direction_groups import (
    PROFESSOR, Stage3DirectionGroupBase, contact_state, result_file)

CANDIDATE_STATE = "套磁候选状态.json"
CANDIDATES_MD = "套磁想法候选.md"
CANDIDATES_OVERVIEW = "套磁想法候选总览.md"
PROJECTIONS_FILE = "_contact_projections.json"
CROSS_GROUP_ARG = '[["dir_A","dir_B"]]'
CROSS_GID = contact_state.cross_group_id(["dir_A", "dir_B"])
SECOND_PROFESSOR = "対照 教授"

# Twin-professor quotes: same display name / direction IDs / group ID as the
# base fixture, different canonical professor directory (issue #66 R66-4).
TWIN_QUOTES = {
    "T1": "Future work will extend the twin shared method to batch inputs.",
    "T2": "Future work will benchmark the twin signal pipeline at scale.",
    "T3": "Future work will deploy the twin sensor network citywide.",
}


def call_runner(*argv):
    """Run the deterministic runner in-process; returns (payload, exit_code).

    Used only where low-level wrappers must observe the real call window;
    the subprocess CLI surface stays covered by the run_cli-based cases.
    """
    buffer = io.StringIO()
    old_argv = sys.argv
    code = 0
    try:
        sys.argv = ["contact_state.py", *[str(a) for a in argv]]
        with contextlib.redirect_stdout(buffer), \
                contextlib.redirect_stderr(io.StringIO()):
            try:
                contact_state.main()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = old_argv
    try:
        return json.loads(buffer.getvalue()), code
    except json.JSONDecodeError:
        return None, code


class OpenRecorder:
    """Record the absolute path of every real low-level file open.

    The wrappers only forward: return values, errors and buffering are the
    real ones, so the record is a read log, not a substitute for the owner.
    """

    def __init__(self):
        self.opened = []

    @staticmethod
    def _normalize(path):
        return os.path.realpath(os.path.abspath(str(path)))

    def __enter__(self):
        self.opened = []
        recorder = self
        orig_open = builtins.open
        orig_io_open = io.open
        orig_os_open = os.open

        def wrapped_open(file, *args, **kwargs):
            recorder.opened.append(recorder._normalize(file))
            return orig_open(file, *args, **kwargs)

        def wrapped_os_open(path, *args, **kwargs):
            recorder.opened.append(recorder._normalize(path))
            return orig_os_open(path, *args, **kwargs)

        self._orig = (orig_open, orig_io_open, orig_os_open)
        # pathlib.Path.open resolves through io.open, not builtins.open, so
        # both bindings must be wrapped to see every real text/binary open.
        builtins.open = wrapped_open
        io.open = wrapped_open
        os.open = wrapped_os_open
        return self

    def __exit__(self, *exc_info):
        builtins.open, io.open, os.open = self._orig
        return False

    def was_opened(self, path):
        return self._normalize(path) in self.opened


@contextlib.contextmanager
def gated_os_replace(predicate, action):
    """Wrap os.replace: matching installs are owned by `action(real, src, dst)`.

    The wrapper hands the real os.replace to the action, which decides whether
    to perform it, block around it, or raise instead; non-matching calls are
    forwarded untouched.
    """
    real = os.replace

    def wrapped(src, dst, *args, **kwargs):
        if predicate(os.path.realpath(os.path.abspath(str(src))),
                     os.path.realpath(os.path.abspath(str(dst)))):
            return action(real, src, dst)
        return real(src, dst)

    with mock.patch("os.replace", wrapped):
        yield


@contextlib.contextmanager
def failing_unlink(predicate):
    """Wrap os.unlink so matching cleanup targets raise a synthetic OSError."""
    real = os.unlink

    def wrapped(path, *args, **kwargs):
        if predicate(os.path.realpath(os.path.abspath(str(path)))):
            raise OSError("synthetic cleanup unlink failure")
        return real(path, *args, **kwargs)

    with mock.patch("os.unlink", wrapped):
        yield


class TestIssue66Stage3(Stage3DirectionGroupBase):
    """One professor A (dir_A/dir_B + shared paper) from the shared builder."""

    def setUp(self):
        super().setUp()
        self.overview_path = self.root / "教授研究" / CANDIDATES_OVERVIEW
        self.registry_path = self.root / "教授研究" / PROJECTIONS_FILE

    # -- shared helpers ---------------------------------------------------

    def write_a_results(self, name, docs=None):
        docs = docs or {"dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
                        "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])}
        return self.write_results(name, docs)

    def write_a_cross(self, results):
        """Write professor A's explicit cross-direction group result."""
        write_json(results / result_file("candidates", CROSS_GID),
                   {"schema": 2, "kind": "cross_candidates",
                    "group_id": CROSS_GID, "direction_ids": ["dir_A", "dir_B"],
                    "candidates": [self.cross_candidate(
                        "XA", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                        gap_owner={"P2": "dir_A", "P3": "dir_B"})]})
        return results

    def finalize_a_ok(self, name="s3-a", *extra):
        results = self.write_a_results(name)
        out = self.stage3_finalize(results, *extra)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return out

    def snapshot(self, *paths):
        return {Path(p): (Path(p).read_bytes() if Path(p).exists() else None)
                for p in paths}

    def assert_unchanged(self, before):
        for path, old in before.items():
            current = path.read_bytes() if path.exists() else None
            self.assertEqual(current, old, f"unexpected change: {path}")

    def overview_business_body(self):
        """Overview body minus the volatile generation-timestamp line."""
        _, body = contact_state.split_frontmatter(
            self.overview_path.read_text(encoding="utf-8"))
        return "\n".join(line for line in body.splitlines()
                         if not line.startswith("> 2"))

    def build_twin_professor(self):
        """Second professor with the SAME display name, direction IDs and
        cross-group ID as professor A, in a different canonical directory."""
        self.twin_gap_ids = {key: quote_id(quote)
                             for key, quote in TWIN_QUOTES.items()}
        saved_dir, saved_professor = self.prof_dir, self.professor
        twin_dir = self.root / "教授研究" / "Y分野" / PROFESSOR
        (twin_dir / "论文分析").mkdir(parents=True)
        self.prof_dir, self.professor = twin_dir, PROFESSOR
        try:
            papers = [
                self.make_paper("T1", "Twin Shared Method Paper",
                                ["twin", "shared"], [TWIN_QUOTES["T1"]]),
                self.make_paper("T2", "Twin Signal Paper",
                                ["twin", "signal"], [TWIN_QUOTES["T2"]]),
                self.make_paper("T3", "Twin Sensor Paper",
                                ["twin", "sensor"], [TWIN_QUOTES["T3"]]),
            ]
            directions = [
                self.make_direction("dir_A", ["T1", "T2"], name_ja="信号処理",
                                    name_zh="信号处理", summary="Twin 信号处理"),
                self.make_direction("dir_B", ["T1", "T3"], name_ja="センサ網",
                                    name_zh="传感网络", summary="Twin 传感网络"),
            ]
            facts_path = self.write_facts(papers, directions, name="facts-twin.json")
            self.run_resolve(facts_path, {})
            payload = self.run_stage2_finalize(facts_path)
            self.assertEqual(payload["status"], "ok",
                             msg=json.dumps(payload, ensure_ascii=False))
        finally:
            self.prof_dir, self.professor = saved_dir, saved_professor
        self.twin_dir = twin_dir
        return twin_dir

    def twin_candidate(self, cid, item_key, direction_id="dir_A"):
        candidate = {"id": cid, "kind": "direction",
                     "direction_ids": [direction_id], "origin": "generated",
                     "title": f"候选 {cid}",
                     "one_liner": "教授的 Twin 工作启发我思考延伸方向",
                     "research_question": "该方法在批量输入下是否保持相同收敛性？",
                     "points": [], "gap_refs": [], "papers": [],
                     "fit": "high", "fit_note": "", "red_lines": [],
                     "why_recommended": "兴趣契合", "tension_points": []}
        if item_key is not None:
            candidate["points"] = ["挂在缺口 1"]
            candidate["gap_refs"] = [{"direction_id": direction_id,
                                      "item_key": item_key,
                                      "gap_id": self.twin_gap_ids[item_key]}]
            candidate["papers"] = [{"item_key": item_key,
                                    "direction_ids": [direction_id],
                                    "role": "基座", "fit_note": "教授通讯"}]
        return candidate

    def twin_doc(self, ckey, item_keys, priority):
        return {"schema": 2, "kind": "candidates", "direction_id": ckey,
                "mode": "generated", "priority": priority,
                "candidates": [self.twin_candidate(f"{ckey}_{n}", key,
                                                   direction_id=ckey)
                               for n, key in enumerate(item_keys, start=1)]}

    def twin_cross_candidate(self, cid):
        idea = self.twin_candidate(cid, None)
        idea["kind"] = "cross_direction"
        idea["direction_ids"] = ["dir_A", "dir_B"]
        idea["gap_refs"] = [
            {"direction_id": "dir_A", "item_key": "T2",
             "gap_id": self.twin_gap_ids["T2"]},
            {"direction_id": "dir_B", "item_key": "T3",
             "gap_id": self.twin_gap_ids["T3"]}]
        idea["papers"] = [{"item_key": "T1", "direction_ids": ["dir_A", "dir_B"],
                           "role": "共同基座", "fit_note": "共享论文"}]
        return idea

    def finalize_twin_ok(self, priority_a, cross_count=1):
        """Finalize the twin: dir_A with 4 candidates, dir_B with 3."""
        results = self.root / "twin-s3results"
        results.mkdir(parents=True, exist_ok=True)
        write_json(results / result_file("candidates", "dir_A"),
                   self.twin_doc("dir_A", ["T1", "T2", "T1", "T2"], priority_a))
        write_json(results / result_file("candidates", "dir_B"),
                   self.twin_doc("dir_B", ["T1", "T3", None], "并推 Twin"))
        cross = [self.twin_cross_candidate(f"XB{n}")
                 for n in range(1, cross_count + 1)]
        write_json(results / result_file("candidates", CROSS_GID),
                   {"schema": 2, "kind": "cross_candidates",
                    "group_id": CROSS_GID, "direction_ids": ["dir_A", "dir_B"],
                    "candidates": cross})
        saved_dir, saved_professor = self.prof_dir, self.professor
        self.prof_dir, self.professor = self.twin_dir, PROFESSOR
        try:
            out = self.stage3_finalize(results, "--cross-direction-groups",
                                       CROSS_GROUP_ARG)
        finally:
            self.prof_dir, self.professor = saved_dir, saved_professor
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return out

    # -- S3-ISO-1 ---------------------------------------------------------

    def test_s3_iso_1_local_finalize_isolation(self):
        """Each single-variable anomaly leaves A's local commit intact.

        Per the frozen recipe the three sub-scenarios run SEPARATELY, each
        with exactly ONE non-owner disturbance in place; A's finalize must
        succeed, the disturbed object's exact bytes must survive, the other
        non-owner objects must stay absent, and the low-level open record
        must prove finalize never opened any of the three.
        """
        a_pack = self.prof_dir / "套磁候选输入.json"
        a_results = self.write_a_results("s3-iso-1")
        foreign_state = self.root / "教授研究" / "Y分野" / SECOND_PROFESSOR / CANDIDATE_STATE

        def reset_single_variable_baseline():
            shutil.rmtree(self.root / "教授研究" / "Y分野", ignore_errors=True)
            self.overview_path.unlink(missing_ok=True)
            self.registry_path.unlink(missing_ok=True)

        for disturbance in ("b_state_malformed", "overview_conflict",
                            "registry_malformed"):
            with self.subTest(scenario=disturbance):
                reset_single_variable_baseline()
                if disturbance == "b_state_malformed":
                    foreign_state.parent.mkdir(parents=True, exist_ok=True)
                    foreign_state.write_text("{ malformed foreign state",
                                             encoding="utf-8")
                    disturbed = foreign_state
                elif disturbance == "overview_conflict":
                    self.overview_path.write_text("手工改过的总览\n", encoding="utf-8")
                    disturbed = self.overview_path
                else:
                    self.registry_path.write_text("{ malformed registry",
                                                  encoding="utf-8")
                    disturbed = self.registry_path
                before = self.snapshot(disturbed)

                with OpenRecorder() as recorder:
                    payload, code = call_runner(
                        "stage3-finalize", "--professor-dir", self.prof_dir,
                        "--results", a_results, "--program-root", self.root)
                self.assertEqual(code, 0)
                self.assertEqual(payload["status"], "ok", payload)
                self.assert_unchanged(before)
                # Single variable: the two undisturbed non-owner objects
                # must remain absent for this run.
                for other in (foreign_state, self.overview_path, self.registry_path):
                    if other != disturbed:
                        self.assertFalse(other.exists(),
                                         f"unexpected non-owner object: {other}")
                # Negative proof: none of the three forbidden paths opened.
                for forbidden in (foreign_state, self.overview_path,
                                  self.registry_path):
                    self.assertFalse(recorder.was_opened(forbidden))
                # Positive control: the recorder sees A's own real reads.
                self.assertTrue(recorder.was_opened(a_pack))

    # -- S3-ISO-3 ---------------------------------------------------------

    def test_s3_iso_3_local_manual_conflict(self):
        """A's own manually edited local Markdown still fails closed."""
        self.finalize_a_ok("s3-iso-3")
        md_path = self.prof_dir / CANDIDATES_MD
        state_path = self.prof_dir / CANDIDATE_STATE
        md_path.write_text(
            md_path.read_text(encoding="utf-8") + "\n人工修改的一行\n",
            encoding="utf-8")
        manual_md = md_path.read_bytes()
        before = self.snapshot(state_path, self.overview_path, self.registry_path)

        out = self.stage3_finalize(self.write_a_results("s3-iso-3-reuse"))

        self.assertEqual(out["status"], "needs_decision", out)
        self.assertEqual(out["reason_code"], "manual_markdown_changed")
        self.assert_unchanged(before)
        self.assertEqual(md_path.read_bytes(), manual_md)

    # -- S3-ISO-4 ---------------------------------------------------------

    def test_s3_iso_4_commit_marker(self):
        """Markdown-first / state-last commit marker with real fault windows."""
        self.finalize_a_ok("s3-iso-4")
        md_path = self.prof_dir / CANDIDATES_MD
        state_path = self.prof_dir / CANDIDATE_STATE
        old_md, old_state = md_path.read_bytes(), state_path.read_bytes()
        a_results = self.write_a_results("s3-iso-4-reuse")
        # A changed profile makes the re-render deterministically different
        # from the old bytes (render header 校准 flip), so "new Markdown
        # installed" is byte-observable even when the clock has not ticked.
        profile = self.root / "iso4-profile.md"
        profile.write_text("兴趣：第二种输入模式的比较\n", encoding="utf-8")
        profile_args = ("--profile", str(profile))

        # 1. Pause after the Markdown install, before the state replace: a
        #    concurrent reader sees the NEW Markdown already installed while
        #    the candidate state is still the OLD committed one, and the
        #    failing state replace restores both old byte sets.
        attempted, released = threading.Event(), threading.Event()
        observed = {}

        def reader():
            self.assertTrue(attempted.wait(30))
            observed["state"] = state_path.read_bytes()
            observed["md"] = md_path.read_bytes()
            released.set()

        def gate(real, src, dst):
            if Path(dst) == state_path:
                attempted.set()
                self.assertTrue(released.wait(30))
                raise OSError("synthetic candidate-state install failure")

        watcher = threading.Thread(target=reader)
        watcher.start()
        try:
            with gated_os_replace(
                    lambda src, dst: dst == os.path.realpath(state_path), gate):
                payload, code = call_runner(
                    "stage3-finalize", "--professor-dir", self.prof_dir,
                    "--results", a_results, "--program-root", self.root,
                    *profile_args)
        finally:
            watcher.join(30)
        self.assertEqual(payload["reason_code"], "local_pair_commit_failed", payload)
        self.assertEqual(observed["state"], old_state,
                         "a reader before the commit point saw new state bytes")
        self.assertNotEqual(observed["md"], old_md,
                            "the new Markdown was not installed before the "
                            "state replace: install order not observable")
        self.assertEqual(md_path.read_bytes(), old_md)
        self.assertEqual(state_path.read_bytes(), old_state)

        # 2. Release the state replace: the reader only after the atomic
        #    replace sees the NEW committed state whose render SHA matches
        #    the installed Markdown body.
        attempted, released = threading.Event(), threading.Event()
        observed = {}

        def reader_after_install():
            self.assertTrue(attempted.wait(30))
            observed["state"] = json.loads(state_path.read_text(encoding="utf-8"))
            released.set()

        def install_then_release(real, src, dst):
            real(src, dst)  # the atomic install has happened at this point
            attempted.set()
            self.assertTrue(released.wait(30))

        watcher = threading.Thread(target=reader_after_install)
        watcher.start()
        try:
            with gated_os_replace(
                    lambda src, dst: dst == os.path.realpath(state_path),
                    install_then_release):
                payload, code = call_runner(
                    "stage3-finalize", "--professor-dir", self.prof_dir,
                    "--results", a_results, "--program-root", self.root,
                    *profile_args)
        finally:
            watcher.join(30)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok", payload)
        _, md_body = contact_state.split_frontmatter(
            md_path.read_text(encoding="utf-8"))
        self.assertEqual(observed["state"]["cache"]["render"][CANDIDATES_MD]["sha256"],
                         contact_state.sha256_text(md_body))

        # 3. Post-commit cleanup unlink failure: both new byte sets stay, the
        #    committed transaction is not rolled back or re-framed. A second
        #    profile makes this transaction's content deterministically
        #    different from the previous run's committed pair (the frontmatter
        #    state_fingerprint binds the profile), so retention of the NEW
        #    bytes is provable even within the same second.
        previous_md = md_path.read_bytes()
        previous_state_bytes = state_path.read_bytes()
        previous_state = json.loads(previous_state_bytes)
        profile2 = self.root / "iso4-profile-2.md"
        profile2.write_text("兴趣变化：第二种输入模式的扩展比较\n", encoding="utf-8")
        profile2_args = ("--profile", str(profile2))
        staged_prefixes = (f".{CANDIDATES_MD}.", f".{CANDIDATE_STATE}.")
        owner_dir = os.path.realpath(self.prof_dir)

        def cleanup_target(path):
            return (os.path.dirname(path) == owner_dir
                    and Path(path).name.startswith(staged_prefixes))

        with failing_unlink(cleanup_target):
            payload, code = call_runner(
                "stage3-finalize", "--professor-dir", self.prof_dir,
                "--results", a_results, "--program-root", self.root,
                *profile2_args)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok", payload)
        current_state = json.loads(state_path.read_text(encoding="utf-8"))
        _, md_body = contact_state.split_frontmatter(
            md_path.read_text(encoding="utf-8"))
        self.assertEqual(current_state["cache"]["render"][CANDIDATES_MD]["sha256"],
                         contact_state.sha256_text(md_body))
        # Review C2: the old pair is self-consistent too, so consistency
        # alone cannot prove retention. Both retained files must be THIS
        # transaction's new content — not the previous run's committed pair
        # (a cleanup-failure rollback would restore exactly those bytes).
        self.assertNotEqual(md_path.read_bytes(), previous_md,
                            "cleanup failure must not roll the local Markdown "
                            "back to the previous run's bytes")
        self.assertNotEqual(state_path.read_bytes(), previous_state_bytes,
                            "cleanup failure must not roll the candidate state "
                            "back to the previous run's bytes")
        self.assertNotEqual(current_state["profile_fingerprint"],
                            previous_state["profile_fingerprint"])
        self.assertEqual(current_state["profile_fingerprint"],
                         contact_state.profile_fingerprint(str(profile2)))
        self.assertIn("profile：有", md_path.read_text(encoding="utf-8"))

    # -- S3-ISO-5 ---------------------------------------------------------

    def test_s3_iso_5_aggregate_identity_derivation(self):
        """Same display name / IDs across professors stay separate rows."""
        self.build_twin_professor()
        a_results = self.write_a_cross(self.write_a_results("s3-iso-5-a"))
        out = self.stage3_finalize(a_results, "--cross-direction-groups",
                                   CROSS_GROUP_ARG)
        self.assertEqual(out["status"], "ok",
                         msg=json.dumps(out, ensure_ascii=False))
        self.finalize_twin_ok(priority_a="主推 候选1（Y分野）", cross_count=2)
        a_state = self.prof_dir / CANDIDATE_STATE
        twin_state = self.twin_dir / CANDIDATE_STATE
        # Local Markdowns are manually corrupted AFTER the commits: the
        # overview must not take a single fact from them.
        for path in (self.prof_dir / CANDIDATES_MD, self.twin_dir / CANDIDATES_MD):
            path.write_text(path.read_text(encoding="utf-8") + "\n与状态矛盾的人工行\n",
                            encoding="utf-8")
        states_before = self.snapshot(a_state, twin_state)

        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["professor_count"], 2)
        body = self.overview_business_body()
        a_link = "X分野/試験 教授/套磁想法候选.md"
        twin_link = "Y分野/試験 教授/套磁想法候选.md"
        # One direction row per (canonical professor, direction), values from
        # each committed state; the corrupted Markdown contributes only links.
        self.assertIn(f"| 試験 教授 | 信号処理 | 3 | 主推 1 | [{CANDIDATES_MD}]({a_link}) |",
                      body)
        self.assertIn(f"| 試験 教授 | 信号処理 | 4 | 主推 候选1（Y分野） | [{CANDIDATES_MD}]({twin_link}) |",
                      body)
        self.assertIn(f"| 試験 教授 | センサ網 | 3 | 主推 1 | [{CANDIDATES_MD}]({a_link}) |", body)
        self.assertIn(f"| 試験 教授 | センサ網 | 3 | 并推 Twin | [{CANDIDATES_MD}]({twin_link}) |", body)
        # Cross rows keep the same group ID for both professors, and each
        # row's candidate count comes from its OWN committed state (1 vs 2).
        self.assertIn(f"| 試験 教授 | 跨方向：dir_A＋dir_B | 1 | 显式跨方向组（group_id {CROSS_GID}） | [{CANDIDATES_MD}]({a_link}) |",
                      body)
        self.assertIn(f"| 試験 教授 | 跨方向：dir_A＋dir_B | 2 | 显式跨方向组（group_id {CROSS_GID}） | [{CANDIDATES_MD}]({twin_link}) |",
                      body)
        self.assertNotIn("与状态矛盾的人工行", body)
        # Stable ordering: canonical professor identity is the tie-breaker.
        self.assertLess(body.index(a_link), body.index(twin_link))
        self.assert_unchanged(states_before)

        # Delete + rebuild derives the same business rows/links from the
        # committed states alone (only the generation time may differ).
        self.overview_path.unlink()
        out2 = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out2["status"], "ok", out2)
        self.assertEqual(self.overview_business_body(), body)
        self.assert_unchanged(states_before)

    # -- S3-ISO-6 ---------------------------------------------------------

    def test_s3_iso_6_rebuild_failure_legacy(self):
        """Every rebuild failure preserves bytes; legacy identity is strict."""
        self.finalize_a_ok("s3-iso-6-a")
        b_state_path = self.build_second_professor() / CANDIDATE_STATE
        b_pack_path = self.root / "教授研究" / "Y分野" / SECOND_PROFESSOR / "套磁候选输入.json"
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        # Local files of BOTH professors plus the aggregate artifacts: every
        # failure sub-scenario must leave all of them byte-identical.
        snapshot_paths = (self.prof_dir / CANDIDATE_STATE,
                          self.prof_dir / CANDIDATES_MD,
                          b_state_path,
                          self.root / "教授研究" / "Y分野" / SECOND_PROFESSOR / CANDIDATES_MD,
                          self.overview_path, self.registry_path)
        legacy_candidate = {"id": "C1", "title": "旧候选", "one_liner": "一句话",
                            "research_question": "旧的问题", "points": [],
                            "gap_ids": [], "papers": [], "fit": "high",
                            "fit_note": "", "why_recommended": "旧理由",
                            "tension_points": []}

        def write_b_state(payload):
            b_state_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        original_b_state = b_state_path.read_text(encoding="utf-8")
        original_b_pack = b_pack_path.read_text(encoding="utf-8")
        try:
            # (a) malformed committed state → fail before any write.
            b_state_path.write_text("{ malformed", encoding="utf-8")
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertIn("invalid", out["reason_code"])
            self.assert_unchanged(before)

            # (b) legacy collection_key with 0 canonical matches → fail closed
            #     with legacy_direction_identity before any write.
            write_b_state({"schema": 1, "professor": SECOND_PROFESSOR,
                           "directions": [{"collection_key": "CK_UNKNOWN",
                                           "candidates": [legacy_candidate]}],
                           "input_fingerprints": {"CK_UNKNOWN": "legacy-fp"}})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "legacy_direction_identity")
            self.assert_unchanged(before)

            # (c) 1-match legacy identity migrates in memory only: rebuild
            #     succeeds, the v1 state file itself stays byte-identical.
            write_b_state({"schema": 1, "professor": SECOND_PROFESSOR,
                           "directions": [{"collection_key": "dir_C",
                                           "name_ja": "対照", "name_zh": "对照",
                                           "candidates": [legacy_candidate]}],
                           "input_fingerprints": {"dir_C": "legacy-fp"}})
            b_bytes = b_state_path.read_bytes()
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "ok", out)
            self.assertIn(
                f"| {SECOND_PROFESSOR} | 対照 | 1 | — | "
                f"[{CANDIDATES_MD}](Y分野/{SECOND_PROFESSOR}/{CANDIDATES_MD}) |",
                self.overview_business_body())
            self.assertEqual(b_state_path.read_bytes(), b_bytes)

            # (d) two pack directions sharing the referenced collection_key →
            #     multi-match fails closed before any write.
            pack = json.loads(original_b_pack)
            duplicate = json.loads(json.dumps(pack["directions"][0]))
            duplicate["direction_id"] = "dir_D"
            duplicate["name_ja"] = "第二方向"
            pack["directions"].append(duplicate)
            write_json(b_pack_path, pack)
            write_b_state({"schema": 1, "professor": SECOND_PROFESSOR,
                           "directions": [{"collection_key": "dir_C",
                                           "candidates": [legacy_candidate]}],
                           "input_fingerprints": {"dir_C": "legacy-fp"}})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "legacy_direction_identity")
            self.assert_unchanged(before)

            # (d2) review D1: a v2 state with valid schema/kind/identity
            #      stamps but a structurally corrupt directions container
            #      fails closed BEFORE any overview write.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": {"dir_C": {"candidates": []}}})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (d3) review D1: candidates as a non-list on a stamped v2 row —
            #      the count basis is corrupt, so the rebuild must stop and
            #      preserve the old overview.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": [{"direction_id": "dir_C",
                                           "candidates": "garbage"}]})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (d4) review D1: a cross group without a machine group identity
            #      fails closed before any overview write.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": [{"direction_id": "dir_C", "candidates": []}],
                           "cross_direction_groups": [{"direction_ids": ["dir_C"],
                                                        "candidates": []}]})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (d5) review C1: a null candidate list on a stamped v2 row is
            #      CORRUPT, not zero candidates — the rebuild must fail
            #      closed instead of publishing a count-0 row.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": [{"direction_id": "dir_C",
                                           "name_ja": "対照", "name_zh": "对照",
                                           "candidates": None}]})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (d6) review C1: non-list candidate members and null group
            #      fields fail closed before any overview write.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": [{"direction_id": "dir_C",
                                           "candidates": [None, "garbage"]}],
                           "cross_direction_groups": [
                               {"group_id": "cross:abc", "direction_ids": None,
                                "candidates": None}]})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (e) manual overview conflict fails the rebuild, keeps the edit.
            b_state_path.write_text(original_b_state, encoding="utf-8")
            b_pack_path.write_text(original_b_pack, encoding="utf-8")
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "ok", out)
            self.overview_path.write_text(
                self.overview_path.read_text(encoding="utf-8") + "\n人工改动\n",
                encoding="utf-8")
            manual = self.overview_path.read_bytes()
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "needs_decision", out)
            self.assertEqual(out["reason_code"], "manual_markdown_changed")
            self.assert_unchanged(before)
            self.assertEqual(self.overview_path.read_bytes(), manual)

            # (f) final-replace I/O failure keeps the old overview bytes.
            self.overview_path.unlink()
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "ok", out)
            before = self.snapshot(*snapshot_paths)

            def explode(real, src, dst):
                raise OSError("synthetic overview install failure")

            with gated_os_replace(
                    lambda src, dst: dst == os.path.realpath(self.overview_path),
                    explode):
                payload, code = call_runner(
                    "stage3-rebuild-overview", "--program-root", self.root)
            self.assertEqual(payload["reason_code"], "overview_write_failed", payload)
            self.assert_unchanged(before)
        finally:
            b_state_path.write_text(original_b_state, encoding="utf-8")
            b_pack_path.write_text(original_b_pack, encoding="utf-8")

    # -- S3-ISO-7 ---------------------------------------------------------

    def test_s3_iso_7_registry_stage4_source(self):
        """Registry independence for rebuild + Stage 4 keeps its local source."""
        self.finalize_a_ok("s3-iso-7")
        a_state = self.prof_dir / CANDIDATE_STATE
        selection = {"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
                     "direction_ids": ["dir_A"],
                     "ideas": [{"id": "dir_A_1", "note": "主推"}]}

        def stale_managed_overview():
            body_old = "# 套磁想法候选总览\n\n旧一代聚合。\n"
            sha_old = contact_state.sha256_text(body_old)
            fingerprint = contact_state.sha256_obj(
                {"projection": CANDIDATES_OVERVIEW, "body": sha_old})
            self.overview_path.write_text(
                contact_state.render_frontmatter(fingerprint, sha_old) + body_old,
                encoding="utf-8")

        # Overview missing → generated; registry missing before and after.
        self.assertTrue(not self.registry_path.exists())
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertFalse(self.registry_path.exists())

        # Stale but managed overview → rebuildable and refreshed.
        stale_managed_overview()
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertIn(PROFESSOR, self.overview_business_body())
        # Corrupt (frontmatter gone) → fail closed, bytes unchanged.
        self.overview_path.write_text("被破坏的总览\n", encoding="utf-8")
        broken = self.overview_path.read_bytes()
        out = run_cli("stage3-rebuild-overview", "--program-root", self.root)
        self.assertEqual(parse(out)["reason_code"], "manual_markdown_changed")
        self.assertEqual(self.overview_path.read_bytes(), broken)

        # Restore a managed overview, then prove registry independence:
        # malformed / stale registry → no read, no write, no side effect.
        self.overview_path.unlink()
        rebuild_ok = parse(run_cli("stage3-rebuild-overview",
                                   "--program-root", self.root))
        self.assertEqual(rebuild_ok["status"], "ok")
        self.overview_path.unlink()
        self.registry_path.write_text("{ malformed registry", encoding="utf-8")
        malformed = self.registry_path.read_bytes()
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(self.registry_path.read_bytes(), malformed)
        self.registry_path.write_text(
            json.dumps({"render": {"套磁邮件总览.md": {"sha256": "old"}}},
                       ensure_ascii=False),
            encoding="utf-8")
        stale_registry = self.registry_path.read_bytes()
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(self.registry_path.read_bytes(), stale_registry)

        # Low-level proof: a rebuild never even opens the registry.
        with OpenRecorder() as recorder:
            payload, code = call_runner(
                "stage3-rebuild-overview", "--program-root", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok", payload)
        self.assertFalse(recorder.was_opened(self.registry_path))
        self.assertTrue(recorder.was_opened(a_state))

        # Stage 4 keeps joining the professor-local state under every
        # overview anomaly (missing / stale / corrupt).
        for condition in ("missing", "stale", "corrupt"):
            with self.subTest(overview=condition):
                if self.overview_path.exists():
                    self.overview_path.unlink()
                if condition == "stale":
                    stale_managed_overview()
                elif condition == "corrupt":
                    self.overview_path.write_text("被破坏的总览\n", encoding="utf-8")
                overview_before = self.snapshot(self.overview_path)
                sel_input = self.root / f"sel-input-{condition}.json"
                sel_input.write_text(json.dumps({"selections": [selection]},
                                                ensure_ascii=False),
                                     encoding="utf-8")
                out4 = parse(run_cli("stage4-finalize", "--program-root", self.root,
                                     "--selection-input", sel_input))
                self.assertEqual(out4["status"], "ok", out4)
                pack = json.loads((self.root / "教授研究" / "邮件输入.json")
                                  .read_text(encoding="utf-8"))
                email = next(e for e in pack["emails"]
                             if e["email_id"] == f"{PROFESSOR}::dir_A::dir_A_1")
                self.assertEqual(
                    {(g["direction_id"], g["item_key"], g["gap_id"])
                     for g in email["gaps"]},
                    {("dir_A", "P1", self.gap_ids["P1"])})
                self.assert_unchanged(overview_before)

    # -- S3-COMP-1 --------------------------------------------------------

    @staticmethod
    def machine_projection(state):
        """Volatile-field-free projection of the candidate machine contract."""
        return {
            "schema": state["schema"], "kind": state["kind"],
            "identity_version": state["identity_version"],
            "generator_contract_version": state["generator_contract_version"],
            "professor": state["professor"],
            "profile_fingerprint": state["profile_fingerprint"],
            "input_fingerprints": state["input_fingerprints"],
            "directions": [{"direction_id": d["direction_id"],
                            "stage3_status": d["stage3_status"],
                            "candidates": [{"id": c["id"], "kind": c["kind"],
                                            "direction_ids": c["direction_ids"],
                                            "gap_refs": c["gap_refs"],
                                            "papers": [p["item_key"]
                                                       for p in c["papers"]]}
                                           for c in d["candidates"]]}
                           for d in state["directions"]],
            "cross_direction_groups": [{"group_id": g["group_id"],
                                         "direction_ids": g["direction_ids"],
                                         "direction_fingerprints":
                                             g["direction_fingerprints"],
                                         "profile_fingerprint":
                                             g["profile_fingerprint"],
                                         "candidates": [c["id"]
                                                        for c in g["candidates"]]}
                                        for g in state["cross_direction_groups"]],
        }

    def test_s3_comp_1_preserved_candidate_contract(self):
        """Two directions + one cross group keep the frozen machine contract."""
        results = self.write_a_cross(self.write_a_results("s3-comp-1"))
        out = self.stage3_finalize(results, "--cross-direction-groups",
                                   CROSS_GROUP_ARG)
        self.assertEqual(out["status"], "ok", out)
        state_path = self.prof_dir / CANDIDATE_STATE
        state = json.loads(state_path.read_text(encoding="utf-8"))
        projection = self.machine_projection(state)
        self.assertEqual(projection["schema"], 2)
        self.assertEqual([d["direction_id"] for d in projection["directions"]],
                         ["dir_A", "dir_B"])
        self.assertEqual(projection["cross_direction_groups"][0]["group_id"],
                         CROSS_GID)
        self.assertEqual(projection["cross_direction_groups"][0]["direction_ids"],
                         ["dir_A", "dir_B"])

        # Validator round 1 fails the dir_A scope and the cross-group scope
        # (both proven from the rendered text), so the correction round
        # re-renders both and the group survives the correction finalize.
        validation = self.root / "comp1-validation.json"
        finding = {"rule": "B5", "severity": "blocking",
                   "location": "validator 自报位置", "quote": "",
                   "suggestion": "首次出现时用日常语言解释。"}
        dir_a_finding = dict(finding, quote="候选 dir_A_1")
        cross_finding = dict(finding, quote="候选 XA")
        write_json(validation, {"result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "fail", "blocking": 2, "minor": 0,
            "issues": [dir_a_finding, cross_finding]}]})
        record = parse(run_cli("stage3-record-validation", "--professor-dir",
                               self.prof_dir, "--validation-file", validation))
        self.assertEqual(record["needs_correction"], True, record)
        block = json.loads(state_path.read_text(encoding="utf-8"))["validator"]
        self.assertEqual(set(block["pending"]),
                         {"direction:dir_A", f"group:{CROSS_GID}"})
        self.assertEqual(block["results"]["dir_B"]["result"], "pass")

        # Correction rerender: wording/priority repaired, machine projection
        # frozen, unprocessed scopes keep their proofs, render SHA carried.
        revised = self.generated_doc("dir_A", ["P1", "P2", None])
        revised["priority"] = "主推 候选1（修订版）"
        write_json(results / result_file("candidates", "dir_A"), revised)
        out = self.stage3_finalize(results, "--validation-file", validation)
        self.assertEqual(out["status"], "ok", out)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(self.machine_projection(state), projection)
        block = state["validator"]
        self.assertEqual(block["round"], 1)
        self.assertEqual(block["render_sha256"],
                         state["cache"]["render"][CANDIDATES_MD]["sha256"])
        self.assertIn("dir_B", block["results"])
        self.assertEqual(block["results"]["dir_B"]["result"], "pass")
        self.assertEqual(block["groups"], {})
        self.assertEqual(block["pending"], {})

        # Round 2 on the corrected render is the terminal record.
        write_json(validation, {"result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "pass", "blocking": 0, "minor": 0, "issues": []}]})
        record = parse(run_cli("stage3-record-validation", "--professor-dir",
                               self.prof_dir, "--validation-file", validation))
        self.assertEqual(record["needs_correction"], False, record)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["validator"]["results"]["dir_A"]["result"], "pass")
        self.assertEqual(state["validator"]["results"]["dir_A"]["rounds"], 2)

    # -- S3-DEP-1 ---------------------------------------------------------

    def test_s3_dep_1_no_issue48_lock_dependency(self):
        """#48 writer lock is not a prerequisite anywhere on the #66 path."""
        # Finalize + rebuild run with no lock fixture and create no lock
        # artifacts anywhere in the program root.
        self.finalize_a_ok("s3-dep-1")
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        lock_files = [p for p in self.root.rglob("*")
                      if p.is_file() and (p.name.endswith(".lock")
                                          or ".lock." in p.name)]
        self.assertEqual(lock_files, [])


class CredentialEntryIsolationTests(TestIssue66Stage3):
    """The isolation / manual-conflict / transaction / candidate-contract
    facts re-proved through the frozen credential entry (r13 §5.2): capture
    once, then every commit consumes the credential and re-supplying source
    parameters is refused."""

    def setUp(self):
        super().setUp()
        self._cap_seq = itertools.count(1)

    def capture(self, *extra):
        cap_dir = self.root / f"cap-iso-{next(self._cap_seq)}"
        plan = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root,
                             "--capture-invocation", cap_dir, *extra))
        self.assertEqual(plan["status"], "ok",
                         msg=json.dumps(plan, ensure_ascii=False))
        return plan

    def credential_finalize(self, cap, results, *extra):
        # Credential consumption and re-supplied source parameters are
        # mutually exclusive, so --program-root must NOT be passed here.
        return parse(run_cli(
            "stage3-finalize",
            "--invocation-file", cap["invocation_file"],
            "--invocation-sha256", cap["invocation_sha256"],
            "--results", str(results), *extra))

    def test_s3_iso_1_b_anomalies_via_credential_entry(self):
        """R66-1 through the credential path: B state / overview / registry
        anomalies never block or touch A's local commit, and the credential
        finalize opens none of the three forbidden objects."""
        a_pack = self.prof_dir / "套磁候选输入.json"
        foreign_state = (self.root / "教授研究" / "Y分野" / SECOND_PROFESSOR
                         / CANDIDATE_STATE)

        def reset_single_variable_baseline():
            shutil.rmtree(self.root / "教授研究" / "Y分野", ignore_errors=True)
            self.overview_path.unlink(missing_ok=True)
            self.registry_path.unlink(missing_ok=True)

        cap = self.capture()
        for disturbance in ("b_state_malformed", "overview_conflict",
                            "registry_malformed"):
            with self.subTest(scenario=disturbance):
                reset_single_variable_baseline()
                if disturbance == "b_state_malformed":
                    foreign_state.parent.mkdir(parents=True, exist_ok=True)
                    foreign_state.write_text("{ malformed foreign state",
                                             encoding="utf-8")
                    disturbed = foreign_state
                elif disturbance == "overview_conflict":
                    self.overview_path.write_text("手工改过的总览\n",
                                                  encoding="utf-8")
                    disturbed = self.overview_path
                else:
                    self.registry_path.write_text("{ malformed registry",
                                                  encoding="utf-8")
                    disturbed = self.registry_path
                before = self.snapshot(disturbed)
                a_results = self.write_a_results(f"cred-iso-1-{disturbance}")
                # In-process call so OpenRecorder can observe real opens.
                with OpenRecorder() as recorder:
                    out, code = call_runner(
                        "stage3-finalize",
                        "--invocation-file", cap["invocation_file"],
                        "--invocation-sha256", cap["invocation_sha256"],
                        "--results", str(a_results))
                self.assertEqual(code, 0)
                self.assertEqual(out["status"], "ok", out)
                self.assert_unchanged(before)
                for other in (foreign_state, self.overview_path,
                              self.registry_path):
                    if other != disturbed:
                        self.assertFalse(other.exists(),
                                         f"unexpected non-owner object: {other}")
                for forbidden in (foreign_state, self.overview_path,
                                  self.registry_path):
                    self.assertFalse(recorder.was_opened(forbidden))
                self.assertTrue(recorder.was_opened(a_pack))

    def test_s3_iso_3_manual_conflict_via_credential_entry(self):
        """A's own manually edited local Markdown still fails closed when the
        commit arrives through the credential entry."""
        cap = self.capture()
        out = self.credential_finalize(cap, self.write_a_results("cred-iso-3"))
        self.assertEqual(out["status"], "ok", out)
        md_path = self.prof_dir / CANDIDATES_MD
        state_path = self.prof_dir / CANDIDATE_STATE
        md_path.write_text(
            md_path.read_text(encoding="utf-8") + "\n人工修改的一行\n",
            encoding="utf-8")
        manual_md = md_path.read_bytes()
        before = self.snapshot(state_path, self.overview_path,
                               self.registry_path)
        out2 = self.credential_finalize(
            cap, self.write_a_results("cred-iso-3-reuse"))
        self.assertEqual(out2["status"], "needs_decision", out2)
        self.assertEqual(out2["reason_code"], "manual_markdown_changed")
        self.assert_unchanged(before)
        self.assertEqual(md_path.read_bytes(), manual_md)

    def test_s3_iso_4_commit_marker_via_credential_entry(self):
        """Markdown-first / state-last stays observable through the
        credential entry: the correction round re-renders the Markdown (the
        only caller-legal way to change the render over a frozen credential),
        the pre-commit failure restores both old byte sets, and the released
        commit binds the committed state's render to the installed body."""
        cap = self.capture()
        results = self.write_a_results("cred-iso-4")
        out = self.credential_finalize(cap, results)
        self.assertEqual(out["status"], "ok", out)
        md_path = self.prof_dir / CANDIDATES_MD
        state_path = self.prof_dir / CANDIDATE_STATE
        # Record a real blocking finding, then correct dir_A's prose: the
        # correction work set re-renders dir_A, so "new Markdown installed"
        # is byte-observable through the credential replay.
        validation = self.root / "cred-iso-4-validation.json"
        write_json(validation, {"result": "ok", "files": [{
            "file": str(md_path), "artifact": "candidates",
            "verdict": "fail", "blocking": 1, "minor": 0,
            "issues": [{"rule": "B5", "severity": "blocking",
                        "location": "validator 自报位置",
                        "quote": "候选 dir_A_1",
                        "suggestion": "首次出现时用日常语言解释。"}]}]})
        record = parse(run_cli("stage3-record-validation", "--professor-dir",
                               self.prof_dir, "--validation-file", validation))
        self.assertEqual(record["needs_correction"], True, record)
        # The rollback baseline is the state as of the correction commit's
        # start: the first-round commit plus the recorded validator block.
        old_md, old_state = md_path.read_bytes(), state_path.read_bytes()
        corrected = self.generated_doc("dir_A", ["P1", "P2", None])
        corrected["candidates"][0]["one_liner"] = (
            "教授的工作启发我思考延伸方向（ISO-4 凭据修正改写）")
        write_json(results / result_file("candidates", "dir_A"), corrected)

        def cred_correction_argv():
            return ("stage3-finalize",
                    "--invocation-file", cap["invocation_file"],
                    "--invocation-sha256", cap["invocation_sha256"],
                    "--results", str(results),
                    "--validation-file", str(validation))

        attempted, released = threading.Event(), threading.Event()
        observed = {}

        def reader():
            self.assertTrue(attempted.wait(30))
            observed["state"] = state_path.read_bytes()
            observed["md"] = md_path.read_bytes()
            released.set()

        def gate(real, src, dst):
            # The credential carries the RESOLVED professor directory, so the
            # runner's raw dst is the /private/tmp form while state_path was
            # built from the /tmp form; compare resolved.
            if Path(dst) == Path(os.path.realpath(state_path)):
                attempted.set()
                self.assertTrue(released.wait(30))
                raise OSError("synthetic candidate-state install failure")

        watcher = threading.Thread(target=reader)
        watcher.start()
        try:
            with gated_os_replace(
                    lambda src, dst: dst == os.path.realpath(state_path), gate):
                payload, code = call_runner(*cred_correction_argv())
        finally:
            watcher.join(30)
        self.assertEqual(payload["reason_code"], "local_pair_commit_failed",
                         payload)
        self.assertEqual(observed["state"], old_state)
        self.assertNotEqual(observed["md"], old_md)
        self.assertEqual(md_path.read_bytes(), old_md)
        self.assertEqual(state_path.read_bytes(), old_state)

        # Release the state replace: the committed state's render SHA binds
        # the installed Markdown body, as on the plain entry.
        attempted, released = threading.Event(), threading.Event()
        observed = {}

        def reader_after_install():
            self.assertTrue(attempted.wait(30))
            observed["state"] = json.loads(
                state_path.read_text(encoding="utf-8"))
            released.set()

        def install_then_release(real, src, dst):
            real(src, dst)
            attempted.set()
            self.assertTrue(released.wait(30))

        watcher = threading.Thread(target=reader_after_install)
        watcher.start()
        try:
            with gated_os_replace(
                    lambda src, dst: dst == os.path.realpath(state_path),
                    install_then_release):
                payload, code = call_runner(*cred_correction_argv())
        finally:
            watcher.join(30)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok", payload)
        _, md_body = contact_state.split_frontmatter(
            md_path.read_text(encoding="utf-8"))
        self.assertEqual(
            observed["state"]["cache"]["render"][CANDIDATES_MD]["sha256"],
            contact_state.sha256_text(md_body))

    def test_s3_comp_1_preserved_contract_via_credential_entry(self):
        """Two directions + one cross group keep the frozen machine contract
        when both the first round and the correction consume the credential;
        the group survives and unprocessed scopes keep their proofs."""
        # The cross-direction group request is a first-round control: it is
        # captured INTO the credential, never re-supplied at finalize.
        cap = self.capture("--cross-direction-groups", CROSS_GROUP_ARG)
        results = self.write_a_cross(self.write_a_results("cred-comp-1"))
        out = self.credential_finalize(cap, results)
        self.assertEqual(out["status"], "ok", out)
        state_path = self.prof_dir / CANDIDATE_STATE
        state = json.loads(state_path.read_text(encoding="utf-8"))
        projection = self.machine_projection(state)
        self.assertEqual(projection["schema"], 2)
        self.assertEqual([d["direction_id"] for d in projection["directions"]],
                         ["dir_A", "dir_B"])
        self.assertEqual(projection["cross_direction_groups"][0]["group_id"],
                         CROSS_GID)
        self.assertEqual(projection["cross_direction_groups"][0]["direction_ids"],
                         ["dir_A", "dir_B"])

        # Round 1 fails the dir_A scope and the cross-group scope; the
        # credential correction re-renders both and the group survives.
        validation = self.root / "cred-comp-1-validation.json"
        finding = {"rule": "B5", "severity": "blocking",
                   "location": "validator 自报位置", "quote": "",
                   "suggestion": "首次出现时用日常语言解释。"}
        write_json(validation, {"result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "fail", "blocking": 2, "minor": 0,
            "issues": [dict(finding, quote="候选 dir_A_1"),
                       dict(finding, quote="候选 XA")]}]})
        record = parse(run_cli("stage3-record-validation", "--professor-dir",
                               self.prof_dir, "--validation-file", validation))
        self.assertEqual(record["needs_correction"], True, record)
        block = json.loads(state_path.read_text(encoding="utf-8"))["validator"]
        self.assertEqual(set(block["pending"]),
                         {"direction:dir_A", f"group:{CROSS_GID}"})
        self.assertEqual(block["results"]["dir_B"]["result"], "pass")

        revised = self.generated_doc("dir_A", ["P1", "P2", None])
        revised["priority"] = "主推 候选1（凭据修订版）"
        write_json(results / result_file("candidates", "dir_A"), revised)
        out = self.credential_finalize(cap, results,
                                       "--validation-file", validation)
        self.assertEqual(out["status"], "ok", out)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(self.machine_projection(state), projection)
        block = state["validator"]
        self.assertEqual(block["round"], 1)
        self.assertEqual(block["render_sha256"],
                         state["cache"]["render"][CANDIDATES_MD]["sha256"])
        self.assertIn("dir_B", block["results"])
        self.assertEqual(block["results"]["dir_B"]["result"], "pass")
        self.assertEqual(block["groups"], {})
        self.assertEqual(block["pending"], {})

        # Round 2 on the corrected render is the terminal record.
        write_json(validation, {"result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "pass", "blocking": 0, "minor": 0, "issues": []}]})
        record = parse(run_cli("stage3-record-validation", "--professor-dir",
                               self.prof_dir, "--validation-file", validation))
        self.assertEqual(record["needs_correction"], False, record)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["validator"]["results"]["dir_A"]["result"], "pass")
        self.assertEqual(state["validator"]["results"]["dir_A"]["rounds"], 2)


if __name__ == "__main__":
    unittest.main()
