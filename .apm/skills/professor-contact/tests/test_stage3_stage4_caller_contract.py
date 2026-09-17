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
