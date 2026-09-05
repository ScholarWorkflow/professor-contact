"""Static contract regressions for the stage-3 idea-generator agent document.

The agent prompt is executable contract, not prose: a duplicate frontmatter key
changes parser behavior across YAML implementations, and a stale result-file
routing instruction makes real agents assemble filenames the runner never
reads, resurfacing ``result_missing`` after the direction-id-v1 migration.
"""
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_PATH = REPO_ROOT / ".apm" / "agents" / "professor-contact-idea-generator.agent.md"


def _frontmatter_lines(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError("missing closing frontmatter delimiter") from exc
    return lines[1:end]


class Stage3IdeaGeneratorAgentContractTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AGENT_PATH.exists(), f"missing agent document: {AGENT_PATH}")
        self.text = AGENT_PATH.read_text(encoding="utf-8")
        self.frontmatter = _frontmatter_lines(self.text)

    def test_frontmatter_keys_are_unique(self):
        seen = {}
        for line in self.frontmatter:
            if not line or line[0].isspace():
                continue
            key = line.partition(":")[0].strip()
            seen[key] = seen.get(key, 0) + 1
        duplicates = {key: count for key, count in seen.items() if count > 1}
        self.assertEqual(
            {}, duplicates,
            "duplicate top-level frontmatter keys are parser-dependent; keep one of each",
        )

    def test_frontmatter_declares_single_subagent_mode(self):
        modes = [line for line in self.frontmatter if line.startswith("mode:")]
        self.assertEqual(
            ["mode: subagent"], modes,
            "frontmatter must declare exactly one `mode: subagent`",
        )

    def test_no_legacy_collection_key_result_routing(self):
        self.assertNotIn(
            "candidates-<collection_key>", self.text,
            "result filenames must never be assembled from collection_key; "
            "the runner routes results through plan-returned result_file only",
        )

    def test_plan_returned_result_file_contract_is_present(self):
        self.assertIn("result_file", self.text)
        self.assertIn(
            "精确文件名", self.text,
            "the agent must state that model results go to the exact plan-returned filename",
        )
        self.assertIn(
            "绝不自拼", self.text,
            "the agent must forbid self-assembling result filenames",
        )


if __name__ == "__main__":
    unittest.main()
