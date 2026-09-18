"""Deterministic Codex orchestration contract (issue #51 behaviour, issue #47 layout).

The merge gate is intentionally identity-agnostic.  fixtures@9 treats
requested_role / loaded_identity as optional diagnostics, so this suite must
not turn exact child names or named-role matches into PASS/FAIL conditions.

These tests cover only producer-owned orchestration invariants that are
mechanically provable from source.  For Codex, when the business flow needs a
child the coordinator must use Codex's *documented native subagent/custom-agent
delegation* (delegate to the exact installed name and wait), never inline or
simulate the child, keep the delegation chain non-recursive (the payload
carries only this stage's business fields and no coordinator delegates to its
own machine name), reserve "runtime blocker" for a real machine/runtime
delegation error, keep Codex/OpenCode invocation syntax isolated, and keep
characterization-only tool envelopes out of production text.  An under-
development / default-off runtime feature (Code Mode, programmatic tool-calling
discovery) must never become a production prerequisite.

The analyzer is a target-scoped projection (issue #47): the shared root
``.apm/agents`` has no ``professor-contact-analyzer.agent.md``; Codex reads the
Codex package projection and OpenCode reads the OpenCode package projection.
Every other agent document is target-agnostic and lives at the root, so the
tests resolve source paths through separate Codex/OpenCode resolvers instead of
one generic path.
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
    ROOT_AGENTS,
    SKILL_CODEX_REGION,
    SKILL_PATH,
    all_production_source_paths,
    codex_agent_path,
    frontmatter_and_body,
    opencode_agent_path,
    read,
    segment,
)

# Issue #51 §2 keeps the "no private envelope" requirement in production and
# bans only version-private surfaces: a measured tool-search namespace, the raw
# spawn request shape, or a fixed catalog command from one characterization
# run.  `spawn_agent` itself is a documented Codex tool name, so only its call
# form stays out of production instructions.
FORBIDDEN_PRIVATE_LITERALS = (
    "ALL_TOOLS",
    "multi_agent_v1__",
    "spawn_agent(",
    "agent_type=",
    "agent_role=",
)

# Words that must never appear as an ordinary Codex delegation prerequisite in
# production source.  `professor-research#26/#27` reconciled the contract to
# documented native delegation; Code Mode and programmatic tool-calling
# discovery are under development / default-off and cannot gate a real child.
CODEX_OBSOLETE_PREREQUISITES = (
    "Code Mode",
    "programmatic tool-calling",
    "discovery surface",
)

# Each coordinator source document may state the invariant in its own
# language; every invariant needs at least one of its literals, verbatim.
# This replaces issue #51's obsolete "discover the capability first" gate with
# the reconciled documented-native-delegation contract (issue #47 Phase 4).
CODEX_NATIVE_DELEGATION_INVARIANTS = {
    "documented-native-delegation": (
        "使用 Codex 官方文档所定义的原生委派能力",
        "documented native subagent/custom-agent delegation",
    ),
    "delegate-exact-name-and-wait": (
        "按 exact installed name 委派已安装的 named custom agent 并等待其结果",
        "delegate to the exact installed named custom agent and wait for its result",
    ),
    "no-inline-no-shell-eval": (
        "不得 inline 或模拟 child 的业务",
        "never inline or simulate the child's work",
    ),
    "only-real-machine-error-blocker": (
        "只有真实的机器级/运行时委派错误才能记为 Codex runtime/feature blocker",
        "only a real machine-level/runtime delegation error may be recorded as a "
        "Codex runtime/feature blocker",
    ),
    "no-undocumented-prerequisite": (
        "都不是普通 Codex 委派的前提",
        "is a prerequisite for ordinary delegation",
    ),
}


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


def _root_agent(name: str) -> Path:
    """Physical path of a target-agnostic (root) agent source document."""
    return ROOT_AGENTS / f"{name}.agent.md"


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
    body = frontmatter_and_body(codex_agent_path(name))[1]
    return segment(body, markers[0], markers[1])


def _opencode_branch(name: str) -> str:
    markers = OPENCODE_BRANCH_MARKERS[name]
    body = frontmatter_and_body(opencode_agent_path(name))[1]
    return segment(body, markers[0], markers[1])


class CodexDelegationInventoryTests(unittest.TestCase):
    """Issue #47 Phase 2: logical identity inventory and physical layout are
    two distinct invariants.  test_p47_target_isolation.py is the layout
    authority; these tests prove the #52 inventory helper does not silently
    assume one analyzer file under the shared root."""

    def test_logical_source_inventory_partitions_the_eight_repo_agents(self):
        delegators = set(CODEX_NESTED_DELEGATOR_AGENTS)
        leaves = set(CODEX_NON_DELEGATORS)
        self.assertFalse(delegators & leaves)
        self.assertEqual(delegators | leaves, set(ALL_AGENT_NAMES))

    def test_root_analyzer_is_absent_and_both_target_projections_exist(self):
        analyzer = "professor-contact-analyzer"
        self.assertFalse(
            (ROOT_AGENTS / f"{analyzer}.agent.md").exists(),
            "issue #47 removed the mixed-target root analyzer; do not restore it",
        )
        self.assertTrue(codex_agent_path(analyzer).exists())
        self.assertTrue(opencode_agent_path(analyzer).exists())

    def test_both_analyzer_projections_keep_the_same_machine_name(self):
        for path in (
            codex_agent_path("professor-contact-analyzer"),
            opencode_agent_path("professor-contact-analyzer"),
        ):
            with self.subTest(path=path):
                frontmatter, _ = frontmatter_and_body(path)
                self.assertIn("name: professor-contact-analyzer", frontmatter)

    def test_seven_shared_agents_resolve_to_the_root_for_both_targets(self):
        shared = [name for name in ALL_AGENT_NAMES if name != "professor-contact-analyzer"]
        self.assertEqual(len(shared), 7)
        for name in shared:
            with self.subTest(name=name):
                self.assertEqual(codex_agent_path(name), _root_agent(name))
                self.assertEqual(opencode_agent_path(name), _root_agent(name))
                self.assertTrue(_root_agent(name).exists())

    def test_production_source_paths_cover_skill_plus_seven_root_agents_plus_two_analyzers(self):
        paths = all_production_source_paths()
        self.assertIn(SKILL_PATH, paths)
        # 7 shared root agents + 2 target-scoped analyzer projections = 9 agent docs
        self.assertEqual(len(paths), 1 + 7 + 2)
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(path.exists(), f"missing production source: {path}")


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
        body = frontmatter_and_body(codex_agent_path("professor-contact-analyzer"))[1]
        self.assertRegex(
            body,
            r"(?is)max_concurrent_threads_per_session[\s\S]{0,300}(?:不等价|不能互相替代)",
        )

    def test_email_generator_stage5_business_contract_is_untouched(self):
        body = frontmatter_and_body(_root_agent("professor-contact-email-generator"))[1]
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
                self.assertIn(needle, read(_root_agent(leaf)))

    def test_idea_generator_codex_sibling_boundary_stays_caller_owned(self):
        body = frontmatter_and_body(_root_agent("professor-contact-idea-generator"))[1]
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


class CodexNativeDelegationContractTests(unittest.TestCase):
    """Issue #47 Phase 4: production source requires documented native
    delegation (not a Code Mode discovery gate) before awaiting a child."""

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
                   for literal in CODEX_NATIVE_DELEGATION_INVARIANTS[invariant])

    def test_every_codex_coordinator_states_the_native_delegation_invariants(self):
        for label, branch in self.branches.items():
            for invariant in CODEX_NATIVE_DELEGATION_INVARIANTS:
                with self.subTest(doc=label, invariant=invariant):
                    self.assertTrue(
                        self._has(branch, invariant),
                        f"{label}: production source omits {invariant}",
                    )

    def test_native_delegation_reads_as_a_precondition_to_waiting_on_children(self):
        for label, branch in self.branches.items():
            with self.subTest(doc=label):
                requirement = _first_position(
                    branch, CODEX_NATIVE_DELEGATION_INVARIANTS["documented-native-delegation"])
                wait = WAIT_PATTERN.search(branch)
                self.assertIsNotNone(wait, f"{label}: no wait-for-child-result step")
                self.assertLess(
                    requirement, wait.start(),
                    "documented native delegation must be stated before the "
                    "delegated child is awaited",
                )

    def test_generated_codex_projection_keeps_the_native_delegation_invariant(self):
        """`apm install` embeds each agent body verbatim as
        `developer_instructions` and copies SKILL.md itself, so the invariant
        must survive in exactly that projected segment."""
        for name in CODEX_NESTED_DELEGATOR_AGENTS:
            frontmatter, body = frontmatter_and_body(codex_agent_path(name))
            projected = HTML_COMMENT_PATTERN.sub("", body)
            with self.subTest(agent=name):
                self.assertTrue(self._has(projected, "documented-native-delegation"),
                                f"{name}: projection loses the native delegation gate")
                self.assertFalse(
                    self._has("\n".join(frontmatter), "documented-native-delegation"),
                    f"{name}: frontmatter is not projected into Codex instructions",
                )
        self.assertTrue(self._has(read(SKILL_PATH), "documented-native-delegation"))

    def test_no_production_codex_source_makes_code_mode_discovery_a_prerequisite(self):
        """The obsolete Code Mode / programmatic tool-calling discovery gate
        must not appear anywhere in the production Codex contract."""
        docs = {
            "SKILL.md Codex caller": segment(
                read(SKILL_PATH), SKILL_CODEX_REGION[0], SKILL_CODEX_REGION[1]),
        }
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            docs[owner] = _codex_branch(owner)
        for label, branch in docs.items():
            for literal in CODEX_OBSOLETE_PREREQUISITES:
                with self.subTest(doc=label, literal=literal):
                    self.assertNotIn(literal, branch)

    def test_opencode_branches_stay_free_of_the_codex_native_delegation_wording(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                branch = _opencode_branch(owner)
                self.assertNotIn("Code Mode", branch)
                self.assertNotIn(
                    "使用 Codex 官方文档所定义的原生委派能力", branch)
                self.assertRegex(
                    branch, r"(?is)(?:task\s*\(|Task 委派|native Task)",
                    "OpenCode projection keeps its own Task delegation path",
                )

    def test_leaf_sources_do_not_gain_a_delegation_contract(self):
        for leaf in CODEX_NON_DELEGATORS:
            text = read(_root_agent(leaf))
            for invariant in CODEX_NATIVE_DELEGATION_INVARIANTS:
                with self.subTest(leaf=leaf, invariant=invariant):
                    self.assertFalse(self._has(text, invariant))

    def test_no_version_private_tool_envelope_reaches_production_contracts(self):
        for path in all_production_source_paths():
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
            frontmatter, body = frontmatter_and_body(codex_agent_path(name))
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
            text = read(_root_agent(leaf))
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
