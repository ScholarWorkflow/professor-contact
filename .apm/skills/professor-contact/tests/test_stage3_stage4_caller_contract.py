"""Caller-contract regressions for the Stage-3/4 dual-runtime handoff.

The main Skill owns the runtime boundary.  Static tests only ensure that the
instructions do not collapse OpenCode tools and Codex custom-agent semantics
into a made-up common API; runtime identity is verified by smoke tests.
"""
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"


class Stage3Stage4CallerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SKILL_PATH.exists():
            raise AssertionError(f"missing Skill document: {SKILL_PATH}")
        cls.text = SKILL_PATH.read_text(encoding="utf-8")

    def test_stage3_has_distinct_runtime_orchestration(self):
        self.assertIn("professor-contact-idea-generator", self.text)
        self.assertIn("professor-contact-style-validator", self.text)
        self.assertIn("OpenCode-only", self.text)
        self.assertIn("Codex", self.text)
        self.assertIn("stage3-record-validation", self.text)

    def test_stage3_codex_root_routes_generator_wait_validator_wait(self):
        section = self._stage34_orchestration_section()
        codex_start = section.index("- **Codex（root caller")
        stage3 = section[codex_start:]
        generator = stage3.index("professor-contact-idea-generator")
        generator_wait = stage3.index("等待生成 + `stage3-finalize` 完成")
        validator = stage3.index("professor-contact-style-validator")
        validator_wait = stage3.index("并等待需要的 child 完成后再继续")
        self.assertLess(generator, generator_wait)
        self.assertLess(generator_wait, validator)
        self.assertLess(validator, validator_wait)
        self.assertIn("root caller", stage3)

    def test_read_first_section_states_stage3_completion_requires_validation_record(self):
        # Batch-5 runtime regression: the R3-A root read only the first ~280
        # lines of SKILL.md and never reached the validator-loop section, so it
        # announced "Stage 3 complete" without stage3-record-validation. The
        # read-first completion summary must surface that obligation early.
        header = self.text[: self.text.index("## What this is for")]
        self.assertIn("Stage 收尾硬性步骤（read first", header)
        self.assertIn("stage3-record-validation", header)
        self.assertIn("validator` 字段为空即未完成", header)
        self.assertIn("阅读边界", header)

    def test_correction_round_message_keeps_required_business_input(self):
        # Batch-6 runtime regression: the correction round said the child
        # message may ONLY contain validation_file, but idea-generator's Input
        # contract requires folder_path — the correction agent answered
        # `missing folder_path` twice, burned the thread budget, and the
        # second validator never ran. The rule must keep the required
        # business input while still banning direction_id / issue prose.
        self.assertRegex(
            self.text,
            r"child message = Stage 3 正常业务输入（`folder_path` 等 Input contract 必需字段",
        )
        howto = self.text[self.text.index("task(subagent_type: \"professor-contact-idea-generator\", prompt: \"folder_path: <...>\\nvalidation_file:"):]
        self.assertIn("validation_file: <已记录的 validator 原始 JSON 绝对路径>", howto[:400])

    def test_stage3_retry_and_root_inline_forbidden_list_are_load_bearing(self):
        section = self._stage34_orchestration_section()
        for required in (
            "最多 2 轮",
            "stage3-record-validation",
            "stage3-plan",
            "candidate model generation",
            "candidate result file",
            "stage3-finalize",
            "不重读 Stage 2",
            "不扩展方向事实",
        ):
            with self.subTest(required=required):
                self.assertIn(required, section)

    def test_stage3_validator_scope_and_correction_handoff_are_exact(self):
        section = self._stage34_orchestration_section()
        self.assertIn("child message **只允许**含渲染后的单一教授级", section)
        self.assertIn("artifact: candidates", section)
        self.assertIn("validation-file", section)
        self.assertIn("再次委派 style-validator", section)

    def test_stage3_two_round_limit_is_two_validator_calls(self):
        section = self._stage34_orchestration_section()
        for required in (
            "验证轮 = style-validator 调用次数，不是修订次数",
            "最多 2 次 style-validator",
            "第 2 次 validator 返回后禁止再委派 idea-generator",
            "初次 generator → 第 1 次 validator",
            "一次修订 generator → 第 2 次 validator",
        ):
            self.assertIn(required, section)

    def test_stage3_correction_passes_raw_file_not_issue_prose(self):
        section = self._stage34_orchestration_section()
        self.assertIn("validation_file: <原始 JSON 绝对路径>", section)
        self.assertIn("不得把 issues 摘抄或改写成 prose", section)
        # BLOCKER 1 (issue #47 review @4e911dd): the caller never nominates the
        # scope to repair — the recorded round does.
        self.assertIn("**不得传 direction_id、不得把 issues 摘抄或改写成 prose**", section)
        self.assertNotIn("direction_id: <失败方向 ID>", section)

    def test_stage3_records_every_round_before_planning_a_correction(self):
        section = self._stage34_orchestration_section()
        for required in (
            "每一轮 validator 返回后先由 runner 记录，再决定是否修正",
            "`stage3-record-validation` 必须在 `stage3-plan --validation-file` 之前完成",
            "由它绑定当前渲染 SHA、判定失败范围、累计轮次并返回 `needs_correction`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, section)

    def test_stage4_has_codex_user_boundary_and_opencode_question_boundary(self):
        self.assertIn("professor-contact-selection", self.text)
        self.assertIn("question", self.text)
        self.assertIn("needs_input", self.text)
        self.assertIn("pending_selection", self.text)
        self.assertIn("套磁候选状态.json", self.text)
        self.assertIn("stage4-finalize", self.text)

    def test_caller_contract_does_not_encode_undocumented_codex_spawn_api(self):
        # `spawn_agent`/`spawnAgent` are documented Codex multi-agent tool
        # names; they stay out of the caller convention so the contract never
        # binds to one concrete tool envelope (issue #51), not because the
        # names were private.
        for forbidden in ("spawn_agent(", "agent_type=", "agent_role=", "spawnAgent"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.text,
                    "Codex custom-agent orchestration must stay at the documented named-agent level",
                )

    def _stage34_orchestration_section(self):
        """Return the Stage 3/4 orchestration-boundary section of SKILL.md.

        The Codex delegation contract lives in this section only; asserting on
        the whole document would stay green after the section is deleted or
        broken, because unrelated stages mention words like 等待 elsewhere.
        """
        marker = "### Stage 3/4 编排边界"
        start = self.text.find(marker)
        self.assertGreaterEqual(
            start, 0,
            "the Stage 3/4 orchestration-boundary section must exist in SKILL.md",
        )
        next_heading = self.text.find("\n### ", start + len(marker))
        if next_heading == -1:
            return self.text[start:]
        return self.text[start:next_heading]

    def test_stage34_section_names_all_three_custom_agents(self):
        section = self._stage34_orchestration_section()
        for required in (
            "professor-contact-idea-generator",
            "professor-contact-style-validator",
            "professor-contact-selection",
        ):
            with self.subTest(required=required):
                self.assertIn(
                    required, section,
                    "the Stage 3/4 orchestration-boundary section must name "
                    "the exact installed custom agents",
                )

    def test_stage34_section_locks_codex_named_agent_delegation(self):
        section = self._stage34_orchestration_section()
        self.assertRegex(
            section, r"委派|delegate|use",
            "the Codex branch must delegate via the documented product "
            "semantics: use the installed named custom agent; the runtime "
            "owns spawn/wait orchestration",
        )
        self.assertRegex(
            section, r"等待.{0,80}完成",
            "the caller must wait for the needed child to finish before "
            "continuing",
        )

    def test_stage34_section_requires_stage4_redelegation_on_next_user_turn(self):
        section = self._stage34_orchestration_section()
        self.assertRegex(
            section, r"重新委派.{0,20}professor-contact-selection",
            "the next user turn must re-delegate the selection agent with an "
            "explicit selection instead of depending on child memory",
        )

    def _stage4_user_boundary(self):
        section = self._stage34_orchestration_section()
        marker = "**Stage 4 用户选择边界"
        start = section.find(marker)
        self.assertGreaterEqual(
            start, 0,
            "the Stage 4 user boundary must stay inside the Stage 3/4 section",
        )
        return section[start:]

    def test_stage4_always_delegates_before_handling_either_selection_state(self):
        stage4 = self._stage4_user_boundary()
        self.assertRegex(
            stage4,
            r"无论.{0,30}selection.{0,50}必须先委派.{0,80}professor-contact-selection",
            "Stage 4 must route both present and omitted selection through the named child",
        )
        self.assertRegex(
            stage4,
            r"professor-contact-selection.{0,100}等待",
            "the caller must wait for the Stage 4 child before consuming its result",
        )
        self.assertRegex(
            stage4,
            r"selection omitted.{0,80}不是.{0,40}(提前|caller).{0,20}(结束|return)",
            "missing selection must be a child input path, not a caller early return",
        )

    def test_stage4_forbids_caller_side_simulation_and_default_selection(self):
        stage4 = self._stage4_user_boundary()
        for required in (
            "提前返回 prose",
            "自行构造候选",
            "模拟 pending_selection",
            "默认/推荐/自动选第一项",
            "直接调用 stage4-finalize",
            "inline 执行 selection agent",
        ):
            with self.subTest(required=required):
                self.assertIn(
                    required,
                    stage4,
                    "the Stage 4 caller contract must name this bypass explicitly",
                )

    def test_stage4_keeps_opencode_question_separate_from_codex_redelegation(self):
        stage4 = self._stage4_user_boundary()
        self.assertIn("OpenCode", stage4)
        self.assertIn("question", stage4)
        self.assertIn("multiple: true", stage4)
        self.assertIn("Codex", stage4)
        self.assertIn("重新委派", stage4)

    def test_stage34_section_rejects_envelope_binding_or_wrong_runtime_protocols(self):
        section = self._stage34_orchestration_section()
        # The tool names below are documented Codex surfaces; the ban keeps
        # the business contract from binding to their concrete envelope and
        # from re-importing wrong-runtime tools (issue #51).
        for forbidden in (
            "spawnAgent", "spawn_agent(", "agent_type=", "agent_role=",
            "codex exec resume",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden, section,
                    "the Stage 3/4 section must stay at the documented "
                    "named-agent level and keep wrong-runtime tools out",
                )

    def test_caller_does_not_make_resume_a_stage4_state_protocol(self):
        self.assertNotIn("codex exec resume", self.text)


if __name__ == "__main__":
    unittest.main()
