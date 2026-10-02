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


def _is_professor_local_reference(token: str, filename: str) -> bool:
    """True when token binds filename at a professor-local parent.

    A professor-local reference is anchored inside the program root (either a
    relative path or one under the ``<program_root>`` placeholder), carries no
    ``..`` escape segment, and stores the state file at least one directory
    below that root in a directory that is not the retired program state dir.
    Absolute paths, root-level state files and ``教授研究/<state file>`` all
    fail this check, so only comparing the last directory name is not enough.
    """
    path = PurePosixPath(token)
    if path.name != filename or ".." in path.parts:
        return False
    if token.startswith("/"):
        return False
    segments = path.parts
    if segments and segments[0] == "<program_root>":
        segments = segments[1:]
    if len(segments) < 2:
        return False
    return segments[-2] != PROGRAM_STATE_DIR


def _state_reference_scopes(text: str, filename: str) -> tuple[list[str], list[str], list[str]]:
    """Split bound filename references into (local, foreign, unbound).

    ``foreign`` collects every bound reference that is not professor-local:
    the retired program-level path, root-level files, outside-root absolute
    paths and ``..`` escapes.
    """
    local: list[str] = []
    foreign: list[str] = []
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
        bucket = local if _is_professor_local_reference(token, filename) else foreign
        bucket.append(token)
    return local, foreign, unbound


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


class Issue65Gate2Stage1Tests(unittest.TestCase):
    def setUp(self):
        self.env = stage1_fixture.Stage1CandidateTests(
            "test_selected_directions_keep_separate_candidate_sets_with_shared_paper_once"
        )
        self.env.setUp()
        self.addCleanup(self.env.tearDown)

    def _call_stage1_ok(self, func, *args, scenario):
        """Run one Stage-1 call that must succeed; crashes fail the assertion.

        A raw product exception must not escape as a test-body error: it is
        converted into an assertion failure at the product-call boundary so
        the evaluator can attribute it to the producer.
        """
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                payload = func(*args)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
            self.fail(f"{scenario} exited {code}: {out.getvalue()!r}")
        except Exception as exc:
            self.fail(f"{scenario} raised {type(exc).__name__}: {exc}")
        self.assertIsInstance(payload, dict, f"{scenario} returned {payload!r}")
        return payload

    def _expect_stage1_rejection(self, func, *args, expected_status):
        """Run one Stage-1 call that must fail closed.

        needs_input terminals emit their JSON payload and exit 2; the error
        terminal raises the frozen invalid_stage1_input problem. Exit 0, an
        ok payload, or unparseable output never counts as a rejection.
        """
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                payload = func(*args)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
            self.assertEqual(code, 2, f"rejection exit code: {code!r}, output: {out.getvalue()!r}")
            try:
                payload = json.loads(out.getvalue())
            except json.JSONDecodeError:
                self.fail(f"rejection emitted unparseable output: {out.getvalue()!r}")
            self.assertEqual(
                payload.get("status"), expected_status,
                f"rejection terminal is not the contract's {expected_status!r}: {payload}")
            return
        except ValueError as exc:
            self.assertIn("invalid_stage1_input", str(exc),
                          f"rejection raised a non-contract problem: {exc}")
            return
        self.fail(f"rejection did not fail closed, returned: {payload!r}")

    def test_issue65_stage1_professor_local_authority_and_isolation(self):
        root = self.env.root
        legacy_stage1 = root / "教授研究" / STAGE1_NAME
        legacy_target = root / "教授研究" / TARGET_NAME
        a_dir = stage1_fixture.same_name_professor(root, "labA", "fp-a", professor="教授甲")
        b_dir = stage1_fixture.same_name_professor(root, "labB", "fp-b", professor="教授乙")
        a_target = a_dir / TARGET_NAME
        b_target = b_dir / TARGET_NAME
        a_state = stage1_fixture.professor_local_state(a_dir)
        b_state = stage1_fixture.professor_local_state(b_dir)

        stage1_fixture.build(root, b_target)
        self.assertTrue(b_state.is_file())
        legacy_stage1.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "professor-contact-stage1",
                    "updated_at": None,
                    "professors": [],
                    "sentinel": "issue-65-legacy-stage1-sentinel",
                },
                ensure_ascii=False,
                indent=1,
            )
            + "\n",
            encoding="utf-8",
        )
        legacy_target.write_text("{ retired program target sentinel", encoding="utf-8")
        b_before = b_state.read_bytes()
        legacy_stage1_before = legacy_stage1.read_bytes()
        legacy_target_before = legacy_target.read_bytes()

        forbidden = [b_state, legacy_stage1, legacy_target]
        guard = stage1_fixture.ForbiddenAuthorityGuard(forbidden)
        with guard:
            _first, first_payload = stage1_fixture.build(root, a_target)
            self.assertEqual(first_payload.get("status"), "ok")
            verified = self._call_stage1_ok(
                stage1_fixture.stage1.verify_command, root, a_target, scenario="A verify")
            self.assertEqual(verified.get("status"), "ok")
            _again, again_payload = stage1_fixture.build(root, a_target)
            self.assertEqual(again_payload.get("status"), "ok")
            reverified = self._call_stage1_ok(
                stage1_fixture.stage1.verify_command, root, a_target, scenario="A reverify")
            self.assertEqual(reverified.get("status"), "ok")
        self.assertEqual(guard.accesses, [], f"foreign/retired authority accessed: {guard.accesses}")
        self.assertEqual(b_state.read_bytes(), b_before)
        self.assertEqual(legacy_stage1.read_bytes(), legacy_stage1_before)
        self.assertEqual(legacy_target.read_bytes(), legacy_target_before)

        # A missing state must not be substituted by B's state: verify must end
        # in the contract's needs_input terminal with a matching exit code.
        a_before = a_state.read_bytes()
        a_state.unlink()
        guard = stage1_fixture.ForbiddenAuthorityGuard(forbidden)
        try:
            with guard:
                self._expect_stage1_rejection(
                    stage1_fixture.stage1.verify_command, root, a_target,
                    expected_status="needs_input")
        finally:
            a_state.write_bytes(a_before)
        self.assertEqual(guard.accesses, [], f"missing-A verify accessed B/retired state: {guard.accesses}")

        # A structurally valid B snapshot placed on A's authoritative path is
        # B's state, not A's: verify must end in the contract's error terminal
        # without consuming it, and A's own bytes must come back unchanged.
        guard = stage1_fixture.ForbiddenAuthorityGuard(forbidden)
        try:
            with guard:
                a_state.write_bytes(b_before)
                self._expect_stage1_rejection(
                    stage1_fixture.stage1.verify_command, root, a_target,
                    expected_status="error")
        finally:
            a_state.write_bytes(a_before)
        self.assertEqual(a_state.read_bytes(), a_before)
        self.assertEqual(b_state.read_bytes(), b_before)
        self.assertEqual(guard.accesses, [], f"owner-mismatch verify accessed B/retired state: {guard.accesses}")


class Issue65Gate2Stage2Tests(stage2_fixture.Issue65Stage2BindingEnv):
    DISPLAY = "教授甲"
    B_DISPLAY = "教授乙"

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

    def _gate2_guard(self):
        return stage2_fixture._ForeignAuthorityGuard(
            [self.b_snapshot, self.legacy_snapshot, self.legacy_target]
        )

    def _parse_formal_payload(self, text: str, scenario: str) -> dict:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            self.fail(f"{scenario} emitted unparseable output: {text!r}")
        self.assertIsInstance(
            payload, dict, f"{scenario} output is not a JSON object: {text!r}")
        return payload

    def _require_rejected(self, text: str, code, scenario: str) -> None:
        """A rejection must be the contract's needs_refresh terminal, exit 2.

        Garbage output, empty output, unrelated exits or any other status are
        not fail-closed evidence; they fail the oracle here.
        """
        payload = self._parse_formal_payload(text, scenario)
        self.assertEqual(
            payload.get("status"), "needs_refresh",
            f"{scenario} rejection terminal is not needs_refresh: {payload}")
        self.assertEqual(code, 2, f"{scenario} exit code: {code!r}")

    def _require_accepted(self, text: str, code, scenario: str) -> None:
        payload = self._parse_formal_payload(text, scenario)
        self.assertEqual(payload.get("status"), "ok", f"{scenario} terminal: {payload}")
        self.assertIsNone(code, f"{scenario} exit code: {code!r}")

    def test_issue65_stage2_exact_stage1_binding_lifecycle(self):
        self.legacy_target = self.root / "教授研究" / TARGET_NAME
        self.legacy_target.write_text("{ retired program target sentinel", encoding="utf-8")
        legacy_target_before = self.legacy_target.read_bytes()

        # A missing local state cannot fall through to B or retired authority:
        # the rejection must be the contract's needs_refresh terminal.
        a_snapshot_before = self.a_snapshot.read_bytes()
        outputs_before_missing = self.outputs_state()
        self.a_snapshot.unlink()
        guard = self._gate2_guard()
        try:
            with guard:
                text, code = self._raw_preflight()
            self._require_rejected(text, code, "missing-A preflight")
            self.assertEqual(self.outputs_state(), outputs_before_missing)
            self.assertEqual(guard.accesses, [], f"missing-A preflight accessed B/retired state: {guard.accesses}")
        finally:
            self.a_snapshot.write_bytes(a_snapshot_before)

        # A structurally valid B snapshot placed on A's authoritative path is
        # B's state, not A's: Stage 2 must reject it in the same needs_refresh
        # terminal without reading candidate content, writing formal state or
        # falling back to the retired aggregate, then A's exact bytes return.
        self.a_snapshot.write_bytes(self.b_snapshot.read_bytes())
        outputs_before_misowned = self.outputs_state()
        guard = self._gate2_guard()
        try:
            with guard:
                text, code = self._raw_preflight()
            self._require_rejected(text, code, "owner-mismatch preflight")
            self.assertEqual(self.outputs_state(), outputs_before_misowned)
            self.assertEqual(guard.accesses, [], f"owner-mismatch preflight accessed B/retired state: {guard.accesses}")
        finally:
            self.a_snapshot.write_bytes(a_snapshot_before)
        self.assertEqual(self.a_snapshot.read_bytes(), a_snapshot_before)

        guard = self._gate2_guard()
        with guard:
            proof = self.preflight()
        self.assertEqual(proof.get("status"), "ok", proof)
        self.assertEqual(guard.accesses, [], f"preflight accessed B/retired state: {guard.accesses}")
        self.preflight_file.write_text(json.dumps(proof, ensure_ascii=False), encoding="utf-8")
        self._write_facts(preflight_id=proof["preflight_id"])

        guard = self._gate2_guard()
        with guard:
            planned = self.plan()
        self.assertEqual(planned.get("status"), "ok", planned)
        self.assertEqual(guard.accesses, [], f"plan accessed B/retired state: {guard.accesses}")

        target_before = self.a_target.read_bytes()
        snapshot_before = self.a_snapshot.read_bytes()
        outputs_before = self.outputs_state()
        b_before = self.fingerprint(self.b_snapshot)
        legacy_stage1_before = self.fingerprint(self.legacy_snapshot)

        drifted = json.loads(self.a_target.read_text(encoding="utf-8"))
        drifted["directions"][0]["user_note"] = "gate2 changed target binding"
        self.a_target.write_text(json.dumps(drifted, ensure_ascii=False, indent=1), encoding="utf-8")
        guard = self._gate2_guard()
        with guard:
            text, code = self.finalize()
        self._require_rejected(text, code, "stale-target finalize")
        self.assertEqual(self.outputs_state(), outputs_before)
        self.assertEqual(guard.accesses, [], f"stale-target finalize accessed B/retired state: {guard.accesses}")
        self.a_target.write_bytes(target_before)

        state = json.loads(self.a_snapshot.read_text(encoding="utf-8"))
        original_fingerprint = state.get("input_fingerprint")
        self.assertIsInstance(original_fingerprint, str, "binding token prerequisite changed; revalidate Gate 2")
        replacement = ("0" if set(original_fingerprint) != {"0"} else "1") * len(original_fingerprint)
        state["input_fingerprint"] = replacement
        self.a_snapshot.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        guard = self._gate2_guard()
        with guard:
            text, code = self.finalize()
        self._require_rejected(text, code, "stale-Stage1 finalize")
        self.assertEqual(self.outputs_state(), outputs_before)
        self.assertEqual(guard.accesses, [], f"stale-Stage1 finalize accessed B/retired state: {guard.accesses}")
        self.a_snapshot.write_bytes(snapshot_before)

        guard = self._gate2_guard()
        with guard:
            text, code = self.finalize()
        self._require_accepted(text, code, "legal finalize")
        self.assertEqual(guard.accesses, [], f"legal finalize accessed B/retired state: {guard.accesses}")
        self.assertEqual(self.fingerprint(self.b_snapshot), b_before)
        self.assertEqual(self.fingerprint(self.legacy_snapshot), legacy_stage1_before)
        self.assertEqual(self.legacy_target.read_bytes(), legacy_target_before)
        self.assertEqual(self.a_target.read_bytes(), target_before)
        self.assertEqual(self.a_snapshot.read_bytes(), snapshot_before)


class Stage1HandoffIdentityTests(unittest.TestCase):
    def test_issue65_stage1_transient_handoff_is_collision_free(self):
        # Stage-1 caller wiring consumes an explicit professor-local target.
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        caller_payloads = _task_prompt(skill_text, "professor-contact-downloader")
        self.assertTrue(caller_payloads, "no active Stage-1 caller payload in SKILL.md")
        for block in caller_payloads:
            local, foreign, unbound = _state_reference_scopes(block, TARGET_NAME)
            self.assertTrue(local, f"Stage-1 caller payload has no local target: {block}")
            self.assertEqual(
                foreign, [],
                f"Stage-1 caller payload points at non-professor-local authority: {foreign}")
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
                self.assertTrue(
                    _is_professor_local_reference(value, TARGET_NAME),
                    f"Stage-1 command uses a non-professor-local target: {value!r} in {block}",
                )

        # The downloader's returned handoff must expose Stage-1 snapshots only
        # through professor-local paths owned by the same professor-local
        # target parent in the same payload; returning the retired
        # program-level aggregate would otherwise pass unnoticed. The
        # name-keyed outer mapping shape stays unchecked by design.
        downloader_fenced = "\n".join(_fenced(downloader_text))
        snapshot_local, snapshot_foreign, snapshot_unbound = _state_reference_scopes(
            downloader_fenced, STAGE1_NAME)
        self.assertEqual(
            snapshot_foreign, [],
            f"downloader active block references non-professor-local Stage-1 state: {snapshot_foreign}")
        self.assertEqual(
            snapshot_unbound, [],
            f"downloader active block references Stage-1 state without a bound path: {snapshot_unbound}")
        for payload in _json_blocks(downloader_text):
            values = list(_strings(payload))
            target_parents = {
                parent for value in values
                if (parent := _state_parent(value, TARGET_NAME)) is not None
            }
            snapshot_parents = {
                parent for value in values
                if (parent := _state_parent(value, STAGE1_NAME)) is not None
            }
            for parent in snapshot_parents:
                self.assertTrue(
                    _is_professor_local_reference(f"{parent}/{STAGE1_NAME}", STAGE1_NAME),
                    f"downloader returns Stage-1 snapshot outside a professor-local parent: {parent}",
                )
                self.assertIn(
                    parent, target_parents,
                    f"downloader returns a Stage-1 snapshot for a professor with no "
                    f"matching local target in the same payload: {parent}")

        # The reviewed scope permits name-keyed returns for unique professor names.
        # This case proves local-target wiring, not same-name collision handling.

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
                        self.assertTrue(
                            _is_professor_local_reference(value, TARGET_NAME),
                            f"{agent.name}: command uses a non-professor-local target: {value!r}",
                        )
                foreign_stage1 = _state_reference_scopes(
                    "\n".join(_fenced(text)), STAGE1_NAME)[1]
                self.assertEqual(
                    foreign_stage1, [],
                    f"{agent.name}: active block still names retired program-level Stage-1 authority",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
