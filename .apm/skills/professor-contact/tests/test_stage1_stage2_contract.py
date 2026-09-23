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
        agent = (ROOT.parents[2] / "packages" / "professor-contact-opencode" / ".apm" / "agents" / "professor-contact-analyzer.agent.md").read_text(
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
        agent = (ROOT.parents[2] / "packages" / "professor-contact-opencode" / ".apm" / "agents" / "professor-contact-analyzer.agent.md").read_text(
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


class Stage2PreflightContractTests(unittest.TestCase):
    """Issue #11 contracts: the early preflight gate sits between Stage 1
    verify and every expensive Stage 2 step, and reuse_all is a true no-op.
    """

    def test_analyzer_contract_orders_preflight_before_zotero_and_reads(self):
        agent = (ROOT.parents[2] / "packages" / "professor-contact-opencode" / ".apm" / "agents" / "professor-contact-analyzer.agent.md").read_text(
            encoding="utf-8"
        )
        resolve = agent.index("### Step 2 — Deterministic target resolver")
        verify = agent.index("### Step 2.5 — Verify + consume the Stage 1 candidate snapshot")
        preflight = agent.index("### Step 2.6 — Stage 2 early preflight gate")
        zotero = agent.index("### Step 2.7 — Zotero connectivity")
        reads = agent.index("### Step 3 — Read candidate-set direction papers")
        # Fixed order: resolve < Stage 1 verify < preflight < Zotero probe/session
        # < candidate paper reads. A refactor must never move the Zotero probe
        # (or any read) back in front of the preflight gate.
        self.assertLess(resolve, verify)
        self.assertLess(verify, preflight)
        self.assertLess(preflight, zotero)
        self.assertLess(zotero, reads)
        # The Zotero probe step is explicitly gated on process professors.
        gate_section = agent[preflight:reads]
        self.assertIn("仅当 `process_professors` 非空", gate_section)

    def test_analyzer_contract_reuse_all_is_a_no_op(self):
        agent = (ROOT.parents[2] / "packages" / "professor-contact-opencode" / ".apm" / "agents" / "professor-contact-analyzer.agent.md").read_text(
            encoding="utf-8"
        )
        preflight = agent.index("### Step 2.6 — Stage 2 early preflight gate")
        reads = agent.index("### Step 3 — Read candidate-set direction papers")
        gate_section = agent[preflight:reads]
        # reuse_all forbids every expensive action for that professor.
        for forbidden in ("get_item_details", "get_item_abstract", "get_content",
                          "OCR", "paper-analysis full|gap-only",
                          "stage2_chatgpt_handoff build", "Stage 2 模型 job",
                          "stage2-plan", "stage2-finalize", "style validator"):
            self.assertIn(forbidden, gate_section)
        self.assertIn("no-op reuse", gate_section)
        self.assertIn("不 rewrite pack", gate_section)
        # The preflight command itself is local-only.
        self.assertIn("不碰 Zotero", gate_section)
        self.assertIn("不读 PDF 内容", gate_section)
        self.assertIn("不写任何 workflow state", gate_section)
        # Preflight stdout is saved and passed back to finalize.
        self.assertIn("/tmp/<教授名>_stage2_preflight.json", gate_section)
        self.assertIn("--preflight-file", agent)
        self.assertIn("preflight_inputs_changed", agent)

    def test_analyzer_contract_documents_no_early_exit_cases(self):
        agent = (ROOT.parents[2] / "packages" / "professor-contact-opencode" / ".apm" / "agents" / "professor-contact-analyzer.agent.md").read_text(
            encoding="utf-8"
        )
        preflight = agent.index("### Step 2.6 — Stage 2 early preflight gate")
        reads = agent.index("### Step 3 — Read candidate-set direction papers")
        gate_section = agent[preflight:reads]
        # An explicitly provided chatgpt_result must never be ignored, and
        # kb_import=true is an explicit external side effect.
        self.assertIn("chatgpt_result", gate_section)
        self.assertIn("kb_import=true", gate_section)
        self.assertIn("禁止 early hard exit", gate_section)
        # Partial miss never stitches preflight reuse back into results.
        self.assertIn("partial miss", gate_section.lower())
        self.assertIn("stage2-plan", gate_section)
        # Handoff compatibility: reuse_all with zero jobs builds no ZIP.
        self.assertIn("不生成新 handoff ZIP", gate_section)

    def test_analyzer_contract_pins_initialization_hard_rule(self):
        agent = (ROOT.parents[2] / "packages" / "professor-contact-opencode" / ".apm" / "agents" / "professor-contact-analyzer.agent.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Stage 2 初始化顺序固定且 preflight gate 不可绕过", agent)
        self.assertIn("resolve → `contact_targets.py resolve` → `contact_stage1.py verify` → "
                      "逐教授 `contact_state.py stage2-preflight`", agent)
        self.assertIn("correctness-preserving", agent)
        self.assertIn("绝不生成新的科学事实", agent)

    def test_skill_contract_documents_the_preflight_gate(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("stage2-preflight", skill)
        self.assertIn("reuse_all", skill)
        self.assertIn("cache.preflight", skill)
        self.assertIn("preflight_inputs_changed", skill)
        self.assertIn("correctness-preserving", skill)
        self.assertIn("绝不为 cache 检查重读 PDF bytes", skill)
        self.assertIn("--preflight-file", skill)
        # Stage 3 stays the only consumer of directions[]; preflight is cache.
        self.assertIn("仅 cache，Stage 3 不读取", skill)

    def test_analyzer_contract_binds_facts_to_the_preflight_proof(self):
        agent = (ROOT.parents[2] / "packages" / "professor-contact-opencode" / ".apm" / "agents" / "professor-contact-analyzer.agent.md").read_text(
            encoding="utf-8"
        )
        # Step 6.1 carries the saved proof id into the facts JSON...
        self.assertIn('"stage2_preflight": {"preflight_id"', agent)
        facts_section = agent[agent.index("6.1 采集 facts JSON"):
                              agent.index("6.3 跑 `stage2-finalize`")]
        self.assertIn("preflight_id", facts_section)
        # ...and finalize verifies the binding before any write.
        finalize_section = agent[agent.index("6.3 跑 `stage2-finalize`"):]
        self.assertIn("preflight_proof_id", finalize_section)
        self.assertIn("preflight_proof_binding", finalize_section)
        self.assertIn("任何写盘之前", finalize_section)
        # The gate documents fail-closed handling for malformed cache shapes.
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("preflight_cache_malformed", skill)
        self.assertIn("preflight_record_missing", skill)
        self.assertIn("stage2_preflight.preflight_id", skill)


if __name__ == "__main__":
    unittest.main()
