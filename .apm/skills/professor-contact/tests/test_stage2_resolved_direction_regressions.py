"""Regression tests for Stage 2 resolved-direction candidate detection and reuse."""
import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"
SPEC = importlib.util.spec_from_file_location("contact_state", SCRIPT)
contact_state = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(contact_state)


class DummyContext:
    def __init__(self, direction_plans, papers=None):
        self.direction_plans = direction_plans
        self.papers = papers or {}


class ResolvedDirectionRegressionTests(unittest.TestCase):
    def test_addition_candidate_targets_strongest_non_provisional_direction(self):
        """A cross-cluster addition must point at the direction full-text evidence favors."""
        ctx = DummyContext([
            {
                "ckey": "dir_A",
                "direction": {
                    "member_keys": ["P1"],
                    "relevant_keys": ["P1"],
                    "provisional_member_keys": [],
                },
            },
            {
                "ckey": "dir_B",
                "direction": {
                    "member_keys": ["P1"],
                    "relevant_keys": ["P1"],
                    "provisional_member_keys": ["P1"],
                },
            },
        ])
        affinity = {"P1": {"dir_A": 3.5, "dir_B": 1.0}}

        additions = contact_state._detect_candidates_for_addition(ctx, affinity)

        self.assertEqual(len(additions), 1)
        self.assertEqual(additions[0]["item_key"], "P1")
        self.assertEqual(additions[0]["target_direction"], "dir_A")

    def test_merge_candidate_requires_at_least_two_shared_papers(self):
        """One shared paper is insufficient under the documented merge contract."""
        ctx = DummyContext([
            {
                "ckey": "dir_A",
                "direction": {
                    "name_ja": "信号処理",
                    "name_zh": "信号处理",
                    "summary_zh": "自适应信号处理与传感网络",
                    "member_keys": ["P1", "P2"],
                    "relevant_keys": ["P1", "P2"],
                },
            },
            {
                "ckey": "dir_B",
                "direction": {
                    "name_ja": "信号処理研究",
                    "name_zh": "信号处理研究",
                    "summary_zh": "自适应信号处理与传感网络",
                    "member_keys": ["P1", "P3"],
                    "relevant_keys": ["P1", "P3"],
                },
            },
        ])

        merges = contact_state._detect_merge_candidates(ctx)

        self.assertEqual(merges, [])

    def test_reused_direction_ignores_stale_result_file(self):
        """A cached direction must not be re-applied from a stale result file when no job was emitted."""
        direction = {
            "collection_key": "dir_A",
            "name_ja": "信号処理",
            "name_zh": "信号处理",
            "summary_zh": "信号処理の研究",
            "status": "active",
            "member_keys": ["P1"],
            "relevant_keys": ["P1"],
            "provisional_member_keys": ["P1"],
            "named_keys": [],
            "user_note": "",
        }
        papers = {
            "P1": {
                "item_key": "P1",
                "title": "Adaptive Signal Processing",
                "year": 2024,
                "month": 1,
                "authorship": "corresponding",
                "abstract": "signal processing",
                "has_pdf": False,
            }
        }
        ctx = DummyContext([{"ckey": "dir_A", "direction": direction}], papers)
        fingerprint = contact_state._per_direction_fingerprint(direction, papers)
        prior = {
            "resolved_direction_id": "dir_A",
            "provisional_direction_id": "dir_A",
            "name_ja": "信号処理",
            "name_zh": "信号处理",
            "resolution_type": "unchanged",
            "papers_to_add": [],
            "papers_to_remove": [],
            "paper_justifications": {},
            "split_target": None,
            "merge_target": None,
            "user_note": "",
            "input_fingerprint": fingerprint,
            "reused": False,
        }

        with tempfile.TemporaryDirectory() as td:
            results_dir = Path(td)
            # Simulate a fixed /tmp results directory retaining an old result from a
            # previous run. stage2-resolve-plan would emit no job for dir_A because
            # the cached fingerprint matches, so this file must be ignored.
            (results_dir / "resolve-dir_A.json").write_text(json.dumps({
                "schema": 1,
                "kind": "resolve",
                "collection_key": "dir_A",
                "resolved": {
                    "resolved_direction_id": "dir_A",
                    "provisional_direction_id": "dir_A",
                    "name_ja": "古い名前",
                    "name_zh": "旧名称",
                    "resolution_type": "renamed",
                    "papers_to_add": [],
                    "papers_to_remove": [],
                    "paper_justifications": {},
                    "split_target": None,
                    "merge_target": None,
                    "user_note": "",
                },
            }, ensure_ascii=False), encoding="utf-8")

            resolved = contact_state.validate_resolve_results(
                ctx, results_dir, reused={"dir_A": prior})

        self.assertEqual(resolved["dir_A"]["resolution_type"], "unchanged")
        self.assertTrue(resolved["dir_A"].get("reused"))
        self.assertEqual(resolved["dir_A"]["name_ja"], "信号処理")


if __name__ == "__main__":
    unittest.main()
