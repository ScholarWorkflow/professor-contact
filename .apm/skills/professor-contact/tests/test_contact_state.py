import argparse
import contextlib
import hashlib
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from datetime import datetime
from pathlib import Path
from issue64_test_support import path_set
from stage2_upstream_fixture import run_bound_stage2_plan, run_bound_stage2_finalize

import importlib.util

from _stage4_handoff_test_support import stage4_row, stage4_rows

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"

_spec = importlib.util.spec_from_file_location("contact_state", SCRIPT)
contact_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contact_state)

_stage1_spec = importlib.util.spec_from_file_location(
    "contact_stage1_state_tests", ROOT / "scripts" / "contact_stage1.py")
contact_stage1 = importlib.util.module_from_spec(_stage1_spec)
sys.modules[_stage1_spec.name] = contact_stage1
_stage1_spec.loader.exec_module(contact_stage1)

_targets_spec = importlib.util.spec_from_file_location(
    "contact_targets_state_tests", ROOT / "scripts" / "contact_targets.py")
contact_targets = importlib.util.module_from_spec(_targets_spec)
sys.modules[_targets_spec.name] = contact_targets
_targets_spec.loader.exec_module(contact_targets)


def result_file(kind: str, identity: str) -> str:
    """Mirror the runner's deterministic result-file naming (issue #8)."""
    return contact_state.safe_result_file(kind, identity)


def quote_id(quote: str) -> str:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", quote)).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def stage5_templates(root: Path) -> tuple[Path, Path]:
    """Deterministic synthetic templates the Stage-5 renderer requires."""
    template = root / "synthetic-template.md"
    followup = root / "synthetic-followup-template.md"
    if not template.exists():
        template.write_text("{{大学}}／{{研究科}}／{{先生名}}先生\n{{出身校}} {{氏名}}\n{{入学年度}} {{入学月}} {{専攻}} {{学位}}\n{{兴趣段}}\n{{未来志向}}\n{{学習中}}\n{{志望}}", encoding="utf-8")
    if not followup.exists():
        followup.write_text("{{先生名}}先生\n{{大学}} {{研究科}} {{学位}}\n{{出身校}} {{氏名}}\n{{初回送信日}}\n{{研究主题}}\n{{メールアドレス}}", encoding="utf-8")
    return template, followup


def run_cli(*arguments):
    args = list(map(str, arguments))
    if args and args[0] in {"stage5-plan", "stage5-finalize"} and "--program-root" in args:
        root = Path(args[args.index("--program-root") + 1])
        template, followup = stage5_templates(root)
        if "--template" not in args:
            args.extend(["--template", str(template)])
        if "--mode" in args and args[args.index("--mode") + 1] in {"both", "followup"} and "--followup-template" not in args:
            args.extend(["--followup-template", str(followup)])
        # Issue #67 handoff: Stage-4 email facts are professor-local, so a Stage-5
        # fixture that has committed exactly one local pack passes that exact path
        # to the runner instead of relying on the legacy program-level default.
        if "--email-pack" not in args:
            pack_name = contact_state.EMAIL_PACK
            local_packs = sorted(root.glob(f"教授研究/*/{pack_name}")) + \
                sorted(root.glob(f"教授研究/*/*/{pack_name}"))
            if len(local_packs) == 1:
                args.extend(["--email-pack", str(local_packs[0])])
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          text=True, capture_output=True, check=False)


def raw_cli(*arguments):
    """Run the CLI with exactly these arguments: no fixture-side inference."""
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
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

    def run_bound_stage2_plan(self, facts: Path):
        return run_bound_stage2_plan(run_cli, facts)

    def stage2_run(self, gap_overrides=None):
        facts = self.write_facts()
        results = self.root / "results"
        self.write_stage2_results(results, gap_overrides)
        plan = parse(self.run_bound_stage2_plan(facts))
        self.assertEqual(plan["status"], "ok")
        out = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(out["status"], "ok", out)
        return out

    def stage3_run(self, profile=None, candidate_extra=None):
        facts = self.write_facts()
        results = self.root / "results"
        self.write_stage2_results(results)
        self.assertEqual(parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))["status"], "ok")
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
        plan = parse(self.run_bound_stage2_plan(facts))
        direction = plan["directions"][0]
        self.assertLessEqual(direction["judge_count"], 10)
        self.assertGreaterEqual(direction["judge_count"], 5)
        plan2 = parse(self.run_bound_stage2_plan(facts))
        self.assertEqual(plan["directions"][0]["judge_count"],
                         plan2["directions"][0]["judge_count"])

    def test_01b_same_year_month_order_is_conservative(self):
        for source_month, paper_month in ((12, 1), (None, 1), (12, None)):
            def extra(facts, source_month=source_month, paper_month=paper_month):
                facts["papers"][1]["year"] = 2023
                facts["papers"][0]["month"] = source_month
                facts["papers"][1]["month"] = paper_month

            facts = self.write_facts(extra)
            plan = parse(self.run_bound_stage2_plan(facts))
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
        plan = parse(self.run_bound_stage2_plan(self.write_facts()))
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
        out = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_reference_id")
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_02_freshness_cache_partial_invalidation(self):
        self.stage2_run()
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertEqual(len(cache["entries"]), 2)
        results = self.root / "results"
        out = parse(run_bound_stage2_finalize(run_cli, self.write_facts(), "--results", results))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["freshness_judged"], 0)
        for paper in self.papers:
            if paper["item_key"] == "BBBB2222":
                paper["abstract"] = "updated abstract of the 2024 real-time paper"
        results2 = self.root / "results2"
        self.write_stage2_results(results2)
        out2 = parse(run_bound_stage2_finalize(run_cli, self.write_facts(), "--results", results2))
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
        out4 = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                        "--selection-input", sel_input,
                                        "--profile", str(profile))))
        self.assertEqual(out4["status"], "needs_refresh")
        self.assertEqual(out4["reason_code"], "profile_changed")
        self.assertFalse((self.root / "教授研究" / "套磁选择.json").exists())
        self.assertFalse((self.prof_dir / "套磁选择.json").exists())

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

    def test_05e_overview_manual_edit_does_not_block_local_finalize(self):
        # Issue #66: the program overview is a derived projection owned by
        # stage3-rebuild-overview. A manual overview edit (or any program-level
        # projection problem) must NOT block, roll back or re-judge a legal
        # professor-local Stage-3 commit, and finalize must not touch the
        # overview or the projection registry at all.
        self.stage3_run()
        md_path = self.prof_dir / "套磁想法候选.md"
        state_path = self.prof_dir / "套磁候选状态.json"
        overview_path = self.root / "教授研究" / "套磁想法候选总览.md"
        registry_path = self.root / "教授研究" / "_contact_projections.json"
        overview_path.write_text(
            "# 套磁想法候选总览\n\n上一轮 rebuild 留下的聚合。\n", encoding="utf-8")
        overview_before = overview_path.read_bytes()
        registry_missing_before = not registry_path.exists()
        overview_path.write_text(
            overview_path.read_text(encoding="utf-8").replace("聚合", "手工改动"),
            encoding="utf-8")
        overview_edited = overview_path.read_bytes()
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
        self.assertEqual(out["status"], "ok", out)
        # The professor-local pair advanced to the new profile render…
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["profile_fingerprint"],
                         contact_state.profile_fingerprint(str(profile)))
        rendered = md_path.read_text(encoding="utf-8")
        _, md_body = contact_state.split_frontmatter(rendered)
        self.assertEqual(state["cache"]["render"]["套磁想法候选.md"]["sha256"],
                         contact_state.sha256_text(md_body))
        # …while the overview keeps the manual edit byte-for-byte and the
        # registry is never created or touched by the local commit.
        self.assertEqual(overview_path.read_bytes(), overview_edited)
        self.assertNotEqual(overview_edited, overview_before)
        self.assertTrue(registry_missing_before)
        self.assertFalse(registry_path.exists())

    def test_06_email_pack_exact_join_only(self):
        self.stage3_run()
        g1 = quote_id(self.gap_quotes["AAAA1111"])
        sel_input = self.root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1", "note": "ok"}]}]}, ensure_ascii=False), encoding="utf-8")
        out = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                       "--selection-input", sel_input)))
        self.assertEqual(out["status"], "ok", out)
        pack = json.loads((self.prof_dir / "邮件输入.json").read_text(encoding="utf-8"))
        email = pack["emails"][0]
        self.assertEqual([g["gap_id"] for g in email["gaps"]], [g1])
        self.assertEqual(email["gaps"][0]["status"], "open")
        (sel_input).write_text(json.dumps(
            {"selections": [{
                "professor": "試験 教授", "professor_dir": str(self.prof_dir),
                "collection_key": "DIR00001",
                "ideas": [{"id": "no_such_idea"}]}]}, ensure_ascii=False), encoding="utf-8")
        out2 = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                        "--selection-input", sel_input)))
        self.assertEqual(out2["status"], "error")
        self.assertEqual(out2["reason_code"], "unknown_idea_id")

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
        out = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                       "--selection-input", sel_input)))
        self.assertEqual(out["status"], "ok", out)
        email = json.loads((self.prof_dir / "邮件输入.json").read_text(
            encoding="utf-8"))["emails"][0]
        self.assertEqual([paper["item_key"] for paper in email["papers"]], ["AAAA1111"])
        self.assertEqual(email["papers"][0]["title"], "Synthetic comparison of input patterns")

    def test_06c_invalid_papers_override_does_not_write(self):
        self.stage3_run()
        selection_path = self.prof_dir / "套磁选择.json"
        email_pack_path = self.prof_dir / "邮件输入.json"
        sel_input = self.root / "sel_invalid_override.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1", "papers_override": ["AAAA1111", "AAAA1111"]}]
        }]}, ensure_ascii=False), encoding="utf-8")
        out = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                       "--selection-input", sel_input)))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "invalid_papers_override")
        self.assertFalse(selection_path.exists())
        self.assertFalse(email_pack_path.exists())

    def test_06d_duplicate_stage4_selection_is_rejected_before_write(self):
        self.stage3_run()
        selection_path = self.prof_dir / "套磁选择.json"
        email_pack_path = self.prof_dir / "邮件输入.json"
        sel = {"professor": "試験 教授", "professor_dir": str(self.prof_dir),
               "collection_key": "DIR00001", "ideas": [{"id": "DIR00001_1"}]}
        sel_input = self.root / "duplicate-selection.json"
        sel_input.write_text(json.dumps({"selections": [sel, dict(sel)]}, ensure_ascii=False), encoding="utf-8")
        out = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                       "--selection-input", sel_input)))
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
        out = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_reference_id")
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_06e2_truncated_gap_id_is_rejected_with_legal_ids_in_message(self):
        # Batch-3 runtime failure shape: the analyzer dropped one character
        # from a 64-hex gap id. The rejection must stay fail-closed AND name
        # the legal job gap ids so the model can repair its result file by
        # copying the right id verbatim.
        facts = self.write_facts()
        results = self.root / "truncated-freshness"
        self.write_stage2_results(results)
        legal_id = quote_id(self.gap_quotes["AAAA1111"])
        freshness_path = results / "freshness-DIR00001.json"
        freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
        row = next(row for row in freshness["results"] if row["gap_id"] == legal_id)
        row["gap_id"] = legal_id[:-1]  # 63 hex: one character lost
        freshness_path.write_text(json.dumps(freshness, ensure_ascii=False),
                                  encoding="utf-8")
        out = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_reference_id")
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())
        self.assertIn(legal_id, out.get("message") or "")

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
        self.assertEqual(stage4_row(parse(run_cli(
            "stage4-finalize", "--program-root", self.root,
            "--selection-input", first_input)))["status"], "ok")

        second_input = self.root / "select-second.json"
        second_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(self.prof_dir),
            "collection_key": "DIR00002", "ideas": [{"id": "DIR00002_1"}]
        }]}, ensure_ascii=False), encoding="utf-8")
        out4 = stage4_row(parse(run_cli(
            "stage4-finalize", "--program-root", self.root,
            "--selection-input", second_input)))
        self.assertEqual(out4["status"], "ok", out4)
        selection = json.loads((self.prof_dir / "套磁选择.json").read_text(encoding="utf-8"))
        self.assertEqual(selection["schema"], contact_state.STAGE4_LOCAL_SCHEMA)
        self.assertEqual({s["collection_key"] for s in selection["selections"]},
                         {"DIR00001", "DIR00002"})
        email_pack = json.loads((self.prof_dir / "邮件输入.json").read_text(encoding="utf-8"))
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
        out = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                       "--selection-input", sel_input)))
        self.assertEqual(out["status"], "ok")
        raw = (self.prof_dir / "邮件输入.json").read_text(encoding="utf-8")
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
        before = json.loads(state_path.read_text(encoding="utf-8"))
        validation_path = self.root / "stage3-validation.json"
        validation_path.write_text(json.dumps({"result": "ok", "files": [{
            "file": str(self.prof_dir / "套磁想法候选.md"), "artifact": "candidates",
            "verdict": "pass", "blocking": 0, "minor": 0, "issues": []}]},
            ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage3-record-validation", "--professor-dir", self.prof_dir,
                            "--validation-file", validation_path))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["raw_verdict"], "pass")
        self.assertEqual(out["scopes"], [{"scope": "direction:DIR00001", "result": "pass",
                                          "rounds": 1, "blocking": 0}])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["validator"]["results"]["DIR00001"]["result"], "pass")
        self.assertEqual(state["validator"]["render_sha256"], out["render_sha256"])
        # The record is bookkeeping next to the candidates, never a rewrite.
        self.assertEqual(state["directions"], before["directions"])
        self.assertEqual(state["cache"], before["cache"])
        old = state_path.read_bytes()
        validation_path.write_text(json.dumps({"results": [{
            "direction_id": "DIR00001", "result": "pass", "rounds": 1, "issues": []}]},
            ensure_ascii=False), encoding="utf-8")
        bad = parse(run_cli("stage3-record-validation", "--professor-dir", self.prof_dir,
                            "--validation-file", validation_path))
        self.assertEqual(bad["status"], "error")
        self.assertEqual(bad["reason_code"], "invalid_validation_json")
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
        out = parse(run_bound_stage2_finalize(run_cli, facts, "--results", results))
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


ISSUE59_PROFESSOR = "試験 教授"
ISSUE59_OTHER_PROFESSOR = "佐藤 花子"
ISSUE59_DIRECTION_ID = "DIR00001"
ISSUE59_IDEA_ID = "DIR00001_1"
ISSUE59_PEER_IDEA_ID = "DIR00001_2"
ISSUE59_EMAIL_ID = "試験 教授::DIR00001::DIR00001_1"
ISSUE59_PEER_EMAIL_ID = "試験 教授::DIR00001::DIR00001_2"
ISSUE59_OTHER_EMAIL_ID = "佐藤 花子::DIR00001::DIR00001_1"
ISSUE59_IDEAS = {ISSUE59_EMAIL_ID: ISSUE59_IDEA_ID,
                 ISSUE59_PEER_EMAIL_ID: ISSUE59_PEER_IDEA_ID,
                 ISSUE59_OTHER_EMAIL_ID: ISSUE59_IDEA_ID}
ISSUE59_GAP_QUOTE = ("Future work will extend the synthetic comparison "
                     "to a second input pattern.")
ISSUE59_PAPER_TITLE = "Synthetic comparison of input patterns"
ISSUE59_EMAIL_ADDRESS = "faculty@example.test"
ISSUE59_STALE_DAYS = 45
# One owner-shaped source-state reason, used only to make professor B
# demonstrably stale inside the program-level checker report.
ISSUE59_B_STALE_REASON = "source_changed:papers_json:Y分野/佐藤 花子/papers.json"
ISSUE59_MALFORMED_JSON = "{ this is not the email state"
def issue59_checker_stub(stale=None, marker=None):
    """Deterministic stand-in for professor-research's ``contact_evidence.py``.

    ``stale`` maps a professor to the owner-shaped reason their *live source
    state* is out of date; the report stays program-level, so its top-level
    ``result`` goes stale as soon as any professor does. ``marker`` is written
    only by the rebuild branch, which lets a case prove that an unrelated
    professor never pulled Stage 5 into a rebuild.
    """
    return (
        "import json, os, sys\n"
        f"STALE = {json.dumps(dict(stale or {}), ensure_ascii=False)}\n"
        f"MARKER = {json.dumps(str(marker or ''), ensure_ascii=False)}\n"
        "artifact = json.load(open(os.path.join(sys.argv[1], '教授研究', "
        f"{json.dumps(contact_state.CONTACT_EVIDENCE_FILE)}), encoding='utf-8'))\n"
        "if '--check' in sys.argv:\n"
        "    entries = [{'name': r['professor']['name'],\n"
        "                'result': 'stale' if STALE.get(r['professor']['name']) else 'fresh',\n"
        "                'reasons': [STALE[r['professor']['name']]]\n"
        "                if STALE.get(r['professor']['name']) else []}\n"
        "               for r in artifact['professors']]\n"
        "    reasons = sorted({x for e in entries for x in e['reasons']})\n"
        "    print(json.dumps({'result': 'stale' if reasons else 'fresh',\n"
        "                      'reasons': reasons, 'professors': entries},\n"
        "                     ensure_ascii=False))\n"
        "else:\n"
        "    if MARKER:\n"
        "        open(MARKER, 'w', encoding='utf-8').write('rebuilt\\n')\n"
        "    print(json.dumps({'result': 'ok'}))\n")


def issue59_verified_at(days_ago: int = 1) -> str:
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


# Computed once per process so repeated fixture calls stay byte-identical while
# remaining inside the runner's 30-day verify-cache window.
ISSUE59_VERIFIED_AT = issue59_verified_at()


def issue59_email_row(professor, professor_dir, *, idea_id=ISSUE59_IDEA_ID,
                      direction_id=ISSUE59_DIRECTION_ID,
                      name="合成输入比较", contact_evidence=None):
    """Build one legal Stage-4 email row through the producer compiler.

    The Issue-59 fixture owns only fixed synthetic Stage-4 source values. All
    derived handoff fields (identity, paper/gap projection, allowed sources,
    fingerprints carried into the row, and source_hash) come from
    compile_email_entry, so this fixture cannot drift into a shadow Stage-4
    producer.
    """
    professor_dir = Path(professor_dir)
    gap_id = quote_id(ISSUE59_GAP_QUOTE)
    input_fingerprint = contact_state.sha256_obj({
        "fixture": "issue59-stage4-input",
        "professor": professor,
        "direction_id": direction_id,
    })
    gap = {
        "gap_id": gap_id, "item_key": "AAAA1111",
        "paper_title": ISSUE59_PAPER_TITLE, "paper_year": 2023,
        "quote": ISSUE59_GAP_QUOTE,
        "translation_zh": f"中译：{ISSUE59_GAP_QUOTE[:24]}",
        "source": "Conclusion", "page": 8, "status": "open",
        "confidence": "high", "completed_part": None, "remaining_gap": None,
        "evidence": "无更晚论文实现该点（AAAA1111）",
    }
    credibility = {
        "verdict": "站得住", "mainline": "主线",
        "authorship_line": "corresponding_dominant", "note": "test",
    }
    pack_direction = {
        "direction_id": direction_id,
        "collection_key": direction_id,
        "name_ja": name,
        "name_zh": name,
        "user_note": "我想比较两种合成输入的处理结果。",
        "input_fingerprint": input_fingerprint,
        "supporting_item_keys": ["AAAA1111"],
        "named_keys": [],
        "resolved_addition_keys": [],
        "gap_shortlist": [gap],
        "gaps_excluded": [],
        "completed_gap_blacklist": [],
        "red_lines": [{
            "scope": "global", "text": "不得引用未提供来源的数字",
            "banned_phrases": ["99.9%"],
        }],
        "credibility": credibility,
        "narrative": {
            "positioning": [{
                "text": (f"教授从 {{P:AAAA1111}} 起研究合成输入比较；"
                         f"{{G:{gap_id}}} 是延伸点。"),
            }],
        },
    }
    pack = {
        "professor": professor,
        "professor_dir": str(professor_dir),
        "papers": {
            "AAAA1111": {
                "item_key": "AAAA1111",
                "title": ISSUE59_PAPER_TITLE,
                "year": 2023,
                "authorship": "corresponding",
            },
        },
        "directions": [pack_direction],
    }
    idea = {
        "id": idea_id,
        "title": "第二种输入模式的合成比较",
        "idea_zh": "",
        "direction_ids": [direction_id],
        "papers": [{
            "item_key": "AAAA1111",
            "direction_ids": [direction_id],
            "fit_note": "教授通讯",
        }],
        "gap_refs": [{
            "direction_id": direction_id,
            "item_key": "AAAA1111",
            "gap_id": gap_id,
        }],
        "red_lines": [],
        "banned_phrases": [],
        "_profile_fields": {},
    }
    # compile_email_entry currently does not consume program_root, but pass the
    # semantic root so the fixture remains correct if that helper begins using
    # it later.
    program_root = professor_dir.parents[2]
    return contact_state.compile_email_entry(
        pack, {}, pack_direction, idea, "", program_root, None,
        contact_evidence=contact_evidence)


def issue59_result(gap_id, email_id=ISSUE59_EMAIL_ID, idea_id=ISSUE59_IDEA_ID):
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
                {"output": "③", "source_ids": [f"gap:{gap_id}"]},
                {"output": "④", "source_ids": ["template"]},
                {"output": "future", "source_ids": [f"idea:{idea_id}"]}]}


def issue59_choices(email_id=ISSUE59_EMAIL_ID):
    return {"email_id": email_id, "first_choice": False,
            "signature_name": "試験 太郎", "learning": "比較手法の基礎知識の習得"}


def issue59_evidence_record(professor, item_key, *,
                            email=ISSUE59_EMAIL_ADDRESS):
    """One professor record exactly representable by the owner reconciler.

    Keep the pre-existing Issue-59 baseline on ``confirmed_cross_source``:
    the fixture now earns that verdict from a real official candidate plus one
    recent high-confidence correspondence record, instead of hand-authoring a
    schema-2 artifact that the owner checker would reject.
    """
    return {
        "professor": {"name": professor, "name_romaji": None},
        "official_emails": [{
            "email": email, "current_source": True,
            "provenance": [{"source_type": "official_professor_candidate",
                            "source": "issue59-fixture"}]}],
        "paper_correspondence": [{
            "email": email, "name": professor, "item_key": item_key, "doi": None,
            "paper_year": 2025, "channel": "correspondence", "confidence": "high",
            "identity_match": "direct", "recent": True,
            "current_email_evidence": False}],
        "identity": {"matched_verified_contacts": 1,
                     "unmatched_verified_contacts": [],
                     "ambiguous_unpaired_records_ignored": 0},
        "verdict": "confirmed_cross_source",
        "confirmed_emails": [email],
        "conflicting_paper_emails": [],
        "current_email": email,
        "evidence_status": {
            "official_candidates_unavailable": False,
            "professor_papers_unavailable": False,
            "paper_correspondence_unavailable": False,
            "signature_aliases_unavailable": False,
            "current_email_blocked_by": []},
    }


def issue59_projection_hash(value):
    """Hash the minimal owner projection used by this fixture.

    The source JSON below contains only fields consumed by
    professor-research/contact_evidence.py, so its owner projection is the
    value itself.  Canonical separators + sorted keys match the documented
    schema-2 fingerprint contract without copying the owner reconciler.
    """
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def issue59_source_fingerprint(source, path, professors_root, projection=None):
    path = Path(path)
    rel = path.relative_to(professors_root).as_posix()
    if projection is None:
        return {"source": source, "path": rel, "present": False,
                "sha256": None, "bytes": None}
    return {"source": source, "path": rel, "present": True,
            "sha256": issue59_projection_hash(projection),
            "bytes": len(path.read_bytes())}


def issue59_write_evidence(program_root, professor_dirs, stale_for=()):
    """Write an owner-contract-valid evidence handoff plus frozen snapshots.

    Unlike the source-state checker stub, this artifact is not synthetic
    readiness evidence: it follows professor-research's schema-2 handoff,
    including the persisted sources and non-empty fingerprint index that the
    real ``contact_evidence.py --check`` requires.  The stub is therefore
    limited to supplying the case-specific fresh/stale source-state report.
    """
    program_root = Path(program_root)
    professors_root = program_root / "教授研究"
    professor_dirs = {name: Path(path) for name, path in professor_dirs.items()}
    professors = list(professor_dirs)

    candidates = [
        {"name": name, "email": ISSUE59_EMAIL_ADDRESS, "source": "issue59-fixture"}
        for name in professors
    ]
    candidates_path = professors_root / "_professor_candidates.json"
    candidates_path.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=1), encoding="utf-8")

    paper_projections = []
    evidence_item_keys = {}
    correspondence = {}
    for index, (name, professor_dir) in enumerate(professor_dirs.items()):
        professor_dir.mkdir(parents=True, exist_ok=True)
        item_key = "AAAA1111" if index == 0 else f"ISS59{index:03d}"
        evidence_item_keys[name] = item_key
        papers = {
            "professor": {"name": name},
            "papers": [{"item_key": item_key, "year": 2025}],
        }
        papers_path = professor_dir / "papers.json"
        papers_path.write_text(
            json.dumps(papers, ensure_ascii=False, indent=1), encoding="utf-8")
        paper_projections.append((papers_path, papers))
        correspondence[item_key] = {
            "paper_year": 2025,
            "channel": "correspondence",
            "confidence": "high",
            "contacts": [{
                "name": name, "email": ISSUE59_EMAIL_ADDRESS,
                "channel": "correspondence", "confidence": "high",
            }],
        }

    correspondence_path = professors_root / "_corresp_cache.json"
    correspondence_path.write_text(
        json.dumps(correspondence, ensure_ascii=False, indent=1), encoding="utf-8")
    signature_path = professors_root / "_署名对照.json"
    fingerprints = [
        issue59_source_fingerprint(
            "professor_candidates", candidates_path, professors_root, candidates),
        issue59_source_fingerprint(
            "paper_correspondence", correspondence_path, professors_root,
            correspondence),
        issue59_source_fingerprint(
            "signature_book", signature_path, professors_root),
    ]
    fingerprints.extend(
        issue59_source_fingerprint(
            "papers_json", papers_path, professors_root, projection)
        for papers_path, projection in paper_projections)

    artifact = {
        "schema": 2, "kind": contact_state.CONTACT_EVIDENCE_KIND,
        "generated_at": contact_state.now_utc(),
        "recent_paper_years": 5, "current_year": int(contact_state.now_utc()[:4]),
        "scope": "workflow_evidence_not_send_time_authority",
        "sources": {
            "professor_candidates": "_professor_candidates.json",
            "paper_correspondence": "_corresp_cache.json",
            "signature_book": "_署名对照.json",
        },
        "degraded": False, "global_degraded": False, "source_errors": [],
        "source_fingerprints": {"algorithm": "sha256", "files": fingerprints},
        "professors": [
            issue59_evidence_record(name, evidence_item_keys[name])
            for name in professors
        ],
    }
    path = professors_root / contact_state.CONTACT_EVIDENCE_FILE
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=1), encoding="utf-8")
    snapshots = {}
    for name in professors:
        frozen = artifact
        if name in stale_for:
            frozen = json.loads(json.dumps(artifact, ensure_ascii=False))
            for record in frozen["professors"]:
                if record["professor"]["name"] == name:
                    record["official_emails"][0]["email"] = "moved@example.test"
                    record["current_email"] = "moved@example.test"
        snapshots[name] = contact_state.contact_evidence_snapshot(frozen, None, name)
    return snapshots


def install_issue59_checker(case, program_root, stale=None):
    """Certify fixture professors as source-state fresh, except ``stale``.

    The stub stands in for professor-research's ``contact_evidence.py`` and
    must live outside the program root, which holds user data only; the
    injected locator variable is restored when the case ends.
    """
    saved = os.environ.get(contact_state.UPSTREAM_SCRIPT_ENV)

    def restore():
        if saved is None:
            os.environ.pop(contact_state.UPSTREAM_SCRIPT_ENV, None)
        else:
            os.environ[contact_state.UPSTREAM_SCRIPT_ENV] = saved

    case.addCleanup(restore)
    holder = tempfile.TemporaryDirectory(prefix="issue59-checker-")
    case.addCleanup(holder.cleanup)
    script = Path(holder.name) / "skills" / "professor-collector" / "scripts"
    script = script / "contact_evidence.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    marker = Path(holder.name) / "rebuild-marker.txt"
    script.write_text(issue59_checker_stub(stale, marker), encoding="utf-8")
    os.environ[contact_state.UPSTREAM_SCRIPT_ENV] = str(script)
    return marker


def write_issue59_verify(program_root, professor_dir, professor, *, days_ago=1,
                         email_value=ISSUE59_EMAIL_ADDRESS):
    info = Path(program_root) / "info.json"
    boshu = Path(program_root) / "boshu_analysis.json"
    verify = {
        "professor": professor,
        "verified_at": (ISSUE59_VERIFIED_AT if days_ago == 1
                        else issue59_verified_at(days_ago)),
        "source_fingerprints": {
            "info_json": f"{info}:{int(info.stat().st_mtime)}",
            "boshu_analysis": f"{boshu}:{int(boshu.stat().st_mtime)}"},
        "items": {
            "email": {"verdict": "confirmed", "value": email_value, "sources": []},
            "roster": {"verdict": "confirmed", "value": "X分野/教授 @P.1", "sources": []},
            "season": {"verdict": "confirmed", "value": "春季 少数名", "sources": []},
            "header": {"verdict": "confirmed", "value": "", "sources": []},
            "subject_batch": {"verdict": "confirmed", "value": "", "sources": []},
            "schedule": {"verdict": "unverified", "value": None, "sources": []},
            "consent": {"verdict": "unverified", "value": None, "sources": []},
            "warnings": []}}
    path = Path(professor_dir) / "_contact_verify.json"
    path.write_text(json.dumps(verify, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def write_issue59_overview(program_root):
    """Seed the program aggregate with fixed bytes a targeted run must keep."""
    path = Path(program_root) / "教授研究" / contact_state.EMAIL_OVERVIEW
    path.write_text("# 套磁邮件总览\n\n> issue59 预置聚合表：定向运行不得改写\n",
                    encoding="utf-8")
    return path


def write_issue59_stale_overview(program_root):
    """A managed aggregate whose body no longer matches its recorded render sha.

    Batch Stage 5 must surface that as ``needs_decision`` before writing
    anything; a targeted run must never open the aggregate at all.
    """
    body = ("# 套磁邮件总览\n\n> 2026-01-01T00:00:00Z ｜ 由 contact_state 渲染\n\n"
            "| 教授 | 方向（ja/zh） | 收件邮箱 | 核验 | 首封邮件 | 跟进邮件 | "
            "首封纯文本 | 跟进纯文本 |\n|---|---|---|---|---|---|---|---|\n")
    sha = contact_state.sha256_text(body)
    key = contact_state.EMAIL_OVERVIEW
    path = Path(program_root) / "教授研究" / key
    path.write_text(contact_state.render_frontmatter(
        contact_state.sha256_obj({"projection": key, "body": sha}), sha) + body,
        encoding="utf-8")
    (Path(program_root) / "教授研究" / contact_state.PROJECTIONS_FILE).write_text(
        json.dumps({"render": {key: {"sha256": "0" * 64}}}), encoding="utf-8")
    return path


def write_issue59_stage5_fixture(program_root, specs=(), *, extra_rows=(),
                                 overview=None, case=None):
    """Materialize the Stage 4 → Stage 5 handoff directly under ``program_root``.

    No Stage 2/3/4 runner is involved: every ``邮件输入.json`` row, every
    per-professor ``_contact_verify.json`` / ``套磁邮件状态.json`` and the
    program aggregate come from this writer, so one valid target can sit
    beside any amount of unrelated or invalid state.

    Each spec is a dict of ``professor`` / ``direction_id`` / ``idea_id`` /
    ``field`` / ``dir`` / ``verified``
    (``fresh`` | ``stale`` | ``missing`` | ``malformed``) /
    ``evidence`` (``none`` | ``fresh`` | ``stale``) / ``source_state``
    (``stale`` asks the injected checker to report that professor stale) /
    ``email_state``. ``overview`` seeds the program aggregate with ``"seed"``
    bytes or a conflicting managed render with ``"conflict"``.
    """
    program_root = Path(program_root)
    research = program_root / "教授研究"
    research.mkdir(parents=True, exist_ok=True)
    (program_root / "info.json").write_text(json.dumps({
        "university": "試験大学", "department": "試験研究科",
        "target": {"intake_year": 2027, "intake_term": "april"}}), encoding="utf-8")
    (program_root / "boshu_analysis.json").write_text(json.dumps({
        "exam_type": {"degree": "博士前期課程",
                      "selection_name": "春季 テスト選抜 合成工学専攻"}},
        ensure_ascii=False), encoding="utf-8")

    normalized = []
    for spec in (list(specs) or [{}]):
        spec = dict(spec)
        spec.setdefault("professor", ISSUE59_PROFESSOR)
        spec.setdefault("idea_id", ISSUE59_IDEA_ID)
        spec.setdefault("field", "X分野" if spec["professor"] == ISSUE59_PROFESSOR
                        else "Y分野")
        spec.setdefault("verified", "fresh")
        spec.setdefault("evidence", "fresh")
        spec.setdefault("dir", research / spec["field"] / spec["professor"])
        normalized.append(spec)

    wanted = list(dict.fromkeys(
        spec["professor"] for spec in normalized if spec["evidence"] != "none"))
    snapshots = {}
    checker_marker = None
    if wanted:
        if case is None:
            raise AssertionError(
                "issue59 fixture: an evidence snapshot needs a unittest case so "
                "PROFESSOR_CONTACT_EVIDENCE_SCRIPT is restored")
        checker_marker = install_issue59_checker(case, program_root, stale={
            spec["professor"]: ISSUE59_B_STALE_REASON for spec in normalized
            if spec.get("source_state") == "stale"})
        professor_dirs = {}
        for spec in normalized:
            if spec["evidence"] != "none":
                professor_dirs.setdefault(spec["professor"], Path(spec["dir"]))
        snapshots = issue59_write_evidence(
            program_root, professor_dirs,
            stale_for=[s["professor"] for s in normalized if s["evidence"] == "stale"])

    rows, dirs, verified_dirs = [], {}, {}
    for spec in normalized:
        professor_dir = Path(spec["dir"])
        row = issue59_email_row(
            spec["professor"], professor_dir,
            idea_id=spec["idea_id"],
            direction_id=spec.get("direction_id", ISSUE59_DIRECTION_ID),
            contact_evidence=snapshots.get(spec["professor"]))
        rows.append(row)
        dirs[spec["professor"]] = professor_dir
        professor_dir.mkdir(parents=True, exist_ok=True)
        if spec.get("email_state") is not None:
            payload = spec["email_state"]
            (professor_dir / contact_state.EMAIL_STATE).write_text(
                payload if isinstance(payload, str)
                else json.dumps(payload, ensure_ascii=False, indent=1),
                encoding="utf-8")
        if spec["verified"] == "missing":
            continue
        if spec["verified"] == "malformed":
            verified_dirs[spec["professor"]] = (
                professor_dir / contact_state.VERIFY_FILE)
            verified_dirs[spec["professor"]].write_text(
                ISSUE59_MALFORMED_JSON, encoding="utf-8")
            continue
        verified_dirs[spec["professor"]] = write_issue59_verify(
            program_root, professor_dir, spec["professor"],
            days_ago=1 if spec["verified"] == "fresh" else ISSUE59_STALE_DAYS)

    pack_path = research / contact_state.EMAIL_PACK
    pack_path.write_text(json.dumps({
        "schema": contact_state.EMAIL_PACK_SCHEMA,
        "kind": contact_state.EMAIL_PACK_KIND,
        "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
        "managed_by": contact_state.MANAGED_BY,
        "generated_at": contact_state.now_utc(),
        "program_root": str(program_root),
        "profile_fingerprint": None,
        "emails": rows + list(extra_rows)}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    if overview == "conflict":
        write_issue59_stale_overview(program_root)
    elif overview == "seed":
        write_issue59_overview(program_root)
    return {"program_root": program_root, "pack": pack_path, "rows": rows,
            "dirs": dirs, "verify": verified_dirs,
            "overview": (research / contact_state.EMAIL_OVERVIEW
                         if overview else None),
            "checker_marker": checker_marker,
            "email_ids": [row["email_id"] for row in rows],
            "gap_id": quote_id(ISSUE59_GAP_QUOTE)}


class TestStage5(BaseEnv):
    def test_stage5_requires_user_template(self):
        self.prepare()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "stage5-plan", "--program-root", str(self.root),
             "--email-pack", str(self.email_pack),
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
        out = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                       "--selection-input", sel_input)))
        self.assertEqual(out["status"], "ok", out)
        self.email_pack = Path(out["email_pack"])
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
            "professor": "試験 教授", "verified_at": ISSUE59_VERIFIED_AT,
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
        return issue59_result(g1)

    def choices(self):
        return issue59_choices()

    def final_surfaces(self, mode):
        """Every email file the caller can observe after a committed write."""
        prefixes = ["套磁邮件"] + (["套磁跟进邮件"] if mode == "both" else [])
        return [self.prof_dir / f"{prefix}.{ext}"
                for prefix in prefixes for ext in ("md", "txt")]

    def commit_both(self, raw_path, choices_path, draft):
        """Commit plan drafts through the public finalize path and return every
        final rendered surface."""
        email_id = self.choices()["email_id"]
        keys = {"initial": email_id, "followup": f"{email_id}::followup"}
        mapping = {}
        for row in draft["drafts"]:
            text_path = self.root / f"final-{row['kind']}.txt"
            text_path.write_text(row["draft"], encoding="utf-8")
            mapping[keys[row["kind"]]] = str(text_path)
        map_path = self.root / "final-map.json"
        map_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage5-finalize", "--program-root", self.root, "--mode", "both",
                            "--result", raw_path, "--humanized-map", map_path,
                            "--choices", choices_path))
        self.assertEqual(out["status"], "ok", out)
        return "\n".join(path.read_text(encoding="utf-8")
                         for path in self.final_surfaces("both"))

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
        fixture = write_issue59_stage5_fixture(self.root, [
            {"professor": ISSUE59_PROFESSOR},
            {"professor": ISSUE59_PROFESSOR, "idea_id": ISSUE59_PEER_IDEA_ID}],
            case=self)
        g1 = fixture["gap_id"]
        second_id = ISSUE59_PEER_EMAIL_ID

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
        overview_path = self.root / "教授研究" / contact_state.EMAIL_OVERVIEW
        self.assertEqual(out["overview_md"], str(overview_path), out)
        md_paths = {Path(row["md"]) for row in out["emails"]}
        txt_paths = {Path(row["txt"]) for row in out["emails"]}
        self.assertEqual(len(md_paths), 2)
        self.assertEqual(len(txt_paths), 2)
        self.assertTrue(all(path.is_file() for path in md_paths | txt_paths))
        self.assertNotIn(self.prof_dir / "套磁邮件.md", md_paths)
        self.assertNotIn(self.prof_dir / "套磁邮件.txt", txt_paths)

        # Issue #59 T59-5: A and A2 share one 套磁邮件状态.json, so a targeted
        # A2 run must leave the already rendered A bytes and A's state entry
        # alone instead of rewriting the professor's whole state file.
        first_id = self.choices()["email_id"]
        a_files = {Path(row[key]): Path(row[key]).read_bytes()
                   for row in out["emails"] if row["email_id"] == first_id
                   for key in ("md", "txt")}
        shared_state = self.prof_dir / "套磁邮件状态.json"
        a_state = copy.deepcopy(json.loads(
            shared_state.read_text(encoding="utf-8"))["emails"][first_id])

        one = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", raw_path, "--humanized-map", humanized_map,
                            "--choices", choices_path, "--email-id", second_id))
        self.assertEqual(one["status"], "ok", one)
        self.assertEqual(Path(one["emails"][0]["md"]),
                         next(path for path in md_paths if "DIR00001_2" in path.name))
        self.assertEqual({path: path.read_bytes() for path in a_files}, a_files)
        persisted = json.loads(shared_state.read_text(encoding="utf-8"))
        self.assertEqual(persisted["emails"][first_id], a_state)
        self.assertIn(second_id, persisted["emails"])

        overview = overview_path.read_text(encoding="utf-8")
        self.assertEqual(overview.count("[.md]("), 2)
        state = json.loads((self.prof_dir / "套磁邮件状态.json").read_text(encoding="utf-8"))
        self.assertEqual({entry["files"]["md"] for entry in state["emails"].values()},
                         {str(path) for path in md_paths})


    def test_stage5_batch_failure_does_not_write_first_email(self):
        g1 = write_issue59_stage5_fixture(self.root, case=self)["gap_id"]
        raw1 = self.raw_result(g1)
        raw_one_path = self.root / "first-raw.json"
        raw_one_path.write_text(json.dumps(raw1, ensure_ascii=False), encoding="utf-8")
        choices_one_path = self.root / "first-choices.json"
        choices_one_path.write_text(json.dumps(self.choices(), ensure_ascii=False), encoding="utf-8")
        draft = parse(run_cli("stage5-plan", "--program-root", self.root,
                              "--result", raw_one_path, "--choices", choices_one_path))
        self.assertEqual(draft["status"], "ok", draft)
        raw2 = json.loads(json.dumps(raw1, ensure_ascii=False))
        second_id = ISSUE59_PEER_EMAIL_ID
        write_issue59_stage5_fixture(self.root, [
            {"professor": ISSUE59_PROFESSOR},
            {"professor": ISSUE59_PROFESSOR, "idea_id": ISSUE59_PEER_IDEA_ID}],
            case=self)
        raw2["email_id"] = second_id
        raw2["source_map"][-1]["source_ids"] = [f"idea:{ISSUE59_PEER_IDEA_ID}"]
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
        self.assertEqual(list(self.prof_dir.glob("套磁邮件*.md")), [])
        self.assertEqual(list(self.prof_dir.glob("套磁邮件*.txt")), [])
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

    def test_stage5_first_allows_missing_initial_sent_date(self):
        g1 = self.prepare()
        raw_path = self.root / "first-without-date-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "first-without-date-choices.json"
        choices = dict(self.choices())
        choices.pop("initial_sent_date", None)
        choices_path.write_text(json.dumps(choices, ensure_ascii=False), encoding="utf-8")

        out = parse(run_cli("stage5-plan", "--program-root", self.root, "--mode", "first",
                            "--result", raw_path, "--choices", choices_path))
        self.assertEqual(out["status"], "ok", out)

    def test_stage5_rejects_non_boolean_first_choice(self):
        g1 = self.prepare()
        raw_path = self.root / "non-boolean-choice-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "non-boolean-choice.json"
        choices = dict(self.choices(), first_choice="false")
        choices_path.write_text(json.dumps(choices, ensure_ascii=False), encoding="utf-8")

        out = parse(run_cli("stage5-plan", "--program-root", self.root,
                            "--result", raw_path, "--choices", choices_path))

        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "missing_user_choice")
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())

    def test_stage5_rejects_blank_signature_and_learning(self):
        g1 = self.prepare()
        raw_path = self.root / "blank-choice-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "blank-choice.json"

        for field in ("signature_name", "learning"):
            choices = dict(self.choices(), **{field: "   "})
            choices_path.write_text(json.dumps(choices, ensure_ascii=False), encoding="utf-8")
            out = parse(run_cli("stage5-plan", "--program-root", self.root,
                                "--result", raw_path, "--choices", choices_path))
            self.assertEqual(out["status"], "error", field)
            self.assertEqual(out["reason_code"], "missing_user_choice", field)

    def test_stage5_followup_requires_non_placeholder_initial_sent_date(self):
        g1 = self.prepare()
        raw_path = self.root / "followup-choice-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "followup-choice.json"

        for label, sent_date in (
                ("missing", None),
                ("blank", "   "),
                ("placeholder", "{{初回送信日}}")):
            with self.subTest(case=label):
                choices = dict(self.choices())
                if sent_date is None:
                    choices.pop("initial_sent_date", None)
                else:
                    choices["initial_sent_date"] = sent_date
                choices_path.write_text(json.dumps(choices, ensure_ascii=False), encoding="utf-8")
                out = parse(run_cli("stage5-plan", "--program-root", self.root, "--mode", "both",
                                    "--result", raw_path, "--choices", choices_path))
                self.assertEqual(out["status"], "error", label)
                self.assertEqual(out["reason_code"], "missing_user_choice", label)

    def test_stage5_choices_id_mapping_fails_closed(self):
        g1 = write_issue59_stage5_fixture(self.root, case=self)["gap_id"]
        raw_path = self.root / "id-mapping-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "id-mapping-choice.json"

        valid = self.choices()
        invalid_cases = (
            ("missing-email-id",
             {key: value for key, value in valid.items() if key != "email_id"}),
            ("unknown-email-id", dict(valid, email_id="unknown-email-id")),
            ("duplicate-email-id", [valid, dict(valid)]),
            ("selected-id-set-mismatch", []),
        )
        for label, invalid_choices in invalid_cases:
            with self.subTest(case=label):
                choices_path.write_text(
                    json.dumps(invalid_choices, ensure_ascii=False), encoding="utf-8")
                out = parse(run_cli("stage5-plan", "--program-root", self.root,
                                    "--result", raw_path, "--choices", choices_path))
                self.assertEqual(out["status"], "error", label)
                self.assertEqual(out["reason_code"], "invalid_result_json", label)

    def test_stage5_choices_cannot_replace_the_verified_recipient(self):
        # Issue #43 freezes one interaction at this caller boundary:
        # choices.email_address may confirm the Step 2.5 verdict but can never
        # become a second recipient authority. The rest of the evidence ladder
        # stays owned by the contact-evidence tests, so only the three rows
        # observable from here are checked, through the public plan path.
        g1 = self.prepare()
        verified = "faculty@example.test"
        raw_path = self.root / "recipient-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choices_path = self.root / "recipient-choices.json"
        verify_path = self.prof_dir / "_contact_verify.json"

        for label, cached, supplied, accepted in (
                ("different-address", verified, "other@example.test", False),
                ("no-verified-address", None, verified, False),
                ("same-address", verified, verified, True)):
            with self.subTest(label=label):
                cache = json.loads(verify_path.read_text(encoding="utf-8"))
                cache["items"]["email"] = {
                    "verdict": "confirmed" if cached else "unverified",
                    "value": cached,
                    "sources": []}
                verify_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                for surface in self.final_surfaces("both"):
                    surface.unlink(missing_ok=True)
                choices_path.write_text(json.dumps(
                    dict(self.choices(), initial_sent_date="2026年9月1日",
                         email_address=supplied), ensure_ascii=False), encoding="utf-8")
                draft = parse(run_cli("stage5-plan", "--program-root", self.root, "--mode", "both",
                                      "--result", raw_path, "--choices", choices_path))
                if not accepted:
                    self.assertNotEqual(draft["status"], "ok", label)
                    for surface in self.final_surfaces("both"):
                        self.assertFalse(surface.exists(), label)
                    continue
                self.assertEqual(draft["status"], "ok", draft)
                self.assertIn(verified, self.commit_both(raw_path, choices_path, draft))

    def test_stage5_gate_stops_before_the_choices_file_is_read(self):
        g1 = self.prepare()
        # The cache fingerprint goes stale after info.json is rewritten.
        info = self.root / "info.json"
        touched = int(info.stat().st_mtime) + 3600
        os.utime(info, (touched, touched))
        raw_path = self.root / "gated-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        # A missing file is the strongest observable proof of the ordering:
        # if the runner touches choices before the verification gate, this path
        # cannot return the verification reason below.
        choices_path = self.root / "missing-gated-choices.json"
        self.assertFalse(choices_path.exists())

        out = parse(run_cli("stage5-plan", "--program-root", self.root,
                            "--result", raw_path, "--choices", choices_path))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertFalse((self.prof_dir / "套磁邮件.md").exists())

    def test_stage5_finalize_gate_stops_before_the_choices_file_is_read(self):
        # Issue #43 freezes verification-before-choices for the Stage-5 runner,
        # not only for the planning command.  A missing choices file makes the
        # ordering observable without depending on an exact verify reason code.
        g1 = self.prepare()
        info = self.root / "info.json"
        touched = int(info.stat().st_mtime) + 3600
        os.utime(info, (touched, touched))
        raw_path = self.root / "finalize-gated-raw.json"
        raw_path.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        humanized_path = self.root / "finalize-gated-humanized.txt"
        humanized_path.write_text("unused because verification must stop first", encoding="utf-8")
        choices_path = self.root / "missing-finalize-gated-choices.json"
        self.assertFalse(choices_path.exists())

        out = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", raw_path, "--humanized", humanized_path,
                            "--choices", choices_path))
        self.assertEqual(out["status"], "needs_refresh", out)
        for surface in self.final_surfaces("first"):
            self.assertFalse(surface.exists())
        self.assertFalse((self.prof_dir / "套磁邮件状态.json").exists())

        # Batch boundary subcase: the gate is whole-batch, not per email —
        # after professor A passes, a later sibling professor B with no verify
        # cache must still stop the run before the choices file is read.  The
        # professor attribution proves the runner really got past A, so the
        # stop cannot come from leftover state on A.
        g1 = self.prepare()
        pack_path = self.email_pack
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        b_dir = self.prof_dir.parent / "第二 教授"
        b_dir.mkdir(parents=True, exist_ok=True)
        self.assertFalse((b_dir / "_contact_verify.json").exists())
        b_email_id = "第二 教授::DIR00001::DIR00001_1"
        b_row = copy.deepcopy(pack["emails"][0])
        b_row["professor"] = "第二 教授"
        b_row["professor_dir"] = str(b_dir)
        b_row["email_id"] = b_email_id
        pack["emails"].append(b_row)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        a_raw = self.raw_result(g1)
        b_raw = copy.deepcopy(a_raw)
        b_raw["email_id"] = b_email_id
        batch_raw_path = self.root / "finalize-gated-batch-raw.json"
        batch_raw_path.write_text(json.dumps([a_raw, b_raw], ensure_ascii=False), encoding="utf-8")
        a_humanized = self.root / "finalize-gated-batch-a.txt"
        b_humanized = self.root / "finalize-gated-batch-b.txt"
        a_humanized.write_text("unused because verification must stop first", encoding="utf-8")
        b_humanized.write_text("unused because verification must stop first", encoding="utf-8")
        batch_map_path = self.root / "finalize-gated-batch-map.json"
        batch_map_path.write_text(json.dumps({
            a_raw["email_id"]: str(a_humanized),
            b_email_id: str(b_humanized)}, ensure_ascii=False), encoding="utf-8")
        batch_choices_path = self.root / "missing-finalize-gated-batch-choices.json"
        self.assertFalse(batch_choices_path.exists())

        out = parse(run_cli("stage5-finalize", "--program-root", self.root,
                            "--result", batch_raw_path, "--humanized-map", batch_map_path,
                            "--choices", batch_choices_path))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out.get("professor"), "第二 教授", out)
        for surface in self.final_surfaces("first"):
            self.assertFalse(surface.exists())
        for ext in ("md", "txt"):
            self.assertFalse((b_dir / f"套磁邮件.{ext}").exists())
        self.assertFalse((self.prof_dir / "套磁邮件状态.json").exists())
        self.assertFalse((b_dir / "套磁邮件状态.json").exists())

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
        out4 = stage4_row(parse(run_cli("stage4-finalize", "--program-root", self.root,
                                        "--selection-input", sel_input)))
        self.assertEqual(out4["status"], "ok", out4)
        email_pack = json.loads(
            (self.prof_dir / "邮件输入.json").read_text(encoding="utf-8"))
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


ISSUE59_DEPENDENCY_VARIANTS = ("state", "verify", "clean", "overview-conflict")


def issue59_write_json(program_root, name, payload):
    path = Path(program_root) / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def issue59_write_results(program_root, name, email_ids, extra_rows=()):
    gap_id = quote_id(ISSUE59_GAP_QUOTE)
    rows = [issue59_result(gap_id, email_id=email_id,
                           idea_id=ISSUE59_IDEAS[email_id]) for email_id in email_ids]
    return issue59_write_json(program_root, name, rows + list(extra_rows))


def issue59_write_choices(program_root, name, email_ids, extra_rows=()):
    return issue59_write_json(
        program_root, name,
        [issue59_choices(email_id) for email_id in email_ids] + list(extra_rows))


def issue59_dependency_variant(program_root, variant, case):
    """Build T59-4 dependency shapes from scratch.

    ``state`` corrupts only B's 套磁邮件状态.json; ``verify`` corrupts only B's
    _contact_verify.json while its state still lists B's rendered files (the
    shape the pre-fix aggregate path read first); ``clean`` leaves both valid
    and seeds no program aggregate; ``overview-conflict`` leaves B valid and
    seeds only a managed aggregate projection conflict. Each variant is built
    in its own program root so every subcase changes one acceptance dimension.
    """
    program_root = Path(program_root)
    b_dir = program_root / "教授研究" / "Y分野" / ISSUE59_OTHER_PROFESSOR
    b_state = {"schema": 1, "kind": "email_state", "professor": ISSUE59_OTHER_PROFESSOR,
               "emails": {ISSUE59_OTHER_EMAIL_ID: {
                   "files": {"md": str(b_dir / "套磁邮件.md"),
                             "txt": str(b_dir / "套磁邮件.txt")},
                   "validation": {"result": "pass", "rounds": 1}}}}
    fixture = write_issue59_stage5_fixture(program_root, [
        {"professor": ISSUE59_PROFESSOR, "evidence": "fresh"},
        {"professor": ISSUE59_OTHER_PROFESSOR, "evidence": "fresh",
         "email_state": ISSUE59_MALFORMED_JSON if variant == "state" else b_state,
         "verified": "malformed" if variant == "verify" else "fresh"}],
        overview=("conflict" if variant == "overview-conflict"
                  else None if variant == "clean" else "seed"), case=case)
    if variant != "state":
        for name in ("套磁邮件.md", "套磁邮件.txt"):
            (b_dir / name).write_text("ISSUE59-B-RENDERED\n", encoding="utf-8")
    return {"fixture": fixture,
            "results": issue59_write_results(
                program_root, "issue59-dependency-raw.json", [ISSUE59_EMAIL_ID]),
            "choices": issue59_write_choices(
                program_root, "issue59-dependency-choices.json", [ISSUE59_EMAIL_ID]),
            "b_dir": b_dir,
            "b_state": b_dir / contact_state.EMAIL_STATE,
            "b_verify": b_dir / contact_state.VERIFY_FILE,
            "overview": fixture["overview"]}


class TestStage5TargetedEmailScope(BaseEnv):
    """Issue #59: ``--email-id`` is a hard single-email execution scope.

    Every case runs the public Stage-5 CLI against a program root whose
    ``邮件输入.json`` mixes the one valid target with unrelated rows that are
    malformed, escaped, stale or simply unusable. A targeted run must resolve
    the requested id first and then behave as if nothing else in the pack
    existed; batch mode keeps its existing all-email validation.
    """

    def setUp(self):
        super().setUp()
        env = contact_state.UPSTREAM_SCRIPT_ENV
        saved = os.environ.get(env)

        def restore():
            if saved is None:
                os.environ.pop(env, None)
            else:
                os.environ[env] = saved

        self.addCleanup(restore)
        # Hermetic default: no sibling/installed producer script answers, so an
        # evidence case only works when the fixture installs its own stub.
        os.environ[env] = str(self.root / "checker-not-installed.py")
        # <program_root.parent>/issue59-outside backs every invalid-path
        # control and never leaks into the shared temp directory.
        self.outside_root = self.root.parent / "issue59-outside"
        self.addCleanup(shutil.rmtree, self.outside_root, True)
        self.gap_id = quote_id(ISSUE59_GAP_QUOTE)

    # ---- deterministic input builders ------------------------------------

    def outside(self, professor):
        return self.outside_root / professor

    def write_json(self, name, payload, root=None):
        return issue59_write_json(root or self.root, name, payload)

    def write_results(self, name, email_ids, extra_rows=()):
        return issue59_write_results(self.root, name, email_ids, extra_rows)

    def write_choices(self, name, email_ids, extra_rows=()):
        return issue59_write_choices(self.root, name, email_ids, extra_rows)

    def result_row(self, email_id):
        return issue59_result(self.gap_id, email_id=email_id,
                              idea_id=ISSUE59_IDEAS[email_id])

    def write_pack(self, rows):
        """Replace 邮件输入.json so exactly one unrelated defect is visible."""
        path = self.root / "教授研究" / contact_state.EMAIL_PACK
        pack = json.loads(path.read_text(encoding="utf-8"))
        pack["emails"] = list(rows)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
        return pack

    def defective_rows(self, fixture, defect):
        """The fixture's own pack rows plus the named defect and nothing else."""
        rows = copy.deepcopy(fixture["rows"])
        if defect == "not-a-dict":
            return rows + ["not-a-dict"]
        if defect == "duplicate-unrelated-email-id":
            return rows + [copy.deepcopy(rows[-1])]
        target = rows[0] if defect.startswith("selected-") else rows[-1]
        if defect in ("outside-root-professor-dir", "selected-outside-root"):
            target["professor_dir"] = str(self.outside(target["professor"]))
        elif defect == "non-string-professor-dir":
            target["professor_dir"] = 42
        elif defect == "missing-email-id":
            del target["email_id"]
        else:
            raise AssertionError(f"unknown defect: {defect}")
        return rows

    def humanized_map(self, name, drafts):
        mapping = {}
        for row in drafts:
            body = self.root / f"humanized-{row['output_id'].replace('::', '-')}.txt"
            body.write_text(row["draft"], encoding="utf-8")
            mapping[row["output_id"]] = str(body)
        return self.write_json(name, mapping)

    def plan(self, *arguments, root=None):
        return parse(run_cli("stage5-plan", "--program-root", root or self.root,
                             *arguments))

    def finalize(self, *arguments, root=None):
        return parse(run_cli("stage5-finalize", "--program-root", root or self.root,
                             *arguments))

    def humanized(self, name, results, choices, root=None):
        """The render input finalize needs: A's own plan draft, unedited."""
        draft = self.plan("--result", results, "--choices", choices,
                          "--email-id", ISSUE59_EMAIL_ID, root=root)
        self.assertEqual(draft["status"], "ok", draft)
        path = (root or self.root) / f"{name}-humanized.txt"
        path.write_text(draft["drafts"][0]["draft"], encoding="utf-8")
        return path

    def snapshot(self, *paths):
        return {str(path): Path(path).read_bytes() for path in paths
                if path is not None and Path(path).exists()}

    def stage5_artifact_snapshot(self, root=None):
        """Capture only Stage-5 rendered/state artifacts for no-write oracles."""
        program_root = Path(root or self.root)
        research = program_root / "教授研究"
        if not research.exists():
            return {}
        snapshot = {}
        for path in research.rglob("*"):
            if not path.is_file():
                continue
            if path.name == contact_state.EMAIL_STATE or path.name.startswith("套磁邮件"):
                snapshot[str(path.relative_to(program_root))] = path.read_bytes()
        return snapshot

    # ---- scope assertions -------------------------------------------------

    def assert_plan_jobs_are_one_a(self, jobs):
        self.assertEqual(jobs["status"], "ok", jobs)
        self.assertEqual(jobs["emails"], [ISSUE59_EMAIL_ID])
        self.assertEqual(jobs["verify"], {ISSUE59_PROFESSOR: "ok"})
        self.assertEqual([job["job_id"] for job in jobs["jobs"]],
                         [f"email:{ISSUE59_EMAIL_ID}"])

    def assert_drafts_are_one_a(self, payload):
        self.assertEqual(payload["status"], "ok", payload)
        self.assertEqual([row["email_id"] for row in payload["drafts"]],
                         [ISSUE59_EMAIL_ID])

    def assert_output_is_one_a(self, payload):
        self.assertEqual(payload["status"], "ok", payload)
        self.assertEqual([(row["email_id"], row["output_id"]) for row in payload["emails"]],
                         [(ISSUE59_EMAIL_ID, ISSUE59_EMAIL_ID)])

    # ---- cases ------------------------------------------------------------

    def test_issue59_t59_1_email_id_is_resolved_before_any_other_check(self):
        fixture = write_issue59_stage5_fixture(self.root, [
            {"professor": ISSUE59_PROFESSOR, "evidence": "fresh"},
            {"professor": ISSUE59_OTHER_PROFESSOR, "evidence": "fresh"}], case=self)
        results = self.write_results("issue59-1-raw.json", [ISSUE59_EMAIL_ID])
        choices = self.write_choices("issue59-1-choices.json", [ISSUE59_EMAIL_ID])
        humanized = self.humanized("issue59-1", results, choices)

        # Defects that used to block both targeted surfaces, plus the two
        # pack-wide ID defects that used to block finalize before selection.
        both_surfaces = ("outside-root-professor-dir", "non-string-professor-dir",
                         "not-a-dict")
        for defect in both_surfaces + ("missing-email-id",
                                       "duplicate-unrelated-email-id"):
            self.write_pack(self.defective_rows(fixture, defect))
            with self.subTest(defect=defect, surface="finalize"):
                self.assert_output_is_one_a(self.finalize(
                    "--result", results, "--choices", choices, "--humanized", humanized,
                    "--email-id", ISSUE59_EMAIL_ID))
            if defect not in both_surfaces:
                continue
            with self.subTest(defect=defect, surface="plan"):
                self.assert_plan_jobs_are_one_a(
                    self.plan("--email-id", ISSUE59_EMAIL_ID))

        # Collision naming comes from identity metadata, so an unselected
        # same-professor peer's path is never resolved. Derive the expected
        # filename from the frozen naming contract rather than another product run.
        peers = write_issue59_stage5_fixture(self.root, [
            {"professor": ISSUE59_PROFESSOR, "evidence": "fresh"},
            {"professor": ISSUE59_PROFESSOR, "idea_id": ISSUE59_PEER_IDEA_ID,
             "evidence": "fresh"}], case=self)
        peer_results = self.write_results("issue59-1-peer-raw.json", peers["email_ids"])
        peer_choices = self.write_choices("issue59-1-peer-choices.json", peers["email_ids"])
        peer_humanized = self.humanized(
            "issue59-1-peer", peer_results, peer_choices)

        email_hash = hashlib.sha256(
            ISSUE59_EMAIL_ID.encode("utf-8")).hexdigest()[:8]
        suffix = f"{ISSUE59_DIRECTION_ID}_{ISSUE59_IDEA_ID}_{email_hash}"
        expected_md = f"套磁邮件_{suffix}.md"
        expected_txt = f"套磁邮件_{suffix}.txt"

        # Only A2's professor_dir escapes: A keeps the contract-defined
        # collision-suffixed name without resolving A2's path.
        self.write_pack(self.defective_rows(peers, "outside-root-professor-dir"))
        escaped = self.finalize(
            "--result", peer_results, "--choices", peer_choices,
            "--humanized", peer_humanized, "--email-id", ISSUE59_EMAIL_ID)
        self.assert_output_is_one_a(escaped)
        self.assertEqual(Path(escaped["emails"][0]["md"]).name, expected_md)
        self.assertEqual(Path(escaped["emails"][0]["txt"]).name, expected_txt)

        # A malformed same-professor row without a usable email identity is not
        # a real collision peer. This is a separate fresh root so the naming
        # oracle is not affected by the valid-A2 collision subcase above.
        malformed_root = self.root / "malformed-same-professor-peer"
        malformed = write_issue59_stage5_fixture(malformed_root, [
            {"professor": ISSUE59_PROFESSOR, "evidence": "fresh"},
            {"professor": ISSUE59_PROFESSOR, "idea_id": ISSUE59_PEER_IDEA_ID,
             "evidence": "fresh"}], case=self)
        malformed_rows = copy.deepcopy(malformed["rows"])
        del malformed_rows[1]["email_id"]
        malformed_pack = malformed_root / "教授研究" / contact_state.EMAIL_PACK
        pack = json.loads(malformed_pack.read_text(encoding="utf-8"))
        pack["emails"] = malformed_rows
        malformed_pack.write_text(
            json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
        malformed_results = issue59_write_results(
            malformed_root, "issue59-1-malformed-peer-raw.json", [ISSUE59_EMAIL_ID])
        malformed_choices = issue59_write_choices(
            malformed_root, "issue59-1-malformed-peer-choices.json", [ISSUE59_EMAIL_ID])
        malformed_humanized = self.humanized(
            "issue59-1-malformed-peer", malformed_results, malformed_choices,
            root=malformed_root)
        malformed_out = self.finalize(
            "--result", malformed_results, "--choices", malformed_choices,
            "--humanized", malformed_humanized, "--email-id", ISSUE59_EMAIL_ID,
            root=malformed_root)
        self.assert_output_is_one_a(malformed_out)
        self.assertEqual(Path(malformed_out["emails"][0]["md"]).name, "套磁邮件.md")
        self.assertEqual(Path(malformed_out["emails"][0]["txt"]).name, "套磁邮件.txt")

        # Fail-closed controls on both command surfaces: the target must exist,
        # must be unambiguous, and its own path must stay inside the program.
        missing = "不存在的::DIR00001::DIR00001_1"
        for control, rows, reason, expected_message in (
                ("missing-target", copy.deepcopy(fixture["rows"]), "invalid_params",
                 f"email_id not found: {missing}"),
                ("duplicate-selected",
                 [copy.deepcopy(fixture["rows"][0]) for _ in (0, 1)],
                 "invalid_email_pack", None),
                ("selected-outside-root",
                 self.defective_rows(fixture, "selected-outside-root"),
                 "invalid_professor_dir", None)):
            self.write_pack(rows)
            target = missing if control == "missing-target" else ISSUE59_EMAIL_ID
            for surface in ("plan", "finalize"):
                with self.subTest(control=control, surface=surface):
                    before = self.stage5_artifact_snapshot()
                    payload = (self.plan("--email-id", target) if surface == "plan"
                               else self.finalize("--result", results, "--choices",
                                                  choices, "--humanized", humanized,
                                                  "--email-id", target))
                    self.assertEqual(payload["status"], "error", payload)
                    self.assertEqual(payload["reason_code"], reason, payload)
                    if expected_message is not None:
                        self.assertEqual(payload["message"], expected_message)
                    self.assertEqual(
                        self.stage5_artifact_snapshot(), before,
                        f"{control}/{surface}: fail-closed validation mutated Stage-5 artifacts")
                    if control == "selected-outside-root":
                        self.assertFalse(
                            self.outside_root.exists(),
                            f"{surface}: invalid selected path created files outside program_root")

    def test_issue59_t59_2_result_and_choices_rows_are_selected_scoped(self):
        write_issue59_stage5_fixture(self.root, case=self)
        results = self.write_results("issue59-2-raw.json", [ISSUE59_EMAIL_ID])
        choices = self.write_choices("issue59-2-choices.json", [ISSUE59_EMAIL_ID])
        humanized = self.humanized("issue59-2", results, choices)

        unrelated = {
            "non-dict-row": ["not-a-row"],
            "missing-email-id": [{"idea": {"id": "DIR00001_1"}}],
            "duplicate-unrelated-email-id": [
                {"email_id": "幽灵 教授::DIR00007::DIR00007_1"},
                {"email_id": "幽灵 教授::DIR00007::DIR00007_1"}],
        }
        for label, extra in unrelated.items():
            for document in ("result", "choices"):
                with self.subTest(defect=label, document=document):
                    rows = ([self.result_row(ISSUE59_EMAIL_ID)] + extra
                            if document == "result" else
                            [issue59_choices(ISSUE59_EMAIL_ID)] + extra)
                    noisy = self.write_json(f"issue59-2-{label}-{document}.json", rows)
                    raw = noisy if document == "result" else results
                    picked = noisy if document == "choices" else choices
                    self.assert_drafts_are_one_a(self.plan(
                        "--result", raw, "--choices", picked,
                        "--email-id", ISSUE59_EMAIL_ID))
                    self.assert_output_is_one_a(self.finalize(
                        "--result", raw, "--choices", picked, "--humanized", humanized,
                        "--email-id", ISSUE59_EMAIL_ID))

        # The selected id's own occurrence is still validated exactly once
        # in both scoped documents.
        for label, email_ids in (("duplicated", [ISSUE59_EMAIL_ID, ISSUE59_EMAIL_ID]),
                                 ("absent", [ISSUE59_OTHER_EMAIL_ID])):
            for document in ("result", "choices"):
                bad_result = (self.write_results(
                    f"issue59-2-{label}-result.json", email_ids)
                              if document == "result" else results)
                bad_choices = (self.write_choices(
                    f"issue59-2-{label}-choices.json", email_ids)
                               if document == "choices" else choices)
                for surface in ("plan", "finalize"):
                    with self.subTest(selected=label, document=document,
                                      surface=surface):
                        before = self.stage5_artifact_snapshot()
                        payload = (self.plan(
                            "--result", bad_result, "--choices", bad_choices,
                            "--email-id", ISSUE59_EMAIL_ID)
                                   if surface == "plan" else self.finalize(
                            "--result", bad_result, "--choices", bad_choices,
                            "--humanized", humanized,
                            "--email-id", ISSUE59_EMAIL_ID))
                        self.assertEqual(payload["status"], "error", payload)
                        self.assertEqual(payload["reason_code"], "invalid_result_json",
                                         payload)
                        self.assertEqual(
                            self.stage5_artifact_snapshot(), before,
                            f"{label}/{document}/{surface}: invalid selected row mutated "
                            "Stage-5 artifacts")

        # A selected row's own content contract is not relaxed by scoping on
        # either deterministic Stage-5 command surface.
        broken = self.write_json("issue59-2-broken.json",
                                 [dict(self.result_row(ISSUE59_EMAIL_ID),
                                       future_aspiration_ja="")])
        for surface in ("plan", "finalize"):
            with self.subTest(selected="invalid-raw", surface=surface):
                before = self.stage5_artifact_snapshot()
                payload = (self.plan(
                    "--result", broken, "--choices", choices,
                    "--email-id", ISSUE59_EMAIL_ID)
                           if surface == "plan" else self.finalize(
                    "--result", broken, "--choices", choices,
                    "--humanized", humanized, "--email-id", ISSUE59_EMAIL_ID))
                self.assertEqual(payload["status"], "error", payload)
                self.assertEqual(payload["reason_code"], "invalid_result_json", payload)
                self.assertEqual(
                    self.stage5_artifact_snapshot(), before,
                    f"invalid-raw/{surface}: invalid selected result mutated "
                    "Stage-5 artifacts")

        # Batch mode keeps load_id_map(exact=True) strict. The choices half of
        # that boundary is owned by test_stage5_choices_id_mapping_fails_closed
        # (T59-5), so only the raw-result loader control is added here.
        batch_raw = self.write_json("issue59-2-batch-raw.json",
                                    [self.result_row(ISSUE59_EMAIL_ID),
                                     {"first_choice": True}])
        batch = self.plan("--result", batch_raw, "--choices", choices)
        self.assertEqual(batch["status"], "error", batch)
        self.assertEqual(batch["reason_code"], "invalid_result_json", batch)

    def test_issue59_t59_3_unrelated_stale_source_state_cannot_rebuild_for_a(self):
        fixture = write_issue59_stage5_fixture(self.root, [
            {"professor": ISSUE59_PROFESSOR, "evidence": "fresh"},
            {"professor": ISSUE59_OTHER_PROFESSOR, "evidence": "fresh",
             "source_state": "stale"}], case=self)
        marker = fixture["checker_marker"]
        results = self.write_results("issue59-3-raw.json", fixture["email_ids"])
        choices = self.write_choices("issue59-3-choices.json", fixture["email_ids"])
        humanized = self.humanized("issue59-3", results, choices)

        jobs = self.plan("--email-id", ISSUE59_EMAIL_ID)
        self.assert_plan_jobs_are_one_a(jobs)
        self.assertEqual(set(jobs["contact_evidence"]), {ISSUE59_PROFESSOR})
        self.assert_output_is_one_a(self.finalize(
            "--result", results, "--choices", choices, "--humanized", humanized,
            "--email-id", ISSUE59_EMAIL_ID))
        self.assertFalse(marker.exists(),
                         "B alone must not pull a targeted run into a rebuild")

        # The owner report stays program-level: B is visible inside it.
        report, error = contact_state.run_upstream_check_argv([
            sys.executable, str(contact_state.upstream_check_script()),
            str(self.root), "--check"])
        self.assertIsNone(error)
        self.assertEqual(report["result"], "stale")
        self.assertEqual({entry["name"]: entry["result"] for entry in report["professors"]},
                         {ISSUE59_PROFESSOR: "fresh", ISSUE59_OTHER_PROFESSOR: "stale"})

    def test_issue59_t59_4_targeted_finalize_has_no_unrelated_dependency(self):
        for variant in ISSUE59_DEPENDENCY_VARIANTS:
            with self.subTest(variant=variant):
                root = self.root / f"variant-{variant}"
                prepared = issue59_dependency_variant(root, variant, self)
                results, choices = prepared["results"], prepared["choices"]
                b_dir = prepared["b_dir"]
                overview = prepared["overview"]
                b_outputs = (b_dir / "套磁邮件.md", b_dir / "套磁邮件.txt")
                absent_b_outputs = tuple(path for path in b_outputs if not path.exists())
                untouched = self.snapshot(
                    prepared["b_state"], prepared["b_verify"], *b_outputs, overview)
                aggregate = root / "教授研究" / contact_state.EMAIL_OVERVIEW
                projection_registry = (
                    root / "教授研究" / contact_state.PROJECTIONS_FILE)
                projection_before = (
                    projection_registry.read_bytes()
                    if projection_registry.is_file() else None)
                if variant == "clean":
                    # A third independently built instance, not a finalized
                    # fixture with its aggregate removed afterwards.
                    self.assertFalse(aggregate.exists())
                    self.assertFalse((root / "教授研究" / "X分野" / ISSUE59_PROFESSOR
                                      / "套磁邮件.md").exists())
                humanized = self.humanized(f"issue59-4-{variant}", results, choices,
                                           root=root)
                out = self.finalize("--result", results, "--choices", choices,
                                    "--humanized", humanized,
                                    "--email-id", ISSUE59_EMAIL_ID, root=root)
                self.assertEqual(out["status"], "ok", out)
                self.assertEqual([row["email_id"] for row in out["emails"]],
                                 [ISSUE59_EMAIL_ID])
                a_dir = root / "教授研究" / "X分野" / ISSUE59_PROFESSOR
                self.assertTrue((a_dir / "套磁邮件.md").is_file())
                self.assertTrue((a_dir / "套磁邮件.txt").is_file())
                state_path = a_dir / contact_state.EMAIL_STATE
                self.assertTrue(state_path.is_file())
                state = json.loads(state_path.read_text(encoding="utf-8"))
                self.assertEqual(list(state["emails"]), [ISSUE59_EMAIL_ID])
                for name, payload in untouched.items():
                    self.assertEqual(Path(name).read_bytes(), payload, name)
                for path in absent_b_outputs:
                    self.assertFalse(
                        path.exists(),
                        f"targeted finalize created unrelated output: {path}")
                if overview is None:
                    self.assertFalse(aggregate.exists())
                    self.assertIsNone(out["overview_md"], out)
                else:
                    self.assertEqual(out["overview_md"], str(overview), out)
                if projection_before is None:
                    self.assertFalse(
                        projection_registry.exists(),
                        "targeted finalize created program projection metadata")
                else:
                    self.assertTrue(projection_registry.is_file())
                    self.assertEqual(
                        projection_registry.read_bytes(), projection_before,
                        "targeted finalize mutated program projection metadata")

    def test_issue59_t59_5_batch_mode_still_validates_every_pack_row(self):
        fixture = write_issue59_stage5_fixture(self.root, [
            {"professor": ISSUE59_PROFESSOR, "evidence": "fresh"},
            {"professor": ISSUE59_OTHER_PROFESSOR, "evidence": "fresh"}], case=self)
        both = fixture["email_ids"]
        results = self.write_results("issue59-5-raw.json", both)
        choices = self.write_choices("issue59-5-choices.json", both)
        drafts = self.plan("--result", results, "--choices", choices)
        self.assertEqual(drafts["status"], "ok", drafts)
        humanized = self.humanized_map("issue59-5-map.json", drafts["drafts"])

        # Only B's professor_dir escapes the program root.
        self.write_pack(self.defective_rows(fixture, "outside-root-professor-dir"))
        for surface in ("plan", "finalize"):
            with self.subTest(surface=surface):
                payload = (self.plan("--result", results, "--choices", choices)
                           if surface == "plan" else self.finalize(
                        "--result", results, "--choices", choices,
                        "--humanized-map", humanized))
                self.assertEqual(payload["status"], "error", payload)
                self.assertEqual(payload["reason_code"], "invalid_professor_dir",
                                 payload)
                self.assertFalse(
                    self.outside_root.exists(),
                    f"{surface}: invalid B path created files outside program_root")
        b_dir = fixture["dirs"][ISSUE59_OTHER_PROFESSOR]
        for professor_dir in (self.prof_dir, b_dir):
            self.assertFalse((professor_dir / "套磁邮件.md").exists())
            self.assertFalse((professor_dir / "套磁邮件.txt").exists())
            self.assertFalse((professor_dir / contact_state.EMAIL_STATE).exists())

        # AC59-7 also freezes the batch aggregate compatibility path that this
        # PR moved under the new targeted/batch branch.  Reuse the existing
        # managed-conflict fixture rather than adding a new top-level case.
        conflict_root = self.root / "batch-overview-conflict"
        conflict_fixture = write_issue59_stage5_fixture(conflict_root, [
            {"professor": ISSUE59_PROFESSOR, "evidence": "fresh"},
            {"professor": ISSUE59_OTHER_PROFESSOR, "evidence": "fresh"}],
            overview="conflict", case=self)
        conflict_results = issue59_write_results(
            conflict_root, "issue59-5-conflict-raw.json",
            conflict_fixture["email_ids"])
        conflict_choices = issue59_write_choices(
            conflict_root, "issue59-5-conflict-choices.json",
            conflict_fixture["email_ids"])
        conflict_plan = self.plan(
            "--result", conflict_results, "--choices", conflict_choices,
            root=conflict_root)
        self.assertEqual(conflict_plan["status"], "ok", conflict_plan)
        humanized_map = {}
        for row in conflict_plan["drafts"]:
            rendered = conflict_root / (
                "issue59-5-conflict-" +
                row["output_id"].replace("::", "-") + ".txt")
            rendered.write_text(row["draft"], encoding="utf-8")
            humanized_map[row["output_id"]] = str(rendered)
        conflict_humanized = issue59_write_json(
            conflict_root, "issue59-5-conflict-humanized-map.json",
            humanized_map)

        conflict_overview = conflict_fixture["overview"]
        projection_registry = (
            conflict_root / "教授研究" / contact_state.PROJECTIONS_FILE)
        overview_before = conflict_overview.read_bytes()
        projection_before = projection_registry.read_bytes()
        conflict = self.finalize(
            "--result", conflict_results, "--choices", conflict_choices,
            "--humanized-map", conflict_humanized, root=conflict_root)
        self.assertEqual(conflict["status"], "needs_decision", conflict)
        self.assertEqual(conflict["reason_code"], "manual_markdown_changed", conflict)
        self.assertEqual(conflict["target"], str(conflict_overview), conflict)
        self.assertEqual(conflict_overview.read_bytes(), overview_before)
        self.assertEqual(projection_registry.read_bytes(), projection_before)
        for professor_dir in conflict_fixture["dirs"].values():
            self.assertFalse((professor_dir / "套磁邮件.md").exists())
            self.assertFalse((professor_dir / "套磁邮件.txt").exists())
            self.assertFalse((professor_dir / contact_state.EMAIL_STATE).exists())


class _ForeignAuthorityGuard:
    """Record existence / metadata / content / mutation access to foreign state.

    Same oracle shape as the Stage-1 caller contract: only the syscall layer is
    wrapped, so constructing a path string never counts as an access.
    """

    _PATH_ARGS = {
        "stat": (0,), "lstat": (0,), "open": (0,), "remove": (0,), "unlink": (0,),
        "rename": (0, 1), "replace": (0, 1), "mkdir": (0,), "makedirs": (0,),
        "rmdir": (0,), "utime": (0,), "chmod": (0,), "link": (0, 1),
        "symlink": (0, 1), "readlink": (0,), "access": (0,),
    }

    def __init__(self, forbidden):
        self.targets = set()
        for path in forbidden:
            literal = os.path.abspath(os.fspath(path))
            self.targets.add(literal)
            self.targets.add(os.path.realpath(literal))
        self.accesses: list[str] = []
        self._restore = []

    def _record(self, operation, value):
        try:
            text = os.fspath(value)
        except TypeError:
            return
        if isinstance(text, bytes):
            text = os.fsdecode(text)
        if not isinstance(text, str) or not text:
            return
        if os.path.abspath(text) in self.targets:
            self.accesses.append(f"{operation} {text}")

    def _path_proxy(self, original, operation, indexes):
        def proxy(*args, **kwargs):
            for index in indexes:
                if index < len(args):
                    self._record(operation, args[index])
            for name in ("src", "dst", "path", "file", "filename"):
                if name in kwargs:
                    self._record(operation, kwargs[name])
            return original(*args, **kwargs)
        return proxy

    def _enum_proxy(self, original, operation):
        def proxy(path, *args, **kwargs):
            base = os.path.abspath(os.fspath(path))
            result = original(path, *args, **kwargs)
            if operation == "listdir":
                names = list(result)
                for name in names:
                    self._record(f"{operation}:{base}", f"{base}/{name}")
                return names

            def yielded():
                with result as iterator:
                    for entry in iterator:
                        self._record(f"{operation}:{base}", f"{base}/{entry.name}")
                        yield entry
            return yielded()
        return proxy

    def __enter__(self):
        import builtins

        for name, indexes in self._PATH_ARGS.items():
            original = getattr(os, name)
            setattr(os, name, self._path_proxy(original, name, indexes))
            self._restore.append((os, name, original))
        for name in ("listdir", "scandir"):
            original = getattr(os, name)
            setattr(os, name, self._enum_proxy(original, name))
            self._restore.append((os, name, original))
        for module, label in ((io, "io.open"), (builtins, "open")):
            original = module.open
            setattr(module, "open", self._path_proxy(original, label, (0,)))
            self._restore.append((module, "open", original))
        self._restore.append((Path, "open", Path.open))
        Path.open = self._path_proxy(Path.open, "Path.open", (0,))
        return self

    def __exit__(self, exc_type, exc, tb):
        for module, name, original in reversed(self._restore):
            setattr(module, name, original)
        self._restore = []
        return False


class Issue65Stage2BindingEnv(unittest.TestCase):
    """A/B share one display professor name; only canonical identity separates them."""

    DISPLAY = "教授同名"
    B_DISPLAY = None
    PACK = "套磁候选输入.json"
    ANALYSIS_MD = "套磁候选分析.md"
    FRESHNESS_CACHE = Path("论文分析") / "_freshness_cache.json"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.legacy_snapshot = self.root / "教授研究" / "套磁阶段1候选.json"
        self.gap_quotes = {
            "AAAA1111": "Future work will extend the synthetic comparison to a second input pattern.",
            "BBBB2222": "We plan to test a second synthetic processing path.",
        }
        self.prof_dirs = {}
        self.targets = {}
        self.snapshots = {}
        for group in ("labA", "labB"):
            professor = self.DISPLAY if group == "labA" else (self.B_DISPLAY or self.DISPLAY)
            self.prof_dirs[group] = self._make_professor(group, f"fp-{group}", professor=professor)
        self.a_dir = self.prof_dirs["labA"]
        self.b_dir = self.prof_dirs["labB"]
        self.a_target = self.targets["labA"]
        self.b_target = self.targets["labB"]
        self.a_snapshot = self.snapshots["labA"]
        self.b_snapshot = self.snapshots["labB"]
        ledger = self.root / "教授研究" / "_署名对照.json"
        ledger.write_text(json.dumps({
            "updated_at": "2026-09-29T00:00:00Z", "overrides": {},
            "professors": {self.DISPLAY: {
                "books": [{"prof_name_tokens": ["教授", self.DISPLAY.removeprefix("教授")], "seed_count": 2, "auto": [],
                           "conflicted": [], "offenders": [], "typos": [], "mashes": []}],
                "seed_count": 2}}}, ensure_ascii=False), encoding="utf-8")
        self.legacy_snapshot.write_text(json.dumps({
            "schema_version": 1, "kind": "professor-contact-stage1", "updated_at": None,
            "professors": [], "sentinel": "issue-65-legacy-aggregate-sentinel"},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        self.preflight_file = self.root / "preflight.json"
        self.results = self._write_results()
        self.facts_path = self._write_facts()

    def tearDown(self):
        self.temp.cleanup()

    # -- fixture -----------------------------------------------------------

    def _preview(self, fingerprint: str, *, professor: str | None = None) -> dict:
        return {
            "schema_version": 1, "professor": professor if professor is not None else self.DISPLAY,
            "direction_id_version": "members-v1", "membership_mode": "overlap_allowed",
            "membership_coverage": {"assigned_unique_members": 2, "membership_edges": 2,
                                    "overlap_member_count": 0, "overlap_members": [],
                                    "unassigned_mountable_count": 0},
            "preview_fingerprint": fingerprint,
            "preview_fingerprint_version": "preview-v1",
            "coverage": 1.0, "data_confidence": "high",
            "directions": [{
                "direction_id": "DIR00001", "name_ja": "合成输入比较", "name_zh": "合成输入比较",
                "summary_zh": "比较两种合成输入的处理结果",
                "member_fingerprint": f"mf-{fingerprint}",
                "members": [{"item_key": "AAAA1111", "preview_confidence": "high"},
                            {"item_key": "BBBB2222", "preview_confidence": "high"}],
                "low_confidence_count": 0, "coverage_share": 1.0,
                "representatives": [{"item_key": "AAAA1111",
                                     "title": "Synthetic comparison of input patterns",
                                     "year": 2023}],
                "user_note": "我想比较两种合成输入的处理结果。",
            }],
        }

    def _make_professor(self, group: str, fingerprint: str, *, professor: str | None = None) -> Path:
        display = professor if professor is not None else self.DISPLAY
        professor_dir = self.root / "教授研究" / group / display
        analysis_dir = professor_dir / "论文分析"
        analysis_dir.mkdir(parents=True)
        preview = professor_dir / "方向预筛.json"
        preview.write_text(json.dumps(self._preview(fingerprint, professor=display), ensure_ascii=False, indent=1),
                           encoding="utf-8")
        catalog = []
        for key, year, status in (("AAAA1111", 2023, "downloaded"),
                                  ("BBBB2222", 2024, "downloaded")):
            analysis = analysis_dir / f"{key}.md"
            analysis.write_text(f"# analysis {key}\n", encoding="utf-8")
            sidecar = make_sidecar(analysis, [self.gap_quotes[key]])
            catalog.append({"item_key": key, "title": f"{key} title", "title_zh": None,
                            "pdf_status": status, "analysis_file": str(analysis),
                            "sidecar_file": str(sidecar)})
        (professor_dir / "papers.json").write_text(
            json.dumps({"professor": {"name": display}, "papers": catalog},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        contact_targets.bootstrap_target(
            self.root, preview, {"direction_ids": ["DIR00001"],
                                 "notes": {"DIR00001": "我想比较两种合成输入的处理结果。"}},
            selected_at="2026-09-29T00:00:00Z")
        built = io.StringIO()
        with contextlib.redirect_stdout(built):
            contact_stage1.build_command(
                self.root, professor_dir / "套磁目标.json", None)
        self.snapshots[group] = professor_dir / "套磁阶段1候选.json"
        self.targets[group] = professor_dir / "套磁目标.json"
        return professor_dir

    def _write_facts(self, preflight_id=None) -> Path:
        papers = []
        for key, year, authorship, has_pdf in (("AAAA1111", 2023, "corresponding", True),
                                               ("BBBB2222", 2024, "first", True)):
            analysis = self.a_dir / "论文分析" / f"{key}.md"
            papers.append({
                "item_key": key, "title": f"{key} title", "year": year, "month": 5,
                "authorship": authorship, "abstract": f"Abstract for {key}.",
                "has_pdf": has_pdf, "authors": ["試験 One"],
                "analysis_file": str(analysis),
                "sidecar_file": str(analysis) + ".future_work.json"})
        facts = {
            "program_root": str(self.root), "professor_dir": str(self.a_dir),
            "professor": self.DISPLAY, "current_year": datetime.now().year,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": [{
                "collection_key": "DIR00001", "direction_id": "DIR00001",
                "name_ja": "合成输入比较", "name_zh": "合成输入比较", "status": "active",
                "member_keys": ["AAAA1111", "BBBB2222"],
                "relevant_keys": ["AAAA1111", "BBBB2222"], "named_keys": ["AAAA1111"],
                "user_note": "我想比较两种合成输入的处理结果。",
                "credibility": {"verdict": "站得住", "mainline": "主线",
                                "authorship_line": "corresponding_dominant", "note": "test"},
                "red_lines": []}],
        }
        if preflight_id:
            facts["stage2_preflight"] = {"preflight_id": preflight_id}
        self.facts_path = self.root / "facts.json"
        self.facts_path.write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        return self.facts_path

    def _write_results(self) -> Path:
        results = self.root / "results"
        results.mkdir(parents=True, exist_ok=True)
        rows = [{"gap_id": quote_id(quote), "status": "open", "candidate_paper_ids": [],
                 "evidence": f"无更晚论文实现该点（{key}）", "confidence": "high"}
                for key, quote in self.gap_quotes.items()]
        (results / "freshness-DIR00001.json").write_text(json.dumps({
            "schema": 1, "kind": "freshness", "collection_key": "DIR00001", "direction_id":
            "DIR00001", "results": rows}, ensure_ascii=False), encoding="utf-8")
        g1 = quote_id(self.gap_quotes["AAAA1111"])
        (results / "narrative.json").write_text(json.dumps({
            "schema": 1, "kind": "narrative", "directions": [{
                "collection_key": "DIR00001", "direction_id": "DIR00001",
                "positioning": [{"kind": "para",
                                 "text": "教授从 {{P:AAAA1111}} 起研究合成输入比较；{{G:" + g1 + "}} 是延伸点。",
                                 "refs": ["paper:AAAA1111", "gap:" + g1],
                                 "concrete_object": "合成输入与第二种模式",
                                 "input_example": "输入一组固定的合成样本",
                                 "output_example": "系统给出两种处理结果"}],
                "gap_notes": [{"gap_id": g1, "summary": "扩展到第二种输入模式",
                               "explanation": "研究计划比较另一种合成场景。"}]}]},
            ensure_ascii=False), encoding="utf-8")
        return results

    # -- guarded product invocations ---------------------------------------

    def guard(self):
        return _ForeignAuthorityGuard([self.b_snapshot, self.legacy_snapshot])

    def _capture(self, func, *args):
        """Run a formal Stage-2 command in-process; return (stdout, exit code)."""
        buffer = io.StringIO()
        code = None
        try:
            with contextlib.redirect_stdout(buffer):
                func(*args)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
        return buffer.getvalue(), code

    def _run_formal(self, func, *args, scenario):
        """Run one formal Stage-2 command; escaping crashes fail the assertion.

        A raw product exception must not escape as a test-body error: the
        product-call boundary converts it into an assertion failure so the
        evaluator can attribute it to the producer instead of the fixture.
        """
        try:
            return self._capture(func, *args)
        except Exception as exc:
            self.fail(f"{scenario} product call raised {type(exc).__name__}: {exc}")

    def _formal_ok_payload(self, text: str, code, scenario: str) -> dict:
        """Parse one formal command's stdout that must be an ok terminal."""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            self.fail(f"{scenario} emitted unparseable output: {text!r}")
        self.assertEqual(payload.get("status"), "ok", f"{scenario} terminal: {payload}")
        self.assertIsNone(code, f"{scenario} exit code: {code!r}")
        return payload

    def preflight(self):
        args = argparse.Namespace(
            program_root=str(self.root), professor=self.DISPLAY,
            target_file=str(self.a_target), paper_analysis="relevant",
            gap_scope="selected_direction", freshness_scope="shortlist",
            max_relevant_papers=None)
        text, code = self._run_formal(contact_state.cmd_stage2_preflight, args,
                                      scenario="preflight")
        return self._formal_ok_payload(text, code, "preflight")

    def plan(self):
        args = argparse.Namespace(facts=str(self.facts_path),
                                  preflight_file=str(self.preflight_file))
        text, code = self._run_formal(contact_state.cmd_stage2_plan, args, scenario="plan")
        return self._formal_ok_payload(text, code, "plan")

    def plan_raw(self, preflight_file):
        """Run the formal plan against an explicit preflight file (no ok assert)."""
        args = argparse.Namespace(facts=str(self.facts_path),
                                  preflight_file=str(preflight_file))
        return self._run_formal(contact_state.cmd_stage2_plan, args, scenario="plan")

    def finalize(self):
        args = argparse.Namespace(facts=str(self.facts_path),
                                  results=str(self.results),
                                  decision_file=None, resolved_directions=None,
                                  preflight_file=str(self.preflight_file))
        return self._run_formal(contact_state.cmd_stage2_finalize, args, scenario="finalize")

    def outputs_state(self):
        state = {}
        for relative in (self.PACK, self.ANALYSIS_MD, str(self.FRESHNESS_CACHE)):
            path = self.a_dir / relative
            raw = path.read_bytes() if path.is_file() else None
            state[relative] = (path.is_file(), raw)
        return state

    def fingerprint(self, path: Path):
        raw = path.read_bytes() if path.is_file() else None
        return (path.is_file(), hashlib.sha256(raw or b"").hexdigest())


class Issue65Stage2BindingTests(Issue65Stage2BindingEnv):
    def test_issue65_stage2_exact_stage1_binding_lifecycle(self):
        # C65-02: Stage 2 binds A's exact local target + A's exact local Stage-1 state.
        self.assertEqual(self.a_snapshot.parent, self.a_dir)
        self.assertNotEqual(self.a_snapshot, self.b_snapshot)
        self.assertTrue(self.a_snapshot.is_file())
        self.assertTrue(self.b_snapshot.is_file())

        guard = self.guard()
        with guard:
            proof = self.preflight()
        self.assertEqual(proof["status"], "ok", proof)
        self.assertEqual(proof["professor"], self.DISPLAY)
        self.assertEqual(str(Path(proof["pack_path"]).parent), str(self.a_dir))
        self.assertEqual(guard.accesses, [], f"preflight accessed foreign authority: {guard.accesses}")
        self.preflight_file.write_text(json.dumps(proof, ensure_ascii=False), encoding="utf-8")
        self._write_facts(preflight_id=proof["preflight_id"])

        guard = self.guard()
        with guard:
            planned = self.plan()
        self.assertEqual(planned["status"], "ok", planned)
        self.assertEqual(planned["professor"], self.DISPLAY)
        self.assertEqual(str(Path(planned["professor_dir"])), str(self.a_dir))
        self.assertEqual(guard.accesses, [], f"plan accessed foreign authority: {guard.accesses}")

        target_before = self.a_target.read_bytes()
        snapshot_before = self.a_snapshot.read_bytes()
        outputs_before = self.outputs_state()
        b_before = self.fingerprint(self.b_snapshot)
        legacy_before = self.fingerprint(self.legacy_snapshot)

        # local-target digest negative subcase
        drifted = json.loads(self.a_target.read_text(encoding="utf-8"))
        drifted["directions"][0]["user_note"] = "我想比较三种合成输入的处理结果。"
        self.assertEqual(drifted["professor_dir"], json.loads(target_before)["professor_dir"])
        self.assertEqual(drifted["preview_path"], json.loads(target_before)["preview_path"])
        self.a_target.write_text(json.dumps(drifted, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
        guard = self.guard()
        with guard:
            text, code = self.finalize()
        self.assertEqual(code, 2, f"finalize accepted a changed local target: {text}")
        self.assertEqual(guard.accesses, [],
                         f"rejected finalize accessed foreign authority: {guard.accesses}")
        self.assertEqual(self.outputs_state(), outputs_before)
        self.a_target.write_bytes(target_before)

        # Stage-1 fingerprint negative subcase
        state = json.loads(self.a_snapshot.read_text(encoding="utf-8"))
        original_fingerprint = state["input_fingerprint"]
        self.assertNotIn("professors", state)
        self.assertEqual(str(Path(state["professor_dir"])),
                         str(Path("教授研究") / "labA" / self.DISPLAY))
        state["input_fingerprint"] = "0" * len(original_fingerprint)
        self.a_snapshot.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        guard = self.guard()
        with guard:
            text, code = self.finalize()
        self.assertEqual(code, 2, f"finalize accepted a changed Stage-1 fingerprint: {text}")
        self.assertEqual(guard.accesses, [],
                         f"rejected finalize accessed foreign authority: {guard.accesses}")
        self.assertEqual(self.outputs_state(), outputs_before)
        self.a_snapshot.write_bytes(snapshot_before)

        # the same path must succeed once the exact bound inputs are restored
        guard = self.guard()
        with guard:
            text, code = self.finalize()
        self.assertIsNone(code, f"legal fixture failed to finalize: {text}")
        self.assertEqual(guard.accesses, [], f"finalize accessed foreign authority: {guard.accesses}")

        outputs_after = self.outputs_state()
        for relative in (self.PACK, self.ANALYSIS_MD, str(self.FRESHNESS_CACHE)):
            self.assertTrue(outputs_after[relative][0], f"a legal finalize must write {relative}")
            if outputs_before[relative][0]:
                self.assertNotEqual(outputs_after[relative], outputs_before[relative],
                                    f"a legal finalize must refresh {relative}")
        self.assertEqual(self.fingerprint(self.b_snapshot), b_before)
        self.assertEqual(self.fingerprint(self.legacy_snapshot), legacy_before)
        self.assertEqual(self.a_target.read_bytes(), target_before)
        self.assertEqual(self.a_snapshot.read_bytes(), snapshot_before)


class TestIssue64Stage2PlanBinding(Issue65Stage2BindingEnv):
    """G64-T6（适配教授本地快照）：plan 消费已保存的 preflight 证明并把完整
    教授本地目标身份重新绑定；只改 selection_history 这类部分指纹覆盖不到的
    目标内容，必须在 plan 与 finalize 两处失败且零写入。"""

    def _preflight_for(self, professor, target_file):
        args = argparse.Namespace(
            program_root=str(self.root), professor=professor,
            target_file=str(target_file), paper_analysis="relevant",
            gap_scope="selected_direction", freshness_scope="shortlist",
            max_relevant_papers=None)
        text, code = self._run_formal(contact_state.cmd_stage2_preflight, args,
                                      scenario=f"preflight {target_file}")
        return self._formal_ok_payload(text, code, f"preflight {target_file}")

    def _save_proof(self, proof):
        self.preflight_file.write_text(json.dumps(proof, ensure_ascii=False), encoding="utf-8")
        return proof

    def _bind_facts(self, proof):
        self._write_facts(preflight_id=proof["preflight_id"])

    def _mutate_target_selection_history(self):
        target = json.loads(self.a_target.read_text(encoding="utf-8"))
        target["selection_history"] = [dict(
            selected_at="2026-09-30T00:00:00Z",
            selected_direction_ids=list(target["selected_direction_ids"]))]
        self.a_target.write_text(json.dumps(target, ensure_ascii=False, indent=1),
                                 encoding="utf-8")

    def test_issue64_t6_plan_carries_the_consumed_preflight_proof(self):
        proof = self._save_proof(self.preflight())
        self._bind_facts(proof)
        planned = self.plan()
        self.assertEqual(planned.get("status"), "ok", planned)
        self.assertEqual(planned.get("preflight_id"), proof["preflight_id"])
        identity = planned.get("transaction_identity")
        self.assertEqual(identity["professor"], self.DISPLAY)
        self.assertEqual(Path(identity["target_state"]).resolve(),
                         self.a_target.resolve())
        snapshot = json.loads(self.a_snapshot.read_text(encoding="utf-8"))
        self.assertEqual(identity["stage1_input_fingerprint"],
                         snapshot["input_fingerprint"])

    def test_issue64_t6_plan_refuses_a_sibling_preflight_proof(self):
        sibling_proof = self._save_proof(self._preflight_for(self.DISPLAY, self.b_target))
        self._bind_facts(sibling_proof)
        text, code = self.plan_raw(self.preflight_file)
        payload = json.loads(text)
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertEqual(payload["reason_code"], "preflight_inputs_changed", payload)
        self.assertEqual(code, 2)

    def test_issue64_t6_plan_refuses_a_missing_preflight_file(self):
        text, code = self.plan_raw(self.root / "不存在的证明.json")
        payload = json.loads(text)
        self.assertEqual(payload["reason_code"], "invalid_params", payload)
        self.assertEqual(code, 1)

    def test_issue64_t6_selection_history_change_fails_plan_and_finalize_with_zero_writes(self):
        proof = self._save_proof(self.preflight())
        self._bind_facts(proof)
        outputs_before = self.outputs_state()
        self._mutate_target_selection_history()

        text, code = self.plan_raw(self.preflight_file)
        payload = json.loads(text)
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertEqual(code, 2)
        self.assertIn("identity", payload.get("drift", []), payload)

        text, code = self.finalize()
        payload = json.loads(text)
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertEqual(code, 2)
        self.assertIn("identity", payload.get("drift", []), payload)
        self.assertEqual(self.outputs_state(), outputs_before)

ISSUE67_FAULT_SITECUSTOMIZE = '''"""Test-only fault injection: fail one atomic-JSON install inside the runner.

The deterministic issue #67 proofs need to observe what a pair-atomic write does
when the SECOND file cannot be installed. Nothing in the product reads these
variables; sitecustomize is imported by the interpreter before the CLI starts, so
the failure lands exactly on os.replace() that contact_state's writer calls.
"""
import os as _os
from pathlib import Path as _Path

_TARGET_DIR = _os.environ.get("PC67_FAULT_DIR")
_TARGET_NAME = _os.environ.get("PC67_FAULT_NAME")
_REMAINING = int(_os.environ.get("PC67_FAULT_TIMES", "1"))
_REAL_REPLACE = _os.replace


def _replace(src, dst, *args, **kwargs):
    global _REMAINING
    if _TARGET_DIR and _TARGET_NAME and _REMAINING > 0:
        path = _Path(dst)
        if path.name == _TARGET_NAME and str(path.resolve().parent) == _TARGET_DIR:
            # Only the product's own write faults; the rollback path has to be
            # able to move the backup back into place.
            _REMAINING -= 1
            raise OSError(28, "injected install failure")
    return _REAL_REPLACE(src, dst, *args, **kwargs)


_os.replace = _replace
'''


class _Issue67Stage4Fixture(BaseEnv):
    """Shared two-professor fixture for the issue #67 Stage-4 proofs.

    It carries no test methods: every case class that mixes it in declares its
    own, so the Gate-2 recipe can run each proof class by name.
    """

    SELECT = contact_state.SELECTION_FILE
    PACK = contact_state.EMAIL_PACK

    def setUp(self):
        super().setUp()
        self.assertEqual(self.stage3_run()["status"], "ok")
        self.research = self.root / "教授研究"
        # Every invalid-path control lives outside the program tree and never
        # leaks into the shared temp directory.
        self.outside = self.root.parent / "issue67-outside"
        self.addCleanup(shutil.rmtree, self.outside, True)
        self.faultsite = Path(str(self.temp.name) + "-faultsite")
        self.addCleanup(shutil.rmtree, self.faultsite, True)

    # ---- fixture helpers --------------------------------------------------

    def clone_professor(self, name, field="Y分野"):
        """Give a second professor its own current Stage-3 state and input pack."""
        directory = self.research / field / name
        directory.mkdir(parents=True, exist_ok=True)
        for filename in (contact_state.CANDIDATE_STATE, contact_state.INPUT_PACK):
            data = json.loads((self.prof_dir / filename).read_text(encoding="utf-8"))
            if filename == contact_state.INPUT_PACK:
                data["professor"] = name
                data["professor_dir"] = str(directory)
            (directory / filename).write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return directory

    def row(self, directory, idea="DIR00001_1", professor=None, direction_ids=None):
        ideas = ([{"id": entry} for entry in idea] if isinstance(idea, (list, tuple))
                 else [{"id": idea}])
        entry = {"professor": professor or directory.name,
                 "professor_dir": str(directory), "collection_key": "DIR00001",
                 "ideas": ideas}
        if direction_ids is not None:
            entry["direction_ids"] = list(direction_ids)
        return entry

    def stage4_process(self, rows, name="sel.json"):
        sel_input = self.root / name
        sel_input.write_text(json.dumps({"selections": rows}, ensure_ascii=False),
                             encoding="utf-8")
        return run_cli("stage4-finalize", "--program-root", self.root,
                       "--selection-input", sel_input)

    def stage4(self, rows, name="sel.json"):
        return parse(self.stage4_process(rows, name))

    def pair(self, directory):
        return (directory / self.SELECT, directory / self.PACK)

    def pair_bytes(self, directory):
        return [path.read_bytes() if path.exists() else None
                for path in self.pair(directory)]

    def assert_no_pair(self, directory, msg=""):
        for path in self.pair(directory):
            self.assertFalse(path.exists(), f"{msg} expected no write: {path}")

    def assert_program_pair_absent(self):
        for filename in (self.SELECT, self.PACK):
            self.assertFalse((self.research / filename).exists(),
                             f"program-level Stage-4 authority must stay unwritten: {filename}")

    def inject_install_fault(self, directory, filename):
        """Fail os.replace() for one target file inside the runner subprocess."""
        self.faultsite.mkdir(parents=True, exist_ok=True)
        (self.faultsite / "sitecustomize.py").write_text(
            ISSUE67_FAULT_SITECUSTOMIZE, encoding="utf-8")
        saved = {key: os.environ.get(key) for key in
                 ("PYTHONPATH", "PC67_FAULT_DIR", "PC67_FAULT_NAME", "PC67_FAULT_TIMES")}

        def restore():
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.addCleanup(restore)
        os.environ["PYTHONPATH"] = str(self.faultsite)
        os.environ["PC67_FAULT_DIR"] = str(Path(directory).resolve())
        os.environ["PC67_FAULT_NAME"] = filename

    def clear_install_fault(self):
        """Let the next (fresh retry) run write normally again."""
        for key in ("PYTHONPATH", "PC67_FAULT_DIR", "PC67_FAULT_NAME"):
            os.environ.pop(key, None)

    def write_legacy_program_pair(self, selections, emails):
        """Drop a legacy schema-2 program-level pair in as history only."""
        legacy_selection = self.research / self.SELECT
        legacy_selection.write_text(json.dumps(
            {"schema": contact_state.SELECTION_SCHEMA, "kind": contact_state.SELECTION_KIND,
             "managed_by": contact_state.MANAGED_BY, "selections": selections},
            ensure_ascii=False, indent=1), encoding="utf-8")
        legacy_pack = self.research / self.PACK
        legacy_pack.write_text(json.dumps(
            {"schema": contact_state.EMAIL_PACK_SCHEMA, "kind": contact_state.EMAIL_PACK_KIND,
             "managed_by": contact_state.MANAGED_BY, "emails": emails},
            ensure_ascii=False, indent=1), encoding="utf-8")
        return legacy_selection, legacy_pack

    def migrate(self, directory):
        process = run_cli("stage4-migrate-local", "--program-root", self.root,
                          "--professor-dir", directory)
        return parse(process), process


class Issue67ProfessorLocalStage4Tests(_Issue67Stage4Fixture):
    """`PC67-DSTATE`: Stage-4 authority is one professor-local pair per professor_dir.

    Every case drives the public CLI against a program root that carries two
    professors and proves from actual file bytes that an unrelated professor is
    never a prerequisite, that one professor's pair is written atomically or not
    at all, and that the legacy program-level pair neither authorizes nor blocks
    anything (Gate 1 R67-G1-1/2/3/5/9/10/11).
    """

    # ---- R67-G1-1/2/4: one professor's fault is that professor's own -------

    def test_01_valid_professor_commits_while_unrelated_professor_fails_closed(self):
        """A valid + B expected professor-scoped invalid → A commits, B zero-write."""
        prof_b = self.clone_professor("対照 教授")
        out = self.stage4([self.row(self.prof_dir), self.row(prof_b, idea="ghost_idea")],
                          name="b1.json")
        self.assertEqual(out["status"], "partial", out)
        rows = stage4_rows(out)
        self.assertEqual([row["professor"] for row in rows],
                         ["試験 教授", "対照 教授"], out)
        row_a, row_b = rows
        self.assertEqual(row_a["status"], "ok", out)
        self.assertEqual(Path(row_a["selection_file"]).parent, self.prof_dir)
        self.assertEqual(Path(row_a["email_pack"]).parent, self.prof_dir)
        self.assertTrue(Path(row_a["selection_file"]).is_file())
        self.assertTrue(Path(row_a["email_pack"]).is_file())
        selection = json.loads(Path(row_a["selection_file"]).read_text(encoding="utf-8"))
        self.assertEqual(selection["schema"], contact_state.STAGE4_LOCAL_SCHEMA)
        self.assertEqual([s["professor"] for s in selection["selections"]], ["試験 教授"])
        pack = json.loads(Path(row_a["email_pack"]).read_text(encoding="utf-8"))
        self.assertEqual(pack["schema"], contact_state.STAGE4_LOCAL_SCHEMA)
        self.assertEqual([e["email_id"] for e in pack["emails"]],
                         ["試験 教授::DIR00001::DIR00001_1"])
        self.assertEqual(row_b["status"], "error", out)
        self.assertEqual(row_b["reason_code"], "unknown_idea_id")
        self.assertIsNone(row_b["selection_file"])
        self.assertIsNone(row_b["email_pack"])
        self.assert_no_pair(prof_b, "B failed closed")
        self.assert_program_pair_absent()

    def test_02_professor_own_invalid_state_input_or_selection_writes_nothing(self):
        """A's own broken state / input pack / selection fails A with zero write."""
        selection_path, email_path = self.pair(self.prof_dir)
        state_path = self.prof_dir / contact_state.CANDIDATE_STATE
        pack_path = self.prof_dir / contact_state.INPUT_PACK
        original_state = state_path.read_bytes()

        # (a) selection names an idea that does not exist in A's own state.
        out = self.stage4([self.row(self.prof_dir, idea="ghost_idea")], name="b2a.json")
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(stage4_row(out)["reason_code"], "unknown_idea_id")
        self.assert_no_pair(self.prof_dir, "invalid selection")

        # (b) A's candidate state is gone: the row names needs_stage3 and A
        # writes nothing.
        state_path.unlink()
        out = self.stage4([self.row(self.prof_dir)], name="b2b.json")
        self.assertEqual(out["status"], "error", out)
        row = stage4_row(out)
        self.assertEqual(row["reason_code"], "validation_failed")
        self.assertEqual([entry["reason"] for entry in row["skipped"]],
                         ["needs_stage3"], out)
        self.assert_no_pair(self.prof_dir, "missing state")

        # (c) state is back but the input pack is gone: the direction identity
        # cannot be mapped from the missing pack, so A fails closed with no write.
        state_path.write_bytes(original_state)
        pack_path.unlink()
        out = self.stage4([self.row(self.prof_dir)], name="b2c.json")
        self.assertEqual(out["status"], "error", out)
        row = stage4_row(out)
        self.assertEqual(row["reason_code"], "legacy_direction_identity")
        self.assertIsNone(row["selection_file"])
        self.assertIsNone(row["email_pack"])
        self.assert_no_pair(self.prof_dir, "missing input pack")
        self.assert_program_pair_absent()
        self.assertFalse(selection_path.exists())
        self.assertFalse(email_path.exists())

    # ---- R67-G1-3: the pair is one atomic unit ----------------------------

    def test_03_second_file_install_failure_rolls_the_pair_back(self):
        """An install failure on 邮件输入.json must restore 套磁选择.json: one
        professor either has its complete pair or its previous pair."""
        first = self.stage4([self.row(self.prof_dir)], name="b3-first.json")
        row_a = stage4_row(first)
        self.assertEqual(row_a["status"], "ok", first)
        before = self.pair_bytes(self.prof_dir)

        self.inject_install_fault(self.prof_dir, self.PACK)
        process = self.stage4_process(
            [self.row(self.prof_dir, idea=["DIR00001_1", "DIR00001_2"])],
            name="b3-second.json")
        self.assertNotEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout.strip(), "",
                         "an unexpected fault must not print an aggregate success")
        self.assertEqual(self.pair_bytes(self.prof_dir), before,
                         "the pair must roll back to its previous bytes")
        self.assert_program_pair_absent()

    def test_04_half_present_local_pair_fails_closed_without_minting_the_other_half(self):
        """Only 套磁选择.json on disk is a corrupt authority: fail closed, keep the
        bytes, never generate the missing counterpart."""
        selection_path = self.prof_dir / self.SELECT
        sentinel = b'{"schema": 3, "selections": []}\n'
        selection_path.write_bytes(sentinel)
        out = self.stage4([self.row(self.prof_dir)], name="b4.json")
        self.assertEqual(out["status"], "error", out)
        row = stage4_row(out)
        self.assertEqual(row["reason_code"], "local_pair_incomplete")
        self.assertIsNone(row["selection_file"])
        self.assertIsNone(row["email_pack"])
        self.assertEqual(selection_path.read_bytes(), sentinel)
        self.assertFalse((self.prof_dir / self.PACK).exists())
        self.assert_program_pair_absent()

    def test_05_local_selection_row_for_another_professor_fails_closed(self):
        """A professor-local container may not hold a foreign row: this professor
        fails closed and its own bytes stay untouched."""
        first = self.stage4([self.row(self.prof_dir)], name="b5-first.json")
        before = self.pair_bytes(self.prof_dir)
        selection_path = self.prof_dir / self.SELECT
        foreign = json.loads(selection_path.read_text(encoding="utf-8"))
        foreign["selections"][0]["professor_dir"] = str(self.research / "Z分野" / "别家 教授")
        selection_path.write_text(json.dumps(foreign, ensure_ascii=False), encoding="utf-8")
        foreign_bytes = selection_path.read_bytes()
        out = self.stage4([self.row(self.prof_dir)], name="b5.json")
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(stage4_row(out)["reason_code"], "local_selection_foreign_row")
        self.assertEqual(selection_path.read_bytes(), foreign_bytes,
                         "the corrupt local selection must not be rewritten")
        self.assertEqual((self.prof_dir / self.PACK).read_bytes(), before[1])
        self.assert_program_pair_absent()

    # ---- R67-G1-9: canonical professor_dir, not the display name ----------

    def test_06_same_display_name_two_directories_keep_two_local_states(self):
        """Two canonical directories that display the same professor name own two
        independent pairs; neither row is the other's prerequisite."""
        twin = self.clone_professor("試験 教授", field="Z分野")
        out = self.stage4([self.row(self.prof_dir), self.row(twin)], name="b6.json")
        self.assertEqual(out["status"], "ok", out)
        rows = {row["professor_dir"]: row for row in stage4_rows(out)}
        self.assertEqual(sorted(Path(key).name for key in rows),
                         ["試験 教授", "試験 教授"], out)
        for directory in (self.prof_dir, twin):
            row = rows[str(directory)]
            self.assertEqual(row["status"], "ok", out)
            self.assertEqual(row["professor"], "試験 教授")
            pack = json.loads(Path(row["email_pack"]).read_text(encoding="utf-8"))
            self.assertEqual(len(pack["emails"]), 1, pack)
            self.assertEqual(pack["professor_dir"], str(directory))
            self.assertEqual(Path(row["selection_file"]).parent, directory)
        self.assertEqual(len(list(self.research.rglob(self.SELECT))), 2)
        self.assert_program_pair_absent()

    def test_07_professor_dir_outside_the_program_writes_nothing_anywhere(self):
        """An out-of-root professor_dir fails that professor only: zero local and
        zero external write, and the other professor still commits."""
        escaped = self.outside / "越境 教授"
        escaped.mkdir(parents=True)
        for filename in (contact_state.CANDIDATE_STATE, contact_state.INPUT_PACK):
            shutil.copy2(self.prof_dir / filename, escaped / filename)
        out = self.stage4([self.row(self.prof_dir), self.row(escaped)], name="b7.json")
        self.assertEqual(out["status"], "partial", out)
        rows = stage4_rows(out)
        self.assertEqual(rows[0]["status"], "ok", out)
        self.assertEqual(rows[1]["status"], "error", out)
        self.assertEqual(rows[1]["reason_code"], "invalid_professor_dir")
        self.assertIsNone(rows[1]["selection_file"])
        self.assertIsNone(rows[1]["email_pack"])
        self.assert_no_pair(escaped, "out-of-root professor")
        self.assertEqual(sorted(path.name for path in escaped.iterdir()),
                         sorted([contact_state.CANDIDATE_STATE, contact_state.INPUT_PACK]),
                         "the out-of-root directory must not gain any file")
        self.assert_program_pair_absent()

    # ---- R67-G1-5/11: legacy program-level pair is history, not authority --

    def test_08_scoped_migration_recompiles_current_facts_and_skips_foreign_legacy(self):
        """Migrating A reads only A's legacy rows and rebuilds the local email
        facts from current Stage-3 state; B's stale legacy row is neither copied
        nor a prerequisite."""
        prof_b = self.clone_professor("対照 教授")
        gap = quote_id(self.gap_quotes["AAAA1111"])
        legacy_selection, legacy_pack = self.write_legacy_program_pair(
            [{"professor": "試験 教授", "professor_dir": str(self.prof_dir),
              "direction_ids": ["DIR00001"], "ideas": [{"id": "DIR00001_1"}]},
             {"professor": "対照 教授",
              "professor_dir": str(self.research / "Q分野" / "早已消失 教授"),
              "direction_ids": ["DIR00001"], "ideas": [{"id": "ghost_idea"}]}],
            [{"email_id": "試験 教授::DIR00001::DIR00001_1",
              "professor": "試験 教授",
              "idea": {"id": "DIR00001_1", "title": "LEGACY-ONLY-TITLE"},
              "gaps": [{"gap_id": "0" * 64, "status": "closed"}]}])
        legacy_before = (legacy_selection.read_bytes(), legacy_pack.read_bytes())

        out, process = self.migrate(self.prof_dir)
        self.assertEqual(out["status"], "migrated", out)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(out["professor_dir"], str(self.prof_dir))
        self.assertEqual(out["migrated_rows"], 1, out)
        pack_text = Path(out["email_pack"]).read_text(encoding="utf-8")
        pack = json.loads(pack_text)
        self.assertEqual(pack["schema"], contact_state.STAGE4_LOCAL_SCHEMA)
        self.assertEqual(pack["emails"][0]["idea"]["title"], "第二种输入模式的合成比较")
        self.assertEqual([entry["gap_id"] for entry in pack["emails"][0]["gaps"]], [gap])
        self.assertNotIn("LEGACY-ONLY-TITLE", pack_text)
        self.assertNotIn("0" * 64, pack_text)

        # B's legacy row points at a directory that is not B: nothing to migrate,
        # and B's own facts stay untouched until an explicit finalize.
        out_b, process_b = self.migrate(prof_b)
        self.assertEqual(out_b["status"], "not_applicable", out_b)
        self.assertEqual(process_b.returncode, 0, process_b.stderr)
        self.assert_no_pair(prof_b, "foreign legacy row")
        self.assertEqual((legacy_selection.read_bytes(), legacy_pack.read_bytes()),
                         legacy_before, "legacy bytes must never be modified")

    def test_09_legacy_rows_for_another_professor_never_block_explicit_finalize(self):
        """Only B has legacy rows: A's explicit legal finalize still commits, and
        B's history is not smuggled into A's local pair."""
        prof_b = self.clone_professor("対照 教授")
        legacy_selection, legacy_pack = self.write_legacy_program_pair(
            [{"professor": "対照 教授", "professor_dir": str(prof_b),
              "direction_ids": ["DIR00001"], "ideas": [{"id": "DIR00001_1"}]}],
            [{"email_id": "対照 教授::DIR00001::DIR00001_1",
              "professor": "対照 教授",
              "idea": {"id": "DIR00001_1", "title": "LEGACY-ONLY-TITLE"}}])
        legacy_before = (legacy_selection.read_bytes(), legacy_pack.read_bytes())
        out = self.stage4([self.row(self.prof_dir)], name="b9.json")
        self.assertEqual(out["status"], "ok", out)
        row = stage4_row(out)
        self.assertEqual(row["status"], "ok", out)
        pack_text = Path(row["email_pack"]).read_text(encoding="utf-8")
        self.assertEqual([e["email_id"] for e in json.loads(pack_text)["emails"]],
                         ["試験 教授::DIR00001::DIR00001_1"])
        self.assertNotIn("対照 教授", pack_text)
        self.assertNotIn("LEGACY-ONLY-TITLE", pack_text)
        self.assert_no_pair(prof_b, "B was only history")
        self.assertEqual((legacy_selection.read_bytes(), legacy_pack.read_bytes()),
                         legacy_before)

    def test_10_complete_local_pair_outranks_conflicting_legacy_rows(self):
        """A committed local pair is the only authority: a conflicting legacy
        global pair is neither read nor rewritten, and migration preserves it."""
        first = self.stage4([self.row(self.prof_dir)], name="b10-first.json")
        row = stage4_row(first)
        self.assertEqual(row["status"], "ok", first)
        legacy_selection, legacy_pack = self.write_legacy_program_pair(
            [{"professor": "試験 教授", "professor_dir": str(self.prof_dir),
              "direction_ids": ["DIR00001"], "ideas": [{"id": "ghost_idea"}]}],
            [{"email_id": "試験 教授::DIR00001::ghost_idea",
              "professor": "試験 教授", "idea": {"id": "ghost_idea",
                                                 "title": "LEGACY-ONLY-TITLE"}}])
        legacy_before = (legacy_selection.read_bytes(), legacy_pack.read_bytes())

        out = self.stage4([self.row(self.prof_dir)], name="b10.json")
        self.assertEqual(stage4_row(out)["status"], "ok", out)
        pack_text = Path(stage4_row(out)["email_pack"]).read_text(encoding="utf-8")
        self.assertNotIn("ghost_idea", pack_text)
        self.assertNotIn("LEGACY-ONLY-TITLE", pack_text)
        self.assertIn("DIR00001_1", pack_text)
        # The legacy email row is history: the rebuilt local pack still carries
        # exactly the one current-facts email, not the legacy idea's entry.
        self.assertEqual([e["email_id"] for e in json.loads(pack_text)["emails"]],
                         ["試験 教授::DIR00001::DIR00001_1"])

        # The deterministic migration sees a complete pair and preserves it
        # byte-for-byte instead of re-deriving it from the legacy rows.
        before = self.pair_bytes(self.prof_dir)
        migrated, process = self.migrate(self.prof_dir)
        self.assertEqual(migrated["status"], "already_local", migrated)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(self.pair_bytes(self.prof_dir), before)
        self.assertEqual((legacy_selection.read_bytes(), legacy_pack.read_bytes()),
                         legacy_before)

    def test_11_legacy_row_that_matches_surface_but_not_current_facts_writes_no_pair(self):
        """A legacy row scoped to this professor whose idea no longer exists in
        the current candidate state must fail closed with no local pair."""
        legacy_selection, legacy_pack = self.write_legacy_program_pair(
            [{"professor": "試験 教授", "professor_dir": str(self.prof_dir),
              "direction_ids": ["DIR00001"], "ideas": [{"id": "DIR00001_9"}]}],
            [{"email_id": "試験 教授::DIR00001::DIR00001_9", "professor": "試験 教授",
              "idea": {"id": "DIR00001_9", "title": "LEGACY-ONLY-TITLE"}}])
        legacy_before = (legacy_selection.read_bytes(), legacy_pack.read_bytes())
        out, process = self.migrate(self.prof_dir)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "unknown_idea_id")
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertIsNone(out["selection_file"])
        self.assertIsNone(out["email_pack"])
        self.assert_no_pair(self.prof_dir, "uncompilable legacy row")
        self.assertEqual((legacy_selection.read_bytes(), legacy_pack.read_bytes()),
                         legacy_before)

    def test_12_fatal_after_a_commit_keeps_a_and_fresh_retry_uses_current_facts(self):
        """Unexpected fatal inside B's pair write: A keeps its committed bytes, B
        rolls back, the program-level pair gains no authority — and a fresh retry
        re-enters from A's local authority plus B's CURRENT facts."""
        prof_b = self.clone_professor("対照 教授")
        legacy_selection, legacy_pack = self.write_legacy_program_pair(
            [{"professor": "試験 教授", "professor_dir": str(self.prof_dir),
              "direction_ids": ["DIR00001"], "ideas": [{"id": "ghost_idea"}]},
             {"professor": "対照 教授", "professor_dir": str(prof_b),
              "direction_ids": ["DIR00001"], "ideas": [{"id": "ghost_idea"}]}],
            [{"email_id": "試験 教授::DIR00001::ghost_idea", "professor": "試験 教授",
              "idea": {"id": "ghost_idea", "title": "LEGACY-ONLY-TITLE"}}])
        legacy_before = (legacy_selection.read_bytes(), legacy_pack.read_bytes())

        self.inject_install_fault(prof_b, self.PACK)
        process = self.stage4_process([self.row(self.prof_dir), self.row(prof_b)],
                                      name="b12-first.json")
        self.clear_install_fault()
        self.assertEqual(process.stdout.strip(), "",
                         "a fatal run must not print an aggregate success")
        self.assertNotEqual(process.returncode, 0, process.stderr)
        pair_a = self.pair(self.prof_dir)
        self.assertTrue(all(path.is_file() for path in pair_a),
                        "professor A's committed pair stays authority")
        committed_a = [path.read_bytes() for path in pair_a]
        self.assert_no_pair(prof_b, "fatal professor rolled back")
        self.assertEqual((legacy_selection.read_bytes(), legacy_pack.read_bytes()),
                         legacy_before, "the legacy global pair gains no authority")

        # Fresh retry: B's own current facts changed while the process was down.
        state_path = prof_b / contact_state.CANDIDATE_STATE
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["directions"][0]["candidates"][0]["title"] = "重跑后的当前事实"
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        out = self.stage4([self.row(prof_b)], name="b12-retry.json")
        self.assertEqual(out["status"], "ok", out)
        row_b = stage4_row(out)
        self.assertEqual(row_b["status"], "ok", out)
        pack_text = Path(row_b["email_pack"]).read_text(encoding="utf-8")
        self.assertIn("重跑后的当前事实", pack_text)
        self.assertNotIn("ghost_idea", pack_text)
        self.assertNotIn("LEGACY-ONLY-TITLE", pack_text)

        # A is untouched by the retry and the legacy bytes never moved.
        self.assertEqual([path.read_bytes() for path in pair_a], committed_a)
        self.assertEqual((legacy_selection.read_bytes(), legacy_pack.read_bytes()),
                         legacy_before)


class Issue67AdjacentStateTests(_Issue67Stage4Fixture):
    """`PC67-DADJ`: Stage-4 authority moved without moving its neighbours.

    Proves the four adjacency boundaries issue #67 had to leave intact: Stage-3
    selected refresh reads the professor-local selection, a mixed Stage-4 result
    hands off only the successful professor's pack, the #59 ``email_id`` stays
    independent of ``professor_dir``, and no #68 Stage-5 batch surface appeared.
    """

    def stage5(self, *arguments):
        template, _ = stage5_templates(self.root)
        return parse(raw_cli("stage5-plan", "--program-root", self.root,
                             "--template", template, *arguments))

    def add_direction_b(self):
        """Give this professor a second ready direction (DIR00002)."""
        results = self.add_second_direction()
        out = parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--results", results, "--program-root", self.root,
            "--collection-key", "DIR00002"))
        self.assertEqual(out["status"], "ok", out)

    def make_state_stale(self):
        """Every recorded direction fingerprint differs from the input pack."""
        path = self.prof_dir / contact_state.CANDIDATE_STATE
        state = json.loads(path.read_text(encoding="utf-8"))
        state["input_fingerprints"] = {did: "stale-fingerprint"
                                       for did in state["input_fingerprints"]}
        path.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    def job_directions(self, payload):
        return sorted({job["direction_id"] for job in payload["jobs"]})

    # ---- R67-G1-6: the selected refresh scope is the local selection -------

    def test_01_stage3_selected_refresh_scopes_from_the_professor_local_selection(self):
        self.add_direction_b()
        committed = self.stage4([self.row(self.prof_dir)], name="adj1.json")
        self.assertEqual(stage4_row(committed)["status"], "ok", committed)
        selection_file = Path(stage4_row(committed)["selection_file"])
        self.assertEqual(selection_file, self.prof_dir / self.SELECT)
        self.make_state_stale()

        scoped = parse(run_cli(
            "stage3-plan", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--refresh-scope", "selected",
            "--selection", selection_file))
        self.assertEqual(scoped["status"], "ok", scoped)
        self.assertEqual(self.job_directions(scoped), ["DIR00001"], scoped)

        # The same invocation over the whole pack proves the scope really came
        # from the selection file and not from a coincidence of staleness.
        everything = parse(run_cli(
            "stage3-plan", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--refresh-scope", "all"))
        self.assertEqual(self.job_directions(everything), ["DIR00001", "DIR00002"])

    def test_02_selected_refresh_needs_an_explicit_selection_and_ignores_legacy(self):
        self.add_direction_b()
        # Without any selection container the scope cannot be invented: the run
        # fails closed instead of silently refreshing every direction.
        missing = run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                          "--program-root", self.root, "--refresh-scope", "selected")
        self.assertEqual(missing.returncode, 1, missing.stdout)
        payload = parse(missing)
        self.assertEqual(payload["reason_code"], "invalid_params")
        self.assertIn("selection file unreadable", payload["message"])

        committed = self.stage4([self.row(self.prof_dir)], name="adj2.json")
        self.assertEqual(stage4_row(committed)["status"], "ok", committed)
        # A legacy global file that names the OTHER direction must not widen the
        # local scope: the professor-local pair is the selection authority.
        self.write_legacy_program_pair(
            [{"professor": "試験 教授", "professor_dir": str(self.prof_dir),
              "collection_key": "DIR00002", "ideas": [{"id": "DIR00002_1"}]}], [])
        self.make_state_stale()
        scoped = parse(run_cli(
            "stage3-plan", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--refresh-scope", "selected",
            "--selection", self.prof_dir / self.SELECT))
        self.assertEqual(self.job_directions(scoped), ["DIR00001"], scoped)

    def test_03_scoped_finalize_with_the_local_selection_keeps_other_directions(self):
        self.add_direction_b()
        committed = self.stage4([self.row(self.prof_dir)], name="adj3.json")
        self.assertEqual(stage4_row(committed)["status"], "ok", committed)
        self.make_state_stale()
        state_path = self.prof_dir / contact_state.CANDIDATE_STATE
        before = json.loads(state_path.read_text(encoding="utf-8"))

        plan = parse(run_cli(
            "stage3-plan", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--refresh-scope", "selected",
            "--selection", self.prof_dir / self.SELECT))
        self.assertEqual(self.job_directions(plan), ["DIR00001"])
        results = self.root / "adj3-results"
        results.mkdir(parents=True, exist_ok=True)
        source = self.root / "s3results" / result_file("candidates", "DIR00001")
        (results / result_file("candidates", "DIR00001")).write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8")
        out = parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir,
            "--results", results, "--program-root", self.root,
            "--refresh-scope", "selected", "--selection", self.prof_dir / self.SELECT))
        self.assertEqual(out["status"], "ok", out)
        after = json.loads(state_path.read_text(encoding="utf-8"))
        recorded = {d["direction_id"]: d for d in after["directions"]}
        self.assertEqual(sorted(recorded), ["DIR00001", "DIR00002"])
        self.assertEqual(recorded["DIR00002"],
                         {d["direction_id"]: d for d in before["directions"]}["DIR00002"],
                         "the scoped-out direction keeps its recorded candidates")
        # Stage 4's professor-local authority is untouched by the Stage-3 refresh.
        self.assertEqual([s["direction_ids"] for s in json.loads(
            (self.prof_dir / self.SELECT).read_text(encoding="utf-8"))["selections"]],
                         [["DIR00001"]])

    # ---- R67-G1-4/7: handoff follows the professor rows --------------------

    def test_04_mixed_result_hands_off_only_the_successfully_committed_pack(self):
        prof_b = self.clone_professor("対照 教授")
        out = self.stage4([self.row(self.prof_dir), self.row(prof_b, idea="ghost_idea")],
                          name="adj4.json")
        self.assertEqual(out["status"], "partial", out)
        row_a, row_b = stage4_rows(out)
        self.assertEqual(row_a["status"], "ok")
        self.assertIsNone(row_b["email_pack"])
        self.assert_program_pair_absent()

        # Stage 4 committed no pack for B and never writes the program-level file,
        # so a Stage-5 run only works when the caller passes the exact local pack
        # it received from results[].
        default = self.stage5()
        self.assertEqual(default["status"], "needs_refresh", default)
        self.assertEqual(default["reason_code"], "missing_email_pack")
        handed_off = self.stage5("--email-pack", row_a["email_pack"])
        self.assertEqual(handed_off["status"], "ok", handed_off)
        self.assertNotEqual(handed_off.get("reason_code"), "missing_email_pack")

    def test_05_fatal_run_without_aggregate_success_gives_the_caller_nothing(self):
        prof_b = self.clone_professor("対照 教授")
        self.inject_install_fault(prof_b, self.PACK)
        process = self.stage4_process([self.row(self.prof_dir), self.row(prof_b)],
                                      name="adj5.json")
        self.assertNotEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout.strip(), "")
        self.assert_no_pair(prof_b, "fatal professor rolled back")
        # Nothing was handable off: no aggregate JSON and no pack for B.
        self.assertEqual(list(prof_b.glob(self.PACK)), [])

    # ---- R67-G1-8: #59 email identity is untouched by professor_dir --------

    def test_06_email_id_stays_the_three_part_identity_regardless_of_directory(self):
        twin = self.clone_professor("試験 教授", field="Z分野")
        out = self.stage4([self.row(self.prof_dir), self.row(twin)], name="adj6.json")
        self.assertEqual(out["status"], "ok", out)
        rows = stage4_rows(out)
        self.assertEqual(len(rows), 2, out)
        expected = "試験 教授::DIR00001::DIR00001_1"
        for row in rows:
            pack = json.loads(Path(row["email_pack"]).read_text(encoding="utf-8"))
            self.assertEqual([entry["email_id"] for entry in pack["emails"]], [expected])
            self.assertEqual(Path(row["email_pack"]).parent.name, row["professor"])
        self.assertEqual({Path(row["email_pack"]) for row in rows},
                         {self.prof_dir / self.PACK, twin / self.PACK})

        # --email-id resolves inside the pack the caller handed over, not globally.
        for row in rows:
            planned = self.stage5("--email-pack", row["email_pack"],
                                  "--email-id", expected)
            self.assertEqual(planned["status"], "ok", planned)
            self.assertEqual([job["result_schema"]["email_id"] for job in planned["jobs"]],
                             [expected], planned)

    # ---- #48/#68 out of scope: no new writer lock or Stage-5 batch surface --

    def test_07_no_stage5_batch_or_email_fanout_surface_was_added(self):
        parser = contact_state.build_parser()
        sub = next(action for action in parser._actions
                   if isinstance(action, argparse._SubParsersAction))
        commands = sorted(sub.choices)
        self.assertIn("stage4-migrate-local", commands)
        self.assertEqual([name for name in commands if "batch" in name], [],
                         "issue #68 stage-5 batch is not part of issue #67")
        stage4_options = {option for action in sub.choices["stage4-finalize"]._actions
                          for option in action.option_strings}
        self.assertEqual(stage4_options - {"-h", "--help"},
                         {"--program-root", "--selection-input", "--profile"},
                         "stage4-finalize stays one aggregate call, never per-email")
        for name in ("stage5-plan", "stage5-finalize"):
            options = {option for action in sub.choices[name]._actions
                       for option in action.option_strings}
            self.assertIn("--email-pack", options, name)
            self.assertIn("--email-id", options, name)
            self.assertNotIn("--professor-dir", options, name)

    def test_08_cross_selection_scope_refreshes_every_participating_direction(self):
        """A cross-direction local row scopes BOTH participants into the refresh.

        The row's single `collection_key` only maps to the primary direction, so
        the selected scope has to be read from the canonical `direction_ids`.
        """
        self.add_direction_b()
        groups = json.dumps([["DIR00001", "DIR00002"]])
        plan = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root,
                             "--cross-direction-groups", groups))
        self.assertEqual(plan["status"], "ok", plan)
        cross_job = next(job for job in plan["jobs"] if job["kind"] == "cross_direction")
        gaps = cross_job["model_input"]["gaps"]
        cited = [{"direction_id": "DIR00001", "item_key": gaps[0]["item_key"],
                  "gap_id": gaps[0]["gap_id"]},
                 {"direction_id": "DIR00002", "item_key": gaps[1]["item_key"],
                  "gap_id": gaps[1]["gap_id"]}]
        papers = [{"item_key": paper["item_key"], "direction_ids": ["DIR00001", "DIR00002"],
                   "role": "共同基座", "fit_note": "共享论文"}
                  for paper in cross_job["model_input"]["papers"][:1]]
        results = self.root / "adj8-cross"
        results.mkdir(parents=True, exist_ok=True)
        (results / cross_job["result_file"]).write_text(json.dumps(
            {"schema": 2, "kind": "cross_candidates",
             "group_id": cross_job["group_id"],
             "direction_ids": ["DIR00001", "DIR00002"],
             "candidates": [{
                 "id": "CROSS_1", "kind": "cross_direction",
                 "direction_ids": ["DIR00001", "DIR00002"], "origin": "generated",
                 "title": "两种输入模式共用同一约束", "one_liner": "同一约束跨两个方向",
                 "research_question": "同一约束能否同时服务两个方向",
                 "points": [], "gap_refs": cited, "anchor_notes": {}, "papers": papers,
                 "fit": "null", "red_lines": []}]},
            ensure_ascii=False), encoding="utf-8")
        finalized = parse(run_cli(
            "stage3-finalize", "--professor-dir", self.prof_dir, "--results", results,
            "--program-root", self.root, "--cross-direction-groups", groups))
        self.assertEqual(finalized["status"], "ok", finalized)

        committed = self.stage4([self.row(self.prof_dir, idea="CROSS_1",
                                         direction_ids=["DIR00001", "DIR00002"])],
                                name="adj8.json")
        self.assertEqual(stage4_row(committed)["status"], "ok", committed)
        row = json.loads((self.prof_dir / self.SELECT).read_text(
            encoding="utf-8"))["selections"][0]
        self.assertEqual(row["direction_ids"], ["DIR00001", "DIR00002"])
        self.assertEqual(row["collection_key"], "DIR00001")

        self.make_state_stale()
        scoped = parse(run_cli(
            "stage3-plan", "--professor-dir", self.prof_dir,
            "--program-root", self.root, "--refresh-scope", "selected",
            "--selection", self.prof_dir / self.SELECT))
        self.assertEqual(self.job_directions(scoped), ["DIR00001", "DIR00002"], scoped)


class Issue67SameProfessorFailClosedTests(_Issue67Stage4Fixture):
    """R67-G1-3: inside ONE professor, any entry failure fails the whole batch.

    A professor whose own selection batch carries an entry that cannot be
    resolved against its current facts (invalid direction identity) must fail
    with zero writes -- never a partial commit of the valid remainder. A
    professor-local prior selection that contains a non-object entry is a
    corrupt authority: re-submission must fail closed without rewriting the
    pair, never silently drop the entry.
    """

    def test_01_invalid_direction_entry_fails_the_whole_professor(self):
        """DIR00001 (valid) + DIR99999 (absent from pack) -> error, zero write."""
        out = self.stage4([
            self.row(self.prof_dir, direction_ids=["DIR00001"]),
            self.row(self.prof_dir, direction_ids=["DIR99999"], idea="ghost"),
        ], name="fc1.json")
        self.assertEqual(out["status"], "error", out)
        row = stage4_row(out)
        self.assertEqual(row["reason_code"], "validation_failed", out)
        self.assertIn(
            {"detail": "direction not in state/pack", "direction_ids": ["DIR99999"],
             "professor": "試験 教授", "reason": "needs_refresh"},
            row["skipped"], out)
        self.assert_no_pair(self.prof_dir, "invalid direction entry")
        self.assert_program_pair_absent()

    def test_02_prior_selection_non_object_entry_fails_closed(self):
        """A null entry in the professor-local prior selection stops the commit."""
        first = self.stage4([self.row(self.prof_dir, idea=["DIR00001_1", "DIR00001_2"])],
                            name="fc2-first.json")
        self.assertEqual(stage4_row(first)["status"], "ok", first)
        selection_path = self.prof_dir / self.SELECT
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        selection["selections"] = [None] + selection["selections"]
        selection_path.write_text(json.dumps(selection, ensure_ascii=False, indent=1) + "\n",
                                  encoding="utf-8")
        corrupted = (selection_path.read_bytes(), (self.prof_dir / self.PACK).read_bytes())

        out = self.stage4([self.row(self.prof_dir, idea="DIR00001_1")], name="fc2.json")
        self.assertEqual(out["status"], "error", out)
        row = stage4_row(out)
        self.assertEqual(row["reason_code"], "invalid_selection", out)
        self.assertIsNone(row["selection_file"], out)
        self.assertIsNone(row["email_pack"], out)
        self.assertEqual((selection_path.read_bytes(), (self.prof_dir / self.PACK).read_bytes()),
                         corrupted, "the corrupt prior selection must not be rewritten")
        self.assert_program_pair_absent()


if __name__ == "__main__":
    unittest.main(verbosity=2)
