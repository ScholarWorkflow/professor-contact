"""U1 fixed-evidence display and real blocker ownership (test plan t5).

Covers the six must-test targets of ``plan/stage2-fixed-evidence/test-plan.md``:
trusted citation display (U1-A), missing-metadata handoff (U1-B), real fragment
ownership in validation reports (U1-C), fixed blockers stopping the model
rewrite while narrative keeps two rounds (U1-D), old-pack update through the
ordinary preflight -> process -> finalize path (U1-E), and the ordinary
acceptance split between body, business state, binding and old validation
(U1-F).

The branches added for stage2-u1-t5 encode the r5 contracts that the current
product does not implement yet: a display-only reference whose current record
has no title, the renderer map as the only direction authority, raw managed
body bytes for the preflight/record/refine/acceptance bindings, and the
``display_version`` 2 marker.  They therefore fail on the pre-r5 product until
the product owner lands the r5 implementation.
"""
import copy
import hashlib
import json
import re
from pathlib import Path

from test_contact_state import (
    BaseEnv,
    contact_state,
    parse,
    run_cli,
    stage2_style_validation_report,
)
from stage2_upstream_fixture import run_bound_stage2_finalize, prepare_consumption

CITATION_KEY = "CCCC3333"
CITATION_TITLE = "Unrelated synthetic example"
CITATION_LINK = f"[{CITATION_TITLE}](zotero://select/library/items/{CITATION_KEY})"
ORDINARY_EIGHT = "DDDD8888"
ORDINARY_DATE = "2024-05-01"
DISPLAY_ONLY_KEY = "EEEE4444"
DISPLAY_ONLY_TITLE = "Obsidian atlas archival reference"
DISPLAY_ONLY_LINK = (
    f"[{DISPLAY_ONLY_TITLE}](zotero://select/library/items/{DISPLAY_ONLY_KEY})")
DISPLAY_ONLY_EVIDENCE = (
    f"显示参考 zotero://select/library/items/{DISPLAY_ONLY_KEY}，证据原句保留。")
DISPLAY_ONLY_RENDERED = f"- 后续论文依据：显示参考 {DISPLAY_ONLY_LINK}，证据原句保留。"
U1_TARGET_DISPLAY_VERSION = 3
GENERATED_STAMP_RE = re.compile(
    (r"(?m)^> (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) ｜ 数据来源：")
    .encode("utf-8"))
FAKE_HEADING_QUOTE = "中文🙂固定续行"
FAKE_HEADING_LINE = f"## 方向 假方向：{FAKE_HEADING_QUOTE}"


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
        prepared = prepare_consumption(run_cli, facts_path)
        if prepared.returncode != 0:
            raise AssertionError(f"consumption fixture failed: {prepared.stdout} {prepared.stderr}")
        result = json.loads(prepared.stdout)
        if result.get("status") != "ok":
            raise AssertionError(f"consumption fixture not ready: {result}")

    def finalize(self, facts_path, proof, results, *extra):
        return parse(run_bound_stage2_finalize(
            run_cli, facts_path, "--results", results, *extra))

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

    # -- t5 byte-level observation helpers (test plan §6.1) -------------------

    def managed_path(self):
        return self.prof_dir / contact_state.ANALYSIS_MD

    def managed_parts(self):
        """The real header bytes and body bytes, read straight from disk."""
        raw = self.managed_path().read_bytes()
        self.assertTrue(raw.startswith(b"---\n"), raw[:40])
        end = raw.find(b"\n---\n", 4)
        self.assertGreaterEqual(end, 0, raw[:200])
        start = end + len(b"\n---\n") + 1
        self.assertEqual(raw[start - 1:start], b"\n", raw[end:start + 2])
        return raw[:start], raw[start:]

    def write_managed_parts(self, header, body):
        self.managed_path().write_bytes(header + body)

    def body_digest(self, body):
        return hashlib.sha256(body).hexdigest()

    def display_version(self):
        return self.pack()["cache"]["render"][contact_state.ANALYSIS_MD][
            "u1"]["display_version"]

    def set_display_version(self, version):
        pack = self.pack()
        pack["cache"]["render"][contact_state.ANALYSIS_MD][
            "u1"]["display_version"] = version
        self.write_pack(pack)

    def rewrite_consistent_input(self, body):
        """§6.1(7): keep the old hash/map/header consistent with actual bytes."""
        pack = self.pack()
        digest = self.body_digest(body)
        entry = pack["cache"]["render"][contact_state.ANALYSIS_MD]
        ownership = entry.get("ownership")
        self.assertIsInstance(ownership, dict)
        entry["sha256"] = digest
        ownership["body_sha256"] = digest
        header = contact_state.render_frontmatter(
            contact_state.stage2_pack_state_fingerprint(pack), digest)
        self.write_managed_parts(header.encode("utf-8"), body)
        self.write_pack(pack)

    def assert_ownership_matches_body(self, body):
        pack = self.pack()
        entry = pack["cache"]["render"][contact_state.ANALYSIS_MD]
        ownership = entry["ownership"]
        digest = self.body_digest(body)
        lines = body.decode("utf-8").splitlines()
        self.assertEqual(entry["sha256"], digest)
        self.assertEqual(ownership["body_sha256"], digest)
        self.assertEqual(ownership["line_count"], len(lines))
        for fragment in ownership["fragments"]:
            for line_no, start, end in fragment["ranges"]:
                self.assertGreaterEqual(line_no, 0)
                self.assertLess(line_no, len(lines))
                self.assertGreaterEqual(start, 0)
                self.assertLessEqual(start, end)
                self.assertLessEqual(end, len(lines[line_no]))
        return ownership

    def record_pass(self, name):
        report = self.write_report(name, [])
        recorded = self.record(report)
        self.assertEqual(recorded["status"], "ok", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertTrue(recorded["terminal"], recorded)
        return report

    def bind_proof(self, facts_path, payload, name):
        proof = self.root / name
        proof.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        self.bind_facts_to_preflight(facts_path, payload)
        return proof

    def stage2_plan(self, facts_path, proof):
        return parse(run_cli("stage2-plan", "--facts", facts_path,
                             "--preflight-file", proof))

    def add_display_reference_paper(self, facts):
        facts["papers"].append({
            "item_key": DISPLAY_ONLY_KEY, "title": DISPLAY_ONLY_TITLE,
            "year": 1900, "authors": [], "authorship": "unknown",
            "has_pdf": False})

    def display_reference_overrides(self):
        overrides = self.gap_override()
        overrides["AAAA1111"]["evidence"] = DISPLAY_ONLY_EVIDENCE
        return overrides

    def display_reference_line(self):
        return next(line for line in self.body_lines()
                    if line.startswith("- 后续论文依据：显示参考"))

    def direction_snapshot(self):
        direction = self.pack()["directions"][0]
        return {
            "supporting": sorted(direction.get("supporting_item_keys") or []),
            "relevant": list(direction.get("relevant_keys") or []),
            "named": sorted(direction.get("named_keys") or []),
            "narrative": copy.deepcopy(direction.get("narrative")),
            "gaps": copy.deepcopy(direction.get("gap_shortlist")),
            "blacklist": copy.deepcopy(direction.get("completed_gap_blacklist")),
        }

    def cache_entries(self):
        cache = json.loads(
            (self.prof_dir / contact_state.FRESHNESS_CACHE).read_text(encoding="utf-8"))
        return copy.deepcopy(cache.get("entries") or {})

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
        translation_line = f"- 中译：{gap['translation_zh']}"
        explanation = direction["narrative"]["gap_notes"][gap["gap_id"]]["explanation"]
        translation_index = lines.index(translation_line)
        self.assertEqual(lines[translation_index + 1], f"- 大白话：{explanation}")
        self.assertEqual(lines[translation_index + 2], "- 页码：p.8（Conclusion）")
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

        # A display-only reference whose current record exists but has no trusted
        # title must fail before writing instead of borrowing the old canonical
        # title (r5 §3.1.4). EEEE4444 is not a member/named/relevant key, so the
        # direction fingerprint and the accepted membership stay unchanged.
        null_env = self._fresh_env()
        null_facts, null_results, _null_proof = null_env.generate_pack(
            null_env.display_reference_overrides(),
            mutate_facts=null_env.add_display_reference_paper)
        self.assertIn(DISPLAY_ONLY_KEY, null_env.pack()["papers"])
        self.assertEqual(null_env.display_reference_line(), DISPLAY_ONLY_RENDERED)
        null_env.set_display_version(1)
        null_snapshot = null_env.direction_snapshot()
        self.assertEqual(null_snapshot["supporting"],
                         ["AAAA1111", "BBBB2222", "CCCC3333"])
        self.assertEqual(null_snapshot["relevant"], ["AAAA1111", "BBBB2222"])
        self.assertEqual(
            null_env.pack()["directions"][0]["narrative_later_papers"], {})
        null_gap_id = contact_state.quote_id(self.gap_quotes["AAAA1111"])
        self.assertEqual(
            [row["evidence"] for row in null_env.pack()["directions"][0]["gap_shortlist"]
             if row["gap_id"] == null_gap_id], [DISPLAY_ONLY_EVIDENCE])
        facts = json.loads(Path(null_facts).read_text(encoding="utf-8"))
        next(paper for paper in facts["papers"]
             if paper["item_key"] == DISPLAY_ONLY_KEY)["title"] = None
        Path(null_facts).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        analysis_path = null_env.prof_dir / contact_state.ANALYSIS_MD
        pack_path = null_env.prof_dir / contact_state.INPUT_PACK
        freshness_path = null_env.prof_dir / contact_state.FRESHNESS_CACHE

        proof_path, payload = null_env.save_preflight("u1b-null-preflight.json")
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("fixed_evidence_display_update", payload["reason_codes"], payload)
        null_direction = next(row for row in payload["directions"]
                              if row["direction_id"] == "DIR00001")
        self.assertIn("fixed_evidence_display_update",
                      null_direction["reason_codes"], null_direction)
        null_env.bind_facts_to_preflight(null_facts, payload)
        plan = null_env.stage2_plan(null_facts, proof_path)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(plan["jobs"], [], plan)
        self.assertFalse(plan["write_needed"], plan)
        ctx = contact_state.Stage2Context(Path(null_facts))
        plan_entry = next(entry for entry in ctx.direction_plans
                          if entry["did"] == "DIR00001")
        self.assertTrue(plan_entry["reuse"], plan_entry)
        old_entry = plan_entry["old"]
        old_fingerprint = old_entry.get("provisional_input_fingerprint") \
            or old_entry["input_fingerprint"]
        self.assertEqual(plan_entry["fingerprint"], old_fingerprint)

        analysis_before = analysis_path.read_bytes()
        pack_before = pack_path.read_bytes()
        facts_before = Path(null_facts).read_bytes()
        freshness_before = freshness_path.read_bytes()
        out = null_env.finalize(null_facts, proof_path, null_results)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "missing_paper_reference_title", out)
        self.assertEqual(out.get("direction"), "DIR00001", out)
        self.assertEqual(out.get("gap_id"), expected_gap_id, out)
        self.assertEqual(out.get("field"), "evidence", out)
        self.assertEqual(out.get("item_key"), DISPLAY_ONLY_KEY, out)
        self.assertIn("no trusted title", out.get("message") or "", out)
        self.assertNotIn(DISPLAY_ONLY_TITLE, json.dumps(out, ensure_ascii=False), out)
        self.assertEqual(analysis_path.read_bytes(), analysis_before)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(Path(null_facts).read_bytes(), facts_before)
        self.assertEqual(freshness_path.read_bytes(), freshness_before)
        self.assertEqual(null_env.display_version(), 1)
        self.assertEqual(null_env.direction_snapshot(), null_snapshot)

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

        overrides = env.gap_override()
        overrides["AAAA1111"]["completed_part"] = (
            f"{CITATION_LINK} 已完成一部分；\n## 方向 假方向：{FAKE_HEADING_QUOTE}")
        facts_path, results, proof = env.generate_pack(
            overrides, narrative_mutate=drop_summary)
        return env, facts_path, results, proof

    def test_u1_c_report_ownership_uses_real_fragments(self):
        env, facts_path, results, proof = self._attribution_env()
        lines = env.body_lines()
        evidence_title_line = next(
            index + 1 for index, line in enumerate(lines)
            if "后续论文依据：" in line and CITATION_TITLE in line)
        summary_line = next(
            index + 1 for index, line in enumerate(lines)
            if line.startswith("1. 【作者 future work】"))
        narrative_line = env.physical_line("这里讨论后续论文依据")

        # The source value itself contains a real `## 方向 ` continuation line.
        # The character view locates it exactly; the UTF-8 prefix length differs
        # from the character start, so a byte/character mix-up cannot pass.
        body_view = env.document()["body"]
        self.assertEqual(body_view.splitlines().count(FAKE_HEADING_LINE), 1)
        quote_start = FAKE_HEADING_LINE.index(FAKE_HEADING_QUOTE)
        quote_end = quote_start + len(FAKE_HEADING_QUOTE)
        self.assertEqual(FAKE_HEADING_LINE[quote_start:quote_end], FAKE_HEADING_QUOTE)
        self.assertNotEqual(len(FAKE_HEADING_LINE[:quote_start].encode("utf-8")),
                            quote_start)

        report = env.write_report("u1c-report.json", [
            env.blocking_issue(CITATION_TITLE, evidence_title_line),
            env.blocking_issue("评估时间", "评估时间"),
            env.blocking_issue(FAKE_HEADING_QUOTE, "固定续行"),
            env.blocking_issue("中译：Future", summary_line),
            env.blocking_issue("这里讨论后续论文依据", narrative_line),
            env.blocking_issue("依据：后续由", evidence_title_line),
        ])
        analysis_before = (env.prof_dir / contact_state.ANALYSIS_MD).read_bytes()
        report_bytes = Path(report).read_bytes()
        recorded = env.record(report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertTrue(recorded["needs_owner_fix"], recorded)
        self.assertEqual((env.prof_dir / contact_state.ANALYSIS_MD).read_bytes(),
                         analysis_before)
        self.assertEqual(Path(report).read_bytes(), report_bytes)
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
        validator = pack["validator"]
        self.assertEqual(validator["fixed_blocking"], fixed)
        pending = validator["pending"]["DIR00001"]
        # The raw report stays intact: original issues/notes/verdict are kept and
        # the pending rows are exactly those issues, not a rewritten summary.
        raw_report = json.loads(Path(report).read_text(encoding="utf-8"))
        original_issues = raw_report["files"][0]["issues"]
        self.assertEqual(len(original_issues), 6, original_issues)
        self.assertEqual(pending, original_issues)
        self.assertEqual(validator["issues"], original_issues)
        self.assertEqual(validator["notes"], raw_report["notes"])
        self.assertEqual(validator["raw_verdict"], "fail")

        # Both refine entries stop before any job/body write, even when filtered.
        pack_before = (env.prof_dir / contact_state.INPUT_PACK).read_bytes()
        for extra in ((), ("--direction-id", "DIR00001")):
            plan = env.refine_plan(report, *extra)
            self.assertEqual(plan["status"], "needs_owner_fix", plan)
            self.assertEqual(plan["reason_code"], "fixed_evidence_blocking", plan)
            self.assertEqual(plan["jobs"], [], plan)
            self.assertFalse(plan["write_needed"], plan)
            self.assertEqual((env.prof_dir / contact_state.ANALYSIS_MD).read_bytes(),
                             analysis_before)
            self.assertEqual((env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                             pack_before)
            self.assertEqual(Path(report).read_bytes(), report_bytes)
            finalized = env.refine_finalize(results, report, *extra)
            self.assertEqual(finalized["status"], "needs_owner_fix", finalized)
            self.assertEqual(finalized["rewritten"], [], finalized)
            self.assertEqual((env.prof_dir / contact_state.ANALYSIS_MD).read_bytes(),
                             analysis_before)
            self.assertEqual((env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                             pack_before)
            self.assertEqual(Path(report).read_bytes(), report_bytes)

        # The generated link punctuation and Zotero destination belong to the
        # generator, not to the source that supplied the paper facts.
        link_env = self._fresh_env()
        link_facts, link_results, link_proof = link_env.generate_pack(
            link_env.gap_override())
        link_url = f"zotero://select/library/items/{CITATION_KEY}"
        link_line = next(
            index + 1 for index, line in enumerate(link_env.body_lines())
            if "后续论文依据：" in line and link_url in line)
        link_report = link_env.write_report("u1c-link.json", [
            link_env.blocking_issue(link_url, link_line)])
        link_recorded = link_env.record(link_report)
        self.assertEqual(link_recorded["status"], "needs_correction", link_recorded)
        link_gap_id = contact_state.quote_id(link_env.gap_quotes["AAAA1111"])
        link_rows = link_recorded["fixed_blocking"]["DIR00001"]
        self.assertIn({"direction_id": "DIR00001", "gap_id": link_gap_id,
                       "field": "evidence", "owner": "generator"}, link_rows)
        self.assertNotIn({"direction_id": "DIR00001", "gap_id": link_gap_id,
                          "field": "evidence", "owner": "source"}, link_rows)

        # The blacklist evidence uses the same split: its generated link is a
        # generator problem, while the completed-paper title remains source.
        blacklist_env = self._fresh_env()
        blacklist_overrides = blacklist_env.gap_override()
        blacklist_overrides["BBBB2222"] = {
            "status": "done_by_self",
            "candidate_paper_ids": [CITATION_KEY],
            "evidence": "zotero://select/library/items/AAAA1111 已接住该点。",
        }
        blacklist_facts, blacklist_results, blacklist_proof = blacklist_env.generate_pack(
            blacklist_overrides)
        blacklist_url = "zotero://select/library/items/AAAA1111"
        blacklist_line = next(
            index + 1 for index, line in enumerate(blacklist_env.body_lines())
            if blacklist_url in line and "依据：" in line)
        blacklist_report = blacklist_env.write_report("u1c-blacklist-link.json", [
            blacklist_env.blocking_issue(blacklist_url, blacklist_line)])
        blacklist_recorded = blacklist_env.record(blacklist_report)
        self.assertEqual(blacklist_recorded["status"], "needs_correction",
                         blacklist_recorded)
        blacklist_gap_id = contact_state.quote_id(
            blacklist_env.gap_quotes["BBBB2222"])
        blacklist_rows = blacklist_recorded["fixed_blocking"]["DIR00001"]
        self.assertIn({"direction_id": "DIR00001", "gap_id": blacklist_gap_id,
                       "field": "blacklist_evidence", "owner": "generator"},
                      blacklist_rows)

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

        # One real lifecycle proves the B-absent fallback, the pack-only refine
        # and the pending preservation on ordinary acceptance (t5 §6.4).
        pending_env = self._fresh_env()

        def add_pending_block(narrative):
            narrative["directions"][0]["positioning"].append({
                "kind": "para", "text": "纯叙事待改文字。", "refs": [],
                "concrete_object": "合成叙事对象",
                "input_example": "输入一份叙事样本",
                "output_example": "得到一段叙事结论"})

        pending_facts, pending_results, _pending_proof = pending_env.generate_pack(
            pending_env.display_reference_overrides(),
            mutate_facts=pending_env.add_display_reference_paper,
            narrative_mutate=add_pending_block)
        pending_env.set_display_version(1)
        pending_snapshot = pending_env.direction_snapshot()
        pending_cache = pending_env.cache_entries()
        # B-absent: the current facts no longer carry the display-only record; the
        # accepted canonical record is the only remaining source.
        facts = json.loads(Path(pending_facts).read_text(encoding="utf-8"))
        facts["papers"] = [paper for paper in facts["papers"]
                           if paper["item_key"] != DISPLAY_ONLY_KEY]
        Path(pending_facts).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        proof_path, payload = pending_env.save_preflight("u1d-preflight.json")
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("fixed_evidence_display_update", payload["reason_codes"], payload)
        pending_env.bind_facts_to_preflight(pending_facts, payload)
        plan = pending_env.stage2_plan(pending_facts, proof_path)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(plan["jobs"], [], plan)
        accepted = pending_env.finalize(pending_facts, proof_path, pending_results)
        self.assertEqual(accepted["status"], "ok", accepted)
        self.assertEqual(pending_env.display_reference_line(), DISPLAY_ONLY_RENDERED)
        self.assertEqual(pending_env.display_version(), U1_TARGET_DISPLAY_VERSION)
        accepted_body = pending_env.managed_parts()[1]
        accepted_ownership = pending_env.assert_ownership_matches_body(accepted_body)
        self.assertEqual(accepted_ownership["body_sha256"],
                         pending_env.body_digest(accepted_body))
        self.assertEqual(pending_env.document()["header"]["render_sha256"],
                         pending_env.body_digest(accepted_body))
        pack = pending_env.pack()
        self.assertEqual(pack["papers"][DISPLAY_ONLY_KEY]["title"], DISPLAY_ONLY_TITLE)
        gap_id = contact_state.quote_id(pending_env.gap_quotes["AAAA1111"])
        self.assertEqual(
            [row["evidence"] for row in pack["directions"][0]["gap_shortlist"]
             if row["gap_id"] == gap_id], [DISPLAY_ONLY_EVIDENCE])
        after_absent = pending_env.direction_snapshot()
        self.assertEqual(after_absent["supporting"], pending_snapshot["supporting"])
        self.assertEqual(after_absent["relevant"], pending_snapshot["relevant"])
        self.assertEqual(after_absent["narrative"], pending_snapshot["narrative"])
        self.assertEqual(after_absent["gaps"], pending_snapshot["gaps"])
        self.assertEqual(after_absent["blacklist"], pending_snapshot["blacklist"])
        self.assertEqual(pending_env.cache_entries(), pending_cache)

        # Round 1: a pure narrative blocking is a legal pending state.
        pending_line = pending_env.physical_line("纯叙事待改文字")
        report = pending_env.write_report("u1d-pending.json", [
            pending_env.blocking_issue("纯叙事待改文字", pending_line)])
        recorded = pending_env.record(report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertFalse(recorded["needs_owner_fix"], recorded)
        self.assertEqual(recorded["fixed_blocking"], {}, recorded)
        validator_before = copy.deepcopy(pending_env.pack()["validator"])
        report_bytes = Path(report).read_bytes()
        body_before = pending_env.managed_parts()[1]

        out = pending_env.finalize(pending_facts, proof_path, pending_results)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(pending_env.managed_parts()[1], body_before)
        validator_after = pending_env.pack()["validator"]
        for field in ("round", "phase", "pending", "results", "issues", "notes",
                      "raw_verdict", "validation_sha256", "render_sha256"):
            self.assertEqual(validator_after[field], validator_before[field], field)
        self.assertEqual(validator_after["pack_sha256"],
                         contact_state.stage2_pack_content_fingerprint(pending_env.pack()))
        self.assertEqual(Path(report).read_bytes(), report_bytes)

        # Pack-only refinement: delete the /tmp facts file first to prove the
        # refinement consumes only the accepted canonical pack.
        facts_bytes = Path(pending_facts).read_bytes()
        Path(pending_facts).unlink()
        plan = pending_env.refine_plan(report)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["DIR00001"], plan)
        rewrite = pending_env.write_narrative_rewrite("纯叙事待改文字", "纯叙事已改文字")
        refined = pending_env.refine_finalize(rewrite, report)
        self.assertEqual(refined["status"], "ok", refined)
        self.assertEqual(refined["phase"], "awaiting_second_validation", refined)
        self.assertTrue(refined["round_retained"], refined)
        pack = pending_env.pack()
        self.assertEqual(pack["validator"]["round"], 1, pack["validator"])
        body_refined = pending_env.managed_parts()[1]
        self.assertIn("纯叙事已改文字".encode("utf-8"), body_refined)
        self.assertNotIn("纯叙事待改文字".encode("utf-8"), body_refined)
        pending_env.assert_ownership_matches_body(body_refined)
        self.assertEqual(pack["papers"][DISPLAY_ONLY_KEY]["title"], DISPLAY_ONLY_TITLE)
        self.assertEqual(pending_env.display_reference_line(), DISPLAY_ONLY_RENDERED)
        after_refine = pending_env.direction_snapshot()
        self.assertEqual(after_refine["supporting"], pending_snapshot["supporting"])
        self.assertEqual(after_refine["relevant"], pending_snapshot["relevant"])
        self.assertEqual(after_refine["gaps"], pending_snapshot["gaps"])
        self.assertEqual(after_refine["blacklist"], pending_snapshot["blacklist"])

        # Restore the same facts bytes; ordinary acceptance must keep the pending
        # first round and the refined body, then the second round records the
        # fixed terminal finding.
        Path(pending_facts).write_bytes(facts_bytes)
        proof_path, payload = pending_env.save_preflight("u1d-restored-preflight.json")
        pending_env.bind_facts_to_preflight(pending_facts, payload)
        plan = pending_env.stage2_plan(pending_facts, proof_path)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(plan["jobs"], [], plan)
        out = pending_env.finalize(pending_facts, proof_path, pending_results)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(pending_env.managed_parts()[1], body_refined)
        validator = pending_env.pack()["validator"]
        self.assertEqual(validator["round"], 1, validator)
        self.assertEqual(validator["phase"], "awaiting_second_validation", validator)
        self.assertEqual(validator["pending"], validator_before["pending"])
        self.assertEqual(validator["results"], validator_before["results"])

        round2_line = pending_env.physical_line("评估时间：", expected=1)
        round2 = pending_env.write_report("u1d-pending-round2.json", [
            pending_env.blocking_issue("评估时间：", round2_line)])
        round2_bytes = Path(round2).read_bytes()
        terminal = pending_env.record(round2)
        self.assertEqual(terminal["status"], "ok", terminal)
        self.assertEqual(terminal["round"], 2, terminal)
        self.assertTrue(terminal["terminal"], terminal)
        self.assertTrue(terminal["needs_owner_fix"], terminal)
        pack = pending_env.pack()
        self.assertEqual(pack["validator"]["results"]["DIR00001"]["result"],
                         "fail_after_2_rounds")
        self.assertEqual(pack["validator"]["fixed_blocking"]["DIR00001"][0]["owner"],
                         "generator")
        stopped = pending_env.refine_plan(round2)
        self.assertEqual(stopped["status"], "needs_owner_fix", stopped)
        self.assertEqual(stopped["jobs"], [], stopped)
        self.assertEqual(Path(report).read_bytes(), report_bytes)
        self.assertEqual(Path(round2).read_bytes(), round2_bytes)

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

        # E-v1: an accepted old pack with display_version=1 but a fully valid raw
        # byte binding upgrades through the normal process path without losing the
        # recorded terminal state, and a second preflight reuses it (t5 §6.4).
        upgrade_env = self._fresh_env()
        upgrade_facts, upgrade_results, _upgrade_proof = upgrade_env.generate_pack(
            upgrade_env.gap_override())
        self.assertEqual(upgrade_env.display_version(), U1_TARGET_DISPLAY_VERSION)
        upgrade_report = upgrade_env.record_pass("u1e-v1-pass.json")
        upgrade_report_bytes = Path(upgrade_report).read_bytes()
        upgrade_pack = upgrade_env.pack()
        validator_before = copy.deepcopy(upgrade_pack["validator"])
        self.assertEqual(validator_before["phase"], "terminal")
        entry_before = copy.deepcopy(
            upgrade_pack["cache"]["render"][contact_state.ANALYSIS_MD])
        body_bytes = upgrade_env.managed_parts()[1]
        body_sha = upgrade_env.body_digest(body_bytes)
        # Historical v1 marker only: the real validator, body bytes and map stay.
        upgrade_env.set_display_version(1)
        upgrade_pack = upgrade_env.pack()
        upgrade_pack["validator"]["pack_sha256"] = \
            contact_state.stage2_pack_content_fingerprint(upgrade_pack)
        upgrade_env.write_pack(upgrade_pack)

        upgrade_pack = upgrade_env.pack()
        body = upgrade_env.managed_parts()[1]
        entry = upgrade_pack["cache"]["render"][contact_state.ANALYSIS_MD]
        self.assertEqual(upgrade_env.body_digest(body), body_sha)
        self.assertEqual(entry["sha256"], body_sha)
        self.assertEqual(entry["ownership"]["body_sha256"], body_sha)
        self.assertEqual(upgrade_pack["validator"]["render_sha256"], body_sha)
        self.assertEqual(upgrade_env.document()["header"]["render_sha256"], body_sha)
        self.assertEqual(upgrade_pack["validator"]["pack_sha256"],
                         contact_state.stage2_pack_content_fingerprint(upgrade_pack))
        self.assertEqual(upgrade_pack["validator"]["validation_sha256"],
                         hashlib.sha256(upgrade_report_bytes).hexdigest())
        self.assertEqual(upgrade_env.document()["header"]["state_fingerprint"],
                         contact_state.stage2_pack_state_fingerprint(upgrade_pack))

        proof_path, payload = upgrade_env.save_preflight("u1e-v1-preflight.json")
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("fixed_evidence_display_update", payload["reason_codes"], payload)
        upgrade_direction = next(row for row in payload["directions"]
                                 if row["direction_id"] == "DIR00001")
        self.assertIn("fixed_evidence_display_update",
                      upgrade_direction["reason_codes"], upgrade_direction)
        upgrade_env.bind_facts_to_preflight(upgrade_facts, payload)
        plan = upgrade_env.stage2_plan(upgrade_facts, proof_path)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(plan["jobs"], [], plan)
        self.assertFalse(plan["write_needed"], plan)
        out = upgrade_env.finalize(upgrade_facts, proof_path, upgrade_results)
        self.assertEqual(out["status"], "ok", out)
        body_after = upgrade_env.managed_parts()[1]
        self.assertEqual(body_after, body_bytes)
        pack = upgrade_env.pack()
        self.assertEqual(upgrade_env.display_version(), U1_TARGET_DISPLAY_VERSION)
        validator = pack["validator"]
        for field in ("round", "phase", "pending", "results", "issues", "notes",
                      "raw_verdict", "validation_sha256", "render_sha256",
                      "validation_render_sha256"):
            self.assertEqual(validator[field], validator_before[field], field)
        self.assertEqual(validator["pack_sha256"],
                         contact_state.stage2_pack_content_fingerprint(pack))
        entry = pack["cache"]["render"][contact_state.ANALYSIS_MD]
        self.assertEqual(entry["ownership"]["body_sha256"],
                         upgrade_env.body_digest(body_after))
        for key in entry_before:
            if key != "u1":
                self.assertIn(key, entry)
        self.assertEqual(Path(upgrade_report).read_bytes(), upgrade_report_bytes)
        again = upgrade_env.preflight()
        self.assertEqual(again["action"], "reuse_all", again)
        self.assertNotIn("fixed_evidence_display_update", again["reason_codes"], again)

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

        # An equivalent body with a stale header binding is invalid old evidence:
        # the acceptance must fail closed and write nothing.
        header_pack = env.pack()
        header_pack.pop("validator", None)
        env.write_pack(header_pack)
        header, body = contact_state.split_frontmatter(
            (env.prof_dir / contact_state.ANALYSIS_MD).read_text(encoding="utf-8"))
        (env.prof_dir / contact_state.ANALYSIS_MD).write_text(
            contact_state.render_frontmatter("0" * 64, contact_state.sha256_text(body))
            + body, encoding="utf-8")
        stale_header_bytes = (env.prof_dir / contact_state.ANALYSIS_MD).read_bytes()
        pack_before = (env.prof_dir / contact_state.INPUT_PACK).read_bytes()
        out = env.finalize(facts_path, proof, results)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "validation_render_stale", out)
        self.assertEqual((env.prof_dir / contact_state.ANALYSIS_MD).read_bytes(),
                         stale_header_bytes)
        self.assertEqual((env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         pack_before)

        # A real fixed-evidence change is accepted as new structured input: the
        # managed body changes, the old validator retires, and its raw report
        # file stays untouched.
        fixed_env = self._fresh_env()
        fixed_facts, fixed_results, fixed_proof = fixed_env.generate_pack(
            fixed_env.gap_override())
        old_report = fixed_env.write_report("u1f-fixed-pass.json", [])
        self.assertEqual(fixed_env.record(old_report)["status"], "ok")
        old_pack = fixed_env.pack()
        self.assertEqual(old_pack["validator"]["phase"], "terminal")
        old_body = fixed_env.document()["body"]
        old_report_bytes = Path(old_report).read_bytes()
        fixed_gap_id = contact_state.quote_id(fixed_env.gap_quotes["AAAA1111"])
        old_evidence = (f"后续由 {CITATION_KEY} 完成，日期 {ORDINARY_DATE}，"
                        f"未知 {ORDINARY_EIGHT} 与 12345678 保留。")
        new_evidence = old_evidence[:-1] + "；新增固定证据对照。"
        freshness_path = fixed_results / "freshness-DIR00001.json"
        freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
        fixed_rows = [row for row in freshness["results"]
                      if row["gap_id"] == fixed_gap_id]
        self.assertEqual(len(fixed_rows), 1, fixed_rows)
        self.assertEqual(fixed_rows[0]["evidence"], old_evidence)
        fixed_rows[0]["evidence"] = new_evidence
        freshness_path.write_text(json.dumps(freshness, ensure_ascii=False),
                                  encoding="utf-8")
        cache_path = fixed_env.prof_dir / contact_state.FRESHNESS_CACHE
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertIn(fixed_gap_id, cache["entries"])
        del cache["entries"][fixed_gap_id]
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

        payload = fixed_env.preflight()
        self.assertEqual(payload["action"], "process", payload)
        fixed_direction = next(row for row in payload["directions"]
                               if row["direction_id"] == "DIR00001")
        self.assertIn("freshness_cache_changed",
                      fixed_direction["reason_codes"], fixed_direction)
        fixed_preflight = fixed_env.root / "u1f-fixed-preflight.json"
        fixed_preflight.write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
        fixed_env.bind_facts_to_preflight(fixed_facts, payload)
        plan = parse(run_cli("stage2-plan", "--facts", fixed_facts,
                             "--preflight-file", fixed_preflight))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertTrue(any(job["kind"] == "freshness" for job in plan["jobs"]), plan)
        out = fixed_env.finalize(fixed_facts, fixed_preflight, fixed_results)
        self.assertEqual(out["status"], "ok", out)
        pack = fixed_env.pack()
        fixed_gap = next(row for row in pack["directions"][0]["gap_shortlist"]
                         if row["gap_id"] == fixed_gap_id)
        self.assertEqual(fixed_gap["evidence"], new_evidence)
        new_body = fixed_env.document()["body"]
        self.assertNotEqual(new_body, old_body)
        self.assertIn("新增固定证据对照", new_body)
        self.assertIn(CITATION_LINK, new_body)
        self.assertIsNone(pack.get("validator"))
        self.assertEqual(Path(old_report).read_bytes(), old_report_bytes)

        # A business-fingerprint change whose visible body is equivalent still
        # expires the old certification and refreshes only the header; the raw
        # body bytes stay identical.
        business_env = self._fresh_env()
        business_facts, business_results, _business_proof = business_env.generate_pack(
            business_env.gap_override())
        self.assertEqual(business_env.display_version(), U1_TARGET_DISPLAY_VERSION)
        business_report = business_env.record_pass("u1f-business-pass.json")
        business_report_bytes = Path(business_report).read_bytes()
        body_before = business_env.managed_parts()[1]
        facts = json.loads(Path(business_facts).read_text(encoding="utf-8"))
        facts["directions"][0]["credibility"]["note"] = "只影响指纹不进入正文的说明"
        Path(business_facts).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
        proof_path, payload = business_env.save_preflight("u1f-business-preflight.json")
        business_env.bind_facts_to_preflight(business_facts, payload)
        plan = business_env.stage2_plan(business_facts, proof_path)
        self.assertEqual(plan["status"], "ok", plan)
        out = business_env.finalize(business_facts, proof_path, business_results)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(business_env.managed_parts()[1], body_before)
        pack = business_env.pack()
        self.assertIsNone(pack.get("validator"))
        self.assertEqual(business_env.document()["header"]["state_fingerprint"],
                         contact_state.stage2_pack_state_fingerprint(pack))
        self.assertEqual(Path(business_report).read_bytes(), business_report_bytes)

        # With business and body unchanged, only an invalid old binding is
        # rejected before any write and must not be silently re-bound.
        stale_env = self._fresh_env()
        stale_facts, stale_results, stale_proof = stale_env.generate_pack()
        stale_report = stale_env.write_report("u1f-stale-pass.json", [])
        self.assertEqual(stale_env.record(stale_report)["status"], "ok")
        stale_pack = stale_env.pack()
        self.assertEqual(stale_pack["validator"]["pack_sha256"],
                         contact_state.stage2_pack_content_fingerprint(stale_pack))
        stale_pack["validator"]["pack_sha256"] = "0" * 64
        stale_env.write_pack(stale_pack)
        stale_pack_bytes = (stale_env.prof_dir / contact_state.INPUT_PACK).read_bytes()
        analysis_path = stale_env.prof_dir / contact_state.ANALYSIS_MD
        analysis_bytes = analysis_path.read_bytes()
        stale_facts_bytes = Path(stale_facts).read_bytes()
        stale_report_bytes = Path(stale_report).read_bytes()
        out = stale_env.finalize(stale_facts, stale_proof, stale_results)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out.get("reason_code"), "validation_render_stale", out)
        self.assertEqual((stale_env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         stale_pack_bytes)
        self.assertEqual(analysis_path.read_bytes(), analysis_bytes)
        self.assertEqual(Path(stale_facts).read_bytes(), stale_facts_bytes)
        self.assertEqual(Path(stale_report).read_bytes(), stale_report_bytes)
        self.assertEqual(stale_env.pack()["validator"]["pack_sha256"], "0" * 64)

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
        match = re.search(r"全文级 \d+ 篇", raw)
        self.assertIsNotNone(match)
        original_source_text = match.group(0)
        changed = raw.replace(original_source_text, "全文级 9 篇", 1)
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
        self.assertIn(original_source_text, repaired)
        self.assertNotIn("全文级 9 篇", repaired)

        # A user-note line with the generated source-line prefix is not the top
        # source line: its timestamp change is a real body change.
        note_old = "2026-10-20T10:00:00Z ｜ 数据来源：个人记录"
        note_new = "2026-10-21T10:00:00Z ｜ 数据来源：个人记录"

        def add_note(facts):
            facts["directions"][0]["user_note"] = note_old

        note_env = self._fresh_env()
        note_facts, note_results, _ = note_env.generate_pack(mutate_facts=add_note)
        old_note_body = note_env.document()["body"]
        self.assertIn(f"> {note_old}", old_note_body)
        facts = json.loads(Path(note_facts).read_text(encoding="utf-8"))
        facts["directions"][0]["user_note"] = note_new
        Path(note_facts).write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        proof_path, payload = note_env.save_preflight("u1f-note-preflight.json")
        note_env.bind_facts_to_preflight(note_facts, payload)
        plan = parse(run_cli("stage2-plan", "--facts", note_facts,
                             "--preflight-file", proof_path))
        self.assertEqual(plan["status"], "ok", plan)
        out = note_env.finalize(note_facts, proof_path, note_results)
        self.assertEqual(out["status"], "ok", out)
        new_note_body = note_env.document()["body"]
        self.assertIn(f"> {note_new}", new_note_body)
        self.assertNotIn(f"> {note_old}", new_note_body)
        self.assertNotEqual(new_note_body, old_note_body)

        # F-time: a determinate generation-time difference is ignored while every
        # other body byte is preserved; no parent-process clock mock is used.
        time_env = self._fresh_env()
        time_facts, time_results, _time_proof = time_env.generate_pack(
            time_env.gap_override())
        self.assertEqual(time_env.display_version(), U1_TARGET_DISPLAY_VERSION)
        _header, body = time_env.managed_parts()
        self.assertNotIn(b"\r", body)
        stamps = list(GENERATED_STAMP_RE.finditer(body))
        self.assertEqual(len(stamps), 1, stamps)
        old_stamp = stamps[0].group(1)
        self.assertEqual(len(old_stamp), 20)
        new_body = body.replace(old_stamp, b"2000-01-01T00:00:00Z", 1)
        self.assertEqual(len(new_body), len(body))
        self.assertNotEqual(new_body, body)
        time_env.rewrite_consistent_input(new_body)
        time_report = time_env.record_pass("u1f-time-pass.json")
        time_report_bytes = Path(time_report).read_bytes()
        validator_before = copy.deepcopy(time_env.pack()["validator"])
        payload = time_env.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        proof_path = time_env.bind_proof(time_facts, payload, "u1f-time-preflight.json")
        body_before = time_env.managed_parts()[1]
        self.assertIn(b"2000-01-01T00:00:00Z", body_before)
        out = time_env.finalize(time_facts, proof_path, time_results)
        self.assertEqual(out["status"], "ok", out)
        body_after = time_env.managed_parts()[1]
        self.assertEqual(body_after, body_before)
        self.assertIn(b"2000-01-01T00:00:00Z", body_after)
        pack = time_env.pack()
        entry = pack["cache"]["render"][contact_state.ANALYSIS_MD]
        digest = time_env.body_digest(body_after)
        self.assertEqual(entry["sha256"], digest)
        self.assertEqual(entry["ownership"]["body_sha256"], digest)
        self.assertEqual(time_env.document()["header"]["render_sha256"], digest)
        validator = pack["validator"]
        for field in ("round", "phase", "pending", "results", "raw_verdict",
                      "validation_sha256", "render_sha256", "validation_render_sha256"):
            self.assertEqual(validator[field], validator_before[field], field)
        self.assertEqual(validator["pack_sha256"],
                         contact_state.stage2_pack_content_fingerprint(pack))
        ownership = time_env.assert_ownership_matches_body(body_after)
        lines = body_after.decode("utf-8").splitlines()
        evidence_line = next(index for index, line in enumerate(lines)
                             if line.startswith("- 后续论文依据："))
        needle_start = lines[evidence_line].index("后续由")
        needle_end = needle_start + len("后续由")
        self.assertTrue(any(
            fragment.get("field") == "evidence"
            and any(row[0] == evidence_line and row[1] < needle_end
                    and row[2] > needle_start for row in fragment["ranges"])
            for fragment in ownership["fragments"]))
        self.assertEqual(Path(time_report).read_bytes(), time_report_bytes)

        # F-preflight/finalize: the newest marker cannot hide an LF -> CRLF disk
        # change from the preflight reuse gate (r5 §3.4/§3.6).
        crlf_env = self._fresh_env()
        crlf_facts, crlf_results, _crlf_proof = crlf_env.generate_pack(
            crlf_env.gap_override())
        self.assertEqual(crlf_env.display_version(), U1_TARGET_DISPLAY_VERSION)
        crlf_report = crlf_env.record_pass("u1f-crlf-pass.json")
        crlf_report_bytes = Path(crlf_report).read_bytes()
        payload = crlf_env.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        proof_path = crlf_env.bind_proof(crlf_facts, payload, "u1f-crlf-reuse.json")
        facts_before = Path(crlf_facts).read_bytes()
        cache_before = (crlf_env.prof_dir / contact_state.FRESHNESS_CACHE).read_bytes()
        old_digest = crlf_env.pack()["cache"]["render"][contact_state.ANALYSIS_MD]["sha256"]
        header, body = crlf_env.managed_parts()
        self.assertNotIn(b"\r", body)
        self.assertIn(b"\n", body)
        crlf_body = body.replace(b"\n", b"\r\n")
        self.assertNotEqual(crlf_body, body)
        self.assertEqual(crlf_body.replace(b"\r\n", b"\n"), body)
        crlf_env.write_managed_parts(header, crlf_body)
        self.assertEqual(crlf_env.document()["header"]["render_sha256"], old_digest)
        markdown_before = crlf_env.managed_path().read_bytes()
        pack_before = (crlf_env.prof_dir / contact_state.INPUT_PACK).read_bytes()

        again = crlf_env.preflight()
        self.assertEqual(again["action"], "process", again)
        self.assertIn("validator_not_accepted", again["reason_codes"], again)
        direction_row = next(row for row in again["directions"]
                             if row["direction_id"] == "DIR00001")
        self.assertEqual(direction_row["action"], "process", direction_row)
        self.assertIn("validator_not_accepted", direction_row["reason_codes"],
                      direction_row)
        self.assertEqual(crlf_env.managed_path().read_bytes(), markdown_before)
        self.assertEqual((crlf_env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         pack_before)

        out = crlf_env.finalize(crlf_facts, proof_path, crlf_results)
        self.assertIn(out["status"], {"error", "needs_decision"}, out)
        self.assertIn(out.get("reason_code"),
                      {"validation_render_stale", "manual_markdown_changed"}, out)
        self.assertNotIn(out.get("reason_code"),
                         {"preflight_inputs_changed", "invalid_params",
                          "invalid_result_json"}, out)
        self.assertEqual(crlf_env.managed_path().read_bytes(), markdown_before)
        self.assertEqual((crlf_env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         pack_before)
        self.assertEqual(Path(crlf_facts).read_bytes(), facts_before)
        self.assertEqual((crlf_env.prof_dir / contact_state.FRESHNESS_CACHE).read_bytes(),
                         cache_before)
        self.assertEqual(Path(crlf_report).read_bytes(), crlf_report_bytes)
        self.assertEqual(crlf_env.display_version(), U1_TARGET_DISPLAY_VERSION)

        # F-record: an unregistered first-round pass report is isolated from a
        # body whose bytes changed, not rejected by round/terminal rules.
        record_env = self._fresh_env()
        record_facts, record_results, _record_proof = record_env.generate_pack(
            record_env.gap_override())
        self.assertNotIn("validator", record_env.pack())
        record_report = record_env.write_report("u1f-record-pass.json", [])
        record_report_bytes = Path(record_report).read_bytes()
        record_header, record_body = record_env.managed_parts()
        record_env.write_managed_parts(record_header, record_body.replace(b"\n", b"\r\n"))
        markdown_before = record_env.managed_path().read_bytes()
        pack_before = (record_env.prof_dir / contact_state.INPUT_PACK).read_bytes()
        out = record_env.record(record_report)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out.get("reason_code"), "validation_render_stale", out)
        self.assertEqual(record_env.managed_path().read_bytes(), markdown_before)
        self.assertEqual((record_env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         pack_before)
        self.assertEqual(Path(record_report).read_bytes(), record_report_bytes)
        self.assertNotIn("validator", record_env.pack())

        # F-refine: a registered legal pending report with a body that lost its
        # final newline byte is stale for both refine entries.
        refine_env = self._fresh_env()

        def add_refine_block(narrative):
            narrative["directions"][0]["positioning"].append({
                "kind": "para", "text": "纯叙事待改文字。", "refs": [],
                "concrete_object": "合成叙事对象",
                "input_example": "输入一份叙事样本",
                "output_example": "得到一段叙事结论"})

        refine_facts, refine_results, _refine_proof = refine_env.generate_pack(
            narrative_mutate=add_refine_block)
        refine_line = refine_env.physical_line("纯叙事待改文字")
        refine_report = refine_env.write_report("u1f-refine.json", [
            refine_env.blocking_issue("纯叙事待改文字", refine_line)])
        recorded = refine_env.record(refine_report)
        self.assertEqual(recorded["status"], "needs_correction", recorded)
        self.assertEqual(recorded["round"], 1, recorded)
        self.assertFalse(recorded["needs_owner_fix"], recorded)
        plan = refine_env.refine_plan(refine_report)
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["DIR00001"],
                         plan)
        rewrite = refine_env.write_narrative_rewrite("纯叙事待改文字", "纯叙事已改文字")
        report_bytes = Path(refine_report).read_bytes()
        rewrite_bytes = {path.name: path.read_bytes() for path in rewrite.iterdir()}
        header, body = refine_env.managed_parts()
        self.assertTrue(body.endswith(b"\n"))
        trimmed = body[:-1]
        self.assertEqual(len(trimmed), len(body) - 1)
        refine_env.write_managed_parts(header, trimmed)
        markdown_before = refine_env.managed_path().read_bytes()
        pack_before = (refine_env.prof_dir / contact_state.INPUT_PACK).read_bytes()
        bad_plan = refine_env.refine_plan(refine_report)
        self.assertEqual(bad_plan["status"], "error", bad_plan)
        self.assertEqual(bad_plan.get("reason_code"), "validation_render_stale",
                         bad_plan)
        self.assertEqual(refine_env.managed_path().read_bytes(), markdown_before)
        self.assertEqual((refine_env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         pack_before)
        self.assertEqual(Path(refine_report).read_bytes(), report_bytes)
        bad_final = refine_env.refine_finalize(rewrite, refine_report)
        self.assertEqual(bad_final["status"], "error", bad_final)
        self.assertEqual(bad_final.get("reason_code"), "validation_render_stale",
                         bad_final)
        self.assertEqual(refine_env.managed_path().read_bytes(), markdown_before)
        self.assertEqual((refine_env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         pack_before)
        self.assertEqual(Path(refine_report).read_bytes(), report_bytes)
        pending_state = refine_env.pack()["validator"]
        self.assertEqual(pending_state["phase"], "needs_correction", pending_state)
        self.assertEqual(pending_state["round"], 1, pending_state)
        for name, content in rewrite_bytes.items():
            self.assertEqual((rewrite / name).read_bytes(), content, name)

        # F-manual: without any old validator, an unannounced CRLF edit still
        # needs a decision and must not upgrade the display marker.
        spec_env = self._fresh_env()
        spec_facts, spec_results, _spec_proof = spec_env.generate_pack(
            spec_env.gap_override())
        self.assertNotIn("validator", spec_env.pack())
        spec_env.set_display_version(1)
        proof_path, payload = spec_env.save_preflight("u1f-manual-preflight.json")
        spec_env.bind_facts_to_preflight(spec_facts, payload)
        header, body = spec_env.managed_parts()
        spec_env.write_managed_parts(header, body.replace(b"\n", b"\r\n"))
        markdown_before = spec_env.managed_path().read_bytes()
        pack_before = (spec_env.prof_dir / contact_state.INPUT_PACK).read_bytes()
        cache_before = (spec_env.prof_dir / contact_state.FRESHNESS_CACHE).read_bytes()
        facts_before = Path(spec_facts).read_bytes()
        out = spec_env.finalize(spec_facts, proof_path, spec_results)
        self.assertEqual(out["status"], "needs_decision", out)
        self.assertEqual(out.get("reason_code"), "manual_markdown_changed", out)
        self.assertEqual(spec_env.managed_path().read_bytes(), markdown_before)
        self.assertEqual((spec_env.prof_dir / contact_state.INPUT_PACK).read_bytes(),
                         pack_before)
        self.assertEqual((spec_env.prof_dir / contact_state.FRESHNESS_CACHE).read_bytes(),
                         cache_before)
        self.assertEqual(Path(spec_facts).read_bytes(), facts_before)
        self.assertEqual(spec_env.display_version(), 1)

        # F-valid-CRLF: a legal old CRLF body with a consistent raw binding is not
        # a broken binding; the ordinary acceptance writes the LF candidate.
        valid_env = self._fresh_env()
        valid_facts, valid_results, valid_proof = valid_env.generate_pack(
            valid_env.gap_override())
        self.assertNotIn("validator", valid_env.pack())
        _header, body = valid_env.managed_parts()
        crlf_body = body.replace(b"\n", b"\r\n")
        self.assertEqual(crlf_body.replace(b"\r\n", b"\n"), body)
        valid_env.rewrite_consistent_input(crlf_body)
        valid_report = valid_env.record_pass("u1f-valid-crlf-pass.json")
        valid_report_bytes = Path(valid_report).read_bytes()
        out = valid_env.finalize(valid_facts, valid_proof, valid_results)
        self.assertEqual(out["status"], "ok", out)
        body_after = valid_env.managed_parts()[1]
        self.assertNotIn(b"\r", body_after)
        self.assertNotEqual(body_after, crlf_body)
        # The only non-time difference from the old CRLF body is the line ending.
        stamp_placeholder = "> <stamp> ｜ 数据来源：".encode("utf-8")
        normalized_new = GENERATED_STAMP_RE.sub(stamp_placeholder, body_after)
        normalized_old = GENERATED_STAMP_RE.sub(stamp_placeholder, crlf_body)
        self.assertEqual(normalized_new.splitlines(), normalized_old.splitlines())
        pack = valid_env.pack()
        self.assertIsNone(pack.get("validator"))
        digest = valid_env.body_digest(body_after)
        entry = pack["cache"]["render"][contact_state.ANALYSIS_MD]
        self.assertEqual(entry["sha256"], digest)
        self.assertEqual(entry["ownership"]["body_sha256"], digest)
        self.assertEqual(valid_env.document()["header"]["render_sha256"], digest)
        self.assertEqual(Path(valid_report).read_bytes(), valid_report_bytes)


class SourcePaperCitationTests(FixedEvidenceBase):
    def test_source_identity_is_rendered_without_later_candidates(self):
        evidence = "AAAA1111（2021）：库内没有更晚论文；ZXCV1234 是普通文字。"
        self.generate_pack({
            "AAAA1111": {
                "status": "unknown", "candidate_paper_ids": [],
                "evidence": evidence,
            },
        })
        pack = self.pack()
        gap = next(gap for direction in pack["directions"]
                   for gap in direction["gap_shortlist"]
                   if gap["item_key"] == "AAAA1111")
        self.assertEqual(gap["evidence"], evidence)
        self.assertEqual(gap["candidate_paper_ids"], [])
        body = self.document()["body"]
        self.assertIn("zotero://select/library/items/AAAA1111", body)
        self.assertNotIn("后续论文依据：AAAA1111", body)
        self.assertIn("ZXCV1234 是普通文字", body)

    def test_blacklist_source_identity_uses_the_same_display_rule(self):
        self.generate_pack({
            "AAAA1111": {
                "status": "done_by_self", "candidate_paper_ids": [],
                "evidence": "AAAA1111 原论文已经包含该结果。",
            },
        })
        body = self.document()["body"]
        self.assertNotIn("AAAA1111 原论文已经包含该结果", body)
        self.assertIn(
            "](zotero://select/library/items/AAAA1111) 原论文已经包含该结果", body)



if __name__ == "__main__":
    import unittest
    unittest.main()

