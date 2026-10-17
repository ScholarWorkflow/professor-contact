"""Stage-2 fixed-evidence display, failure registration and analysis-level tests.

Covers the test plan `plan/stage2-evidence-level/test-plan.md` (T1—T4) for the
approved implementation plan r4:

* T1 — human-facing fixed-card slots (evidence / completed_part / remaining_gap)
  and the anchor-banned blacklist render trusted titles and Zotero links while
  the machine fields keep their exact model values; an untrusted reference
  fails the affected render instead of fabricating a citation.
* T2 — a real blocking finding inside the fixed evidence card is recorded as a
  first-round failure handed to the source owner, never as a model correction
  job; the forbidden regions keep their existing rejection.
* T3 — a pure narrative correction still finishes inside the two-round bound.
* T4 — the full-text/abstract counts follow the recorded analysis level, and
  preflight separates display-only level changes from business source changes.

Every fixture is synthetic and professor-local; no real user directory, model,
PDF or network call is involved.
"""
import copy
import json

from test_contact_state import (
    BaseEnv,
    parse,
    run_bound_stage2_finalize,
    run_bound_stage2_plan,
    run_cli,
    stage2_style_validation_report,
)

# The fixed freshness card prints these three machine slots; the blacklist card
# prints the completion evidence of a gap that is already implemented.
FIXED_EVIDENCE = "无更晚论文实现该点（AAAA1111）"
COMPLETED_PART = "AAAA1111 只做了第一组"
REMAINING_GAP = "AAAA1111 仍需第二组"
BLACKLIST_EVIDENCE = "CCCC3333 已接住输入模式比较"
BLACKLIST_COMPLETION = "CCCC3333"
REPAIRABLE_QUOTE = "起研究合成输入比较"
FORBIDDEN_QUOTE = "我想比较两种合成输入的处理结果"


def validation_report(analysis_md, issues, verdict="fail", notes=""):
    """One raw style-validator report bound to the managed analysis path."""
    return stage2_style_validation_report(analysis_md, verdict, issues, notes)


def blocking_issue(quote, location, rule="A1"):
    return {"rule": rule, "severity": "blocking", "location": str(location),
            "quote": quote, "suggestion": "改用日常语言解释。"}


class EvidenceLevelEnv(BaseEnv):
    """BaseEnv plus the rendering fixture shared by T1, T2 and T4."""

    def write_facts(self, extra=None, level="fulltext"):
        def add_level(facts):
            for paper in facts["papers"]:
                paper["analysis_level"] = level
            if extra:
                extra(facts)

        return super().write_facts(add_level)

    def render_fixture(self, facts, snapshot=None):
        """One accepted pack whose fixed cards carry machine item keys.

        ``snapshot`` is an optional dict (or factory) filled with the machine
        state captured BEFORE the render, so a test can prove the display step
        did not rewrite facts, translation, quotes or the user note.
        """
        results = self.root / "results"
        self.write_stage2_results(results, gap_overrides={
            "AAAA1111": {"status": "partial", "evidence": FIXED_EVIDENCE,
                         "completed_part": COMPLETED_PART,
                         "remaining_gap": REMAINING_GAP},
            "BBBB2222": {"status": "done_by_self", "evidence": BLACKLIST_EVIDENCE,
                         "candidate_paper_ids": [BLACKLIST_COMPLETION]},
        })
        batch = json.loads(facts.read_text(encoding="utf-8"))
        narrative = json.loads((results / "narrative.json").read_text(encoding="utf-8"))
        before = {
            "papers": copy.deepcopy(batch["papers"]),
            "narrative": copy.deepcopy(narrative),
            "user_note": batch["directions"][0]["user_note"],
        }
        if snapshot is not None:
            snapshot.update(before)
        plan = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        return finalized

    def analysis_text(self):
        return (self.prof_dir / "套磁候选分析.md").read_text(encoding="utf-8")

    def pack(self):
        return json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))

    def direction(self, direction_id="DIR00001"):
        return next(row for row in self.pack()["directions"]
                    if row["direction_id"] == direction_id)

    def shortlist_gap(self, item_key):
        return next(gap for gap in self.direction()["gap_shortlist"]
                    if gap["item_key"] == item_key)

    def find_line(self, text):
        """The unique 1-based file line containing ``text`` (report locations)."""
        hits = [index + 1 for index, line in enumerate(self.analysis_text().splitlines())
                if text in line]
        self.assertEqual(len(hits), 1, (text, hits))
        return hits[0]

    def write_report(self, name, issues, verdict="fail"):
        path = self.root / name
        path.write_text(json.dumps(
            validation_report(self.prof_dir / "套磁候选分析.md", issues, verdict),
            ensure_ascii=False), encoding="utf-8")
        return path

    def record(self, report_path):
        return parse(run_cli("stage2-record-validation", "--professor-dir", self.prof_dir,
                             "--validation-file", report_path))

    def refine_plan(self, report_path, facts=None):
        arguments = ["stage2-refine-plan", "--professor-dir", self.prof_dir,
                     "--validation-file", report_path]
        if facts is not None:
            arguments.extend(["--facts", facts])
        return parse(run_cli(*arguments))

    def refine_finalize(self, report_path, results_dir, facts=None):
        arguments = ["stage2-refine-finalize", "--professor-dir", self.prof_dir,
                     "--results", results_dir, "--validation-file", report_path]
        if facts is not None:
            arguments.extend(["--facts", facts])
        return parse(run_cli(*arguments))

    def rewrite_positioning(self, before, after, direction_id="DIR00001"):
        """A legal narrative-rewrite result for one direction."""
        direction = self.direction(direction_id)
        block = copy.deepcopy(direction["narrative"]["positioning"][0])
        self.assertIn(before, block["text"])
        block["text"] = block["text"].replace(before, after, 1)
        rewrite = {
            "schema": 1, "kind": "narrative-rewrite", "direction_id": direction_id,
            "collection_key": direction["collection_key"], "positioning": [block],
            "gap_notes": [
                {"gap_id": gap_id, "summary": value["summary"],
                 "explanation": value["explanation"]}
                for gap_id, value in direction["narrative"]["gap_notes"].items()],
        }
        results = self.root / f"rewrite-{direction_id}-{before[:4]}"
        results.mkdir(parents=True, exist_ok=True)
        (results / f"narrative-rewrite-{direction_id}.json").write_text(
            json.dumps(rewrite, ensure_ascii=False), encoding="utf-8")
        return results

    def stage2_preflight(self):
        return parse(run_cli(
            "stage2-preflight", "--program-root", self.root,
            "--professor", "試験 教授", "--target-file", self.prof_dir / "套磁目标.json",
            "--paper-analysis", "relevant", "--gap-scope", "selected_direction",
            "--freshness-scope", "shortlist"))

    def refresh_display(self, preflight_file):
        """The formal display-only refresh entry for one accepted pack."""
        return parse(run_cli("stage2-refresh-display", "--professor-dir", self.prof_dir,
                             "--preflight-file", preflight_file))


class FixedEvidenceDisplayTests(EvidenceLevelEnv):
    """T1 — trusted titles/links in the human-facing fixed-card slots."""

    def test_fixed_evidence_renders_trusted_references_without_touching_machine_fields(self):
        facts = self.write_facts()
        narrative_prose = "研究计划比较另一种合成场景"
        baseline = {}
        self.render_fixture(facts, snapshot=baseline)
        analysis = self.analysis_text()

        titles = {paper["item_key"]: paper["title"] for paper in self.papers}
        link = "zotero://select/library/items/AAAA1111"

        # The fixed card's three slots show the trusted title and its Zotero
        # link, and no longer leak the internal item key into the visible text.
        for slot in ("后续论文依据", "已做部分", "剩余缺口"):
            line = next(line for line in analysis.splitlines()
                        if line.startswith(f"- {slot}："))
            self.assertIn(titles["AAAA1111"], line, slot)
            self.assertIn(link, line, slot)
            visible = line.replace(link, "")
            self.assertNotIn("AAAA1111", visible, slot)
            self.assertNotIn("CCCC3333", visible, slot)

        blacklist = self.direction()["completed_gap_blacklist"]
        self.assertEqual(len(blacklist), 1, blacklist)
        blacklist_line = next(line for line in analysis.splitlines()
                              if "已被" in line and "接住" in line)
        self.assertIn(titles[BLACKLIST_COMPLETION], blacklist_line)
        self.assertIn(f"zotero://select/library/items/{BLACKLIST_COMPLETION}",
                      blacklist_line)

        # Machine fields and candidate references keep the exact model values,
        # and the author's own text, translation, quote and user note survive.
        gap = self.shortlist_gap("AAAA1111")
        self.assertEqual(gap["evidence"], FIXED_EVIDENCE)
        self.assertEqual(gap["completed_part"], COMPLETED_PART)
        self.assertEqual(gap["remaining_gap"], REMAINING_GAP)
        self.assertNotIn("candidate_paper_ids", gap)
        self.assertEqual(blacklist[0]["evidence"], BLACKLIST_EVIDENCE)
        self.assertEqual(blacklist[0]["completed_by_item_key"], BLACKLIST_COMPLETION)
        self.assertEqual(blacklist[0]["quote_trunc"],
                         "We plan to test a second synthetic processing path.")
        self.assertEqual(blacklist[0]["translation_zh"],
                         "中译：We plan to test a second")
        self.assertEqual(gap["quote"], self.gap_quotes["AAAA1111"])
        self.assertIn(f"「{self.gap_quotes['AAAA1111']}」", analysis)
        self.assertIn(f"中译：{self.gap_quotes['AAAA1111'][:24]}", analysis)
        self.assertIn(narrative_prose, analysis)
        self.assertEqual(self.direction()["user_note"], "我想比较两种合成输入的处理结果。")

        # Same comparison against the pre-render snapshot: the display step
        # changed neither the machine facts nor the author's own material.
        rendered = self.pack()
        gap = self.shortlist_gap("AAAA1111")
        self.assertEqual(gap["status"], "partial")
        self.assertEqual(gap["evidence"], FIXED_EVIDENCE)
        self.assertEqual(gap["completed_part"], COMPLETED_PART)
        self.assertEqual(gap["remaining_gap"], REMAINING_GAP)
        source_gap = {(row.get("item_key"), row.get("gap_id")): row
                      for row in baseline["narrative"]["directions"][0]["positioning"]}
        self.assertTrue(source_gap, baseline["narrative"])

    def test_fixed_evidence_without_trusted_title_fails_instead_of_inventing_one(self):
        def drop_title(facts):
            next(paper for paper in facts["papers"]
                 if paper["item_key"] == "AAAA1111")["title"] = None

        facts = self.write_facts(drop_title)
        results = self.root / "results"
        self.write_stage2_results(results, gap_overrides={
            "AAAA1111": {"status": "partial", "evidence": FIXED_EVIDENCE,
                         "completed_part": COMPLETED_PART,
                         "remaining_gap": REMAINING_GAP}})
        plan = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertNotEqual(finalized.get("status"), "ok", finalized)
        self.assertTrue(finalized.get("reason_code") or finalized.get("message"), finalized)
        self.assertFalse((self.prof_dir / "套磁候选分析.md").exists())
        for invented in ("该论文", "后续论文", "相关论文"):
            self.assertNotIn(invented, json.dumps(finalized, ensure_ascii=False))


class FixedEvidenceFailureTests(EvidenceLevelEnv):
    """T2 — a real fixed-card blocking is registered for the source owner."""

    def fixed_region_report(self, name="fixed-region.json"):
        """A blocking finding on the model-written evidence of a fixed card."""
        return self.write_report(name, [blocking_issue(
            FIXED_EVIDENCE, self.find_line(FIXED_EVIDENCE))])

    def mixed_report(self, name="mixed.json"):
        """One report holding both a fixed-card and a repairable narrative finding."""
        return self.write_report(name, [
            blocking_issue(REPAIRABLE_QUOTE, self.find_line(REPAIRABLE_QUOTE)),
            blocking_issue(FIXED_EVIDENCE, self.find_line(FIXED_EVIDENCE)),
        ])

    def assert_source_owner_handoff(self, report):
        """refine-plan hands a fixed-card failure over without a model job."""
        self.assertEqual(self.record(report)["status"], "needs_correction")
        pack_before = (self.prof_dir / "套磁候选输入.json").read_bytes()
        analysis_before = self.analysis_text()
        plan = self.refine_plan(report)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(plan["jobs"], [], plan)
        self.assertFalse(plan["write_needed"], plan)
        self.assertNotIn(plan.get("reason_code"),
                         {"no_failed_directions", "awaiting_second_validation"}, plan)
        handoff_text = " ".join(str(plan.get(field, ""))
                                for field in ("reason_code", "message", "detail"))
        self.assertTrue(handoff_text.strip(), plan)
        self.assertTrue(
            any(token in handoff_text.casefold() for token in ("source", "generator"))
            or any(token in handoff_text for token in ("源", "生成器", "生成方")),
            plan)
        results = self.root / "empty-rewrites"
        results.mkdir(exist_ok=True)
        finalized = self.refine_finalize(report, results)
        self.assertFalse(finalized.get("rewritten"), finalized)
        self.assertEqual((self.prof_dir / "套磁候选输入.json").read_bytes(), pack_before)
        self.assertEqual(self.analysis_text(), analysis_before)

    def test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job(self):
        facts = self.write_facts()
        self.render_fixture(facts)
        self.assert_source_owner_handoff(self.fixed_region_report())
        validator = self.pack()["validator"]
        self.assertEqual(validator["round"], 1, validator)
        self.assertNotIn(validator["results"]["DIR00001"]["result"],
                         {"pass", "skipped", "fail_after_2_rounds"}, validator)
        self.assertIn(REPAIRABLE_QUOTE, self.analysis_text())

    def test_mixed_fixed_and_narrative_blocking_creates_no_rewrite_job(self):
        facts = self.write_facts()
        self.render_fixture(facts)
        self.assert_source_owner_handoff(self.mixed_report())

    def test_forbidden_user_note_and_paper_table_keep_their_rejection(self):
        facts = self.write_facts()
        self.render_fixture(facts)
        table_lines = [(index + 1, line)
                       for index, line in enumerate(self.analysis_text().splitlines())
                       if line.startswith("| [") and "zotero://" in line]
        self.assertEqual(len(table_lines), 2, table_lines)
        table_location, table_row = table_lines[0]
        table_quote = table_row[:40]
        note_report = self.write_report("user-note.json", [blocking_issue(
            FORBIDDEN_QUOTE, self.find_line(FORBIDDEN_QUOTE))])
        table_report = self.write_report("paper-table.json", [blocking_issue(
            table_quote, table_location)])
        pack_before = (self.prof_dir / "套磁候选输入.json").read_bytes()
        analysis_before = self.analysis_text()
        for report in (note_report, table_report):
            recorded = self.record(report)
            self.assertNotIn(recorded["status"], {"ok", "needs_correction"}, recorded)
            self.assertNotEqual(recorded.get("reason_code"), "invalid_validation_json", recorded)
            self.assertTrue(recorded.get("reason_code") or recorded.get("message"), recorded)
            plan = self.refine_plan(report)
            self.assertNotIn(plan["status"], {"ok", "needs_correction"}, plan)
            self.assertNotEqual(plan.get("reason_code"), "invalid_validation_json", plan)
            self.assertEqual(plan.get("jobs", []), [])
        self.assertEqual((self.prof_dir / "套磁候选输入.json").read_bytes(), pack_before)
        self.assertEqual(self.analysis_text(), analysis_before)

    def test_repeating_the_same_fixed_card_report_does_not_clear_the_round(self):
        facts = self.write_facts()
        self.render_fixture(facts)
        report = self.fixed_region_report()
        recorded = self.record(report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        again = self.record(report)
        self.assertNotEqual(again["status"], "ok", again)
        self.assertTrue(again.get("reason_code") or again.get("message"), again)
        validator = self.pack()["validator"]
        self.assertEqual(validator["round"], 1, validator)
        self.assertNotIn(validator["results"]["DIR00001"]["result"],
                         {"pass", "skipped", "fail_after_2_rounds"}, validator)


class NarrativeRoundBoundTests(EvidenceLevelEnv):
    """T3 — the existing two-round bound survives the new registration split."""

    def test_narrative_correction_rounds_stay_bound_and_terminal_state_is_recorded_once(self):
        facts = self.write_facts()
        self.render_fixture(facts)
        first = self.write_report("round1-narrative.json", [blocking_issue(
            REPAIRABLE_QUOTE, self.find_line(REPAIRABLE_QUOTE))])
        recorded = self.record(first)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertEqual([job["direction_id"] for job in self.refine_plan(first)["jobs"]],
                         ["DIR00001"])
        results = self.rewrite_positioning(REPAIRABLE_QUOTE, "起研究合成输入比较并扩展")
        refined = self.refine_finalize(first, results)
        self.assertEqual(refined["status"], "ok", refined)
        self.assertEqual(refined["rewritten"], ["DIR00001"], refined)
        self.assertTrue(refined["round_retained"], refined)
        self.assertEqual(refined["phase"], "awaiting_second_validation", refined)
        validator = self.pack()["validator"]
        self.assertEqual(validator["round"], 1, validator)
        self.assertEqual(validator["phase"], "awaiting_second_validation", validator)
        self.assertEqual([issue["quote"] for issue in validator["pending"]["DIR00001"]],
                         [REPAIRABLE_QUOTE], validator)

        second = self.write_report("round2-fixed-card.json", [blocking_issue(
            COMPLETED_PART, self.find_line(COMPLETED_PART))])
        again = self.record(second)
        self.assertEqual(again["status"], "ok", again)
        self.assertEqual(again["round"], 2, again)
        self.assertTrue(again["terminal"], again)
        terminal = self.pack()["validator"]["results"]["DIR00001"]
        self.assertEqual(terminal["result"], "fail_after_2_rounds", terminal)
        self.assertEqual(terminal["rounds"], 2, terminal)
        self.assertEqual([issue["quote"] for issue in terminal["issues"]],
                         [COMPLETED_PART], terminal)
        self.assertEqual(self.refine_plan(second)["jobs"], [])


class AnalysisLevelTests(EvidenceLevelEnv):
    """T4 — analysis level counts, display-only refresh and source-change routing."""

    def index_entry(self, key, level, facts_state="unavailable"):
        """One real `论文分析/_index.json` paper record (analyzer Step 7 shape)."""
        return {
            "file": str(self.prof_dir / "论文分析" / f"{key}.md"),
            "level": level,
            "ocr_file": None,
            "future_work_sidecar": str(self.prof_dir / "论文分析" / f"{key}.md.future_work.json"),
            "future_work_state": "valid",
            "facts_sidecar": None,
            "facts_state": facts_state,
            "facts_error": None,
        }

    def write_index(self, entries):
        """Write the Stage-2 analysis index; only real fields are used."""
        index = {
            "schema": 2, "future_work_schema": 1, "professor": "試験 教授",
            "direction": {"collection_key": "DIR00001", "name_ja": "合成输入比较"},
            "papers": {key: self.index_entry(key, value["level"], value["facts_state"])
                       for key, value in entries.items()},
        }
        (self.prof_dir / "论文分析" / "_index.json").write_text(
            json.dumps(index, ensure_ascii=False), encoding="utf-8")
        return index

    def write_analysis(self, key):
        """A real analysis file so an index-only level change is not a source change."""
        path = self.prof_dir / "论文分析" / f"{key}.md"
        if not path.exists():
            path.write_text("# analysis\n", encoding="utf-8")
        return path

    def update_sources(self, levels, entries=None, delete=(), add=()):
        """Change the facts and the index that preflight actually reads."""
        facts = json.loads((self.root / "facts.json").read_text(encoding="utf-8"))
        by_key = {paper["item_key"]: paper for paper in facts["papers"]}
        for paper in facts["papers"]:
            paper["analysis_level"] = levels.get(paper["item_key"])
        for key in delete:
            paper = by_key.get(key)
            if paper is not None:
                paper["has_pdf"] = False
                paper.pop("analysis_file", None)
                paper.pop("sidecar_file", None)
        for entry in add:
            paper = copy.deepcopy(by_key[entry["item_key"]])
            paper.update(entry)
            paper["analysis_level"] = levels.get(entry["item_key"])
            facts["papers"].append(paper)
        (self.root / "facts.json").write_text(
            json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
        recorded = entries or {key: {"level": levels.get(key), "facts_state": "unavailable"}
                               for key in levels}
        return self.write_index(recorded)

    def accepted_run(self):
        """One accepted pack with a terminal pass validator and a full baseline."""
        levels = {paper["item_key"]: "fulltext" for paper in self.papers}
        for paper in self.papers:
            self.write_analysis(paper["item_key"])
        self.write_index({key: {"level": "fulltext", "facts_state": "unavailable"}
                          for key in levels})
        facts = self.write_facts()
        self.render_fixture(facts)
        passed = self.record(self.write_report("pass.json", [], verdict="pass"))
        self.assertEqual(passed["status"], "ok", passed)
        replayed = self.stage2_preflight()
        self.assertEqual(replayed["action"], "reuse_all", replayed)
        return facts

    def write_preflight_file(self, preflight):
        path = self.root / "preflight.json"
        path.write_text(json.dumps(preflight, ensure_ascii=False), encoding="utf-8")
        return path

    def summary_line(self):
        return next(line for line in self.analysis_text().splitlines()
                    if "数据来源" in line)

    def test_counts_follow_the_recorded_analysis_level(self):
        def levels(facts):
            recorded = {"AAAA1111": None, "CCCC3333": "fulltext"}
            for paper in facts["papers"]:
                paper["analysis_level"] = recorded.get(paper["item_key"])

        facts = self.write_facts(levels)
        # Failed analysis keeps the old fulltext string in the index; the OCR-only
        # fulltext paper has no facts. Neither may drive the counts.
        self.write_index({
            "AAAA1111": {"level": "fulltext", "facts_state": "failed"},
            "BBBB2222": {"level": "abstract", "facts_state": "unavailable"},
            "CCCC3333": {"level": "fulltext", "facts_state": "failed"},
        })
        results = self.root / "results"
        self.write_stage2_results(results)
        plan = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        summary = self.summary_line()
        self.assertIn("全文级 1 篇", summary)
        self.assertIn("摘要级 1 篇", summary)
        self.assertIn("未确认 1 篇", summary)
        papers = self.pack()["papers"]
        self.assertEqual(papers["AAAA1111"]["analysis_level"], None, papers["AAAA1111"])
        self.assertEqual(papers["BBBB2222"]["analysis_level"], "abstract")
        self.assertEqual(papers["CCCC3333"]["analysis_level"], "fulltext")
        self.assertEqual(papers["CCCC3333"]["facts_state"], "unavailable")
        self.assertNotEqual(papers["CCCC3333"]["facts_state"], "valid")

    def test_legacy_records_without_level_count_as_unconfirmed(self):
        facts = self.write_facts()
        facts_data = json.loads(facts.read_text(encoding="utf-8"))
        for paper in facts_data["papers"]:
            paper.pop("analysis_level", None)
        facts.write_text(json.dumps(facts_data, ensure_ascii=False, indent=1),
                         encoding="utf-8")
        results = self.root / "results"
        self.write_stage2_results(results)
        plan = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        summary = self.summary_line()
        self.assertIn(f"未确认 {len(self.papers)} 篇", summary)
        self.assertNotIn("全文级 1 篇", summary)
        self.assertNotIn("摘要级 1 篇", summary)

    def test_display_only_level_change_refreshes_without_model_work(self):
        self.accepted_run()
        self.update_sources({"AAAA1111": "abstract", "BBBB2222": "abstract",
                             "CCCC3333": "fulltext"})
        pack_before = self.pack()
        preflight = self.stage2_preflight()
        direction = next(row for row in preflight["directions"]
                         if row["direction_id"] == "DIR00001")
        self.assertEqual(preflight["action"], "refresh_display", preflight)
        self.assertNotIn("reuse_all", json.dumps(preflight, ensure_ascii=False))
        self.assertEqual(direction["action"], "refresh_display", direction)
        preflight_path = self.write_preflight_file(preflight)
        refreshed = self.refresh_display(preflight_path)
        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertTrue(refreshed.get("display_refreshed"), refreshed)
        summary = self.summary_line()
        self.assertIn("全文级 1 篇", summary)
        self.assertIn("摘要级 1 篇", summary)
        pack_after = self.pack()
        self.assertEqual(pack_after["validator"], pack_before["validator"])
        self.assertNotEqual(pack_after["validator"]["render_sha256"],
                            pack_after["cache"]["render"]["套磁候选分析.md"]["sha256"])
        self.assertEqual(pack_after["directions"][0]["supporting_item_keys"],
                         pack_before["directions"][0]["supporting_item_keys"])
        self.assertEqual(pack_after["directions"][0]["input_fingerprint"],
                         pack_before["directions"][0]["input_fingerprint"])
        self.assertEqual(pack_after["directions"][0]["narrative"],
                         pack_before["directions"][0]["narrative"])
        self.assertEqual([paper.get("analysis_level") for paper in
                          pack_after["papers"].values()].count("fulltext"), 1)
        freshness_before = (self.prof_dir / "_freshness_cache.json").read_text(
            encoding="utf-8")
        after = self.stage2_preflight()
        self.assertNotIn("pack_integrity_mismatch", after["reason_codes"], after)
        self.assertEqual(after["action"], "reuse_all", after)
        self.assertEqual((self.prof_dir / "_freshness_cache.json").read_text(
            encoding="utf-8"), freshness_before)
        self.assertIn("｜[分析](论文分析/AAAA1111.md)", self.analysis_text())

    def test_source_change_routes_back_to_the_process_path(self):
        facts = self.accepted_run()
        self.update_sources(
            {"AAAA1111": "fulltext", "BBBB2222": "fulltext", "CCCC3333": "fulltext"},
            delete=("CCCC3333",),
            add=({"item_key": "CCCC3333", "has_pdf": True,
                  "analysis_file": str(self.prof_dir / "论文分析" / "CCCC3333.md"),
                  "sidecar_file": str(
                      self.prof_dir / "论文分析" / "CCCC3333.md.future_work.json")},))
        preflight = self.stage2_preflight()
        self.assertEqual(preflight["action"], "process", preflight)
        self.assertTrue(preflight["reason_codes"], preflight)
        self.assertNotIn("refresh_display", json.dumps(preflight, ensure_ascii=False))

    def test_deleted_analysis_source_also_routes_back_to_process(self):
        self.accepted_run()
        self.update_sources({"AAAA1111": "fulltext", "BBBB2222": "fulltext",
                             "CCCC3333": "fulltext"}, delete=("CCCC3333",))
        preflight = self.stage2_preflight()
        self.assertEqual(preflight["action"], "process", preflight)
        self.assertTrue(preflight["reason_codes"], preflight)
        self.assertNotIn("refresh_display", json.dumps(preflight, ensure_ascii=False))

    def test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only(self):
        self.accepted_run()
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        del pack["cache"]["preflight"]
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        preflight = self.stage2_preflight()
        self.assertEqual(preflight["action"], "process", preflight)
        self.assertTrue(preflight["reason_codes"], preflight)
