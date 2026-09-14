"""Issue #40: the runtime verifier proves formal topology + continuity only.

Named-role identity is a diagnostic that never gates; ``delegation=unobservable``
maps to a NOT TESTED observability gap, never a producer FAIL; malformed
evidence still fails closed; Stage 4/5 canonical files are program-level only;
next-stage formal loaders must actually consume each artifact.
"""
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

PROF = Path("教授研究/X分野/Example Professor")


def write_items_config(directory: Path) -> Path:
    config = directory / "config" / "zotero-items.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({
        "schema_version": 1,
        "item_keys": ["K1AAAA", "K2BBBB"],
        "ready_item_keys": ["K1AAAA"],
        "fill_target_item_key": "K2BBBB",
        "fill_target_pdf_status": "pending",
        "fixture_run_id": "run-xyz",
    }), encoding="utf-8")
    return config


def make_consumer(root: Path, behaviors: dict[str, str] | None = None) -> Path:
    """Create a stub clean consumer whose runner scripts answer deterministically."""
    scripts = root / ".agents/skills/professor-contact/scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    behaviors = behaviors or {}
    for name in ("contact_stage1.py", "contact_state.py"):
        ok = behaviors.get(name, "ok") == "ok"
        body = (
            "import json, sys\n"
            "sys.argv = sys.argv\n"
            + ("print(json.dumps({'status': 'ok'}))\n" if ok else
               "print(json.dumps({'status': 'needs_refresh'})); sys.exit(3)\n")
        )
        (scripts / name).write_text(body, encoding="utf-8")
    return root


def adapter_evidence(directory: Path, name: str, *, relations, delegation_state="confirmed",
                     fixture_status="FIXTURE_READY", identity=None, reason_code=None) -> Path:
    """relations: list of (tool, status, parent_thread, child_thread) tuples."""
    rows = [{"tool": tool, "status": status,
             "parent_thread_id": parent, "sender_thread_id": parent,
             "receiver_thread_ids": [child] if isinstance(child, str) else list(child)}
            for tool, status, parent, child in relations]
    child_ids = sorted({child for row in rows for child in row["receiver_thread_ids"]})
    payload = {
        "schema": 1,
        "role": "codex-eval-evidence",
        "fixture_status": fixture_status,
        "delegation": {
            "state": delegation_state,
            "basis": ["formal_spawn_relation"] if delegation_state == "confirmed" else [],
            "formal_child_count": len(child_ids),
            "child_thread_ids": child_ids,
            "reason_code": reason_code,
        },
        "dispatch": {
            "thread_relations": rows,
            "agent_identity": identity or {},
        },
    }
    path = Path(directory) / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def eval_response(directory: Path, *, terminated=True) -> Path:
    path = Path(directory) / "response.json"
    path.write_text(json.dumps({
        "version": "0.153.4",
        "output": {"thread_id": "t0", "turn_id": "u0",
                   "termination_reason": "end_turn" if terminated else ""},
    }), encoding="utf-8")
    return path


class Issue32VerifierTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name) / "program"
        self.profile = Path(self.holder.name) / "profile"
        self.config = write_items_config(Path(self.holder.name))
        builder.build_fixture(self.root, self.profile, zotero_items_config=self.config)

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
            "min_siblings": 1,
            "require_followup": False,
        }
        values.update(overrides)
        return Namespace(**values)

    # ---- setup gates -----------------------------------------------------

    def test_initial_checkpoint_is_pass_and_stage_outputs_are_absent(self):
        payload = verifier._checkpoint_initial(self.args())
        self.assertEqual(payload["status"], "pass", payload)
        self.assertFalse((self.root / "教授研究/套磁目标.json").exists())

    def test_initial_requires_owner_raw_sources_without_prebuilt_evidence(self):
        (self.root / "教授研究/contact-evidence-fixture-input.json").write_text("{}", encoding="utf-8")
        payload = verifier._checkpoint_initial(self.args())
        self.assertEqual(payload["status"], "fail", payload)
        (self.root / "教授研究/contact-evidence-fixture-input.json").unlink()
        self.assertEqual(verifier._checkpoint_initial(self.args())["status"], "pass")

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

    # ---- R1: Stage 1 continuity -----------------------------------------

    def test_stage1_uses_dynamic_manifest_keys_and_formal_stage2_loader(self):
        consumer = make_consumer(Path(self.holder.name) / "consumer-ok")
        (self.root / "教授研究/套磁阶段1候选.json").write_text(json.dumps({
            "schema_version": 1,
            "kind": "professor-contact-stage1",
            "professors": [{"professor": "Example Professor",
                            "directions": [{"direction_id": "DIR00001",
                                            "candidate_keys": ["K1AAAA", "K2BBBB"]}]}],
        }), encoding="utf-8")
        payload = verifier._checkpoint_stage1_final(self.args(consumer_root=consumer))
        self.assertEqual(payload["status"], "pass", payload)

        consumer_fail = make_consumer(Path(self.holder.name) / "consumer-bad",
                                      behaviors={"contact_stage1.py": "fail"})
        payload = verifier._checkpoint_stage1_final(self.args(consumer_root=consumer_fail))
        self.assertEqual(payload["status"], "fail", payload)

    def test_stage1_does_not_require_collector_payload_wrapper(self):
        consumer = make_consumer(Path(self.holder.name) / "consumer-ok2")
        (self.root / "教授研究/套磁阶段1候选.json").write_text(json.dumps({
            "schema_version": 1, "kind": "professor-contact-stage1",
            "professors": [{"professor": "Example Professor",
                            "directions": [{"direction_id": "DIR00001",
                                            "candidate_keys": ["K1AAAA", "K2BBBB"]}]}],
        }), encoding="utf-8")
        response = eval_response(Path(self.holder.name))
        response.write_text(json.dumps({"output": {
            "thread_id": "t", "termination_reason": "end_turn",
            "app_server_events": [], "notes": "collector ran; no payload wrapper"}}),
            encoding="utf-8")
        payload = verifier._checkpoint_stage1_final(
            self.args(consumer_root=consumer, eval_response=response))
        self.assertEqual(payload["status"], "pass", payload)

    def test_stage1_fails_without_snapshot(self):
        consumer = make_consumer(Path(self.holder.name) / "consumer-ok3")
        payload = verifier._checkpoint_stage1_final(self.args(consumer_root=consumer))
        self.assertEqual(payload["status"], "fail", payload)

    # ---- R2: Stage 2 continuity -----------------------------------------

    def test_stage2_requires_direction_join_and_formal_stage3_loader(self):
        consumer = make_consumer(Path(self.holder.name) / "consumer-ok4")
        prof = self.root / PROF
        pack = {"schema": 2, "professor": "Example Professor",
                "directions": [{"direction_id": "DIR00001"}]}
        (prof / "套磁候选输入.json").write_text(json.dumps(pack), encoding="utf-8")
        payload = verifier._checkpoint_stage2_final(self.args(consumer_root=consumer))
        self.assertEqual(payload["status"], "pass", payload)

        pack["directions"][0]["direction_id"] = "OTHER"
        (prof / "套磁候选输入.json").write_text(json.dumps(pack), encoding="utf-8")
        payload = verifier._checkpoint_stage2_final(self.args(consumer_root=consumer))
        self.assertEqual(payload["status"], "fail", payload)

    # ---- R3-A: Stage 3 state readable by the Stage 4 reader --------------

    def test_stage3_requires_readable_state_with_machine_direction(self):
        prof = self.root / PROF
        state = {"schema": 2, "directions": [{"direction_id": "DIR00001",
                                              "candidates": [{"id": "idea-1"}]}]}
        (prof / "套磁候选状态.json").write_text(json.dumps(state), encoding="utf-8")
        payload = verifier._checkpoint_stage3_final(self.args())
        self.assertEqual(payload["status"], "pass", payload)

        state["directions"][0]["direction_id"] = "OTHER"
        (prof / "套磁候选状态.json").write_text(json.dumps(state), encoding="utf-8")
        payload = verifier._checkpoint_stage3_final(self.args())
        self.assertEqual(payload["status"], "fail", payload)

    def test_make_stage4_selection_sorts_candidates_and_writes_only_requested_file(self):
        prof = self.root / PROF
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

    # ---- R3-B: no-selection boundary, program-level zero-write -----------

    def test_stage4_needs_input_checks_program_level_only(self):
        prof = self.root / PROF
        # Same-named files inside the professor directory must not create a
        # false pass/fail signal: only program-level canonical paths count.
        (prof / "套磁选择.json").write_text("{}", encoding="utf-8")
        (prof / "邮件输入.json").write_text("{}", encoding="utf-8")
        response = eval_response(Path(self.holder.name))
        payload = verifier._checkpoint_stage4_needs_input(self.args(eval_response=response))
        self.assertEqual(payload["status"], "pass", payload)

        (self.root / "教授研究/套磁选择.json").write_text("{}", encoding="utf-8")
        payload = verifier._checkpoint_stage4_needs_input(self.args(eval_response=response))
        self.assertEqual(payload["status"], "fail", payload)

    def test_stage4_needs_input_requires_a_normally_terminated_run(self):
        response = eval_response(Path(self.holder.name), terminated=False)
        payload = verifier._checkpoint_stage4_needs_input(self.args(eval_response=response))
        self.assertEqual(payload["status"], "fail", payload)

    # ---- R4: explicit selection continuation + final artifact ------------

    def test_stage4_final_requires_program_level_canonical_files(self):
        consumer = make_consumer(Path(self.holder.name) / "consumer-ok5")
        prof = self.root / PROF
        (prof / "套磁选择.json").write_text(json.dumps({"professor": "x"}), encoding="utf-8")
        (prof / "邮件输入.json").write_text(json.dumps({"emails": []}), encoding="utf-8")
        payload = verifier._checkpoint_stage4_final(self.args(consumer_root=consumer))
        self.assertEqual(payload["status"], "fail", payload)

        (self.root / "教授研究/套磁选择.json").write_text(json.dumps({"selection": []}), encoding="utf-8")
        (self.root / "教授研究/邮件输入.json").write_text(json.dumps({"emails": [{"email_id": "e1"}]}),
                                                          encoding="utf-8")
        payload = verifier._checkpoint_stage4_final(self.args(consumer_root=consumer))
        self.assertEqual(payload["status"], "pass", payload)

    def test_stage5_checks_artifact_existence_and_frozen_pack_readability(self):
        prof = self.root / PROF
        (prof / "套磁邮件.md").write_text("initial email", encoding="utf-8")
        (self.root / "教授研究/邮件输入.json").write_text(
            json.dumps({"emails": [{"email_id": "e1"}]}), encoding="utf-8")
        payload = verifier._checkpoint_stage5_final(self.args())
        self.assertEqual(payload["status"], "pass", payload)

        payload = verifier._checkpoint_stage5_final(self.args(require_followup=True))
        self.assertEqual(payload["status"], "fail", payload)

        (prof / "套磁跟进邮件.md").write_text("followup", encoding="utf-8")
        payload = verifier._checkpoint_stage5_final(self.args(require_followup=True))
        self.assertEqual(payload["status"], "pass", payload)

    # ---- runtime topology: formal delegation only ------------------------

    def test_runtime_graph_formal_topology_positive_and_negative(self):
        relations = [
            ("spawnAgent", "completed", "root", "child-a"),
            ("spawnAgent", "completed", "child-a", "grandchild-a"),
        ]
        adapter = adapter_evidence(Path(self.holder.name), "d2.json", relations=relations)
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter, eval_response=eval_response(Path(self.holder.name)),
            min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "pass", payload)

        shallow = [("spawnAgent", "completed", "root", "child-a")]
        adapter_shallow = adapter_evidence(Path(self.holder.name), "d1.json", relations=shallow)
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter_shallow, eval_response=eval_response(Path(self.holder.name)),
            min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "fail", payload)

    def test_runtime_graph_r2_requires_anonymous_depth_three(self):
        relations = [
            ("spawnAgent", "completed", "root", "l1"),
            ("spawnAgent", "completed", "l1", "l2"),
            ("spawnAgent", "completed", "l2", "l3"),
        ]
        adapter = adapter_evidence(Path(self.holder.name), "r2.json", relations=relations)
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter, eval_response=eval_response(Path(self.holder.name)),
            min_edges=3, required_depth=3))
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["observed"]["formal_depth"], 3)

        adapter_broken = adapter_evidence(Path(self.holder.name), "r2b.json", relations=relations[:2])
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter_broken, eval_response=eval_response(Path(self.holder.name)),
            min_edges=3, required_depth=3))
        self.assertEqual(payload["status"], "fail", payload)

    def test_runtime_graph_r3_requires_minimum_root_siblings(self):
        relations = [
            ("spawnAgent", "completed", "root", "child-a"),
            ("spawnAgent", "completed", "root", "child-b"),
        ]
        adapter = adapter_evidence(Path(self.holder.name), "r3.json", relations=relations)
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter, eval_response=eval_response(Path(self.holder.name)),
            min_edges=2, required_depth=1, min_siblings=2))
        self.assertEqual(payload["status"], "pass", payload)

        single = [("spawnAgent", "completed", "root", "child-a")]
        adapter_single = adapter_evidence(Path(self.holder.name), "r3b.json", relations=single)
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter_single, eval_response=eval_response(Path(self.holder.name)),
            min_edges=1, required_depth=1, min_siblings=2))
        self.assertEqual(payload["status"], "fail", payload)

    def test_unobservable_delegation_is_not_tested_never_fail(self):
        adapter = adapter_evidence(Path(self.holder.name), "unobs.json", relations=[],
                                   delegation_state="unobservable",
                                   fixture_status="HARNESS_DISPATCH_UNCONFIRMED",
                                   reason_code="no_supported_formal_spawn_relation")
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter, eval_response=eval_response(Path(self.holder.name))))
        self.assertEqual(payload["status"], "not_tested", payload)
        self.assertEqual(payload["observed"]["classification"], "observability_gap")
        self.assertEqual(verifier.main(["runtime-graph",
                                        "--adapter-output", str(adapter),
                                        "--eval-response", str(eval_response(Path(self.holder.name))),
                                        "--program-root", str(self.root)]), 2)

    def test_malformed_evidence_fails_closed_as_harness_error(self):
        adapter = adapter_evidence(Path(self.holder.name), "bad.json", relations=[],
                                   fixture_status="INVALID_EVIDENCE")
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter, eval_response=eval_response(Path(self.holder.name))))
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["observed"]["classification"], "invalid_evidence")

    def test_conflicting_formal_ownership_fails_closed(self):
        relations = [
            ("spawnAgent", "completed", "root", "child-a"),
            ("spawnAgent", "completed", "other-root", "child-a"),
        ]
        adapter = adapter_evidence(Path(self.holder.name), "conflict.json", relations=relations)
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter, eval_response=eval_response(Path(self.holder.name))))
        self.assertEqual(payload["status"], "fail", payload)

    def test_identity_diagnostics_never_change_a_confirmed_delegation(self):
        relations = [("spawnAgent", "completed", "root", "child-a")]
        for identity in (
                {"child-a": {"requested_role": {"state": "contradicted", "value": "other"},
                             "loaded_identity": {"state": "unobservable"}}},
                {"child-a": {"requested_role": {"state": "confirmed", "value": "paper-analysis"},
                             "loaded_identity": {"state": "confirmed", "value": "paper-analysis"}}},
        ):
            adapter = adapter_evidence(Path(self.holder.name), "ident.json", relations=relations,
                                       identity=identity)
            payload = verifier._checkpoint_runtime_graph(self.args(
                adapter_output=adapter, eval_response=eval_response(Path(self.holder.name)),
                min_edges=1, required_depth=1))
            self.assertEqual(payload["status"], "pass", payload)
            self.assertEqual(payload["observed"]["identity_diagnostics"], identity)

    def test_common_eval_gate_requires_a_normally_terminated_run(self):
        relations = [("spawnAgent", "completed", "root", "child-a")]
        adapter = adapter_evidence(Path(self.holder.name), "gate.json", relations=relations)
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=adapter, eval_response=eval_response(Path(self.holder.name), terminated=False)))
        self.assertEqual(payload["status"], "fail", payload)


if __name__ == "__main__":
    unittest.main()
