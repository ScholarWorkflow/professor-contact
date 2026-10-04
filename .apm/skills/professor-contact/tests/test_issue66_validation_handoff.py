"""Issue #66 r13 §6 acceptance: validation evidence production, handoff, record.

Exactly this implementation step, nothing more:
- §6.1  ``stage3-prepare-validation`` verifies the invocation credential and the
        professor's committed state, derives the round decision from the
        recorded validator facts (never from the temp directory), and creates a
        one-time handoff (metadata + validator output path + saved target path)
        in an exclusive per-professor/per-round system-temp directory.
- §6.3  ``stage3-save-validation`` re-verifies the handoff (metadata digest,
        credential bytes, professor, round, render), then copies the regular
        source file's exact bytes — no re-serialization — to a target created
        exclusively; a full failure verdict is equally legal; failures clean
        only what they created.
- §6.4  ``stage3-record-validation --handoff-file + --handoff-sha256 +
        --expected-validation-sha256`` digests the exact byte buffer it parses,
        then reuses the existing evidence/scopes/round rules; the legacy
        ``--professor-dir + --validation-file`` mode is untouched and the two
        modes are mutually exclusive.

Proof conventions follow the shared fixtures: real CLI runs, direct file
reads for byte claims, no sleeps, no owner mocking.
"""
import hashlib
import itertools
import json
import os
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import (
    parse, quote_id, run_cli, write_json)
from test_stage3_direction_groups import (
    PROFESSOR, Stage3DirectionGroupBase, contact_state, result_file)

CANDIDATE_STATE = "套磁候选状态.json"
CANDIDATES_MD = "套磁想法候选.md"
INVOCATION_VERSION = "stage3-invocation-v1"
HANDOFF_VERSION = "stage3-handoff-v1"


class ValidationHandoffBase(Stage3DirectionGroupBase):
    """The shared pipeline, plus one captured first-round credential.

    The first generation commit is intentional: prepare/save/record all read
    the COMMITTED candidate state, so tests opt in via ``commit_first``.
    """

    def setUp(self):
        super().setUp()
        cap_dir = self.root / "invocation"
        plan = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root,
                             "--capture-invocation", cap_dir))
        self.assertEqual(plan["status"], "ok",
                         msg=json.dumps(plan, ensure_ascii=False))
        self.cap = plan
        self._seq = itertools.count(1)
        self.g1 = self.write_results("g1", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})

    # -- pipeline helpers --------------------------------------------------

    def commit_first(self):
        out = self.credential_finalize(self.g1)
        self.assertEqual(out["status"], "ok",
                         msg=json.dumps(out, ensure_ascii=False))
        return out

    def credential_finalize(self, results, *extra):
        return parse(run_cli("stage3-finalize",
                             "--invocation-file", self.cap["invocation_file"],
                             "--invocation-sha256", self.cap["invocation_sha256"],
                             "--results", str(results), *extra))

    def credential_plan(self, *extra):
        return parse(run_cli("stage3-plan",
                             "--invocation-file", self.cap["invocation_file"],
                             "--invocation-sha256", self.cap["invocation_sha256"],
                             *extra))

    # -- handoff helpers ---------------------------------------------------

    def prepare(self, round_no, *extra):
        return parse(run_cli("stage3-prepare-validation",
                             "--invocation-file", self.cap["invocation_file"],
                             "--invocation-sha256", self.cap["invocation_sha256"],
                             "--round", str(round_no), *extra))

    def prepare_credential(self, payload, round_no):
        path, sha = self.write_credential(payload)
        return parse(run_cli("stage3-prepare-validation",
                             "--invocation-file", path,
                             "--invocation-sha256", sha,
                             "--round", str(round_no)))

    def write_credential(self, payload):
        path = self.root / f"crafted-{next(self._seq)}.json"
        write_json(path, payload)
        return str(path), hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def finding(quote):
        return {"rule": "B5", "severity": "blocking", "location": "validator 自报位置",
                "quote": quote, "suggestion": "首次出现时用日常语言解释。"}

    def validator_bytes(self, issues=(), verdict=None):
        """The validator's complete single business message as exact bytes."""
        blocking = [i for i in issues if i.get("severity") == "blocking"]
        payload = {"result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": verdict or ("fail" if blocking else "pass"),
            "blocking": len(blocking), "minor": 0, "issues": list(issues)}],
            "notes": ""}
        return (json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8")

    def validator_writes(self, out, issues=(), verdict=None):
        """The validator's one exclusive write of its raw message bytes."""
        raw = self.validator_bytes(issues, verdict)
        target = Path(out["output_file"])
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        return raw

    def save(self, out, sha=None):
        return parse(run_cli("stage3-save-validation",
                             "--handoff-file", out["handoff_file"],
                             "--handoff-sha256", sha or out["handoff_sha256"]))

    def record_handoff(self, out, expected_sha):
        return parse(run_cli("stage3-record-validation",
                             "--handoff-file", out["handoff_file"],
                             "--handoff-sha256", out["handoff_sha256"],
                             "--expected-validation-sha256", expected_sha))

    def write_legacy_validation(self, raw):
        path = self.root / f"legacy-validation-{next(self._seq)}.json"
        path.write_bytes(raw)
        return path

    def record_legacy(self, raw):
        path = self.write_legacy_validation(raw)
        return parse(run_cli("stage3-record-validation",
                             "--professor-dir", self.prof_dir,
                             "--validation-file", path))

    def load_state(self):
        return json.loads(
            (self.prof_dir / CANDIDATE_STATE).read_text(encoding="utf-8"))

    def recommit_changed_render(self, name):
        """A new committed render over the same credential, deterministically.

        Render timestamps only carry second resolution, so the render is moved
        by regenerating dir_A from changed content: its recorded fingerprint is
        invalidated in the pack, which defeats the reuse gate.
        """
        self.rewrite_pack_fingerprint("dir_A", f"sha256:{name}")
        changed = self.generated_doc("dir_A", ["P1", "P2", None])
        changed["candidates"][0]["title"] = f"候选 dir_A_1 {name}"
        regen = self.write_results(f"regen-{name}", {"dir_A": changed})
        out = self.credential_finalize(regen)
        self.assertEqual(out["status"], "ok",
                         msg=json.dumps(out, ensure_ascii=False))
        return out


class PrepareHandoffTests(ValidationHandoffBase):
    """§6.1: credential verification, round facts, exclusive creation."""

    def test_prepare_creates_the_one_time_round_handoff(self):
        self.commit_first()
        out = self.prepare(1)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["round"], 1)
        self.assertEqual(out["professor_dir"], str(self.prof_dir.resolve()))
        self.assertEqual(out["candidates_md"],
                         str((self.prof_dir / CANDIDATES_MD).resolve()))
        state = self.load_state()
        self.assertEqual(out["render_sha256"],
                         state["cache"]["render"][CANDIDATES_MD]["sha256"])
        handoff = Path(out["handoff_file"])
        raw = handoff.read_bytes()
        self.assertEqual(out["handoff_sha256"], hashlib.sha256(raw).hexdigest())
        metadata = json.loads(raw.decode("utf-8"))
        self.assertEqual(metadata["version"], HANDOFF_VERSION)
        self.assertEqual(metadata["professor_dir"], str(self.prof_dir.resolve()))
        self.assertEqual(metadata["round"], 1)
        self.assertEqual(metadata["render_sha256"], out["render_sha256"])
        self.assertEqual(metadata["invocation_file"],
                         str(Path(self.cap["invocation_file"]).resolve()))
        self.assertEqual(metadata["invocation_sha256"], self.cap["invocation_sha256"])
        # Source and target are distinct, bound in the metadata, and absent.
        out_path, target = Path(out["output_file"]), Path(out["validation_file"])
        self.assertNotEqual(out_path, target)
        self.assertEqual(metadata["output_file"], str(out_path))
        self.assertEqual(metadata["validation_file"], str(target))
        self.assertFalse(out_path.exists())
        self.assertFalse(target.exists())
        # Temp files never enter the professor state directory.
        self.assertNotEqual(Path(out["professor_dir"]),
                            Path(out["handoff_file"]).parent)

    def test_prepare_verifies_the_credential_first(self):
        self.commit_first()
        template = json.loads(
            Path(self.cap["invocation_file"]).read_text(encoding="utf-8"))
        # Digest mismatch over the real credential bytes.
        out = parse(run_cli("stage3-prepare-validation",
                            "--invocation-file", self.cap["invocation_file"],
                            "--invocation-sha256", "0" * 64, "--round", "1"))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "invocation_sha256_mismatch")
        # Damaged credential, digest of the damaged bytes.
        out = self.prepare_credential({"version": INVOCATION_VERSION, "oops": True}, 1)
        self.assertEqual(out["reason_code"], "invalid_invocation")
        # Unsupported credential version.
        out = self.prepare_credential({**template, "version": "stage3-invocation-v0"}, 1)
        self.assertEqual(out["reason_code"], "invocation_version_unsupported")
        # Professor directory outside the credential's program root.
        out = self.prepare_credential(
            {**template, "professor_dir": str(self.root / "其他研究" / PROFESSOR)}, 1)
        self.assertEqual(out["reason_code"], "invalid_professor_dir")
        # Nothing above wrote a handoff for this professor's round directory.
        self.assertFalse(self.handoff_round_dir(1).exists())

    def handoff_round_dir(self, round_no):
        token = hashlib.sha256(
            str(self.prof_dir.resolve()).encode("utf-8")).hexdigest()[:16]
        return Path(tempfile.gettempdir()) / "professor-contact-stage3-handoff" \
            / token / f"round-{round_no}"

    def test_prepare_rejects_a_stale_profile_digest(self):
        profile = self.root / "profile.md"
        profile.write_text("研究兴趣：第一版。\n", encoding="utf-8")
        cap_dir = self.root / "invocation-profiled"
        plan = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root, "--profile", profile,
                             "--capture-invocation", cap_dir))
        self.assertEqual(plan["status"], "ok",
                         msg=json.dumps(plan, ensure_ascii=False))
        self.commit_first()
        profile.write_text("研究兴趣：第二版。\n", encoding="utf-8")
        out = parse(run_cli("stage3-prepare-validation",
                            "--invocation-file", plan["invocation_file"],
                            "--invocation-sha256", plan["invocation_sha256"],
                            "--round", "1"))
        self.assertEqual(out["status"], "needs_refresh",
                         msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["reason_code"], "validation_source_changed")

    def test_round_rules_come_from_committed_records(self):
        # No committed state yet: prepare reads the professor, nothing else.
        out = self.prepare(1)
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "missing_candidate_state")
        self.commit_first()
        # Round 2 without any recorded round is refused.
        out = self.prepare(2)
        self.assertEqual(out["reason_code"], "validation_round_sequence_invalid")
        out1 = self.prepare(1)
        self.assertEqual(out1["status"], "ok", msg=json.dumps(out1, ensure_ascii=False))
        raw = self.validator_writes(out1, [self.finding("候选 dir_A_1")])
        saved = self.save(out1)
        self.assertEqual(saved["status"], "ok",
                         msg=json.dumps(saved, ensure_ascii=False))
        recorded = self.record_handoff(out1, saved["validation_sha256"])
        self.assertEqual(recorded["status"], "ok",
                         msg=json.dumps(recorded, ensure_ascii=False))
        self.assertEqual(recorded["round"], 1)
        self.assertTrue(recorded["needs_correction"])
        # Round 1 cannot be reopened over a recorded round…
        out = self.prepare(1)
        self.assertEqual(out["reason_code"], "validation_round_already_recorded")
        # …and round 2 cannot bypass the owed correction.
        out = self.prepare(2)
        self.assertEqual(out["reason_code"], "validation_correction_required")
        # Commit the credential correction (Step 1 context) with the recorded file.
        cplan = self.credential_plan("--validation-file", saved["validation_file"])
        self.assertEqual(cplan["status"], "ok",
                         msg=json.dumps(cplan, ensure_ascii=False))
        self.assertEqual(cplan["correction_scopes"], ["direction:dir_A"])
        corrected = self.generated_doc("dir_A", ["P1", "P2", None])
        corrected["candidates"][0]["title"] = "候选 dir_A_1 修正版"
        fix = self.write_results("fix-a", {"dir_A": corrected})
        fin = self.credential_finalize(fix, "--validation-file", saved["validation_file"])
        self.assertEqual(fin["status"], "ok",
                         msg=json.dumps(fin, ensure_ascii=False))
        # Still no round 1; round 2 now matches the committed correction facts.
        self.assertEqual(self.prepare(1)["reason_code"],
                         "validation_round_already_recorded")
        out2 = self.prepare(2)
        self.assertEqual(out2["status"], "ok",
                         msg=json.dumps(out2, ensure_ascii=False))
        self.assertEqual(out2["round"], 2)
        self.assertNotEqual(out2["render_sha256"], saved["render_sha256"])
        self.assertNotEqual(out2["validation_file"], out1["validation_file"])
        self.assertNotEqual(out2["handoff_file"], out1["handoff_file"])

    def test_round_two_needs_a_correction_not_a_pass(self):
        self.commit_first()
        out = self.prepare(1)
        self.validator_writes(out)
        saved = self.save(out)
        recorded = self.record_handoff(out, saved["validation_sha256"])
        self.assertFalse(recorded["needs_correction"])
        # Round 1 recorded pass: the terminal record already exists.
        out = self.prepare(2)
        self.assertEqual(out["reason_code"], "validation_rounds_exhausted")

    def test_prepare_never_reuses_a_round_directory(self):
        self.commit_first()
        first = self.prepare(1)
        self.assertEqual(first["status"], "ok",
                         msg=json.dumps(first, ensure_ascii=False))
        handoff_bytes = Path(first["handoff_file"]).read_bytes()
        second = self.prepare(1)
        self.assertEqual(second["status"], "error")
        self.assertEqual(second["reason_code"], "validation_handoff_collision")
        self.assertEqual(Path(first["handoff_file"]).read_bytes(), handoff_bytes,
                         "the first handoff is immutable, never reused")


class SaveHandoffTests(ValidationHandoffBase):
    """§6.3: metadata re-verification, byte-exact copy, failure discipline."""

    def test_save_copies_the_exact_source_bytes(self):
        self.commit_first()
        out = self.prepare(1)
        # Deliberately non-canonical serialization: unsorted keys, indent=2,
        # no trailing newline — the copy may not normalize any of it.
        payload = {"notes": "备注正文", "result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "pass", "blocking": 0, "minor": 1, "issues": []}]}
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.assertFalse(raw.endswith(b"\n"))
        fd = os.open(out["output_file"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        saved = self.save(out)
        self.assertEqual(saved["status"], "ok",
                         msg=json.dumps(saved, ensure_ascii=False))
        self.assertEqual(saved["validation_file"], out["validation_file"])
        self.assertEqual(saved["validation_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(saved["round"], 1)
        self.assertEqual(saved["render_sha256"], out["render_sha256"])
        self.assertEqual(Path(saved["validation_file"]).read_bytes(), raw)
        # The source survives the save (forensics stay possible).
        self.assertEqual(Path(out["output_file"]).read_bytes(), raw)

    def test_save_verifies_utf8_json_structure_and_attribution(self):
        self.commit_first()
        out = self.prepare(1)
        source = Path(out["output_file"])
        def attempt(raw, label, reason="invalid_validation_json"):
            source.write_bytes(raw)
            with self.subTest(case=label):
                saved = self.save(out)
                self.assertEqual(saved["status"], "error")
                self.assertEqual(saved["reason_code"], reason)
                # A failed save never deletes the validator's source.
                self.assertEqual(source.read_bytes(), raw)
        attempt(b"\xff\xfe not utf-8", "invalid utf-8")
        attempt(b"{ malformed", "broken json")
        attempt(json.dumps({"result": "ok", "files": []}).encode("utf-8"),
                "missing notes")
        attempt(json.dumps({"result": "ok", "notes": "", "files": [{
            "file": str(self.prof_dir / "套磁候选分析.md"), "artifact": "candidates",
            "verdict": "pass", "issues": []}]}).encode("utf-8"),
            "candidates entry not bound to this professor")
        attempt(json.dumps({"result": "ok", "notes": "", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "mostly_fine", "issues": []}]}).encode("utf-8"),
            "unknown verdict")
        attempt(json.dumps({"result": "ok", "notes": "", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "fail", "issues": []}]}).encode("utf-8"),
            "fail without blocking issue")
        # A complete failure result is equally legal.
        raw = self.validator_bytes([self.finding("候选 dir_A_1")])
        source.write_bytes(raw)
        saved = self.save(out)
        self.assertEqual(saved["status"], "ok",
                         msg=json.dumps(saved, ensure_ascii=False))
        self.assertEqual(Path(saved["validation_file"]).read_bytes(), raw)

    def test_save_rejects_symlinks_and_existing_targets(self):
        self.commit_first()
        out = self.prepare(1)
        raw = self.validator_writes(out)
        source, target = Path(out["output_file"]), Path(out["validation_file"])
        # A symlinked source is not this round's regular file.
        shadow = self.root / "shadow-output.json"
        shadow.write_bytes(raw)
        source.unlink()
        source.symlink_to(shadow)
        saved = self.save(out)
        self.assertEqual(saved["reason_code"], "invalid_validation_source")
        self.assertTrue(shadow.exists(), "a failed save keeps the source material")
        # Restore the real source; a dangling target symlink is refused too.
        source.unlink()
        source.write_bytes(raw)
        target.symlink_to(self.root / "missing.json")
        saved = self.save(out)
        self.assertEqual(saved["reason_code"], "validation_handoff_collision")
        # A plain pre-existing target is refused without touching it.
        target.unlink()
        marker = "占位".encode("utf-8")
        target.write_bytes(marker)
        saved = self.save(out)
        self.assertEqual(saved["reason_code"], "validation_handoff_collision")
        self.assertEqual(target.read_bytes(), marker)
        # The clean path still succeeds and creates the target exclusively.
        target.unlink()
        saved = self.save(out)
        self.assertEqual(saved["status"], "ok",
                         msg=json.dumps(saved, ensure_ascii=False))
        self.assertEqual(target.read_bytes(), raw)
        # And a second save can never overwrite the recorded target.
        again = self.save(out)
        self.assertEqual(again["reason_code"], "validation_handoff_collision")
        self.assertEqual(target.read_bytes(), raw)

    def test_save_refuses_tampered_or_foreign_metadata(self):
        self.commit_first()
        out = self.prepare(1)
        self.validator_writes(out)
        # Wrong handoff digest.
        saved = self.save(out, sha="0" * 64)
        self.assertEqual(saved["status"], "error")
        self.assertEqual(saved["reason_code"], "handoff_sha256_mismatch")
        metadata = json.loads(
            Path(out["handoff_file"]).read_text(encoding="utf-8"))
        # Tampered version, re-digested honestly.
        tampered = {**metadata, "version": "stage3-handoff-v0"}
        path = self.root / "tampered-handoff.json"
        write_json(path, tampered)
        saved = parse(run_cli("stage3-save-validation", "--handoff-file", path,
                              "--handoff-sha256",
                              hashlib.sha256(path.read_bytes()).hexdigest()))
        self.assertEqual(saved["reason_code"], "invalid_handoff")
        # Broken credential binding inside the metadata.
        tampered = {**metadata, "invocation_sha256": "0" * 64}
        write_json(path, tampered)
        saved = parse(run_cli("stage3-save-validation", "--handoff-file", path,
                              "--handoff-sha256",
                              hashlib.sha256(path.read_bytes()).hexdigest()))
        self.assertEqual(saved["reason_code"], "invalid_handoff")
        self.assertFalse(Path(out["validation_file"]).exists())

    def test_save_refuses_a_changed_render(self):
        self.commit_first()
        out = self.prepare(1)
        self.validator_writes(out)
        # A new plain commit over the same credential advances the render.
        self.recommit_changed_render("改版")
        saved = self.save(out)
        self.assertEqual(saved["status"], "error")
        self.assertEqual(saved["reason_code"], "validation_render_changed")
        self.assertFalse(Path(out["validation_file"]).exists())


class RecordHandoffTests(ValidationHandoffBase):
    """§6.4: digest over the parsed buffer, mode exclusivity, legacy compat."""

    def committed_round1(self, issues=()):
        self.commit_first()
        out = self.prepare(1)
        self.validator_writes(out, list(issues))
        saved = self.save(out)
        self.assertEqual(saved["status"], "ok",
                         msg=json.dumps(saved, ensure_ascii=False))
        return out, saved

    def test_record_modes_are_mutually_exclusive(self):
        out, saved = self.committed_round1()
        base = ["--handoff-file", out["handoff_file"],
                "--handoff-sha256", out["handoff_sha256"],
                "--expected-validation-sha256", saved["validation_sha256"]]
        # A partial handoff triple is refused.
        partial = parse(run_cli("stage3-record-validation",
                                "--handoff-file", out["handoff_file"]))
        self.assertEqual(partial["status"], "error")
        self.assertEqual(partial["reason_code"], "invalid_params")
        # Handoff + legacy arguments mix is refused without precedence.
        mixed = parse(run_cli("stage3-record-validation", *base,
                              "--professor-dir", self.prof_dir))
        self.assertEqual(mixed["status"], "error")
        self.assertEqual(mixed["reason_code"], "invalid_params")
        mixed2 = parse(run_cli("stage3-record-validation", *base,
                               "--validation-file", saved["validation_file"]))
        self.assertEqual(mixed2["status"], "error")
        self.assertEqual(mixed2["reason_code"], "invalid_params")
        # Neither mode is also refused.
        neither = parse(run_cli("stage3-record-validation"))
        self.assertEqual(neither["status"], "error")
        self.assertEqual(neither["reason_code"], "invalid_params")
        state = self.load_state()
        self.assertIsNone(state.get("validator"))

    def test_record_digests_the_bytes_it_actually_parses(self):
        out, saved = self.committed_round1([self.finding("候选 dir_A_1")])
        expected = saved["validation_sha256"]
        wrong = parse(run_cli("stage3-record-validation",
                              "--handoff-file", out["handoff_file"],
                              "--handoff-sha256", out["handoff_sha256"],
                              "--expected-validation-sha256", "0" * 64))
        self.assertEqual(wrong["status"], "error")
        self.assertEqual(wrong["reason_code"], "validation_sha256_mismatch")
        state = self.load_state()
        self.assertIsNone(state.get("validator"),
                          "a refused record writes nothing")
        # The accepted digest is exactly what the record consumed.
        recorded = self.record_handoff(out, expected)
        self.assertEqual(recorded["status"], "ok",
                         msg=json.dumps(recorded, ensure_ascii=False))
        self.assertEqual(recorded["validation_input_sha256"], expected)
        self.assertEqual(recorded["round"], 1)
        self.assertTrue(recorded["needs_correction"])
        state = self.load_state()
        self.assertEqual(state["validator"]["round"], 1)
        self.assertEqual(state["validator"]["render_sha256"],
                         saved["render_sha256"])

    def test_record_refuses_a_render_that_moved_after_prepare(self):
        out, saved = self.committed_round1()
        self.recommit_changed_render("挪动")
        recorded = self.record_handoff(out, saved["validation_sha256"])
        self.assertEqual(recorded["status"], "error")
        self.assertEqual(recorded["reason_code"], "validation_render_changed")
        self.assertIsNone(self.load_state().get("validator"))

    def test_legacy_record_mode_stays_unchanged(self):
        self.commit_first()
        raw = self.validator_bytes()
        path = self.write_legacy_validation(raw)
        recorded = parse(run_cli("stage3-record-validation",
                                 "--professor-dir", self.prof_dir,
                                 "--validation-file", path))
        self.assertEqual(recorded["status"], "ok",
                         msg=json.dumps(recorded, ensure_ascii=False))
        self.assertEqual(recorded["round"], 1)
        self.assertFalse(recorded["needs_correction"])
        self.assertEqual(recorded["validation_input_sha256"],
                         hashlib.sha256(raw).hexdigest())


class EndToEndHandoffLoopTests(ValidationHandoffBase):
    """§6.4/§7: prepare → validator → save → record → correction → round 2."""

    def test_first_round_correction_and_second_round_loop(self):
        # G1: the generator committed; prepare round 1 (准备一).
        self.commit_first()
        out1 = self.prepare(1)
        self.assertEqual(out1["status"], "ok",
                         msg=json.dumps(out1, ensure_ascii=False))
        # V1: the validator writes its one raw file; the final message bytes
        # are exactly the file bytes by construction here.
        raw1 = self.validator_writes(out1, [self.finding("候选 dir_A_1")])
        # 保存一: byte-exact copy; 记录一: needs_correction drives the loop.
        saved1 = self.save(out1)
        self.assertEqual(Path(saved1["validation_file"]).read_bytes(), raw1)
        rec1 = self.record_handoff(out1, saved1["validation_sha256"])
        self.assertTrue(rec1["needs_correction"])
        # G2: the correction sub-thread reuses the ORIGINAL credential plus the
        # recorded validation file (Step 1 correction context).
        cplan = self.credential_plan("--validation-file", saved1["validation_file"])
        self.assertEqual(cplan["status"], "ok",
                         msg=json.dumps(cplan, ensure_ascii=False))
        self.assertEqual(cplan["correction_scopes"], ["direction:dir_A"])
        corrected = self.generated_doc("dir_A", ["P1", "P2", None])
        corrected["candidates"][0]["title"] = "候选 dir_A_1 修正版"
        fix = self.write_results("g2", {"dir_A": corrected})
        fin2 = self.credential_finalize(fix, "--validation-file",
                                        saved1["validation_file"])
        self.assertEqual(fin2["status"], "ok",
                         msg=json.dumps(fin2, ensure_ascii=False))
        self.assertEqual(fin2["corrected"], ["dir_A"])
        # 准备二 from the same credential on the corrected render.
        out2 = self.prepare(2)
        self.assertEqual(out2["status"], "ok",
                         msg=json.dumps(out2, ensure_ascii=False))
        self.assertNotEqual(out2["render_sha256"], out1["render_sha256"])
        # V2 passes: 保存二 → 记录二 → terminal.
        raw2 = self.validator_writes(out2)
        saved2 = self.save(out2)
        self.assertEqual(saved2["status"], "ok",
                         msg=json.dumps(saved2, ensure_ascii=False))
        rec2 = self.record_handoff(out2, saved2["validation_sha256"])
        self.assertEqual(rec2["status"], "ok",
                         msg=json.dumps(rec2, ensure_ascii=False))
        self.assertEqual(rec2["round"], 2)
        self.assertFalse(rec2["needs_correction"])
        self.assertTrue(rec2["terminal"])
        state = self.load_state()
        self.assertEqual(state["validator"]["round"], 2)
        self.assertEqual(state["validator"]["results"]["dir_A"]["result"], "pass")
        self.assertEqual(state["validator"]["results"]["dir_A"]["rounds"], 2)
        self.assertEqual(state["validator"]["render_sha256"],
                         state["cache"]["render"][CANDIDATES_MD]["sha256"])
        # A third round can never be prepared.
        self.assertEqual(self.prepare(1)["reason_code"],
                         "validation_round_already_recorded")
        self.assertEqual(self.prepare(2)["reason_code"],
                         "validation_rounds_exhausted")


if __name__ == "__main__":
    unittest.main()
