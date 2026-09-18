import contextlib
import io
import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BUILDER_PATH = TESTS_DIR / "runtime/build_issue32_e2e_fixture.py"
VERIFIER_PATH = TESTS_DIR / "runtime/verify_issue32_e2e.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module("issue32_fixture_builder_for_verifier", BUILDER_PATH)
verifier = load_module("issue32_verifier", VERIFIER_PATH)


class Issue32VerifierTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name) / "program"
        self.profile = Path(self.holder.name) / "profile"
        builder.build_fixture(self.root, self.profile)

    def args(self, **overrides):
        values = {
            "program_root": self.root,
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

    def test_initial_checkpoint_is_pass_and_stage0_state_is_absent(self):
        payload = verifier._checkpoint_initial(self.args())
        self.assertEqual(payload["status"], "pass", payload)
        self.assertFalse((self.root / "教授研究/套磁目标.json").exists())

    def test_install_reads_exact_professor_contact_commit_from_structured_lock(self):
        consumer = Path(self.holder.name) / "consumer"
        (consumer / ".agents/skills/professor-contact").mkdir(parents=True)
        (consumer / ".agents/skills/professor-contact/SKILL.md").write_text("installed", encoding="utf-8")
        (consumer / ".codex/agents").mkdir(parents=True)
        (consumer / ".codex/agents/professor-contact.toml").write_text("name='professor-contact'", encoding="utf-8")
        producer_sha = "a" * 40
        (consumer / "apm.lock.yaml").write_text(
            "dependencies:\n"
            "  - name: professor-research\n"
            f"    resolved_commit: {producer_sha}\n"
            "  - name: professor-contact\n"
            "    resolved_commit: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n",
            encoding="utf-8")
        payload = verifier._checkpoint_install(self.args(
            consumer_root=consumer, producer_sha=producer_sha))
        self.assertEqual(payload["status"], "fail", payload)

        (consumer / "apm.lock.yaml").write_text(
            "dependencies:\n"
            "  - name: professor-research\n"
            f"    resolved_commit: {producer_sha}\n"
            "  - name: professor-contact\n"
            f"    resolved_commit: {producer_sha}\n",
            encoding="utf-8")
        payload = verifier._checkpoint_install(self.args(
            consumer_root=consumer, producer_sha=producer_sha))
        self.assertEqual(payload["status"], "pass", payload)

    def test_install_cli_does_not_require_program_root(self):
        args = verifier._parser().parse_args([
            "install", "--consumer-root", "/tmp/consumer",
        ])
        self.assertIsNone(args.program_root)

    def test_stage0_needs_input_requires_structured_selection_request(self):
        response = Path(self.holder.name) / "stage0.json"
        response.write_text(json.dumps({
            "selection_request": {"direction_ids": ["DIR00001"], "status": "needs_input"}
        }), encoding="utf-8")
        payload = verifier._checkpoint_stage0_needs_input(self.args(eval_response=response))
        self.assertEqual(payload["status"], "pass", payload)

        response.write_text("The model says it needs a selection.", encoding="utf-8")
        payload = verifier._checkpoint_stage0_needs_input(self.args(eval_response=response))
        self.assertEqual(payload["status"], "fail", payload)

    def test_stage4_snapshot_reports_program_level_zero_write_artifacts(self):
        payload = verifier._checkpoint_stage4_snapshot(self.args())
        self.assertEqual(
            payload["artifacts"],
            {
                "套磁选择.json": {"exists": False, "sha256": None},
                "邮件输入.json": {"exists": False, "sha256": None},
            },
        )

    def test_stage4_snapshot_cli_persists_requested_output(self):
        output = Path(self.holder.name) / "stage4-snapshot.json"
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = verifier.main([
                "stage4-snapshot",
                "--program-root", str(self.root),
                "--output", str(output),
            ])
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(output.read_text(encoding="utf-8"))["artifacts"]["套磁选择.json"],
            {"exists": False, "sha256": None},
        )

    def test_stage3_snapshot_covers_stage3_and_stage4_program_outputs(self):
        payload = verifier._checkpoint_stage3_snapshot(self.args())
        self.assertEqual(payload["status"], "pass", payload)
        self.assertTrue(payload["artifacts"]["套磁候选状态.json"]["sha256"] is None)
        self.assertEqual(
            set(payload["artifacts"]),
            {
                "套磁候选状态.json", "套磁想法候选.md", "套磁想法候选总览.md",
                "套磁选择.json", "邮件输入.json",
            },
        )
        stage4 = self.root / "教授研究/套磁选择.json"
        stage4.parent.mkdir(parents=True, exist_ok=True)
        stage4.write_text("{}", encoding="utf-8")
        payload = verifier._checkpoint_stage3_snapshot(self.args())
        self.assertEqual(payload["status"], "pass", payload)
        self.assertTrue(payload["artifacts"]["套磁选择.json"]["exists"])

    def test_make_stage4_selection_sorts_candidates_and_writes_only_requested_file(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        state = {"schema_version": 2, "directions": [{"direction_id": "DIR00001"}],
                 "candidates": [{"id": "zeta"}, {"id": "alpha"}, {"id": "beta"}]}
        (prof / "套磁候选状态.json").write_text(json.dumps(state), encoding="utf-8")
        output = Path(self.holder.name) / "selection.json"
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        payload = verifier._checkpoint_make_stage4_selection(self.args(output=output))
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["observed"]["selected_id"], "alpha")
        selected = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(selected["selection"][0]["ideas"][0]["id"], "alpha")
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        self.assertEqual(before, after)

    def test_stage2_requires_machine_contract_and_allows_new_bbbb_analysis(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        pack = {
            "schema": 2,
            "kind": "professor-contact-stage2-input",
            "identity_version": "direction-id-v1",
            "managed_by": "contact_state",
            "professor": "Example Professor",
            "professor_dir": str(prof),
            "papers": {"AAAA1111": {"item_key": "AAAA1111"}},
            "directions": [{
                "direction_id": "DIR00001",
                "input_fingerprint": "direction-fingerprint",
                "supporting_item_keys": ["AAAA1111"],
            }],
        }
        (prof / "套磁候选输入.json").write_text(json.dumps(pack), encoding="utf-8")
        (prof / "论文分析/AAAA1111.md").write_text("analysis", encoding="utf-8")
        (prof / "论文分析/AAAA1111.future_work.json").write_text("{}", encoding="utf-8")
        (prof / "论文分析/BBBB2222.md").write_text("analysis created in Stage 2", encoding="utf-8")
        payload = verifier._checkpoint_stage2_final(self.args())
        self.assertEqual(payload["status"], "pass", payload)

        pack["directions"][0]["direction_id"] = "OTHER"
        pack["notes"] = "DIR00001 appears only in unrelated text"
        (prof / "套磁候选输入.json").write_text(json.dumps(pack), encoding="utf-8")
        payload = verifier._checkpoint_stage2_final(self.args())
        self.assertEqual(payload["status"], "fail", payload)

    def test_stage3_requires_current_v2_state_and_real_validation(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        candidates = [
            {"id": f"idea-{index}", "direction_ids": ["DIR00001"]}
            for index in range(3)
        ]
        state = {
            "schema": 2,
            "kind": "professor-contact-stage3-state",
            "identity_version": "direction-id-v1",
            "generator_contract_version": "stage3-ideas-v2",
            "directions": [{"direction_id": "DIR00001", "candidates": candidates}],
            "validator": {"results": {"DIR00001": {
                "result": "pass", "rounds": 1, "issues": []
            }}},
        }
        path = prof / "套磁候选状态.json"
        path.write_text(json.dumps(state), encoding="utf-8")
        payload = verifier._checkpoint_stage3_final(self.args())
        self.assertEqual(payload["status"], "pass", payload)

        state["kind"] = "wrong-kind"
        path.write_text(json.dumps(state), encoding="utf-8")
        payload = verifier._checkpoint_stage3_final(self.args())
        self.assertEqual(payload["status"], "fail", payload)

    def test_stage5_requires_structured_pass_for_both_outputs_and_frozen_pack(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        for name in ("套磁邮件.md", "套磁跟进邮件.md", "套磁邮件.txt", "套磁跟进邮件.txt"):
            (prof / name).write_text("send checklist; pass 通过", encoding="utf-8")
        email_id = "Example Professor::DIR00001::idea-1"
        email_pack = {
            "schema": 2,
            "kind": "professor-contact-email-input",
            "identity_version": "direction-id-v1",
            "emails": [{
                "email_id": email_id,
                "direction_ids": ["DIR00001"],
                "source_hash": "source-fingerprint",
                "contact_evidence": {
                    "record_fingerprint": "record-fingerprint",
                    "record": {"email": "faculty@example.edu"},
                },
            }],
        }
        (prof / "邮件输入.json").write_text(json.dumps(email_pack), encoding="utf-8")
        email_state = {
            "schema": 1,
            "emails": {email_id: {
                "input_fingerprint": "source-fingerprint",
                "validation": {"result": "fail_after_2_rounds", "rounds": 2, "issues": ["bad"]},
                "followup": {"validation": {"result": "fail_after_2_rounds", "rounds": 2, "issues": ["bad"]}},
            }},
        }
        state_path = prof / "套磁邮件状态.json"
        state_path.write_text(json.dumps(email_state), encoding="utf-8")
        payload = verifier._checkpoint_stage5_final(self.args())
        self.assertEqual(payload["status"], "fail", payload)

        for validation in (
            email_state["emails"][email_id]["validation"],
            email_state["emails"][email_id]["followup"]["validation"],
        ):
            validation.update(result="pass", rounds=1, issues=[])
        state_path.write_text(json.dumps(email_state), encoding="utf-8")
        payload = verifier._checkpoint_stage5_final(self.args())
        self.assertEqual(payload["status"], "pass", payload)

    def test_runtime_graph_rejects_identity_only_and_accepts_formal_events(self):
        identity = Path(self.holder.name) / "identity.json"
        identity.write_text(json.dumps({"loaded_agents": ["professor-contact", "downloader"]}), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(self.args(adapter_output=identity))
        self.assertEqual(payload["status"], "fail", payload)

        events = Path(self.holder.name) / "adapter.json"
        events.write_text(json.dumps({
            "delegation": {
                "state": "confirmed",
                "basis": ["formal_spawn_relation"],
                "formal_child_count": 2,
                "child_thread_ids": ["downloader", "analyzer"],
            },
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "parent_thread_id": "contact", "receiver_thread_ids": ["downloader"]},
                {"tool": "spawnAgent", "status": "completed",
                 "parent_thread_id": "downloader", "receiver_thread_ids": ["analyzer"]},
                {"tool": "wait", "status": "completed",
                 "parent_thread_id": "contact", "receiver_thread_ids": ["analyzer"]},
            ]},
        }), encoding="utf-8")
        raw_response = Path(self.holder.name) / "response.json"
        raw_response.write_text(json.dumps({
            "output": {"app_server_events": [{"type": "spawnAgent"}]},
        }), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(
            self.args(adapter_output=events, eval_response=raw_response,
                      min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "pass", payload)

        misplaced_raw = Path(self.holder.name) / "misplaced-response.json"
        misplaced_raw.write_text(json.dumps({"app_server_events": []}), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(
            self.args(adapter_output=events, eval_response=misplaced_raw,
                      min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "fail", payload)

        disconnected = Path(self.holder.name) / "disconnected.json"
        disconnected.write_text(json.dumps({
            "delegation": {"state": "confirmed", "basis": ["formal_spawn_relation"],
                            "child_thread_ids": ["c1", "c2"]},
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "parent_thread_id": "p1", "receiver_thread_ids": ["c1"]},
                {"tool": "spawnAgent", "status": "completed",
                 "parent_thread_id": "p2", "receiver_thread_ids": ["c2"]},
            ]},
        }), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(
            self.args(adapter_output=disconnected, min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "fail", payload)

        unobservable = Path(self.holder.name) / "unobservable.json"
        unobservable.write_text(json.dumps({
            "delegation": {"state": "unobservable", "basis": [], "child_thread_ids": []},
            "dispatch": {"thread_relations": []},
        }), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(self.args(adapter_output=unobservable))
        self.assertEqual(payload["status"], "fail", payload)


if __name__ == "__main__":
    unittest.main()
