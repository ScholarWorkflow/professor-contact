"""Tests for Stage 2 resolved_direction functionality (issue #7).

Verifies that Stage 2 can resolve provisional directions against full-text
evidence and emit authoritative resolved_direction state.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"


def run_cli(*arguments):
    import subprocess
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
                          text=True, capture_output=True, check=False)


def parse(result):
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"stdout not JSON: {result.stdout!r}\nstderr: {result.stderr!r}")


def quote_id(quote: str) -> str:
    import re
    import unicodedata
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", quote)).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def make_sidecar(analysis: Path, quotes: list, page: int = 8) -> Path:
    items = [{"id": quote_id(q), "quote": q, "translation_zh": f"中译：{q[:24]}",
              "source": "Conclusion", "page": page} for q in quotes]
    sidecar = Path(str(analysis) + ".future_work.json")
    sidecar.write_text(json.dumps({
        "schema": 1, "extractor_version": "future-work-v1",
        "analysis": analysis.name, "status": "ok", "items": items},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return sidecar


def make_facts_sidecar(analysis: Path, pdf: Path, quotes: list, *,
                       topic_terms=None, fingerprint=None) -> Path:
    sidecar = Path(str(analysis) + ".facts.json")
    payload = {
        "schema": 1, "kind": "paper-analysis-facts", "generator_version": "facts-v1",
        "analysis": analysis.name,
        "input_fingerprint": fingerprint or ("sha256:" + hashlib.sha256(pdf.read_bytes()).hexdigest()),
        "evidence_level": "fulltext", "status": "ok",
        "paper": {"title": "Test Paper", "authors": ["Author"], "year": 2024, "venue": "V", "doi": None},
        "research_problem": "problem", "research_object": "object", "approach": "approach",
        "findings": ["finding"], "contributions": ["contribution"],
        "topic_terms": topic_terms or ["signal", "processing", "sensor"],
        "limitations": ["limitation"],
        "source_anchors": {"approach": ["§3"]}, "confidence": 0.8,
        "future_work_ids": [quote_id(q) for q in quotes],
    }
    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return sidecar


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


class ResolvedDirectionPlanTests(unittest.TestCase):
    """Tests for stage2-resolve-plan command."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _make_paper_with_facts(self, item_key, title, topic_terms, quotes, year=2024):
        """Create a paper with analysis, sidecar, and facts files."""
        analysis = self.prof_dir / "论文分析" / f"{item_key}.md"
        analysis.write_text(f"# {title}\n\n## 总结\nsummary\n", encoding="utf-8")
        pdf = self.root / f"{item_key}.pdf"
        pdf.write_bytes(b"%PDF-1.4\nbody")
        make_sidecar(analysis, quotes)
        make_facts_sidecar(analysis, pdf, quotes, topic_terms=topic_terms)
        return {"item_key": item_key, "title": title, "year": year,
                "authorship": "corresponding", "has_pdf": True,
                "analysis_file": str(analysis), "sidecar_file": str(analysis) + ".future_work.json",
                "facts_file": str(analysis) + ".facts.json", "pdf_file": str(pdf)}

    def test_resolve_plan_emits_jobs_for_each_direction(self):
        """stage2-resolve-plan should emit one resolve job per direction."""
        papers = [
            self._make_paper_with_facts("P1", "Adaptive Signal Processing",
                                        ["signal", "processing", "adaptive"],
                                        ["Future work will extend to multi-agent systems."]),
            self._make_paper_with_facts("P2", "Sensor Networks for IoT",
                                        ["sensor", "network", "iot"],
                                        ["We plan to test in real deployments."]),
        ]
        facts = {
            "program_root": str(self.root),
            "professor_dir": str(self.prof_dir),
            "professor": "試験 教授",
            "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": [
                {
                    "collection_key": "dir_A",
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理与传感网络",
                    "status": "active",
                    "member_keys": ["P1", "P2"],
                    "provisional_member_keys": ["P1", "P2"],
                    "relevant_keys": ["P1", "P2"],
                    "named_keys": [],
                    "user_note": "",
                    "credibility": {"verdict": "站得住", "mainline": "主线", "authorship_line": "corresponding_dominant", "note": ""},
                    "red_lines": [],
                },
            ],
        }
        facts_path = self.root / "facts.json"
        write_json(facts_path, facts)
        result = run_cli("stage2-resolve-plan", "--facts", str(facts_path))
        payload = parse(result)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(len(payload["jobs"]), 1)
        self.assertEqual(payload["jobs"][0]["kind"], "resolve")
        self.assertEqual(payload["jobs"][0]["collection_key"], "dir_A")

    def test_resolve_plan_detects_removal_candidates(self):
        """stage2-resolve-plan should detect papers that don't belong."""
        papers = [
            self._make_paper_with_facts("P1", "Adaptive Signal Processing",
                                        ["signal", "processing", "adaptive"],
                                        ["Future work will extend to multi-agent systems."]),
            # P2 has topic terms that don't match the signal processing direction
            self._make_paper_with_facts("P2", "Kitchen Chemistry Experiments",
                                        ["chemistry", "kitchen", "experiments"],
                                        ["We plan to test new recipes."]),
        ]
        facts = {
            "program_root": str(self.root),
            "professor_dir": str(self.prof_dir),
            "professor": "試験 教授",
            "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": [
                {
                    "collection_key": "dir_A",
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理与传感网络",
                    "status": "active",
                    "member_keys": ["P1", "P2"],
                    "provisional_member_keys": ["P1", "P2"],
                    "relevant_keys": ["P1", "P2"],
                    "named_keys": [],
                    "user_note": "",
                    "credibility": {"verdict": "站得住", "mainline": "主线", "authorship_line": "corresponding_dominant", "note": ""},
                    "red_lines": [],
                },
            ],
        }
        facts_path = self.root / "facts.json"
        write_json(facts_path, facts)
        result = run_cli("stage2-resolve-plan", "--facts", str(facts_path))
        payload = parse(result)
        self.assertEqual(payload["status"], "ok")
        # P2 should be flagged for removal (chemistry vs signal processing)
        self.assertTrue(len(payload["candidates"]["removals"]) > 0)
        removal_keys = [r["item_key"] for r in payload["candidates"]["removals"]]
        self.assertIn("P2", removal_keys)

    def test_resolve_plan_no_changes_when_all_match(self):
        """stage2-resolve-plan should report no material changes when papers match."""
        papers = [
            self._make_paper_with_facts("P1", "Adaptive Signal Processing",
                                        ["信号", "处理", "自适应"],
                                        ["Future work will extend to multi-agent systems."]),
            self._make_paper_with_facts("P2", "Robust Sensor Networks",
                                        ["传感", "网络", "稳健"],
                                        ["We plan to test in real deployments."]),
        ]
        facts = {
            "program_root": str(self.root),
            "professor_dir": str(self.prof_dir),
            "professor": "試験 教授",
            "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": [
                {
                    "collection_key": "dir_A",
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理与传感网络",
                    "status": "active",
                    "member_keys": ["P1", "P2"],
                    "provisional_member_keys": ["P1", "P2"],
                    "relevant_keys": ["P1", "P2"],
                    "named_keys": [],
                    "user_note": "",
                    "credibility": {"verdict": "站得住", "mainline": "主线", "authorship_line": "corresponding_dominant", "note": ""},
                    "red_lines": [],
                },
            ],
        }
        facts_path = self.root / "facts.json"
        write_json(facts_path, facts)
        result = run_cli("stage2-resolve-plan", "--facts", str(facts_path))
        payload = parse(result)
        self.assertEqual(payload["status"], "ok")
        # No removals expected since both papers match signal processing
        self.assertEqual(len(payload["candidates"]["removals"]), 0)


class ResolvedDirectionFinalizeTests(unittest.TestCase):
    """Tests for stage2-resolve-finalize command."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _make_paper_with_facts(self, item_key, title, topic_terms, quotes, year=2024):
        analysis = self.prof_dir / "论文分析" / f"{item_key}.md"
        analysis.write_text(f"# {title}\n\n## 总结\nsummary\n", encoding="utf-8")
        pdf = self.root / f"{item_key}.pdf"
        pdf.write_bytes(b"%PDF-1.4\nbody")
        make_sidecar(analysis, quotes)
        make_facts_sidecar(analysis, pdf, quotes, topic_terms=topic_terms)
        return {"item_key": item_key, "title": title, "year": year,
                "authorship": "corresponding", "has_pdf": True,
                "analysis_file": str(analysis), "sidecar_file": str(analysis) + ".future_work.json",
                "facts_file": str(analysis) + ".facts.json", "pdf_file": str(pdf)}

    def test_resolve_finalize_unchanged_when_no_result(self):
        """stage2-resolve-finalize should produce unchanged resolution when no result file."""
        papers = [
            self._make_paper_with_facts("P1", "Adaptive Signal Processing",
                                        ["signal", "processing"],
                                        ["Future work will extend."]),
        ]
        facts = {
            "program_root": str(self.root),
            "professor_dir": str(self.prof_dir),
            "professor": "試験 教授",
            "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": [
                {
                    "collection_key": "dir_A",
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理",
                    "status": "active",
                    "member_keys": ["P1"],
                    "provisional_member_keys": ["P1"],
                    "relevant_keys": ["P1"],
                    "named_keys": [],
                    "user_note": "",
                    "credibility": {"verdict": "站得住", "mainline": "主线", "authorship_line": "corresponding_dominant", "note": ""},
                    "red_lines": [],
                },
            ],
        }
        facts_path = self.root / "facts.json"
        write_json(facts_path, facts)
        results_dir = self.root / "results"
        results_dir.mkdir()
        result = run_cli("stage2-resolve-finalize", "--facts", str(facts_path), "--results", str(results_dir))
        payload = parse(result)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(len(payload["directions"]), 1)
        self.assertEqual(payload["directions"][0]["resolution_type"], "unchanged")
        self.assertFalse(payload["needs_user_choice"])

    def test_resolve_finalize_applies_removal(self):
        """stage2-resolve-finalize should apply paper removal from valid result."""
        papers = [
            self._make_paper_with_facts("P1", "Adaptive Signal Processing",
                                        ["signal", "processing"],
                                        ["Future work will extend."]),
            self._make_paper_with_facts("P2", "Kitchen Chemistry",
                                        ["chemistry", "kitchen"],
                                        ["More experiments needed."]),
        ]
        facts = {
            "program_root": str(self.root),
            "professor_dir": str(self.prof_dir),
            "professor": "試験 教授",
            "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": [
                {
                    "collection_key": "dir_A",
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理",
                    "status": "active",
                    "member_keys": ["P1", "P2"],
                    "provisional_member_keys": ["P1", "P2"],
                    "relevant_keys": ["P1", "P2"],
                    "named_keys": [],
                    "user_note": "",
                    "credibility": {"verdict": "站得住", "mainline": "主线", "authorship_line": "corresponding_dominant", "note": ""},
                    "red_lines": [],
                },
            ],
        }
        facts_path = self.root / "facts.json"
        write_json(facts_path, facts)
        results_dir = self.root / "results"
        results_dir.mkdir()
        # Write a resolve result that removes P2
        resolve_result = {
            "schema": 1, "kind": "resolve", "collection_key": "dir_A",
            "resolved": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "refined",
                "papers_to_add": [],
                "papers_to_remove": ["P2"],
                "paper_justifications": {"P2": "Topic terms (chemistry, kitchen) do not match signal processing direction"},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        }
        write_json(results_dir / "resolve-dir_A.json", resolve_result)
        result = run_cli("stage2-resolve-finalize", "--facts", str(facts_path), "--results", str(results_dir))
        payload = parse(result)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["directions"][0]["resolution_type"], "refined")
        self.assertIn("P2", payload["directions"][0]["papers_to_remove"])
        self.assertTrue(payload["needs_user_choice"])

    def test_resolve_finalize_rejects_invalid_removal(self):
        """stage2-resolve-finalize should reject removal of non-provisional papers."""
        papers = [
            self._make_paper_with_facts("P1", "Adaptive Signal Processing",
                                        ["signal", "processing"],
                                        ["Future work will extend."]),
        ]
        facts = {
            "program_root": str(self.root),
            "professor_dir": str(self.prof_dir),
            "professor": "試験 教授",
            "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": [
                {
                    "collection_key": "dir_A",
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理",
                    "status": "active",
                    "member_keys": ["P1"],
                    "provisional_member_keys": ["P1"],
                    "relevant_keys": ["P1"],
                    "named_keys": [],
                    "user_note": "",
                    "credibility": {"verdict": "站得住", "mainline": "主线", "authorship_line": "corresponding_dominant", "note": ""},
                    "red_lines": [],
                },
            ],
        }
        facts_path = self.root / "facts.json"
        write_json(facts_path, facts)
        results_dir = self.root / "results"
        results_dir.mkdir()
        # Try to remove a non-provisional paper (P99 doesn't exist in provisional)
        resolve_result = {
            "schema": 1, "kind": "resolve", "collection_key": "dir_A",
            "resolved": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "refined",
                "papers_to_add": [],
                "papers_to_remove": ["P99"],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        }
        write_json(results_dir / "resolve-dir_A.json", resolve_result)
        result = run_cli("stage2-resolve-finalize", "--facts", str(facts_path), "--results", str(results_dir))
        payload = parse(result)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "invalid_result_json")


class ResolvedPipelineMixin:
    """Shared helpers for full resolve → plan → finalize pipeline tests."""

    professor = "試験 教授"

    def make_paper(self, item_key, title, topic_terms, quotes, year=2024):
        analysis = self.prof_dir / "论文分析" / f"{item_key}.md"
        analysis.write_text(f"# {title}\n\n## 总结\nsummary\n", encoding="utf-8")
        pdf = self.root / f"{item_key}.pdf"
        pdf.write_bytes(b"%PDF-1.4\nbody")
        make_sidecar(analysis, quotes)
        make_facts_sidecar(analysis, pdf, quotes, topic_terms=topic_terms)
        return {"item_key": item_key, "title": title, "year": year,
                "authorship": "corresponding", "has_pdf": True,
                "analysis_file": str(analysis), "sidecar_file": str(analysis) + ".future_work.json",
                "facts_file": str(analysis) + ".facts.json", "pdf_file": str(pdf)}

    @staticmethod
    def make_direction(ckey, member_keys, *, name_ja="方向", name_zh="方向", summary="方向概要",
                       provisional_keys=None, named_keys=None):
        keys = list(member_keys)
        return {
            "collection_key": ckey,
            "name_ja": name_ja,
            "name_zh": name_zh,
            "summary_zh": summary,
            "status": "active",
            "member_keys": keys,
            "provisional_member_keys": list(provisional_keys) if provisional_keys is not None else keys,
            "relevant_keys": keys,
            "named_keys": list(named_keys or []),
            "user_note": "",
            "credibility": {"verdict": "站得住", "mainline": "主线",
                            "authorship_line": "corresponding_dominant", "note": ""},
            "red_lines": [],
        }

    def write_facts(self, papers, directions):
        facts_path = self.root / "facts.json"
        write_json(facts_path, {
            "program_root": str(self.root),
            "professor_dir": str(self.prof_dir),
            "professor": self.professor,
            "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": directions,
        })
        return facts_path

    def run_resolve(self, facts_path, resolve_results):
        """resolve-plan → write per-direction resolve results → resolve-finalize."""
        plan_payload = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(plan_payload["status"], "ok")
        results_dir = self.root / "resolve_results"
        results_dir.mkdir(exist_ok=True)
        for ckey, resolved in resolve_results.items():
            write_json(results_dir / f"resolve-{ckey}.json", {
                "schema": 1, "kind": "resolve", "collection_key": ckey, "resolved": resolved})
        finalize_payload = parse(run_cli("stage2-resolve-finalize",
                                         "--facts", str(facts_path),
                                         "--results", str(results_dir)))
        self.assertEqual(finalize_payload["status"], "ok",
                         msg=json.dumps(finalize_payload, ensure_ascii=False))
        return plan_payload, finalize_payload

    def run_stage2_finalize(self, facts_path):
        """stage2-plan → freshness/narrative results → stage2-finalize with the sidecar."""
        plan_payload = parse(run_cli("stage2-plan", "--facts", str(facts_path)))
        results_dir = self.root / "stage2_results"
        results_dir.mkdir(exist_ok=True)
        narrative_directions = []
        for job in plan_payload["jobs"]:
            if job["kind"] != "freshness":
                continue
            ckey = job["collection_key"]
            freshness_rows = [{
                "gap_id": gap["gap_id"], "status": "open", "candidate_paper_ids": [],
                "evidence": "No later papers found", "confidence": "high",
            } for gap in job["model_input"]["gaps"]]
            write_json(results_dir / f"freshness-{ckey}.json", {
                "schema": 1, "kind": "freshness", "collection_key": ckey,
                "results": freshness_rows})
        for direction_entry in plan_payload["directions"]:
            ckey = direction_entry["collection_key"]
            narrative_directions.append({
                "collection_key": ckey,
                "positioning": [{"kind": "para", "text": f"Positioning for {ckey}",
                                 "refs": [], "concrete_object": "o", "input_example": "i",
                                 "output_example": "x"}],
                "gap_notes": [],
            })
        write_json(results_dir / "narrative.json", {
            "schema": 1, "kind": "narrative", "directions": narrative_directions})
        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        payload = parse(run_cli("stage2-finalize", "--facts", str(facts_path),
                                "--results", str(results_dir),
                                "--resolved-directions", str(sidecar_path)))
        return payload

    def load_pack(self):
        return json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))


class Stage2FinalizeWithResolvedTests(ResolvedPipelineMixin, unittest.TestCase):
    """stage2-finalize consumes the resolve sidecar produced by the resolve pipeline."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_finalize_applies_resolved_directions_to_pack(self):
        """A refined resolution removes the misclustered paper from the pack."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work will extend."]),
            self.make_paper("P2", "Kitchen Chemistry", ["chemistry", "kitchen"],
                            ["More experiments."]),
        ]
        facts_path = self.write_facts(papers, [self.make_direction("dir_A", ["P1", "P2"])])

        _, resolve_payload = self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "refined",
                "papers_to_add": [],
                "papers_to_remove": ["P2"],
                "paper_justifications": {"P2": "Topic mismatch"},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        })
        self.assertTrue(resolve_payload["needs_user_choice"])

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        self.assertTrue(payload["resolved_directions_applied"])
        pack = self.load_pack()
        self.assertEqual(len(pack["directions"]), 1)
        supporting_keys = [p["item_key"] for p in pack["directions"][0]["supporting_papers"]]
        self.assertNotIn("P2", supporting_keys)
        self.assertIn("P1", supporting_keys)
        rd = pack["directions"][0]["resolved_direction"]
        self.assertEqual(rd["resolution_type"], "refined")
        self.assertEqual(rd["resolved_direction_id"], "dir_A")
        # Pack root keeps the resolved index.
        self.assertEqual(pack["resolved_directions"]["directions"][0]["resolution_type"], "refined")

    def test_finalize_stamps_resolved_subfield_on_unchanged_directions(self):
        """Every direction carries resolved_direction, even when unchanged."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work will extend."]),
        ]
        facts_path = self.write_facts(papers, [self.make_direction("dir_A", ["P1"])])

        _, resolve_payload = self.run_resolve(facts_path, {})
        self.assertFalse(resolve_payload["needs_user_choice"])

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        pack = self.load_pack()
        rd = pack["directions"][0]["resolved_direction"]
        self.assertEqual(rd["resolution_type"], "unchanged")
        self.assertEqual(rd["resolved_direction_id"], "dir_A")
        self.assertEqual(rd["provisional_direction_id"], "dir_A")

    def test_finalize_fails_closed_on_stale_resolved_file(self):
        """A resolved entry whose fingerprint no longer matches is rejected."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work will extend."]),
        ]
        facts_path = self.write_facts(papers, [self.make_direction("dir_A", ["P1"])])
        self.run_resolve(facts_path, {})

        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["directions"][0]["input_fingerprint"] = "0" * 64
        write_json(sidecar_path, sidecar)

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "resolved_directions_stale")
        self.assertEqual(payload["stale_directions"][0]["problem"], "input_fingerprint_mismatch")

    def test_finalize_fails_closed_on_cross_professor_resolved_file(self):
        """A sidecar written for another professor is never applied."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work will extend."]),
        ]
        facts_path = self.write_facts(papers, [self.make_direction("dir_A", ["P1"])])
        self.run_resolve(facts_path, {})

        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["professor"] = "別の教授"
        write_json(sidecar_path, sidecar)

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "resolved_directions_professor_mismatch")

    def test_finalize_fails_closed_on_missing_direction_entry(self):
        """Every current direction must be covered by the resolved file."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work will extend."]),
        ]
        facts_path = self.write_facts(papers, [self.make_direction("dir_A", ["P1"])])
        self.run_resolve(facts_path, {})

        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["directions"] = []
        write_json(sidecar_path, sidecar)

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "resolved_directions_stale")
        self.assertEqual(payload["stale_directions"][0]["problem"], "missing_from_resolved_file")


class MergeCandidateDetectionTests(unittest.TestCase):
    """Tests for merge candidate detection."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _make_paper_with_facts(self, item_key, title, topic_terms, quotes, year=2024):
        analysis = self.prof_dir / "论文分析" / f"{item_key}.md"
        analysis.write_text(f"# {title}\n\n## 总结\nsummary\n", encoding="utf-8")
        pdf = self.root / f"{item_key}.pdf"
        pdf.write_bytes(b"%PDF-1.4\nbody")
        make_sidecar(analysis, quotes)
        make_facts_sidecar(analysis, pdf, quotes, topic_terms=topic_terms)
        return {"item_key": item_key, "title": title, "year": year,
                "authorship": "corresponding", "has_pdf": True,
                "analysis_file": str(analysis), "sidecar_file": str(analysis) + ".future_work.json",
                "facts_file": str(analysis) + ".facts.json", "pdf_file": str(pdf)}

    def test_detect_merge_candidates(self):
        """Directions with high profile overlap should be flagged for merge."""
        papers = [
            self._make_paper_with_facts("P1", "Adaptive Signal Processing",
                                        ["signal", "processing", "adaptive"],
                                        ["Future work."]),
            self._make_paper_with_facts("P2", "Sensor Networks",
                                        ["sensor", "network", "signal"],
                                        ["More tests."]),
        ]
        facts = {
            "program_root": str(self.root),
            "professor_dir": str(self.prof_dir),
            "professor": "試験 教授",
            "current_year": 2026,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": papers,
            "directions": [
                {
                    "collection_key": "dir_A",
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理与传感网络",
                    "status": "active",
                    "member_keys": ["P1", "P2"],
                    "provisional_member_keys": ["P1", "P2"],
                    "relevant_keys": ["P1", "P2"],
                    "named_keys": [],
                    "user_note": "",
                    "credibility": {"verdict": "站得住", "mainline": "主线", "authorship_line": "corresponding_dominant", "note": ""},
                    "red_lines": [],
                },
                {
                    "collection_key": "dir_B",
                    "name_ja": "信号处理",
                    "name_zh": "信号处理方向",
                    "summary_zh": "传感网络与信号处理研究",
                    "status": "active",
                    "member_keys": ["P1", "P2"],
                    "provisional_member_keys": ["P1", "P2"],
                    "relevant_keys": ["P1", "P2"],
                    "named_keys": [],
                    "user_note": "",
                    "credibility": {"verdict": "站得住", "mainline": "主线", "authorship_line": "corresponding_dominant", "note": ""},
                    "red_lines": [],
                },
            ],
        }
        facts_path = self.root / "facts.json"
        write_json(facts_path, facts)
        result = run_cli("stage2-resolve-plan", "--facts", str(facts_path))
        payload = parse(result)
        self.assertEqual(payload["status"], "ok")
        # Both directions share papers and have high profile overlap, should flag merge
        self.assertTrue(len(payload["candidates"]["merges"]) > 0)


class Stage2SplitEndToEndTests(ResolvedPipelineMixin, unittest.TestCase):
    """Issue #7 acceptance #3: a split produces two stable resolved IDs and
    Stage 3 generates separate jobs for both authoritative directions."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_split_creates_second_authoritative_direction_and_stage3_jobs(self):
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Signal future work A."]),
            self.make_paper("P2", "Robust Estimation Theory", ["信号", "推定"],
                            ["Signal future work B."]),
            self.make_paper("P3", "Smart Greenhouse Control", ["制御", "温室"],
                            ["Control future work A."]),
            self.make_paper("P4", "Robot Arm Control Systems", ["制御", "口ボット"],
                            ["Control future work B."]),
        ]
        facts_path = self.write_facts(papers, [
            self.make_direction("dir_A", ["P1", "P2", "P3", "P4"],
                                name_ja="信号と制御", name_zh="信号与控制",
                                summary="信号处理与控制系统"),
        ])

        _, resolve_payload = self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "split_from",
                "papers_to_add": ["P3", "P4"],
                "papers_to_remove": [],
                "paper_justifications": {
                    "P3": "control-line full text", "P4": "control-line full text"},
                "split_target": "dir_A__control",
                "merge_target": None,
                "user_note": "",
            },
        })
        self.assertTrue(resolve_payload["needs_user_choice"])
        self.assertEqual(resolve_payload["new_splits"][0]["new_resolved_id"], "dir_A__control")

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        pack = self.load_pack()

        # Two authoritative direction entries with two stable resolved IDs.
        by_ckey = {d["collection_key"]: d for d in pack["directions"]}
        self.assertEqual(set(by_ckey), {"dir_A", "dir_A__control"})
        self.assertEqual(
            {d["resolved_direction"]["resolved_direction_id"] for d in pack["directions"]},
            {"dir_A", "dir_A__control"})
        # Source kept the signal papers and lost the control ones; the split
        # entry carries exactly the control papers and their gaps.
        self.assertEqual(
            sorted(p["item_key"] for p in by_ckey["dir_A"]["supporting_papers"]),
            ["P1", "P2"])
        self.assertEqual(
            sorted(p["item_key"] for p in by_ckey["dir_A__control"]["supporting_papers"]),
            ["P3", "P4"])
        self.assertEqual(by_ckey["dir_A__control"]["resolved_direction"]["provisional_direction_id"],
                         "dir_A")
        for gap in by_ckey["dir_A"]["gap_shortlist"]:
            self.assertIn(gap["item_key"], ["P1", "P2"])
        for gap in by_ckey["dir_A__control"]["gap_shortlist"]:
            self.assertIn(gap["item_key"], ["P3", "P4"])

        # Stage 3 generates separate jobs for both authoritative directions.
        stage3_payload = parse(run_cli("stage3-plan", "--professor-dir", str(self.prof_dir),
                                       "--program-root", str(self.root)))
        self.assertEqual(stage3_payload["status"], "ok",
                         msg=json.dumps(stage3_payload, ensure_ascii=False))
        stage3_ckeys = {job["collection_key"] for job in stage3_payload["jobs"]}
        self.assertEqual(stage3_ckeys, {"dir_A", "dir_A__control"})

    def test_merge_keeps_only_target_direction_and_stage3_job(self):
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Signal future work A."]),
            self.make_paper("P2", "Signal Processing Networks", ["信号", "処理"],
                            ["Signal future work B."]),
        ]
        facts_path = self.write_facts(papers, [
            self.make_direction("dir_A", ["P1"], name_ja="信号処理", name_zh="信号处理",
                                summary="自适应信号处理"),
            self.make_direction("dir_B", ["P2"], name_ja="信号処理ネットワーク",
                                name_zh="信号处理网络", summary="信号处理与网络研究"),
        ])

        _, resolve_payload = self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理", "name_zh": "信号处理",
                "resolution_type": "unchanged",
                "papers_to_add": [], "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None, "merge_target": None, "user_note": "",
            },
            "dir_B": {
                "resolved_direction_id": "dir_B",
                "provisional_direction_id": "dir_B",
                "name_ja": "信号処理ネットワーク", "name_zh": "信号处理网络",
                "resolution_type": "merged_into",
                "papers_to_add": [], "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": "dir_A",
                "user_note": "",
            },
        })
        self.assertTrue(resolve_payload["needs_user_choice"])

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        pack = self.load_pack()

        # Only the authoritative target direction survives.
        self.assertEqual([d["collection_key"] for d in pack["directions"]], ["dir_A"])
        target = pack["directions"][0]
        self.assertEqual(
            sorted(p["item_key"] for p in target["supporting_papers"]), ["P1", "P2"])
        self.assertEqual(target["resolved_direction"]["merged_from"], ["dir_B"])
        # Paper identity is preserved: P2 keeps its exact item_key and metadata.
        p2 = next(p for p in target["supporting_papers"] if p["item_key"] == "P2")
        self.assertEqual(p2["title"], "Signal Processing Networks")
        self.assertTrue(p2["resolved_addition"])

        # The pack-root index keeps the source→target mapping for references.
        index = {d["provisional_direction_id"]: d
                 for d in pack["resolved_directions"]["directions"]}
        self.assertEqual(index["dir_B"]["merge_target"], "dir_A")
        self.assertEqual(index["dir_B"]["resolution_type"], "merged_into")

        # Stage 3 only generates a job for the surviving direction.
        stage3_payload = parse(run_cli("stage3-plan", "--professor-dir", str(self.prof_dir),
                                       "--program-root", str(self.root)))
        self.assertEqual(stage3_payload["status"], "ok",
                         msg=json.dumps(stage3_payload, ensure_ascii=False))
        stage3_ckeys = {job["collection_key"] for job in stage3_payload["jobs"]}
        self.assertEqual(stage3_ckeys, {"dir_A"})

    def test_merge_chain_is_rejected(self):
        """merged_into a direction that is itself merged_into is invalid."""
        papers = [
            self.make_paper("P1", "Paper One", ["主题", "一"], ["Gap one."]),
            self.make_paper("P2", "Paper Two", ["主题", "二"], ["Gap two."]),
            self.make_paper("P3", "Paper Three", ["主题", "三"], ["Gap three."]),
        ]
        facts_path = self.write_facts(papers, [
            self.make_direction("dir_A", ["P1"]),
            self.make_direction("dir_B", ["P2"]),
            self.make_direction("dir_C", ["P3"]),
        ])
        results_dir = self.root / "resolve_results"
        results_dir.mkdir()
        write_json(results_dir / "resolve-dir_A.json", {
            "schema": 1, "kind": "resolve", "collection_key": "dir_A",
            "resolved": {"resolved_direction_id": "dir_A", "provisional_direction_id": "dir_A",
                         "name_ja": "A", "name_zh": "甲", "resolution_type": "unchanged",
                         "papers_to_add": [], "papers_to_remove": [], "paper_justifications": {},
                         "split_target": None, "merge_target": None, "user_note": ""}})
        write_json(results_dir / "resolve-dir_B.json", {
            "schema": 1, "kind": "resolve", "collection_key": "dir_B",
            "resolved": {"resolved_direction_id": "dir_B", "provisional_direction_id": "dir_B",
                         "name_ja": "B", "name_zh": "乙", "resolution_type": "merged_into",
                         "papers_to_add": [], "papers_to_remove": [], "paper_justifications": {},
                         "split_target": None, "merge_target": "dir_C", "user_note": ""}})
        write_json(results_dir / "resolve-dir_C.json", {
            "schema": 1, "kind": "resolve", "collection_key": "dir_C",
            "resolved": {"resolved_direction_id": "dir_C", "provisional_direction_id": "dir_C",
                         "name_ja": "C", "name_zh": "丙", "resolution_type": "merged_into",
                         "papers_to_add": [], "papers_to_remove": [], "paper_justifications": {},
                         "split_target": None, "merge_target": "dir_A", "user_note": ""}})
        result = run_cli("stage2-resolve-finalize", "--facts", str(facts_path),
                         "--results", str(results_dir))
        payload = parse(result)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "invalid_result_json")
        self.assertIn("merge chain", payload["message"])


class ResolvedReuseTests(ResolvedPipelineMixin, unittest.TestCase):
    """Issue #7 acceptance #5: unchanged resolved directions reuse cached state
    and never re-run the resolve job; stale ones re-resolve."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_resolve_plan_reuses_unchanged_directions(self):
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work."]),
        ]
        facts_path = self.write_facts(papers, [self.make_direction("dir_A", ["P1"])])

        first = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(first["status"], "ok")
        self.assertEqual(first["directions"][0]["action"], "process")
        self.assertTrue(first["write_needed"])

        self.run_resolve(facts_path, {})  # writes the sidecar with fingerprints

        second = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(second["status"], "ok")
        self.assertEqual(second["directions"][0]["action"], "reuse")
        self.assertEqual(second["jobs"], [])
        self.assertFalse(second["write_needed"])

    def test_resolve_plan_reprocesses_when_facts_change(self):
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work."]),
        ]
        facts_path = self.write_facts(papers, [self.make_direction("dir_A", ["P1"])])
        self.run_resolve(facts_path, {})

        # Change a resolved-relevant input: rewrite the paper's facts sidecar.
        analysis = self.prof_dir / "论文分析" / "P1.md"
        make_facts_sidecar(analysis, self.root / "P1.pdf", ["Future work."],
                           topic_terms=["信号", "処理", "新項目"])

        second = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(second["directions"][0]["action"], "process")
        self.assertTrue(second["write_needed"])

    def test_resolve_finalize_preserves_reused_entries_without_results(self):
        """Re-running resolve-finalize without new results keeps the resolved
        state (and does not re-raise needs_user_choice for already-applied changes)."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work."]),
            self.make_paper("P2", "Kitchen Chemistry", ["chemistry", "kitchen"],
                            ["More experiments."]),
        ]
        facts_path = self.write_facts(papers, [self.make_direction("dir_A", ["P1", "P2"])])
        _, first = self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理", "name_zh": "信号处理",
                "resolution_type": "refined",
                "papers_to_add": [], "papers_to_remove": ["P2"],
                "paper_justifications": {"P2": "Topic mismatch"},
                "split_target": None, "merge_target": None, "user_note": "",
            },
        })
        self.assertTrue(first["needs_user_choice"])

        # Second run with an empty results dir: the entry is reused as-is.
        results_dir = self.root / "resolve_results"
        for stale in results_dir.glob("resolve-*.json"):
            stale.unlink()
        second = parse(run_cli("stage2-resolve-finalize",
                               "--facts", str(facts_path), "--results", str(results_dir)))
        self.assertEqual(second["status"], "ok",
                         msg=json.dumps(second, ensure_ascii=False))
        entry = next(d for d in second["directions"] if d["provisional_direction_id"] == "dir_A")
        self.assertEqual(entry["resolution_type"], "refined")
        self.assertFalse(second["needs_user_choice"],
                         "an already-applied refinement must not re-prompt the user")


if __name__ == "__main__":
    unittest.main()
