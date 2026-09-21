"""Deterministic Codex orchestration contract (issue #51/#55 behaviour, issue #47 layout).

The merge gate is intentionally identity-agnostic.  fixtures@9 treats
requested_role / loaded_identity as optional diagnostics, so this suite must
not turn exact child names or named-role matches into PASS/FAIL conditions.

These tests cover only producer-owned orchestration invariants that are
mechanically provable from source: delegate and wait when a child is required
through Codex's *documented native subagent/custom-agent delegation* (direct
delegation to the exact installed name, with no capability probe as a
prerequisite), never inline or simulate the child, fail closed on a real
machine-level delegation error, keep Codex/OpenCode invocation syntax isolated,
keep the delegation chain non-recursive (the payload carries only this stage's
business fields and no coordinator delegates to its own machine name), keep
characterization-only tool envelopes out of production text, and lock the
top-level Stage 1–5 routing matrix and the Stage 3/5 ownership boundaries.  An
under-development / default-off runtime feature (Code Mode, programmatic
tool-calling discovery) must never become a production prerequisite.
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
# This replaces issue #51's obsolete "discover the capability first" gate and
# issue #55's routing correction with one documented-native-delegation
# contract: direct delegation to the exact installed name, no capability probe
# prerequisite, no shell/eval substitution.
CODEX_NATIVE_DELEGATION_INVARIANTS = {
    "documented-native-delegation": (
        "使用 Codex 官方文档所定义的原生委派能力",
        "documented native subagent/custom-agent delegation",
        "需要 child 时直接委派",
        "directly delegate the PDF fill to the installed named custom agent",
        "directly delegate to the installed named custom agent",
    ),
    "delegate-exact-name-and-wait": (
        "按 exact installed name 委派已安装的 named custom agent 并等待其结果",
        "delegate to the exact installed named custom agent and wait for its result",
        "直接要求 Codex 使用已安装的 exact named custom agent，并等待它返回结果",
    ),
    "no-inline-no-shell-eval": (
        "不得 inline 或模拟 child 的业务",
        "never inline or simulate the child's work",
        "不得由 parent inline 模拟或代替 child 完成业务",
    ),
    "only-real-machine-error-blocker": (
        "只有真实的机器级/运行时委派错误才能记为 Codex runtime/feature blocker",
        "only a real machine-level/runtime delegation error may be recorded as a "
        "Codex runtime/feature blocker",
        "只有真实的 machine-level delegation failure 才记录 Codex runtime/feature blocker",
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


def agent_path(name: str) -> Path:
    """Issue #47 layout resolution for the #57 gate suites: shared agents stay
    at the repository root and the target-scoped analyzer resolves to its
    Codex projection, which carries the Codex runtime gates."""
    return codex_agent_path(name)


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


class EarlyRuntimeRoutingGateTests(unittest.TestCase):
    """Runtime routing must survive bounded/partial instruction reads.

    PC57-R1 characterization: the root read only a leading slice of the
    installed Skill (~240 lines), missed the Codex branch that started
    later, and copied the earlier OpenCode route into shell commands.  The
    contract that survives that evidence is *section order*: the runtime
    routing gate is a load-bearing preamble that must precede every target
    branch and every business section.  Per the Test Engineer Rule the
    ordering is asserted structurally against the documents' own headings —
    no fixed line budget, because no characterization run establishes a
    stable read boundary measured in lines.
    """

    GATE_HEADING = "## Runtime routing gate (read first)"

    # Invariants the gate section itself must state (heading-delimited).
    GATE_LITERALS = (
        "当前 host",
        "真实委派动作",
        "不是能力探测前置条件",
        "machine-level failure",
        "`opencode run`",
        "`codex exec`",
    )

    # First business/instruction section of each document, named by that
    # document's own heading.
    FIRST_BUSINESS_SECTION = {
        "SKILL.md": "## What this is for",
        "professor-contact-downloader": "## Input",
        "professor-contact-analyzer": "## 套磁方向方法论",
        "professor-contact-email-generator": "## Authoritative base contract",
    }

    def _gate_section(self, label: str, body: str) -> str:
        start = body.index(self.GATE_HEADING)
        nxt = body.find("\n## ", start + len(self.GATE_HEADING))
        self.assertLess(start, nxt if nxt != -1 else len(body), label)
        return body[start : nxt if nxt != -1 else len(body)]

    def _assert_gate_precedes_business(self, label: str, body: str):
        gate = body.index(self.GATE_HEADING)
        self.assertLess(
            gate,
            body.index(self.FIRST_BUSINESS_SECTION[label]),
            label,
        )
        for literal in self.GATE_LITERALS:
            self.assertIn(literal, self._gate_section(label, body), label)

    def test_root_skill_front_loads_all_stage_routes_before_business_detail(self):
        body = frontmatter_and_body(SKILL_PATH)[1]
        self._assert_gate_precedes_business("SKILL.md", body)
        gate = body.index(self.GATE_HEADING)
        first_business = body.index(self.FIRST_BUSINESS_SECTION["SKILL.md"])
        for stage, owner in {
            "1": "professor-contact-downloader",
            "2": "professor-contact-analyzer",
            "3": "professor-contact-idea-generator",
            "4": "professor-contact-selection",
            "5": "professor-contact-email-generator",
        }.items():
            with self.subTest(stage=stage):
                route = body.index(f"Stage {stage} → `{owner}`")
                self.assertLess(gate, route)
                self.assertLess(route, first_business)
        self.assertLess(gate, body.index("### OpenCode 分支"))
        self.assertLess(gate, body.index("### Codex 分支"))

    def test_every_nested_coordinator_front_loads_the_same_runtime_gate(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                body = frontmatter_and_body(agent_path(owner))[1]
                self._assert_gate_precedes_business(owner, body)
                gate = body.index(self.GATE_HEADING)
                self.assertLess(
                    gate,
                    body.index(CODEX_BRANCH_MARKERS[owner][0]),
                )
                # Issue #47 target isolation: the OpenCode branch lives in the
                # OpenCode projection, and the same gate must front-load there.
                opencode_body = frontmatter_and_body(opencode_agent_path(owner))[1]
                self.assertLess(
                    opencode_body.index(self.GATE_HEADING),
                    opencode_body.index(OPENCODE_BRANCH_MARKERS[owner][0]),
                )


class NestedNativeInvocationCheckpointTests(unittest.TestCase):
    """Nested coordinators must turn routing prose into a concrete action.

    PC57-R1 ``OwoMoS`` reached the installed analyzer, prepared a real local
    paper-analysis job, and then returned
    ``codex_runtime_delegation_unavailable`` without making any native child
    call.  The early abstract gate was present, but the long coordinator flow
    diluted it before the execution and return boundaries.  Keep the stable
    documented tool name (without freezing a private call signature) in every
    nested gate, and repeat the zero-attempt prohibition at the analyzer's
    load-bearing execution and return checkpoints.
    """

    def test_nested_gates_name_the_native_tool_without_a_call_signature(self):
        for owner in CODEX_NESTED_DELEGATOR_AGENTS:
            with self.subTest(owner=owner):
                body = frontmatter_and_body(agent_path(owner))[1]
                start = body.index("## Runtime routing gate (read first)")
                end = body.index("\n## ", start + 1)
                gate = body[start:end]
                self.assertIn("`spawn_agent`", gate, owner)
                self.assertNotRegex(gate, r"spawn_agent\s*\(", owner)

    def test_analyzer_repeats_native_call_at_execution_boundary(self):
        body = frontmatter_and_body(agent_path("professor-contact-analyzer"))[1]
        start = body.index("6. **本地 route → `paper-analysis full`")
        end = body.index("6.5 **future-work sidecar", start)
        execution = body[start:end]
        self.assertIn("`spawn_agent`", execution)
        self.assertIn("exact named `paper-analysis`", execution)
        self.assertRegex(execution, r"未调用[\s\S]{0,120}不得返回")

    def test_analyzer_waits_for_running_child_without_local_timeout(self):
        """A wait heartbeat is not a child failure.

        PC47-R2 observed a healthy paper-analysis child still marked running
        after four wait calls.  The analyzer closed it and invented
        ``paper_analysis_timeout``, losing the whole Stage 2 output.  The
        production contract must make the terminal-state boundary explicit.
        """
        body = frontmatter_and_body(agent_path("professor-contact-analyzer"))[1]
        start = body.index("### Codex 分支")
        end = body.index("## Input", start)
        codex = body[start:end]
        for literal in (
            "单次等待超时只是 heartbeat",
            "只要 child 状态仍是 running、pending 或 inProgress，就继续等待",
            "不得按等待次数或本地经过时间关闭、打断或放弃 child",
            "completed、明确的 machine-level failure 或用户中止",
        ):
            self.assertIn(literal, codex)

    def test_analyzer_audits_zero_attempt_before_its_only_final_message(self):
        body = frontmatter_and_body(agent_path("professor-contact-analyzer"))[1]
        start = body.index("### Step 7 — Return value")
        end = body.index("## Errors", start)
        return_contract = body[start:end]
        self.assertIn("`spawn_agent`", return_contract)
        self.assertIn("codex_runtime_delegation_unavailable", return_contract)
        self.assertRegex(return_contract, r"零次[\s\S]{0,160}禁止")


class EarlyMachineOutputGateTests(unittest.TestCase):
    """Machine-returning agents must not leak progress prose as results.

    The single-message protocol is load-bearing preamble: the Machine output
    gate must be the first H2 section of its document and must precede the
    document's business/tool-flow/return-value sections.  Ordering is
    asserted structurally against the documents' own headings — no fixed
    line budget (Test Engineer Rule).
    """

    MACHINE_OUTPUT_AGENTS = (
        "professor-contact-analyzer",
        "professor-contact-email-validator",
        "professor-contact-idea-generator",
        "professor-contact-selection",
        "professor-contact-style-validator",
    )

    MACHINE_GATE_HEADING = "## Machine output gate (read first)"

    MACHINE_GATE_LITERALS = (
        "不要发送进度说明",
        "唯一一条 assistant message",
        "JSON object",
    )

    FIRST_BUSINESS_SECTION = {
        "professor-contact-analyzer": "## 套磁方向方法论",
        "professor-contact-email-validator": "## 校验规则",
        "professor-contact-idea-generator": "## 核心平衡原则",
        "professor-contact-selection": "## Input",
        "professor-contact-style-validator": "## Input",
    }

    def _gate_section(self, body: str) -> str:
        start = body.index(self.MACHINE_GATE_HEADING)
        nxt = body.find("\n## ", start + len(self.MACHINE_GATE_HEADING))
        return body[start : nxt if nxt != -1 else len(body)]

    def test_every_json_agent_front_loads_single_message_protocol(self):
        for owner in self.MACHINE_OUTPUT_AGENTS:
            with self.subTest(owner=owner):
                body = frontmatter_and_body(agent_path(owner))[1]
                headings = [
                    match.start() for match in re.finditer(r"(?m)^## ", body)
                ]
                self.assertTrue(headings, owner)
                gate = body.index(self.MACHINE_GATE_HEADING)
                self.assertEqual(gate, headings[0], owner)
                self.assertLess(
                    gate,
                    body.index(self.FIRST_BUSINESS_SECTION[owner]),
                    owner,
                )
                section = self._gate_section(body)
                for literal in self.MACHINE_GATE_LITERALS:
                    self.assertIn(literal, section, owner)


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
        for path in all_production_source_paths():
            text = read(path)
            for literal in FORBIDDEN_PRIVATE_LITERALS:
                with self.subTest(path=path.name, literal=literal):
                    self.assertNotIn(literal, text)
            self.assertNotRegex(text, r"(?i)tool[- ]catalog")
            self.assertNotRegex(text, r"枚举 tool catalog")
            self.assertNotRegex(text, r"必须先枚举[\s\S]{0,40}(?:才|方)允许")


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
                if literal == "Code Mode":
                    # #57's reconciliation keeps the literal only as a
                    # rejected inference source, never a prerequisite.
                    for match in re.finditer(re.escape(literal), branch):
                        context = branch[max(0, match.start() - 24):match.start()]
                        self.assertTrue(
                            "缺少" in context or "reject" in context.lower(),
                            f"{label}: Code Mode must stay a rejected inference "
                            f"source, saw context: {context!r}",
                        )
                    self.assertIsNone(
                        re.search(r"必须[^。\n]*Code Mode", branch),
                        f"{label}: Code Mode must never be required",
                    )
                    continue
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
