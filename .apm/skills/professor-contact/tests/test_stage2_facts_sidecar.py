import hashlib
import json
import subprocess
import sys
import tempfile
import re
import unicodedata
import unittest
from pathlib import Path

from stage2_test_support import run_bound_stage2_plan

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"


def quote_id(quote: str) -> str:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", quote)).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def run_cli(*arguments):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
                          text=True, capture_output=True, check=False)


def parse(result):
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"stdout not JSON: {result.stdout!r}\nstderr: {result.stderr!r}")


def make_sidecar(analysis: Path, quotes: list, page: int = 8, *,
                 analysis_binding: str | None = None) -> Path:
    """Write a future-work sidecar in the canonical paper-analysis form.

    Real `future_work.py finalize` records `"analysis": analysis.name`
    (basename). `analysis_binding` overrides it for legacy/compat cases.
    """
    items = [{"id": quote_id(q), "quote": q, "translation_zh": f"中译：{q[:24]}",
              "source": "Conclusion", "page": page} for q in quotes]
    sidecar = Path(str(analysis) + ".future_work.json")
    sidecar.write_text(json.dumps({
        "schema": 1, "extractor_version": "future-work-v1",
        "analysis": analysis_binding if analysis_binding is not None else analysis.name,
        "status": "ok", "items": items},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return sidecar


def facts_payload(analysis: Path, pdf: Path, quotes: list, *,
                  fingerprint: str | None = None, joined_ids=None) -> dict:
    return {
        "schema": 1,
        "kind": "paper-analysis-facts",
        "generator_version": "facts-v1",
        "analysis": analysis.name,
        "input_fingerprint": fingerprint or ("sha256:" + hashlib.sha256(pdf.read_bytes()).hexdigest()),
        "evidence_level": "fulltext",
        "status": "ok",
        "paper": {"title": "Synthetic comparison of input patterns",
                  "authors": ["Author One", "Example Professor"], "year": 2023,
                  "venue": "Synthetic Venue", "doi": None},
        "research_problem": "How to compare synthetic input patterns reliably.",
        "research_object": "Synthetic comparison of input patterns.",
        "approach": "A deterministic comparison pipeline.",
        "findings": ["Comparison remains stable across patterns."],
        "contributions": ["A synthetic comparison method."],
        "topic_terms": ["synthetic", "comparison"],
        "limitations": ["Only two input patterns."],
        "source_anchors": {"approach": ["§3 Method"]},
        "confidence": 0.8,
        "future_work_ids": [quote_id(q) for q in quotes] if joined_ids is None else joined_ids,
    }


def make_facts_sidecar(analysis: Path, pdf: Path, quotes: list, **kwargs) -> Path:
    sidecar = Path(str(analysis) + ".facts.json")
    sidecar.write_text(json.dumps(
        facts_payload(analysis, pdf, quotes, **kwargs), ensure_ascii=False, indent=1),
        encoding="utf-8")
    return sidecar


GAP_QUOTES = {
    "AAAA1111": "Future work will extend the synthetic comparison to a second input pattern.",
    "BBBB2222": "We plan to test a second synthetic processing path.",
}


class FactsSidecarTests(unittest.TestCase):
    """Stage 2 consumes paper-analysis facts sidecars as the machine evidence
    source for fulltext paper facts, with fingerprint + exact-join validation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)
        self.pdf = self.root / "paper-AAAA.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nsynthetic full body")
        self.gap_quotes = dict(GAP_QUOTES)
        self.papers = [
            {"item_key": "AAAA1111", "title": "Synthetic comparison of input patterns",
             "year": 2023, "month": 5, "authorship": "corresponding",
             "abstract": "We study a synthetic comparison of input patterns.",
             "has_pdf": True, "authors": ["Author One", "Example Professor"]},
            {"item_key": "BBBB2222", "title": "Synthetic processing path evaluation",
             "year": 2024, "month": 3, "authorship": "first",
             "abstract": "A synthetic system for comparing two processing paths.",
             "has_pdf": False, "authors": ["Example Professor"]},
        ]
        for key, quote in self.gap_quotes.items():
            analysis = self.prof_dir / "论文分析" / f"{key}.md"
            analysis.write_text("# analysis\n", encoding="utf-8")
            sidecar = make_sidecar(analysis, [quote])
            for paper in self.papers:
                if paper["item_key"] == key:
                    paper["analysis_file"] = str(analysis)
                    paper["sidecar_file"] = str(sidecar)
        self.facts_sidecar = make_facts_sidecar(
            self.prof_dir / "论文分析" / "AAAA1111.md", self.pdf, [GAP_QUOTES["AAAA1111"]])
        for paper in self.papers:
            if paper["item_key"] == "AAAA1111":
                paper["facts_file"] = str(self.facts_sidecar)
                paper["pdf_file"] = str(self.pdf)

    def tearDown(self):
        self.temp.cleanup()

    def write_facts(self) -> Path:
        facts = {
            "program_root": str(self.root), "professor_dir": str(self.prof_dir),
            "professor": "試験 教授", "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": self.papers,
            "directions": [{
                "collection_key": "DIR00001", "name_ja": "合成输入比较", "name_zh": "合成输入比较",
                "status": "active",
                "member_keys": ["AAAA1111", "BBBB2222"],
                "relevant_keys": ["AAAA1111", "BBBB2222"],
                "named_keys": ["AAAA1111"],
                "user_note": "我想比较两种合成输入的处理结果。",
                "credibility": {"verdict": "站得住", "mainline": "主线",
                                "authorship_line": "corresponding_dominant", "note": "test"},
                "red_lines": [],
            }],
        }
        path = self.root / "facts.json"
        path.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    def write_stage2_results(self, results: Path):
        results.mkdir(parents=True, exist_ok=True)
        rows = []
        for key, quote in self.gap_quotes.items():
            rows.append({"gap_id": quote_id(quote), "status": "open",
                         "candidate_paper_ids": [], "evidence": f"无更晚论文实现该点（{key}）",
                         "confidence": "high"})
        (results / "freshness-DIR00001.json").write_text(json.dumps({
            "schema": 1, "kind": "freshness", "collection_key": "DIR00001",
            "results": rows}, ensure_ascii=False), encoding="utf-8")
        g1 = quote_id(GAP_QUOTES["AAAA1111"])
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

    def stage2_run(self):
        facts = self.write_facts()
        results = self.root / "results"
        self.write_stage2_results(results)
        plan = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(plan["status"], "ok", plan)
        out = parse(run_cli("stage2-finalize", "--facts", facts, "--results", results))
        self.assertEqual(out["status"], "ok", out)
        return json.loads(
            (self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))

    def supporting(self, pack, item_key):
        """v2: the canonical professor-level paper record (issue #8 §3.3)."""
        return pack["papers"][item_key]

    def test_valid_facts_sidecar_is_normalized_into_the_pack(self):
        # Integration regression: both sidecars use the canonical paper-analysis
        # basename `analysis` binding and the full stage2-plan → stage2-finalize
        # path must reuse the facts sidecar (facts_state == valid).
        pack = self.stage2_run()
        row = self.supporting(pack, "AAAA1111")
        self.assertEqual(row["facts_state"], "valid")
        self.assertIsNone(row["facts_error"])
        paper_facts = row["paper_facts"]
        self.assertIsNotNone(paper_facts)
        self.assertEqual(paper_facts["evidence_level"], "fulltext")
        self.assertEqual(paper_facts["input_fingerprint"],
                         "sha256:" + hashlib.sha256(self.pdf.read_bytes()).hexdigest())
        self.assertEqual(paper_facts["research_problem"],
                         "How to compare synthetic input patterns reliably.")
        self.assertEqual(paper_facts["topic_terms"], ["synthetic", "comparison"])
        # future_work_ids stay exact joins into the authoritative quoted sidecar.
        self.assertEqual(paper_facts["future_work_ids"], [quote_id(GAP_QUOTES["AAAA1111"])])
        # BBBB2222 has an analysis and sidecar but no facts sidecar: honestly unavailable.
        other = self.supporting(pack, "BBBB2222")
        self.assertEqual(other["facts_state"], "unavailable")
        self.assertEqual(other["facts_error"], "missing_facts_sidecar")
        self.assertIsNone(other["paper_facts"])

    def test_legacy_absolute_path_sidecar_still_accepted(self):
        analysis = self.prof_dir / "论文分析" / "AAAA1111.md"
        make_sidecar(analysis, [GAP_QUOTES["AAAA1111"]], analysis_binding=str(analysis))
        pack = self.stage2_run()
        row = self.supporting(pack, "AAAA1111")
        self.assertEqual(row["facts_state"], "valid")
        self.assertIsNotNone(row["paper_facts"])

    def test_sidecar_bound_to_different_analysis_is_rejected(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("contact_state_facts_unit2", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        make_sidecar(self.prof_dir / "论文分析" / "AAAA1111.md",
                     [GAP_QUOTES["AAAA1111"]], analysis_binding="BBBB2222.md")
        ctx = module.Stage2Context(self.write_facts())
        record = ctx.facts_for("AAAA1111")
        self.assertEqual(record, (None, "failed", "facts_future_work_join_mismatch"))

    def test_facts_sidecar_bound_to_different_analysis_is_rejected(self):
        payload = json.loads(self.facts_sidecar.read_text(encoding="utf-8"))
        payload["analysis"] = "OTHER.md"
        self.facts_sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
        pack = self.stage2_run()
        row = self.supporting(pack, "AAAA1111")
        self.assertEqual(row["facts_state"], "failed")
        self.assertEqual(row["facts_error"], "invalid_facts_sidecar")
        self.assertIsNone(row["paper_facts"])

    def _same_basename_setup(self, *, misdirect_sidecar_for=None, misdirect_facts_for=None):
        """Two same-basename analyses in different author directories.

        Both canonical sidecars legitimately record `analysis: "T.md"`, so only
        the physical sibling location tells them apart.
        """
        quote_a = GAP_QUOTES["AAAA1111"]
        quote_b = GAP_QUOTES["BBBB2222"]
        analysis_a = self.prof_dir / "论文分析" / "A" / "T.md"
        analysis_b = self.prof_dir / "论文分析" / "B" / "T.md"
        for analysis in (analysis_a, analysis_b):
            analysis.parent.mkdir(parents=True, exist_ok=True)
            analysis.write_text("# analysis\n", encoding="utf-8")
        sidecar_a = make_sidecar(analysis_a, [quote_a])
        sidecar_b = make_sidecar(analysis_b, [quote_b])
        pdf_a = self.root / "paper-A.pdf"
        pdf_a.write_bytes(b"%PDF-1.4\npaper A")
        pdf_b = self.root / "paper-B.pdf"
        pdf_b.write_bytes(b"%PDF-1.4\npaper B")
        facts_a = make_facts_sidecar(analysis_a, pdf_a, [quote_a])
        facts_b = make_facts_sidecar(analysis_b, pdf_b, [quote_b])
        # With a misdirected sidecar the victim loses its gap, so only the
        # healthy paper's gap is judged in the stage2 results.
        if misdirect_sidecar_for:
            self.gap_quotes = {"AAAA1111": quote_a}
        else:
            self.gap_quotes = {"AAAA1111": quote_a, "BBBB2222": quote_b}
        self.papers = [
            {"item_key": "AAAA1111", "title": "Same synthetic title",
             "year": 2023, "month": 5, "authorship": "corresponding",
             "abstract": "Abstract A.", "has_pdf": True,
             "authors": ["Example Professor"],
             "analysis_file": str(analysis_a),
             "sidecar_file": str(sidecar_a),
             "facts_file": str(facts_b if misdirect_facts_for == "AAAA1111" else facts_a),
             "pdf_file": str(pdf_a)},
            {"item_key": "BBBB2222", "title": "Same synthetic title",
             "year": 2024, "month": 3, "authorship": "first",
             "abstract": "Abstract B.", "has_pdf": True,
             "authors": ["Example Professor"],
             "analysis_file": str(analysis_b),
             "sidecar_file": str(sidecar_a if misdirect_sidecar_for == "BBBB2222" else sidecar_b),
             "facts_file": str(facts_b),
             "pdf_file": str(pdf_b)},
        ]

    def test_same_basename_sidecar_from_wrong_directory_is_rejected(self):
        # B's sidecar_file is mis-assembled to point at A's sidecar; both
        # canonical sidecars say analysis="T.md", so only the exact sibling
        # binding can keep A's future-work evidence from leaking into B.
        self._same_basename_setup(misdirect_sidecar_for="BBBB2222")
        pack = self.stage2_run()
        shortlist = pack["directions"][0]["gap_shortlist"]
        self.assertEqual(len(shortlist), 1)
        self.assertEqual(shortlist[0]["item_key"], "AAAA1111")
        self.assertEqual(shortlist[0]["gap_id"], quote_id(GAP_QUOTES["AAAA1111"]))
        row_b = self.supporting(pack, "BBBB2222")
        self.assertEqual(row_b["facts_state"], "failed")
        self.assertEqual(row_b["facts_error"], "facts_future_work_join_mismatch")
        self.assertIsNone(row_b["paper_facts"])
        row_a = self.supporting(pack, "AAAA1111")
        self.assertEqual(row_a["facts_state"], "valid")

    def test_facts_sidecar_from_wrong_directory_is_rejected(self):
        # A's facts_file points at B's facts sidecar: same basename, valid JSON,
        # but the wrong physical sibling — the facts record must fail closed.
        self._same_basename_setup(misdirect_facts_for="AAAA1111")
        pack = self.stage2_run()
        row_a = self.supporting(pack, "AAAA1111")
        self.assertEqual(row_a["facts_state"], "failed")
        self.assertEqual(row_a["facts_error"], "invalid_facts_sidecar")
        self.assertIsNone(row_a["paper_facts"])
        row_b = self.supporting(pack, "BBBB2222")
        self.assertEqual(row_b["facts_state"], "valid")
        self.assertIsNotNone(row_b["paper_facts"])

    def test_source_fingerprint_mismatch_fails_closed(self):
        stale = make_facts_sidecar(
            self.prof_dir / "论文分析" / "AAAA1111.md", self.pdf,
            [GAP_QUOTES["AAAA1111"]], fingerprint="sha256:" + "0" * 64)
        self.assertTrue(stale.is_file())
        pack = self.stage2_run()
        row = self.supporting(pack, "AAAA1111")
        self.assertEqual(row["facts_state"], "failed")
        self.assertEqual(row["facts_error"], "facts_source_fingerprint_mismatch")
        self.assertIsNone(row["paper_facts"])

    def test_missing_current_pdf_fails_closed(self):
        for paper in self.papers:
            if paper["item_key"] == "AAAA1111":
                paper["pdf_file"] = str(self.root / "vanished.pdf")
        pack = self.stage2_run()
        row = self.supporting(pack, "AAAA1111")
        self.assertEqual(row["facts_state"], "failed")
        self.assertEqual(row["facts_error"], "facts_source_fingerprint_mismatch")
        self.assertIsNone(row["paper_facts"])

    def test_future_work_join_mismatch_fails_closed(self):
        unknown = hashlib.sha256(b"never quoted anywhere").hexdigest()
        make_facts_sidecar(
            self.prof_dir / "论文分析" / "AAAA1111.md", self.pdf,
            [GAP_QUOTES["AAAA1111"]], joined_ids=[unknown])
        pack = self.stage2_run()
        row = self.supporting(pack, "AAAA1111")
        self.assertEqual(row["facts_state"], "failed")
        self.assertEqual(row["facts_error"], "facts_future_work_join_mismatch")
        self.assertIsNone(row["paper_facts"])

    def test_broken_authoritative_sidecar_fails_facts_too(self):
        # With the authoritative sidecar broken, AAAA1111's gap leaves the pool
        # and a full stage2 run would rightly reject the stale results — so this
        # case asserts the facts context directly.
        import importlib.util
        spec = importlib.util.spec_from_file_location("contact_state_facts_unit", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        (self.prof_dir / "论文分析" / "AAAA1111.md.future_work.json").write_text(
            '{"schema": 1, "status": "nope"}', encoding="utf-8")
        ctx = module.Stage2Context(self.write_facts())
        record = ctx.facts_for("AAAA1111")
        self.assertEqual(record, (None, "failed", "facts_future_work_join_mismatch"))

    def test_facts_sidecar_change_invalidates_direction_reuse(self):
        facts = self.write_facts()
        results = self.root / "results"
        self.write_stage2_results(results)
        self.assertEqual(parse(run_bound_stage2_plan(run_cli, facts))["status"], "ok")
        self.assertEqual(parse(run_cli("stage2-finalize", "--facts", facts,
                                       "--results", results))["status"], "ok")
        rerun = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(rerun["directions"][0]["action"], "reuse")

        # Any byte change to the facts sidecar must invalidate the input pack.
        payload = json.loads(self.facts_sidecar.read_text(encoding="utf-8"))
        payload["confidence"] = 0.7
        self.facts_sidecar.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        after = parse(run_bound_stage2_plan(run_cli, facts))
        self.assertEqual(after["directions"][0]["action"], "process")

    def test_invalid_facts_sidecar_shape_fails_closed(self):
        payload = json.loads(self.facts_sidecar.read_text(encoding="utf-8"))
        payload["research_problem"] = "   "
        self.facts_sidecar.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        pack = self.stage2_run()
        row = self.supporting(pack, "AAAA1111")
        self.assertEqual(row["facts_state"], "failed")
        self.assertEqual(row["facts_error"], "invalid_facts_sidecar")
        self.assertIsNone(row["paper_facts"])


if __name__ == "__main__":
    unittest.main()
