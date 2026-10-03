"""Direct compatibility proofs for issue #74 plan-4 migration."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


BASE_SHA = "768b49ef4514e36edec6b57ed3821a99af9e9c00"
TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"
REPO_ROOT = TESTS_DIR.parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def snapshot_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


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

    def test_generated_bytes_hashes_and_returns_match_compatibility_base(self):
        base_check = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{BASE_SHA}^{{commit}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if base_check.returncode != 0:
            self.skipTest(
                "compatibility base commit is not present in this checkout; "
                "the formal issue-74 recipe verifies it before T74-CLI starts"
            )

        current53 = load_module(
            "issue74_parity_current53", RUNTIME_DIR / "prepare_issue53_stage4_fixture.py"
        )
        current55 = load_module(
            "issue74_parity_current55", RUNTIME_DIR / "prepare_issue55_stage3_fixture.py"
        )

        with tempfile.TemporaryDirectory() as directory:
            holder = Path(directory)
            baseline_checkout = holder / "baseline-checkout"
            add = subprocess.run(
                [
                    "git", "-C", str(REPO_ROOT), "worktree", "add", "--detach",
                    str(baseline_checkout), BASE_SHA,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if add.returncode != 0:
                self.fail(f"could not create compatibility-base worktree: {add.stderr}")
            try:
                baseline_runtime = (
                    baseline_checkout
                    / ".apm/skills/professor-contact/tests/runtime"
                )
                baseline53 = load_module(
                    "issue74_parity_base53",
                    baseline_runtime / "prepare_issue53_stage4_fixture.py",
                )
                baseline55 = load_module(
                    "issue74_parity_base55",
                    baseline_runtime / "prepare_issue55_stage3_fixture.py",
                )

                root53 = holder / "fixture53"
                program53 = root53 / "program"
                profile53 = root53 / "profile"
                output53 = root53 / "output/setup.json"
                baseline_manifest53 = baseline53.build_fixture(
                    program53, profile53, output=output53
                )
                baseline_bytes53 = snapshot_files(root53)
                shutil.rmtree(root53)
                current_manifest53 = current53.build_fixture(
                    program53, profile53, output=output53
                )
                self.assertEqual(current_manifest53, baseline_manifest53)
                self.assertEqual(snapshot_files(root53), baseline_bytes53)

                root55 = holder / "fixture55"
                program55 = root55 / "program"
                output55 = root55 / "output/setup.json"
                baseline_manifest55 = baseline55.build_fixture(program55, output=output55)
                baseline_bytes55 = snapshot_files(root55)
                shutil.rmtree(root55)
                current_manifest55 = current55.build_fixture(program55, output=output55)
                self.assertEqual(current_manifest55, baseline_manifest55)
                self.assertEqual(snapshot_files(root55), baseline_bytes55)
            finally:
                subprocess.run(
                    [
                        "git", "-C", str(REPO_ROOT), "worktree", "remove", "--force",
                        str(baseline_checkout),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )


if __name__ == "__main__":
    unittest.main()