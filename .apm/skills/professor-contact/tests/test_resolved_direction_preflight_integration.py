"""Integration regressions: issue #7 resolved directions × issue #11 preflight.

The early preflight must be able to PROVE the authoritative resolved-direction
state, not just the old provisional one-to-one pack layout:

1. semantics version bump — packs accepted under older resolution semantics
   cannot reuse_all; one new Stage-2 run re-arms the early gate.
2. provisional→resolved mapping — an accepted split (1 provisional → N
   resolved) and an accepted merge (N provisional → 1 resolved) both hit
   reuse_all on a fully unchanged second run, with identical Stage-3
   visibility; dropping a resolved entry from the pack is detected.
3. resolution evidence universe — a candidate outside every direction's
   relevant/gap scope joins the reuse identity via candidate-union artifact
   guards: its facts change must miss the early gate and re-trigger the
   affected resolution, while analysis-Markdown-only edits may force the slow
   path but never re-burn accepted resolve jobs.
4. proof binding — a `_resolved_directions.json` produced under one
   preflight/facts generation cannot be accepted or applied under another;
   refusals are zero-write and the round recovers by re-running resolve.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import contact_state  # noqa: E402
from test_stage2_preflight import PreflightBase, make_sidecar, parse, quote_id, run_cli  # noqa: E402
from test_stage2_resolved_direction import make_facts_sidecar  # noqa: E402


class ResolvedPreflightBase(PreflightBase):
    """PreflightBase plus valid full-text facts for the candidate papers."""

    def setUp(self):
        super().setUp()
        self.with_candidate_fulltext = False
        self.cccc_quote = "Future work will broaden the synthetic comparison corpus."
        self.add_valid_facts("AAAA1111", ["synthetic", "comparison", "input"],
                             self.gap_quotes["AAAA1111"])
        self.add_valid_facts("BBBB2222", ["synthetic", "comparison", "path"],
                             self.gap_quotes["BBBB2222"])

    # -- fixture helpers -----------------------------------------------------

    def write_facts(self):
        self.facts_path.write_text(json.dumps(self.facts, ensure_ascii=False, indent=1),
                                   encoding="utf-8")

    def add_valid_facts(self, key, topic_terms, quote):
        """Give an existing analyzed paper a facts sidecar (facts_state=valid)."""
        paper = next(p for p in self.facts["papers"] if p["item_key"] == key)
        analysis = Path(paper["analysis_file"])
        pdf = self.prof_dir / "论文分析" / f"{key}.pdf"
        pdf.write_bytes(b"%PDF-1.4 synthetic evidence for " + key.encode() + b"\n")
        paper["pdf_file"] = str(pdf)
        paper["has_pdf"] = True
        paper["facts_file"] = str(analysis) + ".facts.json"
        make_facts_sidecar(analysis, pdf, [quote], topic_terms=topic_terms)
        self.write_facts()

    def add_candidate_fulltext(self, key="CCCC3333"):
        """Attach full analysis + facts to a candidate the relevance gate skipped.

        CCCC3333 is in DIR00001's Stage-1 candidate union but not in
        relevant_keys and originally has no analysis at all — exactly the
        "full text could rescue it back" candidate the resolution evidence
        universe must cover.
        """
        paper = next(p for p in self.facts["papers"] if p["item_key"] == key)
        analysis = self.prof_dir / "论文分析" / f"{key}.md"
        analysis.write_text(f"# analysis {key}\n", encoding="utf-8")
        sidecar = make_sidecar(analysis, [self.cccc_quote])
        pdf = self.prof_dir / "论文分析" / f"{key}.pdf"
        pdf.write_bytes(b"%PDF-1.4 synthetic evidence for " + key.encode() + b"\n")
        paper.update({"analysis_file": str(analysis), "sidecar_file": str(sidecar),
                      "facts_file": str(analysis) + ".facts.json",
                      "pdf_file": str(pdf), "has_pdf": True})
        make_facts_sidecar(analysis, pdf, [self.cccc_quote],
                           topic_terms=["synthetic", "comparison", "corpus"])
        self.with_candidate_fulltext = True
        self.write_facts()

    def write_stage2_results(self):
        results = super().write_stage2_results()
        if self.with_candidate_fulltext:
            # CCCC3333's future-work sidecar joins the DIR00001 gap pool, so
            # its gap needs a freshness row for finalize to accept the round.
            path = results / "freshness-DIR00001.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["results"].append({
                "gap_id": quote_id(self.cccc_quote), "status": "open",
                "candidate_paper_ids": [],
                "evidence": "无更晚论文实现该点（CCCC3333）", "confidence": "high"})
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        return results

    # -- round helpers -------------------------------------------------------

    @property
    def results_dir(self) -> Path:
        return self.root / "results"

    def start_round(self):
        """Run preflight, save its payload, and bind the facts run to its proof."""
        plan = self.preflight()
        self.assertEqual(plan["action"], "process", plan)
        plan_path = self.root / "stage2-preflight.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        self.bind_facts_to_plan(plan_path)
        return plan_path

    def write_resolve_result(self, ckey, resolved):
        self.results_dir.mkdir(parents=True, exist_ok=True)
        (self.results_dir / f"resolve-{ckey}.json").write_text(json.dumps(
            {"schema": 1, "kind": "resolve", "collection_key": ckey,
             "resolved": resolved}, ensure_ascii=False, indent=1), encoding="utf-8")

    def resolve_finalize(self):
        out = parse(run_cli("stage2-resolve-finalize", "--facts", self.facts_path,
                            "--results", self.results_dir))
        self.assertEqual(out["status"], "ok", out)
        return out

    def accept(self, ckeys):
        out = parse(run_cli("stage2-resolve-accept", "--facts", self.facts_path,
                            "--ckeys", ",".join(ckeys)))
        self.assertEqual(out["status"], "ok", out)
        return out

    def finalize(self, plan_path):
        out = parse(run_cli(
            "stage2-finalize", "--facts", self.facts_path,
            "--results", self.write_stage2_results(),
            "--preflight-file", plan_path,
            "--resolved-directions",
            str(self.prof_dir / "论文分析" / "_resolved_directions.json")))
        self.assertEqual(out["status"], "ok", out)
        return out

    def stage3_direction_keys(self):
        out = parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                            "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        return sorted(job["direction_id"] for job in out["jobs"])


class TestSemanticsVersionBump(ResolvedPreflightBase):
    """Requirement 1: the semantics bump gates old packs through the slow path."""

    def test_old_semantics_pack_cannot_reuse_all_and_re_arms_after_one_run(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"]["preflight"]["resolution_semantics_version"] = \
            contact_state.STAGE2_RESOLUTION_SEMANTICS_VERSION - 1
        self._write_pack(pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("resolution_semantics_changed", payload["reason_codes"], payload)

        # One full new-semantics Stage-2 run (finalize with the preflight file
        # re-seeds cache.preflight) re-arms the early gate for the next run.
        plan_path = self.start_round()
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.write_stage2_results(),
                            "--preflight-file", plan_path))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(self._read_meta()["resolution_semantics_version"],
                         contact_state.STAGE2_RESOLUTION_SEMANTICS_VERSION)
        self.assertEqual(self.preflight()["action"], "reuse_all", self.preflight())


class TestResolvedSetReuse(ResolvedPreflightBase):
    """Requirement 2: the provisional→resolved mapping is provable for reuse."""

    def _accept_split(self):
        plan_path = self.start_round()
        self.write_resolve_result("DIR00001", {
            "resolved_direction_id": "DIR00001", "provisional_direction_id": "DIR00001",
            "name_ja": "合成输入比较", "name_zh": "合成输入比较",
            "resolution_type": "split_from",
            "papers_to_add": ["BBBB2222"], "papers_to_remove": [],
            "paper_justifications": {"BBBB2222": "Second processing path clusters separately."},
            "split_target": "DIR00001__sub", "merge_target": None,
            "user_note": "我想比较两种合成输入的处理结果。"})
        fin = self.resolve_finalize()
        self.assertTrue(fin["needs_user_choice"], fin)
        self.accept(["DIR00001"])
        return self.finalize(plan_path)

    def test_accepted_split_reuses_all_with_identical_stage3_visibility(self):
        self._accept_split()
        pack = self._read_pack()
        self.assertEqual(sorted(d["direction_id"] for d in pack["directions"]),
                         ["DIR00001", "DIR00001__sub", "DIR00002"])
        child = next(d for d in pack["directions"] if d["direction_id"] == "DIR00001__sub")
        self.assertEqual(child["resolved_direction"]["provisional_direction_id"], "DIR00001")
        self.record_validation(keys=("DIR00001", "DIR00001__sub", "DIR00002"))
        stage3_first = self.stage3_direction_keys()
        self.assertEqual(stage3_first, ["DIR00001", "DIR00001__sub", "DIR00002"])

        # Fully unchanged second run: the split child keeps early reuse via its
        # stable resolved ID — no preflight_record_missing loop.
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertEqual(self.stage3_direction_keys(), stage3_first)

    def test_dropping_the_split_child_from_the_pack_blocks_reuse(self):
        self._accept_split()
        self.record_validation(keys=("DIR00001", "DIR00001__sub", "DIR00002"))
        pack = self._read_pack()
        pack["directions"] = [d for d in pack["directions"]
                              if d["direction_id"] != "DIR00001__sub"]
        self._write_pack(pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        source = self.direction(payload, "DIR00001")
        self.assertIn("resolved_set_changed", source["reason_codes"], source)

    def test_accepted_merge_reuses_all_and_keeps_single_stage3_direction(self):
        plan_path = self.start_round()
        self.write_resolve_result("DIR00002", {
            "resolved_direction_id": "DIR00002", "provisional_direction_id": "DIR00002",
            "name_ja": "第二方向", "name_zh": "第二方向",
            "resolution_type": "merged_into",
            "papers_to_add": [], "papers_to_remove": [],
            "paper_justifications": {},
            "split_target": None, "merge_target": "DIR00001", "user_note": ""})
        fin = self.resolve_finalize()
        self.assertTrue(fin["needs_user_choice"], fin)
        self.accept(["DIR00002"])
        self.finalize(plan_path)

        pack = self._read_pack()
        self.assertEqual([d["direction_id"] for d in pack["directions"]], ["DIR00001"])
        target = pack["directions"][0]
        self.assertEqual(target["resolved_direction"]["merged_from"], ["DIR00002"])
        # The merged-away source keeps its provenance mapping for freshness.
        self.assertEqual(self._read_meta()["directions"]["DIR00002"]["resolved_direction_ids"],
                         [])
        self.assertEqual(self._read_meta()["directions"]["DIR00002"]["merged_into"], "DIR00001")
        self.record_validation(keys=("DIR00001",))
        stage3_first = self.stage3_direction_keys()
        self.assertEqual(stage3_first, ["DIR00001"])

        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertEqual(self.stage3_direction_keys(), stage3_first)


class TestResolutionEvidenceUniverse(ResolvedPreflightBase):
    """Requirement 3: candidate-union evidence joins the reuse identity."""

    def test_candidate_fulltext_change_misses_early_gate_and_re_triggers_resolution(self):
        self.add_candidate_fulltext()
        self.build_accepted_state()
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)

        # A material full-text facts change for the non-relevant candidate:
        # its facts sidecar bytes change, so the recorded candidate-union
        # guard flips and the early gate must miss.
        analysis = self.prof_dir / "论文分析" / "CCCC3333.md"
        pdf = self.prof_dir / "论文分析" / "CCCC3333.pdf"
        make_facts_sidecar(analysis, pdf, [self.cccc_quote],
                           topic_terms=["synthetic", "comparison", "input", "adaptive"])
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("artifact_changed", payload["reason_codes"], payload)

        # The affected resolution is re-judged: the changed topic terms are
        # part of every resolve model_input over the candidate union.
        out = parse(run_cli("stage2-resolve-plan", "--facts", self.facts_path))
        self.assertEqual(out["status"], "ok", out)
        self.assertTrue(out["write_needed"], out)
        actions = {d["direction_id"]: d["action"] for d in out["directions"]}
        self.assertEqual(actions["DIR00001"], "process", out)

    def test_analysis_markdown_edit_does_not_re_burn_accepted_resolve_jobs(self):
        plan_path = self.start_round()
        self.write_resolve_result("DIR00001", {
            "resolved_direction_id": "DIR00001", "provisional_direction_id": "DIR00001",
            "name_ja": "合成输入比较", "name_zh": "合成输入比较",
            "resolution_type": "unchanged",
            "papers_to_add": [], "papers_to_remove": [], "paper_justifications": {},
            "split_target": None, "merge_target": None, "user_note": ""})
        self.write_resolve_result("DIR00002", {
            "resolved_direction_id": "DIR00002", "provisional_direction_id": "DIR00002",
            "name_ja": "第二方向", "name_zh": "第二方向",
            "resolution_type": "unchanged",
            "papers_to_add": [], "papers_to_remove": [], "paper_justifications": {},
            "split_target": None, "merge_target": None, "user_note": ""})
        fin = self.resolve_finalize()
        self.assertFalse(fin["needs_user_choice"], fin)
        self.finalize(plan_path)
        self.record_validation()
        self.assertEqual(self.preflight()["action"], "reuse_all", self.preflight())

        # An editorial Markdown edit may cost the early exit (the analysis
        # artifact guard flips) but must NOT re-burn accepted resolve jobs:
        # the resolve model_input never hashed analysis Markdown prose.
        analysis = Path(self.facts["papers"][0]["analysis_file"])
        analysis.write_text(analysis.read_text(encoding="utf-8") + "\n手改段落\n",
                            encoding="utf-8")
        out = parse(run_cli("stage2-resolve-plan", "--facts", self.facts_path))
        self.assertEqual(out["status"], "ok", out)
        self.assertFalse(out["write_needed"], out)
        self.assertTrue(all(d["action"] == "reuse" for d in out["directions"]), out)


class TestResolvedProofBinding(ResolvedPreflightBase):
    """Requirement 4: the sidecar is bound to its facts/preflight generation."""

    def _accept_split_under_current_proof(self):
        plan_path = self.start_round()
        self.write_resolve_result("DIR00001", {
            "resolved_direction_id": "DIR00001", "provisional_direction_id": "DIR00001",
            "name_ja": "合成输入比较", "name_zh": "合成输入比较",
            "resolution_type": "split_from",
            "papers_to_add": ["BBBB2222"], "papers_to_remove": [],
            "paper_justifications": {"BBBB2222": "Second processing path clusters separately."},
            "split_target": "DIR00001__sub", "merge_target": None, "user_note": ""})
        self.resolve_finalize()
        self.accept(["DIR00001"])
        self.finalize(plan_path)
        return plan_path

    def _advance_to_new_generation(self):
        """A later invocation observes changed target state: a new proof id."""
        self.target["directions"][0]["user_note"] = "later invocation note"
        self._write_target()
        plan = self.preflight()
        self.assertEqual(plan["action"], "process", plan)
        plan_path = self.root / "later-preflight.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        self.bind_facts_to_plan(plan_path)
        return plan_path

    def test_accept_refuses_sidecar_from_earlier_generation(self):
        self._accept_split_under_current_proof()
        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        sidecar_before = sidecar_path.read_bytes()
        self._advance_to_new_generation()

        out = parse(run_cli("stage2-resolve-accept", "--facts", self.facts_path,
                            "--ckeys", "DIR00001"))
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "resolved_directions_proof_mismatch", out)
        self.assertEqual(sidecar_path.read_bytes(), sidecar_before)

    def test_finalize_refuses_stale_generation_sidecar_with_zero_writes(self):
        self._accept_split_under_current_proof()
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.prof_dir / "套磁候选分析.md"
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        before = {p: p.read_bytes() for p in (pack_path, md_path, cache_path)}
        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        sidecar_before = sidecar_path.read_bytes()
        plan_path = self._advance_to_new_generation()

        out = parse(run_cli(
            "stage2-finalize", "--facts", self.facts_path,
            "--results", self.write_stage2_results(),
            "--preflight-file", plan_path,
            "--resolved-directions", str(sidecar_path)))
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertEqual(out["reason_code"], "resolved_directions_proof_mismatch", out)
        self.assertIn("resolved_directions_proof_binding", out["drift"], out)
        for path, payload in before.items():
            self.assertEqual(path.read_bytes(), payload, path)
        self.assertEqual(sidecar_path.read_bytes(), sidecar_before)

    def test_recovery_restamps_sidecar_for_the_new_generation(self):
        self._accept_split_under_current_proof()
        plan_path = self._advance_to_new_generation()

        # Re-running the resolve pipeline under the new proof restamps the
        # sidecar (entries stay accepted — the facts-driven fingerprints did
        # not change), and the choice/application then succeed again.
        fin = self.resolve_finalize()
        self.assertFalse(fin["needs_user_choice"], fin)
        self.assertEqual(fin["stage2_preflight_id"],
                         json.loads(plan_path.read_text(encoding="utf-8"))["preflight_id"])
        self.accept(["DIR00001"])
        out = self.finalize(plan_path)
        self.assertTrue(out["resolved_directions_applied"], out)
        pack = self._read_pack()
        self.assertEqual(sorted(d["direction_id"] for d in pack["directions"]),
                         ["DIR00001", "DIR00001__sub", "DIR00002"])


if __name__ == "__main__":
    unittest.main()
