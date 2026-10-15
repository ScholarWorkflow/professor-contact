"""Tests for the Stage-2 raw style report handoff and one-round correction."""
import copy
import json
from pathlib import Path

from test_contact_state import (
    BaseEnv,
    parse,
    run_bound_stage2_finalize,
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
        self.assertNotEqual(out.get("reason_code"), "invalid_validation_json", out)
        self.assertTrue(out.get("reason_code") or out.get("message"), out)
        self.assertEqual(pack_path.read_bytes(), before)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), original_analysis)

        report = self.write_validation("stale-render.json", verdict="pass", quote=None)
        analysis_path.write_text(analysis_path.read_text(encoding="utf-8") +
                                "\n合成的人工修改。\n", encoding="utf-8")
        protected_analysis = analysis_path.read_text(encoding="utf-8")

        out = self.record_validation(report)
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assertNotEqual(out.get("reason_code"), "invalid_validation_json", out)
        self.assertTrue(out.get("reason_code") or out.get("message"), out)
        self.assertEqual(pack_path.read_bytes(), before)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), protected_analysis)

    def test_stage2_nonrepairable_user_note_does_not_create_a_correction_job(self):
        facts = self.write_facts()
        results = self.root / "results"
        self.write_stage2_results(results)
        note_quote = "我想比较两种合成输入的处理结果"
        facts_data = json.loads(facts.read_text(encoding="utf-8"))
        next(paper for paper in facts_data["papers"]
             if paper["item_key"] == "AAAA1111")["title"] = note_quote
        facts.write_text(json.dumps(facts_data, ensure_ascii=False), encoding="utf-8")
        narrative_path = results / "narrative.json"
        narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
        narrative["directions"][0]["positioning"].append({
            "kind": "para", "text": note_quote, "refs": [],
            "concrete_object": "两种合成输入",
            "input_example": "输入两种固定的合成样本",
            "output_example": "比较两种处理结果",
        })
        narrative_path.write_text(json.dumps(narrative, ensure_ascii=False), encoding="utf-8")
        plan = parse(self.run_bound_stage2_plan(facts))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        pack_path = self.prof_dir / "套磁候选输入.json"
        analysis_path = self.prof_dir / "套磁候选分析.md"
        protected_pack = json.loads(pack_path.read_text(encoding="utf-8"))
        protected_directions = copy.deepcopy(protected_pack["directions"])
        protected_analysis = analysis_path.read_text(encoding="utf-8")
        note_line = protected_analysis.splitlines().index(f"> {note_quote}。") + 1
        citation_line = next(index + 1 for index, line in enumerate(protected_analysis.splitlines())
                             if note_quote in line and "zotero://" in line)
        reports = []
        for name, location in (("nonrepairable-note.json", note_line),
                               ("nonrepairable-citation.json", citation_line)):
            report = self.write_validation(name, quote=note_quote, location=str(location))
            out = self.record_validation(report)
            self.assertNotIn(out["status"], {"ok", "needs_correction"}, out)
            self.assertEqual(out.get("reason_code"), "validation_issue_not_repairable", out)
            self.assertTrue(out.get("reason_code") or out.get("message"), out)
            reports.append(report)
        pack_after_record = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(pack_after_record["directions"], protected_directions)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), protected_analysis)
        for report in reports:
            self.assert_no_accepted_validation("DIR00001")
            plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                                 "--validation-file", report))
            self.assertNotIn(plan["status"], {"ok", "needs_correction"}, plan)
            self.assertNotEqual(plan.get("reason_code"), "invalid_validation_json", plan)
            self.assertTrue(plan.get("reason_code") or plan.get("message"), plan)
            self.assertEqual(plan.get("jobs", []), [])
        pack_after_plan = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(pack_after_plan["directions"], protected_directions)
        self.assertEqual(analysis_path.read_text(encoding="utf-8"), protected_analysis)

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
        self.assertNotEqual(out.get("reason_code"), "invalid_validation_json", out)
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

if __name__ == "__main__":
    import unittest
    unittest.main()
