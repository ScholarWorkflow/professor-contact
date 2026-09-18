from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"
ANALYZER_PATH = AGENTS_DIR / "professor-contact-analyzer.agent.md"
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


class ApmDeploymentMetadataTests(unittest.TestCase):
    def test_manifest_keeps_opencode_and_codex_targets(self):
        manifest = (REPO_ROOT / "apm.yml").read_text(encoding="utf-8")
        match = re.search(r"(?m)^targets:\s*\[([^\]]+)\]\s*$", manifest)
        self.assertIsNotNone(match, "apm.yml must declare explicit inline targets")
        targets = [part.strip() for part in match.group(1).split(",") if part.strip()]
        self.assertEqual(targets, ["opencode", "codex"])

    def test_all_agent_frontmatter_descriptions_are_yaml_safe(self):
        agent_paths = sorted(AGENTS_DIR.glob("*.agent.md"))
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

        for expected in EXPECTED_AGENT_NAMES:
            self.assertIn(expected, names, f"missing source agent {expected!r}")
        self.assertEqual(
            set(names),
            set(EXPECTED_AGENT_NAMES),
            "the .apm/agents source set must be exactly the 8 professor-contact agents",
        )

    def test_opencode_native_frontmatter_is_preserved(self):
        for name in EXPECTED_AGENT_NAMES:
            with self.subTest(agent=name):
                path = AGENTS_DIR / f"{name}.agent.md"
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
        # `spawn_agent` is a documented, stable Codex multi-agent tool name;
        # the caller convention stays off it so the business contract never
        # binds to one specific tool envelope (issue #51), not because the
        # name were private.
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

        # `subagent_depth`, Task and question are OpenCode/runtime-local
        # concepts; `agent_role`/`agent_path` are invented observability
        # fields. `spawn_agent` is a documented Codex multi-agent tool, but
        # the business branch must not bind to its concrete envelope — the
        # documented named-custom-agent contract is the whole API (issue #51).
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

    def test_no_scholarflow_codex_dependency_is_introduced(self):
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertNotIn("scholarflow-codex", manifest.lower())
        self.assertNotIn("scholarflow-codex", SKILL_PATH.read_text(encoding="utf-8").lower())
        for path in sorted(AGENTS_DIR.glob("*.agent.md")):
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
