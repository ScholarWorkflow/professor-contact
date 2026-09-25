import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
WRAPPER = ROOT / "scripts" / "stage5_immutable.py"
RUNNER = ROOT / "scripts" / "contact_state.py"
CHECKER_ENV = "PROFESSOR_CONTACT_EVIDENCE_SCRIPT"

spec = importlib.util.spec_from_file_location("contact_state_test_helpers", HERE / "test_contact_state.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

BaseEnv = helpers.BaseEnv
parse = helpers.parse


def run_wrapper(*arguments):
    args = list(map(str, arguments))
    if args and args[0] in {"stage5-plan", "stage5-finalize"} and "--program-root" in args:
        root = Path(args[args.index("--program-root") + 1])
        template = root / "synthetic-template.md"
        followup = root / "synthetic-followup-template.md"
        if not template.exists():
            template.write_text("FIXED-BEGIN\n{{大学}}／{{研究科}}／{{先生名}}先生\nFIXED-SELFINTRO {{出身校}} {{氏名}}\n{{入学年度}} {{入学月}} {{専攻}} {{学位}}\nFIXED-INTEREST\n{{兴趣段}}\nFIXED-FUTURE\n{{未来志向}}\nFIXED-LEARNING {{学習中}}\n{{志望}}\nFIXED-END", encoding="utf-8")
        if not followup.exists():
            followup.write_text("FOLLOWUP-FIXED-BEGIN\n{{先生名}}先生\n{{大学}} {{研究科}} {{学位}}\n{{出身校}} {{氏名}}\n{{初回送信日}}\n{{研究主题}}\n{{メールアドレス}}\nFOLLOWUP-FIXED-END", encoding="utf-8")
        if "--template" not in args:
            args.extend(["--template", str(template)])
        if "--mode" in args and args[args.index("--mode") + 1] in {"both", "followup"} and "--followup-template" not in args:
            args.extend(["--followup-template", str(followup)])
    return subprocess.run([sys.executable, str(WRAPPER), *args], text=True, capture_output=True, check=False)


class TestStage5ImmutableTemplates(BaseEnv):
    prepare = helpers.TestStage5.prepare
    raw_result = helpers.TestStage5.raw_result
    choices = helpers.TestStage5.choices

    def write_inputs(self, g1, choices=None):
        raw = self.root / "raw.json"
        raw.write_text(json.dumps(self.raw_result(g1), ensure_ascii=False), encoding="utf-8")
        choice = self.root / "choices.json"
        choice.write_text(json.dumps(choices or self.choices(), ensure_ascii=False), encoding="utf-8")
        return raw, choice

    def test_finalize_without_full_body_humanizer_preserves_fixed_segments(self):
        g1 = self.prepare()
        raw, choice = self.write_inputs(g1)
        out = parse(run_wrapper("stage5-finalize", "--program-root", self.root,
                                "--result", raw, "--choices", choice))
        self.assertEqual(out["status"], "ok", out)
        txt = (self.prof_dir / "套磁邮件.txt").read_text(encoding="utf-8")
        for marker in ["FIXED-BEGIN", "FIXED-SELFINTRO", "FIXED-INTEREST",
                       "FIXED-FUTURE", "FIXED-LEARNING", "FIXED-END"]:
            self.assertIn(marker, txt)
        self.assertNotIn("{{", txt)
        md = (self.prof_dir / "套磁邮件.md").read_text(encoding="utf-8")
        self.assertIn("过稿: none", md)
        self.assertNotIn("过稿: humanizer-ja(business)", md)

    def test_dynamic_field_polish_provenance_is_explicit(self):
        g1 = self.prepare()
        raw, choice = self.write_inputs(g1)
        out = parse(run_wrapper("stage5-finalize", "--program-root", self.root,
                                "--result", raw, "--choices", choice,
                                "--polish-mode", "dynamic-fields-only"))
        self.assertEqual(out["status"], "ok", out)
        md = (self.prof_dir / "套磁邮件.md").read_text(encoding="utf-8")
        self.assertIn("过稿: humanizer-ja(dynamic-fields-only)", md)
        self.assertNotIn("过稿: humanizer-ja(business)", md)

    def test_full_body_humanized_argument_is_ignored(self):
        g1 = self.prepare()
        raw, choice = self.write_inputs(g1)
        malicious = self.root / "full-body-humanized.txt"
        malicious.write_text("Subject: hacked\n\nMUTATED-TEMPLATE", encoding="utf-8")
        out = parse(run_wrapper("stage5-finalize", "--program-root", self.root,
                                "--result", raw, "--choices", choice,
                                "--humanized", malicious))
        self.assertEqual(out["status"], "ok", out)
        txt = (self.prof_dir / "套磁邮件.txt").read_text(encoding="utf-8")
        self.assertIn("FIXED-BEGIN", txt)
        self.assertNotIn("MUTATED-TEMPLATE", txt)
        self.assertNotIn("Subject: hacked", txt)

    def test_first_and_followup_are_both_rendered_from_stable_templates(self):
        g1 = self.prepare()
        choices = dict(self.choices(), initial_sent_date="2026年9月1日")
        raw, choice = self.write_inputs(g1, choices)
        out = parse(run_wrapper("stage5-finalize", "--program-root", self.root,
                                "--mode", "both", "--result", raw,
                                "--choices", choice))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual({row["kind"] for row in out["emails"]}, {"initial", "followup"})
        followup = (self.prof_dir / "套磁跟进邮件.txt").read_text(encoding="utf-8")
        self.assertIn("FOLLOWUP-FIXED-BEGIN", followup)
        self.assertIn("FOLLOWUP-FIXED-END", followup)
        self.assertIn("2026年9月1日", followup)
        followup_md = (self.prof_dir / "套磁跟进邮件.md").read_text(encoding="utf-8")
        self.assertIn("过稿: none", followup_md)


class TestStage5ImmutableTargetedScope(BaseEnv):
    """Issue #59 T59-6: the supported immutable finalize entry inherits the
    runner's selected-email scope instead of adding a wrapper-only path."""

    def immutable_finalize(self, root, results, choices):
        return parse(run_wrapper(
            "stage5-finalize", "--program-root", root, "--result", results,
            "--choices", choices, "--email-id", helpers.ISSUE59_EMAIL_ID))

    def test_issue59_t59_6_wrapper_finalize_keeps_selected_email_scope(self):
        prepared = helpers.issue59_dependency_variant(self.root, "state", self)
        overview = prepared["overview"]
        a_dir = self.root / "教授研究" / "X分野" / helpers.ISSUE59_PROFESSOR
        b_dir = prepared["b_dir"]
        untouched = {
            str(path): Path(path).read_bytes()
            for path in (prepared["b_state"], prepared["b_verify"], overview)}
        out = self.immutable_finalize(self.root, prepared["results"],
                                      prepared["choices"])
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual([(row["email_id"], row["output_id"])
                          for row in out["emails"]],
                         [(helpers.ISSUE59_EMAIL_ID, helpers.ISSUE59_EMAIL_ID)])
        state = json.loads((a_dir / "套磁邮件状态.json").read_text(encoding="utf-8"))
        self.assertEqual(list(state["emails"]), [helpers.ISSUE59_EMAIL_ID])
        self.assertFalse((b_dir / "套磁邮件.md").exists())
        self.assertEqual(out["overview_md"], str(overview), out)
        for name, payload in untouched.items():
            self.assertEqual(Path(name).read_bytes(), payload, name)




# The wrapper executes a temporary copy of the runner; the copy's __file__
# lives in a scratch directory, so the installed-layout checker locator must
# be resolved from the real runner's location and pinned for the child via
# the documented injection point.
WRAPPER_CHECKER_STUB = (
    "import json, sys\n"
    "if '--check' in sys.argv:\n"
    "    print(json.dumps({'result': 'fresh', 'reasons': [], 'professors': "
    "[{'name': '試験 教授', 'result': 'fresh', 'reasons': []}]}))\n"
    "else:\n"
    "    print(json.dumps({'result': 'ok', 'action': 'unchanged'}))\n"
)


def _fresh_timestamp():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TestWrapperKeepsInstalledLayoutLocator(unittest.TestCase):
    """stage5-finalize through the wrapper must still certify contact-evidence
    freshness from the APM shared install layout (issue #31 completion
    criterion 3): the temp-copy runner must not lose the sibling
    professor-collector checker just because its __file__ is a scratch dir."""

    def setUp(self):
        self._saved_env = os.environ.get(CHECKER_ENV)
        os.environ.pop(CHECKER_ENV, None)
        self._temp = tempfile.TemporaryDirectory(prefix="stage5-wrapper-locator-")
        self.consumer = Path(self._temp.name)
        scripts = (self.consumer / ".agents" / "skills" /
                   "professor-contact" / "scripts")
        scripts.mkdir(parents=True)
        (scripts / "contact_state.py").write_text(
            RUNNER.read_text(encoding="utf-8"), encoding="utf-8")
        wrapper = scripts / "stage5_immutable.py"
        wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
        self.wrapper = wrapper
        sibling = (self.consumer / ".agents" / "skills" /
                   "professor-collector" / "scripts")
        sibling.mkdir(parents=True)
        (sibling / "contact_evidence.py").write_text(
            WRAPPER_CHECKER_STUB, encoding="utf-8")

    def tearDown(self):
        self._temp.cleanup()
        if self._saved_env is None:
            os.environ.pop(CHECKER_ENV, None)
        else:
            os.environ[CHECKER_ENV] = self._saved_env

    def _compile_fixture(self):
        fixture_root = self.consumer / "fixture" / "program"
        fixture_root.mkdir(parents=True)

        class _Fixture(BaseEnv):
            raw_result = helpers.TestStage5.raw_result
            choices = helpers.TestStage5.choices

            def setUp(inner):
                inner.root = fixture_root
                inner.prof_dir = (inner.root / "教授研究" / "X分野" /
                                  "試験 教授")
                (inner.prof_dir / "论文分析").mkdir(parents=True)
                inner.gap_quotes = {
                    "AAAA1111": "Future work will extend the synthetic comparison to a second input pattern.",
                    "BBBB2222": "We plan to test a second synthetic processing path.",
                }
                inner.papers = [
                    {"item_key": "AAAA1111", "title": "Synthetic comparison of input patterns",
                     "year": 2023, "month": 5, "authorship": "corresponding",
                     "abstract": "We study a synthetic comparison of input patterns.",
                     "has_pdf": True, "authors": ["Author One", "Example Professor"]},
                    {"item_key": "BBBB2222", "title": "Synthetic processing path evaluation",
                     "year": 2024, "month": 3, "authorship": "first",
                     "abstract": "A synthetic system for comparing two processing paths.",
                     "has_pdf": True, "authors": ["Example Professor"]},
                    {"item_key": "CCCC3333", "title": "Unrelated synthetic example",
                     "year": 2026, "month": 1, "authorship": "middle",
                     "abstract": "A deliberately unrelated synthetic example.",
                     "has_pdf": False, "authors": ["Other Author"]},
                ]
                for key, quote in inner.gap_quotes.items():
                    analysis = inner.prof_dir / "论文分析" / f"{key}.md"
                    analysis.write_text("# analysis\n", encoding="utf-8")
                    sidecar = helpers.make_sidecar(analysis, [quote])
                    for paper in inner.papers:
                        if paper["item_key"] == key:
                            paper["analysis_file"] = str(analysis)
                            paper["sidecar_file"] = str(sidecar)

            def tearDown(inner):
                pass

        env = _Fixture("setUp")
        env.setUp()
        env.stage3_run()
        (fixture_root / "synthetic-template.md").write_text(
            "FIXED-BEGIN\n{{大学}}／{{研究科}}／{{先生名}}先生\nFIXED-SELFINTRO {{出身校}} {{氏名}}\n"
            "{{入学年度}} {{入学月}} {{専攻}} {{学位}}\nFIXED-INTEREST\n{{兴趣段}}\nFIXED-FUTURE\n{{未来志向}}\n"
            "FIXED-LEARNING {{学習中}}\n{{志望}}\nFIXED-END", encoding="utf-8")
        # schema-2 artifact the wrapper-run finalize must certify as fresh
        record = {
            "professor": {"name": "試験 教授", "name_romaji": None},
            "official_emails": [],
            "paper_correspondence": [],
            "identity": {"matched_verified_contacts": 1,
                         "unmatched_verified_contacts": [],
                         "ambiguous_unpaired_records_ignored": 0},
            "verdict": "confirmed_cross_source",
            "confirmed_emails": ["faculty@example.test"],
            "conflicting_paper_emails": [],
            "current_email": "faculty@example.test",
        }
        artifact = {
            "schema": 2, "kind": "professor-contact-evidence",
            "generated_at": _fresh_timestamp(),
            "recent_paper_years": 5, "current_year": 2026,
            "scope": "workflow_evidence_not_send_time_authority",
            "sources": {}, "degraded": False, "source_errors": [],
            "professors": [record],
        }
        (fixture_root / "教授研究" / "_联系方式证据.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=1), encoding="utf-8")
        sel_input = fixture_root / "sel_input.json"
        sel_input.write_text(json.dumps({"selections": [{
            "professor": "試験 教授", "professor_dir": str(env.prof_dir),
            "collection_key": "DIR00001",
            "ideas": [{"id": "DIR00001_1"}]}]}, ensure_ascii=False), encoding="utf-8")
        out = parse(helpers.run_cli("stage4-finalize", "--program-root", fixture_root,
                                    "--selection-input", sel_input))
        self.assertEqual(out["status"], "ok", out)
        (fixture_root / "info.json").write_text(json.dumps({
            "university": "試験大学", "department": "試験研究科",
            "target": {"intake_year": 2027, "intake_term": "april"}}), encoding="utf-8")
        (fixture_root / "boshu_analysis.json").write_text(json.dumps({
            "exam_type": {"degree": "博士前期課程", "selection_name": "春季 テスト選抜 合成工学専攻"}
        }, ensure_ascii=False), encoding="utf-8")
        stat = (fixture_root / "info.json").stat()
        boshu_stat = (fixture_root / "boshu_analysis.json").stat()
        verify = {
            "professor": "試験 教授", "verified_at": "2026-08-27T16:00:00Z",
            "source_fingerprints": {
                "info_json": f"{fixture_root / 'info.json'}:{int(stat.st_mtime)}",
                "boshu_analysis": f"{fixture_root / 'boshu_analysis.json'}:{int(boshu_stat.st_mtime)}"},
            "items": {
                "email": {"verdict": "confirmed", "value": "faculty@example.test", "sources": []},
                "roster": {"verdict": "confirmed", "value": "X分野/教授 @P.1", "sources": []},
                "season": {"verdict": "confirmed", "value": "春季 少数名", "sources": []},
                "header": {"verdict": "confirmed", "value": "", "sources": []},
                "subject_batch": {"verdict": "confirmed", "value": "", "sources": []},
                "schedule": {"verdict": "unverified", "value": None, "sources": []},
                "consent": {"verdict": "unverified", "value": None, "sources": []},
                "warnings": []}}
        (env.prof_dir / "_contact_verify.json").write_text(
            json.dumps(verify, ensure_ascii=False, indent=1), encoding="utf-8")
        return env

    def test_finalize_through_wrapper_certifies_installed_layout_checker(self):
        env = self._compile_fixture()
        g1 = helpers.quote_id(env.gap_quotes["AAAA1111"])
        raw = self.consumer / "fixture" / "raw.json"
        raw.write_text(json.dumps(env.raw_result(g1), ensure_ascii=False),
                       encoding="utf-8")
        choice = self.consumer / "fixture" / "choices.json"
        choice.write_text(json.dumps(env.choices(), ensure_ascii=False),
                          encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(self.wrapper), "stage5-finalize",
             "--program-root", str(env.root),
             "--template", str(env.root / "synthetic-template.md"),
             "--result", str(raw),
             "--choices", str(choice), "--polish-mode", "none"],
            text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        state_path = env.prof_dir / "套磁邮件状态.json"
        self.assertTrue(state_path.is_file(), result.stdout + result.stderr)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        decisions = [
            entry.get("contact_evidence") or {}
            for entry in (state.get("emails") or {}).values()]
        self.assertTrue(decisions, state)
        for decision in decisions:
            self.assertEqual(decision.get("status"), "confirmed_cross_source",
                             decision)
            self.assertIsNone(decision.get("reason_code"), decision)
        self.assertNotIn("contact_evidence_check_unavailable",
                         json.dumps(state, ensure_ascii=False))
