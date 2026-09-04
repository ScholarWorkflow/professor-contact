"""Stage 3 resolved-direction grouping regressions (issue #8).

Stage 3 must consume Stage 2 resolved directions: ideas grouped per resolved
direction with exact direction_id/item_key/gap_id references, shared papers
keeping a single paper identity, cross-direction ideas only when explicitly
labeled with all participating resolved direction IDs, and per-direction
reuse of unchanged idea state.
"""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import (
    ResolvedPipelineMixin, parse, quote_id, run_cli, write_json)

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
        self.pack_directions = {d["collection_key"]: d for d in pack["directions"]}
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

    def make_candidate(self, cid, item_key):
        candidate = {"id": cid, "title": f"候选 {cid}",
                     "one_liner": "教授的工作启发我思考延伸方向",
                     "research_question": "该方法在流式输入下是否保持相同收敛性？",
                     "points": [], "gap_ids": [], "papers": [],
                     "fit": "high", "fit_note": "", "red_lines": [],
                     "why_recommended": "兴趣契合", "tension_points": []}
        if item_key is not None:
            candidate["points"] = ["挂在缺口 1"]
            candidate["gap_ids"] = [{"item_key": item_key,
                                     "gap_id": self.gap_ids[item_key]}]
            candidate["papers"] = [{"item_key": item_key, "role": "基座",
                                    "fit_note": "教授通讯"}]
        return candidate

    def generated_doc(self, ckey, item_keys, cross=None):
        doc = {"schema": 1, "kind": "candidates", "collection_key": ckey,
               "mode": "generated", "priority": "主推 1",
               "candidates": [self.make_candidate(f"{ckey}_{n}", key)
                              for n, key in enumerate(item_keys, start=1)]}
        if cross is not None:
            doc["cross_direction_candidates"] = cross
        return doc

    def write_results(self, name, docs):
        results = self.root / name
        results.mkdir(parents=True, exist_ok=True)
        for ckey, doc in docs.items():
            write_json(results / f"candidates-{ckey}.json", doc)
        return results

    def cross_candidate(self, cid, direction_ids, gap_key, paper_keys):
        return dict(self.make_candidate(cid, gap_key),
                    direction_ids=list(direction_ids),
                    papers=[{"item_key": key, "role": "共同基座", "fit_note": "共享论文"}
                            for key in paper_keys])

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

    def rewrite_pack_fingerprint(self, ckey, fingerprint):
        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        for direction in pack["directions"]:
            if direction["collection_key"] == ckey:
                direction["input_fingerprint"] = fingerprint
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")


class Stage3DirectionGroupTests(Stage3DirectionGroupBase):

    def test_plan_groups_jobs_per_resolved_direction_with_exact_ids(self):
        plan = self.stage3_plan()
        self.assertEqual(plan["status"], "ok")
        by_key = {d["collection_key"]: d for d in plan["directions"]}
        self.assertEqual(set(by_key), {"dir_A", "dir_B"})
        self.assertEqual(by_key["dir_A"]["direction_id"], "dir_A")
        self.assertEqual(by_key["dir_B"]["direction_id"], "dir_B")
        self.assertEqual([j["collection_key"] for j in plan["jobs"]],
                         ["dir_A", "dir_B"])
        for job in plan["jobs"]:
            model_input = job["model_input"]
            self.assertEqual(model_input["direction_id"], job["collection_key"])
            known = {d["direction_id"] for d in model_input["known_directions"]}
            self.assertEqual(known, {"dir_A", "dir_B"})
            self.assertIn("cross_direction", model_input["rules"])

    def test_ideas_grouped_per_direction_share_paper_identity(self):
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))

        state = self.load_state()
        state_dirs = {d["collection_key"]: d for d in state["directions"]}
        self.assertEqual(state_dirs["dir_A"]["direction_id"], "dir_A")
        self.assertEqual(state_dirs["dir_B"]["direction_id"], "dir_B")
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
        # Direction sections carry the resolved direction ID and stay separate.
        self.assertIn("方向 ID：dir_A", md)
        self.assertIn("方向 ID：dir_B", md)
        self.assertLess(md.index("方向 ID：dir_A"), md.index("方向 ID：dir_B"))
        metas = candidate_metas(md)
        self.assertEqual({m["direction_id"] for m in metas}, {"dir_A", "dir_B"})
        # The shared paper renders the same single analysis link from BOTH
        # sections — referenced twice, duplicated never.
        self.assertEqual(md.count("[分析](论文分析/P1.md)"), 2)
        self.assertEqual(md.count("[分析](论文分析/P2.md)"), 1)
        self.assertEqual(md.count("[分析](论文分析/P3.md)"), 1)

    def test_unchanged_rerun_reuses_per_direction_idea_state(self):
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        first = self.stage3_finalize(results)
        self.assertEqual(first["status"], "ok")
        state_one = self.load_state()
        md_one = self.load_md()

        plan = self.stage3_plan()
        self.assertEqual({d["collection_key"]: d["action"]
                          for d in plan["directions"]},
                         {"dir_A": "reuse", "dir_B": "reuse"})
        self.assertEqual(plan["jobs"], [])

        second = self.stage3_finalize(results)
        self.assertEqual(second["status"], "ok")
        self.assertEqual(sorted(second["reused"]), ["dir_A", "dir_B"])
        state_two = self.load_state()
        self.assertEqual(state_two["directions"], state_one["directions"])
        self.assertEqual(self.md_body(self.load_md()), self.md_body(md_one))

    def test_cross_direction_idea_explicit_and_separated(self):
        cross = [self.cross_candidate("dir_A_X1", ["dir_A", "dir_B"], "P3",
                                      ["P1", "P3"])]
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None], cross=cross),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))

        state = self.load_state()
        cross_state = state["cross_direction"]
        self.assertEqual(len(cross_state), 1)
        entry = cross_state[0]
        self.assertEqual(entry["id"], "dir_A_X1")
        self.assertEqual(entry["direction_ids"], ["dir_A", "dir_B"])
        self.assertEqual(entry["owner_collection_key"], "dir_A")
        self.assertEqual(entry["owner_direction_id"], "dir_A")
        pack_fps = {self.pack_directions[c]["resolved_direction"]["resolved_direction_id"]:
                    self.pack_directions[c]["input_fingerprint"]
                    for c in ("dir_A", "dir_B")}
        self.assertEqual(entry["direction_fingerprints"], pack_fps)
        for direction in state["directions"]:
            self.assertNotIn("dir_A_X1", {c["id"] for c in direction["candidates"]})

        md = self.load_md()
        self.assertIn("## 跨方向想法（显式标注）", md)
        self.assertGreater(md.index("## 跨方向想法（显式标注）"),
                           md.index("方向 ID：dir_B"),
                           "cross-direction ideas must render after all per-direction sections")
        self.assertIn("**参与方向**：信号処理（dir_A）＋センサ網（dir_B）", md)
        cross_meta = [m for m in candidate_metas(md) if m.get("cross_direction")]
        self.assertEqual(len(cross_meta), 1)
        self.assertEqual(cross_meta[0]["direction_ids"], ["dir_A", "dir_B"])
        # The shared paper now appears once per direction section plus the
        # cross section — still one item_key identity everywhere.
        self.assertEqual(md.count("[分析](论文分析/P1.md)"), 3)
        # An unchanged rerun keeps both per-direction and cross state.
        plan = self.stage3_plan()
        self.assertEqual({d["collection_key"]: d["action"]
                          for d in plan["directions"]},
                         {"dir_A": "reuse", "dir_B": "reuse"})
        self.assertEqual(plan["jobs"], [])

    def test_cross_direction_fail_closed_on_implicit_or_unknown(self):
        good = {"dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
                "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])}
        cases = [
            ("single participant id",
             self.cross_candidate("X1", ["dir_A"], "P1", ["P1"])),
            ("unknown participant id",
             self.cross_candidate("X1", ["dir_A", "dir_Z"], "P1", ["P1"])),
            ("owning direction missing",
             self.cross_candidate("X1", ["dir_B", "dir_Z"], "P1", ["P1"])),
        ]
        for label, cross in cases:
            with self.subTest(case=label):
                docs = copy.deepcopy(good)
                docs["dir_A"]["cross_direction_candidates"] = [cross]
                results = self.write_results(f"s3-bad-{label.replace(' ', '-')}", docs)
                out = self.stage3_finalize(results)
                self.assertEqual(out["status"], "error",
                                 msg=json.dumps(out, ensure_ascii=False))
                self.assertEqual(out["reason_code"], "invalid_result_json")
                self.assertFalse((self.prof_dir / "套磁候选状态.json").exists())

    def test_implicit_merge_rejected(self):
        """A per-direction candidate must never reach into another direction's slice."""
        doc = self.generated_doc("dir_A", ["P1", "P2", None])
        intruder = self.make_candidate("dir_A_4", "P3")
        intruder["gap_ids"] = []
        doc["candidates"].append(intruder)
        results = self.write_results("s3-implicit", {
            "dir_A": doc, "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "unknown_paper_id")
        self.assertFalse((self.prof_dir / "套磁候选状态.json").exists())

    def test_cross_ideas_do_not_replace_per_direction_minimum(self):
        """Generated mode still needs 3-5 per-direction ideas; cross ideas are extra."""
        cross = [self.cross_candidate("dir_A_X1", ["dir_A", "dir_B"], "P3", ["P1", "P3"])]
        doc = self.generated_doc("dir_A", ["P1", "P2"], cross=cross)
        self.assertEqual(len(doc["candidates"]), 2)
        results = self.write_results("s3-short", {
            "dir_A": doc, "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["reason_code"], "invalid_result_json")

    def test_participant_change_invalidates_cross_then_recovers(self):
        cross = [self.cross_candidate("dir_A_X1", ["dir_A", "dir_B"], "P3",
                                      ["P1", "P3"])]
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None], cross=cross),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        first = self.stage3_finalize(results)
        self.assertEqual(first["status"], "ok")

        self.rewrite_pack_fingerprint("dir_B", "mutated-dir-b-fingerprint")

        # Plan fails the cross idea's freshness: the owning direction must
        # reprocess even though its own fingerprint is unchanged.
        plan = self.stage3_plan()
        actions = {d["collection_key"]: d["action"] for d in plan["directions"]}
        self.assertEqual(actions, {"dir_A": "process", "dir_B": "process"})
        self.assertNotEqual(plan["jobs"], [])

        # Finalize applies the same gate as plan, so the loop converges: both
        # owners reprocess from their results and the cross idea is re-verified
        # against the CURRENT pack before its fingerprints are re-recorded.
        out = self.stage3_finalize(results)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        entry = self.load_state()["cross_direction"][0]
        self.assertEqual(entry["direction_fingerprints"]["dir_B"],
                         "mutated-dir-b-fingerprint")
        # The recovered state reuses cleanly on the next unchanged run.
        plan_again = self.stage3_plan()
        self.assertEqual({d["collection_key"]: d["action"]
                          for d in plan_again["directions"]},
                         {"dir_A": "reuse", "dir_B": "reuse"})
        self.assertEqual(plan_again["jobs"], [])

    def test_vanished_owner_drops_cross_entries(self):
        cross = [self.cross_candidate("dir_A_X1", ["dir_A", "dir_B"], "P3",
                                      ["P1", "P3"])]
        results = self.write_results("s3", {
            "dir_A": self.generated_doc("dir_A", ["P1", "P2", None], cross=cross),
            "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])})
        first = self.stage3_finalize(results)
        self.assertEqual(first["status"], "ok")

        pack_path = self.prof_dir / "套磁候选输入.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        pack["directions"] = [d for d in pack["directions"]
                              if d["collection_key"] != "dir_A"]
        pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

        out = self.stage3_finalize(results, "--collection-key", "dir_B")
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["dropped_cross_direction"], ["dir_A_X1"])
        self.assertEqual(self.load_state()["cross_direction"], [])


if __name__ == "__main__":
    unittest.main()
