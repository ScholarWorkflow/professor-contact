"""Deterministic #57 acceptance: routing invariants and verifier behavior.

Covers PC57-D1's source-contract minimum for Stage-2/Stage-4 routing plus the
adapter@9 evidence interpretation of the ``stage2-routing`` and dynamically
projected ``stage4-needs-input`` checkpoints.
"""
import importlib.util
import json
import re
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"
REPO_ROOT = Path(__file__).resolve().parents[4]
# Issue #47 target isolation: the analyzer is target-scoped, so the #57 Codex
# source contract reads the Codex projection and the OpenCode-branch contract
# reads the OpenCode projection.  The shared root analyzer must stay absent.
ANALYZER_PATH = (
    REPO_ROOT / "packages" / "professor-contact-codex" / ".apm" / "agents"
    / "professor-contact-analyzer.agent.md")
OPENCODE_ANALYZER_PATH = (
    REPO_ROOT / "packages" / "professor-contact-opencode" / ".apm" / "agents"
    / "professor-contact-analyzer.agent.md")
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"

# The frozen PC53 regression expectation.  The dynamic projection must keep
# reproducing exactly this payload for the unchanged #53 fixture.
PC53_REGRESSION_EXPECTATION = [{
    "professor": "Example Professor",
    "kind": "direction",
    "direction_ids": ["DIR00001"],
    "candidates": [
        {
            "id": "idea-001",
            "title": "Adaptive extension",
            "one_liner": "Explore an adaptive extension of the synthetic processing setting.",
            "research_question": "How can the synthetic setting adapt to changing conditions?",
            "fit": "high",
        },
        {
            "id": "idea-002",
            "title": "Robust extension",
            "one_liner": "Explore robustness under changing synthetic conditions.",
            "research_question": "How robust is the synthetic setting under change?",
            "fit": "medium",
        },
    ],
}]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load_module(
    "issue57_routing_verifier_for_tests",
    RUNTIME_DIR / "verify_issue32_e2e.py",
)
issue53_fixture = load_module(
    "issue57_pc53_fixture_for_tests",
    RUNTIME_DIR / "prepare_issue53_stage4_fixture.py",
)
issue57_fixture = load_module(
    "issue57_pc57_fixture_for_tests",
    RUNTIME_DIR / "prepare_issue57_stage4_fixture.py",
)


def _codex_branch(text: str) -> str:
    start = text.index("### Codex 分支")
    return text[start:text.index("## Input", start)]


def _formal_relation_children(relation) -> list[str] | None:
    """Receivers of a relation that satisfies the parser's formal spawn
    shape, or ``None`` for relations that are not formal spawns.

    adapter@9 never partially normalizes: a ``spawnAgent`` relation without
    a non-empty owner, without a non-empty ``receiver_thread_ids`` list, or
    with any receiver that is not a non-empty string is corrupted evidence
    that fails the whole payload closed before any normalized relation
    exists, so it can never appear in ``thread_relations``.  This helper
    therefore rejects such a relation outright instead of silently skipping
    it."""
    if not isinstance(relation, dict) or relation.get("tool") != "spawnAgent":
        return None
    sender = relation.get("sender_thread_id")
    receivers = relation.get("receiver_thread_ids")
    if (not isinstance(sender, str) or not sender
            or not isinstance(receivers, list) or not receivers
            or not all(isinstance(child, str) and child
                       for child in receivers)):
        raise ValueError(
            "malformed formal spawnAgent relation: adapter@9 fails the whole "
            "evidence closed before normalization, so a normalized relation "
            "graph can never contain one")
    return receivers


def _delegation_summary(relations) -> dict:
    """Build adapter@9's delegation summary from a normalized relation graph.

    The pinned parser derives the summary mechanically from the formal
    ``spawnAgent`` relations of the response under the frozen
    ``confirmed_rule`` shape (exact ``spawnAgent`` tool, non-empty
    ``sender_thread_id`` owner, non-empty ``receiver_thread_ids`` of
    non-empty strings), so ``child_thread_ids`` is the sorted distinct
    concrete child set and a synthetic fixture must never hand-write a
    summary that disagrees with its own ``thread_relations``.  A malformed
    formal relation is corrupted evidence that fails the whole payload
    closed before normalization — it can never appear in a normalized
    graph, so the helper raises on one instead of partially accepting the
    rest of the graph.
    """
    children: set[str] = set()
    for relation in relations:
        receivers = _formal_relation_children(relation)
        if receivers:
            children.update(receivers)
    if children:
        return {
            "state": "confirmed",
            "formal_child_count": len(children),
            "child_thread_ids": sorted(children),
            "basis": ["formal_spawn_relation"],
            "reason_code": None,
        }
    return {
        "state": "unobservable",
        "formal_child_count": 0,
        "child_thread_ids": [],
        "basis": [],
        "reason_code": "no_supported_formal_spawn_relation",
    }


# The pinned adapter@9 fixture-status contract enumerates exactly eight
# statuses (skills-test-fixtures@88d2056, FIXTURE_STATUSES).  The
# prerequisite gate must freeze the whole enum verbatim, with the pinned
# §8 semantics: harness and dependency blockers are NOT TESTED (never
# INVALID), only corrupted adapter evidence and out-of-contract statuses
# fail closed as INVALID, and the two named-role identity diagnostics
# stay non-gating.  Both checkpoints (Stage-2 routing and Stage-4
# needs-input) are graded against this one shared table so they cannot
# drift apart.
ADAPTER_STATUS_MATRIX = (
    ("BLOCKED_DEPENDENCY", "blocked", "BLOCKED_RUNTIME_PROVIDER"),
    ("HARNESS_ERROR", "blocked", "BLOCKED_RUNTIME_PROVIDER"),
    ("HARNESS_CONTAMINATION", "blocked", "BLOCKED_RUNTIME_PROVIDER"),
    ("NOT_RUN", "blocked", "BLOCKED_RUNTIME_PROVIDER"),
    ("INVALID_EVIDENCE", "invalid", "INVALID_TEST_EXECUTION"),
    ("SOMETHING_ELSE", "invalid", "INVALID_TEST_EXECUTION"),
)
NON_GATING_IDENTITY_STATUSES = ("HARNESS_DISPATCH_UNCONFIRMED",
                                "HARNESS_DISPATCH_MISMATCH")


class SyntheticDelegationSummaryShapeTests(unittest.TestCase):
    """The helper is synthetic adapter@9 evidence: it must mirror the
    parser's ``confirmed_rule`` exactly and refuse — never normalize — any
    relation the parser would fail closed before normalization."""

    def test_complete_formal_relation_yields_confirmed_summary(self):
        summary = _delegation_summary([{
            "tool": "spawnAgent", "status": "completed",
            "sender_thread_id": "root-1",
            "receiver_thread_ids": ["coordinator-1", "coordinator-1"],
        }])
        self.assertEqual(summary["state"], "confirmed")
        self.assertEqual(summary["child_thread_ids"], ["coordinator-1"])
        self.assertEqual(summary["formal_child_count"], 1)
        self.assertEqual(summary["basis"], ["formal_spawn_relation"])

    def test_non_spawn_relations_do_not_contribute_children(self):
        # A wait-tool relation is a normalized relation but never a formal
        # spawn, so a wait-only graph stays legitimately unobservable.
        summary = _delegation_summary([
            {"tool": "wait", "sender_thread_id": "root-1",
             "receiver_thread_ids": ["child-1"]},
        ])
        self.assertEqual(summary["state"], "unobservable")
        self.assertEqual(summary["child_thread_ids"], [])
        self.assertEqual(summary["basis"], [])
        self.assertEqual(
            summary["reason_code"], "no_supported_formal_spawn_relation")

    def test_malformed_formal_relations_are_rejected_before_normalization(self):
        # The parser appends a formal relation to normalized evidence only
        # after the full shape check and fails the whole payload closed
        # otherwise, so no normalized graph can ever contain one: the
        # helper raises instead of deriving an ``unobservable`` summary
        # from it.  An empty receiver list is corrupted on a completed
        # formal spawn and silently skipped while in progress — either way
        # it never reaches a normalized graph.
        for relation in (
            {"tool": "spawnAgent", "status": "completed",
             "receiver_thread_ids": ["child-1"]},
            {"tool": "spawnAgent", "status": "completed",
             "sender_thread_id": "", "receiver_thread_ids": ["child-1"]},
            {"tool": "spawnAgent", "status": "completed",
             "sender_thread_id": "root-1", "receiver_thread_ids": None},
            {"tool": "spawnAgent", "status": "completed",
             "sender_thread_id": "root-1", "receiver_thread_ids": []},
            {"tool": "spawnAgent", "status": "item/started",
             "sender_thread_id": "root-1", "receiver_thread_ids": []},
            {"tool": "spawnAgent", "status": "completed",
             "sender_thread_id": "root-1", "receiver_thread_ids": "child-1"},
            {"tool": "spawnAgent", "status": "completed",
             "sender_thread_id": "root-1", "receiver_thread_ids": 123},
            {"tool": "spawnAgent", "status": "completed",
             "sender_thread_id": "root-1",
             "receiver_thread_ids": ["good-child", 123]},
            {"tool": "spawnAgent", "status": "completed",
             "sender_thread_id": "root-1",
             "receiver_thread_ids": ["good-child", None]},
            {"tool": "spawnAgent", "status": "completed",
             "sender_thread_id": "root-1", "receiver_thread_ids": [""]},
        ):
            with self.subTest(relation=relation):
                with self.assertRaises(ValueError):
                    _formal_relation_children(relation)
                with self.assertRaises(ValueError):
                    _delegation_summary([relation])

    def test_mixed_valid_and_malformed_relations_are_rejected_whole(self):
        # adapter@9 fails the whole evidence closed on the malformed
        # relation, so the valid relation is never summarized: there is no
        # "confirmed / kept-child" partial normalization to mirror.
        with self.assertRaises(ValueError):
            _delegation_summary([
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "root-1",
                 "receiver_thread_ids": ["good-child", 123]},
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "root-1",
                 "receiver_thread_ids": ["kept-child"]},
            ])


class Stage2CodexSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ANALYZER_PATH.exists():
            raise AssertionError(f"missing analyzer document: {ANALYZER_PATH}")
        cls.analyzer = ANALYZER_PATH.read_text(encoding="utf-8")
        cls.codex = _codex_branch(cls.analyzer)
        if not OPENCODE_ANALYZER_PATH.exists():
            raise AssertionError(
                f"missing analyzer document: {OPENCODE_ANALYZER_PATH}")
        cls.opencode_analyzer = OPENCODE_ANALYZER_PATH.read_text(encoding="utf-8")

    def test_required_child_delegation_is_the_first_action_then_wait(self):
        self.assertIn("原生委派就是处理该 child 的第一个动作", self.codex)
        delegation = self.codex.index("第一个动作")
        wait = self.codex.index("等待 child 结果返回")
        consume = self.codex.index("才能继续依赖该结果")
        self.assertLess(delegation, wait)
        self.assertLess(wait, consume)

    def test_unavailable_blocker_is_legal_only_after_current_run_failure(self):
        self.assertIn("codex_runtime_delegation_unavailable", self.codex)
        self.assertIn("当前运行", self.codex)
        self.assertRegex(
            self.codex,
            r"codex_runtime_delegation_unavailable[^。]*当前运行[^。]*delegation failure",
            "the blocker code must be bound to a current-run returned failure",
        )

    def test_catalog_discovery_prose_and_prior_run_inference_are_forbidden(self):
        for forbidden_source in (
            "工具目录", "Code Mode", "推理或行文", "以往运行",
        ):
            with self.subTest(forbidden_source=forbidden_source):
                self.assertIn(forbidden_source, self.codex)
        self.assertRegex(
            self.codex,
            r"绝不从[^。]*工具目录[^。]*以往运行",
            "the inference sources must be rejected in one explicit rule",
        )

    def test_no_private_spawn_signature_and_no_code_mode_prerequisite(self):
        for forbidden in ("spawn_agent(", "agent_type=", "agent_role=", "agent_path",
                          "task(", "Task("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.codex)
        # Code Mode may appear only as a rejected inference source, never as a
        # delegation prerequisite.
        for match in re.finditer(r"Code Mode", self.codex):
            context = self.codex[max(0, match.start() - 24):match.start()]
            self.assertTrue(
                "缺少" in context or "reject" in context.lower(),
                f"Code Mode must stay a rejected inference source, saw context: {context!r}",
            )
        self.assertIsNone(re.search(r"必须[^。\n]*Code Mode", self.codex))

    def test_opencode_branch_keeps_depth_fallback_and_task_semantics(self):
        opencode = self.opencode_analyzer[
            self.opencode_analyzer.index("### OpenCode 分支"):self.opencode_analyzer.index("### Codex 分支")]
        self.assertIn("subagent_depth", opencode)
        self.assertIn("深度受限", opencode)
        self.assertIn("摘要级脉络", opencode)
        self.assertIn("不构成 Codex 侧的迁移成功证据", opencode)


class Stage4SkillEntryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SKILL_PATH.exists():
            raise AssertionError(f"missing Skill document: {SKILL_PATH}")
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")
        marker = "#### Codex 下 Stage 1–5 顶层 routing matrix"
        start = cls.skill.index(marker)
        end = cls.skill.index("#### Stage 2 在 Codex 下的委派链与用户选择", start)
        cls.entry = cls.skill[start:end]

    def test_stage4_entry_fixes_delegation_wait_consume_order(self):
        self.assertIn("FIRST routing action", self.entry)
        first = self.entry.index("FIRST routing action")
        delegate = self.entry.index("delegate professor-contact-selection")
        wait = self.entry.index("-> wait")
        consume = self.entry.index("only then consume child result")
        self.assertLess(first, delegate)
        self.assertLess(delegate, wait)
        self.assertLess(wait, consume)

    def test_stage4_entry_covers_selection_present_and_omitted(self):
        self.assertRegex(
            self.entry,
            r"无论 `selection` 提供还是省略",
            "the entry rule must fire for both selection states",
        )
        self.assertIn("selection omitted", self.entry)
        self.assertIn("不是 root 的提前返回条件", self.entry)

    def test_stage4_omitted_selection_forbids_root_preflight_before_delegation(self):
        """The observed R3-B failure must not recur as an inline root preflight."""
        self.assertIn("委派前不得读取任何 Stage 4 状态文件", self.entry)
        self.assertIn("不得先用 shell 或文件工具检查候选", self.entry)
        self.assertIn("root 自行返回 `needs_input` 视为 routing failure", self.entry)

    def test_stage4_entry_does_not_duplicate_child_business_instructions(self):
        # The added entry rule stays at the routing level: no selection
        # schema, no candidate field list, no finalize usage.
        marker = "Stage 4 请求没有例外顺序"
        added_block = self.entry[self.entry.index(marker):]
        for child_business in ("direction_ids", "research_question", "stage4-finalize"):
            with self.subTest(child_business=child_business):
                self.assertNotIn(
                    child_business, added_block,
                    "the Stage-4 entry rule must not duplicate child business "
                    "instructions into root",
                )

    def test_named_identity_stays_out_of_the_routing_matrix(self):
        self.assertNotRegex(
            self.entry, r"expected[-_]agent",
            "routing must never be pinned to a machine identity field",
        )


class Stage2RoutingVerifierTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.program = self.root / "program"
        self.program.mkdir()

    def args(self, **overrides):
        values = {
            "program_root": self.program,
            "consumer_root": None,
            "eval_response": None,
            "adapter_output": None,
            "producer_sha": "",
            "output": None,
            "min_edges": 1,
            "required_depth": 1,
            "pre_snapshot": None,
            "post_snapshot": None,
        }
        values.update(overrides)
        return Namespace(**values)

    def _relation(self, sender, children, *, status="completed", parent=None):
        relation = {
            "tool": "spawnAgent", "status": status,
            "sender_thread_id": sender, "receiver_thread_ids": list(children),
        }
        if parent is not None:
            relation["parent_thread_id"] = parent
        return relation

    def _write_evidence(self, relations, *, envelope_ok=True, extra_adapter=None,
                        fixture_status="FIXTURE_READY", omit_fixture_status=False):
        # A hand-written delegation override skips the derivation: the
        # helper raises on a malformed formal relation, and the
        # defense-in-depth cases that need one always supply their own
        # deliberately impossible summary.
        override = (extra_adapter or {}).get("delegation")
        adapter = {
            "fixture_status": fixture_status,
            "delegation": (override if override is not None
                           else _delegation_summary(relations)),
            "dispatch": {"thread_relations": relations},
        }
        if extra_adapter:
            adapter.update(extra_adapter)
        if omit_fixture_status:
            del adapter["fixture_status"]
        adapter_path = self.root / "adapter.json"
        adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
        response_path = self.root / "response.json"
        response_path.write_text(json.dumps({
            "passed": envelope_ok,
            "output": {
                "exit_code": 0 if envelope_ok else 1,
                "termination_reason": "completed" if envelope_ok else "error",
                "thread_id": "root-1",
                "app_server_events": [],
            },
        }), encoding="utf-8")
        return adapter_path, response_path

    def _run(self, relations, **kwargs):
        adapter, response = self._write_evidence(relations, **kwargs)
        return verifier._checkpoint_stage2_routing(self.args(
            eval_response=response, adapter_output=adapter))

    def _nested_relations(self, *, root_status="completed", nested_status="item/started",
                          root_parent="root-1", nested_parent="coordinator-1"):
        return [
            self._relation("root-1", ["coordinator-1"], status=root_status,
                           parent=root_parent),
            self._relation("coordinator-1", ["paper-1"], status=nested_status,
                           parent=nested_parent),
        ]

    def test_pass_target_with_completed_envelope(self):
        payload = self._run(self._nested_relations())
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS_TARGET")
        self.assertTrue(payload["routing_target_proved"])
        self.assertEqual(payload["downstream_status"], "completed")
        self.assertEqual(payload["max_anonymous_depth"], 2)
        self.assertEqual(payload["root_direct_spawn_child_ids"], ["coordinator-1"])
        self.assertEqual(
            payload["nested_formal_spawns"],
            [{"sender_thread_id": "coordinator-1", "receiver_thread_ids": ["paper-1"]}])

    def test_pass_target_survives_later_downstream_failure(self):
        payload = self._run(self._nested_relations(), envelope_ok=False)
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS_TARGET",
                         "a proven routing target must not be reversed by a "
                         "later downstream failure")
        self.assertEqual(payload["downstream_status"], "blocked_or_failed_out_of_scope")
        self.assertTrue(payload["routing_target_proved"])

    def test_formal_gate_never_depends_on_relation_status_or_child_completion(self):
        # adapter@9 freezes only tool/sender/receivers for a formal relation.
        # thread_relations[].status is the raw item.status projection with no
        # contract-frozen enum, so any value — including null and an absent
        # key — must gate identically, and the empty app-server event stream
        # proves no child completion is ever required.
        for status in ("started", "inProgress", "item/started", "item/completed",
                       "queued", None):
            with self.subTest(status=status):
                payload = self._run(self._nested_relations(nested_status=status))
                self.assertEqual(payload["status"], "pass", payload)
                self.assertEqual(payload["classification"], "PASS_TARGET")
                self.assertTrue(payload["routing_target_proved"])
        relations = self._nested_relations(nested_status=None)
        del relations[1]["status"]
        payload = self._run(relations)
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS_TARGET")

    def test_ownership_follows_sender_thread_id_only(self):
        # parent_thread_id claims root, but the formal owner is a shadow
        # thread: the child is not a root child, so the target is unproven.
        shadow = [
            self._relation("shadow-1", ["coordinator-1"], parent="root-1"),
            self._relation("coordinator-1", ["paper-1"], status="item/started"),
        ]
        payload = self._run(shadow)
        self.assertEqual(payload["status"], "blocked", payload)
        self.assertEqual(payload["classification"], "BLOCKED_OBSERVABILITY")
        self.assertEqual(payload["root_direct_spawn_child_ids"], [])

        # The reverse: sender_thread_id is root even when the app-server
        # attribution (parent_thread_id) points elsewhere.
        attributed = [
            self._relation("root-1", ["coordinator-1"], parent="unrelated-9"),
            self._relation("coordinator-1", ["paper-1"], parent="root-1"),
        ]
        payload = self._run(attributed)
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS_TARGET")

    def test_sender_owner_conflict_is_invalid_evidence(self):
        relations = [
            self._relation("root-1", ["coordinator-1"]),
            self._relation("other-root", ["coordinator-1"]),
            self._relation("coordinator-1", ["paper-1"]),
        ]
        payload = self._run(relations)
        self.assertEqual(payload["status"], "invalid", payload)
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")

    def test_unobservable_and_missing_formal_surface_block(self):
        # Real unobservable runs stay conservatively blocked: with no
        # supported formal relation anywhere (a wait-tool relation is not
        # one, nor is an empty relation list), or with formal edges that
        # trace only to a foreign sender, the checkpoint is NOT TESTED and
        # is never inferred as a zero-attempt producer FAIL.
        for relations in ([], [
            {"tool": "wait", "sender_thread_id": "root-1",
             "receiver_thread_ids": ["coordinator-1"]},
        ]):
            payload = self._run(relations)
            self.assertEqual(payload["status"], "blocked", payload)
            self.assertEqual(payload["classification"], "BLOCKED_OBSERVABILITY")

        no_root_child = self._run([
            self._relation("not-root", ["coordinator-1"]),
            self._relation("coordinator-1", ["paper-1"]),
        ])
        self.assertEqual(no_root_child["status"], "blocked", no_root_child)
        self.assertEqual(no_root_child["classification"], "BLOCKED_OBSERVABILITY")

    def test_unobservable_summary_with_formal_relations_is_invalid(self):
        # Deliberately impossible adapter output: adapter@9 derives the
        # summary from the relation graph, so unobservable can only mean no
        # supported formal relation exists.  Contradictory machine evidence
        # fails closed as INVALID_TEST_EXECUTION — it must never be
        # downgraded to a conservative BLOCKED_OBSERVABILITY.
        unobservable = self._run(
            self._nested_relations(),
            extra_adapter={"delegation": {"state": "unobservable", "basis": [],
                                          "child_thread_ids": []}})
        self.assertEqual(unobservable["status"], "invalid")
        self.assertEqual(unobservable["classification"], "INVALID_TEST_EXECUTION")

    def test_confirmed_summary_without_formal_relations_is_invalid(self):
        # The mirror image: the parser cannot emit confirmed without a
        # formal relation either, so a confirmed summary over an empty
        # relation list fails closed the same way, before any observability
        # verdict.
        payload = self._run([], extra_adapter={"delegation": {
            "state": "confirmed", "formal_child_count": 1,
            "child_thread_ids": ["coordinator-1"],
            "basis": ["formal_spawn_relation"], "reason_code": None}})
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")

    def test_summary_field_mismatches_are_invalid(self):
        # adapter@9 freezes all five summary fields as one mechanical
        # derivation of the relation graph, so a wrong child set, count,
        # basis entry, or reason code is as impossible as a wrong state
        # and fails closed the same way.  A superset basis in particular
        # must be rejected: the parser emits exactly
        # ["formal_spawn_relation"], never a membership-compatible list.
        base = _delegation_summary(self._nested_relations())
        self.assertEqual(base["state"], "confirmed")
        for field, wrong in (
            ("child_thread_ids", ["coordinator-1", "WRONG-CHILD"]),
            ("formal_child_count", 3),
            ("basis", ["formal_spawn_relation", "runtime_observation"]),
            ("reason_code", "unexpected_reason"),
        ):
            with self.subTest(field=field):
                payload = self._run(
                    self._nested_relations(),
                    extra_adapter={"delegation": dict(base, **{field: wrong})})
                self.assertEqual(payload["status"], "invalid", payload)
                self.assertEqual(payload["classification"],
                                 "INVALID_TEST_EXECUTION")

    def test_unobservable_summary_field_drift_is_invalid_not_blocked(self):
        # The full-field gate also guards the zeroed unobservable shape: a
        # drifted count, basis, or reason code over an empty relation graph
        # is impossible output and must fail closed instead of reaching the
        # conservative BLOCKED_OBSERVABILITY downgrade.
        for field, wrong in (("formal_child_count", 1),
                             ("basis", ["formal_spawn_relation"]),
                             ("reason_code", None)):
            with self.subTest(field=field):
                summary = {
                    "state": "unobservable", "formal_child_count": 0,
                    "child_thread_ids": [], "basis": [],
                    "reason_code": "no_supported_formal_spawn_relation",
                }
                summary[field] = wrong
                payload = self._run([], extra_adapter={"delegation": summary})
                self.assertEqual(payload["status"], "invalid", payload)
                self.assertEqual(payload["classification"],
                                 "INVALID_TEST_EXECUTION")

    def test_provider_failure_before_target_is_blocked_runtime(self):
        payload = self._run([], envelope_ok=False)
        self.assertEqual(payload["status"], "blocked", payload)
        self.assertEqual(payload["classification"], "BLOCKED_RUNTIME_PROVIDER")

    def test_adapter_status_matrix_matches_the_frozen_contract(self):
        # The prerequisite gate freezes the pinned adapter@9 status enum
        # verbatim and is graded against the same shared table as Stage 4:
        # harness and dependency blockers (e.g. a null codex_version) are
        # NOT TESTED even with a healthy nested topology, while only
        # corrupted adapter evidence and out-of-contract statuses —
        # including a missing fixture_status field — fail closed as
        # INVALID.
        cases = list(ADAPTER_STATUS_MATRIX)
        cases.append(("(missing)", "invalid", "INVALID_TEST_EXECUTION"))
        for fixture_status, expected_status, expected_classification in cases:
            with self.subTest(fixture_status=fixture_status):
                kwargs = ({"omit_fixture_status": True}
                          if fixture_status == "(missing)"
                          else {"fixture_status": fixture_status})
                payload = self._run(self._nested_relations(), **kwargs)
                self.assertEqual(payload["status"], expected_status, payload)
                self.assertEqual(payload["classification"],
                                 expected_classification)
                if expected_status == "blocked":
                    self.assertFalse(payload["routing_target_proved"])

    def test_identity_diagnostic_statuses_do_not_block_a_proven_target(self):
        # adapter@9 keeps named-role identity strictly diagnostic: an
        # unconfirmed or mismatched dispatch never downgrades a confirmed
        # delegation, so neither identity status may prerequisite-block a
        # run whose formal relation and envelope evidence stand on their
        # own.
        for fixture_status in NON_GATING_IDENTITY_STATUSES:
            with self.subTest(fixture_status=fixture_status):
                payload = self._run(self._nested_relations(),
                                    extra_adapter={"fixture_status": fixture_status})
                self.assertEqual(payload["status"], "pass", payload)
                self.assertEqual(payload["classification"], "PASS_TARGET")
                self.assertTrue(payload["routing_target_proved"])

    def test_adapter_prerequisite_requires_the_fixture_status_field(self):
        relations = self._nested_relations()
        adapter = {
            "delegation": _delegation_summary(relations),
            "dispatch": {"thread_relations": relations},
        }
        adapter_path = self.root / "adapter-no-status.json"
        adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
        response_path = self.root / "response-no-status.json"
        response_path.write_text(json.dumps({
            "passed": True,
            "output": {"exit_code": 0, "termination_reason": "completed",
                       "thread_id": "root-1", "app_server_events": []},
        }), encoding="utf-8")
        payload = verifier._checkpoint_stage2_routing(self.args(
            eval_response=response_path, adapter_output=adapter_path))
        self.assertEqual(payload["status"], "invalid", payload)
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")

    def test_malformed_relation_shape_is_invalid(self):
        # Deliberately impossible adapter output: the pinned parser fails
        # closed on a spawnAgent relation without its senderThreadId before
        # any normalized FIXTURE_READY payload exists, so the confirmed
        # summary below is hand-written (never helper-derived). This input
        # isolates the checkpoint's own relation-shape classification as
        # defense in depth.
        relations = [{
            "tool": "spawnAgent", "status": "completed",
            "parent_thread_id": "root-1", "receiver_thread_ids": ["coordinator-1"],
        }]
        adapter, response = self._write_evidence(
            relations,
            extra_adapter={"delegation": {
                "state": "confirmed", "formal_child_count": 1,
                "child_thread_ids": ["coordinator-1"],
                "basis": ["formal_spawn_relation"], "reason_code": None,
            }})
        payload = verifier._checkpoint_stage2_routing(self.args(
            eval_response=response, adapter_output=adapter))
        self.assertEqual(payload["status"], "invalid", payload)
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")

    def test_named_identity_fields_remain_non_gating(self):
        payload = self._run(
            self._nested_relations(),
            extra_adapter={
                "loaded_agents": ["professor-contact-downloader"],
                "requested_role": "mismatched-role",
                "identity": {"loaded_identity": "unobservable"},
            })
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS_TARGET")


class Stage4DynamicProjectionTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)

    def args(self, program_root, **overrides):
        values = {
            "program_root": program_root,
            "consumer_root": None,
            "eval_response": None,
            "adapter_output": None,
            "producer_sha": "",
            "output": None,
            "min_edges": 1,
            "required_depth": 1,
            "pre_snapshot": None,
            "post_snapshot": None,
        }
        values.update(overrides)
        return Namespace(**values)

    def _write_snapshot(self, program_root, path):
        payload = verifier._checkpoint_stage4_snapshot(self.args(program_root))
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _evidence(self, program_root, pending, *, child_id="child-sel",
                  sender="root-1", parent="root-1",
                  fixture_status="FIXTURE_READY",
                  delegation_override=None, child_texts=None,
                  omit_fixture_status=False):
        suffix = abs(hash(program_root)) % 9999
        adapter_path = self.root / f"adapter-{suffix}.json"
        relations = [{
            "tool": "spawnAgent", "status": "completed",
            "sender_thread_id": sender, "parent_thread_id": parent,
            "receiver_thread_ids": [child_id],
        }]
        delegation = (delegation_override
                      if delegation_override is not None
                      else _delegation_summary(relations))
        adapter = {
            "fixture_status": fixture_status,
            "delegation": delegation,
            "dispatch": {"thread_relations": relations},
        }
        if omit_fixture_status:
            del adapter["fixture_status"]
        adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
        business_text = json.dumps({"result": "needs_input",
                                    "pending_selection": pending},
                                   ensure_ascii=False)
        texts = [business_text] if child_texts is None else child_texts
        events = [{"message": {
            "method": "rawResponseItem/completed",
            "params": {
                "threadId": "root-1",
                "item": {"type": "message", "role": "developer", "content": []},
            },
        }}]
        for text in texts:
            events.append({"message": {
                "method": "rawResponseItem/completed",
                "params": {
                    "threadId": child_id,
                    "item": {"type": "message", "role": "assistant",
                             "content": [{"type": "output_text", "text": text}]},
                },
            }})
        response_path = self.root / f"response-{suffix}.json"
        response_path.write_text(json.dumps({
            "output": {"thread_id": "root-1", "app_server_events": events},
        }), encoding="utf-8")
        return adapter_path, response_path

    def _stage4_verdict(self, program_root, pending, *, pre, post, **kwargs):
        adapter_path, response_path = self._evidence(program_root, pending,
                                                     **kwargs)
        return verifier._checkpoint_stage4_needs_input(self.args(
            program_root,
            eval_response=response_path, adapter_output=adapter_path,
            pre_snapshot=pre, post_snapshot=post,
        ))

    def _run_stage4(self, program_root, pending, **kwargs):
        suffix = abs(hash(program_root)) % 9999
        pre = self.root / f"pre-{suffix}.json"
        post = self.root / f"post-{suffix}.json"
        self._write_snapshot(program_root, pre)
        self._write_snapshot(program_root, post)
        return self._stage4_verdict(program_root, pending, pre=pre, post=post,
                                    **kwargs)

    def test_dynamic_projection_reproduces_pc53_regression_and_issue57_sentinel(self):
        program53 = self.root / "program53"
        issue53_fixture.build_fixture(program53, self.root / "profile53",
                                      output=self.root / "setup53.json")
        expected53 = verifier._expected_pending_projection(program53)
        self.assertEqual(expected53, PC53_REGRESSION_EXPECTATION,
                         "the #53 fixed fixture must keep projecting the frozen "
                         "PC53 expectation unchanged")
        payload = self._run_stage4(program53, expected53)
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS")

        program57 = self.root / "program57"
        manifest57 = issue57_fixture.build_fixture(
            program57, self.root / "profile57", output=self.root / "setup57.json")
        expected57 = verifier._expected_pending_projection(program57)
        candidate_ids = [candidate["id"] for candidate in expected57[0]["candidates"]]
        self.assertEqual(expected57[0]["professor"], issue57_fixture.PROFESSOR)
        self.assertEqual(expected57[0]["direction_ids"], ["DIR57ROUTE"])
        self.assertEqual(candidate_ids, list(issue57_fixture.CANDIDATE_IDS))
        self.assertEqual(manifest57["candidate_ids"], list(issue57_fixture.CANDIDATE_IDS))
        payload = self._run_stage4(program57, expected57, child_id="child-57")
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS")

        # The projections are not interchangeable: feeding the #53 pending
        # payload against the #57 program is a product failure, proving the
        # verifier is dynamic rather than hard-coded.
        crossed = self._run_stage4(program57, expected53, child_id="child-cross")
        self.assertEqual(crossed["status"], "fail", crossed)
        self.assertEqual(crossed["classification"], "FAIL_PRODUCT")

    def test_cross_direction_group_is_projected_with_sorted_direction_ids(self):
        program = self.root / "program-cross"
        state_path = program / "教授研究/X分野/Cross Professor/套磁候选状态.json"
        base = {
            "id": "cross-1",
            "title": "Cross idea",
            "one_liner": "Combine both directions.",
            "research_question": "What emerges from combining both directions?",
            "fit": "high",
        }
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps({
            "schema": 2,
            "kind": "professor-contact-stage3-state",
            "directions": [{
                "direction_id": "DIRB",
                "candidates": [{
                    "id": "dir-b-1", "title": "B idea",
                    "one_liner": "B one liner.",
                    "research_question": "B question?",
                    "fit": "medium",
                }],
            }, {
                "direction_id": "DIRA",
                "candidates": [],
            }],
            "cross_direction_groups": [{
                "group_id": "cross:hash",
                "direction_ids": ["DIRB", "DIRA"],
                "candidates": [base],
            }],
        }, ensure_ascii=False), encoding="utf-8")
        expected = verifier._expected_pending_projection(program)
        self.assertEqual(len(expected), 2, expected)
        self.assertEqual(expected[0]["kind"], "direction")
        self.assertEqual(expected[0]["direction_ids"], ["DIRB"])
        self.assertEqual(expected[1]["kind"], "cross_direction")
        self.assertEqual(expected[1]["direction_ids"], ["DIRA", "DIRB"],
                         "cross groups must project sorted canonical direction_ids")
        payload = self._run_stage4(program, expected, child_id="child-cross2")
        self.assertEqual(payload["status"], "pass", payload)

        partial = self._run_stage4(program, [expected[0]], child_id="child-partial")
        self.assertEqual(partial["status"], "fail", partial)
        self.assertEqual(partial["classification"], "FAIL_PRODUCT")

    def test_stage4_ownership_follows_sender_thread_id_only(self):
        # adapter@9's formal ownership authority is sender_thread_id; the
        # same rule the Stage-2 checkpoint proves must hold for Stage-4
        # root-child discovery.
        program = self.root / "program-owner"
        issue57_fixture.build_fixture(program, self.root / "profile-owner",
                                      output=self.root / "setup-owner.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)

        # parent_thread_id claims the root, but the formal owner is a shadow
        # thread: the child is not a root child, so the run is conservatively
        # blocked (NOT TESTED), never judged against the unowned result.
        shadow = self._run_stage4(program, expected, child_id="child-shadow",
                                  sender="shadow-1", parent="root-1")
        self.assertEqual(shadow["status"], "blocked", shadow)
        self.assertEqual(shadow["classification"], "BLOCKED_OBSERVABILITY")
        self.assertIsNone(shadow["target_child_id"])

        # The reverse: sender_thread_id is the root even when the app-server
        # attribution points elsewhere; the Path-C result is consumed
        # normally.
        attributed = self._run_stage4(program, expected, child_id="child-attrib",
                                      sender="root-1", parent="unrelated-9")
        self.assertEqual(attributed["status"], "pass", attributed)
        self.assertEqual(attributed["classification"], "PASS")
        self.assertEqual(attributed["target_child_id"], "child-attrib")

    def test_no_formal_child_is_blocked_observability_not_fail(self):
        program = self.root / "program-blocked"
        issue57_fixture.build_fixture(program, self.root / "profile-blocked",
                                      output=self.root / "setup-blocked.json")
        expected = verifier._expected_pending_projection(program)
        pre = self.root / "pre-blocked.json"
        post = self.root / "post-blocked.json"
        self._write_snapshot(program, pre)
        self._write_snapshot(program, post)

        # The shape adapter@9 actually emits when no formal spawn relation
        # was observed: delegation=unobservable with the documented reason
        # code, never confirmed-with-empty-children.
        adapter_path = self.root / "adapter-nospawn.json"
        adapter_path.write_text(json.dumps({
            "fixture_status": "FIXTURE_READY",
            "delegation": {
                "state": "unobservable",
                "formal_child_count": 0,
                "child_thread_ids": [],
                "basis": [],
                "reason_code": "no_supported_formal_spawn_relation",
            },
            "dispatch": {"thread_relations": []},
        }), encoding="utf-8")
        response_path = self.root / "response-nospawn.json"
        response_path.write_text(json.dumps({
            "output": {"thread_id": "root-1", "app_server_events": []},
        }), encoding="utf-8")
        payload = verifier._checkpoint_stage4_needs_input(self.args(
            program,
            eval_response=response_path, adapter_output=adapter_path,
            pre_snapshot=pre, post_snapshot=post,
        ))
        self.assertEqual(payload["status"], "blocked", payload)
        self.assertEqual(payload["classification"], "BLOCKED_OBSERVABILITY",
                         "absence of a formal child alone must never be FAIL_PRODUCT")
        self.assertIsNotNone(expected)

        # A legal confirmed delegation whose sender is not the root also has
        # no root-direct child: still BLOCKED_OBSERVABILITY.
        foreign_relations = [{
            "tool": "spawnAgent", "status": "completed",
            "sender_thread_id": "other-root",
            "receiver_thread_ids": ["child-x"],
        }]
        adapter_path = self.root / "adapter-foreign-sender.json"
        adapter_path.write_text(json.dumps({
            "fixture_status": "FIXTURE_READY",
            "delegation": _delegation_summary(foreign_relations),
            "dispatch": {"thread_relations": foreign_relations},
        }), encoding="utf-8")
        response_path = self.root / "response-foreign-sender.json"
        response_path.write_text(json.dumps({
            "output": {"thread_id": "root-1", "app_server_events": []},
        }), encoding="utf-8")
        payload = verifier._checkpoint_stage4_needs_input(self.args(
            program,
            eval_response=response_path, adapter_output=adapter_path,
            pre_snapshot=pre, post_snapshot=post,
        ))
        self.assertEqual(payload["status"], "blocked", payload)
        self.assertEqual(payload["classification"], "BLOCKED_OBSERVABILITY")

    def test_summary_relation_contradictions_fail_closed(self):
        # adapter@9 derives the delegation summary from the relation graph,
        # so unobservable-with-formal-relations (and its mirror,
        # confirmed-without-any) is impossible output.  Both must fail
        # closed as INVALID_TEST_EXECUTION, never downgrade to the
        # conservative BLOCKED_OBSERVABILITY of a genuinely unobservable
        # run.
        program = self.root / "program-contradiction"
        issue57_fixture.build_fixture(program, self.root / "profile-contradiction",
                                      output=self.root / "setup-contradiction.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)
        pre = self.root / "pre-contradiction.json"
        post = self.root / "post-contradiction.json"
        self._write_snapshot(program, pre)
        self._write_snapshot(program, post)
        relations = [{
            "tool": "spawnAgent", "status": "completed",
            "sender_thread_id": "root-1", "parent_thread_id": "root-1",
            "receiver_thread_ids": ["child-contradiction"],
        }]
        response_path = self.root / "response-contradiction.json"
        response_path.write_text(json.dumps({
            "output": {"thread_id": "root-1", "app_server_events": []},
        }), encoding="utf-8")
        contradictory_adapters = [{
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "unobservable", "formal_child_count": 0,
                           "child_thread_ids": [], "basis": [],
                           "reason_code": "no_supported_formal_spawn_relation"},
            "dispatch": {"thread_relations": relations},
        }, {
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "confirmed", "formal_child_count": 1,
                           "child_thread_ids": ["child-contradiction"],
                           "basis": ["formal_spawn_relation"],
                           "reason_code": None},
            "dispatch": {"thread_relations": []},
        }]
        for index, adapter in enumerate(contradictory_adapters):
            adapter_path = self.root / f"adapter-contradiction-{index}.json"
            adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
            payload = verifier._checkpoint_stage4_needs_input(self.args(
                program,
                eval_response=response_path, adapter_output=adapter_path,
                pre_snapshot=pre, post_snapshot=post))
            self.assertEqual(payload["status"], "invalid", payload)
            self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")

    def test_summary_field_mismatches_are_invalid(self):
        # Same full-field gate as Stage 2, on the Stage-4 checkpoint: any
        # frozen summary field that disagrees with the mechanical
        # derivation of the adapter's own relation graph — child set,
        # count, basis, or reason code — fails closed before the
        # observability verdict.  A superset basis in particular must be
        # rejected: the parser emits exactly ["formal_spawn_relation"].
        program = self.root / "program-field-drift"
        issue57_fixture.build_fixture(program, self.root / "profile-field-drift",
                                      output=self.root / "setup-field-drift.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)
        base = {
            "state": "confirmed", "formal_child_count": 1,
            "child_thread_ids": ["child-drift"],
            "basis": ["formal_spawn_relation"], "reason_code": None,
        }
        for field, wrong in (
            ("child_thread_ids", ["WRONG-CHILD"]),
            ("formal_child_count", 2),
            ("basis", ["formal_spawn_relation", "runtime_observation"]),
            ("reason_code", "unexpected_reason"),
        ):
            with self.subTest(field=field):
                payload = self._run_stage4(
                    program, expected, child_id="child-drift",
                    delegation_override=dict(base, **{field: wrong}))
                self.assertEqual(payload["status"], "invalid", payload)
                self.assertEqual(payload["classification"],
                                 "INVALID_TEST_EXECUTION")

    def test_snapshot_evidence_is_classified_by_attribution(self):
        # Frozen #57 verdict table: only a write positively attributed to
        # this run is a product failure.  A preexisting Stage-4 output is
        # precondition pollution (INVALID), a post snapshot that drifted
        # from the current artifacts is stale or tampered evidence
        # (INVALID), and only consistent evidence showing the output
        # after a clean pre state proves the omitted-selection path wrote
        # it (FAIL_PRODUCT).
        program = self.root / "program-preexisting"
        issue57_fixture.build_fixture(program, self.root / "profile-preexisting",
                                      output=self.root / "setup-preexisting.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)
        output_path = program / "教授研究/套磁选择.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        payload = self._run_stage4(program, expected, child_id="child-pre")
        self.assertEqual(payload["status"], "invalid", payload)
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION",
                         "a preexisting output can never be attributed to "
                         "this run")

        program = self.root / "program-drift"
        issue57_fixture.build_fixture(program, self.root / "profile-drift",
                                      output=self.root / "setup-drift.json")
        expected = verifier._expected_pending_projection(program)
        pre = self.root / "pre-drift.json"
        post = self.root / "post-drift.json"
        self._write_snapshot(program, pre)
        output_path = program / "教授研究/套磁选择.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        self._write_snapshot(program, post)
        output_path.unlink()
        payload = self._stage4_verdict(program, expected, pre=pre, post=post)
        self.assertEqual(payload["status"], "invalid", payload)
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION",
                         "a post snapshot that disagrees with the current "
                         "artifacts is stale or tampered evidence")

        output_path.write_text("{}", encoding="utf-8")
        self._write_snapshot(program, post)
        payload = self._stage4_verdict(program, expected, pre=pre, post=post)
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["classification"], "FAIL_PRODUCT",
                         "consistent evidence of a Stage-4 output after a "
                         "clean pre state is this run's write")

    def test_every_business_message_is_load_bearing(self):
        # The frozen verdict counts business JSONs, not children, and
        # never lets a later message mask an earlier one: a duplicate
        # Path-C result, a wrong-result object, or a non-JSON assistant
        # message is already a violation even when a valid Path-C result
        # follows it.
        program = self.root / "program-multi"
        issue57_fixture.build_fixture(program, self.root / "profile-multi",
                                      output=self.root / "setup-multi.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)
        business = json.dumps({"result": "needs_input",
                               "pending_selection": expected}, ensure_ascii=False)
        cases = {
            "duplicate path-c results": [business, business],
            "wrong result then path-c": [
                json.dumps({"result": "selected",
                            "pending_selection": expected}, ensure_ascii=False),
                business,
            ],
            "non-json then path-c": ["阶段说明：正在汇总候选。", business],
        }
        for label, texts in cases.items():
            with self.subTest(case=label):
                payload = self._run_stage4(program, expected,
                                           child_id="child-multi",
                                           child_texts=texts)
                self.assertEqual(payload["status"], "fail", payload)
                self.assertEqual(payload["classification"], "FAIL_PRODUCT")

    def test_cross_child_wrong_and_duplicate_results_fail(self):
        # The exactly-one rule spans all direct root children: an
        # observable wrong-result object on another child is a violation
        # in its own right, and two children each emitting a Path-C
        # result is a duplicate — neither may be collapsed into the
        # surviving result.
        program = self.root / "program-cross-children"
        issue57_fixture.build_fixture(program, self.root / "profile-cross-children",
                                      output=self.root / "setup-cross-children.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)
        suffix = abs(hash(program)) % 9999
        pre = self.root / f"pre-{suffix}.json"
        post = self.root / f"post-{suffix}.json"
        self._write_snapshot(program, pre)
        self._write_snapshot(program, post)
        relations = [{
            "tool": "spawnAgent", "status": "completed",
            "sender_thread_id": "root-1", "parent_thread_id": "root-1",
            "receiver_thread_ids": ["child-a", "child-b"],
        }]

        def message(child, text):
            return {"message": {
                "method": "rawResponseItem/completed",
                "params": {"threadId": child, "item": {
                    "type": "message", "role": "assistant",
                    "content": [{"type": "output_text", "text": text}]}}}}

        business = json.dumps({"result": "needs_input",
                               "pending_selection": expected}, ensure_ascii=False)
        cases = {
            "wrong result on other child": [
                message("child-a", json.dumps({"result": "selected"},
                                              ensure_ascii=False)),
                message("child-b", business),
            ],
            "duplicate across children": [
                message("child-a", business),
                message("child-b", business),
            ],
        }
        for label, child_events in cases.items():
            with self.subTest(case=label):
                adapter_path = self.root / f"adapter-cross-{suffix}.json"
                adapter_path.write_text(json.dumps({
                    "fixture_status": "FIXTURE_READY",
                    "delegation": _delegation_summary(relations),
                    "dispatch": {"thread_relations": relations},
                }), encoding="utf-8")
                response_path = self.root / f"response-cross-{suffix}.json"
                response_path.write_text(json.dumps({
                    "output": {"thread_id": "root-1",
                               "app_server_events": child_events},
                }), encoding="utf-8")
                payload = verifier._checkpoint_stage4_needs_input(self.args(
                    program,
                    eval_response=response_path, adapter_output=adapter_path,
                    pre_snapshot=pre, post_snapshot=post))
                self.assertEqual(payload["status"], "fail", payload)
                self.assertEqual(payload["classification"], "FAIL_PRODUCT")

    def test_stage4_adapter_status_matrix_matches_the_frozen_contract(self):
        # The same shared fixture-status table as Stage 2, graded on the
        # Stage-4 checkpoint: harness and dependency blockers are NOT
        # TESTED, while only corrupted adapter evidence and
        # out-of-contract statuses — including a missing fixture_status
        # field — fail closed as INVALID.
        program = self.root / "program-matrix"
        issue57_fixture.build_fixture(program, self.root / "profile-matrix",
                                      output=self.root / "setup-matrix.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)
        cases = list(ADAPTER_STATUS_MATRIX)
        cases.append(("(missing)", "invalid", "INVALID_TEST_EXECUTION"))
        for fixture_status, expected_status, expected_classification in cases:
            with self.subTest(fixture_status=fixture_status):
                kwargs = ({"omit_fixture_status": True}
                          if fixture_status == "(missing)"
                          else {"fixture_status": fixture_status})
                payload = self._run_stage4(
                    program, expected, child_id="child-matrix", **kwargs)
                self.assertEqual(payload["status"], expected_status, payload)
                self.assertEqual(payload["classification"],
                                 expected_classification)

    def test_stage4_identity_diagnostic_statuses_do_not_block_path_c(self):
        # adapter@9 keeps named-role identity strictly diagnostic, so an
        # unconfirmed or mismatched dispatch never prerequisite-blocks a
        # run whose formal delegation and business evidence stand on
        # their own.
        program = self.root / "program-identity"
        issue57_fixture.build_fixture(program, self.root / "profile-identity",
                                      output=self.root / "setup-identity.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)
        for fixture_status in NON_GATING_IDENTITY_STATUSES:
            with self.subTest(fixture_status=fixture_status):
                payload = self._run_stage4(program, expected,
                                           child_id="child-identity",
                                           fixture_status=fixture_status)
                self.assertEqual(payload["status"], "pass", payload)
                self.assertEqual(payload["classification"], "PASS")

    def test_stage4_prerequisite_outranks_product_write_attribution(self):
        # Verdict precedence on one fixed feature surface: a clean pre
        # snapshot, a post snapshot consistent with the current
        # artifacts, and a Stage-4 output written this run.  Only the
        # fixture_status varies.  A harness/provider blocker or corrupted
        # adapter evidence is decided before feature attribution — under
        # HARNESS_CONTAMINATION the evidence sources are outside the
        # allowed roots, so the filesystem write can no longer be trusted
        # as a producer FAIL — while the identity diagnostics stay
        # non-gating and a ready fixture still fails the producer.
        program = self.root / "program-precedence"
        issue57_fixture.build_fixture(program, self.root / "profile-precedence",
                                      output=self.root / "setup-precedence.json")
        expected = verifier._expected_pending_projection(program)
        self.assertIsNotNone(expected)
        suffix = abs(hash(program)) % 9999
        pre = self.root / f"pre-{suffix}.json"
        post = self.root / f"post-{suffix}.json"
        self._write_snapshot(program, pre)
        output_path = program / "教授研究/套磁选择.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        self._write_snapshot(program, post)
        cases = {
            "FIXTURE_READY": ("fail", "FAIL_PRODUCT"),
            "HARNESS_ERROR": ("blocked", "BLOCKED_RUNTIME_PROVIDER"),
            "HARNESS_CONTAMINATION": ("blocked", "BLOCKED_RUNTIME_PROVIDER"),
            "NOT_RUN": ("blocked", "BLOCKED_RUNTIME_PROVIDER"),
            "BLOCKED_DEPENDENCY": ("blocked", "BLOCKED_RUNTIME_PROVIDER"),
            "INVALID_EVIDENCE": ("invalid", "INVALID_TEST_EXECUTION"),
            "HARNESS_DISPATCH_UNCONFIRMED": ("fail", "FAIL_PRODUCT"),
            "HARNESS_DISPATCH_MISMATCH": ("fail", "FAIL_PRODUCT"),
        }
        for fixture_status, (status, classification) in cases.items():
            with self.subTest(fixture_status=fixture_status):
                payload = self._stage4_verdict(program, expected, pre=pre,
                                               post=post,
                                               child_id="child-precedence",
                                               fixture_status=fixture_status)
                self.assertEqual(payload["status"], status, payload)
                self.assertEqual(payload["classification"], classification,
                                 payload)

    def test_malformed_or_missing_candidate_state_is_invalid(self):
        program = self.root / "program-bad"
        program.mkdir()
        payload = verifier._expected_pending_projection(program)
        self.assertIsNone(payload)

        state_path = program / "教授研究/X分野/Bad Professor/套磁候选状态.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(verifier._expected_pending_projection(program))


if __name__ == "__main__":
    unittest.main()
