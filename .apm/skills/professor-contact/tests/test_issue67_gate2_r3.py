"""Gate-2 regressions added for the issue #67 Gate-1 r3 contract.

These tests stay producer-local and deterministic. They only cover the three
false-PASS gaps introduced by the r3 acceptance contract; clean-consumer
delegation remains owned by PC67-RISO.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from test_contact_state import (
    _Issue67Stage4Fixture,
    contact_state,
    parse,
    run_cli,
    stage4_row,
)


class Issue67Gate2R3IdentityTests(_Issue67Stage4Fixture):
    """PC67-DSTATE supplement: display text is never formal Stage-4 identity."""

    def test_same_canonical_scope_with_different_display_names_is_duplicate(self):
        out = self.stage4(
            [
                self.row(self.prof_dir, professor="旧表示"),
                self.row(self.prof_dir, professor="新表示"),
            ],
            name="r3-display-duplicate.json",
        )
        self.assertEqual(out["status"], "error", out)
        row = stage4_row(out)
        self.assertEqual(row["reason_code"], "duplicate_selection", out)
        self.assertIsNone(row["selection_file"])
        self.assertIsNone(row["email_pack"])
        self.assert_no_pair(self.prof_dir, "duplicate canonical scope")
        self.assert_program_pair_absent()

    def test_display_name_change_replaces_the_existing_canonical_scope(self):
        first = self.stage4(
            [self.row(self.prof_dir, professor="旧表示", idea="DIR00001_1")],
            name="r3-display-first.json",
        )
        self.assertEqual(stage4_row(first)["status"], "ok", first)

        second = self.stage4(
            [self.row(self.prof_dir, professor="新表示", idea="DIR00001_2")],
            name="r3-display-second.json",
        )
        self.assertEqual(stage4_row(second)["status"], "ok", second)

        selection = json.loads(
            (self.prof_dir / self.SELECT).read_text(encoding="utf-8")
        )
        rows = selection["selections"]
        self.assertEqual(len(rows), 1, selection)
        self.assertEqual(rows[0]["direction_ids"], ["DIR00001"])
        self.assertEqual([idea["id"] for idea in rows[0]["ideas"]], ["DIR00001_2"])
        self.assert_program_pair_absent()


class Issue67Gate2R3SelectedRefreshTests(_Issue67Stage4Fixture):
    """PC67-DADJ supplement: explicit local selection is professor-bound."""

    def _make_state_stale(self) -> None:
        path = self.prof_dir / contact_state.CANDIDATE_STATE
        state = json.loads(path.read_text(encoding="utf-8"))
        state["input_fingerprints"] = {
            direction_id: "r3-stale-fingerprint"
            for direction_id in state["input_fingerprints"]
        }
        path.write_text(
            json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    @staticmethod
    def _tree_bytes(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def test_explicit_local_selection_rejects_foreign_or_missing_professor_identity(self):
        committed = self.stage4(
            [self.row(self.prof_dir)], name="r3-selected-authority.json"
        )
        self.assertEqual(stage4_row(committed)["status"], "ok", committed)
        selection_path = self.prof_dir / self.SELECT
        valid = json.loads(selection_path.read_text(encoding="utf-8"))
        foreign = self.clone_professor("対照 教授")
        self._make_state_stale()

        variants = {}

        container_foreign = copy.deepcopy(valid)
        container_foreign["professor_dir"] = str(foreign)
        variants["foreign_container"] = container_foreign

        row_foreign = copy.deepcopy(valid)
        row_foreign["selections"][0]["professor_dir"] = str(foreign)
        variants["foreign_row"] = row_foreign

        row_missing = copy.deepcopy(valid)
        row_missing["selections"][0].pop("professor_dir", None)
        variants["missing_row_identity"] = row_missing

        for label, document in variants.items():
            with self.subTest(variant=label):
                selection_path.write_text(
                    json.dumps(document, ensure_ascii=False, indent=1),
                    encoding="utf-8",
                )
                before = self._tree_bytes(self.prof_dir)

                plan_process = run_cli(
                    "stage3-plan",
                    "--professor-dir",
                    self.prof_dir,
                    "--program-root",
                    self.root,
                    "--refresh-scope",
                    "selected",
                    "--selection",
                    selection_path,
                )
                self.assertEqual(plan_process.returncode, 1, plan_process.stderr)
                plan = parse(plan_process)
                self.assertEqual(plan["reason_code"], "selection_scope_mismatch", plan)
                self.assertNotIn("jobs", plan)
                self.assertEqual(self._tree_bytes(self.prof_dir), before)

                results = self.root / f"r3-selected-{label}-results"
                results.mkdir(parents=True, exist_ok=True)
                finalize_process = run_cli(
                    "stage3-finalize",
                    "--professor-dir",
                    self.prof_dir,
                    "--results",
                    results,
                    "--program-root",
                    self.root,
                    "--refresh-scope",
                    "selected",
                    "--selection",
                    selection_path,
                )
                self.assertEqual(finalize_process.returncode, 1, finalize_process.stderr)
                finalized = parse(finalize_process)
                self.assertEqual(
                    finalized["reason_code"], "selection_scope_mismatch", finalized
                )
                self.assertEqual(self._tree_bytes(self.prof_dir), before)


REPO_ROOT = Path(__file__).resolve().parents[4]
SELECTION_AGENT = REPO_ROOT / ".apm" / "agents" / "professor-contact-selection.agent.md"


class Issue67Gate2R3SelectionContractTests(unittest.TestCase):
    """PC67-DADJ supplement: lock the r3 pre-runner routing and input compatibility."""

    def setUp(self):
        self.assertTrue(
            SELECTION_AGENT.is_file(), f"missing selection agent: {SELECTION_AGENT}"
        )
        self.text = SELECTION_AGENT.read_text(encoding="utf-8")

    def _step1(self) -> str:
        start = self.text.index("### Step 1")
        end = self.text.index("### Step 2", start)
        return self.text[start:end]

    def test_explicit_selection_routes_requested_professors_before_formal_reads(self):
        step1 = self._step1()
        no_dir = step1.index("条目没有目录来源")
        before_no_dir = step1[:no_dir]
        self.assertRegex(
            before_no_dir,
            r"先按原请求逐教授分流.{0,40}再读任何教授正式文件",
        )
        self.assertNotIn(
            'find 教授研究 -name "套磁候选状态.json"',
            before_no_dir,
            "whole-project discovery is only allowed after entering the no-dir branch",
        )

    def test_reliable_professor_dir_does_not_require_unrelated_professor_state(self):
        step1 = self._step1()
        known = step1.index("条目已带可靠 `professor_dir`")
        no_dir = step1.index("条目没有目录来源", known)
        known_dir_branch = step1[known:no_dir]
        self.assertRegex(
            known_dir_branch,
            r"只读取请求所涉及教授.{0,100}(?:不得|不是).{0,120}(?:全项目扫描|前置读取条件)",
        )
        self.assertNotIn('find 教授研究 -name', known_dir_branch)

    def test_no_dir_structured_and_natural_language_inputs_remain_supported_per_request(self):
        step1 = self._step1()
        no_dir = step1[step1.index("条目没有目录来源"):]
        self.assertRegex(
            self.text,
            r"professor_dir.{0,80}(?:绝不|不).{0,40}(?:用户新增必填项|必填)",
        )
        self.assertRegex(no_dir, r"结构化.{0,30}自然语言")
        self.assertIn("逐请求", no_dir)
        self.assertRegex(
            no_dir,
            r"同名.{0,40}(?:歧义|无法唯一).{0,80}(?:只|对应请求)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
