from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"
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
