from pathlib import Path, PurePosixPath
import json
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"
STAGE0_AGENT = AGENTS_DIR / "professor-contact.agent.md"
STAGE1_AGENT = AGENTS_DIR / "professor-contact-downloader.agent.md"
STAGE2_AGENT = (
    REPO_ROOT
    / "packages"
    / "professor-contact-opencode"
    / ".apm"
    / "agents"
    / "professor-contact-analyzer.agent.md"
)
STAGE2_CODEX_AGENT = (
    REPO_ROOT
    / "packages"
    / "professor-contact-codex"
    / ".apm"
    / "agents"
    / "professor-contact-analyzer.agent.md"
)
TARGET_NAME = "套磁目标.json"
STAGE1_STATE_NAME = "套磁阶段1候选.json"
PROGRAM_STATE_DIR = "教授研究"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fenced(text: str, language: str | None = None) -> list[str]:
    """Active result / command / payload blocks only.

    Gate-2 evidence scope: prose, migration notes and prohibitions may name a
    retired path without making the shipped handoff depend on it, so every
    assertion below reads fenced blocks and nothing else.
    """
    tag = language if language is not None else "[a-zA-Z0-9]*"
    return re.findall(rf"```{tag}\n(.*?)```", text, flags=re.DOTALL)


def _bash_blocks(text: str) -> list[str]:
    return _fenced(text, "(?:bash|shell|sh)")


def _json_objects(text: str, key: str) -> list[dict]:
    """Parse the fenced json blocks that carry `key` as a business field."""
    found = []
    for block in _fenced(text, "json"):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and key in payload:
            found.append(payload)
    return found


#: Characters that can never appear inside one of these state-file path references.
_PATH_STOP = set(" \t\n\"'`(){}[],;|&，。；：（）「」、")


def _task_prompt(text: str, agent_name: str) -> list[str]:
    """Return the business prompt of each ``task(subagent_type: "<agent>", ...)``."""
    pattern = re.compile(
        r'task\(subagent_type:\s*"' + re.escape(agent_name) + r'"[^)]*?prompt:\s*"(?P<prompt>[^"]*)"'
    )
    return [match.group("prompt") for match in pattern.finditer(text)]


def _parent_of_reference(token: str) -> str:
    return PurePosixPath(token).parent.name.strip("<>")


def _state_reference_scopes(text: str, filename: str) -> tuple[list[str], list[str], list[str]]:
    """Split every mention of `filename` into local / program-level / unbound."""
    local: list[str] = []
    program: list[str] = []
    unbound: list[str] = []
    for match in re.finditer(re.escape(filename), text):
        start = match.start()
        if start == 0 or text[start - 1] != "/":
            unbound.append(filename)
            continue
        cursor = start
        while cursor > 0 and text[cursor - 1] not in _PATH_STOP:
            cursor -= 1
        token = text[cursor:start + len(filename)]
        bucket = program if _parent_of_reference(token) == PROGRAM_STATE_DIR else local
        bucket.append(token)
    return local, program, unbound


def _assert_professor_local(value: str, filename: str, case: str) -> None:
    path = PurePosixPath(value)
    assert path.name == filename, f"{case}: {value!r} is not a {filename} reference"
    assert _parent_of_reference(value) != PROGRAM_STATE_DIR, (
        f"{case}: {value!r} still points at the program-level {PROGRAM_STATE_DIR}/ authority"
    )


class Stage01CallerContractTests(unittest.TestCase):
    """Lock only the target/caller contracts introduced by issues #28 and #42.

    Runtime behavior is intentionally not mocked here. Codex/OpenCode runtime
    acceptance belongs to the clean-consumer smoke procedure in
    PROJECT_CONSENSUS; these tests only prevent source-level caller contracts
    from drifting while the implementation is developed.
    """

    #: Commands whose only Stage-0 authority input is one professor's local target.
    TARGET_BOUND_COMMANDS = (
        "contact_targets.py resolve",
        "contact_stage1.py build",
        "contact_stage1.py verify",
        "stage2-preflight",
    )
    #: Sources owned by the Stage 0-1 caller contract.
    STAGE01_SOURCES = (STAGE0_AGENT, STAGE1_AGENT, SKILL_PATH)

    @staticmethod
    def _clauses(text: str) -> list[str]:
        """Sentences with backslash-continued command lines joined back together."""
        return re.split(r"[。；\n]", text.replace("\\\n", " "))

    def test_issue64_t7_every_target_bound_command_names_the_local_target_file(self):
        """R64-6 caller side (G64-T7): no documented invocation may omit --target-file."""
        for path in self.STAGE01_SOURCES:
            text = _read(path)
            for clause in self._clauses(text):
                for command in self.TARGET_BOUND_COMMANDS:
                    if command in clause:
                        self.assertIn(
                            "--target-file",
                            clause,
                            msg=f"{path.name}: {command} without an explicit local target: {clause}",
                        )

    #: Canonical professor-local identity a transaction record must carry (R64-17).
    TRANSACTION_IDENTITY_FIELDS = ('"professor_dir"', '"preview_path"', '"target_state"')
    #: Sources that carry the Stage 0 -> Stage 1 -> Stage 2 local-target handoff.
    HANDOFF_SOURCES = (STAGE0_AGENT, STAGE1_AGENT, SKILL_PATH, STAGE2_AGENT, STAGE2_CODEX_AGENT)

    @staticmethod
    def _json_blocks(text: str) -> list[str]:
        return re.findall(r"```json\n(.*?)```", text, flags=re.DOTALL)

    def test_issue64_t4_caller_handoff_is_professor_local_transaction_records(self):
        """G64-T4 support (R64-17): every handoff contract carries one record per
        professor-local transaction, identified by canonical paths.

        The main proof is the two-same-name-professors case in
        `test_contact_targets.py`; this assertion only pins the caller-facing
        source contract so a display-name-keyed handoff cannot come back.
        """
        for path in self.HANDOFF_SOURCES:
            text = _read(path)
            with self.subTest(source=str(path.relative_to(REPO_ROOT))):
                self.assertIn('"transactions"', text)
                blocks = self._json_blocks(text)
                self.assertTrue(blocks, msg=f"{path.name}: no JSON contract block")
                carriers = [block for block in blocks
                            if all(field in block for field in self.TRANSACTION_IDENTITY_FIELDS)]
                self.assertTrue(carriers, msg=f"{path.name}: no transaction record example")
        # Pin each authoritative carrier separately, not any unrelated example.
        stage0 = _read(STAGE0_AGENT)
        input_section = stage0.split('## Input', 1)[1].split('## ', 1)[0]
        input_record = json.loads(self._json_blocks(input_section)[0])['transactions']
        self.assertIsInstance(input_record, list)
        self.assertTrue(input_record)
        for record in input_record:
            self.assertTrue({'professor_dir', 'preview_path'} <= record.keys())
        pending_section = stage0.split('When returning `needs_input`', 1)[1]
        pending = json.loads(self._json_blocks(pending_section)[0])['selection_request']
        self.assertIsInstance(pending, list)
        self.assertTrue(pending)
        for record in pending:
            self.assertTrue({'professor_dir', 'preview_path'} <= record.keys())
        for path in (STAGE0_AGENT, STAGE1_AGENT, STAGE2_AGENT, STAGE2_CODEX_AGENT):
            text = _read(path)
            # Return sections follow every input/selection example.
            text = text[text.index('Return'):]
            records = [json.loads(block)['transactions'] for block in self._json_blocks(text)
                       if '"transactions"' in block]
            self.assertTrue(records)
            for carrier in records:
                self.assertIsInstance(carrier, list)
                for record in carrier:
                    self.assertTrue({'professor_dir', 'preview_path', 'target_state'} <= record.keys())

    def test_issue64_t4_no_contract_example_hands_off_targets_keyed_by_display_name(self):
        """A `{"target_states": {"同名教授": ...}}` result silently drops one transaction."""
        for path in self.HANDOFF_SOURCES:
            text = _read(path)
            rel = str(path.relative_to(REPO_ROOT))
            for block in self._json_blocks(text):
                self.assertNotIn("target_states", block, msg=f"{rel}: name-keyed handoff shape")
            for line in text.splitlines():
                if "target_states" in line:
                    self.assertTrue(
                        any(marker in line for marker in ("禁止", "绝不", "不得", "Never", "never")),
                        msg=f"{rel}: name-keyed shape stated as contract: {line}",
                    )

    def test_issue64_t4_stage0_documents_bootstrap_and_revision_split(self):
        """G64-T7 support (R64-4/8): `select` revises only; `bootstrap` establishes."""
        stage0 = _read(STAGE0_AGENT)
        skill = _read(SKILL_PATH)
        for text in (stage0, skill):
            self.assertRegex(
                text,
                r"(?is)bootstrap_required[\s\S]{0,160}(?:zero writes|零写入)",
            )
        self.assertRegex(
            stage0,
            r"(?is)only Stage-0 entry that establishes a professor.s first",
        )

    def test_issue64_t7_retired_program_table_only_appears_as_a_prohibition_or_migration_input(self):
        retired = "教授研究/套磁目标.json"
        prohibition = r'(?i)(?:绝不(?:回退)?读|不读|不得(?:读|写|读取)|Never (?:read|open|write))'
        migration = r'(?:contact_targets\.py (?:bootstrap|migrate)|`bootstrap`)[\s\S]*(?:only|只在|纯迁移)'
        for path in self.HANDOFF_SOURCES:
            text = _read(path)
            lines = [line for line in text.splitlines() if retired in line]
            self.assertTrue(lines, msg=f"{path.name}: retired table never mentioned")
            for line in lines:
                self.assertTrue(
                    re.search(prohibition, line) is not None or (
                        path in self.STAGE01_SOURCES and (
                            re.search(migration, line) is not None or (
                                re.search(r'(?:only|只在|纯迁移)', line) is not None
                                and re.search(r'contact_targets\.py (?:bootstrap|migrate)|`bootstrap`', line)
                            ))),
                    msg=f"{path.name}: {line}",
                )

    def test_issue64_t7_stage0_documents_one_professor_per_transaction_and_partial_results(self):
        text = _read(STAGE0_AGENT)
        self.assertIn("<教授目录>/套磁目标.json", text)
        self.assertRegex(text, r"(?is)one[` ]+select[` ]+call is one professor-local transaction")
        self.assertRegex(text, r"(?is)partial[\s\S]{0,300}(?:never|does not)[\s\S]{0,200}(?:roll back|rolls back)")

    def test_issue64_t7_stage1_resolves_one_professor_per_invocation(self):
        text = _read(STAGE1_AGENT)
        self.assertRegex(
            text,
            r"(?is)one invocation resolves exactly one professor",
        )
        self.assertIn("missing_target_state", text)

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

    def test_stage0_and_stage1_do_not_depend_on_undocumented_call_surfaces(self):
        text = "\n".join((_read(STAGE0_AGENT), _read(STAGE1_AGENT), _read(SKILL_PATH)))

        # `spawn_agent` is documented and stable in Codex's multi-agent tool
        # set, but Stage 0-1 documents must not bind to a concrete tool
        # envelope; named custom-agent delegation is the whole contract
        # (issue #51). `agent_role`/`agent_path` are invented event fields.
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

    def test_issue65_shipped_professor_local_handoff_contract(self):
        # C65-03: every active Stage 0-2 handoff block binds professor-local state.
        # 1. Stage 0's active success result exposes the current professor-local
        #    target, so the transaction identity is a canonical path, not a display name.
        stage0_results = _json_objects(_read(STAGE0_AGENT), "target_states")
        self.assertTrue(
            stage0_results,
            "Stage 0 has no parseable active result block carrying target_states",
        )
        for payload in stage0_results:
            refs = payload["target_states"]
            self.assertIsInstance(refs, dict, f"target_states is not per-professor: {refs}")
            self.assertTrue(refs, "target_states is empty")
            self.assertNotIn("target_state", payload, "one program-level target path is not a handoff")
            for display, value in refs.items():
                _assert_professor_local(value, TARGET_NAME, f"Stage 0 result for {display}")

        # 2. The Stage-1 caller payload passes that local target as business input.
        caller_payloads = _task_prompt(_read(SKILL_PATH), "professor-contact-downloader")
        self.assertTrue(caller_payloads, "no active Stage-1 caller payload in SKILL.md")
        for block in caller_payloads:
            local, program, unbound = _state_reference_scopes(block, TARGET_NAME)
            self.assertTrue(local, f"Stage-1 caller payload has no local target: {block}")
            self.assertEqual(program, [], f"Stage-1 caller payload points at the program table: {block}")
            self.assertEqual(unbound, [], f"Stage-1 caller target is display-name-only: {block}")
            self.assertEqual(
                _state_reference_scopes(block, STAGE1_STATE_NAME)[1],
                [],
                f"Stage-1 caller payload requires a program-wide Stage-1 authority: {block}",
            )

        # 3. The downloader's active Stage-1 commands bind the local target, and its
        #    active return names the local Stage-1 owner.
        downloader_text = _read(STAGE1_AGENT)
        stage1_commands = [
            block for block in _bash_blocks(downloader_text) if "contact_stage1.py" in block
        ]
        self.assertTrue(stage1_commands, "downloader has no active contact_stage1.py command")
        for block in stage1_commands:
            flags = re.findall(r'--target-file\s+"([^"]+)"', block)
            self.assertTrue(flags, f"contact_stage1.py invoked without a local target: {block}")
            for value in flags:
                _assert_professor_local(value, TARGET_NAME, "downloader Stage-1 command")
            self.assertEqual(
                _state_reference_scopes(block, STAGE1_STATE_NAME)[1],
                [],
                f"downloader Stage-1 command reads the program-level snapshot: {block}",
            )
        returned = _json_objects(downloader_text, "stage1_snapshots")
        self.assertTrue(returned, "downloader return has no per-professor stage1_snapshots field")
        for payload in returned:
            refs = payload["stage1_snapshots"]
            self.assertIsInstance(refs, dict, f"downloader stage1_snapshots is not per-professor: {refs}")
            self.assertTrue(refs, "downloader stage1_snapshots is empty")
            for display, value in refs.items():
                _assert_professor_local(
                    value, STAGE1_STATE_NAME, f"downloader Stage-1 state for {display}"
                )

        # 4. Both shipped analyzer projections bind Stage 2 to the local target plus
        #    the exact local Stage-1 state.
        for agent in (STAGE2_AGENT, STAGE2_CODEX_AGENT):
            with self.subTest(analyzer=str(agent.relative_to(REPO_ROOT))):
                text = _read(agent)
                active = _bash_blocks(text)
                stage1_verify = [b for b in active if "contact_stage1.py" in b and "verify" in b]
                preflight = [b for b in active if "stage2-preflight" in b]
                self.assertTrue(
                    stage1_verify, f"{agent.name}: no active contact_stage1.py verify command"
                )
                self.assertTrue(preflight, f"{agent.name}: no active stage2-preflight command")
                for block in stage1_verify + preflight:
                    flags = re.findall(r'--target-file\s+"([^"]+)"', block)
                    self.assertTrue(
                        flags, f"{agent.name}: Stage-2 command without a local target: {block}"
                    )
                    for value in flags:
                        _assert_professor_local(value, TARGET_NAME, f"{agent.name} Stage-2 command")
                    self.assertEqual(
                        _state_reference_scopes(block, STAGE1_STATE_NAME)[1],
                        [],
                        f"{agent.name} Stage-2 command reads the program-level snapshot: {block}",
                    )
                self.assertEqual(
                    _state_reference_scopes("\n".join(_fenced(text)), STAGE1_STATE_NAME)[1],
                    [],
                    f"{agent.name}: an active block still names the program-level Stage-1 state",
                )
                stage2_returns = _json_objects(text, "stage1_snapshots")
                self.assertTrue(
                    stage2_returns,
                    f"{agent.name} return does not expose the consumed local Stage-1 state",
                )
                for payload in stage2_returns:
                    refs = payload["stage1_snapshots"]
                    self.assertIsInstance(refs, dict, f"stage1_snapshots is not per-professor: {refs}")
                    self.assertTrue(refs, "stage1_snapshots is empty")
                    for display, value in refs.items():
                        _assert_professor_local(
                            value, STAGE1_STATE_NAME, f"{agent.name} Stage-1 state for {display}"
                        )

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
