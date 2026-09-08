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

    def test_stage4_has_codex_user_boundary_and_opencode_question_boundary(self):
        self.assertIn("professor-contact-selection", self.text)
        self.assertIn("question", self.text)
        self.assertIn("needs_input", self.text)
        self.assertIn("pending_selection", self.text)
        self.assertIn("套磁候选状态.json", self.text)
        self.assertIn("stage4-finalize", self.text)

    def test_caller_contract_does_not_encode_undocumented_codex_spawn_api(self):
        for forbidden in ("spawn_agent(", "agent_type=", "agent_role="):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.text,
                    "Codex custom-agent orchestration must stay at the documented named-agent level",
                )

    def test_caller_does_not_make_resume_a_stage4_state_protocol(self):
        self.assertNotIn("codex exec resume", self.text)
        self.assertRegex(
            self.text,
            r"(?:重新|再次).{0,40}professor-contact-selection",
            "the next user turn must call selection again instead of depending on child memory",
        )


if __name__ == "__main__":
    unittest.main()
