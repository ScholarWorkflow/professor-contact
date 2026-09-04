"""Downstream invalidation regressions for authoritative Stage 2 resolutions."""
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import ResolvedPipelineMixin


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

        # First materialize the unchanged authoritative direction and remember the
        # exact fingerprint that Stage 3 uses for reuse decisions.
        self.run_resolve(facts_path, {})
        first_finalize = self.run_stage2_finalize(facts_path)
        self.assertEqual(first_finalize["status"], "ok")
        before = self.load_pack()["directions"][0]["input_fingerprint"]

        # Force a fresh resolve over the same provisional facts, now removing P2
        # from the authoritative direction. The downstream input fingerprint must
        # change even though the provisional Stage-2 plan fingerprint did not.
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


if __name__ == "__main__":
    unittest.main()
