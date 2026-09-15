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
    """Lock only the target/caller contracts introduced by issues #28 and #42.

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

    @staticmethod
    def _section_between(text: str, start: str, end: str) -> str:
        start_index = text.index(start)
        end_index = text.index(end, start_index)
        return text[start_index:end_index]

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

    def test_stage1_declares_the_optional_access_mode_enum(self):
        agent_text = _read(STAGE1_AGENT)
        skill_text = _read(SKILL_PATH)

        agent_enum = re.search(
            r'(?m)^- `access_mode` \(optional\): `(?P<enum>"[^"\n]+" \| "[^"\n]+")`(?= \(exact values:)',
            agent_text,
        )
        self.assertIsNotNone(agent_enum)
        self.assertEqual(agent_enum.group("enum"), '"oa_only" | "allow_non_oa"')

        skill_enum = re.search(
            r'(?m)^\| `access_mode` \| no \|.*?显式值严格为 `?(?P<enum>"[^"\n]+" \| "[^"\n]+")`?(?=，在)',
            skill_text,
        )
        self.assertIsNotNone(skill_enum)
        self.assertEqual(skill_enum.group("enum"), '"oa_only" | "allow_non_oa"')

        self.assertEqual(
            re.findall(r'"([^"\n]+)"', agent_enum.group("enum")),
            ["oa_only", "allow_non_oa"],
        )
        self.assertEqual(
            re.findall(r'"([^"\n]+)"', skill_enum.group("enum")),
            ["oa_only", "allow_non_oa"],
        )

    def test_stage1_access_mode_has_explicit_legal_omitted_and_illegal_routes(self):
        agent_text = _read(STAGE1_AGENT)
        skill_text = _read(SKILL_PATH)

        # These are separate assertions on purpose: neither source may borrow
        # a missing branch from the other source's prose.
        self.assertIn(
            "Only when `action == \"pdf_fill_needed\"` may the downloader consume or validate",
            agent_text,
        )
        self.assertRegex(
            agent_text,
            r"(?is)An explicitly supplied legal value is added to the collector business\s+payload verbatim",
        )
        self.assertIn(
            "When `access_mode` is omitted, omit the `access_mode` line entirely.",
            agent_text,
        )
        self.assertIn("When an explicit value is illegal", agent_text)
        self.assertIn("before spawning or calling the", agent_text)
        self.assertIn("collector return the existing structured `error`", agent_text)
        self.assertRegex(
            agent_text,
            r"(?is)Do not spawn the collector,\s*map the value to a legal one, or add a `needs_input` continuation\.",
        )

        self.assertIn(
            "显式值严格只能是 `oa_only` 或 `allow_non_oa`，并以同名同值原样加入 collector payload。",
            skill_text,
        )
        self.assertIn(
            "未提供时完全省略 `access_mode`，不生成默认值、不变成 downloader 的 `needs_input`、不发明 child continuation/resume",
            skill_text,
        )
        self.assertIn(
            "非法值只在 `action=pdf_fill_needed` 时校验，并在 collector spawn 前返回结构化 `error`",
            skill_text,
        )
        self.assertIn(
            "不自动映射、不 spawn、不新增 `needs_input` continuation。",
            skill_text,
        )

    def test_stage1_access_mode_validation_is_guarded_by_pdf_fill_needed(self):
        agent_flow = self._section_between(
            _read(STAGE1_AGENT),
            "### 5. Fill only the missing candidate keys (item-scoped fast path)",
            "### 6. Refresh the snapshot after the collector returns (mandatory)",
        )
        agent_guard = agent_flow.index(
            'Only when `action == "pdf_fill_needed"` may the downloader consume or validate'
        )
        self.assertLess(
            agent_guard,
            agent_flow.index("An explicitly supplied legal value"),
        )
        self.assertLess(
            agent_guard,
            agent_flow.index("When `access_mode` is omitted"),
        )
        self.assertLess(
            agent_guard,
            agent_flow.index("When an explicit value is illegal"),
        )
        self.assertNotRegex(agent_flow[:agent_guard], r"(?i)validate|illegal|非法|校验")

        skill_stage1 = self._section_between(
            _read(SKILL_PATH),
            "### Stage 1 方向候选集与定向补 PDF",
            "### Canonical target state",
        )
        skill_guard = skill_stage1.index(
            "非法值只在 `action=pdf_fill_needed` 时校验"
        )
        self.assertLess(
            skill_guard,
            skill_stage1.index("并在 collector spawn 前返回结构化 `error`"),
        )
        self.assertNotRegex(skill_stage1[:skill_guard], r"(?i)validate|illegal|非法|校验")

    def test_stage1_access_mode_does_not_change_noop_or_resolution_routing(self):
        text = _read(STAGE1_AGENT)

        self.assertRegex(
            text,
            r"(?is)action\s*==\s*[\"']noop[\"'][\s\S]{0,700}(?:access_mode)[\s\S]{0,300}(?:do not|不得|不)[\s\S]{0,200}(?:validate|校验|consume|消费)",
        )
        self.assertRegex(
            text,
            r"(?is)action\s*==\s*[\"']needs_resolution[\"'][\s\S]{0,1000}(?:access_mode)[\s\S]{0,300}(?:do not|不得|不)[\s\S]{0,200}(?:validate|校验|consume|消费)",
        )

    def test_stage1_access_mode_is_shared_by_opencode_and_codex_callers(self):
        agent_text = _read(STAGE1_AGENT)
        skill_text = _read(SKILL_PATH)

        agent_opencode = re.search(
            r"```text\n(task\(subagent_type: \"professor-collector\"[\s\S]*?)```",
            agent_text,
        )
        self.assertIsNotNone(agent_opencode)
        for field in ("folder_path:", "pdf_only: true", "item_keys:"):
            self.assertIn(field, agent_opencode.group(1))
        self.assertNotIn("\\naccess_mode:", agent_opencode.group(1))
        self.assertNotRegex(agent_opencode.group(1), r"(?m)^\s*access_mode\s*:")
        self.assertIn("# access_mode: <oa_only|allow_non_oa>", agent_opencode.group(1))

        skill_opencode = self._section_between(
            skill_text,
            "# 阶段 1：方向候选集 + 定向补 PDF",
            "# 阶段 2：分析",
        )
        for field in ("folder_path:", "professors:", "named_papers_file:"):
            self.assertIn(field, skill_opencode)
        self.assertNotIn("\\naccess_mode:", skill_opencode)
        self.assertNotRegex(skill_opencode, r"(?m)^\s*access_mode\s*:")
        self.assertIn("# access_mode: <oa_only|allow_non_oa>", skill_opencode)

        skill_payload = self._section_between(
            skill_text,
            "5. **定向补下**",
            "6. **重跑幂等**",
        )
        for field in ("pdf_only:true", "item_keys=", "access_mode="):
            self.assertIn(field, skill_payload)

        agent_codex = self._section_between(
            agent_text,
            "**Codex (non-interactive)**",
            "- This is the **item-scoped PDF fill fast path**",
        )
        for field in ("`folder_path`", "`pdf_only: true`", "`item_keys`"):
            self.assertIn(field, agent_codex)
        self.assertRegex(agent_codex, r"appending the caller-provided legal `access_mode` line.*omitting it")

        skill_codex = self._section_between(
            skill_text,
            "#### Codex 下的 Stage 1：委派 exact named custom agent `professor-collector`",
            "### Stage 3/4 编排边界",
        )
        for field in ("`folder_path`", "`pdf_only:true`", "`item_keys="):
            self.assertIn(field, skill_codex)
        self.assertIn("access_mode=<oa_only|allow_non_oa>", skill_codex)
        self.assertIn("缺省时完全省略该字段", skill_codex)

        payload = re.search(
            r"`professor-collector\((?P<body>[^`]+)\)`",
            self._section_between(
                skill_text,
                "5. **定向补下**",
                "6. **重跑幂等**",
            ),
        )
        self.assertIsNotNone(payload)
        for field in ("pdf_only:true", "item_keys=", "access_mode="):
            self.assertIn(field, payload.group("body"))
        self.assertNotIn("professors", payload.group("body"))

    def test_stage1_prompt_templates_make_access_mode_conditional(self):
        """The base delegation prompt must not contain an empty access_mode slot."""
        agent_text = _read(STAGE1_AGENT)
        skill_text = _read(SKILL_PATH)

        agent_section = agent_text[
            agent_text.index("**OpenCode (native Task/subagent delegation)**") :
        ]
        agent_prompt = re.search(
            r"```text\n(task\(subagent_type: \"professor-collector\"[\s\S]*?)```",
            agent_section,
        )
        self.assertIsNotNone(agent_prompt)
        self.assertNotIn("\\naccess_mode:", agent_prompt.group(1))
        self.assertNotRegex(agent_prompt.group(1), r"(?m)^\s*access_mode\s*:")
        self.assertRegex(
            agent_prompt.group(1),
            r"(?im)^#.*access_mode.*(?:append|conditional|追加|条件)",
        )

        opencode_block = re.search(
            r"```\n([\s\S]*?task\(subagent_type: \"professor-contact-downloader\"[\s\S]*?)```",
            skill_text,
        )
        self.assertIsNotNone(opencode_block)
        self.assertNotIn("\\naccess_mode:", opencode_block.group(1))
        self.assertNotRegex(opencode_block.group(1), r"(?m)^\s*access_mode\s*:")
        self.assertRegex(
            opencode_block.group(1),
            r"(?im)^#.*access_mode.*(?:append|conditional|追加|缺省)",
        )


if __name__ == "__main__":
    unittest.main()
