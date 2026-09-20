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

PROFESSOR_DIR = Path("教授研究/X分野/Example Professor")


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
            self.assertTrue((profile / "套磁邮件/套磁信息.md").is_file())
            self.assertTrue((profile / "套磁邮件/套磁模板.md").is_file())
            self.assertTrue((profile / "套磁邮件/套磁跟进模板.md").is_file())
            self.assertIn("faculty@example.edu", (root / "教授研究/contact-evidence-fixture-input.json").read_text())
            candidates = json.loads(
                (root / "教授研究/_professor_candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(candidates, [{
                "name": "Example Professor",
                "email": "faculty@example.edu",
                "source": "https://example.test/faculty/example-professor",
                "provenance": "synthetic official faculty page",
            }])

    def test_canonical_fixture_carries_exactly_one_pending_item(self):
        """#40 R1/R2 continuity needs one item that R1 fills and R2 analyzes."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            builder.build_fixture(root, Path(directory) / "profile")

            key = builder.CANONICAL_ITEM_KEY
            papers = json.loads(
                (root / PROFESSOR_DIR / "papers.json").read_text(encoding="utf-8"))
            self.assertEqual([row["item_key"] for row in papers["papers"]], [key])
            self.assertEqual(papers["papers"][0]["pdf_status"], "pending")
            self.assertNotIn("pdf_path", papers["papers"][0])
            self.assertNotIn("ready_item_keys", papers["papers"][0])

            preview = json.loads(
                (root / PROFESSOR_DIR / "方向预筛.json").read_text(encoding="utf-8"))
            direction = preview["directions"][0]
            self.assertEqual([row["item_key"] for row in direction["members"]], [key])
            self.assertEqual([row["item_key"] for row in direction["representatives"]], [key])

            self.assertFalse(list((root / PROFESSOR_DIR / "论文分析").glob("*.pdf")))
            self.assertFalse(list((root / PROFESSOR_DIR / "论文分析").glob("*.md")))
            self.assertFalse(list((root / PROFESSOR_DIR / "论文分析").glob("*.future_work.json")))

    def test_manifest_records_single_canonical_key_without_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            manifest = builder.build_fixture(root, Path(directory) / "profile")

            self.assertEqual(manifest["item_keys"], [builder.CANONICAL_ITEM_KEY])
            self.assertEqual(manifest["canonical_item_key"], builder.CANONICAL_ITEM_KEY)
            self.assertNotIn("ready_item_keys", manifest)
            self.assertNotIn("missing_item_keys", manifest)
            self.assertNotIn("fill_target_item_key", manifest)
            self.assertFalse((root / "教授研究/套磁目标.json").exists())
            self.assertFalse((root / "教授研究/套磁阶段1候选.json").exists())

    def test_manifest_forbids_program_level_stage4_outputs(self):
        """Stage 4 canonical products are program-level; professor-local paths are stale."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            manifest = builder.build_fixture(root, Path(directory) / "profile")
            forbidden = {Path(path) for path in manifest["forbidden_product_outputs"]}

            self.assertIn(Path("教授研究/套磁选择.json"), forbidden)
            self.assertIn(Path("教授研究/邮件输入.json"), forbidden)
            self.assertIn(Path("教授研究/套磁目标.json"), forbidden)
            self.assertIn(Path("教授研究/套磁阶段1候选.json"), forbidden)
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁候选输入.json"), forbidden)
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁候选状态.json"), forbidden)
            for stale in (
                "教授研究/X分野/Example Professor/套磁选择.json",
                "教授研究/X分野/Example Professor/邮件输入.json",
            ):
                self.assertNotIn(Path(stale), forbidden)
            self.assertTrue((root / PROFESSOR_DIR / "方向预筛.json").is_file())

    def test_runtime_item_key_replaces_the_default_everywhere(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            manifest = builder.build_fixture(
                root, Path(directory) / "profile", item_key="RT999999",
                fixture_run_id="zotero-20260916T000000Z-00001")

            self.assertEqual(manifest["item_keys"], ["RT999999"])
            self.assertEqual(manifest["canonical_item_key"], "RT999999")
            self.assertEqual(manifest["fixture_run_id"], "zotero-20260916T000000Z-00001")
            papers = json.loads(
                (root / PROFESSOR_DIR / "papers.json").read_text(encoding="utf-8"))
            self.assertEqual([row["item_key"] for row in papers["papers"]], ["RT999999"])
            preview = json.loads(
                (root / PROFESSOR_DIR / "方向预筛.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [row["item_key"] for row in preview["directions"][0]["members"]],
                ["RT999999"])

    def test_refuses_blank_key_and_default_key_with_run_id(self):
        with tempfile.TemporaryDirectory() as directory:
            for overrides in ({"item_key": ""}, {"item_key": "   "},
                              {"item_key": None, "fixture_run_id": "run-1"}):
                with self.subTest(**overrides):
                    with self.assertRaises(builder.FixtureBuildError):
                        builder.build_fixture(
                            Path(directory) / "program", Path(directory) / "profile",
                            **overrides)

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
