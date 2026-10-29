"""Targeted Markdown-only translation checks; no model-quality claim."""
import json

import test_stage5_immutable as support

BaseEnv = support.BaseEnv
parse = support.parse
run_wrapper = support.run_wrapper


class TestEmailTranslation(BaseEnv):
    prepare = support.TestStage5ImmutableTemplates.prepare
    raw_result = support.TestStage5ImmutableTemplates.raw_result
    choices = support.TestStage5ImmutableTemplates.choices
    write_inputs = support.TestStage5ImmutableTemplates.write_inputs

    def setup_translation(self):
        gap = self.prepare()
        raw, choices = self.write_inputs(gap, {**self.choices(), "initial_sent_date": "2026年10月1日"})
        self.args = ["--program-root", self.root, "--email-pack", self.email_pack,
                     "--mode", "both", "--result", raw, "--choices", choices]
        drafts = parse(run_wrapper("stage5-plan", *self.args))["drafts"]
        self.translations = {row["output_id"]: {
            "source_text": row["translation_source"],
            "subject_zh": "首封主题" if row["kind"] == "initial" else "回复：首封主题",
            "body_zh": "这是首封核对译文。" if row["kind"] == "initial" else "这是跟进核对译文。",
        } for row in drafts}
        self.translation_path = self.root / "translations.json"
        self.drafts = drafts
        self.save_translation()
        return drafts

    def save_translation(self):
        self.translation_path.write_text(json.dumps(self.translations, ensure_ascii=False), encoding="utf-8")

    def finalize(self):
        return run_wrapper("stage5-finalize", *self.args, "--translations", self.translation_path)

    def outputs(self):
        return {p: p.read_bytes() for p in self.prof_dir.iterdir()
                if p.name in {"套磁邮件.md", "套磁邮件.txt", "套磁跟进邮件.md",
                              "套磁跟进邮件.txt", "套磁邮件状态.json"}}

    def test_both_translations_are_markdown_only(self):
        drafts = self.setup_translation()
        templates = {p: p.read_bytes() for p in self.root.glob("synthetic*template.md")}
        result = self.finalize()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(parse(result)["status"], "ok")
        for row in drafts:
            stem = "套磁邮件" if row["kind"] == "initial" else "套磁跟进邮件"
            md = (self.prof_dir / f"{stem}.md").read_text(encoding="utf-8")
            txt = (self.prof_dir / f"{stem}.txt").read_text(encoding="utf-8")
            translation = self.translations[row["output_id"]]
            self.assertEqual(txt, row["translation_source"])
            self.assertNotIn(translation["body_zh"], txt)
            self.assertIn("主题：" + translation["subject_zh"], md)
            self.assertIn(translation["body_zh"], md)
            self.assertLess(md.index("## 邮件正文"), md.index("## 中文译文"))
            self.assertLess(md.index("## 中文译文"), md.index("## 来源标注"))
        self.assertEqual(templates, {p: p.read_bytes() for p in templates})

    def test_stale_missing_and_manual_changes_preserve_outputs(self):
        drafts = self.setup_translation()
        self.assertEqual(parse(self.finalize())["status"], "ok")
        before = self.outputs()
        first_id, followup_id = (row["output_id"] for row in drafts)
        source = self.translations[first_id]["source_text"]
        self.translations[first_id]["source_text"] = source + "旧稿"
        self.save_translation()
        result = self.finalize()
        outcome = parse(result)
        self.assertEqual(outcome["status"], "error")
        self.assertEqual(outcome["reason_code"], "translation_stale")
        self.assertEqual(before, self.outputs())
        self.translations[first_id]["source_text"] = source
        followup = self.translations.pop(followup_id)
        self.save_translation()
        result = self.finalize()
        outcome = parse(result)
        self.assertEqual(outcome["status"], "error")
        self.assertEqual(outcome["reason_code"], "translation_missing")
        self.assertEqual(before, self.outputs())
        self.translations[followup_id] = followup
        self.save_translation()
        md = self.prof_dir / "套磁邮件.md"
        md.write_text(md.read_text(encoding="utf-8") + "\n用户手改\n", encoding="utf-8")
        before = self.outputs()
        result = self.finalize()
        outcome = parse(result)
        self.assertEqual(outcome["status"], "needs_decision")
        self.assertEqual(outcome["reason_code"], "manual_markdown_changed")
        self.assertEqual(before, self.outputs())
