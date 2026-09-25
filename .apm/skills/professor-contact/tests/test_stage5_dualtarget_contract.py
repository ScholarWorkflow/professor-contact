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

# Issue #43 freezes the public choices row. Natural-language explanations are
# not machine schema: behavior tests own retirement / recipient-authority
# semantics, while this source contract checks only the formal public fields.
CHOICE_PUBLIC_KEYS = ("email_id", "first_choice", "signature_name", "learning",
                      "initial_sent_date", "followup_subject", "email_address")

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

    def _declared_public_choice_keys(self, label, section):
        """Return only the keys named by the section's authoritative public-schema
        declaration.  Other backticked names in retirement/authority clauses are
        deliberately outside this declaration."""
        for statement in self._statements(section):
            flat = " ".join(statement.split())
            marker = next(
                (candidate for candidate in (
                    "public row schema is exactly",
                    "公开字段只有这七个",
                ) if candidate in flat),
                None,
            )
            if marker is None:
                continue
            declaration = flat.split(marker, 1)[1]
            if marker == "公开字段只有这七个":
                declaration = declaration.split("。", 1)[0]
            else:
                declaration = re.split(
                    r"(?:\.\s+Anything outside it|:\s*any other key)",
                    declaration,
                    maxsplit=1,
                )[0]
            return tuple(re.findall(r"`([a-z][a-z0-9_]*)`", declaration))
        self.fail(f"{label}: authoritative public choices schema declaration missing")

    def assert_public_choice_contract(self, label, section):
        """The natural-language documents expose the same formal caller schema.

        Do not infer rejection semantics for non-public compatibility keys from
        prose here. This static contract checks only the formally advertised
        caller field names and that recipient authority is referenced beside the
        caller field; recipient-authority behavior stays covered through the
        public runner path in test_contact_state.py.
        """
        declared = self._declared_public_choice_keys(label, section)
        self.assertCountEqual(
            declared,
            CHOICE_PUBLIC_KEYS,
            f"{label}: public choices schema must be exactly the frozen seven keys",
        )
        authority = [
            statement for statement in self._statements(section)
            if "email_address" in statement and "items.email.value" in statement
        ]
        self.assertTrue(
            authority,
            f"{label}: choices.email_address must be documented together with "
            f"the verified items.email.value authority",
        )

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

        opencode = self._section(body, "### OpenCode branch", "### Codex branch")
        codex = self._section(body, "### Codex branch",
                              "### humanizer-ja stage-5 constraints")
        self.assertIn("choices", opencode)
        self.assertIn("question", opencode)
        self.assertIn("choices", codex)
        self.assertIn("--choices", codex)
        self.assertNotIn("question(", codex)
        self.assertNotIn("task(subagent_type", codex)

        legacy = LEGACY_CONTRACT.read_text(encoding="utf-8")

        # The authoritative public-input declarations, rather than incidental
        # wording, are the source-level contract. Non-public compatibility-key
        # semantics are intentionally outside this acceptance; runner tests own
        # recipient-authority behavior.
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


# Issue #59 T59-7 reads the caller documents, so it resolves the installed
# projection first (the formal clean consumer has no .apm/agents tree at all)
# and only falls back to the repository source.
ISSUE59_GENERATOR_CANDIDATES = (
    REPO_ROOT / ".opencode" / "agents" / "professor-contact-email-generator.md",
    REPO_ROOT / ".agents" / "agents" / "professor-contact-email-generator.md",
    GENERATOR,
)

# The markers below express contract semantics, not a frozen prose sentence.
# T59-7 deliberately evaluates the authoritative targeted-scope section as a
# whole and then its clauses; subordinate bullets/paragraphs do not need to
# repeat --email-id merely to satisfy the test.
ISSUE59_T59_7_ITEMS = (
    ("keep one selected email_id across the plan and immutable finalize calls",
     (("stage5-plan",), ("stage5-finalize",), ("email_id", "--email-id"),
      ("same", "同一", "相同"))),
    ("run the validator only for the selected rendered outputs",
     (("professor-contact-email-validator",),
      ("selected", "被选", "本次渲染"),
      ("rendered", "render", "渲染", "output", "输出"),
      ("only", "只", "仅"))),
    ("write only the selected output ids before recording validation",
     (("validation file", "validation 文件", "校验文件"),
      ("selected", "被选", "本次渲染"),
      ("output id", "output_id", "output ids", "输出的 id", "输出 id", "输出 ID"),
      ("stage5-record-validation",),
      ("only", "只", "仅"))),
    ("keep stage5-record-validation on its existing row-scoped contract",
     (("stage5-record-validation",), ("--professor-dir",), ("--validation-file",),
      ("--email-id",), ("no", "not", "never", "不", "不得", "无需", "禁止"))),
)


def _issue59_document_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return _frontmatter_and_body(path)[1] if text.startswith("---\n") else text


def _issue59_targeted_scope_section(body: str) -> str:
    """Return the smallest heading section carrying the targeted Stage-5 contract.

    The acceptance contract is section-scoped.  A harmless Markdown refactor
    must not fail merely because --email-id moved to the heading/intro while
    the subordinate bullets retained the same semantics.
    """
    lines = body.splitlines()
    candidates = []
    for index, line in enumerate(lines):
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if not heading:
            continue
        level = len(heading.group(1))
        end = index + 1
        while end < len(lines):
            next_heading = re.match(r"^(#{1,6})\s+(.+)$", lines[end])
            if next_heading and len(next_heading.group(1)) <= level:
                break
            end += 1
        section = "\n".join(lines[index:end]).strip()
        if ("--email-id" in section and
                "stage5-plan" in section and "stage5-finalize" in section and
                "professor-contact-email-validator" in section and
                "stage5-record-validation" in section):
            candidates.append(section)
    return min(candidates, key=len) if candidates else ""


def _issue59_contract_units(section: str) -> list:
    """Split one contract section into semantic clauses without freezing layout."""
    units, current = [], []
    for line in section.splitlines() + [""]:
        starts = not line.strip() or re.match(r"(?:[-*]|\d+\.)\s", line)
        if starts:
            block = "\n".join(current).strip()
            if block:
                units.append(block)
            current = [line] if line.strip() else []
        else:
            current.append(line)
    return units


class Issue59TargetedScopeDocumentContractTests(unittest.TestCase):
    """T59-7: current Stage-5 caller docs keep selected-output scope."""

    def setUp(self):
        self.generator = next((path for path in ISSUE59_GENERATOR_CANDIDATES
                               if path.is_file()), None)
        self.documents = {
            "generator": self.generator,
            "SKILL.md": SKILL_PATH,
            "workflow-reference": SKILL_DIR / "docs" / "workflow-reference.md",
        }

    def test_issue59_t59_7_targeted_scope_documents_hold_selected_output_scope(self):
        self.assertIsNotNone(
            self.generator,
            f"no generator document among {ISSUE59_GENERATOR_CANDIDATES}")
        for label, path in self.documents.items():
            with self.subTest(document=label):
                self.assertTrue(path.is_file(), f"{label}: missing {path}")
                section = _issue59_targeted_scope_section(
                    _issue59_document_body(path))
                self.assertTrue(
                    section,
                    f"{label}: no authoritative --email-id Stage-5 scope section in {path}")
                units = _issue59_contract_units(section)
                for item, token_groups in ISSUE59_T59_7_ITEMS:
                    with self.subTest(document=label, item=item):
                        matched = []
                        for unit in units:
                            lowered = unit.lower()
                            if all(any(token.lower() in lowered for token in group)
                                   for group in token_groups):
                                matched.append(unit)
                        self.assertTrue(
                            matched,
                            f"{label}: the targeted-scope section never states {item}")


if __name__ == "__main__":
    unittest.main()
