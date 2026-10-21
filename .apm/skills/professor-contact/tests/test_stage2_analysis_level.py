"""U5 actual analysis-level propagation and honest statistics (plan r6/t6).

The tests exercise the plan's L1-L6 targets through the same formal entries the
analyzer uses: facts acceptance, canonical pack merge, the managed renderer, the
early preflight branch and the level-refresh/managed-write lifecycle. They reuse
the accepted-state fixture of ``test_stage2_preflight`` instead of rebuilding a
second Stage-2 universe.

The r4/t5 rounds added three checks: a facts null cannot override a known index
registration, the lock-internal refresh must re-read the same complete business
guards, and the managed body is read, hashed and written as raw bytes. The
r6/t6 round adds the refresh ownership/u1 field-preservation check.
"""

import contextlib
import copy
import hashlib
import io
import json
import re
import tempfile
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def managed_bytes(body: bytes, state_fingerprint: str, *, newline: bytes = b"\n",
                  render_sha256: str | None = None) -> bytes:
    """Build a self-consistent managed file with the requested raw line endings."""
    body_sha = render_sha256 if render_sha256 is not None else sha256_bytes(body)
    lines = [b"---", b"managed_by: contact_state",
             b"state_fingerprint: " + state_fingerprint.encode("utf-8"),
             b"render_sha256: " + body_sha.encode("ascii"),
             b"---", b"", b""]
    return newline.join(lines) + body


def split_managed_bytes(data: bytes, *, newline: bytes = b"\n") -> tuple[bytes, bytes]:
    """Split the stored managed bytes without decoding or newline conversion."""
    marker = newline + b"---" + newline
    if not data.startswith(b"---" + newline) or marker not in data:
        raise AssertionError(f"not a managed file: {data[:80]!r}")
    end = data.index(marker)
    body_start = end + len(marker)
    if data[body_start:body_start + len(newline)] == newline:
        body_start += len(newline)
    return data[:body_start], data[body_start:]


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

    def assert_validation_report_bound(self, pack=None):
        """The validator must bind the exact report bytes it was recorded from."""
        pack = self._read_pack() if pack is None else pack
        self.assertEqual(pack["validator"]["validation_sha256"],
                         sha256_bytes((self.root / "validation.json").read_bytes()))

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

    def test_null_facts_against_a_known_registration_are_rejected_without_writes(self):
        self.stage2_finalize()
        pack_path = self.prof_dir / "套磁候选输入.json"
        analysis_path = self.analysis_md()
        before_pack = pack_path.read_bytes()
        before_md = analysis_path.read_bytes()

        def clear(facts):
            for paper in facts["papers"]:
                if paper["item_key"] in ("AAAA1111", "BBBB2222"):
                    paper["analysis_level"] = None
        self.patch_facts(clear)
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_facts", out)
        self.assertIn("analysis_level_conflict", out["message"])
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(analysis_path.read_bytes(), before_md)

    def test_missing_level_field_against_a_known_registration_is_rejected(self):
        self.stage2_finalize()
        pack_path = self.prof_dir / "套磁候选输入.json"
        analysis_path = self.analysis_md()
        before_pack = pack_path.read_bytes()
        before_md = analysis_path.read_bytes()

        def drop(facts):
            for paper in facts["papers"]:
                if paper["item_key"] == "AAAA1111":
                    paper.pop("analysis_level", None)
        self.patch_facts(drop)
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_facts", out)
        self.assertIn("analysis_level_conflict", out["message"])
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(analysis_path.read_bytes(), before_md)

    def test_unknown_level_accepts_null_then_a_new_registration_turns_known(self):
        self.levels = {"AAAA1111": None, "BBBB2222": "abstract"}
        self.write_index()
        self.bind_levels()
        index_path = self.prof_dir / "论文分析" / "_index.json"
        index_before = index_path.read_bytes()
        self.build_accepted_state()
        self.assertEqual(index_path.read_bytes(), index_before)
        pack = self._read_pack()
        self.assertIsNone(pack["papers"]["AAAA1111"]["analysis_level"])

        # The next preflight does not revive a known level from the accepted
        # canonical pack while the producer still registers no level.
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertIsNone(self._read_pack()["papers"]["AAAA1111"]["analysis_level"])

        # The producer's next real success updates the same registration; the
        # earlier null must not keep suppressing it.
        self.levels["AAAA1111"] = "fulltext"
        self.write_index()
        plan = self.save_preflight("new-known.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["changed_levels"], {"AAAA1111": "fulltext"})
        pack = self._read_pack()
        self.assertEqual(pack["papers"]["AAAA1111"]["analysis_level"], "fulltext")
        self.assertNotIn("validator", pack)

    def test_abstract_registration_survives_a_failed_fulltext_upgrade(self):
        # The PDF exists, but the current successful registration is abstract.
        # A failed full-text upgrade must not turn that valid abstract source
        # into fulltext or null.
        pdf = self.prof_dir / "论文分析" / "BBBB2222.pdf"
        pdf.write_bytes(b"%PDF-1.4 synthetic test document\n")

        def add_pdf(facts):
            for paper in facts["papers"]:
                if paper["item_key"] == "BBBB2222":
                    paper["pdf_file"] = str(pdf)
                    paper["has_pdf"] = True
        self.patch_facts(add_pdf)
        self.stage2_finalize()
        papers = self._read_pack()["papers"]
        self.assertEqual(papers["BBBB2222"]["analysis_level"], "abstract")
        self.assertTrue(papers["BBBB2222"]["pdf_available"])

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

    def test_current_legal_unknown_overrides_an_old_known_canonical(self):
        self.build_accepted_state()
        self.assertEqual(self._read_pack()["papers"]["AAAA1111"]["analysis_level"],
                         "fulltext")
        # The producer replaces the successful registration with a legal
        # unknown: the index entry still selects the same existing file but no
        # level remains. This is not a contradictory facts null.
        self.levels["AAAA1111"] = None
        self.write_index()
        self.bind_levels()
        plan = self.save_preflight("unknown-over-known.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        pack = self._read_pack()
        self.assertIsNone(pack["papers"]["AAAA1111"]["analysis_level"])
        # The old known canonical must not be restored on the next preflight.
        payload = self.preflight()
        self.assertEqual(payload["action"], "process", payload)
        self.assertIsNone(self._read_pack()["papers"]["AAAA1111"]["analysis_level"])

    def test_missing_level_field_in_an_old_pack_reads_as_null(self):
        self.build_accepted_state()
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = self._read_pack()
        for record in pack["papers"].values():
            record.pop("analysis_level", None)
        # Keep the accepted cache/validator containers and rebind the validator
        # to this fixture before the tested call. The fixture is a self-consistent
        # old accepted schema-2 pack whose paper records predate the field.
        validator = pack.get("validator")
        if isinstance(validator, dict):
            validator["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
        self._write_pack(pack)
        raw_before = pack_path.read_bytes()
        raw = read_json(pack_path)
        deep_before = copy.deepcopy(raw)

        # The compatibility record view shows the old missing field as null and
        # does not mutate the raw pack or its nested paper records.
        compatibility = contact_state._canonical_paper_record(raw["papers"]["AAAA1111"])
        self.assertEqual(pack_path.read_bytes(), raw_before)
        self.assertEqual(raw, deep_before)
        self.assertNotIn("analysis_level", raw["papers"]["AAAA1111"])
        self.assertIsNone(compatibility["analysis_level"])
        self.assertIsNone(
            contact_state._canonical_paper_record(
                raw["papers"]["BBBB2222"])["analysis_level"])

        # It is not a new facts declaration and must not block the current known
        # registration on the next normal acceptance. The compatibility-view
        # check above only observes the raw pack; the product-internal old
        # snapshot is covered by the shared finalize binding review.
        out = parse(self.finalize_with_current_proof())
        self.assertEqual(out["status"], "ok", out)
        papers = self._read_pack()["papers"]
        self.assertEqual(papers["AAAA1111"]["analysis_level"], "fulltext")
        self.assertEqual(papers["BBBB2222"]["analysis_level"], "abstract")

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

    def test_normal_finalize_rejects_consumed_artifact_stat_drift(self):
        self.build_accepted_state()
        plan = self.save_preflight("finalize-artifact-drift.json")
        self.assertEqual(read_json(plan)["action"], "reuse_all")
        self.bind_facts_to_plan(plan)
        plan_out = parse(run_cli("stage2-plan", "--facts", self.facts_path,
                                 "--preflight-file", plan))
        self.assertEqual(plan_out["status"], "ok", plan_out)
        self.assertEqual(plan_out["jobs"], [], plan_out)
        self.assertFalse(plan_out["write_needed"], plan_out)
        self.assertEqual({entry["action"] for entry in plan_out["directions"]},
                         {"reuse"}, plan_out)

        pack = self._read_pack()
        self.assert_validation_report_bound(pack)
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        validation_path = self.root / "validation.json"
        pack_before = pack_path.read_bytes()
        md_before = md_path.read_bytes()
        cache_before = cache_path.read_bytes()
        validation_before = validation_path.read_bytes()
        facts_before = self.facts_path.read_bytes()
        target_before = self.target_file.read_bytes()
        snapshot_path = self.prof_dir / "套磁阶段1候选.json"
        snapshot_before = snapshot_path.read_bytes()
        index_path = self.prof_dir / "论文分析" / "_index.json"
        index_before = index_path.read_bytes()
        plan_before = plan.read_bytes()
        sidecars = {}
        for paper in self.facts["papers"]:
            sidecar = paper.get("sidecar_file")
            if sidecar:
                sidecars[sidecar] = Path(sidecar).read_bytes()
        results_before = {path.name: path.read_bytes()
                          for path in sorted((self.root / "results").iterdir())
                          if path.is_file()}
        guards_before = copy.deepcopy(pack["cache"]["preflight"]["directions"])
        # BBBB2222 is shared by both directions, so the accepted narrative covers
        # every direction this finalize may need; an unrelated "unexpected
        # direction" result error cannot replace the consumed-source guard.
        analysis = self.prof_dir / "论文分析" / "BBBB2222.md"
        source_before = analysis.read_bytes()
        index = read_json(index_path)
        self.assertEqual(index["papers"]["BBBB2222"]["level"], "abstract")

        changed = source_before + b"\n<!-- source changed after consumption -->\n"
        analysis.write_bytes(changed)
        self.assertGreater(len(changed), len(source_before))
        self.assertEqual(read_json(index_path), index)

        payload = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                                "--results", self.root / "results",
                                "--preflight-file", plan))
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertEqual(payload["reason_code"], "preflight_inputs_changed", payload)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(md_path.read_bytes(), md_before)
        self.assertEqual(cache_path.read_bytes(), cache_before)
        self.assertEqual(validation_path.read_bytes(), validation_before)
        self.assertEqual(self.facts_path.read_bytes(), facts_before)
        self.assertEqual(self.target_file.read_bytes(), target_before)
        self.assertEqual(snapshot_path.read_bytes(), snapshot_before)
        self.assertEqual(index_path.read_bytes(), index_before)
        self.assertEqual(plan.read_bytes(), plan_before)
        self.assertEqual({key: Path(key).read_bytes() for key in sidecars}, sidecars)
        self.assertEqual({path.name: path.read_bytes()
                          for path in sorted((self.root / "results").iterdir())
                          if path.is_file()}, results_before)
        pack_after = self._read_pack()
        self.assertEqual(pack_after["cache"]["preflight"]["directions"], guards_before)
        self.assertEqual(analysis.read_bytes(), changed)

        next_payload = self.preflight()
        self.assertEqual(next_payload["action"], "process", next_payload)
        self.assertIn("artifact_changed",
                      self.direction(next_payload, "DIR00001")["reason_codes"],
                      next_payload)

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
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        pack_before, md_before = pack_path.read_bytes(), md_path.read_bytes()
        plan = self.save_preflight("refresh-bad-binding.json")
        result = self.refresh(plan)
        payload = parse(result)
        self.assertEqual(payload["status"], "error", (result.stdout, result.stderr))
        self.assertEqual(payload["reason_code"], "validation_render_stale", payload)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(md_path.read_bytes(), md_before)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

    def _break_managed_state_fingerprint(self):
        md = self.analysis_md()
        header, body = split_managed_bytes(md.read_bytes())
        broken = re.sub(rb"(?m)^state_fingerprint: .*$",
                        b"state_fingerprint: " + b"0" * 64, header) + body
        md.write_bytes(broken)
        return broken

    def test_invalid_old_header_binding_is_an_evidence_error_not_a_rebind(self):
        self.make_shared_level_pair()
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "fulltext"}
        self.write_index()
        md = self.analysis_md()
        broken = self._break_managed_state_fingerprint()
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack_before = pack_path.read_bytes()
        plan = self.save_preflight("refresh-bad-header.json")
        payload = parse(self.refresh(plan))
        self.assertEqual(payload["status"], "error", payload)
        self.assertTrue(payload.get("reason_code"), payload)
        self.assertNotIn(payload.get("reason_code"),
                         {"invalid_params", "invalid_facts",
                          "preflight_inputs_changed", "refresh_requires_process",
                          "stage2_writer_busy", "stage2_managed_write_failed",
                          "stage2_pack_write_failed"},
                         payload)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(md.read_bytes(), broken)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

    def test_normal_acceptance_rejects_an_invalid_old_header_binding(self):
        self.build_accepted_state()
        broken = self._break_managed_state_fingerprint()

        def rename(facts):
            # Projection-only change: the body and business basis stay equal, so
            # the normal finalize reaches the old-certification branch.
            facts["directions"][0]["collection_key"] = "DIR00001-renamed"
        self.patch_facts(rename)
        plan = self.save_preflight("finalize-bad-header.json")
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack_before = pack_path.read_bytes()
        payload = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                                "--results", self.root / "results",
                                "--preflight-file", plan))
        self.assertEqual(payload["status"], "error", payload)
        self.assertIn("validation", payload.get("reason_code", ""), payload)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(self.analysis_md().read_bytes(), broken)

    def test_normal_acceptance_rejects_an_invalid_old_validator_binding(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["validator"]["render_sha256"] = "0" * 64
        self._write_pack(pack)

        def rename(facts):
            facts["directions"][0]["collection_key"] = "DIR00001-renamed"
        self.patch_facts(rename)
        plan = self.save_preflight("finalize-bad-validator.json")
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        pack_before, md_before = pack_path.read_bytes(), md_path.read_bytes()
        payload = parse(run_cli("stage2-finalize", "--facts", self.facts_path,
                                "--results", self.root / "results",
                                "--preflight-file", plan))
        self.assertEqual(payload["status"], "error", payload)
        self.assertIn("validation", payload.get("reason_code", ""), payload)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(md_path.read_bytes(), md_before)

    def test_legacy_statistics_body_is_reaccepted_before_the_marker(self):
        self.build_accepted_state()
        md = self.analysis_md()
        text = md.read_bytes().decode("utf-8")
        legacy = re.sub(
            r"数据来源：全文级 \d+ 篇 · 摘要级 \d+ 篇 · 未确认 \d+ 篇（共 \d+ 篇）",
            "数据来源：全文级 3 篇 · 摘要级 1 篇（共 4 篇）", text)
        self.assertNotEqual(legacy, text)
        header, body = contact_state.split_frontmatter(legacy)
        self.assertEqual(header["managed_by"], "contact_state")
        body_sha = sha256_bytes(body.encode("utf-8"))
        # The legacy body is a legal old state: its actual header, cache and
        # validator all bind the bytes that are really on disk. The fixture must
        # not rely on a stale header to reach the old-format branch.
        legacy = re.sub(r"(?m)^render_sha256: .*$",
                        f"render_sha256: {body_sha}", legacy, count=1)
        md.write_bytes(legacy.encode("utf-8"))
        pack = self._read_pack()
        pack["cache"]["preflight"]["statistics_version"] = None
        pack["cache"]["render"]["套磁候选分析.md"]["sha256"] = body_sha
        validator = pack.get("validator")
        if isinstance(validator, dict):
            validator["render_sha256"] = body_sha
            validator["validation_render_sha256"] = body_sha
            validator["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
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

    def test_statistics_marker_only_refresh_keeps_the_old_body_bytes(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"]["preflight"]["statistics_version"] = None
        validator = pack.get("validator")
        if isinstance(validator, dict):
            validator["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
        self._write_pack(pack)
        before = self.analysis_md().read_bytes()
        _, body = split_managed_bytes(before)
        before_sha = sha256_bytes(body)
        plan = self.save_preflight("marker-only.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        self.assertFalse(out["md_written"], out)
        self.assertTrue(out["validator_preserved"], out)
        self.assertEqual(self.analysis_md().read_bytes(), before)
        self.assertEqual(out["md_sha256"], before_sha)
        updated = self._read_pack()
        self.assertEqual(updated["cache"]["render"][contact_state.ANALYSIS_MD]["sha256"],
                         before_sha)
        self.assertEqual(updated["validator"]["render_sha256"], before_sha)
        self.assertEqual(
            updated["cache"]["preflight"]["statistics_version"], 1)

    def test_refresh_preserves_rendered_ownership_and_u1(self):
        self.build_accepted_state()
        pack = self._read_pack()
        before = copy.deepcopy(pack["cache"]["render"][contact_state.ANALYSIS_MD])
        self.assertIn("ownership", before)
        self.assertIn("u1", before)
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("refresh-ownership.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        self.assertTrue(out["md_written"], out)
        after = self._read_pack()["cache"]["render"][contact_state.ANALYSIS_MD]
        self.assertNotEqual(after["sha256"], before["sha256"])
        self.assertEqual(after.get("u1"), before["u1"])
        ownership = after.get("ownership")
        self.assertIsInstance(ownership, dict, after)
        self.assertIn("version", ownership)
        self.assertIn("line_count", ownership)
        self.assertIn("fragments", ownership)
        self.assertEqual(ownership.get("body_sha256"), after["sha256"])
        _, body = split_managed_bytes(self.analysis_md().read_bytes())
        self.assertEqual(after["sha256"], sha256_bytes(body))

    def test_refresh_with_an_illegal_index_level_returns_needs_refresh(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("invalid-level-refresh.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        index_path = self.prof_dir / "论文分析" / "_index.json"
        index = read_json(index_path)
        index["papers"]["AAAA1111"]["level"] = "partial"
        write_json(index_path, index)
        pack_path = self.prof_dir / "套磁候选输入.json"
        before = pack_path.read_bytes()
        payload = parse(self.refresh(plan))
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertIn(payload.get("reason_code"),
                      {"refresh_requires_process", "preflight_inputs_changed"}, payload)
        self.assertEqual(pack_path.read_bytes(), before)

    def _rewrite_managed_crlf(self):
        md = self.analysis_md()
        header, body = split_managed_bytes(md.read_bytes())
        match = re.search(rb"(?m)^state_fingerprint: (.*)$", header)
        self.assertIsNotNone(match)
        state_fingerprint = match.group(1).decode("utf-8")
        crlf_body = body.replace(b"\n", b"\r\n")
        md.write_bytes(managed_bytes(crlf_body, state_fingerprint, newline=b"\r\n"))
        body_sha = sha256_bytes(crlf_body)
        pack = self._read_pack()
        render_entry = pack["cache"]["render"]["套磁候选分析.md"]
        render_entry["sha256"] = body_sha
        ownership = render_entry.get("ownership")
        if isinstance(ownership, dict):
            # Rewriting the body line endings changes its byte hash; the
            # ownership map must still describe the bytes on disk.
            ownership["body_sha256"] = body_sha
        validator = pack.get("validator")
        if isinstance(validator, dict):
            validator["render_sha256"] = body_sha
            validator["validation_render_sha256"] = body_sha
            validator["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
        self._write_pack(pack)
        return crlf_body, body_sha

    def test_legal_crlf_managed_file_is_read_as_real_bytes(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"]["preflight"]["statistics_version"] = None
        self._write_pack(pack)
        crlf_body, body_sha = self._rewrite_managed_crlf()
        plan = self.save_preflight("crlf.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        # The renderer emits LF. A CRLF body is a real byte change, not an
        # equivalent body obtained from a universal-newline read.
        self.assertTrue(out["md_written"], out)
        written = self.analysis_md().read_bytes()
        _, written_body = split_managed_bytes(written)
        self.assertNotIn(b"\r\n", written_body)
        self.assertNotEqual(sha256_bytes(written_body), body_sha)
        updated = self._read_pack()
        self.assertEqual(updated["cache"]["render"][contact_state.ANALYSIS_MD]["sha256"],
                         sha256_bytes(written_body))
        self.assertNotIn("validator", updated)

    def test_crlf_body_without_a_matching_binding_is_not_accepted(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"]["preflight"]["statistics_version"] = None
        pack["validator"]["pack_sha256"] = \
            contact_state.stage2_pack_content_fingerprint(pack)
        self._write_pack(pack)
        plan = self.save_preflight("crlf-stale.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")

        pack = self._read_pack()
        self.assert_validation_report_bound(pack)
        schema_before = pack.get("schema")
        phase_before = pack["validator"].get("phase")
        round_before = pack["validator"].get("round")
        results_before = copy.deepcopy(pack["validator"]["results"])
        md = self.analysis_md()
        data = md.read_bytes()
        header, body = split_managed_bytes(data)
        self.assertTrue(body)
        self.assertIn(b"\n", body)
        self.assertTrue(data.endswith(body))
        self.assertNotIn(b"\r\n", body)
        state_match = re.search(rb"(?m)^state_fingerprint: (.*)$", header)
        render_match = re.search(rb"(?m)^render_sha256: (.*)$", header)
        self.assertIsNotNone(state_match)
        self.assertIsNotNone(render_match)
        self.assertEqual(render_match.group(1).decode("ascii"), sha256_bytes(body))
        self.assertEqual(pack["cache"]["render"][contact_state.ANALYSIS_MD]["sha256"],
                         sha256_bytes(body))
        self.assertEqual(pack["validator"]["render_sha256"], sha256_bytes(body))
        expected_state = sha256_bytes(json.dumps({
            "professor": pack["professor"],
            "directions": {d["direction_id"]: d.get("input_fingerprint")
                           for d in pack["directions"]},
        }, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        self.assertEqual(state_match.group(1).decode("utf-8"), expected_state)

        def pack_sha_without_validator(payload):
            without_validator = {k: v for k, v in payload.items() if k != "validator"}
            return sha256_bytes(json.dumps(without_validator, ensure_ascii=False,
                                           sort_keys=True).encode("utf-8"))

        self.assertEqual(pack["validator"]["pack_sha256"],
                         pack_sha_without_validator(pack))
        crlf_body = body.replace(b"\n", b"\r\n")
        self.assertNotEqual(crlf_body, body)
        self.assertNotEqual(sha256_bytes(crlf_body), sha256_bytes(body))
        broken = data[:len(data) - len(body)] + crlf_body
        md.write_bytes(broken)

        pack_path = self.prof_dir / "套磁候选输入.json"
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        validation_path = self.root / "validation.json"
        pack_before = pack_path.read_bytes()
        cache_before = cache_path.read_bytes()
        validation_before = validation_path.read_bytes()
        payload = parse(self.refresh(plan))
        self.assertIn(payload["status"], ("needs_decision", "error"), payload)
        self.assertEqual(payload.get("reason_code"),
                         "manual_markdown_changed" if payload["status"] == "needs_decision"
                         else "validation_render_stale", payload)
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(md.read_bytes(), broken)
        self.assertEqual(cache_path.read_bytes(), cache_before)
        self.assertEqual(validation_path.read_bytes(), validation_before)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())
        pack_after = self._read_pack()
        self.assert_validation_report_bound(pack_after)
        self.assertEqual(pack_after.get("schema"), schema_before)
        self.assertEqual(pack_after["validator"].get("phase"), phase_before)
        self.assertEqual(pack_after["validator"].get("round"), round_before)
        self.assertEqual(pack_after["validator"]["results"], results_before)
        self.assertEqual(pack_after["validator"]["pack_sha256"],
                         pack_sha_without_validator(pack_after))

    def test_preflight_reuses_a_legal_crlf_managed_file(self):
        self.build_accepted_state()
        self._rewrite_managed_crlf()
        payload = self.preflight()
        self.assertEqual(payload["action"], "reuse_all", payload)
        self.assertNotIn("validator_not_accepted",
                         self.direction(payload, "DIR00001")["reason_codes"], payload)

    def test_validation_recording_accepts_a_legal_crlf_managed_file(self):
        self.stage2_finalize()
        _crlf_body, body_sha = self._rewrite_managed_crlf()
        self.record_validation()
        pack = self._read_pack()
        self.assertEqual(pack["cache"]["render"][contact_state.ANALYSIS_MD]["sha256"],
                         body_sha)
        self.assertEqual(pack["validator"]["render_sha256"], body_sha)

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
        # to bind the new business basis. Expected SHAs come from the actual
        # stored bytes, not from a decoding helper.
        _, body_before = split_managed_bytes(before)
        header_after, body_after = split_managed_bytes(self.analysis_md().read_bytes())
        self.assertEqual(body_after, body_before)
        match = re.search(rb"(?m)^render_sha256: (.*)$", header_after)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).decode("ascii"), sha256_bytes(body_after))
        pack = self._read_pack()
        self.assertNotIn("validator", pack)
        self.assertEqual(pack["cache"]["render"]["套磁候选分析.md"]["sha256"],
                         sha256_bytes(body_after))
        self.assertEqual(out["md_sha256"], sha256_bytes(body_after))
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

    def _analysis_path(self) -> Path:
        return self.prof_dir / "论文分析" / "AAAA1111.md"

    def _drift_after_lease(self):
        """Change an existing consumed analysis after the lease, before re-read."""
        analysis = self._analysis_path()
        state = {"mutated": False}
        original_init = contact_state.Stage2PackRefineContext.__init__

        def init_then_drift(instance, *arguments, **keywords):
            original_init(instance, *arguments, **keywords)
            if not state["mutated"]:
                state["mutated"] = True
                analysis.write_text("# drift after the lease\n", encoding="utf-8")

        contact_state.Stage2PackRefineContext.__init__ = init_then_drift
        self.addCleanup(setattr, contact_state.Stage2PackRefineContext,
                        "__init__", original_init)

    def _drift_after_observation(self):
        """Change the same source at the post-gate render stage, before the write.

        The refresh gate runs before ``stage2_render_precheck``; that check is
        the first existing post-gate consumer of ``Stage2PackRefineContext``.
        Hooking its static helper places the change after the gate observation
        and before the managed write, independent of when the old Markdown is
        read. The hook is installed disarmed and armed only after the zero-write
        snapshots, so setup reads cannot trigger it.
        """
        analysis = self._analysis_path()
        context_class = contact_state.Stage2PackRefineContext
        original_descriptor = context_class.__dict__["narrative_later_keys_for"]
        original = original_descriptor.__func__
        state = {"armed": False, "mutated": False}

        def arm():
            state["armed"] = True

        def record_then_drift(direction):
            if state["armed"] and not state["mutated"]:
                state["mutated"] = True
                analysis.write_text("# drift after the observation\n", encoding="utf-8")
            return original(direction)

        context_class.narrative_later_keys_for = staticmethod(record_then_drift)
        self.addCleanup(setattr, context_class, "narrative_later_keys_for",
                        original_descriptor)
        return arm

    def _drift_accepted_pack_after_observation(self):
        """Externally update the accepted pack after the gate, before the write.

        The same post-gate render-precheck hook is used, but it changes the
        accepted pack (a new cache entry plus a self-consistent validator pack
        fingerprint) instead of the analysis source. The pack has already been
        read by the refresh context, so the old context must stop rather than
        overwrite the externally updated snapshot.
        """
        pack_path = self.prof_dir / "套磁候选输入.json"
        context_class = contact_state.Stage2PackRefineContext
        original_descriptor = context_class.__dict__["narrative_later_keys_for"]
        original = original_descriptor.__func__
        state = {"armed": False, "triggered": 0, "external_bytes": None}

        def arm():
            state["armed"] = True

        def record_then_drift(direction):
            if state["armed"] and state["triggered"] == 0:
                state["triggered"] += 1
                pack = read_json(pack_path)
                pack["cache"]["foreign_cache"] = {"kept": True, "revision": 2}
                pack["validator"]["pack_sha256"] = \
                    contact_state.stage2_pack_content_fingerprint(pack)
                write_json(pack_path, pack)
                state["external_bytes"] = pack_path.read_bytes()
            return original(direction)

        context_class.narrative_later_keys_for = staticmethod(record_then_drift)
        self.addCleanup(setattr, context_class, "narrative_later_keys_for",
                        original_descriptor)
        return arm, state

    def _refresh_in_process(self, plan):
        """Run the real refresh handler in this process so the drift doubles apply."""
        arguments = type("Args", (), {
            "program_root": str(self.root), "professor": PROFESSOR,
            "target_file": str(self.target_file), "preflight_file": str(plan),
            "decision_file": None})()
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                contact_state.cmd_stage2_refresh_level(arguments)
            except SystemExit:
                pass
        return json.loads(stdout.getvalue())

    def _assert_zero_write_needs_refresh(self, plan, arm=None):
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        before_pack, before_md = pack_path.read_bytes(), md_path.read_bytes()
        if arm is not None:
            # Arm only after the zero-write snapshots: the observation-point
            # drift must happen inside the refresh handler, not during setup.
            arm()
        payload = self._refresh_in_process(plan)
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertIn(payload.get("reason_code"),
                      {"preflight_inputs_changed", "refresh_requires_process"}, payload)
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(md_path.read_bytes(), before_md)
        self.assertFalse((self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())
        # After the drift the next preflight must go back to process instead of
        # continuing with a level-only refresh or claiming reuse.
        next_payload = self.preflight()
        self.assertEqual(next_payload["action"], "process", next_payload)
        self.assertIn("artifact_changed",
                      self.direction(next_payload, "DIR00001")["reason_codes"],
                      next_payload)
        return payload

    def test_source_drift_after_lease_returns_needs_refresh(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("lease-drift.json")
        self._drift_after_lease()
        self._assert_zero_write_needs_refresh(plan)

    def test_source_drift_after_observation_returns_needs_refresh(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("observation-drift.json")
        arm = self._drift_after_observation()
        self._assert_zero_write_needs_refresh(plan, arm)

    def test_accepted_pack_drift_after_observation_returns_needs_refresh(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("accepted-pack-drift.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")

        def pack_sha_without_validator(data):
            payload = json.loads(data)
            payload.pop("validator", None)
            return sha256_bytes(json.dumps(payload, ensure_ascii=False,
                                           sort_keys=True).encode("utf-8"))

        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        validation_path = self.root / "validation.json"
        before_pack = pack_path.read_bytes()
        before_pack_obj = json.loads(before_pack)
        self.assert_validation_report_bound(before_pack_obj)
        before_md, before_cache = md_path.read_bytes(), cache_path.read_bytes()
        before_validation = validation_path.read_bytes()
        self.assertEqual(before_pack_obj["validator"]["pack_sha256"],
                         pack_sha_without_validator(before_pack))

        arm, state = self._drift_accepted_pack_after_observation()
        arm()
        payload = self._refresh_in_process(plan)
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertIn(payload.get("reason_code"),
                      {"preflight_inputs_changed", "refresh_requires_process"}, payload)
        self.assertEqual(state["triggered"], 1)
        self.assertIsNotNone(state["external_bytes"])
        self.assertNotEqual(state["external_bytes"], before_pack)
        external = json.loads(state["external_bytes"])
        self.assertEqual(external["cache"]["foreign_cache"],
                         {"kept": True, "revision": 2})
        self.assertEqual(external["validator"]["pack_sha256"],
                         pack_sha_without_validator(state["external_bytes"]))
        self.assertEqual(external["validator"]["validation_sha256"],
                         sha256_bytes(before_validation))
        # The external update may only add cache.foreign_cache and rebind the
        # validator pack hash; levels, directions, state/render bindings and
        # validator results must remain the accepted snapshot.
        normalized_external = copy.deepcopy(external)
        normalized_before = copy.deepcopy(before_pack_obj)
        for payload_obj in (normalized_external, normalized_before):
            payload_obj["cache"].pop("foreign_cache", None)
            payload_obj["validator"].pop("pack_sha256", None)
        self.assertEqual(normalized_external, normalized_before)
        self.assertEqual(pack_path.read_bytes(), state["external_bytes"])
        self.assertEqual(md_path.read_bytes(), before_md)
        self.assertEqual(cache_path.read_bytes(), before_cache)
        self.assertEqual(validation_path.read_bytes(), before_validation)
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
        validator = pack.get("validator")
        if isinstance(validator, dict):
            # The added cache/resolved fields are part of the accepted pack;
            # keep the old validation binding legal before exercising refresh.
            validator["pack_sha256"] = contact_state.stage2_pack_content_fingerprint(pack)
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
        # The half-written state must not be reused. The next preflight cannot
        # inherit the old certification; it either processes or re-enters the
        # bounded refresh, but never reuse_all.
        next_payload = self.preflight()
        self.assertNotEqual(next_payload["action"], "reuse_all", next_payload)
        self.assertIn("validator_not_accepted",
                      self.direction(next_payload, "DIR00001")["reason_codes"],
                      next_payload)


class TestManagedBodyBytes(unittest.TestCase):
    """Only the fixed renderer generation timestamp may be ignored, on disk bytes."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "套磁候选分析.md"
        self.state_fingerprint = "sf-1"
        self.body = (
            "# 套磁候选分析 — P\n\n"
            "$$\\newcommand{\\dif}{\\mathop{}\\!\\mathrm{d}}$$\n\n"
            "> 2026-01-01T00:00:00Z ｜ 数据来源：全文级 1 篇 · 摘要级 2 篇 · "
            "未确认 1 篇（共 4 篇）｜ 由 contact_state 确定性渲染（重跑=全量重写）\n"
            "计划于 2026-01-01T00:00:00Z 推进后续工作。\n"
        ).encode("utf-8")

    def _write_managed(self, body, *, newline=b"\n", render_sha256=None):
        body_sha = render_sha256 if render_sha256 is not None else sha256_bytes(body)
        data = managed_bytes(body, self.state_fingerprint, newline=newline,
                             render_sha256=body_sha)
        self.path.write_bytes(data)
        return body_sha

    def _accept(self, candidate):
        return contact_state.stage2_accept_managed_body(
            self.path, candidate.decode("utf-8"), sha256_bytes(self.body), None,
            self.state_fingerprint,
            contact_state.stage2_old_managed_render(self.path))

    def test_only_the_fixed_generation_time_is_ignored(self):
        body_sha = self._write_managed(self.body)
        old = contact_state.stage2_old_managed_render(self.path)
        self.assertTrue(old["readable"], old)
        self.assertTrue(old["binding_valid"], old)
        self.assertEqual(old["body"].encode("utf-8"), self.body)
        self.assertEqual(old["body_sha256"], body_sha)
        later = self.body.replace(b"2026-01-01T00:00:00Z", b"2026-02-02T03:04:05Z", 1)
        result = self._accept(later)
        self.assertFalse(result["written"], result)
        self.assertEqual(result["sha256"], body_sha)
        self.assertEqual(self.path.read_bytes(),
                         managed_bytes(self.body, self.state_fingerprint))

    def test_statistics_and_narrative_time_stay_significant(self):
        self._write_managed(self.body)
        statistics_changed = self.body.replace("全文级 1".encode(), "全文级 2".encode())
        result = self._accept(statistics_changed)
        self.assertFalse(result["equivalent"], result)
        self.assertTrue(result["written"], result)
        self.assertNotEqual(result["sha256"], sha256_bytes(self.body))

        self._write_managed(self.body)
        narrative_changed = self.body.replace(
            b"2026-01-01T00:00:00Z", b"2026-03-03T00:00:00Z", 2)
        result = self._accept(narrative_changed)
        self.assertFalse(result["equivalent"], result)
        self.assertTrue(result["written"], result)

        self._write_managed(self.body)
        result = self._accept(self.body.rstrip(b"\n"))
        self.assertFalse(result["equivalent"], result)
        self.assertTrue(result["written"], result)

    def test_crlf_bytes_are_read_and_hashed_without_normalization(self):
        crlf = self.body.replace(b"\n", b"\r\n")
        body_sha = self._write_managed(crlf, newline=b"\r\n")
        old = contact_state.stage2_old_managed_render(self.path)
        self.assertTrue(old["readable"], old)
        self.assertTrue(old["binding_valid"], old)
        self.assertEqual(old["body"].encode("utf-8"), crlf)
        self.assertEqual(old["body_sha256"], body_sha)

    def test_legal_crlf_body_keeps_its_bytes_when_only_the_header_changes(self):
        crlf = self.body.replace(b"\n", b"\r\n")
        body_sha = self._write_managed(crlf, newline=b"\r\n")
        old = contact_state.stage2_old_managed_render(self.path)
        self.assertTrue(old["binding_valid"], old)
        later = crlf.replace(b"2026-01-01T00:00:00Z", b"2026-02-02T03:04:05Z", 1)
        result = contact_state.stage2_accept_managed_body(
            self.path, later.decode("utf-8"), body_sha, None, "sf-2", old)
        self.assertTrue(result["written"], result)
        self.assertEqual(result["sha256"], body_sha)
        header, body = split_managed_bytes(self.path.read_bytes())
        self.assertEqual(body, crlf)
        self.assertIn(b"state_fingerprint: sf-2", header)
        match = re.search(rb"(?m)^render_sha256: (.*)$", header)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).decode("ascii"), sha256_bytes(body))

    def test_crlf_body_without_a_matching_binding_is_not_accepted(self):
        crlf = self.body.replace(b"\n", b"\r\n")
        lf_sha = sha256_bytes(self.body)
        self._write_managed(crlf, newline=b"\r\n", render_sha256=lf_sha)
        old = contact_state.stage2_old_managed_render(self.path)
        self.assertFalse(old["binding_valid"], old)
        result = self._accept(self.body)
        self.assertTrue(result["needs_decision"], result)
        self.assertFalse(result["written"], result)

    def test_a_crlf_old_body_and_an_lf_candidate_are_a_change(self):
        crlf = self.body.replace(b"\n", b"\r\n")
        body_sha = self._write_managed(crlf, newline=b"\r\n")
        old = contact_state.stage2_old_managed_render(self.path)
        result = contact_state.stage2_accept_managed_body(
            self.path, self.body.decode("utf-8"), body_sha, None,
            self.state_fingerprint, old)
        self.assertFalse(result["equivalent"], result)
        self.assertTrue(result["written"], result)
        self.assertNotEqual(result["sha256"], body_sha)
        _, body = split_managed_bytes(self.path.read_bytes())
        self.assertEqual(body, self.body)


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
            # L1's static facts contract: new facts must follow the current
            # registration, and a conflicting known value must be rejected
            # instead of silently rewritten.
            self.assertIn("按与 runner 相同的资格规则", document)
            self.assertIn("没有成功登记、文件缺失、路径不符或无法确认时一律传",
                          document)
            self.assertIn("已知值与当前登记冲突会被 runner 按输入错误拒绝", document)
            self.assertIn("不得静默改传另一个已知值", document)


if __name__ == "__main__":
    unittest.main()
