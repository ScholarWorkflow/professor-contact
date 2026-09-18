"""Deterministic Codex orchestration contract for issue #51.

The merge gate is intentionally identity-agnostic.  fixtures@9 treats
requested_role / loaded_identity as optional diagnostics, so this suite must
not turn exact child names or named-role matches into PASS/FAIL conditions.

These tests cover only producer-owned orchestration invariants that are
mechanically provable from source: native delegation is required where the
source document is a coordinator, sequential dependencies wait for results,
parents do not inline/simulate child work, machine-level delegation failures
fail closed, Codex/OpenCode syntax stays isolated, and characterization-only
discovery literals stay out of production contracts.
"""
from pathlib import Path
import re
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _codex_delegation_contract import (  # noqa: E402
    ALL_AGENT_NAMES,
    CODEX_BRANCH_MARKERS,
    CODEX_NESTED_DELEGATOR_AGENTS,
    CODEX_NON_DELEGATORS,
    OPENCODE_BRANCH_MARKERS,
    SKILL_CODEX_REGION,
    SKILL_PATH,
    agent_path,
    frontmatter_and_body,
    read,
    segment,
)

FORBIDDEN_CONTRACT_LITERALS = (
    "Code Mode",
    "ALL_TOOLS",
    "tool catalog",
    "discovery surface",
    "spawn_agent(",
    "agent_type=",
    "agent_role=",
)

FAIL_CLOSED_PATTERN = re.compile(
    r"(?is)(?:blocker|不降级|降级伪装|does not happen|never fall back|"
    r"不降级成|不得降级|记为 codex runtime)"
)
WAIT_PATTERN = re.compile(r"(?is)(?:wait|等待)[\s\S]{0,200}?(?:result|结果|完成)")
DELEGATION_PATTERN = re.compile(r"(?is)(?:delegate|delegation|委派)")
NO_INLINE_PATTERN = re.compile(
    r"(?is)(?:do not inline|不.*模拟|不复制.*instructions|inline-simulate|"
    r"不由父代理模拟|不把.*内部论文分析 prompt 复制|不.*inline)"
)


def _codex_branch(name: str) -> str:
    markers = CODEX_BRANCH_MARKERS[name]
    body = frontmatter_and_body(agent_path(name))[1]
    return segment(body, markers[0], markers[1])


def _opencode_branch(name: str) -> str:
    markers = OPENCODE_BRANCH_MARKERS[name]
    body = frontmatter_and_body(agent_path(name))[1]
    return segment(body, markers[0], markers[1])


class CodexDelegationInventoryTests(unittest.TestCase):
    def test_source_inventory_partitions_the_eight_repo_agents(self):
        delegators = set(CODEX_NESTED_DELEGATOR_AGENTS)
        leaves = set(CODEX_NON_DELEGATORS)
        self.assertFalse(delegators & leaves)
        self.assertEqual(delegators | leaves, set(ALL_AGENT_NAMES))


class CodexNestedDelegatorContractTests(unittest.TestCase):
    """Per-coordinator source invariants without child-identity assertions."""

    def test_codex_branch_requires_native_delegation_and_wait(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                branch = _codex_branch(owner)
                self.assertRegex(branch, DELEGATION_PATTERN)
                self.assertRegex(branch, WAIT_PATTERN)

    def test_codex_branch_fails_closed_on_machine_level_delegation_failure(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                self.assertRegex(_codex_branch(owner), FAIL_CLOSED_PATTERN)

    def test_codex_branch_never_inline_or_simulate_child_work(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                self.assertRegex(_codex_branch(owner), NO_INLINE_PATTERN)

    def test_codex_branch_stays_off_opencode_syntax(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                branch = _codex_branch(owner)
                self.assertNotRegex(branch, r"task\s*\(")
                self.assertNotIn("subagent_type", branch)
                self.assertNotRegex(branch, r"question\s*\(")

    def test_codex_branch_carries_no_discovery_or_envelope_literal(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            branch = _codex_branch(owner)
            for literal in FORBIDDEN_CONTRACT_LITERALS:
                with self.subTest(owner=owner, literal=literal):
                    self.assertNotIn(literal, branch)

    def test_child_prompts_carry_no_topology_test_hints(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                branch = _codex_branch(owner)
                self.assertNotRegex(branch, r"(?i)nested topology")
                self.assertNotRegex(branch, r"(?i)depth\s*>\s*=")
                self.assertNotRegex(branch, r"(?i)请 spawn")

    def test_opencode_branch_keeps_native_task_semantics(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                branch = _opencode_branch(owner)
                self.assertRegex(
                    branch,
                    r"(?is)(?:task\s*\(|Task 委派|native Task)",
                    "OpenCode projection must keep its Task delegation path",
                )

    def test_downloader_stage1_payload_is_untouched_by_the_delegation_contract(self):
        branch = _codex_branch("professor-contact-downloader")
        for field in ("`folder_path`", "`pdf_only: true`", "`item_keys`", "`access_mode`"):
            self.assertIn(field, branch)
        self.assertIn("omitting it when absent", branch)

    def test_analyzer_stage2_business_concurrency_rule_is_untouched(self):
        body = frontmatter_and_body(agent_path("professor-contact-analyzer"))[1]
        self.assertRegex(
            body,
            r"(?is)max_concurrent_threads_per_session[\s\S]{0,300}(?:不等价|不能互相替代)",
        )

    def test_email_generator_stage5_business_contract_is_untouched(self):
        body = frontmatter_and_body(agent_path("professor-contact-email-generator"))[1]
        self.assertIn("dynamic-fields-only", body)
        self.assertIn("Do not pass `--humanized` or `--humanized-map`", body)
        self.assertIn("needs_input", _codex_branch("professor-contact-email-generator"))


class CodexLeafAgentTests(unittest.TestCase):
    def test_leaf_agents_stay_outside_the_nested_source_inventory(self):
        for leaf in CODEX_NON_DELEGATORS:
            with self.subTest(leaf=leaf):
                self.assertNotIn(leaf, CODEX_NESTED_DELEGATOR_AGENTS)

    def test_leaf_agents_keep_explicit_no_spawn_boundaries(self):
        expectations = {
            "professor-contact": "Never spawn subagents.",
            "professor-contact-selection": "You NEVER spawn sub-agents.",
            "professor-contact-style-validator": "绝不 spawn 子代理",
            "professor-contact-idea-generator": "你不启动任何子代理",
            "professor-contact-email-validator": "never spawn or delegate sub-agents",
        }
        for leaf, needle in expectations.items():
            with self.subTest(leaf=leaf):
                self.assertIn(needle, read(agent_path(leaf)))

    def test_idea_generator_codex_sibling_boundary_stays_caller_owned(self):
        body = frontmatter_and_body(agent_path("professor-contact-idea-generator"))[1]
        start = body.index("**Codex 分支（调用线程 sibling 编排；本 agent 不启动任何子代理）**")
        branch = body[start:]
        self.assertIn("调用线程", branch)
        self.assertNotRegex(branch, r"task\s*\(")


class CodexCallerSkillContractTests(unittest.TestCase):
    """Caller orchestration checks that do not assert runtime role identity."""

    @classmethod
    def setUpClass(cls):
        cls.skill = read(SKILL_PATH)

    def _skill_codex_region(self) -> str:
        return segment(self.skill, SKILL_CODEX_REGION[0], SKILL_CODEX_REGION[1])

    def test_codex_caller_region_delegates_and_waits(self):
        region = self._skill_codex_region()
        self.assertRegex(region, r"(?is)delegate to / use[\s\S]{0,200}(?:wait|等待)")
        self.assertRegex(region, r"(?is)等待该子代理完成并返回结果")
        self.assertRegex(region, r"(?is)不\*\*把子代理的 instructions 复制进父对话里自己执行")

    def test_codex_caller_region_has_no_opencode_syntax(self):
        self.assertNotRegex(self._skill_codex_region(), r"task\(subagent_type")

    def test_stage0_codex_boundary_is_fresh_redelegation_with_explicit_selection(self):
        region = self._skill_codex_region()
        self.assertIn("needs_input", region)
        self.assertIn("selection_request", region)
        self.assertIn("重新委派", region)
        self.assertRegex(region, r"(?is)不恢复第一轮的会话/线程")

    def test_stage4_codex_boundary_preserves_explicit_selection_input(self):
        region = self._skill_codex_region()
        self.assertRegex(region, r"重新委派[\s\S]{0,200}`selection`")


class DiscoveryGateRetirementTests(unittest.TestCase):
    """The mandatory discovery precondition stays retired everywhere."""

    def test_no_discovery_literal_survives_in_any_production_contract(self):
        docs = [SKILL_PATH] + [agent_path(name) for name in ALL_AGENT_NAMES]
        for path in docs:
            text = read(path)
            for literal in ("Code Mode", "ALL_TOOLS", "discovery surface"):
                with self.subTest(path=path.name, literal=literal):
                    self.assertNotIn(literal, text)
            self.assertNotRegex(text, r"(?i)tool[- ]catalog")
            self.assertNotRegex(text, r"枚举 tool catalog")

    def test_analyzer_keeps_native_delegation_wait_and_fail_closed_semantics(self):
        branch = _codex_branch("professor-contact-analyzer")
        self.assertRegex(branch, DELEGATION_PATTERN)
        self.assertRegex(branch, r"(?is)等待结果返回后再继续")
        self.assertRegex(branch, r"(?is)记为 codex runtime/feature blocker")


if __name__ == "__main__":
    unittest.main()
