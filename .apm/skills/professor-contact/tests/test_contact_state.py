import hashlib
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

import importlib.util

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"

_spec = importlib.util.spec_from_file_location("contact_state", SCRIPT)
contact_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contact_state)


def result_file(kind: str, identity: str) -> str:
    """Mirror the runner's deterministic result-file naming (issue #8)."""
    return contact_state.safe_result_file(kind, identity)


def quote_id(quote: str) -> str:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", quote)).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def run_cli(*arguments):
    args = list(map(str, arguments))
    if args and args[0] in {"stage5-plan", "stage5-finalize"} and "--program-root" in args:
        root = Path(args[args.index("--program-root") + 1])
        template = root / "synthetic-template.md"
        followup = root / "synthetic-followup-template.md"
        if not template.exists():
            template.write_text("{{大学}}／{{研究科}}／{{先生名}}先生\n{{出身校}} {{氏名}}\n{{入学年度}} {{入学月}} {{専攻}} {{学位}}\n{{兴趣段}}\n{{未来志向}}\n{{学習中}}\n{{志望}}", encoding="utf-8")
        if not followup.exists():
            followup.write_text("{{先生名}}先生\n{{大学}} {{研究科}} {{学位}}\n{{出身校}} {{氏名}}\n{{初回送信日}}\n{{研究主题}}\n{{メールアドレス}}", encoding="utf-8")
        if "--template" not in args:
            args.extend(["--template", str(template)])
        if "--mode" in args and args[args.index("--mode") + 1] in {"both", "followup"} and "--followup-template" not in args:
            args.extend(["--followup-template", str(followup)])
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          text=True, capture_output=True, check=False)


def parse(result):
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"stdout not JSON: {result.stdout!r}\nstderr: {result.stderr!r}")


def make_sidecar(analysis: Path, quotes: list, page: int = 8) -> Path:
    items = [{"id": quote_id(q), "quote": q, "translation_zh": f"中译：{q[:24]}",
              "source": "Conclusion", "page": page} for q in quotes]
    sidecar = Path(str(analysis) + ".future_work.json")
    sidecar.write_text(json.dumps({
        "schema": 1, "extractor_version": "future-work-v1",
        "analysis": str(analysis), "status": "ok", "items": items},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return sidecar


class BaseEnv(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)
        self.gap_quotes = {
            "AAAA1111": "Future work will extend the synthetic comparison to a second input pattern.",
            "BBBB2222": "We plan to test a second synthetic processing path.",
        }
        self.papers = [
            {"item_key": "AAAA1111", "title": "Synthetic comparison of input patterns",
             "year": 2023, "month": 5, "authorship": "corresponding",
             "abstract": "We study a synthetic comparison of input patterns.",
             "has_pdf": True, "authors": ["Author One", "Example Professor"]},
            {"item_key": "BBBB2222", "title": "Synthetic processing path evaluation",
             "year": 2024, "month": 3, "authorship": "first",
             "abstract": "A synthetic system for comparing two processing paths.",
             "has_pdf": True, "authors": ["Example Professor"]},
            {"item_key": "CCCC3333", "title": "Unrelated synthetic example",
             "year": 2026, "month": 1, "authorship": "middle",
             "abstract": "A deliberately unrelated synthetic example.",
             "has_pdf": False, "authors": ["Other Author"]},
        ]
        for key, quote in self.gap_quotes.items():
            analysis = self.prof_dir / "论文分析" / f"{key}.md"
            analysis.write_text("# analysis\n", encoding="utf-8")
            sidecar = make_sidecar(analysis, [quote])
            for paper in self.papers:
                if paper["item_key"] == key:
                    paper["analysis_file"] = str(analysis)
                    paper["sidecar_file"] = str(sidecar)

    def tearDown(self):
        self.temp.cleanup()

    def write_facts(self, extra=None) -> Path:
        facts = {
            "program_root": str(self.root), "professor_dir": str(self.prof_dir),
            "professor": "試験 教授", "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": self.papers,
            "directions": [{
                "collection_key": "DIR00001", "name_ja": "合成输入比较", "name_zh": "合成输入比较",
                "status": "active",
                "member_keys": ["AAAA1111", "BBBB2222", "CCCC3333"],
                "relevant_keys": ["AAAA1111", "BBBB2222"],
                "named_keys": ["AAAA1111"],
                "user_note": "我想比较两种合成输入的处理结果。",
                "credibility": {"verdict": "站得住", "mainline": "主线",
                                "authorship_line": "corresponding_dominant", "note": "test"},
                 "red_lines": [{"scope": "global", "text": "不得引用未提供来源的数字",
                                "banned_phrases": ["99.9%"]}],
            }],
        }
        if extra:
            extra(facts)
        path = self.root / "facts.json"
        path.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    def write_stage2_results(self, results: Path, gap_overrides=None):
        results.mkdir(parents=True, exist_ok=True)
        overrides = gap_overrides or {}
        rows = []
        for key, quote in self.gap_quotes.items():
            row = {"gap_id": quote_id(quote), "status": "open",
                   "candidate_paper_ids": [], "evidence": f"无更晚论文实现该点（{key}）",
                   "confidence": "high"}
            row.update(overrides.get(key, {}))
            rows.append(row)
        (results / "freshness-DIR00001.json").write_text(json.dumps({
            "schema": 1, "kind": "freshness", "collection_key": "DIR00001",
            "results": rows}, ensure_ascii=False), encoding="utf-8")
        g1 = quote_id(self.gap_quotes["AAAA1111"])
        (results / "narrative.json").write_text(json.dumps({
            "schema": 1, "kind": "narrative", "directions": [{
                "collection_key": "DIR00001",
                 "positioning": [{"kind": "para",
                                   "text": "教授从 {{P:AAAA1111}} 起研究合成输入比较；{{G:" + g1 + "}} 是延伸点。",
                                  "refs": ["paper:AAAA1111", "gap:" + g1],
                                   "concrete_object": "合成输入与第二种模式",
                                   "input_example": "输入一组固定的合成样本",
                                   "output_example": "系统给出两种处理结果"}],
                 "gap_notes": [{"gap_id": g1, "summary": "扩展到第二种输入模式",
                                "explanation": "研究计划比较另一种合成场景。"}]}]},
            ensure_ascii=False), encoding="utf-8")

    def stage2_run(self, gap_overrides=None):
        facts = self.write_facts()
        results = self.root / "results"
        self.write_stage2_results(results, gap_overrides)
        plan = parse(run_cli("stage2-plan", "--facts", facts))
        self.assertEqual(plan["status"], "ok")
        out = parse(run_cli("stage2-finalize", "--facts", facts, "--results", results))
        self.assertEqual(out["status"], "ok", out)
        return out

    def stage3_run(self, profile=None, candidate_extra=None):
        facts = self.write_facts()
        results = self.root / "results"
        self.write_stage2_results(results)
        self.assertEqual(parse(run_cli(
            "stage2-finalize", "--facts", facts, "--results", results))["status"], "ok")
        s3 = self.root / "s3results"
        s3.mkdir(parents=True, exist_ok=True)
        g1 = quote_id(self.gap_quotes["AAAA1111"])
        def make_candidate(cid, origin):
            candidate = {
                "id": cid, "kind": "direction", "direction_ids": ["DIR00001"],
                "origin": origin,
                "title": "第二种输入模式的合成比较",
                "one_liner": "教授的合成比较启发我扩展输入模式",
                "research_question": "第二种输入模式能否在相同约束下保持比较结果",
                "points": ["挂在缺口①"],
                "gap_refs": [{"direction_id": "DIR00001", "item_key": "AAAA1111",
                              "gap_id": g1}],
                "anchor_notes": {},
                "papers": [{"item_key": "AAAA1111", "direction_ids": ["DIR00001"],
                            "role": "基座", "fit_note": "教授通讯"}],
                "fit": "high", "fit_note": "", "red_lines": [],
                "why_recommended": "兴趣契合", "tension_points": []}
            return candidate

        candidate = make_candidate("DIR00001_1", "user_refined")
        if candidate_extra:
            candidate_extra(candidate)
        doc = {"schema": 2, "kind": "candidates", "direction_id": "DIR00001",
               "mode": "refined",
                "refined": {"core_intent": "合成输入比较",
                            "calibration": [], "idea_zh": "把比较推进到第二种输入模式",
                           "variants": [], "mismatches": [],
                           "gap_ids": [{"item_key": "AAAA1111", "gap_id": g1}]},
               "candidates": [candidate, make_candidate("DIR00001_2", "generated"),
                              make_candidate("DIR00001_3", "generated")],
               "priority": "主推 候选1"}
        (s3 / result_file("candidates", "DIR00001")).write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", s3, "--program-root", self.root,
                            "--profile", profile or ""))
        return out

    def add_second_direction(self):
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        second = copy.deepcopy(pack["directions"][0])
        second["collection_key"] = "DIR00002"
        second["direction_id"] = "DIR00002"
        second["name_ja"] = "第二方向"
        second["name_zh"] = "第二方向"
        second["input_fingerprint"] = "second-direction-fingerprint"
        pack["directions"].append(second)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

        original = json.loads(
            (self.root / "s3results" / result_file("candidates", "DIR00001"))
            .read_text(encoding="utf-8"))
        original["direction_id"] = "DIR00002"
        original["mode"] = "generated"
        candidates = []
        for number in range(1, 4):
            candidate = copy.deepcopy(original["candidates"][0])
            candidate["id"] = f"DIR00002_{number}"
            candidate["title"] = f"第二方向候选{number}"
            candidate["direction_ids"] = ["DIR00002"]
            candidate["origin"] = "generated"
            for ref in candidate["gap_refs"]:
                ref["direction_id"] = "DIR00002"
            for paper in candidate["papers"]:
                paper["direction_ids"] = ["DIR00002"]
            candidates.append(candidate)
        original["candidates"] = candidates
        results = self.root / "second-s3results"
        results.mkdir(parents=True, exist_ok=True)
        (results / result_file("candidates", "DIR00002")).write_text(
            json.dumps(original, ensure_ascii=False), encoding="utf-8")
        return results


class TestRunnerBasics(BaseEnv):
    def test_stage2_end_to_end_and_blacklist(self):
        out = self.stage2_run(gap_overrides={
            "BBBB2222": {"status": "done_by_self",
                         "evidence": "CCCC3333 无关；无更晚论文做缓解闭环，但用户判定已被接住"}})
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        direction = pack["directions"][0]
        self.assertEqual(len(direction["completed_gap_blacklist"]), 1)
        self.assertEqual(direction["gap_shortlist"][0]["gap_id"],
                         quote_id(self.gap_quotes["AAAA1111"]))
        blacklist_ids = {b["gap_id"] for b in direction["completed_gap_blacklist"]}
        self.assertNotIn(quote_id(self.gap_quotes["BBBB2222"]),
                         {g["gap_id"] for g in direction["gap_shortlist"]})
        md = (self.prof_dir / "套磁候选分析.md").read_text(encoding="utf-8")
        self.assertIn("已被本人实现（禁锚）", md)
        self.assertIn("future work #1", md)
        self.assertIn("managed_by: contact_state", md)

    def test_01_shortlist_selects_at_most_ten_stable(self):
        def extra(facts):
            facts["directions"][0]["named_keys"] = []
            papers = []
            for index in range(15):
                key = f"PPPP{index:04d}"
                quote = f"Future work number {index}: extend evaluation to new modalities."
                analysis = self.prof_dir / "论文分析" / f"{key}.md"
                analysis.write_text("# a\n", encoding="utf-8")
                sidecar = make_sidecar(analysis, [quote])
                papers.append({
                     "item_key": key, "title": f"Synthetic study number {index}",
                    "year": 2020 + index % 6, "month": 1, "authorship": "middle",
                     "abstract": "synthetic comparison study", "has_pdf": False,
                    "authors": [], "analysis_file": str(analysis),
                    "sidecar_file": str(sidecar)})
            facts["papers"] = self.papers + papers
            facts["directions"][0]["member_keys"] = [p["item_key"] for p in facts["papers"]]
            facts["directions"][0]["relevant_keys"] = []
        facts = self.write_facts(extra)
        results = self.root / "results"
        plan = parse(run_cli("stage2-plan", "--facts", facts))
        direction = plan["directions"][0]
        self.assertLessEqual(direction["judge_count"], 10)
        self.assertGreaterEqual(direction["judge_count"], 5)
        plan2 = parse(run_cli("stage2-plan", "--facts", facts))
        self.assertEqual(plan["directions"][0]["judge_count"],
                         plan2["directions"][0]["judge_count"])

    def test_01b_same_year_month_order_is_conservative(self):
        for source_month, paper_month in ((12, 1), (None, 1), (12, None)):
            def extra(facts, source_month=source_month, paper_month=paper_month):
                facts["papers"][1]["year"] = 2023
                facts["papers"][0]["month"] = source_month
                facts["papers"][1]["month"] = paper_month

            facts = self.write_facts(extra)
            plan = parse(run_cli("stage2-plan", "--facts", facts))
            freshness = next(job for job in plan["jobs"] if job["kind"] == "freshness")
            first_gap = next(gap for gap in freshness["model_input"]["gaps"]
                             if gap["item_key"] == "AAAA1111")
            self.assertNotIn("BBBB2222", {paper["item_key"]
                                           for paper in first_gap["candidates"]["papers"]})

    def test_01c_invalid_sidecar_is_not_consumed(self):
        sidecar_path = Path(self.papers[0]["sidecar_file"])
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["analysis"] = str(self.prof_dir / "论文分析" / "other.md")
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
        plan = parse(run_cli("stage2-plan", "--facts", self.write_facts()))
        self.assertEqual(plan["directions"][0]["gap_pool"], 1)

    def test_01d_narrative_cannot_reference_non_direction_paper(self):
        facts = self.write_facts()
        results = self.root / "bad-narrative"
        self.write_stage2_results(results)
        narrative_path = results / "narrative.json"
        narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
        block = narrative["directions"][0]["positioning"][0]
        block["text"] = "不相关论文 {{P:CCCC3333}}。"
        block["refs"] = ["paper:CCCC3333"]
        narrative_path.write_text(json.dumps(narrative, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage2-finalize", "--facts", facts, "--results", results))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_reference_id")
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_02_freshness_cache_partial_invalidation(self):
        self.stage2_run()
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertEqual(len(cache["entries"]), 2)
        results = self.root / "results"
        out = parse(run_cli("stage2-finalize", "--facts", self.write_facts(),
                            "--results", results))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["freshness_judged"], 0)
        for paper in self.papers:
            if paper["item_key"] == "BBBB2222":
                paper["abstract"] = "updated abstract of the 2024 real-time paper"
        results2 = self.root / "results2"
        self.write_stage2_results(results2)
        out2 = parse(run_cli("stage2-finalize", "--facts", self.write_facts(),
                             "--results", results2))
        self.assertEqual(out2["status"], "ok")
        self.assertEqual(out2["freshness_judged"], 1,
                         "only the gap whose later-candidate set changed re-judges; the other stays cached")

    def test_03_done_by_self_rejected_as_candidate_anchor(self):
        out = self.stage2_run(gap_overrides={
            "BBBB2222": {"status": "done_by_self", "evidence": "已由后续论文接住"}})
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        black = pack["directions"][0]["completed_gap_blacklist"]
        self.assertEqual(len(black), 1)
        s3 = self.root / "s3results"
        g2 = quote_id(self.gap_quotes["BBBB2222"])
        doc = {"schema": 2, "kind": "candidates", "direction_id": "DIR00001",
               "mode": "generated",
               "candidates": [{
                   "id": "X1", "kind": "direction", "direction_ids": ["DIR00001"],
                   "title": "t", "one_liner": "o",
                   "research_question": "rq?",
                   "points": [],
                   "gap_refs": [{"direction_id": "DIR00001", "item_key": "BBBB2222",
                                 "gap_id": g2}],
                   "papers": [], "fit": "null", "red_lines": []},
                   {"id": "X2", "kind": "direction", "direction_ids": ["DIR00001"],
                    "title": "t", "one_liner": "o",
                    "research_question": "rq?", "points": [], "gap_refs": [],
                    "papers": [], "fit": "null", "red_lines": []},
                   {"id": "X3", "kind": "direction", "direction_ids": ["DIR00001"],
                    "title": "t", "one_liner": "o",
                    "research_question": "rq?", "points": [], "gap_refs": [],
                    "papers": [], "fit": "null", "red_lines": []}]}
        s3.mkdir(parents=True, exist_ok=True)
        (s3 / result_file("candidates", "DIR00001")).write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", s3, "--program-root", self.root))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "blacklisted_gap_anchor")

    def test_04_profile_change_invalidates_stage3_not_stage2(self):
        profile = self.root / "profile.md"
        profile.write_text("兴趣：合成输入比较\n", encoding="utf-8")
        self.stage2_run()
        out_first = self.stage3_run(profile=str(profile))
        self.assertEqual(out_first["status"], "ok", out_first)
        pack_before = (self.prof_dir / "套磁候选输入.json").read_bytes()
        profile.write_text("兴趣：合成输入比较与排序\n", encoding="utf-8")
        out = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                            "--profile", str(profile), "--program-root", self.root))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out.get("profile_changed_reason"), "profile_changed")
        self.assertTrue(out["write_needed"])
        pack_after = (self.prof_dir / "套磁候选输入.json").read_bytes()
        self.assertEqual(pack_before, pack_after)
        sel_input = self.root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1"}]}]}, ensure_ascii=False), encoding="utf-8")
        out4 = parse(run_cli("stage4-finalize", "--program-root", self.root,
                             "--selection-input", sel_input, "--profile", str(profile)))
        self.assertEqual(out4["status"], "needs_refresh")
        self.assertEqual(out4["reason_code"], "profile_changed")
        self.assertFalse((self.root / "教授研究" / "套磁选择.json").exists())

    def test_05_missing_packs_need_refresh(self):
        out = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                            "--program-root", self.root))
        self.assertEqual(out["status"], "needs_refresh")
        self.assertEqual(out["reason_code"], "missing_input_pack")
        out5 = parse(run_cli("stage5-plan", "--program-root", self.root))
        self.assertEqual(out5["status"], "needs_refresh")
        self.assertEqual(out5["reason_code"], "missing_email_pack")
        self.assertFalse((self.prof_dir / "套磁想法候选.md").exists())

    def test_professor_dir_must_be_inside_program_root(self):
        outside = self.root.parent / "outside-professor"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "stage3-plan", "--program-root", str(self.root),
             "--professor-dir", str(outside)],
            text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(parse(result)["reason_code"], "invalid_professor_dir")

    def test_05b_collection_key_limits_stage3(self):
        self.stage3_run()
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        other = json.loads(json.dumps(pack["directions"][0]))
        other["collection_key"] = "OTHER01"
        other["direction_id"] = "OTHER01"
        other["name_ja"] = "別方向"
        other["name_zh"] = "另一个方向"
        other["input_fingerprint"] = "other-fingerprint"
        other["user_note"] = ""
        other["gap_pool_count"] = 0
        other["gap_shortlist"] = []
        other["gaps_excluded"] = []
        other["completed_gap_blacklist"] = []
        pack["directions"].append(other)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

        plan = parse(run_cli(
            "stage3-plan", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--collection-key", "DIR00001"))
        self.assertEqual(plan["status"], "ok")
        self.assertEqual([d["direction_id"] for d in plan["directions"]], ["DIR00001"])
        self.assertTrue(all(j["direction_id"] == "DIR00001" for j in plan["jobs"]))

        results = self.root / "s3results"
        out = parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--results", results, "--program-root", self.root,
            "--collection-key", "DIR00001"))
        self.assertEqual(out["status"], "ok", out)
        state = json.loads((self.prof_dir / "套磁候选状态.json").read_text(encoding="utf-8"))
        self.assertEqual([d["direction_id"] for d in state["directions"]], ["DIR00001"])

    def test_05c_scoped_stage3_refresh_preserves_other_state(self):
        self.stage3_run()
        results = self.add_second_direction()
        out = parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--results", results, "--program-root", self.root,
            "--collection-key", "DIR00002"))
        self.assertEqual(out["status"], "ok", out)
        state = json.loads((self.prof_dir / "套磁候选状态.json").read_text(encoding="utf-8"))
        self.assertEqual([d["direction_id"] for d in state["directions"]],
                         ["DIR00001", "DIR00002"])

    def test_05d_scoped_stage3_rejects_six_generated_candidates(self):
        self.stage2_run()
        results = self.root / "too-many-candidates"
        results.mkdir(parents=True, exist_ok=True)
        g1 = quote_id(self.gap_quotes["AAAA1111"])
        candidate = {
            "id": "X", "kind": "direction", "direction_ids": ["DIR00001"],
            "title": "候选", "one_liner": "一句话",
            "research_question": "能否回答一个新的问题", "points": [],
            "gap_refs": [{"direction_id": "DIR00001", "item_key": "AAAA1111",
                          "gap_id": g1}],
            "anchor_notes": {}, "papers": [], "fit": "null", "red_lines": []}
        doc = {"schema": 2, "kind": "candidates", "direction_id": "DIR00001",
               "mode": "generated", "candidates": [dict(candidate, id=f"X{i}") for i in range(6)]}
        (results / result_file("candidates", "DIR00001")).write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--results", results, "--program-root", self.root))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "invalid_result_json")

    def test_05e_overview_manual_edit_blocks_before_md_write(self):
        self.stage3_run()
        md_path = self.prof_dir / "套磁想法候选.md"
        md_before = md_path.read_bytes()
        overview_path = self.root / "教授研究" / "套磁想法候选总览.md"
        overview_path.write_text(
            overview_path.read_text(encoding="utf-8").replace("推荐顺序", "手工改动"),
            encoding="utf-8")
        profile = self.root / "changed-profile.md"
        profile.write_text("兴趣发生变化\n", encoding="utf-8")
        results = self.root / "rerender-results"
        self.write_stage2_results(results)
        # Reuse the valid candidate result generated by stage3_run.
        (results / result_file("candidates", "DIR00001")).write_text(
            (self.root / "s3results" / result_file("candidates", "DIR00001"))
            .read_text(encoding="utf-8"), encoding="utf-8")
        out = parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--results", results, "--program-root", self.root,
            "--profile", profile))
        self.assertEqual(out["status"], "needs_decision")
        self.assertEqual(out["reason_code"], "manual_markdown_changed")
        self.assertEqual(md_path.read_bytes(), md_before)

    def test_06_email_pack_exact_join_only(self):
        self.stage3_run()
        g1 = quote_id(self.gap_quotes["AAAA1111"])
        sel_input = self.root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1", "note": "ok"}]}]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", sel_input))
        self.assertEqual(out["status"], "ok", out)
        pack = json.loads((self.root / "教授研究" / "邮件输入.json").read_text(encoding="utf-8"))
        email = pack["emails"][0]
        self.assertEqual([g["gap_id"] for g in email["gaps"]], [g1])
        self.assertEqual(email["gaps"][0]["status"], "open")
        (sel_input).write_text(json.dumps(
            {"selections": [{
                "professor": "試験 教授", "professor_dir": str(self.prof_dir),
                "collection_key": "DIR00001",
                "ideas": [{"id": "no_such_idea"}]}]}, ensure_ascii=False), encoding="utf-8")
        out2 = parse(run_cli("stage4-finalize", "--program-root", self.root,
                             "--selection-input", sel_input))
        self.assertEqual(out2["status"], "error")

    def test_06b_papers_override_controls_email_order(self):
        self.stage3_run()
        state_path = self.prof_dir / "套磁候选状态.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["directions"][0]["candidates"][0]["papers"] = [
            {"item_key": "BBBB2222", "title": "wrong", "year": 1900,
             "authorship": "middle", "role": "second", "fit_note": ""},
            {"item_key": "AAAA1111", "title": "wrong", "year": 1900,
             "authorship": "middle", "role": "first", "fit_note": ""},
        ]
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        sel_input = self.root / "sel_override.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1", "papers_override": ["AAAA1111"]}]
        }]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", sel_input))
        self.assertEqual(out["status"], "ok", out)
        email = json.loads((self.root / "教授研究" / "邮件输入.json").read_text(
            encoding="utf-8"))["emails"][0]
        self.assertEqual([paper["item_key"] for paper in email["papers"]], ["AAAA1111"])
        self.assertEqual(email["papers"][0]["title"], "Synthetic comparison of input patterns")

    def test_06c_invalid_papers_override_does_not_write(self):
        self.stage3_run()
        selection_path = self.root / "教授研究" / "套磁选择.json"
        email_pack_path = self.root / "教授研究" / "邮件输入.json"
        sel_input = self.root / "sel_invalid_override.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1", "papers_override": ["AAAA1111", "AAAA1111"]}]
        }]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", sel_input))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "invalid_papers_override")
        self.assertFalse(selection_path.exists())
        self.assertFalse(email_pack_path.exists())

    def test_06d_duplicate_stage4_selection_is_rejected_before_write(self):
        self.stage3_run()
        selection_path = self.root / "教授研究" / "套磁选择.json"
        email_pack_path = self.root / "教授研究" / "邮件输入.json"
        sel = {"professor": "試験 教授", "professor_dir": str(self.prof_dir),
               "collection_key": "DIR00001", "ideas": [{"id": "DIR00001_1"}]}
        sel_input = self.root / "duplicate-selection.json"
        sel_input.write_text(json.dumps({"selections": [sel, dict(sel)]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", sel_input))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "duplicate_selection")
        self.assertFalse(selection_path.exists())
        self.assertFalse(email_pack_path.exists())

    def test_06e_freshness_result_rejects_duplicate_and_unknown_gap(self):
        facts = self.write_facts()
        results = self.root / "bad-freshness"
        self.write_stage2_results(results)
        freshness = json.loads((results / "freshness-DIR00001.json").read_text(encoding="utf-8"))
        freshness["results"].append({"gap_id": "f" * 64, "status": "open",
                                      "candidate_paper_ids": [], "evidence": "bad"})
        (results / "freshness-DIR00001.json").write_text(
            json.dumps(freshness, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage2-finalize", "--facts", facts, "--results", results))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_reference_id")
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_06f_stage4_preserves_previous_direction_selection(self):
        self.stage3_run()
        results = self.add_second_direction()
        out3 = parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--results", results, "--program-root", self.root,
            "--collection-key", "DIR00002"))
        self.assertEqual(out3["status"], "ok", out3)

        first_input = self.root / "select-first.json"
        first_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001", "ideas": [{"id": "DIR00001_1"}]
        }]}, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(parse(run_cli(
            "stage4-finalize", "--program-root", self.root,
            "--selection-input", first_input))["status"], "ok")

        second_input = self.root / "select-second.json"
        second_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00002", "ideas": [{"id": "DIR00002_1"}]
        }]}, ensure_ascii=False), encoding="utf-8")
        out4 = parse(run_cli(
            "stage4-finalize", "--program-root", self.root,
            "--selection-input", second_input))
        self.assertEqual(out4["status"], "ok", out4)
        selection = json.loads((self.root / "教授研究" / "套磁选择.json").read_text(encoding="utf-8"))
        self.assertEqual({s["collection_key"] for s in selection["selections"]},
                         {"DIR00001", "DIR00002"})
        email_pack = json.loads((self.root / "教授研究" / "邮件输入.json").read_text(encoding="utf-8"))
        self.assertEqual({e["collection_key"] for e in email_pack["emails"]},
                         {"DIR00001", "DIR00002"})

    def test_07_partial_downgraded_and_email_use(self):
        out = self.stage2_run(gap_overrides={
            "AAAA1111": {"status": "partial", "evidence": "BBBB2222 做了一半",
                         "completed_part": "", "remaining_gap": ""}})
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        gap = pack["directions"][0]["gap_shortlist"][0]
        self.assertEqual(gap["status"], "unknown")
        self.assertTrue(gap["downgraded"])

    def test_08_manual_markdown_edit_needs_decision(self):
        self.stage3_run()
        md_path = self.prof_dir / "套磁想法候选.md"
        md_path.write_text(
            md_path.read_text(encoding="utf-8").replace("第二种输入模式", "手工改动"),
            encoding="utf-8")
        profile = self.root / "profile.md"
        profile.write_text("兴趣：变化后\n", encoding="utf-8")
        facts = self.write_facts()
        results = self.root / "results"
        s3 = self.root / "s3results"
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", s3, "--program-root", self.root,
                            "--profile", str(profile)))
        self.assertEqual(out["status"], "needs_decision")
        self.assertEqual(out["reason_code"], "manual_markdown_changed")
        decision = self.root / "decision.json"
        decision.write_text(json.dumps({"decision": "overwrite"}), encoding="utf-8")
        out2 = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                             "--results", s3, "--program-root", self.root,
                             "--profile", str(profile), "--decision-file", decision))
        self.assertEqual(out2["status"], "ok")

    def test_09_missing_result_keeps_state(self):
        self.stage3_run()
        state_bytes = (self.prof_dir / "套磁候选状态.json").read_bytes()
        profile = self.root / "profile.md"
        profile.write_text("兴趣：新一次变化\n", encoding="utf-8")
        empty = self.root / "empty_results"
        empty.mkdir(exist_ok=True)
        out = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                            "--results", empty, "--program-root", self.root,
                            "--profile", str(profile)))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "result_missing")
        self.assertEqual((self.prof_dir / "套磁候选状态.json").read_bytes(), state_bytes)

    def test_10_email_pack_self_contained(self):
        self.stage3_run()
        sel_input = self.root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1"}]}]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", sel_input))
        self.assertEqual(out["status"], "ok")
        raw = (self.root / "教授研究" / "邮件输入.json").read_text(encoding="utf-8")
        self.assertNotIn("论文分析", raw)
        self.assertNotIn("future_work.json", raw)
        self.assertNotIn("_index.json", raw)
        pack = json.loads(raw)
        email = pack["emails"][0]
        self.assertIn("allowed_sources", email)
        self.assertIn("gap:" + quote_id(self.gap_quotes["AAAA1111"]),
                      email["allowed_sources"])
        gap = email["gaps"][0]
        self.assertIn("quote", gap)
        self.assertIn("page", gap)
        self.assertIn("status", gap)

    def test_11_stage2_validator_is_persisted_separately(self):
        self.stage2_run(gap_overrides={
            "AAAA1111": {"status": "partial", "evidence": "仍有一部分待核对",
                          "completed_part": "已完成旧场景", "remaining_gap": "还需新场景"}})
        pack_path = self.prof_dir / "套磁候选输入.json"
        validation_path = self.root / "stage2-validation.json"
        validation_path.write_text(json.dumps({"results": [{
            "direction_id": "DIR00001", "result": "fail_after_2_rounds",
            "rounds": 2, "issues": [{"rule": "A1"}]}]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage2-record-validation", "--professor-dir", self.prof_dir,
                            "--validation-file", validation_path))
        self.assertEqual(out["status"], "ok", out)
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(pack["validator"]["results"]["DIR00001"]["result"], "fail_after_2_rounds")
        self.assertEqual(pack["directions"][0]["gap_shortlist"][0]["status"], "partial")
        old = pack_path.read_bytes()
        validation_path.write_text(json.dumps({"results": [{
            "collection_key": "NO_SUCH_DIRECTION", "result": "pass", "rounds": 1, "issues": []
        }]}, ensure_ascii=False), encoding="utf-8")
        bad = parse(run_cli("stage2-record-validation", "--professor-dir", self.prof_dir,
                            "--validation-file", validation_path))
        self.assertEqual(bad["status"], "error")
        self.assertEqual(pack_path.read_bytes(), old)

    def test_12_stage3_validator_is_persisted_separately(self):
        self.stage3_run()
        state_path = self.prof_dir / "套磁候选状态.json"
        validation_path = self.root / "stage3-validation.json"
        validation_path.write_text(json.dumps({"results": [{
            "direction_id": "DIR00001", "result": "pass", "rounds": 1, "issues": []
        }]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage3-record-validation", "--professor-dir", self.prof_dir,
                            "--validation-file", validation_path))
        self.assertEqual(out["status"], "ok", out)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["validator"]["results"]["DIR00001"]["result"], "pass")
        old = state_path.read_bytes()
        validation_path.write_text(json.dumps({"results": [{
            "collection_key": "NO_SUCH_DIRECTION", "result": "pass", "rounds": 1, "issues": []
        }]}, ensure_ascii=False), encoding="utf-8")
        bad = parse(run_cli("stage3-record-validation", "--professor-dir", self.prof_dir,
                            "--validation-file", validation_path))
        self.assertEqual(bad["status"], "error")
        self.assertEqual(state_path.read_bytes(), old)

    def test_13_stage2_validator_rewrite_round_trips_structured_narrative(self):
        self.stage2_run()
        validation_path = self.root / "stage2-rewrite-validation.json"
        validation_path.write_text(json.dumps({"results": [{
            "direction_id": "DIR00001", "result": "fail_after_2_rounds",
            "rounds": 2, "issues": [{"rule": "B5", "quote": "术语"}]
        }]}, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(parse(run_cli(
            "stage2-record-validation", "--professor-dir", self.prof_dir,
            "--validation-file", validation_path))["status"], "ok")

        facts = self.write_facts()
        plan = parse(run_cli("stage2-refine-plan", "--facts", facts,
                            "--validation-file", validation_path))
        self.assertEqual(plan["status"], "ok")
        self.assertEqual(len(plan["jobs"]), 1)
        model_input = plan["jobs"][0]["model_input"]
        self.assertIn("current_narrative", model_input)
        self.assertEqual(model_input["issues"][0]["rule"], "B5")

        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        narrative = pack["directions"][0]["narrative"]
        block = dict(narrative["positioning"][0])
        block["text"] = block["text"].replace("教授从", "教授先做了")
        rewrite = {
            "schema": 1, "kind": "narrative-rewrite", "collection_key": "DIR00001",
            "positioning": [block],
            "gap_notes": [{"gap_id": gap_id, "summary": value["summary"],
                           "explanation": value["explanation"]}
                          for gap_id, value in narrative["gap_notes"].items()]
        }
        results = self.root / "rewrite-results"
        results.mkdir()
        (results / "narrative-rewrite-DIR00001.json").write_text(
            json.dumps(rewrite, ensure_ascii=False), encoding="utf-8")
        cache_before = (self.prof_dir / "论文分析" / "_freshness_cache.json").read_bytes()
        out = parse(run_cli("stage2-refine-finalize", "--facts", facts,
                            "--results", results, "--validation-file", validation_path))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["rewritten"], ["DIR00001"])
        updated_pack = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertIn("教授先做了", updated_pack["directions"][0]["narrative"]["positioning"][0]["text"])
        self.assertNotIn("validator", updated_pack)
        self.assertEqual(cache_before,
                         (self.prof_dir / "论文分析" / "_freshness_cache.json").read_bytes())
        self.assertIn("教授先做了", (self.prof_dir / "套磁候选分析.md").read_text(encoding="utf-8"))

    def test_14_global_red_line_does_not_leak_item_key(self):
        def extra(facts):
            facts["directions"][0]["red_lines"].append({
                "scope": "global", "text": "不要把 AAAA1111 作为教授本人论文",
                "banned_phrases": []})

        self.stage2_run()
        facts = self.write_facts(extra)
        results = self.root / "redline-results"
        self.write_stage2_results(results)
        out = parse(run_cli("stage2-finalize", "--facts", facts, "--results", results))
        self.assertEqual(out["status"], "ok", out)
        md = (self.prof_dir / "套磁候选分析.md").read_text(encoding="utf-8")
        global_lines = [line for line in md.splitlines() if line.startswith("- 【全局】")]
        self.assertTrue(any("AAAA1111" not in line and
                           "Synthetic comparison of input patterns" in line
                           for line in global_lines))

    def test_15_stage2_refine_can_use_persisted_pack_without_facts(self):
        self.stage2_run()
        validation_path = self.root / "pack-only-validation.json"
        validation_path.write_text(json.dumps({"results": [{
            "direction_id": "DIR00001", "result": "fail_after_2_rounds",
            "rounds": 2, "issues": [{"rule": "B5"}]
        }]}, ensure_ascii=False), encoding="utf-8")
        plan = parse(run_cli("stage2-refine-plan", "--professor-dir", self.prof_dir,
                            "--validation-file", validation_path))
        self.assertEqual(plan["status"], "ok", plan)
        self.assertEqual(plan["directions"], ["DIR00001"])

        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        narrative = pack["directions"][0]["narrative"]
        block = dict(narrative["positioning"][0])
        block["text"] = block["text"].replace("教授从", "教授先做了")
        results = self.root / "pack-only-results"
        results.mkdir()
        (results / "narrative-rewrite-DIR00001.json").write_text(json.dumps({
            "schema": 1, "kind": "narrative-rewrite", "collection_key": "DIR00001",
            "positioning": [block], "gap_notes": []}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage2-refine-finalize", "--professor-dir", self.prof_dir,
                            "--results", results, "--validation-file", validation_path))
        self.assertEqual(out["status"], "ok", out)
        self.assertIn("教授先做了", (self.prof_dir / "套磁候选分析.md").read_text(encoding="utf-8"))


class TestStage5(BaseEnv):
    def test_stage5_requires_user_template(self):
        self.prepare()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "stage5-plan", "--program-root", str(self.root),
             "--mode", "first", "--template", str(self.root / "missing-template.md")],
            text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        payload = parse(result)
        self.assertEqual(payload["reason_code"], "template_error")

    def prepare(self):
        self.stage3_run()
        sel_input = self.root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1"}]}]}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage4-finalize", "--program-root", self.root,
                            "--selection-input", sel_input))
        self.assertEqual(out["status"], "ok", out)
        (self.root / "info.json").write_text(json.dumps({
            "university": "試験大学", "department": "試験研究科",
            "target": {"intake_year": 2027, "intake_term": "april"}}), encoding="utf-8")
        (self.root / "boshu_analysis.json").write_text(json.dumps({
            "exam_type": {"degree": "博士前期課程", "selection_name": "春季 テスト選抜 合成工学専攻"}
        }, ensure_ascii=False), encoding="utf-8")
        import time as time_mod
        stat = (self.root / "info.json").stat()
        boshu_stat = (self.root / "boshu_analysis.json").stat()
        verify = {
            "professor": "試験 教授", "verified_at": "2026-08-27T16:00:00Z",
            "source_fingerprints": {
                "info_json": f"{self.root / 'info.json'}:{int(stat.st_mtime)}",
                "boshu_analysis": f"{self.root / 'boshu_analysis.json'}:{int(boshu_stat.st_mtime)}"},
            "items": {
                "email": {"verdict": "confirmed", "value": "faculty@example.test", "sources": []},
                "roster": {"verdict": "confirmed", "value": "X分野/教授 @P.1", "sources": []},
                "season": {"verdict": "confirmed", "value": "春季 少数名", "sources": []},
                "header": {"verdict": "confirmed", "value": "", "sources": []},
                "subject_batch": {"verdict": "confirmed", "value": "", "sources": []},
                "schedule": {"verdict": "unverified", "value": None, "sources": []},
                "consent": {"verdict": "unverified", "value": None, "sources": []},
                "warnings": []}}
        (self.prof_dir / "_contact_verify.json").write_text(
            json.dumps(verify, ensure_ascii=False, indent=1), encoding="utf-8")
        return quote_id(self.gap_quotes["AAAA1111"])

    def raw_result(self, g1):
        email_id = "試験 教授::DIR00001::DIR00001_1"
        return {"schema": 1, "kind": "email", "email_id": email_id,
                "interest_sentences_ja": [
                    "合成输入を比较する仕組みを、分かりやすく検証できる形にしたいと考えてきました。",
                    "先生のご論文「Synthetic comparison of input patterns」を拝読し、入力比較を広げる可能性に気づかされました。",
                    "例えば、別の合成入力でも同じ比較ができれば、といったことです。",
                    "このような比較場面は、まだ数多く存在すると感じております。"],
                "future_aspiration_ja": "入力設計、評価実験、実データへの適用",
                "learning_candidates": ["比較手法の基礎知識の習得", "評価方法の基礎"],
                "source_map": [
                    {"output": "①", "source_ids": ["profile.interest"]},
                    {"output": "②", "source_ids": ["paper:AAAA1111"]},
                    {"output": "③", "source_ids": [f"gap:{g1}"]},
                    {"output": "④", "source_ids": ["template"]},
                    {"output": "future", "source_ids": ["idea:DIR00001_1"]}]}

    def choices(self):
        return {"email_id": "試験 教授::DIR00001::DIR00001_1", "first_choice": False,
                "signature_name": "試験 太郎", "learning": "比較手法の基礎知識の習得"}

    def test_stage5_full_flow_and_fact_card(self):
        g1 = self.prepare()
        raw_path = self.root / "email_raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "choices.json"
        choices_path.write_text(json.dumps(self.choices(), ensure_ascii=False), encoding="utf-8")
        draft = parse(run_cli("stage5-plan", "--program-root", self.root,
                              "--result", raw_path, "--choices", choices_path))
        self.assertEqual(draft["status"], "ok", draft)
        humanized_path = self.root / "humanized.txt"
        humanized_path.write_text(draft["drafts"][0]["draft"], encoding="utf-8")
        out = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", raw_path, "--humanized", humanized_path,
                            "--choices", choices_path))
        self.assertEqual(out["status"], "ok", out)
        md = (self.prof_dir / "套磁邮件.md").read_text(encoding="utf-8")
        self.assertIn("## 送信前核对", md)
        self.assertIn("| 抬头逐字 | 試験大学／試験研究科／試験 教授先生 | confirmed |", md)
        self.assertIn("## 事实核对卡（发送前人工确认）", md)
        self.assertIn("<details>", md)
        self.assertIn("作者原话", md)
        self.assertIn("zotero://select/library/items/AAAA1111", md)
        txt = (self.prof_dir / "套磁邮件.txt").read_text(encoding="utf-8")
        self.assertTrue(txt.startswith("Subject: "))
        self.assertNotIn("managed_by", txt)
        self.assertNotIn("事实核对卡", txt)
        self.assertNotIn("送信前核对", txt)

        validation_path = self.root / "validation.json"
        validation_path.write_text(json.dumps({"results": [{
            "email_id": self.choices()["email_id"], "result": "pass",
            "rounds": 1, "issues": []}]}, ensure_ascii=False), encoding="utf-8")
        validation = parse(run_cli("stage5-record-validation", "--professor-dir",
                                   self.prof_dir, "--validation-file", validation_path))
        self.assertEqual(validation["status"], "ok", validation)
        state = json.loads((self.prof_dir / "套磁邮件状态.json").read_text(encoding="utf-8"))
        self.assertEqual(state["emails"][self.choices()["email_id"]]["validation"]["result"], "pass")

    def test_stage5_checklist_header_row_matches_body_salutation(self):
        # The 「抬头逐字」 checklist row must show the assembled body's own
        # salutation line verbatim; a synthesized header variant (e.g. one
        # that appends 「：」 the user template never had) diverges from the
        # body and the rendered file contradicts itself.
        g1 = self.prepare()
        raw_path = self.root / "email_raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "choices.json"
        choices_path.write_text(json.dumps(self.choices(), ensure_ascii=False), encoding="utf-8")
        draft = parse(run_cli("stage5-plan", "--program-root", self.root,
                              "--result", raw_path, "--choices", choices_path))
        self.assertEqual(draft["status"], "ok", draft)
        humanized_path = self.root / "humanized.txt"
        humanized_path.write_text(draft["drafts"][0]["draft"], encoding="utf-8")
        out = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", raw_path, "--humanized", humanized_path,
                            "--choices", choices_path))
        self.assertEqual(out["status"], "ok", out)
        md = (self.prof_dir / "套磁邮件.md").read_text(encoding="utf-8")
        row = next(line for line in md.splitlines() if line.startswith("| 抬头逐字 |"))
        header_cell = row.split("|")[2].strip()
        body_section = md.split("## 邮件正文", 1)[1]
        salutation = next(line.strip() for line in body_section.splitlines()
                          if "試験 教授" in line)
        self.assertEqual(header_cell, salutation)

    def test_stage5_both_outputs_followup_reuses_facts_and_date(self):
        g1 = self.prepare()
        raw_path = self.root / "both-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices = dict(self.choices(), initial_sent_date="2026年9月1日")
        choices_path = self.root / "both-choices.json"
        choices_path.write_text(json.dumps(choices, ensure_ascii=False), encoding="utf-8")

        draft = parse(run_cli("stage5-plan", "--program-root", self.root, "--mode", "both",
                              "--result", raw_path, "--choices", choices_path))
        self.assertEqual(draft["status"], "ok", draft)
        self.assertEqual({row["output_id"] for row in draft["drafts"]},
                         {choices["email_id"], choices["email_id"] + "::followup"})
        followup = next(row for row in draft["drafts"] if row["kind"] == "followup")
        self.assertIn("2026年9月1日", followup["draft"])
        self.assertIn("合成输入比较", followup["draft"])
        self.assertIn("Re: ", followup["draft"])

        initial_path = self.root / "both-initial.txt"
        followup_path = self.root / "both-followup.txt"
        initial_path.write_text(next(row for row in draft["drafts"] if row["kind"] == "initial")["draft"],
                                encoding="utf-8")
        followup_path.write_text(followup["draft"], encoding="utf-8")
        map_path = self.root / "both-map.json"
        map_path.write_text(json.dumps({choices["email_id"]: str(initial_path),
                                        choices["email_id"] + "::followup": str(followup_path)},
                                       ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage5-finalize", "--program-root", self.root, "--mode", "both",
                            "--result", raw_path, "--humanized-map", map_path,
                            "--choices", choices_path))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual({row["kind"] for row in out["emails"]}, {"initial", "followup"})
        followup_md = self.prof_dir / "套磁跟进邮件.md"
        self.assertTrue(followup_md.is_file())
        followup_text = followup_md.read_text(encoding="utf-8")
        self.assertIn("类型：无回复跟进", followup_text)
        self.assertIn("初次发送日：2026年9月1日", followup_text)
        self.assertIn("## 送信前核对", followup_text)
        self.assertIn("首封邮件中的研究方向", followup_text)
        state = json.loads((self.prof_dir / "套磁邮件状态.json").read_text(encoding="utf-8"))
        self.assertIn("followup", state["emails"][choices["email_id"]])

        validation_path = self.root / "both-validation.json"
        validation_path.write_text(json.dumps({"results": [
            {"email_id": choices["email_id"], "result": "pass", "rounds": 1, "issues": []},
            {"email_id": choices["email_id"], "output_id": choices["email_id"] + "::followup",
             "result": "pass", "rounds": 1, "issues": []}]}, ensure_ascii=False), encoding="utf-8")
        validation = parse(run_cli("stage5-record-validation", "--professor-dir", self.prof_dir,
                                   "--validation-file", validation_path))
        self.assertEqual(validation["status"], "ok", validation)
        state = json.loads((self.prof_dir / "套磁邮件状态.json").read_text(encoding="utf-8"))
        self.assertEqual(state["emails"][choices["email_id"]]["followup"]["validation"]["result"], "pass")

    def test_stage5_multiple_emails_use_distinct_files(self):
        g1 = self.prepare()
        pack_path = self.root / "教授研究" / "邮件输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        second = json.loads(json.dumps(pack["emails"][0], ensure_ascii=False))
        second_id = "试验 教授::DIR00001::DIR00001_2"
        second["email_id"] = second_id
        second["idea"]["id"] = "DIR00001_2"
        second["idea"]["title"] = "第二个候选"
        second["allowed_sources"].append("idea:DIR00001_2")
        pack["emails"].append(second)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

        raw1 = self.raw_result(g1)
        raw2 = json.loads(json.dumps(raw1, ensure_ascii=False))
        raw2["email_id"] = second_id
        raw2["source_map"][-1]["source_ids"] = ["idea:DIR00001_2"]
        raw_path = self.root / "email_raw.json"
        raw_path.write_text(json.dumps([raw1, raw2], ensure_ascii=False), encoding="utf-8")
        choices1 = self.choices()
        choices2 = dict(choices1, email_id=second_id)
        choices_path = self.root / "choices.json"
        choices_path.write_text(json.dumps([choices1, choices2], ensure_ascii=False), encoding="utf-8")

        draft = parse(run_cli("stage5-plan", "--program-root", self.root,
                              "--result", raw_path, "--choices", choices_path))
        self.assertEqual(draft["status"], "ok", draft)
        self.assertEqual(len(draft["drafts"]), 2)
        humanized_one = self.root / "humanized-one.txt"
        humanized_two = self.root / "humanized-two.txt"
        humanized_one.write_text(draft["drafts"][0]["draft"], encoding="utf-8")
        humanized_two.write_text(draft["drafts"][1]["draft"], encoding="utf-8")
        humanized_map = self.root / "humanized-map.json"
        humanized_map.write_text(json.dumps({
            self.choices()["email_id"]: str(humanized_one),
            second_id: str(humanized_two)}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", raw_path, "--humanized-map", humanized_map,
                            "--choices", choices_path))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(len(out["emails"]), 2)
        md_paths = {Path(row["md"]) for row in out["emails"]}
        txt_paths = {Path(row["txt"]) for row in out["emails"]}
        self.assertEqual(len(md_paths), 2)
        self.assertEqual(len(txt_paths), 2)
        self.assertTrue(all(path.is_file() for path in md_paths | txt_paths))
        self.assertNotIn(self.prof_dir / "套磁邮件.md", md_paths)
        self.assertNotIn(self.prof_dir / "套磁邮件.txt", txt_paths)

        one = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", raw_path, "--humanized-map", humanized_map,
                            "--choices", choices_path, "--email-id", second_id))
        self.assertEqual(one["status"], "ok", one)
        self.assertEqual(Path(one["emails"][0]["md"]),
                         next(path for path in md_paths if "DIR00001_2" in path.name))

        overview = (self.root / "教授研究" / "套磁邮件总览.md").read_text(encoding="utf-8")
        self.assertEqual(overview.count("[.md]("), 2)
        state = json.loads((self.prof_dir / "套磁邮件状态.json").read_text(encoding="utf-8"))
        self.assertEqual({entry["files"]["md"] for entry in state["emails"].values()},
                         {str(path) for path in md_paths})

    def test_stage5_batch_failure_does_not_write_first_email(self):
        g1 = self.prepare()
        raw1 = self.raw_result(g1)
        raw_one_path = self.root / "first-raw.json"
        raw_one_path.write_text(json.dumps(raw1, ensure_ascii=False), encoding="utf-8")
        choices_one_path = self.root / "first-choices.json"
        choices_one_path.write_text(json.dumps(self.choices(), ensure_ascii=False), encoding="utf-8")
        draft = parse(run_cli("stage5-plan", "--program-root", self.root,
                              "--result", raw_one_path, "--choices", choices_one_path))
        self.assertEqual(draft["status"], "ok", draft)
        raw2 = json.loads(json.dumps(raw1, ensure_ascii=False))
        second_id = "试验 教授::DIR00001::DIR00001_2"
        pack_path = self.root / "教授研究" / "邮件输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        second = json.loads(json.dumps(pack["emails"][0], ensure_ascii=False))
        second["email_id"] = second_id
        second["idea"]["id"] = "DIR00001_2"
        second["allowed_sources"].append("idea:DIR00001_2")
        pack["emails"].append(second)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        raw2["email_id"] = second_id
        raw2["future_aspiration_ja"] = ""
        raw_path = self.root / "batch-raw.json"
        raw_path.write_text(json.dumps([raw1, raw2], ensure_ascii=False), encoding="utf-8")
        choices = [self.choices(), dict(self.choices(), email_id=second_id)]
        choices_path = self.root / "batch-choices.json"
        choices_path.write_text(json.dumps(choices, ensure_ascii=False), encoding="utf-8")
        first_humanized = self.root / "first-humanized.txt"
        second_humanized = self.root / "second-humanized.txt"
        first_humanized.write_text(draft["drafts"][0]["draft"], encoding="utf-8")
        second_humanized.write_text("unused", encoding="utf-8")
        map_path = self.root / "batch-map.json"
        map_path.write_text(json.dumps({
            self.choices()["email_id"]: str(first_humanized),
            second_id: str(second_humanized)}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", raw_path, "--humanized-map", map_path,
                            "--choices", choices_path))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "invalid_result_json")
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())
        self.assertFalse((self.prof_dir / "套磁邮件状态.json").exists())

    def test_humanizer_lost_title_rejected(self):
        g1 = self.prepare()
        raw_path = self.root / "email_raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "choices.json"
        choices_path.write_text(json.dumps(self.choices(), ensure_ascii=False), encoding="utf-8")
        draft = parse(run_cli("stage5-plan", "--program-root", self.root,
                              "--result", raw_path, "--choices", choices_path))
        humanized_path = self.root / "humanized.txt"
        broken = draft["drafts"][0]["draft"].replace(
            "Synthetic comparison of input patterns", "参考論文")
        humanized_path.write_text(broken, encoding="utf-8")
        out = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", raw_path, "--humanized", humanized_path,
                            "--choices", choices_path))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "humanizer_violation")
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())

    def test_stage5_requires_explicit_user_choices(self):
        g1 = self.prepare()
        raw_path = self.root / "missing-choice-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "missing-choice.json"
        choices_path.write_text(json.dumps({"email_id": self.choices()["email_id"],
                                             "signature_name": "试验 太郎",
                                             "learning": "机器学习基础"}, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage5-plan", "--program-root", self.root,
                            "--result", raw_path, "--choices", choices_path))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "missing_user_choice")
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())

    def test_done_by_self_gap_banned_in_source_map(self):
        self.stage2_run(gap_overrides={
            "AAAA1111": {"status": "done_by_self", "evidence": "已由教授后续论文接住"}})
        g1 = quote_id(self.gap_quotes["AAAA1111"])
        s3 = self.root / "s3results"
        s3.mkdir(parents=True, exist_ok=True)
        doc = {"schema": 2, "kind": "candidates", "direction_id": "DIR00001",
               "mode": "generated",
               "candidates": [{
                   "id": "X1", "kind": "direction", "direction_ids": ["DIR00001"],
                   "title": "踩已完成点的延伸", "one_liner": "o",
                   "research_question": "rq?",
                   "points": [],
                   "gap_refs": [{"direction_id": "DIR00001", "item_key": "AAAA1111",
                                 "gap_id": g1}],
                    "anchor_notes": {"difference_point": "用第二种合成输入而非第一种输入"},
                   "papers": [], "fit": "null", "red_lines": []},
                   {"id": "X2", "kind": "direction", "direction_ids": ["DIR00001"],
                    "title": "t", "one_liner": "o",
                    "research_question": "rq?", "points": [], "gap_refs": [],
                    "papers": [], "fit": "null", "red_lines": []},
                   {"id": "X3", "kind": "direction", "direction_ids": ["DIR00001"],
                    "title": "t", "one_liner": "o",
                    "research_question": "rq?", "points": [], "gap_refs": [],
                    "papers": [], "fit": "null", "red_lines": []}]}
        (s3 / result_file("candidates", "DIR00001")).write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        out3 = parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                             "--results", s3, "--program-root", self.root))
        self.assertEqual(out3["status"], "ok", out3)
        sel_input = self.root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
             "ideas": [{"id": "X1"}]}]}, ensure_ascii=False), encoding="utf-8")
        out4 = parse(run_cli("stage4-finalize", "--program-root", self.root,
                             "--selection-input", sel_input))
        self.assertEqual(out4["status"], "ok", out4)
        email_pack = json.loads(
            (self.root / "教授研究" / "邮件输入.json").read_text(encoding="utf-8"))
        self.assertEqual(email_pack["emails"][0]["anchorable_gaps"], [])
        raw = self.raw_result(g1)
        raw["email_id"] = "試験 教授::DIR00001::X1"
        raw_path = self.root / "email_raw.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage5-plan", "--program-root", self.root,
                            "--result", raw_path))
        self.assertEqual(out["status"], "error")
        self.assertIn("done_by_self", out.get("message", ""))


class TestMigrate(BaseEnv):
    def test_migrate_plan_legacy_needs_stage2(self):
        (self.prof_dir / "论文分析" / "_index.json").write_text(json.dumps({
            "professor": "試験 教授", "directions": [], "papers": {
                "AAAA1111": {"file": "x.md", "gap": "old quote", "gap_status": "open"}}},
            ensure_ascii=False), encoding="utf-8")
        plan = parse(run_cli("migrate-v3", "--plan", "--program-root", self.root))
        self.assertEqual(plan["status"], "ok")
        self.assertEqual(plan["directions"][0]["classification"], "needs_stage2")
        self.assertEqual(plan["ready_count"], 0)

    def test_migrate_ready_apply_without_model(self):
        for key, quote in self.gap_quotes.items():
            index_path = self.prof_dir / "论文分析" / "_index.json"
            papers = {}
            for k, q in self.gap_quotes.items():
                papers[k] = {
                    "file": str(self.prof_dir / "论文分析" / f"{k}.md"),
                    "authorship": "first", "future_work_sidecar": str(
                        self.prof_dir / "论文分析" / f"{k}.md.future_work.json"),
                    "gaps": [{"gap_id": quote_id(q), "status": "open", "evidence": "无更晚论文"}]}
            index_path.write_text(json.dumps({
                "schema": 2, "future_work_schema": 1, "professor": "試験 教授",
                "direction": {"collection_key": "DIR00001", "name_ja": "合成输入比较"},
                "credibility": {"verdict": "站得住", "mainline": "主线"},
                "papers": papers}, ensure_ascii=False), encoding="utf-8")
            break
        (self.prof_dir / "套磁想法候选.md").write_text(
            "<!-- candidate_meta: {\"id\":\"c1\",\"gap_ids\":[{\"item_key\":\"AAAA1111\","
            "\"gap_id\":\"" + quote_id(self.gap_quotes["AAAA1111"]) + "\"}]} -->\n",
            encoding="utf-8")
        (self.prof_dir / "papers.json").write_text(json.dumps({"papers": [
            {"item_key": key, "title": self.papers[index]["title"],
             "year": self.papers[index]["year"], "authorship": "first"}
            for index, key in enumerate(("AAAA1111", "BBBB2222"))]},
            ensure_ascii=False), encoding="utf-8")
        plan = parse(run_cli("migrate-v3", "--plan", "--program-root", self.root))
        entry = plan["directions"][0]
        self.assertEqual(entry["classification"], "ready")
        self.assertEqual(plan["ready_count"], 1)
        plan_path = self.root / "mplan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("migrate-v3", "--apply", plan_path, "--program-root", self.root))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(len(out["applied"]), 1)
        pack = json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))
        self.assertTrue(pack.get("migrated"))
        cache = json.loads((self.prof_dir / "论文分析" / "_freshness_cache.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cache["entries"]), 2)
        for entry_e in cache["entries"].values():
            self.assertTrue(entry_e.get("migrated"))
        plan_after = parse(run_cli("migrate-v3", "--plan", "--program-root", self.root))
        self.assertEqual(plan_after["ready_count"], 0)

    def test_migrate_gap_id_mismatch_is_blocked(self):
        index_path = self.prof_dir / "论文分析" / "_index.json"
        quote = self.gap_quotes["AAAA1111"]
        index_path.write_text(json.dumps({
            "schema": 2, "future_work_schema": 1, "professor": "试验 教授",
            "papers": {"AAAA1111": {
                "file": str(self.prof_dir / "论文分析" / "AAAA1111.md"),
                "authorship": "first", "future_work_sidecar": str(
                    self.prof_dir / "论文分析" / "AAAA1111.md.future_work.json"),
                "gaps": [{"gap_id": "f" * 64, "status": "open", "evidence": "x"}]}}},
            ensure_ascii=False), encoding="utf-8")
        (self.prof_dir / "papers.json").write_text(json.dumps({"papers": [
            {"item_key": "AAAA1111", "title": "A", "year": 2024, "authorship": "first"}
        ]}, ensure_ascii=False), encoding="utf-8")
        plan = parse(run_cli("migrate-v3", "--plan", "--program-root", self.root))
        entry = plan["directions"][0]
        self.assertNotEqual(entry["classification"], "ready")
        self.assertTrue(any("gap ID" in reason for reason in entry["reasons"]))
        self.assertEqual(plan["ready_count"], 0)

    def test_migrate_missing_metadata_is_not_ready(self):
        index_path = self.prof_dir / "论文分析" / "_index.json"
        quote = self.gap_quotes["AAAA1111"]
        index_path.write_text(json.dumps({
            "schema": 2, "future_work_schema": 1, "professor": "试验 教授",
            "papers": {"AAAA1111": {
                "file": str(self.prof_dir / "论文分析" / "AAAA1111.md"),
                "authorship": "first", "future_work_sidecar": str(
                    self.prof_dir / "论文分析" / "AAAA1111.md.future_work.json"),
                "gaps": [{"gap_id": quote_id(quote), "status": "open", "evidence": "x"}]}}},
            ensure_ascii=False), encoding="utf-8")
        (self.prof_dir / "套磁想法候选.md").write_text(
            "<!-- candidate_meta: {\"id\":\"c1\",\"gap_ids\":[{\"item_key\":\"AAAA1111\","
            "\"gap_id\":\"" + quote_id(quote) + "\"}]} -->\n", encoding="utf-8")
        plan = parse(run_cli("migrate-v3", "--plan", "--program-root", self.root))
        self.assertEqual(plan["directions"][0]["classification"], "blocked")
        self.assertEqual(plan["ready_count"], 0)

    def test_migrate_scans_no_category_fallback(self):
        fallback = self.root / "教授研究" / "无分类教授"
        (fallback / "论文分析").mkdir(parents=True)
        analysis = fallback / "论文分析" / "P.md"
        analysis.write_text("# analysis\n", encoding="utf-8")
        quote = "a future item"
        make_sidecar(analysis, [quote])
        gap_id = quote_id(quote)
        (fallback / "论文分析" / "_index.json").write_text(json.dumps({
            "schema": 2, "future_work_schema": 1, "professor": "无分类教授",
            "papers": {"PKEY001": {"file": str(analysis), "authorship": "first",
                "future_work_sidecar": str(Path(str(analysis) + ".future_work.json")),
                "gaps": [{"gap_id": gap_id, "status": "open", "evidence": "x"}]}}},
            ensure_ascii=False), encoding="utf-8")
        (fallback / "papers.json").write_text(json.dumps({"papers": [
            {"item_key": "PKEY001", "title": "Fallback paper", "year": 2024, "authorship": "first"}
        ]}, ensure_ascii=False), encoding="utf-8")
        (fallback / "套磁想法候选.md").write_text(
            "<!-- candidate_meta: {\"id\":\"c1\",\"gap_ids\":[{\"item_key\":\"PKEY001\","
            "\"gap_id\":\"" + gap_id + "\"}]} -->\n", encoding="utf-8")
        plan = parse(run_cli("migrate-v3", "--plan", "--program-root", self.root))
        entry = next(e for e in plan["directions"] if e["professor"] == "无分类教授")
        self.assertEqual(entry["classification"], "ready")

    def test_migrate_existing_input_pack_is_skipped(self):
        index_path = self.prof_dir / "论文分析" / "_index.json"
        papers = {}
        for key, quote in self.gap_quotes.items():
            papers[key] = {
                "file": str(self.prof_dir / "论文分析" / f"{key}.md"),
                "authorship": "first",
                "future_work_sidecar": str(self.prof_dir / "论文分析" / f"{key}.md.future_work.json"),
                "gaps": [{"gap_id": quote_id(quote), "status": "open", "evidence": "无更晚论文"}]}
        index_path.write_text(json.dumps({
            "schema": 2, "future_work_schema": 1, "professor": "試験 教授",
             "direction": {"collection_key": "DIR00001", "name_ja": "合成输入比较"},
            "papers": papers}, ensure_ascii=False), encoding="utf-8")
        (self.prof_dir / "papers.json").write_text(json.dumps({"papers": [
            {"item_key": key, "title": self.papers[index]["title"],
             "year": self.papers[index]["year"], "authorship": "first"}
            for index, key in enumerate(("AAAA1111", "BBBB2222"))]
        }, ensure_ascii=False), encoding="utf-8")
        (self.prof_dir / "套磁想法候选.md").write_text(
            "<!-- candidate_meta: {\"id\":\"c1\",\"gap_ids\":[{\"item_key\":\"AAAA1111\","
            "\"gap_id\":\"" + quote_id(self.gap_quotes["AAAA1111"]) + "\"}]} -->\n",
            encoding="utf-8")
        (self.prof_dir / "套磁候选输入.json").write_text(
            json.dumps({"schema": 2, "migrated": True}, ensure_ascii=False), encoding="utf-8")
        plan = parse(run_cli("migrate-v3", "--plan", "--program-root", self.root))
        entry = next(e for e in plan["directions"] if e["professor"] == "試験 教授")
        self.assertTrue(entry["already_migrated"])
        self.assertEqual(plan["ready_count"], 0)
        plan_path = self.root / "already-migrated-plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("migrate-v3", "--apply", plan_path, "--program-root", self.root))
        self.assertEqual(out["status"], "ok")
        self.assertTrue(any(row["reason"] == "already_migrated" for row in out["skipped"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
