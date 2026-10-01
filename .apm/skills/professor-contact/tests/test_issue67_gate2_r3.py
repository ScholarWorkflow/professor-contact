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

    def test_explicit_selection_routes_requested_professors_before_formal_reads(self):
        self.assertIn(
            "bind each requested professor BEFORE any whole-project read", self.text
        )
        self.assertIn("先按原请求逐教授分流，再读任何教授正式文件", self.text)
        self.assertIn("只读取请求所涉及教授", self.text)
        self.assertIn("不得先执行全项目扫描", self.text)

    def test_reliable_professor_dir_does_not_require_unrelated_professor_state(self):
        self.assertIn("条目已带可靠 `professor_dir`", self.text)
        self.assertIn("无关教授的候选状态/输入包/身份/迁移状态都不是本教授的前置读取条件", self.text)
        self.assertIn("零读取、零写入", self.text)

    def test_no_dir_structured_and_natural_language_inputs_remain_supported_per_request(self):
        self.assertIn("`professor_dir` 绝不因此变成用户新增必填项", self.text)
        self.assertIn("结构化只报名字 / 自然语言", self.text)
        self.assertIn("逐请求", self.text)
        self.assertIn("同名多个目录是歧义", self.text)
        self.assertIn("只给该请求返回待补输入行", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
