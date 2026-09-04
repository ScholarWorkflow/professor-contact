"""Downstream invalidation regressions for authoritative Stage 2 resolutions."""
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import ResolvedPipelineMixin, parse, run_cli


class ResolvedDirectionDownstreamRegressionTests(ResolvedPipelineMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

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

        (self.prof_dir / "论文分析" / "_resolved_directions.json").unlink()
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
        second_finalize = self.run_stage2_finalize(facts_path)
        self.assertEqual(second_finalize["status"], "ok")
        direction = self.load_pack()["directions"][0]
        after = direction["input_fingerprint"]
        supporting = {p["item_key"] for p in direction["supporting_papers"]}

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
        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(payload["status"], "ok")

        by_key = {d["collection_key"]: d for d in self.load_pack()["directions"]}
        self.assertEqual(set(by_key), {"dir_A", "dir_A__control"})
        self.assertEqual(
            {p["item_key"] for p in by_key["dir_A__control"]["supporting_papers"]},
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
        first = self.run_stage2_finalize(facts_path)
        self.assertEqual(first["status"], "ok")
        first_by_key = {d["collection_key"]: d for d in self.load_pack()["directions"]}
        self.assertEqual(
            {p["item_key"] for p in first_by_key["dir_A__control"]["supporting_papers"]}, {"P2"})

        reuse_plan, reuse_finalize = self.run_resolve(facts_path, {})
        self.assertEqual(reuse_plan["jobs"], [])
        self.assertFalse(reuse_finalize["needs_user_choice"])
        second = self.run_stage2_finalize(facts_path)
        self.assertEqual(second["status"], "ok")
        second_by_key = {d["collection_key"]: d for d in self.load_pack()["directions"]}
        self.assertEqual(
            {p["item_key"] for p in second_by_key["dir_A__control"]["supporting_papers"]},
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

        second_plan = parse(run_cli("stage2-plan", "--facts", str(facts_path)))
        self.assertEqual(second_plan["directions"][0]["action"], "reuse")
        second = self.run_stage2_finalize(facts_path)
        self.assertEqual(second["status"], "ok")
        second_direction = self.load_pack()["directions"][0]
        self.assertEqual(second_direction["provisional_input_fingerprint"], provisional)

        third_plan = parse(run_cli("stage2-plan", "--facts", str(facts_path)))
        self.assertEqual(
            third_plan["directions"][0]["action"], "reuse",
            "second finalize corrupted provisional_input_fingerprint and broke Stage-2 reuse",
        )


if __name__ == "__main__":
    unittest.main()
