"""Static contract regressions for the stage-3 idea-generator agent document.

The agent prompt is executable contract, not prose.  These tests deliberately
cover only documented/runtime-neutral instructions; real Codex/OpenCode agent
invocation remains a clean-consumer smoke-test responsibility.
"""
from pathlib import Path
import json
import tomllib
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_PATH = REPO_ROOT / ".apm" / "agents" / "professor-contact-idea-generator.agent.md"
VALIDATOR_PATH = REPO_ROOT / ".apm" / "agents" / "professor-contact-style-validator.agent.md"
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"


def _frontmatter_lines(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError("missing closing frontmatter delimiter") from exc
    return lines[1:end]


def _section(text: str, start: str, end: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise AssertionError(f"missing section start: {start}")
    end_at = text.find(end, start_at + len(start))
    if end_at < 0:
        raise AssertionError(f"missing section end: {end}")
    return text[start_at:end_at]


def _section_to_end(text: str, start: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise AssertionError(f"missing section start: {start}")
    return text[start_at:]


def _assert_in_order(testcase, text: str, tokens: list[str], label: str) -> None:
    positions = [text.find(token) for token in tokens]
    testcase.assertTrue(
        all(position >= 0 for position in positions),
        f"{label} is missing handoff steps: "
        f"{[token for token, position in zip(tokens, positions) if position < 0]}",
    )
    testcase.assertEqual(
        positions, sorted(positions),
        f"{label} must follow prepare → validator output_file → save → record",
    )


class Stage3IdeaGeneratorAgentContractTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AGENT_PATH.exists(), f"missing agent document: {AGENT_PATH}")
        self.assertTrue(VALIDATOR_PATH.exists(), f"missing validator document: {VALIDATOR_PATH}")
        self.assertTrue(SKILL_PATH.exists(), f"missing skill document: {SKILL_PATH}")
        self.text = AGENT_PATH.read_text(encoding="utf-8")
        self.validator_text = VALIDATOR_PATH.read_text(encoding="utf-8")
        self.skill_text = SKILL_PATH.read_text(encoding="utf-8")
        self.frontmatter = _frontmatter_lines(self.text)

    def test_frontmatter_keys_are_unique(self):
        seen = {}
        for line in self.frontmatter:
            if not line or line[0].isspace():
                continue
            key = line.partition(":")[0].strip()
            seen[key] = seen.get(key, 0) + 1
        duplicates = {key: count for key, count in seen.items() if count > 1}
        self.assertEqual(
            {}, duplicates,
            "duplicate top-level frontmatter keys are parser-dependent; keep one of each",
        )

    def test_frontmatter_declares_single_subagent_mode(self):
        modes = [line for line in self.frontmatter if line.startswith("mode:")]
        self.assertEqual(
            ["mode: subagent"], modes,
            "frontmatter must declare exactly one `mode: subagent`",
        )

    def test_no_legacy_collection_key_result_routing(self):
        self.assertNotIn(
            "candidates-<collection_key>", self.text,
            "result filenames must never be assembled from collection_key; "
            "the runner routes results through plan-returned result_file only",
        )

    def test_plan_returned_result_file_contract_is_present(self):
        self.assertIn("result_file", self.text)
        self.assertIn(
            "精确文件名", self.text,
            "the agent must state that model results go to the exact plan-returned filename",
        )
        self.assertIn(
            "绝不自拼", self.text,
            "the agent must forbid self-assembling result filenames",
        )

    def test_runtime_specific_validator_orchestration_is_explicit(self):
        self.assertIn(
            "OpenCode-only", self.text,
            "Task-based nested validation must be explicitly scoped to OpenCode",
        )
        self.assertIn("Codex", self.text)
        self.assertIn(
            "调用线程", self.text,
            "Codex must describe caller-owned sibling orchestration rather than an invented API",
        )
        self.assertIn("professor-contact-style-validator", self.text)

        # Source declaration and deterministic TOML string encoding only.
        # This synthesized expected payload is not an installation artifact;
        # the clean installer check owns the actual installed projection.
        agent_body = self.text.split("---", 2)[2].strip("\n")
        codex_projection = tomllib.loads(
            f"developer_instructions = {json.dumps(agent_body)}\n"
        )["developer_instructions"]
        for marker in (
            "也不读取任何其它教授的状态",
            "绝不读写程序级",
            "总览是 terminal 后由",
        ):
            with self.subTest(projection_marker=marker):
                self.assertIn(marker, self.text)
                self.assertIn(marker, codex_projection)
        # R19 clarification R4 keeps the declared local dependency boundary;
        # it withdraws complete child-input collection and derived gates.
        self.assertIn("也不读取任何其它教授的状态", self.skill_text)
        self.assertIn("不会阻塞、回滚或重判任何一次合法的教授本地提交",
                      self.skill_text)

    def test_validation_result_is_runner_recorded_and_bounded(self):
        self.assertIn("stage3-record-validation", self.text)
        self.assertRegex(
            self.text,
            r"(?:最多|max)\s*2\s*(?:轮|round)",
            "the style correction loop must remain capped at two rounds",
        )

    def test_fixed_writer_contract_and_caller_stop_before_save_on_error(self):
        validator_write = _section(
            self.validator_text,
            "### E. Stage-3 原文落盘",
            "## Return value",
        )
        for marker in (
            "contact_state.py stage3-write-validation",
            "--result-json",
            "--output-file",
            "--output-map-json",
            "唯一一份",
            "完整业务 JSON 对象",
            "stdout",
            "退出码为",
            "成功 stdout 是完整结果原文并与指定文件中的字节完全相同",
            "命令失败",
            "error",
            "停止",
            "不得自行重建",
            "排他方式",
            "0600",
            "保留已完成文件",
        ):
            with self.subTest(validator_contract=marker):
                self.assertIn(marker, validator_write)

        loop = _section(
            self.text,
            "### Step 3.6 — 白话校验循环",
            "### Step 4 — Return value",
        )
        for marker in (
            "stage3-write-validation",
            "入口非零",
            "结果缺失/不完整",
            "立即按既有 error JSON",
            "不运行 save、record 或修正轮",
        ):
            with self.subTest(caller_contract=marker):
                self.assertIn(marker, loop)
        handoff_chain = _section(
            loop,
            "每轮原始 JSON 都按",
            "两个分支的业务规则完全相同",
        )
        _assert_in_order(
            self, handoff_chain,
            ["stage3-prepare-validation", "validator 固定入口写入",
             "stage3-save-validation", "stage3-record-validation"],
            "固定写入后的 caller 顺序",
        )
        opencode = _section(loop, "**OpenCode 分支", "**Codex 分支")
        for marker in (
            "prepare 返回的完整绝对输出路径",
            "prepare 已返回的所有输出路径",
            "无重复的一对一映射",
            "不能补造输出位置",
            "不得重建或重序列化 validator JSON",
        ):
            with self.subTest(prepared_binding=marker):
                self.assertIn(marker, opencode)

    def test_validator_without_output_file_remains_read_only(self):
        validator_write = _section(
            self.validator_text,
            "### E. Stage-3 原文落盘",
            "## Return value",
        )
        hard_rules = _section_to_end(self.validator_text, "## Hard rules")
        self.assertIn("未传 `output_file` 时保持原有只读行为", validator_write)
        self.assertIn("未传 `output_file` 的调用绝不 write/edit 任何文件", hard_rules)
        self.assertIn("不调用写入入口", validator_write)

    def test_opencode_example_and_common_closeout_follow_skill_handoff_chain(self):
        tokens = [
            "stage3-prepare-validation",
            "output_file",
            "stage3-save-validation",
            "stage3-record-validation --handoff-file",
            "--expected-validation-sha256",
        ]
        skill_chain = _section(
            self.skill_text,
            "**Stage 3 在 validator 记录之前不算完成**",
            "**Stage 3 终态后重建程序级总览",
        )
        _assert_in_order(self, skill_chain, tokens, "SKILL 四步交接链")

        agent_loop = _section(
            self.text,
            "### Step 3.6 — 白话校验循环",
            "### Step 4 — Return value",
        )
        opencode = _section(agent_loop, "**OpenCode 分支", "**Codex 分支")
        common_closeout = _section(self.text, "**共同收尾", "### Step 4")
        with self.subTest(section="OpenCode 示例"):
            _assert_in_order(self, opencode, tokens, "OpenCode 示例")
        with self.subTest(section="共同收尾"):
            _assert_in_order(self, common_closeout, tokens, "共同收尾")
        with self.subTest(section="禁止旧直接记录方式"):
            self.assertNotIn(
                "stage3-record-validation --professor-dir",
                opencode + common_closeout,
                "Stage 3 handoff must record the saved handoff, not the legacy direct file mode",
            )

    def test_validator_failure_uses_runner_correction_input(self):
        self.assertIn("--validation-file", self.text)
        self.assertIn("current_result", self.text)
        self.assertIn("validator_issues", self.text)

    def test_contract_does_not_bind_to_a_specific_spawn_tool_envelope(self):
        # `spawn_agent` itself is a documented, stable Codex multi-agent tool
        # name (issue #51): the ban exists so the agent contract never binds
        # to one concrete tool envelope or request schema, not because the
        # name were private. `agent_type=`/`agent_role=` are undocumented
        # request-side shapes.
        for forbidden in ("spawn_agent(", "agent_type=", "agent_role="):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.text,
                    "keep the contract at the documented named-custom-agent level",
                )


if __name__ == "__main__":
    unittest.main()
