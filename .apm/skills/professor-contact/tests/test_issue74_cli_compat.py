"""Direct CLI compatibility proof for issue #74 plan-4 migration."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"


class Issue74CliCompatibilityTests(unittest.TestCase):
    def test_both_fixture_entrypoints_run_from_unrelated_cwd_without_pythonpath(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unrelated = root / "unrelated"
            unrelated.mkdir()
            output = root / "output"
            output.mkdir()

            env = dict(os.environ)
            env.pop("PYTHONPATH", None)

            cases = [
                (
                    "issue53",
                    RUNTIME_DIR / "prepare_issue53_stage4_fixture.py",
                    [
                        "--program-root", str(root / "issue53-program"),
                        "--profile-root", str(root / "issue53-profile"),
                        "--output", str(output / "issue53.json"),
                    ],
                    output / "issue53.json",
                    "stage4-only",
                ),
                (
                    "issue55",
                    RUNTIME_DIR / "prepare_issue55_stage3_fixture.py",
                    [
                        "--program-root", str(root / "issue55-program"),
                        "--output", str(output / "issue55.json"),
                    ],
                    output / "issue55.json",
                    "issue55-stage3-pre",
                ),
            ]

            for label, script, args, manifest_path, expected_kind in cases:
                with self.subTest(entrypoint=label):
                    result = subprocess.run(
                        [sys.executable, "-B", str(script), *args],
                        cwd=unrelated,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["status"], "ok", payload)
                    self.assertTrue(manifest_path.is_file(), manifest_path)
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    self.assertEqual(manifest["fixture_kind"], expected_kind, manifest)
                    self.assertEqual(manifest["manual_patch"], "no", manifest)


if __name__ == "__main__":
    unittest.main()
