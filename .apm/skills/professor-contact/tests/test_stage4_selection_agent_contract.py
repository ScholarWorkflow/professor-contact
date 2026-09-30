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
        self.assertTrue(
            "显式" in self.text or "explicit" in self.text,
            "the agent must retain an explicit-selection input path",
        )
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
        self.assertTrue("显式" in self.text or "explicit" in self.text)
        self.assertIn("selection", self.text)
        self.assertNotIn("codex exec resume", self.text)

    def test_contract_forbids_default_or_recommended_auto_selection(self):
        self.assertRegex(
            self.text,
            r"(?:不得|不能|禁止|不).{0,30}(?:默认|推荐|第一).{0,20}(?:选择|选)",
            "the agent must not substitute its own recommendation for user choice",
        )

    def test_stage4_finalize_command_sources_profile_from_state(self):
        self.assertRegex(
            self.text,
            r"--profile\s*<[^>]*profile_path[^>]*>",
            "stage4-finalize must receive --profile taken from the candidate state's "
            "top-level profile_path; the runner recomputes the profile fingerprint "
            "from it and fail-closes with profile_changed otherwise",
        )
        self.assertNotIn(
            "或省略", self.text,
            "omitting --profile is not a valid variant: with it absent the runner's "
            "current profile fingerprint is None and never matches a recorded one",
        )


class Issue67Stage4SelectionContractTests(unittest.TestCase):
    """Issue #67: the selection child works per canonical professor, never globally.

    These are the documented-input halves of `PC67-DADJ`; the machine halves run in
    `Issue67AdjacentStateTests`, and the actual delegation lives in the runtime
    smoke cases.
    """

    def setUp(self):
        self.assertTrue(AGENT_PATH.exists(), f"missing agent document: {AGENT_PATH}")
        self.text = AGENT_PATH.read_text(encoding="utf-8")

    def test_canonical_professor_dir_is_the_per_professor_read_and_map_unit(self):
        for required in ("professor_dir", "canonical", "套磁候选状态.json",
                         "每轮重新读盘"):
            with self.subTest(required=required):
                self.assertIn(required, self.text)
        self.assertRegex(
            self.text,
            r"(?:显示名|同名|display).{0,40}(?:不|never)\S{0,20}(?:合并|merge|同一)",
            "the same display name must not merge two canonical directories")

    def test_pending_selection_row_carries_the_professor_directory(self):
        self.assertIn("pending_selection", self.text)
        self.assertRegex(
            self.text,
            r'"professor_dir"\s*:',
            "every pending_selection entry must name the canonical professor_dir the "
            "next turn has to write back")

    def test_aggregate_result_is_consumed_row_by_row(self):
        for required in ("results[]", "partial", "needs_refresh", "selection_file",
                         "email_pack"):
            with self.subTest(required=required):
                self.assertIn(required, self.text)
        self.assertRegex(
            self.text,
            r"(?:别的教授|其他教授).{0,40}(?:不|never)\S{0,16}(?:阻断|前置条件|撤销)",
            "one professor's failure must neither block nor revoke another's commit")

    def test_path_c_still_delegates_waits_and_writes_nothing_formally(self):
        self.assertIn("OpenCode", self.text)
        self.assertIn("question", self.text)
        self.assertIn("重新委派本 agent", self.text)
        self.assertRegex(
            self.text,
            r"重新委派本 agent.{0,40}显式传入.{0,20}selection",
            "the next user turn must re-delegate this child with an explicit "
            "selection instead of resuming the old child thread")
        self.assertRegex(
            self.text,
            r"(?:零写盘|不写任何文件|零写入)",
            "the missing-selection turn must stay free of formal writes")

    def test_legacy_program_pair_is_never_written_and_only_migrates_per_professor(self):
        self.assertIn("stage4-migrate-local", self.text)
        self.assertIn("already_local", self.text)
        self.assertIn("local_pair_incomplete", self.text)
        self.assertRegex(
            self.text,
            r"(?:程序级|教授研究/套磁选择\.json).{0,60}(?:绝不|never)\S{0,12}(?:写入|权威)",
            "the program-level pair must stay a historical source, never authority")

    def test_runner_comes_from_the_exact_installed_consumer_skill(self):
        self.assertNotIn(
            "skillrepo exec professor-contact",
            self.text,
            "a clean consumer must not resolve Stage-4 through an ambient registered "
            "development checkout",
        )
        self.assertIn(
            ".agents/skills/professor-contact/scripts/contact_state.py",
            self.text,
            "the Stage-4 command must execute the runner installed in this consumer",
        )
        self.assertRegex(
            self.text,
            r"(?:精确提交|exact[- ]SHA|当前 consumer).{0,80}(?:安装|installed).{0,80}runner",
            "the command provenance rule must be explicit enough for a clean consumer",
        )

    def test_selection_professor_is_copied_from_the_professor_input_pack(self):
        self.assertIn("套磁候选输入.json", self.text)
        self.assertRegex(
            self.text,
            r"professor.{0,40}(?:原样|逐字|exact).{0,40}(?:复制|抄)",
            "the display professor must come from the selected directory's input pack, "
            "not from the directory basename or a guessed label",
        )

    def test_agent_never_invents_or_auto_selects_for_a_professor(self):
        self.assertRegex(
            self.text,
            r"(?:不得|禁止|绝不).{0,30}(?:默认|推荐|自动选第一项)",
            "the child may not substitute its own recommendation for user choice")


if __name__ == "__main__":
    unittest.main()
