from pathlib import Path
import json
import re
import tomllib
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"
OPENCode_AGENT_DIR = REPO_ROOT / "packages" / "professor-contact-opencode" / ".apm" / "agents"
CODEX_AGENT_DIR = REPO_ROOT / "packages" / "professor-contact-codex" / ".apm" / "agents"
ANALYZER_PATH = OPENCode_AGENT_DIR / "professor-contact-analyzer.agent.md"
MANIFEST_PATH = REPO_ROOT / "apm.yml"

# Machine identities of the 8 source agents; install projections (Codex TOML /
# OpenCode md) are keyed by these exact names.
EXPECTED_AGENT_NAMES = (
    "professor-contact",
    "professor-contact-downloader",
    "professor-contact-analyzer",
    "professor-contact-idea-generator",
    "professor-contact-selection",
    "professor-contact-email-generator",
    "professor-contact-email-validator",
    "professor-contact-style-validator",
)


def _source_agent_paths():
    return sorted(AGENTS_DIR.glob("*.agent.md")) + [
        OPENCode_AGENT_DIR / "professor-contact-analyzer.agent.md",
        CODEX_AGENT_DIR / "professor-contact-analyzer.agent.md",
    ]


def _source_agent_by_name():
    paths = {}
    for path in sorted(AGENTS_DIR.glob("*.agent.md")) + [ANALYZER_PATH]:
        frontmatter, _ = _frontmatter_and_body(path)
        fields = _top_level_fields(frontmatter)
        name = fields.get("name", "")
        if name in paths:
            raise AssertionError(f"duplicate source agent machine name {name!r}")
        paths[name] = path
    return paths

# Caller-facing stage agents (the two validators are invoked by their owning
# stage agents, not by the caller).
STAGE_AGENT_NAMES = (
    "professor-contact",
    "professor-contact-downloader",
    "professor-contact-analyzer",
    "professor-contact-idea-generator",
    "professor-contact-selection",
    "professor-contact-email-generator",
)

# Direct APM dependencies locked by the #27 clean-install closure audit.
# humanizer-ja (stage 5) and vision-tools (stage 2 OCR chain) are consumed by
# name and are provided by ScholarWorkflow/base-skills.
EXPECTED_DEPENDENCIES = (
    "ScholarWorkflow/zotero-tools",
    "ScholarWorkflow/knowledge-tools",
    "ScholarWorkflow/paper-analysis",
    "ScholarWorkflow/pdf-processing-core",
    "ScholarWorkflow/professor-research",
    "ScholarWorkflow/base-skills",
)


def _frontmatter_and_body(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path}: missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError(f"{path}: missing closing frontmatter delimiter") from exc
    return lines[1:end], "\n".join(lines[end + 1 :]).strip()


def _top_level_fields(frontmatter_lines):
    fields = {}
    for line in frontmatter_lines:
        if not line or line[0].isspace():
            continue
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def _assert_yaml_safe_description(testcase: unittest.TestCase, path: Path, value: str):
    testcase.assertTrue(value, f"{path}: description must be non-empty")

    if value.startswith("'"):
        testcase.assertTrue(value.endswith("'"), f"{path}: unterminated single-quoted description")
        inner = value[1:-1]
        i = 0
        while i < len(inner):
            if inner[i] == "'":
                testcase.assertLess(i + 1, len(inner), f"{path}: single quote must be doubled")
                testcase.assertEqual(inner[i + 1], "'", f"{path}: single quote must be doubled")
                i += 2
            else:
                i += 1
        return

    if value.startswith('"'):
        testcase.assertTrue(value.endswith('"'), f"{path}: unterminated double-quoted description")
        return

    if value.startswith(("|", ">")):
        return

    # YAML plain scalars treat `: ` as a mapping indicator and ` #` as a
    # comment boundary. Either can invalidate or silently truncate an agent
    # description, so descriptions containing them must be quoted.
    testcase.assertNotIn(": ", value, f"{path}: description containing ': ' must be quoted")
    testcase.assertNotIn(" #", value, f"{path}: description containing ' #' must be quoted")


def _target_branch(text: str, heading: str, next_heading: str | None = None) -> str:
    start = text.index(heading)
    if next_heading is not None:
        end = text.index(next_heading, start + len(heading))
    else:
        match = re.search(r"(?m)^#{1,3}\s+", text[start + len(heading) :])
        end = len(text) if match is None else start + len(heading) + match.start()
    return text[start:end]


# Delegation-discovery hard gate (PC47-R2-DELEGATION-DISCOVERY-01): the Codex
# analyzer observed in R2 judged delegation unavailable with zero delegation
# attempts. The production contract must force it to discover the runtime's
# native multi-agent delegation surface first, delegate the exact installed
# names after discovery, and fail closed only on a machine-level failure.
CODEX_DISCOVERY_GATE_MARKERS = (
    "在判定 delegation unavailable 之前",
    "Code Mode / programmatic tool-calling discovery surface",
    "发现当前 session 实际可调用的原生 multi-agent delegation capability",
    "不得硬编码版本私有的 spawn JSON schema、固定 namespace 名或私有工具名",
    "必须按既有业务 contract 用 **exact installed name** 真正发起委派并等待结果",
    "Code Mode `exec` 作为 programmatic tool caller 是允许的",
    "`exec` shell 子进程、`curl`、另起 eval 会话都不是 native delegation 的替代路径",
)

# The fail-closed reason code may only be emitted after discovery plus an
# actual native delegation attempt returned a machine-level failure; the
# model's own "no interface" impression is never machine evidence.
CODEX_DELEGATION_REASON_CODE = "codex_runtime_delegation_unavailable"


def _assert_codex_discovery_gate(codex: str):
    for marker in CODEX_DISCOVERY_GATE_MARKERS:
        assert marker in codex, f"missing discovery-gate marker: {marker}"

    reason_lines = [
        line for line in codex.splitlines() if CODEX_DELEGATION_REASON_CODE in line
    ]
    assert reason_lines, "the fail-closed reason code must be named in the Codex branch"
    for line in reason_lines:
        assert "discovery" in line, f"reason code line lacks discovery semantics: {line}"
        assert "实际尝试" in line, f"reason code line lacks actual-attempt semantics: {line}"
        assert (
            "machine-level failure" in line or "机器级失败" in line
        ), f"reason code line lacks machine-level-failure semantics: {line}"
        assert "没看到接口" in line, (
            f"reason code line must name the forbidden 'no interface' shortcut: {line}"
        )


class ApmDeploymentMetadataTests(unittest.TestCase):
    def test_manifest_keeps_opencode_and_codex_targets(self):
        manifest = (REPO_ROOT / "apm.yml").read_text(encoding="utf-8")
        match = re.search(r"(?m)^targets:\s*\[([^\]]+)\]\s*$", manifest)
        self.assertIsNotNone(match, "apm.yml must declare explicit inline targets")
        targets = [part.strip() for part in match.group(1).split(",") if part.strip()]
        self.assertEqual(targets, ["opencode", "codex"])

    def test_all_agent_frontmatter_descriptions_are_yaml_safe(self):
        agent_paths = _source_agent_paths()
        self.assertTrue(agent_paths, "expected at least one .apm/agents/*.agent.md file")

        for path in agent_paths:
            with self.subTest(agent=path.name):
                frontmatter, body = _frontmatter_and_body(path)
                fields = _top_level_fields(frontmatter)
                self.assertTrue(fields.get("name"), f"{path}: name must be non-empty")
                _assert_yaml_safe_description(self, path, fields.get("description", ""))
                self.assertTrue(body, f"{path}: agent body must be non-empty")

    def test_all_eight_source_agents_exist_with_exact_machine_names(self):
        names = {}
        for path in AGENTS_DIR.glob("*.agent.md"):
            frontmatter, _ = _frontmatter_and_body(path)
            fields = _top_level_fields(frontmatter)
            name = fields.get("name", "")
            self.assertTrue(name, f"{path}: frontmatter name must be non-empty")
            if name in names:
                self.fail(f"{path}: duplicate agent machine name {name!r} (already in {names[name]})")
            names[name] = path.name

        self.assertEqual(
            set(names), set(EXPECTED_AGENT_NAMES) - {"professor-contact-analyzer"},
            "the root source set must contain the 7 shared agents; analyzer projections are target-scoped",
        )
        for package_dir in (OPENCode_AGENT_DIR, CODEX_AGENT_DIR):
            path = package_dir / "professor-contact-analyzer.agent.md"
            self.assertTrue(path.exists(), f"missing target-scoped analyzer {path}")
            frontmatter, _ = _frontmatter_and_body(path)
            fields = _top_level_fields(frontmatter)
            self.assertEqual(fields.get("name"), "professor-contact-analyzer")

        for expected in EXPECTED_AGENT_NAMES:
            if expected == "professor-contact-analyzer":
                continue
            self.assertIn(expected, names, f"missing source agent {expected!r}")

    def test_opencode_native_frontmatter_is_preserved(self):
        for name in EXPECTED_AGENT_NAMES:
            with self.subTest(agent=name):
                path = _source_agent_by_name()[name]
                self.assertTrue(path.exists(), f"{path}: source agent must exist")
                frontmatter, _ = _frontmatter_and_body(path)
                fields = _top_level_fields(frontmatter)
                # Minimal OpenCode-native contract: hidden subagents reachable
                # via OpenCode's native Task delegation. Codex compatibility
                # must never strip these.
                self.assertEqual(fields.get("mode"), "subagent", f"{path}: mode")
                self.assertEqual(fields.get("hidden"), "true", f"{path}: hidden")

    def test_stage2_analyzer_preserves_opencode_task_and_question_permissions(self):
        frontmatter, _ = _frontmatter_and_body(ANALYZER_PATH)
        frontmatter_text = "\n".join(frontmatter)
        self.assertRegex(
            frontmatter_text,
            r"(?ms)^permission:\s*$.*?^\s+task:\s*allow\s*$",
            "Stage 2 analyzer must remain callable through OpenCode's documented Task permission",
        )
        self.assertRegex(
            frontmatter_text,
            r"(?ms)^permission:\s*$.*?^\s+question:\s*allow\s*$",
            "OpenCode's existing interactive user-choice capability must not be removed by the Codex migration",
        )

    def test_skill_caller_convention_is_target_aware(self):
        skill = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("### OpenCode 分支", skill, "OpenCode caller branch must be explicit")
        self.assertIn("### Codex 分支", skill, "Codex caller branch must be explicit")
        self.assertIn("### 共享调用表", skill, "shared stage -> agent table must be explicit")

        opencode_branch = skill.index("### OpenCode 分支")
        codex_branch = skill.index("### Codex 分支")
        self.assertLess(opencode_branch, codex_branch)

        for name in STAGE_AGENT_NAMES:
            self.assertIn(f"`{name}`", skill, f"shared caller table must name {name!r}")

        # The legacy cross-target claim (OpenCode's hidden + Task tool being
        # presented as the unified truth) must be gone.
        self.assertNotIn("the ONLY way", skill)
        self.assertNotIn("the Task tool is the ONLY way", skill)
        self.assertNotRegex(skill, r"spawn_agent\s*\(")
        self.assertNotIn("agent_role", skill)
        self.assertNotIn("agent_path", skill)

    def test_skill_task_tool_examples_stay_inside_the_opencode_branch(self):
        skill = SKILL_PATH.read_text(encoding="utf-8")
        opencode_branch = skill.index("### OpenCode 分支")
        codex_branch = skill.index("### Codex 分支")

        for match in re.finditer(r"task\(subagent_type", skill):
            self.assertGreaterEqual(
                match.start(),
                opencode_branch,
                "task(subagent_type: ...) examples must live in the OpenCode branch",
            )
            self.assertLess(
                match.start(),
                codex_branch,
                "task(subagent_type: ...) examples must not leak into the Codex branch",
            )

    def test_stage2_analyzer_has_explicit_target_specific_delegation_contract(self):
        _, analyzer = _frontmatter_and_body(ANALYZER_PATH)
        self.assertIn("### OpenCode 分支", analyzer, "Stage 2 analyzer must explain its OpenCode delegation path")
        self.assertIn("### Codex 分支", analyzer, "Stage 2 analyzer must explain its Codex delegation path")

        opencode = _target_branch(analyzer, "### OpenCode 分支", "### Codex 分支")
        codex = _target_branch(analyzer, "### Codex 分支")

        for delegated_name in ("paper-analysis", "professor-contact-style-validator"):
            self.assertIn(delegated_name, opencode, f"OpenCode branch must retain delegation to {delegated_name}")
            self.assertIn(delegated_name, codex, f"Codex branch must delegate to installed custom agent {delegated_name}")

        self.assertIn(
            "subagent_depth",
            opencode,
            "OpenCode branch must retain the documented nested-subagent depth budget needed by Stage 2",
        )
        self.assertTrue(
            "name" in codex.lower() or "机器名" in codex,
            "Codex branch must identify installed custom agents by their configured name",
        )

        # These are OpenCode/runtime-local concepts or invented observability
        # fields. Codex's documented contract is named custom agents plus the
        # normal subagent workflow; do not present these as Codex APIs.
        self.assertNotIn("subagent_depth", codex)
        self.assertNotRegex(codex, r"task\s*\(")
        self.assertNotRegex(codex, r"question\s*\(")
        self.assertNotRegex(codex, r"spawn_agent\s*\(")
        self.assertNotIn("agent_role", codex)
        self.assertNotIn("agent_path", codex)

    def test_stage2_codex_noninteractive_choice_uses_fresh_root_and_persisted_state(self):
        _, analyzer = _frontmatter_and_body(ANALYZER_PATH)
        skill = SKILL_PATH.read_text(encoding="utf-8")
        stage2_docs = f"{skill}\n{analyzer}"

        # The Codex eval harness runs one fresh root thread per invocation and
        # does not support session resume; Stage 2 user-choice continuity must
        # therefore never be documented as session resume.
        self.assertNotIn(
            "codex exec resume",
            stage2_docs,
            "session resume must not be the documented Stage 2 Codex user-choice continuation path",
        )
        self.assertTrue(
            "needs_input" in stage2_docs or "needs_user_choice" in stage2_docs,
            "the first non-interactive pass must stop at an explicit needs-input state rather than auto-accepting",
        )
        self.assertIn(
            "fresh root",
            stage2_docs,
            "Stage 2 Codex continuation must be described as fresh-root runs",
        )
        self.assertRegex(
            stage2_docs,
            r"(?s)fresh root.{0,600}(facts|指纹|proof)",
            "the fresh-root second pass must rely on persisted deterministic Stage 2 state",
        )
        self.assertRegex(
            stage2_docs,
            r"(?s)fresh root.{0,400}同一 program root",
            "the fresh-root second pass must re-read the same program root",
        )
        self.assertRegex(
            stage2_docs,
            r"显式(提供)?用户选择",
            "the fresh-root second pass must be driven by an explicit user selection",
        )

    def test_stage2_analyzer_keeps_business_concurrency_limit_separate_from_codex_thread_limit(self):
        _, analyzer = _frontmatter_and_body(ANALYZER_PATH)
        self.assertRegex(
            analyzer,
            r"(?:同时|同批)[^\n]{0,80}最多[^\n]{0,40}(?:\*\*)?3(?:\*\*)?[^\n]{0,80}paper-analysis",
            "Stage 2 must retain its business rule of at most three concurrent paper-analysis jobs",
        )

        codex = _target_branch(analyzer, "### Codex 分支")
        if "max_concurrent_threads_per_session" in codex:
            self.assertRegex(
                codex,
                r"(?s)max_concurrent_threads_per_session.{0,240}(?:不等价|not equivalent|不是)",
                "Codex's global thread limit must not be described as the Stage 2 paper-analysis concurrency rule",
            )

    def _codex_analyzer_branch(self):
        _, analyzer = _frontmatter_and_body(
            CODEX_AGENT_DIR / "professor-contact-analyzer.agent.md"
        )
        return _target_branch(analyzer, "### Codex 分支")

    def test_codex_analyzer_requires_runtime_subagent_delegation(self):
        codex = self._codex_analyzer_branch()
        self.assertRegex(
            codex,
            r"(?s)当前 Codex session.{0,240}subagent delegation capability",
            "Codex Stage 2 must require the delegation capability actually provided by the current session",
        )

    def test_codex_analyzer_does_not_equate_missing_opencode_task_with_no_delegation(self):
        codex = self._codex_analyzer_branch()
        self.assertRegex(
            codex,
            r"(?s)OpenCode.*task.{0,180}(?:无关|not related|不等于)",
            "the Codex branch must say that OpenCode task syntax is unrelated to Codex delegation availability",
        )

    def test_codex_analyzer_requires_machine_failure_before_runtime_blocker(self):
        codex = self._codex_analyzer_branch()
        self.assertRegex(
            codex,
            r"(?s)实际尝试.{0,220}(?:机器级失败|machine-level failure).{0,180}(?:blocker|阻塞)",
            "a runtime blocker requires an attempted delegation and a machine-level failure",
        )

    def test_codex_analyzer_requires_discovery_before_delegation_unavailable(self):
        _assert_codex_discovery_gate(self._codex_analyzer_branch())

    def test_codex_discovery_gate_markers_are_load_bearing(self):
        codex = self._codex_analyzer_branch()
        for marker in CODEX_DISCOVERY_GATE_MARKERS:
            with self.subTest(marker=marker):
                mutated = codex.replace(marker, "")
                with self.assertRaises(AssertionError):
                    _assert_codex_discovery_gate(mutated)

    def test_codex_reason_code_semantics_are_load_bearing(self):
        codex = self._codex_analyzer_branch()
        reason_line = next(
            line for line in codex.splitlines() if CODEX_DELEGATION_REASON_CODE in line
        )
        for drop in ("discovery", "实际尝试", "machine-level failure", "没看到接口"):
            with self.subTest(dropped=drop):
                mutated_line = reason_line.replace(drop, "")
                mutated = codex.replace(reason_line, mutated_line)
                with self.assertRaises(AssertionError):
                    _assert_codex_discovery_gate(mutated)

    def test_codex_delegation_discovery_gate_survives_install_toml_projection(self):
        """The clean-install writes the Codex projection body into the
        generated ``.codex/agents/professor-contact-analyzer.toml``
        ``developer_instructions`` (frontmatter stripped, edge newlines
        normalized, TOML basic-string escaped). Gate the discovery markers on
        that payload shape, not only on the source Markdown."""
        path = CODEX_AGENT_DIR / "professor-contact-analyzer.agent.md"
        frontmatter, body = _frontmatter_and_body(path)
        fields = _top_level_fields(frontmatter)
        instructions = body.strip("\n")

        # JSON basic-string escaping is TOML basic-string escaping for the
        # escapes json.dumps emits (\b\t\n\f\r\"\\\uXXXX), so the rendered
        # document below is exactly the TOML the installer writes.
        toml_text = (
            f"name = {json.dumps(fields['name'])}\n"
            f"description = {json.dumps(fields['description'])}\n"
            f"developer_instructions = {json.dumps(instructions)}\n"
        )
        parsed = tomllib.loads(toml_text)
        self.assertEqual(parsed["name"], "professor-contact-analyzer")
        self.assertEqual(parsed["developer_instructions"], instructions)
        _assert_codex_discovery_gate(parsed["developer_instructions"])

    def test_codex_discovery_gate_stays_out_of_the_opencode_projection(self):
        _, body = _frontmatter_and_body(ANALYZER_PATH)
        self.assertNotIn(
            "Code Mode / programmatic tool-calling discovery surface",
            body,
            "the delegation-discovery gate is Codex-branch contract; the OpenCode "
            "projection keeps its native Task/question/permission contract",
        )

    def test_codex_analyzer_keeps_exact_paper_analysis_role(self):
        codex = self._codex_analyzer_branch()
        self.assertRegex(
            codex,
            r"exact installed name [`']?paper-analysis[`']?",
            "Codex must delegate to the exact installed paper-analysis role",
        )

    def test_codex_analyzer_does_not_inline_paper_analysis(self):
        codex = self._codex_analyzer_branch()
        self.assertRegex(
            codex,
            r"(?s)(?:不得|不).*?(?:inline|模拟执行).*?paper-analysis",
            "Codex analyzer must not inline or simulate paper-analysis",
        )

    def test_codex_analyzer_does_not_hardcode_internal_spawn_api(self):
        codex = self._codex_analyzer_branch()
        for forbidden in (
            "multi_agent_v1__",
            "ALL_TOOLS",
            "multi_agent_v1__spawn_agent",
            "spawnAgent",
            "spawn_agent",
            "collabAgentToolCall",
            "receiverThreadIds",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    codex,
                    "the Codex product contract must not hard-code internal runtime APIs",
                )

    # Phrases that suppress paper-analysis's contract-required internal leaf
    # delegation. They may appear in an analyzer contract only inside the rule
    # that forbids writing them into a caller prompt.
    DELEGATION_SUPPRESSING_PHRASES = (
        "不要委派更深层代理",
        "不要启动子代理",
        "禁止继续 spawn",
    )

    def _analyzer_projections(self):
        for package_dir in (OPENCode_AGENT_DIR, CODEX_AGENT_DIR):
            path = package_dir / "professor-contact-analyzer.agent.md"
            _, body = _frontmatter_and_body(path)
            yield path, body

    def test_analyzer_depth_boundary_starts_at_paper_analysis_leaves(self):
        for path, body in self._analyzer_projections():
            with self.subTest(projection=path.parents[2].name):
                self.assertIn(
                    "从 `paper-analysis` 自己的只读分析叶子开始",
                    body,
                    "the depth budget must place the no-deeper boundary at paper-analysis's leaves",
                )
                self.assertIn(
                    "不从 `paper-analysis` coordinator 开始",
                    body,
                    "the depth budget must not stop paper-analysis's own coordination",
                )
                self.assertIn(
                    "叶子必须是终点",
                    body,
                    "leaves must be documented as the terminal delegation level",
                )

    def test_top_level_recursion_clause_subjects_analyzer_not_the_chain(self):
        recursion_lines = []
        for path, body in self._analyzer_projections():
            with self.subTest(projection=path.parents[2].name):
                line = next(
                    (text for text in body.splitlines() if "绝不递归" in text),
                    None,
                )
                self.assertIsNotNone(
                    line,
                    "the top-level recursion clause must exist in each projection",
                )
                # The former parenthetical disjunct banned leaf spawning with no
                # subject, so the whole chain could be misread as unable to spawn
                # the leaves; the ban must name analyzer as the only spawner.
                self.assertNotIn(
                    "、不 spawn `paper-analysis` 的内部叶子",
                    line,
                    "the leaf-spawn ban must not stand without an explicit analyzer subject",
                )
                self.assertIn(
                    "绝不递归：analyzer 不加载 `paper-analysis` skill",
                    line,
                    "the recursion clause must name analyzer as the subject of the skill ban",
                )
                self.assertIn(
                    "也不由 analyzer 自己直接 spawn `paper-analysis` 的内部叶子",
                    line,
                    "the leaf-spawn ban must name analyzer itself as the only forbidden spawner",
                )
                self.assertIn(
                    "`paper-analysis` coordinator 必须按其自身正式 contract 的 Step 3 自行启动 3 个只读分析叶子",
                    line,
                    "the recursion clause must keep paper-analysis's coordinator duty explicit",
                )
                self.assertIn(
                    "这些叶子不得再继续委派",
                    line,
                    "leaves must stay terminal in the same sentence that lifts the coordinator ban",
                )
                recursion_lines.append(line)
        self.assertEqual(
            recursion_lines[0],
            recursion_lines[1],
            "the recursion clause is shared text and must stay byte-identical across projections",
        )

    def test_analyzer_requires_paper_analysis_full_mode_leaf_delegation(self):
        for path, body in self._analyzer_projections():
            with self.subTest(projection=path.parents[2].name):
                self.assertIn(
                    "允许且要求的委派链",
                    body,
                    "the contract must allow and require analyzer -> paper-analysis -> leaves",
                )
                self.assertRegex(
                    body,
                    r"full mode 下 `paper-analysis` 是 coordinator",
                    "full-mode paper-analysis must be documented as the coordinator of its own leaves",
                )
                self.assertRegex(
                    body,
                    r"按它自身正式 contract 的 Step 3",
                    "leaf delegation must stay owned by paper-analysis's own contract",
                )

    def test_analyzer_contract_confines_suppression_phrases_to_the_prohibition_rule(self):
        for path, body in self._analyzer_projections():
            with self.subTest(projection=path.parents[2].name):
                hits = [
                    line
                    for line in body.splitlines()
                    if any(phrase in line for phrase in self.DELEGATION_SUPPRESSING_PHRASES)
                ]
                self.assertTrue(
                    hits,
                    "the contract must explicitly enumerate the suppression semantics it forbids",
                )
                for line in hits:
                    self.assertIn(
                        "绝不写入",
                        line,
                        "suppression phrases are only allowed inside the forbid-writing rule",
                    )
                    self.assertIn("阻止", line)
                    self.assertIn("paper-analysis", line)

    def test_analyzer_caller_prompt_carries_business_inputs_only(self):
        for path, body in self._analyzer_projections():
            with self.subTest(projection=path.parents[2].name):
                self.assertRegex(
                    body,
                    r"(?:Task/)?委派 prompt 只装业务输入，不装编排约束",
                    "caller prompts must carry business inputs only, not orchestration constraints",
                )
                self.assertRegex(
                    body,
                    r"research_direction_file",
                    "the business-input enumeration must keep the existing Input contract parameters",
                )
                self.assertIn(
                    "绝不重写、裁剪或覆盖 `paper-analysis` 自身的内部 orchestration 规则",
                    body,
                    "caller prompts must not rewrite or override paper-analysis's internal orchestration",
                )

    def test_depth_guard_targets_leaves_not_the_coordinator(self):
        codex = self._codex_analyzer_branch()
        self.assertRegex(
            codex,
            r"analyzer 不递归 spawn analyzer",
            "the depth guard must forbid analyzer self-recursion",
        )
        self.assertRegex(
            codex,
            r"analyzer 不 spawn `paper-analysis` 的内部叶子",
            "the depth guard must forbid analyzer spawning paper-analysis's leaves",
        )
        self.assertRegex(
            codex,
            r"analyzer 不要求叶子再继续分派",
            "the depth guard must forbid analyzer demanding further dispatch from leaves",
        )
        self.assertRegex(
            codex,
            r"`paper-analysis` coordinator 仍按自己的正式 contract 负责启动其 3 个只读叶子",
            "the depth guard must keep paper-analysis's own coordinator duty intact",
        )

    def test_spawn_api_names_stay_out_of_both_analyzer_projections(self):
        for path, body in self._analyzer_projections():
            with self.subTest(projection=path.parents[2].name):
                for forbidden in (
                    "multi_agent_v1__",
                    "ALL_TOOLS",
                    "multi_agent_v1__spawn_agent",
                    "spawnAgent",
                    "spawn_agent",
                    "collabAgentToolCall",
                    "receiverThreadIds",
                ):
                    self.assertNotIn(
                        forbidden,
                        body,
                        "Codex internal spawn tool/event names must not enter either projection",
                    )

    def test_opencode_task_delegation_branch_survives_the_depth_boundary_fix(self):
        _, body = _frontmatter_and_body(ANALYZER_PATH)
        opencode = _target_branch(body, "### OpenCode 分支", "### Codex 分支")
        self.assertIn(
            "用 OpenCode 官方 Task 委派方式启动 `paper-analysis`",
            opencode,
            "the OpenCode Task delegation path must remain the documented mechanism",
        )
        self.assertIn(
            "subagent_depth",
            opencode,
            "the OpenCode depth budget documentation must remain",
        )

    def test_no_scholarflow_codex_dependency_is_introduced(self):
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertNotIn("scholarflow-codex", manifest.lower())
        self.assertNotIn("scholarflow-codex", SKILL_PATH.read_text(encoding="utf-8").lower())
        for path in _source_agent_paths():
            self.assertNotIn(
                "scholarflow-codex",
                path.read_text(encoding="utf-8").lower(),
                f"{path}: scholarflow-codex must not appear in agent sources",
            )

    def test_declared_dependencies_match_the_audited_closure(self):
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        deps = re.findall(r"(?m)^\s*-\s+(ScholarWorkflow/[\w-]+)\s*$", manifest)
        self.assertEqual(
            tuple(deps),
            EXPECTED_DEPENDENCIES,
            "apm.yml dependencies must stay exactly the audited direct closure",
        )


if __name__ == "__main__":
    unittest.main()
