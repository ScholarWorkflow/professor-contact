"""Deterministic Codex native-delegation contract (issue #51).

Codex business prompts must rely on Codex's documented native multi-agent /
custom-agent semantics only: exact installed custom-agent `name`, real
delegation with sequential waiting, no inline simulation, no OpenCode-syntax
leakage, no undocumented namespace / request schema / characterization-only
discovery literal, and fail-closed behaviour on machine-level delegation
failure.  The expected inventory lives in `_codex_delegation_contract.py` and
is producer-owned; these tests compare each agent document's target branch
against it mechanically.

The generated `.codex/agents/<name>.toml` projection copies each agent body
verbatim into `developer_instructions`, so locking the body's Codex branch is
also what keeps the generated TOML invariants intact.  OpenCode runtime
acceptance is deliberately not re-promoted here (migration rule): its existing
deterministic target-isolation coverage stays, nothing more.
"""
from pathlib import Path
import re
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _codex_delegation_contract import (  # noqa: E402
    ALL_AGENT_NAMES,
    CODEX_BRANCH_MARKERS,
    CODEX_CALLER_SIBLING_EDGES,
    CODEX_CALLER_STAGE_EDGES,
    CODEX_NESTED_DELEGATORS,
    CODEX_NON_DELEGATORS,
    OPENCODE_BRANCH_MARKERS,
    SKILL_CODEX_REGION,
    SKILL_PATH,
    agent_path,
    frontmatter_and_body,
    read,
    segment,
)

# Undocumented / characterization-only surfaces that must never return as a
# production precondition, plus request-schema/envelope literals that business
# prompts must not bind to.  `spawn_agent` is a documented, stable Codex
# multi-agent tool name — it is banned here NOT because it is private but to
# keep the business contract from binding to one specific tool envelope.
FORBIDDEN_CONTRACT_LITERALS = (
    "Code Mode",
    "ALL_TOOLS",
    "tool catalog",
    "discovery surface",
    "spawn_agent(",
    "agent_type=",
    "agent_role=",
)

# Machine evidence that a delegator fails closed when native delegation is
# genuinely unavailable: block as a runtime/feature blocker instead of letting
# the parent silently do the child's work.
FAIL_CLOSED_PATTERN = re.compile(
    r"(?is)(?:blocker|不降级|降级伪装|does not happen|never fall back|"
    r"不降级成|不得降级|记为 codex runtime)"
)

WAIT_PATTERN = re.compile(r"(?is)(?:wait|等待)[\s\S]{0,200}?(?:result|结果|完成)")

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
    def test_inventory_partitions_exactly_the_eight_source_agents(self):
        delegators = set(CODEX_NESTED_DELEGATORS)
        leaves = set(CODEX_NON_DELEGATORS)
        self.assertFalse(delegators & leaves, "an agent cannot be both delegator and leaf")
        self.assertEqual(delegators | leaves, set(ALL_AGENT_NAMES))

    def test_every_delegator_child_is_an_exact_installed_name(self):
        for owner, children in CODEX_NESTED_DELEGATORS.items():
            self.assertTrue(children, f"{owner}: delegation row must not be empty")
            for child in children:
                with self.subTest(owner=owner, child=child):
                    self.assertRegex(child, r"^[a-z0-9-]+$")
                    self.assertNotIn(" ", child)
                    self.assertNotIn("<", child)

    def test_repo_owned_children_have_source_agent_documents(self):
        upstream = {"professor-collector", "paper-analysis"}
        for owner, children in CODEX_NESTED_DELEGATORS.items():
            for child in children:
                if child in upstream:
                    continue
                with self.subTest(owner=owner, child=child):
                    self.assertTrue(
                        agent_path(child).is_file(),
                        f"repo-owned child {child!r} must exist as a source agent",
                    )


class CodexNestedDelegatorContractTests(unittest.TestCase):
    """Per-delegator Codex-branch invariants, driven by the owned mapping."""

    def test_codex_branch_names_each_exact_installed_child(self):
        for owner, children in CODEX_NESTED_DELEGATORS.items():
            branch = _codex_branch(owner)
            for child in children:
                with self.subTest(owner=owner, child=child):
                    self.assertIn(f"`{child}`", branch)

    def test_codex_branch_requires_native_named_delegation_and_wait(self):
        for owner in CODEX_NESTED_DELEGATORS:
            with self.subTest(owner=owner):
                branch = _codex_branch(owner)
                self.assertRegex(
                    branch,
                    r"(?is)(?:named custom agent|安装后的机器名|installed named custom agent|安装后)",
                    "delegation must target the installed named custom agent identity",
                )
                self.assertRegex(branch, WAIT_PATTERN)

    def test_codex_branch_fails_closed_on_machine_level_delegation_failure(self):
        for owner in CODEX_NESTED_DELEGATORS:
            with self.subTest(owner=owner):
                self.assertRegex(_codex_branch(owner), FAIL_CLOSED_PATTERN)

    def test_codex_branch_never_inline_or_simulate_the_child(self):
        for owner in CODEX_NESTED_DELEGATORS:
            with self.subTest(owner=owner):
                self.assertRegex(_codex_branch(owner), NO_INLINE_PATTERN)

    def test_codex_branch_stays_off_opencode_syntax(self):
        for owner in CODEX_NESTED_DELEGATORS:
            with self.subTest(owner=owner):
                branch = _codex_branch(owner)
                self.assertNotRegex(branch, r"task\s*\(")
                self.assertNotIn("subagent_type", branch)
                self.assertNotRegex(branch, r"question\s*\(")

    def test_codex_branch_carries_no_discovery_or_envelope_literal(self):
        for owner in CODEX_NESTED_DELEGATORS:
            branch = _codex_branch(owner)
            for literal in FORBIDDEN_CONTRACT_LITERALS:
                with self.subTest(owner=owner, literal=literal):
                    self.assertNotIn(literal, branch)

    def test_child_prompts_carry_only_the_existing_business_input(self):
        # Invariant 9: the delegation prompt carries the documented input
        # contract, never test hints about spawning/topology.
        for owner in CODEX_NESTED_DELEGATORS:
            with self.subTest(owner=owner):
                branch = _codex_branch(owner)
                self.assertNotRegex(branch, r"(?i)nested topology")
                self.assertNotRegex(branch, r"(?i)depth\s*>\s*=")
                self.assertNotRegex(branch, r"(?i)请 spawn")

    def test_opencode_branch_keeps_native_task_semantics_for_the_same_children(self):
        for owner, children in CODEX_NESTED_DELEGATORS.items():
            with self.subTest(owner=owner):
                branch = _opencode_branch(owner)
                self.assertRegex(
                    branch,
                    r"(?is)(?:task\s*\(|Task 委派|native Task)",
                    "OpenCode projection must keep its documented Task delegation path",
                )
                for child in children:
                    self.assertIn(child, branch)

    def test_downloader_stage1_payload_is_untouched_by_the_delegation_contract(self):
        branch = _codex_branch("professor-contact-downloader")
        for field in ("`folder_path`", "`pdf_only: true`", "`item_keys`", "`access_mode`"):
            self.assertIn(field, branch)
        self.assertIn("omitting it when absent", branch)

    def test_analyzer_stage2_business_concurrency_rule_is_untouched(self):
        # Mapping-driven hardening must not absorb the ≤3 paper-analysis
        # business cap into any Codex thread-limit claim.
        body = frontmatter_and_body(agent_path("professor-contact-analyzer"))[1]
        self.assertRegex(
            body,
            r"(?is)max_concurrent_threads_per_session[\s\S]{0,300}(?:不等价|不能互相替代)",
        )

    def test_email_generator_stage5_business_contract_is_untouched(self):
        body = frontmatter_and_body(agent_path("professor-contact-email-generator"))[1]
        self.assertIn("dynamic-fields-only", body)
        self.assertIn("Do not pass `--humanized` or `--humanized-map`", body)
        branch = _codex_branch("professor-contact-email-generator")
        self.assertIn("`professor-contact-email-validator`", branch)
        self.assertIn("needs_input", branch)


class CodexLeafAgentTests(unittest.TestCase):
    def test_leaf_agents_stay_outside_the_nested_mapping(self):
        for leaf in CODEX_NON_DELEGATORS:
            with self.subTest(leaf=leaf):
                self.assertNotIn(leaf, CODEX_NESTED_DELEGATORS)

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

    def test_idea_generator_codex_sibling_boundary_is_unchanged(self):
        body = frontmatter_and_body(agent_path("professor-contact-idea-generator"))[1]
        start = body.index("**Codex 分支（调用线程 sibling 编排；本 agent 不启动任何子代理）**")
        branch = body[start:]
        self.assertIn("调用线程", branch)
        self.assertIn("professor-contact-style-validator", branch)
        # The sibling delegation belongs to the caller thread, not to a nested
        # spawn by the idea-generator itself.
        self.assertNotRegex(branch, r"task\s*\(")


class CodexCallerSkillContractTests(unittest.TestCase):
    """Caller-level edges live in SKILL.md and are verified separately."""

    @classmethod
    def setUpClass(cls):
        cls.skill = read(SKILL_PATH)

    def _skill_codex_region(self) -> str:
        return segment(self.skill, SKILL_CODEX_REGION[0], SKILL_CODEX_REGION[1])

    def test_shared_call_table_locks_every_stage_agent_edge(self):
        for stage, name in CODEX_CALLER_STAGE_EDGES:
            with self.subTest(stage=stage, name=name):
                self.assertRegex(
                    self.skill,
                    rf"(?m)^\| {stage} \| `{re.escape(name)}` \|",
                )

    def test_caller_table_keeps_validators_out_of_direct_caller_scope(self):
        self.assertIn(
            "`professor-contact-email-validator` / `professor-contact-style-validator` 不由 caller 直接驱动",
            self.skill,
        )

    def test_caller_sibling_edge_stays_out_of_the_nested_mapping(self):
        skill = self.skill
        for owner, sibling in CODEX_CALLER_SIBLING_EDGES:
            with self.subTest(owner=owner, sibling=sibling):
                # Neither the Stage 3 agent nor its validator carries a
                # nested-delegation row: on Codex the sibling validator is
                # delegated by the caller thread only.
                self.assertNotIn(owner, CODEX_NESTED_DELEGATORS)
                self.assertNotIn(sibling, CODEX_NESTED_DELEGATORS)
                self.assertIn("调用线程先委派 named `professor-contact-idea-generator`", skill)
                self.assertIn("再委派 named `professor-contact-style-validator`", skill)

    def test_codex_caller_region_delegates_named_agents_and_waits(self):
        region = self._skill_codex_region()
        self.assertRegex(region, r"(?is)delegate to / use[\s\S]{0,200}(?:wait|等待)")
        self.assertRegex(region, r"(?is)等待该子代理完成并返回结果")
        self.assertRegex(region, r"(?is)不\*\*把子代理的 instructions 复制进父对话里自己执行")

    def test_codex_caller_region_has_no_opencode_syntax(self):
        region = self._skill_codex_region()
        self.assertNotRegex(region, r"task\(subagent_type")

    def test_stage0_codex_boundary_is_fresh_redelegation_with_explicit_selection(self):
        region = self._skill_codex_region()
        self.assertIn("needs_input", region)
        self.assertIn("selection_request", region)
        self.assertRegex(region, r"重新委派[\s\S]{0,200}professor-contact")
        self.assertRegex(region, r"(?is)不恢复第一轮的会话/线程")

    def test_stage4_codex_boundary_redelegates_the_selection_agent(self):
        region = self._skill_codex_region()
        self.assertRegex(region, r"重新委派 `professor-contact-selection` 并显式传入 `selection`")

    def test_stage2_codex_chain_names_the_analyzer_nested_children(self):
        region = self._skill_codex_region()
        self.assertIn("caller → `professor-contact-analyzer`", region)
        self.assertIn("`paper-analysis`（每篇论文一个）与 `professor-contact-style-validator`", region)


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

    def test_analyzer_keeps_the_documented_native_chain_wording(self):
        branch = _codex_branch("professor-contact-analyzer")
        self.assertIn("`paper-analysis`", branch)
        self.assertIn("`professor-contact-style-validator`", branch)
        self.assertRegex(branch, r"(?is)等待结果返回后再继续")
        self.assertRegex(branch, r"(?is)记为 codex runtime/feature blocker")


if __name__ == "__main__":
    unittest.main()
