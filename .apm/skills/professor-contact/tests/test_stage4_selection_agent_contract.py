"""Static contract regressions for the Stage-4 selection agent document.

These tests guard the documented user-choice boundary only.  They do not claim
to prove that Codex or OpenCode actually invoked a named agent; that belongs to
the clean-consumer runtime smoke tests required by PROJECT_CONSENSUS.
"""
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_PATH = REPO_ROOT / ".apm" / "agents" / "professor-contact-selection.agent.md"


def _frontmatter_lines(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError("missing closing frontmatter delimiter") from exc
    return lines[1:end]


class Stage4SelectionAgentContractTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AGENT_PATH.exists(), f"missing agent document: {AGENT_PATH}")
        self.text = AGENT_PATH.read_text(encoding="utf-8")
        self.frontmatter = _frontmatter_lines(self.text)

    def test_frontmatter_keys_are_unique_and_mode_stays_subagent(self):
        seen = {}
        for line in self.frontmatter:
            if not line or line[0].isspace():
                continue
            key = line.partition(":")[0].strip()
            seen[key] = seen.get(key, 0) + 1
        self.assertEqual({}, {key: n for key, n in seen.items() if n > 1})
        self.assertEqual(
            ["mode: subagent"],
            [line for line in self.frontmatter if line.startswith("mode:")],
        )

    def test_explicit_selection_path_remains_supported(self):
        self.assertIn("selection", self.text)
        self.assertIn("显式", self.text)
        self.assertIn("stage4-finalize", self.text)

    def test_opencode_question_path_is_explicitly_runtime_scoped(self):
        self.assertIn("question", self.text)
        self.assertIn(
            "OpenCode-only", self.text,
            "interactive question-tool instructions must not be presented as a Codex API",
        )

    def test_codex_missing_selection_returns_pending_choices_without_finalize(self):
        self.assertIn("Codex", self.text)
        self.assertIn("needs_input", self.text)
        self.assertIn("pending_selection", self.text)
        self.assertRegex(
            self.text,
            r"(?:不得|不能|禁止).{0,40}stage4-finalize",
            "missing-selection Codex path must explicitly forbid formal finalization",
        )

    def test_pending_selection_is_rendered_from_machine_state(self):
        self.assertIn("套磁候选状态.json", self.text)
        self.assertIn("pending_selection", self.text)
        for field in ("direction_ids", "candidates", "research_question"):
            with self.subTest(field=field):
                self.assertIn(field, self.text)

    def test_codex_next_turn_reloads_state_instead_of_resuming_child_memory(self):
        self.assertIn("重新读取", self.text)
        self.assertIn("显式", self.text)
        self.assertIn("selection", self.text)
        self.assertNotIn("codex exec resume", self.text)

    def test_contract_forbids_default_or_recommended_auto_selection(self):
        self.assertRegex(
            self.text,
            r"(?:不得|不能|禁止|不).{0,30}(?:默认|推荐|第一).{0,20}(?:选择|选)",
            "the agent must not substitute its own recommendation for user choice",
        )


if __name__ == "__main__":
    unittest.main()
