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
        actions = {row["collection_key"]: row["action"] for row in rerun["directions"]}
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
        actions = {row["collection_key"]: row["action"] for row in rerun["directions"]}
        self.assertEqual(
            actions["dir_A"],
            "process",
            "dir_A was reused even though dir_B's profile changed the cross-direction affinity/merge/addition evidence included in dir_A's resolve model_input.",
        )


if __name__ == "__main__":
    unittest.main()
