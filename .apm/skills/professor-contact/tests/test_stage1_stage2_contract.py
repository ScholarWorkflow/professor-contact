import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Analyzer commands whose input is the Stage-0 target of exactly one professor.
TARGET_BOUND_COMMANDS = ("scripts/contact_targets", "scripts/contact_stage1", "stage2-preflight")
RETIRED_PROGRAM_TABLE = "教授研究/套磁目标.json"
PROHIBITION_MARKERS = ("绝不", "不读", "退役", "migrate")


def bash_commands(text: str) -> list[str]:
    """Every ```bash fenced command, joined across backslash continuations."""
    commands = []
    for block in re.findall(r"```bash\n(.*?)```", text, flags=re.S):
        for chunk in re.split(r"\n\s*\n", block):
            command = " ".join(line.rstrip("\\").strip() for line in chunk.splitlines())
            if command.strip():
                commands.append(command)
    return commands


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


class Stage2ScopeContractTests(unittest.TestCase):
    """PC-S2-SCOPE-1: relevance/top-N never truncates candidate full analysis."""

    def _analyzers(self):
        for target in ("professor-contact-codex", "professor-contact-opencode"):
            path = (ROOT.parents[2] / "packages" / target / ".apm" / "agents"
                    / "professor-contact-analyzer.agent.md")
            yield target, path.read_text(encoding="utf-8")

    def test_analyzer_input_separates_post_scope_from_full_analysis(self):
        for target, agent in self._analyzers():
            with self.subTest(target=target):
                inputs = agent.split("## Input\n", 1)[1].split("\n## ", 1)[0]
                paper = next(line for line in inputs.splitlines()
                             if line.startswith("- `paper_analysis` "))
                cap = next(line for line in inputs.splitlines()
                           if line.startswith("- `max_relevant_papers` "))
                for token in ("历史保留名称", "`relevant`", "缺省", "`all`",
                              "全部候选视作相关", "gap / future-work 补齐与叙事后处理",
                              "两种模式下 full `paper-analysis` 都固定覆盖",
                              "selected directions", "`candidate_keys` 去重并集",
                              "不得被本参数截断", "复用有效 full analysis",
                              "否则恰好补一次 full pass"):
                    self.assertIn(token, paper)
                for token in ("只限制", "gap / future-work 补齐与叙事后处理",
                              "非点名相关论文数", "不限制 candidate union 的 full-analysis job 数",
                              "user_note", "`user_named`", "永不因该值被截断"):
                    self.assertIn(token, cap)
                for stale in ("只跑**相关论文**", "方向全部成员论文，强制全量",
                              "补哪些论文的分析"):
                    self.assertNotIn(stale, paper)

    def test_analyzer_cost_gate_discloses_untruncated_full_analysis_cost(self):
        for target, agent in self._analyzers():
            with self.subTest(target=target):
                gate = agent.split("4. **成本门", 1)[1].split("\n4.5 ", 1)[0]
                for token in ("max_relevant_papers=N", "前 N 篇非点名相关论文",
                              "相关证据集共有 N 篇", "全部纳入 gap/叙事后处理",
                              "仅排序前 10 进入 gap/叙事后处理", "无论选择哪项",
                              "candidate union 内缺失/stale 的 full `paper-analysis` 仍照常补齐",
                              "去重后实际需补 M 篇", "约 4M 次代理调用", "OCR 耗时另计",
                              "user_note 点名与 Stage 1 `user_named` 论文仍豁免截断"):
                    self.assertIn(token, gate)
                for stale in ("全量跑 N 篇", "只跑前 10", "约 4N 次代理"):
                    self.assertNotIn(stale, gate)

    def test_caller_contract_keeps_full_analysis_independent_of_post_scope(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        inputs = skill.split("### Input contract（公共字段）\n", 1)[1].split("\n##", 1)[0]
        paper = next(line for line in inputs.splitlines()
                     if line.startswith("| `paper_analysis` |"))
        behavior = skill.split("## Behavior notes for callers\n", 1)[1].split("\n## ", 1)[0]
        independent = next(line for line in behavior.splitlines()
                           if line.startswith("- **每阶段独立跑、可中断**"))
        for token in ("历史保留名称", "`relevant`", "缺省", "`all`", "全部候选视作相关",
                      "不受 `paper_analysis` 或 `max_relevant_papers` / relevant top-N 截断",
                      "user_note 点名与 Stage 1 `user_named` 仍豁免截断"):
            self.assertIn(token, paper)
        for section in (paper, independent):
            for token in ("full `paper-analysis`", "固定覆盖", "selected directions",
                          "`candidate_keys` 去重并集", "gap / future-work 补齐与叙事后处理",
                          "相关集 >10 篇且未显式限额"):
                self.assertIn(token, section)
            for stale in ("只跑相关论文", "只跑**相关论文**", "方向全部成员论文，强制全量"):
                self.assertNotIn(stale, section)
        self.assertIn("不减少 full-analysis 范围或 job 数", independent)


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
        # Preflight stdout is saved and passed back to finalize, at this
        # professor transaction's own transient location.
        self.assertIn("<本教授事务临时目录>/stage2_preflight.json", gate_section)
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
        self.assertIn("resolve → 逐教授 `contact_targets.py resolve --target-file", agent)
        self.assertIn("`contact_stage1.py verify --target-file`", agent)
        self.assertIn("逐教授 `contact_state.py stage2-preflight --target-file`", agent)
        self.assertIn("correctness-preserving", agent)
        self.assertIn("绝不生成新的科学事实", agent)

    def test_issue64_t7_both_projections_pass_the_local_target_explicitly(self):
        """G64-T4/T7 support (R64-17): analyzer input and handoff stay professor-local.

        Every target-bound analyzer command names one professor's own local
        target, and the returned handoff carries the professor's
        target_states / stage1_snapshots maps — requirement r2 permits the
        name-keyed outer shape in the unique-name scope, and the retired
        program-level paths stay excluded (C65-03 owns that proof).
        """
        for target in ("professor-contact-codex", "professor-contact-opencode"):
            with self.subTest(target=target):
                agent = self._analyzer(target)
                bound = [command for command in bash_commands(agent)
                         if any(name in command for name in TARGET_BOUND_COMMANDS)]
                self.assertTrue(bound, msg=target)
                for command in bound:
                    self.assertIn("--target-file", command, msg=command)
                self.assertIn('"target_states": {', agent)
                self.assertIn('"stage1_snapshots": {', agent)
                self.assertNotIn('"transactions": [', agent)

    def test_issue64_t7_program_level_table_is_only_a_prohibition(self):
        """R64-5 (G64-T7): neither analyzer reads or reconstructs the retired table."""
        for target in ("professor-contact-codex", "professor-contact-opencode"):
            with self.subTest(target=target):
                agent = self._analyzer(target)
                mentioned = [line for line in agent.splitlines()
                             if RETIRED_PROGRAM_TABLE in line]
                self.assertTrue(mentioned, msg=target)
                for line in mentioned:
                    self.assertTrue(
                        any(marker in line for marker in PROHIBITION_MARKERS),
                        msg=line,
                    )
                self.assertIn("不自行推导路径", agent)

    def test_issue64_t7_stage2_plan_commands_pass_the_saved_preflight_proof(self):
        """The production plan hop consumes the proof saved by Step 2.6."""
        expected_proof = "--preflight-file <本教授事务临时目录>/stage2_preflight.json"
        for target in ("professor-contact-codex", "professor-contact-opencode"):
            with self.subTest(target=target):
                commands = [command for command in bash_commands(self._analyzer(target))
                            if "scripts/contact_state stage2-plan" in command]
                self.assertEqual(len(commands), 1, msg=commands)
                self.assertIn("--facts /tmp/<教授名>_套磁_facts.json", commands[0])
                self.assertIn(expected_proof, commands[0])

    def test_issue64_t7_preflight_proof_save_is_per_professor_transaction(self):
        """R64-17/R64-20 supplement (§6/§8.2): each professor transaction saves the
        preflight proof at its own transient location and carries the actual path
        in its transaction record, so two professors in different canonical
        directories can never share, overwrite or delete one another's proof."""
        for target in ("professor-contact-codex", "professor-contact-opencode"):
            with self.subTest(target=target):
                agent = self._analyzer(target)
                # The display-name-keyed shared path is retired: professor B's
                # preflight must not be able to overwrite professor A's proof.
                self.assertNotIn("/tmp/<教授名>_stage2_preflight.json", agent, msg=target)
                self.assertIn("<本教授事务临时目录>/stage2_preflight.json", agent, msg=target)
                self.assertIn("不再根据教授展示名", agent, msg=target)

    def _analyzer(self, target: str) -> str:
        path = (ROOT.parents[2] / "packages" / target / ".apm" / "agents"
                / "professor-contact-analyzer.agent.md")
        return path.read_text(encoding="utf-8")

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
