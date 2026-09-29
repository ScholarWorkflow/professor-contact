"""Stage 2 early preflight cache gate regression tests (issue #11).

The preflight must decide from persisted state alone whether an accepted
``套磁候选输入.json`` can be reused verbatim, before any Zotero access, PDF
read or expensive Stage 2 evidence preparation. Anything that cannot be
proven safe falls back to the existing slow path unchanged.

Scenario letters in comments reference the issue's test plan (§29).
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"
sys.path.insert(0, str(ROOT / "scripts"))

import contact_state  # noqa: E402

PROFESSOR = "試験 教授"
YEAR = datetime.now().year


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


def make_sidecar(analysis: Path, quotes: list, page: int = 8) -> Path:
    items = [{"id": quote_id(q), "quote": q, "translation_zh": f"中译：{q[:24]}",
              "source": "Conclusion", "page": page} for q in quotes]
    sidecar = Path(str(analysis) + ".future_work.json")
    sidecar.write_text(json.dumps({
        "schema": 1, "extractor_version": "future-work-v1",
        "analysis": str(analysis), "status": "ok", "items": items},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return sidecar


class PreflightBase(unittest.TestCase):
    """Program root with one professor, two selected directions, accepted pack."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / PROFESSOR
        (self.prof_dir / "论文分析").mkdir(parents=True)
        self.gap_quotes = {
            "AAAA1111": "Future work will extend the synthetic comparison to a second input pattern.",
            "BBBB2222": "We plan to test a second synthetic processing path.",
        }
        self.facts = {
            "program_root": str(self.root), "professor_dir": str(self.prof_dir),
            "professor": PROFESSOR, "current_year": YEAR,
            "params": {"gap_scope": "selected_direction", "freshness_scope": "shortlist"},
            "papers": [], "directions": []}
        self.catalog_papers = []
        for key, year, authorship in (("AAAA1111", 2023, "corresponding"),
                                      ("BBBB2222", 2024, "first"),
                                      ("CCCC3333", 2026, "middle")):
            abstract = {"AAAA1111": "We study a synthetic comparison of input patterns.",
                        "BBBB2222": "A synthetic system for comparing two processing paths.",
                        "CCCC3333": "A deliberately unrelated synthetic example."}[key]
            paper = {"item_key": key, "title": key + " title", "year": year, "month": 5,
                     "authorship": authorship, "abstract": abstract,
                     "authors": ["Example Professor"], "has_pdf": key != "CCCC3333"}
            self.facts["papers"].append(paper)
            status = "downloaded" if key != "CCCC3333" else "unknown"
            self.catalog_papers.append({"item_key": key, "title": paper["title"],
                                        "title_zh": None, "pdf_status": status})
        (self.prof_dir / "papers.json").write_text(
            json.dumps({"papers": self.catalog_papers}, ensure_ascii=False), encoding="utf-8")
        for key, quote in self.gap_quotes.items():
            analysis = self.prof_dir / "论文分析" / f"{key}.md"
            analysis.write_text(f"# analysis {key}\n", encoding="utf-8")
            sidecar = make_sidecar(analysis, [quote])
            for paper in self.facts["papers"]:
                if paper["item_key"] == key:
                    paper["analysis_file"] = str(analysis)
                    paper["sidecar_file"] = str(sidecar)
        self.pdf_path = self.prof_dir / "论文分析" / "AAAA1111.pdf"
        self.pdf_path.write_bytes(b"%PDF-1.4 synthetic test document\n")
        self.facts["papers"][0]["pdf_file"] = str(self.pdf_path)
        self.facts["directions"] = [
            {"collection_key": "DIR00001", "name_ja": "合成输入比较", "name_zh": "合成输入比较",
             "status": "active",
             "member_keys": ["AAAA1111", "BBBB2222", "CCCC3333"],
             "relevant_keys": ["AAAA1111", "BBBB2222"], "named_keys": ["AAAA1111"],
             "user_note": "我想比较两种合成输入的处理结果。",
             "credibility": {"verdict": "站得住", "mainline": "主线",
                             "authorship_line": "corresponding_dominant", "note": "test"},
             "red_lines": []},
            {"collection_key": "DIR00002", "name_ja": "第二方向", "name_zh": "第二方向",
             "status": "active", "member_keys": ["BBBB2222"], "relevant_keys": ["BBBB2222"],
             "named_keys": [], "user_note": "第二方向的用户笔记。",
             "credibility": {}, "red_lines": []},
        ]
        self.facts_path = self.root / "facts.json"
        self.facts_path.write_text(json.dumps(self.facts, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        self.target = {
            "schema_version": 2, "kind": "professor-contact-target",
            "selected_at": "2026-01-01T00:00:00Z",
            "professor": PROFESSOR, "professor_dir": str(Path("教授研究") / "X分野" / PROFESSOR),
            "preview_path": str(Path("教授研究") / "X分野" / PROFESSOR / "方向预筛.json"),
            "preview_fingerprint": "pv-1", "preview_fingerprint_version": "v1",
            "selected_direction_ids": ["DIR00001", "DIR00002"],
            "directions": [
                {"direction_id": "DIR00001", "name_ja": "合成输入比较", "name_zh": "合成输入比较",
                 "summary_zh": "比较合成输入",
                 "members": [{"item_key": "AAAA1111", "preview_confidence": "high"},
                             {"item_key": "BBBB2222", "preview_confidence": "high"},
                             {"item_key": "CCCC3333", "preview_confidence": "low"}],
                 "user_note": "我想比较两种合成输入的处理结果。"},
                {"direction_id": "DIR00002", "name_ja": "第二方向", "name_zh": "第二方向",
                 "summary_zh": "第二条线索",
                 "members": [{"item_key": "BBBB2222", "preview_confidence": "high"}],
                 "user_note": "第二方向的用户笔记。"},
            ],
            "selection_history": [],
        }
        self.target_file = self.prof_dir / "套磁目标.json"
        self._write_target()
        self.snapshot_entry = {
            "professor": PROFESSOR,
            "professor_dir": str(Path("教授研究") / "X分野" / PROFESSOR),
            "preview_fingerprint": "pv-1",
            "input_fingerprint": "stage1-fp-1",
            "built_at": "2026-01-01T00:00:00Z", "action": "noop",
            "directions": [
                {"direction_id": "DIR00001",
                 "provisional_member_keys": ["AAAA1111", "BBBB2222", "CCCC3333"],
                 "candidate_keys": ["AAAA1111", "BBBB2222", "CCCC3333"],
                 "expansion_reasons": {"AAAA1111": ["provisional_member"],
                                       "BBBB2222": ["provisional_member"],
                                       "CCCC3333": ["provisional_member", "low_confidence_preview"]},
                 "expansion_evidence": {},
                 "pdf_readiness": {"usable_item_keys": ["AAAA1111", "BBBB2222"],
                                   "missing_item_keys": ["CCCC3333"],
                                   "unresolved_item_keys": [],
                                   "status_counts": {"downloaded": 2, "unknown": 1}}},
                {"direction_id": "DIR00002",
                 "provisional_member_keys": ["BBBB2222"],
                 "candidate_keys": ["BBBB2222"],
                 "expansion_reasons": {"BBBB2222": ["provisional_member"]},
                 "expansion_evidence": {},
                 "pdf_readiness": {"usable_item_keys": ["BBBB2222"],
                                   "missing_item_keys": [], "unresolved_item_keys": [],
                                   "status_counts": {"downloaded": 1}}},
            ]}
        self._write_snapshot()
        # Real zotero-paper-tagger ledger shape: per-professor name-variant
        # books plus per-professor human overrides under a shared file.
        self.ledger = {
            "updated_at": "2026-01-01T00:00:00Z", "overrides": {},
            "professors": {
                PROFESSOR: {"books": [{"prof_name_tokens": ["試験", "教授"],
                                       "seed_count": 3, "auto": [], "conflicted": [],
                                       "offenders": [], "typos": [], "mashes": []}],
                            "seed_count": 3},
                "別の教授": {"books": [{"prof_name_tokens": ["別", "教授"],
                                        "seed_count": 2, "auto": [], "conflicted": [],
                                        "offenders": [], "typos": [], "mashes": []}],
                             "seed_count": 2},
            }}
        ledger = self.root / "教授研究" / "_署名对照.json"
        ledger.write_text(json.dumps(self.ledger, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    # -- fixture writers ----------------------------------------------------

    def _write_target(self):
        self.target_file.write_text(
            json.dumps(self.target, ensure_ascii=False, indent=1), encoding="utf-8")

    def _write_snapshot(self):
        snapshot = {"schema_version": 1, "kind": "professor-contact-stage1",
                    "updated_at": "2026-01-01T00:00:00Z", "professors": [self.snapshot_entry]}
        path = self.root / "教授研究" / "套磁阶段1候选.json"
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")

    def _read_pack(self) -> dict:
        return json.loads((self.prof_dir / "套磁候选输入.json").read_text(encoding="utf-8"))

    def _write_pack(self, pack: dict):
        contact_state.atomic_json(self.prof_dir / "套磁候选输入.json", pack)

    def _read_meta(self) -> dict:
        return self._read_pack()["cache"]["preflight"]

    # -- Stage 2 accepted state ---------------------------------------------

    def write_stage2_results(self) -> Path:
        results = self.root / "results"
        results.mkdir(parents=True, exist_ok=True)
        rows = [{"gap_id": quote_id(quote), "status": "open", "candidate_paper_ids": [],
                 "evidence": f"无更晚论文实现该点（{key}）", "confidence": "high"}
                for key, quote in self.gap_quotes.items()]
        (results / "freshness-DIR00001.json").write_text(json.dumps({
            "schema": 1, "kind": "freshness", "collection_key": "DIR00001",
            "results": rows}, ensure_ascii=False), encoding="utf-8")
        (results / "freshness-DIR00002.json").write_text(json.dumps({
            "schema": 1, "kind": "freshness", "collection_key": "DIR00002",
            "results": [rows[1]]}, ensure_ascii=False), encoding="utf-8")
        g1 = quote_id(self.gap_quotes["AAAA1111"])
        g2 = quote_id(self.gap_quotes["BBBB2222"])
        (results / "narrative.json").write_text(json.dumps({
            "schema": 1, "kind": "narrative", "directions": [
                {"collection_key": "DIR00001",
                 "positioning": [{"kind": "para",
                                  "text": "教授从 {{P:AAAA1111}} 起研究合成输入比较；{{G:" + g1 + "}} 是延伸点。",
                                  "refs": ["paper:AAAA1111", "gap:" + g1],
                                  "concrete_object": "合成输入与第二种模式",
                                  "input_example": "输入一组固定的合成样本",
                                  "output_example": "系统给出两种处理结果"}],
                 "gap_notes": [{"gap_id": g1, "summary": "扩展到第二种输入模式",
                                "explanation": "研究计划比较另一种合成场景。"}]},
                {"collection_key": "DIR00002",
                 "positioning": [{"kind": "para",
                                  "text": "教授的 {{P:BBBB2222}} 开辟了第二方向；{{G:" + g2 + "}} 待延伸。",
                                  "refs": ["paper:BBBB2222", "gap:" + g2],
                                  "concrete_object": "第二种处理路径",
                                  "input_example": "输入第二类处理请求",
                                  "output_example": "给出该路径的评估结果"}],
                 "gap_notes": [{"gap_id": g2, "summary": "测试第二条处理路径",
                                "explanation": "计划验证第二条路径的可行性。"}]},
            ]}, ensure_ascii=False), encoding="utf-8")
        return results

    def stage2_finalize(self):
        facts = self.facts_path
        results = self.write_stage2_results()
        out = parse(run_cli("stage2-finalize", "--facts", facts, "--results", results))
        self.assertEqual(out["status"], "ok", out)
        return out

    def record_validation(self, result="pass", rounds=1, keys=("DIR00001", "DIR00002")):
        validation = {"results": [{"direction_id": key, "result": result,
                                   "rounds": rounds, "issues": []} for key in keys]}
        path = self.root / "validation.json"
        path.write_text(json.dumps(validation, ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage2-record-validation", "--professor-dir", self.prof_dir,
                            "--validation-file", path))
        self.assertEqual(out["status"], "ok", out)

    def seed_preflight_meta(self, current_year=None, **param_overrides):
        """Seed cache.preflight the way stage2-finalize does with a preflight file."""
        pack = self._read_pack()
        ctx = contact_state.Stage2Context(self.facts_path)
        params = contact_state.stage2_preflight_params(
            param_overrides.get("paper_analysis", "relevant"),
            param_overrides.get("gap_scope", "selected_direction"),
            param_overrides.get("freshness_scope", "shortlist"),
            param_overrides.get("max_relevant_papers"))
        meta = contact_state.stage2_preflight_metadata(
            program_root=self.root, professor_dir=self.prof_dir,
            target=contact_state.read_stage2_target(
                self.target_file, self.root, PROFESSOR),
            snapshot_entry=contact_state.read_stage1_professor_entry(self.root, PROFESSOR),
            pack_directions=pack["directions"], params=params,
            current_year=current_year if current_year is not None else YEAR,
            ctx=ctx, cache_entries=contact_state.load_freshness_cache(self.prof_dir))
        pack.setdefault("cache", {})["preflight"] = meta
        self._write_pack(pack)
        return meta

    def bind_facts_to_plan(self, plan_path):
        """Record the preflight proof id in facts the way analyzer Step 6.1 does."""
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        self.facts["stage2_preflight"] = {"preflight_id": plan.get("preflight_id")}
        self.facts_path.write_text(json.dumps(self.facts, ensure_ascii=False, indent=1),
                                   encoding="utf-8")

    def build_accepted_state(self):
        self.stage2_finalize()
        self.record_validation()
        self.seed_preflight_meta()

    # -- preflight invocation ------------------------------------------------

    def preflight(self, **overrides):
        args = argparse.Namespace(
            program_root=str(self.root), professor=PROFESSOR,
            target_file=str(self.target_file),
            paper_analysis=overrides.get("paper_analysis", "relevant"),
            gap_scope=overrides.get("gap_scope", "selected_direction"),
            freshness_scope=overrides.get("freshness_scope", "shortlist"),
            max_relevant_papers=overrides.get("max_relevant_papers"))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            contact_state.cmd_stage2_preflight(args)
        return json.loads(buffer.getvalue())

    def forbid_pdf_reads(self):
        """Fail the test if any code path reads PDF bytes during preflight."""
        original = Path.read_bytes

        def guarded(path):
            if str(path).endswith(".pdf"):
                raise AssertionError(f"preflight read PDF bytes: {path}")
            return original(path)

        Path.read_bytes = guarded
        self.addCleanup(setattr, Path, "read_bytes", original)

    def direction(self, payload, ckey):
        return next(entry for entry in payload["directions"]
                    if entry["direction_id"] == ckey)


class TestPreflightDecision(PreflightBase):
    def test_a_legacy_pack_falls_back_to_process(self):
        self.stage2_finalize()
        self.record_validation()
        payload = self.preflight()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["action"], "process")
        self.assertIn("legacy_pack_no_preflight", payload["reason_codes"])
        direction = self.direction(payload, "DIR00001")
        self.assertEqual(direction["action"], "process")
        self.assertIn("preflight_record_missing", direction["reason_codes"])

    def test_b_perfect_no_change_reuses_without_pdf_reads(self):
        self.build_accepted_state()
        self.forbid_pdf_reads()
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertEqual(payload["reason_codes"], [])
        direction = self.direction(payload, "DIR00001")
        self.assertEqual(direction["action"], "reuse")
        self.assertEqual(direction["reason_codes"], [])

    def test_c_target_note_change_invalidates_only_that_direction(self):
        self.build_accepted_state()
        self.target["directions"][0]["user_note"] = "改过之后的笔记。"
        self._write_target()
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        changed = self.direction(payload, "DIR00001")
        self.assertEqual(changed["action"], "process")
        self.assertIn("target_changed", changed["reason_codes"])
        retained = self.direction(payload, "DIR00002")
        self.assertEqual(retained["action"], "reuse", retained)

    def test_d_selection_add_invalidates_only_new_direction(self):
        self.build_accepted_state()
        self.target["selected_direction_ids"].append("DIR00003")
        self.target["directions"].append(
            {"direction_id": "DIR00003", "name_ja": "第三方向", "name_zh": "第三方向",
             "summary_zh": "第三条线索",
             "members": [{"item_key": "CCCC3333", "preview_confidence": "high"}],
             "user_note": ""})
        self.snapshot_entry["input_fingerprint"] = "stage1-fp-3"
        self.snapshot_entry["directions"].append(
            {"direction_id": "DIR00003", "provisional_member_keys": ["CCCC3333"],
             "candidate_keys": ["CCCC3333"],
             "expansion_reasons": {"CCCC3333": ["provisional_member"]},
             "expansion_evidence": {},
             "pdf_readiness": {"usable_item_keys": [], "missing_item_keys": ["CCCC3333"],
                               "unresolved_item_keys": [], "status_counts": {"unknown": 1}}})
        self._write_target()
        self._write_snapshot()
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        new_direction = self.direction(payload, "DIR00003")
        self.assertEqual(new_direction["action"], "process")
        self.assertIn("preflight_record_missing", new_direction["reason_codes"])
        self.assertIn("validator_not_accepted", new_direction["reason_codes"])
        self.assertEqual(self.direction(payload, "DIR00001")["action"], "reuse")
        self.assertEqual(self.direction(payload, "DIR00002")["action"], "reuse")

    def test_e_stage1_candidate_change_marks_affected_direction(self):
        self.build_accepted_state()
        self.snapshot_entry["directions"][0]["candidate_keys"].append("DDDD4444")
        self.snapshot_entry["input_fingerprint"] = "stage1-fp-2"
        self._write_snapshot()
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("stage1_professor_changed", payload["reason_codes"])
        changed = self.direction(payload, "DIR00001")
        self.assertEqual(changed["action"], "process")
        self.assertIn("candidate_set_changed", changed["reason_codes"])
        self.assertEqual(self.direction(payload, "DIR00002")["action"], "reuse")

    def test_f_stage1_fingerprint_change_blocks_reuse_all(self):
        self.build_accepted_state()
        self.snapshot_entry["input_fingerprint"] = "stage1-fp-rebuilt"
        self._write_snapshot()
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("stage1_professor_changed", payload["reason_codes"])

    def test_g_whole_preview_fingerprint_alone_does_not_invalidate(self):
        self.build_accepted_state()
        self.target["preview_fingerprint"] = "pv-2"
        self.snapshot_entry["preview_fingerprint"] = "pv-2"
        self._write_target()
        self._write_snapshot()
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)

    def test_h_papers_catalog_change_blocks_reuse_all(self):
        self.build_accepted_state()
        catalog = json.loads((self.prof_dir / "papers.json").read_text(encoding="utf-8"))
        catalog["papers"][2]["pdf_status"] = "downloaded"
        (self.prof_dir / "papers.json").write_text(
            json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("papers_catalog_changed", payload["reason_codes"])

    def test_i_authorship_ledger_change_blocks_reuse_all(self):
        self.build_accepted_state()
        ledger = self.root / "教授研究" / "_署名对照.json"
        ledger.write_text(json.dumps({"entries": {"changed": True}}, ensure_ascii=False),
                          encoding="utf-8")
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("authorship_ledger_changed", payload["reason_codes"])
        ledger.unlink()
        payload = self.preflight()
        self.assertIn("authorship_ledger_changed", payload["reason_codes"])

    def _write_catalog(self):
        (self.prof_dir / "papers.json").write_text(
            json.dumps({"papers": self.catalog_papers}, ensure_ascii=False), encoding="utf-8")

    def _write_ledger(self):
        (self.root / "教授研究" / "_署名对照.json").write_text(
            json.dumps(self.ledger, ensure_ascii=False), encoding="utf-8")

    def test_i2_noncandidate_catalog_addition_keeps_reuse_all(self):
        self.build_accepted_state()
        catalog = json.loads((self.prof_dir / "papers.json").read_text(encoding="utf-8"))
        catalog["papers"].append({"item_key": "DDDD4444", "title": "unrelated paper",
                                  "year": 2026, "pdf_status": "downloaded"})
        (self.prof_dir / "papers.json").write_text(
            json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertNotIn("papers_catalog_changed", payload["reason_codes"])

    def test_i3_other_professors_ledger_and_rebuild_timestamp_keep_reuse_all(self):
        self.build_accepted_state()
        self.ledger["professors"]["別の教授"]["seed_count"] = 99
        self.ledger["updated_at"] = "2026-08-01T00:00:00Z"
        self._write_ledger()
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertNotIn("authorship_ledger_changed", payload["reason_codes"])

    def test_i4_current_professor_ledger_change_blocks_reuse_all(self):
        self.build_accepted_state()
        self.ledger["professors"][PROFESSOR]["conflicted"] = [
            {"kind": "abbr", "example": "S. A.", "count": 1, "reason": "ambiguous"}]
        self._write_ledger()
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("authorship_ledger_changed", payload["reason_codes"])

    def test_i5_malformed_catalog_or_ledger_fails_closed(self):
        self.build_accepted_state()
        catalog_path = self.prof_dir / "papers.json"
        for broken in ('{"papers": "garbage"}', "{not json at all"):
            catalog_path.write_text(broken, encoding="utf-8")
            payload = self.preflight()
            self.assertEqual(payload["action"], "process", broken)
            self.assertIn("papers_catalog_changed", payload["reason_codes"])
        catalog_path.unlink()
        payload = self.preflight()
        self.assertIn("papers_catalog_changed", payload["reason_codes"])
        self._write_catalog()
        ledger_path = self.root / "教授研究" / "_署名对照.json"
        for broken in ('{"professors": ["not", "a", "dict"]}',
                       '{"overrides": "garbage", "professors": {}}', "{broken"):
            ledger_path.write_text(broken, encoding="utf-8")
            payload = self.preflight()
            self.assertEqual(payload["action"], "process", broken)
            self.assertIn("authorship_ledger_changed", payload["reason_codes"])
        ledger_path.unlink()
        payload = self.preflight()
        self.assertIn("authorship_ledger_changed", payload["reason_codes"])

    def test_i6_noncandidate_catalog_change_does_not_break_finalize_seeding(self):
        self.build_accepted_state()
        catalog = json.loads((self.prof_dir / "papers.json").read_text(encoding="utf-8"))
        catalog["papers"].append({"item_key": "EEEE5555", "title": "later unrelated paper",
                                  "year": 2026, "pdf_status": "unknown"})
        (self.prof_dir / "papers.json").write_text(
            json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
        plan_payload = self.preflight()
        self.assertEqual(plan_payload["action"], "reuse_all")
        plan = self.root / "preflight.json"
        plan.write_text(json.dumps(plan_payload, ensure_ascii=False), encoding="utf-8")
        self.bind_facts_to_plan(plan)
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.write_stage2_results(),
                            "--preflight-file", plan))
        self.assertEqual(out["status"], "ok", out)
        # finalize seeds the same candidate-view fingerprint preflight computed
        self.assertEqual(self._read_meta()["program_inputs"],
                         plan_payload["preflight_inputs"]["program_inputs"])

    def test_j_deleted_artifact_prevents_reuse(self):
        self.build_accepted_state()
        Path(self.facts["papers"][1]["sidecar_file"]).unlink()
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        direction = self.direction(payload, "DIR00001")
        self.assertIn("artifact_missing", direction["reason_codes"])
        self.assertEqual(self.direction(payload, "DIR00002")["action"], "process")
        self.assertIn("artifact_missing", self.direction(payload, "DIR00002")["reason_codes"])

    def test_k_artifact_stat_change_prevents_reuse_without_pdf_reads(self):
        self.build_accepted_state()
        os.utime(self.pdf_path, ns=(1_000_000_000_000_000_000, 1_000_000_000_000_000_000))
        self.forbid_pdf_reads()
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("artifact_changed", self.direction(payload, "DIR00001")["reason_codes"])
        analysis = Path(self.facts["papers"][0]["analysis_file"])
        with analysis.open("a", encoding="utf-8") as handle:
            handle.write("\nappended\n")
        payload = self.preflight()
        self.assertIn("artifact_changed", self.direction(payload, "DIR00001")["reason_codes"])

    def test_l_freshness_cache_change_prevents_reuse(self):
        self.build_accepted_state()
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        gap_id = quote_id(self.gap_quotes["AAAA1111"])
        cache["entries"][gap_id]["status"] = "partial"
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("freshness_cache_changed",
                      self.direction(payload, "DIR00001")["reason_codes"])
        cache_path.unlink()
        payload = self.preflight()
        self.assertIn("freshness_cache_changed",
                      self.direction(payload, "DIR00001")["reason_codes"])

    def test_m_param_changes_block_reuse(self):
        self.build_accepted_state()
        for overrides in ({"paper_analysis": "all"}, {"gap_scope": "relevant"},
                          {"freshness_scope": "full"}, {"max_relevant_papers": 5}):
            payload = self.preflight(**overrides)
            self.assertEqual(payload["action"], "process", overrides)
            self.assertIn("params_changed", payload["reason_codes"], overrides)
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all")
        meta = self._read_meta()
        meta["current_year"] = YEAR - 1
        pack = self._read_pack()
        pack["cache"]["preflight"] = meta
        self._write_pack(pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("params_changed", payload["reason_codes"])

    def test_n_version_changes_block_reuse(self):
        self.build_accepted_state()
        pack = self._read_pack()
        meta = pack["cache"]["preflight"]
        meta["version"] = "stage2-preflight-v0"
        self._write_pack(pack)
        payload = self.preflight()
        self.assertIn("preflight_version_changed", payload["reason_codes"])
        pack = self._read_pack()
        pack["cache"]["preflight"]["version"] = contact_state.STAGE2_PREFLIGHT_VERSION
        pack["cache"]["preflight"]["resolution_semantics_version"] = 0
        self._write_pack(pack)
        payload = self.preflight()
        self.assertIn("resolution_semantics_changed", payload["reason_codes"])
        self.assertNotIn("preflight_version_changed", payload["reason_codes"])

    def test_o_pack_integrity_mismatch_blocks_reuse(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["directions"][0]["name_ja"] = "手改的方向名"
        self._write_pack(pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("pack_integrity_mismatch", payload["reason_codes"])

    def test_p_validator_gate(self):
        self.build_accepted_state()
        pack = self._read_pack()
        del pack["validator"]
        self._write_pack(pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("validator_not_accepted",
                      self.direction(payload, "DIR00001")["reason_codes"])
        self.record_validation(result="fail_after_2_rounds", rounds=2)
        payload = self.preflight()
        self.assertIn("validator_not_accepted",
                      self.direction(payload, "DIR00001")["reason_codes"])
        self.record_validation(result="skipped", rounds=0)
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)

    def test_partial_invalidation_keeps_unaffected_direction_reusable(self):
        self.build_accepted_state()
        self.snapshot_entry["directions"][1]["candidate_keys"].append("EEEE5555")
        self.snapshot_entry["input_fingerprint"] = "stage1-fp-2"
        self._write_snapshot()
        payload = self.preflight()
        self.assertEqual(payload["action"], "process")
        self.assertIn("stage1_professor_changed", payload["reason_codes"])
        self.assertEqual(self.direction(payload, "DIR00001")["action"], "reuse")
        changed = self.direction(payload, "DIR00002")
        self.assertEqual(changed["action"], "process")
        self.assertIn("candidate_set_changed", changed["reason_codes"])
        plan = parse(run_cli("stage2-plan", "--facts", self.facts_path))
        self.assertEqual(plan["status"], "ok")
        by_key = {entry["direction_id"]: entry for entry in plan["directions"]}
        self.assertEqual(by_key["DIR00001"]["action"], "reuse")
        self.assertEqual(by_key["DIR00002"]["action"], "reuse")


class TestPreflightGuardrails(PreflightBase):
    def test_invalid_params_fail_fast(self):
        for overrides in ({"paper_analysis": "bogus"}, {"gap_scope": "bogus"},
                          {"freshness_scope": "bogus"}, {"max_relevant_papers": 0}):
            with self.assertRaises(SystemExit):
                self.preflight(**overrides)

    def test_missing_target_state_is_a_hard_error(self):
        """S0-ISO-5: the retired program-level table is not a Stage 2 fallback."""
        self.target_file.unlink()
        program_table = self.root / "教授研究" / "套磁目标.json"
        program_table.write_text(json.dumps(
            {"schema_version": 2, "kind": "professor-contact-target",
             **{key: value for key, value in self.target.items()
                if key not in ("schema_version", "kind")}},
            ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.preflight()
        program_table.unlink()
        with self.assertRaises(SystemExit):
            self.preflight()

    def test_preflight_never_constructs_stage2_context_or_reads_analysis_bytes(self):
        self.build_accepted_state()
        self.forbid_pdf_reads()
        original_open = Path.open

        opened = []

        def guarded_open(path, *args, **kwargs):
            opened.append(str(path))
            return original_open(path, *args, **kwargs)

        Path.open = guarded_open
        self.addCleanup(setattr, Path, "open", original_open)
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all")
        for path in opened:
            self.assertFalse(path.endswith(".pdf"), path)


class TestFinalizePreflightWiring(PreflightBase):
    """stage2-finalize seeding + --preflight-file TOCTOU guard (issue §17/§19)."""

    def save_preflight_file(self, name="preflight.json", **overrides) -> Path:
        payload = self.preflight(**overrides)
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_legacy_slow_path_seeds_metadata_for_next_run(self):
        self.stage2_finalize()
        self.record_validation()
        self.assertIn("legacy_pack_no_preflight", self.preflight()["reason_codes"])
        plan = self.save_preflight_file()
        self.bind_facts_to_plan(plan)
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.root / "results",
                            "--preflight-file", plan))
        self.assertEqual(out["status"], "ok", out)
        pack = self._read_pack()
        self.assertIn("preflight", pack["cache"])
        self.assertEqual(pack["cache"]["preflight"]["accepted_directions_sha256"],
                         contact_state.sha256_obj(pack["directions"]))
        self.assertIn("validator", pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)

    def test_finalize_without_preflight_file_stays_legacy(self):
        self.stage2_finalize()
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.root / "results"))
        self.assertEqual(out["status"], "ok", out)
        self.assertNotIn("preflight", self._read_pack().get("cache", {}))

    def test_finalize_race_on_target_change_writes_nothing(self):
        self.build_accepted_state()
        plan = self.save_preflight_file()
        pack_before = (self.prof_dir / "套磁候选输入.json").read_bytes()
        md_before = (self.prof_dir / "套磁候选分析.md").read_bytes()
        cache_before = (self.prof_dir / "论文分析" / "_freshness_cache.json").read_bytes()
        self.target["directions"][0]["user_note"] = "preflight 之后的修改。"
        self._write_target()
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.root / "results",
                            "--preflight-file", plan))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "preflight_inputs_changed")
        self.assertEqual((self.prof_dir / "套磁候选输入.json").read_bytes(), pack_before)
        self.assertEqual((self.prof_dir / "套磁候选分析.md").read_bytes(), md_before)
        self.assertEqual((self.prof_dir / "论文分析" / "_freshness_cache.json").read_bytes(),
                         cache_before)

    def test_finalize_race_on_stage1_and_papers_changes_writes_nothing(self):
        self.build_accepted_state()
        changed_catalog = json.loads(
            (self.prof_dir / "papers.json").read_text(encoding="utf-8"))
        changed_catalog["papers"][0]["title"] = "Late title edit"
        for mutate in (
                lambda: (self.snapshot_entry.update(
                    {"input_fingerprint": "late-stage1-fp"}), self._write_snapshot()),
                lambda: (self.prof_dir / "papers.json").write_text(
                    json.dumps(changed_catalog, ensure_ascii=False), encoding="utf-8")):
            plan = self.save_preflight_file()
            pack_before = (self.prof_dir / "套磁候选输入.json").read_bytes()
            mutate()
            out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                                "--results", self.root / "results",
                                "--preflight-file", plan))
            self.assertEqual(out["status"], "needs_refresh", out)
            self.assertEqual(out["reason_code"], "preflight_inputs_changed")
            self.assertEqual((self.prof_dir / "套磁候选输入.json").read_bytes(), pack_before)

    def test_finalize_race_on_selection_change_writes_nothing(self):
        self.build_accepted_state()
        plan = self.save_preflight_file()
        pack_before = (self.prof_dir / "套磁候选输入.json").read_bytes()
        self.target["selected_direction_ids"].pop()
        self._write_target()
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.root / "results",
                            "--preflight-file", plan))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertIn("selected_direction_ids", out["drift"])
        self.assertEqual((self.prof_dir / "套磁候选输入.json").read_bytes(), pack_before)

    def test_finalize_preflight_file_must_match_professor(self):
        self.stage2_finalize()
        plan_path = self.root / "preflight.json"
        plan_path.write_text(json.dumps(
            {"status": "ok", "professor": "別の教授", "preflight_inputs": {}},
            ensure_ascii=False), encoding="utf-8")
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.root / "results",
                            "--preflight-file", plan_path))
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_params")

    def test_finalize_preflight_file_must_be_a_preflight_payload(self):
        self.stage2_finalize()
        plan_path = self.root / "preflight.json"
        plan_path.write_text(json.dumps({"unrelated": True}), encoding="utf-8")
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.root / "results",
                            "--preflight-file", plan_path))
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_params")

    def test_stage3_plan_consumes_pack_with_preflight_cache(self):
        self.build_accepted_state()
        fps = {d["direction_id"]: d["input_fingerprint"]
               for d in self._read_pack()["directions"]}
        out = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                            "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertTrue(out["write_needed"])
        self.assertEqual({d["direction_id"]: d["input_fingerprint"]
                          for d in self._read_pack()["directions"]}, fps)

    def test_record_validation_preserves_preflight_cache(self):
        self.build_accepted_state()
        self.record_validation()
        pack = self._read_pack()
        self.assertIn("preflight", pack["cache"])
        self.assertIn("validator", pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)


if __name__ == "__main__":
    unittest.main()
