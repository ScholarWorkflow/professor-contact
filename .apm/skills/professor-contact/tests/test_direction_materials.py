"""TP1 T2-T6 checks for direction-scoped experience materials.

Prepared by the local test engineer from
``plan/direction-experience-materials/test-plan.md`` (TP1.5).  The product
feature is not implemented in this commit: every case drives the planned
public entry points (``contact_state.py direction-materials-save`` and the
Stage-4/Stage-5 commands that must carry the frozen slice) and reads the
planned ``方向素材.json`` shape.  Running this module before the implementation
lands therefore records 未执行, never PASS.

Scope is exactly T2-T6 of the plan's single required checklist; T1 is a static
reading task and has no case here.  T4 rebuilds the Stage-4 pack and creates
fresh Stage-5 result and draft files for the updated answer; no model-result
material fingerprint or stale-result rejection contract is introduced.
"""

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parent / "scripts" / "contact_state.py"

_spec = importlib.util.spec_from_file_location(
    "contact_state_test_helpers", HERE / "test_contact_state.py")
helpers = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = helpers
_spec.loader.exec_module(helpers)

BaseEnv = helpers.BaseEnv
parse = helpers.parse
run_cli = helpers.run_cli
contact_state = helpers.contact_state
issue59_choices = helpers.issue59_choices
issue59_write_evidence = helpers.issue59_write_evidence
install_issue59_checker = helpers.install_issue59_checker
write_issue59_verify = helpers.write_issue59_verify

MATERIALS = "方向素材.json"
SAVE_COMMAND = "direction-materials-save"
PROFESSOR = "試験 教授"
DIRECTION_A = "DIR00001"
DIRECTION_B = "DIR00002"

# Synthetic experience answers: fixed text the user "gave", never rewritten.
ANSWER_A_V1 = ("高校の授業でグラフ理論の課題を解いたとき、入力の並びを変えると"
               "結果が変わるのが面白いと感じた。")
ANSWER_A_V2 = ("高校の授業でグラフ理論の課題を解いたとき、入力の並びを変えると"
               "結果が変わるのが面白いと感じた。今は簡単な例で試している。")
ANSWER_A_V3 = "短期のアルバイトで、表計算の並べ替えを手で確かめたことがある。"
ANSWER_B = "ゼミで読んだ論文の図が分かりやすく、同じ題材を自分でも試してみたいと思った。"
QUESTION_A = "グラフやネットワークに関係することを、授業などで触れたことはありますか？"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runner_commands():
    """The CLI subcommands the runner under test actually registers."""
    import argparse
    spec = importlib.util.spec_from_file_location("direction_materials_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    parser = module.build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("runner parser registers no subcommands")


def require_save_entry(case):
    """Skip with 未执行, not fail, until the planned entry point exists.

    TP1 states the new capability is not implemented in this PR; a missing
    command is an unimplemented product, so the recipe records 未执行 rather
    than a business failure.
    """
    if SAVE_COMMAND not in runner_commands():
        case.skipTest(f"{SAVE_COMMAND} is not implemented yet: TP1 T2-T6 未执行")


def material_entries(data, direction_id):
    """Read one direction's materials from the planned ``方向素材.json`` shape.

    The plan fixes the per-direction grouping, the stable ``material_id`` and
    the verbatim ``question``/``answer``; it does not fix list vs. mapping for
    the bucket, so this reader accepts either and never invents an entry.
    """
    bucket = ((data or {}).get("directions") or {}).get(direction_id) or []
    if isinstance(bucket, dict):
        bucket = list(bucket.values())
    return bucket


# The Stage-4 fact tuple the pre-feature runner hashed: ``contact_state.py``
# ``EMAIL_SOURCE_HASH_FIELDS`` on main ``b67dd3c``, before direction materials
# existed. A pack written back then carries a hash over exactly these keys.
LEGACY_SOURCE_HASH_FIELDS = (
    "email_id", "direction_ids", "directions", "idea", "papers", "gaps",
    "red_lines", "allowed_sources", "contact_evidence", "cross_direction",
)


def legacy_source_hash(entry):
    """The pre-feature ``email_source_hash`` for one row.

    Same canonical encoding the runner uses (``ensure_ascii=False``,
    ``sort_keys=True``) over the fixed pre-feature key tuple.
    """
    payload = {key: entry[key] for key in LEGACY_SOURCE_HASH_FIELDS}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def strip_material_fields(pack):
    """The pre-feature pack shape: no ``direction_material*`` field anywhere."""

    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()
                    if not str(key).startswith("direction_material")}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return clean(pack)


def legacy_pack(pack):
    """A faithful pre-feature pack: old field structure *and* its old hash.

    Dropping the new fields alone leaves the hash the current rule computed over
    them, which no pre-feature producer ever wrote. Recompute each row with the
    old key tuple (and drop the ``direction_material:`` source ids a
    pre-feature pack could not contain) so the fixture really is an old pack.
    """
    legacy = strip_material_fields(pack)
    for email in legacy.get("emails") or []:
        if not isinstance(email, dict):
            continue
        sources = email.get("allowed_sources")
        if isinstance(sources, list):
            email["allowed_sources"] = [
                source for source in sources
                if not (isinstance(source, str)
                        and source.startswith("direction_material:"))]
        email["source_hash"] = legacy_source_hash(email)
    return legacy


class _DirectionMaterialsBase(BaseEnv):
    """One synthetic professor with two canonical directions, both selected.

    No test methods live here: each case class declares its own so the recipe
    can run the classes by name.
    """

    def setUp(self):
        super().setUp()
        self.profile = self.root / "profile.md"
        self.profile.write_text("兴趣：合成输入比较\n", encoding="utf-8")
        self.assertEqual(self.stage3_run(profile=str(self.profile))["status"], "ok")
        second = self.add_second_direction()
        self.assertEqual(parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--results", second, "--program-root", self.root,
            "--collection-key", DIRECTION_B,
            "--profile", str(self.profile)))["status"], "ok")
        issue59_write_evidence(self.root, {PROFESSOR: self.prof_dir})
        install_issue59_checker(self, self.root)
        self.stage4(self.both_directions(), name="sel-both.json")
        (self.root / "info.json").write_text(json.dumps({
            "university": "試験大学", "department": "試験研究科",
            "target": {"intake_year": 2027, "intake_term": "april"}},
            ensure_ascii=False), encoding="utf-8")
        (self.root / "boshu_analysis.json").write_text(json.dumps({
            "exam_type": {"degree": "博士前期課程",
                          "selection_name": "春季 テスト選抜 合成工学専攻"}},
            ensure_ascii=False), encoding="utf-8")
        write_issue59_verify(self.root, self.prof_dir, PROFESSOR)

    # ---- Stage-4 fixture --------------------------------------------------

    def selection(self, direction_id, idea_id):
        return {"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
                "direction_ids": [direction_id], "ideas": [{"id": idea_id}]}

    def both_directions(self):
        return [self.selection(DIRECTION_A, "DIR00001_1"),
                self.selection(DIRECTION_B, "DIR00002_1")]

    def stage4(self, selections, name="sel.json"):
        path = self.root / name
        path.write_text(json.dumps({"selections": selections}, ensure_ascii=False),
                        encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", path,
                            "--profile", str(self.profile)))
        self.assertEqual(out["status"], "ok", out)
        row = helpers.stage4_row(out)
        self.email_pack = Path(row["email_pack"])
        return out

    def pack(self):
        return json.loads(self.email_pack.read_text(encoding="utf-8"))

    def email(self, direction_id):
        rows = [row for row in self.pack()["emails"]
                if row.get("direction_ids") == [direction_id]]
        self.assertEqual(len(rows), 1, rows)
        return rows[0]

    def email_for_idea(self, idea_id):
        rows = [row for row in self.pack()["emails"]
                if (row.get("idea") or {}).get("id") == idea_id]
        self.assertEqual(len(rows), 1, rows)
        return rows[0]

    def clone_professor(self, name, field="Y分野"):
        """A second professor whose pack carries the same direction ids."""
        directory = self.root / "教授研究" / field / name
        directory.mkdir(parents=True, exist_ok=True)
        for filename in (contact_state.CANDIDATE_STATE, contact_state.INPUT_PACK):
            data = json.loads((self.prof_dir / filename).read_text(encoding="utf-8"))
            if filename == contact_state.INPUT_PACK:
                data["professor"] = name
                data["professor_dir"] = str(directory)
            (directory / filename).write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return directory

    # ---- material file and save entry ------------------------------------

    def materials_path(self, professor_dir=None):
        return Path(professor_dir or self.prof_dir) / MATERIALS

    def materials(self, professor_dir=None):
        path = self.materials_path(professor_dir)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, direction_id=DIRECTION_A, *, answer=ANSWER_A_V1, question=None,
             material_id=None, expected_sha256=None, expect_missing=False,
             professor_dir=None):
        arguments = [SAVE_COMMAND, "--program-root", str(self.root),
                     "--professor-dir", str(professor_dir or self.prof_dir),
                     "--direction-id", direction_id, "--answer", answer]
        if question is not None:
            arguments.extend(["--question", question])
        if material_id is not None:
            arguments.extend(["--material-id", material_id])
        if expected_sha256 is not None:
            arguments.extend(["--expected-sha256", expected_sha256])
        if expect_missing:
            arguments.append("--expect-missing")
        return run_cli(*arguments)

    def save_ok(self, **arguments):
        payload = parse(self.save(**arguments))
        self.assertEqual(payload["status"], "ok", payload)
        return payload

    # ---- Stage-5 fixture --------------------------------------------------

    def stage5(self, *arguments):
        return run_cli("stage5-plan", "--program-root", self.root,
                       "--email-pack", str(self.email_pack), *arguments)

    def plan(self, email_id=None, *arguments):
        extra = ("--email-id", email_id) if email_id else ()
        return parse(self.stage5(*extra, *arguments))

    def model_result(self, email, *, first_source=None,
                     gap_source=None, name="raw.json"):
        """One legal three-part synthetic model result for the current pack."""
        payload = {
            "schema": 1, "kind": "email", "email_id": email["email_id"],
            "interest_sentences_ja": [
                "合成入力の比較を、身近な例から考えてきました。",
                f"先生のご論文「{email['papers'][0]['title']}」を拝読し、"
                "比較の広がりに気づきました。",
                "例えば、別の合成入力でも同じ比較ができれば、と考えています。"],
            "future_aspiration_ja": "入力設計、評価実験、実データへの適用",
            "learning_candidates": ["比較手法の基礎知識の習得", "評価方法の基礎"],
            "source_map": [
                {"output": "①", "source_ids": [first_source or "profile.interest"]},
                {"output": "②", "source_ids": [f"paper:{email['papers'][0]['item_key']}"]},
                {"output": "③", "source_ids": [gap_source or
                                                f"gap:{email['anchorable_gaps'][0]}"]},
                {"output": "future", "source_ids": [f"idea:{email['idea']['id']}"]}],
        }
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def choices(self, email, name="choices.json"):
        path = self.root / name
        path.write_text(json.dumps(issue59_choices(email["email_id"]),
                                   ensure_ascii=False), encoding="utf-8")
        return path

    def draft(self, email, raw, choices, name="draft.txt"):
        plan = parse(self.stage5("--result", raw, "--choices", choices,
                                 "--email-id", email["email_id"]))
        self.assertEqual(plan["status"], "ok", plan)
        path = self.root / name
        path.write_text(plan["drafts"][0]["draft"], encoding="utf-8")
        return path

    def finalize(self, email, raw, choices, humanized):
        return run_cli("stage5-finalize", "--program-root", self.root,
                       "--email-pack", str(self.email_pack),
                       "--result", raw, "--choices", choices,
                       "--humanized", humanized, "--email-id", email["email_id"])

    def rendered(self, email=None):
        """Every Stage-5 surface a committed run leaves for this professor."""
        paths = [self.prof_dir / contact_state.EMAIL_STATE]
        if email is not None:
            entry = (self.email_state().get("emails") or {}).get(email["email_id"]) or {}
            paths.extend(Path(value) for value in (entry.get("files") or {}).values())
        return {str(path): path.read_bytes() for path in paths if path.is_file()}

    def email_state(self):
        path = self.prof_dir / contact_state.EMAIL_STATE
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def rendered_text(self, email):
        entry = (self.email_state().get("emails") or {}).get(email["email_id"]) or {}
        md = (entry.get("files") or {}).get("md")
        return Path(md).read_text(encoding="utf-8") if md else ""

    def commit_email(self, email, *, first_source=None, name="raw.json"):
        raw = self.model_result(email, first_source=first_source, name=name)
        choices = self.choices(email, name=f"choices-{name}")
        humanized = self.draft(email, raw, choices, name=f"draft-{name}.txt")
        out = parse(self.finalize(email, raw, choices, humanized))
        self.assertEqual(out["status"], "ok", out)
        return raw, choices, humanized


class DirectionMaterialsSaveTests(_DirectionMaterialsBase):
    """T2: one saved answer stays verbatim and freezes for its direction only."""

    def test_t2_saved_answer_is_frozen_for_the_selected_direction_only(self):
        require_save_entry(self)
        state_before = (self.prof_dir / contact_state.CANDIDATE_STATE).read_bytes()
        profile_before = self.profile.read_bytes()
        saved = self.save_ok(direction_id=DIRECTION_A, question=QUESTION_A,
                             answer=ANSWER_A_V1, expect_missing=True)
        material_id = saved["material_id"]
        self.assertTrue(material_id)
        self.assertEqual(Path(saved["materials_file"]).resolve(),
                         self.materials_path().resolve())

        data = self.materials()
        self.assertEqual(data["schema"], 1)
        self.assertEqual(Path(data["professor_dir"]).resolve(), self.prof_dir.resolve())
        entries = material_entries(data, DIRECTION_A)
        self.assertEqual(len(entries), 1, entries)
        self.assertEqual(entries[0]["material_id"], material_id)
        self.assertEqual(entries[0]["question"], QUESTION_A)
        self.assertEqual(entries[0]["answer"], ANSWER_A_V1)
        self.assertEqual(material_entries(data, DIRECTION_B), [])
        # The answer is user input, not a profile or Stage-3 fact.
        self.assertEqual((self.prof_dir / contact_state.CANDIDATE_STATE).read_bytes(),
                         state_before)
        self.assertEqual(self.profile.read_bytes(), profile_before)

        self.stage4(self.both_directions(), name="sel-after-save.json")
        email_a, email_b = self.email(DIRECTION_A), self.email(DIRECTION_B)
        self.assertEqual([row["answer"] for row in email_a["direction_materials"]],
                         [ANSWER_A_V1])
        self.assertEqual(email_a["direction_materials"][0]["direction_id"], DIRECTION_A)
        self.assertEqual(email_a["direction_materials"][0]["material_id"], material_id)
        self.assertEqual(email_b["direction_materials"], [])
        source = f"direction_material:{DIRECTION_A}:{material_id}"
        self.assertIn(source, email_a["allowed_sources"])
        self.assertNotIn(source, email_b["allowed_sources"])

        # Same direction, same material: a recompile keeps the stable identity.
        self.stage4(self.both_directions(), name="sel-again.json")
        self.assertEqual([row["material_id"] for row in self.email(DIRECTION_A)
                          ["direction_materials"]], [material_id])
        self.assertEqual((self.prof_dir / contact_state.CANDIDATE_STATE).read_bytes(),
                         state_before)

    def test_t2_selection_changes_do_not_delete_saved_materials(self):
        require_save_entry(self)
        saved = self.save_ok(direction_id=DIRECTION_A, question=QUESTION_A,
                             answer=ANSWER_A_V1, expect_missing=True)
        material_id = saved["material_id"]
        file_before = self.materials_path().read_bytes()

        # Same direction, another idea: the material is reusable, not re-asked.
        self.stage4([self.selection(DIRECTION_A, "DIR00001_2"),
                     self.selection(DIRECTION_B, "DIR00002_1")],
                    name="sel-other-idea.json")
        other = self.email_for_idea("DIR00001_2")
        self.assertEqual([row["answer"] for row in other["direction_materials"]],
                         [ANSWER_A_V1])

        # Deselect direction A through the public Stage-4 entry: an empty idea
        # list for that scope removes its email, never the user's answer.
        self.stage4([{"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
                      "direction_ids": [DIRECTION_A], "ideas": []},
                     self.selection(DIRECTION_B, "DIR00002_1")],
                    name="sel-deselect.json")
        self.assertEqual([row["direction_ids"] for row in self.pack()["emails"]],
                         [[DIRECTION_B]])
        self.assertEqual(self.materials_path().read_bytes(), file_before)
        self.assertEqual([row["material_id"] for row in
                          material_entries(self.materials(), DIRECTION_A)],
                         [material_id])

        # Re-select direction A: the same answer is frozen again.
        self.stage4(self.both_directions(), name="sel-reselect.json")
        self.assertEqual([row["material_id"] for row in self.email(DIRECTION_A)
                          ["direction_materials"]], [material_id])


class DirectionMaterialsProvenanceTests(_DirectionMaterialsBase):
    """T3: the frozen slice is the only legal experience source."""

    def _frozen(self):
        require_save_entry(self)
        saved = self.save_ok(direction_id=DIRECTION_A, question=QUESTION_A,
                             answer=ANSWER_A_V1, expect_missing=True)
        self.stage4(self.both_directions(), name="sel-t3.json")
        email = self.email(DIRECTION_A)
        plan = self.plan(email["email_id"])
        self.assertEqual(plan["status"], "ok", plan)
        return saved["material_id"], email, plan["jobs"][0]

    def test_t3_frozen_material_reference_is_accepted_and_rendered(self):
        material_id, email, job = self._frozen()
        self.assertEqual([row["answer"] for row in job["model_input"]
                          ["direction_materials"]], [ANSWER_A_V1])
        source = f"direction_material:{DIRECTION_A}:{material_id}"
        self.assertIn(source, self.email(DIRECTION_A)["allowed_sources"])
        raw, choices, humanized = self.commit_email(
            email, first_source=source, name="t3-legal.json")
        md = self.rendered_text(self.email(DIRECTION_A))
        self.assertIn("| 句 | 来源 |", md)
        self.assertTrue(material_id in md or ANSWER_A_V1 in md, md)
        # "显示准确来源": the ① row must render a human-readable source, not the
        # bare machine id the renderer falls back to for unknown sources.
        first_row = next((line for line in md.splitlines()
                          if line.startswith("| 兴趣段①")), "")
        self.assertTrue(first_row, md)
        cells = [cell.strip() for cell in first_row.strip("|").split("|")]
        self.assertEqual(len(cells), 2, first_row)
        self.assertNotEqual(cells[1], source, first_row)

    def test_t3_unfrozen_material_cannot_be_cited(self):
        material_id, email, job = self._frozen()
        raw, choices, humanized = self.commit_email(
            email, name="t3-baseline.json")
        before = self.rendered(email)

        for label, source in (
                ("other-direction", f"direction_material:{DIRECTION_B}:{material_id}"),
                ("unknown", f"direction_material:{DIRECTION_A}:MAT00000000")):
            bad = self.model_result(email, first_source=source,
                                    name=f"t3-{label}.json")
            rejected = self.finalize(email, bad, choices, humanized)
            self.assertNotEqual(rejected.returncode, 0, label)
            self.assertIn("allowed_sources", rejected.stdout, label)
            self.assertEqual(self.rendered(email), before, label)

        # ③ still has to cite a gap; a material may never replace it.
        bad_gap = self.model_result(email,
                                    gap_source=f"direction_material:{DIRECTION_A}:{material_id}",
                                    name="t3-gap.json")
        rejected = self.finalize(email, bad_gap, choices, humanized)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("gap:", rejected.stdout)
        self.assertEqual(self.rendered(email), before)


class DirectionMaterialsFreshnessTests(_DirectionMaterialsBase):
    """T4: changing an answer refreshes only the emails that depend on it."""

    def test_t4_answer_update_requires_a_stage4_refreeze(self):
        require_save_entry(self)
        saved = self.save_ok(direction_id=DIRECTION_A, question=QUESTION_A,
                             answer=ANSWER_A_V1, expect_missing=True)
        material_id = saved["material_id"]
        self.stage4(self.both_directions(), name="sel-t4.json")
        email = self.email(DIRECTION_A)
        hash_v1 = email["source_hash"]
        plan_v1 = self.plan(email["email_id"])
        self.assertEqual(plan_v1["status"], "ok", plan_v1)
        self.assertEqual([row["answer"] for row in plan_v1["jobs"][0]
                          ["model_input"]["direction_materials"]], [ANSWER_A_V1])
        raw, choices, humanized = self.commit_email(email, name="t4-v1.json")
        before = self.rendered(email)
        state_before = (self.prof_dir / contact_state.CANDIDATE_STATE).read_bytes()
        profile_before = self.profile.read_bytes()

        # Update the same material: the frozen pack is now stale.
        self.save_ok(direction_id=DIRECTION_A, material_id=material_id,
                     answer=ANSWER_A_V2,
                     expected_sha256=digest(self.materials_path()))
        stale_plan = self.plan(email["email_id"])
        self.assertEqual(stale_plan["status"], "needs_refresh", stale_plan)
        stale_final = parse(self.finalize(email, raw, choices, humanized))
        self.assertEqual(stale_final["status"], "needs_refresh", stale_final)
        self.assertEqual(self.rendered(email), before)

        # Re-freeze through Stage 4: the email input hash and the slice change.
        self.stage4(self.both_directions(), name="sel-refreeze.json")
        email_v2 = self.email(DIRECTION_A)
        self.assertNotEqual(email_v2["source_hash"], hash_v1)
        plan_v2 = self.plan(email_v2["email_id"])
        self.assertEqual(plan_v2["status"], "ok", plan_v2)
        self.assertEqual([row["answer"] for row in email_v2["direction_materials"]],
                         [ANSWER_A_V2])
        self.assertEqual([row["answer"] for row in plan_v2["jobs"][0]
                          ["model_input"]["direction_materials"]], [ANSWER_A_V2])

        # Rebuild this run's result AND draft from the refreshed Stage-5 input.
        # Never pair the old draft/result with the new email pack.
        source = f"direction_material:{DIRECTION_A}:{material_id}"
        self.assertIn(source, email_v2["allowed_sources"])
        self.commit_email(email_v2, first_source=source, name="t4-v2.json")
        md = self.rendered_text(self.email(DIRECTION_A))
        self.assertTrue(material_id in md or ANSWER_A_V2 in md, md)

        # An unrelated direction's answer never changes this email's fingerprint.
        hash_a = self.email(DIRECTION_A)["source_hash"]
        hash_b = self.email(DIRECTION_B)["source_hash"]
        self.save_ok(direction_id=DIRECTION_B, answer=ANSWER_B, expect_missing=True)
        self.stage4(self.both_directions(), name="sel-b-change.json")
        self.assertEqual(self.email(DIRECTION_A)["source_hash"], hash_a)
        self.assertNotEqual(self.email(DIRECTION_B)["source_hash"], hash_b)

        # No profile or Stage-3 rewrite anywhere in the sequence.
        self.assertEqual((self.prof_dir / contact_state.CANDIDATE_STATE).read_bytes(),
                         state_before)
        self.assertEqual(self.profile.read_bytes(), profile_before)


class DirectionMaterialsCompatibilityTests(_DirectionMaterialsBase):
    """T5: old packs keep working until their direction gains a live answer."""

    def test_t5_pack_without_materials_keeps_old_behavior(self):
        require_save_entry(self)
        self.stage4(self.both_directions(), name="sel-t5.json")
        current = self.pack()
        legacy = legacy_pack(current)
        self.email_pack.write_text(json.dumps(legacy, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        email = self.email(DIRECTION_A)
        self.assertNotIn("direction_materials", email)
        # The fixture is an old pack only if its hash matches the old field
        # structure; keeping the new-rule hash would test a shape no
        # pre-feature producer ever wrote.
        self.assertEqual(email["source_hash"], legacy_source_hash(email))

        plan = self.plan(email["email_id"])
        self.assertEqual(plan["status"], "ok", plan)
        job = plan["jobs"][0]
        # No live answer exists for this direction, so the old pack is complete.
        raw, choices, humanized = self.commit_email(email, name="t5-legacy.json")
        self.assertEqual(self.materials_path().exists(), False)

        before = self.rendered(email)
        saved = self.save_ok(direction_id=DIRECTION_A, answer=ANSWER_A_V1,
                             expect_missing=True)
        stale_plan = self.plan(email["email_id"])
        self.assertEqual(stale_plan["status"], "needs_refresh", stale_plan)
        stale_final = parse(self.finalize(email, raw, choices, humanized))
        self.assertEqual(stale_final["status"], "needs_refresh", stale_final)
        self.assertEqual(self.rendered(email), before)

        # After the required Stage-4 refreeze the same email becomes renderable
        # again; the old pack is never rewritten in place.
        self.stage4(self.both_directions(), name="sel-t5-refrozen.json")
        refrozen = self.email(DIRECTION_A)
        self.assertEqual([row["material_id"] for row in refrozen["direction_materials"]],
                         [saved["material_id"]])
        plan_after = self.plan(refrozen["email_id"])
        self.assertEqual(plan_after["status"], "ok", plan_after)

    def test_t5_removed_material_is_a_slice_change(self):
        require_save_entry(self)
        self.save_ok(direction_id=DIRECTION_A, answer=ANSWER_A_V1, expect_missing=True)
        self.stage4(self.both_directions(), name="sel-t5-removed.json")
        email = self.email(DIRECTION_A)
        plan = self.plan(email["email_id"])
        self.assertEqual(plan["status"], "ok", plan)
        raw, choices, humanized = self.commit_email(email, name="t5-frozen.json")
        before = self.rendered(email)

        # Withdrawing the answer is the same slice change as adding one.
        self.materials_path().rename(
            self.materials_path().with_name(MATERIALS + ".withdrawn"))
        stale_plan = self.plan(email["email_id"])
        self.assertEqual(stale_plan["status"], "needs_refresh", stale_plan)
        stale_final = parse(self.finalize(email, raw, choices, humanized))
        self.assertEqual(stale_final["status"], "needs_refresh", stale_final)
        self.assertEqual(self.rendered(email), before)


class DirectionMaterialsSaveGuardTests(_DirectionMaterialsBase):
    """T6: the save entry refuses foreign binding and never overwrites by guess."""

    def test_t6_save_rejects_foreign_binding_and_stale_digest(self):
        require_save_entry(self)
        # (1) A direction outside this professor's formal range.
        unknown = self.save(direction_id="DIR99999", answer=ANSWER_A_V1,
                            expect_missing=True)
        self.assertNotEqual(unknown.returncode, 0)
        self.assertFalse(self.materials_path().exists())

        # (2) A professor directory outside program_root/教授研究, both a sibling
        # of the program root and one inside it but outside 教授研究.
        for outside in (self.root / "outside" / "教授",
                        Path(tempfile.mkdtemp(prefix="direction-materials-outside-"))
                        / "教授"):
            self.addCleanup(shutil.rmtree, outside.parent, True)
            outside.mkdir(parents=True, exist_ok=True)
            foreign_dir = self.save(professor_dir=outside, answer=ANSWER_A_V1,
                                    expect_missing=True)
            self.assertNotEqual(foreign_dir.returncode, 0, outside)
            self.assertFalse((outside / MATERIALS).exists(), outside)

        # (3) Normal save, then an update bound to the wrong old digest.
        saved = self.save_ok(direction_id=DIRECTION_A, question=QUESTION_A,
                             answer=ANSWER_A_V1, expect_missing=True)
        material_id = saved["material_id"]
        file_sha = digest(self.materials_path())
        before = self.materials_path().read_bytes()
        stale = self.save(direction_id=DIRECTION_A, material_id=material_id,
                          answer=ANSWER_A_V2, expected_sha256="0" * 64)
        self.assertNotEqual(stale.returncode, 0)
        self.assertEqual(self.materials_path().read_bytes(), before)

        # (4) The correct digest updates the same entry instead of duplicating it.
        self.save_ok(direction_id=DIRECTION_A, material_id=material_id,
                     answer=ANSWER_A_V2, expected_sha256=file_sha)
        entries = material_entries(self.materials(), DIRECTION_A)
        self.assertEqual(len(entries), 1, entries)
        self.assertEqual(entries[0]["material_id"], material_id)
        self.assertEqual(entries[0]["answer"], ANSWER_A_V2)
        updated = self.materials_path().read_bytes()

        # (5) An unreadable file is not an empty library to overwrite.
        broken = b'{ this is not the direction material file'
        self.materials_path().write_bytes(broken)
        refused = self.save(direction_id=DIRECTION_A, answer=ANSWER_A_V3,
                            expect_missing=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(self.materials_path().read_bytes(), broken)
        self.materials_path().write_bytes(updated)

        # (6) A same-named direction in another professor stays professor-local.
        # Do not require material_id uniqueness across different professors.
        other = self.clone_professor("別 教授")
        other_saved = self.save_ok(direction_id=DIRECTION_A, answer=ANSWER_B,
                                   expect_missing=True, professor_dir=other)
        other_entries = material_entries(self.materials(other), DIRECTION_A)
        self.assertEqual(len(other_entries), 1, other_entries)
        self.assertEqual(other_entries[0]["material_id"], other_saved["material_id"])
        self.assertEqual(other_entries[0]["answer"], ANSWER_B)
        self.assertEqual(self.materials_path().read_bytes(), updated)


if __name__ == "__main__":
    unittest.main()
