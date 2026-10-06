"""Static contract regressions for the stage-3 idea-generator agent document.

The agent prompt is executable contract, not prose.  These tests deliberately
cover only documented/runtime-neutral instructions; real Codex/OpenCode agent
invocation remains a clean-consumer smoke-test responsibility.
"""
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_PATH = REPO_ROOT / ".apm" / "agents" / "professor-contact-idea-generator.agent.md"
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
        self.assertTrue(SKILL_PATH.exists(), f"missing skill document: {SKILL_PATH}")
        self.text = AGENT_PATH.read_text(encoding="utf-8")
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

    def test_validation_result_is_runner_recorded_and_bounded(self):
        self.assertIn("stage3-record-validation", self.text)
        self.assertRegex(
            self.text,
            r"(?:最多|max)\s*2\s*(?:轮|round)",
            "the style correction loop must remain capped at two rounds",
        )

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
