import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
WRAPPER = ROOT / "scripts" / "stage5_immutable.py"

spec = importlib.util.spec_from_file_location("contact_state_test_helpers", HERE / "test_contact_state.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

BaseEnv = helpers.BaseEnv
TestStage5 = helpers.TestStage5
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
    prepare = TestStage5.prepare
    raw_result = TestStage5.raw_result
    choices = TestStage5.choices

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
