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


class Stage2FinalizeWithResolvedTests(unittest.TestCase):
    """Tests for stage2-finalize with resolved_directions parameter."""

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

    def test_finalize_applies_resolved_directions_to_pack(self):
        """stage2-finalize should apply resolved directions to the pack."""
        papers = [
            self._make_paper_with_facts("P1", "Adaptive Signal Processing",
                                        ["signal", "processing"],
                                        ["Future work will extend."]),
            self._make_paper_with_facts("P2", "Kitchen Chemistry",
                                        ["chemistry", "kitchen"],
                                        ["More experiments."]),
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

        # Create resolved directions file
        resolved = {
            "schema": 1,
            "kind": "professor-contact-resolved-directions",
            "professor": "試験 教授",
            "generated_at": "2026-01-01T00:00:00Z",
            "directions": [
                {
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
            ],
        }
        resolved_path = self.root / "resolved.json"
        write_json(resolved_path, resolved)

        # Need to run stage2-plan first to get the gap IDs for freshness results
        plan_result = run_cli("stage2-plan", "--facts", str(facts_path))
        plan_payload = parse(plan_result)

        # Create freshness results matching the gaps from stage2-plan
        results_dir = self.root / "results"
        results_dir.mkdir()
        freshness_results = []
        for job in plan_payload["jobs"]:
            if job["kind"] == "freshness":
                for gap in job["model_input"]["gaps"]:
                    freshness_results.append({
                        "gap_id": gap["gap_id"],
                        "status": "open",
                        "candidate_paper_ids": [],
                        "evidence": "No later papers found",
                        "confidence": "high",
                    })
        freshness_result = {
            "schema": 1, "kind": "freshness", "collection_key": "dir_A",
            "results": freshness_results,
        }
        write_json(results_dir / "freshness-dir_A.json", freshness_result)
        narrative_result = {
            "schema": 1, "kind": "narrative",
            "directions": [
                {
                    "collection_key": "dir_A",
                    "positioning": [
                        {"kind": "para", "text": "Test positioning {{P:P1}}", "refs": ["paper:P1"],
                         "concrete_object": "obj", "input_example": "in", "output_example": "out"},
                    ],
                    "gap_notes": [],
                },
            ],
        }
        write_json(results_dir / "narrative.json", narrative_result)

        result = run_cli("stage2-finalize", "--facts", str(facts_path),
                         "--results", str(results_dir),
                         "--resolved-directions", str(resolved_path))
        payload = parse(result)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["resolved_directions_applied"])
        # Check that P2 was removed from supporting_papers
        pack_path = self.prof_dir / "套磁候选输入.json"
        self.assertTrue(pack_path.is_file())
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(len(pack["directions"]), 1)
        supporting_keys = [p["item_key"] for p in pack["directions"][0]["supporting_papers"]]
        self.assertNotIn("P2", supporting_keys)
        self.assertIn("P1", supporting_keys)
        # Check resolved_direction metadata
        self.assertIn("resolved_direction", pack["directions"][0])
        self.assertEqual(pack["directions"][0]["resolved_direction"]["resolution_type"], "refined")


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


if __name__ == "__main__":
    unittest.main()
