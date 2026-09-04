"""Regression tests for the Stage-2 resolved-direction user-acceptance boundary.

A material resolve result is only a proposal until the user explicitly adopts it.
The deterministic Stage-2 finalizer must never turn a proposed direction into the
Stage-3 fact source merely because a caller passed the sidecar path.
"""
import json
import tempfile
import unittest
from pathlib import Path

from test_stage2_resolved_direction import ResolvedPipelineMixin, parse, run_cli


class ResolvedDirectionAcceptanceBoundaryTests(ResolvedPipelineMixin, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof_dir = self.root / "教授研究" / "X分野" / "試験 教授"
        (self.prof_dir / "论文分析").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _refined(self, ckey, remove_key):
        return {
            "resolved_direction_id": ckey,
            "provisional_direction_id": ckey,
            "name_ja": f"{ckey} refined",
            "name_zh": f"{ckey} 修正",
            "resolution_type": "refined",
            "papers_to_add": [],
            "papers_to_remove": [remove_key],
            "paper_justifications": {remove_key: "full-text topic mismatch"},
            "split_target": None,
            "merge_target": None,
            "user_note": "",
        }

    def test_stage2_finalize_rejects_unaccepted_material_proposal(self):
        """Passing a proposed sidecar must not itself count as user acceptance."""
        papers = [
            self.make_paper("P1", "Signal Paper", ["signal", "processing"], ["Future A."]),
            self.make_paper("P2", "Chemistry Paper", ["chemistry", "catalyst"], ["Future B."]),
        ]
        facts_path = self.write_facts(
            papers,
            [self.make_direction(
                "dir_A", ["P1", "P2"], name_ja="Signal Processing",
                name_zh="信号处理", summary="signal processing")],
        )

        _, resolve_finalize = self.run_resolve(
            facts_path, {"dir_A": self._refined("dir_A", "P2")})
        self.assertTrue(resolve_finalize["needs_user_choice"])

        sidecar = json.loads(
            (self.prof_dir / "论文分析" / "_resolved_directions.json").read_text(encoding="utf-8"))
        self.assertEqual(sidecar["directions"][0]["acceptance"], "proposed")

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(
            payload["status"], "error",
            "stage2-finalize applied a material proposal before an explicit user-adopt transition",
        )
        self.assertFalse(
            (self.prof_dir / "套磁候选输入.json").exists(),
            "an unaccepted proposal leaked into the Stage-3 fact source",
        )
        sidecar_after = json.loads(
            (self.prof_dir / "论文分析" / "_resolved_directions.json").read_text(encoding="utf-8"))
        self.assertEqual(
            sidecar_after["directions"][0]["acceptance"], "proposed",
            "stage2-finalize silently promoted the proposal to accepted",
        )

    def test_partial_keep_provisional_does_not_accept_other_pending_direction(self):
        """Keeping A provisional must not silently adopt B's still-pending proposal."""
        papers = [
            self.make_paper("A1", "Signal Baseline", ["signal", "processing"], ["Future A1."]),
            self.make_paper("A2", "Chemistry Intruder", ["chemistry", "catalyst"], ["Future A2."]),
            self.make_paper("B1", "Control Baseline", ["control", "robust"], ["Future B1."]),
            self.make_paper("B2", "Vision Intruder", ["vision", "image"], ["Future B2."]),
        ]
        facts_path = self.write_facts(
            papers,
            [
                self.make_direction(
                    "dir_A", ["A1", "A2"], name_ja="Signal Processing",
                    name_zh="信号处理", summary="signal processing"),
                self.make_direction(
                    "dir_B", ["B1", "B2"], name_ja="Robust Control",
                    name_zh="鲁棒控制", summary="robust control"),
            ],
        )
        _, resolve_finalize = self.run_resolve(
            facts_path,
            {
                "dir_A": self._refined("dir_A", "A2"),
                "dir_B": self._refined("dir_B", "B2"),
            },
        )
        self.assertTrue(resolve_finalize["needs_user_choice"])

        empty_results = self.root / "keep_results"
        empty_results.mkdir()
        keep_payload = parse(run_cli(
            "stage2-resolve-finalize",
            "--facts", str(facts_path),
            "--results", str(empty_results),
            "--keep-provisional", "dir_A",
        ))
        self.assertEqual(keep_payload["status"], "ok", msg=json.dumps(keep_payload, ensure_ascii=False))

        sidecar_path = self.prof_dir / "论文分析" / "_resolved_directions.json"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        by_id = {row["provisional_direction_id"]: row for row in sidecar["directions"]}
        self.assertEqual(by_id["dir_A"]["acceptance"], "accepted")
        self.assertEqual(by_id["dir_A"].get("decision"), "user_kept_provisional")
        self.assertEqual(by_id["dir_B"]["acceptance"], "proposed")

        payload = self.run_stage2_finalize(facts_path)
        self.assertEqual(
            payload["status"], "error",
            "stage2-finalize accepted dir_B even though only dir_A received a user decision",
        )
        sidecar_after = json.loads(sidecar_path.read_text(encoding="utf-8"))
        by_id_after = {row["provisional_direction_id"]: row for row in sidecar_after["directions"]}
        self.assertEqual(
            by_id_after["dir_B"]["acceptance"], "proposed",
            "a pending direction was silently promoted while applying another direction's decision",
        )


if __name__ == "__main__":
    unittest.main()
