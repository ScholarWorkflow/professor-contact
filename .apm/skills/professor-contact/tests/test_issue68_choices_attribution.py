"""Issue #68 plan r10 §2/§3: choices attribution and read-only discovery.

The r10 candidate plan specifies the cross-professor choice identity as
``(canonical professor_dir, email_id)``. These cases lock the deterministic
runner side of that contract: explicit ``professor_dir`` rows partition first,
legacy rows without a directory compute ``original_candidates`` from the
caller's read-only scope before any explicit binding is considered, only a
multi-candidate row may exclude professors a legal explicit row already
satisfied, and ``stage5-list-inputs`` discovers professor-local packs without
reading or writing anything else. The plan's representative
counterexamples 2-5 each have a case here.
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("contact_state_test_helpers",
                                              HERE / "test_contact_state.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

BaseEnv = helpers.BaseEnv
parse = helpers.parse
contact_state = helpers.contact_state
A = helpers.ISSUE59_PROFESSOR
B = helpers.ISSUE59_OTHER_PROFESSOR
A_ID = helpers.ISSUE59_EMAIL_ID
B_ID = helpers.ISSUE59_OTHER_EMAIL_ID
MALFORMED = helpers.ISSUE59_MALFORMED_JSON
WRAPPER = HERE.parent / "scripts" / "stage5_immutable.py"


def explicit_row(email_id, professor_dir):
    """A canonical choices row that names its professor directory explicitly."""
    return dict(helpers.issue59_choices(email_id), professor_dir=str(professor_dir))


class R10TwoProfessorFixture:
    """Shared fixture builder: professor A and B, both fresh."""

    def a_b_fixture(self, root=None):
        return helpers.write_issue59_stage5_fixture(
            root or self.root,
            [{"professor": A, "evidence": "fresh"},
             {"professor": B, "evidence": "fresh"}], case=self)

    def colliding_owner_fixture(self):
        """Two legal packs with the same display name and compiled email id.

        Both owners share the synthetic recipient evidence, but own separate
        directories, verification caches, packs and eventual output/state.
        The scope is derived from these packs, never invented independently.
        """
        fixture = helpers.write_issue59_stage5_fixture(
            self.root, [{"professor": A, "evidence": "fresh"}], case=self)
        a_dir = fixture["dirs"][A].resolve()
        b_dir = (self.root / "教授研究" / "Y分野" / A).resolve()
        b_dir.mkdir(parents=True)
        row = helpers.issue59_email_row(
            A, b_dir, contact_evidence=fixture["rows"][0]["contact_evidence"])
        b_pack = helpers.write_stage5_local_pack(self.root, A, b_dir, [row])
        helpers.write_issue59_verify(self.root, b_dir, A)
        packs = [fixture["pack"], b_pack]
        scope = {}
        for path in packs:
            pack = json.loads(path.read_text(encoding="utf-8"))
            scope[str(Path(pack["professor_dir"]).resolve())] = [
                email["email_id"] for email in pack["emails"]]
        self.assertEqual(scope, {str(a_dir): [A_ID], str(b_dir): [A_ID]})
        return a_dir, b_dir, packs, self.write_json("collision-scope.json", scope)


class TestStage5ChoicesAttribution(helpers.Stage5LocalHarness, R10TwoProfessorFixture,
                                   BaseEnv):
    """Plan r10 §3: two-phase attribution shared by plan and finalize."""

    def stage5_call(self, surface, *, results, choices, email_id, pack,
                    scope=None, root=None):
        program_root = Path(root or self.root)
        arguments = ["--result", results, "--choices", choices,
                     "--email-id", email_id]
        if scope is not None:
            arguments += ["--choices-scope", scope]
        if surface == "finalize":
            placeholder = program_root / "placeholder-humanized.txt"
            placeholder.write_text("占位正文\n", encoding="utf-8")
            arguments += ["--humanized", placeholder]
        return parse(helpers.run_cli(f"stage5-{surface}", "--program-root",
                                     program_root, "--email-pack", pack,
                                     *arguments))

    def test_issue68_r10_counterexample3_unique_candidate_legacy_row_is_a_duplicate(self):
        """Legacy row with original_candidates={A} must bind A and fail A's
        exact-one check beside the legal explicit row — never be dropped."""
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"}], case=self)
        a_dir = fixture["dirs"][A]
        results = self.write_results("r10-cx3-raw.json", [A_ID])
        choices = self.write_json("r10-cx3-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   helpers.issue59_choices(A_ID)])
        for surface in ("plan", "finalize"):
            with self.subTest(surface=surface):
                before = self.stage5_artifact_snapshot()
                out = self.stage5_call(surface, results=results, choices=choices,
                                       email_id=A_ID, pack=self.pack_for())
                self.assertEqual(out["status"], "error", out)
                self.assertEqual(out["reason_code"], "invalid_result_json", out)
                self.assertEqual(self.stage5_artifact_snapshot(), before,
                                 f"{surface}: the duplicate committed artifacts")
        batch = self.plan("--result", results, "--choices", choices)
        self.assertEqual(batch["status"], "error", batch)
        self.assertEqual(batch["reason_code"], "invalid_result_json", batch)

    def test_issue68_r10_counterexample4_multi_candidate_excludes_satisfied_owner(self):
        """With original_candidates={A,B}, excluding the explicitly satisfied A
        leaves B: the legacy row binds B and A is neither duplicate nor
        ambiguous."""
        a_dir, b_dir, packs, scope = self.colliding_owner_fixture()
        results = self.write_results("r10-cx4-raw.json", [A_ID])
        rows = [explicit_row(A_ID, a_dir), helpers.issue59_choices(A_ID)]
        for order in (rows, list(reversed(rows))):
            choices = self.write_json("r10-cx4-choices.json", order)
            for surface in ("plan", "finalize"):
                for pack in packs:
                    with self.subTest(order=order, surface=surface, pack=pack):
                        jobs = self.plan("--result", results, "--choices", choices,
                                         "--choices-scope", scope, "--email-id", A_ID,
                                         pack=pack)
                        self.assertEqual(jobs["status"], "ok", jobs)
                        self.assertEqual([row["email_id"] for row in jobs["drafts"]], [A_ID])
                        if surface == "finalize":
                            other = packs[1] if pack == packs[0] else packs[0]
                            other_dir = Path(json.loads(other.read_text())["professor_dir"])
                            other_before = {p: p.read_bytes() for p in other_dir.iterdir() if p.is_file()}
                            humanized = self.root / "collision-humanized.txt"
                            humanized.write_text(jobs["drafts"][0]["draft"], encoding="utf-8")
                            out = self.finalize("--result", results, "--choices", choices,
                                                "--choices-scope", scope, "--email-id", A_ID,
                                                "--humanized", humanized, pack=pack)
                            self.assertEqual(out["status"], "ok", out)
                            state = Path(json.loads(pack.read_text())["professor_dir"]) / contact_state.EMAIL_STATE
                            self.assertTrue(state.is_file())
                            self.assertEqual({p: p.read_bytes() for p in other_dir.iterdir() if p.is_file()},
                                             other_before)

    def test_issue68_r10_undecided_multi_candidate_owner_returns_needs_input(self):
        a_dir, b_dir, packs, scope = self.colliding_owner_fixture()
        results = self.write_results("r10-amb-raw.json", [A_ID])
        choices = self.write_json("r10-amb-choices.json",
                                  [helpers.issue59_choices(A_ID)])
        for surface, pack in ((surface, pack) for surface in ("plan", "finalize") for pack in packs):
            with self.subTest(surface=surface, pack=pack):
                before = self.stage5_artifact_snapshot()
                out = self.stage5_call(surface, results=results, choices=choices,
                                       email_id=A_ID, pack=pack,
                                       scope=scope)
                self.assertEqual(out["status"], "needs_input", out)
                self.assertEqual(out["reason_code"], "choice_owner_ambiguous", out)
                self.assertEqual(out.get("email_ids"), [A_ID], out)
                self.assertEqual(self.stage5_artifact_snapshot(), before,
                                 f"{surface}: ambiguity wrote Stage-5 artifacts")

    def test_issue68_r10_counterexample2_cross_professor_error_stays_with_its_owner(self):
        """R11 §3.3: a wrong ``B_dir + A's id`` row fails only B — B's batch
        run answers ``needs_input`` / ``choice_owner_invalid``, B's targeted
        run filters the unselected id first and fails only by its own missing
        rule. A never rebinds or inherits B's bad row in either mode."""
        fixture = self.a_b_fixture()
        a_dir, b_dir = fixture["dirs"][A], fixture["dirs"][B]
        scope = self.write_json("r10-cx2-scope.json",
                                {str(a_dir): [A_ID], str(b_dir): [B_ID]})
        a_results = self.write_results("r10-cx2-a-raw.json", [A_ID])
        b_results = self.write_results("r10-cx2-b-raw.json", [B_ID])
        choices = self.write_json("r10-cx2-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(A_ID, b_dir)])
        a_jobs = self.plan("--result", a_results, "--choices", choices,
                           "--choices-scope", scope, "--email-id", A_ID,
                           pack=self.pack_for(A))
        self.assertEqual(a_jobs["status"], "ok", a_jobs)
        self.assertEqual([row["email_id"] for row in a_jobs["drafts"]], [A_ID],
                         a_jobs)
        a_batch = self.plan("--result", a_results, "--choices", choices,
                            "--choices-scope", scope, pack=self.pack_for(A))
        self.assertEqual(a_batch["status"], "ok", a_batch)
        self.assertEqual(sorted(row["email_id"] for row in a_batch["drafts"]),
                         [A_ID], a_batch)
        b_batch = self.plan("--result", b_results, "--choices", choices,
                            "--choices-scope", scope, pack=self.pack_for(B))
        self.assertEqual(b_batch["status"], "needs_input", b_batch)
        self.assertEqual(b_batch["reason_code"], "choice_owner_invalid", b_batch)
        b_jobs = self.plan("--result", b_results, "--choices", choices,
                           "--choices-scope", scope, "--email-id", B_ID,
                           pack=self.pack_for(B))
        self.assertEqual(b_jobs["status"], "error", b_jobs)
        self.assertEqual(b_jobs["reason_code"], "invalid_result_json", b_jobs)

    def test_issue68_r11_targeted_run_filters_unselected_explicit_rows(self):
        """R11 §3.3 rule 2 + counterexamples: in a targeted run the
        professor's own unselected explicit rows are noise — never
        ``choice_owner_invalid``, never field errors — while the target X
        keeps its strict checks and plan/finalize stay identical."""
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"},
            {"professor": A, "evidence": "fresh",
             "idea_id": helpers.ISSUE59_PEER_IDEA_ID}], case=self)
        a_dir = fixture["dirs"][A]
        x_id, y_id = fixture["email_ids"]
        results = self.write_results("r11-filter-raw.json", [x_id])
        humanized = self.root / "r11-filter-humanized.txt"
        # Same professor, unselected explicit Y rows of every shape: plain,
        # broken fields, missing id, duplicated unknown id.
        choices_variants = {
            "plain-y": [explicit_row(x_id, a_dir), explicit_row(y_id, a_dir)],
            "broken-y-fields": [explicit_row(x_id, a_dir),
                                dict(explicit_row(y_id, a_dir),
                                     first_choice="not-a-boolean")],
            "y-without-id": [explicit_row(x_id, a_dir),
                             {"professor_dir": str(a_dir), "first_choice": True}],
            "duplicate-unknown-id": [explicit_row(x_id, a_dir),
                                     explicit_row("幽灵::D::I", a_dir),
                                     explicit_row("幽灵::D::I", a_dir)],
        }
        for label, rows in choices_variants.items():
            choices = self.write_json(f"r11-filter-{label}-choices.json", rows)
            draft = self.plan("--result", results, "--choices", choices,
                              "--email-id", x_id, pack=self.pack_for())
            self.assertEqual(draft["status"], "ok", draft)
            self.assertEqual([row["email_id"] for row in draft["drafts"]], [x_id],
                             draft)
            if label != "plain-y":
                continue
            humanized.write_text(draft["drafts"][0]["draft"], encoding="utf-8")
            out = self.finalize("--result", results, "--choices", choices,
                                "--email-id", x_id, "--humanized", humanized,
                                pack=self.pack_for())
            self.assertEqual(out["status"], "ok", out)
            self.assertEqual([row["email_id"] for row in out["emails"]], [x_id],
                             out)

        # The same filter holds when the unselected id sits inside another
        # professor's scope entry of a full multi-professor scope: the
        # caller's unselected explicit Y must not become an ownership error.
        fixture = self.a_b_fixture()
        a_dir, b_dir = fixture["dirs"][A], fixture["dirs"][B]
        scope = self.write_json("r11-filter-full-scope.json",
                                {str(a_dir): [A_ID], str(b_dir): [B_ID]})
        results = self.write_results("r11-filter-full-raw.json", [A_ID])
        choices = self.write_json("r11-filter-full-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(B_ID, a_dir)])
        jobs = self.plan("--result", results, "--choices", choices,
                         "--choices-scope", scope, "--email-id", A_ID,
                         pack=self.pack_for(A))
        self.assertEqual(jobs["status"], "ok", jobs)
        self.assertEqual([row["email_id"] for row in jobs["drafts"]], [A_ID],
                         jobs)

    def test_issue68_r10_counterexample5_invalid_explicit_dir_never_transfers_by_id(self):
        """An explicit row whose directory cannot map into this run never
        turns into the professor whose id happens to match: A only fails by
        its own missing rule."""
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"}], case=self)
        results = self.write_results("r10-cx5-raw.json", [A_ID])
        for label, row_dir in (
                ("outside-program", self.outside("别人")),
                ("unselected-professor",
                 self.root / "教授研究" / "Z分野" / "第三教授")):
            with self.subTest(explicit_dir=label):
                choices = self.write_json(f"r10-cx5-{label}-choices.json",
                                          [explicit_row(A_ID, row_dir)])
                out = self.plan("--result", results, "--choices", choices,
                                "--email-id", A_ID, pack=self.pack_for())
                self.assertEqual(out["status"], "error", out)
                self.assertEqual(out["reason_code"], "invalid_result_json", out)

    def test_issue68_r10_choices_scope_is_validated_against_this_run(self):
        fixture = self.a_b_fixture()
        a_dir = fixture["dirs"][A]
        results = self.write_results("r10-scope-raw.json", [A_ID])
        choices = self.write_json("r10-scope-choices.json",
                                  [helpers.issue59_choices(A_ID)])
        cases = {
            "not-an-object": [],
            "owner-missing": {str(fixture["dirs"][B]): [B_ID]},
            "outside-dir": {str(self.outside("别人")): [A_ID]},
            "ids-not-strings": {str(a_dir): [42]},
        }
        for label, payload in cases.items():
            with self.subTest(scope=label):
                scope = self.write_json(f"r10-scope-{label}.json", payload)
                out = self.plan("--result", results, "--choices", choices,
                                "--choices-scope", scope, "--email-id", A_ID,
                                pack=self.pack_for(A))
                self.assertEqual(out["status"], "error", out)
                self.assertEqual(out["reason_code"], "invalid_params", out)

    def test_issue68_r10_foreign_rows_stay_noise_without_a_scope(self):
        """P7: other professors' rows and unknown ids never block this owner
        when the caller passes no scope (default scope = this pack)."""
        self.a_b_fixture()
        results = self.write_results("r10-noise-raw.json", [A_ID])
        choices = self.write_json("r10-noise-choices.json",
                                  [helpers.issue59_choices(A_ID),
                                   helpers.issue59_choices(B_ID),
                                   {"email_id": "幽灵 教授::D::I"}])
        out = self.plan("--result", results, "--choices", choices,
                        "--email-id", A_ID, pack=self.pack_for(A))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual([row["email_id"] for row in out["drafts"]], [A_ID], out)

    def test_issue68_r10_single_object_choices_and_default_scope_keep_working(self):
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"}], case=self)
        results = self.write_results("r10-legacy-raw.json", [A_ID])
        choices = self.write_json("r10-legacy-choices.json",
                                  helpers.issue59_choices(A_ID))
        humanized = self.humanized("r10-legacy", results, choices)
        out = self.finalize("--result", results, "--choices", choices,
                            "--humanized", humanized, "--email-id", A_ID)
        self.assertEqual(out["status"], "ok", out)
        self.assertTrue(Path(out["emails"][0]["md"]).is_file(), out)


class TestStage5ListInputs(helpers.Stage5LocalHarness, R10TwoProfessorFixture,
                           BaseEnv):
    """Plan r10 §2: ``stage5-list-inputs`` is read-only and row-isolated."""

    def research_files(self):
        research = self.root / "教授研究"
        return {str(path): path.read_bytes()
                for path in sorted(research.rglob("*")) if path.is_file()}

    def test_issue68_r10_list_inputs_discovers_local_packs_independently(self):
        fixture = self.a_b_fixture()
        research = self.root / "教授研究"
        b_pack = self.pack_for(B)
        b_pack.write_text(MALFORMED, encoding="utf-8")
        legacy = research / contact_state.EMAIL_PACK
        legacy.write_text(MALFORMED, encoding="utf-8")
        before = self.research_files()

        out = parse(helpers.run_cli("stage5-list-inputs",
                                    "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        rows = out["inputs"]
        a_row = next(row for row in rows if row["professor"] == A)
        self.assertEqual(a_row["status"], "ok", a_row)
        self.assertIsNone(a_row["reason_code"], a_row)
        self.assertEqual(a_row["professor_dir"], str(fixture["dirs"][A]), a_row)
        self.assertEqual(a_row["email_pack"], str(self.pack_for(A)), a_row)
        b_row = next(row for row in rows if row["email_pack"] == str(b_pack))
        self.assertEqual(b_row["status"], "error", b_row)
        self.assertEqual(b_row["reason_code"], "missing_email_pack", b_row)
        self.assertFalse(
            any(row["email_pack"] == str(legacy) for row in rows),
            "the legacy program pack became a discovery row")
        self.assertEqual(self.research_files(), before,
                         "discovery wrote or mutated a file")
        self.assertFalse((research / contact_state.PROJECTIONS_FILE).exists())
        self.assertFalse((research / contact_state.EMAIL_OVERVIEW).exists())

    def test_issue68_r10_list_inputs_professor_filter_and_ambiguity(self):
        self.a_b_fixture()
        only = parse(helpers.run_cli("stage5-list-inputs", "--program-root",
                                     self.root, "--professor", A))
        self.assertEqual(only["status"], "ok", only)
        self.assertEqual([row["professor"] for row in only["inputs"]], [A], only)

        missing = parse(helpers.run_cli("stage5-list-inputs", "--program-root",
                                        self.root, "--professor", "不存在的教授"))
        self.assertEqual(missing["status"], "needs_input", missing)
        self.assertEqual(missing["reason_code"], "professor_not_found", missing)

        # A second valid container claiming the same professor never resolves
        # by guessing: the discovery answer is needs_input instead.
        mirror = self.root / "教授研究" / "W分野" / A
        helpers.write_stage5_local_pack(
            self.root, A, mirror,
            [helpers.issue59_email_row(A, mirror)])
        ambiguous = parse(helpers.run_cli("stage5-list-inputs", "--program-root",
                                          self.root, "--professor", A))
        self.assertEqual(ambiguous["status"], "needs_input", ambiguous)
        self.assertEqual(ambiguous["reason_code"], "professor_ambiguous", ambiguous)

    def test_issue68_r10_list_input_reason_codes(self):
        self.a_b_fixture()
        b_pack = self.pack_for(B)
        payload = json.loads(b_pack.read_text(encoding="utf-8"))
        payload["schema"] = contact_state.EMAIL_PACK_SCHEMA
        b_pack.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        shifted = self.root / "教授研究" / "X分野" / "别的目录"
        helpers.write_stage5_local_pack(self.root, "移位 教授", shifted, [])
        shifted_pack = shifted / contact_state.EMAIL_PACK
        doc = json.loads(shifted_pack.read_text(encoding="utf-8"))
        doc["professor_dir"] = str(self.root / "教授研究" / "X分野" / "其他位置")
        shifted_pack.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                                encoding="utf-8")

        out = parse(helpers.run_cli("stage5-list-inputs",
                                    "--program-root", self.root))
        rows = {row["email_pack"]: row for row in out["inputs"]}
        self.assertEqual(rows[str(b_pack)]["reason_code"], "invalid_email_pack", out)
        self.assertEqual(rows[str(shifted_pack)]["reason_code"],
                         "invalid_professor_dir", out)

        empty = self.root / "empty-program"
        (empty / "教授研究").mkdir(parents=True)
        bare = parse(helpers.run_cli("stage5-list-inputs",
                                     "--program-root", empty))
        self.assertEqual(bare, {"status": "ok", "inputs": []}, bare)


class TestStage5ImmutableWrapperForwardsChoicesScope(helpers.Stage5LocalHarness,
                                                    R10TwoProfessorFixture,
                                                    BaseEnv):
    """The wrapper forwards ``--choices-scope`` to its internal plan call, so
    the immutable finalize path shares the exact attribution semantics."""

    def wrapper_finalize(self, *extra, pack=None):
        template = self.root / "synthetic-template.md"
        if not template.is_file():
            template.write_text(
                "{{大学}}／{{研究科}}／{{先生名}}先生\n{{出身校}} {{氏名}}\n"
                "{{入学年度}} {{入学月}} {{専攻}} {{学位}}\n{{兴趣段}}\n{{未来志向}}\n"
                "{{学習中}}\n{{志望}}", encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(WRAPPER), "stage5-finalize",
             "--program-root", str(self.root), "--email-pack", str(pack or self.pack_for(A)),
             "--mode", "first", "--template", str(template), *extra],
            text=True, capture_output=True, check=False)

    def test_issue68_r10_wrapper_attribution_matches_the_runner(self):
        a_dir, b_dir, packs, scope = self.colliding_owner_fixture()
        results = self.write_results("r10-wrap-raw.json", [A_ID])
        choices = self.write_json("r10-wrap-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   helpers.issue59_choices(A_ID)])
        common = ["--result", str(results), "--choices", str(choices),
                  "--email-id", A_ID]

        without_scope = self.wrapper_finalize(*common, pack=packs[0])
        self.assertNotEqual(without_scope.returncode, 0, without_scope.stdout)
        self.assertEqual(json.loads(without_scope.stdout)["reason_code"],
                         "invalid_result_json", without_scope.stdout)

        for pack in packs:
            with self.subTest(pack=pack):
                with_scope = self.wrapper_finalize(*common, "--choices-scope", str(scope), pack=pack)
                payload = json.loads(with_scope.stdout)
                self.assertEqual(payload["status"], "ok", payload)
                self.assertEqual([row["email_id"] for row in payload["emails"]], [A_ID], payload)
                owner_dir = Path(json.loads(pack.read_text())["professor_dir"])
                for row in payload["emails"]:
                    self.assertEqual(Path(row["md"]).parent.resolve(), owner_dir.resolve())


if __name__ == "__main__":
    unittest.main(verbosity=2)
