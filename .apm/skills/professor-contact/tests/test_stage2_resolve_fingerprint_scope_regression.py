"""Regression tests for Stage-2 resolved-direction fingerprint scope."""
import json
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import ResolvedPipelineMixin, parse, run_cli


class ResolveFingerprintScopeRegression(ResolvedPipelineMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_analysis_markdown_edit_does_not_invalidate_resolved_direction_when_facts_unchanged(self):
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"], ["Future work A."]),
            self.make_paper("P2", "Catalytic Chemistry", ["catalytic", "chemistry"], ["Future work B."]),
        ]
        directions = [
            self.make_direction("dir_A", ["P1"], name_ja="Signal Processing", name_zh="信号处理", summary="signal processing"),
            self.make_direction("dir_B", ["P2"], name_ja="Catalytic Chemistry", name_zh="催化化学", summary="catalytic chemistry"),
        ]
        facts_path = self.write_facts(papers, directions)

        unchanged = {}
        for ckey, ja, zh in (("dir_A", "Signal Processing", "信号处理"),
                             ("dir_B", "Catalytic Chemistry", "催化化学")):
            unchanged[ckey] = {
                "resolved_direction_id": ckey,
                "provisional_direction_id": ckey,
                "name_ja": ja,
                "name_zh": zh,
                "resolution_type": "unchanged",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            }
        self.run_resolve(facts_path, unchanged)

        analysis = Path(papers[1]["analysis_file"])
        analysis.write_text(analysis.read_text(encoding="utf-8") + "\nEditorial note only.\n", encoding="utf-8")

        rerun = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(rerun["status"], "ok", msg=json.dumps(rerun, ensure_ascii=False))
        actions = {row["direction_id"]: row["action"] for row in rerun["directions"]}
        self.assertEqual(
            actions,
            {"dir_A": "reuse", "dir_B": "reuse"},
            "Editing analysis Markdown without changing the full-text facts consumed by resolution should not trigger new resolve jobs.",
        )

    def test_other_direction_profile_change_invalidates_target_resolution(self):
        """A cached direction must invalidate when another profile changes its model_input.

        Every resolve job receives paper_evidence.affinity_scores for ALL selected
        directions and merge/addition candidates computed across those directions.
        Therefore changing dir_B's profile changes the actual model_input for dir_A
        even when no paper facts changed. Reusing dir_A would be stale.
        """
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"], ["Future work A."]),
            self.make_paper("P2", "Catalytic Chemistry", ["catalytic", "chemistry"], ["Future work B."]),
        ]
        directions = [
            self.make_direction("dir_A", ["P1"], name_ja="Signal Processing", name_zh="信号处理", summary="signal processing"),
            self.make_direction("dir_B", ["P2"], name_ja="Catalytic Chemistry", name_zh="催化化学", summary="catalytic chemistry"),
        ]
        facts_path = self.write_facts(papers, directions)

        unchanged = {}
        for ckey, ja, zh in (("dir_A", "Signal Processing", "信号处理"),
                             ("dir_B", "Catalytic Chemistry", "催化化学")):
            unchanged[ckey] = {
                "resolved_direction_id": ckey,
                "provisional_direction_id": ckey,
                "name_ja": ja,
                "name_zh": zh,
                "resolution_type": "unchanged",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            }
        self.run_resolve(facts_path, unchanged)

        payload = json.loads(facts_path.read_text(encoding="utf-8"))
        by_key = {d["collection_key"]: d for d in payload["directions"]}
        by_key["dir_B"]["name_ja"] = "Signal Processing Applications"
        by_key["dir_B"]["name_zh"] = "信号处理应用"
        by_key["dir_B"]["summary_zh"] = "signal processing adaptive filtering sensor network"
        facts_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

        rerun = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(rerun["status"], "ok", msg=json.dumps(rerun, ensure_ascii=False))
        actions = {row["direction_id"]: row["action"] for row in rerun["directions"]}
        self.assertEqual(
            actions["dir_A"],
            "process",
            "dir_A was reused even though dir_B's profile changed the cross-direction affinity/merge/addition evidence included in dir_A's resolve model_input.",
        )

    def test_cross_direction_facts_validity_change_invalidates_target_resolution(self):
        """Union paper evidence validity is a dependency even when its sidecar belongs to B.

        facts_for(P2) validates exact future_work_ids against P2's current future-work
        sidecar. Every direction's paper_evidence exposes P2 facts_state/facts_error,
        so breaking that join changes dir_A's actual model_input and can remove the
        evidence needed for a cross-cluster addition. dir_A must not reuse stale state.
        """
        papers = [
            self.make_paper("P1", "Adaptive Signal Processing", ["signal", "processing"], ["Future work A."]),
            self.make_paper("P2", "Catalytic Chemistry", ["catalytic", "chemistry"], ["Future work B."]),
        ]
        directions = [
            self.make_direction("dir_A", ["P1"], name_ja="Signal Processing", name_zh="信号处理", summary="signal processing"),
            self.make_direction("dir_B", ["P2"], name_ja="Catalytic Chemistry", name_zh="催化化学", summary="catalytic chemistry"),
        ]
        facts_path = self.write_facts(papers, directions)

        unchanged = {}
        for ckey, ja, zh in (("dir_A", "Signal Processing", "信号处理"),
                             ("dir_B", "Catalytic Chemistry", "催化化学")):
            unchanged[ckey] = {
                "resolved_direction_id": ckey,
                "provisional_direction_id": ckey,
                "name_ja": ja,
                "name_zh": zh,
                "resolution_type": "unchanged",
                "papers_to_add": [],
                "papers_to_remove": [],
                "paper_justifications": {},
                "split_target": None,
                "merge_target": None,
                "user_note": "",
            }
        self.run_resolve(facts_path, unchanged)

        p2_sidecar = Path(papers[1]["sidecar_file"])
        sidecar_payload = json.loads(p2_sidecar.read_text(encoding="utf-8"))
        sidecar_payload["items"] = []
        p2_sidecar.write_text(json.dumps(sidecar_payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

        rerun = parse(run_cli("stage2-resolve-plan", "--facts", str(facts_path)))
        self.assertEqual(rerun["status"], "ok", msg=json.dumps(rerun, ensure_ascii=False))
        actions = {row["direction_id"]: row["action"] for row in rerun["directions"]}
        self.assertEqual(
            actions["dir_A"],
            "process",
            "dir_A was reused even though P2's future-work sidecar broke the full-text facts evidence chain and changed P2 facts_state in dir_A's paper_evidence.",
        )


if __name__ == "__main__":
    unittest.main()
