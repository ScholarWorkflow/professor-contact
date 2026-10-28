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
from stage2_upstream_fixture import run_bound_stage2_finalize, run_bound_stage2_plan

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import contact_state  # noqa: E402
from test_stage2_preflight import PreflightBase, make_sidecar, parse, quote_id, run_cli  # noqa: E402
from test_stage2_resolved_direction import (  # noqa: E402
    finalize_resolve, make_facts_sidecar, new_resolve_results_dir, plan_resolve,
    write_resolve_results)


class ResolvedPreflightBase(PreflightBase):
    """PreflightBase plus valid full-text facts for the candidate papers."""

    def setUp(self):
        super().setUp()
        self.with_candidate_fulltext = False
        # One resolve round = one exclusive results directory + one round
        # identity; `new_results_dir()` rotates both.
        self._results_dir = None
        self._resolve_plan = None
        self._resolve_results = {}
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
        """The current resolve round's exclusive results directory."""
        if self._results_dir is None:
            self.new_results_dir()
        return self._results_dir

    def new_results_dir(self) -> Path:
        """Start a new resolve round: exclusive directory plus its own identity.

        `stage2-resolve-plan` requires a pre-existing absolute results directory
        that holds no expected result file yet, so every new round allocates a
        fresh one and re-plans into it; `stage2-resolve-finalize` then reads the
        very same directory. The ordinary `stage2-finalize`
        freshness/narrative results directory is a different one and stays put.
        """
        self._results_dir = new_resolve_results_dir(self.root)
        self._resolve_plan = None
        self._resolve_results = {}
        return self._results_dir

    def resolve_plan(self):
        """This round's `stage2-resolve-plan` receipt, planned at most once."""
        if self._resolve_plan is None:
            out = plan_resolve(self.facts_path, self.results_dir)
            self.assertEqual(out["status"], "ok", out)
            self._resolve_plan = out
        return self._resolve_plan

    def start_round(self):
        """Run preflight, save its payload, and bind the facts run to its proof."""
        self.new_results_dir()
        plan = self.preflight()
        self.assertEqual(plan["action"], "process", plan)
        plan_path = self.root / "stage2-preflight.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        self.bind_facts_to_plan(plan_path)
        return plan_path

    def write_resolve_result(self, ckey, resolved):
        """Simulate this round's model result, keeping the `resolved` decision.

        The round's plan receipt supplies the expected `result_file` names and
        the `resolve_run_id` every file must echo. Directions this test does not
        name still receive a complete synthesized `unchanged` result, because a
        missing file is no longer a legal "nothing changed" input.
        """
        self._resolve_results[ckey] = resolved
        write_resolve_results(self.results_dir, self.resolve_plan(),
                              self._resolve_results, self.facts_path)

    def resolve_finalize(self):
        if getattr(self, "_resolve_plan", None) is None:
            self.resolve_plan()
        out = finalize_resolve(self.facts_path, self.results_dir)
        self.assertEqual(out["status"], "ok", out)
        return out

    def accept(self, ckeys):
        out = parse(run_cli("stage2-resolve-accept", "--facts", self.facts_path,
                            "--ckeys", ",".join(ckeys)))
        self.assertEqual(out["status"], "ok", out)
        return out

    def finalize(self, plan_path):
        out = parse(run_bound_stage2_finalize(
            run_cli, self.facts_path,
            "--results", self.write_stage2_results(),
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
        direction = pack["directions"][0]
        original_narrative = dict(direction["narrative"])
        kept, completed = direction["gap_shortlist"]
        # Model the legacy low_rank projection and an already accepted blacklist.
        direction["gap_shortlist"] = []
        direction["gaps_excluded"] = [dict(kept, reason="low_rank（本轮未选，不代表不重要）")]
        blacklist = dict(completed, completed_by_item_key="CCCC3333",
                         candidate_paper_ids=["CCCC3333"], evidence="已有人工确认的完成证据",
                         confidence="high", evaluated_at="2026-01-01T00:00:00Z")
        direction["completed_gap_blacklist"] = [blacklist]
        pack["cache"]["preflight"]["resolution_semantics_version"] = \
            contact_state.STAGE2_RESOLUTION_SEMANTICS_VERSION - 1
        self._write_pack(pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("resolution_semantics_changed", payload["reason_codes"], payload)

        # One full new-semantics Stage-2 run (finalize with the preflight file
        # re-seeds cache.preflight) re-arms the early gate for the next run.
        plan_path = self.start_round()
        out = parse(run_bound_stage2_finalize(
            run_cli, self.facts_path, "--results", self.write_stage2_results()))
        self.assertEqual(out["status"], "ok", out)
        rebuilt = self._read_pack()["directions"][0]
        self.assertEqual([gap["gap_id"] for gap in rebuilt["gap_shortlist"]], [kept["gap_id"]])
        self.assertEqual(rebuilt["gaps_excluded"], [])
        self.assertEqual(rebuilt["gap_shortlist"][0]["status"], kept["status"])
        self.assertEqual(rebuilt["gap_shortlist"][0]["evidence"], kept["evidence"])
        self.assertEqual(rebuilt["narrative"], original_narrative)
        self.assertEqual(len(rebuilt["completed_gap_blacklist"]), 1)
        for field in ("gap_id", "candidate_paper_ids", "evidence", "confidence", "evaluated_at"):
            self.assertEqual(rebuilt["completed_gap_blacklist"][0][field], blacklist[field])
        self.assertEqual(self._read_meta()["resolution_semantics_version"],
                         contact_state.STAGE2_RESOLUTION_SEMANTICS_VERSION)
        self.seed_validator_results("pass", rounds=1)
        self.assertEqual(self.preflight()["action"], "reuse_all", self.preflight())

    def test_missing_meta_rebuilds_only_legacy_low_rank_projection(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"].pop("preflight", None)
        pack["validator"]["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
        self.assertFalse(contact_state.stage2_pack_requires_membership_rebuild(pack))
        direction = pack["directions"][0]
        gap = direction["gap_shortlist"].pop()
        direction["gaps_excluded"] = [dict(gap, reason="low_rank（本轮未选，不代表不重要）")]
        pack["validator"]["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
        self.assertTrue(contact_state.stage2_pack_requires_membership_rebuild(pack))


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

    def test_old_semantics_rebuild_preserves_split_child_blacklist(self):
        self._accept_split()
        pack = self._read_pack()
        parent = next(d for d in pack["directions"] if d["direction_id"] == "DIR00001")
        child = next(d for d in pack["directions"] if d["direction_id"] == "DIR00001__sub")
        parent_gap = parent["gap_shortlist"].pop()
        parent["gaps_excluded"] = [dict(parent_gap, reason="low_rank（本轮未选，不代表不重要）")]
        child_gap = child["gap_shortlist"].pop()
        blacklist = dict(child_gap, completed_by_item_key="CCCC3333",
                         candidate_paper_ids=["CCCC3333"], evidence="子方向已有完成证据",
                         confidence="high", evaluated_at="2026-01-01T00:00:00Z")
        blacklist.pop("candidate_paper_ids")  # legacy blacklist stores only completed_by_item_key
        child["completed_gap_blacklist"] = [blacklist]
        pack["cache"]["preflight"]["resolution_semantics_version"] = \
            contact_state.STAGE2_RESOLUTION_SEMANTICS_VERSION - 1
        self._write_pack(pack)
        plan_path = self.start_round()
        planned = parse(run_bound_stage2_plan(run_cli, self.facts_path))
        self.assertEqual(planned["status"], "ok", planned)
        self.assertEqual(planned["jobs"], [], planned)
        # Rebind the accepted resolution to this generation; cached work is reused.
        self.assertEqual(self.resolve_plan()["jobs"], [])
        self.resolve_finalize()
        self.finalize(plan_path)
        rebuilt = self._read_pack()
        parent = next(d for d in rebuilt["directions"] if d["direction_id"] == "DIR00001")
        child = next(d for d in rebuilt["directions"] if d["direction_id"] == "DIR00001__sub")
        self.assertEqual([gap["gap_id"] for gap in parent["gap_shortlist"]], [parent_gap["gap_id"]])
        self.assertEqual(parent["gap_shortlist"][0]["evidence"], parent_gap["evidence"])
        self.assertEqual(child["gap_shortlist"], [])
        self.assertEqual(child["gaps_excluded"], [])
        self.assertEqual(len(child["completed_gap_blacklist"]), 1)
        self.assertEqual(child["completed_gap_blacklist"][0]["candidate_paper_ids"], ["CCCC3333"])
        for field in ("gap_id", "evidence", "confidence", "evaluated_at"):
            self.assertEqual(child["completed_gap_blacklist"][0][field], blacklist[field])

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
        # part of every resolve model_input over the candidate union. The
        # observation call still needs its own round results directory.
        out = plan_resolve(self.facts_path, self.new_results_dir())
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
        # the resolve model_input never hashed analysis Markdown prose. This
        # observation call plans a fresh round into its own directory.
        analysis = Path(self.facts["papers"][0]["analysis_file"])
        analysis.write_text(analysis.read_text(encoding="utf-8") + "\n手改段落\n",
                            encoding="utf-8")
        out = plan_resolve(self.facts_path, self.new_results_dir())
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
        # A new proof generation is a new resolve round: its own results
        # directory, so no earlier round's file can stand in for this one.
        self.new_results_dir()
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
