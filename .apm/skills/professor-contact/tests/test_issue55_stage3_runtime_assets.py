"""Deterministic assets and verifier coverage for issue #55 PC55-R1."""

import importlib.util
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"
FIXTURE_SCRIPT = RUNTIME_DIR / "prepare_issue55_stage3_fixture.py"
REQUEST_SCRIPT = RUNTIME_DIR / "build_issue55_eval_request.py"
VERIFIER_SCRIPT = RUNTIME_DIR / "verify_issue32_e2e.py"
PRODUCTION_STATE_SCRIPT = TESTS_DIR.parent / "scripts/contact_state.py"


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
        paper = pack["papers"]["PAPER0001"]
        self.assertEqual(
            set(paper),
            {"item_key", "title", "year", "authorship", "analysis_file",
             "pdf_available", "facts_state", "facts_error", "paper_facts"},
        )
        self.assertEqual(paper["facts_state"], "valid")
        self.assertIsInstance(paper["paper_facts"], dict)
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

    def test_fixture_passes_real_stage3_plan_compatibility_check(self):
        result = subprocess.run(
            [
                sys.executable, "-B", str(PRODUCTION_STATE_SCRIPT), "stage3-plan",
                "--program-root", str(self.program),
                "--professor-dir", str(self.program / "教授研究/X分野/Example Professor"),
                "--profile", str(self.program / "套磁邮件/套磁信息.md"),
                "--refresh-scope", "flagged",
                "--direction-id", "DIR00001",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok", payload)
        self.assertTrue(payload["write_needed"], payload)
        self.assertEqual(payload["skipped_direction_ids"], [], payload)
        self.assertEqual(
            [row for row in payload["directions"]
             if row.get("direction_id") == "DIR00001" and row.get("action") == "process"],
            [{"direction_id": "DIR00001", "collection_key": None, "action": "process"}],
        )
        candidate_jobs = [job for job in payload["jobs"]
                          if job.get("kind") == "candidates"
                          and job.get("direction_id") == "DIR00001"]
        self.assertEqual(len(candidate_jobs), 1, payload)
        self.assertEqual(
            candidate_jobs,
            [job for job in payload["jobs"] if job.get("kind") == "candidates"],
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
        self.assertEqual(argv[7:10], ["--model", "gpt-6-luna", "--config"])
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

    def _write_state(self, *, validation="pass", direction_candidates=None,
                     top_level_candidates=None, duplicate_direction=False):
        candidates = [
            {"id": f"idea-{index}", "direction_ids": ["DIR00001"]}
            for index in range(1, 4)
        ]
        if direction_candidates is None:
            direction_candidates = candidates
        directions = [{"direction_id": "DIR00001", "candidates": direction_candidates}]
        if duplicate_direction:
            directions.append({"direction_id": "DIR00001", "candidates": direction_candidates})
        state = {
            "schema": 2,
            "kind": "professor-contact-stage3-state",
            "identity_version": "direction-id-v1",
            "generator_contract_version": "stage3-ideas-v2",
            "directions": directions,
            "validator": {"results": {"DIR00001": {
                "result": validation,
                "rounds": 2 if validation == "fail_after_2_rounds" else 1,
                "issues": [] if validation == "pass" else ["candidate issue"],
            }}},
        }
        if top_level_candidates is not None:
            state["candidates"] = top_level_candidates
        path = self.program / "教授研究/X分野/Example Professor/套磁候选状态.json"
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    def _write_evidence(self, *, direct_children=("child-generator", "child-validator"),
                        delegation_state="confirmed", sender_field=True,
                        nested_sender=None):
        relations = [
            {"tool": "spawnAgent", "sender_thread_id": "root-thread",
             "receiver_thread_ids": list(direct_children)},
            {"tool": "wait", "sender_thread_id": "root-thread",
             "receiver_thread_ids": list(direct_children)},
            {"tool": "sendInput", "sender_thread_id": "root-thread",
             "receiver_thread_ids": [direct_children[0]]},
        ]
        if nested_sender is not None:
            relations.insert(1, {
                "tool": "spawnAgent", "sender_thread_id": nested_sender,
                "receiver_thread_ids": ["nested-child"],
            })
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

    def _run(self, *, validation="pass", direction_candidates=None,
             top_level_candidates=None, dirty_pre=False, stale_post=False,
             duplicate_direction=False,
             **evidence):
        state_path = self.program / "教授研究/X分野/Example Professor/套磁候选状态.json"
        state_path.unlink(missing_ok=True)
        pre = self.output / "stage3-pre.json"
        if dirty_pre:
            self._write_state(
                validation=validation,
                direction_candidates=direction_candidates,
                top_level_candidates=top_level_candidates,
                duplicate_direction=duplicate_direction,
            )
        self._write_snapshot(pre)
        if not dirty_pre:
            self._write_state(
                validation=validation,
                direction_candidates=direction_candidates,
                top_level_candidates=top_level_candidates,
                duplicate_direction=duplicate_direction,
            )
        post = self.output / "stage3-post.json"
        self._write_snapshot(post)
        if stale_post:
            state_path.write_text(
                state_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )
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

    def test_stage3_routing_rejects_nested_formal_spawn_from_root_child(self):
        payload = self._run(nested_sender="child-validator")
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["classification"], "FAIL_PRODUCT")
        self.assertTrue(any(
            row["name"] == "no_nested_formal_spawn" and row["status"] == "fail"
            for row in payload["checks"]
        ))

    def test_stage3_routing_requires_exactly_two_root_children_for_one_round(self):
        payload = self._run(
            validation="pass",
            direct_children=("child-generator", "child-validator", "unexpected"),
        )
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["classification"], "FAIL_PRODUCT")

    def test_stage3_routing_requires_exactly_four_root_children_for_two_rounds(self):
        payload = self._run(
            validation="fail_after_2_rounds",
            direct_children=("generator-1", "validator-1"),
        )
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["classification"], "FAIL_PRODUCT")

    def test_stage3_routing_accepts_clean_two_round_sibling_topology(self):
        payload = self._run(
            validation="fail_after_2_rounds",
            direct_children=("generator-1", "validator-1", "generator-2", "validator-2"),
        )
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["classification"], "PASS")

    def test_stage3_routing_rejects_parent_only_relation_as_invalid_evidence(self):
        payload = self._run(sender_field=False)
        self.assertEqual(payload["status"], "invalid", payload)
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")

    def test_stage3_routing_uses_only_direction_owned_candidates(self):
        fake_top_level = [
            {"id": f"fake-{index}", "direction_ids": ["DIR00001"]}
            for index in range(1, 4)
        ]
        payload = self._run(
            direction_candidates=[], top_level_candidates=fake_top_level,
        )
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["classification"], "FAIL_PRODUCT")

    def test_stage3_routing_rejects_duplicate_direction_rows(self):
        payload = self._run(duplicate_direction=True)
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["classification"], "FAIL_PRODUCT")

    def test_stage3_routing_invalidates_dirty_pre_and_stale_post_snapshots(self):
        dirty_pre = self._run(dirty_pre=True)
        self.assertEqual(dirty_pre["status"], "invalid", dirty_pre)
        self.assertEqual(dirty_pre["classification"], "INVALID_TEST_EXECUTION")

        stale_post = self._run(stale_post=True)
        self.assertEqual(stale_post["status"], "invalid", stale_post)
        self.assertEqual(stale_post["classification"], "INVALID_TEST_EXECUTION")

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

    def test_runtime_assets_have_cli_success_and_failure_smoke_paths(self):
        cli_program = self.root / "cli-program"
        cli_setup = self.output / "cli-runtime-setup.json"
        fixture_result = subprocess.run(
            [sys.executable, "-B", str(FIXTURE_SCRIPT),
             "--program-root", str(cli_program), "--output", str(cli_setup)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(fixture_result.returncode, 0, fixture_result.stderr)
        self.assertEqual(json.loads(fixture_result.stdout)["status"], "ok")

        foreign = self.root / "foreign-cli"
        foreign.mkdir()
        (foreign / "keep.txt").write_text("keep", encoding="utf-8")
        fixture_failure = subprocess.run(
            [sys.executable, "-B", str(FIXTURE_SCRIPT),
             "--program-root", str(foreign),
             "--output", str(self.output / "foreign-cli.json")],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(fixture_failure.returncode, 0)
        self.assertEqual(json.loads(fixture_failure.stdout)["status"], "error")

        rendered = self.output / "cli-prompt.txt"
        request_output = self.output / "cli-request.json"
        request_result = subprocess.run(
            [sys.executable, "-B", str(REQUEST_SCRIPT),
             "--consumer-root", str(self.consumer), "--program-root", str(self.program),
             "--prompt-template", str(RUNTIME_DIR / "prompts/issue55-stage3-routing.txt"),
             "--rendered-prompt", str(rendered), "--output", str(request_output)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(request_result.returncode, 0, request_result.stderr)
        self.assertEqual(json.loads(request_result.stdout)["status"], "ok")

        request_failure = subprocess.run(
            [sys.executable, "-B", str(REQUEST_SCRIPT),
             "--consumer-root", str(self.consumer), "--program-root", str(self.program),
             "--prompt-template", str(RUNTIME_DIR / "prompts/issue55-stage3-routing.txt"),
             "--rendered-prompt", str(rendered), "--model", "gpt-5.5",
             "--output", str(request_output)],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(request_failure.returncode, 0)
        self.assertEqual(json.loads(request_failure.stdout)["status"], "error")

        snapshot_output = self.output / "cli-snapshot.json"
        snapshot_result = subprocess.run(
            [sys.executable, "-B", str(VERIFIER_SCRIPT), "stage3-snapshot",
             "--program-root", str(self.program), "--output", str(snapshot_output)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(snapshot_result.returncode, 0, snapshot_result.stderr)
        self.assertEqual(json.loads(snapshot_result.stdout)["status"], "pass")

        missing_snapshot = subprocess.run(
            [sys.executable, "-B", str(VERIFIER_SCRIPT), "stage3-snapshot",
             "--program-root", str(self.root / "missing-program")],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(missing_snapshot.returncode, 0)
        self.assertEqual(json.loads(missing_snapshot.stdout)["status"], "fail")

        self._write_state()
        post = self.output / "cli-post.json"
        self._write_snapshot(post)
        adapter, response = self._write_evidence()
        routing_output = self.output / "cli-routing.json"
        routing_result = subprocess.run(
            [sys.executable, "-B", str(VERIFIER_SCRIPT), "stage3-routing",
             "--program-root", str(self.program), "--eval-response", str(response),
             "--adapter-output", str(adapter), "--pre-snapshot", str(snapshot_output),
             "--post-snapshot", str(post), "--output", str(routing_output)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(routing_result.returncode, 0, routing_result.stderr)
        self.assertEqual(json.loads(routing_result.stdout)["classification"], "PASS")

        self._write_state(direction_candidates=[])
        bad_post = self.output / "cli-bad-post.json"
        self._write_snapshot(bad_post)
        bad_routing = subprocess.run(
            [sys.executable, "-B", str(VERIFIER_SCRIPT), "stage3-routing",
             "--program-root", str(self.program), "--eval-response", str(response),
             "--adapter-output", str(adapter), "--pre-snapshot", str(snapshot_output),
             "--post-snapshot", str(bad_post)],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(bad_routing.returncode, 0)
        self.assertEqual(json.loads(bad_routing.stdout)["classification"], "FAIL_PRODUCT")


if __name__ == "__main__":
    unittest.main()
