"""Tests for the Stage-2 raw style report handoff and one-round correction."""
import copy
import json
from pathlib import Path

from test_contact_state import (
    BaseEnv,
    parse,
    run_cli,
    stage2_style_validation_report,
)


class Stage2ValidationHandoffTests(BaseEnv):
    def write_validation(self, name, verdict="fail", quote="教授从", severity="blocking",
                         location=None):
        issues = []
        if quote:
            issues.append({
                "rule": "A1",
                "severity": severity,
                "location": location or quote,
                "quote": quote,
                "suggestion": "改用日常语言解释。",
            })
        report = stage2_style_validation_report(
            self.prof_dir / "套磁候选分析.md", verdict, issues)
        path = self.root / name
        path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        return path

    def record_validation(self, path):
        return parse(run_cli("stage2-record-validation", "--professor-dir", self.prof_dir,
                             "--validation-file", path))

    def assert_direction_not_accepted(self, direction_id):
        direction = self.stage2_preflight_direction(direction_id)
        self.assertIn("validator_not_accepted", direction["reason_codes"])

    def assert_no_accepted_validation(self, direction_id):
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        results = pack.get("validator", {}).get("results", {})
        record = results.get(direction_id, {})
        self.assertNotIn(record.get("result"), {"pass", "skipped"}, record)

    def rewrite_direction(self, direction_id, before, after):
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        direction = next(d for d in pack["directions"]
                         if d["direction_id"] == direction_id)
        narrative = direction["narrative"]
        block = copy.deepcopy(narrative["positioning"][0])
        self.assertIn(before, block["text"])
        block["text"] = block["text"].replace(before, after, 1)
        rewrite = {
            "schema": 1,
            "kind": "narrative-rewrite",
            "direction_id": direction_id,
            "collection_key": direction["collection_key"],
            "positioning": [block],
            "gap_notes": [
                {"gap_id": gap_id, "summary": value["summary"],
                 "explanation": value["explanation"]}
                for gap_id, value in narrative["gap_notes"].items()
            ],
        }
        results = self.root / f"rewrite-{direction_id}"
        results.mkdir()
        (results / f"narrative-rewrite-{direction_id}.json").write_text(
            json.dumps(rewrite, ensure_ascii=False), encoding="utf-8")
        return results

    def test_stage2_second_blocking_round_is_terminal(self):
        self.stage2_run()
        first = self.write_validation("first-round.json")
        recorded = self.record_validation(first)
        self.assertEqual(recorded["status"], "needs_correction", recorded)

        plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                             "--validation-file", first))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["DIR00001"])
        results = self.rewrite_direction("DIR00001", "教授从", "教授先从")
        finalized = parse(run_cli("stage2-refine-finalize", "--professor-dir", self.prof_dir,
                                  "--results", results, "--validation-file", first))
        self.assertEqual(finalized["status"], "ok", finalized)
        self.assert_direction_not_accepted("DIR00001")

        second = self.write_validation("second-round.json", quote="教授先从")
        recorded_again = self.record_validation(second)
        self.assertEqual(recorded_again["status"], "ok", recorded_again)
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        terminal = pack["validator"]["results"]["DIR00001"]
        self.assertEqual(terminal["result"], "fail_after_2_rounds")
        self.assertEqual(terminal["rounds"], 2)
        self.assert_direction_not_accepted("DIR00001")

        third_plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                                   "--validation-file", second))
        self.assertEqual(third_plan["status"], "ok", third_plan)
        self.assertEqual(third_plan["jobs"], [])

    def test_stage2_report_for_stale_render_is_rejected_without_pack_write(self):
        self.stage2_run()
        pack_path = self.prof_dir / "套磁候选输入.json"
        before = pack_path.read_bytes()
        analysis_path = self.prof_dir / "套磁候选分析.md"
        original_analysis = analysis_path.read_text(encoding="utf-8")

        wrong_target = self.write_validation("wrong-target.json", verdict="pass", quote=None)
        report_data = json.loads(wrong_target.read_text(encoding="utf-8"))
        report_data["files"][0]["file"] = str(self.prof_dir / "not-managed.md")
        wrong_target.write_text(json.dumps(report_data, ensure_ascii=False), encoding="utf-8")
        out = self.record_validation(wrong_target)
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assertTrue(out.get("reason_code") or out.get("message"), out)
        self.assertEqual(pack_path.read_bytes(), before)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), original_analysis)

        report = self.write_validation("stale-render.json", verdict="pass", quote=None)
        analysis_path.write_text(analysis_path.read_text(encoding="utf-8") +
                                "\n合成的人工修改。\n", encoding="utf-8")
        protected_analysis = analysis_path.read_text(encoding="utf-8")

        out = self.record_validation(report)
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assertTrue(out.get("reason_code") or out.get("message"), out)
        self.assertEqual(pack_path.read_bytes(), before)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), protected_analysis)

    def test_stage2_ambiguous_quote_does_not_create_a_correction_job(self):
        self.stage2_run_two_directions(unique_second_narrative=False)
        report = self.write_validation("ambiguous-quote.json")

        out = self.record_validation(report)
        self.assertNotIn(out["status"], {"ok", "needs_correction"}, out)
        self.assert_no_accepted_validation("DIR00001")
        self.assert_no_accepted_validation("DIR00002")
        plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                             "--validation-file", report))
        self.assertNotIn(plan["status"], {"ok", "needs_correction"}, plan)
        self.assertTrue(plan.get("reason_code") or plan.get("message"), plan)
        self.assertEqual(plan.get("jobs", []), [])

    def test_stage2_nonrepairable_user_note_does_not_create_a_correction_job(self):
        self.stage2_run()
        report = self.write_validation(
            "nonrepairable-note.json", quote="我想比较两种合成输入的处理结果",
            location="用户笔记（原文）")

        out = self.record_validation(report)
        self.assertNotIn(out["status"], {"ok", "needs_correction"}, out)
        self.assert_no_accepted_validation("DIR00001")
        plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                             "--validation-file", report))
        self.assertNotIn(plan["status"], {"ok", "needs_correction"}, plan)
        self.assertTrue(plan.get("reason_code") or plan.get("message"), plan)
        self.assertEqual(plan.get("jobs", []), [])

    def test_stage2_refinement_rejects_changed_input_pack(self):
        self.stage2_run()
        report = self.write_validation("changed-pack.json")
        recorded = self.record_validation(report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)

        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        pack["directions"][0]["user_note"] = "合成状态变更，不得沿用旧报告。"
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        before = pack_path.read_bytes()
        out = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                            "--validation-file", report))
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assertTrue(out.get("reason_code") or out.get("message"), out)
        self.assertEqual(out.get("jobs", []), [])
        self.assertEqual(pack_path.read_bytes(), before)

    def test_stage2_preflight_accepts_legacy_pass_and_skipped_records(self):
        self.stage2_run()
        pack_path = self.prof_dir / "套磁候选输入.json"
        target_path = self.prof_dir / "套磁目标.json"
        for result in ("pass", "skipped"):
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            pack["validator"] = {"results": {"DIR00001": {"result": result}}}
            pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
            preflight = parse(run_cli(
                "stage2-preflight", "--program-root", self.root,
                "--professor", "試験 教授", "--target-file", target_path,
                "--paper-analysis", "relevant", "--gap-scope", "selected_direction",
                "--freshness-scope", "shortlist"))
            self.assertEqual(preflight["status"], "ok", preflight)
            direction = next(row for row in preflight["directions"]
                             if row["direction_id"] == "DIR00001")
            self.assertNotIn("validator_not_accepted", direction["reason_codes"])

    def test_stage2_calling_docs_keep_the_raw_report_sequence(self):
        repo = Path(__file__).resolve().parents[4]
        codex_path = repo / "packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md"
        opencode_path = repo / "packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md"
        skill_path = repo / ".apm/skills/professor-contact/SKILL.md"

        def section(text, start_marker, end_marker):
            start = text.index(start_marker)
            end = text.index(end_marker, start)
            return text[start:end]

        def assert_order(owner, text, markers):
            cursor = 0
            for marker in markers:
                position = text.find(marker, cursor)
                self.assertGreaterEqual(position, 0, f"{owner}: {marker} 顺序缺失")
                cursor = position + len(marker)

        def assert_first_round_to_refinement(owner, text):
            assert_order(owner, text, ("原样", "stage2-record-validation", "needs_correction",
                                       "stage2-refine-plan", "stage2-refine-finalize"))
            record_at = text.index("stage2-record-validation")
            refine_at = text.index("stage2-refine-plan", record_at)
            condition = text[record_at:refine_at]
            self.assertTrue(
                any(marker in condition for marker in ("才", "仅当", "只有", "若")),
                f"{owner}: 修订入口未限定在 needs_correction 条件下")

        codex_text = codex_path.read_text(encoding="utf-8")
        codex_section = section(codex_text, "### Step 6.5 — 白话校验循环",
                                "### Step 7 — Return value")
        assert_first_round_to_refinement("Codex analyzer", codex_section)
        codex_after_finalize = codex_section.split("stage2-refine-finalize", 1)[1]
        assert_order("Codex second validation", codex_after_finalize,
                     ("subagent", "professor-contact-style-validator", "等待",
                      "stage2-record-validation", "停止"))

        opencode_text = opencode_path.read_text(encoding="utf-8")
        opencode_section = section(opencode_text, "### Step 6.5 — 白话校验循环",
                                   "### Step 7 — Return value")
        assert_first_round_to_refinement("OpenCode analyzer", opencode_section)
        opencode_after_finalize = opencode_section.split("stage2-refine-finalize", 1)[1]
        assert_order("OpenCode second validation", opencode_after_finalize,
                     ('task(subagent_type: "professor-contact-style-validator"', "等待",
                      "stage2-record-validation", "停止"))

        skill_text = skill_path.read_text(encoding="utf-8")
        skill_section = section(skill_text, "## 确定性 runner 与状态文件",
                                "## 阶段 5 — 套磁邮件")
        assert_first_round_to_refinement("professor-contact skill", skill_section)
        skill_after_finalize = skill_section.split("stage2-refine-finalize", 1)[1]
        assert_order("professor-contact skill second validation", skill_after_finalize,
                     ("professor-contact-style-validator", "stage2-record-validation", "停止"))

        validator = repo / ".apm/agents/professor-contact-style-validator.agent.md"
        self.assertIn("只报告不改写", validator.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import unittest
    unittest.main()
