from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
ROOT_AGENTS = REPO_ROOT / ".apm" / "agents"
OPENCode_PACKAGE = REPO_ROOT / "packages" / "professor-contact-opencode"
CODEX_PACKAGE = REPO_ROOT / "packages" / "professor-contact-codex"
ANALYZER_NAME = "professor-contact-analyzer"


def _frontmatter_and_body(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path}: missing opening frontmatter delimiter")
    end = lines.index("---", 1)
    return lines[1:end], "\n".join(lines[end + 1 :]).strip()


def _fields(lines):
    result = {}
    for line in lines:
        if line and not line[0].isspace():
            key, separator, value = line.partition(":")
            if separator:
                result[key.strip()] = value.strip()
    return result


def _manifest_fields(path: Path):
    text = path.read_text(encoding="utf-8")
    name = re.search(r"(?m)^name:\s*(\S+)\s*$", text)
    targets = re.search(r"(?m)^targets:\s*\[([^\]]+)\]\s*$", text)
    if name is None or targets is None:
        raise AssertionError(f"{path}: package manifest must declare name and inline targets")
    return name.group(1), [part.strip() for part in targets.group(1).split(",") if part.strip()]


class P47TargetIsolationTests(unittest.TestCase):
    """Lock the target-specific Stage 2 projection required by PR #47."""

    def test_target_packages_have_exact_scopes_and_single_stage2_projection(self):
        self.assertTrue(OPENCode_PACKAGE.exists(), "OpenCode target package is missing")
        self.assertTrue(CODEX_PACKAGE.exists(), "Codex target package is missing")
        self.assertEqual(
            _manifest_fields(OPENCode_PACKAGE / "apm.yml"),
            ("professor-contact-opencode", ["opencode"]),
        )
        self.assertEqual(
            _manifest_fields(CODEX_PACKAGE / "apm.yml"),
            ("professor-contact-codex", ["codex"]),
        )

        root_analyzer = ROOT_AGENTS / f"{ANALYZER_NAME}.agent.md"
        self.assertFalse(
            root_analyzer.exists(),
            "the mixed analyzer must not remain in the root dual-target projection",
        )
        for package in (OPENCode_PACKAGE, CODEX_PACKAGE):
            path = package / ".apm" / "agents" / f"{ANALYZER_NAME}.agent.md"
            self.assertTrue(path.exists(), f"missing target-specific analyzer: {path}")
            frontmatter, body = _frontmatter_and_body(path)
            fields = _fields(frontmatter)
            self.assertEqual(fields.get("name"), ANALYZER_NAME)
            self.assertEqual(fields.get("mode"), "subagent")
            self.assertEqual(fields.get("hidden"), "true")
            self.assertTrue(body)

    def test_opencode_projection_preserves_native_delegation_contract(self):
        path = OPENCode_PACKAGE / ".apm" / "agents" / f"{ANALYZER_NAME}.agent.md"
        frontmatter, body = _frontmatter_and_body(path)
        frontmatter_text = "\n".join(frontmatter)
        self.assertRegex(frontmatter_text, r"(?ms)^permission:\s*$.*?^\s+task:\s*allow\s*$")
        self.assertRegex(frontmatter_text, r"(?ms)^permission:\s*$.*?^\s+question:\s*allow\s*$")
        self.assertIn("### OpenCode 分支", body)
        self.assertIn("### Codex 分支", body)
        self.assertRegex(body, r"task\s*\(")

    def test_codex_projection_is_named_agent_only_and_keeps_stage2_delegation(self):
        path = CODEX_PACKAGE / ".apm" / "agents" / f"{ANALYZER_NAME}.agent.md"
        _, body = _frontmatter_and_body(path)
        self.assertIn("Codex", body)
        self.assertIn("paper-analysis", body)
        self.assertIn("professor-contact-style-validator", body)
        self.assertRegex(body, r"(?is)(?:delegate|use|委派)[\s\S]{0,500}(?:wait|等待)")
        for forbidden in ("task(", "question(", "spawn_agent(", "spawnAgent"):
            self.assertNotIn(forbidden, body, f"Codex projection leaked OpenCode API {forbidden!r}")
        # #57's front-loaded routing gate names `opencode run` only inside the
        # explicit shell-substitution prohibition; any other mention leaks
        # operative OpenCode syntax into the Codex projection.
        for match in re.finditer(r"opencode run", body):
            line_start = body.rfind("\n", 0, match.start()) + 1
            line_end = body.find("\n", match.end())
            line = body[line_start:line_end if line_end != -1 else len(body)]
            self.assertRegex(
                line, r"禁止用 shell|不得用 shell",
                f"opencode run may appear only as a named prohibition, saw: {line!r}")


if __name__ == "__main__":
    unittest.main()
