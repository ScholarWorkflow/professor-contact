from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"
STAGE0_AGENT = AGENTS_DIR / "professor-contact.agent.md"
STAGE1_AGENT = AGENTS_DIR / "professor-contact-downloader.agent.md"
STAGE2_AGENT = AGENTS_DIR / "professor-contact-analyzer.agent.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class Stage01CallerContractTests(unittest.TestCase):
    """Lock only the target/caller contracts introduced by issue #28.

    Runtime behavior is intentionally not mocked here. Codex/OpenCode runtime
    acceptance belongs to the clean-consumer smoke procedure in
    PROJECT_CONSENSUS; these tests only prevent source-level caller contracts
    from drifting while the implementation is developed.
    """

    def test_stage0_exposes_structured_selection_for_noninteractive_callers(self):
        text = _read(STAGE0_AGENT)

        # Stage 0 must be callable with the same machine identity used by the
        # deterministic helper instead of forcing a runtime-specific UI.
        self.assertIn("`selection`", text)
        self.assertIn("direction_ids", text)
        self.assertIn("notes", text)
        self.assertIn("OpenCode", text)
        self.assertIn("Codex", text)

        # Codex non-interactive no-input handling is a business result, not an
        # invented nested-child continuation protocol.
        self.assertIn("needs_input", text)
        self.assertIn("selection_request", text)
        self.assertRegex(text, r"contact_targets\.py[\s\S]*?\bselect\b")

    @staticmethod
    def _command_blocks(text: str) -> str:
        blocks = re.findall(r"```(?:bash|shell|sh)\n(.*?)```", text, flags=re.DOTALL)
        return "\n".join(blocks)

    def test_stage01_helper_invocations_execute_the_installed_skill_scripts(self):
        """Clean-consumer source provenance: delivered Stage 0-1 call sites must
        execute the scripts installed with this skill in the current workspace.

        `skillrepo exec <repo> <resource>` resolves by host-global
        registration, which is outside the consumer; the 2026-09-12 clean
        consumer run machine-observed it running repo-owned scripts from a
        development checkout instead of the consumer installation. The caller
        convention therefore anchors every helper invocation to this skill's
        own installed directory, the same self-anchored pattern the
        professor-collector agent definition uses. Prose may name the banned
        wrapper; no command block may use it.
        """
        placeholder = "<professor-contact-skill-dir>"
        expected_helpers = {
            STAGE0_AGENT: ("contact_targets.py",),
            STAGE1_AGENT: ("contact_targets.py", "contact_stage1.py"),
            SKILL_PATH: ("contact_targets.py",),
        }
        for path, helpers in expected_helpers.items():
            text = _read(path)
            commands = self._command_blocks(text)
            self.assertNotIn("skillrepo exec", commands)
            self.assertNotIn(".apm/skills/", commands)
            for helper in helpers:
                self.assertIn(
                    f"python3 {placeholder}/scripts/{helper}",
                    commands,
                    f"{path.name}: {helper} must be invoked from this skill's installed directory",
                )
            # The placeholder is defined as this skill's own installed copy in
            # the current workspace, with the consumer install location named.
            self.assertIn(placeholder, text)
            self.assertIn(".agents/skills/professor-contact", text)

    def test_stage2_analyzer_helper_invocations_execute_the_installed_skill_scripts(self):
        """Stage 2 shares the clean-consumer source provenance contract.

        The 2026-09-15 issue #39 PC39-R1 runtime run machine-observed the same
        failure already fixed for Stage 0-1: the analyzer's delivered command
        blocks invoked `skillrepo exec professor-contact .apm/skills/...`,
        which resolved outside the consumer (EACCES) and drove the model to
        run deterministic runners from a development checkout. Stage 2's
        deterministic helpers must execute from this skill's installed
        directory like every other stage.
        """
        placeholder = "<professor-contact-skill-dir>"
        text = _read(STAGE2_AGENT)
        commands = self._command_blocks(text)
        self.assertNotIn("skillrepo exec", commands)
        self.assertNotIn(".apm/skills/", commands)
        for helper in ("contact_targets.py", "contact_stage1.py", "contact_state.py",
                       "stage2_input_router.py", "stage2_chatgpt_handoff.py"):
            self.assertIn(
                f"python3 {placeholder}/scripts/{helper}",
                commands,
                f"analyzer: {helper} must be invoked from this skill's installed directory",
            )
        self.assertIn(placeholder, text)
        self.assertIn(".agents/skills/professor-contact", text)

    def test_stage0_and_stage1_do_not_depend_on_invented_codex_event_fields(self):
        text = "\n".join((_read(STAGE0_AGENT), _read(STAGE1_AGENT), _read(SKILL_PATH)))

        self.assertNotRegex(text, r"spawn_agent\s*\(")
        self.assertNotIn("agent_role", text)
        self.assertNotIn("agent_path", text)

    def test_stage1_documents_target_specific_professor_collector_delegation(self):
        text = _read(STAGE1_AGENT)

        # OpenCode keeps its documented Task/subagent path.
        self.assertIn("OpenCode", text)
        self.assertIn('task(subagent_type: "professor-collector"', text)

        # Codex must refer to the installed named custom role and wait for its
        # result; no undocumented spawn function is required by this test.
        self.assertIn("Codex", text)
        self.assertRegex(text, r"(?is)Codex[\s\S]*?professor-collector")
        self.assertRegex(text, r"(?is)Codex[\s\S]*?(?:delegate|use|委派)[\s\S]*?(?:wait|等待)")

    def test_stage1_keeps_item_scoped_fill_rebuild_and_single_retry_contract(self):
        text = _read(STAGE1_AGENT)

        self.assertIn("pdf_only: true", text)
        self.assertIn("item_keys", text)
        self.assertRegex(
            text,
            r"(?is)(?:never|不得|绝不能)[\s\S]{0,300}professors[\s\S]{0,300}item_keys",
        )
        self.assertRegex(text, r"(?is)(?:retry once|重试一次)[\s\S]{0,300}(?:same|相同)")
        self.assertRegex(
            text,
            r"(?is)(?:refresh|re-run|rebuild|重新)[\s\S]{0,500}contact_stage1\.py[\s\S]{0,200}\bbuild\b",
        )

    def test_stage1_source_keeps_noop_and_resolution_fail_closed(self):
        text = _read(STAGE1_AGENT)

        self.assertRegex(text, r"(?is)action\s*==\s*[\"']noop[\"'][\s\S]{0,500}(?:do not spawn|不得调用|不调用)")
        self.assertRegex(
            text,
            r"(?is)action\s*==\s*[\"']needs_resolution[\"'][\s\S]{0,800}(?:partial)[\s\S]{0,500}(?:do not spawn|不得调用|不调用)",
        )


if __name__ == "__main__":
    unittest.main()
