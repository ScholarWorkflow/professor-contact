"""Downstream invalidation regressions for authoritative Stage 2 resolutions."""
import json
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import (
    ResolvedPipelineMixin,
    finalize_resolve,
    new_resolve_results_dir,
    parse,
    plan_resolve,
    run_cli,
    write_json,
    write_resolve_results,
)
from stage2_test_support import run_bound_stage2_plan
from stage2_upstream_fixture import run_bound_stage2_finalize


class ResolvedDirectionDownstreamRegressionTests(ResolvedPipelineMixin, unittest.TestCase):
    ANALYSIS_MD = "套磁候选分析.md"
    INPUT_PACK = "套磁候选输入.json"
    RESOLVED_SIDECAR = "_resolved_directions.json"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    # ------------------------------------------------------------------
    # Fixture helpers shared by the regression cases below.
    # ------------------------------------------------------------------

    def _new_program_case(self, name):
        """One isolated program root + professor dir for one synthetic state.

        Every fixture in this file writes outside the repository (under
        `self.temp`) and never touches a real Zotero library, professor dir or
        user cache. Independent program roots keep several Stage-2 states (and
        several synthetic professors with the same display name) apart.
        """
        case_root = Path(self.temp.name) / name
        prof_dir = case_root / "教授研究" / "X分野" / self.professor
        (prof_dir / "论文分析").mkdir(parents=True)
        self.root = case_root
        self.prof_dir = prof_dir
        return prof_dir

    @staticmethod
    def _pack_directions(pack):
        return {direction["direction_id"]: direction for direction in pack["directions"]}

    @staticmethod
    def _pack_gap_index(direction):
        """gap_id -> item_key over the direction's shortlist and excluded rows."""
        gaps = list(direction.get("gap_shortlist") or []) + list(direction.get("gaps_excluded") or [])
        return {gap["gap_id"]: gap["item_key"] for gap in gaps}

    @staticmethod
    def _material_titles(job):
        """The P-reference scope (item_key -> trusted title) offered to a rewrite job."""
        return {entry["item_key"]: entry.get("title")
                for entry in job["model_input"]["allowed_material"]["papers"]}

    @staticmethod
    def _material_gaps(job):
        return {entry["gap_id"]: entry.get("item_key")
                for entry in job["model_input"]["allowed_material"]["gaps"]}

    def _run_stage2_finalize_with_narratives(self, facts_path, narratives, *,
                                             gap_note_items=None):
        """Formal `stage2-plan` → results → `stage2-finalize` with test narratives.

        Same pipeline as `ResolvedPipelineMixin.run_stage2_finalize`, except the
        test controls the narrative text of named directions so a direction can
        carry a real `{{P:item_key}}` reference (or a marker a style-validator
        report can quote verbatim). Unnamed directions get a plain block.
        `gap_note_items` maps a direction id to one of its OWN member item keys;
        that member's real gap of this round (`model_input.gaps` of the same
        narrative job: gap_id, quote and its translation) becomes the direction's
        original research-gap note, so a later refinement has an unchanged note
        to copy. The member must keep its gap in the materialised direction.
        """
        plan_payload = parse(run_bound_stage2_plan(run_cli, facts_path))
        self.assertEqual(plan_payload["status"], "ok",
                         msg=json.dumps(plan_payload, ensure_ascii=False))
        results_dir = self.root / "stage2_results"
        results_dir.mkdir(exist_ok=True)
        for job in plan_payload["jobs"]:
            if job["kind"] != "freshness":
                continue
            did = job["direction_id"]
            write_json(results_dir / f"freshness-{did}.json", {
                "schema": 1, "kind": "freshness", "direction_id": did,
                "results": [{"gap_id": gap["gap_id"], "status": "open",
                             "candidate_paper_ids": [],
                             "evidence": "No later papers found", "confidence": "high"}
                            for gap in job["model_input"]["gaps"]]})
        directions = []
        for job in plan_payload["jobs"]:
            if job["kind"] != "narrative":
                continue
            did = job["direction_id"]
            block = narratives.get(did) or {
                "kind": "para", "text": f"Positioning for {did}", "refs": [],
                "concrete_object": "合成方向对象", "input_example": "输入一组合成样本",
                "output_example": "得到一组合成结果"}
            notes = []
            noted_item = (gap_note_items or {}).get(did)
            if noted_item is not None:
                member_gaps = [gap for gap in job["model_input"]["gaps"]
                               if gap.get("item_key") == noted_item]
                self.assertTrue(member_gaps,
                                msg=f"{did}: no real gap of {noted_item} in this round")
                notes.append({"gap_id": member_gaps[0]["gap_id"],
                              "summary": member_gaps[0]["quote"],
                              "explanation": member_gaps[0]["translation_zh"]})
            directions.append({"direction_id": did, "positioning": [block],
                               "gap_notes": notes})
        write_json(results_dir / "narrative.json",
                   {"schema": 1, "kind": "narrative", "directions": directions})
        sidecar_path = self.prof_dir / "论文分析" / self.RESOLVED_SIDECAR
        payload = parse(run_bound_stage2_finalize(
            run_cli, str(facts_path), "--results", str(results_dir),
            "--resolved-directions", str(sidecar_path)))
        self.assertEqual(payload["status"], "ok", msg=json.dumps(payload, ensure_ascii=False))
        return payload

    def _marker_hits(self, marker):
        """(physical line number, line) of every rendered line carrying `marker`."""
        lines = (self.prof_dir / self.ANALYSIS_MD).read_text(encoding="utf-8").splitlines()
        return [(index + 1, line) for index, line in enumerate(lines) if marker in line]

    def _write_blocking_report(self, name, markers):
        """A raw style-validator report whose blocking quotes are `markers`."""
        if isinstance(markers, str):
            markers = [markers]
        issues = []
        for marker in markers:
            self.assertLessEqual(len(marker), 40, msg=marker)
            hits = self._marker_hits(marker)
            self.assertEqual(len(hits), 1,
                             msg=f"marker {marker!r} must own exactly one rendered line: {hits}")
            line_number, line = hits[0]
            self.assertEqual(line.count(marker), 1, msg=line)
            issues.append({"rule": "A1", "severity": "blocking",
                           "location": str(line_number), "quote": marker,
                           "suggestion": "改成更日常的说法。"})
        report = {
            "result": "ok",
            "files": [{
                "file": str(self.prof_dir / self.ANALYSIS_MD),
                "artifact": "analysis",
                "verdict": "fail",
                "blocking": len(issues),
                "minor": 0,
                "issues": issues,
            }],
            "notes": "",
        }
        path = self.root / name
        write_json(path, report)
        return path

    def _record_validation(self, report_path):
        payload = parse(run_cli("stage2-record-validation", "--professor-dir", str(self.prof_dir),
                                "--validation-file", str(report_path)))
        self.assertEqual(payload["status"], "needs_correction",
                         msg=json.dumps(payload, ensure_ascii=False))
        return payload

    def _refine_plan(self, report_path, *, facts_path=None, direction_id=None):
        arguments = ["stage2-refine-plan"]
        if facts_path is not None:
            arguments += ["--facts", str(facts_path)]
        else:
            arguments += ["--professor-dir", str(self.prof_dir)]
        arguments += ["--validation-file", str(report_path)]
        if direction_id is not None:
            arguments += ["--direction-id", direction_id]
        return parse(run_cli(*arguments))

    def _refine_finalize(self, report_path, jobs, blocks, *, facts_path=None, gap_notes=None):
        """Write one complete rewrite per open job and run the formal finalizer.

        A narrative-rewrite result carries the WHOLE narrative (plan 5.1: keep
        the unchanged facts, gaps, freshness and user notes), so a direction the
        caller does not name in `gap_notes` copies every research-gap note of its
        own original narrative: the formal refine plan hands this round that
        narrative in `model_input.current_narrative.gap_notes` (gap_id ->
        summary/explanation) as read from the current input pack. Only the
        positioning text named by the report is rewritten; no note is invented
        and no other direction's notes are mixed in. An explicit
        `gap_notes[direction_id]` still overrides that direction.
        """
        def original_gap_notes(job):
            """This round's own gap notes for one job, as the rewrite payload list."""
            narrative = (job.get("model_input") or {}).get("current_narrative") or {}
            notes = narrative.get("gap_notes")
            if not isinstance(notes, dict):
                return []
            return [{"gap_id": gap_id, "summary": note["summary"],
                     "explanation": note["explanation"]}
                    for gap_id, note in notes.items()]

        results_dir = self.root / "refine-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        for job in jobs:
            did = job["direction_id"]
            write_json(results_dir / job["result_file"], {
                "schema": 1,
                "kind": "narrative-rewrite",
                "direction_id": did,
                "collection_key": did,
                "positioning": [blocks[did]],
                "gap_notes": (gap_notes or {}).get(did, original_gap_notes(job)),
            })
        arguments = ["stage2-refine-finalize"]
        if facts_path is not None:
            arguments += ["--facts", str(facts_path)]
        else:
            arguments += ["--professor-dir", str(self.prof_dir)]
        arguments += ["--results", str(results_dir), "--validation-file", str(report_path)]
        return parse(run_cli(*arguments))

    def _stage3_jobs(self):
        payload = parse(run_cli("stage3-plan", "--professor-dir", str(self.prof_dir),
                                "--program-root", str(self.root)))
        self.assertEqual(payload["status"], "ok", msg=json.dumps(payload, ensure_ascii=False))
        return {job["direction_id"]: job for job in payload["jobs"]}

    # ------------------------------------------------------------------
    # Migrated regressions (originally written against the fixed result dir).
    # ------------------------------------------------------------------

    def test_refined_membership_changes_stage3_input_fingerprint(self):
        """Stage 3 must not reuse candidates after Stage 2 changes authoritative membership."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work A."]),
            self.make_paper("P2", "Kitchen Chemistry", ["chemistry", "kitchen"],
                            ["Future work B."]),
        ]
        facts_path = self.write_facts(
            papers, [self.make_direction("dir_A", ["P1", "P2"],
                                         name_ja="信号処理", name_zh="信号处理",
                                         summary="自适应信号处理")])

        self.run_resolve(facts_path, {})
        first_finalize = self.run_stage2_finalize(facts_path)
        self.assertEqual(first_finalize["status"], "ok")
        before = self.load_pack()["directions"][0]["input_fingerprint"]

        (self.prof_dir / "论文分析" / self.RESOLVED_SIDECAR).unlink()
        self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "refined",
                "papers_to_add": [],
                "papers_to_remove": ["P2"],
                "paper_justifications": {"P2": "full-text topic mismatch"},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        })
        accepted = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))
        second_finalize = self.run_stage2_finalize(facts_path)
        self.assertEqual(second_finalize["status"], "ok")
        direction = self.load_pack()["directions"][0]
        after = direction["input_fingerprint"]
        supporting = set(direction["supporting_item_keys"])

        self.assertEqual(supporting, {"P1"})
        self.assertNotEqual(
            before, after,
            "authoritative membership changed but Stage-3 reuse fingerprint stayed identical",
        )

    def test_split_materializes_candidate_outside_relevant_set(self):
        """A full-text candidate rescued after the abstract gate must survive a split."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work A."]),
            self.make_paper("P2", "Robust Control from Full Text", ["制御", "ロバスト"],
                            ["Future work B."]),
        ]
        direction = self.make_direction(
            "dir_A", ["P1", "P2"], name_ja="信号処理", name_zh="信号处理",
            summary="信号处理与控制", provisional_keys=["P1"])
        direction["relevant_keys"] = ["P1"]
        facts_path = self.write_facts(papers, [direction])

        self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "split_from",
                "papers_to_add": ["P2"],
                "papers_to_remove": [],
                "paper_justifications": {"P2": "full text shows a distinct robust-control line"},
                "split_target": "dir_A__control",
                "merge_target": None,
                "user_note": "",
            },
        })
        accepted = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))
        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok")

        by_key = {d["direction_id"]: d for d in self.load_pack()["directions"]}
        self.assertEqual(set(by_key), {"dir_A", "dir_A__control"})
        self.assertEqual(
            set(by_key["dir_A__control"]["supporting_item_keys"]),
            {"P2"},
            "split target lost the candidate that full-text resolution rescued outside relevant_keys",
        )

    def test_reused_split_preserves_materialized_child_membership(self):
        """An unchanged rerun must not rebuild an accepted split child from an already-pruned source."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work A."]),
            self.make_paper("P2", "Robust Control", ["制御", "ロバスト"],
                            ["Future work B."]),
        ]
        facts_path = self.write_facts(
            papers, [self.make_direction("dir_A", ["P1", "P2"],
                                         name_ja="信号処理", name_zh="信号处理",
                                         summary="信号处理与控制")])
        split = {
            "resolved_direction_id": "dir_A",
            "provisional_direction_id": "dir_A",
            "name_ja": "信号処理",
            "name_zh": "信号处理",
            "resolution_type": "split_from",
            "papers_to_add": ["P2"],
            "papers_to_remove": [],
            "paper_justifications": {"P2": "distinct robust-control cluster"},
            "split_target": "dir_A__control",
            "merge_target": None,
            "user_note": "",
        }

        self.run_resolve(facts_path, {"dir_A": split})
        accepted = self.accept_resolved(facts_path, ["dir_A"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))
        first = self.run_stage2_finalize(facts_path)
        self.assertEqual(first["status"], "ok")
        first_by_key = {d["direction_id"]: d for d in self.load_pack()["directions"]}
        self.assertEqual(
            set(first_by_key["dir_A__control"]["supporting_item_keys"]), {"P2"})

        reuse_plan, reuse_finalize = self.run_resolve(facts_path, {})
        self.assertEqual(reuse_plan["jobs"], [])
        self.assertFalse(reuse_finalize["needs_user_choice"])
        second = self.run_stage2_finalize(facts_path)
        self.assertEqual(second["status"], "ok")
        second_by_key = {d["direction_id"]: d for d in self.load_pack()["directions"]}
        self.assertEqual(
            set(second_by_key["dir_A__control"]["supporting_item_keys"]),
            {"P2"},
            "reused split child was rebuilt from the pruned source and lost its papers",
        )

    def test_stage2_reuse_keeps_provisional_fingerprint_across_repeated_finalize(self):
        """A reuse finalize must not overwrite the Stage-2 provisional fingerprint with the downstream one."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["信号", "処理"],
                            ["Future work A."]),
        ]
        facts_path = self.write_facts(
            papers, [self.make_direction("dir_A", ["P1"],
                                         name_ja="信号処理", name_zh="信号处理",
                                         summary="信号处理")])
        self.run_resolve(facts_path, {})
        first = self.run_stage2_finalize(facts_path)
        self.assertEqual(first["status"], "ok")
        first_direction = self.load_pack()["directions"][0]
        provisional = first_direction["provisional_input_fingerprint"]
        downstream = first_direction["input_fingerprint"]
        self.assertNotEqual(provisional, downstream)

        second_plan = parse(run_bound_stage2_plan(run_cli, facts_path))
        self.assertEqual(second_plan["directions"][0]["action"], "reuse")
        second = self.run_stage2_finalize(facts_path)
        self.assertEqual(second["status"], "ok")
        second_direction = self.load_pack()["directions"][0]
        self.assertEqual(second_direction["provisional_input_fingerprint"], provisional)

        third_plan = parse(run_bound_stage2_plan(run_cli, facts_path))
        self.assertEqual(
            third_plan["directions"][0]["action"], "reuse",
            "second finalize corrupted provisional_input_fingerprint and broke Stage-2 reuse",
        )

    def test_membership_resolution_requires_valid_fulltext_facts(self):
        """The deterministic finalizer must reject add/remove membership changes without full-text facts."""
        p1 = self.make_paper("P1", "Provisional Paper", ["信号"], ["Future work A."])
        p2 = self.make_paper("P2", "Expanded Candidate", ["制御"], ["Future work B."])
        for paper in (p1, p2):
            Path(paper["facts_file"]).unlink()
            paper["facts_file"] = None
        direction = self.make_direction(
            "dir_A", ["P1", "P2"], name_ja="信号処理", name_zh="信号处理",
            summary="信号处理", provisional_keys=["P1"])
        facts_path = self.write_facts([p1, p2], [direction])

        # One exclusive results directory for this round: the plan stamps the
        # round identity into every job and finalize only reads that directory.
        results_dir = new_resolve_results_dir(self.root)
        plan_payload = plan_resolve(facts_path, results_dir)
        self.assertEqual(plan_payload["status"], "ok",
                         msg=json.dumps(plan_payload, ensure_ascii=False))
        write_resolve_results(results_dir, plan_payload, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "refined",
                "papers_to_add": ["P2"],
                "papers_to_remove": ["P1"],
                "paper_justifications": {
                    "P1": "model claimed mismatch without full-text facts",
                    "P2": "model claimed support without full-text facts",
                },
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        }, facts_path)

        payload = finalize_resolve(facts_path, results_dir)
        self.assertEqual(payload["status"], "error", msg=json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["reason_code"], "invalid_result_json")

    # ------------------------------------------------------------------
    # T1: formal membership vs. analysis reference scope, and both refine
    # entry points (plan 5.1 T1 recipe; plan 3.1 and 3.4.2).
    # ------------------------------------------------------------------

    def test_member_reference_persistence_and_refine_sources(self):
        self._new_program_case("t1-main")
        member_keys = [f"MEMBER0{index}" for index in range(1, 7)]
        reference_key = "GTQBNPED"
        accepted_key = "D6XQCHTP"
        other_key = "OTHER0001"
        reference_title = "Trusted Reference Review"
        other_title = "Other Direction Study"

        papers = [self.make_paper(key, f"Synthetic member study {index}", ["信号", "処理"],
                                  [f"Synthetic member future work {index}."])
                  for index, key in enumerate(member_keys, start=1)]
        papers.append(self.make_paper(reference_key, reference_title, ["参考", "レビュー"], []))
        papers.append(self.make_paper(accepted_key, "Rescued Full Text Study", ["信号"],
                                      ["Rescued future work."]))
        papers.append(self.make_paper(other_key, other_title, ["制御"],
                                      ["Other direction future work."]))

        front = self.make_direction("dir_A", member_keys, name_ja="信号処理", name_zh="信号处理",
                                    summary="合成前方向")
        front["relevant_keys"] = member_keys + [reference_key]
        other = self.make_direction("dir_B", [other_key, reference_key, accepted_key],
                                    name_ja="制御系統", name_zh="控制系统",
                                    summary="合成另一方向", provisional_keys=[other_key])
        other["relevant_keys"] = [other_key, reference_key]
        facts_path = self.write_facts(papers, [front, other], name="t1-facts.json")

        _, finalize_payload = self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理", "name_zh": "信号处理",
                "resolution_type": "refined",
                "papers_to_add": [accepted_key],
                "papers_to_remove": [],
                "paper_justifications": {accepted_key: "full text supports the front direction"},
                "split_target": None, "merge_target": None, "user_note": "",
            },
            "dir_B": {
                "resolved_direction_id": "dir_B",
                "provisional_direction_id": "dir_B",
                "name_ja": "制御系統", "name_zh": "控制系统",
                "resolution_type": "refined",
                "papers_to_add": [reference_key],
                "papers_to_remove": [],
                "paper_justifications": {reference_key: "full text supports the other direction"},
                "split_target": None, "merge_target": None, "user_note": "",
            },
        })
        self.assertTrue(finalize_payload["needs_user_choice"])
        accepted = self.accept_resolved(facts_path, ["dir_A", "dir_B"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))

        marker = "T1参考范围标记"
        front_block = {
            "kind": "para",
            "text": marker + "：{{P:" + reference_key + "}} 只作参考引用。",
            "refs": [f"paper:{reference_key}"],
            "concrete_object": "一组合成参考论文",
            "input_example": "输入一份合成论文参考范围",
            "output_example": "得到一份保留参考范围的修订稿",
        }
        self._run_stage2_finalize_with_narratives(facts_path, {"dir_A": front_block},
                                                  gap_note_items={"dir_A": member_keys[0]})

        pack = self.load_pack()
        by_id = self._pack_directions(pack)
        front_pack = by_id["dir_A"]
        other_pack = by_id["dir_B"]
        expected_members = set(member_keys) | {accepted_key}
        expected_references = set(member_keys) | {reference_key}

        # 1) The front direction has exactly the seven accepted formal members;
        #    the analysis reference paper never becomes one of them.
        self.assertEqual(set(front_pack["supporting_item_keys"]), expected_members)
        self.assertNotIn(reference_key, front_pack["supporting_item_keys"])
        self.assertIn(reference_key, front_pack["relevant_keys"])
        self.assertEqual(set(front_pack["relevant_keys"]), expected_references)
        # An accepted member change never widens the P-reference licence, and a
        # reference-only paper is never promoted to a member.
        self.assertNotIn(accepted_key, front_pack["relevant_keys"])
        self.assertEqual(set(other_pack["supporting_item_keys"]), {other_key, reference_key})

        # 2) The professor-level papers map keeps ONE trusted canonical record
        #    for the reference paper (title/year/authorship/analysis path).
        papers_map = pack["papers"]
        reference_record = papers_map[reference_key]
        self.assertEqual(reference_record["item_key"], reference_key)
        self.assertEqual(reference_record["title"], reference_title)
        self.assertEqual(reference_record["year"], 2024)
        self.assertEqual(reference_record["authorship"], "corresponding")
        self.assertTrue(reference_record.get("analysis_file"))
        self.assertEqual([key for key, record in papers_map.items()
                          if isinstance(record, dict) and record.get("title") == reference_title],
                         [reference_key])

        # 3) The downstream identity is the seven-member state, and the
        #    reference-only paper must not widen what Stage 3 consumes.
        fingerprint = front_pack["input_fingerprint"]
        if isinstance(fingerprint, dict):
            # Optional structured view: assert the hashed member list when the
            # implementation exposes it, otherwise rely on the Stage-3 scope.
            self.assertEqual(set(fingerprint.get("final_supporting_keys") or []),
                             expected_members)
        else:
            self.assertIsInstance(fingerprint, str)
        self.assertNotEqual(front_pack.get("provisional_input_fingerprint"), fingerprint)

        stage3 = self._stage3_jobs()
        front_job = stage3["dir_A"]
        self.assertEqual({paper["item_key"] for paper in front_job["model_input"]["supporting_papers"]},
                         expected_members)
        self.assertEqual({gap["item_key"] for gap in front_job["model_input"]["gaps"]},
                         set(member_keys))
        self.assertNotIn(reference_key,
                         {gap["item_key"] for gap in front_job["model_input"]["gaps"]})

        # 4) The rendered P reference is the trusted title, never the item key.
        analysis = (self.prof_dir / self.ANALYSIS_MD).read_text(encoding="utf-8")
        self.assertIn(f"[{reference_title}](zotero://select/library/items/{reference_key})", analysis)
        self.assertNotIn(f"[{reference_key}](zotero://select/library/items/{reference_key})", analysis)

        # 5) Both refine entry points read the same materialised pack: identical
        #    final direction set, identical P scope with trusted titles, and the
        #    same final gaps (the receipts need not be byte-identical).
        report = self._write_blocking_report("t1-first-round.json", marker)
        self._record_validation(report)
        facts_entry = self._refine_plan(report, facts_path=facts_path)
        pack_entry = self._refine_plan(report)
        for label, entry in (("facts", facts_entry), ("professor-dir", pack_entry)):
            self.assertEqual(entry["status"], "ok",
                             msg=f"{label}: {json.dumps(entry, ensure_ascii=False)}")
            self.assertEqual(set(entry["directions"]), {"dir_A"}, msg=label)
            self.assertEqual([job["direction_id"] for job in entry["jobs"]], ["dir_A"], msg=label)
        facts_job = facts_entry["jobs"][0]
        pack_job = pack_entry["jobs"][0]
        expected_gaps = self._pack_gap_index(front_pack)
        for label, job in (("facts", facts_job), ("professor-dir", pack_job)):
            self.assertEqual(set(self._material_titles(job)), expected_references, msg=label)
            self.assertEqual(self._material_gaps(job), expected_gaps, msg=label)
        self.assertEqual(self._material_titles(facts_job), self._material_titles(pack_job))
        self.assertEqual(self._material_titles(pack_job)[reference_key], reference_title)
        self.assertNotIn(other_key, self._material_titles(pack_job))

        # 6) A normal refinement through the facts entry renders the P
        #    reference as the real title and leaves membership, gaps and L
        #    permission untouched. The rewrite replaces the WHOLE narrative, so
        #    dir_A's original research-gap note must come through unchanged.
        original_gap_notes = front_pack["narrative"]["gap_notes"]
        self.assertTrue(original_gap_notes,
                        "the fixture must give dir_A an original research-gap note")
        self.assertTrue(
            set(original_gap_notes) <= {gap["gap_id"] for gap in front_pack["gap_shortlist"]},
            "the original gap note must stay in dir_A's own rendered shortlist")
        rewritten_block = {
            "kind": "para",
            "text": "T1修订稿：{{P:" + reference_key + "}} 仍作参考引用。",
            "refs": [f"paper:{reference_key}"],
            "concrete_object": "一组合成参考论文",
            "input_example": "输入一份合成论文参考范围",
            "output_example": "得到一份保留参考范围的修订稿",
        }
        finalized = self._refine_finalize(report, [facts_job], {"dir_A": rewritten_block},
                                          facts_path=facts_path)
        self.assertEqual(finalized["status"], "ok",
                         msg=json.dumps(finalized, ensure_ascii=False))
        self.assertEqual(finalized["rewritten"], ["dir_A"])

        after = self._pack_directions(self.load_pack())["dir_A"]
        self.assertEqual(set(after["supporting_item_keys"]), expected_members)
        self.assertEqual(set(after["relevant_keys"]), expected_references)
        self.assertEqual([gap["gap_id"] for gap in after["gap_shortlist"]],
                         [gap["gap_id"] for gap in front_pack["gap_shortlist"]])
        self.assertEqual(after.get("narrative_later_papers"),
                         front_pack.get("narrative_later_papers"))
        self.assertEqual(after["narrative"]["positioning"][0]["text"], rewritten_block["text"])
        self.assertEqual(after["narrative"]["gap_notes"], original_gap_notes,
                         "the refinement cleared research-gap notes the report did not name")
        analysis_after = (self.prof_dir / self.ANALYSIS_MD).read_text(encoding="utf-8")
        self.assertIn(f"[{reference_title}](zotero://select/library/items/{reference_key})",
                      analysis_after)
        for note in original_gap_notes.values():
            self.assertIn(f"- 大白话：{note['explanation']}", analysis_after)
        self.assertNotIn(marker, analysis_after)

        # 7) Independent fixture: an accepted pack plus genuinely changed paper
        #    facts must be refused with a refresh request, not silently served
        #    from the pack-only path.
        self._assert_stale_reference_facts_are_refused()

    def _assert_stale_reference_facts_are_refused(self):
        self._new_program_case("t1-stale-facts")
        member_key = "STALE001"
        reference_key = "STALEREF"
        papers = [
            self.make_paper(member_key, "Stale Fixture Member", ["信号", "処理"],
                            ["Stale fixture future work."]),
            self.make_paper(reference_key, "Stale Fixture Reference", ["参考", "レビュー"], []),
        ]
        direction = self.make_direction("dir_S", [member_key], name_ja="陈旧检查",
                                        name_zh="陈旧检查", summary="陈旧事实检查")
        direction["relevant_keys"] = [member_key, reference_key]
        facts_path = self.write_facts(papers, [direction], name="stale-facts.json")

        self.run_resolve(facts_path, {})
        marker = "T1陈旧事实标记"
        block = {"kind": "para", "text": marker + " 原事实指纹检查。", "refs": [],
                 "concrete_object": "一组合成陈旧输入", "input_example": "输入一份合成事实快照",
                 "output_example": "得到一份陈旧拒绝回执"}
        self._run_stage2_finalize_with_narratives(facts_path, {"dir_S": block})
        report = self._write_blocking_report("t1-stale-round.json", marker)
        self._record_validation(report)

        pack_path = self.prof_dir / self.INPUT_PACK
        analysis_path = self.prof_dir / self.ANALYSIS_MD
        pack_before = pack_path.read_bytes()
        analysis_before = analysis_path.read_bytes()
        files_before = sorted(str(path.relative_to(self.prof_dir))
                              for path in self.prof_dir.rglob("*") if path.is_file())

        # The reference paper's facts sidecar is the changed original input: its
        # digest feeds the original direction fingerprint.
        sidecar_path = Path(papers[1]["facts_file"])
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["topic_terms"] = ["再検討", "照合"]
        sidecar["confidence"] = 0.5
        write_json(sidecar_path, sidecar)

        stale = self._refine_plan(report, facts_path=facts_path)
        self.assertEqual(stale["status"], "needs_refresh",
                         msg=json.dumps(stale, ensure_ascii=False))
        self.assertEqual(stale["reason_code"], "source_fingerprint_changed")
        self.assertEqual(stale.get("jobs") or [], [])
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(analysis_path.read_bytes(), analysis_before)
        self.assertEqual(sorted(str(path.relative_to(self.prof_dir))
                                for path in self.prof_dir.rglob("*") if path.is_file()),
                         files_before)

    # ------------------------------------------------------------------
    # T2: legal ownership (split/merge), source mapping and reference
    # inheritance (plan 5.1 T2 recipe; plan 3.1.2/5 and 3.4.2/3).
    # ------------------------------------------------------------------

    def test_resolved_reference_inheritance_and_source_mapping(self):
        state = self._build_split_and_merge_state()
        facts_path = state["facts_path"]

        # 1) Legal split and merge: source reference scope is kept, the new
        #    child owns exactly its approved final members (including a legal
        #    full-text rescue) and never inherits the source's extra reference,
        #    and the merge target unions the participants' reference sets
        #    without the third direction or the source narrative.
        self.assertEqual(set(state["by_id"]), {"dir_A", state["child"], "dir_B", "dir_D"})
        source = state["by_id"]["dir_A"]
        self.assertEqual(set(source["supporting_item_keys"]), {state["split_source"]})
        self.assertEqual(set(source["relevant_keys"]),
                         {state["split_source"], state["split_moved"], state["split_reference"]})
        self.assertNotIn(state["split_moved"], source["supporting_item_keys"])

        child = state["by_id"][state["child"]]
        self.assertEqual(set(child["supporting_item_keys"]),
                         {state["split_moved"], state["rescue"]})
        self.assertEqual(set(child["relevant_keys"]), {state["split_moved"], state["rescue"]})
        self.assertNotIn(state["split_reference"], child["relevant_keys"])
        # Shared paper identity: the rescue candidate keeps ONE canonical record.
        self.assertEqual(set(state["by_id"]["dir_D"]["supporting_item_keys"]),
                         {state["rescue"], state["third"]})
        self.assertEqual(state["pack"]["papers"][state["rescue"]]["title"],
                         "Rescued Full Text Study")

        target = state["by_id"]["dir_B"]
        expected_target_members = {state["merge_target"], state["merge_target2"],
                                   state["merge_source"]}
        expected_target_references = {state["merge_target"], state["merge_target2"],
                                      state["merge_reference"], state["merge_source"],
                                      state["merge_source_reference"]}
        self.assertEqual(set(target["supporting_item_keys"]), expected_target_members)
        self.assertEqual(set(target["relevant_keys"]), expected_target_references)
        for outsider in (state["rescue"], state["third"], state["third_reference"]):
            self.assertNotIn(outsider, target["supporting_item_keys"])
            self.assertNotIn(outsider, target["relevant_keys"])
        # Gap migration: the merge source's gap follows its paper, the third
        # direction's gaps never join, and the split moved its gap to the child.
        self.assertEqual({gap["item_key"] for gap in target["gap_shortlist"]},
                         expected_target_members)
        self.assertTrue(set(self._pack_gap_index(target)).isdisjoint(
            set(self._pack_gap_index(state["by_id"]["dir_D"]))))
        self.assertEqual({gap["item_key"] for gap in source["gap_shortlist"]},
                         {state["split_source"]})
        self.assertEqual({gap["item_key"] for gap in child["gap_shortlist"]},
                         {state["split_moved"]})
        self.assertFalse({gap["gap_id"] for gap in source["gap_shortlist"]}
                         & {gap["gap_id"] for gap in child["gap_shortlist"]})
        # The target keeps its own narrative; the merge source's is not glued on.
        expected_target_block = {
            "kind": "para", "text": state["block_b"]["text"],
            "refs": [f"paper:{state['merge_target']}"],
            "concrete_object": state["block_b"]["concrete_object"],
            "input_example": state["block_b"]["input_example"],
            "output_example": state["block_b"]["output_example"]}
        self.assertEqual(target["narrative"]["positioning"], [expected_target_block])
        self.assertNotIn(state["marker_c"], json.dumps(target["narrative"], ensure_ascii=False))

        # 2) An unchanged rerun keeps the materialised child membership and both
        #    reference scopes.
        reuse_plan, reuse_finalize = self.run_resolve(facts_path, {})
        self.assertEqual(reuse_plan["jobs"], [])
        self.assertFalse(reuse_finalize["needs_user_choice"])
        self.assertEqual(self.run_stage2_finalize(facts_path)["status"], "ok")

        pack = self.load_pack()
        by_id = self._pack_directions(pack)
        target = by_id["dir_B"]
        self.assertEqual(set(by_id), {"dir_A", state["child"], "dir_B", "dir_D"})
        self.assertEqual(set(by_id[state["child"]]["supporting_item_keys"]),
                         {state["split_moved"], state["rescue"]})
        self.assertEqual(set(by_id[state["child"]]["relevant_keys"]),
                         {state["split_moved"], state["rescue"]})
        self.assertEqual(set(by_id["dir_A"]["relevant_keys"]),
                         {state["split_source"], state["split_moved"], state["split_reference"]})
        self.assertEqual(set(by_id["dir_A"]["supporting_item_keys"]), {state["split_source"]})

        # 3) The pack's raw source mapping keeps the vanished merge source with
        #    a source fingerprint that is not the resolve fingerprint, while the
        #    final public fingerprint still drives downstream consumers.
        rows = {row["provisional_direction_id"]: row
                for row in pack["resolved_directions"]["directions"]}
        self.assertEqual(set(rows), {"dir_A", "dir_B", "dir_C", "dir_D"})
        self.assertNotIn("dir_C", by_id)
        source_row = rows["dir_C"]
        self.assertEqual(source_row["resolution_type"], "merged_into")
        self.assertEqual(source_row["merge_target"], "dir_B")
        self.assertEqual(source_row["resolved_direction_id"], "dir_C")
        source_fingerprint = source_row.get("provisional_input_fingerprint")
        self.assertIsInstance(source_fingerprint, str,
                              msg="the source mapping row must store the raw source fingerprint")
        self.assertTrue(source_fingerprint)
        self.assertNotEqual(source_fingerprint, source_row.get("input_fingerprint"),
                            msg="the source mapping fingerprint must not be the resolve fingerprint")
        for did in ("dir_A", "dir_B", "dir_D"):
            self.assertEqual(rows[did].get("provisional_input_fingerprint"),
                             by_id[did].get("provisional_input_fingerprint"), msg=did)

        # 4) Both refine entries use the FINAL directions: the split child and
        #    the merge target are addressable, the vanished source is not, and
        #    the reference/gap scope is the materialised pack scope.
        report = self._write_blocking_report("t2-first-round.json",
                                             [state["marker_a"], state["marker_b"]])
        self._record_validation(report)
        facts_entry = self._refine_plan(report, facts_path=facts_path)
        pack_entry = self._refine_plan(report)
        for label, entry in (("facts", facts_entry), ("professor-dir", pack_entry)):
            self.assertEqual(entry["status"], "ok",
                             msg=f"{label}: {json.dumps(entry, ensure_ascii=False)}")
            self.assertEqual(set(entry["directions"]), {"dir_A", "dir_B"}, msg=label)
            self.assertEqual({job["direction_id"] for job in entry["jobs"]},
                             {"dir_A", "dir_B"}, msg=label)
        facts_jobs = {job["direction_id"]: job for job in facts_entry["jobs"]}
        pack_jobs = {job["direction_id"]: job for job in pack_entry["jobs"]}
        expected_source_scope = {state["split_source"], state["split_moved"],
                                 state["split_reference"]}
        for label, jobs in (("facts", facts_jobs), ("professor-dir", pack_jobs)):
            self.assertEqual(set(self._material_titles(jobs["dir_A"])),
                             expected_source_scope, msg=label)
            self.assertEqual(set(self._material_titles(jobs["dir_B"])),
                             expected_target_references, msg=label)
            self.assertEqual(self._material_gaps(jobs["dir_B"]),
                             self._pack_gap_index(target), msg=label)
        self.assertEqual(self._material_titles(facts_jobs["dir_A"]),
                         self._material_titles(pack_jobs["dir_A"]))
        self.assertEqual(self._material_titles(facts_jobs["dir_B"]),
                         self._material_titles(pack_jobs["dir_B"]))
        self.assertEqual(self._material_titles(pack_jobs["dir_A"])[state["split_reference"]],
                         "Split Reference Review")
        self.assertEqual(
            self._material_titles(pack_jobs["dir_B"])[state["merge_source_reference"]],
            "Merge Source Reference")

        child_scope = self._refine_plan(report, direction_id=state["child"])
        self.assertEqual(child_scope["status"], "ok",
                         msg=json.dumps(child_scope, ensure_ascii=False))
        self.assertEqual(child_scope["jobs"], [])
        vanished_scope = self._refine_plan(report, direction_id="dir_C")
        self.assertNotEqual(vanished_scope["status"], "ok",
                            msg=json.dumps(vanished_scope, ensure_ascii=False))
        self.assertEqual(vanished_scope.get("jobs") or [], [])

        # 5) One pack-only revision of the final directions keeps members and
        #    the source mapping, uses the migrated gap and renders real titles.
        target_gap_index = self._pack_gap_index(target)
        self.assertIn(state["merge_source"], set(target_gap_index.values()),
                      msg="the merge source gap must migrate with its paper")
        merged_gap_id = next(gap_id for gap_id, item_key in target_gap_index.items()
                             if item_key == state["merge_source"])
        # The split source's original narrative already carries a research-gap
        # note of the member that stays in the source; the whole-narrative
        # rewrite must copy it over unchanged.
        source_gap_notes = by_id["dir_A"]["narrative"]["gap_notes"]
        self.assertTrue(source_gap_notes,
                        "the fixture must give the split source an original research-gap note")
        self.assertTrue(
            set(source_gap_notes) <= {gap["gap_id"] for gap in by_id["dir_A"]["gap_shortlist"]},
            "the original gap note must stay in the source's own rendered shortlist")
        rewritten_a = {
            "kind": "para",
            "text": "T2拆分源修订：{{P:" + state["split_moved"] + "}} 与 {{P:"
                    + state["split_reference"] + "}} 仍属源参考范围。",
            "refs": [f"paper:{state['split_moved']}", f"paper:{state['split_reference']}"],
            "concrete_object": "一组合成拆分样本",
            "input_example": "输入一份合成拆分输入",
            "output_example": "得到一份拆分后的分析稿",
        }
        rewritten_b = {
            "kind": "para",
            "text": "T2合并目标修订：{{P:" + state["merge_source"] + "}} 与 {{P:"
                    + state["merge_source_reference"] + "}} 属合并参考范围，{{G:"
                    + merged_gap_id + "}} 为迁移 gap。",
            "refs": [f"paper:{state['merge_source']}",
                     f"paper:{state['merge_source_reference']}",
                     f"gap:{merged_gap_id}"],
            "concrete_object": "一组合成合并样本",
            "input_example": "输入一份合成合并输入",
            "output_example": "得到一份合并后的分析稿",
        }
        finalized = self._refine_finalize(
            report, [pack_jobs["dir_A"], pack_jobs["dir_B"]],
            {"dir_A": rewritten_a, "dir_B": rewritten_b},
            gap_notes={"dir_B": [{"gap_id": merged_gap_id,
                                  "summary": "迁移后的合并缺口",
                                  "explanation": "该缺口随合并源论文进入目标方向。"}]})
        self.assertEqual(finalized["status"], "ok",
                         msg=json.dumps(finalized, ensure_ascii=False))
        self.assertEqual(sorted(finalized["rewritten"]), ["dir_A", "dir_B"])

        pack_after = self.load_pack()
        by_id_after = self._pack_directions(pack_after)
        self.assertEqual(set(by_id_after), {"dir_A", state["child"], "dir_B", "dir_D"})
        self.assertEqual(set(by_id_after["dir_B"]["supporting_item_keys"]),
                         expected_target_members)
        self.assertEqual(set(by_id_after["dir_B"]["relevant_keys"]), expected_target_references)
        self.assertEqual(set(by_id_after["dir_A"]["supporting_item_keys"]), {state["split_source"]})
        self.assertEqual(pack_after["resolved_directions"]["directions"],
                         pack["resolved_directions"]["directions"])
        self.assertEqual(by_id_after["dir_B"]["narrative"]["positioning"][0]["text"],
                         rewritten_b["text"])
        # The reported target keeps exactly its own updated note; the untouched
        # source direction must still carry its original note instead of [].
        self.assertEqual(set(by_id_after["dir_B"]["narrative"]["gap_notes"]), {merged_gap_id})
        self.assertEqual(by_id_after["dir_A"]["narrative"]["gap_notes"], source_gap_notes,
                         "the refinement cleared research-gap notes the report did not name")
        analysis = (self.prof_dir / self.ANALYSIS_MD).read_text(encoding="utf-8")
        self.assertIn(f"[{state['merge_source_title']}]"
                      f"(zotero://select/library/items/{state['merge_source']})", analysis)
        self.assertIn(f"[Merge Source Reference]"
                      f"(zotero://select/library/items/{state['merge_source_reference']})",
                      analysis)
        for note in source_gap_notes.values():
            self.assertIn(f"- 大白话：{note['explanation']}", analysis)

        # 6) Only the vanished source's original-facts field changes (red_lines
        #    enters the original fingerprint but not the resolve fingerprint):
        #    the facts entry must ask for a refresh and write nothing.
        original_facts = Path(facts_path).read_bytes()
        facts_payload = json.loads(original_facts.decode("utf-8"))
        source_direction = next(direction for direction in facts_payload["directions"]
                                if direction["collection_key"] == "dir_C")
        source_direction["red_lines"] = [{"scope": "direction", "text": "合并源新增红线。"}]
        write_json(Path(facts_path), facts_payload)

        pack_path = self.prof_dir / self.INPUT_PACK
        analysis_path = self.prof_dir / self.ANALYSIS_MD
        pack_before = pack_path.read_bytes()
        analysis_before = analysis_path.read_bytes()
        stale = self._refine_plan(report, facts_path=facts_path)
        self.assertEqual(stale["status"], "needs_refresh",
                         msg=json.dumps(stale, ensure_ascii=False))
        self.assertEqual(stale["reason_code"], "source_fingerprint_changed")
        self.assertEqual(stale.get("jobs") or [], [])
        self.assertEqual(pack_path.read_bytes(), pack_before)
        self.assertEqual(analysis_path.read_bytes(), analysis_before)

        # An old merged pack without the source fingerprint must ask for a
        # refresh as well: no fabricated fingerprint, no membership inference.
        Path(facts_path).write_bytes(original_facts)
        legacy_pack = json.loads(pack_path.read_text(encoding="utf-8"))
        for row in legacy_pack["resolved_directions"]["directions"]:
            row.pop("provisional_input_fingerprint", None)
        write_json(pack_path, legacy_pack)
        legacy_before = pack_path.read_bytes()
        legacy = self._refine_plan(report, facts_path=facts_path)
        self.assertEqual(legacy["status"], "needs_refresh",
                         msg=json.dumps(legacy, ensure_ascii=False))
        self.assertIn(legacy["reason_code"], {"source_fingerprint_changed", "needs_refresh"})
        self.assertEqual(legacy.get("jobs") or [], [])
        self.assertEqual(pack_path.read_bytes(), legacy_before)
        pack_path.write_bytes(pack_before)

        # 7) The acceptance/materialisation boundary: a split that would move
        #    every provisional member away is rejected with zero writes, even
        #    though the reference scope still names a paper.
        self._assert_emptied_source_split_is_rejected()

        # 8) Pack-only legacy reads: a missing relevant_keys field falls back to
        #    the members as the minimum scope, an explicit empty list stays an
        #    empty P licence, and neither uses professor-level papers.
        self.assertEqual(self._assert_legacy_relevant_keys_scope("t2-legacy-missing", "missing"),
                         {"LEGACY01"})
        self.assertEqual(self._assert_legacy_relevant_keys_scope("t2-legacy-empty", "empty"),
                         set())

    def _build_split_and_merge_state(self):
        """Materialise one accepted split and one accepted merge in one state."""
        self._new_program_case("t2-split-merge")
        keys = {
            "split_source": "SPLIT001",
            "split_moved": "SPLIT002",
            "split_reference": "SPLITREF",
            "rescue": "RESCUE01",
            "merge_target": "MERGE001",
            "merge_target2": "MERGE002",
            "merge_reference": "MERGEREF",
            "merge_source": "MERGEC01",
            "merge_source_reference": "MERGECREF",
            "third": "OTHER001",
            "third_reference": "OTHERREF",
            "child": "dir_A__control",
        }
        papers = [
            self.make_paper(keys["split_source"], "Split Source Kept Study", ["信号", "処理"],
                            ["Split source future work."]),
            self.make_paper(keys["split_moved"], "Split Moved Study", ["制御", "ロボット"],
                            ["Split moved future work."]),
            self.make_paper(keys["split_reference"], "Split Reference Review", ["信号"], []),
            self.make_paper(keys["rescue"], "Rescued Full Text Study", ["制御"],
                            ["Rescued future work."]),
            self.make_paper(keys["merge_target"], "Merge Target Study", ["信号", "処理"],
                            ["Merge target future work."]),
            self.make_paper(keys["merge_target2"], "Merge Target Second Study", ["信号"],
                            ["Merge target second future work."]),
            self.make_paper(keys["merge_reference"], "Merge Target Reference", ["信号"], []),
            self.make_paper(keys["merge_source"], "Merge Source Study", ["信号", "処理"],
                            ["Merge source future work."]),
            self.make_paper(keys["merge_source_reference"], "Merge Source Reference", ["信号"], []),
            self.make_paper(keys["third"], "Third Direction Study", ["材料"],
                            ["Third direction future work."]),
            self.make_paper(keys["third_reference"], "Third Direction Reference", ["材料"], []),
        ]
        directions = [
            self.make_direction("dir_A", [keys["split_source"], keys["split_moved"]],
                                name_ja="拆分源方向", name_zh="拆分源", summary="拆分源方向"),
            self.make_direction("dir_B", [keys["merge_target"], keys["merge_target2"]],
                                name_ja="合并目标方向", name_zh="合并目标", summary="合并目标方向"),
            self.make_direction("dir_C", [keys["merge_source"]],
                                name_ja="合并源方向", name_zh="合并源", summary="合并源方向"),
            self.make_direction("dir_D", [keys["rescue"], keys["third"]],
                                name_ja="第三方向", name_zh="第三方向", summary="第三方向"),
        ]
        directions[0]["relevant_keys"] = [keys["split_source"], keys["split_moved"],
                                         keys["split_reference"]]
        directions[1]["relevant_keys"] = [keys["merge_target"], keys["merge_target2"],
                                         keys["merge_reference"]]
        directions[2]["relevant_keys"] = [keys["merge_source"], keys["merge_source_reference"]]
        directions[3]["relevant_keys"] = [keys["rescue"], keys["third"], keys["third_reference"]]
        facts_path = self.write_facts(papers, directions, name="t2-facts.json")

        self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A", "provisional_direction_id": "dir_A",
                "name_ja": "拆分源方向", "name_zh": "拆分源",
                "resolution_type": "split_from",
                "papers_to_add": [keys["split_moved"], keys["rescue"]],
                "papers_to_remove": [],
                "paper_justifications": {
                    keys["split_moved"]: "moved into the control child",
                    keys["rescue"]: "full text rescues a candidate outside the source relevant set"},
                "split_target": keys["child"], "merge_target": None, "user_note": "",
            },
            "dir_C": {
                "resolved_direction_id": "dir_C", "provisional_direction_id": "dir_C",
                "name_ja": "合并源方向", "name_zh": "合并源",
                "resolution_type": "merged_into",
                "papers_to_add": [], "papers_to_remove": [],
                "paper_justifications": {}, "split_target": None,
                "merge_target": "dir_B", "user_note": "",
            },
        })
        accepted = self.accept_resolved(facts_path, ["dir_A", "dir_C"])
        self.assertEqual(accepted["status"], "ok", msg=json.dumps(accepted, ensure_ascii=False))

        marker_a = "T2拆分源标记"
        marker_b = "T2合并目标标记"
        marker_c = "T2合并源标记"
        block_a = {
            "kind": "para",
            "text": marker_a + "：{{P:" + keys["split_moved"] + "}} 与 {{P:"
                    + keys["split_reference"] + "}} 保留在源参考范围。",
            "refs": [f"paper:{keys['split_moved']}", f"paper:{keys['split_reference']}"],
            "concrete_object": "一组合成拆分样本",
            "input_example": "输入一份合成拆分输入",
            "output_example": "得到一份拆分后的分析稿",
        }
        block_b = {
            "kind": "para",
            "text": marker_b + "：{{P:" + keys["merge_target"] + "}} 为合并目标原参考。",
            "refs": [f"paper:{keys['merge_target']}"],
            "concrete_object": "一组合成合并样本",
            "input_example": "输入一份合成合并输入",
            "output_example": "得到一份合并后的分析稿",
        }
        block_c = {
            "kind": "para",
            "text": marker_c + " 不应拼接进目标。",
            "refs": [],
            "concrete_object": "一组合成源叙事",
            "input_example": "输入一份合成源叙事",
            "output_example": "得到一份被丢弃的源叙事",
        }
        self._run_stage2_finalize_with_narratives(
            facts_path, {"dir_A": block_a, "dir_B": block_b, "dir_C": block_c},
            gap_note_items={"dir_A": keys["split_source"]})

        pack = self.load_pack()
        state = dict(keys)
        state.update({
            "facts_path": facts_path,
            "pack": pack,
            "by_id": self._pack_directions(pack),
            "marker_a": marker_a,
            "marker_b": marker_b,
            "marker_c": marker_c,
            "block_a": block_a,
            "block_b": block_b,
            "block_c": block_c,
            "merge_source_title": "Merge Source Study",
        })
        return state

    def _assert_emptied_source_split_is_rejected(self):
        """A split moving the only provisional member away fails closed."""
        self._new_program_case("t2-emptied-source")
        member_key = "EMPTY001"
        reference_key = "EMPTYREF"
        papers = [
            self.make_paper(member_key, "Only Provisional Member", ["信号"],
                            ["Only member future work."]),
            self.make_paper(reference_key, "Reference Only Paper", ["信号"], []),
        ]
        direction = self.make_direction("dir_E", [member_key], name_ja="空源方向",
                                        name_zh="空源方向", summary="唯一成员将被移空")
        direction["relevant_keys"] = [member_key, reference_key]
        facts_path = self.write_facts(papers, [direction], name="emptied-facts.json")

        results_dir = new_resolve_results_dir(self.root)
        plan_payload = plan_resolve(facts_path, results_dir)
        self.assertEqual(plan_payload["status"], "ok",
                         msg=json.dumps(plan_payload, ensure_ascii=False))
        write_resolve_results(results_dir, plan_payload, {
            "dir_E": {
                "resolved_direction_id": "dir_E", "provisional_direction_id": "dir_E",
                "name_ja": "空源方向", "name_zh": "空源方向",
                "resolution_type": "split_from",
                "papers_to_add": [member_key], "papers_to_remove": [],
                "paper_justifications": {member_key: "move the only provisional member away"},
                "split_target": "dir_E__child", "merge_target": None, "user_note": "",
            },
        }, facts_path)

        payload = finalize_resolve(facts_path, results_dir)
        self.assertEqual(payload["status"], "error", msg=json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["reason_code"], "invalid_result_json")
        # Zero authoritative writes: the reference-only paper cannot stand in
        # for the emptied provisional membership.
        self.assertFalse((self.prof_dir / "论文分析" / self.RESOLVED_SIDECAR).exists())
        self.assertFalse((self.prof_dir / self.INPUT_PACK).exists())
        self.assertFalse((self.prof_dir / self.ANALYSIS_MD).exists())

    def _assert_legacy_relevant_keys_scope(self, name, mode):
        """Pack-only read of a legacy direction: (missing | empty) relevant_keys."""
        self._new_program_case(name)
        marker = f"T2旧包标记{name}"
        papers = [
            self.make_paper("LEGACY01", "Legacy Shared Study", ["信号"],
                            ["Legacy gap one."]),
            self.make_paper("LEGACY02", "Legacy Second Study", ["制御"],
                            ["Legacy gap two."]),
        ]
        directions = [
            self.make_direction("dir_L", ["LEGACY01"], name_ja="旧包方向", name_zh="旧包方向",
                                summary="旧包读取范围"),
            self.make_direction("dir_M", ["LEGACY02"], name_ja="对照方向", name_zh="对照方向",
                                summary="教授级论文兜底对照"),
        ]
        facts_path = self.write_facts(papers, directions, name=f"{name}-facts.json")
        self.run_resolve(facts_path, {})
        block = {"kind": "para", "text": marker + " 旧包读取范围检查。", "refs": [],
                 "concrete_object": "一组合成旧包输入", "input_example": "输入一份旧格式输入包",
                 "output_example": "得到一份范围受限的修订任务"}
        self._run_stage2_finalize_with_narratives(facts_path, {"dir_L": block})

        pack_path = self.prof_dir / self.INPUT_PACK
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        direction = next(row for row in pack["directions"] if row["direction_id"] == "dir_L")
        if mode == "missing":
            direction.pop("relevant_keys", None)
        else:
            direction["relevant_keys"] = []
        write_json(pack_path, pack)

        report = self._write_blocking_report(f"{name}-round.json", marker)
        self._record_validation(report)
        plan = self._refine_plan(report)
        self.assertEqual(plan["status"], "ok", msg=json.dumps(plan, ensure_ascii=False))
        self.assertEqual([job["direction_id"] for job in plan["jobs"]], ["dir_L"])
        job = plan["jobs"][0]
        if mode == "missing":
            self.assertEqual(self._material_titles(job), {"LEGACY01": "Legacy Shared Study"})
        else:
            self.assertEqual(self._material_titles(job), {})
        self.assertNotIn("LEGACY02", self._material_titles(job))
        return set(self._material_titles(job))


if __name__ == "__main__":
    unittest.main()
