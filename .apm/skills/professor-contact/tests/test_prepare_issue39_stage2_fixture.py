"""Issue #39: build a producer-owned Stage 2 runtime prerequisite.

The runtime case must enter the installed analyzer with a product-built Stage 0
target and Stage 1 snapshot.  This test keeps that setup separate from the
Stage 1 LLM download/collector chain and binds the program to dynamic Zotero
fixture keys instead of the old fake keys.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
HELPER_PATH = TESTS_DIR / "runtime" / "prepare_issue39_stage2_fixture.py"
spec = importlib.util.spec_from_file_location("prepare_issue39_stage2_fixture", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def items_config(run_id="fixture-run-39"):
    return {
        "schema_version": 1,
        "fixture_repository": "skills-test-fixtures",
        "fixture_revision": "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972",
        "fixture_run_id": run_id,
        "item_keys": ["ZK9QA2XA", "ZK8PB4YB"],
        "ready_item_keys": ["ZK9QA2XA"],
        "fill_target_item_key": "ZK8PB4YB",
        "fill_target_pdf_status": "pending",
        "attachment_keys": {
            "ZK9QA2XA": "ATT-ZK9QA2XA",
            "ZK8PB4YB": "ATT-ZK8PB4YB",
        },
    }


class PrepareIssue39Stage2FixtureTests(unittest.TestCase):
    def test_builds_stage2_prerequisite_with_dynamic_keys_and_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "program"
            evidence_path = Path(directory) / "output" / "setup.json"
            evidence = helper.prepare_stage2_prerequisite(
                program_root=root,
                zotero_items_config=items_config(),
                zotero_http_url="http://127.0.0.1:24119",
                zotero_mcp_url="http://127.0.0.1:24120/mcp",
                professor_research_sha="producer-sha-for-test",
                output=evidence_path,
            )

            self.assertEqual(evidence["helper"], helper.HELPER_ID)
            self.assertEqual(evidence["fixture"]["repository"], "skills-test-fixtures")
            self.assertEqual(
                evidence["fixture"]["revision"],
                "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972",
            )
            self.assertEqual(evidence["fixture_run_id"], "fixture-run-39")
            self.assertEqual(evidence["item_keys"], ["ZK9QA2XA", "ZK8PB4YB"])
            self.assertEqual(evidence["ready_item_keys"], ["ZK9QA2XA"])
            self.assertEqual(evidence["fill_target_item_key"], "ZK8PB4YB")
            self.assertEqual(evidence["stage0"]["status"], "ok")
            self.assertEqual(evidence["stage1"]["build"]["status"], "ok")
            self.assertEqual(evidence["stage1"]["verify"]["status"], "ok")
            self.assertEqual(evidence["professor_research_sha"], "producer-sha-for-test")
            self.assertTrue(evidence_path.is_file())

            program = root / "教授研究" / "X分野" / "Example Professor"
            self.assertTrue((root / "教授研究" / "套磁目标.json").is_file())
            self.assertTrue((root / "教授研究" / "套磁阶段1候选.json").is_file())
            papers = helper.read_json(program / "papers.json")["papers"]
            by_key = {row["item_key"]: row for row in papers}
            self.assertEqual(by_key["ZK9QA2XA"]["pdf_status"], "downloaded")
            self.assertEqual(by_key["ZK8PB4YB"]["pdf_status"], "pending")
            self.assertTrue((program / "论文分析" / "ZK9QA2XA.pdf").is_file())
            self.assertFalse((program / "套磁候选输入.json").exists())

    def test_rejects_production_zotero_ports(self):
        with self.assertRaises(helper.SetupError):
            helper.validate_runtime_endpoints(
                "http://127.0.0.1:23119", "http://127.0.0.1:24120/mcp")
        with self.assertRaises(helper.SetupError):
            helper.validate_runtime_endpoints(
                "http://127.0.0.1:24119", "http://127.0.0.1:23120/mcp")

    def test_rejects_legacy_fake_item_keys(self):
        config = items_config()
        config["item_keys"] = ["AAAA1111", "ZK8PB4YB"]
        config["ready_item_keys"] = ["AAAA1111"]
        config["attachment_keys"] = {
            "AAAA1111": "ATT-AAAA1111", "ZK8PB4YB": "ATT-ZK8PB4YB",
        }
        with self.assertRaises(helper.SetupError):
            helper.validate_items_config(config)

    def test_rejects_unpinned_fixture_revision(self):
        config = items_config()
        config["fixture_revision"] = "main"
        with self.assertRaises(helper.SetupError):
            helper.validate_items_config(config)


if __name__ == "__main__":
    unittest.main()
