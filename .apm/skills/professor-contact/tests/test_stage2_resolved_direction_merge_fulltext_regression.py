"""Regression for issue #7: full-text evidence must be able to merge disjoint preview clusters."""
import json
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import ResolvedPipelineMixin, parse, run_cli


class FullTextMergeRegression(ResolvedPipelineMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_disjoint_preview_clusters_can_be_merge_candidates_from_fulltext(self):
        """Two disjoint preview clusters can still be the same full-text research line.

        Issue #7 allows provisional directions to merge when full-text evidence shows
        they are the same line. Requiring shared paper IDs makes that impossible for
        the common case where preview clusters are disjoint even though their papers'
        full-text topic facts converge on the same research line.
        """
        common_terms = [
            "adaptive", "signal", "processing", "sensor", "network",
            "estimation", "robust", "filtering",
        ]
        papers = [
            self.make_paper("P1", "Adaptive Filtering I", common_terms, ["Future A1."]),
            self.make_paper("P2", "Adaptive Filtering II", common_terms, ["Future A2."]),
            self.make_paper("P3", "Robust Sensor Estimation I", common_terms, ["Future B1."]),
            self.make_paper("P4", "Robust Sensor Estimation II", common_terms, ["Future B2."]),
        ]
        dir_a = self.make_direction(
            "dir_A", ["P1", "P2"],
            name_ja="Adaptive Signal Processing",
            name_zh="自适应信号处理",
            summary="adaptive signal processing sensor estimation robust filtering",
        )
        dir_b = self.make_direction(
            "dir_B", ["P3", "P4"],
            name_ja="Robust Signal Processing",
            name_zh="稳健信号处理",
            summary="robust signal processing sensor estimation adaptive filtering",
        )
        facts_path = self.write_facts(papers, [dir_a, dir_b])

        payload = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(payload["status"], "ok", msg=json.dumps(payload, ensure_ascii=False))
        merge_pairs = {
            frozenset((row["direction_a"], row["direction_b"]))
            for row in payload["candidates"]["merges"]
        }
        self.assertIn(
            frozenset(("dir_A", "dir_B")),
            merge_pairs,
            "full-text-equivalent directions cannot merge unless their provisional "
            "candidate sets already share >=2 paper IDs",
        )


if __name__ == "__main__":
    unittest.main()
