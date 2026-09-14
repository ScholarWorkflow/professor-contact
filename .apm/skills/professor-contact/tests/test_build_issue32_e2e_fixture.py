import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BUILDER_PATH = TESTS_DIR / "runtime/build_issue32_e2e_fixture.py"
spec = importlib.util.spec_from_file_location("issue32_fixture_builder", BUILDER_PATH)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Issue32FixtureBuilderTests(unittest.TestCase):
    def test_builds_raw_inputs_without_product_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            profile = Path(directory) / "profile"
            manifest = builder.build_fixture(
                root, profile, consumer_root=Path(directory) / "consumer",
                professor_research_sha="accepted-sha-for-test")

            self.assertEqual(manifest["fixture_mode"], "initial_raw_inputs")
            self.assertEqual(manifest["professor"], "Example Professor")
            self.assertEqual(manifest["direction_ids"], ["DIR00001"])
            self.assertEqual(manifest["item_keys"], ["AAAA1111", "BBBB2222"])
            self.assertTrue((root / "教授研究/X分野/Example Professor/论文分析/AAAA1111.pdf").is_file())
            self.assertFalse((root / "教授研究/套磁目标.json").exists())
            self.assertFalse((root / "教授研究/套磁阶段1候选.json").exists())
            forbidden = {Path(path) for path in manifest["forbidden_product_outputs"]}
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁候选输入.json"), forbidden)
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁候选状态.json"), forbidden)
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁选择.json"), forbidden)
            self.assertIn(Path("教授研究/X分野/Example Professor/邮件输入.json"), forbidden)
            self.assertFalse(list((root / "教授研究/X分野/Example Professor/论文分析").glob("*.md")))
            self.assertFalse(list((root / "教授研究/X分野/Example Professor/论文分析").glob("*.future_work.json")))
            self.assertTrue((profile / "套磁邮件/套磁信息.md").is_file())
            self.assertTrue((profile / "套磁邮件/套磁模板.md").is_file())
            self.assertTrue((profile / "套磁邮件/套磁跟进模板.md").is_file())
            self.assertIn("faculty@example.edu", (root / "教授研究/contact-evidence-fixture-input.json").read_text())

    def test_manifest_protects_builder_owned_rebuilds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            profile = Path(directory) / "profile"
            builder.build_fixture(root, profile)
            manifest = builder.build_fixture(root, profile)
            loaded = json.loads((root / "fixture-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded["builder"], builder.MANIFEST_ID)
            self.assertEqual(manifest["builder_sha256"], loaded["builder_sha256"])


if __name__ == "__main__":
    unittest.main()
