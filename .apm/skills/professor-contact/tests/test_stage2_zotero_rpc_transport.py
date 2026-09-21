"""PR #47 review 5701729598: Stage 2 Zotero transport must be deterministic.

The R2 analyzer child probe succeeded on the injected fixture endpoints and
then hand-wrote the production port back into the real RPCs. These tests lock
the producer-owned deterministic transport boundary:

- ``stage2_zotero_rpc.py`` resolves endpoints from the environment only
  (unset/empty -> production fallback) with one trailing slash dropped, and
  its CLI exposes no URL/port/endpoint override;
- real requests must land on a non-default, OS-assigned random port with the
  exact MCP path, session header and ``tools/call`` payload — the tests never
  depend on 23119/23120 being free and never contact the production fallback;
- both analyzer projections carry the post-SID transport boundary in the text
  that installs as the Codex ``developer_instructions``.
"""

import http.server
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".apm" / "skills" / "professor-contact"
HELPER_PATH = SKILL_DIR / "scripts" / "stage2_zotero_rpc.py"
CODEX_ANALYZER_PATH = (
    REPO_ROOT
    / "packages"
    / "professor-contact-codex"
    / ".apm"
    / "agents"
    / "professor-contact-analyzer.agent.md"
)
OPENCODE_ANALYZER_PATH = (
    REPO_ROOT
    / "packages"
    / "professor-contact-opencode"
    / ".apm"
    / "agents"
    / "professor-contact-analyzer.agent.md"
)


def _load_helper_module():
    spec = importlib.util.spec_from_file_location("stage2_zotero_rpc", HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frontmatter_and_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path}: missing opening frontmatter delimiter")
    end = lines.index("---", 1)
    return "\n".join(lines[end + 1 :])


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start + len(start_marker))
    return text[start:end]


def _helper_env(overrides: dict[str, str]) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ZOTERO_")}
    env.update(overrides)
    return env


def _run_helper(args: list[str], env_overrides: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HELPER_PATH), *args],
        capture_output=True,
        text=True,
        timeout=30,
        env=_helper_env(env_overrides),
    )


class _CaptureHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401 - silence request logging
        pass

    def _capture(self, body: str) -> None:
        self.server.requests.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": {k.lower(): v for k, v in self.headers.items()},
                "body": body,
            }
        )
        payload = self.server.response_body.encode("utf-8")
        self.send_response(self.server.response_status)
        self.send_header("Content-Type", self.server.response_content_type)
        self.send_header("Content-Length", str(len(payload)))
        for key, value in self.server.response_headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802 - http.server API
        self._capture("")

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", "0"))
        self._capture(self.rfile.read(length).decode("utf-8"))


class _CaptureServer:
    """Loopback server on an OS-assigned random port; never a default port."""

    def __init__(self):
        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
        self._httpd.requests = []
        self._httpd.response_status = 200
        self._httpd.response_content_type = "application/json"
        self._httpd.response_body = "{}"
        self._httpd.response_headers = {}
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def requests(self):
        return self._httpd.requests

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    @property
    def response_body(self) -> str:
        return self._httpd.response_body

    def respond(self, status=200, content_type="application/json", body="{}", headers=None):
        self._httpd.response_status = status
        self._httpd.response_content_type = content_type
        self._httpd.response_body = body
        self._httpd.response_headers = dict(headers or {})

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


def _refused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ResolveEndpointTests(unittest.TestCase):
    def setUp(self):
        self.helper = _load_helper_module()

    def test_fallback_constants_are_the_production_defaults(self):
        self.assertEqual(self.helper.MCP_FALLBACK, "http://127.0.0.1:23120/mcp")
        self.assertEqual(self.helper.HTTP_FALLBACK, "http://127.0.0.1:23119")

    def test_env_override_wins_and_trailing_slash_is_dropped(self):
        for env_name, fallback, value in (
            ("ZOTERO_MCP_URL", self.helper.MCP_FALLBACK, "http://127.0.0.1:24126/mcp/"),
            ("ZOTERO_HTTP_URL", self.helper.HTTP_FALLBACK, "http://127.0.0.1:24125/"),
        ):
            with self.subTest(env=env_name):
                old = os.environ.get(env_name)
                os.environ[env_name] = value
                try:
                    endpoint, source = self.helper.resolve_endpoint(env_name, fallback)
                finally:
                    if old is None:
                        os.environ.pop(env_name, None)
                    else:
                        os.environ[env_name] = old
                self.assertEqual(endpoint, value.rstrip("/"))
                self.assertEqual(source, "env")

    def test_unset_env_uses_the_production_fallback(self):
        for env_name, fallback in (
            ("ZOTERO_MCP_URL", self.helper.MCP_FALLBACK),
            ("ZOTERO_HTTP_URL", self.helper.HTTP_FALLBACK),
        ):
            with self.subTest(env=env_name):
                old = os.environ.pop(env_name, None)
                try:
                    endpoint, source = self.helper.resolve_endpoint(env_name, fallback)
                finally:
                    if old is not None:
                        os.environ[env_name] = old
                self.assertEqual((endpoint, source), (fallback, "fallback"))

    def test_empty_env_uses_the_production_fallback(self):
        for env_name, fallback in (
            ("ZOTERO_MCP_URL", self.helper.MCP_FALLBACK),
            ("ZOTERO_HTTP_URL", self.helper.HTTP_FALLBACK),
        ):
            with self.subTest(env=env_name):
                old = os.environ.get(env_name)
                os.environ[env_name] = "   "
                try:
                    endpoint, source = self.helper.resolve_endpoint(env_name, fallback)
                finally:
                    if old is None:
                        os.environ.pop(env_name, None)
                    else:
                        os.environ[env_name] = old
                self.assertEqual((endpoint, source), (fallback, "fallback"))


class HelperCliSurfaceTests(unittest.TestCase):
    OVERRIDE_FLAGS = ("--url", "--port", "--endpoint", "--base-url")

    def test_help_never_offers_an_endpoint_override_flag(self):
        for args in (["--help"], ["mcp", "--help"], ["http", "--help"]):
            with self.subTest(args=args):
                done = _run_helper(args, {})
                self.assertEqual(done.returncode, 0, done.stderr)
                for flag in self.OVERRIDE_FLAGS:
                    self.assertNotIn(flag, done.stdout)

    def test_url_port_and_endpoint_flags_are_rejected(self):
        cases = (
            ["mcp", "--url", "http://127.0.0.1:23120/mcp", "--session-id", "s",
             "--tool", "t", "--arguments-json", "{}"],
            ["mcp", "--endpoint", "http://127.0.0.1:23120/mcp", "--session-id", "s",
             "--tool", "t", "--arguments-json", "{}"],
            ["http", "--port", "23119", "--path", "/api/x"],
            ["http", "--base-url", "http://127.0.0.1:23119", "--path", "/api/x"],
        )
        for args in cases:
            with self.subTest(args=args):
                done = _run_helper(args, {})
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)

    def test_invalid_arguments_json_fails_closed_without_contacting_any_server(self):
        with _CaptureServer() as server:
            for raw in ("{bad", "[1, 2]", '"text"'):
                with self.subTest(arguments_json=raw):
                    done = _run_helper(
                        ["mcp", "--session-id", "s", "--tool", "t",
                         "--arguments-json", raw],
                        {"ZOTERO_MCP_URL": f"http://127.0.0.1:{server.port}/mcp"},
                    )
                    self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
                    self.assertIn("invalid_arguments_json", done.stderr)
            self.assertEqual(server.requests, [])

    def test_non_relative_path_is_rejected(self):
        for path in ("http://127.0.0.1:23119/api/x", "api/x", "/api/x http://x"):
            with self.subTest(path=path):
                done = _run_helper(["http", "--path", path], {})
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)


class RandomPortTransportTests(unittest.TestCase):
    def setUp(self):
        server = _CaptureServer()
        server.__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        self.server = server
        # Trailing slashes on purpose: the helper must normalize before use.
        self.env = {
            "ZOTERO_HTTP_URL": f"http://127.0.0.1:{server.port}/",
            "ZOTERO_MCP_URL": f"http://127.0.0.1:{server.port}/mcp/",
        }

    def test_mcp_call_reaches_random_port_with_exact_contract(self):
        self.server.respond(
            body=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": "{\"title\": \"ok\"}"}]},
            })
        )
        done = _run_helper(
            ["mcp", "--session-id", "SID-123", "--tool", "get_item_details",
             "--arguments-json", "{\"itemKey\": \"7GMEQ9R5\"}"],
            self.env,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(self.server.requests), 1)
        request = self.server.requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["path"], "/mcp")
        self.assertEqual(request["headers"]["mcp-session-id"], "SID-123")
        self.assertTrue(
            request["headers"]["content-type"].startswith("application/json"))
        self.assertIn("text/event-stream", request["headers"]["accept"])
        envelope = json.loads(request["body"])
        self.assertEqual(envelope["jsonrpc"], "2.0")
        self.assertEqual(envelope["method"], "tools/call")
        self.assertEqual(envelope["params"]["name"], "get_item_details")
        self.assertEqual(envelope["params"]["arguments"], {"itemKey": "7GMEQ9R5"})
        self.assertEqual(
            json.loads(done.stdout),
            json.loads(self.server.response_body),
        )

    def test_http_call_reaches_random_port_with_relative_path_and_query(self):
        self.server.respond(body=json.dumps({"items": [{"key": "NVSIVAQZ"}]}))
        done = _run_helper(
            ["http", "--path",
             "/api/users/0/collections/ABC/items?format=json&limit=100&start=0"],
            self.env,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(self.server.requests), 1)
        request = self.server.requests[0]
        self.assertEqual(request["method"], "GET")
        self.assertEqual(
            request["path"],
            "/api/users/0/collections/ABC/items?format=json&limit=100&start=0",
        )
        self.assertEqual(json.loads(done.stdout), {"items": [{"key": "NVSIVAQZ"}]})

    def test_http_call_preserves_pagination_total_without_changing_body_stdout(self):
        """Authorship pagination needs Zotero's Total-Results response header.

        Keep stdout backward-compatible for existing body consumers, but expose
        the total count through a deterministic JSON sidecar so the analyzer can
        decide whether start=100, 200, ... is required.  Other response metadata
        is intentionally outside this regression contract.
        """
        body = {"items": [{"key": "PAGE1"}]}
        # The acceptance contract defines both observable branches: a usable
        # Total-Results header becomes an integer, while an absent header is
        # represented explicitly as null.  Keep both in this one pagination
        # case instead of creating a separate format/error matrix.
        for label, headers, expected_total in (
            ("present", {"Total-Results": "101"}, 101),
            ("missing", {}, None),
        ):
            with self.subTest(total_results=label), tempfile.TemporaryDirectory() as tmp:
                self.server.respond(body=json.dumps(body), headers=headers)
                meta_path = Path(tmp) / "response-meta.json"
                done = _run_helper(
                    [
                        "http",
                        "--path",
                        "/api/users/0/collections/ABC/items?format=json&limit=100&start=0",
                        "--response-meta",
                        str(meta_path),
                    ],
                    self.env,
                )
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(json.loads(done.stdout), body)
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["total_results"], expected_total)

    def test_sse_response_is_unwrapped_to_data_payloads(self):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": []}})
        self.server.respond(
            content_type="text/event-stream",
            body=f"event: message\ndata: {payload}\n\n",
        )
        done = _run_helper(
            ["mcp", "--session-id", "s", "--tool", "t", "--arguments-json", "{}"],
            self.env,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), json.loads(payload))

    def test_transport_failure_names_the_resolved_endpoint(self):
        dead = _refused_port()
        done = _run_helper(
            ["mcp", "--session-id", "s", "--tool", "t", "--arguments-json", "{}"],
            {"ZOTERO_MCP_URL": f"http://127.0.0.1:{dead}/mcp"},
        )
        self.assertEqual(done.returncode, 4, done.stdout + done.stderr)
        error = json.loads(done.stderr)
        self.assertEqual(error["error"], "transport_failure")
        self.assertEqual(error["endpoint"], f"http://127.0.0.1:{dead}/mcp")
        self.assertEqual(error["source"], "env")
        self.assertEqual(done.stdout, "")

    def test_non_2xx_is_a_machine_error_with_the_endpoint(self):
        self.server.respond(status=500, body="boom")
        done = _run_helper(
            ["http", "--path", "/api/users/0/collections/ABC/items"],
            self.env,
        )
        self.assertEqual(done.returncode, 5, done.stdout + done.stderr)
        error = json.loads(done.stderr)
        self.assertEqual(error["error"], "http_status")
        self.assertEqual(error["status"], 500)
        self.assertEqual(error["endpoint"],
                         f"http://127.0.0.1:{self.server.port}/api/users/0/collections/ABC/items")


class TransportBoundaryProjectionTests(unittest.TestCase):
    """The installed Codex ``developer_instructions`` = projection body after
    frontmatter; the transport boundary must live in that payload, not just in
    a file the install never reads."""

    def test_codex_developer_instructions_route_zotero_through_the_helper(self):
        body = _frontmatter_and_body(CODEX_ANALYZER_PATH)
        step27 = _section(body, "### Step 2.7", "### Step 3")
        authorship = _section(body, "1.7 **署名线判定", "2. **判定相关论文")
        hard_rules = body[body.index("## Hard rules"):]
        for label, section in (("step27", step27), ("hard_rules", hard_rules)):
            with self.subTest(section=label):
                self.assertIn("stage2_zotero_rpc.py", section)
        self.assertIn("Transport boundary（取得 SID 后生效）", step27)
        self.assertIn("禁止再用 `curl`、Python requests 或手写 URL/port 直连 Zotero", step27)
        self.assertIn("--session-id", step27)
        self.assertIn("--arguments-json", step27)
        self.assertIn(
            "stage2_zotero_rpc.py http --path \"/api/users/0/collections/",
            authorship,
        )
        self.assertIn(
            "stage2_zotero_rpc.py mcp --session-id \"$SID\" --tool get_item_details",
            body,
        )
        self.assertIn("不得自行换端口重试", step27)

    def test_authorship_pagination_consumes_helper_response_metadata(self):
        """Both target projections must keep the pre-existing all-pages contract."""
        for path in (CODEX_ANALYZER_PATH, OPENCODE_ANALYZER_PATH):
            with self.subTest(projection=path.parents[2].name):
                body = _frontmatter_and_body(path)
                authorship = _section(body, "1.7 **署名线判定", "2. **判定相关论文")
                self.assertIn("--response-meta", authorship)
                self.assertIn("total_results", authorship)
                self.assertIn("start=N", authorship)

    def test_projection_contract_documents_no_endpoint_override_flag(self):
        for path in (CODEX_ANALYZER_PATH, OPENCODE_ANALYZER_PATH):
            with self.subTest(projection=path.parents[2].name):
                body = _frontmatter_and_body(path)
                self.assertIsNone(
                    re.search(r"--(url|port|endpoint|base-url)\b", body),
                    f"{path}: endpoint override flags must not be documented",
                )

    def test_transport_boundary_sentences_are_byte_identical_across_projections(self):
        markers = (
            "5. **Transport boundary（取得 SID 后生效）**",
            "   - `get_item_details {\"itemKey\":\"<key>\"}`（经 helper：",
        )
        for marker in markers:
            def line_of(path):
                for line in _frontmatter_and_body(path).splitlines():
                    if line.startswith(marker):
                        return line
                raise AssertionError(f"{path}: missing {marker!r}")

            self.assertEqual(
                line_of(CODEX_ANALYZER_PATH),
                line_of(OPENCODE_ANALYZER_PATH),
                "the shared transport boundary must stay byte-identical across projections",
            )

    def test_opencode_projection_mirrors_the_shared_transport_sections(self):
        body = _frontmatter_and_body(OPENCODE_ANALYZER_PATH)
        step27 = _section(body, "### Step 2.7", "### Step 3")
        self.assertIn("Transport boundary（取得 SID 后生效）", step27)
        self.assertIn("stage2_zotero_rpc.py", step27)

    def test_helper_ships_inside_the_installed_skill_scripts(self):
        self.assertTrue(
            HELPER_PATH.is_file(),
            "stage2_zotero_rpc.py must ship inside the installed skill scripts",
        )


if __name__ == "__main__":
    unittest.main()
