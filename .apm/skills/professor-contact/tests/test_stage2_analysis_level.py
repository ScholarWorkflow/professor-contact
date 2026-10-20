"""U5 actual analysis-level propagation and honest statistics (plan r3).

The tests exercise the plan's L1-L6 targets through the same formal entries the
analyzer uses: facts acceptance, canonical pack merge, the managed renderer, the
early preflight branch and the level-refresh/managed-write lifecycle. They reuse
the accepted-state fixture of ``test_stage2_preflight`` instead of rebuilding a
second Stage-2 universe.
"""

import contextlib
import io
import json
import re
import unittest
from pathlib import Path

from test_stage2_preflight import (  # noqa: E402
    PROFESSOR, PreflightBase, parse, quote_id, run_cli,
)
import contact_state  # noqa: E402

ROOT = Path(__file__).parents[1]
REPO = Path(__file__).parents[4]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


class AnalysisLevelBase(PreflightBase):
    """PreflightBase plus a real ``论文分析/_index.json`` and facts levels."""

    def setUp(self):
        super().setUp()
        self.levels = {"AAAA1111": "fulltext", "BBBB2222": "abstract"}
        for direction, did in zip(self.facts["directions"], ("DIR00001", "DIR00002")):
            direction["direction_id"] = did
        self.write_index()
        self.bind_levels()

    # -- fixture writers ----------------------------------------------------

    def write_index(self, levels=None):
        levels = self.levels if levels is None else levels
        papers = {}
        for key in ("AAAA1111", "BBBB2222"):
            analysis = self.prof_dir / "论文分析" / f"{key}.md"
            papers[key] = {
                "file": str(analysis),
                "level": levels.get(key),
                "future_work_sidecar": str(analysis) + ".future_work.json",
                "facts_sidecar": None,
            }
        write_json(self.prof_dir / "论文分析" / "_index.json", {
            "schema": 2, "future_work_schema": 1, "professor": PROFESSOR,
            "generated_at": "2026-01-01T00:00:00Z", "papers": papers})

    def bind_levels(self, levels="same"):
        levels = self.levels if levels == "same" else levels
        for paper in self.facts["papers"]:
            if paper["item_key"] in levels:
                paper["analysis_level"] = levels[paper["item_key"]]
        write_json(self.facts_path, self.facts)

    def patch_facts(self, mutator):
        """Change the on-disk facts while preserving their preflight binding."""
        facts = read_json(self.facts_path)
        mutator(facts)
        write_json(self.facts_path, facts)
        self.facts = facts

    def finalize_with_current_proof(self):
        from stage2_upstream_fixture import run_bound_stage2_finalize
        return run_bound_stage2_finalize(
            run_cli, self.facts_path, "--results", self.root / "results")

    def write_stage2_results(self):
        results = super().write_stage2_results()
        if getattr(self, "shared_pair", False):
            rows = [{"gap_id": quote_id(quote), "status": "open",
                     "candidate_paper_ids": [],
                     "evidence": f"无更晚论文实现该点（{key}）", "confidence": "high"}
                    for key, quote in self.gap_quotes.items()]
            (results / "freshness-DIR00002.json").write_text(json.dumps({
                "schema": 1, "kind": "freshness", "direction_id": "DIR00002",
                "results": rows}, ensure_ascii=False), encoding="utf-8")
        return results

    def make_shared_level_pair(self):
        """Both level papers become members of both directions before acceptance.

        Only then does swapping their levels keep the aggregate statistic equal
        while the per-direction canonical values still change.
        """
        self.shared_pair = True
        second_target = self.target["directions"][1]
        second_target["members"].append({"item_key": "AAAA1111",
                                         "preview_confidence": "high"})
        second_snapshot = self.snapshot_entry["directions"][1]
        for field in ("provisional_member_keys", "candidate_keys"):
            if "AAAA1111" not in second_snapshot[field]:
                second_snapshot[field].append("AAAA1111")
        second_snapshot["expansion_reasons"]["AAAA1111"] = ["provisional_member"]
        self.facts["directions"][1]["member_keys"].append("AAAA1111")
        self._write_target()
        self._write_snapshot()
        write_json(self.facts_path, self.facts)

    def save_preflight(self, name="preflight.json"):
        payload = self.preflight()
        path = self.root / name
        write_json(path, payload)
        return path

    def refresh(self, preflight_file, *extra):
        out = run_cli("stage2-refresh-level", "--program-root", self.root,
                      "--professor", PROFESSOR, "--target-file", self.target_file,
                      "--preflight-file", preflight_file, *extra)
        return out

    def analysis_md(self) -> Path:
        return self.prof_dir / "套磁候选分析.md"

    def header_line(self) -> str:
        for line in self.analysis_md().read_text(encoding="utf-8").splitlines():
            if "数据来源：" in line:
                return line
        raise AssertionError("statistics header missing")


class TestFactsLevelContract(AnalysisLevelBase):
    """L1: the facts entry carries the current success-only level, never a guess."""

    def test_known_and_unknown_levels_reach_the_canonical_pack(self):
        self.stage2_finalize()
        papers = self._read_pack()["papers"]
        self.assertEqual(papers["AAAA1111"]["analysis_level"], "fulltext")
        self.assertEqual(papers["BBBB2222"]["analysis_level"], "abstract")
        self.assertIsNone(papers["CCCC3333"]["analysis_level"])
        # OCR-only/without facts can still be a successful fulltext analysis.
        self.assertEqual(papers["AAAA1111"]["facts_state"], "unavailable")

    def test_facts_level_conflicting_with_the_current_registration_is_invalid(self):
        self.facts["papers"][0]["analysis_level"] = "abstract"
        write_json(self.facts_path, self.facts)
        result = run_cli("stage2-finalize", "--facts", self.facts_path,
                         "--results", self.root / "results",
                         "--preflight-file", self.save_preflight())
        payload = parse(result)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "invalid_facts")
        self.assertIn("analysis_level_conflict", payload["message"])

    def test_illegal_level_is_an_input_error(self):
        self.facts["papers"][0]["analysis_level"] = "partial"
        write_json(self.facts_path, self.facts)
        result = run_cli("stage2-finalize", "--facts", self.facts_path,
                         "--results", self.root / "results",
                         "--preflight-file", self.save_preflight())
        payload = parse(result)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "invalid_facts")

    def test_explicit_null_clears_a_registered_level(self):
        self.stage2_finalize()
        def clear(facts):
            for paper in facts["papers"]:
                if paper["item_key"] in ("AAAA1111", "BBBB2222"):
                    paper["analysis_level"] = None
        self.patch_facts(clear)
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "ok", out)
        papers = self._read_pack()["papers"]
        self.assertIsNone(papers["AAAA1111"]["analysis_level"])
        self.assertIsNone(papers["BBBB2222"]["analysis_level"])



    def test_analysis_file_and_pdf_without_a_success_registration_are_unknown(self):
        analysis = self.prof_dir / "论文分析" / "CCCC3333.md"
        analysis.write_text("# unregistered analysis\n", encoding="utf-8")

        def mutate(facts):
            for paper in facts["papers"]:
                if paper["item_key"] == "CCCC3333":
                    paper["analysis_file"] = str(analysis)
                    paper["has_pdf"] = True
                    paper["analysis_level"] = None
        self.patch_facts(mutate)
        self.write_stage2_results()
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "ok", out)
        papers = self._read_pack()["papers"]
        self.assertIsNone(papers["CCCC3333"]["analysis_level"])
        self.assertTrue(papers["CCCC3333"]["pdf_available"])
        self.assertEqual(papers["CCCC3333"]["analysis_file"], str(analysis))

    def test_consumed_analysis_path_contradicting_the_index_is_invalid(self):
        alternative = self.prof_dir / "论文分析" / "AAAA1111-alt.md"
        alternative.write_text("# alternative analysis\n", encoding="utf-8")

        def mutate(facts):
            for paper in facts["papers"]:
                if paper["item_key"] == "AAAA1111":
                    paper["analysis_file"] = str(alternative)
                    paper["analysis_level"] = None
        self.patch_facts(mutate)
        result = run_cli("stage2-finalize", "--facts", self.facts_path,
                         "--results", self.root / "results",
                         "--preflight-file", self.save_preflight())
        payload = parse(result)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "invalid_facts")
        self.assertIn("analysis_file", payload["message"])

    def test_ocr_only_fulltext_without_facts_can_still_be_fulltext(self):
        analysis = self.prof_dir / "论文分析" / "EEEE5555.md"
        analysis.write_text("# OCR-only full text\n", encoding="utf-8")
        self.facts["papers"].append({
            "item_key": "EEEE5555", "title": "EEEE5555 title", "year": 2025,
            "month": 2, "authorship": "middle", "abstract": "ocr only sample",
            "authors": ["Example Professor"], "has_pdf": False,
            "analysis_file": str(analysis), "analysis_level": "fulltext"})
        self.facts["directions"][0]["member_keys"].append("EEEE5555")
        index = read_json(self.prof_dir / "论文分析" / "_index.json")
        index["papers"]["EEEE5555"] = {"file": str(analysis), "level": "fulltext"}
        write_json(self.prof_dir / "论文分析" / "_index.json", index)
        write_json(self.facts_path, self.facts)
        self.write_stage2_results()
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "ok", out)
        papers = self._read_pack()["papers"]
        self.assertEqual(papers["EEEE5555"]["analysis_level"], "fulltext")
        self.assertEqual(papers["EEEE5555"]["facts_state"], "unavailable")
        self.assertFalse(papers["EEEE5555"]["pdf_available"])

class TestCanonicalMerge(AnalysisLevelBase):
    """L2: one explicit assignment covers fresh/reused/resolved/old merges."""

    def test_known_level_survives_a_reuse_finalize_and_validator(self):
        self.build_accepted_state()
        self.assertIn("validator", self._read_pack())
        # A projection-only collection_key change on a reused entry must not
        # mutate the isolated old snapshot the validator binding compares with.
        def rename(facts):
            facts["directions"][0]["collection_key"] = "DIR00001-renamed"
        self.patch_facts(rename)
        out = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                            "--results", self.root / "results",
                            "--preflight-file", self.save_preflight("reuse-preflight.json")))
        self.assertEqual(out["status"], "ok", out)
        pack = self._read_pack()
        self.assertIn("validator", pack)
        self.assertEqual(pack["papers"]["AAAA1111"]["analysis_level"], "fulltext")
        self.assertEqual(pack["directions"][0]["collection_key"], "DIR00001-renamed")

    def test_missing_level_field_in_an_old_pack_reads_as_null(self):
        self.build_accepted_state()
        pack = self._read_pack()
        for record in pack["papers"].values():
            record.pop("analysis_level", None)
        pack.pop("cache", None)
        pack.pop("validator", None)
        self._write_pack(pack)
        def clear(facts):
            for paper in facts["papers"]:
                if paper["item_key"] in ("AAAA1111", "BBBB2222"):
                    paper["analysis_level"] = None
        self.patch_facts(clear)
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "ok", out)
        papers = self._read_pack()["papers"]
        self.assertIsNone(papers["AAAA1111"]["analysis_level"])
        self.assertIsNone(papers["BBBB2222"]["analysis_level"])

    def test_v1_migration_treats_missing_and_null_alike_but_rejects_conflict(self):
        base = {
            "schema": 1,
            "directions": [
                {"collection_key": "DIR00001", "name_ja": "一",
                 "supporting_papers": [{"item_key": "AAAA1111", "title": "T"}]},
                {"collection_key": "DIR00002", "name_ja": "二",
                 "supporting_papers": [{"item_key": "AAAA1111", "title": "T",
                                        "analysis_level": None}]},
            ],
        }
        normalized = contact_state.normalize_input_pack(base)
        self.assertIsNone(normalized["papers"]["AAAA1111"]["analysis_level"])
        conflicting = json.loads(json.dumps(base))
        conflicting["directions"][1]["supporting_papers"][0]["analysis_level"] = "fulltext"
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stdout(io.StringIO()):
                contact_state.normalize_input_pack(conflicting)


class TestStatisticsRender(AnalysisLevelBase):
    """L3: three mutually exclusive classes over the existing member projection."""

    def test_header_counts_members_only_and_shared_members_per_contribution(self):
        self.stage2_finalize()
        self.assertEqual(
            "全文级 1 篇 · 摘要级 2 篇 · 未确认 1 篇（共 4 篇）",
            self.header_line().split("数据来源：")[1].split("｜")[0].strip())
        pack = self._read_pack()
        self.assertEqual(set(pack["directions"][0]["supporting_item_keys"]),
                         {"AAAA1111", "BBBB2222", "CCCC3333"})
        self.assertEqual(pack["directions"][1]["supporting_item_keys"], ["BBBB2222"])

    def test_reference_only_paper_stays_out_of_the_statistic(self):
        analysis = self.prof_dir / "论文分析" / "DDDD4444.md"
        analysis.write_text("# reference only\n", encoding="utf-8")
        self.facts["papers"].append({
            "item_key": "DDDD4444", "title": "DDDD4444 title", "year": 2025,
            "month": 4, "authorship": "middle", "abstract": "reference only",
            "authors": ["Example Professor"], "has_pdf": False,
            "analysis_file": str(analysis), "analysis_level": "fulltext"})
        self.facts["directions"][0]["relevant_keys"] = [
            "AAAA1111", "BBBB2222", "DDDD4444"]
        write_json(self.facts_path, self.facts)
        self.write_stage2_results()
        self.levels["DDDD4444"] = "fulltext"
        index = read_json(self.prof_dir / "论文分析" / "_index.json")
        index["papers"]["DDDD4444"] = {"file": str(analysis), "level": "fulltext"}
        write_json(self.prof_dir / "论文分析" / "_index.json", index)
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "ok", out)
        pack = self._read_pack()
        self.assertNotIn("DDDD4444", pack["directions"][0]["supporting_item_keys"])
        self.assertIn("DDDD4444", pack["directions"][0]["relevant_keys"])
        self.assertEqual(pack["papers"]["DDDD4444"]["analysis_level"], "fulltext")
        self.assertEqual(
            "全文级 1 篇 · 摘要级 2 篇 · 未确认 1 篇（共 4 篇）",
            self.header_line().split("数据来源：")[1].split("｜")[0].strip())


class TestPreflightBranches(AnalysisLevelBase):
    """L4: limited source identity is business; level and format are separate."""

    def test_unchanged_state_reuses_all(self):
        self.build_accepted_state()
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertEqual(self.direction_action(payload, "DIR00001"), "reuse")

    def test_level_only_change_takes_the_refresh_branch(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        payload = self.preflight()
        self.assertEqual(payload["action"], "refresh_level", payload)
        self.assertEqual(self.direction_action(payload, "DIR00001"), "refresh_level")
        self.assertEqual(self.direction(payload, "DIR00001")["reason_codes"], [])

    def test_management_fields_do_not_change_the_business_source(self):
        self.build_accepted_state()
        index = read_json(self.prof_dir / "论文分析" / "_index.json")
        index["generated_at"] = "2026-02-02T00:00:00Z"
        index["papers"]["AAAA1111"]["kb_entry_id"] = "kb-123"
        write_json(self.prof_dir / "论文分析" / "_index.json", index)
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)

    def test_new_fixed_facts_candidate_is_a_business_change(self):
        self.build_accepted_state()
        (self.prof_dir / "论文分析" / "AAAA1111.md.facts.json").write_text(
            json.dumps({"schema": 1, "kind": "paper-facts"}), encoding="utf-8")
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("source_changed", self.direction(payload, "DIR00001")["reason_codes"])

    def test_missing_projection_processes_once(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"]["preflight"]["directions"]["DIR00001"].pop("source_projection")
        self._write_pack(pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("source_projection_missing",
                      self.direction(payload, "DIR00001")["reason_codes"])

    def test_illegal_index_level_processes_instead_of_writing_a_known_value(self):
        self.build_accepted_state()
        index = read_json(self.prof_dir / "论文分析" / "_index.json")
        index["papers"]["AAAA1111"]["level"] = "partial"
        write_json(self.prof_dir / "论文分析" / "_index.json", index)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        self.assertIn("analysis_level_unreadable",
                      self.direction(payload, "DIR00001")["reason_codes"])

    def test_not_accepted_validator_blocks_reuse_all(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["validator"]["results"]["DIR00001"]["result"] = "needs_correction"
        self._write_pack(pack)
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        self.assertEqual(self.direction_action(payload, "DIR00001"), "process")
        self.assertIn("validator_not_accepted",
                      self.direction(payload, "DIR00001")["reason_codes"])

    def direction_action(self, payload, direction_id):
        return self.direction(payload, direction_id)["action"]


class TestLevelRefresh(AnalysisLevelBase):
    """L5: bounded acceptance shared with normal finalize."""

    def test_statistic_change_updates_body_and_expires_old_certification(self):
        self.build_accepted_state()
        before = self.analysis_md().read_bytes()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("refresh.json")
        payload = read_json(plan)
        self.assertEqual(payload["action"], "refresh_level", payload)
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        self.assertTrue(out["md_written"])
        self.assertFalse(out["validator_preserved"])
        self.assertEqual(out["changed_levels"], {"AAAA1111": "abstract"})
        pack = self._read_pack()
        self.assertEqual(pack["papers"]["AAAA1111"]["analysis_level"], "abstract")
        self.assertEqual(pack["papers"]["BBBB2222"]["analysis_level"], "abstract")
        self.assertNotIn("validator", pack)
        self.assertNotEqual(before, self.analysis_md().read_bytes())
        self.assertIn("全文级 0 篇 · 摘要级 3 篇 · 未确认 1 篇（共 4 篇）",
                      self.header_line())
        # Refresh never rewrites business state.
        self.assertEqual(set(pack["directions"][0]["supporting_item_keys"]),
                         {"AAAA1111", "BBBB2222", "CCCC3333"})

    def test_equivalent_body_swap_keeps_the_valid_old_certification(self):
        self.make_shared_level_pair()
        self.build_accepted_state()
        before = self.analysis_md().read_bytes()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "fulltext"}
        self.write_index()
        plan = self.save_preflight("refresh-swap.json")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        self.assertFalse(out["md_written"])
        self.assertTrue(out["validator_preserved"])
        self.assertEqual(self.analysis_md().read_bytes(), before)
        pack = self._read_pack()
        self.assertIn("validator", pack)
        self.assertEqual(pack["validator"]["round"], 1)
        self.assertEqual(pack["validator"]["phase"], "terminal")
        self.assertEqual(pack["papers"]["AAAA1111"]["analysis_level"], "abstract")
        self.assertEqual(pack["papers"]["BBBB2222"]["analysis_level"], "fulltext")

    def test_invalid_old_binding_is_an_evidence_error_not_a_rebind(self):
        self.make_shared_level_pair()
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "fulltext"}
        self.write_index()
        pack = self._read_pack()
        pack["validator"]["render_sha256"] = "0" * 64
        self._write_pack(pack)
        plan = self.save_preflight("refresh-bad-binding.json")
        result = self.refresh(plan)
        payload = parse(result)
        self.assertEqual(payload["status"], "error", (result.stdout, result.stderr))
        self.assertEqual(payload["reason_code"], "validation_render_stale", payload)

    def test_legacy_statistics_body_is_reaccepted_before_the_marker(self):
        self.build_accepted_state()
        md = self.analysis_md()
        text = md.read_text(encoding="utf-8")
        legacy = re.sub(
            r"数据来源：全文级 \d+ 篇 · 摘要级 \d+ 篇 · 未确认 \d+ 篇（共 \d+ 篇）",
            "数据来源：全文级 3 篇 · 摘要级 1 篇（共 4 篇）", text)
        self.assertNotEqual(legacy, text)
        header, body = contact_state.split_frontmatter(legacy)
        self.assertEqual(header["managed_by"], "contact_state")
        md.write_text(legacy, encoding="utf-8")
        pack = self._read_pack()
        pack["cache"]["preflight"]["statistics_version"] = None
        pack["cache"]["render"]["套磁候选分析.md"]["sha256"] = \
            contact_state.sha256_text(body)
        self._write_pack(pack)
        plan = self.save_preflight("legacy-stats.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "ok", out)
        self.assertIn("全文级 1 篇 · 摘要级 2 篇 · 未确认 1 篇（共 4 篇）",
                      self.header_line())
        updated = self._read_pack()
        self.assertEqual(
            updated["cache"]["preflight"]["statistics_version"], 1)

    def test_business_change_with_equivalent_body_keeps_body_but_expires_certification(self):
        self.build_accepted_state()
        before = self.analysis_md().read_bytes()

        def mutate(facts):
            # `credibility.note` is model-relevant but never rendered, so the real
            # body stays byte-equivalent while the business basis changes.
            facts["directions"][0]["credibility"]["note"] = "business-only change"
        self.patch_facts(mutate)
        results = self.write_stage2_results()
        narrative = read_json(results / "narrative.json")
        narrative["directions"] = [
            entry for entry in narrative["directions"]
            if entry.get("collection_key") == "DIR00001"]
        write_json(results / "narrative.json", narrative)
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "ok", out)
        # The real body survives byte-for-byte; only the machine header may move
        # to bind the new business basis.
        _, body_before = contact_state.split_frontmatter(before.decode("utf-8"))
        header_after, body_after = contact_state.split_frontmatter(
            self.analysis_md().read_text(encoding="utf-8"))
        self.assertEqual(body_after, body_before)
        self.assertEqual(header_after["render_sha256"],
                         contact_state.sha256_text(body_after))
        pack = self._read_pack()
        self.assertNotIn("validator", pack)
        self.assertEqual(pack["cache"]["render"]["套磁候选分析.md"]["sha256"],
                         contact_state.sha256_text(body_after))
        self.assertEqual(out["md_sha256"], contact_state.sha256_text(body_after))
        self.assertEqual(pack["papers"]["AAAA1111"]["analysis_level"], "fulltext")

    def test_manual_body_edit_needs_decision_without_writing_the_pack(self):
        self.build_accepted_state()
        with self.analysis_md().open("a", encoding="utf-8") as handle:
            handle.write("\n人工补充的一行。\n")
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("refresh-manual.json")
        pack_path = self.prof_dir / "套磁候选输入.json"
        before = pack_path.read_bytes()
        result = self.refresh(plan)
        payload = parse(result)
        self.assertEqual(payload["status"], "needs_decision")
        self.assertEqual(pack_path.read_bytes(), before)


class TestRefreshProtection(AnalysisLevelBase):
    """L6: the new writer uses the existing lease/refine protections."""

    def test_busy_writer_returns_without_any_business_write(self):
        from stage2_chatgpt_handoff import acquire_local_lease, release_local_lease
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("busy.json")
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        before_pack = pack_path.read_bytes()
        before_md = md_path.read_bytes()
        acquire_local_lease(self.prof_dir, "another-writer")
        try:
            result = self.refresh(plan)
        finally:
            release_local_lease(self.prof_dir, "another-writer")
        payload = parse(result)
        self.assertEqual(payload["status"], "stage2_writer_busy")
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(md_path.read_bytes(), before_md)

    def test_binding_drift_returns_needs_refresh_releases_and_writes_nothing(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("drift.json")
        self.target["directions"][0]["user_note"] = "预检之后才改的笔记。"
        self._write_target()
        pack_path = self.prof_dir / "套磁候选输入.json"
        before = pack_path.read_bytes()
        payload = parse(self.refresh(plan))
        self.assertEqual(payload["status"], "needs_refresh")
        self.assertIn("preflight_inputs_changed", payload["reason_code"])
        self.assertEqual(pack_path.read_bytes(), before)
        self.assertFalse((self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

    def test_refresh_keeps_the_accepted_sources_and_foreign_cache(self):
        self.build_accepted_state()
        pack = self._read_pack()
        recorded = {direction_id: record.get("consumed_sources")
                    for direction_id, record in pack["cache"]["preflight"]["directions"].items()}
        recorded_pdf = {direction_id: record.get("pdf_sources")
                        for direction_id, record in pack["cache"]["preflight"]["directions"].items()}
        recorded_sources = {direction_id: record.get("source_projection")
                            for direction_id, record in pack["cache"]["preflight"]["directions"].items()}
        pack["cache"]["u1_render"] = {"future": "kept"}
        pack["resolved_directions"] = {"schema": 2, "applied_at": "fixed",
                                       "directions": []}
        self._write_pack(pack)
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("refresh-audit.json")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        updated = self._read_pack()
        self.assertEqual(updated["cache"]["u1_render"], {"future": "kept"})
        self.assertEqual(updated["resolved_directions"], pack["resolved_directions"])
        directions = updated["cache"]["preflight"]["directions"]
        for direction_id, record in directions.items():
            self.assertEqual(record.get("consumed_sources"), recorded[direction_id])
            self.assertEqual(record.get("pdf_sources"), recorded_pdf[direction_id])
            self.assertEqual(record.get("source_projection"), recorded_sources[direction_id])

    def test_successful_refresh_releases_the_lease(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "fulltext"}
        self.write_index()
        plan = self.save_preflight("release.json")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        self.assertTrue(out["lease_released"])
        self.assertFalse((self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

    def _fail_lease_unlink(self):
        lease = (self.prof_dir / "论文分析" / ".stage2-local-writer.json").resolve()
        original = Path.unlink

        def failing_unlink(path, *args, **kwargs):
            if Path(path).resolve() == lease:
                raise OSError("synthetic lease unlink failure")
            return original(path, *args, **kwargs)

        Path.unlink = failing_unlink
        self.addCleanup(setattr, Path, "unlink", original)
        return lease

    def test_release_failure_is_reported_on_the_success_path(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("release-failure.json")
        lease = self._fail_lease_unlink()
        arguments = type("Args", (), {
            "program_root": str(self.root), "professor": PROFESSOR,
            "target_file": str(self.target_file), "preflight_file": str(plan),
            "decision_file": None})()
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            contact_state.cmd_stage2_refresh_level(arguments)
        out = json.loads(stdout.getvalue())
        self.assertEqual(out["status"], "ok", out)
        self.assertFalse(out["lease_released"])
        self.assertIn("synthetic lease unlink failure", out["lease_release_error"])
        self.assertIn("lease release failed", stderr.getvalue())
        self.assertTrue(lease.exists())

    def test_release_failure_on_a_soft_exit_is_also_reported(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("soft-release-failure.json")
        # Make the post-lease gate find nothing left to refresh: the command
        # soft-exits after acquiring the lease, so the finally must report.
        pack = self._read_pack()
        record = pack["cache"]["preflight"]["directions"]["DIR00001"]
        record["level_projection"] = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        record["level_projection"]["CCCC3333"] = None
        pack["cache"]["preflight"]["directions"]["DIR00002"]["level_projection"] = {
            "BBBB2222": "abstract"}
        self._write_pack(pack)
        lease = self._fail_lease_unlink()
        arguments = type("Args", (), {
            "program_root": str(self.root), "professor": PROFESSOR,
            "target_file": str(self.target_file), "preflight_file": str(plan),
            "decision_file": None})()
        stdout, stderr = io.StringIO(), io.StringIO()
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                contact_state.cmd_stage2_refresh_level(arguments)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertIn("lease release failed", stderr.getvalue())
        self.assertTrue(lease.exists())

    def test_pack_io_failure_after_the_markdown_write_stays_unfinished(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("io-failure.json")
        pack_path = self.prof_dir / "套磁候选输入.json"
        before = pack_path.read_bytes()
        original = contact_state._contact_io.atomic_write

        def failing_write(path, text):
            if Path(path) == pack_path:
                raise OSError("synthetic pack write failure")
            return original(path, text)

        contact_state._contact_io.atomic_write = failing_write
        self.addCleanup(setattr, contact_state._contact_io, "atomic_write", original)
        arguments = type("Args", (), {
            "program_root": str(self.root), "professor": PROFESSOR,
            "target_file": str(self.target_file), "preflight_file": str(plan),
            "decision_file": None})()
        buffer = io.StringIO()
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stdout(buffer):
                contact_state.cmd_stage2_refresh_level(arguments)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason_code"], "stage2_pack_write_failed")
        # The pack (the acceptance record) is untouched; the markdown write is a
        # cross-file incomplete state, not a silent success.
        self.assertEqual(pack_path.read_bytes(), before)
        self.assertEqual(
            self._read_pack()["cache"]["preflight"]["statistics_version"], 1)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())


class TestGenerationTimeNormalization(unittest.TestCase):
    """Only the fixed renderer generation timestamp may be ignored."""

    def test_only_the_generation_time_is_ignored(self):
        body = ("# 套磁候选分析 — P\n\n"
                "$$\\newcommand{\\dif}{\\mathop{}\\!\\mathrm{d}}$$\n\n"
                "> 2026-01-01T00:00:00Z ｜ 数据来源：全文级 1 篇 · 摘要级 2 篇 · "
                "未确认 1 篇（共 4 篇）｜ 由 contact_state 确定性渲染（重跑=全量重写）\n")
        later = body.replace("2026-01-01T00:00:00Z", "2026-02-02T03:04:05Z")
        statistics_changed = body.replace("全文级 1", "全文级 2")
        crlf = body.replace("\n", "\r\n")
        without_trailing = body.rstrip("\n")
        normalize = contact_state.stage2_body_without_generation_time
        self.assertEqual(normalize(body), normalize(later))
        self.assertNotEqual(normalize(body), normalize(statistics_changed))
        # Only the timestamp token may be ignored; line endings and other bytes
        # stay significant.
        self.assertNotEqual(normalize(body), normalize(crlf))
        self.assertNotEqual(normalize(body), normalize(without_trailing))


class TestAnalyzerContract(unittest.TestCase):
    """The two analyzer projections must explain the same contract."""

    def test_both_analyzers_pass_the_level_and_consume_the_refresh_branch(self):
        codex = (REPO / "packages/professor-contact-codex/.apm/agents/"
                 "professor-contact-analyzer.agent.md").read_text(encoding="utf-8")
        opencode = (REPO / "packages/professor-contact-opencode/.apm/agents/"
                    "professor-contact-analyzer.agent.md").read_text(encoding="utf-8")
        for document in (codex, opencode):
            self.assertIn("analysis_level", document)
            self.assertIn("stage2-refresh-level", document)
            self.assertIn("refresh_level", document)
            self.assertIn("全文级", document)
            # The explicit external-result/KB exception must still route to the
            # original process path instead of being swallowed by the refresh.
            self.assertIn("chatgpt_result", document)
            self.assertIn("kb_import", document)
            self.assertIn("禁止 early hard exit", document)


if __name__ == "__main__":
    unittest.main()
