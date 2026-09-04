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

    def test_analyzer_contract_invokes_resolve_pipeline(self):
        """Issue #7: Stage 2 must resolve provisional directions against full-text
        evidence and emit authoritative resolved_direction state."""
        agent = (ROOT.parents[1] / "agents" / "professor-contact-analyzer.agent.md").read_text(
            encoding="utf-8"
        )
        # The resolve subcommand must be invoked by the analyzer.
        self.assertIn("stage2-resolve-plan", agent)
        self.assertIn("stage2-resolve-finalize", agent)
        self.assertIn("--resolved-directions", agent)
        # resolved_direction state must be propagated downstream.
        self.assertIn("resolved_direction", agent)
        self.assertIn("_resolved_directions.json", agent)
        # Material changes must trigger user confirmation.
        self.assertIn("needs_user_choice", agent)
        self.assertIn("material_changes", agent)
        # The five resolution types must be documented.
        for rtype in ("unchanged", "renamed", "split_from", "merged_into", "refined"):
            self.assertIn(rtype, agent)
        # Correction operations (add/remove) must be available.
        for op in ("papers_to_add", "papers_to_remove"):
            self.assertIn(op, agent)
        # Proposal lifecycle: a material change is proposed BEFORE the user
        # chooses, only the successful stage2-finalize application accepts it,
        # and reuse gates consume accepted entries only.
        self.assertIn("acceptance", agent)
        self.assertIn("proposed", agent)
        self.assertIn("accepted", agent)
        # Results are bound to the exact direction identity; only split_from
        # may introduce a new ID via split_target.
        self.assertIn("resolved_direction_id", agent)
        self.assertIn("split_target", agent)
        self.assertIn("invalid_result_json", agent)
        # Resolution evidence covers the professor-level candidate union, so a
        # cross-preview-cluster paper can be added from full text alone.
        self.assertIn("candidate union", agent)

    def test_skill_contract_documents_resolved_direction(self):
        """SKILL.md must document the resolved_direction contract."""
        skill = (ROOT / "SKILL.md").read_text(
            encoding="utf-8"
        )
        # resolved_direction must be referenced as the authoritative Stage 2 output.
        self.assertIn("resolved_direction", skill)
        # The proposal→acceptance lifecycle and the union evidence scope.
        self.assertIn("acceptance", skill)
        self.assertIn("proposed", skill)
        self.assertIn("candidate union", skill)


if __name__ == "__main__":
    unittest.main()
