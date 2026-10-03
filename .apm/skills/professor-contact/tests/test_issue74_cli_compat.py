"""Direct compatibility proofs for issue #74 plan-4 migration."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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

    def test_build_fixture_return_objects_match_written_manifest_contracts(self):
        fixture53 = load_module(
            "issue74_cli_fixture53", RUNTIME_DIR / "prepare_issue53_stage4_fixture.py"
        )
        fixture55 = load_module(
            "issue74_cli_fixture55", RUNTIME_DIR / "prepare_issue55_stage3_fixture.py"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            output.mkdir()

            output53 = output / "issue53.json"
            manifest53 = fixture53.build_fixture(
                root / "issue53-program",
                root / "issue53-profile",
                output=output53,
            )
            self.assertEqual(
                set(manifest53),
                {
                    "schema_version", "builder", "fixture_kind", "program_root",
                    "profile_root", "professor", "direction_id", "input_hashes",
                    "forbidden_outputs", "manual_patch",
                },
            )
            self.assertEqual(
                manifest53,
                json.loads(output53.read_text(encoding="utf-8")),
            )

            output55 = output / "issue55.json"
            manifest55 = fixture55.build_fixture(root / "issue55-program", output=output55)
            self.assertEqual(
                set(manifest55),
                {
                    "schema_version", "builder", "fixture_kind", "program_root",
                    "professor", "direction_id", "item_key", "gap_id", "input_hashes",
                    "forbidden_outputs", "stage1_stage2_runtime_artifacts", "manual_patch",
                    "network_used", "runtime_fixture_started",
                },
            )
            self.assertEqual(
                manifest55,
                json.loads(output55.read_text(encoding="utf-8")),
            )


if __name__ == "__main__":
    unittest.main()
