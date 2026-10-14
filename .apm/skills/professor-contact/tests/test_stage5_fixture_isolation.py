import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_contact_state as helpers
import test_stage5_immutable as immutable


class TestStage5FixtureIsolation(unittest.TestCase):
    def assert_isolated_fixture(self, invoke):
        key = helpers.contact_state.UPSTREAM_SCRIPT_ENV
        with tempfile.TemporaryDirectory(prefix="stage5-external-checker-") as holder:
            external = Path(holder) / "contact_evidence.py"
            marker = Path(holder) / "called.txt"
            external.write_text(
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('called')\n"
                "raise RuntimeError('External checker must not run')\n",
                encoding="utf-8")
            with patch.dict(os.environ, {key: str(external)}):
                fixture = helpers.TestStage5("test_stage5_full_flow_and_fact_card")
                fixture.setUp()
                try:
                    gap = fixture.prepare()
                    injected = helpers.contact_state.upstream_check_script()
                    self.assertIsNotNone(injected)
                    self.assertNotEqual(injected, external)
                    self.assertNotIn(fixture.root, injected.parents)
                    artifact, error = helpers.contact_state.load_contact_evidence(fixture.root)
                    self.assertIsNone(error)
                    self.assertIsNotNone(artifact)
                    self.assertEqual(artifact["schema"], 2)
                    self.assertTrue(artifact["source_fingerprints"]["files"])
                    pack_before = fixture.email_pack.read_bytes()
                    pack = json.loads(pack_before)
                    expected = helpers.contact_state.contact_evidence_snapshot(
                        artifact, error, "試験 教授")
                    self.assertIsNotNone(expected)
                    self.assertEqual(pack["emails"][0]["contact_evidence"], expected)
                    raw = fixture.root / "raw.json"
                    choices = fixture.root / "choices.json"
                    raw.write_text(json.dumps(fixture.raw_result(gap)), encoding="utf-8")
                    choices.write_text(json.dumps(fixture.choices()), encoding="utf-8")
                    process = invoke(
                        "stage5-plan", "--program-root", fixture.root,
                        "--email-pack", fixture.email_pack,
                        "--result", raw, "--choices", choices)
                    result = helpers.parse(process)
                    self.assertEqual(process.returncode, 0, result)
                    self.assertEqual(result["status"], "ok", result)
                    self.assertTrue(result["drafts"])
                    humanized = fixture.root / "humanized.txt"
                    humanized.write_text(result["drafts"][0]["draft"], encoding="utf-8")
                    process = invoke(
                        "stage5-finalize", "--program-root", fixture.root,
                        "--email-pack", fixture.email_pack,
                        "--result", raw, "--choices", choices,
                        "--humanized", humanized)
                    result = helpers.parse(process)
                    self.assertEqual(process.returncode, 0, result)
                    self.assertEqual(result["status"], "ok", result)
                    self.assertTrue((fixture.prof_dir / "套磁邮件.txt").is_file())
                    self.assertEqual(fixture.email_pack.read_bytes(), pack_before)
                    self.assertFalse(fixture.checker_marker.exists())
                finally:
                    fixture.tearDown()
                    fixture.doCleanups()
                self.assertEqual(os.environ.get(key), str(external))
                self.assertFalse(injected.exists())
            self.assertFalse(marker.exists())

    def test_direct_runner_uses_complete_isolated_fixture(self):
        self.assert_isolated_fixture(helpers.run_cli)

    def test_immutable_wrapper_uses_complete_isolated_fixture(self):
        self.assert_isolated_fixture(immutable.run_wrapper)
