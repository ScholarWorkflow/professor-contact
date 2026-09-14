"""Issue #40: fixture builder binds real dynamic Zotero keys only.

The builder must never hardcode ``AAAA1111``/``BBBB2222`` as Zotero keys
(regression #12: fixed fake keys may not masquerade as real library keys),
must accept the setup helper's dynamic item/attachment keys, must keep the
fill target in the product's formal retryable pre-download state, must never
pre-create Stage 1-5 canonical product outputs, and must record the dynamic
keys plus the fixture run id in the manifest.
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


def items_config(directory: Path, *, item_keys=("ZK9QA2XA", "ZK8PB4YB"),
                 ready=("ZK9QA2XA",), fill_target="ZK8PB4YB",
                 fill_status="pending", run_id="run-2026-09-15-a",
                 attachments=None) -> Path:
    config = directory / "config" / "zotero-items.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "item_keys": list(item_keys),
        "ready_item_keys": list(ready),
        "fill_target_item_key": fill_target,
        "fill_target_pdf_status": fill_status,
        "fixture_run_id": run_id,
        "attachment_keys": attachments or {key: f"ATT-{key}" for key in item_keys},
    }
    config.write_text(json.dumps(payload), encoding="utf-8")
    return config


class Issue32FixtureBuilderTests(unittest.TestCase):
    def test_builds_raw_inputs_from_dynamic_zotero_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            profile = Path(directory) / "profile"
            config = items_config(Path(directory))
            manifest = builder.build_fixture(
                root, profile, zotero_items_config=config,
                consumer_root=Path(directory) / "consumer",
                professor_research_sha="accepted-sha-for-test",
                zotero_http_url="http://127.0.0.1:20000",
                zotero_mcp_url="http://127.0.0.1:20001/mcp")

            self.assertEqual(manifest["fixture_mode"], "initial_raw_inputs")
            self.assertEqual(manifest["professor"], "Example Professor")
            self.assertEqual(manifest["direction_ids"], ["DIR00001"])
            self.assertEqual(manifest["item_keys"], ["ZK9QA2XA", "ZK8PB4YB"])
            self.assertEqual(manifest["ready_item_keys"], ["ZK9QA2XA"])
            self.assertEqual(manifest["missing_item_keys"], ["ZK8PB4YB"])
            self.assertEqual(manifest["fill_target_item_key"], "ZK8PB4YB")
            self.assertEqual(manifest["fill_target_pdf_status"], "pending")
            self.assertEqual(manifest["fixture_run_id"], "run-2026-09-15-a")
            self.assertEqual(manifest["attachment_keys"],
                             {"ZK9QA2XA": "ATT-ZK9QA2XA", "ZK8PB4YB": "ATT-ZK8PB4YB"})
            self.assertEqual(manifest["professor_research_sha"], "accepted-sha-for-test")
            prof = root / "教授研究/X分野/Example Professor"
            papers_payload = json.loads((prof / "papers.json").read_text(encoding="utf-8"))
            papers = {row["item_key"]: row for row in papers_payload["papers"]}
            self.assertEqual(sorted(papers), ["ZK8PB4YB", "ZK9QA2XA"])
            self.assertEqual(papers["ZK9QA2XA"]["pdf_status"], "downloaded")
            self.assertEqual(papers["ZK9QA2XA"]["pdf_path"], "论文分析/ZK9QA2XA.pdf")
            # The fill target stays in the formal retryable state without a
            # local pdf_path; its PDF only exists as the Zotero attachment.
            self.assertEqual(papers["ZK8PB4YB"]["pdf_status"], "pending")
            self.assertNotIn("pdf_path", papers["ZK8PB4YB"])
            self.assertTrue((prof / "论文分析/ZK9QA2XA.pdf").is_file())
            self.assertFalse((prof / "论文分析/ZK8PB4YB.pdf").exists())
            preview = json.loads((prof / "方向预筛.json").read_text(encoding="utf-8"))
            members = [row["item_key"] for row in preview["directions"][0]["members"]]
            self.assertEqual(sorted(members), ["ZK8PB4YB", "ZK9QA2XA"])
            self.assertFalse((root / "教授研究/套磁目标.json").exists())
            self.assertFalse((root / "教授研究/套磁阶段1候选.json").exists())
            forbidden = {Path(path) for path in manifest["forbidden_product_outputs"]}
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁候选输入.json"), forbidden)
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁候选状态.json"), forbidden)
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁选择.json"), forbidden)
            self.assertIn(Path("教授研究/X分野/Example Professor/套磁候选输入.json"), forbidden)
            self.assertFalse(list((prof / "论文分析").glob("*.md")))
            self.assertFalse(list((prof / "论文分析").glob("*.future_work.json")))
            self.assertTrue((profile / "套磁邮件/套磁信息.md").is_file())
            self.assertTrue((profile / "套磁邮件/套磁模板.md").is_file())
            self.assertTrue((profile / "套磁邮件/套磁跟进模板.md").is_file())
            self.assertIn("faculty@example.edu",
                          (root / "教授研究/contact-evidence-fixture-input.json").read_text(encoding="utf-8"))

    def test_requires_dynamic_items_config(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(Path(directory) / "program", Path(directory) / "profile")

    def test_manifest_refuses_legacy_hardcoded_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            for keys in (("AAAA1111", "BBBB2222"), ("ZK9QA2XA", "BBBB2222")):
                config = items_config(Path(directory), item_keys=keys,
                                      ready=(keys[0],), fill_target=keys[1])
                with self.assertRaises(builder.FixtureBuildError):
                    builder.build_fixture(Path(directory) / f"program-{keys[0]}",
                                          Path(directory) / "profile",
                                          zotero_items_config=config)

    def test_attachment_keys_must_cover_every_item(self):
        with tempfile.TemporaryDirectory() as directory:
            config = items_config(Path(directory),
                                  attachments={"ZK9QA2XA": "ATT-ZK9QA2XA"})
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(Path(directory) / "program",
                                      Path(directory) / "profile",
                                      zotero_items_config=config)

    def test_fill_target_rejects_non_retryable_status(self):
        with tempfile.TemporaryDirectory() as directory:
            for status in ("missing", "downloaded", "unknown", ""):
                config = items_config(Path(directory), fill_status=status)
                with self.assertRaises(builder.FixtureBuildError,
                                       msg=f"status {status!r} must be rejected"):
                    builder.build_fixture(Path(directory) / f"program-{status or 'empty'}",
                                          Path(directory) / "profile",
                                          zotero_items_config=config)

    def test_fill_target_must_differ_from_ready_items(self):
        with tempfile.TemporaryDirectory() as directory:
            config = items_config(Path(directory), fill_target="ZK9QA2XA")
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(Path(directory) / "program",
                                      Path(directory) / "profile",
                                      zotero_items_config=config)

    def test_deterministic_pdf_shared_by_local_inputs_and_zotero_import(self):
        ready_pdf = builder.paper_pdf_bytes("ZK9QA2XA", "ready")
        again = builder.paper_pdf_bytes("ZK9QA2XA", "ready")
        fill_pdf = builder.paper_pdf_bytes("ZK8PB4YB", "fill")
        self.assertEqual(ready_pdf, again)
        self.assertNotEqual(ready_pdf, fill_pdf)
        for payload in (ready_pdf, fill_pdf):
            self.assertTrue(payload.startswith(b"%PDF-1.4"))
            self.assertIn(b"/Type /Page", payload)
            self.assertIn(b"/Contents", payload)
            self.assertTrue(payload.rstrip().endswith(b"%%EOF"))

    def test_manifest_protects_builder_owned_rebuilds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            profile = Path(directory) / "profile"
            config = items_config(Path(directory))
            builder.build_fixture(root, profile, zotero_items_config=config)
            manifest = builder.build_fixture(root, profile, zotero_items_config=config)
            loaded = json.loads((root / "fixture-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded["builder"], builder.MANIFEST_ID)
            self.assertEqual(manifest["builder_sha256"], loaded["builder_sha256"])

    def test_rebuild_refuses_foreign_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            root.mkdir()
            (root / "fixture-manifest.json").write_text(
                json.dumps({"builder": "someone-else"}), encoding="utf-8")
            config = items_config(Path(directory))
            with self.assertRaises(builder.FixtureBuildError):
                builder.build_fixture(root, Path(directory) / "profile",
                                      zotero_items_config=config)


if __name__ == "__main__":
    unittest.main()
