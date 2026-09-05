"""Stage 3 resolved-direction grouping regressions (issue #8).

Stage 3 must consume Stage 2 resolved directions: ideas grouped per resolved
direction with exact direction_id/item_key/gap_id references, shared papers
keeping a single paper identity, cross-direction ideas only when explicitly
labeled with all participating resolved direction IDs, and per-direction
reuse of unchanged idea state.
"""
import copy
import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import (
    ResolvedPipelineMixin, parse, quote_id, run_cli, write_json)

_SCRIPT = Path(__file__).parents[1] / "scripts" / "contact_state.py"
_spec = importlib.util.spec_from_file_location("contact_state_cs", _SCRIPT)
contact_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contact_state)


def result_file(kind: str, identity: str) -> str:
    """Mirror the runner's deterministic result-file naming (issue #8 §4.1)."""
    return contact_state.safe_result_file(kind, identity)


PROFESSOR = "試験 教授"

QUOTES = {
    "P1": "Future work will extend the shared method to streaming inputs.",
    "P2": "Future work plans a robustness benchmark for the signal pipeline.",
    "P3": "Future work will deploy the sensor network at campus scale.",
}


def candidate_metas(md_text: list) -> list:
    return [json.loads(m) for m in
            re.findall(r"<!-- candidate_meta: (.*?) -->", md_text)]


class Stage3DirectionGroupBase(ResolvedPipelineMixin, unittest.TestCase):
    """Two resolved directions (dir_A, dir_B) sharing paper P1."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / PROFESSOR
        (self.prof_dir / "论文分析").mkdir(parents=True)
        papers = [
            self.make_paper("P1", "Shared Method Paper", ["method", "shared"],
                            [QUOTES["P1"]]),
            self.make_paper("P2", "Signal Robustness Paper", ["signal", "robust"],
                            [QUOTES["P2"]]),
            self.make_paper("P3", "Campus Sensor Paper", ["sensor", "network"],
                            [QUOTES["P3"]]),
        ]
        directions = [
            self.make_direction("dir_A", ["P1", "P2"], name_ja="信号処理",
                                name_zh="信号处理", summary="信号处理方向"),
            self.make_direction("dir_B", ["P1", "P3"], name_ja="センサ網",
                                name_zh="传感网络", summary="传感网络方向"),
        ]
        facts_path = self.write_facts(papers, directions)
        self.run_resolve(facts_path, {})
        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok",
                         msg=json.dumps(payload, ensure_ascii=False))
        pack = self.load_pack()
        self.pack_directions = {d["direction_id"]: d for d in pack["directions"]}
        self.gap_ids = {key: quote_id(quote) for key, quote in QUOTES.items()}

    def tearDown(self):
        self.temp.cleanup()

    # -- helpers ---------------------------------------------------------

    def stage3_plan(self, *extra_args):
        return parse(run_cli("stage3-plan", "--professor-dir", self.prof_dir,
                             "--program-root", self.root, *extra_args))

    def stage3_finalize(self, results_dir, *extra_args):
        return parse(run_cli("stage3-finalize", "--professor-dir", self.prof_dir,
                             "--results", results_dir,
                             "--program-root", self.root, *extra_args))

    def make_candidate(self, cid, item_key, direction_id="dir_A", origin="generated"):
        candidate = {"id": cid, "kind": "direction",
                     "direction_ids": [direction_id], "origin": origin,
                     "title": f"候选 {cid}",
                     "one_liner": "教授的工作启发我思考延伸方向",
                     "research_question": "该方法在流式输入下是否保持相同收敛性？",
                     "points": [], "gap_refs": [], "papers": [],
                     "fit": "high", "fit_note": "", "red_lines": [],
                     "why_recommended": "兴趣契合", "tension_points": []}
        if item_key is not None:
            candidate["points"] = ["挂在缺口 1"]
            candidate["gap_refs"] = [{"direction_id": direction_id,
                                      "item_key": item_key,
                                      "gap_id": self.gap_ids[item_key]}]
            candidate["papers"] = [{"item_key": item_key,
                                    "direction_ids": [direction_id],
                                    "role": "基座", "fit_note": "教授通讯"}]
        return candidate

    def generated_doc(self, ckey, item_keys):
        return {"schema": 2, "kind": "candidates", "direction_id": ckey,
                "mode": "generated", "priority": "主推 1",
                "candidates": [self.make_candidate(f"{ckey}_{n}", key,
                                                   direction_id=ckey)
                               for n, key in enumerate(item_keys, start=1)]}

    def write_results(self, name, docs):
        results = self.root / name
        results.mkdir(parents=True, exist_ok=True)
        for did, doc in docs.items():
            write_json(results / result_file("candidates", did), doc)
        return results

    def cross_doc(self, direction_ids, candidates):
        return {"schema": 2, "kind": "cross_candidates",
                "group_id": contact_state.cross_group_id(sorted(direction_ids)),
                "direction_ids": sorted(direction_ids),
                "candidates": candidates}

    def cross_candidate(self, cid, direction_ids, gap_keys, paper_keys,
                        gap_owner=None):
        """A cross candidate citing gaps/papers from BOTH participants.

        gap_keys: item keys whose gaps are cited; gap_owner maps item_key →
        the direction_id cited in the triple (default: first participant).
        """
        direction_ids = sorted(direction_ids)
        gap_owner = gap_owner or {}
        idea = self.make_candidate(cid, None)
        idea["kind"] = "cross_direction"
        idea["direction_ids"] = list(direction_ids)
        idea["gap_refs"] = [
            {"direction_id": gap_owner.get(key, direction_ids[0]),
             "item_key": key, "gap_id": self.gap_ids[key]}
            for key in gap_keys]
        idea["papers"] = [{"item_key": key, "direction_ids": list(direction_ids),
                           "role": "共同基座", "fit_note": "共享论文"}
                          for key in paper_keys]
        return idea

    def load_state(self):
        return json.loads(
            (self.prof_dir / "套磁候选状态.json").read_text(encoding="utf-8"))

    def load_md(self):
        return (self.prof_dir / "套磁想法候选.md").read_text(encoding="utf-8")

    @staticmethod
    def md_body(md_text: str) -> str:
        """MD content modulo the render timestamp and its hash line."""
        kept = [line for line in md_text.splitlines()
                if not line.startswith("> 2") and not line.startswith("render_sha256:")]
        return "\n".join(kept)

    def rewrite_pack_fingerprint(self, did, fingerprint):
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        for direction in pack["directions"]:
            if direction["direction_id"] == did:
                direction["input_fingerprint"] = fingerprint
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

    def stage4_finalize(self, selections, name="sel-input.json"):
        sel_input = self.root / name
        sel_input.write_text(json.dumps({"selections": selections},
                                        ensure_ascii=False), encoding="utf-8")
        return parse(run_cli("stage4-finalize", "--program-root", self.root,
                             "--selection-input", sel_input))

    def selection_doc(self):
        return json.loads((self.root / "教授研究" / "套磁选择.json")
                          .read_text(encoding="utf-8"))

    def email_pack(self):
        return json.loads((self.root / "教授研究" / "邮件输入.json")
                          .read_text(encoding="utf-8"))

    @staticmethod
    def source_hash(entry):
        payload = {key: entry[key] for key in (
            "email_id", "direction_ids", "directions", "idea", "papers", "gaps",
            "red_lines", "allowed_sources", "contact_evidence", "cross_direction")}
        return hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class Stage3DirectionGroupTests(Stage3DirectionGroupBase):

    CROSS_GROUP = '[["dir_A","dir_B"]]'

    def _cross_request(self):
        """Request the A+B group on plan; returns (results, cross_job)."""
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        plan = self.stage3_plan("--cross-direction-groups", self.CROSS_GROUP)
        cross_job = next(j for j in plan["jobs"] if j["kind"] == "cross_direction")
        return results, cross_job

    def _write_cross_result(self, cross_job, candidates, name=None):
        """Write the cross result NEXT TO the ordinary results (finalize reads
        both from one results dir); pass name=None to reuse the "s3" dir."""
        cross_dir = self.root / (name or "s3")
        cross_dir.mkdir(exist_ok=True)
        write_json(cross_dir / result_file("candidates", cross_job["group_id"]),
                   self.cross_doc(["dir_A", "dir_B"], candidates))
        return cross_dir

    def _grounded_cross(self, cid="X1"):
        return self.cross_candidate(cid, ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                                    gap_owner={"P2": "dir_A", "P3": "dir_B"})

    def test_plan_groups_jobs_per_resolved_direction_with_exact_ids(self):
        plan = self.stage3_plan()
        self.assertEqual(plan["status"], "ok")
        by_did = {d["direction_id"]: d for d in plan["directions"]}
        self.assertEqual(set(by_did), {"dir_A", "dir_B"})
        self.assertEqual(by_did["dir_A"]["collection_key"], "dir_A")
        self.assertEqual([j["direction_id"] for j in plan["jobs"]],
                         ["dir_A", "dir_B"])
        for job in plan["jobs"]:
            self.assertEqual(job["kind"], "candidates")
            self.assertEqual(job["model_input"]["direction_id"], job["direction_id"])
            self.assertNotIn("known_directions", job["model_input"])
            self.assertNotIn("cross_direction", job["model_input"]["rules"])
        # Default (no explicit groups) means NO cross-direction work at all.
        self.assertEqual(plan["cross_direction_groups"], [])

    def test_ideas_grouped_per_direction_share_paper_identity(self):
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))

        state = self.load_state()
        self.assertEqual(state["schema"], 2)
        self.assertEqual(state["identity_version"], "direction-id-v1")
        state_dirs = {d["direction_id"]: d for d in state["directions"]}
        # Shared paper P1 is referenced by both directions under the SAME
        # item_key; no per-direction paper identity was invented.
        dir_a_keys = {p["item_key"] for c in state_dirs["dir_A"]["candidates"]
                      for p in c["papers"]}
        dir_b_keys = {p["item_key"] for c in state_dirs["dir_B"]["candidates"]
                      for p in c["papers"]}
        self.assertIn("P1", dir_a_keys)
        self.assertIn("P1", dir_b_keys)
        self.assertEqual(dir_a_keys, {"P1", "P2"})
        self.assertEqual(dir_b_keys, {"P1", "P3"})

        md = self.load_md()
        self.assertIn("方向 ID：dir_A", md)
        self.assertIn("方向 ID：dir_B", md)
        self.assertLess(md.index("方向 ID：dir_A"), md.index("方向 ID：dir_B"))
        metas = candidate_metas(md)
        self.assertEqual({tuple(m["direction_ids"]) for m in metas},
                         {("dir_A",), ("dir_B",)})
        first_meta = next(m for m in metas if m["direction_ids"] == ["dir_A"])
        self.assertTrue(all(set(ref) >= {"direction_id", "item_key", "gap_id"}
                            for ref in first_meta["gap_refs"]))
        # The shared paper renders the same single analysis link from BOTH
        # sections — referenced twice, duplicated never.
        self.assertEqual(md.count("[分析](论文分析/P1.md)"), 2)
        self.assertEqual(md.count("[分析](论文分析/P2.md)"), 1)
        self.assertEqual(md.count("[分析](论文分析/P3.md)"), 1)
        self.assertNotIn("## 跨方向想法（显式标注）", md)

    def test_unchanged_rerun_reuses_per_direction_idea_state(self):
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        first = self.stage3_finalize(results)
        self.assertEqual(first["status"], "ok")
        state_one = self.load_state()
        md_one = self.load_md()

        plan = self.stage3_plan()
        self.assertEqual({d["direction_id"]: d["action"]
                          for d in plan["directions"]},
                         {"dir_A": "reuse", "dir_B": "reuse"})
        self.assertEqual(plan["jobs"], [])

        second = self.stage3_finalize(results)
        self.assertEqual(second["status"], "ok")
        self.assertEqual(sorted(second["reused"]), ["dir_A", "dir_B"])
        state_two = self.load_state()
        self.assertEqual(state_two["directions"], state_one["directions"])
        self.assertEqual(self.md_body(self.load_md()), self.md_body(md_one))

    def test_explicit_cross_group_generates_separate_job_and_section(self):
        results, cross_job = self._cross_request()
        kinds = {job["kind"] for job in
                 self.stage3_plan("--cross-direction-groups",
                                  self.CROSS_GROUP)["jobs"]}
        self.assertEqual(kinds, {"candidates", "cross_direction"})
        self.assertEqual(cross_job["direction_ids"], ["dir_A", "dir_B"])
        self.assertTrue(cross_job["group_id"].startswith("cross:"))
        gap_owners = {g["item_key"]: sorted(g["direction_ids"])
                      for g in cross_job["model_input"]["gaps"]}
        self.assertEqual(gap_owners.get("P2"), ["dir_A"])
        self.assertEqual(gap_owners.get("P3"), ["dir_B"])

        self._write_cross_result(cross_job, [self._grounded_cross()])
        out = self.stage3_finalize(results, "--cross-direction-groups",
                                   self.CROSS_GROUP)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))

        state = self.load_state()
        groups = state["cross_direction_groups"]
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group["direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(group["group_id"], cross_job["group_id"])
        pack_fps = {did: self.pack_directions[did]["input_fingerprint"]
                    for did in ("dir_A", "dir_B")}
        self.assertEqual(group["direction_fingerprints"], pack_fps)
        for direction in state["directions"]:
            self.assertNotIn("X1", {c["id"] for c in direction["candidates"]})

        md = self.load_md()
        self.assertIn("## 跨方向想法（显式标注）", md)
        self.assertGreater(md.index("## 跨方向想法（显式标注）"),
                           md.index("方向 ID：dir_B"),
                           "cross-direction ideas must render after all per-direction sections")
        self.assertIn("**参与方向**：信号処理（dir_A）＋センサ網（dir_B）", md)
        cross_meta = [m for m in candidate_metas(md) if m.get("cross_direction")]
        self.assertEqual(len(cross_meta), 1)
        self.assertEqual(cross_meta[0]["direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(md.count("[分析](论文分析/P1.md)"), 3)
        # Cross state reuses on an unchanged rerun — zero jobs.
        plan_again = self.stage3_plan("--cross-direction-groups", self.CROSS_GROUP)
        self.assertEqual(plan_again["jobs"], [])

    def test_no_explicit_group_means_no_cross_section_and_drops_stale_group(self):
        results, cross_job = self._cross_request()
        self._write_cross_result(cross_job, [self._grounded_cross()])
        out = self.stage3_finalize(results, "--cross-direction-groups",
                                   self.CROSS_GROUP)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(len(self.load_state()["cross_direction_groups"]), 1)
        # Re-running WITHOUT the group drops the group deterministically.
        out2 = self.stage3_finalize(results)
        self.assertEqual(out2["status"], "ok")
        self.assertEqual(out2["dropped_cross_direction"],
                         [{"group_id": cross_job["group_id"],
                           "direction_ids": ["dir_A", "dir_B"],
                           "reason": "group_not_requested"}])
        self.assertEqual(self.load_state()["cross_direction_groups"], [])
        self.assertNotIn("## 跨方向想法（显式标注）", self.load_md())
        # And a run that never requested groups has no cross section at all.
        results_plain = self.write_results("s3-plain", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        self.assertEqual(self.stage3_finalize(results_plain)["status"], "ok")
        self.assertNotIn("## 跨方向想法（显式标注）", self.load_md())

    def test_cross_group_input_fail_closed(self):
        for label, raw in [("single id", '["dir_A"]'),
                           ("unknown id", '["dir_A","dir_Z"]'),
                           ("not nested lists", '["dir_A"]')]:
            with self.subTest(case=label):
                out = self.stage3_plan("--cross-direction-groups", raw)
                self.assertEqual(out["status"], "error",
                                 msg=json.dumps(out, ensure_ascii=False))
                self.assertEqual(out["reason_code"], "invalid_params")

    def test_cross_result_fail_closed_on_ungrounded_or_wrong_triple(self):
        results, cross_job = self._cross_request()
        ungrounded = self.cross_candidate("X1", ["dir_A", "dir_B"], ["P2"], ["P2"])
        ungrounded["papers"][0]["direction_ids"] = ["dir_A"]
        cases = [
            ("grounded only in A", ungrounded),
            ("B gap claimed under wrong direction",
             self.cross_candidate("X1", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                                  gap_owner={"P2": "dir_A", "P3": "dir_A"})),
        ]
        for label, cross in cases:
            with self.subTest(case=label):
                self._write_cross_result(cross_job, [cross], name="s3")
                out = self.stage3_finalize(results, "--cross-direction-groups",
                                           self.CROSS_GROUP)
                self.assertEqual(out["status"], "error",
                                 msg=json.dumps(out, ensure_ascii=False))
                self.assertEqual(out["reason_code"], "unknown_reference_id")
                self.assertFalse((self.prof_dir / "套磁候选状态.json").exists())

    def test_implicit_merge_rejected(self):
        """A per-direction candidate must never reach into another direction's slice."""
        doc = self.generated_doc("dir_A", ["P1", "P2", None])
        intruder = self.make_candidate("dir_A_4", "P3")
        intruder["gap_refs"] = []
        doc["candidates"].append(intruder)
        results = self.write_results("s3-implicit", {
            "dir_A": doc, "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_paper_id")
        self.assertFalse((self.prof_dir / "套磁候选状态.json").exists())

    def test_wrong_direction_provenance_rejected_even_when_gap_valid_elsewhere(self):
        """(P3, gap) is a VALID B reference — but cited as (dir_A, P3, gap) it
        must be rejected: the exact triple join is direction-scoped."""
        doc = self.generated_doc("dir_A", ["P1", "P2", None])
        thief = self.make_candidate("dir_A_4", None)
        thief["gap_refs"] = [{"direction_id": "dir_A", "item_key": "P3",
                              "gap_id": self.gap_ids["P3"]}]
        doc["candidates"].append(thief)
        results = self.write_results("s3-triple", {
            "dir_A": doc, "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_reference_id")

    def test_refined_mode_requires_3_5_selectable_with_user_refined(self):
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        next(d for d in pack["directions"]
             if d["direction_id"] == "dir_A")["user_note"] = "请以流式输入为主线"
        next(d for d in pack["directions"]
             if d["direction_id"] == "dir_A")["input_fingerprint"] = "refined-fp"
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        plan = self.stage3_plan()
        job_a = next(j for j in plan["jobs"] if j["direction_id"] == "dir_A")
        self.assertEqual(job_a["model_input"]["mode"], "refined")

        doc = self.generated_doc("dir_A", ["P1", "P2", None])
        doc["mode"] = "refined"
        doc["refined"] = {"core_intent": "流式输入下的自适应",
                          "calibration": [], "idea_zh": "把 P1 的方法推进到流式输入",
                          "variants": [], "mismatches": [],
                          "gap_ids": [{"item_key": "P1", "gap_id": self.gap_ids["P1"]}]}
        doc["candidates"][0]["origin"] = "user_refined"
        other = self.generated_doc("dir_B", ["P1", "P3", None])
        results_dir = self.root / "s3-refined"
        write_json(results_dir / result_file("candidates", "dir_A"), doc)
        write_json(results_dir / result_file("candidates", "dir_B"), other)
        out = self.stage3_finalize(results_dir)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        state = self.load_state()
        dir_a = next(d for d in state["directions"] if d["direction_id"] == "dir_A")
        self.assertEqual(len(dir_a["candidates"]), 3)
        self.assertEqual(sum(1 for c in dir_a["candidates"]
                             if c["origin"] == "user_refined"), 1)
        self.assertIsNotNone(dir_a["refined"])

        # Without a user_refined candidate the refined result is rejected.
        self.rewrite_pack_fingerprint("dir_A", "refined-fp-2")
        doc_bad = copy.deepcopy(doc)
        doc_bad["candidates"][0]["origin"] = "generated"
        results_bad = self.root / "s3-refined-bad"
        write_json(results_bad / result_file("candidates", "dir_A"), doc_bad)
        write_json(results_bad / result_file("candidates", "dir_B"), other)
        out_bad = self.stage3_finalize(results_bad, "--direction-id", "dir_A")
        self.assertEqual(out_bad["status"], "error")
        self.assertEqual(out_bad["reason_code"], "invalid_result_json")

    def test_skip_direction_persists_and_recovers(self):
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        plan = self.stage3_plan("--skip-direction-ids", "dir_A")
        self.assertEqual(plan["status"], "ok")
        actions = {d["direction_id"]: d["action"] for d in plan["directions"]}
        self.assertEqual(actions, {"dir_A": "skipped", "dir_B": "process"})
        self.assertEqual([j["direction_id"] for j in plan["jobs"]], ["dir_B"])
        out = self.stage3_finalize(results, "--skip-direction-ids", "dir_A")
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["skipped_direction_ids"], ["dir_A"])
        state = self.load_state()
        dir_a = next(d for d in state["directions"] if d["direction_id"] == "dir_A")
        self.assertEqual(dir_a["stage3_status"], "skipped")
        self.assertEqual(dir_a["candidates"], [])
        dir_b = next(d for d in state["directions"] if d["direction_id"] == "dir_B")
        self.assertEqual(dir_b["stage3_status"], "ready")

        # Unchanged rerun keeps B reused; A stays skipped without a job.
        plan2 = self.stage3_plan("--skip-direction-ids", "dir_A")
        self.assertEqual({d["direction_id"]: d["action"]
                          for d in plan2["directions"]},
                         {"dir_A": "skipped", "dir_B": "reuse"})
        # Dropping the skip processes A normally, then everything reuses.
        out2 = self.stage3_finalize(results)
        self.assertEqual(out2["status"], "ok")
        plan3 = self.stage3_plan()
        self.assertEqual({d["direction_id"]: d["action"]
                          for d in plan3["directions"]},
                         {"dir_A": "reuse", "dir_B": "reuse"})

    def test_participant_change_invalidates_only_cross_group(self):
        results, cross_job = self._cross_request()
        self._write_cross_result(cross_job, [self._grounded_cross()])
        out = self.stage3_finalize(results, "--cross-direction-groups",
                                   self.CROSS_GROUP)
        self.assertEqual(out["status"], "ok")

        # dir_B's evidence changed: the cross group must regenerate while
        # dir_A's own ideas stay reusable.
        self.rewrite_pack_fingerprint("dir_B", "mutated-dir-b-fingerprint")
        plan2 = self.stage3_plan("--cross-direction-groups", self.CROSS_GROUP)
        actions = {d["direction_id"]: d["action"] for d in plan2["directions"]}
        self.assertEqual(actions, {"dir_A": "reuse", "dir_B": "process"})
        self.assertEqual([j["kind"] for j in plan2["jobs"]].count("cross_direction"),
                         1)

        out2 = self.stage3_finalize(results, "--cross-direction-groups",
                                    self.CROSS_GROUP)
        self.assertEqual(out2["status"], "ok", msg=json.dumps(out2, ensure_ascii=False))
        group = self.load_state()["cross_direction_groups"][0]
        self.assertEqual(group["direction_fingerprints"]["dir_B"],
                         "mutated-dir-b-fingerprint")
        # Converged: the next unchanged run has zero jobs.
        plan3 = self.stage3_plan("--cross-direction-groups", self.CROSS_GROUP)
        self.assertEqual(plan3["jobs"], [])

    def test_stage4_selects_cross_group_and_compiles_union_email_pack(self):
        """Selecting a cross idea compiles one email entry from the
        participants' slice union — shared paper P1 keeps its single identity,
        and the email id comes from the canonical direction scope."""
        results, cross_job = self._cross_request()
        self._write_cross_result(cross_job, [self._grounded_cross()],
                                 name="s3")
        out = self.stage3_finalize(results, "--cross-direction-groups",
                                   self.CROSS_GROUP)
        self.assertEqual(out["status"], "ok")

        sel = {"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
               "direction_ids": ["dir_A", "dir_B"],
               "ideas": [{"id": "X1", "note": "主推"}]}
        out4 = self.stage4_finalize([sel])
        self.assertEqual(out4["status"], "ok", msg=json.dumps(out4, ensure_ascii=False))
        self.assertEqual(out4["emails_compiled"], 1)
        self.assertEqual(out4["skipped"], [])

        selection = self.selection_doc()
        self.assertEqual(selection["schema"], 2)
        self.assertEqual(selection["selections"][0]["direction_ids"],
                         ["dir_A", "dir_B"])

        emails = {e["email_id"]: e for e in self.email_pack()["emails"]}
        cross_email = emails[f"{PROFESSOR}::dir_A+dir_B::X1"]
        self.assertEqual(cross_email["direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual([d["direction_id"] for d in cross_email["directions"]],
                         ["dir_A", "dir_B"])
        self.assertEqual(cross_email["cross_direction"]["group_id"],
                         cross_job["group_id"])
        # Union of participant slices, deduplicated by item_key: the shared
        # paper P1 appears exactly once with its single identity.
        self.assertEqual([p["item_key"] for p in cross_email["papers"]], ["P1"])
        self.assertEqual(cross_email["papers"][0]["direction_ids"],
                         ["dir_A", "dir_B"])
        # Exact (direction_id, item_key, gap_id) join across both slices.
        self.assertEqual(
            {(g["direction_id"], g["item_key"], g["gap_id"]) for g in cross_email["gaps"]},
            {("dir_A", "P2", self.gap_ids["P2"]), ("dir_B", "P3", self.gap_ids["P3"])})
        self.assertEqual(cross_email["source_hash"], self.source_hash(cross_email))

        # A+B == B+A: the same selection written in reverse order produces the
        # identical canonical email id.
        sel_rev = dict(sel, direction_ids=["dir_B", "dir_A"])
        out4b = self.stage4_finalize([sel_rev], name="sel-input-rev.json")
        self.assertEqual(out4b["status"], "ok")
        self.assertIn(f"{PROFESSOR}::dir_A+dir_B::X1",
                      [e["email_id"] for e in self.email_pack()["emails"]])

    def test_stage4_stale_cross_participant_needs_refresh_before_write(self):
        """A changed participant fingerprint must fail the WHOLE stage-4 batch
        before any selection/email file is written."""
        results, cross_job = self._cross_request()
        self._write_cross_result(cross_job, [self._grounded_cross()],
                                 name="s3")
        self.assertEqual(self.stage3_finalize(
            results, "--cross-direction-groups", self.CROSS_GROUP)["status"], "ok")
        self.rewrite_pack_fingerprint("dir_B", "mutated-dir-b-fingerprint")
        sel = {"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
               "direction_ids": ["dir_A", "dir_B"], "ideas": [{"id": "X1"}]}
        out = self.stage4_finalize([sel])
        self.assertEqual(out["status"], "needs_refresh", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["reason_code"], "cross_participant_changed")
        self.assertFalse((self.root / "教授研究" / "套磁选择.json").exists())
        self.assertFalse((self.root / "教授研究" / "邮件输入.json").exists())

    def test_stage4_unknown_idea_fails_closed_for_whole_batch(self):
        """An unknown idea id next to a valid one must fail the whole batch
        instead of silently writing only the valid selection."""
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        self.assertEqual(self.stage3_finalize(results)["status"], "ok")
        sel = {"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
               "direction_id": "dir_A",
               "ideas": [{"id": "dir_A_1"}, {"id": "no_such_idea"}]}
        out = self.stage4_finalize([sel])
        self.assertEqual(out["status"], "error", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["reason_code"], "unknown_idea_id")
        self.assertFalse((self.root / "教授研究" / "套磁选择.json").exists())
        self.assertFalse((self.root / "教授研究" / "邮件输入.json").exists())

    def test_stage4_ordinary_selection_joins_by_direction_id(self):
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        self.assertEqual(self.stage3_finalize(results)["status"], "ok")
        # An idea from dir_B selected under dir_A's scope must be rejected —
        # candidate ids live inside one direction scope, never a global pool.
        sel = {"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
               "direction_id": "dir_A",
               "ideas": [{"id": "dir_B_1"}]}
        out = self.stage4_finalize([sel])
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_idea_id")
        sel_ok = {"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
                  "direction_id": "dir_B",
                  "ideas": [{"id": "dir_B_1"}]}
        out_ok = self.stage4_finalize([sel_ok], name="sel-ok.json")
        self.assertEqual(out_ok["status"], "ok")
        emails = self.email_pack()["emails"]
        self.assertEqual([e["email_id"] for e in emails],
                         [f"{PROFESSOR}::dir_B::dir_B_1"])
        self.assertEqual(emails[0]["direction_ids"], ["dir_B"])


if __name__ == "__main__":
    unittest.main()
