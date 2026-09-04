from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"


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


if __name__ == "__main__":
    unittest.main()
