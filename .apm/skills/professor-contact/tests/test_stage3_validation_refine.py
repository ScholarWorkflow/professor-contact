"""Regression coverage for the Stage-3 validator correction round."""
import copy
import json

from test_stage2_resolved_direction import run_cli, parse, write_json
from test_stage3_direction_groups import Stage3DirectionGroupBase, result_file


class Stage3ValidationRefineTests(Stage3DirectionGroupBase):
    def setUp(self):
        super().setUp()
        self.results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None]),
        })
        out = self.stage3_finalize(self.results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.validation = self.root / "stage3-style-validation.json"
        write_json(self.validation, {
            "result": "ok",
            "files": [{
                "file": str(self.prof_dir / "套磁想法候选.md"),
                "artifact": "candidates",
                "verdict": "fail",
                "blocking": 1,
                "minor": 0,
                "issues": [{
                    "rule": "B5", "severity": "blocking", "location": "第 20 行",
                    "quote": "流式输入", "suggestion": "首次出现时用日常语言解释。",
                }],
            }],
            "notes": "",
        })

    def refine_plan(self):
        return parse(run_cli(
            "stage3-plan", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--direction-id", "dir_A",
            "--validation-file", self.validation,
        ))

    def refine_finalize(self, results):
        return parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--direction-id", "dir_A",
            "--validation-file", self.validation, "--results", results,
        ))

    def test_validation_file_forces_one_correction_job_on_reusable_state(self):
        self.assertEqual(self.stage3_plan("--direction-id", "dir_A")["jobs"], [])
        plan = self.refine_plan()
        self.assertEqual(len(plan["jobs"]), 1)
        job = plan["jobs"][0]
        self.assertEqual(job["direction_id"], "dir_A")
        self.assertEqual(job["model_input"]["current_result"]["candidates"][0]["id"],
                         "dir_A_1")
        self.assertEqual(job["model_input"]["validator_issues"][0]["rule"], "B5")

    def test_correction_finalize_changes_text_only_and_clears_old_validation(self):
        state = self.load_state()
        state["validator"] = {"results": {"dir_A": {"result": "pass", "rounds": 1,
                                                       "issues": []}}}
        write_json(self.prof_dir / "套磁候选状态.json", state)
        before = next(d for d in state["directions"] if d["direction_id"] == "dir_A")
        corrected = self.generated_doc("dir_A", ["P1", "P2", None])
        corrected["candidates"][0]["research_question"] = (
            "数据持续到来时，方法还能否稳定收敛？这里的流式输入是指数据一条条到来。")
        results = self.write_results("refined", {"dir_A": corrected})
        out = self.refine_finalize(results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["corrected"], ["dir_A"])
        after_state = self.load_state()
        self.assertNotIn("validator", after_state)
        after = next(d for d in after_state["directions"] if d["direction_id"] == "dir_A")
        self.assertIn("一条条到来", after["candidates"][0]["research_question"])
        for old, new in zip(before["candidates"], after["candidates"]):
            for field in ("id", "kind", "direction_ids", "origin", "gap_refs",
                          "anchor_notes", "papers", "red_lines"):
                self.assertEqual(old.get(field), new.get(field), field)
        other_before = next(d for d in state["directions"] if d["direction_id"] == "dir_B")
        other_after = next(d for d in after_state["directions"] if d["direction_id"] == "dir_B")
        self.assertEqual(other_before, other_after)

    def test_correction_finalize_rejects_machine_fact_changes(self):
        corrected = self.generated_doc("dir_A", ["P1", "P2", None])
        corrected["candidates"][0]["gap_refs"] = []
        results = self.write_results("bad-refined", {"dir_A": corrected})
        payload = self.refine_finalize(results)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"],
                         "validation_correction_changed_machine_facts")

    def test_correction_rejects_validation_after_source_changes(self):
        self.rewrite_pack_fingerprint("dir_A", "changed-after-validation")
        payload = self.refine_plan()
        self.assertEqual(payload["status"], "needs_refresh")
        self.assertEqual(payload["reason_code"], "validation_source_changed")


if __name__ == "__main__":
    import unittest
    unittest.main()
