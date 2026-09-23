import importlib.util
import json
import shlex
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture = load_module(
    "issue53_fixture_for_tests",
    RUNTIME_DIR / "prepare_issue53_stage4_fixture.py",
)
request_builder = load_module(
    "issue53_request_for_tests",
    RUNTIME_DIR / "build_issue53_eval_request.py",
)
verifier = load_module(
    "issue53_verifier_for_tests",
    RUNTIME_DIR / "verify_issue32_e2e.py",
)


class Issue53Stage4RuntimeAssetTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.program = self.root / "program"
        self.profile = self.root / "profile"
        self.output = self.root / "output"
        self.output.mkdir()
        fixture.build_fixture(
            self.program, self.profile, output=self.output / "setup.json"
        )

    def test_fixture_is_independent_and_contains_the_fixed_candidate_sentinel(self):
        fixture_program = self.root / "builder-program"
        fixture_profile = self.root / "builder-profile"
        manifest = fixture.build_fixture(
            fixture_program, fixture_profile, output=self.output / "builder-setup.json"
        )
        self.assertEqual(manifest["fixture_kind"], "stage4-only")
        state_path = fixture_program / "教授研究/X分野/Example Professor/套磁候选状态.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        profile_path = fixture_profile / "套磁邮件/套磁信息.md"
        self.assertEqual(state["profile_path"], str(profile_path.resolve()))
        self.assertTrue(Path(state["profile_path"]).is_file())
        self.assertEqual(state["directions"][0]["candidates"][0]["id"], "idea-001")
        self.assertFalse((fixture_program / "教授研究/套磁选择.json").exists())
        self.assertFalse((fixture_program / "教授研究/邮件输入.json").exists())
        self.assertTrue((self.output / "builder-setup.json").is_file())
        self.assertEqual(manifest["input_hashes"]["info.json"], fixture.sha256(fixture_program / "info.json"))

    def test_fixture_refuses_foreign_nonempty_directories(self):
        foreign = self.root / "foreign"
        foreign.mkdir()
        (foreign / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(fixture.FixtureBuildError):
            fixture.build_fixture(foreign, self.profile, output=self.output / "setup.json")

    def test_fixture_refuses_paths_inside_the_producer_checkout(self):
        with self.assertRaises(fixture.FixtureBuildError):
            fixture.build_fixture(
                fixture._producer_root() / ".issue53-fixture-forbidden",
                self.profile,
                output=self.output / "setup.json",
            )

    def test_request_builder_emits_only_the_pc53_command_surface(self):
        consumer = self.root / "consumer"
        consumer.mkdir()
        prompt = self.root / "prompt.txt"
        prompt.write_text("fixed prompt", encoding="utf-8")
        request = request_builder.build_request(
            consumer_root=consumer,
            prompt_file=prompt,
            output=self.output / "request.json",
        )
        argv = shlex.split(request["command"])
        self.assertEqual(
            argv[:8],
            [
                "--json", "--ephemeral", "--skip-git-repo-check",
                "--sandbox", "workspace-write", "--cd",
                str(consumer.resolve()), "--model",
            ],
        )
        self.assertIn("gpt-5.6-luna", argv)
        self.assertIn('--config', argv)
        self.assertIn(
            f'projects."{consumer.resolve()}".trust_level="trusted"',
            argv,
        )
        self.assertEqual(argv[-1], "fixed prompt")
        for forbidden in ("network_access", "ZOTERO", "CHROME", "NPM", "agents.max_concurrent"):
            self.assertNotIn(forbidden, request["command"])

    def _args(self, **overrides):
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

    def _write_snapshot(self, path):
        payload = verifier._checkpoint_stage4_snapshot(self._args(output=path))
        path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def _write_evidence(self, result, *, child_ids=("child-1",), status="completed"):
        adapter_path = self.root / f"adapter-{len(list(self.root.glob('adapter-*.json')))}.json"
        adapter_path.write_text(json.dumps({
            "fixture_status": "FIXTURE_READY",
            "delegation": {
                "state": "confirmed",
                "formal_child_count": len(set(child_ids)),
                "child_thread_ids": sorted(set(child_ids)),
                "basis": ["formal_spawn_relation"],
                "reason_code": None,
            },
            "dispatch": {"thread_relations": [{
                "tool": "spawnAgent",
                "status": status,
                "sender_thread_id": "root-1",
                "parent_thread_id": "root-1",
                "receiver_thread_ids": list(child_ids),
            }]},
        }), encoding="utf-8")
        contents = [{
            "type": "output_text",
            "text": json.dumps(result, ensure_ascii=False),
        }]
        events = [{"message": {
            "method": "rawResponseItem/completed",
            "params": {
                "threadId": child_ids[0],
                "item": {"type": "message", "role": "developer", "content": []},
            },
        }}]
        for child_id in child_ids:
            # A non-assistant child item: outside the pinned business
            # surface, so it must never be parsed as a business result.
            events.append({"message": {
                "method": "rawResponseItem/completed",
                "params": {
                    "threadId": child_id,
                    "item": {
                        "type": "message",
                        "role": "developer",
                        "content": [{"type": "output_text", "text": "progress note"}],
                    },
                },
            }})
            events.append({"message": {
                "method": "rawResponseItem/completed",
                "params": {
                    "threadId": child_id,
                    "item": {"type": "message", "role": "assistant", "content": contents},
                },
            }})
        response_path = self.root / "response.json"
        response_path.write_text(json.dumps({
            "output": {"thread_id": "root-1", "app_server_events": events},
        }), encoding="utf-8")
        return adapter_path, response_path

    def _pending(self):
        return [{
            "professor": "Example Professor",
            "kind": "direction",
            "direction_ids": ["DIR00001"],
            "direction_label": "適応信号処理（自适应信号处理）",
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

    def _run_verifier(self, result, **kwargs):
        # setUp already builds the #53 fixture, so the dynamically derived
        # expectation always has canonical state to read -- and any in-test
        # state mutation (dynamic-projection test) must survive until the
        # checkpoint runs.
        adapter_path, response_path = self._write_evidence(result, **kwargs)
        pre = self.root / "pre.json"
        post = self.root / "post.json"
        self._write_snapshot(pre)
        self._write_snapshot(post)
        return verifier._checkpoint_stage4_needs_input(self._args(
            eval_response=response_path,
            adapter_output=adapter_path,
            pre_snapshot=pre,
            post_snapshot=post,
        ))

    def test_verifier_passes_only_child_attributed_exact_path_c_result(self):
        self.assertEqual(
            verifier._expected_pending_projection(self.program),
            verifier._pending_selection_projection(self._pending()),
        )
        payload = self._run_verifier({"result": "needs_input", "pending_selection": self._pending()})
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS")
        self.assertEqual(payload["target_child_id"], "child-1")

    def test_verifier_uses_dynamic_current_candidate_state_not_pc53_fixture(self):
        state_path = self.program / "教授研究/X分野/Example Professor/套磁候选状态.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["directions"][0]["candidates"] = [{
            "id": "dynamic-007",
            "direction_ids": ["DIR00001"],
            "title": "Dynamic extension",
            "one_liner": "A candidate generated by this current run.",
            "research_question": "What changes under the current state?",
            "fit": "low",
        }]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        pending = [{
            "professor": "Example Professor",
            "kind": "direction",
            "direction_ids": ["DIR00001"],
            "candidates": [{
                "id": "dynamic-007",
                "title": "Dynamic extension",
                "one_liner": "A candidate generated by this current run.",
                "research_question": "What changes under the current state?",
                "fit": "low",
            }],
        }]

        payload = self._run_verifier({"result": "needs_input", "pending_selection": pending})
        self.assertEqual(payload["status"], "pass", payload)
        names = {row["name"]: row["status"] for row in payload["checks"]}
        self.assertEqual(names["pending_selection_matches_current_state"], "pass", names)

        stale = self._run_verifier({
            "result": "needs_input", "pending_selection": self._pending(),
        })
        self.assertEqual(stale["status"], "fail", stale)
        names = {row["name"]: row["status"] for row in stale["checks"]}
        self.assertEqual(names["pending_selection_matches_current_state"], "fail", names)

    def test_verifier_accepts_adapter9_in_progress_spawn_relation(self):
        payload = self._run_verifier(
            {"result": "needs_input", "pending_selection": self._pending()},
            status="inProgress",
        )
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS")
        self.assertEqual(payload["target_child_id"], "child-1")

    def test_verifier_classifies_product_and_observability_outcomes(self):
        wrong = self._run_verifier({"result": "ok", "pending_selection": self._pending()})
        self.assertEqual(wrong["classification"], "FAIL_PRODUCT", wrong)

        adapter_path = self.root / "unobservable.json"
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
        response_path = self.root / "unobservable-response.json"
        response_path.write_text(json.dumps({
            "output": {"thread_id": "root-1", "app_server_events": []},
        }), encoding="utf-8")
        pre = self.root / "unobservable-pre.json"
        post = self.root / "unobservable-post.json"
        self._write_snapshot(pre)
        self._write_snapshot(post)
        blocked = verifier._checkpoint_stage4_needs_input(self._args(
            eval_response=response_path, adapter_output=adapter_path,
            pre_snapshot=pre, post_snapshot=post,
        ))
        self.assertEqual(blocked["status"], "blocked", blocked)
        self.assertEqual(blocked["classification"], "BLOCKED_OBSERVABILITY")

        malformed = self.root / "malformed.json"
        malformed.write_text("{}", encoding="utf-8")
        invalid = verifier._checkpoint_stage4_needs_input(self._args(
            eval_response=response_path, adapter_output=malformed,
            pre_snapshot=pre, post_snapshot=post,
        ))
        self.assertEqual(invalid["status"], "invalid", invalid)
        self.assertEqual(invalid["classification"], "INVALID_TEST_EXECUTION")


if __name__ == "__main__":
    unittest.main()
