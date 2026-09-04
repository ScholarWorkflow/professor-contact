import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class Stage1Stage2ContractTests(unittest.TestCase):
    """Integration contracts for the Stage 1 → Stage 2 candidate chain.

    Locks the review requirements that go beyond the Stage 1 builder itself:
    Stage 2 must verify and consume the Stage 1 candidate snapshot instead of
    reading only provisional target-state members.
    """

    def test_analyzer_contract_consumes_stage1_candidate_snapshot(self):
        agent = (ROOT.parents[1] / "agents" / "professor-contact-analyzer.agent.md").read_text(
            encoding="utf-8"
        )
        # Stage 2 verifies the Stage 1 snapshot and reads candidate_keys as the
        # reading/relevance/analysis universe.
        self.assertIn("contact_stage1.py", agent)
        self.assertIn("verify --program-root", agent)
        self.assertIn("candidate_keys", agent)
        self.assertIn("missing_stage1_snapshot", agent)
        self.assertIn("stale_stage1_snapshot", agent)
        self.assertIn("needs_input", agent)
        # Expansion stays non-final: credibility gate on provisional members only.
        self.assertIn("non_final_candidates_only", agent)
        self.assertIn("provisional members", agent)
        self.assertIn("expansion_reasons", agent)
        # Stage 1 user_named candidates get an entry ticket like note-named papers.
        self.assertIn("user_named", agent)
        # gap pool wiring: selected_direction scope works off the candidate universe.
        self.assertIn("member_keys", agent)
        self.assertIn("provisional_member_keys", agent)
        # Old scope wording must be gone: Stage 2 no longer reads bare membership.
        self.assertNotIn("reads member papers from target-state membership", agent)
        self.assertNotIn("成员 item_keys 直接取 target state 的", agent)

    def test_skill_contract_documents_the_candidate_chain(self):
        skill = (ROOT / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("套磁阶段1候选.json", skill)
        self.assertIn("contact_stage1.py verify", skill)
        self.assertIn("补下后刷新快照", skill)
        self.assertIn("needs_resolution", skill)
        self.assertIn("candidate_keys", skill)
        self.assertIn("non_final_candidates_only", skill)


if __name__ == "__main__":
    unittest.main()
