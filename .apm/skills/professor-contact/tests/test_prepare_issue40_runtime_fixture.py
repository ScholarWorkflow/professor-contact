"""Issue #40: deterministic contract of the runtime fixture setup helper.

PC40-R1 requires one producer-owned setup helper that seeds the disposable
Zotero fixture through the real MCP write surface, attaches the deterministic
fill-target PDF, injects the runtime-returned keys into ``papers.json`` and
the preview, and records the official Stage 0 selection.  The helper must fail
closed on every provenance, safety, or protocol mismatch and must never leave
Stage 1–5 canonical outputs behind.
"""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
HELPER_PATH = TESTS_DIR / "runtime" / "prepare_issue40_runtime_fixture.py"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = _load_module("prepare_issue40_runtime_fixture", HELPER_PATH)
builder = _load_module(
    "build_issue32_e2e_fixture",
    TESTS_DIR / "runtime" / "build_issue32_e2e_fixture.py")

PINNED_FIXTURE_SHA = "88d2056f35a6f7e114b6070adbbeeeb355fd4b7f"
READY_KEY = "RTA00001"
FILL_KEY = "RTB00002"
ATTACHMENT_KEY = "ATT00001"
PROFESSOR_DIR = Path("教授研究") / "X分野" / "Example Professor"


@contextmanager
def evidence_file(**overrides):
    evidence = {
        "fixture_kind": "zotero",
        "fixture_repo_sha": PINNED_FIXTURE_SHA,
        "fixture_repo_dirty": "no",
        "fixture_run_id": "zotero-20260916T000000Z-00001",
        "manual_patch": "no",
    }
    evidence.update(overrides)
    with tempfile.TemporaryDirectory(prefix="issue40-evidence.") as tmp:
        path = Path(tmp) / "fixture-evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        yield path


class FakeTransport:
    """Minimal Streamable-HTTP MCP server scripting create/import results."""

    def __init__(self, *, import_payload=None):
        self.item_keys = [READY_KEY, FILL_KEY]
        self.import_payload = import_payload if import_payload is not None else {
            "action": "import", "success": True,
            "data": {"attachmentKey": ATTACHMENT_KEY, "parentItemKey": FILL_KEY},
        }
        self.created = 0
        self.calls = []

    def __call__(self, url, payload_bytes, headers):
        payload = json.loads(payload_bytes)
        self.calls.append((payload.get("method"), payload.get("params")))
        if payload.get("method") == "initialize":
            return 200, {"mcp-session-id": "sess-pc40"}, json.dumps({
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"protocolVersion": "2025-06-18",
                           "serverInfo": {"name": "zotero-mcp", "version": "1.6.0"}},
            })
        if payload.get("method") == "notifications/initialized":
            return 202, {}, ""
        if payload.get("method") == "tools/call":
            params = payload["params"]
            if params.get("name") != "write_item":
                return 200, {}, json.dumps({
                    "jsonrpc": "2.0", "id": payload["id"],
                    "result": {"content": [{"type": "text", "text": "ignored"}]},
                })
            action = params["arguments"]["action"]
            if action == "create":
                key = self.item_keys[self.created]
                self.created += 1
                inner = json.dumps({"itemKey": key, "action": "create"})
            elif action == "import":
                inner = json.dumps(self.import_payload)
            else:
                inner = json.dumps({"success": False, "error": "unknown action"})
            return 200, {}, json.dumps({
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"content": [{"type": "text", "text": inner}]},
            })
        raise AssertionError(f"unexpected method {payload.get('method')!r}")

    def write_item_arguments(self):
        return [params["arguments"]
                for method, params in self.calls
                if method == "tools/call" and params.get("name") == "write_item"]


class PrepareIssue40RuntimeFixtureTest(unittest.TestCase):
    def run_helper(self, transport, evidence, *, consumer_root=None,
                   professor_research_sha="a" * 40,
                   http_url="http://127.0.0.1:24121",
                   mcp_url="http://127.0.0.1:24122/mcp"):
        run_root = tempfile.TemporaryDirectory(prefix="issue40-helper-test.")
        self.addCleanup(run_root.cleanup)
        root = Path(run_root.name)
        program_root = root / "program"
        profile_root = root / "profile"
        output = root / "output" / "runtime-setup.json"
        payload = helper.prepare_runtime_fixture(
            program_root=program_root, profile_root=profile_root,
            consumer_root=consumer_root,
            zotero_http_url=http_url, zotero_mcp_url=mcp_url,
            professor_research_sha=professor_research_sha,
            fixture_evidence=evidence, output=output,
            http_post=transport)
        return payload, root, program_root, output

    def test_happy_path_injects_runtime_keys_and_stage0_target(self):
        transport = FakeTransport()
        with evidence_file() as evidence:
            payload, root, program_root, output = self.run_helper(transport, evidence)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["fixture_repo_sha"], PINNED_FIXTURE_SHA)
        self.assertEqual(payload["item_keys"],
                         {"ready": READY_KEY, "fill_target": FILL_KEY})
        self.assertEqual(payload["fill_target_attachment"]["key"], ATTACHMENT_KEY)
        self.assertEqual(payload["fill_target_attachment"]["parent_item_key"], FILL_KEY)
        self.assertTrue(payload["forbidden_outputs_absent"])
        self.assertNotIn(str(program_root),
                         [call.get("filePath") for call in transport.write_item_arguments()
                          if call.get("action") == "import"])

        papers = json.loads((program_root / PROFESSOR_DIR / "papers.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual([row["item_key"] for row in papers["papers"]],
                         [READY_KEY, FILL_KEY])
        self.assertEqual(papers["papers"][0]["pdf_path"], f"论文分析/{READY_KEY}.pdf")
        self.assertTrue((program_root / PROFESSOR_DIR / f"论文分析/{READY_KEY}.pdf")
                        .is_file())
        preview = json.loads((program_root / PROFESSOR_DIR / "方向预筛.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual([row["item_key"] for row in preview["directions"][0]["members"]],
                         [READY_KEY, FILL_KEY])

        target = json.loads((program_root / "教授研究" / "套磁目标.json")
                            .read_text(encoding="utf-8"))
        row = next(row for row in target["targets"]
                   if row["professor"] == "Example Professor")
        self.assertEqual(row["selected_direction_ids"], ["DIR00001"])

        manifest = json.loads((program_root / "fixture-manifest.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(manifest["item_keys"], [READY_KEY, FILL_KEY])
        self.assertEqual(manifest["missing_item_keys"], [FILL_KEY])
        self.assertEqual(manifest["fixture_run_id"], "zotero-20260916T000000Z-00001")

        stored = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(stored["stage0"]["selected_direction_ids"], ["DIR00001"])
        self.assertIn(READY_KEY, json.dumps(stored["input_hashes"]["program_inputs"]))

        import_calls = [arguments for arguments in transport.write_item_arguments()
                        if arguments["action"] == "import"]
        self.assertEqual(len(import_calls), 1)
        self.assertEqual(import_calls[0]["parentItemKey"], FILL_KEY)
        self.assertTrue(import_calls[0]["filePath"].endswith(".pdf"))
        self.assertEqual(import_calls[0]["title"],
                         "Nonlinear Extensions of Synthetic Processing")

    def test_builder_default_keys_stay_deterministic(self):
        with tempfile.TemporaryDirectory(prefix="issue40-builder-default.") as tmp:
            root = Path(tmp)
            manifest = builder.build_fixture(root / "program", root / "profile")
            self.assertEqual(manifest["item_keys"], ["AAAA1111", "BBBB2222"])
            self.assertNotIn("fixture_run_id", manifest)
            papers = json.loads(
                (root / "program" / PROFESSOR_DIR / "papers.json").read_text(encoding="utf-8"))
            self.assertEqual([row["item_key"] for row in papers["papers"]],
                             ["AAAA1111", "BBBB2222"])

    def test_refuses_production_zotero_ports(self):
        transport = FakeTransport()
        with self.assertRaises(Exception) as ctx:
            self.run_helper(transport, None, http_url="http://127.0.0.1:23119")
        self.assertIn("production", str(ctx.exception))
        with self.assertRaises(Exception) as ctx:
            self.run_helper(transport, None, mcp_url="http://127.0.0.1:23120/mcp")
        self.assertIn("production", str(ctx.exception))
        self.assertEqual(transport.calls, [])

    def test_refuses_unpinned_dirty_or_blank_fixture_evidence(self):
        transport = FakeTransport()
        cases = [
            {"fixture_repo_sha": "0" * 40},
            {"fixture_repo_dirty": "yes"},
            {"manual_patch": "yes"},
            {"fixture_run_id": "   "},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with evidence_file(**overrides) as evidence:
                    with self.assertRaises(Exception):
                        self.run_helper(transport, evidence)
        self.assertEqual(transport.calls, [])

    def test_refuses_missing_fixture_evidence_source(self):
        transport = FakeTransport()
        with mock.patch.dict(os.environ):
            os.environ.pop("FIXTURE_EVIDENCE_FILE", None)
            with self.assertRaises(Exception) as ctx:
                self.run_helper(transport, None)
        self.assertIn("fixture evidence is required", str(ctx.exception))
        self.assertEqual(transport.calls, [])

    def test_refuses_placeholder_professor_research_sha(self):
        transport = FakeTransport()
        with evidence_file() as evidence:
            with self.assertRaises(Exception) as ctx:
                self.run_helper(transport, evidence,
                                professor_research_sha="<professor-research SHA>")
        self.assertIn("40-hex", str(ctx.exception))
        self.assertEqual(transport.calls, [])

    def test_refuses_import_result_without_attachment_key(self):
        transport = FakeTransport(import_payload={"action": "import", "success": True})
        with evidence_file() as evidence:
            with self.assertRaises(Exception) as ctx:
                self.run_helper(transport, evidence)
        self.assertIn("attachmentKey", str(ctx.exception))

    def test_cli_reports_error_as_json_with_exit_1(self):
        with tempfile.TemporaryDirectory(prefix="issue40-cli-test.") as tmp:
            root = Path(tmp)
            completed = subprocess.run(
                ["python3", str(HELPER_PATH),
                 "--program-root", str(root / "program"),
                 "--profile-root", str(root / "profile"),
                 "--zotero-http-url", "http://127.0.0.1:23119",
                 "--zotero-mcp-url", "http://127.0.0.1:24122/mcp",
                 "--professor-research-sha", "a" * 40,
                 "--output", str(root / "output" / "runtime-setup.json")],
                capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "error")
            self.assertIn("production", payload["error"])
            self.assertFalse((root / "output" / "runtime-setup.json").exists())


if __name__ == "__main__":
    unittest.main()
