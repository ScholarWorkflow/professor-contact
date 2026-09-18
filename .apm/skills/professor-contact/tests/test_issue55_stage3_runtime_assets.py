"""Deterministic assets and verifier coverage for issue #55 PC55-R1."""

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
    "issue55_fixture_for_tests",
    RUNTIME_DIR / "prepare_issue55_stage3_fixture.py",
)
request_builder = load_module(
    "issue55_request_for_tests",
    RUNTIME_DIR / "build_issue55_eval_request.py",
)
verifier = load_module(
    "issue55_verifier_for_tests",
    RUNTIME_DIR / "verify_issue32_e2e.py",
)


class Issue55Stage3RuntimeAssetTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.program = self.root / "program"
        self.consumer = self.root / "consumer"
        self.consumer.mkdir()
        self.output = self.root / "output"
        self.output.mkdir()
        fixture.build_fixture(self.program, output=self.output / "runtime-setup.json")

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

    def test_fixture_is_canonical_and_has_no_stage3_or_stage4_outputs(self):
        manifest = json.loads(
            (self.output / "runtime-setup.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["fixture_kind"], "issue55-stage3-pre")
        self.assertEqual(manifest["direction_id"], "DIR00001")
        self.assertEqual(manifest["item_key"], "PAPER0001")
        self.assertEqual(manifest["gap_id"], "GAP0001")
        self.assertEqual(manifest["manual_patch"], "no")
        self.assertFalse(manifest["network_used"])
        self.assertFalse(manifest["runtime_fixture_started"])
        self.assertTrue(
            Path(manifest["program_root"]).resolve().is_relative_to(self.program.resolve())
        )
        input_path = self.program / "教授研究/X分野/Example Professor/套磁候选输入.json"
        pack = json.loads(input_path.read_text(encoding="utf-8"))
        self.assertEqual(pack["schema"], 2)
        self.assertEqual(pack["kind"], "professor-contact-stage2-input")
        self.assertEqual(pack["directions"][0]["direction_id"], "DIR00001")
        self.assertEqual(pack["directions"][0]["gap_shortlist"][0]["gap_id"], "GAP0001")
        profile = self.program / "套磁邮件/套磁信息.md"
        self.assertEqual(
            profile.read_text(encoding="utf-8"),
            "# Synthetic applicant profile\n\n"
            "研究兴趣：适应信号处理、分布变化下的稳健性。\n"
            "经验：使用 Python 进行信号处理实验与可复现分析。\n"
            "希望探索：在变化环境中如何保持在线模型的稳定适应。\n",
        )
        for relative in manifest["forbidden_outputs"]:
            self.assertFalse((self.program / relative).exists(), relative)
        self.assertEqual(
            manifest["input_hashes"]["info.json"],
            fixture.sha256(self.program / "info.json"),
        )

    def test_fixture_refuses_nonempty_and_producer_owned_roots(self):
        foreign = self.root / "foreign"
        foreign.mkdir()
        (foreign / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(fixture.FixtureBuildError):
            fixture.build_fixture(foreign, output=self.output / "foreign.json")
        with self.assertRaises(fixture.FixtureBuildError):
            fixture.build_fixture(
                fixture._producer_root() / ".issue55-fixture-forbidden",
                output=self.output / "producer.json",
            )

    def test_request_builder_freezes_prompt_and_command_surface(self):
        template = RUNTIME_DIR / "prompts/issue55-stage3-routing.txt"
        rendered = self.output / "pc55-stage3-prompt.txt"
        request_path = self.output / "pc55-stage3-request.json"
        request = request_builder.build_request(
            consumer_root=self.consumer,
            program_root=self.program,
            prompt_template=template,
            rendered_prompt=rendered,
            output=request_path,
        )
        argv = shlex.split(request["command"])
        self.assertEqual(argv[:7], [
            "--json", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "workspace-write", "--cd", str(self.consumer.resolve()),
        ])
        self.assertEqual(argv[7:10], ["--model", "gpt-5.6-luna", "--config"])
        self.assertIn('model_reasoning_effort="low"', argv)
        self.assertIn(
            f'projects."{self.consumer.resolve()}".trust_level="trusted"', argv,
        )
        self.assertEqual(argv[-1], rendered.read_text(encoding="utf-8"))
        for forbidden in (
            "agents.max_concurrent_threads_per_session", "network_access",
            "spawnAgent", "professor-contact-idea-generator", "discovery",
            "ZOTERO", "CHROME",
        ):
            self.assertNotIn(forbidden, request["command"])
            self.assertNotIn(forbidden, rendered.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(request_path.read_text(encoding="utf-8")), request)

        drifted = self.output / "drifted-prompt.txt"
        drifted.write_text(template.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        with self.assertRaises(request_builder.RequestBuildError):
            request_builder.build_request(
                consumer_root=self.consumer, program_root=self.program,
                prompt_template=drifted, rendered_prompt=rendered,
                output=request_path,
            )

    def _write_snapshot(self, path):
        payload = verifier._checkpoint_stage3_snapshot(self.args())
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def _write_state(self, *, validation="pass"):
        candidates = [
            {"id": f"idea-{index}", "direction_ids": ["DIR00001"]}
            for index in range(1, 4)
        ]
        state = {
            "schema": 2,
            "kind": "professor-contact-stage3-state",
            "identity_version": "direction-id-v1",
            "generator_contract_version": "stage3-ideas-v2",
            "directions": [{"direction_id": "DIR00001", "candidates": candidates}],
            "candidates": candidates,
            "validator": {"results": {"DIR00001": {
                "result": validation,
                "rounds": 2 if validation == "fail_after_2_rounds" else 1,
                "issues": [] if validation == "pass" else ["candidate issue"],
            }}},
        }
        path = self.program / "教授研究/X分野/Example Professor/套磁候选状态.json"
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    def _write_evidence(self, *, direct_children=("child-generator", "child-validator"),
                        delegation_state="confirmed", sender_field=True):
        relations = [
            {"tool": "spawnAgent", "sender_thread_id": "root-thread",
             "receiver_thread_ids": list(direct_children)},
            {"tool": "spawnAgent", "sender_thread_id": direct_children[0],
             "receiver_thread_ids": ["nested-child"]},
            {"tool": "wait", "sender_thread_id": "root-thread",
             "receiver_thread_ids": list(direct_children)},
            {"tool": "sendInput", "sender_thread_id": "root-thread",
             "receiver_thread_ids": [direct_children[0]]},
        ]
        if not sender_field:
            relations[0].pop("sender_thread_id")
        adapter_path = self.output / "adapter.json"
        adapter_path.write_text(json.dumps({
            "delegation": {
                "state": delegation_state,
                "basis": ["formal_spawn_relation"] if delegation_state == "confirmed" else [],
                "child_thread_ids": list(direct_children),
            },
            "dispatch": {"thread_relations": relations},
        }), encoding="utf-8")
        response_path = self.output / "response.json"
        response_path.write_text(json.dumps({
            "passed": True,
            "output": {
                "exit_code": 0,
                "termination_reason": "completed",
                "thread_id": "root-thread",
                "app_server_events": [],
            },
        }), encoding="utf-8")
        return adapter_path, response_path

    def _run(self, *, validation="pass", **evidence):
        state_path = self.program / "教授研究/X分野/Example Professor/套磁候选状态.json"
        state_path.unlink(missing_ok=True)
        pre = self.output / "stage3-pre.json"
        self._write_snapshot(pre)
        self._write_state(validation=validation)
        post = self.output / "stage3-post.json"
        self._write_snapshot(post)
        adapter, response = self._write_evidence(**evidence)
        return verifier._checkpoint_stage3_routing(self.args(
            pre_snapshot=pre, post_snapshot=post,
            adapter_output=adapter, eval_response=response,
        ))

    def test_stage3_routing_passes_with_root_spawn_filter_and_ignores_wait(self):
        payload = self._run()
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS")
        self.assertEqual(
            payload["root_direct_spawn_child_ids"],
            ["child-generator", "child-validator"],
        )

    def test_stage3_routing_rejects_parent_only_relation_as_invalid_evidence(self):
        payload = self._run(sender_field=False)
        self.assertEqual(payload["status"], "invalid", payload)
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")

    def test_stage3_routing_classifies_unobservable_and_insufficient_children(self):
        blocked = self._run(delegation_state="unobservable")
        self.assertEqual(blocked["status"], "blocked", blocked)
        self.assertEqual(blocked["classification"], "BLOCKED_OBSERVABILITY")

        state_path = self.program / "教授研究/X分野/Example Professor/套磁候选状态.json"
        state_path.unlink(missing_ok=True)
        pre = self.output / "no-formal-pre.json"
        self._write_snapshot(pre)
        self._write_state()
        adapter, response = self._write_evidence()
        payload = json.loads(adapter.read_text(encoding="utf-8"))
        payload["dispatch"]["thread_relations"] = [{
            "tool": "wait", "sender_thread_id": "root-thread",
            "receiver_thread_ids": ["child-generator", "child-validator"],
        }]
        adapter.write_text(json.dumps(payload), encoding="utf-8")
        post = self.output / "no-formal-post.json"
        self._write_snapshot(post)
        no_formal = verifier._checkpoint_stage3_routing(self.args(
            pre_snapshot=pre, post_snapshot=post,
            adapter_output=adapter, eval_response=response,
        ))
        self.assertEqual(no_formal["status"], "blocked", no_formal)
        self.assertEqual(no_formal["classification"], "BLOCKED_OBSERVABILITY")

        insufficient = self._run(direct_children=("only-child",))
        self.assertEqual(insufficient["status"], "fail", insufficient)
        self.assertEqual(insufficient["classification"], "FAIL_PRODUCT")

    def test_stage3_routing_rejects_skipped_validation_and_stage4_outputs(self):
        skipped = self._run(validation="skipped")
        self.assertEqual(skipped["status"], "fail", skipped)
        self.assertEqual(skipped["classification"], "FAIL_PRODUCT")

        state_path = self.program / "教授研究/X分野/Example Professor/套磁候选状态.json"
        state_path.unlink(missing_ok=True)
        pre = self.output / "stage4-pre.json"
        self._write_snapshot(pre)
        self._write_state()
        stage4 = self.program / "教授研究/邮件输入.json"
        stage4.parent.mkdir(parents=True, exist_ok=True)
        stage4.write_text("{}", encoding="utf-8")
        post = self.output / "stage4-post.json"
        self._write_snapshot(post)
        adapter, response = self._write_evidence()
        payload = verifier._checkpoint_stage3_routing(self.args(
            pre_snapshot=pre, post_snapshot=post,
            adapter_output=adapter, eval_response=response,
        ))
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["classification"], "FAIL_PRODUCT")


if __name__ == "__main__":
    unittest.main()
