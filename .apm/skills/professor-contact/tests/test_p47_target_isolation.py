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


class P47TargetIsolationTests(unittest.TestCase):
    """Lock the target-specific Stage 2 projection required by PR #47."""

    def test_target_packages_keep_single_stage2_projection(self):
        # Exact YAML target scopes are acceptance evidence from the clean APM
        # install/characterization recipe, where they are parsed with yq. This
        # source unit test only locks the producer layout; it must not re-parse
        # apm.yml with regex or turn one YAML serialization style into a product
        # invariant.
        root_analyzer = ROOT_AGENTS / f"{ANALYZER_NAME}.agent.md"
        self.assertFalse(
            root_analyzer.exists(),
            "the mixed analyzer must not remain in the root dual-target projection",
        )
        for package in (OPENCode_PACKAGE, CODEX_PACKAGE):
            path = package / ".apm" / "agents" / f"{ANALYZER_NAME}.agent.md"
            self.assertTrue(path.exists(), f"missing target-specific analyzer: {path}")
            _, body = _frontmatter_and_body(path)
            self.assertTrue(body)

    def test_opencode_projection_preserves_native_delegation_contract(self):
        path = OPENCode_PACKAGE / ".apm" / "agents" / f"{ANALYZER_NAME}.agent.md"
        _, body = _frontmatter_and_body(path)
        # Frontmatter permission fields are already covered by the deployment
        # metadata contract. This isolation test stays on the distinct body-level
        # risk: the OpenCode projection must keep its native Task branch.
        self.assertIn("### OpenCode 分支", body)
        self.assertRegex(body, r"task\s*\(")
        # Project Consensus keeps Codex routing rules out of the OpenCode
        # projection. Lock concrete Codex-only operative surfaces only; do not
        # turn unrelated prose or diagnostics into a source-wide keyword gate.
        self.assertNotIn("### Codex 分支", body)
        self.assertNotIn("spawn_agent", body)
        self.assertNotIn(".codex/agents/", body)
        self.assertNotIn("codex exec", body.lower())

    def test_codex_projection_is_named_agent_only_and_keeps_stage2_delegation(self):
        path = CODEX_PACKAGE / ".apm" / "agents" / f"{ANALYZER_NAME}.agent.md"
        _, body = _frontmatter_and_body(path)
        self.assertIn("Codex", body)
        self.assertIn("paper-analysis", body)
        self.assertIn("professor-contact-style-validator", body)
        self.assertRegex(body, r"(?is)(?:delegate|use|委派)[\s\S]{0,500}(?:wait|等待)")
        # OpenCode-only call syntax and the internal camelCase runtime event stay
        # forbidden.  The public Codex tool name `spawn_agent` is intentionally
        # not banned: Project Consensus permits the documented native tool name
        # while keeping private namespaces / parameter schemas out of the contract.
        for forbidden in ("task(", "question(", "spawnAgent"):
            self.assertNotIn(
                forbidden,
                body,
                f"Codex projection leaked target-incompatible/private API {forbidden!r}",
            )
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
