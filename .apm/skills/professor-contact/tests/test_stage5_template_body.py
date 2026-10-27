import contextlib
import importlib.util
import io
import unittest
from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "contact_state.py"
SPEC = importlib.util.spec_from_file_location("contact_state_template_test", RUNNER)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class TestStage5TemplateBody(unittest.TestCase):
    def test_followup_date_is_formatted_only_for_body(self):
        for original, expected in (("2026-10-01", "2026年10月1日"),
                                   ("2026年10月1日", "2026年10月1日"),
                                   (None, "")):
            with self.subTest(original=original):
                choices = {"initial_sent_date": original}
                draft, protected, _ = runner.assemble_followup_draft(
                    {"email_id": "synthetic-email"}, choices, {},
                    "先日{{初回送信日}}にご連絡しました。")
                self.assertIn(f"先日{expected}にご連絡しました。", draft)
                if expected:
                    self.assertIn(expected, protected)
                self.assertEqual(choices, {"initial_sent_date": original})

    def assemble(self, template, *, followup=False, **choices):
        email = {"email_id": "synthetic-email", "professor": "試験 教授"}
        choices = {"signature_name": "試験 太郎", "initial_sent_date": "2026年10月1日",
                   **choices}
        if followup:
            return runner.assemble_followup_draft(email, choices, {}, template)[0]
        return runner.assemble_draft(email, {}, choices, {}, template)[0]

    def test_default_alma_mater_does_not_repeat_template_suffix(self):
        for followup in (False, True):
            with self.subTest(followup=followup):
                draft = self.assemble("{{出身校}}出身の{{氏名}}です。", followup=followup)
                self.assertIn("総合大学出身の試験 太郎です。", draft)
                self.assertNotIn("出身出身", draft)

    def test_explicit_alma_mater_is_preserved(self):
        for followup in (False, True):
            with self.subTest(followup=followup):
                draft = self.assemble("{{出身校}}出身の{{氏名}}です。", followup=followup,
                                      alma_mater="試験大学")
                self.assertIn("試験大学出身の試験 太郎です。", draft)

    def test_fenced_body_excludes_template_instructions(self):
        template = ("# 套磁模板\n\n> 请填写 {{}} 占位符。\n\n```text\n"
                    "{{先生名}}先生\n{{出身校}}出身の{{氏名}}です。\n固定の結び。\n"
                    "```\n\n## 使用说明\n{{未知字段}} 只是说明中的例子。\n")
        for followup in (False, True):
            with self.subTest(followup=followup):
                draft = self.assemble(template, followup=followup)
                self.assertEqual(draft.split("\n\n", 1)[1],
                                 "試験 教授先生\n総合大学出身の試験 太郎です。\n固定の結び。\n")

    def test_body_section_excludes_surrounding_instructions(self):
        template = ("# 套磁模板\n\n说明中的 {{}} 不是正文。\n\n## 邮件正文\n\n"
                    "{{先生名}}先生\n固定の本文。\n\n## 使用说明\n{{例子}}\n")
        for followup in (False, True):
            with self.subTest(followup=followup):
                draft = self.assemble(template, followup=followup)
                self.assertEqual(draft.split("\n\n", 1)[1], "試験 教授先生\n固定の本文。\n")

    def test_trailing_instruction_section_is_not_body(self):
        template = "{{先生名}}先生\n固定の本文。\n\n## 使用说明\n使用 {{}} 填充。\n"
        draft = self.assemble(template)
        self.assertEqual(draft.split("\n\n", 1)[1], "試験 教授先生\n固定の本文。\n")

    def test_plain_template_preserves_fixed_text_and_whitespace(self):
        template = "\n{{先生名}}先生\n\n  固定の本文。\n> 固定の引用。\n\n"
        draft = self.assemble(template)
        self.assertEqual(draft.split("\n\n", 1)[1], template.replace("{{先生名}}", "試験 教授"))

    def test_body_heading_selects_body_block_over_instruction_examples(self):
        template = ("# 模板\n\n```text\n{{说明示例}}\n```\n\n## 正文\n\n"
                    "~~~text\n{{先生名}}先生\n# 固定の見出し\n~~~\n\n## 使用说明\n{{}}\n")
        draft = self.assemble(template)
        self.assertEqual(draft.split("\n\n", 1)[1], "試験 教授先生\n# 固定の見出し\n")

    def test_ambiguous_or_unclosed_body_is_rejected(self):
        templates = ("```text\n本文\n", "```text\n本文\n```\n```text\n別の本文\n```\n",
                     "## 正文\n本文\n## 邮件正文\n別の本文\n")
        for template in templates:
            with self.subTest(template=template):
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                    self.assemble(template)

    def test_unresolved_body_placeholder_is_rejected(self):
        for followup in (False, True):
            for template in ("{{未知字段}}", "{{}}", "```text\n{{未知字段}}\n```",
                             "## 正文\n{{}}\n## 使用说明\n说明\n"):
                with self.subTest(followup=followup, template=template):
                    with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                        self.assemble(template, followup=followup)

