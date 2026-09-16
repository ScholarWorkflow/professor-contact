"""Issue #39: Stage 2 Zotero access must honor the runtime endpoint override.

These tests lock the deterministic producer contract only (analyzer source
text + shape of the resolution rule); they do not test model quality.
Literals `23119`/`23120` must keep their fallback/explanation role inside the
single contract fence — execution paths must go through the resolved
`ZOTERO_HTTP_URL` / `ZOTERO_MCP_URL` variables.
"""
from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[4]
ANALYZER_PATH = (
    REPO_ROOT
    / "packages"
    / "professor-contact-opencode"
    / ".apm"
    / "agents"
    / "professor-contact-analyzer.agent.md"
)

HTTP_FALLBACK = "http://127.0.0.1:23119"
MCP_FALLBACK = "http://127.0.0.1:23120/mcp"
CONTRACT_HTTP_LINE = f'ZOTERO_HTTP_URL="${{ZOTERO_HTTP_URL:-{HTTP_FALLBACK}}}"'
CONTRACT_HTTP_NORMALIZE = 'ZOTERO_HTTP_URL="${ZOTERO_HTTP_URL%/}"'
CONTRACT_MCP_LINE = f'ZOTERO_MCP_URL="${{ZOTERO_MCP_URL:-{MCP_FALLBACK}}}"'
CONTRACT_MCP_NORMALIZE = 'ZOTERO_MCP_URL="${ZOTERO_MCP_URL%/}"'


def _analyzer_body() -> str:
    text = ANALYZER_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("analyzer: missing opening frontmatter delimiter")
    end = lines.index("---", 1)
    return "\n".join(lines[end + 1 :])


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start + len(start_marker))
    return text[start:end]


def _fenced_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


class Stage2ZoteroEndpointContractTests(unittest.TestCase):
    def setUp(self):
        self.body = _analyzer_body()
        self.step27 = _section(self.body, "### Step 2.7", "### Step 3")

    def test_step2_7_defines_the_single_endpoint_resolution_contract(self):
        for line in (CONTRACT_HTTP_LINE, CONTRACT_HTTP_NORMALIZE,
                     CONTRACT_MCP_LINE, CONTRACT_MCP_NORMALIZE):
            self.assertIn(line, self.step27, f"missing contract line: {line}")

    def test_http_endpoint_is_a_base_url_with_production_fallback(self):
        self.assertIn(HTTP_FALLBACK, self.step27)
        self.assertIn("base URL", self.step27)
        # Execution appends paths to the resolved variable, never to a literal.
        self.assertIn('"$ZOTERO_HTTP_URL/connector/ping"', self.step27)
        self.assertIn('"$ZOTERO_HTTP_URL/api/users/0/', self.body)

    def test_mcp_endpoint_is_complete_and_never_double_appends_mcp(self):
        self.assertIn(MCP_FALLBACK, self.step27)
        self.assertIn("完整 MCP endpoint", self.step27)
        self.assertIn("已经包含 `/mcp`", self.step27)
        self.assertRegex(self.step27, r"不得对 resolved `ZOTERO_MCP_URL` 再追加 `/mcp`")
        # The resolved MCP endpoint is already complete: no execution path may
        # append `/mcp` to the variable again.
        self.assertIsNone(
            re.search(r"\$\{?ZOTERO_MCP_URL\}?/mcp", self.body),
            "ZOTERO_MCP_URL must never be suffixed with another /mcp")
        self.assertNotIn("//api", self.body)

    def test_both_endpoints_normalize_trailing_slash(self):
        self.assertIn(CONTRACT_HTTP_NORMALIZE, self.step27)
        self.assertIn(CONTRACT_MCP_NORMALIZE, self.step27)

    def test_connectivity_probe_uses_resolved_endpoints_without_literal_ports(self):
        probe_line = next(line for line in self.step27.splitlines()
                          if "Probe Zotero" in line)
        self.assertIn("$ZOTERO_HTTP_URL", probe_line)
        self.assertIn("ZOTERO_MCP_URL", probe_line)
        for port in ("23119", "23120"):
            self.assertNotIn(port, probe_line)

    def test_mcp_session_inherits_resolved_url_without_reimplementation(self):
        self.assertIn("zotero-mcp-session", self.step27)
        self.assertRegex(
            self.step27,
            r"zotero-mcp-session[\s\S]{0,400}继承 resolved `ZOTERO_MCP_URL`",
        )
        self.assertIn("zotero-read/scripts/new-session.sh", self.step27)

    def test_authorship_line_pagination_uses_resolved_http_url(self):
        section = _section(self.body, "1.7 **署名线判定", "2. **判定相关论文")
        self.assertIn('GET "$ZOTERO_HTTP_URL/api/users/0/collections/', section)
        for port in ("23119", "23120"):
            self.assertNotIn(port, section)

    def test_literal_ports_survive_only_inside_the_fallback_contract_fence(self):
        contract_blocks = [block for block in _fenced_blocks(self.body)
                           if CONTRACT_HTTP_LINE in block]
        self.assertEqual(
            len(contract_blocks), 1,
            "the endpoint fallback contract must be defined exactly once")
        contract_lines = set(contract_blocks[0])
        for line in self.body.splitlines():
            if "23119" in line or "23120" in line:
                self.assertIn(
                    line, contract_lines,
                    f"literal port outside the fallback contract fence: {line!r}")

    def test_hard_rule_locks_resolved_endpoint_consistency(self):
        hard_rules = self.body[self.body.index("## Hard rules"):]
        self.assertRegex(
            hard_rules,
            r"Stage 2 Zotero 访问统一消费 resolved endpoint",
        )
        self.assertRegex(
            hard_rules,
            r"ZOTERO_HTTP_URL[\s\S]{0,200}ZOTERO_MCP_URL",
        )

    def test_opencode_and_codex_stage2_branches_are_preserved(self):
        opencode_start = self.body.index("### OpenCode 分支")
        codex_start = self.body.index("### Codex 分支")
        self.assertLess(opencode_start, codex_start)
        opencode = _section(self.body, "### OpenCode 分支", "### Codex 分支")
        codex = _section(self.body, "### Codex 分支", "## Input")
        for name in ("paper-analysis", "professor-contact-style-validator"):
            self.assertIn(name, opencode)
            self.assertIn(name, codex)


if __name__ == "__main__":
    unittest.main()
