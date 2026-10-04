"""Issue #68 plan r12 §3.3/§3.5: choices ownership and read-only discovery.

Plan r12 moved cross-professor choice attribution to the root deterministic
partition (``stage5-partition-choices``); the frozen identity stays
``(canonical professor_dir, email_id)``. These cases lock the owner side of
that contract: the runner consumes only its own one-professor bundle rows,
a targeted run filters the professor's unselected ids first, a full-professor
batch keeps its own wrong-id failure, and ``stage5-list-inputs`` discovers
professor-local packs without reading or writing anything else.
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
        The root partition derives candidates from these packs directly.
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
        return a_dir, b_dir, [fixture["pack"], b_pack]

    def partition(self, packs, choices):
        """The root deterministic partition over the selected packs."""
        arguments = ["stage5-partition-choices", "--program-root", self.root,
                     "--choices", choices]
        for pack in packs:
            arguments += ["--owner", str(pack)]
        return parse(helpers.run_cli(*arguments))


class TestStage5ChoicesAttribution(helpers.Stage5LocalHarness, R10TwoProfessorFixture,
                                   BaseEnv):
    """Plan r10 §3: two-phase attribution shared by plan and finalize."""

    def stage5_call(self, surface, *, results, choices, email_id, pack,
                    root=None):
        program_root = Path(root or self.root)
        arguments = ["--result", results, "--choices", choices,
                     "--email-id", email_id]
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
        """With candidates={A,B}, the root partition excludes the explicitly
        satisfied A: the legacy row lands in B's bundle, A keeps its explicit
        row, and both one-professor bundles finalize without cross-writes."""
        a_dir, b_dir, packs = self.colliding_owner_fixture()
        results = self.write_results("r10-cx4-raw.json", [A_ID])
        rows = [explicit_row(A_ID, a_dir), helpers.issue59_choices(A_ID)]
        for order in (rows, list(reversed(rows))):
            choices = self.write_json("r10-cx4-choices.json", order)
            partition = self.partition(packs, choices)
            self.assertEqual(partition["status"], "ok", partition)
            owners = {entry["professor_dir"]: entry
                      for entry in partition["owners"]}
            for pack in packs:
                owner_dir = str(Path(
                    json.loads(pack.read_text())["professor_dir"]).resolve())
                with self.subTest(order=order, pack=pack):
                    self.assertEqual(owners[owner_dir]["partition"]["status"],
                                     "ok", partition)
                    bundle = self.write_json(
                        "r10-cx4-bundle.json",
                        owners[owner_dir]["choices_rows"])
                    jobs = self.plan("--result", results, "--choices", bundle,
                                     "--email-id", A_ID, pack=pack)
                    self.assertEqual(jobs["status"], "ok", jobs)
                    self.assertEqual(
                        [row["email_id"] for row in jobs["drafts"]], [A_ID])
                    other = packs[1] if pack == packs[0] else packs[0]
                    other_dir = Path(json.loads(other.read_text())["professor_dir"])
                    other_before = {p: p.read_bytes() for p in other_dir.iterdir() if p.is_file()}
                    humanized = self.root / "collision-humanized.txt"
                    humanized.write_text(jobs["drafts"][0]["draft"], encoding="utf-8")
                    out = self.finalize("--result", results, "--choices", bundle,
                                        "--email-id", A_ID,
                                        "--humanized", humanized, pack=pack)
                    self.assertEqual(out["status"], "ok", out)
                    state = Path(json.loads(pack.read_text())["professor_dir"]) / contact_state.EMAIL_STATE
                    self.assertTrue(state.is_file())
                    self.assertEqual({p: p.read_bytes() for p in other_dir.iterdir() if p.is_file()},
                                     other_before)

    def test_issue68_r10_undecided_multi_candidate_owner_returns_needs_input(self):
        """A legacy row whose id lives in two selected packs stays an
        unresolved root-partition ambiguity: no owner receives the row."""
        a_dir, b_dir, packs = self.colliding_owner_fixture()
        choices = self.write_json("r10-amb-choices.json",
                                  [helpers.issue59_choices(A_ID)])
        before = self.stage5_artifact_snapshot()
        partition = self.partition(packs, choices)
        self.assertEqual(partition["status"], "ok", partition)
        for entry in partition["owners"]:
            self.assertEqual(entry["partition"]["status"], "needs_input",
                             partition)
            self.assertEqual(entry["partition"]["reason_code"],
                             "choice_owner_ambiguous", partition)
            self.assertEqual(entry["partition"]["email_ids"], [A_ID], partition)
            self.assertNotIn("choices_rows", entry, partition)
        self.assertEqual(self.stage5_artifact_snapshot(), before,
                         "ambiguity wrote Stage-5 artifacts")

    def test_issue68_r10_counterexample2_cross_professor_error_stays_with_its_owner(self):
        """Plan r12 §3.3 rule 5: a wrong ``B_dir + A's id`` row fails only B's
        root partition — B answers ``needs_input`` / ``choice_owner_invalid``
        and gets no bundle. A's bundle stays legal in targeted and batch mode,
        and B's row never reaches A's runner."""
        fixture = self.a_b_fixture()
        a_dir, b_dir = fixture["dirs"][A].resolve(), fixture["dirs"][B].resolve()
        a_pack, b_pack = self.pack_for(A), self.pack_for(B)
        a_results = self.write_results("r10-cx2-a-raw.json", [A_ID])
        choices = self.write_json("r10-cx2-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(A_ID, b_dir)])
        partition = self.partition([a_pack, b_pack], choices)
        self.assertEqual(partition["status"], "ok", partition)
        owners = {entry["professor_dir"]: entry for entry in partition["owners"]}
        a_entry, b_entry = owners[str(a_dir)], owners[str(b_dir)]
        self.assertEqual(a_entry["partition"]["status"], "ok", partition)
        self.assertEqual([row["email_id"] for row in a_entry["choices_rows"]],
                         [A_ID], partition)
        self.assertNotIn(str(b_dir), json.dumps(a_entry["choices_rows"]),
                         partition)
        self.assertEqual(b_entry["partition"]["status"], "needs_input",
                         partition)
        self.assertEqual(b_entry["partition"]["reason_code"],
                         "choice_owner_invalid", partition)
        self.assertEqual(b_entry["partition"]["email_id"], A_ID, partition)
        self.assertNotIn("choices_rows", b_entry, partition)
        a_bundle = self.write_json("r10-cx2-a-bundle.json",
                                   a_entry["choices_rows"])
        a_jobs = self.plan("--result", a_results, "--choices", a_bundle,
                           "--email-id", A_ID, pack=a_pack)
        self.assertEqual(a_jobs["status"], "ok", a_jobs)
        self.assertEqual([row["email_id"] for row in a_jobs["drafts"]], [A_ID],
                         a_jobs)
        a_batch = self.plan("--result", a_results, "--choices", a_bundle,
                            pack=a_pack)
        self.assertEqual(a_batch["status"], "ok", a_batch)
        self.assertEqual(sorted(row["email_id"] for row in a_batch["drafts"]),
                         [A_ID], a_batch)

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

        # The same filter holds when the bundle carries another of the
        # professor's own unselected explicit ids: the caller's unselected
        # explicit Y must not become an ownership error.
        fixture = self.a_b_fixture()
        a_dir = fixture["dirs"][A]
        results = self.write_results("r11-filter-full-raw.json", [A_ID])
        choices = self.write_json("r11-filter-full-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(B_ID, a_dir)])
        jobs = self.plan("--result", results, "--choices", choices,
                         "--email-id", A_ID, pack=self.pack_for(A))
        self.assertEqual(jobs["status"], "ok", jobs)
        self.assertEqual([row["email_id"] for row in jobs["drafts"]], [A_ID],
                         jobs)

    def test_issue68_r10_counterexample5_invalid_explicit_dir_never_transfers_by_id(self):
        """A foreign explicit row inside an owner-local bundle is this owner's
        input error (plan r12 §3.5 fail closed); it never transfers its
        failure by id to another professor nor re-binds as a legacy row."""
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
                self.assertEqual(out["reason_code"], "invalid_params", out)
                self.assertIn(str(row_dir), out["message"], out)

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


class TestStage5ImmutableWrapperOwnerLocalChoices(helpers.Stage5LocalHarness,
                                                  R10TwoProfessorFixture,
                                                  BaseEnv):
    """The wrapper inherits only the current owner's pack and owner-local
    choices: raw multi-source ``choices`` fail closed, while the one-professor
    bundle from the root partition finalizes exactly like the runner."""

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
        a_dir, b_dir, packs = self.colliding_owner_fixture()
        results = self.write_results("r10-wrap-raw.json", [A_ID])
        choices = self.write_json("r10-wrap-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   helpers.issue59_choices(A_ID)])

        raw = self.wrapper_finalize("--result", str(results), "--choices",
                                    str(choices), "--email-id", A_ID,
                                    pack=packs[0])
        self.assertNotEqual(raw.returncode, 0, raw.stdout)
        self.assertEqual(json.loads(raw.stdout)["reason_code"],
                         "invalid_result_json", raw.stdout)

        partition = self.partition(packs, choices)
        self.assertEqual(partition["status"], "ok", partition)
        owners = {entry["professor_dir"]: entry
                  for entry in partition["owners"]}
        for pack in packs:
            owner_dir = str(Path(
                json.loads(pack.read_text())["professor_dir"]).resolve())
            with self.subTest(pack=pack):
                bundle = self.write_json(
                    "r10-wrap-bundle.json", owners[owner_dir]["choices_rows"])
                wrapped = self.wrapper_finalize("--result", str(results),
                                                "--choices", str(bundle),
                                                "--email-id", A_ID, pack=pack)
                payload = json.loads(wrapped.stdout)
                self.assertEqual(payload["status"], "ok", payload)
                self.assertEqual([row["email_id"] for row in payload["emails"]], [A_ID], payload)
                for row in payload["emails"]:
                    self.assertEqual(Path(row["md"]).parent.resolve(),
                                     Path(owner_dir).resolve())


if __name__ == "__main__":
    unittest.main(verbosity=2)
