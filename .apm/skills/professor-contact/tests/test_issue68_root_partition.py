"""Issue #68 plan r12 §3.3/§7: root-side deterministic choices partition.

Plan r12 replaces the r11 "every owner receives the same original choices plus
the complete ``choices_scope``" transport with one deterministic partition at
the root boundary: the partition entry takes the selected professor-local
``email_pack`` rows, the raw multi-professor ``choices`` and an optional
per-owner targeted ``email_id``, and answers one self-contained per-owner
bundle keyed by the frozen identity ``(canonical professor_dir, email_id)``.
Legacy rows without a directory resolve their candidates against this run's
selected packs only, ambiguous collisions stay at root as
``needs_input`` / ``choice_owner_ambiguous`` and are never broadcast to any
owner. These cases lock plan r12's representative counterexamples 7.1-7.7
plus the narrowed owner-local loader (plan §3.5): a sibling row that reaches
an owner bundle is that owner's input error, never a reroute.

Test Plan r19 additions: the deterministic row-preserving rerun oracle and
the owner business-bundle isolation oracle (both bound into P7), plus
``TestStage5BatchStaysAtomic`` for P3's zero-partial-commit requirement.
"""

import importlib.util
import json
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
run_cli = helpers.run_cli
contact_state = helpers.contact_state
A = helpers.ISSUE59_PROFESSOR
B = helpers.ISSUE59_OTHER_PROFESSOR
C = "山田 太郎"
A_ID = helpers.ISSUE59_EMAIL_ID
B_ID = helpers.ISSUE59_OTHER_EMAIL_ID
MALFORMED = helpers.ISSUE59_MALFORMED_JSON


def explicit_row(email_id, professor_dir):
    """A canonical choices row that names its professor directory explicitly."""
    return dict(helpers.issue59_choices(email_id), professor_dir=str(professor_dir))


class R12PartitionFixture:
    """Shared fixture builders for the root partition cases."""

    def a_b_fixture(self, root=None):
        return helpers.write_issue59_stage5_fixture(
            root or self.root,
            [{"professor": A, "evidence": "fresh"},
             {"professor": B, "evidence": "fresh"}], case=self)

    def a_b_c_fixture(self):
        return helpers.write_issue59_stage5_fixture(
            self.root,
            [{"professor": A, "evidence": "fresh"},
             {"professor": B, "evidence": "fresh"},
             {"professor": C, "evidence": "fresh"}], case=self)

    def colliding_owner_fixture(self):
        """Two legal packs whose display name and email id collide.

        Both owners are legal professor-local packs with separate canonical
        directories; the partition must derive candidates from these packs,
        never from a scope file.
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
        return a_dir, b_dir, packs

    def pack_ids(self, pack):
        payload = json.loads(Path(pack).read_text(encoding="utf-8"))
        return [email["email_id"] for email in payload["emails"]]

    def partition(self, owners, choices, out=None, root=None):
        """Run the root partition entry: owners = [(pack_path, email_id|None)]."""
        arguments = ["stage5-partition-choices",
                     "--program-root", str(root or self.root),
                     "--choices", str(choices)]
        for pack, email_id in owners:
            arguments.append("--owner")
            arguments.append(str(pack))
            if email_id:
                arguments.append(email_id)
        if out is not None:
            arguments += ["--out", str(out)]
        return parse(run_cli(*arguments))

    def bundle_choices(self, owner, name):
        """Serialize one owner bundle's rows the way the root caller does."""
        return self.write_json(name, owner["choices_rows"])

    def owner_map(self, payload):
        return {entry["professor_dir"]: entry for entry in payload["owners"]}

    def write_results_for(self, name, packs):
        rows = []
        for pack in packs:
            payload = json.loads(Path(pack).read_text(encoding="utf-8"))
            row_dir = payload["professor_dir"]
            for email in payload["emails"]:
                rows.append(email["email_id"])
        return self.write_results(name, rows)


class TestStage5RootPartition(R12PartitionFixture, helpers.Stage5LocalHarness,
                              BaseEnv):
    """Plan r12 §3.3: one deterministic partition at the root boundary."""

    def test_r12_cx1_malformed_b_pack_does_not_block_a_bundle(self):
        """§7.1: B's malformed pack is B's own input-resolution failure; A's
        bundle is still produced and executable."""
        fixture = self.a_b_fixture()
        a_pack, b_pack = self.pack_for(A), self.pack_for(B)
        b_pack.write_text(MALFORMED, encoding="utf-8")
        a_dir = fixture["dirs"][A].resolve()
        choices = self.write_json("cx1-choices.json",
                                  [explicit_row(A_ID, a_dir)])
        out = self.partition([(a_pack, None), (b_pack, None)], choices)
        self.assertEqual(out["status"], "ok", out)
        owners = self.owner_map(out)
        self.assertEqual(owners[str(a_dir)]["partition"]["status"], "ok", out)
        self.assertEqual([row["email_id"] for row in
                          owners[str(a_dir)]["choices_rows"]], [A_ID], out)
        b_entry = next(entry for entry in out["owners"]
                       if entry["email_pack"] == str(b_pack))
        self.assertEqual(b_entry["partition"]["status"], "needs_refresh", out)
        self.assertEqual(b_entry["partition"]["reason_code"],
                         "missing_email_pack", out)
        self.assertNotIn("choices_rows", b_entry, out)
        # A's bundle is executable without B.
        a_choices = self.bundle_choices(owners[str(a_dir)], "cx1-a-bundle.json")
        jobs = self.plan("--result", self.write_results("cx1-raw.json", [A_ID]),
                         "--choices", a_choices, pack=a_pack)
        self.assertEqual(jobs["status"], "ok", jobs)
        self.assertEqual([row["email_id"] for row in jobs["drafts"]], [A_ID])

    def test_r12_cx2_owner_bundles_hold_only_their_own_professor(self):
        """§7.2/§7.6: with A+B rows in the raw choices, each owner's bundle
        carries only that professor's identity bytes — never the sibling's."""
        fixture = self.a_b_fixture()
        a_dir, b_dir = fixture["dirs"][A].resolve(), fixture["dirs"][B].resolve()
        a_pack, b_pack = self.pack_for(A), self.pack_for(B)
        choices = self.write_json("cx2-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(B_ID, b_dir)])
        out_path = self.root / "cx2-bundles.json"
        out = self.partition([(a_pack, None), (b_pack, None)], choices,
                             out=out_path)
        self.assertEqual(out["status"], "ok", out)
        owners = self.owner_map(out)
        a_rows = owners[str(a_dir)]["choices_rows"]
        b_rows = owners[str(b_dir)]["choices_rows"]
        self.assertEqual([row["email_id"] for row in a_rows], [A_ID], out)
        self.assertEqual([row["email_id"] for row in b_rows], [B_ID], out)
        a_raw = json.dumps(a_rows, ensure_ascii=False)
        b_raw = json.dumps(b_rows, ensure_ascii=False)
        self.assertNotIn(B_ID, a_raw, a_raw)
        self.assertNotIn(str(b_dir), a_raw, a_raw)
        self.assertNotIn(A_ID, b_raw, b_raw)
        self.assertNotIn(str(a_dir), b_raw, b_raw)
        # The `試験` canonical bytes survive inside the bundle that owns them.
        self.assertIn("試験".encode("utf-8"), out_path.read_bytes())
        self.assertIn("佐藤".encode("utf-8"), out_path.read_bytes())
        for pack, rows_name, email_id in ((a_pack, "cx2-a-bundle.json", A_ID),
                                          (b_pack, "cx2-b-bundle.json", B_ID)):
            bundle = self.bundle_choices(owners[str(a_dir)] if pack is a_pack
                                         else owners[str(b_dir)], rows_name)
            jobs = self.plan("--result",
                             self.write_results(f"cx2-{email_id}-raw.json",
                                                [email_id]),
                             "--choices", bundle, "--email-id", email_id,
                             pack=pack)
            self.assertEqual(jobs["status"], "ok", jobs)
            self.assertEqual([row["email_id"] for row in jobs["drafts"]],
                             [email_id], jobs)

    def test_r12_cx3_colliding_legacy_row_is_ambiguous_at_root(self):
        """§7.3: a legacy row whose id lives in two selected packs is a root
        partition ambiguity for both owners and is broadcast to neither."""
        a_dir, b_dir, packs = self.colliding_owner_fixture()
        choices = self.write_json("cx3-choices.json",
                                  [helpers.issue59_choices(A_ID)])
        out = self.partition([(packs[0], None), (packs[1], None)], choices)
        self.assertEqual(out["status"], "ok", out)
        owners = self.owner_map(out)
        for dir_ in (a_dir, b_dir):
            entry = owners[str(dir_)]
            self.assertEqual(entry["partition"]["status"], "needs_input", out)
            self.assertEqual(entry["partition"]["reason_code"],
                             "choice_owner_ambiguous", out)
            self.assertEqual(entry["partition"]["email_ids"], [A_ID], out)
            self.assertNotIn("choices_rows", entry, out)

    def test_r12_cx3b_explicit_row_resolves_colliding_legacy_row(self):
        """§7.3: a legal explicit row satisfies its owner, so the colliding
        legacy row binds the other owner instead of ambiguous noise."""
        a_dir, b_dir, packs = self.colliding_owner_fixture()
        for order in ([explicit_row(A_ID, a_dir), helpers.issue59_choices(A_ID)],
                      [helpers.issue59_choices(A_ID), explicit_row(A_ID, a_dir)]):
            choices = self.write_json("cx3b-choices.json", order)
            out = self.partition([(packs[0], None), (packs[1], None)], choices)
            self.assertEqual(out["status"], "ok", out)
            owners = self.owner_map(out)
            self.assertEqual(owners[str(a_dir)]["partition"]["status"], "ok",
                             out)
            self.assertEqual([row["email_id"] for row in
                              owners[str(a_dir)]["choices_rows"]], [A_ID], out)
            self.assertEqual([row.get("professor_dir") for row in
                              owners[str(a_dir)]["choices_rows"]],
                             [str(a_dir)], out)
            self.assertEqual(owners[str(b_dir)]["partition"]["status"], "ok",
                             out)
            self.assertEqual([row["email_id"] for row in
                              owners[str(b_dir)]["choices_rows"]], [A_ID], out)
            self.assertNotIn("professor_dir",
                             owners[str(b_dir)]["choices_rows"][0], out)

    def test_r12_cx4_targeted_bundle_excludes_unselected_same_professor_rows(self):
        """§7.4: targeted X, raw choices also hold this professor's Y — the
        X bundle only holds X and Y blocks nothing."""
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"},
            {"professor": A, "evidence": "fresh",
             "idea_id": helpers.ISSUE59_PEER_IDEA_ID}], case=self)
        a_dir = fixture["dirs"][A].resolve()
        x_id, y_id = fixture["email_ids"]
        a_pack = self.pack_for()
        choices = self.write_json("cx4-choices.json",
                                  [explicit_row(x_id, a_dir),
                                   explicit_row(y_id, a_dir)])
        out = self.partition([(a_pack, x_id)], choices)
        self.assertEqual(out["status"], "ok", out)
        owners = self.owner_map(out)
        entry = owners[str(a_dir)]
        self.assertEqual(entry["partition"]["status"], "ok", out)
        self.assertEqual(entry["email_id"], x_id, out)
        self.assertEqual([row["email_id"] for row in entry["choices_rows"]],
                         [x_id], out)
        self.assertNotIn(y_id, json.dumps(entry["choices_rows"],
                                          ensure_ascii=False), out)
        bundle = self.bundle_choices(entry, "cx4-bundle.json")
        jobs = self.plan("--result", self.write_results("cx4-raw.json", [x_id]),
                         "--choices", bundle, "--email-id", x_id, pack=a_pack)
        self.assertEqual(jobs["status"], "ok", jobs)
        self.assertEqual([row["email_id"] for row in jobs["drafts"]], [x_id],
                         jobs)

    def test_r12_cx5_b_choice_error_does_not_degrade_a(self):
        """§7.5: B's batch error id fails B's partition only; A's bundle stays
        legal and executable."""
        fixture = self.a_b_fixture()
        a_dir, b_dir = fixture["dirs"][A].resolve(), fixture["dirs"][B].resolve()
        a_pack, b_pack = self.pack_for(A), self.pack_for(B)
        choices = self.write_json("cx5-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(A_ID, b_dir)])
        out = self.partition([(a_pack, None), (b_pack, None)], choices)
        self.assertEqual(out["status"], "ok", out)
        owners = self.owner_map(out)
        self.assertEqual(owners[str(a_dir)]["partition"]["status"], "ok", out)
        self.assertEqual([row["email_id"] for row in
                          owners[str(a_dir)]["choices_rows"]], [A_ID], out)
        b_entry = owners[str(b_dir)]
        self.assertEqual(b_entry["partition"]["status"], "needs_input", out)
        self.assertEqual(b_entry["partition"]["reason_code"],
                         "choice_owner_invalid", out)
        self.assertEqual(b_entry["partition"]["email_id"], A_ID, out)
        self.assertNotIn("choices_rows", b_entry, out)
        a_choices = self.bundle_choices(owners[str(a_dir)], "cx5-a-bundle.json")
        jobs = self.plan("--result", self.write_results("cx5-raw.json", [A_ID]),
                         "--choices", a_choices, pack=a_pack)
        self.assertEqual(jobs["status"], "ok", jobs)

    def test_r12_cx7_discovery_rows_drive_partition_and_bad_b_stays_alone(self):
        """§7.7: standalone discovery keeps A/C rows beside a bad B container;
        the partition consumes only the selected ok rows."""
        fixture = self.a_b_c_fixture()
        a_pack, b_pack, c_pack = (self.pack_for(A), self.pack_for(B),
                                  self.pack_for(C))
        b_pack.write_text(MALFORMED, encoding="utf-8")
        discovery = parse(run_cli("stage5-list-inputs",
                                  "--program-root", self.root))
        self.assertEqual(discovery["status"], "ok", discovery)
        rows = {row["email_pack"]: row for row in discovery["inputs"]}
        self.assertEqual(rows[str(a_pack)]["status"], "ok", discovery)
        self.assertEqual(rows[str(c_pack)]["status"], "ok", discovery)
        self.assertEqual(rows[str(b_pack)]["status"], "error", discovery)
        self.assertEqual(rows[str(b_pack)]["reason_code"],
                         "missing_email_pack", discovery)
        c_id = self.pack_ids(c_pack)[0]
        c_dir = Path(json.loads(c_pack.read_text(encoding="utf-8"))["professor_dir"]).resolve()
        a_dir = Path(json.loads(a_pack.read_text(encoding="utf-8"))["professor_dir"]).resolve()
        choices = self.write_json("cx7-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(c_id, c_dir)])
        out = self.partition([(a_pack, None), (c_pack, None)], choices)
        self.assertEqual(out["status"], "ok", out)
        owners = self.owner_map(out)
        self.assertEqual(sorted(owners), sorted([str(a_dir), str(c_dir)]), out)
        self.assertEqual(owners[str(a_dir)]["partition"]["status"], "ok", out)
        self.assertEqual(owners[str(c_dir)]["partition"]["status"], "ok", out)
        self.assertNotIn(B_ID, json.dumps(out["owners"], ensure_ascii=False),
                         out)
        c_bundle = self.bundle_choices(owners[str(c_dir)], "cx7-c-bundle.json")
        results = self.write_json("cx7-raw.json", [
            helpers.issue59_result(self.gap_id, email_id=c_id,
                                   idea_id=c_id.rsplit("::", 1)[-1])])
        jobs = self.plan("--result", results, "--choices", c_bundle,
                         pack=c_pack)
        self.assertEqual(jobs["status"], "ok", jobs)

    def test_r12_partition_preserves_rows_and_reruns_deterministically(self):
        """Plan r19 P7: the partition entry only re-containers rows.

        Every business byte of an explicit row — ``professor_dir``, a
        ``transport_sentinel`` stand-in for caller fields and the compiled
        Stage-4 fields — must survive into its owner's ``choices_rows``
        unchanged, and the same inputs must answer byte-identical output on
        every rerun: the entry is deterministic, with no model in the loop.
        """
        fixture = self.a_b_fixture()
        a_dir, b_dir = fixture["dirs"][A].resolve(), fixture["dirs"][B].resolve()
        a_pack, b_pack = self.pack_for(A), self.pack_for(B)
        a_row = dict(explicit_row(A_ID, a_dir), transport_sentinel="row-a")
        b_row = dict(explicit_row(B_ID, b_dir), transport_sentinel="row-b")
        choices = self.write_json("det-choices.json", [a_row, b_row])
        out_path = self.root / "det-bundles.json"
        first = self.partition([(a_pack, None), (b_pack, None)], choices)
        second = self.partition([(a_pack, None), (b_pack, None)], choices,
                                out=out_path)
        for run in (first, second):
            self.assertEqual(run["status"], "ok", run)
        owners = self.owner_map(second)
        for dir_, row in ((a_dir, a_row), (b_dir, b_row)):
            entry = owners[str(dir_)]
            self.assertEqual(entry["partition"]["status"], "ok", second)
            # Deep equality with the input source row: no field rewritten.
            self.assertEqual(entry["choices_rows"], [row], second)
            self.assertEqual(entry["choices_rows"],
                             self.owner_map(first)[str(dir_)]["choices_rows"],
                             first)
        # Byte-identical canonical output across reruns, and the --out file
        # holds exactly the answered payload.
        canonical_first = json.dumps(first, ensure_ascii=False, sort_keys=True)
        canonical_second = json.dumps(second, ensure_ascii=False, sort_keys=True)
        self.assertEqual(canonical_first, canonical_second)
        self.assertEqual(json.loads(out_path.read_text(encoding="utf-8")),
                         second)

    def test_r12_owner_bundle_has_no_scope_and_no_sibling_state_paths(self):
        """Plan r19 P7: one owner entry leaks nothing about its sibling.

        No ``choices_scope`` structure exists anywhere in the partition
        answer, and an owner entry never carries the sibling's on-disk paths
        (pack, verify cache, papers) nor its identity bytes.
        """
        fixture = self.a_b_fixture()
        a_dir, b_dir = fixture["dirs"][A].resolve(), fixture["dirs"][B].resolve()
        a_pack, b_pack = self.pack_for(A), self.pack_for(B)
        choices = self.write_json("isolation-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(B_ID, b_dir)])
        out_path = self.root / "isolation-bundles.json"
        out = self.partition([(a_pack, None), (b_pack, None)], choices,
                             out=out_path)
        self.assertEqual(out["status"], "ok", out)
        self.assertNotIn("choices_scope", json.dumps(out, ensure_ascii=False),
                         out)
        self.assertNotIn("choices_scope", out_path.read_text(encoding="utf-8"))
        # Enumerate the sibling's real files; never guess their names.
        def dir_files(directory):
            files = sorted(str(path.resolve()) for path in directory.iterdir()
                           if path.is_file())
            self.assertTrue(files, f"fixture produced no files in {directory}")
            self.assertIn(str((directory / contact_state.EMAIL_PACK).resolve()),
                          files, directory)
            return files
        a_files, b_files = dir_files(a_dir), dir_files(b_dir)
        owners = self.owner_map(out)
        a_text = json.dumps(owners[str(a_dir)], ensure_ascii=False)
        b_text = json.dumps(owners[str(b_dir)], ensure_ascii=False)
        for path in b_files:
            self.assertNotIn(path, a_text,
                             f"A's entry carries B's file path: {path}")
        for path in a_files:
            self.assertNotIn(path, b_text,
                             f"B's entry carries A's file path: {path}")
        self.assertNotIn(B_ID, a_text, a_text)
        self.assertNotIn(str(b_dir), a_text, a_text)
        self.assertNotIn(A_ID, b_text, b_text)
        self.assertNotIn(str(a_dir), b_text, b_text)


class TestStage5OwnerLocalBundleLoader(R12PartitionFixture,
                                       helpers.Stage5LocalHarness, BaseEnv):
    """Plan r12 §3.5: the owner runner reads one professor's bundle only."""

    def test_sibling_explicit_row_in_owner_bundle_fails_closed(self):
        """A sibling row that reaches an owner-local bundle is this owner's
        input error — never a reroute to the sibling."""
        fixture = self.a_b_fixture()
        a_dir, b_dir = fixture["dirs"][A], fixture["dirs"][B]
        choices = self.write_json("sibling-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   explicit_row(B_ID, b_dir)])
        results = self.write_results("sibling-raw.json", [A_ID])
        out = self.plan("--result", results, "--choices", choices,
                        pack=self.pack_for(A))
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_params", out)
        self.assertIn(str(b_dir), out["message"], out)

    def test_owner_local_legacy_exact_one_still_applies(self):
        """Legacy rows keep the owner's own exact-one business check: an
        explicit row plus a legacy row for the same id still fails closed."""
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"}], case=self)
        a_dir = fixture["dirs"][A]
        choices = self.write_json("dup-choices.json",
                                  [explicit_row(A_ID, a_dir),
                                   helpers.issue59_choices(A_ID)])
        results = self.write_results("dup-raw.json", [A_ID])
        for surface in ("plan", "finalize"):
            with self.subTest(surface=surface):
                if surface == "finalize":
                    placeholder = self.root / "dup-humanized.txt"
                    placeholder.write_text("占位正文\n", encoding="utf-8")
                    out = self.finalize("--result", results, "--choices",
                                        choices, "--humanized", placeholder)
                else:
                    out = self.plan("--result", results, "--choices", choices)
                self.assertEqual(out["status"], "error", out)
                self.assertEqual(out["reason_code"], "invalid_result_json", out)

    def test_targeted_bundle_of_one_stays_exact(self):
        """Targeted X with only X's row keeps #59: single-email isolation and
        the strict target checks."""
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"}], case=self)
        a_dir = fixture["dirs"][A]
        choices = self.write_json("target-choices.json",
                                  [explicit_row(A_ID, a_dir)])
        results = self.write_results("target-raw.json", [A_ID])
        humanized = self.humanized("target", results, choices)
        out = self.finalize("--result", results, "--choices", choices,
                            "--email-id", A_ID, "--humanized", humanized)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual([row["email_id"] for row in out["emails"]], [A_ID])
        self.assertTrue(Path(out["emails"][0]["md"]).is_file(), out)


class TestStage5BatchStaysAtomic(helpers.Stage5LocalHarness, BaseEnv):
    """Plan r19 P3: one professor's own batch is a zero-partial-commit deal.

    A full-professor batch (no ``--email-id``) whose second email is missing
    its must-have humanized body must answer the whole batch's error and
    commit nothing — no rendered md/txt for either email, no professor state
    — instead of splitting into a partial success. The positive control at
    the end proves every other premise was legal: only the tested condition
    differs between the failing and the committing run.
    """

    def research_files(self):
        research = self.root / "教授研究"
        return {str(path): path.read_bytes()
                for path in sorted(research.rglob("*")) if path.is_file()}

    def test_r19_batch_with_one_missing_humanized_commits_nothing(self):
        fixture = helpers.write_issue59_stage5_fixture(self.root, [
            {"professor": A, "evidence": "fresh"},
            {"professor": A, "evidence": "fresh",
             "idea_id": helpers.ISSUE59_PEER_IDEA_ID}], case=self)
        prof_dir = fixture["dirs"][A].resolve()
        both = list(fixture["email_ids"])
        results = self.write_results("batch-raw.json", both)
        choices = self.write_choices("batch-choices.json", both)
        drafts = self.plan("--result", results, "--choices", choices)
        self.assertEqual(drafts["status"], "ok", drafts)
        self.assertEqual(sorted(row["email_id"] for row in drafts["drafts"]),
                         sorted(both), drafts)
        complete = json.loads(
            self.humanized_map("batch-map.json", drafts["drafts"])
            .read_text(encoding="utf-8"))
        self.assertEqual(sorted(complete), sorted(
            row["output_id"] for row in drafts["drafts"]), complete)
        # The one broken premise: one output's body file does not exist.
        missing_id = sorted(complete)[-1]
        missing_path = self.root / "absent-batch-humanized.txt"
        self.assertFalse(missing_path.exists())
        broken = self.write_json("batch-broken-map.json",
                                 {**complete, missing_id: str(missing_path)})

        before = self.research_files()
        out = self.finalize("--result", results, "--choices", choices,
                            "--humanized-map", broken)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "result_missing", out)
        self.assertIn(str(missing_path), out["message"], out)
        self.assertEqual(self.research_files(), before,
                         "the failed batch left a partial commit behind")
        self.assertFalse(any(path.name == contact_state.EMAIL_STATE or
                             path.name.startswith("套磁邮件")
                             for path in prof_dir.iterdir()),
                         f"partial commit survived in {prof_dir}")

        # Positive control: restore only the tested condition and the very
        # same batch commits both emails in one professor-local transaction.
        out = self.finalize("--result", results, "--choices", choices,
                            "--humanized-map",
                            self.root / "batch-map.json")
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(sorted(row["email_id"] for row in out["emails"]),
                         sorted(both), out)
        rendered = [Path(row["md"]) for row in out["emails"]]
        rendered += [Path(row["txt"]) for row in out["emails"]]
        self.assertEqual(len(set(rendered)), 2 * len(both), out)
        self.assertTrue(all(path.parent.resolve() == prof_dir
                            for path in rendered), out)
        self.assertTrue((prof_dir / contact_state.EMAIL_STATE).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
