"""U1 fixed-evidence display and real blocker ownership (test plan t2).

Covers the six must-test targets of ``plan/stage2-fixed-evidence/test-plan.md``:
trusted citation display (U1-A), missing-metadata handoff (U1-B), real fragment
ownership in validation reports (U1-C), fixed blockers stopping the model
rewrite while narrative keeps two rounds (U1-D), old-pack update through the
ordinary preflight -> process -> finalize path (U1-E), and the ordinary
acceptance split between body, business state, binding and old validation
(U1-F).
"""
import copy
import json
from pathlib import Path

from test_contact_state import (
    BaseEnv,
    contact_state,
    parse,
    run_cli,
    stage2_style_validation_report,
)
from stage2_upstream_fixture import run_bound_stage2_finalize

CITATION_KEY = "CCCC3333"
CITATION_TITLE = "Unrelated synthetic example"
CITATION_LINK = f"[{CITATION_TITLE}](zotero://select/library/items/{CITATION_KEY})"
ORDINARY_EIGHT = "DDDD8888"
ORDINARY_DATE = "2024-05-01"


class FixedEvidenceBase(BaseEnv):
    def _fresh_env(self):
        env = self.__class__(self._testMethodName)
        env.setUp()
        self.addCleanup(env.tearDown)
        return env

    # -- fixture helpers -----------------------------------------------------

    def gap_override(self):
        return {
            "AAAA1111": {
                "status": "partial",
                "candidate_paper_ids": [CITATION_KEY],
                "evidence": (f"后续由 {CITATION_KEY} 完成，日期 {ORDINARY_DATE}，"
                             f"未知 {ORDINARY_EIGHT} 与 12345678 保留。"),
                "completed_part": (f"{CITATION_LINK} 已完成一部分；\n"
                                   f"续行仍由 {CITATION_KEY} 负责。"),
                "remaining_gap": (f"仍缺 {CITATION_KEY} 的对比，"
                                  f"见 zotero://select/library/items/{CITATION_KEY}。"),
            },
            "BBBB2222": {
                "status": "done_by_self",
                "candidate_paper_ids": [CITATION_KEY],
                "evidence": f"{CITATION_KEY} 已接住该点。",
            },
        }

    def generate_pack(self, overrides=None, mutate_facts=None, narrative_mutate=None):
        facts_path = self.write_facts(mutate_facts)
        results = self.root / "results"
        self.write_stage2_results(results, overrides or {})
        if narrative_mutate:
            narrative_path = results / "narrative.json"
            narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
            narrative_mutate(narrative)
            narrative_path.write_text(json.dumps(narrative, ensure_ascii=False),
                                      encoding="utf-8")
        plan = parse(self.run_bound_stage2_plan(facts_path))
        self.assertEqual(plan["status"], "ok", plan)
        finalized = parse(run_bound_stage2_finalize(
            run_cli, facts_path, "--results", results))
        self.assertEqual(finalized["status"], "ok", finalized)
        proof = facts_path.with_name(facts_path.stem + "-preflight.json")
        return facts_path, results, proof

    def pack(self):
        return json.loads(
            (self.prof_dir / contact_state.INPUT_PACK).read_text(encoding="utf-8"))

    def write_pack(self, pack):
        (self.prof_dir / contact_state.INPUT_PACK).write_text(
            json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")

    def document(self):
        raw = (self.prof_dir / contact_state.ANALYSIS_MD).read_text(encoding="utf-8")
        header, body = contact_state.split_frontmatter(raw)
        return {"raw": raw, "header": header, "body": body,
                "sha256": contact_state.sha256_text(body)}

    def body_lines(self):
        return (self.prof_dir / contact_state.ANALYSIS_MD).read_text(
            encoding="utf-8").splitlines()

    def physical_line(self, needle, expected=1):
        hits = [index + 1 for index, line in enumerate(self.body_lines())
                if needle in line]
        self.assertEqual(len(hits), expected, (needle, hits))
        return hits if expected > 1 else hits[0]

    def preflight(self):
        out = parse(run_cli(
            "stage2-preflight", "--program-root", self.root,
            "--professor", "試験 教授",
            "--target-file", self.prof_dir / "套磁目标.json",
            "--paper-analysis", "relevant", "--gap-scope", "selected_direction",
            "--freshness-scope", "shortlist"))
        self.assertEqual(out["status"], "ok", out)
        return out

    def save_preflight(self, name="u1-preflight.json"):
        payload = self.preflight()
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path, payload

    def bind_facts_to_preflight(self, facts_path, payload):
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        facts["stage2_preflight"] = {"preflight_id": payload["preflight_id"]}
        Path(facts_path).write_text(
            json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")

    def finalize(self, facts_path, proof, results, *extra):
        return parse(run_bound_stage2_finalize(
            run_cli, facts_path, "--results", results, *extra)) if proof is None \
            else parse(run_cli("stage2-finalize", "--facts", facts_path,
                               "--preflight-file", proof, "--results", results, *extra))

    def blocking_issue(self, quote, location):
        return {"rule": "A1", "severity": "blocking", "location": location,
                "quote": quote, "suggestion": "改用日常语言解释。"}

    def minor_issue(self, quote, location):
        return {"rule": "A2", "severity": "minor", "location": location,
                "quote": quote, "suggestion": "可以更口语。"}

    def write_report(self, name, issues, verdict=None):
        issues = [dict(issue) for issue in issues]
        if verdict is None:
            verdict = ("fail" if any(issue.get("severity") == "blocking" for issue in issues)
                       else "pass_with_minor" if issues else "pass")
        report = stage2_style_validation_report(
            self.prof_dir / contact_state.ANALYSIS_MD, verdict, issues)
        path = self.root / name
        path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        return path

    def record(self, report_path):
        return parse(run_cli("stage2-record-validation",
                             "--professor-dir", self.prof_dir,
                             "--validation-file", report_path))

    def refine_plan(self, report_path, *extra):
        return parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                             "--validation-file", report_path, *extra))

    def refine_finalize(self, results, report_path, *extra):
        return parse(run_cli("stage2-refine-finalize", "--professor-dir", self.prof_dir,
                             "--results", results, "--validation-file", report_path,
                             *extra))

    def write_narrative_rewrite(self, before, after, name="rewrite"):
        pack = self.pack()
        direction = pack["directions"][0]
        narrative = copy.deepcopy(direction["narrative"])
        block = next(block for block in narrative["positioning"]
                     if before in block.get("text", ""))
        block["text"] = block["text"].replace(before, after, 1)
        rewrite = {
            "schema": 1, "kind": "narrative-rewrite",
            "direction_id": direction["direction_id"],
            "collection_key": direction.get("collection_key"),
            "positioning": narrative["positioning"],
            "gap_notes": [
                {"gap_id": gap_id, "summary": value["summary"],
                 "explanation": value["explanation"]}
                for gap_id, value in narrative["gap_notes"].items()],
        }
        results = self.root / name
        results.mkdir(parents=True, exist_ok=True)
        (results / f"narrative-rewrite-{direction['direction_id']}.json").write_text(
            json.dumps(rewrite, ensure_ascii=False), encoding="utf-8")
        return results

    def card_lines(self):
        lines = self.body_lines()
        start = next(index for index, line in enumerate(lines)
                     if line == "### 可延伸方向")
        return lines[start:]

    def without_links(self, text):
        return contact_state.re.sub(r"\[[^\]\n]*\]\([^)\n]*\)", "", text)

    # -- U1-A ----------------------------------------------------------------

    def test_u1_a_trusted_citation_display_keeps_facts_and_licences(self):
        self.generate_pack(self.gap_override())
        pack = self.pack()
        direction = pack["directions"][0]
        gap = direction["gap_shortlist"][0]
        self.assertEqual(gap["candidate_paper_ids"], [CITATION_KEY])
        # Raw structured facts must survive the display conversion untouched.
        self.assertEqual(gap["quote"], self.gap_quotes["AAAA1111"])
        self.assertEqual(gap["translation_zh"],
                         f"中译：{self.gap_quotes['AAAA1111'][:24]}".strip())
        self.assertEqual((gap["source"], gap["page"]), ("Conclusion", 8))
        self.assertEqual((gap["status"], gap["confidence"]), ("partial", "high"))
        self.assertEqual(
            gap["evidence"],
            f"后续由 {CITATION_KEY} 完成，日期 {ORDINARY_DATE}，"
            f"未知 {ORDINARY_EIGHT} 与 12345678 保留。")
        self.assertEqual(pack["papers"][CITATION_KEY]["title"], CITATION_TITLE)

        lines = self.card_lines()
        card = "\n".join(lines)
        gap_evidence_line = (
            f"- 后续论文依据：后续由 {CITATION_LINK} 完成，日期 {ORDINARY_DATE}，"
            f"未知 {ORDINARY_EIGHT} 与 12345678 保留。")
        completed_line = f"- 已做部分：{CITATION_LINK} 已完成一部分；"
        completed_continuation = f"续行仍由 {CITATION_LINK} 负责。"
        remaining_line = (
            f"- 剩余缺口：仍缺 {CITATION_LINK} 的对比，见 {CITATION_LINK}。")
        blacklist_line = (
            "- We plan to test a second synthetic processing path."
            "——《Synthetic processing path evaluation》（2024）→ "
            f"已被 {CITATION_LINK} 接住（依据：{CITATION_LINK} 已接住该点。）。")
        # One exact line per actual exit: link position, surrounding evidence
        # text and link count are checked in place instead of by a whole-card sum.
        for line in (gap_evidence_line, completed_line, completed_continuation,
                     remaining_line, blacklist_line):
            self.assertIn(line, lines)
        self.assertEqual(gap_evidence_line.count(CITATION_LINK), 1)
        self.assertEqual(completed_line.count(CITATION_LINK), 1)
        self.assertEqual(completed_continuation.count(CITATION_LINK), 1)
        self.assertEqual(remaining_line.count(CITATION_LINK), 2)
        self.assertEqual(blacklist_line.count(CITATION_LINK), 2)
        self.assertLess(lines.index(gap_evidence_line), lines.index(completed_line))
        self.assertLess(lines.index(completed_line),
                        lines.index(completed_continuation))
        self.assertLess(lines.index(completed_continuation),
                        lines.index(remaining_line))
        self.assertLess(lines.index(remaining_line), lines.index(blacklist_line))
        # The card still carries the raw quote/translation/source and freshness
        # conclusion next to the converted citations.
        self.assertIn(f"- 作者原话：「{self.gap_quotes['AAAA1111']}」", card)
        self.assertIn(
            f"- 中译：中译：{self.gap_quotes['AAAA1111'][:24]}".strip(), card)
        self.assertIn("- 页码：p.8（Conclusion）", card)
        self.assertIn("- 当前状态：partial（置信度 high）", card)
        self.assertNotIn(CITATION_KEY, self.without_links(card),
                         "the four exits must not leak the bare key outside a link target")
        self.assertNotIn("[[", card)
        self.assertEqual(card.count(CITATION_LINK), 7, card)
        self.assertIn(ORDINARY_EIGHT, card)
        self.assertIn("12345678", card)
        self.assertIn(ORDINARY_DATE, card)
        # Ordinary eight-digit prose is not a citation and gets no link target.
        self.assertNotIn(f"items/{ORDINARY_EIGHT}", card)
        # Machine evidence stays byte-identical; only the human-facing copy changes.
        blacklist = direction["completed_gap_blacklist"][0]
        self.assertEqual(blacklist["evidence"], f"{CITATION_KEY} 已接住该点。")
        self.assertEqual(blacklist["completed_by_item_key"], CITATION_KEY)
        # Display-only derived metadata never widens membership or P/L licence sets.
        self.assertEqual(sorted(direction["supporting_item_keys"]),
                         ["AAAA1111", "BBBB2222", "CCCC3333"])
        self.assertEqual(direction["relevant_keys"], ["AAAA1111", "BBBB2222"])
        self.assertEqual(direction["narrative_later_papers"], {})

    # -- U1-B ----------------------------------------------------------------

    def test_u1_b_missing_trusted_metadata_fails_before_write(self):
        env = self._fresh_env()
        expected_gap_id = contact_state.quote_id(self.gap_quotes["AAAA1111"])
        facts_path, results, proof = env.generate_pack(env.gap_override())
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        next(paper for paper in facts["papers"]
             if paper["item_key"] == CITATION_KEY)["title"] = ""
        Path(facts_path).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        analysis_path = env.prof_dir / contact_state.ANALYSIS_MD
        pack_path = env.prof_dir / contact_state.INPUT_PACK
        analysis_before = analysis_path.read_bytes()
        pack_before = pack_path.read_bytes()

        out = env.finalize(facts_path, proof, results)
        self.assertNotEqual(out["status"], "ok", out)
        self.assertEqual(out.get("reason_code"), "missing_paper_reference_title", out)
        # The failure names the pre-determined gap, field, paper key and direction
        # so the data owner can act without parsing prose.
        self.assertEqual(out.get("gap_id"), expected_gap_id, out)
        self.assertEqual(out.get("field"), "evidence", out)
        self.assertEqual(out.get("item_key"), CITATION_KEY, out)
        self.assertEqual(out.get("direction"), "DIR00001", out)
        self.assertIn("no trusted title", out.get("message") or "", out)
        self.assertNotIn(CITATION_TITLE, json.dumps(out, ensure_ascii=False), out)
        # The old managed files still hold the old title and raw evidence, and
        # their bytes are untouched by the failed render.
        before_pack = json.loads(pack_before.decode("utf-8"))
        before_gap = before_pack["directions"][0]["gap_shortlist"][0]
        self.assertEqual(
            before_gap["evidence"],
            f"后续由 {CITATION_KEY} 完成，日期 {ORDINARY_DATE}，"
            f"未知 {ORDINARY_EIGHT} 与 12345678 保留。")
        self.assertIn(CITATION_TITLE, analysis_before.decode("utf-8"))
        self.assertEqual(analysis_path.read_bytes(), analysis_before)
        self.assertEqual(pack_path.read_bytes(), pack_before)

        for form, reference in (
                ("markdown-link", "[未知论文](zotero://select/library/items/ZZZZ9999)"),
                ("bare-uri", "zotero://select/library/items/ZZZZ9999")):
            bad = self._fresh_env()
            facts_path = bad.write_facts()
            results = bad.root / "results"
            bad.write_stage2_results(results, {
                "AAAA1111": {"evidence": f"{reference} 没有可信记录。"}})
            plan = parse(bad.run_bound_stage2_plan(facts_path))
            self.assertEqual(plan["status"], "ok", plan)
            proof = facts_path.with_name(facts_path.stem + "-preflight.json")
            analysis_path = bad.prof_dir / contact_state.ANALYSIS_MD
            pack_path = bad.prof_dir / contact_state.INPUT_PACK
            self.assertFalse(analysis_path.exists(), form)
            self.assertFalse(pack_path.exists(), form)
            out = bad.finalize(facts_path, proof, results)
            self.assertNotEqual(out["status"], "ok", (form, out))
            self.assertEqual(out.get("reason_code"),
                             "missing_paper_reference_title", (form, out))
            self.assertEqual(out.get("gap_id"), expected_gap_id, (form, out))
            self.assertEqual(out.get("field"), "evidence", (form, out))
            self.assertEqual(out.get("item_key"), "ZZZZ9999", (form, out))
            self.assertEqual(out.get("direction"), "DIR00001", (form, out))
            self.assertIn("ZZZZ9999", json.dumps(out, ensure_ascii=False), form)
            self.assertFalse(analysis_path.exists(), form)
            self.assertFalse(pack_path.exists(), form)

    # -- U1-C ----------------------------------------------------------------

    def _attribution_env(self):
        env = self._fresh_env()

        def drop_summary(narrative):
            for entry in narrative["directions"]:
                entry["gap_notes"] = []
            entry["positioning"].append({
                "kind": "para", "text": "这里讨论后续论文依据：但仍是叙事。",
                "refs": [], "concrete_object": "合成叙事对象",
                "input_example": "输入一份叙事样本",
                "output_example": "得到一段叙事结论"})

        facts_path, results, proof = env.generate_pack(
            env.gap_override(), narrative_mutate=drop_summary)
        return env, facts_path, results, proof

    def test_u1_c_report_ownership_uses_real_fragments(self):
        env, facts_path, results, proof = self._attribution_env()
        lines = env.body_lines()
        evidence_title_line = next(
            index + 1 for index, line in enumerate(lines)
            if "后续论文依据：" in line and CITATION_TITLE in line)
        label_line = env.physical_line("评估时间：")
        continuation_line = env.physical_line("续行仍由")
        summary_line = next(
            index + 1 for index, line in enumerate(lines)
            if line.startswith("1. 【作者 future work】"))
        narrative_line = env.physical_line("这里讨论后续论文依据")

        report = env.write_report("u1c-report.json", [
            env.blocking_issue(CITATION_TITLE, evidence_title_line),
            env.blocking_issue("评估时间", "评估时间"),
            env.blocking_issue("续行仍由", continuation_line),
            env.blocking_issue("中译：Future", summary_line),
            env.blocking_issue("这里讨论后续论文依据", narrative_line),
            env.blocking_issue("依据：后续由", evidence_title_line),
        ])
        analysis_before = (env.prof_dir / contact_state.ANALYSIS_MD).read_bytes()
        recorded = env.record(report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertTrue(recorded["needs_owner_fix"], recorded)
        self.assertEqual((env.prof_dir / contact_state.ANALYSIS_MD).read_bytes(),
                         analysis_before)
        fixed = recorded["fixed_blocking"]
        self.assertEqual(sorted(fixed), ["DIR00001"], fixed)
        rows = fixed["DIR00001"]
        # Expected direction, gap and fields come from the fixture inputs and the
        # quote id, not from whatever the report happened to return.
        expected_direction = "DIR00001"
        expected_gap_id = contact_state.quote_id(self.gap_quotes["AAAA1111"])
        self.assertCountEqual(rows, [
            {"direction_id": expected_direction, "gap_id": expected_gap_id,
             "field": "evidence", "owner": "source"},
            {"direction_id": expected_direction, "gap_id": expected_gap_id,
             "field": "label", "owner": "generator"},
            {"direction_id": expected_direction, "gap_id": expected_gap_id,
             "field": "completed_part", "owner": "source"},
            {"direction_id": expected_direction, "gap_id": expected_gap_id,
             "field": "summary", "owner": "source"},
        ], rows)
        span_owners = {(row["owner"], row["field"]) for row in rows
                       if row["field"] in ("label", "evidence")}
        self.assertEqual(span_owners, {("generator", "label"), ("source", "evidence")},
                         rows)
        pack = env.pack()
        self.assertEqual(pack["validator"]["fixed_blocking"], fixed)
        pending = pack["validator"]["pending"]["DIR00001"]
        self.assertEqual(len(pending), 6, pending)

        # Both refine entries stop before any job/body write, even when filtered.
        for extra in ((), ("--direction-id", "DIR00001")):
            plan = env.refine_plan(report, *extra)
            self.assertEqual(plan["status"], "needs_owner_fix", plan)
            self.assertEqual(plan["reason_code"], "fixed_evidence_blocking", plan)
            self.assertEqual(plan["jobs"], [], plan)
            self.assertFalse(plan["write_needed"], plan)
            finalized = env.refine_finalize(results, report, *extra)
            self.assertEqual(finalized["status"], "needs_owner_fix", finalized)
            self.assertEqual(finalized["rewritten"], [], finalized)
        self.assertEqual((env.prof_dir / contact_state.ANALYSIS_MD).read_bytes(),
                         analysis_before)

        # An existing excluded region is not promoted into a legal fixed finding.
        excluded_env = self._fresh_env()
        excluded_facts, excluded_results, excluded_proof = excluded_env.generate_pack(
            excluded_env.gap_override())
        user_note_line = excluded_env.physical_line(
            "> 我想比较两种合成输入的处理结果。")
        excluded = excluded_env.write_report("u1c-excluded.json", [
            excluded_env.blocking_issue("我想比较两种合成输入", user_note_line)])
        pack_before = (excluded_env.prof_dir / contact_state.INPUT_PACK).read_bytes()
        refused = excluded_env.record(excluded)
        self.assertNotIn(refused["status"], {"ok", "needs_correction"}, refused)
        self.assertEqual(refused.get("reason_code"), "validation_issue_not_repairable",
                         refused)
        self.assertEqual((excluded_env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         pack_before)

    # -- U1-D ----------------------------------------------------------------

    def test_u1_d_narrative_two_rounds_and_fixed_stop(self):
        env = self._fresh_env()

        def add_narrative_block(narrative):
            narrative["directions"][0]["positioning"].append({
                "kind": "para", "text": "纯叙事待改文字。", "refs": [],
                "concrete_object": "合成叙事对象",
                "input_example": "输入一份叙事样本",
                "output_example": "得到一段叙事结论"})

        facts_path, results, proof = env.generate_pack(narrative_mutate=add_narrative_block)
        narrative_line = env.physical_line("纯叙事待改文字")
        report = env.write_report("u1d-round1.json", [
            env.blocking_issue("纯叙事待改文字", narrative_line)])
        recorded = env.record(report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertFalse(recorded["needs_owner_fix"], recorded)
        self.assertEqual(recorded["fixed_blocking"], {}, recorded)

        plan = env.refine_plan(report)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["DIR00001"],
                         plan)
        rewrite = env.write_narrative_rewrite("纯叙事待改文字", "纯叙事已改文字")
        refined = env.refine_finalize(rewrite, report)
        self.assertEqual(refined["status"], "ok", refined)
        self.assertEqual(refined["phase"], "awaiting_second_validation", refined)
        self.assertTrue(refined["round_retained"], refined)
        pack = env.pack()
        self.assertEqual(pack["validator"]["round"], 1, pack["validator"])
        self.assertIn("纯叙事已改文字", env.document()["body"])

        # Round 2 hits fixed card text: terminal, no third round, owner recorded.
        fixed_line = env.physical_line("评估时间：", expected=2)[0]
        round2 = env.write_report("u1d-round2.json", [
            env.blocking_issue("评估时间：", fixed_line)])
        terminal = env.record(round2)
        self.assertEqual(terminal["status"], "ok", terminal)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        self.assertTrue(terminal["needs_owner_fix"], terminal)
        pack = env.pack()
        self.assertEqual(pack["validator"]["results"]["DIR00001"]["result"],
                         "fail_after_2_rounds")
        self.assertEqual(pack["validator"]["fixed_blocking"]["DIR00001"][0]["owner"],
                         "generator")
        stopped = env.refine_plan(round2)
        self.assertEqual(stopped["status"], "needs_owner_fix", stopped)
        self.assertEqual(stopped["jobs"], [], stopped)

        minor_env = self._fresh_env()
        minor_facts, minor_results, minor_proof = minor_env.generate_pack(
            minor_env.gap_override())
        minor_line = next(index + 1 for index, line in enumerate(minor_env.body_lines())
                          if "评估时间：" in line)
        minor = minor_env.write_report("u1d-minor.json", [
            minor_env.minor_issue(CITATION_TITLE, minor_line)])
        recorded = minor_env.record(minor)
        self.assertEqual(recorded["status"], "ok", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertFalse(recorded["needs_owner_fix"], recorded)
        self.assertEqual(recorded["fixed_blocking"], {}, recorded)
        self.assertEqual(minor_env.pack()["validator"]["results"]["DIR00001"]["result"],
                         "pass")

    # -- U1-E ----------------------------------------------------------------

    def test_u1_e_old_pack_updates_through_process_to_finalize(self):
        env = self._fresh_env()
        facts_path, results, proof = env.generate_pack(env.gap_override())
        self.assertIn(CITATION_TITLE, env.document()["body"])
        pack = env.pack()
        direction = pack["directions"][0]
        entry = pack["cache"]["render"][contact_state.ANALYSIS_MD]
        old_body = env.document()["body"]
        old_body = old_body.replace(
            f"[{CITATION_TITLE}](zotero://select/library/items/{CITATION_KEY})",
            CITATION_KEY)
        old_sha = contact_state.sha256_text(old_body)
        entry.pop("ownership", None)
        entry.pop("u1", None)
        entry["sha256"] = old_sha
        for item in direction["completed_gap_blacklist"]:
            item.pop("candidate_paper_ids", None)
        env.write_pack(pack)
        (env.prof_dir / contact_state.ANALYSIS_MD).write_text(
            contact_state.render_frontmatter(
                contact_state.stage2_pack_state_fingerprint(pack), old_sha) + old_body,
            encoding="utf-8")

        old_preflight = env.preflight()
        self.assertEqual(old_preflight["action"], "process", old_preflight)
        self.assertIn("fixed_evidence_display_update",
                      old_preflight["reason_codes"], old_preflight)
        direction_row = next(row for row in old_preflight["directions"]
                             if row["direction_id"] == "DIR00001")
        self.assertEqual(direction_row["action"], "process", direction_row)
        self.assertIn("fixed_evidence_display_update",
                      direction_row["reason_codes"], direction_row)
        proof_path = env.root / "u1e-preflight.json"
        proof_path.write_text(json.dumps(old_preflight, ensure_ascii=False),
                             encoding="utf-8")
        env.bind_facts_to_preflight(facts_path, old_preflight)

        plan = parse(run_cli("stage2-plan", "--facts", facts_path,
                             "--preflight-file", proof_path))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(plan["jobs"], [], plan)
        self.assertFalse(plan["write_needed"], plan)

        finalized = env.finalize(facts_path, proof_path, results)
        self.assertEqual(finalized["status"], "ok", finalized)
        self.assertNotIn(CITATION_KEY, env.without_links("\n".join(env.card_lines())))
        self.assertIn(CITATION_LINK, env.document()["body"])
        pack = env.pack()
        self.assertEqual(pack["cache"]["render"][contact_state.ANALYSIS_MD]["u1"]
                         ["display_version"], contact_state.STAGE2_U1_DISPLAY_VERSION)
        self.assertIsInstance(
            pack["cache"]["render"][contact_state.ANALYSIS_MD]["ownership"], dict)
        self.assertEqual(
            pack["directions"][0]["completed_gap_blacklist"][0]["candidate_paper_ids"],
            [CITATION_KEY])

        env.record(env.write_report("u1e-pass.json", []))
        again = env.preflight()
        self.assertEqual(again["action"], "reuse_all", again)
        self.assertNotIn("fixed_evidence_display_update", again["reason_codes"], again)

        # No valid cache record: the update must go back through the structured
        # freshness results instead of guessing a candidate list from prose.
        cache_path = env.prof_dir / contact_state.FRESHNESS_CACHE
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        cache["entries"] = {}
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        pack = env.pack()
        entry = pack["cache"]["render"][contact_state.ANALYSIS_MD]
        entry.pop("u1", None)
        env.write_pack(pack)
        proof_path, payload = env.save_preflight("u1e-preflight-2.json")
        self.assertEqual(payload["action"], "process", payload)
        refreshed = next(row for row in payload["directions"]
                         if row["direction_id"] == "DIR00001")
        self.assertIn("freshness_cache_changed", refreshed["reason_codes"], refreshed)
        env.bind_facts_to_preflight(facts_path, payload)
        plan = parse(run_cli("stage2-plan", "--facts", facts_path,
                             "--preflight-file", proof_path))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertTrue(any(job["kind"] == "freshness" for job in plan["jobs"]),
                        "a missing cache must demand structured freshness results")
        out = env.finalize(facts_path, proof_path, results)
        self.assertEqual(out["status"], "ok", out)
        card = "\n".join(env.card_lines())
        self.assertIn(CITATION_LINK, card)
        self.assertNotIn(CITATION_KEY, env.without_links(card))

    # -- U1-F ----------------------------------------------------------------

    def test_u1_f_acceptance_separates_body_business_binding_and_validator(self):
        env = self._fresh_env()
        facts_path, results, proof = env.generate_pack(env.gap_override())
        env.record(env.write_report("u1f-pass.json", []))
        validator_before = copy.deepcopy(env.pack()["validator"])
        self.assertEqual(validator_before["phase"], "terminal")
        document_before = env.document()
        analysis_bytes = (env.prof_dir / contact_state.ANALYSIS_MD).read_bytes()

        # Only the generation time changes: body bytes and two-round state stay.
        out = env.finalize(facts_path, proof, results)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual((env.prof_dir / contact_state.ANALYSIS_MD).read_bytes(),
                         analysis_bytes)
        pack = env.pack()
        self.assertEqual(pack["validator"]["validation_sha256"],
                         validator_before["validation_sha256"])
        self.assertEqual(pack["validator"]["round"], validator_before["round"])
        self.assertEqual(pack["validator"]["phase"], validator_before["phase"])
        self.assertEqual(pack["validator"]["results"], validator_before["results"])

        # An equivalent body with a stale header still gets the machine header
        # corrected, without rewriting the body.
        header_pack = env.pack()
        header_pack.pop("validator", None)
        env.write_pack(header_pack)
        rows = env.document()["body"].splitlines()
        header_pack = env.pack()
        header, body = contact_state.split_frontmatter(
            (env.prof_dir / contact_state.ANALYSIS_MD).read_text(encoding="utf-8"))
        (env.prof_dir / contact_state.ANALYSIS_MD).write_text(
            contact_state.render_frontmatter("0" * 64, contact_state.sha256_text(body))
            + body, encoding="utf-8")
        body_before = body
        out = env.finalize(facts_path, proof, results)
        self.assertEqual(out["status"], "ok", out)
        document = env.document()
        self.assertEqual(document["body"], body_before)
        self.assertEqual(document["header"]["state_fingerprint"],
                         contact_state.stage2_pack_state_fingerprint(env.pack()))

        # A real body/business change starts a fresh validation version.
        env.record(env.write_report("u1f-pass-2.json", []))
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        facts["directions"][0]["user_note"] = "新的用户笔记会改变正文与指纹。"
        Path(facts_path).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        env.save_preflight("u1f-preflight.json")
        plan = parse(run_cli("stage2-plan", "--facts", facts_path,
                             "--preflight-file", env.root / "u1f-preflight.json"))
        self.assertEqual(plan["status"], "ok", plan)
        out = parse(run_cli("stage2-finalize", "--facts", facts_path,
                            "--preflight-file", env.root / "u1f-preflight.json",
                            "--results", results))
        self.assertEqual(out["status"], "ok", out)
        self.assertIsNone(env.pack().get("validator"))
        self.assertIn("新的用户笔记", env.document()["body"])

        # A business-fingerprint change whose visible body is equivalent still
        # expires the old certification and refreshes only the header.
        env.record(env.write_report("u1f-pass-3.json", []))
        body_before = env.document()["body"]
        facts = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        facts["directions"][0]["credibility"]["note"] = "只影响指纹不进入正文的说明"
        Path(facts_path).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        preflight_payload = env.preflight()
        proof_path = env.root / "u1f-preflight-2.json"
        proof_path.write_text(json.dumps(preflight_payload, ensure_ascii=False),
                              encoding="utf-8")
        env.bind_facts_to_preflight(facts_path, preflight_payload)
        plan = parse(run_cli("stage2-plan", "--facts", facts_path,
                             "--preflight-file", proof_path))
        self.assertEqual(plan["status"], "ok", plan)
        out = parse(run_cli("stage2-finalize", "--facts", facts_path,
                            "--preflight-file", proof_path, "--results", results))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(env.document()["body"], body_before)
        self.assertIsNone(env.pack().get("validator"))

        # An invalid old binding with no business change is rejected, untouched.
        stale_env = self._fresh_env()
        stale_facts, stale_results, stale_proof = stale_env.generate_pack()
        stale_env.record(stale_env.write_report("u1f-stale-pass.json", []))
        analysis_path = stale_env.prof_dir / contact_state.ANALYSIS_MD
        analysis_path.write_text(
            analysis_path.read_text(encoding="utf-8") + "\n人工改动。\n",
            encoding="utf-8")
        protected = analysis_path.read_bytes()
        out = stale_env.finalize(stale_facts, stale_proof, stale_results)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out.get("reason_code"), "validation_render_stale", out)
        self.assertEqual(analysis_path.read_bytes(), protected)

        # The source line only ignores its generated timestamp: another text
        # change on the same line is a real body change, not an equivalent render.
        # Remove the old validator and re-bind the header/cache to the edited body
        # so the only possible explanation for a write is the line comparison.
        line_env = self._fresh_env()
        line_facts, line_results, line_proof = line_env.generate_pack()
        line_pack = line_env.pack()
        line_pack.pop("validator", None)
        line_env.write_pack(line_pack)
        analysis_path = line_env.prof_dir / contact_state.ANALYSIS_MD
        raw = analysis_path.read_text(encoding="utf-8")
        changed = raw.replace("全文级 2 篇", "全文级 9 篇", 1)
        self.assertNotEqual(changed, raw)
        header, edited_body = contact_state.split_frontmatter(changed)
        edited_sha = contact_state.sha256_text(edited_body)
        analysis_path.write_text(
            contact_state.render_frontmatter(header["state_fingerprint"], edited_sha)
            + edited_body, encoding="utf-8")
        line_pack = line_env.pack()
        render_entry = line_pack["cache"]["render"][contact_state.ANALYSIS_MD]
        render_entry["sha256"] = edited_sha
        render_entry["ownership"]["body_sha256"] = edited_sha
        line_env.write_pack(line_pack)
        out = line_env.finalize(line_facts, line_proof, line_results)
        self.assertEqual(out["status"], "ok", out)
        repaired = line_env.document()["body"]
        self.assertIn("全文级 2 篇", repaired)
        self.assertNotIn("全文级 9 篇", repaired)

        # With no old validator, a manual body edit still requires a decision.
        manual_env = self._fresh_env()
        manual_facts, manual_results, manual_proof = manual_env.generate_pack()
        pack = manual_env.pack()
        pack.pop("validator", None)
        manual_env.write_pack(pack)
        analysis_path = manual_env.prof_dir / contact_state.ANALYSIS_MD
        analysis_path.write_text(
            analysis_path.read_text(encoding="utf-8") + "\n人工改动。\n",
            encoding="utf-8")
        protected = analysis_path.read_bytes()
        out = manual_env.finalize(manual_facts, manual_proof, manual_results)
        self.assertEqual(out["status"], "needs_decision", out)
        self.assertEqual(analysis_path.read_bytes(), protected)


if __name__ == "__main__":
    import unittest
    unittest.main()
