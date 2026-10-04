"""Issue #68 P1 (PR #72 review r18): the canonical scope survives transport.

AD68-4 and plan r11 §3.3/§3.6/§3.7 freeze what every professor receives: the
same complete original ``choices`` and the same read-only attribution scope,
with the canonical ``professor_dir`` value preserved byte for byte. The formal
run (Y owner thread ``01a106cd…``, ``runtime_seq=14610``) showed the root
agent hand-writing the scope and rewriting ``試験`` (U+8A66 U+9A13) into
``试验`` (U+8BD5 U+9A8C) while the ``choices`` rows kept the canonical value:
the product gave the caller no deterministic way to obtain the scope, so the
value was retyped by a model on the way to ``stage5-plan``.

These cases lock the deterministic transport path: the caller obtains the
complete scope from the runner itself (``stage5-list-inputs
--emit-choices-scope``), the emitted file carries the pack values byte for
byte, and a real owner plan call consumes that file unchanged.
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("contact_state_test_helpers",
                                              HERE / "test_contact_state.py")
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)

BaseEnv = helpers.BaseEnv
parse = helpers.parse
run_cli = helpers.run_cli
A = helpers.ISSUE59_PROFESSOR
B = helpers.ISSUE59_OTHER_PROFESSOR
A_ID = helpers.ISSUE59_EMAIL_ID
B_ID = helpers.ISSUE59_OTHER_EMAIL_ID
CANONICAL = "試験"  # U+8A66 U+9A13 — the frozen directory spelling
REWRITTEN = "试验"  # U+8BD5 U+9A8C — what the formal run delivered


class TestStage5ChoicesScopeTransport(helpers.Stage5LocalHarness, BaseEnv):
    """Plan r11 §3.3/§3.6: the caller's scope is program-obtained and unchanged."""

    def fixture(self):
        return helpers.write_issue59_stage5_fixture(
            self.root, [{"professor": A, "evidence": "fresh"},
                        {"professor": B, "evidence": "fresh"}], case=self)

    def emit_scope(self, fixture, name="owner-choices-scope.json", professor=None):
        scope_path = self.root / name
        arguments = ["stage5-list-inputs", "--program-root", self.root,
                     "--emit-choices-scope", scope_path]
        if professor is not None:
            arguments += ["--professor", professor]
        out = parse(run_cli(*arguments))
        self.assertEqual(out["status"], "ok", out)
        return scope_path

    def test_issue68_p1_emitted_scope_keeps_the_canonical_directory_byte_for_byte(self):
        fixture = self.fixture()
        a_dir = Path(fixture["dirs"][A]).resolve()
        b_dir = Path(fixture["dirs"][B]).resolve()
        scope_path = self.emit_scope(fixture)
        raw = scope_path.read_bytes()
        self.assertIn(CANONICAL.encode("utf-8"), raw)
        self.assertNotIn(REWRITTEN.encode("utf-8"), raw)
        scope = json.loads(raw.decode("utf-8"))
        self.assertEqual(sorted(Path(key).resolve() for key in scope),
                         sorted([a_dir, b_dir]))
        self.assertEqual(scope[next(key for key in scope
                                    if Path(key).resolve() == a_dir)], [A_ID])
        self.assertEqual(scope[next(key for key in scope
                                    if Path(key).resolve() == b_dir)], [B_ID])

    def test_issue68_p1_emitted_scope_drives_a_real_plan_attribution(self):
        fixture = self.fixture()
        a_dir = Path(fixture["dirs"][A]).resolve()
        b_dir = Path(fixture["dirs"][B]).resolve()
        scope_path = self.emit_scope(fixture)
        choices = self.write_json("owner-choices.json", [
            dict(helpers.issue59_choices(A_ID), professor_dir=str(a_dir)),
            dict(helpers.issue59_choices(B_ID), professor_dir=str(b_dir)),
        ])
        results = self.write_results("owner-results.json", [A_ID])
        draft = self.plan("--result", results, "--choices", choices,
                          "--choices-scope", scope_path, "--email-id", A_ID)
        self.assertEqual(draft["status"], "ok", draft)
        self.assertEqual([row["email_id"] for row in draft["drafts"]], [A_ID])

    def test_issue68_p1_emitted_scope_follows_the_professor_filter(self):
        fixture = self.fixture()
        b_dir = Path(fixture["dirs"][B]).resolve()
        scope_path = self.emit_scope(fixture, name="b-scope.json", professor=B)
        scope = json.loads(scope_path.read_text(encoding="utf-8"))
        self.assertEqual({str(Path(key).resolve()): ids
                          for key, ids in scope.items()}, {str(b_dir): [B_ID]})

    def test_issue68_p1_discovery_without_emission_stays_read_only(self):
        self.fixture()
        out = parse(run_cli("stage5-list-inputs", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual([row["status"] for row in out["inputs"]], ["ok", "ok"])
        self.assertFalse((self.root / "owner-choices-scope.json").exists())


if __name__ == "__main__":
    unittest.main()
