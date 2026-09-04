"""Regression tests for Stage 2 resolved-direction candidate detection."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"
SPEC = importlib.util.spec_from_file_location("contact_state", SCRIPT)
contact_state = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(contact_state)


class DummyContext:
    def __init__(self, direction_plans):
        self.direction_plans = direction_plans


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


if __name__ == "__main__":
    unittest.main()
