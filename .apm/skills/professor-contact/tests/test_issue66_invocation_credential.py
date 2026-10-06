"""Issue #66 r13 §5 acceptance: invocation credentials and correction context.

Exactly this implementation step, nothing more:
- §5.1  ``stage3-plan --capture-invocation`` writes an exclusive, immutable
        credential from the parameters THIS invocation parsed and returns its
        path plus the SHA-256 of the exact file bytes; a capture failure fails
        the whole plan.
- §5.2  ``--invocation-file`` + ``--invocation-sha256`` consumption on plan
        and finalize: pair enforcement, mutual exclusion with re-supplied
        source parameters, and damaged / unsupported-version / digest-mismatch
        / ownership / profile-digest refusal before any write.
- §5.4  credential + recorded validation file enters the dedicated correction
        branch: the work set is exactly the recorded D/G, first-round
        skip/selection/group controls stay records (never re-interpreted
        requests), and a first-round-out-of-scope direction named by the
        validator remains correctable.
- §5.5  correction commits replace in place inside the OLD direction/group
        lists and preserve every uninvolved object; plain generation keeps the
        old drop rule.
- §5.6  the old explicit correction entry keeps its admission rules but gains
        the same uninvolved-group preservation (the planned behavior fix).

Proof conventions follow the shared fixtures: real CLI runs, direct file
reads for byte claims, no sleeps, no owner mocking.
"""
import hashlib
import itertools
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import (
    parse, quote_id, run_cli, write_json)
from test_stage3_direction_groups import (
    PROFESSOR, Stage3DirectionGroupBase, contact_state, result_file)
from test_issue66_stage3_local_state import OpenRecorder, call_runner

CANDIDATE_STATE = "套磁候选状态.json"
CANDIDATES_MD = "套磁想法候选.md"
GID_AB = contact_state.cross_group_id(["dir_A", "dir_B"])
GID_AC = contact_state.cross_group_id(["dir_A", "dir_C"])
# Frozen result-read expectations for the two distinct correction scopes.
EXPECTED_DIRECTION_READS = frozenset({"dir_B"})
EXPECTED_GROUP_READS = frozenset({GID_AB})
EXPECTED_FILE_QUOTE_DIRECTIONS = frozenset({"dir_A", "dir_B", "dir_C"})
EXPECTED_SKIP_CORRECTION_READS = frozenset({"dir_A"})
CROSS_AB_ARG = '[["dir_A","dir_B"]]'
CROSS_AC_ARG = '[["dir_A","dir_C"]]'
BOTH_GROUPS_ARG = '[["dir_A","dir_B"],["dir_A","dir_C"]]'
INVOCATION_VERSION = "stage3-invocation-v1"


def expected_result_read_paths(results_dir, direction_ids=(), group_ids=()):
    """Build the frozen result-file read set without consulting observations."""
    identities = (*direction_ids, *group_ids)
    return frozenset(
        OpenRecorder._normalize(Path(results_dir) / result_file("candidates", key))
        for key in identities)


def assert_result_read_set(testcase, recorder, results_dir, expected):
    """Assert exact real result-file reads against frozen test expectations."""
    testcase.assertEqual(recorder.read_paths_under(results_dir), expected,
                         "actual result reads differ from the frozen expected set")


def artifact_snapshot(*roots):
    """Capture existence, filesystem metadata and complete bytes of artifacts.

    Access time is intentionally omitted because reading evidence may update it.
    Directory metadata plus recursive entries also detects create/remove cycles.
    """
    snapshot = {}

    def metadata(info):
        return (info.st_mode, info.st_size, info.st_mtime_ns,
                info.st_ctime_ns, getattr(info, "st_birthtime_ns", None),
                info.st_ino, info.st_nlink, info.st_uid, info.st_gid)

    def visit(path):
        path = Path(path)
        key = str(path)
        try:
            info = path.lstat()
        except FileNotFoundError:
            snapshot[key] = ("absent",)
            return
        kind = stat.S_IFMT(info.st_mode)
        if stat.S_ISLNK(info.st_mode):
            snapshot[key] = ("symlink", metadata(info), os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            snapshot[key] = ("directory", metadata(info))
            for child in sorted(path.iterdir(), key=lambda item: item.name):
                visit(child)
        elif stat.S_ISREG(info.st_mode):
            snapshot[key] = ("file", metadata(info), path.read_bytes())
        else:
            snapshot[key] = ("other", kind, metadata(info))

    for root in roots:
        visit(root)
    return snapshot

# Three active directions; dir_A/dir_B share paper P1, dir_C stands alone so a
# second cross-direction group (A+C) can exist next to (A+B).
QUOTES = {
    "P1": "Future work will extend the shared method to streaming inputs.",
    "P2": "Future work plans a robustness benchmark for the signal pipeline.",
    "P3": "Future work will deploy the sensor network at campus scale.",
    "P4": "Future work will benchmark the adaptive filter bank at scale.",
}


class InvocationCredentialBase(Stage3DirectionGroupBase):
    """Same pipeline fixture as the shared base, but with a third direction."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / PROFESSOR
        (self.prof_dir / "论文分析").mkdir(parents=True)
        papers = [
            self.make_paper("P1", "Shared Method Paper", ["method", "shared"],
                            [QUOTES["P1"]]),
            self.make_paper("P2", "Signal Robustness Paper", ["signal", "robust"],
                            [QUOTES["P2"]]),
            self.make_paper("P3", "Campus Sensor Paper", ["sensor", "network"],
                            [QUOTES["P3"]]),
            self.make_paper("P4", "Adaptive Filter Paper", ["adaptive", "filter"],
                            [QUOTES["P4"]]),
        ]
        directions = [
            self.make_direction("dir_A", ["P1", "P2"], name_ja="信号処理",
                                name_zh="信号处理", summary="信号处理方向"),
            self.make_direction("dir_B", ["P1", "P3"], name_ja="センサ網",
                                name_zh="传感网络", summary="传感网络方向"),
            self.make_direction("dir_C", ["P4"], name_ja="適応制御",
                                name_zh="自适应", summary="自适应方向"),
        ]
        facts_path = self.write_facts(papers, directions)
        self.run_resolve(facts_path, {})
        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        self.gap_ids = {key: quote_id(quote) for key, quote in QUOTES.items()}
        self.validation = self.root / "stage3-style-validation.json"
        self._inv_seq = itertools.count(1)

    # -- fixture helpers ---------------------------------------------------

    def all_docs(self):
        return {"dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
                "dir_B": self.generated_doc("dir_B", ["P1", "P3", None]),
                "dir_C": self.generated_doc("dir_C", ["P4", "P4", None])}

    def write_cross(self, results, gid, candidates):
        ids = ["dir_A", "dir_B"] if gid == GID_AB else ["dir_A", "dir_C"]
        write_json(results / result_file("candidates", gid),
                   {"schema": 2, "kind": "cross_candidates",
                    "group_id": gid, "direction_ids": ids,
                    "candidates": candidates})

    def write_ac_cross(self, results, cid):
        """An A+C cross candidate grounded in each participant's own slice."""
        idea = self.cross_candidate(cid, ["dir_A", "dir_C"], ["P2", "P4"], [],
                                    gap_owner={"P2": "dir_A", "P4": "dir_C"})
        idea["papers"] = [
            {"item_key": "P2", "direction_ids": ["dir_A"],
             "role": "基座", "fit_note": "A 论文"},
            {"item_key": "P4", "direction_ids": ["dir_C"],
             "role": "基座", "fit_note": "C 论文"}]
        self.write_cross(results, GID_AC, [idea])
        return idea

    def capture(self, *extra):
        """First-round plan that captures a credential into a fresh directory."""
        cap_dir = self.root / f"inv-{next(self._inv_seq)}"
        out = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                            "--program-root", self.root,
                            "--capture-invocation", cap_dir, *extra))
        return out, cap_dir

    def credential_plan(self, cap, *extra):
        return parse(run_cli("stage3-plan",
                             "--invocation-file", cap["invocation_file"],
                             "--invocation-sha256", cap["invocation_sha256"],
                             *extra))

    def credential_finalize(self, cap, results, *extra):
        return parse(run_cli("stage3-finalize",
                             "--invocation-file", cap["invocation_file"],
                             "--invocation-sha256", cap["invocation_sha256"],
                             "--results", str(results), *extra))

    def validator_output(self, issues=(), verdict=None):
        blocking = [i for i in issues if i.get("severity") == "blocking"]
        write_json(self.validation, {"result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": verdict or ("fail" if blocking else "pass"),
            "blocking": len(blocking), "minor": 0, "issues": list(issues)}]})
        return self.validation

    @staticmethod
    def finding(quote):
        return {"rule": "B5", "severity": "blocking", "location": "validator 自报位置",
                "quote": quote, "suggestion": "首次出现时用日常语言解释。"}

    def record(self):
        return parse(run_cli("stage3-record-validation",
                             "--professor-dir", self.prof_dir,
                             "--validation-file", self.validation))

    def write_credential(self, payload):
        path = self.root / f"crafted-{next(self._inv_seq)}.json"
        write_json(path, payload)
        return str(path), hashlib.sha256(path.read_bytes()).hexdigest()

    def load_validator_block(self):
        return self.load_state().get("validator") or {}

    def assert_no_side_effects(self, operation, *protected_paths):
        before = artifact_snapshot(*protected_paths)
        result = operation()
        self.assertEqual(artifact_snapshot(*protected_paths), before,
                         "refused invocation changed a protected artifact")
        return result

    def assert_direct_refusal(self, operation, protected, status, reason):
        before = artifact_snapshot(*protected)
        result = operation()
        self.assertEqual(artifact_snapshot(*protected), before,
                         "directly rejected entry changed protected artifacts")
        self.assertEqual(result.get("status"), status, result)
        self.assertEqual(result.get("reason_code"), reason, result)
        self.assertNotIn("written", result)
        if status != "ok":
            self.assertNotIn("jobs", result)
        return result


class CaptureCredentialTests(InvocationCredentialBase):
    """§5.1: credential production."""

    def test_capture_records_parsed_parameters_and_returns_digest(self):
        profile = self.root / "profile.md"
        profile.write_text("研究兴趣：信号处理。\n", encoding="utf-8")
        selection = self.root / "sel.json"
        write_json(selection, {"selections": [
            {"professor": PROFESSOR, "direction_id": "dir_A"}]})
        cap_dir = self.root / "inv-full"
        plan = parse(run_cli(
            "stage3-plan", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--profile", profile,
            "--refresh-scope", "selected", "--selection", selection,
            "--skip-direction-ids", "dir_B",
            "--cross-direction-groups", CROSS_AB_ARG,
            "--capture-invocation", cap_dir))
        self.assertEqual(plan["status"], "ok", msg=json.dumps(plan, ensure_ascii=False))
        self.assertIn("invocation_file", plan)
        self.assertIn("invocation_sha256", plan)
        cred_path = Path(plan["invocation_file"])
        self.assertEqual(cred_path.parent, cap_dir)
        raw = cred_path.read_bytes()
        self.assertEqual(plan["invocation_sha256"], hashlib.sha256(raw).hexdigest())
        cred = json.loads(raw.decode("utf-8"))
        self.assertEqual(cred["version"], INVOCATION_VERSION)
        self.assertEqual(cred["professor_dir"], str(self.prof_dir.resolve()))
        self.assertEqual(cred["program_root"], str(self.root.resolve()))
        self.assertEqual(cred["profile_path"], str(profile.resolve()))
        self.assertEqual(cred["profile_sha256"],
                         hashlib.sha256(profile.read_bytes()).hexdigest())
        self.assertEqual(cred["refresh_scope"], "selected")
        self.assertEqual(cred["selection"], str(selection.resolve()))
        self.assertIsNone(cred["direction_id"])
        self.assertIsNone(cred["collection_key"])
        self.assertIsNone(cred["collection_key_direction_id"])
        self.assertEqual(cred["skip_direction_ids_argument"], "dir_B")
        self.assertEqual(cred["skipped_direction_ids"], ["dir_B"])
        self.assertEqual(cred["cross_direction_groups_argument"], CROSS_AB_ARG)
        self.assertEqual(cred["cross_direction_groups"],
                         [{"group_id": GID_AB, "direction_ids": ["dir_A", "dir_B"]}])

    def test_capture_keeps_absent_parameters_absent(self):
        plan, _ = self.capture()
        self.assertEqual(plan["status"], "ok", msg=json.dumps(plan, ensure_ascii=False))
        cred = json.loads(Path(plan["invocation_file"]).read_text(encoding="utf-8"))
        # 未传入 stays distinct from any business default the runner applies.
        self.assertIsNone(cred["profile_path"])
        self.assertIsNone(cred["profile_sha256"])
        self.assertIsNone(cred["refresh_scope"])
        self.assertIsNone(cred["selection"])
        self.assertIsNone(cred["skip_direction_ids_argument"])
        self.assertEqual(cred["skipped_direction_ids"], [])
        self.assertIsNone(cred["cross_direction_groups_argument"])
        self.assertEqual(cred["cross_direction_groups"], [])

    def test_capture_directory_is_exclusive_and_failure_fails_the_plan(self):
        cap_dir = self.root / "inv-once"
        first = self.capture_into(cap_dir)
        self.assertEqual(first["status"], "ok", msg=json.dumps(first, ensure_ascii=False))
        legit_bytes = (cap_dir / "stage3-invocation.json").read_bytes()
        # A second capture into the same (no longer exclusive) directory fails
        # the whole plan instead of overwriting the credential.
        out = self.capture_into(cap_dir)
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "invalid_params")
        self.assertNotIn("invocation_file", out)
        # A capture target occupied by a plain file fails the plan too.
        occupied = self.root / "inv-occupied"
        occupied.write_text("not a directory", encoding="utf-8")
        out2 = self.capture_into(occupied)
        self.assertEqual(out2["status"], "error")
        self.assertEqual(out2["reason_code"], "invalid_params")
        # The legitimate credential is immutable across both failures.
        self.assertEqual((cap_dir / "stage3-invocation.json").read_bytes(), legit_bytes)

    def capture_into(self, target):
        return parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root,
                             "--capture-invocation", target))

    def test_capture_is_first_round_only(self):
        # A correction plan may not mint a credential.
        out = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                            "--program-root", self.root,
                            "--validation-file", str(self.validator_output()),
                            "--capture-invocation", self.root / "inv-corr"))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "invalid_params")
        self.assertFalse((self.root / "inv-corr").exists())
        # Capture cannot be combined with consuming a credential.
        cap, _ = self.capture()
        out2 = parse(run_cli("stage3-plan", "--program-root", self.root,
                             "--invocation-file", cap["invocation_file"],
                             "--invocation-sha256", cap["invocation_sha256"],
                             "--capture-invocation", self.root / "inv-both"))
        self.assertEqual(out2["status"], "error")
        self.assertEqual(out2["reason_code"], "invalid_params")
        self.assertFalse((self.root / "inv-both").exists())


class InvocationConsumptionTests(InvocationCredentialBase):
    """§5.2: mutual exclusion, digest, version, ownership, profile guard."""

    def test_invocation_rejects_replayed_source_parameters(self):
        cap, _ = self.capture()
        cases = [
            ("professor", ("--professor-dir", str(self.prof_dir))),
            ("program-root", ("--program-root", str(self.root))),
            ("profile", ("--profile", str(self.root / "profile.md"))),
            ("refresh-scope", ("--refresh-scope", "all")),
            ("skip", ("--skip-direction-ids", "dir_A")),
            ("groups", ("--cross-direction-groups", CROSS_AB_ARG)),
            ("direction-id", ("--direction-id", "dir_A")),
            ("collection-key", ("--collection-key", "dir_A")),
            ("selection", ("--selection", str(self.root / "sel.json"))),
        ]
        for label, extra in cases:
            with self.subTest(case=label):
                plan = self.assert_no_side_effects(
                    lambda: self.credential_plan(cap, *extra), self.root)
                self.assertEqual(plan["status"], "error",
                                 msg=json.dumps(plan, ensure_ascii=False))
                self.assertEqual(plan["reason_code"], "invalid_params")
                fin = self.assert_no_side_effects(
                    lambda: self.credential_finalize(
                        cap, self.root / "results", *extra), self.root)
                self.assertEqual(fin["status"], "error")
                self.assertEqual(fin["reason_code"], "invalid_params")

    def test_invocation_pair_is_enforced(self):
        cap, _ = self.capture()
        for label, argv in (
                ("file only", ("--invocation-file", cap["invocation_file"])),
                ("sha only", ("--invocation-sha256", cap["invocation_sha256"]))):
            with self.subTest(case=label):
                out = self.assert_no_side_effects(
                    lambda: parse(run_cli("stage3-plan", *argv)), self.root)
                self.assertEqual(out["status"], "error")
                self.assertEqual(out["reason_code"], "invalid_params")
                fin = self.assert_no_side_effects(
                    lambda: parse(run_cli(
                        "stage3-finalize", *argv,
                        "--results", str(self.root / "results"))), self.root)
                self.assertEqual(fin["status"], "error")
                self.assertEqual(fin["reason_code"], "invalid_params")

    def test_damaged_version_digest_and_ownership_fail_before_writes(self):
        profile = self.root / "profile.md"
        profile.write_text("研究兴趣：拒绝快照来源。\n", encoding="utf-8")
        cap, _ = self.capture("--profile", profile)
        results = self.write_results("refused-results", self.all_docs())
        committed = self.credential_finalize(cap, results)
        self.assertEqual(committed["status"], "ok",
                         msg=json.dumps(committed, ensure_ascii=False))
        credential = json.loads(
            Path(cap["invocation_file"]).read_text(encoding="utf-8"))
        profile_sha = hashlib.sha256(profile.read_bytes()).hexdigest()
        self.assertEqual(cap["profile_fingerprint"], profile_sha)
        self.assertEqual(credential["profile_sha256"], profile_sha)
        self.assertEqual(self.load_state()["profile_fingerprint"], profile_sha)
        prepared = parse(run_cli(
            "stage3-prepare-validation",
            "--invocation-file", cap["invocation_file"],
            "--invocation-sha256", cap["invocation_sha256"],
            "--round", "1"))
        self.assertEqual(prepared["status"], "ok",
                         msg=json.dumps(prepared, ensure_ascii=False))
        handoff = Path(prepared["handoff_file"])
        output = Path(prepared["output_file"])
        validation = Path(prepared["validation_file"])
        # This direct-entry refusal matrix reuses one committed baseline and
        # one complete protected set. Include absent validator paths as their
        # own roots so the expected absence is compared for every invocation.
        protected = (
            self.root,
            self.prof_dir / CANDIDATES_MD,
            self.prof_dir / CANDIDATE_STATE,
            Path(cap["invocation_file"]), results,
            handoff.parent, handoff, output, validation,
        )
        self.addCleanup(shutil.rmtree, handoff.parent, ignore_errors=True)
        self.assertTrue((self.prof_dir / CANDIDATES_MD).is_file())
        self.assertTrue((self.prof_dir / CANDIDATE_STATE).is_file())
        self.assertTrue(Path(cap["invocation_file"]).is_file())
        self.assertTrue(results.is_dir())
        self.assertTrue(handoff.is_file())
        self.assertFalse(output.exists())
        self.assertFalse(validation.exists())
        template = json.loads(
            Path(cap["invocation_file"]).read_text(encoding="utf-8"))

        def assert_plan_and_finalize(path, sha, status, reason):
            self.assert_direct_refusal(
                lambda: parse(run_cli(
                    "stage3-plan", "--invocation-file", path,
                    "--invocation-sha256", sha)),
                protected, status, reason)
            self.assert_direct_refusal(
                lambda: parse(run_cli(
                    "stage3-finalize", "--invocation-file", path,
                    "--invocation-sha256", sha, "--results", results)),
                protected, status, reason)

        # Digest mismatch over the unchanged, genuine credential bytes.
        assert_plan_and_finalize(
            cap["invocation_file"], "0" * 64, "error",
            "invocation_sha256_mismatch")
        # Damaged bytes with their own correct digest.
        damaged = self.root / "damaged-credential.json"
        damaged.write_bytes(b"{ damaged credential")
        damaged_sha = hashlib.sha256(damaged.read_bytes()).hexdigest()
        assert_plan_and_finalize(
            str(damaged), damaged_sha, "error", "invalid_invocation")
        # Unsupported credential version.
        path, sha = self.write_credential(
            {**template, "version": "stage3-invocation-v0"})
        assert_plan_and_finalize(
            path, sha, "error", "invocation_version_unsupported")
        # Professor directory outside the credential's program root.
        foreign = {**template,
                   "professor_dir": str(self.root / "其他研究" / PROFESSOR)}
        path, sha = self.write_credential(foreign)
        assert_plan_and_finalize(
            path, sha, "error", "invalid_professor_dir")

        # A genuine source change is checked through both direct entries after
        # the original credential, state, results, and handoff are committed.
        profile.write_text("研究兴趣：真实来源已变化。\n", encoding="utf-8")
        assert_plan_and_finalize(
            cap["invocation_file"], cap["invocation_sha256"],
            "needs_refresh", "validation_source_changed")

        # And the state runner needs one of the two identity sources.
        out = self.assert_no_side_effects(lambda: parse(run_cli("stage3-plan")),
                                          self.root)
        self.assertEqual(out["reason_code"], "invalid_params")
        fin = self.assert_no_side_effects(
            lambda: parse(run_cli("stage3-finalize", "--results",
                                  str(self.root / "r"))), self.root)
        self.assertEqual(fin["reason_code"], "invalid_params")
        # The direct-entry matrix began from a committed state and protected
        # the candidate, state, credential, result, metadata, source and target.
        self.assertTrue((self.prof_dir / CANDIDATE_STATE).is_file())

    def test_credential_rejection_preserves_the_full_committed_artifact_set(self):
        """Direct plan/finalize refusals leave every bound artifact unchanged."""
        cap, _ = self.capture()
        results = self.write_results("refusal-baseline", self.all_docs())
        committed = self.credential_finalize(cap, results)
        self.assertEqual(committed["status"], "ok",
                         msg=json.dumps(committed, ensure_ascii=False))

        prepared = parse(run_cli(
            "stage3-prepare-validation",
            "--invocation-file", cap["invocation_file"],
            "--invocation-sha256", cap["invocation_sha256"],
            "--round", "1"))
        self.assertEqual(prepared["status"], "ok",
                         msg=json.dumps(prepared, ensure_ascii=False))
        handoff = Path(prepared["handoff_file"])
        source = Path(prepared["output_file"])
        target = Path(prepared["validation_file"])
        source.write_bytes(b"validator source preserved across credential rejection\n")
        self.assertTrue(handoff.is_file())
        self.assertTrue(source.is_file())
        self.assertFalse(target.exists())

        # Record expected absences explicitly, alongside recursive roots that
        # cover the candidate, state, credential, and existing result bytes.
        protected = (
            self.root,
            self.prof_dir / CANDIDATES_MD,
            self.prof_dir / CANDIDATE_STATE,
            Path(cap["invocation_file"]),
            results,
            handoff.parent,
            handoff,
            source,
            target,
        )
        self.assertTrue((self.prof_dir / CANDIDATES_MD).is_file())
        self.assertTrue((self.prof_dir / CANDIDATE_STATE).is_file())
        self.assertTrue(results.is_dir())
        self.assertTrue(Path(cap["invocation_file"]).is_file())

        plan_before = artifact_snapshot(*protected)
        plan = parse(run_cli("stage3-plan",
                             "--invocation-file", cap["invocation_file"],
                             "--invocation-sha256", "0" * 64))
        self.assertEqual(artifact_snapshot(*protected), plan_before,
                         "rejected plan changed bytes, metadata or existence")
        self.assertEqual(plan["status"], "error", plan)
        self.assertEqual(plan["reason_code"], "invocation_sha256_mismatch", plan)
        self.assertNotIn("jobs", plan)

        finalize_before = artifact_snapshot(*protected)
        finalize = parse(run_cli(
            "stage3-finalize",
            "--invocation-file", cap["invocation_file"],
            "--invocation-sha256", "0" * 64,
            "--results", results))
        self.assertEqual(artifact_snapshot(*protected), finalize_before,
                         "rejected finalize changed bytes, metadata or existence")
        self.assertEqual(finalize["status"], "error", finalize)
        self.assertEqual(finalize["reason_code"], "invocation_sha256_mismatch",
                         finalize)
        self.assertNotIn("written", finalize)

    def test_profile_digest_guard_stops_stale_credentials(self):
        profile = self.root / "profile.md"
        profile.write_text("研究兴趣：第一版。\n", encoding="utf-8")
        results = self.write_results("prof-base", self.all_docs())
        first = self.stage3_finalize(results)
        self.assertEqual(first["status"], "ok", msg=json.dumps(first, ensure_ascii=False))
        state_path = self.prof_dir / CANDIDATE_STATE
        before = state_path.read_bytes()
        cap, _ = self.capture("--profile", profile)
        ok = self.credential_plan(cap)
        self.assertEqual(ok["status"], "ok", msg=json.dumps(ok, ensure_ascii=False))
        prepared = parse(run_cli(
            "stage3-prepare-validation",
            "--invocation-file", cap["invocation_file"],
            "--invocation-sha256", cap["invocation_sha256"],
            "--round", "1"))
        self.assertEqual(prepared["status"], "ok",
                         msg=json.dumps(prepared, ensure_ascii=False))
        handoff = Path(prepared["handoff_file"])
        output = Path(prepared["output_file"])
        target = Path(prepared["validation_file"])
        self.addCleanup(shutil.rmtree, handoff.parent, ignore_errors=True)
        protected = (self.root, state_path, self.prof_dir / CANDIDATES_MD,
                     Path(cap["invocation_file"]), results, handoff.parent,
                     handoff, output, target)
        profile.write_text("研究兴趣：第二版。\n", encoding="utf-8")
        self.assert_direct_refusal(
            lambda: self.credential_plan(cap), protected,
            "needs_refresh", "validation_source_changed")
        self.assert_direct_refusal(
            lambda: self.credential_finalize(cap, results), protected,
            "needs_refresh", "validation_source_changed")
        self.assertEqual(state_path.read_bytes(), before)


class CredentialCorrectionTests(InvocationCredentialBase):
    """§5.4/§5.5: the credential correction context and commit synthesis."""

    def assert_validator_after_correction(self, before, after):
        """Compare the entire recorded validation block across correction."""
        expected = json.loads(json.dumps(before["validator"]))
        expected["pending"] = {}
        expected["render_sha256"] = (
            after["cache"]["render"][CANDIDATES_MD]["sha256"])
        self.assertEqual(after["validator"], expected)

    def commit_baseline_with_group(self):
        results = self.write_results("base", self.all_docs())
        self.write_cross(results, GID_AB, [self.cross_candidate(
            "X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
            gap_owner={"P2": "dir_A", "P3": "dir_B"})])
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", str(results), "--program-root", self.root,
                            "--cross-direction-groups", CROSS_AB_ARG))
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return results

    def test_correction_reaches_directions_outside_the_first_round_scope(self):
        self.commit_baseline_with_group()
        selection = self.root / "sel-a.json"
        write_json(selection, {"selections": [
            {"professor": PROFESSOR, "direction_id": "dir_A"}]})
        cap, _ = self.capture("--refresh-scope", "selected", "--selection", selection,
                              "--cross-direction-groups", CROSS_AB_ARG)
        results = self.write_results("first", self.all_docs())
        self.write_cross(results, GID_AB, [self.cross_candidate(
            "X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
            gap_owner={"P2": "dir_A", "P3": "dir_B"})])
        first = self.credential_finalize(cap, results)
        self.assertEqual(first["status"], "ok", msg=json.dumps(first, ensure_ascii=False))

        self.validator_output([self.finding("候选 dir_B_1")])
        recorded = self.record()
        self.assertEqual(recorded["round"], 1)
        self.assertTrue(recorded["needs_correction"])
        baseline_after_record = self.load_state()
        self.assertEqual(baseline_after_record["validator"]["round"], 1)
        self.assertEqual(set(baseline_after_record["validator"]["pending"]),
                         {"direction:dir_B"})

        # The credential correction work set is exactly D — dir_B was outside
        # the first-round selection yet is named by the recorded round.
        cplan = self.credential_plan(cap, "--validation-file", self.validation)
        self.assertEqual(cplan["status"], "ok", msg=json.dumps(cplan, ensure_ascii=False))
        self.assertEqual(cplan["correction_scopes"], ["direction:dir_B"])
        self.assertEqual([job["direction_id"] for job in cplan["jobs"]], ["dir_B"])
        self.assertTrue(cplan["jobs"][0]["job_id"].startswith("candidates-correction:"))
        # Contrast (preserved §5.6 behavior): the old explicit entry still
        # applies the first-round selected filter and drops dir_B from scope.
        eplan = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                              "--program-root", self.root,
                              "--refresh-scope", "selected", "--selection", selection,
                              "--validation-file", self.validation))
        self.assertEqual(eplan["jobs"], [])

        corrected = self.generated_doc("dir_B", ["P1", "P3", None])
        corrected["candidates"][0]["title"] = "候选 dir_B_1 修正版"
        fix = self.write_results("cred-fix-b", {"dir_B": corrected})
        # Read-set sentinel: the correction's work set is exactly dir_B, so
        # garbage in the out-of-set result files must never be consumed and
        # must survive byte-identical.
        (fix / result_file("candidates", "dir_A")).write_bytes(b"{ corrupt dir_A")
        (fix / result_file("candidates", "dir_C")).write_bytes(b"{ corrupt dir_C")
        corrupt_before = {
            "dir_A": (fix / result_file("candidates", "dir_A")).read_bytes(),
            "dir_C": (fix / result_file("candidates", "dir_C")).read_bytes()}
        before = baseline_after_record
        with OpenRecorder() as recorder:
            out, code = call_runner(
                "stage3-finalize", "--invocation-file", cap["invocation_file"],
                "--invocation-sha256", cap["invocation_sha256"],
                "--results", str(fix), "--validation-file", self.validation)
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["corrected"], ["dir_B"])
        self.assertEqual(out["corrected_groups"], [])
        self.assertEqual(out["dropped_cross_direction"], [])
        self.assertEqual(frozenset(out["corrected"]), EXPECTED_DIRECTION_READS)
        self.assertEqual(
            {k: (fix / result_file("candidates", k)).read_bytes()
             for k in corrupt_before},
            corrupt_before, "out-of-set result files were never consumed")
        expected_reads = expected_result_read_paths(
            fix, direction_ids=EXPECTED_DIRECTION_READS)
        assert_result_read_set(self, recorder, fix, expected_reads)
        self.assertTrue(recorder.was_opened(
            fix / result_file("candidates", "dir_B")),
            "the in-scope direction result was opened through the real reader")
        for direction_id in ("dir_A", "dir_C"):
            self.assertFalse(recorder.was_opened(
                fix / result_file("candidates", direction_id)),
                f"out-of-scope direction result was opened: {direction_id}")
        after = self.load_state()
        by_did_before = {d["direction_id"]: d for d in before["directions"]}
        by_did_after = {d["direction_id"]: d for d in after["directions"]}
        changed_directions = frozenset(
            did for did in by_did_before
            if by_did_before[did] != by_did_after[did])
        self.assertEqual(changed_directions, EXPECTED_DIRECTION_READS,
                         "persisted direction replacements must match the fixed set")
        self.assertEqual(by_did_after["dir_A"], by_did_before["dir_A"])
        self.assertEqual(by_did_after["dir_C"], by_did_before["dir_C"])
        self.assertEqual(by_did_after["dir_B"]["candidates"][0]["title"],
                         "候选 dir_B_1 修正版")
        # The uninvolved cross-direction group survives untouched (§5.5-2).
        self.assertEqual(after["cross_direction_groups"],
                         before["cross_direction_groups"])
        self.assert_validator_after_correction(before, after)

    def test_exact_result_read_set_rejects_an_extra_open(self):
        results = self.write_results("read-set-negative", self.all_docs())
        expected = expected_result_read_paths(
            results, direction_ids=EXPECTED_DIRECTION_READS)
        in_scope = results / result_file("candidates", "dir_B")
        out_of_scope = results / result_file("candidates", "dir_A")
        out_of_scope.write_bytes(b"{ corrupt but unchanged after opening")
        out_of_scope_before = out_of_scope.read_bytes()

        with OpenRecorder() as clean:
            in_scope.read_bytes()
        assert_result_read_set(self, clean, results, expected)

        with OpenRecorder() as negative:
            in_scope.read_bytes()
            out_of_scope.read_bytes()
        self.assertEqual(out_of_scope.read_bytes(), out_of_scope_before,
                         "the negative control detects an open without a byte change")
        with self.assertRaises(AssertionError):
            assert_result_read_set(self, negative, results, expected)

    def test_first_round_skip_and_group_request_are_records_not_requests(self):
        # Baseline: dir_B skipped, cross group A+B committed.
        results = self.write_results("skip-base", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_C": self.generated_doc("dir_C", ["P4", "P4", None])})
        self.write_cross(results, GID_AB, [self.cross_candidate(
            "X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
            gap_owner={"P2": "dir_A", "P3": "dir_B"})])
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", str(results), "--program-root", self.root,
                            "--skip-direction-ids", "dir_B",
                            "--cross-direction-groups", CROSS_AB_ARG))
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))

        cap, _ = self.capture("--skip-direction-ids", "dir_B",
                              "--cross-direction-groups", CROSS_AB_ARG)
        rerun = self.credential_finalize(cap, results)
        self.assertEqual(rerun["status"], "ok", msg=json.dumps(rerun, ensure_ascii=False))
        self.assertEqual(rerun["skipped_direction_ids"], ["dir_B"])

        self.validator_output([self.finding("候选 dir_A_1")])
        self.assertEqual(self.record()["round"], 1)
        cplan = self.credential_plan(cap, "--validation-file", self.validation)
        self.assertEqual(cplan["status"], "ok", msg=json.dumps(cplan, ensure_ascii=False))
        self.assertEqual(cplan["correction_scopes"], ["direction:dir_A"])
        self.assertEqual([job["direction_id"] for job in cplan["jobs"]], ["dir_A"])
        # The recorded skip is a record: this round neither re-applies it nor
        # replays the recorded group request.
        self.assertEqual(cplan["skipped_direction_ids"], [])
        self.assertEqual(cplan["cross_direction_groups"], [])

        corrected = self.generated_doc("dir_A", ["P1", "P2", None])
        corrected["candidates"][0]["title"] = "候选 dir_A_1 修正版"
        fix = self.write_results("cred-fix-a", {"dir_A": corrected})
        before = self.load_state()
        with OpenRecorder() as recorder:
            out2, code = call_runner(
                "stage3-finalize", "--invocation-file", cap["invocation_file"],
                "--invocation-sha256", cap["invocation_sha256"],
                "--results", str(fix), "--validation-file", self.validation)
        self.assertEqual(code, 0)
        self.assertEqual(out2["status"], "ok", msg=json.dumps(out2, ensure_ascii=False))
        self.assertEqual(out2["corrected"], ["dir_A"])
        self.assertEqual(out2["corrected_groups"], [])
        self.assertEqual(out2["dropped_cross_direction"], [])
        self.assertEqual(frozenset(out2["corrected"]),
                         EXPECTED_SKIP_CORRECTION_READS)
        expected_reads = expected_result_read_paths(
            fix, direction_ids=EXPECTED_SKIP_CORRECTION_READS)
        assert_result_read_set(self, recorder, fix, expected_reads)
        after = self.load_state()
        dir_b = next(d for d in after["directions"]
                     if d["direction_id"] == "dir_B")
        self.assertEqual(dir_b["stage3_status"], "skipped",
                         "the untouched skip record survives the correction")
        self.assertEqual(after["cross_direction_groups"],
                         before["cross_direction_groups"],
                         "the unrequested group survives the correction")
        before_directions = {row["direction_id"]: row
                             for row in before["directions"]}
        after_directions = {row["direction_id"]: row
                            for row in after["directions"]}
        replaced = frozenset(
            did for did, row in before_directions.items()
            if row != after_directions[did])
        self.assertEqual(replaced, EXPECTED_SKIP_CORRECTION_READS)
        self.assertEqual(after_directions["dir_B"], before_directions["dir_B"])
        self.assert_validator_after_correction(before, after)

    def test_named_group_is_replaced_and_sibling_group_is_kept(self):
        results = self.write_results("two-groups", self.all_docs())
        self.write_cross(results, GID_AB, [self.cross_candidate(
            "X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
            gap_owner={"P2": "dir_A", "P3": "dir_B"})])
        self.write_ac_cross(results, "X2")
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", str(results), "--program-root", self.root,
                            "--cross-direction-groups", BOTH_GROUPS_ARG))
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        before = self.load_state()
        self.assertEqual([g["group_id"] for g in before["cross_direction_groups"]],
                         [GID_AB, GID_AC])

        cap, _ = self.capture("--cross-direction-groups", BOTH_GROUPS_ARG)
        rerun = self.credential_finalize(cap, results)
        self.assertEqual(rerun["status"], "ok", msg=json.dumps(rerun, ensure_ascii=False))

        self.validator_output([self.finding("候选 X1")])
        self.assertEqual(self.record()["round"], 1)
        baseline_after_record = self.load_state()
        self.assertEqual(set(baseline_after_record["validator"]["pending"]),
                         {f"group:{GID_AB}"})
        self.assertIn("dir_C", baseline_after_record["validator"]["results"])
        self.assertIn(GID_AC, baseline_after_record["validator"]["groups"])
        before = baseline_after_record
        cplan = self.credential_plan(cap, "--validation-file", self.validation)
        self.assertEqual(cplan["status"], "ok", msg=json.dumps(cplan, ensure_ascii=False))
        self.assertEqual(cplan["correction_scopes"], [f"group:{GID_AB}"])
        self.assertEqual([job["kind"] for job in cplan["jobs"]], ["cross_direction"])
        self.assertTrue(cplan["jobs"][0]["job_id"].startswith("cross-correction:"))

        corrected = self.cross_candidate(
            "X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
            gap_owner={"P2": "dir_A", "P3": "dir_B"})
        corrected["title"] = "候选 X1 修正版"
        fix = self.write_results("cred-fix-ab", {})
        self.write_cross(fix, GID_AB, [corrected])
        # Read-set sentinel: the sibling group's result file is corrupted in
        # place — the G=GID_AB correction must not consume or rewrite it.
        sibling = fix / result_file("candidates", GID_AC)
        sibling.write_bytes(b"{ corrupt sibling group")
        sibling_before = sibling.read_bytes()
        with OpenRecorder() as recorder:
            out2, code = call_runner(
                "stage3-finalize", "--invocation-file", cap["invocation_file"],
                "--invocation-sha256", cap["invocation_sha256"],
                "--results", str(fix), "--validation-file", self.validation)
        self.assertEqual(code, 0)
        self.assertEqual(out2["status"], "ok", msg=json.dumps(out2, ensure_ascii=False))
        self.assertEqual(out2["corrected"], [])
        self.assertEqual(out2["corrected_groups"], [GID_AB])
        self.assertEqual(out2["dropped_cross_direction"], [])
        self.assertEqual(frozenset(out2["corrected_groups"]), EXPECTED_GROUP_READS)
        self.assertEqual(sibling.read_bytes(), sibling_before,
                         "the out-of-work-set group result was never consumed")
        expected_reads = expected_result_read_paths(
            fix, group_ids=EXPECTED_GROUP_READS)
        assert_result_read_set(self, recorder, fix, expected_reads)
        self.assertTrue(recorder.was_opened(
            fix / result_file("candidates", GID_AB)),
            "the in-scope group result was opened through the real reader")
        self.assertFalse(recorder.was_opened(sibling),
                         "the corrupted sibling group result was never opened")
        after = self.load_state()
        groups = {g["group_id"]: g for g in after["cross_direction_groups"]}
        before_groups = {g["group_id"]: g
                         for g in before["cross_direction_groups"]}
        changed_groups = frozenset(
            gid for gid in before_groups
            if before_groups[gid] != groups[gid])
        self.assertEqual(changed_groups, EXPECTED_GROUP_READS,
                         "persisted group replacements must match the fixed set")
        self.assertEqual([g["group_id"] for g in after["cross_direction_groups"]],
                         [GID_AB, GID_AC], "identity set and order stay unchanged")
        self.assertEqual(groups[GID_AC],
                         next(g for g in before["cross_direction_groups"]
                              if g["group_id"] == GID_AC))
        self.assertEqual(groups[GID_AB]["candidates"][0]["title"], "候选 X1 修正版")
        self.assertEqual(groups[GID_AB]["direction_fingerprints"],
                         next(g for g in before["cross_direction_groups"]
                              if g["group_id"] == GID_AB)["direction_fingerprints"])
        # Group correction does not touch the participating ordinary
        # directions: their candidates and preserved validator records stay.
        by_did = {d["direction_id"]: d for d in after["directions"]}
        by_did_before = {d["direction_id"]: d for d in before["directions"]}
        self.assertEqual(by_did["dir_A"], by_did_before["dir_A"])
        self.assertEqual(by_did["dir_B"], by_did_before["dir_B"])
        changed_directions = frozenset(
            did for did, row in by_did.items()
            if row != by_did_before[did])
        self.assertEqual(changed_directions, frozenset())
        self.assert_validator_after_correction(before, after)
        self.assertEqual(after["validator"]["results"]["dir_C"],
                         before["validator"]["results"]["dir_C"])
        self.assertEqual(after["validator"]["groups"][GID_AC],
                         before["validator"]["groups"][GID_AC])

        # Negative control: the complete record comparison catches losing
        # even one unaffected direction's validator record.
        cleared = json.loads(json.dumps(after))
        del cleared["validator"]["results"]["dir_C"]
        with self.assertRaises(AssertionError):
            self.assert_validator_after_correction(before, cleared)

    def test_render_text_quote_expands_scopes_under_credential(self):
        """File-level expansion (render text, not a candidate title) keeps
        working through the credential correction path (r13 §5.4)."""
        self.commit_baseline_with_group()
        cap, _ = self.capture()
        rerun = self.credential_finalize(cap, self.write_results(
            "expand-base", self.all_docs()))
        self.assertEqual(rerun["status"], "ok", msg=json.dumps(rerun, ensure_ascii=False))
        # "流式输入" only appears in each candidate's research_question prose,
        # so the scope comes from the rendered text, never from a caller guess.
        self.validator_output([self.finding("流式输入")])
        self.assertEqual(self.record()["needs_correction"], True)
        baseline_after_record = self.load_state()
        self.assertEqual(set(baseline_after_record["validator"]["pending"]),
                         {f"direction:{did}"
                          for did in EXPECTED_FILE_QUOTE_DIRECTIONS})
        cplan = self.credential_plan(cap, "--validation-file", self.validation)
        self.assertEqual(cplan["status"], "ok", msg=json.dumps(cplan, ensure_ascii=False))
        self.assertEqual(cplan["correction_scopes"],
                         ["direction:dir_A", "direction:dir_B", "direction:dir_C"])
        self.assertEqual(
            frozenset(job["direction_id"] for job in cplan["jobs"]),
            EXPECTED_FILE_QUOTE_DIRECTIONS)
        self.assertEqual([job["direction_id"] for job in cplan["jobs"]],
                         sorted(EXPECTED_FILE_QUOTE_DIRECTIONS))

        docs = {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None]),
            "dir_C": self.generated_doc("dir_C", ["P4", "P4", None]),
        }
        for did, doc in docs.items():
            doc["candidates"][0]["title"] += " 文件级修正版"
        fix = self.write_results("file-quote-fix", docs)
        with OpenRecorder() as recorder:
            out, code = call_runner(
                "stage3-finalize", "--invocation-file", cap["invocation_file"],
                "--invocation-sha256", cap["invocation_sha256"],
                "--results", str(fix), "--validation-file", self.validation)
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(frozenset(out["corrected"]),
                         EXPECTED_FILE_QUOTE_DIRECTIONS)
        self.assertEqual(out["corrected_groups"], [])
        expected_reads = expected_result_read_paths(
            fix, direction_ids=EXPECTED_FILE_QUOTE_DIRECTIONS)
        assert_result_read_set(self, recorder, fix, expected_reads)

        after = self.load_state()
        before_directions = {
            row["direction_id"]: row
            for row in baseline_after_record["directions"]}
        after_directions = {row["direction_id"]: row for row in after["directions"]}
        replaced = frozenset(
            did for did, row in before_directions.items()
            if row != after_directions[did])
        self.assertEqual(replaced, EXPECTED_FILE_QUOTE_DIRECTIONS)
        self.assertEqual(after["cross_direction_groups"],
                         baseline_after_record["cross_direction_groups"])
        self.assert_validator_after_correction(baseline_after_record, after)

    def test_credential_correction_requires_a_recorded_open_round(self):
        self.commit_baseline_with_group()
        state_path = self.prof_dir / CANDIDATE_STATE
        cap, _ = self.capture()
        # An unrecorded validation file never authorizes a credential correction.
        self.validator_output([self.finding("候选 dir_A_1")])
        protected = (self.root, self.prof_dir / CANDIDATES_MD, state_path,
                     Path(cap["invocation_file"]), self.validation)
        self.assert_direct_refusal(
            lambda: self.credential_plan(
                cap, "--validation-file", self.validation),
            protected, "error", "validation_evidence_not_recorded")
        # An empty work set (a recorded round without open findings) also stops.
        self.validator_output([])
        self.assertEqual(self.record()["needs_correction"], False)
        cap2, _ = self.capture()
        protected2 = (self.root, self.prof_dir / CANDIDATES_MD, state_path,
                      Path(cap2["invocation_file"]), self.validation)
        self.assert_direct_refusal(
            lambda: self.credential_plan(
                cap2, "--validation-file", self.validation),
            protected2, "error", "validation_evidence_not_recorded")


class PlainGenerationCompatTests(InvocationCredentialBase):
    """§5.5/§5.6: the old group-drop rule stays a plain-generation rule."""

    def test_explicit_correction_preserves_uninvolved_groups_in_old_order(self):
        results = self.write_results("two-groups", self.all_docs())
        self.write_cross(results, GID_AB, [self.cross_candidate(
            "X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
            gap_owner={"P2": "dir_A", "P3": "dir_B"})])
        self.write_ac_cross(results, "X2")
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", str(results), "--program-root", self.root,
                            "--cross-direction-groups", BOTH_GROUPS_ARG))
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        before = self.load_state()

        self.validator_output([self.finding("候选 dir_B_1")])
        self.assertEqual(self.record()["round"], 1)
        corrected = self.generated_doc("dir_B", ["P1", "P3", None])
        corrected["candidates"][0]["title"] = "候选 dir_B_1 修正版"
        fix = self.write_results("exp-fix-b", {"dir_B": corrected})
        out2 = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                             "--results", str(fix), "--program-root", self.root,
                             "--validation-file", self.validation))
        self.assertEqual(out2["status"], "ok", msg=json.dumps(out2, ensure_ascii=False))
        self.assertEqual(out2["corrected"], ["dir_B"])
        self.assertEqual(out2["corrected_groups"], [])
        # The behavior fix: unrequested groups are no longer removal requests.
        self.assertEqual(out2["dropped_cross_direction"], [])
        after = self.load_state()
        self.assertEqual(after["cross_direction_groups"],
                         before["cross_direction_groups"])
        by_did = {d["direction_id"]: d for d in after["directions"]}
        self.assertEqual(by_did["dir_B"]["candidates"][0]["title"],
                         "候选 dir_B_1 修正版")

    def test_plain_generation_still_drops_unrequested_groups(self):
        results = self.write_results("plain-base", self.all_docs())
        self.write_cross(results, GID_AB, [self.cross_candidate(
            "X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
            gap_owner={"P2": "dir_A", "P3": "dir_B"})])
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", str(results), "--program-root", self.root,
                            "--cross-direction-groups", CROSS_AB_ARG))
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        cap, _ = self.capture()
        out2 = self.credential_finalize(cap, results)
        self.assertEqual(out2["status"], "ok", msg=json.dumps(out2, ensure_ascii=False))
        # A credential plain generation replays only the recorded group
        # requests; none were recorded, so the old drop rule applies unchanged.
        self.assertEqual(out2["dropped_cross_direction"],
                         [{"group_id": GID_AB,
                           "direction_ids": ["dir_A", "dir_B"],
                           "reason": "group_not_requested"}])
        self.assertEqual(self.load_state()["cross_direction_groups"], [])


if __name__ == "__main__":
    unittest.main()
