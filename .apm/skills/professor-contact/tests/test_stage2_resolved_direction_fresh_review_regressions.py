"""Fresh review regressions for issue #7 resolved-direction identity boundaries."""
import json
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import ResolvedPipelineMixin, parse, run_cli, write_json


class FreshResolvedDirectionReviewRegressions(ResolvedPipelineMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_cross_cluster_addition_can_cross_disjoint_candidate_sets(self):
        """Acceptance #2: a paper provisionally in B can be added to A from full text.

        Stage 1 candidate sets are per-direction and may be disjoint.  Once issue #7
        requires every unique candidate paper to have full facts, resolving A must be
        able to consider a paper that entered the selected-professor candidate union
        through B; otherwise a preview-cluster mistake can never be corrected unless
        Stage 1 happened to expand the same paper into both directions first.
        """
        papers = [
            self.make_paper(
                "P1", "Signal Processing Baseline",
                ["adaptive", "signal", "processing"], ["Future work A."]),
            self.make_paper(
                "P2", "Misclustered Full-text Signal Study",
                [
                    "adaptive", "signal", "processing", "sensor", "network",
                    "estimation", "filtering", "robustness", "dynamics",
                    "frequency", "temporal", "spectral", "multimodal",
                ],
                ["Future work B."]),
        ]
        dir_a = self.make_direction(
            "dir_A", ["P1"], name_ja="Adaptive Signal Processing",
            name_zh="自适应信号处理",
            summary=(
                "adaptive signal processing sensor network estimation filtering "
                "robustness dynamics frequency temporal spectral multimodal"
            ),
        )
        dir_b = self.make_direction(
            "dir_B", ["P2"], name_ja="Catalytic Chemistry",
            name_zh="催化化学", summary="catalytic chemistry synthesis reaction",
        )
        facts_path = self.write_facts(papers, [dir_a, dir_b])

        payload = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(payload["status"], "ok", msg=json.dumps(payload, ensure_ascii=False))
        additions = {(row["item_key"], row["target_direction"])
                     for row in payload["candidates"]["additions"]}
        self.assertIn(
            ("P2", "dir_A"), additions,
            "full-text resolution cannot repair a cross-preview miscluster when the "
            "two Stage-1 per-direction candidate sets are disjoint",
        )

    def test_resolve_finalize_rejects_result_for_wrong_collection_key(self):
        """A resolve file must be bound to the exact job/direction identity."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"],
                            ["Future work."]),
        ]
        facts_path = self.write_facts(
            papers,
            [self.make_direction("dir_A", ["P1"], name_ja="信号処理",
                                 name_zh="信号处理", summary="signal processing")],
        )
        results_dir = self.root / "wrong_identity_results"
        results_dir.mkdir()
        write_json(results_dir / "resolve-dir_A.json", {
            "schema": 1,
            "kind": "resolve",
            "collection_key": "dir_WRONG",
            "resolved": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_WRONG",
                "name_ja": "信号処理",
                "name_zh": "信号处理",
                "resolution_type": "unchanged",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        })

        payload = parse(run_cli(
            "stage2-resolve-finalize", "--facts", str(facts_path),
            "--results", str(results_dir)))
        self.assertEqual(payload["status"], "error", msg=json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["reason_code"], "invalid_result_json")

    def test_non_split_resolution_cannot_drift_resolved_id_from_collection_key(self):
        """Stage 3 uses collection_key, so non-split resolved IDs must not diverge."""
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"],
                            ["Future work."]),
        ]
        facts_path = self.write_facts(
            papers,
            [self.make_direction("dir_A", ["P1"], name_ja="信号処理",
                                 name_zh="信号处理", summary="signal processing")],
        )
        results_dir = self.root / "drifted_resolved_id_results"
        results_dir.mkdir()
        write_json(results_dir / "resolve-dir_A.json", {
            "schema": 1,
            "kind": "resolve",
            "collection_key": "dir_A",
            "resolved": {
                "resolved_direction_id": "dir_OTHER",
                "provisional_direction_id": "dir_A",
                "name_ja": "信号処理（精緻化）",
                "name_zh": "信号处理（精炼）",
                "resolution_type": "renamed",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        })

        payload = parse(run_cli(
            "stage2-resolve-finalize", "--facts", str(facts_path),
            "--results", str(results_dir)))
        self.assertEqual(payload["status"], "error", msg=json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["reason_code"], "invalid_result_json")


if __name__ == "__main__":
    unittest.main()
