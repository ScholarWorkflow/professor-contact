"""Deterministic Codex orchestration contract for issue #55.

The merge gate is intentionally identity-agnostic.  fixtures@9 treats
requested_role / loaded_identity as optional diagnostics, so this suite must
not turn exact child names or named-role matches into PASS/FAIL conditions.

These tests cover only producer-owned orchestration invariants that are
mechanically provable from source: delegate and wait when a child is required,
never inline or simulate the child, fail closed on machine-level delegation
failure, keep Codex/OpenCode syntax isolated, keep the delegation chain
non-recursive (the payload carries only this stage's business fields and no
coordinator delegates to its own machine name), and keep characterization-only
tool envelopes out of production text.  They also lock the top-level Stage 1–5
routing matrix and the Stage 3/5 ownership boundaries.
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

# The product contract stays at the named-agent level and bans version-private
# envelopes: a measured tool-search namespace, the raw spawn request shape, or
# a fixed catalog command from one characterization run.  `spawn_agent` itself
# is a documented Codex tool name, so only its call form stays out of
# production instructions.
FORBIDDEN_PRIVATE_LITERALS = (
    "ALL_TOOLS",
    "multi_agent_v1__",
    "spawn_agent(",
    "agent_type=",
    "agent_role=",
)

# Each coordinator source document may state the invariant in its own
# language; every invariant needs at least one of its literals, verbatim.
# Runtime evidence for issue #51 showed a second, distinct failure shape: a
# coordinator received the caller-facing routing sentence verbatim and
# delegated the task to a named custom agent with *its own* machine name, so
# the chain grew one analyzer layer per hop and the nested leaves were pushed
# past the point where the pinned runtime settles them.  The guard therefore
# belongs to production source, not to the fixed runtime prompt.
CODEX_RECURSION_INVARIANTS = {
    "business-input-only-payload": (
        "委派 payload 只携带该 Stage 的 Input contract 业务输入字段，"
        "不把调用者自己收到的路由指令原文转发给 child",
        "the delegation payload carries only that stage's Input contract "
        "business fields, and never forwards the caller's own received routing "
        "instruction verbatim to the child",
    ),
    "no-self-delegation": (
        "任何 coordinator 不得把任务委派给与自身机器名相同的 named custom agent，"
        "同一委派链里同一个机器名只允许出现一层",
        "no coordinator may delegate to a named custom agent that has its own "
        "machine name; the same machine name may appear only once in a "
        "delegation chain",
    ),
}


def _first_position(text: str, literals) -> int:
    positions = [text.index(literal) for literal in literals if literal in text]
    if not positions:
        raise AssertionError(f"missing invariant literal: {literals}")
    return min(positions)


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
HTML_COMMENT_PATTERN = re.compile(r"(?s)<!--.*?-->")
# Each coordinator document states its own wait step; this is the boundary the
# recursion guard must sit in front of.
RECURSION_BOUNDARY_PATTERN = re.compile(
    r"(?:等待该子代理完成并返回结果|等待结果返回后再继续|"
    r"wait for (?:that child's|its) result)"
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

    def test_codex_branch_carries_no_private_envelope_literal(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            branch = _codex_branch(owner)
            for literal in FORBIDDEN_PRIVATE_LITERALS:
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
        self.assertIn("用户要求执行某个 Stage 本身已经触发该 Stage 的 routing gate", region)
        self.assertIn("当前 Codex root 必须在本轮使用 Codex 原生 subagent workflow", region)
        self.assertRegex(region, r"(?is)等待该子代理完成并返回结果")
        self.assertRegex(region, r"(?is)不\*\*把子代理的 instructions 复制进父对话里自己执行")

    def test_codex_routing_does_not_require_outer_prompt_delegation_words(self):
        region = self._skill_codex_region()
        self.assertIn("不要求用户在外层请求中补写 agent 名或 delegate to / use 句式", region)
        historical_chinese_prompt_routing_rules = (
            "在 prompt 中显式要求 Codex **delegate to / use** 指定的 exact named custom agent",
            "caller 自己的请求中必须明确 **delegate to / use** 指定的 exact named custom agent",
        )
        for old_rule in historical_chinese_prompt_routing_rules:
            with self.subTest(old_rule=old_rule):
                self.assertNotIn(old_rule, region)
        self.assertNotIn("Delegate this task to the installed custom agent", region)

    def test_active_host_selects_runtime_branch_without_cli_discovery(self):
        region = self._skill_codex_region()
        self.assertIn("运行分支只由当前执行器/host 决定", region)
        self.assertIn("不得用 `command -v`", region)
        self.assertRegex(region, r"不得用 shell 调用 `(?:opencode run|codex exec)`")

    def test_caller_separates_delegation_target_from_child_business_payload(self):
        region = self._skill_codex_region()
        self.assertIn("delegation target 与 child message 分开", region)
        self.assertRegex(
            region,
            r"child message.*只能包含该 Stage 的 Input contract 字段和任务约束",
        )
        self.assertRegex(region, r"不得在 child payload 中写[\s\S]{0,120}路由元指令")
        self.assertIn("不得用 shell 调用 `opencode run` 或其它 CLI 冒充 Codex 委派", region)
        self.assertNotIn(
            "Delegate this task to the installed custom agent `professor-contact-downloader`",
            region,
        )

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


class CodexStageRoutingContractTests(unittest.TestCase):
    """Issue #55 top-level routing and ownership gates."""

    @classmethod
    def setUpClass(cls):
        cls.skill = read(SKILL_PATH)
        cls.region = segment(cls.skill, SKILL_CODEX_REGION[0], SKILL_CODEX_REGION[1])

    def test_stage_one_to_five_matrix_names_exact_owner_and_wait_gate(self):
        expected = {
            "1": "professor-contact-downloader",
            "2": "professor-contact-analyzer",
            "3": "professor-contact-idea-generator",
            "4": "professor-contact-selection",
            "5": "professor-contact-email-generator",
        }
        for stage, owner in expected.items():
            with self.subTest(stage=stage):
                self.assertIn(f"| {stage} | `{owner}` | 是 |", self.region)
        self.assertIn("用户要求执行某个 Stage 本身就是 routing gate", self.region)
        self.assertIn("必须先把该 Stage 委派", self.region)
        self.assertIn("并等待结果后再继续", self.region)

    def test_stage3_root_owns_only_validation_record_after_sibling_loop(self):
        start = self.region.index("**Stage 3 validator 校验循环")
        end = self.region.index("**Stage 4 用户选择边界", start)
        section = self.region[start:end]
        codex = section[section.index("- **Codex") :]
        self.assertLess(
            codex.index("professor-contact-idea-generator"),
            codex.index("等待生成 + `stage3-finalize` 完成"),
        )
        self.assertLess(
            codex.index("等待生成 + `stage3-finalize` 完成"),
            codex.index("professor-contact-style-validator"),
        )
        self.assertIn("最多 2 轮", section)
        self.assertIn("stage3-record-validation", section)
        for forbidden in (
            "stage3-plan", "candidate model generation", "candidate result file",
            "stage3-finalize", "自称「validator 已通过" ,
        ):
            with self.subTest(forbidden=forbidden):
                self.assertIn(forbidden, section)

    def test_stage5_top_level_does_not_own_email_validator(self):
        row = next(line for line in self.region.splitlines()
                   if line.startswith("| 5 |"))
        self.assertIn("professor-contact-email-generator", row)
        self.assertIn("email-validator", row)
        self.assertIn("email-validator loop 仍归 email-generator 所有", self.region)

    def test_codex_sources_drop_obsolete_discovery_prerequisite(self):
        branches = {"SKILL.md": self.region}
        branches.update({name: _codex_branch(name)
                         for name in CODEX_NESTED_DELEGATOR_AGENTS})
        forbidden = re.compile(
            r"(?i)(?:before child business work first discover delegation capability|"
            r"Code Mode / programmatic tool-calling surface discovery is a hard prerequisite|"
            r"tool directory/search surface must be queried before delegation|"
            r"discovery failure itself is a runtime blocker|"
            r"Code Mode exec is the required/approved discovery step|"
            r"委派前先发现 delegation capability（硬前置）|"
            r"在执行任何 child 业务内容前，必须先通过当前 Codex 运行时的 Code Mode / "
            r"programmatic tool-calling surface|"
            r"discovery 失败或该能力不可调用时，明确记为 Codex runtime/feature blocker)"
        )
        for name, branch in branches.items():
            with self.subTest(source=name):
                self.assertNotRegex(branch, forbidden)

    def test_opencode_sources_keep_native_task_contract(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                branch = _opencode_branch(owner)
                self.assertRegex(branch, r"(?is)(?:task\s*\(|Task 委派|native Task)")

    def test_no_version_private_tool_envelope_reaches_production_contracts(self):
        docs = [SKILL_PATH] + [agent_path(name) for name in ALL_AGENT_NAMES]
        for path in docs:
            text = read(path)
            for literal in FORBIDDEN_PRIVATE_LITERALS:
                with self.subTest(path=path.name, literal=literal):
                    self.assertNotIn(literal, text)
            self.assertNotRegex(text, r"(?i)tool[- ]catalog")
            self.assertNotRegex(text, r"枚举 tool catalog")
            self.assertNotRegex(text, r"必须先枚举[\s\S]{0,40}(?:才|方)允许")


class CodexRecursionGuardTests(unittest.TestCase):
    """Issue #51 retry evidence: same-name re-delegation deepens the chain."""

    @classmethod
    def setUpClass(cls):
        skill = read(SKILL_PATH)
        cls.branches = {
            "SKILL.md Codex caller": segment(
                skill, SKILL_CODEX_REGION[0], SKILL_CODEX_REGION[1]),
        }
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            cls.branches[owner] = _codex_branch(owner)

    def _has(self, text: str, invariant: str) -> bool:
        return any(literal in text
                   for literal in CODEX_RECURSION_INVARIANTS[invariant])

    def test_every_codex_coordinator_states_the_recursion_guard(self):
        for label, branch in self.branches.items():
            for invariant in CODEX_RECURSION_INVARIANTS:
                with self.subTest(doc=label, invariant=invariant):
                    self.assertTrue(
                        self._has(branch, invariant),
                        f"{label}: production source omits {invariant}",
                    )

    def test_recursion_guard_is_stated_before_awaiting_the_child(self):
        """The payload/self-name guard is only useful while the coordinator is
        still composing the delegation, so it must precede the wait step."""
        for label, branch in self.branches.items():
            with self.subTest(doc=label):
                wait = RECURSION_BOUNDARY_PATTERN.search(branch)
                self.assertIsNotNone(wait, f"{label}: no wait-for-child step found")
                for invariant in CODEX_RECURSION_INVARIANTS:
                    position = _first_position(branch,
                                               CODEX_RECURSION_INVARIANTS[invariant])
                    self.assertLess(
                        position, wait.start(),
                        f"{label}: {invariant} must be stated before awaiting the child",
                    )

    def test_generated_codex_projection_keeps_the_recursion_guard(self):
        for name in CODEX_NESTED_DELEGATOR_AGENTS:
            frontmatter, body = frontmatter_and_body(agent_path(name))
            projected = HTML_COMMENT_PATTERN.sub("", body)
            for invariant in CODEX_RECURSION_INVARIANTS:
                with self.subTest(agent=name, invariant=invariant):
                    self.assertTrue(self._has(projected, invariant),
                                    f"{name}: projection loses {invariant}")
                    self.assertFalse(
                        self._has("\n".join(frontmatter), invariant),
                        f"{name}: frontmatter is not projected into Codex instructions",
                    )

    def test_opencode_branches_stay_free_of_the_codex_recursion_wording(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            branch = _opencode_branch(owner)
            for invariant in CODEX_RECURSION_INVARIANTS:
                with self.subTest(owner=owner, invariant=invariant):
                    for literal in CODEX_RECURSION_INVARIANTS[invariant]:
                        self.assertNotIn(literal, branch)

    def test_leaf_sources_do_not_gain_the_codex_recursion_guard(self):
        for leaf in CODEX_NON_DELEGATORS:
            text = read(agent_path(leaf))
            for invariant in CODEX_RECURSION_INVARIANTS:
                with self.subTest(leaf=leaf, invariant=invariant):
                    self.assertFalse(self._has(text, invariant))

    def test_recursion_guard_stays_a_source_contract_not_an_identity_gate(self):
        for label, branch in self.branches.items():
            for forbidden in ("requested_role", "loaded_identity",
                              "agent_identity", "receiverThreadIds"):
                with self.subTest(doc=label, forbidden=forbidden):
                    self.assertNotIn(forbidden, branch)


class AnalyzerNativeDelegationSemanticsTests(unittest.TestCase):
    def test_analyzer_keeps_native_delegation_wait_and_fail_closed_semantics(self):
        branch = _codex_branch("professor-contact-analyzer")
        self.assertRegex(branch, DELEGATION_PATTERN)
        self.assertRegex(branch, r"(?is)等待结果返回后再继续")
        self.assertRegex(branch, r"(?is)记为 codex runtime/feature blocker")


if __name__ == "__main__":
    unittest.main()
