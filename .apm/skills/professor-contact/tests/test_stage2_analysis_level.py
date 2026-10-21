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
import inspect
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        if getattr(self, "outer_candidate", False):
            papers["CCCC3333"] = read_json(
                self.prof_dir / "论文分析" / "_index.json")["papers"]["CCCC3333"]
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
        plan = getattr(self, "consumption_plan", None)
        if plan is not None:
            # Keep the existing legal model answers, but emit exactly the
            # current plan's jobs instead of adding reused directions.
            jobs = plan["jobs"]
            requested = {job["result_file"] for job in jobs}
            for filename in ("freshness-DIR00001.json", "freshness-DIR00002.json",
                             "narrative.json"):
                path = results / filename
                if filename not in requested:
                    path.unlink(missing_ok=True)
                    continue
                payload = read_json(path)
                if filename == "narrative.json":
                    direction_ids = {job["direction_id"] for job in jobs
                                     if job["kind"] == "narrative"}
                    payload["directions"] = [row for row in payload["directions"]
                                             if (row.get("direction_id") or
                                                 row.get("collection_key")) in direction_ids]
                else:
                    gap_ids = {gap["gap_id"] for job in jobs
                               if job["result_file"] == filename
                               for gap in job["model_input"]["gaps"]}
                    payload["results"] = [row for row in payload["results"]
                                          if row["gap_id"] in gap_ids]
                write_json(path, payload)
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
        payload = self.preflight(gap_scope=self.facts["params"]["gap_scope"])
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

    # -- consumption transaction helpers -----------------------------------

    def prepare_consumption(self):
        """Freeze the current sources and bind the companion into facts."""
        self.consumption_plan = None
        run_dir = Path(tempfile.mkdtemp(prefix="consumption-", dir=self.root))
        preflight_path = self.save_preflight(run_dir / "preflight.json")
        preflight = read_json(preflight_path)
        out = parse(run_cli(
            "stage2-consumption-prepare",
            "--program-root", self.root, "--professor", PROFESSOR,
            "--target-file", self.target_file, "--preflight-file", preflight_path,
            "--run-dir", run_dir))
        self.assertEqual(out["status"], "ok", out)
        companion_path = Path(out["consumption_file"])
        facts = read_json(self.facts_path)
        block = facts.setdefault("stage2_preflight", {})
        block["preflight_id"] = preflight["preflight_id"]
        block["consumption"] = {
            "file": str(companion_path), "run_id": out["run_id"],
            "sources_sha256": out["sources_sha256"]}
        write_json(self.facts_path, facts)
        self.facts = facts
        return preflight_path, run_dir, read_json(companion_path)

    def stage2_finalize(self):
        proof, run_dir, _companion = self.prepare_consumption()
        self.plan_consumption(proof, run_dir)
        self.write_stage2_results()
        self.seal_consumption(run_dir)
        out = self.finalize_consumption(proof)
        self.assertEqual(out["status"], "ok", out)
        return out

    def build_accepted_state(self):
        self.stage2_finalize()
        self.record_validation()
        self.assert_validation_report_bound()

    def plan_consumption(self, preflight_path, run_dir):
        out = parse(run_cli(
            "stage2-plan", "--facts", self.facts_path,
            "--preflight-file", preflight_path, "--run-dir", run_dir))
        self.assertEqual(out["status"], "ok", out)
        self.consumption_plan = out
        return out

    def seal_consumption(self, run_dir):
        out = parse(run_cli(
            "stage2-consumption-seal-results", "--run-dir", run_dir,
            "--results-dir", self.root / "results"))
        self.assertEqual(out["status"], "ok", out)
        return out

    def finalize_consumption(self, preflight_path, *extra):
        return parse(run_cli(
            "stage2-finalize", "--facts", self.facts_path,
            "--results", self.root / "results",
            "--preflight-file", preflight_path, *extra))

    def business_snapshot(self):
        paths = [self.prof_dir / "套磁候选输入.json", self.analysis_md(),
                 self.prof_dir / "论文分析" / "_freshness_cache.json",
                 self.root / "validation.json",
                 self.prof_dir / "论文分析" / "_resolved_directions.json"]
        return {path: path.read_bytes() if path.exists() else None for path in paths}

    def assert_business_unchanged(self, before):
        for path, raw in before.items():
            self.assertEqual(path.read_bytes() if path.exists() else None, raw, str(path))

    def call_handler(self, name, *, handler=None, **arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                (handler or getattr(contact_state, name))(type("Args", (), arguments)())
            except SystemExit:
                pass
        return json.loads(stdout.getvalue())

    def finalize_in_process(self, preflight_path, *, factory_overrides=None, **overrides):
        arguments = dict(facts=str(self.facts_path), results=str(self.root / "results"),
                         preflight_file=str(preflight_path), resolved_directions=None,
                         decision_file=None)
        arguments.update(overrides)
        handler = None
        if factory_overrides:
            # Use the existing factory seam: patching a public alias would not
            # replace the function already captured by the production closure.
            factory = contact_state._stage2_finalize_module.build
            dependencies = {name: getattr(contact_state, name)
                            for name in inspect.signature(factory).parameters
                            if name != "stage2_validation_legality"}
            dependencies["stage2_validation_legality"] = \
                contact_state._stage2_validation.stage2_validation_legality
            dependencies.update(factory_overrides)
            handler = factory(**dependencies).cmd_stage2_finalize
        return self.call_handler("cmd_stage2_finalize", handler=handler, **arguments)

    def prepare_outer_candidate(self):
        """Create E-only C before any proof; C is outside all direction inputs."""
        from test_stage2_resolved_direction import make_sidecar
        self.facts["params"]["gap_scope"] = "relevant"
        self.target["directions"][0]["members"] = [
            row for row in self.target["directions"][0]["members"]
            if row["item_key"] != "CCCC3333"]
        self.snapshot_entry["directions"][0]["provisional_member_keys"] = [
            "AAAA1111", "BBBB2222"]
        self.snapshot_entry["directions"][0]["expansion_reasons"]["CCCC3333"] = [
            "topic_expansion"]
        self.facts["directions"][0]["provisional_member_keys"] = [
            "AAAA1111", "BBBB2222"]
        paper = self.facts["papers"][2]
        paper["year"] = 2020
        analysis = self.prof_dir / "论文分析" / "CCCC3333.md"
        analysis.write_bytes(b"# Synthetic outer candidate\n")
        sidecar = make_sidecar(analysis, ["Future work will test an outer candidate."])
        paper.update(analysis_file=str(analysis), sidecar_file=str(sidecar),
                     analysis_level="abstract")
        self.catalog_papers[2]["year"] = 2020
        write_json(self.prof_dir / "papers.json", {"papers": self.catalog_papers})
        index_path = self.prof_dir / "论文分析" / "_index.json"
        index = read_json(index_path)
        index["papers"]["CCCC3333"] = dict(
            file=str(analysis), level="abstract", future_work_sidecar=str(sidecar),
            facts_sidecar=None)
        write_json(index_path, index)
        self.outer_candidate = True
        self._write_target()
        self._write_snapshot()
        write_json(self.facts_path, self.facts)

    def assert_outer_candidate(self, plan=None):
        pack = self._read_pack()
        meta = pack["cache"]["preflight"]
        self.assertIn("CCCC3333", meta["resolution_evidence_guards"])
        self.assertIn("CCCC3333", self.snapshot_entry["directions"][0]["candidate_keys"])
        ctx = contact_state.Stage2Context(self.facts_path)
        for direction in pack["directions"]:
            self.assertNotIn("CCCC3333", direction["supporting_item_keys"])
            for section in ("gap_shortlist", "gaps_excluded", "completed_gap_blacklist"):
                self.assertNotIn("CCCC3333", [gap["item_key"]
                                            for gap in direction.get(section, [])])
        for direction in self.facts["directions"]:
            self.assertNotIn("CCCC3333", direction["relevant_keys"])
            self.assertNotIn("CCCC3333", contact_state.gap_scope_keys(self.facts, direction))
        for record in meta["directions"].values():
            self.assertNotIn("CCCC3333", record["artifact_guards"])
        for entry in ctx.direction_plans:
            self.assertNotIn("CCCC3333", ctx.narrative_later_keys(entry))
        for job in (plan or {}).get("jobs", []):
            if job["kind"] == "narrative":
                self.assertNotIn("CCCC3333", [paper["item_key"] for paper in
                                             job["model_input"]["later_papers"]])


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

    def _assert_malformed_index_rejected(self, raw: bytes):
        # Isolate the nullable declaration: both known registrations are null,
        # so a rejection cannot come from the other paper's level conflict.
        for paper in self.facts["papers"]:
            if paper["item_key"] in ("AAAA1111", "BBBB2222"):
                paper["analysis_level"] = None
        write_json(self.facts_path, self.facts)
        preflight_path = self.save_preflight("malformed-index-preflight.json")
        index_path = self.prof_dir / "论文分析" / "_index.json"
        index_path.write_bytes(raw)
        run_dir = self.root / "run"
        run_dir.mkdir()
        out = parse(run_cli(
            "stage2-consumption-prepare", "--program-root", self.root,
            "--professor", PROFESSOR, "--target-file", self.target_file,
            "--preflight-file", preflight_path, "--run-dir", run_dir))
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_facts", out)
        self.assertEqual(index_path.read_bytes(), raw)
        self.assertFalse((run_dir / "stage2-consumption.json").exists())

    def test_malformed_index_cannot_be_accepted_as_null(self):
        self._assert_malformed_index_rejected(b"{broken")

    def test_empty_papers_index_cannot_be_accepted_as_null(self):
        self._assert_malformed_index_rejected(json.dumps({
            "schema": 2, "future_work_schema": 1, "professor": PROFESSOR,
            "generated_at": "2026-01-01T00:00:00Z", "papers": {}},
            ensure_ascii=False).encode("utf-8"))

    def _assert_context_rejects_malformed_index(self, raw: bytes):
        for paper in self.facts["papers"]:
            if paper["item_key"] in ("AAAA1111", "BBBB2222"):
                paper["analysis_level"] = None
        write_json(self.facts_path, self.facts)
        index_path = self.prof_dir / "论文分析" / "_index.json"
        index_path.write_bytes(raw)
        buffer = io.StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(buffer):
            contact_state.Stage2Context(self.facts_path)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["status"], "error", payload)
        self.assertEqual(payload["reason_code"], "invalid_facts", payload)
        self.assertEqual(index_path.read_bytes(), raw)

    def test_context_rejects_malformed_index_with_null_levels(self):
        self._assert_context_rejects_malformed_index(b"{broken")

    def test_context_rejects_empty_papers_with_null_levels(self):
        self._assert_context_rejects_malformed_index(json.dumps({
            "schema": 2, "future_work_schema": 1, "professor": PROFESSOR,
            "generated_at": "2026-01-01T00:00:00Z", "papers": {}},
            ensure_ascii=False).encode("utf-8"))

class TestConsumptionFreeze(AnalysisLevelBase):
    """L2/L4: a consumed run commits the sources frozen before facts."""

    def test_process_commits_the_frozen_sources(self):
        analysis_hashes = {
            key: sha256_bytes((self.prof_dir / "论文分析" / f"{key}.md").read_bytes())
            for key in ("AAAA1111", "BBBB2222")}
        frozen_guards = {}
        for key in analysis_hashes:
            source = self.prof_dir / "论文分析" / f"{key}.md"
            stat = source.stat()
            frozen_guards[key] = dict(
                path=str(source), size=stat.st_size, mtime_ns=stat.st_mtime_ns,
                ctime_ns=stat.st_ctime_ns, accepted_digest=analysis_hashes[key])
        preflight_path, run_dir, companion = self.prepare_consumption()
        plan = self.plan_consumption(preflight_path, run_dir)
        self.assertTrue(plan["jobs"], plan)
        self.assertEqual({job["kind"] for job in plan["jobs"]},
                         {"narrative", "freshness"})
        self.write_stage2_results()
        self.seal_consumption(run_dir)
        out = self.finalize_consumption(preflight_path)
        self.assertEqual(out["status"], "ok", out)
        pack = self._read_pack()
        meta = pack["cache"]["preflight"]
        self.assertEqual(meta["resolution_evidence_projection"],
                         companion["sources_projection"])
        for key, guard in frozen_guards.items():
            self.assertEqual(meta["resolution_evidence_guards"][key]["analysis"], guard)
        self.assertEqual(set(meta["directions"]), {"DIR00001", "DIR00002"})
        expected_keys = {"DIR00001": {"AAAA1111", "BBBB2222", "CCCC3333"},
                         "DIR00002": {"BBBB2222"}}
        for did, record in meta["directions"].items():
            self.assertEqual(record["source_projection"]["index"],
                             companion["sources_projection"]["index"])
            self.assertEqual(set(record["source_projection"]["papers"]),
                             expected_keys[did])
            for key, value in record["source_projection"]["papers"].items():
                self.assertEqual(companion["sources_projection"]["papers"][key], value)
        for key, digest in analysis_hashes.items():
            self.assertEqual(
                sha256_bytes((self.prof_dir / "论文分析" / f"{key}.md").read_bytes()),
                digest)
        self.assertEqual(pack["papers"]["AAAA1111"]["analysis_level"], "fulltext")
        self.assertEqual(pack["papers"]["BBBB2222"]["analysis_level"], "abstract")
        header = self.header_line()
        self.assertIn("全文级 1 篇", header)
        self.assertIn("摘要级 2 篇", header)
        self.assertIn("未确认 1 篇", header)
        # Companion content supply is checked separately at the actual prepare
        # read boundary; these guards must still equal the independent F0.

    def test_plan_rejects_a_source_change_after_prepare(self):
        preflight_path, run_dir, _companion = self.prepare_consumption()
        a_analysis = self.prof_dir / "论文分析" / "AAAA1111.md"
        a_analysis.write_bytes(a_analysis.read_bytes() + b"\n<!-- after freeze -->\n")
        out = parse(run_cli(
            "stage2-plan", "--facts", self.facts_path,
            "--preflight-file", preflight_path, "--run-dir", run_dir))
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assertIn(out.get("reason_code"),
                      {"invalid_facts", "preflight_inputs_changed"}, out)
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_finalize_rejects_a_missing_sealed_result(self):
        preflight_path, run_dir, _companion = self.prepare_consumption()
        self.plan_consumption(preflight_path, run_dir)
        self.write_stage2_results()
        self.seal_consumption(run_dir)
        (self.root / "results" / "freshness-DIR00001.json").unlink()
        out = self.finalize_consumption(preflight_path)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_result_json", out)
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_finalize_rejects_an_unsealed_companion(self):
        preflight_path, run_dir, _companion = self.prepare_consumption()
        self.plan_consumption(preflight_path, run_dir)
        self.write_stage2_results()
        self.seal_consumption(run_dir)
        run2 = self.root / "run2"
        run2.mkdir()
        second = parse(run_cli(
            "stage2-consumption-prepare",
            "--program-root", self.root, "--professor", PROFESSOR,
            "--target-file", self.target_file, "--preflight-file", preflight_path,
            "--run-dir", run2))
        self.assertEqual(second["status"], "ok", second)
        facts = read_json(self.facts_path)
        facts["stage2_preflight"]["consumption"] = {
            "file": second["consumption_file"], "run_id": second["run_id"],
            "sources_sha256": second["sources_sha256"]}
        write_json(self.facts_path, facts)
        out = self.finalize_consumption(preflight_path)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_result_json", out)
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_seal_results_supports_a_single_repair_revision(self):
        preflight_path, run_dir, _companion = self.prepare_consumption()
        self.plan_consumption(preflight_path, run_dir)
        results = self.write_stage2_results()
        correct_gap = quote_id(self.gap_quotes["AAAA1111"])
        narrative = read_json(results / "narrative.json")
        narrative["directions"][0]["gap_notes"][0]["gap_id"] = "broken-gap-id"
        write_json(results / "narrative.json", narrative)
        first = self.seal_consumption(run_dir)
        self.assertEqual(first["revision"], 0)
        failed = self.finalize_consumption(preflight_path)
        self.assertEqual(failed["status"], "error", failed)
        self.assertEqual(failed["reason_code"], "unknown_reference_id", failed)
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())
        original_files = {path.name: path.read_bytes() for path in results.iterdir()}
        frozen = read_json(run_dir / "stage2-consumption.json")
        repair = self.root / "repair-1"
        shutil.copytree(results, repair)
        repaired = read_json(repair / "narrative.json")
        repaired["directions"][0]["gap_notes"][0]["gap_id"] = correct_gap
        write_json(repair / "narrative.json", repaired)
        second = parse(run_cli(
            "stage2-consumption-seal-results", "--run-dir", run_dir,
            "--results-dir", repair))
        self.assertEqual(second["status"], "ok", second)
        self.assertEqual(second["revision"], 1, second)
        repaired_out = parse(run_cli(
            "stage2-finalize", "--facts", self.facts_path, "--results", repair,
            "--preflight-file", preflight_path))
        self.assertEqual(repaired_out["status"], "ok", repaired_out)
        accepted = self.business_snapshot()
        current = read_json(run_dir / "stage2-consumption.json")
        for field in ("sources_sha256", "sources_projection", "stage2_plan"):
            self.assertEqual(current[field], frozen[field])
        self.assertEqual({path.name: path.read_bytes() for path in results.iterdir()},
                         original_files)
        third = parse(run_cli(
            "stage2-consumption-seal-results", "--run-dir", run_dir,
            "--results-dir", repair))
        self.assertEqual(third["status"], "error", third)
        self.assertEqual(third["reason_code"], "invalid_params", third)
        self.assert_business_unchanged(accepted)

    def test_finalize_rejects_sealed_results_from_another_run(self):
        preflight_path, run1, _companion = self.prepare_consumption()
        self.plan_consumption(preflight_path, run1)
        results = self.write_stage2_results()
        narrative = read_json(results / "narrative.json")
        narrative["directions"][0]["positioning"][0]["text"] = "R1 sealed body"
        write_json(results / "narrative.json", narrative)
        self.seal_consumption(run1)
        r1_narrative = (results / "narrative.json").read_bytes()
        run2 = self.root / "run2"
        run2.mkdir()
        second = parse(run_cli(
            "stage2-consumption-prepare",
            "--program-root", self.root, "--professor", PROFESSOR,
            "--target-file", self.target_file, "--preflight-file", preflight_path,
            "--run-dir", run2))
        self.assertEqual(second["status"], "ok", second)
        facts = read_json(self.facts_path)
        facts["stage2_preflight"]["consumption"] = {
            "file": second["consumption_file"], "run_id": second["run_id"],
            "sources_sha256": second["sources_sha256"]}
        write_json(self.facts_path, facts)
        self.plan_consumption(preflight_path, run2)
        self.write_stage2_results()
        self.seal_consumption(run2)
        (self.root / "results" / "narrative.json").write_bytes(r1_narrative)
        out = self.finalize_consumption(preflight_path)
        self.assertEqual(out["status"], "error", out)
        self.assertEqual(out["reason_code"], "invalid_result_json", out)
        self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_process_finalize_rejects_frozen_source_drift(self):
        self.build_accepted_state()
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        before_pack = pack_path.read_bytes()
        before_md = md_path.read_bytes()
        self.facts["directions"][0]["user_note"] = "改成新的合成输入比较目标。"
        self.target["directions"][0]["user_note"] = "改成新的合成输入比较目标。"
        self._write_target()
        write_json(self.facts_path, self.facts)
        preflight_path, run_dir, _companion = self.prepare_consumption()
        self.assertEqual(read_json(preflight_path)["action"], "process")
        plan = self.plan_consumption(preflight_path, run_dir)
        self.assertTrue(plan["jobs"], plan)
        self.assertTrue(plan["write_needed"], plan)
        self.write_stage2_results()
        self.seal_consumption(run_dir)
        b_analysis = self.prof_dir / "论文分析" / "BBBB2222.md"
        b_analysis.write_bytes(b_analysis.read_bytes() + b"\n<!-- frozen source drift -->\n")
        out = self.finalize_consumption(preflight_path)
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertIn(out["reason_code"], {"preflight_inputs_changed"}, out)
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(md_path.read_bytes(), before_md)

class TestConsumptionBoundaries(AnalysisLevelBase):
    """The remaining t6 A-D boundaries; preparation never runs these cases."""

    def ready_run(self):
        proof, run_dir, companion = self.prepare_consumption()
        plan = self.plan_consumption(proof, run_dir)
        self.assertTrue(plan["jobs"], plan)
        self.write_stage2_results()
        self.seal_consumption(run_dir)
        return proof, run_dir, companion

    def test_finalize_rejects_bad_index_with_an_existing_freeze(self):
        for raw, declaration in ((b"{broken", None), (b'{"papers":{}}', "missing")):
            with self.subTest(raw=raw, declaration=declaration):
                # Each round seals legal unknown declarations first. Only the
                # index changes afterwards, so a facts-digest mismatch cannot
                # masquerade as rejection of the bad registration.
                case = AnalysisLevelBase()
                case.setUp()
                try:
                    case.levels = {"AAAA1111": None, "BBBB2222": None}
                    case.write_index()
                    case.bind_levels()
                    if declaration == "missing":
                        for paper in case.facts["papers"]:
                            paper.pop("analysis_level", None)
                        write_json(case.facts_path, case.facts)
                    proof, _run_dir, _companion = TestConsumptionBoundaries.ready_run(case)
                    frozen_facts = case.facts_path.read_bytes()
                    (case.prof_dir / "论文分析" / "_index.json").write_bytes(raw)
                    before = case.business_snapshot()
                    out = case.finalize_consumption(proof)
                    self.assertEqual(out["status"], "error", out)
                    self.assertEqual(out["reason_code"], "invalid_facts", out)
                    case.assert_business_unchanged(before)
                    self.assertEqual(case.facts_path.read_bytes(), frozen_facts)
                finally:
                    case.tearDown()
                    case.doCleanups()

    def test_prepare_rejects_drift_after_the_actual_source_read(self):
        proof = self.save_preflight()
        run_dir = self.root / "early-run"
        run_dir.mkdir()
        analysis = self.prof_dir / "论文分析" / "AAAA1111.md"
        original_read = Path.read_bytes
        state = {"read": False}

        def read_then_drift(path):
            raw = original_read(path)
            if path == analysis and not state["read"]:
                state["read"] = True
                path.write_bytes(raw + b"\n<!-- after actual read -->\n")
            return raw

        before = self.business_snapshot()
        with patch.object(Path, "read_bytes", read_then_drift):
            out = self.call_handler(
                "cmd_stage2_consumption_prepare", program_root=str(self.root),
                professor=PROFESSOR, target_file=str(self.target_file),
                preflight_file=str(proof), run_dir=str(run_dir))
        self.assertTrue(state["read"], "prepare did not read the analysis material")
        self.assertIn(out.get("reason_code"),
                      {"invalid_facts", "preflight_inputs_changed"}, out)
        self.assertIn(out["status"], {"error", "needs_refresh"}, out)
        self.assert_business_unchanged(before)

    def test_finalize_does_not_sample_sources_after_the_managed_write(self):
        analysis = self.prof_dir / "论文分析" / "AAAA1111.md"
        raw = analysis.read_bytes()
        stat = analysis.stat()
        frozen_guard = dict(path=str(analysis), size=stat.st_size,
                            mtime_ns=stat.st_mtime_ns, ctime_ns=stat.st_ctime_ns,
                            accepted_digest=sha256_bytes(raw))
        proof, _run_dir, _companion = self.ready_run()
        original_write = contact_state.managed_write
        state = {"written": False}

        def write_then_drift(*arguments, **keywords):
            result = original_write(*arguments, **keywords)
            if result.get("written") and not state["written"]:
                state["written"] = True
                analysis.write_bytes(raw + b"\n<!-- after managed write -->\n")
            return result

        out = self.finalize_in_process(
            proof, factory_overrides={"managed_write": write_then_drift})
        self.assertTrue(state["written"], out)
        if out["status"] == "ok":
            meta = self._read_meta()
            self.assertEqual(meta["resolution_evidence_guards"]["AAAA1111"]["analysis"],
                             frozen_guard)
            for record in meta["directions"].values():
                if "AAAA1111" in record["artifact_guards"]:
                    self.assertEqual(record["artifact_guards"]["AAAA1111"]["analysis"],
                                     frozen_guard)
            self.assertEqual(self.preflight()["action"], "process")
        else:
            self.assertIn(out["status"], {"error", "needs_refresh"}, out)
            self.assertFalse((self.prof_dir / "套磁候选输入.json").exists())

    def test_finalize_rejects_a_missing_companion(self):
        proof, run_dir, _companion = self.ready_run()
        (run_dir / "stage2-consumption.json").unlink()
        before = self.business_snapshot()
        out = self.finalize_consumption(proof)
        self.assertEqual((out["status"], out["reason_code"]),
                         ("error", "invalid_facts"), out)
        self.assert_business_unchanged(before)

    def test_finalize_rejects_a_missing_source_section(self):
        proof, run_dir, _companion = self.ready_run()
        companion = read_json(run_dir / "stage2-consumption.json")
        companion.pop("sources_projection")
        write_json(run_dir / "stage2-consumption.json", companion)
        before = self.business_snapshot()
        out = self.finalize_consumption(proof)
        self.assertEqual((out["status"], out["reason_code"]),
                         ("error", "invalid_facts"), out)
        self.assert_business_unchanged(before)

    def test_finalize_rejects_a_changed_sealed_job_input(self):
        proof, run_dir, _companion = self.ready_run()
        companion_path = run_dir / "stage2-consumption.json"
        companion = read_json(companion_path)
        companion["stage2_plan"]["jobs"][0]["model_input_sha256"] = "0" * 64
        write_json(companion_path, companion)
        before = self.business_snapshot()
        out = self.finalize_consumption(proof)
        self.assertEqual((out["status"], out.get("reason_code")),
                         ("error", "invalid_result_json"), out)
        self.assert_business_unchanged(before)

    def test_process_rejects_source_drift_after_render(self):
        proof, _run_dir, _companion = self.ready_run()
        before = self.business_snapshot()
        original = contact_state.render_analysis_document
        analysis = self.prof_dir / "论文分析" / "BBBB2222.md"
        state = {"rendered": False}

        def render_then_drift(*arguments, **keywords):
            result = original(*arguments, **keywords)
            state["rendered"] = True
            analysis.write_bytes(analysis.read_bytes() + b"\n<!-- after render -->\n")
            return result

        out = self.finalize_in_process(
            proof, factory_overrides={"render_analysis_document": render_then_drift})
        self.assertTrue(state["rendered"], out)
        self.assertEqual((out["status"], out["reason_code"]),
                         ("needs_refresh", "preflight_inputs_changed"), out)
        self.assert_business_unchanged(before)


class TestResolvedConsumptionBoundary(AnalysisLevelBase):
    def test_resolved_process_rejects_an_outer_candidate_drift(self):
        from test_stage2_resolved_direction import (
            ResolvedPipelineMixin, make_facts_sidecar, unchanged_resolved,
        )
        self.prepare_outer_candidate()
        self.professor = PROFESSOR
        index_path = self.prof_dir / "论文分析" / "_index.json"
        index = read_json(index_path)
        for paper in self.facts["papers"]:
            key = paper["item_key"]
            analysis = Path(paper["analysis_file"])
            sidecar = read_json(Path(paper["sidecar_file"]))
            quotes = [row["quote"] for row in sidecar["items"]]
            pdf = self.prof_dir / "论文分析" / f"{key}.pdf"
            if not pdf.exists():
                pdf.write_bytes(b"%PDF-1.4 synthetic resolved input\n")
            facts_file = make_facts_sidecar(analysis, pdf, quotes)
            paper.update(pdf_file=str(pdf), facts_file=str(facts_file), has_pdf=True)
            index["papers"][key]["facts_sidecar"] = str(facts_file)
        write_json(index_path, index)
        self.facts_path = ResolvedPipelineMixin.write_facts(
            self, self.facts["papers"], self.facts["directions"], gap_scope="relevant")
        self.facts = read_json(self.facts_path)
        proof, run_dir, _companion = self.prepare_consumption()
        proposals = {row["direction_id"]: unchanged_resolved(row)
                     for row in self.facts["directions"]}
        ResolvedPipelineMixin.run_resolve(self, self.facts_path, proposals)
        accepted = ResolvedPipelineMixin.accept_resolved(
            self, self.facts_path, ["DIR00001", "DIR00002"])
        self.assertEqual(accepted["status"], "ok", accepted)
        plan = self.plan_consumption(proof, run_dir)
        self.assertTrue(plan["write_needed"], plan)
        self.assertTrue(any(job["kind"] == "narrative" for job in plan["jobs"]))
        ctx = contact_state.Stage2Context(self.facts_path)
        self.assertIn("CCCC3333", contact_state.stage2_resolution_evidence_guards(ctx))
        for entry in ctx.direction_plans:
            self.assertNotIn("CCCC3333", contact_state.gap_scope_keys(ctx.facts, entry["direction"]))
            self.assertNotIn("CCCC3333", entry["direction"]["relevant_keys"])
            self.assertNotIn("CCCC3333", ctx.narrative_later_keys(entry))
            self.assertNotIn("CCCC3333", contact_state.stage2_direction_artifact_guards(
                ctx, entry["direction"]))
        for job in plan["jobs"]:
            if job["kind"] == "narrative":
                self.assertNotIn("CCCC3333", [row["item_key"]
                                             for row in job["model_input"]["later_papers"]])
        self.write_stage2_results()
        self.seal_consumption(run_dir)
        before = self.business_snapshot()
        source = self.prof_dir / "论文分析" / "CCCC3333.md"
        source.write_bytes(source.read_bytes() + b"\n<!-- resolved outer drift -->\n")
        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        out = self.finalize_consumption(proof, "--resolved-directions", sidecar_path)
        self.assertEqual((out["status"], out.get("reason_code")),
                         ("needs_refresh", "preflight_inputs_changed"), out)
        self.assert_business_unchanged(before)


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

    def _break_managed_render_sha(self):
        md = self.analysis_md()
        header, body = split_managed_bytes(md.read_bytes())
        broken = re.sub(rb"(?m)^render_sha256: .*$",
                        b"render_sha256: " + b"0" * 64, header) + body
        md.write_bytes(broken)
        return broken

    def test_refresh_rejects_an_invalid_old_header_render_binding(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        broken = self._break_managed_render_sha()
        pack_path = self.prof_dir / "套磁候选输入.json"
        before_pack = pack_path.read_bytes()
        plan = self.save_preflight("refresh-bad-header-render.json")
        payload = parse(self.refresh(plan))
        self.assertEqual(payload["status"], "error", payload)
        self.assertEqual(payload["reason_code"], "validation_render_stale", payload)
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(self.analysis_md().read_bytes(), broken)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

    def test_refresh_rejects_an_invalid_old_validator_lifecycle(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("refresh-invalid-lifecycle.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        base = self._read_pack()
        cases = [
            ("schema", 3),
            ("round", True),
            ("phase", "unknown"),
            ("pending", ["DIR00001"]),
            ("results", {"DIR00001": {"result": "bogus", "rounds": 1, "issues": []}}),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                pack = copy.deepcopy(base)
                pack["validator"][field] = value
                self._write_pack(pack)
                pack_path = self.prof_dir / "套磁候选输入.json"
                md_path = self.analysis_md()
                before_pack, before_md = pack_path.read_bytes(), md_path.read_bytes()
                payload = parse(self.refresh(plan))
                self.assertEqual(payload["status"], "error", payload)
                self.assertIn(payload.get("reason_code"),
                              {"validation_render_stale", "validation_evidence_not_recorded"},
                              payload)
                self.assertEqual(pack_path.read_bytes(), before_pack)
                self.assertEqual(md_path.read_bytes(), before_md)
                self.assertFalse(
                    (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

    def test_refresh_rejects_an_invalid_old_cache_render_binding(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["cache"]["render"][contact_state.ANALYSIS_MD]["sha256"] = "0" * 64
        pack["validator"]["pack_sha256"] = \
            contact_state.stage2_pack_content_fingerprint(pack)
        self._write_pack(pack)
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        before_pack, before_md = pack_path.read_bytes(), md_path.read_bytes()
        plan = self.save_preflight("refresh-bad-cache.json")
        payload = parse(self.refresh(plan))
        self.assertEqual(payload["status"], "error", payload)
        self.assertEqual(payload["reason_code"], "validation_render_stale", payload)
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(md_path.read_bytes(), before_md)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

    def test_refresh_rejects_an_invalid_old_validator_pack_binding(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["validator"]["pack_sha256"] = "0" * 64
        self._write_pack(pack)
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        before_pack, before_md = pack_path.read_bytes(), md_path.read_bytes()
        plan = self.save_preflight("refresh-bad-pack-binding.json")
        payload = parse(self.refresh(plan))
        self.assertEqual(payload["status"], "error", payload)
        self.assertEqual(payload["reason_code"], "validation_render_stale", payload)
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(md_path.read_bytes(), before_md)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

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

    def test_refresh_without_a_validator_stays_unvalidated(self):
        self.stage2_finalize()
        self.assertNotIn("validator", self._read_pack())
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("refresh-no-validator.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        out = parse(self.refresh(plan))
        self.assertEqual(out["status"], "ok", out)
        self.assertTrue(out["md_written"], out)
        pack = self._read_pack()
        self.assertNotIn("validator", pack)
        self.assertEqual(pack["papers"]["AAAA1111"]["analysis_level"], "abstract")
        _, body = split_managed_bytes(self.analysis_md().read_bytes())
        self.assertEqual(pack["cache"]["render"][contact_state.ANALYSIS_MD]["sha256"],
                         sha256_bytes(body))

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

    def _create_missing_facts_after_observation(self):
        facts_path = self.prof_dir / "论文分析" / "AAAA1111.md.facts.json"
        context_class = contact_state.Stage2PackRefineContext
        original_descriptor = context_class.__dict__["narrative_later_keys_for"]
        original = original_descriptor.__func__
        state = {"armed": False, "created": False, "bytes": None}

        def arm():
            state["armed"] = True

        def record_then_create(direction):
            result = original(direction)
            if state["armed"] and not state["created"]:
                from test_stage2_resolved_direction import make_facts_sidecar
                state["created"] = True
                make_facts_sidecar(
                    self.prof_dir / "论文分析" / "AAAA1111.md", self.pdf_path,
                    [self.gap_quotes["AAAA1111"]])
                state["bytes"] = facts_path.read_bytes()
            return result

        context_class.narrative_later_keys_for = staticmethod(record_then_create)
        self.addCleanup(setattr, context_class, "narrative_later_keys_for",
                        original_descriptor)
        return arm, state

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

    def _drift_freshness_after_lease(self):
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        original_init = contact_state.Stage2PackRefineContext.__init__
        gap_ids = {gap["gap_id"] for row in self._read_pack()["directions"]
                   for section in ("gap_shortlist", "gaps_excluded", "completed_gap_blacklist")
                   for gap in row.get(section, [])}
        cache = read_json(cache_path)
        gap_id = next(key for key in cache["entries"] if key in gap_ids)
        state = {"mutated": False, "bytes": None}

        def init_then_drift(instance, *arguments, **keywords):
            original_init(instance, *arguments, **keywords)
            if not state["mutated"]:
                state["mutated"] = True
                data = read_json(cache_path)
                entry = data["entries"][gap_id]
                self.assertEqual(entry["status"], "open")
                entry["status"] = "unknown"
                write_json(cache_path, data)
                state["bytes"] = cache_path.read_bytes()

        contact_state.Stage2PackRefineContext.__init__ = init_then_drift
        self.addCleanup(setattr, contact_state.Stage2PackRefineContext,
                        "__init__", original_init)
        return state

    def test_refresh_rechecks_freshness_after_lease(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("refresh-freshness.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        report_path = self.root / "validation.json"
        before_pack, before_md, before_report = (
            pack_path.read_bytes(), md_path.read_bytes(), report_path.read_bytes())
        state = self._drift_freshness_after_lease()
        payload = self._refresh_in_process(plan)
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertEqual(payload["reason_code"], "preflight_inputs_changed", payload)
        self.assertTrue(state["mutated"], payload)
        self.assertEqual(cache_path.read_bytes(), state["bytes"])
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(md_path.read_bytes(), before_md)
        self.assertEqual(report_path.read_bytes(), before_report)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())
        next_payload = self.preflight()
        self.assertEqual(next_payload["action"], "process", next_payload)
        self.assertIn("freshness_cache_changed",
                      self.direction(next_payload, "DIR00001")["reason_codes"],
                      next_payload)

    def test_refresh_rechecks_missing_facts_before_write(self):
        self.build_accepted_state()
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        plan = self.save_preflight("refresh-missing-facts.json")
        self.assertEqual(read_json(plan)["action"], "refresh_level")
        pack_path = self.prof_dir / "套磁候选输入.json"
        md_path = self.analysis_md()
        report_path = self.root / "validation.json"
        before_pack, before_md, before_report = (
            pack_path.read_bytes(), md_path.read_bytes(), report_path.read_bytes())
        arm, state = self._create_missing_facts_after_observation()
        arm()
        payload = self._refresh_in_process(plan)
        self.assertEqual(payload["status"], "needs_refresh", payload)
        self.assertEqual(
            (self.prof_dir / "论文分析" / "AAAA1111.md.facts.json").read_bytes(),
            state["bytes"])
        self.assertEqual(pack_path.read_bytes(), before_pack)
        self.assertEqual(md_path.read_bytes(), before_md)
        self.assertEqual(report_path.read_bytes(), before_report)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

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
        recorded = copy.deepcopy(pack["cache"]["preflight"])
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
        refreshed = copy.deepcopy(updated["cache"]["preflight"])
        # Only these approved display fields may move. Comparing the rest of
        # the whole block also retains E/D guards, freshness, and resolved
        # group identities instead of sampling a few convenient source fields.
        for metadata in (recorded, refreshed):
            metadata.pop("statistics_version", None)
            for record in metadata["directions"].values():
                record.pop("level_projection", None)
        self.assertEqual(refreshed, recorded)

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


class TestRefreshRemainingBoundaries(AnalysisLevelBase):
    _refresh_in_process = TestRefreshProtection._refresh_in_process

    def refresh_plan(self):
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        proof = self.save_preflight()
        self.assertEqual(read_json(proof)["action"], "refresh_level")
        return proof

    def assert_refresh_rejected(self, proof, before):
        out = self._refresh_in_process(proof)
        self.assertEqual(out["status"], "needs_refresh", out)
        self.assertIn(out["reason_code"],
                      {"preflight_inputs_changed", "refresh_requires_process"}, out)
        self.assert_business_unchanged(before)
        self.assertFalse(
            (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())

    def test_refresh_rechecks_an_outer_candidate_after_lease(self):
        self.prepare_outer_candidate()
        self.stage2_finalize()
        self.record_validation()
        self.assert_outer_candidate()
        proof = self.refresh_plan()
        before = self.business_snapshot()
        original = contact_state.Stage2PackRefineContext.__init__
        source = self.prof_dir / "论文分析" / "CCCC3333.md"
        state = {"mutated": False}

        def init_then_drift(instance, *arguments, **keywords):
            original(instance, *arguments, **keywords)
            if not state["mutated"]:
                state["mutated"] = True
                source.write_bytes(source.read_bytes() + b"\n<!-- outer drift -->\n")

        with patch.object(contact_state.Stage2PackRefineContext, "__init__", init_then_drift):
            self.assert_refresh_rejected(proof, before)
        self.assertTrue(state["mutated"])
        next_plan = self.preflight(gap_scope="relevant")
        self.assertEqual(next_plan["action"], "process", next_plan)
        self.assertIn("artifact_changed", self.direction(next_plan, "DIR00001")["reason_codes"])

    def test_refresh_rechecks_freshness_before_the_first_write(self):
        self.build_accepted_state()
        proof = self.refresh_plan()
        before = self.business_snapshot()
        cache_path = self.prof_dir / "论文分析" / "_freshness_cache.json"
        old_cache = read_json(cache_path)
        gap_ids = {gap["gap_id"] for row in self._read_pack()["directions"]
                   for section in ("gap_shortlist", "gaps_excluded", "completed_gap_blacklist")
                   for gap in row.get(section, [])}
        gap_id = next(key for key in old_cache["entries"] if key in gap_ids)
        original = contact_state.Stage2PackRefineContext.narrative_later_keys_for
        state = {"mutated": False}

        def observe_then_drift(direction):
            result = original(direction)
            if not state["mutated"]:
                state["mutated"] = True
                changed = copy.deepcopy(old_cache)
                self.assertEqual(changed["entries"][gap_id]["status"], "open")
                changed["entries"][gap_id]["status"] = "unknown"
                write_json(cache_path, changed)
                before[cache_path] = cache_path.read_bytes()
            return result

        with patch.object(contact_state.Stage2PackRefineContext, "narrative_later_keys_for",
                          staticmethod(observe_then_drift)):
            self.assert_refresh_rejected(proof, before)
        self.assertTrue(state["mutated"])
        next_plan = self.preflight()
        self.assertEqual(next_plan["action"], "process", next_plan)
        self.assertIn("freshness_cache_changed",
                      self.direction(next_plan, "DIR00001")["reason_codes"])

    def test_refresh_rejects_the_remaining_illegal_lifecycle_states(self):
        self.build_accepted_state()
        proof = self.refresh_plan()
        base = self._read_pack()
        cases = {
            "round2_needs_correction": dict(round=2, phase="needs_correction"),
            "needs_correction_without_pending": dict(phase="needs_correction", pending={}),
            "unknown_pending_direction": dict(pending={"DIR99999": [{}]}),
            "unknown_result_direction": dict(results={
                **base["validator"]["results"],
                "DIR99999": dict(result="pass", rounds=1, issues=[])}),
        }
        for name, changes in cases.items():
            with self.subTest(name=name):
                pack = copy.deepcopy(base)
                pack["validator"].update(changes)
                self._write_pack(pack)
                before = self.business_snapshot()
                out = parse(self.refresh(proof))
                self.assertEqual(out["status"], "error", out)
                self.assertIn(out["reason_code"],
                              {"validation_render_stale", "validation_evidence_not_recorded"}, out)
                self.assert_business_unchanged(before)
                self.assertFalse(
                    (self.prof_dir / "论文分析" / ".stage2-local-writer.json").exists())


class TestOrdinaryOldStateBoundaries(AnalysisLevelBase):
    _break_managed_render_sha = TestLevelRefresh._break_managed_render_sha

    def test_ordinary_equivalent_finalize_rejects_header_render_damage(self):
        self.build_accepted_state()
        self._break_managed_render_sha()
        proof, run_dir, _companion = self.prepare_consumption()
        plan = self.plan_consumption(proof, run_dir)
        self.assertEqual(plan["jobs"], [], plan)
        self.seal_consumption(run_dir)
        before = self.business_snapshot()
        out = self.finalize_consumption(proof)
        self.assertEqual((out["status"], out["reason_code"]),
                         ("error", "validation_render_stale"), out)
        self.assert_business_unchanged(before)

    def test_ordinary_equivalent_finalize_rejects_validator_pack_damage(self):
        self.build_accepted_state()
        pack = self._read_pack()
        pack["validator"]["pack_sha256"] = "0" * 64
        self._write_pack(pack)
        proof, run_dir, _companion = self.prepare_consumption()
        plan = self.plan_consumption(proof, run_dir)
        self.assertEqual(plan["jobs"], [], plan)
        self.seal_consumption(run_dir)
        before = self.business_snapshot()
        out = self.finalize_consumption(proof)
        self.assertEqual((out["status"], out["reason_code"]),
                         ("error", "validation_render_stale"), out)
        self.assert_business_unchanged(before)

    def test_new_business_needs_explicit_overwrite_and_loses_old_validation(self):
        self.build_accepted_state()
        self._break_managed_render_sha()
        report = (self.root / "validation.json").read_bytes()
        decision = self.root / "overwrite.json"
        write_json(decision, {"decision": "overwrite"})
        self.levels = {"AAAA1111": "abstract", "BBBB2222": "abstract"}
        self.write_index()
        refresh_proof = self.save_preflight("damaged-refresh.json")
        before = self.business_snapshot()
        refused = parse(self.refresh(refresh_proof, "--decision-file", decision))
        self.assertEqual((refused["status"], refused.get("reason_code")),
                         ("error", "validation_render_stale"), refused)
        self.assert_business_unchanged(before)
        self.bind_levels()
        self.facts["directions"][0]["user_note"] = "比较新的合成输入。"
        self.target["directions"][0]["user_note"] = "比较新的合成输入。"
        self._write_target()
        write_json(self.facts_path, self.facts)
        proof, run_dir, _companion = self.prepare_consumption()
        plan = self.plan_consumption(proof, run_dir)
        self.assertTrue(plan["jobs"], plan)
        self.assertTrue(plan["write_needed"], plan)
        self.write_stage2_results()
        self.seal_consumption(run_dir)
        before = self.business_snapshot()
        refused = self.finalize_consumption(proof)
        self.assertEqual((refused["status"], refused["reason_code"]),
                         ("needs_decision", "manual_markdown_changed"), refused)
        self.assert_business_unchanged(before)
        out = self.finalize_consumption(proof, "--decision-file", decision)
        self.assertEqual(out["status"], "ok", out)
        self.assertNotIn("validator", self._read_pack())
        self.assertEqual((self.root / "validation.json").read_bytes(), report)


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
