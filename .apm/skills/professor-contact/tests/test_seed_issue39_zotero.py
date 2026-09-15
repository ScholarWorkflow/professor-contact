"""Issue #39: deterministic contract of the real-MCP Zotero seed helper.

PC39-R1 needs dynamically seeded Zotero items whose real runtime ``itemKey``
values flow into the Stage 2 prerequisite.  The helper must fail closed on
every provenance, safety, or protocol mismatch, and its output must never
contain fabricated keys or attachment keys.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
HELPER_PATH = TESTS_DIR / "runtime" / "seed_issue39_zotero.py"
spec = importlib.util.spec_from_file_location("seed_issue39_zotero", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def fixture_evidence(run_id="zotero-20260915T000000Z-00001"):
    return {
        "fixture_kind": "zotero",
        "fixture_repo_sha": "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972",
        "fixture_repo_dirty": "no",
        "fixture_run_id": run_id,
        "manual_patch": "no",
    }


def write_evidence(directory, evidence):
    path = Path(directory) / "fixture-evidence.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return path


class FakeTransport:
    """Minimal Streamable-HTTP MCP server returning scripted item keys."""

    def __init__(self, item_keys, *, sse=False, omit_session=False):
        self.item_keys = list(item_keys)
        self.sse = sse
        self.omit_session = omit_session
        self.created = 0
        self.calls = []

    def __call__(self, url, payload_bytes, headers):
        payload = json.loads(payload_bytes)
        self.calls.append((payload.get("method"), payload.get("params")))
        if payload.get("method") == "initialize":
            headers = {} if self.omit_session else {"mcp-session-id": "sess-pc39"}
            return 200, headers, json.dumps({
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"protocolVersion": "2025-06-18",
                           "serverInfo": {"name": "zotero-mcp", "version": "1.6.0"}},
            })
        if payload.get("method") == "notifications/initialized":
            return 202, {}, ""
        if payload.get("method") == "tools/call":
            name = payload["params"]["name"]
            if name != "write_item":
                return 200, {}, json.dumps({
                    "jsonrpc": "2.0", "id": payload["id"],
                    "result": {"content": [{"type": "text", "text": "ignored"}]},
                })
            key = self.item_keys[self.created]
            self.created += 1
            inner = json.dumps({"itemKey": key, "action": "create"})
            body_text = inner if not self.sse else (
                "event: message\ndata: " + json.dumps({
                    "jsonrpc": "2.0", "id": payload["id"],
                    "result": {"content": [{"type": "text", "text": inner}]},
                }) + "\n")
            if self.sse:
                return 200, {}, body_text
            return 200, {}, json.dumps({
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"content": [{"type": "text", "text": inner}]},
            })
        raise AssertionError(f"unexpected method {payload.get('method')!r}")


def seed(directory, mcp_url="http://127.0.0.1:24122/mcp",
         evidence=None, transport=None):
    evidence_path = write_evidence(directory, evidence or fixture_evidence())
    output = Path(directory) / "zotero-items.json"
    status = helper.seed_zotero_items(
        zotero_mcp_url=mcp_url,
        fixture_evidence=evidence_path,
        output=output,
        http_post=transport or FakeTransport(["ZK9QA2XA", "ZK8PB4YB"]),
    )
    return status, output


class SeedIssue39ZoteroTests(unittest.TestCase):
    def test_seeds_two_items_with_runtime_returned_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeTransport(["ZK9QA2XA", "ZK8PB4YB"])
            status, output = seed(directory, transport=transport)
            self.assertEqual(status["status"], "ok")
            config = json.loads(output.read_text())
            self.assertEqual(config["schema_version"], 1)
            self.assertEqual(config["fixture_repository"], "skills-test-fixtures")
            self.assertEqual(
                config["fixture_revision"],
                "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972")
            self.assertEqual(config["fixture_run_id"],
                             "zotero-20260915T000000Z-00001")
            self.assertEqual(config["item_keys"], ["ZK9QA2XA", "ZK8PB4YB"])
            self.assertEqual(config["ready_item_keys"], ["ZK9QA2XA"])
            self.assertEqual(config["fill_target_item_key"], "ZK8PB4YB")
            self.assertEqual(config["fill_target_pdf_status"], "pending")
            self.assertNotIn("attachment_keys", config)
            methods = [call[0] for call in transport.calls]
            self.assertEqual(methods[0], "initialize")
            self.assertIn("notifications/initialized", methods)
            self.assertEqual(methods.count("tools/call"), 2)
            write_calls = [params for method, params in transport.calls
                           if method == "tools/call"]
            for params in write_calls:
                arguments = params["arguments"]
                self.assertEqual(arguments["action"], "create")
                self.assertEqual(arguments["itemType"], "journalArticle")
                self.assertEqual(arguments["creators"],
                                 [{"creatorType": "author",
                                   "firstName": "Example",
                                   "lastName": "Professor"}])
            titles = [params["arguments"]["fields"]["title"]
                      for params in write_calls]
            self.assertEqual(titles, ["Adaptive Processing in Synthetic Systems",
                                      "Nonlinear Extensions of Synthetic Processing"])

    def test_parses_sse_framed_write_results(self):
        with tempfile.TemporaryDirectory() as directory:
            status, _ = seed(directory, transport=FakeTransport(
                ["ZQ1AAAAA", "ZQ2BBBBB"], sse=True))
            self.assertEqual(status["status"], "ok")

    def test_missing_item_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = FakeTransport(["ZK9QA2XA", "ZK8PB4YB"])

            def drop_key(url, payload_bytes, headers):
                status, headers_out, text = base(url, payload_bytes, headers)
                try:
                    payload = json.loads(text)
                    inner = json.loads(payload["result"]["content"][0]["text"])
                    inner.pop("itemKey")
                    payload["result"]["content"][0]["text"] = json.dumps(inner)
                    text = json.dumps(payload)
                except (json.JSONDecodeError, KeyError):
                    pass
                return status, headers_out, text

            with self.assertRaises(helper.SeedError):
                seed(directory, transport=drop_key)

    def test_evidence_provenance_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = fixture_evidence()
            evidence["fixture_repo_sha"] = "deadbeef"
            with self.assertRaises(helper.SeedError):
                seed(directory, evidence=evidence)
        with tempfile.TemporaryDirectory() as directory:
            evidence = fixture_evidence()
            evidence["fixture_repo_dirty"] = "yes"
            with self.assertRaises(helper.SeedError):
                seed(directory, evidence=evidence)
        with tempfile.TemporaryDirectory() as directory:
            evidence = fixture_evidence()
            evidence["manual_patch"] = "yes"
            with self.assertRaises(helper.SeedError):
                seed(directory, evidence=evidence)
        with tempfile.TemporaryDirectory() as directory:
            evidence = fixture_evidence()
            evidence["fixture_run_id"] = ""
            with self.assertRaises(helper.SeedError):
                seed(directory, evidence=evidence)

    def test_production_and_incomplete_mcp_urls_are_rejected(self):
        for url in ("http://127.0.0.1:23120/mcp", "http://127.0.0.1:23119/mcp",
                    "http://127.0.0.1:24122", ""):
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(helper.SeedError):
                    seed(directory, mcp_url=url)

    def test_only_runtime_returned_distinct_string_keys_are_accepted(self):
        for bad_keys in (["ZK9QA2XA", "ZK9QA2XA"], ["ZK9QA2XA", 123],
                         ["ZK9QA2XA", ""], ["AAAA1111", "ZK8PB4YB"]):
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(helper.SeedError):
                    seed(directory, transport=FakeTransport(bad_keys))

    def test_initialize_without_session_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(helper.SeedError):
                seed(directory, transport=FakeTransport(
                    ["ZK9QA2XA", "ZK8PB4YB"], omit_session=True))

    def test_jsonrpc_error_response_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            def erroring(url, payload_bytes, headers):
                payload = json.loads(payload_bytes)
                if payload.get("method") == "tools/call":
                    return 200, {}, json.dumps({
                        "jsonrpc": "2.0", "id": payload["id"],
                        "error": {"code": -32000, "message": "library locked"}})
                return FakeTransport(["ZK9QA2XA", "ZK8PB4YB"])(
                    url, payload_bytes, headers)

            with self.assertRaises(helper.SeedError):
                seed(directory, transport=erroring)


if __name__ == "__main__":
    unittest.main()
