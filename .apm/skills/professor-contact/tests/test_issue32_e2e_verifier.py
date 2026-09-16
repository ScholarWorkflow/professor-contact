import importlib.util
import contextlib
import io
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
        }
        values.update(overrides)
        return Namespace(**values)

    def test_initial_checkpoint_is_pass_and_stage0_state_is_absent(self):
        payload = verifier._checkpoint_initial(self.args())
        self.assertEqual(payload["status"], "pass", payload)
        self.assertFalse((self.root / "教授研究/套磁目标.json").exists())

    def test_stage1_final_accepts_runtime_item_keys_from_manifest(self):
        root = Path(self.holder.name) / "dynamic-program"
        profile = Path(self.holder.name) / "dynamic-profile"
        ready_key, fill_key = "READY1234", "FILL5678"
        builder.build_fixture(root, profile, item_keys=(ready_key, fill_key))

        prof = root / "教授研究/X分野/Example Professor"
        papers_path = prof / "papers.json"
        papers = json.loads(papers_path.read_text(encoding="utf-8"))
        for paper in papers["papers"]:
            if paper["item_key"] == fill_key:
                paper["pdf_status"] = "downloaded"
        papers_path.write_text(json.dumps(papers), encoding="utf-8")

        (root / "教授研究/套磁阶段1候选.json").write_text(json.dumps({
            "schema_version": 1,
            "kind": "professor-contact-stage1",
            "professors": [{
                "professor": "Example Professor",
                "directions": [{
                    "direction_id": "DIR00001",
                    "candidate_keys": [ready_key, fill_key],
                    "pdf_readiness": {
                        "usable_item_keys": [ready_key, fill_key],
                        "missing_item_keys": [],
                    },
                }],
            }],
        }), encoding="utf-8")
        response = Path(self.holder.name) / "dynamic-r1-response.json"
        response.write_text(json.dumps({
            "collector_payload": {
                "folder_path": str(root),
                "pdf_only": True,
                "item_keys": [fill_key],
            },
        }), encoding="utf-8")

        payload = verifier._checkpoint_stage1_final(
            self.args(program_root=root, eval_response=response))
        self.assertEqual(payload["status"], "pass", payload)

    def test_stage1_final_accepts_noop_without_collector_payload_when_all_pdfs_ready(self):
        root = Path(self.holder.name) / "noop-program"
        profile = Path(self.holder.name) / "noop-profile"
        ready_key, fill_key = "READY1234", "FILL5678"
        builder.build_fixture(root, profile, item_keys=(ready_key, fill_key))

        prof = root / "教授研究/X分野/Example Professor"
        papers_path = prof / "papers.json"
        papers = json.loads(papers_path.read_text(encoding="utf-8"))
        for paper in papers["papers"]:
            paper["pdf_status"] = "downloaded"
        papers_path.write_text(json.dumps(papers), encoding="utf-8")

        (root / "教授研究/套磁阶段1候选.json").write_text(json.dumps({
            "schema_version": 1,
            "kind": "professor-contact-stage1",
            "professors": [{
                "professor": "Example Professor",
                "directions": [{
                    "direction_id": "DIR00001",
                    "candidate_keys": [ready_key, fill_key],
                    "pdf_readiness": {
                        "usable_item_keys": [ready_key, fill_key],
                        "missing_item_keys": [],
                    },
                }],
            }],
        }), encoding="utf-8")
        response = Path(self.holder.name) / "noop-r1-response.json"
        response.write_text(json.dumps({
            "stage1_result": {
                "action": "noop",
                "papers_pdf_downloaded": 2,
            },
        }), encoding="utf-8")

        payload = verifier._checkpoint_stage1_final(
            self.args(program_root=root, eval_response=response))
        self.assertEqual(payload["status"], "pass", payload)

    def test_install_reads_exact_professor_contact_commit_from_structured_lock(self):
        consumer = Path(self.holder.name) / "consumer"
        (consumer / ".agents/skills/professor-contact").mkdir(parents=True)
        (consumer / ".agents/skills/professor-contact/SKILL.md").write_text("installed", encoding="utf-8")
        (consumer / ".codex/agents").mkdir(parents=True)
        (consumer / ".codex/agents/professor-contact.toml").write_text("name='professor-contact'", encoding="utf-8")
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
