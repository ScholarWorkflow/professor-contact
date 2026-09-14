"""Issue #40: fixture builder uses dynamic Zotero keys and owner raw sources.

The fixture builder must not hardcode ``AAAA1111``/``BBBB2222``; the fill
target must use a product-accepted retry state (never the historical
``missing``); profile inputs live directly under the profile root; and the
only contact sources created are the raw files the owner's
``contact_evidence.py`` actually consumes.
"""
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


def write_items_config(directory: Path, *, item_keys=("K1AAAA", "K2BBBB"),
                       ready=("K1AAAA",), fill_target="K2BBBB",
                       fill_status="pending") -> Path:
    config = directory / "config" / "zotero-items.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "item_keys": list(item_keys),
        "ready_item_keys": list(ready),
        "fill_target_item_key": fill_target,
        "fill_target_pdf_status": fill_status,
        "fixture_run_id": "run-xyz",
    }
    config.write_text(json.dumps(payload), encoding="utf-8")
    return config


class Issue32FixtureBuilderTests(unittest.TestCase):
    def test_builds_raw_inputs_from_dynamic_zotero_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            profile = Path(directory) / "profile"
            config = write_items_config(Path(directory))
            manifest = builder.build_fixture(
                root, profile, consumer_root=Path(directory) / "consumer",
                professor_research_sha="accepted-sha-for-test",
                zotero_items_config=config)

            # Dynamic keys replace the historical hardcoded constants.
            self.assertEqual(manifest["item_keys"], ["K1AAAA", "K2BBBB"])
            self.assertEqual(manifest["ready_item_keys"], ["K1AAAA"])
            self.assertEqual(manifest["fill_target_item_key"], "K2BBBB")
            self.assertEqual(manifest["fixture_run_id"], "run-xyz")
            prof = root / "教授研究/X分野/Example Professor"
            papers = {row["item_key"]: row
                      for row in json.loads((prof / "papers.json").read_text())["papers"]}
            self.assertEqual(sorted(papers), ["K1AAAA", "K2BBBB"])
            self.assertEqual(papers["K1AAAA"]["pdf_status"], "downloaded")
            # The fill target uses a product-accepted retry state, not `missing`.
            self.assertEqual(papers["K2BBBB"]["pdf_status"], "pending")
            self.assertNotIn("pdf_path", papers["K2BBBB"])
            self.assertTrue((prof / "论文分析/K1AAAA.pdf").is_file())
            preview = json.loads((prof / "方向预筛.json").read_text())
            members = [row["item_key"] for row in preview["directions"][0]["members"]]
            self.assertEqual(members, ["K1AAAA", "K2BBBB"])
            self.assertFalse((root / "教授研究/套磁目标.json").exists())
            self.assertFalse(list((prof / "论文分析").glob("*.md")))

    def test_zotero_items_config_rejects_malformed_key_sets(self):
        with tempfile.TemporaryDirectory() as directory:
            config = write_items_config(Path(directory), item_keys=(), ready=(), fill_target="K2BBBB")
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(Path(directory) / "program",
                                      Path(directory) / "profile",
                                      zotero_items_config=config)
        with tempfile.TemporaryDirectory() as directory:
            config = write_items_config(Path(directory), item_keys=("K1AAAA", "K1AAAA"),
                                        ready=("K1AAAA",), fill_target="K1AAAA")
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(Path(directory) / "program",
                                      Path(directory) / "profile",
                                      zotero_items_config=config)

    def test_fill_target_rejects_non_retryable_status(self):
        with tempfile.TemporaryDirectory() as directory:
            config = write_items_config(Path(directory), fill_status="missing")
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(Path(directory) / "program",
                                      Path(directory) / "profile",
                                      zotero_items_config=config)

    def test_ready_key_rejects_non_downloaded_status(self):
        with tempfile.TemporaryDirectory() as directory:
            config = write_items_config(Path(directory), ready=("K2BBBB",))
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(Path(directory) / "program",
                                      Path(directory) / "profile",
                                      zotero_items_config=config)

    def test_zotero_items_config_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(Path(directory) / "program",
                                      Path(directory) / "profile")

    def test_profile_inputs_live_directly_under_profile_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            profile = Path(directory) / "profile"
            config = write_items_config(Path(directory))
            builder.build_fixture(root, profile, zotero_items_config=config)
            for name in ("套磁信息.md", "套磁模板.md", "套磁跟进模板.md"):
                self.assertTrue((profile / name).is_file(), name)
            self.assertFalse((profile / "套磁邮件").exists())

    def test_creates_owner_consumable_raw_contact_sources_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            profile = Path(directory) / "profile"
            config = write_items_config(Path(directory))
            builder.build_fixture(root, profile, zotero_items_config=config)
            professors_root = root / "教授研究"
            candidates = json.loads((professors_root / "_professor_candidates.json").read_text())
            rows = candidates if isinstance(candidates, list) else candidates.get("professors", [])
            self.assertTrue(any(isinstance(row, dict) and row.get("email") == "faculty@example.edu"
                                for row in rows))
            self.assertEqual(json.loads((professors_root / "_corresp_cache.json").read_text()), {})
            self.assertEqual(json.loads((professors_root / "_署名对照.json").read_text()), {})
            # No owner-less fixture input and no pre-built evidence artifact.
            self.assertFalse((professors_root / "contact-evidence-fixture-input.json").exists())
            self.assertFalse((professors_root / "_联系方式证据.json").exists())

    def test_manifest_protects_builder_owned_rebuilds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            profile = Path(directory) / "profile"
            config = write_items_config(Path(directory))
            builder.build_fixture(root, profile, zotero_items_config=config)
            manifest = builder.build_fixture(root, profile, zotero_items_config=config)
            loaded = json.loads((root / "fixture-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded["builder"], builder.MANIFEST_ID)
            self.assertEqual(manifest["builder_sha256"], loaded["builder_sha256"])


if __name__ == "__main__":
    unittest.main()
