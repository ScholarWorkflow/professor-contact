"""Issue #40 runtime setup helper regressions.

The helper is the single R1 setup entry: it must create synthetic items on
the disposable fixture's real write surface, import the deterministic PDFs
as attachments, bind the real keys into the builder inputs, produce the
Stage 1 prerequisite canonical target with the repository's deterministic
Stage 0 helper, and refuse production Zotero ports and missing fixture run
ids.  Deterministic tests exercise the orchestration with a scripted MCP
transport; no Zotero, network, or model is ever started.
"""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
HELPER_PATH = TESTS_DIR / "runtime/prepare_issue40_runtime_fixture.py"
BUILDER_PATH = TESTS_DIR / "runtime/build_issue32_e2e_fixture.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load_module("issue40_runtime_setup", HELPER_PATH)
builder = load_module("issue40_fixture_builder_for_setup", BUILDER_PATH)

HTTP_URL = "http://127.0.0.1:21001"
MCP_URL = "http://127.0.0.1:21002/mcp"


class FakeFixtureMcp:
    """Scripted MCP fixture: hands out deterministic keys and records calls."""

    def __init__(self, item_keys=("QZ7KA1M2", "QZ6LB9N3")):
        self.item_keys = list(item_keys)
        self.create_seq = 0
        self.attachment_seq = 0
        self.requests: list[dict] = []
        self.imported: list[dict] = []
        self.imported_bytes: dict[str, bytes] = {}
        self.initialized = False
        self.server_info = {"name": "zotero-mcp-fixture", "version": "1.6.0"}

    def transport(self, body: bytes) -> bytes:
        request = json.loads(body.decode("utf-8"))
        self.requests.append(request)
        method = request.get("method")
        if method == "initialize":
            return json.dumps({
                "jsonrpc": "2.0", "id": request.get("id"),
                "result": {"protocolVersion": "2024-11-05",
                           "serverInfo": self.server_info},
            }).encode("utf-8")
        if method == "notifications/initialized":
            self.initialized = True
            return b""
        if method == "tools/call":
            return json.dumps(self._tool_call(request)).encode("utf-8")
        return json.dumps({
            "jsonrpc": "2.0", "id": request.get("id"),
            "error": {"code": -32601, "message": f"unexpected method {method}"},
        }).encode("utf-8")

    def _tool_call(self, request: dict) -> dict:
        name = request["params"]["name"]
        arguments = request["params"]["arguments"]
        if name == "write_item" and arguments.get("action") == "create":
            item_key = self.item_keys[self.create_seq]
            self.create_seq += 1
            payload = {"success": True, "data": {"itemKey": item_key, "itemType": "journalArticle"}}
        elif name == "write_item" and arguments.get("action") == "import":
            self.attachment_seq += 1
            self.imported.append(arguments)
            # The staged file only exists during the call; read it here.
            self.imported_bytes[arguments["parentItemKey"]] = Path(arguments["filePath"]).read_bytes()
            payload = {"success": True, "data": {"attachmentKey": f"ATTNUM{self.attachment_seq:04d}",
                                                 "parentItemKey": arguments.get("parentItemKey")}}
        else:
            payload = {"success": False, "error": f"unexpected tool call {name}"}
        return {"jsonrpc": "2.0", "id": request.get("id"),
                "result": {"content": [{"type": "text", "text": json.dumps(payload)}]}}


class Issue40RuntimeSetupTests(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.base = Path(self.holder.name)
        self.program = self.base / "program"
        self.profile = self.base / "profile"
        self.output = self.base / "output" / "runtime-setup.json"

    def prepare(self, fixture: FakeFixtureMcp, *, http_url=HTTP_URL, mcp_url=MCP_URL,
                run_id="run-2026-09-15-a", consumer_root=None, stage0_runner=None):
        return helper.prepare(
            program_root=self.program, profile_root=self.profile,
            consumer_root=consumer_root,
            zotero_http_url=http_url, zotero_mcp_url=mcp_url,
            professor_research_sha="accepted-sha-for-test",
            fixture_run_id=run_id, output=self.output,
            transport=fixture.transport, builder_module=builder,
            stage0_runner=stage0_runner)

    def test_prepare_binds_real_fixture_keys_and_prepares_stage0_target(self):
        fixture = FakeFixtureMcp()
        evidence = self.prepare(fixture)

        # Machine-readable setup evidence with dynamic keys + run id + hashes.
        self.assertEqual(evidence["helper"], helper.HELPER_ID)
        self.assertEqual(evidence["fixture_run_id"], "run-2026-09-15-a")
        self.assertEqual(evidence["professor_research_sha"], "accepted-sha-for-test")
        self.assertEqual(evidence["mcp_server_info"], fixture.server_info)
        saved = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(saved, evidence)

        # MCP write surface: create before import, absolute import path, and
        # the imported bytes are exactly the deterministic builder PDFs.
        creates = [row for row in fixture.requests
                   if row.get("method") == "tools/call"
                   and row["params"]["arguments"].get("action") == "create"]
        imports = [row for row in fixture.requests
                   if row.get("method") == "tools/call"
                   and row["params"]["arguments"].get("action") == "import"]
        self.assertEqual([row["params"]["arguments"]["itemType"] for row in creates],
                         ["journalArticle", "journalArticle"])
        self.assertTrue(fixture.initialized)
        self.assertEqual(len(imports), 2)
        self.assertTrue(fixture.initialized and imports and creates
                        and fixture.requests.index(creates[-1]) < fixture.requests.index(imports[0]))
        roles = {row["item_key"]: row["role"] for row in evidence["items"]}
        for arguments in fixture.imported:
            self.assertTrue(Path(arguments["filePath"]).is_absolute(), arguments)
            parent = arguments["parentItemKey"]
            self.assertEqual(fixture.imported_bytes[parent],
                             builder.paper_pdf_bytes(parent, roles[parent]))
        for row in evidence["items"]:
            self.assertEqual(row["pdf_sha256"], hashlib.sha256(
                builder.paper_pdf_bytes(row["item_key"], row["role"])).hexdigest())

        # Frozen role rule: sorted item keys, first = ready, last = fill.
        item_keys = sorted(fixture.item_keys)
        self.assertEqual(evidence["role_assignment_rule"],
                         "sorted(item_keys): first=ready, last=fill_target")
        self.assertEqual(evidence["ready_item_keys"], [item_keys[0]])
        self.assertEqual(evidence["fill_target_item_key"], item_keys[-1])
        self.assertEqual(evidence["attachment_keys"],
                         {row["item_key"]: row["attachment_key"] for row in evidence["items"]})

        # Builder inputs bind the real keys; fill target keeps retry state.
        manifest = json.loads((self.program / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["item_keys"], fixture.item_keys)
        self.assertEqual(manifest["fixture_run_id"], "run-2026-09-15-a")
        papers = {row["item_key"]: row
                  for row in json.loads(
                      (self.program / "教授研究/X分野/Example Professor/papers.json")
                      .read_text(encoding="utf-8"))["papers"]}
        self.assertEqual(papers[item_keys[0]]["pdf_status"], "downloaded")
        self.assertEqual(papers[item_keys[-1]]["pdf_status"], "pending")
        self.assertNotIn("pdf_path", papers[item_keys[-1]])

        # Stage 0 canonical target produced by the deterministic helper.
        target = json.loads((self.program / "教授研究/套磁目标.json").read_text(encoding="utf-8"))
        self.assertEqual(target["targets"][0]["selected_direction_ids"], ["DIR00001"])
        self.assertEqual(evidence["stage0"]["selected_direction_ids"], ["DIR00001"])
        self.assertEqual(evidence["stage0"]["target_file"],
                         str((self.program / "教授研究/套磁目标.json").resolve()))
        self.assertNotIn("套磁阶段1候选.json",
                         [path.name for path in (self.program / "教授研究").glob("*.json")])

    def test_refuses_production_zotero_ports(self):
        for port in ("23119", "23120"):
            with self.assertRaises(helper.SetupError, msg=f"port {port} must be refused"):
                self.prepare(FakeFixtureMcp(),
                             http_url=f"http://127.0.0.1:{port}",
                             mcp_url=f"http://127.0.0.1:{int(port) + 1}/mcp")
            with self.assertRaises(helper.SetupError, msg=f"port {port} must be refused"):
                self.prepare(FakeFixtureMcp(),
                             http_url="http://127.0.0.1:21001",
                             mcp_url=f"http://127.0.0.1:{port}/mcp")

    def test_requires_fixture_run_id(self):
        with self.assertRaises(helper.SetupError):
            self.prepare(FakeFixtureMcp(), run_id="  ")

    def test_requires_fixture_urls(self):
        with self.assertRaises(helper.SetupError):
            self.prepare(FakeFixtureMcp(), http_url="")
        with self.assertRaises(helper.SetupError):
            self.prepare(FakeFixtureMcp(), mcp_url="ftp://example/mcp")

    def test_role_assignment_is_frozen_and_total(self):
        roles = helper.assign_roles(["ZZZ9", "AAA1"])
        self.assertEqual(roles, {"AAA1": "ready", "ZZZ9": "fill"})
        with self.assertRaises(helper.SetupError):
            helper.assign_roles(["ONLY1"])

    def test_mcp_endpoint_normalizes_mcp_path(self):
        client = helper.ZoteroFixtureMcpClient("http://127.0.0.1:21002")
        self.assertEqual(client.mcp_url, "http://127.0.0.1:21002/mcp")
        client = helper.ZoteroFixtureMcpClient("http://127.0.0.1:21002/mcp")
        self.assertEqual(client.mcp_url, "http://127.0.0.1:21002/mcp")

    def test_tool_failure_is_a_setup_error(self):
        fixture = FakeFixtureMcp()
        origin = fixture._tool_call

        def failing_tool_call(request):
            response = origin(request)
            payload = json.loads(response["result"]["content"][0]["text"])
            payload["success"] = False
            payload["error"] = "boom"
            response["result"]["content"][0]["text"] = json.dumps(payload)
            return response

        fixture._tool_call = failing_tool_call
        with self.assertRaises(helper.SetupError):
            self.prepare(fixture)

    def test_stage0_runner_must_succeed(self):
        with self.assertRaises(helper.SetupError):
            self.prepare(FakeFixtureMcp(), stage0_runner=str(self.base / "missing" / "contact_targets.py"))


if __name__ == "__main__":
    unittest.main()
