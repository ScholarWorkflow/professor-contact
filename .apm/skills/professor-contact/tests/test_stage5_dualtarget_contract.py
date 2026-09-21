"""Stage 5 dual-target (Codex / OpenCode) source contracts and the installed
shared-skills locator layout (issue #31).

The source-level contracts lock the generator/validator documents against
re-importing OpenCode-only calling syntax as a cross-target API or reviving
the retired full-body humanizer path. The locator tests copy the real runner
into a consumer-like `.agents/skills` layout (APM's shared project-scope
install target for both Codex and OpenCode) and prove the sibling upstream
checker is discovered from the normal install — and that a fake producer
planted inside a program root is never used. All fixtures are hermetic: no
runtime locator injection, no user-global agent/skill state.
"""

import importlib.util
import os
import re
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"
SKILL_DIR = HERE.parent
RUNNER = SKILL_DIR / "scripts" / "contact_state.py"
SKILL_PATH = SKILL_DIR / "SKILL.md"
LEGACY_CONTRACT = SKILL_DIR / "docs" / "stage5-legacy-contract.md"
GENERATOR = AGENTS_DIR / "professor-contact-email-generator.agent.md"
VALIDATOR = AGENTS_DIR / "professor-contact-email-validator.agent.md"
CHECKER_ENV = "PROFESSOR_CONTACT_EVIDENCE_SCRIPT"

# Issue #43 freezes the public choices row, the runner-internal keys retired out
# of it, and the wording that keeps `email_address` under the verified recipient.
CHOICE_PUBLIC_KEYS = ("email_id", "first_choice", "signature_name", "learning",
                      "initial_sent_date", "followup_subject", "email_address")
RETIRED_CHOICE_KEY = re.compile(r"[`.](subject|alma_mater)`")
RETIREMENT_MARKERS = ("retired", "superseded", "whitelist", "白名单外", "rejected",
                      "拒绝", "invalid_choices_schema")
RECIPIENT_SUBORDINATION = ("only confirm", "never replace", "一份权威", "唯一", "只是",
                           "不能替换", "不得替换")

# Deterministic stand-in for professor-research's contact_evidence.py: the
# --check form prints a fixture freshness report (the locator tests only need
# the discovery + subprocess boundary, not the ladder business branches that
# test_contact_evidence_ladder.py already covers).
FRESH_CHECKER_STUB = (
    "import json, sys\n"
    "print(json.dumps({'result': 'fresh', 'reasons': [], 'professors': "
    "[{'name': '試験 教授', 'result': 'fresh', 'reasons': []}]}))\n"
)


def _frontmatter_and_body(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    end = lines.index("---", 1)
    return lines[1:end], "\n".join(lines[end + 1 :])


def _top_level_fields(frontmatter_lines):
    fields = {}
    for line in frontmatter_lines:
        if not line or line[0].isspace():
            continue
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


class Stage5DualTargetContractTests(unittest.TestCase):
    """Source contracts: harness calling surfaces and the humanizer boundary."""

    def setUp(self):
        self.generator_text = GENERATOR.read_text(encoding="utf-8")
        _, self.generator_body = _frontmatter_and_body(GENERATOR)
        self.skill_text = SKILL_PATH.read_text(encoding="utf-8")

    def _section(self, body, start_marker, end_marker):
        start = body.index(start_marker)
        end = body.index(end_marker) if end_marker else len(body)
        return body[start:end]

    def _statements(self, section):
        """Split a contract section into caller-facing statements: a new
        top-level bullet or a blank line starts one, so wrapped text stays with
        the bullet it belongs to."""
        blocks = [""]
        for line in section.splitlines():
            if line.startswith("- ") or not line.strip():
                blocks.append(line)
            else:
                blocks[-1] = blocks[-1] + "\n" + line
        return [block for block in blocks if block.strip()]

    def _sentences(self, statement):
        return [part for part in re.split(r"。|(?<=\.)\s+", statement) if part.strip()]

    def assert_public_choice_contract(self, label, section):
        """One public-input statement must advertise exactly the frozen keys,
        name a retired key only inside an explicit retirement clause, and keep
        `email_address` subordinate to the verified recipient."""
        for key in CHOICE_PUBLIC_KEYS:
            self.assertIn(f"`{key}`", section, f"{label}: public key {key} missing")
        for statement in self._statements(section):
            # A retired key may only appear in a sentence that itself says the
            # key is retired, so adding one back to the advertised list fails.
            for sentence in self._sentences(statement):
                for match in RETIRED_CHOICE_KEY.finditer(sentence):
                    self.assertTrue(
                        any(marker in sentence for marker in RETIREMENT_MARKERS),
                        f"{label}: retired key {match.group(1)} advertised as "
                        f"usable: {sentence}")
        authority = [statement for statement in self._statements(section)
                     if "email_address" in statement and "items.email.value" in statement]
        self.assertTrue(authority,
                        f"{label}: choices.email_address is never tied to the "
                        f"verified recipient")
        for statement in authority:
            self.assertIn("recipient_conflict", statement, label)
            self.assertTrue(any(marker in statement for marker in RECIPIENT_SUBORDINATION),
                            f"{label}: email_address not kept subordinate to "
                            f"items.email.value: {statement}")

    def test_generator_document_has_explicit_dual_target_branches(self):
        body = self.generator_body
        openecode_start = body.index("### OpenCode branch")
        codex_start = body.index("### Codex branch")
        humanizer_start = body.index("### humanizer-ja stage-5 constraints")
        self.assertLess(openecode_start, codex_start)
        self.assertLess(codex_start, humanizer_start)

        opencode = self._section(body, "### OpenCode branch", "### Codex branch")
        # OpenCode keeps its native tool surface: Task delegation, native
        # skill loading, question interaction, official web tools.
        self.assertIn("task(subagent_type: \"professor-contact-email-validator\"", opencode)
        self.assertIn("skill(name: \"humanizer-ja\")", opencode)
        self.assertIn("question", opencode)
        self.assertIn("websearch", opencode)
        self.assertIn("webfetch", opencode)

        codex = self._section(body, "### Codex branch",
                              "### humanizer-ja stage-5 constraints")
        # Codex delegates to installed named agents and official surfaces only.
        self.assertIn("`professor-contact-email-generator`", codex)
        self.assertIn("`professor-contact-email-validator`", codex)
        self.assertIn("`humanizer-ja`", codex)
        self.assertIn("web search", codex)

    def test_opencode_call_signatures_stay_inside_the_generator_opencode_branch(self):
        body = self.generator_body
        opencode_start = body.index("### OpenCode branch")
        codex_start = body.index("### Codex branch")
        for needle in ("task(subagent_type", "skill(name:"):
            for match in re.finditer(re.escape(needle), body):
                self.assertGreaterEqual(
                    match.start(), opencode_start,
                    f"{needle!r} must live in the OpenCode branch")
                self.assertLess(
                    match.start(), codex_start,
                    f"{needle!r} must not leak into the Codex branch")
        self.assertNotIn("question(", body)
        # `spawn_agent` is a documented Codex multi-agent tool; the generator
        # body stays off its concrete envelope (issue #51).
        self.assertNotRegex(body, r"spawn_agent\s*\(")

    def test_codex_branch_stops_at_needs_input_without_autofill(self):
        codex = self._section(self.generator_body, "### Codex branch",
                              "### humanizer-ja stage-5 constraints")
        self.assertIn("needs_input", codex)
        self.assertIn("never auto-pick", codex)
        self.assertIn("never fabricate", codex)
        self.assertIn("never write the final email", codex)
        self.assertIn("continuation/resume", codex)

    def test_stage5_choices_are_a_shared_business_input_not_a_runtime_api(self):
        body = self.generator_body
        self.assertIn("optional `choices`", body)
        for needle in ("canonical JSON", "email_id", "first_choice", "signature_name",
                       "initial_sent_date", "temporary", "not persisted"):
            self.assertIn(needle, body)

        opencode = self._section(body, "### OpenCode branch", "### Codex branch")
        codex = self._section(body, "### Codex branch",
                              "### humanizer-ja stage-5 constraints")
        self.assertIn("question", opencode)
        self.assertIn("choices", opencode)
        self.assertIn("--choices", codex)
        self.assertIn("原样", codex)
        self.assertNotIn("question", codex)
        self.assertNotRegex(codex, r"typed\s+spawn|spawn\s+parameter")

        self.assertIn("Stage 4 selection 与 Stage 5 choices 分开", self.skill_text)
        self.assertIn("choices", self.skill_text)
        self.assertIn("not persisted", body)
        legacy = LEGACY_CONTRACT.read_text(encoding="utf-8")
        for needle in ("optional", "choices", "canonical JSON", "first_choice",
                       "initial_sent_date"):
            self.assertIn(needle, legacy)

        # The retired keys stay out of what the authoritative public-input
        # statements advertise, on every target's projection.
        self.assert_public_choice_contract(
            "generator agent",
            self._section(body, "## Stage 5 caller Input contract",
                          "## Direction provenance"))
        self.assert_public_choice_contract(
            "SKILL.md",
            self._section(self.skill_text, "### 5.0 Stage 5 caller choices contract",
                          "### 5.1 "))
        self.assert_public_choice_contract(
            "legacy contract",
            self._section(legacy, "Issue #43 caller rule:", "**Runner 分工**"))

    def test_validator_requires_both_first_and_followup_validation(self):
        body = self.generator_body
        self.assertIn(
            "Run `professor-contact-email-validator` on both rendered first "
            "and follow-up `.md` files", body)

    def test_presend_verification_is_a_hard_executable_gate(self):
        body = self.generator_body
        for needle in (
            "run `contact_state.py stage5-plan` without `--result` and without `--choices`",
            "complete Step 2.5 and write the full professor-level `_contact_verify.json`",
            "until every selected professor reports `verify: ok`",
            "ordinary `verify_missing` / `needs_recheck` is work for Step 2.5",
            "return to Step 2.5, refresh the cache",
        ):
            self.assertIn(needle, body)
        start = body.index("stage5-plan` (no result/choices)")
        self.assertLess(start, body.index("model result JSON", start))
        for needle in ("verify: ok", "verify_missing", "不带 `--result`/`--choices`"):
            self.assertIn(needle, self.skill_text)

    def test_validator_machine_name_and_network_deny_are_intact(self):
        frontmatter, body = _frontmatter_and_body(VALIDATOR)
        fields = _top_level_fields(frontmatter)
        self.assertEqual(fields.get("name"), "professor-contact-email-validator")
        frontmatter_text = "\n".join(frontmatter)
        self.assertIn("webfetch: deny", frontmatter_text)
        self.assertIn("websearch: deny", frontmatter_text)
        # The read-scope contract stays: upstream paper-fact files and the
        # network are forbidden, and no hard ACL is claimed for the Codex
        # projection (workflow contract instead).
        for forbidden in ("候选分析 Markdown", "_index.json", "sidecar",
                          "PDF", "Zotero", "网络"):
            self.assertIn(forbidden, body)
        self.assertIn("硬权限隔离", body)

    def test_stage5_skill_documents_keep_humanizer_dynamic_fields_only(self):
        skill = self.skill_text
        self.assertIn("### 5.6 humanizer-ja 动态字段润色（可选，模板拼装前）", skill)
        self.assertIn("--polish-mode dynamic-fields-only", skill)
        self.assertIn("一律不进入 `humanizer-ja`", skill)
        # The retired full-body path must be gone from the current contract.
        self.assertNotIn("用 `--humanized-map` 一一对应", skill)
        self.assertNotIn("分别对两封邮件正文（Subject + 正文）过一遍", skill)
        self.assertNotIn("拼装+交互 → **过稿**", skill)
        self.assertNotIn("humanizer-ja 过稿", skill)

    def test_generator_wrapper_instructions_reject_full_body_inputs(self):
        body = self.generator_body
        self.assertIn("--polish-mode dynamic-fields-only", body)
        self.assertIn("Do not pass `--humanized` or `--humanized-map`", body)
        self.assertIn("byte-identical", body)
        self.assertIn("never enters the humanizer",
                      self._section(body, "### humanizer-ja stage-5 constraints",
                                    None))

    def test_legacy_stage5_contract_carries_supersession_banner(self):
        legacy = LEGACY_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("superseded humanizer & calling rules", legacy)
        self.assertIn("dynamic-fields-only", legacy)
        self.assertIn("OpenCode-native illustrations", legacy)
        self.assertIn("`--humanized`/`--humanized-map` inputs are ignored", legacy)


class InstalledSharedSkillsLocatorTests(unittest.TestCase):
    """The runner must discover the sibling upstream checker from APM's
    shared project-scope install layout, and never from a program root."""

    def setUp(self):
        self._saved_env = os.environ.get(CHECKER_ENV)
        os.environ.pop(CHECKER_ENV, None)
        self._temp = tempfile.TemporaryDirectory(prefix="stage5-locator-")
        self.consumer = Path(self._temp.name)
        self._module_counter = 0

    def tearDown(self):
        self._temp.cleanup()
        if self._saved_env is None:
            os.environ.pop(CHECKER_ENV, None)
        else:
            os.environ[CHECKER_ENV] = self._saved_env

    def _load_installed_runner(self):
        self._module_counter += 1
        target = (self.consumer / ".agents" / "skills" / "professor-contact" /
                  "scripts" / "contact_state.py")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")
        spec = importlib.util.spec_from_file_location(
            f"contact_state_installed_{self._module_counter}", target)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _write_sibling_checker(self):
        script_dir = (self.consumer / ".agents" / "skills" /
                      "professor-collector" / "scripts")
        script_dir.mkdir(parents=True, exist_ok=True)
        script = script_dir / "contact_evidence.py"
        script.write_text(FRESH_CHECKER_STUB, encoding="utf-8")
        return script

    def test_installed_shared_skills_layout_locator_finds_sibling(self):
        # APM installs both targets' project-scope skills side by side under
        # .agents/skills/<skill>/; the runner's own install location must be
        # enough to find the sibling producer script — no runtime injection,
        # no registered checkout, no user-global state.
        sibling = self._write_sibling_checker()
        module = self._load_installed_runner()
        program_root = self.consumer / "program"
        program_root.mkdir()

        self.assertEqual(module.upstream_check_script(), sibling.resolve())
        report, error = module.run_contact_evidence_check(program_root)
        self.assertIsNone(error)
        self.assertEqual(report["result"], "fresh")
        professor = module.professor_source_state(report, "試験 教授")
        self.assertIsNotNone(professor)
        self.assertEqual(professor["result"], "fresh")

    def test_program_root_fake_producer_is_never_used(self):
        # A producer script planted inside the program root (user data
        # territory) must be invisible to the locator: without a real install
        # the checker is simply missing and the ladder fails closed.
        module = self._load_installed_runner()
        program_root = self.consumer / "program"
        fake = program_root / ".apm" / "skills" / "professor-collector" / "scripts"
        fake.mkdir(parents=True)
        (fake / "contact_evidence.py").write_text(FRESH_CHECKER_STUB,
                                                  encoding="utf-8")

        self.assertIsNone(module.upstream_check_script())
        report, error = module.run_contact_evidence_check(program_root)
        self.assertIsNone(report)
        self.assertEqual(error, "script_missing")


if __name__ == "__main__":
    unittest.main()
