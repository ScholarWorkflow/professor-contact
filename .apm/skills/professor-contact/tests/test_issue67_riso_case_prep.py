import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_DIR / "runtime"
PREPARER_PATH = RUNTIME_DIR / "prepare_issue67_riso_case.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preparer = load_module("issue67_riso_case_preparer_test", PREPARER_PATH)


class Issue67RisoCasePreparationTests(unittest.TestCase):
    def test_derivation_removes_only_valid_legacy_selection_row(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            program = root / "program"
            profile = root / "profile"
            source_output = root / "source-manifest.json"
            output = root / "fixture-manifest.json"

            manifest = preparer.prepare_case(
                program,
                profile,
                source_output=source_output,
                output=output,
            )
            source = json.loads(source_output.read_text(encoding="utf-8"))
            legacy_selection = json.loads(
                (program / "教授研究/套磁选择.json").read_text(encoding="utf-8"))
            legacy_email_path = program / "教授研究/邮件输入.json"
            legacy_email = json.loads(legacy_email_path.read_text(encoding="utf-8"))

            self.assertEqual(legacy_selection["selections"], [])
            self.assertEqual(len(legacy_email["emails"]), 1)
            self.assertEqual(
                manifest["derivation"]["removed_valid_legacy_selection_rows"], 1)
            self.assertEqual(
                manifest["legacy_program_pair"]["教授研究/套磁选择.json"],
                preparer.sha256(program / "教授研究/套磁选择.json"),
            )
            self.assertEqual(
                manifest["legacy_program_pair"]["教授研究/邮件输入.json"],
                source["legacy_program_pair"]["教授研究/邮件输入.json"],
            )
            self.assertEqual(
                manifest["derivation"]["legacy_email_sha256"],
                preparer.sha256(legacy_email_path),
            )
            self.assertNotEqual(
                manifest["legacy_program_pair"]["教授研究/套磁选择.json"],
                source["legacy_program_pair"]["教授研究/套磁选择.json"],
            )

    def test_derivation_preserves_professor_local_fixture_input_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            program = root / "program"
            profile = root / "profile"
            source_output = root / "source-manifest.json"
            output = root / "fixture-manifest.json"

            manifest = preparer.prepare_case(
                program,
                profile,
                source_output=source_output,
                output=output,
            )
            source = json.loads(source_output.read_text(encoding="utf-8"))

            for relative, source_hash in source["input_hashes"].items():
                if relative == "教授研究/套磁选择.json":
                    continue
                self.assertEqual(
                    manifest["input_hashes"][relative], source_hash, relative)
            self.assertEqual(manifest["fault"], source["fault"])
            self.assertEqual(manifest["builder"], source["builder"])
            self.assertEqual(manifest["builder_sha256"], source["builder_sha256"])
            self.assertEqual(manifest["case_preparer"], preparer.PREPARER_ID)
            self.assertEqual(
                manifest["case_preparer_sha256"], preparer.sha256(PREPARER_PATH))
            self.assertEqual(
                manifest["source_manifest_sha256"], preparer.sha256(source_output))


if __name__ == "__main__":
    unittest.main()
