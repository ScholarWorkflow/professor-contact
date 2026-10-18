"""Stage-2 fixed-evidence display, failure registration and analysis-level tests.

Covers the unique test plan `plan/stage2-evidence-level/test-plan.md` (T1—T4):

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
import contextlib
import copy
import hashlib
import io
import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import test_stage2_resolved_direction as resolved_pipeline_tests
from test_contact_state import (
    BaseEnv,
    contact_state,
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
# A NON-empty machine candidate list (package paper, not the gap paper itself):
# the display step must carry it verbatim.
FIXED_CANDIDATES = ("CCCC3333",)
REPAIRABLE_QUOTE = "起研究合成输入比较"
# T1 replaces the item key inside the fixed-card text with the trusted title and
# link, so the T2/T3 report quotes must not contain the key itself.
FIXED_EVIDENCE_QUOTE = "无更晚论文实现该点"
COMPLETED_PART_QUOTE = "只做了第一组"
# Structured signals the product may report when the current business year no
# longer matches the year one preflight was decided for. The year is part of the
# cheap preflight inputs, so the existing generic drift code is accepted next to
# the formal reason code and any dedicated year code; the human-readable message
# is never matched.
YEAR_MISMATCH_SIGNALS = ("params_changed", "preflight_inputs_changed",
                         "current_year_changed", "year_changed")


def managed_body(rendered: str) -> str:
    """The managed Markdown body below the frontmatter, exactly as hashed."""
    _header, body = contact_state.split_frontmatter(rendered)
    return body


def papers_of(pack: dict) -> dict:
    """Canonical paper records without the display-only analysis level."""
    return {key: {field: value for field, value in paper.items()
                  if field != "analysis_level"}
            for key, paper in pack["papers"].items()}


def validation_report(analysis_md, issues, verdict="fail", notes=""):
    """One raw style-validator report bound to the managed analysis path."""
    return stage2_style_validation_report(analysis_md, verdict, issues, notes)


def blocking_issue(quote, location, rule="A1"):
    return {"rule": rule, "severity": "blocking", "location": str(location),
            "quote": quote, "suggestion": "改用日常语言解释。"}


class EvidenceLevelEnv(BaseEnv):
    """BaseEnv plus the rendering fixture shared by T1, T2 and T4."""

    def write_facts(self, *extras, level="fulltext"):
        """Base facts with an analysis level, then every caller extra in order."""
        def add_level(facts):
            for paper in facts["papers"]:
                paper["analysis_level"] = level
            for extra in extras:
                extra(facts)

        return super().write_facts(add_level)

    def render_fixture(self, facts, snapshot=None, evidence=FIXED_EVIDENCE):
        """One accepted pack whose fixed cards carry machine item keys.

        ``snapshot`` is an optional dict (or factory) filled with the machine
        state captured BEFORE the render, so a test can prove the display step
        did not rewrite facts, translation, quotes or the user note. ``evidence``
        is the machine evidence text of the fixed card under test: the default
        keeps the shared constant, and one call may pass a mixed key/link/number
        input without changing the constant T2/T3 quote from.
        """
        results = self.root / "results"
        self.write_stage2_results(results, gap_overrides={
            "AAAA1111": {"status": "partial", "evidence": evidence,
                         "completed_part": COMPLETED_PART,
                         "remaining_gap": REMAINING_GAP,
                         "candidate_paper_ids": list(FIXED_CANDIDATES)},
            "BBBB2222": {"status": "done_by_self", "evidence": BLACKLIST_EVIDENCE,
                         "candidate_paper_ids": [BLACKLIST_COMPLETION]},
        })
        batch = json.loads(facts.read_text(encoding="utf-8"))
        narrative = json.loads((results / "narrative.json").read_text(encoding="utf-8"))
        statuses = json.loads((results / "freshness-DIR00001.json").read_text(
            encoding="utf-8"))["results"]
        gap_id = next(row["gap_id"] for row in statuses
                      if row.get("evidence") == evidence)
        candidate_row = next(row for row in statuses
                             if row["gap_id"] == gap_id)
        self.assertEqual(candidate_row["candidate_paper_ids"],
                         list(FIXED_CANDIDATES),
                         "the pre-render fixture really carries candidate references")
        self.assertEqual(candidate_row["evidence"], evidence,
                         "the pre-render fixture really carries the fixed evidence text")
        self.assertEqual(candidate_row["completed_part"], COMPLETED_PART)
        self.assertEqual(candidate_row["remaining_gap"], REMAINING_GAP)
        self.assertEqual(batch["directions"][0]["user_note"],
                         "我想比较两种合成输入的处理结果。",
                         "the pre-render fixture really carries the user note")
        before = {
            "papers": copy.deepcopy(batch["papers"]),
            "narrative": copy.deepcopy(narrative),
            "user_note": batch["directions"][0]["user_note"],
            "gap_id": candidate_row["gap_id"],
            "candidate_paper_ids": list(candidate_row["candidate_paper_ids"]),
            "evidence": candidate_row["evidence"],
            "completed_part": candidate_row.get("completed_part"),
            "remaining_gap": candidate_row.get("remaining_gap"),
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
        # One representative mixed input: a bare key, an ALREADY correct link
        # and two ordinary eight-digit numbers in the same machine evidence.
        title = next(paper["title"] for paper in self.papers
                     if paper["item_key"] == "AAAA1111")
        link_text = f"[{title}](zotero://select/library/items/AAAA1111)"
        mixed_evidence = ("无更晚论文实现该点（AAAA1111）；已有引用：" + link_text
                          + "；日期 20261018；样本数 12345678")
        baseline = {}
        self.render_fixture(facts, snapshot=baseline, evidence=mixed_evidence)
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

        # The mixed evidence line converts exactly the bare key: the correct
        # link that was already there survives unchanged, and the two ordinary
        # eight-digit numbers stay ordinary text instead of becoming citations.
        evidence_line = next(line for line in analysis.splitlines()
                             if line.startswith("- 后续论文依据："))
        self.assertEqual(evidence_line.count(link_text), 2, evidence_line)
        self.assertEqual(evidence_line.count(link), 2, evidence_line)
        self.assertIn("20261018", evidence_line)
        self.assertIn("12345678", evidence_line)
        remainder = evidence_line.replace(link_text, "")
        self.assertNotIn("AAAA1111", remainder)
        self.assertNotIn("zotero://", remainder)
        for fragment in ("[", "]", "(", ")"):
            self.assertNotIn(fragment, remainder, (fragment, remainder))

        blacklist = self.direction()["completed_gap_blacklist"]
        self.assertEqual(len(blacklist), 1, blacklist)
        blacklist_line = next(line for line in analysis.splitlines()
                              if "已被" in line and "接住" in line)
        self.assertIn(titles[BLACKLIST_COMPLETION], blacklist_line)
        self.assertIn(f"zotero://select/library/items/{BLACKLIST_COMPLETION}",
                      blacklist_line)
        self.assertNotIn(BLACKLIST_COMPLETION, blacklist_line.replace(
            f"zotero://select/library/items/{BLACKLIST_COMPLETION}", ""))

        # Machine fields and candidate references keep the exact model values,
        # and the author's own text, translation, quote and user note survive.
        gap = self.shortlist_gap("AAAA1111")
        self.assertEqual(gap["gap_id"], baseline["gap_id"])
        self.assertEqual(gap["evidence"], baseline["evidence"],
                         "the raw evidence text must survive the display step")
        self.assertEqual(gap["completed_part"], baseline["completed_part"])
        self.assertEqual(gap["remaining_gap"], baseline["remaining_gap"])
        self.assertEqual(gap["candidate_paper_ids"], list(FIXED_CANDIDATES),
                         "candidate references must survive the display step")
        self.assertEqual(blacklist[0]["evidence"], BLACKLIST_EVIDENCE)
        self.assertEqual(blacklist[0]["completed_by_item_key"], BLACKLIST_COMPLETION)
        self.assertEqual(blacklist[0]["quote_trunc"],
                         "We plan to test a second synthetic processing path.")
        self.assertEqual(blacklist[0]["translation_zh"],
                         "中译：We plan to test a second")
        self.assertEqual(gap["quote"], self.gap_quotes["AAAA1111"])
        self.assertIn(f"「{self.gap_quotes['AAAA1111']}」", analysis)
        self.assertIn(f"- 中译：{gap['translation_zh']}", analysis,
                      "the stored translation must be displayed verbatim")
        self.assertIn(narrative_prose, analysis)
        self.assertEqual(self.direction()["user_note"], baseline["user_note"])

        # Same comparison against the pre-render snapshot: the display step
        # changed neither the machine facts nor the author's own material.
        accepted = self.direction()
        self.assertEqual(gap["status"], "partial")
        source_positioning = baseline["narrative"]["directions"][0]["positioning"]
        self.assertEqual([row["text"] for row in source_positioning],
                         [row["text"] for row in accepted["narrative"]["positioning"]])
        baseline_notes = {row["gap_id"]: {"summary": row["summary"],
                                          "explanation": row["explanation"]}
                          for row in baseline["narrative"]["directions"][0]["gap_notes"]}
        self.assertEqual(baseline_notes, accepted["narrative"]["gap_notes"],
                         "the display step must not rewrite the narrative gap notes")
        self.assertEqual(baseline["user_note"], accepted["user_note"])
        self.assertEqual(baseline["narrative"]["directions"][0]["collection_key"],
                         accepted["collection_key"])

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
        # Only the fixed card may still name the untitled AAAA1111: the narrative
        # reference moves to the paper that keeps a trusted title, with its refs
        # kept consistent, so a failure here proves the fixed-slot protection
        # instead of an unrelated narrative reference.
        narrative_path = results / "narrative.json"
        narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
        for block in narrative["directions"][0]["positioning"]:
            block["text"] = block["text"].replace("{{P:AAAA1111}}", "{{P:BBBB2222}}")
            block["refs"] = [ref.replace("paper:AAAA1111", "paper:BBBB2222")
                             for ref in block["refs"]]
        narrative_path.write_text(json.dumps(narrative, ensure_ascii=False),
                                  encoding="utf-8")
        # Preconditions of the scenario, read from the very inputs that run:
        # AAAA1111 has no trusted title anywhere, BBBB2222 has one and is the
        # paper the narrative cites, and this fresh professor directory has no
        # accepted pack or persisted display reference that could backfill it.
        recorded = {paper["item_key"]: paper.get("title") for paper in json.loads(
            facts.read_text(encoding="utf-8"))["papers"]}
        self.assertIsNone(recorded["AAAA1111"])
        self.assertEqual(recorded["BBBB2222"], next(
            paper["title"] for paper in self.papers
            if paper["item_key"] == "BBBB2222"))
        block = narrative["directions"][0]["positioning"][0]
        self.assertIn("{{P:BBBB2222}}", block["text"])
        self.assertIn("paper:BBBB2222", block["refs"])
        self.assertNotIn("paper:AAAA1111", block["refs"])
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())
        plan = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertNotEqual(finalized.get("status"), "ok", finalized)
        self.assertEqual(finalized.get("reason_code"),
                         "missing_fixed_evidence_title", finalized)
        self.assertEqual(finalized.get("item_key"), "AAAA1111", finalized)
        self.assertFalse((self.prof_dir / "套磁候选分析.md").exists())

        # The blacklist's completion-paper link is a separate render branch.
        # Use a separate professor fixture: the fixed card keeps valid titles,
        # while only the completed paper referenced by the blacklist lacks one.
        completion_env = self.__class__(self._testMethodName)
        completion_env.setUp()
        try:
            def drop_completion_title(facts):
                next(paper for paper in facts["papers"]
                     if paper["item_key"] == BLACKLIST_COMPLETION)["title"] = None

            completion_facts = completion_env.write_facts(drop_completion_title)
            completion_results = completion_env.root / "completion-results"
            completion_env.write_stage2_results(completion_results, gap_overrides={
                "AAAA1111": {"status": "partial", "evidence": FIXED_EVIDENCE,
                             "completed_part": COMPLETED_PART,
                             "remaining_gap": REMAINING_GAP},
                "BBBB2222": {"status": "done_by_self",
                             "evidence": "该延伸点已经由另一篇论文完成",
                             "candidate_paper_ids": [BLACKLIST_COMPLETION]},
            })
            completion_plan = parse(run_bound_stage2_plan(run_cli, completion_facts))
            self.assertEqual(completion_plan["status"], "ok", completion_plan)
            completion_finalized = parse(run_bound_stage2_finalize(
                run_cli, completion_facts, "--results", completion_results))
            self.assertEqual(completion_finalized.get("reason_code"),
                             "missing_fixed_evidence_title", completion_finalized)
            self.assertEqual(completion_finalized.get("item_key"),
                             BLACKLIST_COMPLETION, completion_finalized)
            self.assertFalse((completion_env.prof_dir / "套磁候选分析.md").exists())
        finally:
            completion_env.tearDown()


class FixedEvidenceFailureTests(EvidenceLevelEnv):
    """T2 — a real fixed-card blocking is registered for the source owner."""

    def fixed_region_report(self, name="fixed-region.json"):
        """A blocking finding on the model-written evidence of a fixed card."""
        return self.write_report(name, [blocking_issue(
            FIXED_EVIDENCE_QUOTE, self.find_line(FIXED_EVIDENCE_QUOTE))])

    def mixed_report(self, name="mixed.json"):
        """One report holding both a fixed-card and a repairable narrative finding."""
        return self.write_report(name, [
            blocking_issue(REPAIRABLE_QUOTE, self.find_line(REPAIRABLE_QUOTE)),
            blocking_issue(FIXED_EVIDENCE_QUOTE, self.find_line(FIXED_EVIDENCE_QUOTE)),
        ])

    def assert_source_owner_handoff(self, report):
        """refine-plan hands a fixed-card failure over without a model job."""
        report_before = report.read_bytes()
        self.assertEqual(self.record(report)["status"], "needs_correction")
        analysis_before = self.analysis_text()
        pack_before = (self.prof_dir / "套磁候选输入.json").read_bytes()
        plan = self.refine_plan(report)
        self.assertEqual(plan.get("jobs"), [], plan)
        self.assertFalse(plan.get("write_needed"), plan)
        self.assertNotIn(plan.get("reason_code"),
                         {"no_failed_directions", "awaiting_second_validation"}, plan)
        # Check owner and required action together, without mandating that
        # the business handoff serialize both into one particular field.
        owners = ("source", "generator", "源", "生成器", "生成方", "数据准备")
        actions = ("fix", "repair", "regenerate", "修复", "修正", "重新生成",
                   "重做", "处理", "补齐")
        details = " ".join(str(plan.get(field, ""))
                           for field in ("reason_code", "message", "detail"))
        self.assertTrue(any(owner in details.casefold() for owner in owners), plan)
        self.assertTrue(any(action in details.casefold() for action in actions), plan)
        results = self.root / "empty-rewrites"
        results.mkdir(exist_ok=True)
        finalized = self.refine_finalize(report, results)
        self.assertFalse(finalized.get("rewritten"), finalized)
        self.assertEqual((self.prof_dir / "套磁候选输入.json").read_bytes(), pack_before,
                         "refine-finalize must not write the input pack")
        self.assertEqual(self.analysis_text(), analysis_before)
        self.assertEqual(report.read_bytes(), report_before,
                         "the raw validator report must stay unchanged")
        validator = self.pack()["validator"]
        self.assertNotIn(validator["results"]["DIR00001"]["result"],
                         {"pass", "skipped", "fail_after_2_rounds"}, validator)

    def test_fixed_card_blocking_is_recorded_for_the_source_owner_without_a_model_job(self):
        facts = self.write_facts()
        self.render_fixture(facts)
        first_report = self.fixed_region_report()
        original_report = first_report.read_bytes()
        self.assert_source_owner_handoff(first_report)
        validator = self.pack()["validator"]
        self.assertEqual(validator["round"], 1, validator)
        self.assertIn(REPAIRABLE_QUOTE, self.analysis_text())

        # A real source correction is followed by the ordinary Stage-2 path,
        # not narrative refine. The old failure cannot approve the new body.
        old_body = managed_body(self.analysis_text())
        facts_data = json.loads(facts.read_text(encoding="utf-8"))
        next(paper for paper in facts_data["papers"] if paper["item_key"] == "AAAA1111")[
            "title"] = "Synthetic comparison of input patterns (corrected)"
        facts.write_text(json.dumps(facts_data, ensure_ascii=False), encoding="utf-8")
        corrected_results = self.root / "corrected-results"
        self.write_stage2_results(corrected_results, gap_overrides={
            "AAAA1111": {"status": "partial",
                         "evidence": "核对后确认第二组比较仍待完成（AAAA1111）",
                         "completed_part": COMPLETED_PART,
                         "remaining_gap": REMAINING_GAP},
            "BBBB2222": {"status": "done_by_self", "evidence": BLACKLIST_EVIDENCE,
                         "candidate_paper_ids": [BLACKLIST_COMPLETION]},
        })
        # The source owner re-judged this gap's evidence: drop the cached
        # freshness decision so the ordinary Stage-2 run must consume the
        # corrected results file instead of reusing the old status.
        freshness_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
        del freshness["entries"][self.shortlist_gap("AAAA1111")["gap_id"]]
        freshness_path.write_text(json.dumps(freshness, ensure_ascii=False),
                                  encoding="utf-8")
        new_plan = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(new_plan["status"], "ok", new_plan)
        rebuilt = parse(run_bound_stage2_finalize(
            run_cli, facts, "--results", corrected_results))
        self.assertEqual(rebuilt["status"], "ok", rebuilt)
        self.assertNotEqual(managed_body(self.analysis_text()), old_body)
        self.assertIn("核对后确认第二组比较仍待完成", self.analysis_text())
        self.assertNotIn(FIXED_EVIDENCE_QUOTE, self.analysis_text())
        preflight = self.stage2_preflight()
        row = next(row for row in preflight["directions"]
                   if row["direction_id"] == "DIR00001")
        self.assertIn("validator_not_accepted", row["reason_codes"], row)

        # A new validation report must be recorded against the newly generated
        # body before the repaired source can be accepted. Old failure evidence
        # remains untouched and cannot act as the new PASS.
        new_report = self.write_report("corrected-pass.json", [], verdict="pass")
        self.assertNotEqual(new_report.read_bytes(), original_report)
        passed = self.record(new_report)
        self.assertEqual(passed["status"], "ok", passed)
        self.assertEqual(passed["round"], 1, passed)
        recorded = self.pack()["validator"]
        self.assertEqual(recorded["results"]["DIR00001"]["result"], "pass", recorded)
        self.assertEqual(first_report.read_bytes(), original_report)
        checked = self.stage2_preflight()
        checked_row = next(row for row in checked["directions"]
                           if row["direction_id"] == "DIR00001")
        self.assertNotIn("validator_not_accepted", checked_row["reason_codes"],
                         checked_row)

    def test_mixed_fixed_and_narrative_blocking_creates_no_rewrite_job(self):
        facts = self.write_facts()
        self.render_fixture(facts)
        self.assert_source_owner_handoff(self.mixed_report())

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
            COMPLETED_PART_QUOTE, self.find_line(COMPLETED_PART_QUOTE))])
        again = self.record(second)
        self.assertEqual(again["status"], "ok", again)
        self.assertEqual(again["round"], 2, again)
        self.assertTrue(again["terminal"], again)
        terminal = self.pack()["validator"]["results"]["DIR00001"]
        self.assertEqual(terminal["result"], "fail_after_2_rounds", terminal)
        self.assertEqual(terminal["rounds"], 2, terminal)
        self.assertEqual([issue["quote"] for issue in terminal["issues"]],
                         [COMPLETED_PART_QUOTE], terminal)
        self.assertEqual(self.refine_plan(second)["jobs"], [])


class AnalysisLevelTests(EvidenceLevelEnv):
    """T4 — analysis level counts, display-only refresh and source-change routing."""

    def index_entry(self, key, level, facts_state="unavailable", ocr=False,
                    analysis=None, facts=None):
        """One real `论文分析/_index.json` paper record (analyzer Step 7 shape).

        The recorded state follows the analyzer's own rules: a paper with a
        valid future-work sidecar records ``valid`` + its path, while an OCR-only
        paper records ``failed`` + the without-PDF reason and no sidecar path.
        """
        analysis_path = analysis or self.prof_dir / "论文分析" / f"{key}.md"
        sidecar = Path(str(analysis_path) + ".future_work.json")
        if ocr:
            future_state, future_error, sidecar_path = (
                "failed", "future_work_unavailable_without_pdf_handoff", None)
        else:
            future_state, future_error, sidecar_path = "valid", None, str(sidecar)
        facts_error = None
        if facts_state != "valid":
            facts_error = ("facts_unavailable_without_pdf_handoff" if ocr
                           else "missing_facts_sidecar")
        return {
            "file": str(analysis_path),
            "level": level,
            "ocr_file": (str(self.ocr_path(key)) if ocr else None),
            "future_work_sidecar": sidecar_path,
            "future_work_state": future_state,
            "future_work_error": future_error,
            "facts_sidecar": facts,
            "facts_state": facts_state,
            "facts_error": facts_error,
        }

    def ocr_path(self, key):
        return self.prof_dir / "论文分析" / "_ocr" / f"{key}.txt"

    def write_future_work_sidecar(self, key, analysis=None):
        """The declared `valid` future-work sidecar must really exist."""
        analysis = analysis or self.prof_dir / "论文分析" / f"{key}.md"
        sidecar = Path(str(analysis) + ".future_work.json")
        if not sidecar.exists():
            sidecar.write_text(json.dumps({
                "schema": 1, "extractor_version": "future-work-v1",
                "analysis": analysis.name, "status": "ok", "items": [
                    {"id": f"fw-{key}", "quote": self.gap_quotes["AAAA1111"],
                     "translation_zh": "中译：合成证据", "source": "Conclusion",
                     "page": 8}],
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        return sidecar

    def write_index(self, entries):
        """Write the Stage-2 analysis index; the caller controls every field."""
        index = {
            "schema": 2, "future_work_schema": 1, "professor": "試験 教授",
            "direction": {"collection_key": "DIR00001", "name_ja": "合成输入比较"},
            "papers": {key: self.index_entry(
                key, value.get("level"), value.get("facts_state", "unavailable"),
                value.get("ocr", False), value.get("analysis"), value.get("facts"))
                for key, value in entries.items()},
        }
        (self.prof_dir / "论文分析" / "_index.json").write_text(
            json.dumps(index, ensure_ascii=False), encoding="utf-8")
        return index

    def write_analysis(self, key, ocr=False):
        """A real analysis file so an index-only level change is not a source change."""
        path = self.prof_dir / "论文分析" / f"{key}.md"
        if not path.exists():
            path.write_text("# analysis\n", encoding="utf-8")
        if ocr:
            ocr_path = self.ocr_path(key)
            ocr_path.parent.mkdir(parents=True, exist_ok=True)
            ocr_path.write_text("synthetic OCR text\n", encoding="utf-8")
        return path

    def remove_analysis(self, key):
        path = self.prof_dir / "论文分析" / f"{key}.md"
        if path.exists():
            path.unlink()
        return path

    def update_sources(self, levels, entries, delete=(), add=()):
        """Change the facts, the index and the artifact files preflight can see.

        ``delete`` removes the key from the facts catalog and the index and
        deletes its analysis file; ``add`` REPLACES that key's facts record with
        the given one (used to make a previously missing source appear with its
        real artifact paths).

        Existing artifact files are never rewritten here: a display-only refresh
        must keep every guard byte-identical, so the OCR carrier is only declared
        through the index entry (``ocr`` in ``entries``), not re-created.
        """
        facts = json.loads((self.root / "facts.json").read_text(encoding="utf-8"))
        for key in delete:
            self.remove_analysis(key)
        facts["papers"] = [paper for paper in facts["papers"]
                           if paper["item_key"] not in set(delete)]
        for entry in add:
            previous = next((paper for paper in facts["papers"]
                             if paper["item_key"] == entry["item_key"]), None)
            merged = copy.deepcopy(previous) if previous else {}
            merged.update(copy.deepcopy(entry))
            facts["papers"] = [paper for paper in facts["papers"]
                               if paper["item_key"] != entry["item_key"]]
            facts["papers"].append(merged)
        for paper in facts["papers"]:
            paper["analysis_level"] = levels.get(paper["item_key"])
        (self.root / "facts.json").write_text(
            json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
        return self.write_index(entries)

    def accepted_run(self, level="fulltext", indexed=("AAAA1111", "BBBB2222", "CCCC3333"),
                     ocr_only=(), facts_extra=None):
        """One accepted pack with a terminal pass validator and a full baseline.

        ``indexed`` names the papers the accepted baseline records with an
        analysis artifact; keys outside it have no index record and no file, so a
        later appearance is a genuinely new source. ``ocr_only`` names the keys
        that already own an OCR carrier file and index path in that baseline.
        """
        for key in indexed:
            self.write_analysis(key)
        entries = {}
        for key in indexed:
            entries[key] = {"level": level, "facts_state": "unavailable",
                            "ocr": key in ocr_only}
            if key in ocr_only:
                self.write_analysis(key, ocr=True)
            else:
                self.write_future_work_sidecar(key)
        self.write_index(entries)
        facts = self.write_facts(facts_extra) if facts_extra else self.write_facts()
        self.render_fixture(facts)
        passed = self.record(self.write_report("pass.json", [], verdict="pass"))
        self.assertEqual(passed["status"], "ok", passed)
        replayed = self.stage2_preflight()
        self.assertEqual(replayed["action"], "reuse_all", replayed)
        return facts

    def declare_analysis(self, key, analysis, level, facts_state="unavailable",
                         ocr=False):
        """Make one index entry match the artifacts really on disk."""
        entry = {"level": level, "facts_state": facts_state, "analysis": analysis,
                 "ocr": ocr}
        if not ocr:
            self.write_future_work_sidecar(key, analysis=analysis)
        return entry

    def write_preflight_file(self, preflight):
        path = self.root / "preflight.json"
        path.write_text(json.dumps(preflight, ensure_ascii=False), encoding="utf-8")
        return path

    def summary_line(self):
        return next(line for line in self.analysis_text().splitlines()
                    if "数据来源" in line)

    def direction_action(self, direction_id="DIR00001"):
        preflight = self.stage2_preflight()
        row = next(item for item in preflight["directions"]
                   if item["direction_id"] == direction_id)
        return preflight, row

    def direction_papers_only(self, *keys):
        """Keep only these papers in the counted direction set (paper list view)."""
        def narrow(facts):
            direction = facts["directions"][0]
            direction["member_keys"] = list(keys)
            direction["relevant_keys"] = list(keys)
        return narrow

    def direction_scope(self, member_keys, relevant_keys):
        """Keep the formal members and the wider P-citation scope separate."""
        def narrow(facts):
            direction = facts["directions"][0]
            direction["member_keys"] = list(member_keys)
            direction["relevant_keys"] = list(relevant_keys)
        return narrow

    def eligible_refresh_preflight(self):
        """A saved display-only preflight the formal entry may still run."""
        preflight = self.stage2_preflight()
        self.assertEqual(preflight["action"], "refresh_display", preflight)
        return preflight, self.write_preflight_file(preflight)

    def validator_business_fields(self, pack):
        """The certification fields a display-only step must not rewrite."""
        validator = pack.get("validator") or {}
        return {field: validator.get(field) for field in (
            "round", "phase", "results", "validation_sha256", "render_sha256")}

    def run_refresh_entry(self, preflight_file):
        """The formal refresh entry called in-process, so a clock patch applies.

        ``run_cli`` starts a subprocess, where an outer ``patch.object`` never
        reaches the product; only the two clock points of this test call the
        parsed CLI function directly. It changes no business function, fakes no
        return value and adds no runner framework.
        """
        arguments = contact_state.build_parser().parse_args([
            "stage2-refresh-display", "--professor-dir", str(self.prof_dir),
            "--preflight-file", str(preflight_file)])
        stdout = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(stdout):
            try:
                arguments.func(arguments)
            except SystemExit as exited:
                code = exited.code
        return json.loads(stdout.getvalue()), code

    def test_counts_follow_the_recorded_analysis_level(self):
        ccc = self.prof_dir / "论文分析" / "CCCC3333.md"

        def levels(facts):
            recorded = {"AAAA1111": None, "BBBB2222": "abstract",
                        "CCCC3333": "fulltext"}
            for paper in facts["papers"]:
                paper["analysis_level"] = recorded[paper["item_key"]]
                if paper["item_key"] == "CCCC3333":
                    paper["analysis_file"] = str(ccc)

        facts = self.write_facts(levels, self.direction_papers_only(
            "AAAA1111", "BBBB2222", "CCCC3333"))
        # AAAA1111 has an orphaned analysis file but no successful index entry:
        # a file alone cannot establish its level. CCCC3333 is a successful
        # OCR-only fulltext with an OCR carrier but no PDF-grounded facts.
        # A missing facts sidecar by itself does not mean analysis failed.
        self.write_analysis("AAAA1111")
        self.write_analysis("CCCC3333", ocr=True)
        self.write_index({
            "BBBB2222": {"level": "abstract", "facts_state": "unavailable"},
            "CCCC3333": {"level": "fulltext", "facts_state": "unavailable", "ocr": True},
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
        self.assertEqual(papers["AAAA1111"]["analysis_file"], str(
            self.prof_dir / "论文分析" / "AAAA1111.md"))
        self.assertIsNone(papers["AAAA1111"].get("analysis_level"), papers["AAAA1111"])
        self.assertEqual(papers["BBBB2222"].get("analysis_level"), "abstract")
        # OCR-only fulltext keeps its fulltext level even without facts.
        self.assertEqual(papers["CCCC3333"].get("analysis_level"), "fulltext",
                         papers.get("CCCC3333"))
        self.assertEqual(papers["CCCC3333"].get("facts_state"), "unavailable",
                         papers.get("CCCC3333"))

    def test_legacy_records_without_level_count_as_unconfirmed(self):
        facts = self.write_facts(self.direction_papers_only("AAAA1111", "BBBB2222"))
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
        self.assertIn("未确认 2 篇", summary)
        self.assertIn("全文级 0 篇", summary)
        self.assertIn("摘要级 0 篇", summary)

    def test_display_only_level_change_refreshes_without_model_work(self):
        # Complete accepted baseline: the counted direction set already holds
        # the OCR-only fulltext with its index record, analysis and OCR files,
        # so the only change below is the recorded level of AAAA1111/BBBB2222.
        self.accepted_run(ocr_only=("CCCC3333",),
                          facts_extra=self.direction_papers_only(
                              "AAAA1111", "BBBB2222", "CCCC3333"))
        facts_path = self.root / "facts.json"
        pack_before = self.pack()
        freshness_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        freshness_before = freshness_path.read_text(encoding="utf-8")
        # Precondition of the planned scenario: the recorded PASS binds the body
        # that is on disk now, so only a real content change can invalidate it.
        body_before = managed_body(self.analysis_text())
        self.assertEqual(pack_before["validator"]["render_sha256"],
                         hashlib.sha256(body_before.encode("utf-8")).hexdigest())
        self.update_sources({"AAAA1111": "abstract", "BBBB2222": "abstract",
                             "CCCC3333": "fulltext"},
                            {"AAAA1111": {"level": "abstract"},
                             "BBBB2222": {"level": "abstract"},
                             "CCCC3333": {"level": "fulltext", "ocr": True}})
        preflight = self.stage2_preflight()
        self.assertEqual(preflight["action"], "refresh_display", preflight)
        preflight_path = self.write_preflight_file(preflight)
        # The planned display refresh consumes the accepted pack and the index
        # only; /tmp facts is gone by then.
        facts_path.unlink()
        refreshed = self.refresh_display(preflight_path)
        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertTrue(refreshed.get("display_refreshed"), refreshed)
        summary = self.summary_line()
        self.assertIn("全文级 1 篇", summary)
        self.assertIn("摘要级 2 篇", summary)
        # Same pack-only refresh: the fixed cards keep their trusted references.
        analysis = self.analysis_text()
        titles = {paper["item_key"]: paper["title"] for paper in self.papers}
        for slot in ("后续论文依据", "已做部分", "剩余缺口"):
            line = next(line for line in analysis.splitlines()
                        if line.startswith(f"- {slot}："))
            self.assertIn(titles["AAAA1111"], line, slot)
            self.assertIn("zotero://select/library/items/AAAA1111", line, slot)
            self.assertNotIn("AAAA1111", line.replace(
                "zotero://select/library/items/AAAA1111", ""), slot)
        blacklist_line = next(line for line in analysis.splitlines()
                              if "已被" in line and "接住" in line)
        self.assertIn(titles[BLACKLIST_COMPLETION], blacklist_line)
        self.assertIn(f"zotero://select/library/items/{BLACKLIST_COMPLETION}",
                      blacklist_line)
        self.assertNotIn(BLACKLIST_COMPLETION, blacklist_line.replace(
            f"zotero://select/library/items/{BLACKLIST_COMPLETION}", ""))
        pack_after = self.pack()
        # The pack-only refresh keeps the fixed cards' machine fields: only the
        # display-only analysis level and the render binding may move.
        real_fields = ("status", "evidence", "completed_part", "remaining_gap",
                       "quote", "translation_zh", "confidence", "evaluated_at",
                       "candidate_paper_ids", "item_key", "gap_id")
        self.assertEqual(len(pack_after["directions"][0]["gap_shortlist"]),
                         len(pack_before["directions"][0]["gap_shortlist"]))
        for before_gap, after_gap in zip(pack_before["directions"][0]["gap_shortlist"],
                                         pack_after["directions"][0]["gap_shortlist"]):
            self.assertEqual({field: before_gap.get(field) for field in real_fields},
                             {field: after_gap.get(field) for field in real_fields},
                             before_gap.get("item_key"))
        self.assertEqual(pack_after["directions"][0]["completed_gap_blacklist"],
                         pack_before["directions"][0]["completed_gap_blacklist"])
        self.assertEqual(
            [row.get("gap_id") for row in pack_after["directions"][0]["gaps_excluded"]],
            [row.get("gap_id") for row in pack_before["directions"][0]["gaps_excluded"]])
        # The canonical pack now carries the refreshed levels that the counts read.
        levels_after = {key: paper.get("analysis_level")
                        for key, paper in pack_after["papers"].items()}
        self.assertEqual(levels_after, {"AAAA1111": "abstract",
                                        "BBBB2222": "abstract",
                                        "CCCC3333": "fulltext"}, levels_after)
        self.assertEqual(sorted(pack_after["papers"]), ["AAAA1111", "BBBB2222", "CCCC3333"])
        # Business state, model fingerprints and recorded assignment survive.
        self.assertEqual(pack_after["directions"][0]["narrative"],
                         pack_before["directions"][0]["narrative"])
        self.assertEqual(pack_after["directions"][0]["supporting_item_keys"],
                         pack_before["directions"][0]["supporting_item_keys"])
        self.assertEqual(pack_after["directions"][0]["input_fingerprint"],
                         pack_before["directions"][0]["input_fingerprint"])
        self.assertEqual(pack_after["directions"][0]["named_keys"],
                         pack_before["directions"][0]["named_keys"])
        self.assertEqual(papers_of(pack_after), papers_of(pack_before))
        # One display-only refresh rewrote the body, so the recorded PASS bound
        # to the old body must no longer be accepted, and the accepted pack must
        # stay internally consistent (no stale pack-integrity mismatch).
        after, _row = self.direction_action()
        self.assertEqual(after["action"], "process", after)
        self.assertIn("validator_not_accepted", _row["reason_codes"], _row)
        self.assertNotIn("pack_integrity_mismatch", after["reason_codes"], after)
        self.assertNotEqual(hashlib.sha256(managed_body(self.analysis_text()).encode(
            "utf-8")).hexdigest(), pack_before["validator"]["render_sha256"])
        # No model task was created by the display-only step: the freshness
        # cache is untouched, so no re-analysis, assignment or freshness job
        # was queued. A display change is a new validation version: the old
        # certification is formally expired here, so the refreshed body cannot
        # carry the old PASS, and it registers again from round 1 below.
        self.assertEqual(freshness_path.read_text(encoding="utf-8"), freshness_before)
        self.assertFalse(pack_after.get("validator"), pack_after.get("validator"))
        rerecorded = self.record(self.write_report("pass-after-refresh.json", [],
                                                   verdict="pass"))
        self.assertEqual(rerecorded["status"], "ok", rerecorded)
        self.assertEqual(rerecorded["round"], 1, rerecorded)

    def test_ordinary_reuse_replaces_known_level_with_null(self):
        # A legal accepted baseline whose counted set is AAAA1111 + BBBB2222.
        self.accepted_run(facts_extra=self.direction_papers_only(
            "AAAA1111", "BBBB2222"))
        pack_before = self.pack()
        body_before = managed_body(self.analysis_text())
        self.assertEqual(pack_before["papers"]["AAAA1111"]["analysis_level"],
                         "fulltext", pack_before["papers"]["AAAA1111"])
        # Only the CURRENT level statement changes: the same files, the same
        # index paths and states, and both other papers stay fulltext.
        self.update_sources({"AAAA1111": None, "BBBB2222": "fulltext",
                             "CCCC3333": "fulltext"},
                            {"AAAA1111": {"level": None},
                             "BBBB2222": {"level": "fulltext"},
                             "CCCC3333": {"level": "fulltext"}})
        facts_path = self.root / "facts.json"
        plan = parse(run_bound_stage2_plan(run_cli, facts_path))
        self.assertEqual(plan["status"], "ok", plan)
        row = next(item for item in plan["directions"]
                   if item["direction_id"] == "DIR00001")
        self.assertEqual(row["action"], "reuse", plan)
        self.assertEqual(plan["jobs"], [], plan)
        finalized = parse(run_bound_stage2_finalize(
            run_cli, facts_path, "--results", self.root / "results"))
        self.assertEqual(finalized["status"], "ok", finalized)
        # The current null is a real value: the ordinary reuse path must state
        # it and clear the old fulltext instead of carrying the old pack level.
        pack_after = self.pack()
        self.assertIsNone(pack_after["papers"]["AAAA1111"].get("analysis_level"),
                          pack_after["papers"]["AAAA1111"])
        self.assertEqual(pack_after["papers"]["BBBB2222"].get("analysis_level"),
                         "fulltext", pack_after["papers"]["BBBB2222"])
        summary = self.summary_line()
        self.assertIn("全文级 1 篇", summary)
        self.assertIn("摘要级 0 篇", summary)
        self.assertIn("未确认 1 篇", summary)
        self.assertNotEqual(managed_body(self.analysis_text()), body_before)
        # The rebuilt body is a new validation version: the old certification
        # no longer proves it and the new body registers again from round 1.
        _preflight, row_after = self.direction_action()
        self.assertIn("validator_not_accepted", row_after["reason_codes"], row_after)
        rerecorded = self.record(self.write_report("pass-after-null-level.json", [],
                                                   verdict="pass"))
        self.assertEqual(rerecorded["status"], "ok", rerecorded)
        self.assertEqual(rerecorded["round"], 1, rerecorded)

    def test_nonmember_level_refresh_keeps_visible_body_and_round(self):
        # CCCC3333 is inside the P-citation scope but NOT a formal member, so
        # its level never enters the aggregate the managed body shows.
        self.accepted_run(facts_extra=self.direction_scope(
            ("AAAA1111", "BBBB2222"),
            ("AAAA1111", "BBBB2222", "CCCC3333")))
        pack_before = self.pack()
        reference_scope = pack_before["directions"][0]
        self.assertIn("CCCC3333", pack_before["papers"])
        self.assertIn("CCCC3333", reference_scope["relevant_keys"])
        self.assertNotIn("CCCC3333", reference_scope["supporting_item_keys"])
        body_before = self.analysis_text()
        summary_before = self.summary_line()
        certification_before = self.validator_business_fields(pack_before)
        self.update_sources({"AAAA1111": "fulltext", "BBBB2222": "fulltext",
                             "CCCC3333": "abstract"},
                            {"AAAA1111": {"level": "fulltext"},
                             "BBBB2222": {"level": "fulltext"},
                             "CCCC3333": {"level": "abstract"}})
        _preflight, preflight_path = self.eligible_refresh_preflight()
        refreshed = self.refresh_display(preflight_path)
        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertTrue(refreshed.get("display_refreshed"), refreshed)
        pack_after = self.pack()
        self.assertEqual(pack_after["papers"]["CCCC3333"].get("analysis_level"),
                         "abstract", pack_after["papers"]["CCCC3333"])
        # Nothing the body shows moved: the same bytes and the same counts.
        self.assertEqual(self.analysis_text(), body_before)
        self.assertEqual(self.summary_line(), summary_before)
        # The certification stays because it still binds the same body; only the
        # pack digest stored next to it may move with the pack content.
        self.assertEqual(self.validator_business_fields(pack_after),
                         certification_before)
        self.assertEqual(pack_after["validator"]["pack_sha256"],
                         contact_state.stage2_pack_content_fingerprint(pack_after))
        accepted = self.stage2_preflight()
        self.assertEqual(accepted["action"], "reuse_all", accepted)

    def test_ordinary_member_level_swap_keeps_visible_body_and_round(self):
        # No accepted_run shortcut: the two formal members must start on
        # DIFFERENT levels, so the first accepted baseline is built explicitly
        # from the real index, facts, render and record steps.
        for key in ("AAAA1111", "BBBB2222", "CCCC3333"):
            self.write_analysis(key)
            self.write_future_work_sidecar(key)
        self.write_index({"AAAA1111": {"level": "fulltext"},
                          "BBBB2222": {"level": "abstract"},
                          "CCCC3333": {"level": "fulltext"}})

        def levels(facts):
            recorded = {"AAAA1111": "fulltext", "BBBB2222": "abstract",
                        "CCCC3333": "fulltext"}
            for paper in facts["papers"]:
                paper["analysis_level"] = recorded[paper["item_key"]]

        facts = self.write_facts(levels, self.direction_scope(
            ("AAAA1111", "BBBB2222"),
            ("AAAA1111", "BBBB2222", "CCCC3333")))
        self.render_fixture(facts)
        passed = self.record(self.write_report("swap-baseline-pass.json", [],
                                               verdict="pass"))
        self.assertEqual(passed["status"], "ok", passed)
        pack_before = self.pack()
        self.assertEqual(pack_before["papers"]["AAAA1111"]["analysis_level"],
                         "fulltext", pack_before["papers"]["AAAA1111"])
        self.assertEqual(pack_before["papers"]["BBBB2222"]["analysis_level"],
                         "abstract", pack_before["papers"]["BBBB2222"])
        summary_before = self.summary_line()
        self.assertIn("全文级 1 篇", summary_before)
        self.assertIn("摘要级 1 篇", summary_before)
        self.assertIn("未确认 0 篇", summary_before)
        body_before = self.analysis_text()
        certification_before = self.validator_business_fields(pack_before)
        # Only the two members exchange their levels, so the aggregate the body
        # shows stays identical and the ordinary path must not repaint or reset.
        self.update_sources({"AAAA1111": "abstract", "BBBB2222": "fulltext",
                             "CCCC3333": "fulltext"},
                            {"AAAA1111": {"level": "abstract"},
                             "BBBB2222": {"level": "fulltext"},
                             "CCCC3333": {"level": "fulltext"}})
        facts_path = self.root / "facts.json"
        plan = parse(run_bound_stage2_plan(run_cli, facts_path))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(plan["jobs"], [], plan)
        row = next(item for item in plan["directions"]
                   if item["direction_id"] == "DIR00001")
        self.assertEqual(row["action"], "reuse", plan)
        finalized = parse(run_bound_stage2_finalize(
            run_cli, facts_path, "--results", self.root / "results"))
        self.assertEqual(finalized["status"], "ok", finalized)
        pack_after = self.pack()
        self.assertEqual(pack_after["papers"]["AAAA1111"].get("analysis_level"),
                         "abstract", pack_after["papers"]["AAAA1111"])
        self.assertEqual(pack_after["papers"]["BBBB2222"].get("analysis_level"),
                         "fulltext", pack_after["papers"]["BBBB2222"])
        self.assertEqual(self.summary_line(), summary_before)
        self.assertEqual(self.analysis_text(), body_before)
        self.assertEqual(self.validator_business_fields(pack_after),
                         certification_before)
        accepted = self.stage2_preflight()
        self.assertEqual(accepted["action"], "reuse_all", accepted)

    def test_null_facts_candidate_appearance_rejects_stale_refresh(self):
        # The baseline declares NO facts sidecar for AAAA1111 while its analysis
        # file exists, so the fixed candidate `<analysis>.facts.json` must be
        # kept and observed as missing rather than read as "no candidate".
        analysis = self.write_analysis("AAAA1111")
        facts_candidate = Path(str(analysis) + ".facts.json")
        self.assertTrue(analysis.exists())
        self.assertFalse(facts_candidate.exists())
        self.accepted_run()
        index = json.loads((self.prof_dir / "论文分析" / "_index.json").read_text(
            encoding="utf-8"))
        self.assertIsNone(index["papers"]["AAAA1111"]["facts_sidecar"])
        self.assertEqual(index["papers"]["AAAA1111"]["facts_state"], "unavailable")
        recorded = self.pack()["cache"]["preflight"]["analysis_projection"]["keys"]
        self.assertEqual(recorded["AAAA1111"]["facts_sidecar"], str(facts_candidate),
                         recorded["AAAA1111"])
        self.assertFalse(recorded["AAAA1111"]["facts_exists"], recorded["AAAA1111"])
        # A legal display-only level change makes the refresh eligible...
        self.update_sources({"AAAA1111": "abstract", "BBBB2222": "fulltext",
                             "CCCC3333": "fulltext"},
                            {"AAAA1111": {"level": "abstract"},
                             "BBBB2222": {"level": "fulltext"},
                             "CCCC3333": {"level": "fulltext"}})
        _preflight, preflight_path = self.eligible_refresh_preflight()
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack_before = pack_path.read_bytes()
        analysis_before = self.analysis_text()
        # ...and then only the recorded fixed candidate itself appears, at the
        # position the accepted projection recorded, with content that is not
        # valid facts: the appearing file is a source change, not a level.
        facts_candidate.write_text("{}\n", encoding="utf-8")
        refused = self.refresh_display(preflight_path)
        self.assertNotEqual(refused.get("status"), "ok", refused)
        self.assertEqual(refused.get("reason_code"), "display_refresh_stale", refused)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(self.analysis_text(), analysis_before)
        self.assert_routes_back_to_process(self.stage2_preflight())

    def test_bad_candidate_record_is_not_missing_record(self):
        # An unreadable per-key record is NOT the absence of a record: it cannot
        # prove the sources unchanged, so the ordinary process path decides.
        self.accepted_run()
        index_path = self.prof_dir / "论文分析" / "_index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertIsInstance(index["papers"]["AAAA1111"], dict)
        index["papers"]["AAAA1111"] = "broken"
        index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        # The index as a whole is still a legal JSON object with a papers map.
        self.assertEqual(json.loads(index_path.read_text(encoding="utf-8"))["schema"], 2)
        preflight = self.stage2_preflight()
        # "process" is the only remaining action: the bad record can prove
        # neither "nothing changed" (reuse_all) nor a display-only level change.
        self.assertEqual(preflight["action"], "process", preflight)
        # The structured reasons must name the unusable analysis source instead
        # of degrading to "nothing changed"; the human-readable message is never
        # matched and no new string is frozen.
        signals = set(preflight["reason_codes"])
        for row in preflight["directions"]:
            signals.update(row["reason_codes"])
        self.assertTrue(signals & {"analysis_source_changed", "analysis_index_unreadable",
                                   "analysis_projection_unavailable"}, preflight)

    def test_refresh_rechecks_year_at_entry_and_inside_lease(self):
        for entering_lease in (False, True):
            # The two time points describe where the year crosses relative to
            # the write protection; no wall-clock sample is collected.
            point = "写入保护内" if entering_lease else "入口点"
            environment = self.__class__(self._testMethodName)
            environment.setUp()
            try:
                environment.accepted_run()
                environment.update_sources(
                    {"AAAA1111": "abstract", "BBBB2222": "fulltext",
                     "CCCC3333": "fulltext"},
                    {"AAAA1111": {"level": "abstract"},
                     "BBBB2222": {"level": "fulltext"},
                     "CCCC3333": {"level": "fulltext"}})
                preflight, preflight_path = environment.eligible_refresh_preflight()
                year = preflight["preflight_inputs"]["current_year"]
                self.assertEqual(
                    environment.pack()["cache"]["preflight"]["current_year"], year,
                    f"{point}：可刷新的预检必须带已接受的业务年份")
                pack_path = environment.prof_dir / "套磁候选输入.json"
                pack_before = pack_path.read_bytes()
                analysis_before = environment.analysis_text()
                entered = []
                real_scope = contact_state.stage2_local_writer_scope
                with mock.patch.object(contact_state, "datetime",
                                       wraps=datetime) as clock:
                    # Only `.now` is pinned to the test clock; the class itself
                    # stays usable, so nothing but the current business year is
                    # replaced near the two clock points under test.
                    clock.fromisoformat = datetime.fromisoformat
                    clock.strptime = datetime.strptime
                    clock.now.return_value = datetime(year, 12, 31, 23, 59, 59)
                    if entering_lease:
                        # The entry still sees the accepted year; only the real
                        # lease is entered before the clock crosses it.
                        outside_year_clock = datetime(year + 1, 1, 1, 0, 0, 1)

                        @contextlib.contextmanager
                        def scope_that_crosses_the_year(professor_dir):
                            with real_scope(professor_dir):
                                clock.now.return_value = outside_year_clock
                                entered.append(True)
                                yield

                        lease_patch = mock.patch.object(
                            contact_state, "stage2_local_writer_scope",
                            scope_that_crosses_the_year)
                    else:
                        clock.now.return_value = datetime(year + 1, 1, 1, 0, 0, 1)

                        def spy_scope(professor_dir):
                            entered.append(True)
                            return real_scope(professor_dir)

                        lease_patch = mock.patch.object(
                            contact_state, "stage2_local_writer_scope", spy_scope)
                    with lease_patch:
                        payload, code = environment.run_refresh_entry(preflight_path)
                # One standard `-v` failure report carries the exercised time
                # point, whether the real write protection was entered and what
                # the entry returned; no extra print, result file or checker.
                diagnostic = {"时点": point, "写入保护标记": bool(entered),
                              "返回": payload}
                self.assertEqual(code, 2, diagnostic)
                self.assertEqual(payload.get("status"), "needs_refresh", diagnostic)
                self.assertEqual(payload.get("reason_code"),
                                 "display_refresh_stale", diagnostic)
                signals = set(payload.get("reason_codes") or []) \
                    | set(payload.get("drift") or [])
                self.assertTrue(signals & set(YEAR_MISMATCH_SIGNALS), diagnostic)
                if entering_lease:
                    self.assertEqual(entered, [True], diagnostic)
                else:
                    self.assertEqual(entered, [], diagnostic)
                self.assertEqual(pack_path.read_bytes(), pack_before, diagnostic)
                self.assertEqual(environment.analysis_text(), analysis_before,
                                 diagnostic)
            finally:
                environment.tearDown()

    def assert_routes_back_to_process(self, preflight):
        self.assertEqual(preflight["action"], "process", preflight)
        self.assertTrue(preflight["reason_codes"], preflight)

    def test_source_change_routes_back_to_the_process_path(self):
        # The accepted baseline has no index record and no file for CCCC3333.
        self.accepted_run(indexed=("AAAA1111", "BBBB2222"))
        # First plan a legitimate display-only level update. Before writing,
        # a previously absent analysis source appears: the plan is now stale.
        self.update_sources(
            {"AAAA1111": "abstract", "BBBB2222": "fulltext", "CCCC3333": None},
            {"AAAA1111": {"level": "abstract"},
             "BBBB2222": {"level": "fulltext"}})
        level_only = self.stage2_preflight()
        self.assertEqual(level_only["action"], "refresh_display", level_only)
        stale_preflight_file = self.write_preflight_file(level_only)
        self.assertNotIn("CCCC3333", json.loads(
            (self.prof_dir / "论文分析" / "_index.json").read_text(encoding="utf-8"))["papers"])
        analysis = self.prof_dir / "论文分析" / "CCCC3333.md"
        self.assertFalse(analysis.exists())
        # The analysis, its OCR carrier and its index record appear; the
        # facts sidecar stays missing, which the index records as unavailable.
        self.update_sources(
            {"AAAA1111": "abstract", "BBBB2222": "fulltext", "CCCC3333": "fulltext"},
            {"AAAA1111": {"level": "abstract"},
             "BBBB2222": {"level": "fulltext"},
             "CCCC3333": {"level": "fulltext", "facts_state": "unavailable",
                          "analysis": analysis, "ocr": True}},
            add=({"item_key": "CCCC3333", "analysis_file": str(analysis)},))
        self.write_analysis("CCCC3333", ocr=True)
        index = json.loads((self.prof_dir / "论文分析" / "_index.json").read_text(
            encoding="utf-8"))
        self.assertIn("CCCC3333", index["papers"],
                      "the appearing source must be recorded in the index")
        self.assertEqual(index["papers"]["CCCC3333"]["file"], str(analysis))
        self.assertTrue(analysis.exists())
        self.assertTrue(self.ocr_path("CCCC3333").exists())
        pack_before = (self.prof_dir / "套磁候选输入.json").read_bytes()
        analysis_before = self.analysis_text()
        refused = self.refresh_display(stale_preflight_file)
        self.assertNotEqual(refused.get("status"), "ok", refused)
        self.assertEqual((self.prof_dir / "套磁候选输入.json").read_bytes(), pack_before)
        self.assertEqual(self.analysis_text(), analysis_before)
        self.assert_routes_back_to_process(self.stage2_preflight())

    def test_deleted_analysis_source_also_routes_back_to_process(self):
        # Source deletion has its own untouched accepted baseline. Keep facts
        # and every surviving paper's index record unchanged; only CCCC3333's
        # analysis file and index record disappear.
        self.accepted_run()
        self.remove_analysis("CCCC3333")
        self.write_index({"AAAA1111": {"level": "fulltext"},
                          "BBBB2222": {"level": "fulltext"}})
        self.assertFalse((self.prof_dir / "论文分析" / "CCCC3333.md").exists())
        self.assertNotIn("CCCC3333", json.loads(
            (self.prof_dir / "论文分析" / "_index.json").read_text(encoding="utf-8"))["papers"])
        self.assert_routes_back_to_process(self.stage2_preflight())

        # A separate temporary professor fixture checks user edits between a
        # valid display-only preflight and the write, independently of deletion.
        manual_env = self.__class__(self._testMethodName)
        manual_env.setUp()
        try:
            manual_env.accepted_run()
            manual_env.update_sources(
                {"AAAA1111": "abstract", "BBBB2222": "fulltext",
                 "CCCC3333": "fulltext"},
                {"AAAA1111": {"level": "abstract"},
                 "BBBB2222": {"level": "fulltext"},
                 "CCCC3333": {"level": "fulltext"}})
            level_only = manual_env.stage2_preflight()
            manual_env.assertEqual(level_only["action"], "refresh_display",
                                   level_only)
            preflight_file = manual_env.write_preflight_file(level_only)
            analysis_path = manual_env.prof_dir / "套磁候选分析.md"
            analysis_path.write_text(
                manual_env.analysis_text() + "\n用户手动补充的说明。\n",
                encoding="utf-8")
            protected_analysis = analysis_path.read_bytes()
            pack_path = manual_env.prof_dir / "套磁候选输入.json"
            protected_pack = pack_path.read_bytes()
            refused = manual_env.refresh_display(preflight_file)
            manual_env.assertNotEqual(refused.get("status"), "ok", refused)
            manual_env.assertEqual(analysis_path.read_bytes(), protected_analysis)
            manual_env.assertEqual(pack_path.read_bytes(), protected_pack)
        finally:
            manual_env.tearDown()

        # A third, independent baseline keeps the old analysis file and the old
        # pack path but states an EXPLICIT empty analysis path in the index.
        # The explicit empty is a current statement: it must not be backfilled
        # from the old pack path (or the file on disk) and must take the
        # ordinary process path instead of a display refresh.
        empty_env = self.__class__(self._testMethodName)
        empty_env.setUp()
        try:
            empty_env.accepted_run()
            index_path = empty_env.prof_dir / "论文分析" / "_index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            old_analysis = empty_env.prof_dir / "论文分析" / "AAAA1111.md"
            self.assertEqual(index["papers"]["AAAA1111"]["file"], str(old_analysis))
            index["papers"]["AAAA1111"]["file"] = None
            index_path.write_text(json.dumps(index, ensure_ascii=False),
                                  encoding="utf-8")
            self.assertTrue(old_analysis.exists(),
                            "the explicit empty must be the only change")
            self.assertEqual(empty_env.pack()["papers"]["AAAA1111"]["analysis_file"],
                             str(old_analysis))
            empty_env.assert_routes_back_to_process(empty_env.stage2_preflight())
            # Direct observation of the source projection the preflight reads:
            # the current explicit empty is neither re-declared nor selected.
            paths = contact_state.stage2_projection_analysis_paths(
                contact_state.pack_paper_index(empty_env.pack()))
            entry = contact_state.stage2_analysis_projection(
                empty_env.prof_dir, ["AAAA1111"], paths)["keys"]["AAAA1111"]
            empty_env.assertIsNone(entry["analysis_file"], entry)
            empty_env.assertFalse(entry["analysis_exists"], entry)
        finally:
            empty_env.tearDown()

    def test_replaced_analysis_source_routes_back_to_process(self):
        self.accepted_run()
        # Same key, moved analysis file: the index path changes and the old file
        # is gone, so this is a replacement rather than a level-only change.
        old_analysis = self.prof_dir / "论文分析" / "CCCC3333.md"
        new_analysis = self.prof_dir / "论文分析" / "CCCC3333-v2.md"
        new_analysis.write_text("# analysis v2\n", encoding="utf-8")
        old_analysis.unlink()
        Path(str(old_analysis) + ".future_work.json").unlink(missing_ok=True)
        self.update_sources(
            {"AAAA1111": "fulltext", "BBBB2222": "fulltext", "CCCC3333": "fulltext"},
            {"AAAA1111": {"level": "fulltext"},
             "BBBB2222": {"level": "fulltext"},
             "CCCC3333": self.declare_analysis("CCCC3333", new_analysis, "fulltext")},
            add=({"item_key": "CCCC3333", "has_pdf": True,
                  "analysis_file": str(new_analysis)},))
        self.assertTrue(Path(str(new_analysis) + ".future_work.json").exists())
        index = json.loads((self.prof_dir / "论文分析" / "_index.json").read_text(
            encoding="utf-8"))
        self.assertEqual(index["papers"]["CCCC3333"]["file"], str(new_analysis))
        self.assertFalse(old_analysis.exists())
        self.assert_routes_back_to_process(self.stage2_preflight())

    def test_pack_without_a_comparable_baseline_is_not_refreshed_as_display_only(self):
        # accepted_run() already builds the pack, records the terminal PASS and
        # proves the untouched pack reuses (`reuse_all`).
        self.accepted_run()
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        del pack["cache"]["preflight"]
        # Removing the accepted baseline also invalidates the recorded pack
        # digest; recompute only that digest so this case proves the missing
        # baseline is detected instead of a stale validation digest.
        pack["validator"]["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        preflight = self.stage2_preflight()
        self.assertEqual(preflight["action"], "process", preflight)
        self.assertIn("legacy_pack_no_preflight", preflight["reason_codes"], preflight)
        for row in preflight["directions"]:
            self.assertNotIn("validator_not_accepted", row["reason_codes"], row)

        # A second, independent accepted pack keeps its whole cache.preflight but
        # loses the fixed facts-candidate observation of AAAA1111: an accepted
        # source baseline that lacks a state this comparison needs may not be
        # read as "unchanged" either. Only the existing content fingerprint is
        # recomputed, so the refusal cannot come from a stale validator digest.
        baseline_env = self.__class__(self._testMethodName)
        baseline_env.setUp()
        try:
            baseline_env.accepted_run()
            baseline_pack_path = baseline_env.prof_dir / "套磁候选输入.json"
            baseline_pack = json.loads(baseline_pack_path.read_text(encoding="utf-8"))
            projection_keys = baseline_pack["cache"]["preflight"]["analysis_projection"]["keys"]
            self.assertIn("AAAA1111", projection_keys)
            candidate = projection_keys["AAAA1111"]
            for field in ("facts_sidecar", "facts_exists"):
                self.assertIn(field, candidate, candidate)
                del candidate[field]
            baseline_pack["validator"]["pack_sha256"] = \
                contact_state.stage2_pack_content_fingerprint(baseline_pack)
            baseline_pack_path.write_text(json.dumps(baseline_pack, ensure_ascii=False),
                                          encoding="utf-8")
            stale = baseline_env.stage2_preflight()
            baseline_env.assertEqual(stale["action"], "process", stale)
            for row in stale["directions"]:
                baseline_env.assertNotIn("validator_not_accepted", row["reason_codes"], row)
        finally:
            baseline_env.tearDown()


class ResolvedAnalysisLevelTests(resolved_pipeline_tests.ResolvedPipelineMixin,
                                 unittest.TestCase):
    """T4 — a resolution that admits a new member keeps that member's level.

    Reuses the resolved-pipeline helpers and the exact temporary professor
    directory setUp/tearDown of `Stage2FinalizeWithResolvedTests`; no second
    resolve harness and no copied fixture. The fixture class is reached through
    its module and only its setUp/tearDown are bound here, so `unittest
    discover` neither collects that class twice nor inherits its test methods
    into this module under a second name.
    """

    setUp = resolved_pipeline_tests.Stage2FinalizeWithResolvedTests.setUp
    tearDown = resolved_pipeline_tests.Stage2FinalizeWithResolvedTests.tearDown

    def analysis_text(self):
        return (self.prof_dir / "套磁候选分析.md").read_text(encoding="utf-8")

    def summary_line(self):
        return next(line for line in self.analysis_text().splitlines()
                    if "数据来源" in line)

    def test_added_relevant_member_keeps_current_level(self):
        first = self.make_paper("AAAA1111", "Synthetic comparison of input patterns",
                                ["合成", "比较"],
                                ["Future work will extend the comparison."])
        first["analysis_level"] = "abstract"
        second = self.make_paper("BBBB2222", "Synthetic processing path evaluation",
                                 ["合成", "处理"],
                                 ["We plan to test a second synthetic path."])
        second["analysis_level"] = "fulltext"
        facts_path = self.write_facts([first, second], [
            self.make_direction("DIR00001", ["AAAA1111", "BBBB2222"],
                                provisional_keys=["AAAA1111"]),
        ])
        # BBBB2222 is inside the candidate / relevant set but is NOT an original
        # formal member: only the resolution below may admit it.
        self.assertEqual(
            json.loads(facts_path.read_text(encoding="utf-8"))["directions"][0][
                "provisional_member_keys"],
            ["AAAA1111"])
        _, resolve_payload = self.run_resolve(facts_path, {
            "DIR00001": {
                "resolved_direction_id": "DIR00001",
                "provisional_direction_id": "DIR00001",
                "name_ja": "方向",
                "name_zh": "方向",
                "resolution_type": "refined",
                "papers_to_add": ["BBBB2222"],
                "papers_to_remove": [],
                "paper_justifications": {"BBBB2222": "合成全文证据支持该方向"},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        })
        self.assertTrue(resolve_payload["needs_user_choice"], resolve_payload)
        accepted = self.accept_resolved(facts_path, ["DIR00001"])
        self.assertEqual(accepted["status"], "ok",
                         msg=json.dumps(accepted, ensure_ascii=False))
        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        pack = self.load_pack()
        direction = next(entry for entry in pack["directions"]
                         if entry["direction_id"] == "DIR00001")
        # The added paper became a real formal member through the canonical
        # membership path, never by hand-writing supporting_item_keys.
        self.assertEqual(sorted(direction["supporting_item_keys"]),
                         ["AAAA1111", "BBBB2222"])
        self.assertEqual(pack["papers"]["BBBB2222"].get("analysis_level"), "fulltext",
                         pack["papers"]["BBBB2222"])
        self.assertEqual(pack["papers"]["AAAA1111"].get("analysis_level"), "abstract",
                         pack["papers"]["AAAA1111"])
        summary = self.summary_line()
        self.assertIn("全文级 1 篇", summary)
        self.assertIn("摘要级 1 篇", summary)
        self.assertIn("未确认 0 篇", summary)
        self.assertIn("共 2 篇", summary)
