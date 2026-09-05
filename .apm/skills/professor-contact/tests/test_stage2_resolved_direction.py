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
        self.assertEqual(payload["jobs"][0]["direction_id"], "dir_A")

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

    def write_facts(self, papers, directions, name="facts.json"):
        facts_path = self.root / name
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

    def accept_resolved(self, facts_path, ckeys):
        """stage2-resolve-accept: the user adopts the named proposals."""
        return parse(run_cli("stage2-resolve-accept", "--facts", str(facts_path),
                             "--ckeys", ",".join(ckeys)))

    def run_stage2_finalize(self, facts_path):
        """stage2-plan → freshness/narrative results → stage2-finalize with the sidecar."""
        plan_payload = parse(run_cli("stage2-plan", "--facts", str(facts_path)))
        results_dir = self.root / "stage2_results"
        results_dir.mkdir(exist_ok=True)
        narrative_directions = []
        for job in plan_payload["jobs"]:
            if job["kind"] != "freshness":
                continue
            did = job["direction_id"]
            freshness_rows = [{
                "gap_id": gap["gap_id"], "status": "open", "candidate_paper_ids": [],
                "evidence": "No later papers found", "confidence": "high",
            } for gap in job["model_input"]["gaps"]]
            write_json(results_dir / f"freshness-{did}.json", {
                "schema": 1, "kind": "freshness", "direction_id": did,
                "results": freshness_rows})
        for job in plan_payload["jobs"]:
            if job["kind"] != "narrative":
                continue
            did = job["direction_id"]
            narrative_directions.append({
                "direction_id": did,
                "positioning": [{"kind": "para", "text": f"Positioning for {did}",
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

        # The user adopts the refinement: the proposal must be accepted
        # explicitly BEFORE stage2-finalize may apply it.
        accepted = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))
        self.assertEqual(accepted["accepted"], ["dir_A"])

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        self.assertTrue(payload["resolved_directions_applied"])
        pack = self.load_pack()
        self.assertEqual(len(pack["directions"]), 1)
        supporting_keys = list(pack["directions"][0]["supporting_item_keys"])
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

        accepted = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        pack = self.load_pack()

        # Two authoritative direction entries with two stable resolved IDs.
        by_ckey = {d["direction_id"]: d for d in pack["directions"]}
        self.assertEqual(set(by_ckey), {"dir_A", "dir_A__control"})
        self.assertEqual(
            {d["resolved_direction"]["resolved_direction_id"] for d in pack["directions"]},
            {"dir_A", "dir_A__control"})
        # Source kept the signal papers and lost the control ones; the split
        # entry carries exactly the control papers and their gaps.
        self.assertEqual(sorted(by_ckey["dir_A"]["supporting_item_keys"]), ["P1", "P2"])
        self.assertEqual(sorted(by_ckey["dir_A__control"]["supporting_item_keys"]),
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
        stage3_ckeys = {job["direction_id"] for job in stage3_payload["jobs"]}
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

        accepted = self.accept_resolved(facts_path, ["dir_B"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        pack = self.load_pack()

        # Only the authoritative target direction survives.
        self.assertEqual([d["direction_id"] for d in pack["directions"]], ["dir_A"])
        target = pack["directions"][0]
        self.assertEqual(sorted(target["supporting_item_keys"]), ["P1", "P2"])
        self.assertEqual(target["resolved_direction"]["merged_from"], ["dir_B"])
        # Paper identity is preserved: P2 keeps its exact item_key and metadata.
        p2 = pack["papers"]["P2"]
        self.assertEqual(p2["title"], "Signal Processing Networks")
        self.assertIn("P2", target["resolved_addition_keys"])

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
        stage3_ckeys = {job["direction_id"] for job in stage3_payload["jobs"]}
        self.assertEqual(stage3_ckeys, {"dir_A"})

    def test_merge_chain_is_rejected(self):
        """merged_into a direction that is itself merged_into is invalid.

        Both merge pairs carry convergent full-text topic evidence so the
        rejection is decided by the chain rule, not the evidence floor.
        """
        papers = [
            self.make_paper("P1", "Paper One", ["共通", "テーマ", "一"], ["Gap one."]),
            self.make_paper("P2", "Paper Two", ["共通", "テーマ", "二"], ["Gap two."]),
            self.make_paper("P3", "Paper Three", ["共通", "テーマ", "三"], ["Gap three."]),
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


class CandidateUnionEvidenceTests(ResolvedPipelineMixin, unittest.TestCase):
    """Issue #7 required flow #2: resolution evidence covers the full candidate
    union, not just the abstract-level relevant set."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_fingerprint_sensitive_to_candidate_outside_relevant_set(self):
        """A candidate paper outside the relevant set still invalidates the
        resolved fingerprint when its full-text facts change."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work."]),
            # P2 is in the candidate union but NOT in the relevant set.
            self.make_paper("P2", "Signal Processing Networks", ["信号", "処理"],
                            ["Future work B."]),
        ]
        direction = self.make_direction("dir_A", ["P1", "P2"], provisional_keys=["P1"])
        direction["relevant_keys"] = ["P1"]  # abstract gate dropped P2
        facts_path = self.write_facts(papers, [direction])

        before = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(before["directions"][0]["action"], "process")
        # Evidence must cover BOTH candidates even though only P1 is relevant.
        evidence_keys = {p["item_key"] for p in before["jobs"][0]["model_input"]["paper_evidence"]}
        self.assertEqual(evidence_keys, {"P1", "P2"})

        self.run_resolve(facts_path, {})
        after = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(after["directions"][0]["action"], "reuse")

        # Change the non-relevant candidate's facts sidecar: the resolution
        # must be re-evaluated because full-text evidence about ANY candidate
        # can flip membership.
        analysis = self.prof_dir / "论文分析" / "P2.md"
        make_facts_sidecar(analysis, self.root / "P2.pdf", ["Future work B."],
                           topic_terms=["制御", "ロボット"])
        third = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(third["directions"][0]["action"], "process",
                         "a facts change on a non-relevant candidate must invalidate "
                         "the resolved state (candidate-union evidence scope)")


class Stage2SplitReuseChainTests(ResolvedPipelineMixin, unittest.TestCase):
    """Full chain: first split finalize, unchanged reuse finalize, then Stage 3.

    Locks the reuse path for a materialized split: the second finalize must
    keep the accepted child (paper membership, gaps, both stable resolved IDs)
    and Stage 3 must still generate jobs for both directions."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_split_first_apply_then_reuse_then_stage3_jobs(self):
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Signal future work A."]),
            self.make_paper("P2", "Signal Estimation Theory", ["信号", "推定"],
                            ["Signal future work B."]),
            self.make_paper("P3", "Greenhouse Control", ["制御", "温室"],
                            ["Control future work A."]),
            self.make_paper("P4", "Robot Arm Control", ["制御", "口ボット"],
                            ["Control future work B."]),
        ]
        facts_path = self.write_facts(papers, [
            self.make_direction("dir_A", ["P1", "P2", "P3", "P4"],
                                name_ja="信号と制御", name_zh="信号与控制",
                                summary="信号处理与控制系统"),
        ])
        split = {
            "resolved_direction_id": "dir_A",
            "provisional_direction_id": "dir_A",
            "name_ja": "信号処理",
            "name_zh": "信号处理",
            "resolution_type": "split_from",
            "papers_to_add": ["P3", "P4"],
            "papers_to_remove": [],
            "paper_justifications": {"P3": "control cluster", "P4": "control cluster"},
            "split_target": "dir_A__control",
            "merge_target": None,
            "user_note": "",
        }

        self.run_resolve(facts_path, {"dir_A": split})
        accepted = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))
        first = self.run_stage2_finalize(facts_path)
        self.assertEqual(first["status"], "ok", msg=json.dumps(first, ensure_ascii=False))
        first_by_key = {d["direction_id"]: d for d in self.load_pack()["directions"]}
        self.assertEqual(set(first_by_key), {"dir_A", "dir_A__control"})
        self.assertEqual(sorted(first_by_key["dir_A"]["supporting_item_keys"]), ["P1", "P2"])
        self.assertEqual(sorted(first_by_key["dir_A__control"]["supporting_item_keys"]),
                         ["P3", "P4"])
        child_before = first_by_key["dir_A__control"]

        # Unchanged rerun: resolve reuses (no jobs), finalize must keep the child.
        reuse_plan, reuse_finalize = self.run_resolve(facts_path, {})
        self.assertEqual(reuse_plan["jobs"], [])
        self.assertFalse(reuse_finalize["needs_user_choice"])
        second = self.run_stage2_finalize(facts_path)
        self.assertEqual(second["status"], "ok", msg=json.dumps(second, ensure_ascii=False))
        second_by_key = {d["direction_id"]: d for d in self.load_pack()["directions"]}
        self.assertEqual(set(second_by_key), {"dir_A", "dir_A__control"})
        self.assertEqual(sorted(second_by_key["dir_A"]["supporting_item_keys"]),
                         ["P1", "P2"])
        self.assertEqual(sorted(second_by_key["dir_A__control"]["supporting_item_keys"]),
                         ["P3", "P4"])
        self.assertEqual(
            [g["gap_id"] for g in second_by_key["dir_A__control"]["gap_shortlist"]],
            [g["gap_id"] for g in child_before["gap_shortlist"]])

        # Stage 3 still generates jobs for both authoritative directions.
        stage3_payload = parse(run_cli("stage3-plan", "--professor-dir", str(self.prof_dir),
                                       "--program-root", str(self.root)))
        self.assertEqual(stage3_payload["status"], "ok",
                         msg=json.dumps(stage3_payload, ensure_ascii=False))
        stage3_ckeys = {job["direction_id"] for job in stage3_payload["jobs"]}
        self.assertEqual(stage3_ckeys, {"dir_A", "dir_A__control"})


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
        state. Acceptance decides re-prompting: while the refinement is only
        proposed, the pending proposal keeps reporting needs_user_choice and
        stage2-finalize refuses to apply it; only the explicit accept command
        flips it, after which it is never re-prompted."""
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

        # Second run with an empty results dir BEFORE the user chose: the
        # entry is still only a proposal and keeps asking for the choice.
        results_dir = self.root / "resolve_results"
        for stale in results_dir.glob("resolve-*.json"):
            stale.unlink()
        pending_rerun = parse(run_cli("stage2-resolve-finalize",
                                      "--facts", str(facts_path), "--results", str(results_dir)))
        self.assertEqual(pending_rerun["status"], "ok",
                         msg=json.dumps(pending_rerun, ensure_ascii=False))
        pending_entry = next(d for d in pending_rerun["directions"]
                             if d["provisional_direction_id"] == "dir_A")
        self.assertEqual(pending_entry["resolution_type"], "refined",
                         "an unanswered proposal must be carried as-is, not reset")
        self.assertTrue(pending_rerun["needs_user_choice"],
                        "a still-proposed refinement must keep prompting the user")

        # A proposal must NEVER be applied by stage2-finalize on its own:
        # passing the sidecar while the choice is pending fails closed.
        rejected = self.run_stage2_finalize(facts_path)
        self.assertEqual(rejected["status"], "error")
        self.assertEqual(rejected["reason_code"], "resolved_directions_not_accepted")
        self.assertEqual(rejected["not_accepted_directions"], ["dir_A"])

        # The user adopts via the explicit accept command; afterwards a
        # resolve-finalize re-run must NOT re-prompt, and finalize applies.
        accepted = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))
        sidecar = json.loads((self.prof_dir / "论文分析" / "_resolved_directions.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(sidecar["directions"][0].get("acceptance"), "accepted")
        accepted_rerun = parse(run_cli("stage2-resolve-finalize",
                                       "--facts", str(facts_path), "--results", str(results_dir)))
        self.assertEqual(accepted_rerun["status"], "ok",
                         msg=json.dumps(accepted_rerun, ensure_ascii=False))
        accepted_entry = next(d for d in accepted_rerun["directions"]
                              if d["provisional_direction_id"] == "dir_A")
        self.assertEqual(accepted_entry["resolution_type"], "refined")
        self.assertFalse(accepted_rerun["needs_user_choice"],
                         "an accepted refinement must not re-prompt the user")

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        self.assertTrue(payload["resolved_directions_applied"])
        pack = self.load_pack()
        supporting = set(pack["directions"][0]["supporting_item_keys"])
        self.assertEqual(supporting, {"P1"})


class UserKeptProvisionalTests(ResolvedPipelineMixin, unittest.TestCase):
    """Choosing "keep provisional" is itself an authoritative Stage-2 decision.

    The decision must be persisted as explicit accepted resolved state (never
    by omitting --resolved-directions), so the pack always carries an explicit
    resolved_direction per direction and the decision is reused — without
    re-prompting or re-burning resolve jobs — until the resolve input changes.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _material_proposal_setup(self):
        """dir_A gets a rename proposal; dir_B stays unchanged. Returns facts_path."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"],
                            ["Future work A."]),
            self.make_paper("P2", "Catalytic Chemistry", ["catalytic", "chemistry"],
                            ["Future work B."]),
        ]
        directions = [
            self.make_direction("dir_A", ["P1"], name_ja="信号処理", name_zh="信号处理",
                                summary="signal processing"),
            self.make_direction("dir_B", ["P2"], name_ja="触媒化学", name_zh="催化化学",
                                summary="catalytic chemistry"),
        ]
        facts_path = self.write_facts(papers, directions)
        self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "適応信号処理",
                "name_zh": "自适应信号处理",
                "resolution_type": "renamed",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {"P1": "rename follows full-text evidence"},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        })
        return facts_path, papers

    def _keep_provisional(self, facts_path, ckey):
        results_dir = self.root / "resolve_results"
        return parse(run_cli("stage2-resolve-finalize",
                             "--facts", str(facts_path),
                             "--results", str(results_dir),
                             "--keep-provisional", ckey))

    def test_user_kept_provisional_still_writes_explicit_resolved_direction(self):
        facts_path, _papers = self._material_proposal_setup()
        sidecar = json.loads((self.prof_dir / "论文分析" / "_resolved_directions.json")
                             .read_text(encoding="utf-8"))
        entry = next(d for d in sidecar["directions"]
                     if d["provisional_direction_id"] == "dir_A")
        self.assertEqual(entry["acceptance"], "proposed")

        kept = self._keep_provisional(facts_path, "dir_A")
        self.assertEqual(kept["status"], "ok", msg=json.dumps(kept, ensure_ascii=False))
        self.assertEqual(kept["kept_provisional"], ["dir_A"])
        kept_entry = next(d for d in kept["directions"]
                          if d["provisional_direction_id"] == "dir_A")
        self.assertEqual(kept_entry["decision"], "user_kept_provisional")
        self.assertEqual(kept_entry["resolution_type"], "unchanged")
        self.assertFalse(kept["needs_user_choice"],
                         "the user's keep-provisional decision resolves the prompt")

        sidecar = json.loads((self.prof_dir / "论文分析" / "_resolved_directions.json")
                             .read_text(encoding="utf-8"))
        kept_entry = next(d for d in sidecar["directions"]
                          if d["provisional_direction_id"] == "dir_A")
        self.assertEqual(kept_entry["acceptance"], "accepted")
        self.assertEqual(kept_entry["decision"], "user_kept_provisional")
        self.assertEqual(kept_entry["name_ja"], "信号処理",
                         "kept provisional keeps the provisional name")

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok", msg=json.dumps(payload, ensure_ascii=False))
        pack = self.load_pack()
        for direction in pack["directions"]:
            rd = direction.get("resolved_direction")
            self.assertIsNotNone(
                rd, f"{direction['direction_id']} must carry an explicit resolved_direction")
            self.assertEqual(rd["resolved_direction_id"], direction["direction_id"])

    def test_user_kept_provisional_is_reused_until_resolve_input_changes(self):
        facts_path, papers = self._material_proposal_setup()
        self._keep_provisional(facts_path, "dir_A")

        plan = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(plan["status"], "ok", msg=json.dumps(plan, ensure_ascii=False))
        actions = {row["direction_id"]: row["action"] for row in plan["directions"]}
        self.assertEqual(
            actions, {"dir_A": "reuse", "dir_B": "reuse"},
            "an accepted keep-provisional decision must not re-emit resolve jobs "
            "while the resolve input is unchanged")

        make_facts_sidecar(Path(papers[1]["analysis_file"]), self.root / "P2.pdf",
                           ["Future work B."], topic_terms=["electro", "catalysis"])
        changed = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(changed["status"], "ok", msg=json.dumps(changed, ensure_ascii=False))
        actions = {row["direction_id"]: row["action"] for row in changed["directions"]}
        self.assertEqual(
            actions["dir_A"], "process",
            "only a changed resolve fingerprint may re-open the kept-provisional decision")


class StructuralResolutionEvidenceGateTests(ResolvedPipelineMixin, unittest.TestCase):
    """Authoritative restructuring without full-text evidence fails closed.

    The membership gate only sees papers_to_add/papers_to_remove; merged_into
    requires empty lists and renamed/name-only refined may have none, so the
    runner must deterministically demand full-text evidence for those too.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _break_facts_join(paper):
        sidecar = Path(paper["sidecar_file"])
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        payload["items"] = []
        sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")

    def test_merge_resolution_rejected_when_both_directions_lack_valid_fulltext_facts(self):
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"],
                            ["Future work A."]),
            self.make_paper("P2", "Signal Processing Applications", ["signal", "processing"],
                            ["Future work B."]),
        ]
        directions = [
            self.make_direction("dir_A", ["P1"], name_ja="信号処理", name_zh="信号处理",
                                summary="signal processing"),
            self.make_direction("dir_B", ["P2"], name_ja="信号処理応用", name_zh="信号处理应用",
                                summary="applied signal processing"),
        ]
        facts_path = self.write_facts(papers, directions)
        for paper in papers:
            self._break_facts_join(paper)

        results_dir = self.root / "resolve_results"
        results_dir.mkdir()
        write_json(results_dir / "resolve-dir_A.json", {
            "schema": 1, "kind": "resolve", "collection_key": "dir_A",
            "resolved": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "merged_into",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": "dir_B",
                "user_note": "",
            },
        })
        payload = parse(run_cli("stage2-resolve-finalize",
                                "--facts", str(facts_path),
                                "--results", str(results_dir)))
        self.assertEqual(payload["status"], "error", msg=json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["reason_code"], "invalid_result_json")
        self.assertIn("full-text", payload["message"])

    def test_rename_resolution_rejected_without_valid_fulltext_facts(self):
        paper = self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"],
                                ["Future work A."])
        facts_path = self.write_facts(
            [paper], [self.make_direction("dir_A", ["P1"], name_ja="信号処理",
                                           name_zh="信号处理", summary="signal processing")])
        self._break_facts_join(paper)

        results_dir = self.root / "resolve_results"
        results_dir.mkdir()
        write_json(results_dir / "resolve-dir_A.json", {
            "schema": 1, "kind": "resolve", "collection_key": "dir_A",
            "resolved": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "適応信号処理",
                "name_zh": "自适应信号处理",
                "resolution_type": "renamed",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        })
        payload = parse(run_cli("stage2-resolve-finalize",
                                "--facts", str(facts_path),
                                "--results", str(results_dir)))
        self.assertEqual(payload["status"], "error", msg=json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["reason_code"], "invalid_result_json")
        self.assertIn("full-text", payload["message"])


class ResolveAcceptanceBoundaryTests(ResolvedPipelineMixin, unittest.TestCase):
    """Acceptance is a machine-enforced user-choice boundary (issue #7 flow #5).

    stage2-finalize must refuse to apply a sidecar that still carries proposed
    material changes: neither passing the sidecar file directly nor keeping
    provisional for only SOME directions may smuggle an unconfirmed proposal
    into the pack, and finalize itself must never flip acceptance flags.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _two_direction_facts(self):
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"],
                            ["Future work A."]),
            self.make_paper("P2", "Catalytic Chemistry", ["catalytic", "chemistry"],
                            ["Future work B."]),
            self.make_paper("P3", "Electro Chemical Sensors", ["electro", "sensors"],
                            ["Future work C."]),
        ]
        directions = [
            self.make_direction("dir_A", ["P1"], name_ja="信号処理", name_zh="信号处理",
                                summary="signal processing"),
            self.make_direction("dir_B", ["P2", "P3"], name_ja="触媒化学", name_zh="催化化学",
                                summary="catalytic chemistry"),
        ]
        return self.write_facts(papers, directions)

    @staticmethod
    def _rename_proposal():
        return {
            "resolved_direction_id": "dir_A",
            "provisional_direction_id": "dir_A",
            "name_ja": "適応信号処理",
            "name_zh": "自适应信号处理",
            "resolution_type": "renamed",
            "papers_to_add": [],
            "papers_to_remove": [],
            "paper_justifications": {"P1": "rename follows full-text evidence"},
            "split_target": None,
            "merge_target": None,
            "user_note": "",
        }

    @staticmethod
    def _refine_out_proposal():
        return {
            "resolved_direction_id": "dir_B",
            "provisional_direction_id": "dir_B",
            "name_ja": "触媒化学",
            "name_zh": "催化化学",
            "resolution_type": "refined",
            "papers_to_add": [],
            "papers_to_remove": ["P3"],
            "paper_justifications": {"P3": "electro-sensor line is off the catalysis mainline"},
            "split_target": None,
            "merge_target": None,
            "user_note": "",
        }

    def _sidecar_entries(self):
        sidecar = json.loads((self.prof_dir / "论文分析" / "_resolved_directions.json")
                             .read_text(encoding="utf-8"))
        return {d["provisional_direction_id"]: d for d in sidecar["directions"]}

    def test_finalize_rejects_sidecar_with_unaccepted_material_proposal(self):
        """A material proposal passed directly to stage2-finalize fails closed
        and the previously accepted pack stays byte-identical."""
        facts_path = self._two_direction_facts()

        # Baseline: unchanged resolution → finalize builds the first pack.
        self.run_resolve(facts_path, {})
        baseline = self.run_stage2_finalize(facts_path)
        self.assertEqual(baseline["status"], "ok", msg=json.dumps(baseline, ensure_ascii=False))
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack_before = pack_path.read_text(encoding="utf-8")

        # A facts change re-opens dir_A and produces a material rename proposal.
        make_facts_sidecar(self.prof_dir / "论文分析" / "P1.md", self.root / "P1.pdf",
                           ["Future work A."], topic_terms=["適応", "信号処理"])
        _, proposal = self.run_resolve(facts_path, {"dir_A": self._rename_proposal()})
        self.assertTrue(proposal["needs_user_choice"])
        self.assertEqual(self._sidecar_entries()["dir_A"]["acceptance"], "proposed")

        # Passing the sidecar WITHOUT the user's choice must fail closed and
        # leave the old pack exactly as it was.
        rejected = self.run_stage2_finalize(facts_path)
        self.assertEqual(rejected["status"], "error")
        self.assertEqual(rejected["reason_code"], "resolved_directions_not_accepted")
        self.assertEqual(rejected["not_accepted_directions"], ["dir_A"])
        self.assertEqual(pack_path.read_text(encoding="utf-8"), pack_before,
                         "a rejected finalize must not touch the existing pack")

    def test_finalize_rejects_partially_kept_provisional_sidecar(self):
        """--keep-provisional for only SOME directions: the still-proposed
        remainder blocks stage2-finalize instead of being silently applied
        or marked accepted."""
        facts_path = self._two_direction_facts()
        _, proposal = self.run_resolve(facts_path, {
            "dir_A": self._rename_proposal(),
            "dir_B": self._refine_out_proposal(),
        })
        self.assertTrue(proposal["needs_user_choice"])

        results_dir = self.root / "resolve_results"
        kept = parse(run_cli("stage2-resolve-finalize", "--facts", str(facts_path),
                             "--results", str(results_dir), "--keep-provisional", "dir_A"))
        self.assertEqual(kept["status"], "ok", msg=json.dumps(kept, ensure_ascii=False))
        entries = self._sidecar_entries()
        self.assertEqual(entries["dir_A"]["acceptance"], "accepted")
        self.assertEqual(entries["dir_A"]["decision"], "user_kept_provisional")
        self.assertEqual(entries["dir_B"]["acceptance"], "proposed",
                         "keep-provisional must stay scoped to the named directions")

        rejected = self.run_stage2_finalize(facts_path)
        self.assertEqual(rejected["status"], "error")
        self.assertEqual(rejected["reason_code"], "resolved_directions_not_accepted")
        self.assertEqual(rejected["not_accepted_directions"], ["dir_B"])
        # finalize must not have flipped the remaining proposal either.
        self.assertEqual(self._sidecar_entries()["dir_B"]["acceptance"], "proposed")
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists(),
                         "a rejected finalize must not write an input pack")

    def test_resolve_accept_command_validates_keys_and_staleness(self):
        """stage2-resolve-accept is the only adopt path: it rejects unknown
        keys and stale proposals, is idempotent, and unblocks finalize."""
        facts_path = self._two_direction_facts()

        # No sidecar yet → nothing to accept.
        missing = parse(run_cli("stage2-resolve-accept", "--facts", str(facts_path),
                                "--ckeys", "dir_A"))
        self.assertEqual(missing["status"], "error")
        self.assertEqual(missing["reason_code"], "missing_resolved_directions")

        self.run_resolve(facts_path, {})
        unknown = parse(run_cli("stage2-resolve-accept", "--facts", str(facts_path),
                                "--ckeys", "dir_A__ghost"))
        self.assertEqual(unknown["status"], "error")
        self.assertEqual(unknown["reason_code"], "invalid_accept_keys")

        # A facts change re-opens both directions, then the model proposes two
        # material changes; adopt dir_A only.
        make_facts_sidecar(self.prof_dir / "论文分析" / "P1.md", self.root / "P1.pdf",
                           ["Future work A."], topic_terms=["適応", "信号処理"])
        _, proposal = self.run_resolve(facts_path, {
            "dir_A": self._rename_proposal(),
            "dir_B": self._refine_out_proposal(),
        })
        self.assertTrue(proposal["needs_user_choice"])
        first = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(first["status"], "ok", msg=json.dumps(first, ensure_ascii=False))
        self.assertEqual(first["accepted"], ["dir_A"])
        self.assertEqual(first["still_proposed"], ["dir_B"])
        # Accepting an already-accepted direction is an idempotent no-op.
        again = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(again["accepted"], [])
        self.assertEqual(again["already_accepted"], ["dir_A"])

        # A proposal whose fingerprint no longer matches the facts is stale:
        # accepting it must fail closed instead of blessing outdated evidence.
        make_facts_sidecar(self.prof_dir / "论文分析" / "P3.md", self.root / "P3.pdf",
                           ["Future work C."], topic_terms=["電気", "化学"])
        stale = self.accept_resolved(facts_path, ["dir_B"])
        self.assertEqual(stale["status"], "error")
        self.assertEqual(stale["reason_code"], "resolved_directions_stale")
        self.assertEqual(self._sidecar_entries()["dir_B"]["acceptance"], "proposed")


if __name__ == "__main__":
    unittest.main()
