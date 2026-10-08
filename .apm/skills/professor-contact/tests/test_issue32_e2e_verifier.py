import contextlib
import copy
import io
import importlib.util
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BUILDER_PATH = TESTS_DIR / "runtime/build_issue32_e2e_fixture.py"
VERIFIER_PATH = TESTS_DIR / "runtime/verify_issue32_e2e.py"
RUNTIME_DIR = TESTS_DIR / "runtime"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module("issue32_fixture_builder_for_verifier", BUILDER_PATH)
verifier = load_module("issue32_verifier", VERIFIER_PATH)

# Verdict selectors frozen in the issue #43 and issue #47 runtime recipes.  The
# check names live in the verifier, so the recipes stay decidable: #43 judges
# the choices feature only, while #47 final integration additionally requires a
# contract-valid terminal validator record and still never gates copy quality.
ISSUE43_STAGE5_CHECKS = (
    "choice_email_id_matches_pack", "choice_signature_rendered",
    "choice_learning_rendered", "choice_initial_sent_date_rendered",
    "choice_non_first_choice_branch_rendered", "email_entries_frozen_and_valid",
    "final_initial_exists", "final_followup_exists",
)
ISSUE47_INTEGRATION_CHECKS = ISSUE43_STAGE5_CHECKS + (
    "email_validator_terminal_records_valid",
)

# PC67-RISO is graded in-process: the frozen isolation preparer, the frozen
# Stage-4 eval-request builder, and the real Stage-4 producer CLI.  Nothing in
# this file starts Codex; the eval request is only checked as a command surface.
ISSUE67_PREPARER_PATH = RUNTIME_DIR / "prepare_issue67_stage4_isolation_fixture.py"
ISSUE67_PROMPT_PATH = RUNTIME_DIR / "prompts" / "issue67-stage4-isolation.txt"
PRODUCER_PATH = TESTS_DIR.parent / "scripts" / "contact_state.py"
issue67_fixture = load_module(
    "issue67_stage4_isolation_fixture_for_verifier", ISSUE67_PREPARER_PATH)
issue67_request = load_module(
    "issue67_stage4_eval_request_builder_for_verifier",
    RUNTIME_DIR / "build_issue67_eval_request.py",
)
PRODUCER_SHA = "c" * 40
FIXTURE_SHA = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
CHILD_THREAD_ID = "child-selection-1"
# The claims PASS_TARGET must prove directly from bytes and formal relations
# (issue #67 Gate 2 §4); none of them may be inferred from model prose.
ISSUE67_PROVEN_GATES = (
    "install_verdict_pass", "install_verdict_pinned_producer_sha",
    "install_provenance_rederived", "formal_root_child",
    "fixture_inputs_unchanged", "fault_professor_bytes_unchanged",
    "program_level_pair_unchanged", "no_program_level_pair_rewritten",
    "valid_professor_local_pair_written",
    "valid_professor_pair_is_professor_local_schema",
    "valid_professor_pair_bound_to_canonical_professor_dir",
    "valid_professor_pair_carries_current_profile_fingerprint",
    "valid_professor_selection_matches_this_request_and_current_state",
    "valid_professor_email_pack_matches_current_facts",
    "legacy_program_pair_not_promoted_into_local_authority",
    "fault_professor_local_pair_absent",
    "stage4_pair_written_only_where_the_contract_allows",
)
# A non-canonical Stage-2 input pack: the fault shape the counterexample
# preparer swaps in for the frozen candidate-state fault.
NON_CANONICAL_INPUT_PACK_BYTES = (
    b'{\n  "schema": 2,\n  "kind": "professor-contact-stage2-input",\n'
    b'  "identity_version": "direction-id-v0-not-canonical",\n  "directions": []\n}\n'
)
GENERATOR_TOML = (
    'name = "professor-contact-email-generator"\n'
    'description = "Stage 5 email generator"\n'
    'developer_instructions = """## Stage 5 caller Input contract\n'
    'choices canonical JSON email_id first_choice signature_name learning '
    'initial_sent_date --choices\n### Codex branch\npreserve choices unchanged\n'
    '### humanizer-ja stage-5 constraints\n"""\n'
)


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
        self.assertFalse((self.root / "教授研究/X分野/Example Professor/套磁目标.json").exists())
        self.assertFalse((self.root / "教授研究/套磁目标.json").exists())

    def test_stage1_final_accepts_runtime_item_key_from_manifest(self):
        root = Path(self.holder.name) / "dynamic-program"
        profile = Path(self.holder.name) / "dynamic-profile"
        item_key = "RT999999"
        builder.build_fixture(root, profile, item_key=item_key)

        prof = root / "教授研究/X分野/Example Professor"
        papers_path = prof / "papers.json"
        papers = json.loads(papers_path.read_text(encoding="utf-8"))
        self.assertEqual([row["item_key"] for row in papers["papers"]], [item_key])
        papers["papers"][0]["pdf_status"] = "downloaded"
        papers_path.write_text(json.dumps(papers), encoding="utf-8")

        (prof / "套磁阶段1候选.json").write_text(json.dumps({
            "schema_version": 2,
            "kind": "professor-contact-stage1",
            "professor": "Example Professor",
            "directions": [{
                "direction_id": "DIR00001",
                "candidate_keys": [item_key],
                "pdf_readiness": {
                    "usable_item_keys": [item_key],
                    "missing_item_keys": [],
                },
            }],
        }), encoding="utf-8")
        response = Path(self.holder.name) / "dynamic-r1-response.json"
        response.write_text(json.dumps({
            "collector_payload": {
                "folder_path": str(root),
                "pdf_only": True,
                "item_keys": [item_key],
            },
        }), encoding="utf-8")

        payload = verifier._checkpoint_stage1_final(
            self.args(program_root=root, eval_response=response))
        self.assertEqual(payload["status"], "pass", payload)

    def test_stage1_final_rejects_a_second_candidate_outside_the_canonical_item(self):
        """The one-item collapse means a second key is a contract violation."""
        root = Path(self.holder.name) / "two-key-program"
        profile = Path(self.holder.name) / "two-key-profile"
        item_key = "RT999999"
        builder.build_fixture(root, profile, item_key=item_key)

        prof = root / "教授研究/X分野/Example Professor"
        papers_path = prof / "papers.json"
        papers = json.loads(papers_path.read_text(encoding="utf-8"))
        papers["papers"][0]["pdf_status"] = "downloaded"
        papers["papers"].append({"item_key": "OTHER1111", "pdf_status": "downloaded"})
        papers_path.write_text(json.dumps(papers), encoding="utf-8")
        (prof / "套磁阶段1候选.json").write_text(json.dumps({
            "schema_version": 2,
            "kind": "professor-contact-stage1",
            "professor": "Example Professor",
            "directions": [{
                "direction_id": "DIR00001",
                "candidate_keys": [item_key, "OTHER1111"],
                "pdf_readiness": {
                    "usable_item_keys": [item_key, "OTHER1111"],
                    "missing_item_keys": [],
                },
            }],
        }), encoding="utf-8")

        payload = verifier._checkpoint_stage1_final(self.args(program_root=root))

        self.assertEqual(payload["status"], "fail", payload)
        names = {row["name"]: row["status"] for row in payload["checks"]}
        self.assertEqual(names.get("snapshot_members"), "fail", names)
        self.assertEqual(names.get("pdf_readiness"), "fail", names)

    def test_stage1_final_accepts_noop_without_collector_payload_when_pdf_ready(self):
        root = Path(self.holder.name) / "noop-program"
        profile = Path(self.holder.name) / "noop-profile"
        item_key = "RT999999"
        builder.build_fixture(root, profile, item_key=item_key)

        prof = root / "教授研究/X分野/Example Professor"
        papers_path = prof / "papers.json"
        papers = json.loads(papers_path.read_text(encoding="utf-8"))
        papers["papers"][0]["pdf_status"] = "downloaded"
        papers_path.write_text(json.dumps(papers), encoding="utf-8")

        (prof / "套磁阶段1候选.json").write_text(json.dumps({
            "schema_version": 2,
            "kind": "professor-contact-stage1",
            "professor": "Example Professor",
            "directions": [{
                "direction_id": "DIR00001",
                "candidate_keys": [item_key],
                "pdf_readiness": {
                    "usable_item_keys": [item_key],
                    "missing_item_keys": [],
                },
            }],
        }), encoding="utf-8")
        response = Path(self.holder.name) / "noop-r1-response.json"
        response.write_text(json.dumps({
            "stage1_result": {
                "action": "noop",
                "papers_pdf_downloaded": 1,
            },
        }), encoding="utf-8")

        payload = verifier._checkpoint_stage1_final(
            self.args(program_root=root, eval_response=response))
        self.assertEqual(payload["status"], "pass", payload)

    def test_initial_rejects_pre_ready_catalog_or_prebuilt_local_pdf(self):
        """R1 must be the step that fills the single canonical item."""
        prof = self.root / "教授研究/X分野/Example Professor"
        papers_path = prof / "papers.json"
        original_papers = papers_path.read_text(encoding="utf-8")
        papers = json.loads(original_papers)
        papers["papers"][0]["pdf_status"] = "downloaded"
        papers["papers"][0]["pdf_path"] = "论文分析/AAAA1111.pdf"
        papers_path.write_text(json.dumps(papers), encoding="utf-8")
        (prof / "论文分析/AAAA1111.pdf").write_bytes(b"%PDF-1.4\n")

        payload = verifier._checkpoint_initial(self.args())

        names = {row["name"]: row["status"] for row in payload["checks"]}
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(names.get("catalog_pdf_pending"), "fail", names)
        self.assertEqual(names.get("no_prebuilt_local_pdf"), "fail", names)
        papers_path.write_text(original_papers, encoding="utf-8")
        (prof / "论文分析/AAAA1111.pdf").unlink()
        self.assertEqual(verifier._checkpoint_initial(self.args())["status"], "pass")

    def test_initial_rejects_a_two_item_manifest(self):
        manifest_path = self.root / "fixture-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["item_keys"] = ["AAAA1111", "BBBB2222"]
        manifest["canonical_item_key"] = "AAAA1111"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        payload = verifier._checkpoint_initial(self.args())

        names = {row["name"]: row["status"] for row in payload["checks"]}
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(names.get("item_keys"), "fail", names)

    def test_install_reads_exact_professor_contact_commit_from_structured_lock(self):
        consumer = Path(self.holder.name) / "consumer"
        for relative in (*verifier.INSTALL_REQUIRED_FILES,
                         ".codex/agents/professor-contact-email-generator.toml"):
            path = consumer / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("installed", encoding="utf-8")
        (consumer / ".codex/agents/professor-contact-email-generator.toml").write_text(
            'name = "professor-contact-email-generator"\n'
            'description = "Stage 5 email generator"\n'
            'developer_instructions = """## Stage 5 caller Input contract\n'
            'choices canonical JSON email_id first_choice signature_name learning initial_sent_date --choices\n'
            '### Codex branch\npreserve choices unchanged\n'
            '### humanizer-ja stage-5 constraints\n"""\n',
            encoding="utf-8",
        )
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

    def test_install_requires_every_pc55_runtime_asset(self):
        required_surfaces = {
            ".agents/skills/professor-contact/scripts/contact_state.py",
            ".codex/agents/professor-contact-idea-generator.toml",
            ".codex/agents/professor-contact-style-validator.toml",
        }
        self.assertTrue(required_surfaces.issubset(set(verifier.INSTALL_REQUIRED_FILES)))
        consumer = Path(self.holder.name) / "consumer-assets"
        for relative in (*verifier.INSTALL_REQUIRED_FILES,
                         ".codex/agents/professor-contact-email-generator.toml"):
            path = consumer / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("installed", encoding="utf-8")
        (consumer / ".codex/agents/professor-contact-email-generator.toml").write_text(
            'name = "professor-contact-email-generator"\n'
            'description = "Stage 5 email generator"\n'
            'developer_instructions = """## Stage 5 caller Input contract\n'
            'choices canonical JSON email_id first_choice signature_name learning initial_sent_date --choices\n'
            '### Codex branch\npreserve choices unchanged\n'
            '### humanizer-ja stage-5 constraints\n"""\n',
            encoding="utf-8",
        )
        producer_sha = "c" * 40
        (consumer / "apm.lock.yaml").write_text(
            "dependencies:\n"
            "  - name: professor-contact\n"
            f"    resolved_commit: {producer_sha}\n",
            encoding="utf-8",
        )
        payload = verifier._checkpoint_install(self.args(
            consumer_root=consumer, producer_sha=producer_sha))
        self.assertEqual(payload["status"], "pass", payload)

        missing = consumer / ".agents/skills/professor-contact/tests/runtime/build_issue55_eval_request.py"
        missing.unlink()
        payload = verifier._checkpoint_install(self.args(
            consumer_root=consumer, producer_sha=producer_sha))
        self.assertEqual(payload["status"], "fail", payload)
        self.assertTrue(any(
            row["name"].endswith("build_issue55_eval_request.py")
            and row["status"] == "fail"
            for row in payload["checks"]
        ))

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

    def test_make_stage4_selection_cli_alias_accepts_only_stage4_fields(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        (prof / "套磁候选状态.json").write_text(json.dumps({
            "schema_version": 2,
            "directions": [{"direction_id": "DIR00001"}],
            "candidates": [{"id": "alpha"}, {"id": "beta"}],
        }), encoding="utf-8")
        output = Path(self.holder.name) / "selection.json"
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = verifier.main([
                "--make-stage4-selection", "--program-root", str(self.root),
                "--direction-id", "DIR00001",
                "--selection-policy", "lexicographic-first-candidate-id",
                "--output", str(output),
            ])
        self.assertEqual(exit_code, 0)
        selected = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(selected["selection"][0]["ideas"][0]["id"], "alpha")
        self.assertNotIn("first_choice", json.dumps(selected))
        self.assertNotIn("signature_name", json.dumps(selected))
        self.assertNotIn("learning", json.dumps(selected))
        self.assertNotIn("initial_sent_date", json.dumps(selected))

    def test_stage4_final_reads_program_level_outputs(self):
        stage4_root = self.root / "教授研究"
        prof = stage4_root / "X分野/Example Professor"
        email_id = "Example Professor::DIR00001::idea-1"
        (stage4_root / "套磁选择.json").write_text(json.dumps({
            "selection": [{"professor": "Example Professor",
                           "direction_ids": ["DIR00001"], "ideas": [{"id": "idea-1"}]}]
        }), encoding="utf-8")
        (stage4_root / "邮件输入.json").write_text(json.dumps({
            "schema": 2, "kind": "professor-contact-email-input",
            "identity_version": "direction-id-v1",
            "emails": [{
                "email_id": email_id,
                "contact_evidence": {
                    "record_fingerprint": "evidence",
                    "record": {"email": "example@example.edu"},
                },
            }]
        }), encoding="utf-8")

        payload = verifier._checkpoint_stage4_final(self.args())
        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(payload["observed"]["selection_file"],
                         str((stage4_root / "套磁选择.json").resolve()))
        self.assertFalse((prof / "套磁选择.json").exists())

    def test_stage5_pristine_requires_stage4_outputs_and_no_final_state(self):
        stage4_root = self.root / "教授研究"
        prof = stage4_root / "X分野/Example Professor"
        email_id = "Example Professor::DIR00001::idea-1"
        (stage4_root / "套磁选择.json").write_text(json.dumps({
            "selection": [{"professor": "Example Professor",
                           "direction_ids": ["DIR00001"], "ideas": [{"id": "idea-1"}]}]
        }), encoding="utf-8")
        (stage4_root / "邮件输入.json").write_text(json.dumps({
            "schema": 2, "kind": "professor-contact-email-input",
            "identity_version": "direction-id-v1",
            "emails": [{"email_id": email_id}]
        }), encoding="utf-8")

        payload = verifier._checkpoint_stage5_pristine(self.args())
        self.assertEqual(payload["status"], "pass", payload)

        (prof / "套磁邮件状态.json").write_text("{}", encoding="utf-8")
        payload = verifier._checkpoint_stage5_pristine(self.args())
        self.assertEqual(payload["status"], "fail", payload)

    def test_make_stage5_choices_reads_the_real_email_id_and_writes_only_requested_file(self):
        stage4_root = self.root / "教授研究"
        prof = stage4_root / "X分野/Example Professor"
        email_id = "Example Professor::DIR00001::idea-1"
        (stage4_root / "邮件输入.json").write_text(json.dumps({
            "schema": 2, "kind": "professor-contact-email-input",
            "emails": [{"email_id": email_id}]
        }), encoding="utf-8")
        output = Path(self.holder.name) / "stage5-choices.json"
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))

        payload = verifier._checkpoint_make_stage5_choices(self.args(output=output))

        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {
            "email_id": email_id,
            "first_choice": False,
            "signature_name": "Fixture Applicant",
            "learning": "I am studying reproducible research workflows.",
            "initial_sent_date": "2026-09-15",
        })
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        self.assertEqual(before, after)

    def test_make_stage5_choices_cli_keeps_canonical_choices_in_output_file(self):
        stage4_root = self.root / "教授研究"
        email_id = "Example Professor::DIR00001::idea-1"
        (stage4_root / "邮件输入.json").write_text(json.dumps({
            "schema": 2, "kind": "professor-contact-email-input",
            "emails": [{"email_id": email_id}],
        }), encoding="utf-8")
        output = Path(self.holder.name) / "stage5-choices.json"
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = verifier.main([
                "make-stage5-choices",
                "--program-root", str(self.root),
                "--output", str(output),
            ])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {
            "email_id": email_id,
            "first_choice": False,
            "signature_name": "Fixture Applicant",
            "learning": "I am studying reproducible research workflows.",
            "initial_sent_date": "2026-09-15",
        })
        evidence = json.loads(stdout.getvalue())
        self.assertEqual(evidence["status"], "pass", evidence)
        self.assertEqual(evidence["observed"]["payload"]["email_id"], email_id)

    def test_stage5_snapshot_records_fixed_artifacts_without_writing(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))

        payload = verifier._checkpoint_stage5_snapshot(self.args())

        self.assertEqual(payload["status"], "pass", payload)
        self.assertEqual(set(payload), {"status", "observed"})
        artifacts = payload["observed"]["artifacts"]
        expected = {
            "教授研究/X分野/Example Professor/套磁邮件.md",
            "教授研究/X分野/Example Professor/套磁邮件.txt",
            "教授研究/X分野/Example Professor/套磁跟进邮件.md",
            "教授研究/X分野/Example Professor/套磁跟进邮件.txt",
            "教授研究/X分野/Example Professor/套磁邮件状态.json",
        }
        self.assertEqual(set(artifacts), expected)
        self.assertTrue(all(item == {"exists": False, "sha256": None}
                            for item in artifacts.values()))

        initial = prof / "套磁邮件.md"
        initial.write_text("rendered", encoding="utf-8")
        payload = verifier._checkpoint_stage5_snapshot(self.args())
        key = "教授研究/X分野/Example Professor/套磁邮件.md"
        self.assertEqual(payload["observed"]["artifacts"][key], {
            "exists": True, "sha256": verifier._sha256(initial),
        })
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        self.assertEqual(after, sorted(before + [key]))

    def _seed_stage5_final_outputs(self):
        """Seed the canonical issue-43 Stage 5 outputs and matching state."""
        stage4_root = self.root / "教授研究"
        prof = stage4_root / "X分野/Example Professor"
        email_id = "Example Professor::DIR00001::idea-1"
        source_hash = "pack-source"
        (stage4_root / "邮件输入.json").write_text(json.dumps({
            "schema": 2, "kind": "professor-contact-email-input",
            "identity_version": "direction-id-v1",
            "emails": [{
                "email_id": email_id, "source_hash": source_hash,
                "contact_evidence": {
                    "record_fingerprint": "evidence",
                    "record": {"email": "example@example.edu"},
                },
            }],
        }), encoding="utf-8")
        choices = {
            "email_id": email_id,
            "first_choice": False,
            "signature_name": "Fixture Applicant",
            "learning": "I am studying reproducible research workflows.",
            "initial_sent_date": "2026-09-15",
        }
        (prof / "套磁邮件状态.json").write_text(json.dumps({
            "schema": 1,
            "emails": {email_id: {
                "input_fingerprint": source_hash,
                "choices": choices,
                "validation": {"result": "pass", "rounds": 1, "issues": []},
                "followup": {
                    "choices": choices,
                    "validation": {"result": "pass", "rounds": 1, "issues": []},
                },
            }},
        }), encoding="utf-8")
        (prof / "套磁邮件.md").write_text("送信前核对", encoding="utf-8")
        (prof / "套磁邮件.txt").write_text(
            "Fixture University B出身のFixture Applicant（2026年4月、"
            "Adaptive and nonlinear processing、Master of Science）です。\n"
            "I am studying reproducible research workflows. "
            "先生の研究室を志望として出願させていただきたく存じます\n",
            encoding="utf-8")
        (prof / "套磁跟进邮件.md").write_text("送信前核对", encoding="utf-8")
        (prof / "套磁跟进邮件.txt").write_text(
            "Master of ScienceのFixture Applicantです。Fixture University B出身で、"
            "2026-09-15に初回連絡しました。\n",
            encoding="utf-8")
        return email_id

    def test_stage5_final_exposes_fixed_choice_wiring_checks(self):
        self._seed_stage5_final_outputs()

        payload = verifier._checkpoint_stage5_final(self.args())

        self.assertEqual(payload["status"], "pass", payload)
        names = {row["name"]: row["status"] for row in payload["checks"]}
        for name in (
            "choice_email_id_matches_pack", "choice_signature_rendered",
            "choice_learning_rendered", "choice_initial_sent_date_rendered",
            "choice_non_first_choice_branch_rendered", "final_initial_exists",
            "final_followup_exists", "email_entries_frozen_and_valid",
            "email_validator_result_pass",
        ):
            self.assertEqual(names.get(name), "pass", names)

    def _set_stage5_validations(self, initial, followup):
        """Re-seed Stage 5 outputs and overwrite the two validator records."""
        email_id = self._seed_stage5_final_outputs()
        prof = self.root / "教授研究/X分野/Example Professor"
        state = json.loads((prof / "套磁邮件状态.json").read_text(encoding="utf-8"))
        entry = state["emails"][email_id]
        if initial is None:
            entry.pop("validation", None)
        else:
            entry["validation"] = initial
        if followup is None:
            entry.get("followup", {}).pop("validation", None)
        else:
            entry["followup"]["validation"] = followup
        (prof / "套磁邮件状态.json").write_text(json.dumps(state), encoding="utf-8")
        return self.args()

    def test_stage5_final_separates_terminal_validator_record_from_copy_quality(self):
        """#40: a legal non-pass terminal record is diagnostics, not a missing run."""
        scenarios = [
            # (initial, followup, terminal-valid, result-pass)
            ({"result": "pass", "rounds": 1, "issues": []},
             {"result": "pass", "rounds": 2, "issues": []}, "pass", "pass"),
            ({"result": "fail_after_2_rounds", "rounds": 2, "issues": ["wording"]},
             {"result": "fail_after_2_rounds", "rounds": 2, "issues": ["wording"]},
             "pass", "fail"),
            ({"result": "skipped", "rounds": 0, "issues": []},
             {"result": "skipped", "rounds": 0, "issues": []}, "pass", "fail"),
        ]
        for initial, followup, terminal, result in scenarios:
            with self.subTest(initial=initial["result"], rounds=initial["rounds"]):
                payload = verifier._checkpoint_stage5_final(
                    self._set_stage5_validations(initial, followup))
                names = {row["name"]: row["status"] for row in payload["checks"]}
                self.assertEqual(names.get("email_validator_terminal_records_valid"),
                                 terminal, payload)
                self.assertEqual(names.get("email_validator_result_pass"), result, payload)
                # Freezing contact evidence/source is its own machine fact and
                # never follows the validator lifecycle.
                self.assertEqual(names.get("email_entries_frozen_and_valid"), "pass",
                                 payload)

    def test_stage5_final_rejects_missing_malformed_or_illegal_terminal_records(self):
        illegal_rounds = {"result": "pass", "rounds": 5, "issues": []}
        cases = [
            ("missing initial", None, {"result": "pass", "rounds": 1, "issues": []}),
            ("missing followup", {"result": "pass", "rounds": 1, "issues": []}, None),
            ("unknown result", {"result": "needs_review", "rounds": 1, "issues": []},
             {"result": "pass", "rounds": 1, "issues": []}),
            ("non-list issues", {"result": "pass", "rounds": 1, "issues": "bad"},
             {"result": "pass", "rounds": 1, "issues": []}),
            ("illegal rounds", illegal_rounds,
             {"result": "pass", "rounds": 1, "issues": []}),
            ("fail_after_2_rounds with 1 round",
             {"result": "fail_after_2_rounds", "rounds": 1, "issues": ["x"]},
             {"result": "pass", "rounds": 1, "issues": []}),
        ]
        for label, initial, followup in cases:
            with self.subTest(case=label):
                payload = verifier._checkpoint_stage5_final(
                    self._set_stage5_validations(initial, followup))
                names = {row["name"]: row["status"] for row in payload["checks"]}
                self.assertEqual(payload["status"], "fail", payload)
                self.assertEqual(names.get("email_validator_terminal_records_valid"),
                                 "fail", names)
                self.assertEqual(names.get("email_validator_result_pass"), "fail", names)
                self.assertEqual(names.get("email_entries_frozen_and_valid"), "pass",
                                 names)

    def test_fixed_issue43_and_issue47_selectors_stay_apart(self):
        """#43 never gates copy quality; #47 integration requires the terminal record."""
        self.assertEqual(ISSUE43_STAGE5_CHECKS, (
            "choice_email_id_matches_pack", "choice_signature_rendered",
            "choice_learning_rendered", "choice_initial_sent_date_rendered",
            "choice_non_first_choice_branch_rendered", "email_entries_frozen_and_valid",
            "final_initial_exists", "final_followup_exists",
        ))
        self.assertNotIn("email_validator_result_pass", ISSUE43_STAGE5_CHECKS)
        self.assertNotIn("email_validator_terminal_records_valid", ISSUE43_STAGE5_CHECKS)
        self.assertIn("email_validator_terminal_records_valid",
                      ISSUE47_INTEGRATION_CHECKS)
        self.assertNotIn("email_validator_result_pass", ISSUE47_INTEGRATION_CHECKS)
        self._seed_stage5_final_outputs()
        names = {row["name"] for row in
                 verifier._checkpoint_stage5_final(self.args())["checks"]}
        self.assertTrue(set(ISSUE47_INTEGRATION_CHECKS).issubset(names), names)

    def test_stage5_final_rejects_state_and_output_tampered_together(self):
        """Self-consistent state/output tampering must not read as a pass."""
        prof = self.root / "教授研究/X分野/Example Professor"
        self._seed_stage5_final_outputs()
        state = json.loads((prof / "套磁邮件状态.json").read_text(encoding="utf-8"))
        entry = next(iter(state["emails"].values()))
        entry["choices"]["first_choice"] = True
        entry["choices"]["signature_name"] = "Tampered Applicant"
        entry["choices"]["learning"] = "I am studying something else."
        entry["followup"]["choices"]["first_choice"] = True
        entry["followup"]["choices"]["initial_sent_date"] = "2026-01-01"
        (prof / "套磁邮件状态.json").write_text(json.dumps(state), encoding="utf-8")
        (prof / "套磁邮件.txt").write_text(
            "Fixture University B出身のTampered Applicant（2026年4月、"
            "Adaptive and nonlinear processing、Master of Science）です。\n"
            "I am studying something else. "
            "先生の研究室を第一志望として出願させていただきたく存じます\n",
            encoding="utf-8")
        (prof / "套磁跟进邮件.txt").write_text(
            "Master of ScienceのTampered Applicantです。Fixture University B出身で、"
            "2026-01-01に初回連絡しました。\n",
            encoding="utf-8")

        payload = verifier._checkpoint_stage5_final(self.args())

        self.assertEqual(payload["status"], "fail", payload)
        names = {row["name"]: row["status"] for row in payload["checks"]}
        for name in ("choice_signature_rendered", "choice_learning_rendered",
                     "choice_initial_sent_date_rendered",
                     "choice_non_first_choice_branch_rendered"):
            self.assertEqual(names.get(name), "fail", names)
        self.assertEqual(names.get("choice_email_id_matches_pack"), "pass", names)

    def test_stage5_final_rejects_sentinel_at_wrong_template_slot(self):
        """A sentinel still present but off its §6.4 slot must fail its check."""
        prof = self.root / "教授研究/X分野/Example Professor"
        scenarios = [
            ("套磁邮件.txt",
             "Fixture University B出身の（2026年4月、Adaptive and nonlinear processing、"
             "Master of Science）です。\n"
             "I am studying reproducible research workflows. "
             "先生の研究室を志望として出願させていただきたく存じます Fixture Applicant\n",
             "choice_signature_rendered"),
            ("套磁邮件.txt",
             "Fixture University B出身のFixture Applicant（2026年4月、"
             "Adaptive and nonlinear processing、Master of Science）です。 "
             "I am studying reproducible research workflows.\n"
             "先生の研究室を志望として出願させていただきたく存じます\n",
             "choice_learning_rendered"),
            ("套磁跟进邮件.txt",
             "Master of ScienceのFixture Applicantです。Fixture University B出身で、"
             "初回連絡しました（2026-09-15）。\n",
             "choice_initial_sent_date_rendered"),
        ]
        render_checks = ("choice_signature_rendered", "choice_learning_rendered",
                         "choice_initial_sent_date_rendered")
        for filename, text, expected_fail in scenarios:
            with self.subTest(check=expected_fail):
                self._seed_stage5_final_outputs()
                (prof / filename).write_text(text, encoding="utf-8")

                payload = verifier._checkpoint_stage5_final(self.args())

                self.assertEqual(payload["status"], "fail", payload)
                names = {row["name"]: row["status"] for row in payload["checks"]}
                for name in render_checks:
                    expected = "fail" if name == expected_fail else "pass"
                    self.assertEqual(names.get(name), expected, names)
                self.assertEqual(names.get("choice_email_id_matches_pack"), "pass", names)
                self.assertEqual(
                    names.get("choice_non_first_choice_branch_rendered"), "pass", names)

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

    def test_stage2_requires_analysis_of_the_canonical_item_not_a_substitute(self):
        """R2 must analyze the paper R1 filled, so a substitute key cannot pass."""
        root = Path(self.holder.name) / "stage2-program"
        profile = Path(self.holder.name) / "stage2-profile"
        item_key = "RT999999"
        builder.build_fixture(root, profile, item_key=item_key)
        prof = root / "教授研究/X分野/Example Professor"
        (prof / "套磁候选输入.json").write_text(json.dumps({
            "schema": 2,
            "kind": "professor-contact-stage2-input",
            "identity_version": "direction-id-v1",
            "managed_by": "contact_state",
            "professor": "Example Professor",
            "professor_dir": str(prof),
            "papers": {item_key: {"item_key": item_key}},
            "directions": [{
                "direction_id": "DIR00001",
                "input_fingerprint": "direction-fingerprint",
                "supporting_item_keys": [item_key],
            }],
        }), encoding="utf-8")
        (prof / "论文分析/RT000000.md").write_text("analysis of another paper",
                                                   encoding="utf-8")
        (prof / "论文分析/RT000000.future_work.json").write_text("{}", encoding="utf-8")

        payload = verifier._checkpoint_stage2_final(self.args(program_root=root))

        names = {row["name"]: row["status"] for row in payload["checks"]}
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(names.get("analysis_for_canonical_paper"), "fail", names)
        self.assertEqual(names.get("future_work_sidecar"), "fail", names)

        (prof / "论文分析/RT999999.md").write_text("analysis", encoding="utf-8")
        (prof / "论文分析/RT999999.future_work.json").write_text("{}", encoding="utf-8")
        self.assertEqual(
            verifier._checkpoint_stage2_final(self.args(program_root=root))["status"],
            "pass")

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
        stage4_root = self.root / "教授研究"
        prof = self.root / "教授研究/X分野/Example Professor"
        (prof / "套磁邮件.md").write_text("送信前核对", encoding="utf-8")
        (prof / "套磁跟进邮件.md").write_text("送信前核对", encoding="utf-8")
        (prof / "套磁邮件.txt").write_text(
            "Fixture University B出身のFixture Applicant（2026年4月、Adaptive and nonlinear processing、"
            "Master of Science）です。I am studying reproducible research workflows. "
            "先生の研究室を志望として出願させていただきたく存じます", encoding="utf-8")
        (prof / "套磁跟进邮件.txt").write_text(
            "Master of ScienceのFixture Applicantです。Fixture University B出身で、"
            "2026-09-15に初回連絡しました。", encoding="utf-8")
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
        (stage4_root / "邮件输入.json").write_text(json.dumps(email_pack), encoding="utf-8")
        choices = {
            "email_id": email_id,
            "first_choice": False,
            "signature_name": "Fixture Applicant",
            "learning": "I am studying reproducible research workflows.",
            "initial_sent_date": "2026-09-15",
        }
        email_state = {
            "schema": 1,
            "emails": {email_id: {
                "input_fingerprint": "source-fingerprint",
                "choices": choices,
                "validation": {"result": "fail_after_2_rounds", "rounds": 2, "issues": ["bad"]},
                "followup": {"choices": choices, "validation": {
                    "result": "fail_after_2_rounds", "rounds": 2, "issues": ["bad"]}},
            }},
        }
        state_path = prof / "套磁邮件状态.json"
        state_path.write_text(json.dumps(email_state), encoding="utf-8")
        payload = verifier._checkpoint_stage5_final(self.args())
        self.assertEqual(payload["status"], "fail", payload)
        # The unchanged downstream validator's copy quality stays separate
        # evidence: it fails here, while the frozen/source invariant and every
        # issue-43 choices check still pass so the #43 verdict stays decidable.
        names = {row["name"]: row["status"] for row in payload["checks"]}
        self.assertEqual(names.get("email_validator_result_pass"), "fail", names)
        self.assertEqual(names.get("email_entries_frozen_and_valid"), "pass", names)
        for name in ("choice_email_id_matches_pack", "choice_signature_rendered",
                     "choice_learning_rendered", "choice_initial_sent_date_rendered",
                     "choice_non_first_choice_branch_rendered"):
            self.assertEqual(names.get(name), "pass", names)

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
            "fixture_status": "FIXTURE_READY",
            "delegation": {
                "state": "confirmed",
                "basis": ["formal_spawn_relation"],
                "formal_child_count": 2,
                "child_thread_ids": ["downloader", "analyzer"],
            },
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "contact", "parent_thread_id": "contact",
                 "receiver_thread_ids": ["downloader"]},
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "downloader", "parent_thread_id": "downloader",
                 "receiver_thread_ids": ["analyzer"]},
                {"tool": "wait", "status": "completed",
                 "sender_thread_id": "contact", "parent_thread_id": "contact",
                 "receiver_thread_ids": ["analyzer"]},
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
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "confirmed", "basis": ["formal_spawn_relation"],
                            "child_thread_ids": ["c1", "c2"]},
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "p1", "parent_thread_id": "p1",
                 "receiver_thread_ids": ["c1"]},
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "p2", "parent_thread_id": "p2",
                 "receiver_thread_ids": ["c2"]},
            ]},
        }), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(
            self.args(adapter_output=disconnected, min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "fail", payload)

        unobservable = Path(self.holder.name) / "unobservable.json"
        unobservable.write_text(json.dumps({
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "unobservable", "basis": [], "child_thread_ids": []},
            "dispatch": {"thread_relations": []},
        }), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(self.args(adapter_output=unobservable))
        self.assertEqual(payload["status"], "fail", payload)

    def test_runtime_graph_ownership_follows_sender_thread_id_only(self):
        # Pinned sender_rule for the shared topology extraction (consumed by
        # both #32 and #51): a child is owned by sender_thread_id;
        # parent_thread_id is app-server event attribution and never decides
        # an edge.
        sender_owned = Path(self.holder.name) / "sender-owned.json"
        sender_owned.write_text(json.dumps({
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "confirmed", "basis": ["formal_spawn_relation"],
                           "formal_child_count": 2, "child_thread_ids": ["mid", "deep"]},
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "contact", "parent_thread_id": "unrelated-1",
                 "receiver_thread_ids": ["mid"]},
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "mid", "parent_thread_id": "unrelated-2",
                 "receiver_thread_ids": ["deep"]},
            ]},
        }), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(
            self.args(adapter_output=sender_owned, min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "pass", payload)

        # Attribution-only nesting must not pass: the sender chain is
        # disjoint, so no nested formal topology exists.
        attribution_owned = Path(self.holder.name) / "attribution-owned.json"
        attribution_owned.write_text(json.dumps({
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "confirmed", "basis": ["formal_spawn_relation"],
                           "formal_child_count": 2, "child_thread_ids": ["mid", "deep"]},
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "shadow-a", "parent_thread_id": "contact",
                 "receiver_thread_ids": ["mid"]},
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "shadow-b", "parent_thread_id": "mid",
                 "receiver_thread_ids": ["deep"]},
            ]},
        }), encoding="utf-8")
        payload = verifier._checkpoint_runtime_graph(
            self.args(adapter_output=attribution_owned, min_edges=2, required_depth=2))
        self.assertEqual(payload["status"], "fail", payload)


class RuntimeIdentityNoisePolicyTests(unittest.TestCase):
    """Issue #47 final identity policy for the R3/R4 runtime gates.

    The adapter's diagnostics surface may carry named-identity fields
    (``fixture_status``, ``problems``, ``dispatch.agent_identity``) that
    contradict the persisted child role.  ``stage3-routing``,
    ``stage4-needs-input``, and ``runtime-graph`` must classify formal spawn
    relations and business state identically with or without that noise, and
    an identity-only payload must never manufacture a pass.
    """

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

    def _write(self, name, payload):
        path = Path(self.holder.name) / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _with_identity_noise(self, adapter):
        noisy = copy.deepcopy(adapter)
        noisy["fixture_status"] = "HARNESS_DISPATCH_MISMATCH"
        noisy["problems"] = ["contradictory identity evidence for child thread"]
        noisy.setdefault("dispatch", {})["agent_identity"] = {
            "child-thread": {
                "requested_role": {
                    "state": "confirmed",
                    "role": "professor-contact-idea-generator",
                },
                "loaded_identity": {"state": "mismatch", "role": "default"},
            }
        }
        return noisy

    def _stage3_adapter(self):
        return {
            "fixture_status": "FIXTURE_READY",
            "delegation": {
                "state": "confirmed",
                "basis": ["formal_spawn_relation"],
                "formal_child_count": 2,
                "child_thread_ids": ["idea-a", "idea-b"],
            },
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "root-thread",
                 "receiver_thread_ids": ["idea-a"]},
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "root-thread",
                 "receiver_thread_ids": ["idea-b"]},
            ]},
        }

    def _build_stage3_routing_evidence(self):
        pre = verifier._checkpoint_stage3_snapshot(self.args())
        prof = self.root / "教授研究/X分野/Example Professor"
        state = {
            "schema": 2,
            "kind": verifier.CANDIDATE_STATE_KIND,
            "identity_version": verifier.DIRECTION_IDENTITY_VERSION,
            "generator_contract_version": verifier.STAGE3_GENERATOR_CONTRACT_VERSION,
            "directions": [{
                "direction_id": verifier.DIRECTION_ID,
                "candidates": [{"id": f"idea-{index}",
                                "direction_ids": [verifier.DIRECTION_ID]}
                               for index in range(3)],
            }],
            "validator": {"results": {verifier.DIRECTION_ID: {
                "result": "pass", "rounds": 1, "issues": []}}},
        }
        (prof / "套磁候选状态.json").write_text(json.dumps(state), encoding="utf-8")
        post = verifier._checkpoint_stage3_snapshot(self.args())
        return {
            "pre_snapshot": self._write("stage3-pre.json", pre["artifacts"]),
            "post_snapshot": self._write("stage3-post.json", post["artifacts"]),
            "eval_response": self._write("stage3-response.json", {
                "passed": True,
                "output": {
                    "thread_id": "root-thread", "exit_code": 0,
                    "termination_reason": "completed", "app_server_events": [],
                },
            }),
        }

    def test_stage3_routing_ignores_named_identity_noise(self):
        evidence = self._build_stage3_routing_evidence()
        clean = verifier._checkpoint_stage3_routing(self.args(
            adapter_output=self._write("stage3-clean-adapter.json",
                                       self._stage3_adapter()),
            **evidence))
        self.assertEqual(clean["status"], "pass", clean)
        self.assertEqual(clean["classification"], "PASS")

        noisy = verifier._checkpoint_stage3_routing(self.args(
            adapter_output=self._write(
                "stage3-noisy-adapter.json",
                self._with_identity_noise(self._stage3_adapter())),
            **evidence))
        self.assertEqual(noisy, clean)

    def _stage4_adapter(self):
        return {
            "fixture_status": "FIXTURE_READY",
            "delegation": {
                "state": "confirmed",
                "basis": ["formal_spawn_relation"],
                "formal_child_count": 1,
                "child_thread_ids": ["child-c"],
            },
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "root-thread",
                 "parent_thread_id": "root-thread",
                 "receiver_thread_ids": ["child-c"]},
            ]},
        }

    def _build_stage4_needs_input_evidence(self):
        prof = self.root / "教授研究/X分野/Example Professor"
        state = {
            "schema": 2,
            "kind": verifier.CANDIDATE_STATE_KIND,
            "professor": "Example Professor",
            "directions": [{
                "direction_id": verifier.DIRECTION_ID,
                "candidates": [{
                    "id": "idea-1", "title": "确定方向",
                    "one_liner": "一句话概括",
                    "research_question": "研究问题",
                    "fit": "匹配理由",
                }],
            }],
        }
        (prof / "套磁候选状态.json").write_text(json.dumps(state), encoding="utf-8")
        pending = verifier._expected_pending_projection(self.root)
        self.assertIsNotNone(pending)
        self.assertTrue(pending)
        zero = verifier._checkpoint_stage4_snapshot(self.args())["artifacts"]
        return {
            "pre_snapshot": self._write("stage4-pre.json", zero),
            "post_snapshot": self._write("stage4-post.json", zero),
            "eval_response": self._write("stage4-response.json", {
                "output": {
                    "thread_id": "root-thread",
                    "app_server_events": [{
                        "message": {
                            "method": "rawResponseItem/completed",
                            "params": {
                                "threadId": "child-c",
                                "item": {
                                    "type": "message", "role": "assistant",
                                    "content": [{
                                        "type": "output_text",
                                        "text": json.dumps({
                                            "result": "needs_input",
                                            "pending_selection": pending,
                                        }),
                                    }],
                                },
                            },
                        },
                    }],
                },
            }),
        }

    def test_stage4_needs_input_ignores_named_identity_noise(self):
        evidence = self._build_stage4_needs_input_evidence()
        clean = verifier._checkpoint_stage4_needs_input(self.args(
            adapter_output=self._write("stage4-clean-adapter.json",
                                       self._stage4_adapter()),
            **evidence))
        self.assertEqual(clean["status"], "pass", clean)
        self.assertEqual(clean["classification"], "PASS")
        self.assertEqual(clean["target_child_id"], "child-c")

        noisy = verifier._checkpoint_stage4_needs_input(self.args(
            adapter_output=self._write(
                "stage4-noisy-adapter.json",
                self._with_identity_noise(self._stage4_adapter())),
            **evidence))
        self.assertEqual(noisy, clean)

    def test_runtime_graph_ignores_named_identity_noise(self):
        formal = {
            "fixture_status": "FIXTURE_READY",
            "delegation": {
                "state": "confirmed",
                "basis": ["formal_spawn_relation"],
                "formal_child_count": 2,
                "child_thread_ids": ["downloader", "analyzer"],
            },
            "dispatch": {"thread_relations": [
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "contact", "parent_thread_id": "contact",
                 "receiver_thread_ids": ["downloader"]},
                {"tool": "spawnAgent", "status": "completed",
                 "sender_thread_id": "downloader", "parent_thread_id": "downloader",
                 "receiver_thread_ids": ["analyzer"]},
                {"tool": "wait", "status": "completed",
                 "sender_thread_id": "contact", "parent_thread_id": "contact",
                 "receiver_thread_ids": ["analyzer"]},
            ]},
        }
        raw = self._write("graph-response.json", {
            "output": {"app_server_events": [{"type": "spawnAgent"}]}})
        clean = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=self._write("graph-clean-adapter.json", formal),
            eval_response=raw, min_edges=2, required_depth=2))
        self.assertEqual(clean["status"], "pass", clean)

        noisy = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=self._write(
                "graph-noisy-adapter.json",
                self._with_identity_noise(formal)),
            eval_response=raw, min_edges=2, required_depth=2))
        self.assertEqual(noisy, clean)

        identity_only = self._with_identity_noise(
            {"fixture_status": "FIXTURE_READY",
             "loaded_agents": ["professor-contact", "downloader"]})
        payload = verifier._checkpoint_runtime_graph(self.args(
            adapter_output=self._write("graph-identity-only.json", identity_only)))
        self.assertEqual(payload["status"], "fail", payload)
        self.assertEqual(payload["observed"]["formal_relations"], [])



class Issue67Stage4IsolationHarnessTests(unittest.TestCase):
    """PC67-RISO oracle: frozen fixture/prompt/verifier only, never Codex.

    Each case either inspects the shipped assets or drives the real Stage-4
    producer CLI over the frozen fixture and grades the isolation checkpoint
    from file bytes plus synthetic formal-delegation evidence.  The minimal
    counterexample the Gate-2 record requires is a preparer that swaps professor
    B's single malformed candidate-state fault for another fault while every
    other manifest field stays self-consistent with the bytes it ships: that run
    must be ``INVALID_TEST_EXECUTION``, never a PASS.
    """

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name).resolve()
        self.program = self.root / "program"
        self.profile = self.root / "profile"
        self.consumer = self.root / "consumer"
        self.out = self.root / "output"
        self.consumer.mkdir()
        self.out.mkdir()
        self.chain = None
        self.manifest = None
        self.producer_rc = None
        self.producer_result = None

    # -- recipe plumbing ---------------------------------------------------
    def _args(self, **overrides):
        values = {
            "program_root": self.program,
            "consumer_root": self.consumer,
            "eval_response": None,
            "adapter_output": None,
            "producer_sha": PRODUCER_SHA,
            "output": None,
            "min_edges": 1,
            "required_depth": 1,
            "pre_snapshot": None,
            "post_snapshot": None,
            "fixture_manifest": None,
            "eval_request": None,
            "input_sha256": None,
            "install_verdict": None,
            "fixture_sha": FIXTURE_SHA,
        }
        values.update(overrides)
        return Namespace(**values)

    @staticmethod
    def _sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def _write(path, payload):
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                              encoding="utf-8")

    @staticmethod
    def _statuses(payload):
        return {row["name"]: row["status"] for row in payload["checks"]}

    @staticmethod
    def _failed(payload):
        return sorted(row["name"] for row in payload["checks"] if row["status"] != "pass")

    def _frozen_fixture(self, manifest_path):
        return issue67_fixture.build_fixture(self.program, self.profile,
                                            output=manifest_path)

    def _install_consumer(self):
        for relative in verifier.INSTALL_REQUIRED_FILES:
            path = self.consumer / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("installed\n", encoding="utf-8")
        (self.consumer / ".codex/agents/professor-contact-email-generator.toml").write_text(
            GENERATOR_TOML, encoding="utf-8")
        (self.consumer / "apm.lock.yaml").write_text(
            "dependencies:\n  - name: professor-contact\n"
            f"    resolved_commit: {PRODUCER_SHA}\n", encoding="utf-8")

    def _manual_pre_snapshot(self, manifest_path, manifest):
        """The pre-run snapshot shape, for fixtures a mutant preparer shipped."""
        professors = {}
        for entry in manifest["professors"]:
            directory = Path(entry["professor_dir"])
            professors[entry["canonical_professor_dir"]] = {
                "professor": entry["professor"],
                "idea_id": entry["idea_id"],
                "direction_id": entry["direction_id"],
                "input_pack": verifier._file_state(
                    directory / verifier.LOCAL_INPUT_PACK_FILE),
                "candidate_state": verifier._file_state(
                    directory / verifier.LOCAL_CANDIDATE_STATE_FILE),
                "selection_file": verifier._file_state(
                    directory / verifier.LOCAL_SELECTION_FILE),
                "email_pack": verifier._file_state(
                    directory / verifier.LOCAL_EMAIL_PACK_FILE),
            }
        return {
            "status": "pass",
            "checks": [],
            "artifacts": verifier._stage4_artifacts(self.program),
            "isolation_pre": {
                "builder": manifest["builder"],
                "manifest_sha256": self._sha(manifest_path),
                "program_root": str(self.program),
                "professors": professors,
                "fault": {
                    "professor_dir": manifest["fault"]["professor_dir"],
                    "relative_path": manifest["fault"]["relative_path"],
                    "sha256": manifest["fault"]["sha256"],
                },
            },
        }

    def _run_producer(self, manifest):
        selections = [{
            "professor": entry["professor"],
            "professor_dir": entry["professor_dir"],
            "direction_ids": [entry["direction_id"]],
            "ideas": [{"id": entry["idea_id"], "note": ""}],
        } for entry in manifest["professors"]]
        input_path = self.out / "selection-input.json"
        self._write(input_path, {"selections": selections})
        completed = subprocess.run(
            [sys.executable, str(PRODUCER_PATH), "stage4-finalize",
             "--program-root", str(self.program),
             "--selection-input", str(input_path),
             "--profile", manifest["profile_file"]],
            text=True, capture_output=True, check=False)
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = None
        return completed.returncode, payload

    @staticmethod
    def _formal_adapter(*, root_thread="root-1", child=CHILD_THREAD_ID,
                        status="completed", fixture_status="FIXTURE_READY"):
        return {
            "fixture_status": fixture_status,
            "delegation": {
                "state": "confirmed",
                "formal_child_count": 1,
                "child_thread_ids": [child],
                "basis": ["formal_spawn_relation"],
                "reason_code": None,
            },
            "dispatch": {"thread_relations": [{
                "tool": "spawnAgent",
                "status": status,
                "sender_thread_id": root_thread,
                "parent_thread_id": root_thread,
                "receiver_thread_ids": [child],
            }]},
        }

    @staticmethod
    def _raw_response(*, root_thread="root-1", child=CHILD_THREAD_ID, prose="stage4 done",
                      events=None):
        if events is None:
            events = [{"message": {
                "method": "rawResponseItem/completed",
                "params": {
                    "threadId": child,
                    "item": {"type": "message", "role": "assistant",
                             "content": [{"type": "output_text", "text": prose}]},
                },
            }}]
        return {"output": {"thread_id": root_thread, "termination_reason": "completed",
                           "exit_code": 0, "app_server_events": events}}

    def _build(self, *, fixture=None, manual_pre=False):
        """Assemble the frozen PC67-RISO evidence set and run the real producer."""
        manifest_path = self.out / "fixture-manifest.json"
        manifest = (fixture or self._frozen_fixture)(manifest_path)
        pre_path = self.out / "pre-snapshot.json"
        if manual_pre:
            self._write(pre_path, self._manual_pre_snapshot(manifest_path, manifest))
        else:
            pre = verifier._checkpoint_stage4_snapshot(
                self._args(fixture_manifest=manifest_path))
            self.assertEqual(pre["status"], "pass", self._failed(pre))
            self._write(pre_path, pre)
        self._install_consumer()
        install_path = self.out / "install-verdict.json"
        install = verifier._checkpoint_install(self._args())
        self.assertEqual(install["status"], "pass", self._failed(install))
        self._write(install_path, install)
        prompt_path = self.out / verifier.ISSUE67_PROMPT_NAME
        prompt_path.write_text(
            ISSUE67_PROMPT_PATH.read_text(encoding="utf-8").replace(
                "<PROGRAM_ROOT>", str(self.program)),
            encoding="utf-8")
        request_path = self.out / "eval-request.json"
        issue67_request.build_request(
            consumer_root=self.consumer, prompt_file=prompt_path, output=request_path,
            model=verifier.ISSUE67_REQUEST_MODEL,
            reasoning=verifier.ISSUE67_REQUEST_REASONING, timeout=900)
        sha_path = self.out / "input-sha256.txt"
        sha_path.write_text("".join(
            f"{self._sha(path)}  {path}\n"
            for path in (manifest_path, pre_path, prompt_path, request_path)),
            encoding="utf-8")
        self.producer_rc, self.producer_result = self._run_producer(manifest)
        adapter_path = self.out / "adapter.json"
        self._write(adapter_path, self._formal_adapter())
        response_path = self.out / "response.json"
        self._write(response_path, self._raw_response())
        self.manifest = manifest
        self.chain = {
            "fixture_manifest": manifest_path,
            "pre_snapshot": pre_path,
            "eval_request": request_path,
            "input_sha256": sha_path,
            "eval_response": response_path,
            "adapter_output": adapter_path,
            "install_verdict": install_path,
        }
        return self.chain

    def _verdict(self, **overrides):
        if self.chain is None:
            self._build()
        values = dict(self.chain)
        values.update(overrides)
        return verifier._checkpoint_stage4_professor_isolation(self._args(**values))

    def test_persistent_v2_request_accepts_the_existing_isolation_proof(self):
        payload = self._verdict()
        self.assertEqual(payload["classification"], "PASS_TARGET", self._failed(payload))
        request = json.loads(self.chain["eval_request"].read_text(encoding="utf-8"))
        argv = shlex.split(request["command"])
        self.assertNotIn("--ephemeral", argv)
        self.assertIn('features.multi_agent_v2.enabled=true', argv)

    def test_ephemeral_request_is_invalid_even_when_product_files_are_correct(self):
        self._build()
        request_path = self.chain["eval_request"]
        request = json.loads(request_path.read_text(encoding="utf-8"))
        argv = shlex.split(request["command"])
        argv.insert(1, "--ephemeral")
        request["command"] = shlex.join(argv)
        self._write(request_path, request)
        sha_path = self.chain["input_sha256"]
        records = verifier._issue67_input_sha_records(sha_path)
        records[str(request_path)] = self._sha(request_path)
        sha_path.write_text("".join(f"{digest}  {path}\n" for path, digest in records.items()),
                            encoding="utf-8")
        payload = self._verdict()
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("eval_request_command_surface", self._failed(payload))

    def _professor_dirs(self):
        valid = next(row for row in self.manifest["professors"] if row["role"] == "valid")
        fault = next(row for row in self.manifest["professors"]
                     if row["role"] == "malformed_candidate_state")
        return (Path(valid["canonical_professor_dir"]),
                Path(fault["canonical_professor_dir"]))

    def _mutant_preparer(self, manifest_path):
        """Counterexample preparer: B's fault becomes another file, manifest self-consistent."""
        manifest = self._frozen_fixture(manifest_path)
        alpha = Path(manifest["professors"][0]["professor_dir"])
        beta = Path(manifest["professors"][1]["professor_dir"])
        state = json.loads((alpha / verifier.LOCAL_CANDIDATE_STATE_FILE).read_text(
            encoding="utf-8"))
        state["directions"][0]["candidates"][0]["id"] = \
            manifest["professors"][1]["idea_id"]
        self._write(beta / verifier.LOCAL_CANDIDATE_STATE_FILE, state)
        (beta / verifier.LOCAL_INPUT_PACK_FILE).write_bytes(NON_CANONICAL_INPUT_PACK_BYTES)
        for entry in manifest["professors"]:
            directory = Path(entry["professor_dir"])
            entry["input_pack"]["sha256"] = self._sha(
                directory / verifier.LOCAL_INPUT_PACK_FILE)
            entry["candidate_state"]["sha256"] = self._sha(
                directory / verifier.LOCAL_CANDIDATE_STATE_FILE)
            # The mutant ships a canonical candidate state for both professors
            # and still calls the candidate state the fault, so a manifest-only
            # reading looks self-consistent all the way through.
            entry["input_pack"]["canonical"] = directory != beta
            entry["candidate_state"]["canonical"] = True
        manifest["fault"]["sha256"] = self._sha(
            beta / verifier.LOCAL_CANDIDATE_STATE_FILE)
        manifest["fault"]["spec_sha256"] = manifest["fault"]["sha256"]
        manifest["input_hashes"] = {
            relative: self._sha(self.program / relative)
            for relative in manifest["input_hashes"]}
        manifest["legacy_program_pair"] = {
            relative: self._sha(self.program / relative)
            for relative in manifest["legacy_program_pair"]}
        manifest["builder_sha256"] = self._sha(ISSUE67_PREPARER_PATH)
        self._write(manifest_path, manifest)
        return manifest

    # -- shipped assets ----------------------------------------------------
    def test_frozen_isolation_assets_ship_inside_the_installed_consumer(self):
        self.assertIn(".agents/skills/professor-contact/tests/runtime/"
                      "prepare_issue67_stage4_isolation_fixture.py",
                      verifier.INSTALL_REQUIRED_FILES)
        self.assertIn(".agents/skills/professor-contact/tests/runtime/prompts/"
                      "issue67-stage4-isolation.txt", verifier.INSTALL_REQUIRED_FILES)
        self.assertIs(verifier.CHECKPOINTS["stage4-professor-isolation"],
                      verifier._checkpoint_stage4_professor_isolation)
        destinations = {action.dest for action in verifier._parser()._actions}
        self.assertTrue({"fixture_manifest", "eval_request", "input_sha256",
                         "install_verdict", "fixture_sha"} <= destinations)
        self.assertEqual(verifier.STAGE4_LOCAL_SCHEMA, 3)
        self.assertEqual(verifier.ISSUE67_REQUEST_MODEL, "gpt-5.6-luna")
        self.assertEqual(verifier.ISSUE67_REQUEST_REASONING, "low")

    def test_frozen_prompt_identifies_both_professors_by_canonical_directory(self):
        text = ISSUE67_PROMPT_PATH.read_text(encoding="utf-8")
        self.assertEqual(text.count("<PROGRAM_ROOT>"), 1)
        for spec in issue67_fixture.PROFESSORS:
            self.assertIn(f"教授研究/{spec['field']}/{spec['directory']}", text)
            self.assertIn(spec["idea_id"], text)
        # The display name is shared, so it cannot be the transaction identity.
        self.assertNotIn(issue67_fixture.DISPLAY_NAME, text)

    def test_frozen_fixture_freezes_one_candidate_state_fault_and_history_only_pair(self):
        manifest_path = self.out / "fixture-manifest.json"
        manifest = self._frozen_fixture(manifest_path)
        self.assertEqual(manifest["builder"], verifier.ISSUE67_FIXTURE_BUILDER)
        self.assertEqual(manifest["fixture_kind"], "stage4-isolation")
        self.assertEqual(manifest["manual_patch"], "no")
        self.assertEqual(manifest["builder_sha256"], self._sha(ISSUE67_PREPARER_PATH))
        self.assertEqual([row["professor"] for row in manifest["professors"]],
                         [issue67_fixture.DISPLAY_NAME] * 2)
        self.assertEqual(len({row["canonical_professor_dir"]
                              for row in manifest["professors"]}), 2)
        faults = [row for row in manifest["professors"]
                  if not row["candidate_state"]["canonical"]]
        self.assertEqual(len(faults), 1, manifest["professors"])
        self.assertEqual(faults[0]["candidate_state"]["relative_path"],
                         verifier.LOCAL_CANDIDATE_STATE_FILE)
        self.assertEqual(faults[0]["role"], "malformed_candidate_state")
        self.assertEqual(manifest["fault"]["kind"], "malformed_canonical_candidate_state")
        self.assertEqual(manifest["fault"]["expected_reason_code"], "invalid_candidate_state")
        self.assertEqual(manifest["fault"]["relative_path"],
                         verifier.LOCAL_CANDIDATE_STATE_FILE)
        self.assertEqual(
            self._sha(Path(manifest["fault"]["professor_dir"])
                      / verifier.LOCAL_CANDIDATE_STATE_FILE), manifest["fault"]["sha256"])
        self.assertEqual(
            self._sha(Path(manifest["fault"]["professor_dir"])
                      / verifier.LOCAL_CANDIDATE_STATE_FILE),
            hashlib.sha256(issue67_fixture.MALFORMED_CANDIDATE_STATE_BYTES).hexdigest())
        self.assertEqual(len(manifest["forbidden_outputs"]), 4)
        for entry in manifest["professors"]:
            directory = Path(entry["canonical_professor_dir"])
            for name in (verifier.LOCAL_SELECTION_FILE, verifier.LOCAL_EMAIL_PACK_FILE):
                self.assertFalse((directory / name).exists(), directory)
        # The legacy program-level pair is history that contradicts current facts.
        self.assertEqual(sorted(manifest["legacy_program_pair"]),
                         ["教授研究/套磁选择.json", "教授研究/邮件输入.json"])
        legacy = json.loads((self.program / "教授研究/套磁选择.json").read_text(
            encoding="utf-8"))
        self.assertEqual(legacy["schema"], 2)
        self.assertEqual(legacy["selections"][0]["direction_ids"],
                         [issue67_fixture.LEGACY_DIRECTION_ID])
        self.assertNotIn(issue67_fixture.LEGACY_DIRECTION_ID,
                         [row["direction_id"] for row in manifest["professors"]])

    def test_stage4_snapshot_pins_the_isolation_pre_state_and_stays_compatible(self):
        manifest_path = self.out / "fixture-manifest.json"
        manifest = self._frozen_fixture(manifest_path)
        with_manifest = verifier._checkpoint_stage4_snapshot(
            self._args(fixture_manifest=manifest_path))
        self.assertEqual(with_manifest["status"], "pass", self._failed(with_manifest))
        pre = with_manifest["isolation_pre"]
        self.assertEqual(pre["builder"], verifier.ISSUE67_FIXTURE_BUILDER)
        self.assertEqual(pre["manifest_sha256"], self._sha(manifest_path))
        self.assertEqual(pre["program_root"], str(self.program))
        self.assertEqual(pre["fault"], {
            "professor_dir": manifest["fault"]["professor_dir"],
            "relative_path": verifier.LOCAL_CANDIDATE_STATE_FILE,
            "sha256": manifest["fault"]["sha256"]})
        self.assertEqual(set(pre["professors"]),
                         {row["canonical_professor_dir"] for row in manifest["professors"]})
        for row in pre["professors"].values():
            self.assertFalse(row["selection_file"]["exists"])
            self.assertFalse(row["email_pack"]["exists"])
        # The program-level artifact shape other recipes depend on is unchanged.
        without_manifest = verifier._checkpoint_stage4_snapshot(self._args())
        self.assertEqual(without_manifest["artifacts"], with_manifest["artifacts"])
        self.assertNotIn("isolation_pre", without_manifest)
        self.assertEqual(set(without_manifest), {"status", "checks", "artifacts"})

    # -- the positive oracle ----------------------------------------------
    def test_isolation_checkpoint_passes_the_real_producer_isolation(self):
        self._build()
        payload = self._verdict()
        self.assertEqual(payload["status"], "pass", self._failed(payload))
        self.assertEqual(payload["classification"], "PASS_TARGET")
        self.assertEqual(self._failed(payload), [])
        names = self._statuses(payload)
        for gate in ISSUE67_PROVEN_GATES:
            self.assertEqual(names.get(gate), "pass", gate)
        alpha, beta = self._professor_dirs()
        observed = payload["observed"]
        self.assertEqual(observed["producer_sha"], PRODUCER_SHA)
        self.assertEqual(observed["fixture_sha"], FIXTURE_SHA)
        self.assertEqual(observed["consumer_root"], str(self.consumer))
        self.assertEqual(observed["formal_child_thread_ids"], [CHILD_THREAD_ID])
        self.assertEqual(observed["valid_professor_dir"], str(alpha))
        self.assertEqual(observed["fault_professor_dir"], str(beta))
        self.assertEqual(observed["valid_professor_selection_file"],
                         str(alpha / verifier.LOCAL_SELECTION_FILE))
        self.assertEqual(observed["valid_professor_email_pack"],
                         str(alpha / verifier.LOCAL_EMAIL_PACK_FILE))
        self.assertEqual(observed["fault_professor_bytes_sha256"],
                         self.manifest["fault"]["sha256"])
        # The producer itself isolated the two professors in one aggregate call.
        self.assertEqual(self.producer_rc, 0)
        self.assertEqual(self.producer_result["status"], "partial")
        rows = {row["professor_dir"]: row for row in self.producer_result["results"]}
        self.assertEqual(rows[str(alpha)]["status"], "ok")
        self.assertEqual(rows[str(beta)]["status"], "needs_refresh")
        self.assertEqual(rows[str(beta)]["reason_code"], "invalid_candidate_state")
        self.assertIsNone(rows[str(beta)]["selection_file"])
        # What the oracle accepted is a professor-local schema-3 pair carrying
        # the current profile fingerprint, not the legacy program-level schema.
        selection = json.loads((alpha / verifier.LOCAL_SELECTION_FILE).read_text(
            encoding="utf-8"))
        pack = json.loads((alpha / verifier.LOCAL_EMAIL_PACK_FILE).read_text(
            encoding="utf-8"))
        self.assertEqual(selection["schema"], verifier.STAGE4_LOCAL_SCHEMA)
        self.assertEqual(pack["schema"], verifier.STAGE4_LOCAL_SCHEMA)
        self.assertEqual(selection["profile_fingerprint"], self.manifest["profile_sha256"])
        self.assertEqual(len(pack["emails"]), 1)
        self.assertEqual(
            pack["emails"][0]["email_id"],
            f"{issue67_fixture.DISPLAY_NAME}::"
            f"{self.manifest['professors'][0]['direction_id']}::"
            f"{self.manifest['professors'][0]['idea_id']}")

    def test_model_prose_never_grades_the_isolation_verdict(self):
        self._build()
        boasting = ("两位教授的套磁选择与邮件输入都已成功写入程序级容器，"
                    "isolation-beta 也已完成。")
        adapter = self.out / "boasting-adapter.json"
        self._write(adapter, self._formal_adapter())
        response = self.out / "boasting-response.json"
        self._write(response, self._raw_response(prose=boasting))
        loud = self._verdict(adapter_output=adapter, eval_response=response)
        self.assertEqual(loud["classification"], "PASS_TARGET", self._failed(loud))
        alpha, _ = self._professor_dirs()
        for name in (verifier.LOCAL_SELECTION_FILE, verifier.LOCAL_EMAIL_PACK_FILE):
            (alpha / name).unlink()
        silent = self._verdict(adapter_output=adapter, eval_response=response)
        self.assertEqual(silent["status"], "fail", silent)
        self.assertEqual(silent["classification"], "FAIL_PRODUCT")
        self.assertIn("valid_professor_local_pair_written", self._failed(silent))

    # -- the required counterexample --------------------------------------
    def test_swapping_the_single_fault_for_another_fault_is_never_a_pass(self):
        self._build(fixture=self._mutant_preparer, manual_pre=True)
        payload = self._verdict()
        self.assertEqual(payload["status"], "invalid", payload)
        self.assertEqual(payload["classification"], "INVALID_TEST_EXECUTION")
        # Everything the manifest pins still matches the shipped bytes, so the
        # only possible rejection is the frozen single-fault precondition.
        self.assertEqual(self._failed(payload), ["fixture_single_fault"])

    def test_rewriting_the_frozen_fault_bytes_is_a_product_failure(self):
        self._build()
        alpha, beta = self._professor_dirs()
        canonical = json.loads(
            (alpha / verifier.LOCAL_CANDIDATE_STATE_FILE).read_text(encoding="utf-8"))
        canonical["directions"][0]["candidates"][0]["id"] = \
            self.manifest["professors"][1]["idea_id"]
        self._write(beta / verifier.LOCAL_CANDIDATE_STATE_FILE, canonical)
        payload = self._verdict()
        self.assertEqual(payload["classification"], "FAIL_PRODUCT", payload)
        failed = self._failed(payload)
        self.assertIn("fixture_inputs_unchanged", failed)
        self.assertIn("fault_professor_bytes_unchanged", failed)

    def test_writing_the_fault_professor_pair_is_a_product_failure(self):
        self._build()
        alpha, beta = self._professor_dirs()
        for name in (verifier.LOCAL_SELECTION_FILE, verifier.LOCAL_EMAIL_PACK_FILE):
            shutil.copy(alpha / name, beta / name)
        payload = self._verdict()
        self.assertEqual(payload["classification"], "FAIL_PRODUCT", payload)
        failed = self._failed(payload)
        self.assertIn("fault_professor_local_pair_absent", failed)
        self.assertIn("stage4_pair_written_only_where_the_contract_allows", failed)

    def test_pair_bound_to_the_display_name_instead_of_the_directory_is_a_failure(self):
        self._build()
        alpha, _ = self._professor_dirs()
        lookalike = alpha.parent / issue67_fixture.DISPLAY_NAME
        lookalike.mkdir()
        for name in (verifier.LOCAL_SELECTION_FILE, verifier.LOCAL_EMAIL_PACK_FILE):
            shutil.copy(alpha / name, lookalike / name)
        payload = self._verdict()
        self.assertEqual(payload["classification"], "FAIL_PRODUCT", payload)
        self.assertIn("stage4_pair_written_only_where_the_contract_allows",
                      self._failed(payload))
        shutil.rmtree(lookalike)
        # The same pair, now pointing at the display-name directory instead of
        # the canonical one, must fail the identity gate.
        selection_path = alpha / verifier.LOCAL_SELECTION_FILE
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        moved = str(alpha.parent / issue67_fixture.DISPLAY_NAME)
        selection["professor_dir"] = moved
        for row in selection["selections"]:
            row["professor_dir"] = moved
        self._write(selection_path, selection)
        rebound = self._verdict()
        self.assertEqual(rebound["classification"], "FAIL_PRODUCT", rebound)
        self.assertIn("valid_professor_pair_bound_to_canonical_professor_dir",
                      self._failed(rebound))

    def test_legacy_program_pair_regaining_authority_is_a_product_failure(self):
        self._build()
        path = self.program / "教授研究/套磁选择.json"
        legacy = json.loads(path.read_text(encoding="utf-8"))
        legacy["schema"] = verifier.STAGE4_LOCAL_SCHEMA
        legacy["selections"].append({
            "professor": self.manifest["professors"][0]["professor"],
            "professor_dir": self.manifest["professors"][0]["professor_dir"],
            "direction_ids": [self.manifest["professors"][0]["direction_id"]],
            "ideas": [{"id": self.manifest["professors"][0]["idea_id"], "note": ""}],
        })
        self._write(path, legacy)
        payload = self._verdict()
        self.assertEqual(payload["classification"], "FAIL_PRODUCT", payload)
        failed = self._failed(payload)
        self.assertIn("program_level_pair_unchanged", failed)
        self.assertIn("fixture_inputs_unchanged", failed)
        # The Phase-J pin of the same hashes is the second, redundant proof and
        # is only reached once the frozen bytes are intact (see ISSUE67_PROVEN_GATES).
        self.assertNotIn("no_program_level_pair_rewritten", failed)

    def test_local_pair_contradicting_current_facts_or_legacy_identity_fails(self):
        self._build()
        alpha, _ = self._professor_dirs()
        pack_path = alpha / verifier.LOCAL_EMAIL_PACK_FILE
        original = pack_path.read_bytes()
        pack = json.loads(original.decode("utf-8"))
        pack["emails"][0]["idea"]["id"] = "issue67-not-in-current-state"
        self._write(pack_path, pack)
        stale = self._verdict()
        self.assertEqual(stale["classification"], "FAIL_PRODUCT", stale)
        self.assertIn("valid_professor_email_pack_matches_current_facts",
                      self._failed(stale))
        pack_path.write_bytes(original)
        selection_path = alpha / verifier.LOCAL_SELECTION_FILE
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        selection["selections"][0]["direction_ids"] = [
            self.manifest["professors"][0]["direction_id"],
            issue67_fixture.LEGACY_DIRECTION_ID]
        self._write(selection_path, selection)
        promoted = self._verdict()
        self.assertEqual(promoted["classification"], "FAIL_PRODUCT", promoted)
        failed = self._failed(promoted)
        self.assertIn("legacy_program_pair_not_promoted_into_local_authority", failed)
        self.assertIn("valid_professor_selection_matches_this_request_and_current_state",
                      failed)

    # -- verdict attribution ------------------------------------------------
    def test_unobservable_or_unowned_delegation_is_blocked_not_failed(self):
        self._build()
        unobservable = self.out / "unobservable-adapter.json"
        self._write(unobservable, {
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "unobservable", "formal_child_count": 0,
                           "child_thread_ids": [], "basis": [],
                           "reason_code": "no_supported_formal_spawn_relation"},
            "dispatch": {"thread_relations": []},
        })
        empty = self.out / "empty-response.json"
        self._write(empty, self._raw_response(events=[]))
        blocked = self._verdict(adapter_output=unobservable, eval_response=empty)
        self.assertEqual(blocked["status"], "blocked", blocked)
        self.assertEqual(blocked["classification"], "BLOCKED_OBSERVABILITY")
        self.assertIn("delegation_observable", self._failed(blocked))

        foreign = self.out / "foreign-owner-adapter.json"
        self._write(foreign, self._formal_adapter(root_thread="some-other-root"))
        orphan = self._verdict(adapter_output=foreign)
        self.assertEqual(orphan["classification"], "BLOCKED_OBSERVABILITY", orphan)
        self.assertIn("formal_root_child", self._failed(orphan))

        provider = self.out / "provider-adapter.json"
        self._write(provider, self._formal_adapter(fixture_status="BLOCKED_DEPENDENCY"))
        dependent = self._verdict(adapter_output=provider)
        self.assertEqual(dependent["classification"], "BLOCKED_RUNTIME_PROVIDER")

    def test_inconsistent_or_malformed_adapter_evidence_is_an_invalid_run(self):
        self._build()
        lying = self.out / "lying-adapter.json"
        self._write(lying, {
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "confirmed", "formal_child_count": 1,
                           "child_thread_ids": [CHILD_THREAD_ID],
                           "basis": ["formal_spawn_relation"], "reason_code": None},
            "dispatch": {"thread_relations": []},
        })
        inconsistent = self._verdict(adapter_output=lying)
        self.assertEqual(inconsistent["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("delegation_summary_consistent", self._failed(inconsistent))

        malformed = self.out / "malformed-relation-adapter.json"
        self._write(malformed, {
            "fixture_status": "FIXTURE_READY",
            "delegation": {"state": "unobservable", "formal_child_count": 0,
                           "child_thread_ids": [], "basis": [],
                           "reason_code": "no_supported_formal_spawn_relation"},
            "dispatch": {"thread_relations": [{
                "tool": "spawnAgent", "status": "completed",
                "sender_thread_id": "root-1", "parent_thread_id": "root-1",
                "receiver_thread_ids": []}]},
        })
        shape = self._verdict(adapter_output=malformed)
        self.assertEqual(shape["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("adapter_relation_shape", self._failed(shape))

        corrupt = self.out / "corrupt-adapter.json"
        corrupt.write_text("{", encoding="utf-8")
        unreadable = self._verdict(adapter_output=corrupt)
        self.assertEqual(unreadable["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("evidence_readable", self._failed(unreadable))

        invalid_evidence = self.out / "invalid-evidence-adapter.json"
        self._write(invalid_evidence, self._formal_adapter(fixture_status="INVALID_EVIDENCE"))
        stale = self._verdict(adapter_output=invalid_evidence)
        self.assertEqual(stale["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("adapter_invalid_evidence", self._failed(stale))

        missing = self._verdict(adapter_output=None)
        self.assertEqual(missing["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("evidence_supplied", self._failed(missing))

    def test_damaged_or_foreign_harness_evidence_is_an_invalid_run(self):
        self._build()
        failing_install = self.out / "failing-install.json"
        self._write(failing_install, {
            "status": "fail",
            "checks": [{"name": "producer_sha_pinned", "status": "fail", "detail": {}}],
            "observed": {"consumer_root": str(self.consumer)},
        })
        broken = self._verdict(install_verdict=failing_install)
        self.assertEqual(broken["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("install_verdict_pass", self._failed(broken))

        # A lock that resolves to another commit is not exact-SHA provenance.
        (self.consumer / "apm.lock.yaml").write_text(
            "dependencies:\n  - name: professor-contact\n"
            f"    resolved_commit: {'d' * 40}\n", encoding="utf-8")
        rerun = self.out / "rerun-install.json"
        self._write(rerun, verifier._checkpoint_install(
            self._args(producer_sha="d" * 40)))
        provenance = self._verdict(install_verdict=rerun)
        self.assertEqual(provenance["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("install_provenance_rederived", self._failed(provenance))
        (self.consumer / "apm.lock.yaml").write_text(
            "dependencies:\n  - name: professor-contact\n"
            f"    resolved_commit: {PRODUCER_SHA}\n", encoding="utf-8")

        alt = self.out / "alt"
        alt.mkdir()
        network_prompt = alt / "network-prompt.txt"
        network_prompt.write_text("run stage 4 with network access", encoding="utf-8")
        widened = alt / "eval-request.json"
        issue67_request.build_request(
            consumer_root=self.consumer, prompt_file=network_prompt, output=widened,
            model=verifier.ISSUE67_REQUEST_MODEL,
            reasoning=verifier.ISSUE67_REQUEST_REASONING, timeout=900)
        request = json.loads(widened.read_text(encoding="utf-8"))
        request["command"] = request["command"].replace(
            "--sandbox", '--config network_access="allowed" --sandbox', 1)
        self._write(widened, request)
        forbidden = self._verdict(eval_request=widened)
        self.assertEqual(forbidden["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("eval_request_excludes[network_access]", self._failed(forbidden))

        prose_prompt = alt / "issue67-stage4-isolation.txt"
        prose_prompt.write_text("do stage 4 however you like", encoding="utf-8")
        rewritten = alt / "eval-request.json"
        issue67_request.build_request(
            consumer_root=self.consumer, prompt_file=prose_prompt, output=rewritten,
            model=verifier.ISSUE67_REQUEST_MODEL,
            reasoning=verifier.ISSUE67_REQUEST_REASONING, timeout=900)
        foreign_prompt = self._verdict(eval_request=rewritten)
        self.assertEqual(foreign_prompt["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("eval_request_prompt_is_frozen_prompt", self._failed(foreign_prompt))

        damaged = alt / "input-sha256.txt"
        damaged.write_text("not-a-digest  whatever\n", encoding="utf-8")
        unparsable = self._verdict(input_sha256=damaged)
        self.assertEqual(unparsable["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("input_sha256_readable", self._failed(unparsable))

        drifted = alt / "drifted-sha.txt"
        recorded = {Path(line.partition("  ")[2].strip()): line.partition("  ")[0]
                    for line in self.chain["input_sha256"].read_text(
                        encoding="utf-8").splitlines() if line.strip()}
        drifted.write_text("".join(
            f"{'f' * 64}  {path}\n" if path.name == "fixture-manifest.json"
            else f"{digest}  {path}\n" for path, digest in recorded.items()),
            encoding="utf-8")
        unstable = self._verdict(input_sha256=drifted)
        self.assertEqual(unstable["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("input_sha256_records_stable", self._failed(unstable))

        other = self.out / "other-pre.json"
        pre = json.loads(self.chain["pre_snapshot"].read_text(encoding="utf-8"))
        pre["isolation_pre"]["program_root"] = str(self.root / "elsewhere")
        self._write(other, pre)
        foreign_root = self._verdict(pre_snapshot=other)
        self.assertEqual(foreign_root["classification"], "INVALID_TEST_EXECUTION")
        self.assertIn("pre_snapshot_is_for_this_manifest", self._failed(foreign_root))


if __name__ == "__main__":
    unittest.main()
