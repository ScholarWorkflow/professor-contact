import argparse
import contextlib
import importlib.util
import io
import json
import re
import sys
import unittest
from pathlib import Path, PurePosixPath


HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"
STAGE1_AGENT = REPO_ROOT / ".apm" / "agents" / "professor-contact-downloader.agent.md"
STAGE2_OPENCODE = (
    REPO_ROOT
    / "packages"
    / "professor-contact-opencode"
    / ".apm"
    / "agents"
    / "professor-contact-analyzer.agent.md"
)
STAGE2_CODEX = (
    REPO_ROOT
    / "packages"
    / "professor-contact-codex"
    / ".apm"
    / "agents"
    / "professor-contact-analyzer.agent.md"
)
TARGET_NAME = "套磁目标.json"
STAGE1_NAME = "套磁阶段1候选.json"
PROGRAM_STATE_DIR = "教授研究"


def _load_fixture_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


stage1_fixture = _load_fixture_module(
    "issue65_gate2_stage1_fixture", HERE / "test_stage1_candidates.py"
)
stage2_fixture = _load_fixture_module(
    "issue65_gate2_stage2_fixture", HERE / "test_contact_state.py"
)


def _fenced(text: str, language: str | None = None) -> list[str]:
    tag = language if language is not None else r"[a-zA-Z0-9_-]*"
    return re.findall(rf"```{tag}[^\n]*\r?\n(.*?)```", text, flags=re.DOTALL)


def _bash_blocks(text: str) -> list[str]:
    return _fenced(text, r"(?:bash|shell|sh)")


def _json_blocks(text: str) -> list[dict]:
    payloads = []
    for block in _fenced(text, "json"):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _task_prompt(text: str, agent_name: str) -> list[str]:
    pattern = re.compile(
        r'task\(subagent_type:\s*"'
        + re.escape(agent_name)
        + r'"[^)]*?prompt:\s*"(?P<prompt>[^"]*)"'
    )
    return [match.group("prompt") for match in pattern.finditer(text)]


_PATH_STOP = set(" \t\n\"'`(){}[],;|&，。；：（）「」、")


def _parent_of_reference(token: str) -> str:
    return PurePosixPath(token).parent.name.strip("<>")


def _state_reference_scopes(text: str, filename: str) -> tuple[list[str], list[str], list[str]]:
    local: list[str] = []
    program: list[str] = []
    unbound: list[str] = []
    for match in re.finditer(re.escape(filename), text):
        start = match.start()
        if start == 0 or text[start - 1] != "/":
            unbound.append(filename)
            continue
        cursor = start
        while cursor > 0 and text[cursor - 1] not in _PATH_STOP:
            cursor -= 1
        token = text[cursor : start + len(filename)]
        bucket = program if _parent_of_reference(token) == PROGRAM_STATE_DIR else local
        bucket.append(token)
    return local, program, unbound


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _state_parent(value: str, filename: str) -> str | None:
    path = PurePosixPath(value)
    if path.name != filename:
        return None
    return str(path.parent)


def _transaction_parent(record: dict) -> str | None:
    strings = list(_strings(record))
    target_parents = {
        parent
        for value in strings
        if (parent := _state_parent(value, TARGET_NAME)) is not None
    }
    stage1_parents = {
        parent
        for value in strings
        if (parent := _state_parent(value, STAGE1_NAME)) is not None
    }
    if len(target_parents) != 1 or target_parents != stage1_parents:
        return None
    return next(iter(target_parents))


def _display_names(value) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        professor = value.get("professor")
        if isinstance(professor, str):
            names.add(professor)
        professors = value.get("professors")
        if isinstance(professors, list):
            names.update(item for item in professors if isinstance(item, str))
    return names


def _looks_display_key(key: str, parent: str, displays: set[str]) -> bool:
    return key in displays or key == PurePosixPath(parent).name.strip("<>")


def _has_display_keyed_machine_map(value, inherited_displays: set[str] | None = None) -> bool:
    displays = set(inherited_displays or ()) | _display_names(value)
    if isinstance(value, dict):
        if value and all(isinstance(item, str) for item in value.values()):
            path_rows = []
            for key, item in value.items():
                parent = _state_parent(item, TARGET_NAME) or _state_parent(item, STAGE1_NAME)
                if parent is not None:
                    path_rows.append((key, parent))
            if len(path_rows) == len(value):
                if any(_looks_display_key(key, parent, displays) for key, parent in path_rows):
                    return True

        if value and all(isinstance(item, dict) for item in value.values()):
            parents = [_transaction_parent(item) for item in value.values()]
            if all(parent is not None for parent in parents):
                for (key, record), parent in zip(value.items(), parents):
                    record_displays = displays | _display_names(record)
                    if _looks_display_key(key, parent, record_displays):
                        return True

        return any(
            _has_display_keyed_machine_map(item, displays) for item in value.values()
        )
    if isinstance(value, list):
        return any(_has_display_keyed_machine_map(item, displays) for item in value)
    return False


class Issue65Gate2Stage1Tests(unittest.TestCase):
    def setUp(self):
        self.env = stage1_fixture.Stage1CandidateTests(
            "test_selected_directions_keep_separate_candidate_sets_with_shared_paper_once"
        )
        self.env.setUp()
        self.addCleanup(self.env.tearDown)

    def test_issue65_stage1_professor_local_authority_and_isolation(self):
        root = self.env.root
        legacy_snapshot = root / "教授研究" / STAGE1_NAME
        a_dir = stage1_fixture.same_name_professor(root, "labA", "fp-a")
        b_dir = stage1_fixture.same_name_professor(root, "labB", "fp-b")
        a_target = a_dir / TARGET_NAME
        b_target = b_dir / TARGET_NAME
        a_state = stage1_fixture.professor_local_state(a_dir)
        b_state = stage1_fixture.professor_local_state(b_dir)

        stage1_fixture.build(root, b_target)
        self.assertTrue(b_state.is_file())
        legacy_snapshot.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "professor-contact-stage1",
                    "updated_at": None,
                    "professors": [],
                    "sentinel": "issue-65-legacy-aggregate-sentinel",
                },
                ensure_ascii=False,
                indent=1,
            )
            + "\n",
            encoding="utf-8",
        )
        b_before = b_state.read_bytes()
        legacy_before = legacy_snapshot.read_bytes()

        guard = stage1_fixture.ForbiddenAuthorityGuard([b_state, legacy_snapshot])
        with guard:
            _first, first_payload = stage1_fixture.build(root, a_target)
            self.assertEqual(first_payload.get("status"), "ok")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                verified = stage1_fixture.stage1.verify_command(root, a_target)
            self.assertEqual(verified.get("status"), "ok")
            _again, again_payload = stage1_fixture.build(root, a_target)
            self.assertEqual(again_payload.get("status"), "ok")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                reverified = stage1_fixture.stage1.verify_command(root, a_target)
            self.assertEqual(reverified.get("status"), "ok")
        self.assertEqual(guard.accesses, [], f"foreign Stage-1 authority accessed: {guard.accesses}")
        self.assertEqual(b_state.read_bytes(), b_before)
        self.assertEqual(legacy_snapshot.read_bytes(), legacy_before)

        # A missing state must not be substituted by the same-display-name B state.
        a_before = a_state.read_bytes()
        a_state.unlink()
        guard = stage1_fixture.ForbiddenAuthorityGuard([b_state, legacy_snapshot])
        rejected = False
        try:
            with guard, contextlib.redirect_stdout(io.StringIO()):
                result = stage1_fixture.stage1.verify_command(root, a_target)
            rejected = not (isinstance(result, dict) and result.get("status") == "ok")
        except SystemExit:
            rejected = True
        finally:
            a_state.write_bytes(a_before)
        self.assertTrue(rejected, "verify accepted B as A when A Stage-1 state was missing")
        self.assertEqual(guard.accesses, [], f"missing-A verify accessed B/legacy: {guard.accesses}")


class Issue65Gate2Stage2Tests(stage2_fixture.Issue65Stage2BindingEnv):
    def _raw_preflight(self):
        args = argparse.Namespace(
            program_root=str(self.root),
            professor=self.DISPLAY,
            target_file=str(self.a_target),
            paper_analysis="relevant",
            gap_scope="selected_direction",
            freshness_scope="shortlist",
            max_relevant_papers=None,
        )
        return self._capture(stage2_fixture.contact_state.cmd_stage2_preflight, args)

    @staticmethod
    def _is_rejected(text: str, code) -> bool:
        if code is not None:
            return True
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return True
        return not (isinstance(payload, dict) and payload.get("status") == "ok")

    def test_issue65_stage2_exact_stage1_binding_lifecycle(self):
        # A missing local state cannot fall through to the same-display-name B state.
        a_snapshot_before = self.a_snapshot.read_bytes()
        outputs_before_missing = self.outputs_state()
        self.a_snapshot.unlink()
        guard = self.guard()
        try:
            with guard:
                text, code = self._raw_preflight()
            self.assertTrue(self._is_rejected(text, code), text)
            self.assertEqual(self.outputs_state(), outputs_before_missing)
            self.assertEqual(guard.accesses, [], f"missing-A preflight accessed B/legacy: {guard.accesses}")
        finally:
            self.a_snapshot.write_bytes(a_snapshot_before)

        guard = self.guard()
        with guard:
            proof = self.preflight()
        self.assertEqual(proof.get("status"), "ok", proof)
        self.assertEqual(guard.accesses, [], f"preflight accessed B/legacy: {guard.accesses}")
        self.preflight_file.write_text(json.dumps(proof, ensure_ascii=False), encoding="utf-8")
        self._write_facts(preflight_id=proof["preflight_id"])

        guard = self.guard()
        with guard:
            planned = self.plan()
        self.assertEqual(planned.get("status"), "ok", planned)
        self.assertEqual(guard.accesses, [], f"plan accessed B/legacy: {guard.accesses}")

        target_before = self.a_target.read_bytes()
        snapshot_before = self.a_snapshot.read_bytes()
        outputs_before = self.outputs_state()
        b_before = self.fingerprint(self.b_snapshot)
        legacy_before = self.fingerprint(self.legacy_snapshot)

        drifted = json.loads(self.a_target.read_text(encoding="utf-8"))
        drifted["directions"][0]["user_note"] = "gate2 changed target binding"
        self.a_target.write_text(json.dumps(drifted, ensure_ascii=False, indent=1), encoding="utf-8")
        guard = self.guard()
        with guard:
            text, code = self.finalize()
        self.assertTrue(self._is_rejected(text, code), text)
        self.assertEqual(self.outputs_state(), outputs_before)
        self.assertEqual(guard.accesses, [], f"stale-target finalize accessed B/legacy: {guard.accesses}")
        self.a_target.write_bytes(target_before)

        state = json.loads(self.a_snapshot.read_text(encoding="utf-8"))
        original_fingerprint = state.get("input_fingerprint")
        self.assertIsInstance(original_fingerprint, str, "binding token prerequisite changed; revalidate Gate 2")
        replacement = ("0" if set(original_fingerprint) != {"0"} else "1") * len(original_fingerprint)
        state["input_fingerprint"] = replacement
        self.a_snapshot.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        guard = self.guard()
        with guard:
            text, code = self.finalize()
        self.assertTrue(self._is_rejected(text, code), text)
        self.assertEqual(self.outputs_state(), outputs_before)
        self.assertEqual(guard.accesses, [], f"stale-Stage1 finalize accessed B/legacy: {guard.accesses}")
        self.a_snapshot.write_bytes(snapshot_before)

        guard = self.guard()
        with guard:
            text, code = self.finalize()
        self.assertFalse(self._is_rejected(text, code), text)
        self.assertEqual(guard.accesses, [], f"legal finalize accessed B/legacy: {guard.accesses}")
        self.assertEqual(self.fingerprint(self.b_snapshot), b_before)
        self.assertEqual(self.fingerprint(self.legacy_snapshot), legacy_before)
        self.assertEqual(self.a_target.read_bytes(), target_before)
        self.assertEqual(self.a_snapshot.read_bytes(), snapshot_before)


class Stage1HandoffIdentityTests(unittest.TestCase):
    def test_issue65_stage1_transient_handoff_is_collision_free(self):
        # Stage-1 caller wiring consumes an explicit professor-local target.
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        caller_payloads = _task_prompt(skill_text, "professor-contact-downloader")
        self.assertTrue(caller_payloads, "no active Stage-1 caller payload in SKILL.md")
        for block in caller_payloads:
            local, program, unbound = _state_reference_scopes(block, TARGET_NAME)
            self.assertTrue(local, f"Stage-1 caller payload has no local target: {block}")
            self.assertEqual(program, [], f"Stage-1 caller payload points at retired program target: {block}")
            self.assertEqual(unbound, [], f"Stage-1 caller target is not professor-local: {block}")

        downloader_text = STAGE1_AGENT.read_text(encoding="utf-8")
        stage1_commands = [
            block for block in _bash_blocks(downloader_text) if "contact_stage1.py" in block
        ]
        self.assertTrue(stage1_commands, "downloader has no active contact_stage1.py command")
        for block in stage1_commands:
            flags = re.findall(r'--target-file\s+"([^"]+)"', block)
            self.assertTrue(flags, f"Stage-1 command omits explicit local target: {block}")
            for value in flags:
                self.assertNotEqual(
                    _parent_of_reference(value),
                    PROGRAM_STATE_DIR,
                    f"Stage-1 command uses retired program target: {block}",
                )

        # The exact return field/shape is not frozen by Gate 1. If an active
        # result does expose machine state references, it may not re-index them
        # by professor display text. A result with no such state references is
        # acceptable and is proved by the caller/analyzer wiring checks instead.
        for payload in _json_blocks(downloader_text):
            if "result" not in payload:
                continue
            if not any(
                PurePosixPath(value).name in {TARGET_NAME, STAGE1_NAME}
                for value in _strings(payload)
            ):
                continue
            self.assertFalse(
                _has_display_keyed_machine_map(payload),
                "Stage-1 result exposes display-name-keyed machine identity",
            )

        # Both shipped Stage-2 projections must pass the same local target through
        # verify and preflight; direct handler tests alone do not prove this wiring.
        for agent in (STAGE2_OPENCODE, STAGE2_CODEX):
            with self.subTest(analyzer=str(agent.relative_to(REPO_ROOT))):
                text = agent.read_text(encoding="utf-8")
                active = _bash_blocks(text)
                verify_blocks = [
                    block for block in active if "contact_stage1.py" in block and "verify" in block
                ]
                preflight_blocks = [block for block in active if "stage2-preflight" in block]
                self.assertTrue(verify_blocks, f"{agent.name}: no active Stage-1 verify command")
                self.assertTrue(preflight_blocks, f"{agent.name}: no active Stage-2 preflight command")
                for block in verify_blocks + preflight_blocks:
                    flags = re.findall(r'--target-file\s+"([^"]+)"', block)
                    self.assertTrue(flags, f"{agent.name}: command omits explicit local target: {block}")
                    for value in flags:
                        self.assertNotEqual(
                            _parent_of_reference(value),
                            PROGRAM_STATE_DIR,
                            f"{agent.name}: command uses retired program target: {block}",
                        )
                self.assertEqual(
                    _state_reference_scopes("\n".join(_fenced(text)), STAGE1_NAME)[1],
                    [],
                    f"{agent.name}: active block still names retired program-level Stage-1 authority",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
