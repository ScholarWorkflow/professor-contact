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

        Stage 1 candidate sets are per-direction and may be disjoint. Once issue #7
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

    def test_cross_direction_facts_change_invalidates_target_resolution(self):
        """A target direction must invalidate when another direction's candidate facts change.

        Resolution jobs score every selected candidate against every selected direction.
        Therefore dir_A's cached result depends on P2 even when P2 only entered the
        professor-level union through dir_B. If P2's full-text facts later change so it
        now belongs to A, reusing A would freeze the old membership and suppress the
        cross-cluster repair that issue #7 is meant to enable.
        """
        papers = [
            self.make_paper(
                "P1", "Signal Processing Baseline",
                ["adaptive", "signal", "processing"], ["Future work A."]),
            self.make_paper(
                "P2", "Catalytic Chemistry Study",
                ["catalytic", "chemistry", "synthesis"], ["Future work B."]),
        ]
        dir_a = self.make_direction(
            "dir_A", ["P1"], name_ja="Adaptive Signal Processing",
            name_zh="自适应信号处理",
            summary="adaptive signal processing sensor network estimation filtering",
        )
        dir_b = self.make_direction(
            "dir_B", ["P2"], name_ja="Catalytic Chemistry",
            name_zh="催化化学", summary="catalytic chemistry synthesis reaction",
        )
        facts_path = self.write_facts(papers, [dir_a, dir_b])

        self.run_resolve(facts_path, {
            "dir_A": {
                "resolved_direction_id": "dir_A",
                "provisional_direction_id": "dir_A",
                "name_ja": "Adaptive Signal Processing",
                "name_zh": "自适应信号处理",
                "resolution_type": "unchanged",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
            "dir_B": {
                "resolved_direction_id": "dir_B",
                "provisional_direction_id": "dir_B",
                "name_ja": "Catalytic Chemistry",
                "name_zh": "催化化学",
                "resolution_type": "unchanged",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            },
        })

        p2_facts = Path(papers[1]["facts_file"])
        payload = json.loads(p2_facts.read_text(encoding="utf-8"))
        payload["topic_terms"] = [
            "adaptive", "signal", "processing", "sensor", "network",
            "estimation", "filtering", "robustness",
        ]
        p2_facts.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

        rerun = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(rerun["status"], "ok", msg=json.dumps(rerun, ensure_ascii=False))
        actions = {row["direction_id"]: row["action"] for row in rerun["directions"]}
        self.assertEqual(
            actions["dir_A"], "process",
            "dir_A resolution was reused even though a cross-direction candidate's "
            "full-text facts changed and can now alter dir_A membership",
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

    def test_new_material_resolution_is_not_reused_before_user_acceptance(self):
        """A pending material change must not become accepted merely by being written.

        stage2-resolve-finalize currently writes the authoritative sidecar before the
        analyzer asks the user whether to adopt the refined direction. A later plan
        must therefore distinguish pending from accepted state; otherwise a crash,
        deferred answer, or explicit provisional fallback turns the unaccepted
        proposal into a cache hit and suppresses the promised re-prompt.
        """
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"],
                            ["Future work A."]),
            self.make_paper("P2", "Kitchen Chemistry", ["chemistry", "kitchen"],
                            ["Future work B."]),
        ]
        facts_path = self.write_facts(
            papers,
            [self.make_direction("dir_A", ["P1", "P2"], name_ja="信号処理",
                                 name_zh="信号处理", summary="signal processing")],
        )
        _, first_finalize = self.run_resolve(facts_path, {
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
        self.assertTrue(first_finalize["needs_user_choice"])

        rerun_plan = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(rerun_plan["status"], "ok")
        self.assertNotEqual(
            rerun_plan["directions"][0]["action"], "reuse",
            "a just-proposed material resolution was cached as accepted before the "
            "user made the required Stage-2 choice",
        )


if __name__ == "__main__":
    unittest.main()
