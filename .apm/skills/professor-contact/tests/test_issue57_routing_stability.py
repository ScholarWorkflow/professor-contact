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
ANALYZER_PATH = REPO_ROOT / ".apm" / "agents" / "professor-contact-analyzer.agent.md"
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


class Stage2CodexSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ANALYZER_PATH.exists():
            raise AssertionError(f"missing analyzer document: {ANALYZER_PATH}")
        cls.analyzer = ANALYZER_PATH.read_text(encoding="utf-8")
        cls.codex = _codex_branch(cls.analyzer)

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
        opencode = self.analyzer[
            self.analyzer.index("### OpenCode 分支"):self.analyzer.index("### Codex 分支")]
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

    def _write_evidence(self, relations, *, envelope_ok=True, extra_adapter=None):
        adapter = {
            "delegation": {
                "state": "confirmed",
                "basis": ["formal_spawn_relation"],
                "child_thread_ids": ["coordinator-1"],
            },
            "dispatch": {"thread_relations": relations},
        }
        if extra_adapter:
            adapter.update(extra_adapter)
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

    def test_attempt_gate_accepts_started_relations_without_completion(self):
        for status in ("started", "inProgress", "item/started", "item/completed"):
            with self.subTest(status=status):
                payload = self._run(self._nested_relations(nested_status=status))
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
        unobservable = self._run(
            self._nested_relations(),
            extra_adapter={"delegation": {"state": "unobservable", "basis": [],
                                          "child_thread_ids": []}})
        self.assertEqual(unobservable["status"], "blocked")
        self.assertEqual(unobservable["classification"], "BLOCKED_OBSERVABILITY")

        no_spawn = self._run([
            {"tool": "wait", "sender_thread_id": "root-1",
             "receiver_thread_ids": ["coordinator-1"]},
        ])
        self.assertEqual(no_spawn["status"], "blocked")
        self.assertEqual(no_spawn["classification"], "BLOCKED_OBSERVABILITY")

        no_root_child = self._run([
            self._relation("not-root", ["coordinator-1"]),
            self._relation("coordinator-1", ["paper-1"]),
        ])
        self.assertEqual(no_root_child["classification"], "BLOCKED_OBSERVABILITY")

    def test_provider_failure_before_target_is_blocked_runtime(self):
        payload = self._run([], envelope_ok=False)
        self.assertEqual(payload["status"], "blocked", payload)
        self.assertEqual(payload["classification"], "BLOCKED_RUNTIME_PROVIDER")

    def test_malformed_relation_shape_is_invalid(self):
        payload = self._run([
            {"tool": "spawnAgent", "status": "completed",
             "parent_thread_id": "root-1", "receiver_thread_ids": ["coordinator-1"]},
        ])
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

    def _run_stage4(self, program_root, pending, *, child_id="child-sel"):
        adapter_path = self.root / f"adapter-{abs(hash(program_root)) % 9999}.json"
        adapter_path.write_text(json.dumps({
            "delegation": {
                "state": "confirmed",
                "basis": ["formal_spawn_relation"],
                "child_thread_ids": [child_id],
            },
            "dispatch": {"thread_relations": [{
                "tool": "spawnAgent", "status": "completed",
                "sender_thread_id": "root-1", "parent_thread_id": "root-1",
                "receiver_thread_ids": [child_id],
            }]},
        }), encoding="utf-8")
        contents = [{
            "type": "output_text",
            "text": json.dumps({"result": "needs_input",
                                "pending_selection": pending}, ensure_ascii=False),
        }]
        events = [{"message": {
            "method": "rawResponseItem/completed",
            "params": {
                "threadId": "root-1",
                "item": {"type": "message", "role": "developer", "content": []},
            },
        }}, {"message": {
            "method": "rawResponseItem/completed",
            "params": {
                "threadId": child_id,
                "item": {"type": "message", "role": "assistant", "content": contents},
            },
        }}]
        response_path = self.root / f"response-{abs(hash(program_root)) % 9999}.json"
        response_path.write_text(json.dumps({
            "output": {"thread_id": "root-1", "app_server_events": events},
        }), encoding="utf-8")
        pre = self.root / f"pre-{abs(hash(program_root)) % 9999}.json"
        post = self.root / f"post-{abs(hash(program_root)) % 9999}.json"
        self._write_snapshot(program_root, pre)
        self._write_snapshot(program_root, post)
        return verifier._checkpoint_stage4_needs_input(self.args(
            program_root,
            eval_response=response_path, adapter_output=adapter_path,
            pre_snapshot=pre, post_snapshot=post,
        ))

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

    def test_no_formal_child_is_blocked_observability_not_fail(self):
        program = self.root / "program-blocked"
        issue57_fixture.build_fixture(program, self.root / "profile-blocked",
                                      output=self.root / "setup-blocked.json")
        expected = verifier._expected_pending_projection(program)
        adapter_path = self.root / "adapter-nospawn.json"
        adapter_path.write_text(json.dumps({
            "delegation": {
                "state": "confirmed",
                "basis": ["formal_spawn_relation"],
                "child_thread_ids": [],
            },
            "dispatch": {"thread_relations": []},
        }), encoding="utf-8")
        response_path = self.root / "response-nospawn.json"
        response_path.write_text(json.dumps({
            "output": {"thread_id": "root-1", "app_server_events": []},
        }), encoding="utf-8")
        pre = self.root / "pre-blocked.json"
        post = self.root / "post-blocked.json"
        self._write_snapshot(program, pre)
        self._write_snapshot(program, post)
        payload = verifier._checkpoint_stage4_needs_input(self.args(
            program,
            eval_response=response_path, adapter_output=adapter_path,
            pre_snapshot=pre, post_snapshot=post,
        ))
        self.assertEqual(payload["status"], "blocked", payload)
        self.assertEqual(payload["classification"], "BLOCKED_OBSERVABILITY",
                         "absence of a formal child alone must never be FAIL_PRODUCT")
        self.assertIsNotNone(expected)

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
