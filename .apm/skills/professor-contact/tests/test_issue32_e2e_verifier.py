"""Issue #40 verifier regressions for the R1–R4 canonical runtime matrix.

The verifier must judge formal topology and canonical continuity only:
assistant prose never becomes evidence (#14), identity mismatch or
unobservability never downgrades a confirmed delegation into a FAIL (#15),
R3 omission uses pre/post file-state evidence (#16), ``BLOCKED_*`` and
``NOT TESTED`` never map to a pass (#17), and the old E0–E7 business-detail
checkpoints are gone from the canonical recipe (#18).
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BUILDER_PATH = TESTS_DIR / "runtime/build_issue32_e2e_fixture.py"
SETUP_PATH = TESTS_DIR / "runtime/prepare_issue40_runtime_fixture.py"
VERIFIER_PATH = TESTS_DIR / "runtime/verify_issue32_e2e.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module("issue40_builder_for_verifier", BUILDER_PATH)
helper = load_module("issue40_setup_for_verifier", SETUP_PATH)
verifier = load_module("issue40_verifier", VERIFIER_PATH)

FIXTURE_CONFIG = {
    "schema_version": 1,
    "fixture_run_id": "run-verifier-a",
    "item_keys": ["QK4RD7XT", "QK3SE2WV"],
    "ready_item_keys": ["QK4RD7XT"],
    "fill_target_item_key": "QK3SE2WV",
    "fill_target_pdf_status": "pending",
    "attachment_keys": {"QK4RD7XT": "ATTN0001", "QK3SE2WV": "ATTN0002"},
}


def relation(parent, children, tool="spawnAgent", status="completed"):
    return {"tool": tool, "status": status, "parent_thread_id": parent,
            "sender_thread_id": parent, "receiver_thread_ids": children}


def adapter_payload(*, relations, thread_id="root-thread-1",
                    fixture_status="FIXTURE_READY", delegation_state="confirmed",
                    contract=verifier.ADAPTER_CONTRACT_ID, children=None):
    children = children if children is not None else sorted(
        {child for row in relations for child in row["receiver_thread_ids"]})
    payload = {
        "adapter_contract_id": contract,
        "fixture_status": fixture_status,
        "delegation": {"state": delegation_state,
                       "basis": ["formal_spawn_relation"] if delegation_state == "confirmed" else [],
                       "formal_child_count": len(children),
                       "child_thread_ids": children,
                       "reason_code": None if delegation_state == "confirmed"
                       else "no_supported_formal_spawn_relation"},
        "dispatch": {"thread_relations": relations},
        "codex_evidence": {"thread_id": {"value": thread_id}},
    }
    if contract is None:
        payload.pop("adapter_contract_id")
    return payload


class VerifierTestCase(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.base = Path(self.holder.name)
        self.root = self.base / "program"
        self.profile = self.base / "profile"
        builder.build_fixture(self.root, self.profile,
                              zotero_items_config=json.loads(json.dumps(FIXTURE_CONFIG)))

    def args(self, **overrides):
        values = {
            "program_root": self.root,
            "consumer_root": None,
            "adapter_evidence": None,
            "eval_response": None,
            "pre_state": None,
            "selection_input": None,
            "producer_sha": "",
            "professor_research_sha": "",
            "output": None,
            "direction_id": "DIR00001",
            "selection_policy": "",
            "first_choice": False,
            "signature_name": "Fixture Applicant",
            "learning": "I am studying reproducible research workflows.",
            "initial_sent_date": "2026-09-15",
        }
        values.update(overrides)
        return Namespace(**values)

    def write_adapter(self, payload, name="adapter.json"):
        path = self.base / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def stage0_target(self):
        script = TESTS_DIR.parent / "scripts" / "contact_targets.py"
        selection = {"direction_ids": ["DIR00001"], "notes": {"DIR00001": "note"}}
        selection_file = self.base / "stage0-selection.json"
        selection_file.write_text(json.dumps(selection), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(script), "select", "--program-root", str(self.root),
             "--preview", str(self.root / "教授研究/X分野/Example Professor/方向预筛.json"),
             "--selection-file", str(selection_file)],
            capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def stage1_snapshot(self):
        script = TESTS_DIR.parent / "scripts" / "contact_stage1.py"
        completed = subprocess.run(
            [sys.executable, str(script), "build", "--program-root", str(self.root)],
            capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def nested_adapter(self, depth_filename="nested.json"):
        relations = [
            relation("root", ["child-1"]),
            relation("child-1", ["grand-1"]),
        ]
        return self.write_adapter(adapter_payload(
            relations=relations, thread_id="root",
            children=["child-1", "grand-1"]), depth_filename)


class RecipeShapeTests(VerifierTestCase):
    def test_old_e0_e7_checkpoints_are_removed(self):
        # #18: the canonical recipe no longer exposes business-detail gates.
        for legacy in ("initial", "stage0-needs-input", "stage0-final", "stage1-final",
                       "stage2-final", "stage3-final", "stage4-needs-input",
                       "stage4-final", "stage5-final", "runtime-graph"):
            self.assertNotIn(legacy, verifier.CASES)
            with self.assertRaises(SystemExit):
                verifier._parser().parse_args([legacy, "--program-root", str(self.root)])

    def test_runtime_cases_are_exactly_the_canonical_matrix(self):
        self.assertEqual(
            verifier.CASES,
            ("install", "r1", "r2", "r3a", "r3b", "r3-pre-omit", "r4a", "r4b"))


class InstallCaseTests(VerifierTestCase):
    def test_install_requires_consumer_and_pinned_shas(self):
        payload = verifier._checkpoint_install(self.args(consumer_root=self.base / "missing"))
        self.assertEqual(payload["status"], "blocked")

        consumer = self.base / "consumer"
        (consumer / ".agents/skills/professor-contact").mkdir(parents=True)
        (consumer / ".agents/skills/professor-contact/SKILL.md").write_text("installed", encoding="utf-8")
        (consumer / ".codex/agents").mkdir(parents=True)
        (consumer / ".codex/agents/professor-contact.toml").write_text(
            "name = 'professor-contact'", encoding="utf-8")
        producer_sha = "c" * 40
        research_sha = "d" * 40
        (consumer / "apm.lock.yaml").write_text(
            "dependencies:\n"
            f"  - name: professor-research\n    resolved_commit: {research_sha}\n"
            f"  - name: professor-contact\n    resolved_commit: {producer_sha}\n",
            encoding="utf-8")
        payload = verifier._checkpoint_install(self.args(
            consumer_root=consumer, producer_sha=producer_sha,
            professor_research_sha=research_sha))
        self.assertEqual(payload["status"], "pass", payload)

        payload = verifier._checkpoint_install(self.args(
            consumer_root=consumer, producer_sha="e" * 40,
            professor_research_sha=research_sha))
        self.assertEqual(payload["status"], "blocked")

    def test_install_cli_does_not_require_program_root(self):
        args = verifier._parser().parse_args(["--case", "install",
                                              "--consumer-root", "/tmp/consumer"])
        self.assertIsNone(args.program_root)


class AdapterGateTests(VerifierTestCase):
    def r1(self, adapter_path):
        return verifier._checkpoint_r1(self.args(adapter_evidence=adapter_path))

    def test_unreadable_adapter_is_invalid_evidence_and_never_pass(self):
        payload = self.r1(self.base / "missing.json")
        self.assertEqual(payload["status"], "invalid_evidence")

        bad = self.base / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.r1(bad)["status"], "invalid_evidence")

    def test_wrong_adapter_contract_is_invalid_evidence(self):
        path = self.write_adapter(adapter_payload(
            relations=[relation("root", ["a"]), relation("a", ["b"])],
            contract="skills-test-fixtures/codex-eval-adapter@8"))
        self.assertEqual(self.r1(path)["status"], "invalid_evidence")

    def test_missing_contract_declaration_is_invalid_evidence(self):
        path = self.write_adapter(adapter_payload(
            relations=[relation("root", ["a"]), relation("a", ["b"])], contract=None))
        self.assertEqual(self.r1(path)["status"], "invalid_evidence")

    def test_harness_failure_is_blocked_not_fail(self):
        for status in ("HARNESS_ERROR", "HARNESS_CONTAMINATION"):
            path = self.write_adapter(adapter_payload(
                relations=[relation("root", ["a"]), relation("a", ["b"])],
                fixture_status=status))
            self.assertEqual(self.r1(path)["status"], "blocked")

    def test_invalid_evidence_status_is_invalid_evidence(self):
        path = self.write_adapter(adapter_payload(
            relations=[relation("root", ["a"]), relation("a", ["b"])],
            fixture_status="INVALID_EVIDENCE"))
        self.assertEqual(self.r1(path)["status"], "invalid_evidence")

    def test_unobservable_delegation_is_not_tested_and_never_pass(self):
        # #17: an observability gap is never a pass and never a producer FAIL.
        path = self.write_adapter(adapter_payload(relations=[], delegation_state="unobservable"))
        payload = self.r1(path)
        self.assertEqual(payload["status"], "not_tested")

    def test_identity_mismatch_never_fails_confirmed_delegation(self):
        # #15: HARNESS_DISPATCH_MISMATCH is identity diagnostics only; with
        # the product state intact the case still passes outright.
        path = self.write_adapter(adapter_payload(
            relations=[relation("root", ["a"]), relation("a", ["b"])],
            fixture_status="HARNESS_DISPATCH_MISMATCH"))
        self.stage0_target()
        self.stage1_snapshot()
        payload = self.r1(path)
        self.assertEqual(payload["status"], "pass", payload)
        self.assertNotIn("adapter_delegation_confirmed",
                         {row["name"] for row in payload["checks"] if row["status"] == "fail"})

    def test_identity_unconfirmed_with_confirmed_delegation_continues(self):
        # #14: named-identity diagnostics never gate the run.
        path = self.write_adapter(adapter_payload(
            relations=[relation("root", ["a"]), relation("a", ["b"])],
            fixture_status="HARNESS_DISPATCH_UNCONFIRMED"))
        self.stage0_target()
        payload = self.r1(path)
        self.assertNotEqual(payload["status"], "not_tested")
        self.assertNotIn("adapter_delegation_confirmed",
                         {row["name"] for row in payload["checks"] if row["status"] == "fail"})


class R1CaseTests(VerifierTestCase):
    def test_r1_passes_with_formal_nesting_artifact_and_loader_consumption(self):
        self.stage0_target()
        self.stage1_snapshot()
        adapter = self.write_adapter(adapter_payload(
            relations=[relation("root", ["child-1"]), relation("child-1", ["grand-1"])],
            thread_id="root", children=["child-1", "grand-1"]))
        payload = verifier._checkpoint_r1(self.args(adapter_evidence=adapter))
        self.assertEqual(payload["status"], "pass", payload)

    def test_r1_requires_depth_two_formal_nesting(self):
        self.stage0_target()
        self.stage1_snapshot()
        adapter = self.write_adapter(adapter_payload(relations=[relation("root", ["child-1"])]))
        payload = verifier._checkpoint_r1(self.args(adapter_evidence=adapter))
        self.assertEqual(payload["status"], "fail")
        self.assertIn("nested_depth",
                      {row["name"] for row in payload["checks"] if row["status"] == "fail"})

    def test_r1_fails_without_stage1_artifact(self):
        self.stage0_target()
        adapter = self.write_adapter(adapter_payload(
            relations=[relation("root", ["a"]), relation("a", ["b"])]))
        payload = verifier._checkpoint_r1(self.args(adapter_evidence=adapter))
        self.assertEqual(payload["status"], "fail")

    def test_r1_is_blocked_when_fixture_provenance_is_stale(self):
        manifest_path = self.root / "fixture-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["item_keys"] = ["AAAA1111", "BBBB2222"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        payload = verifier._checkpoint_r1(self.args(
            adapter_evidence=self.nested_adapter()))
        self.assertEqual(payload["status"], "blocked")

    def test_r1_never_repairs_product_state(self):
        self.stage0_target()
        self.stage1_snapshot()
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*")
                        if path.is_file())
        payload = verifier._checkpoint_r1(self.args(adapter_evidence=self.nested_adapter()))
        self.assertEqual(payload["status"], "pass")
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*")
                       if path.is_file())
        self.assertEqual(before, after)


class R2CaseTests(VerifierTestCase):
    def stage2_pack(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        pack = {
            "schema": 2,
            "kind": "professor-contact-stage2-input",
            "identity_version": "direction-id-v1",
            "managed_by": "contact_state",
            "professor": "Example Professor",
            "professor_dir": str(prof),
            "papers": {key: {"item_key": key} for key in FIXTURE_CONFIG["item_keys"]},
            "directions": [{
                "direction_id": "DIR00001",
                "input_fingerprint": "direction-fingerprint",
                "supporting_item_keys": list(FIXTURE_CONFIG["item_keys"]),
            }],
        }
        (prof / "套磁候选输入.json").write_text(json.dumps(pack, ensure_ascii=False),
                                              encoding="utf-8")

    def stub_consumer(self):
        consumer = self.base / "consumer"
        scripts = consumer / ".agents/skills/professor-contact/scripts"
        scripts.mkdir(parents=True)
        (scripts / "contact_state.py").write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "assert '--direction-id' in sys.argv\n"
            "print(json.dumps({'jobs': [{'job_id': 'candidates:x:DIR00001',"
            " 'direction_id': 'DIR00001'}], 'reuse': [], 'skipped': []}))\n",
            encoding="utf-8")
        return consumer

    def deepest_adapter(self, name="deepest.json"):
        relations = [
            relation("root", ["l1"]),
            relation("l1", ["l2"]),
            relation("l2", ["l3"]),
        ]
        return self.write_adapter(adapter_payload(
            relations=relations, thread_id="root",
            children=["l1", "l2", "l3"]), name)

    def test_r2_passes_with_depth_three_pack_and_stage3_loader(self):
        self.stage2_pack()
        consumer = self.stub_consumer()
        payload = verifier._checkpoint_r2(self.args(
            adapter_evidence=self.deepest_adapter(), consumer_root=consumer))
        self.assertEqual(payload["status"], "pass", payload)

    def test_r2_requires_formal_depth_three(self):
        self.stage2_pack()
        consumer = self.stub_consumer()
        relations = [relation("root", ["l1"]), relation("l1", ["l2"])]
        payload = verifier._checkpoint_r2(self.args(
            adapter_evidence=self.write_adapter(adapter_payload(
                relations=relations, thread_id="root", children=["l1", "l2"])),
            consumer_root=consumer))
        self.assertEqual(payload["status"], "fail")

    def test_r2_fails_when_stage3_loader_cannot_consume(self):
        self.stage2_pack()
        consumer = self.base / "consumer"
        scripts = consumer / ".agents/skills/professor-contact/scripts"
        scripts.mkdir(parents=True)
        (scripts / "contact_state.py").write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "print(json.dumps({'jobs': [], 'reuse': ['DIR00001'], 'skipped': []}))\n",
            encoding="utf-8")
        payload = verifier._checkpoint_r2(self.args(
            adapter_evidence=self.deepest_adapter(), consumer_root=consumer))
        self.assertEqual(payload["status"], "fail")
        self.assertIn("stage3_loader_consumes_stage2_pack",
                      {row["name"] for row in payload["checks"] if row["status"] == "fail"})

    def test_r2_fails_without_stage2_pack(self):
        consumer = self.stub_consumer()
        payload = verifier._checkpoint_r2(self.args(
            adapter_evidence=self.deepest_adapter(), consumer_root=consumer))
        self.assertEqual(payload["status"], "fail")


class R3CaseTests(VerifierTestCase):
    def stage3_state(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        candidates = [{"id": f"idea-{index}", "kind": "direction",
                       "direction_ids": ["DIR00001"]} for index in range(3)]
        state = {
            "schema": 2,
            "kind": "professor-contact-stage3-state",
            "identity_version": "direction-id-v1",
            "generator_contract_version": "stage3-ideas-v2",
            "directions": [{"direction_id": "DIR00001", "candidates": candidates}],
            "candidates": candidates,
        }
        (prof / "套磁候选状态.json").write_text(json.dumps(state, ensure_ascii=False),
                                              encoding="utf-8")

    def sibling_adapter(self, children=("sib-a", "sib-b"), name="siblings.json"):
        relations = [relation("root", [child]) for child in children]
        return self.write_adapter(adapter_payload(
            relations=relations, thread_id="root",
            children=list(children)), name)

    def test_r3a_passes_with_two_root_siblings_and_canonical_state(self):
        self.stage3_state()
        payload = verifier._checkpoint_r3a(self.args(adapter_evidence=self.sibling_adapter()))
        self.assertEqual(payload["status"], "pass", payload)

    def test_r3a_requires_two_distinct_root_children(self):
        self.stage3_state()
        payload = verifier._checkpoint_r3a(self.args(
            adapter_evidence=self.sibling_adapter(children=("sib-a",))))
        self.assertEqual(payload["status"], "fail")
        self.assertIn("root_sibling_children",
                      {row["name"] for row in payload["checks"] if row["status"] == "fail"})

    def test_r3a_fails_without_stage3_state(self):
        payload = verifier._checkpoint_r3a(self.args(adapter_evidence=self.sibling_adapter()))
        self.assertEqual(payload["status"], "fail")

    def test_r3a_rejects_conflicting_formal_ownership(self):
        self.stage3_state()
        relations = [relation("root", ["sib-a"]), relation("root", ["sib-b"]),
                     relation("other-parent", ["sib-b"], )]
        payload = verifier._checkpoint_r3a(self.args(
            adapter_evidence=self.write_adapter(adapter_payload(
                relations=relations, thread_id="root",
                children=["sib-a", "sib-b"]))))
        self.assertEqual(payload["status"], "invalid_evidence")

    def test_r3_pre_omit_records_file_state_evidence(self):
        payload = verifier._checkpoint_r3_pre_omit(self.args(output=self.base / "pre.json"))
        self.assertEqual(payload["status"], "pass", payload)
        snapshot = payload["observed"]["snapshot"]
        self.assertFalse(snapshot["教授研究/套磁选择.json"]["exists"])
        self.assertFalse(snapshot["教授研究/邮件输入.json"]["exists"])

    def test_r3_pre_omit_fails_when_outputs_already_exist(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        (self.root / "教授研究/套磁选择.json").write_text("{}", encoding="utf-8")
        (prof / "邮件输入.json").write_text("{}", encoding="utf-8")
        payload = verifier._checkpoint_r3_pre_omit(self.args(output=self.base / "pre.json"))
        self.assertEqual(payload["status"], "fail")

    def write_pre_state(self, name="pre.json"):
        """Emulate main()'s verdict write for the pre-omit checkpoint."""
        pre = self.base / name
        payload = verifier._checkpoint_r3_pre_omit(self.args(output=pre))
        pre.write_text(json.dumps(payload), encoding="utf-8")
        return pre

    def test_r3b_passes_when_outputs_absent_before_and_after(self):
        pre = self.write_pre_state()
        adapter = self.write_adapter(adapter_payload(
            relations=[relation("root", ["child-1"]), relation("child-1", ["grand-1"])],
            thread_id="root", children=["child-1", "grand-1"]), "r3b.json")
        payload = verifier._checkpoint_r3b(self.args(
            pre_state=pre, adapter_evidence=adapter))
        self.assertEqual(payload["status"], "pass", payload)

    def test_r3b_fails_when_selection_appears_after_omit_run(self):
        pre = self.write_pre_state()
        (self.root / "教授研究/套磁选择.json").write_text("{}", encoding="utf-8")
        payload = verifier._checkpoint_r3b(self.args(
            pre_state=pre, adapter_evidence=self.nested_adapter("r3b.json")))
        self.assertEqual(payload["status"], "fail")
        self.assertIn("absent_after_omit:教授研究/套磁选择.json",
                      {row["name"] for row in payload["checks"] if row["status"] == "fail"})

    def test_r3b_requires_pre_state(self):
        payload = verifier._checkpoint_r3b(self.args(
            adapter_evidence=self.nested_adapter("r3b.json")))
        self.assertEqual(payload["status"], "fail")
        self.assertIn("pre_state_supplied",
                      {row["name"] for row in payload["checks"] if row["status"] == "fail"})

    def test_r3_omission_verdict_never_reads_assistant_prose(self):
        # #16: the omission boundary rests on file-state evidence only.  The
        # response carrying needs_input wording never flips the verdict in
        # either direction: with the outputs still absent the case passes
        # (covered conversely by the file-appears test above).
        pre = self.write_pre_state()
        adapter = self.write_adapter({
            **adapter_payload(relations=[relation("root", ["child-1"])],
                              thread_id="root", children=["child-1"]),
            "assistant_text": "needs_input: pending_selection 请选择候选",
        })
        payload = verifier._checkpoint_r3b(self.args(
            pre_state=pre, adapter_evidence=adapter))
        self.assertEqual(payload["status"], "pass", payload)


class R4CaseTests(VerifierTestCase):
    def stage4_outputs(self, idea_id="idea-alpha"):
        prof = self.root / "教授研究/X分野/Example Professor"
        selection = {"schema": 2, "selection": [{
            "professor": "Example Professor", "direction_ids": ["DIR00001"],
            "ideas": [{"id": idea_id}]}]}
        (self.root / "教授研究/套磁选择.json").write_text(
            json.dumps(selection, ensure_ascii=False), encoding="utf-8")
        email_pack = {"schema": 2, "kind": "professor-contact-email-input",
                      "identity_version": "direction-id-v1",
                      "emails": [{"email_id": f"Example Professor::DIR00001::{idea_id}",
                                  "direction_ids": ["DIR00001"]}]}
        (self.root / "教授研究/邮件输入.json").write_text(
            json.dumps(email_pack, ensure_ascii=False), encoding="utf-8")

    def selection_file(self, idea_id="idea-alpha"):
        path = self.base / "r4-selection.json"
        payload = {"selection": [{"professor": "Example Professor",
                                  "direction_ids": ["DIR00001"],
                                  "ideas": [{"id": idea_id}]}]}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_r4a_passes_when_product_selection_matches_input(self):
        self.stage4_outputs("idea-alpha")
        payload = verifier._checkpoint_r4a(self.args(
            selection_input=self.selection_file("idea-alpha"),
            adapter_evidence=self.nested_adapter("r4a.json")))
        self.assertEqual(payload["status"], "pass", payload)

    def test_r4a_fails_when_consumed_candidate_differs(self):
        self.stage4_outputs("idea-zeta")
        payload = verifier._checkpoint_r4a(self.args(
            selection_input=self.selection_file("idea-alpha"),
            adapter_evidence=self.nested_adapter("r4a.json")))
        self.assertEqual(payload["status"], "fail")
        self.assertIn("stage4_consumed_selection_matches_input",
                      {row["name"] for row in payload["checks"] if row["status"] == "fail"})

    def test_r4a_fails_without_stage4_outputs(self):
        payload = verifier._checkpoint_r4a(self.args(
            selection_input=self.selection_file(),
            adapter_evidence=self.nested_adapter("r4a.json")))
        self.assertEqual(payload["status"], "fail")

    def stage5_artifacts(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        for name in ("套磁邮件.md", "套磁跟进邮件.md", "套磁邮件.txt", "套磁跟进邮件.txt"):
            (prof / name).write_text("out", encoding="utf-8")
        (prof / "套磁邮件状态.json").write_text(json.dumps({
            "schema": 1, "emails": {"Example Professor::DIR00001::idea-alpha": {}}}),
            encoding="utf-8")

    def test_r4b_passes_with_nested_delegation_and_final_artifacts(self):
        self.stage5_artifacts()
        payload = verifier._checkpoint_r4b(self.args(
            adapter_evidence=self.nested_adapter("r4b.json")))
        self.assertEqual(payload["status"], "pass", payload)

    def test_r4b_requires_followup_artifacts(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        (prof / "套磁邮件.md").write_text("out", encoding="utf-8")
        (prof / "套磁邮件.txt").write_text("out", encoding="utf-8")
        (prof / "套磁邮件状态.json").write_text("{}", encoding="utf-8")
        payload = verifier._checkpoint_r4b(self.args(
            adapter_evidence=self.nested_adapter("r4b.json")))
        self.assertEqual(payload["status"], "fail")
        self.assertIn("followup_email_artifacts",
                      {row["name"] for row in payload["checks"] if row["status"] == "fail"})


class MakeStage4SelectionTests(VerifierTestCase):
    def stage3_state(self, candidates):
        prof = self.root / "教授研究/X分野/Example Professor"
        state = {
            "schema": 2,
            "kind": "professor-contact-stage3-state",
            "identity_version": "direction-id-v1",
            "generator_contract_version": "stage3-ideas-v2",
            "directions": [{"direction_id": "DIR00001", "candidates": candidates}],
            "candidates": candidates,
        }
        (prof / "套磁候选状态.json").write_text(json.dumps(state, ensure_ascii=False),
                                              encoding="utf-8")

    def select(self, **overrides):
        values = {
            "program_root": self.root,
            "output": self.base / "selection.json",
            "direction_id": "DIR00001",
            "selection_policy": "lexicographic-first-candidate-id",
            "first_choice": False,
            "signature_name": "Fixture Applicant",
            "learning": "I am studying reproducible research workflows.",
            "initial_sent_date": "2026-09-15",
        }
        values.update(overrides)
        return verifier._checkpoint_make_stage4_selection(Namespace(**values))

    def test_applies_frozen_lexicographic_first_policy(self):
        self.stage3_state([{"id": "zeta", "direction_ids": ["DIR00001"]},
                           {"id": "alpha", "direction_ids": ["DIR00001"]},
                           {"id": "beta", "direction_ids": ["DIR00001"]},
                           {"id": "other-direction", "direction_ids": ["DIR00002"]}])
        payload = self.select()
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["observed"]["selected_id"], "alpha")
        written = json.loads((self.base / "selection.json").read_text(encoding="utf-8"))
        self.assertEqual(written["selection_policy"], "lexicographic-first-candidate-id")
        self.assertEqual(written["selection"][0]["ideas"][0]["id"], "alpha")
        self.assertIs(written["first_choice"], False)
        self.assertEqual(written["signature_name"], "Fixture Applicant")
        self.assertEqual(written["learning"], "I am studying reproducible research workflows.")
        self.assertEqual(written["initial_sent_date"], "2026-09-15")

    def test_rejects_any_other_selection_policy(self):
        self.stage3_state([{"id": "alpha", "direction_ids": ["DIR00001"]}])
        payload = self.select(selection_policy="model-pick")
        self.assertEqual(payload["status"], "fail")

    def test_fails_without_candidates_in_direction(self):
        self.stage3_state([])
        payload = self.select()
        self.assertEqual(payload["status"], "fail")

    def test_writes_only_the_requested_output_file(self):
        self.stage3_state([{"id": "alpha", "direction_ids": ["DIR00001"]}])
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*")
                        if path.is_file())
        payload = self.select()
        self.assertEqual(payload["status"], "pass")
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*")
                       if path.is_file())
        self.assertEqual(before, after)

    def test_cli_flags_freeze_the_selection_inputs(self):
        args = verifier._parser().parse_args([
            "--make-stage4-selection",
            "--program-root", str(self.root),
            "--direction-id", "DIR00001",
            "--selection-policy", "lexicographic-first-candidate-id",
            "--first-choice", "false",
            "--signature-name", "Fixture Applicant",
            "--learning", "I am studying reproducible research workflows.",
            "--initial-sent-date", "2026-09-15",
            "--output", str(self.base / "selection.json")])
        self.assertTrue(args.make_stage4_selection)
        self.assertIsNone(args.case)
        self.assertEqual(args.selection_policy, "lexicographic-first-candidate-id")
        self.assertEqual(args.first_choice, "false")

    def test_exit_code_is_zero_only_for_pass(self):
        # #17: BLOCKED / NOT TESTED / INVALID_EVIDENCE never count as done.
        unobservable = self.write_adapter(adapter_payload(relations=[], delegation_state="unobservable"))
        self.assertEqual(verifier.main(["--case", "r1", "--program-root", str(self.root),
                                        "--adapter-evidence", str(unobservable)]), 1)
        missing = self.base / "missing-adapter.json"
        self.assertEqual(verifier.main(["--case", "r1", "--program-root", str(self.root),
                                        "--adapter-evidence", str(missing)]), 1)
        self.assertEqual(verifier.main(["--case", "r3-pre-omit", "--program-root", str(self.root),
                                        "--output", str(self.base / "pre.json")]), 0)


if __name__ == "__main__":
    unittest.main()
