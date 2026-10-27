"""TP1: only repairable Stage2 prose is style-checked, with a repair route.

Synthetic existing fixtures and public runner commands; no model/network calls.
"""
import copy
import json

from test_contact_state import contact_state, parse, run_cli
repair_support = __import__("test_stage2_source_evidence_repair")


class Stage2StyleRepairScopeTests(repair_support.SourceEvidenceRepairFixture):
    def scope(self):
        result = parse(run_cli("stage2-prepare-validation", "--professor-dir", self.prof_dir))
        self.assertEqual(result["status"], "ok", result)
        return result["analysis_scope"]

    def test_scope_contains_generated_prose_not_source_or_labels(self):
        self.generate_pack(self.gap_override())
        before = self.all_files_snapshot()
        scope = self.scope()
        self.assertEqual(self.all_files_snapshot(), before)
        fields = {row["field"] for row in scope["fragments"]}
        self.assertTrue({"positioning.text", "positioning.concrete_object",
                         "positioning.input_example", "positioning.output_example",
                         "summary", "explanation", "evidence", "blacklist_evidence",
                         "completed_part", "remaining_gap"} <= fields, fields)
        text = "\n".join(row["text"] for row in scope["fragments"])
        for forbidden in (self.gap_quotes["AAAA1111"], self.gap_quotes["BBBB2222"],
                          "Unrelated synthetic example", "Synthetic comparison of input patterns",
                          "- 中译：", "- 当前状态：", "- 后续论文依据："):
            self.assertNotIn(forbidden, text)
        lines = self.body_lines()
        for row in scope["fragments"]:
            self.assertEqual(lines[row["line"] - 1][row["start"]:row["end"]], row["text"])
        self.assertIn(self.gap_quotes["AAAA1111"], self.document()["body"])
        self.assertEqual(scope, self.scope())

    def test_source_and_label_style_reports_are_rejected_without_writes(self):
        self.generate_pack(self.gap_override())
        for index, (quote, prefix) in enumerate((
                ("Future work will extend", "- 作者原话："),
                ("- 中译：", "- 中译："),
                ("后续论文依据", "- 后续论文依据："),
                ("Unrelated synthetic example", "- 已做部分："))):
            with self.subTest(quote=quote):
                before = self.all_files_snapshot()
                report = self.write_report(f"outside-{index}.json", [
                    self.blocking_issue(quote, self.line_with(quote, prefix))])
                result = self.record(report)
                self.assertEqual(result.get("reason_code"), "validation_scope_mismatch", result)
                self.assertEqual(self.all_files_snapshot(), before)

    def test_mixed_label_prose_routes_only_the_real_repair_target(self):
        self.generate_pack(self.gap_override())
        quote = "大白话：研究计划比较另一种合成场景。"
        report = self.write_report("narrative-mixed.json", [
            self.blocking_issue(quote, self.physical_line(quote))])
        result = self.record(report)
        self.assertEqual(result["status"], "needs_correction", result)
        self.assertFalse(result["needs_owner_fix"], result)
        plan = self.refine_plan(report)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(len(plan["jobs"]), 1)

    def test_mixed_freshness_label_keeps_three_field_repair(self):
        self.generate_pack(self.gap_override())
        quote = "后续论文依据：后续由"
        report = self.write_report("freshness-mixed.json", [
            self.blocking_issue(quote, self.physical_line(quote))])
        result = self.record(report)
        self.assertTrue(result["needs_owner_fix"], result)
        owners = result["fixed_blocking"]["DIR00001"]
        self.assertEqual([(row["owner"], row["field"]) for row in owners],
                         [("source", "evidence")])
        gap = self.gap_id("AAAA1111")
        old = self.cache_entry(gap)["model_evidence"]
        outcome = self.repair([self.repair_row("model_evidence", old,
                                             old.replace("后续由", "后续工作由"))])
        self.assertEqual(outcome["status"], "needs_refresh", outcome)
        self.assertEqual(self.cache_entry(gap)["status"], "partial")

    def test_missing_explanation_and_optional_summary_can_be_added(self):
        self.generate_pack(self.gap_override(), narrative_mutate=lambda n:
                           n["directions"][0].update(gap_notes=[]))
        scope = self.scope()
        missing = [row for row in scope["fragments"] if row["missing"]]
        explanation = next(row for row in missing if row["field"] == "explanation")
        summary = next(row for row in missing if row["field"] == "summary")
        self.assertTrue(explanation["required"])
        self.assertFalse(summary["required"])
        before = self.direction_snapshot()
        cache_before = self.cache_path().read_bytes()
        issue = self.blocking_issue(explanation["text"], explanation["line"])
        issue["rule"] = "B5"
        report = self.write_report("missing.json", [issue])
        self.assertEqual(self.record(report)["status"], "needs_correction")
        plan = self.refine_plan(report)
        self.assertEqual(plan["status"], "ok", plan)
        job = plan["jobs"][0]
        rewrite = {"schema": 1, "kind": "narrative-rewrite",
                   "direction_id": job["direction_id"],
                   "positioning": copy.deepcopy(job["model_input"]["current_narrative"]["positioning"]),
                   "gap_notes": [{"gap_id": explanation["gap_id"],
                                  "summary": "比较第二种输入。",
                                  "explanation": "把另一组输入交给同一个程序，比较两次得到的结果。"}]}
        results = self.root / "scope-rewrite"
        results.mkdir()
        (results / job["result_file"]).write_text(json.dumps(rewrite, ensure_ascii=False), encoding="utf-8")
        outcome = self.refine_finalize(results, report)
        self.assertEqual(outcome["status"], "ok", outcome)
        after = self.direction_snapshot()
        for key in ("gaps", "blacklist", "supporting", "relevant", "named"):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(self.cache_path().read_bytes(), cache_before)
        self.assertIn("比较第二种输入。", self.document()["body"])
        passed = self.record(self.write_report("rechecked.json", []))
        self.assertEqual(passed["status"], "ok", passed)
        self.assertEqual(passed["round"], 2)

    def test_missing_or_stale_scope_is_not_recorded_as_pass(self):
        self.generate_pack(self.gap_override())
        for variant in ("missing", "stale"):
            before = self.all_files_snapshot()
            report = self.write_report(f"{variant}.json", [])
            data = json.loads(report.read_text())
            if variant == "missing":
                data["files"][0].pop("analysis_scope")
            else:
                data["files"][0]["analysis_scope"]["scope_sha256"] = "0" * 64
            report.write_text(json.dumps(data, ensure_ascii=False))
            result = self.record(report)
            self.assertEqual(result.get("reason_code"), "validation_scope_mismatch", result)
            self.assertEqual(self.all_files_snapshot(), before)

    def test_source_structure_report_routes_to_owner_not_prose_rewrite(self):
        self.generate_pack(self.gap_override())
        quote = "Synthetic comparison of input patterns"
        issue = self.blocking_issue(quote, self.line_with(quote, "| ["))
        issue["rule"] = "C8"
        report = self.write_report("structure.json", [issue])
        result = self.record(report)
        self.assertTrue(result.get("needs_owner_fix"), result)
        self.assertEqual(self.refine_plan(report)["status"], "needs_owner_fix")

    def test_old_scope_less_record_is_archived_once_on_normal_upgrade(self):
        facts, results, _proof = self.generate_pack(self.gap_override())
        self.record_pass("before-upgrade.json")
        pack = self.pack()
        pack["validator"].pop("analysis_scope")
        render = pack["cache"]["render"][contact_state.ANALYSIS_MD]
        render["u1"]["display_version"] = 3
        render["ownership"]["version"] = 1
        for fragment in render["ownership"]["fragments"]:
            for field in ("style_checkable", "missing", "required"):
                fragment.pop(field, None)
        # Simulate a legitimately accepted legacy snapshot, not corrupted binding.
        pack["validator"]["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
        self.write_pack(pack)
        body_before = self.document()["body"]
        cache_before = self.cache_path().read_bytes()
        _proof, preflight, _plan = self.refresh(facts)
        self.assertEqual(preflight["action"], "process", preflight)
        refreshed = parse(self.finalize_bound(facts, results))
        self.assertEqual(refreshed["status"], "ok", refreshed)
        upgraded = self.pack()
        self.assertNotIn("validator", upgraded)
        self.assertEqual(len(upgraded["validation_history"]), 1)
        self.assertEqual(upgraded["cache"]["render"][contact_state.ANALYSIS_MD]["ownership"]["version"], 2)
        self.assertEqual(self.document()["body"], body_before)
        self.assertEqual(self.cache_path().read_bytes(), cache_before)
        self.record_pass("new-scope-pass.json")
        active = copy.deepcopy(self.pack()["validator"])
        self.refresh(facts)
        repeated = parse(self.finalize_bound(facts, results))
        self.assertEqual(repeated["status"], "ok", repeated)
        current = self.pack()
        # Acceptance may update metadata; only its pack binding is recomputed.
        self.assertEqual(current["validator"]["pack_sha256"],
                         contact_state.stage2_pack_content_fingerprint(current))
        active["pack_sha256"] = current["validator"]["pack_sha256"]
        self.assertEqual(current["validator"], active)
        self.assertEqual(len(current["validation_history"]), 1)
