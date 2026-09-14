#!/usr/bin/env python3
"""Issue #40 runtime setup helper: the single R1 common-setup entry point.

The helper is the only supported way to prepare the disposable runtime
fixture; executors never hand-assemble Zotero state.  It

1. opens an MCP session against the fixture ``ZOTERO_MCP_URL``;
2. creates synthetic journal items through the fixture's real write surface
   (``write_item`` ``action=create``);
3. imports the deterministic builder PDFs as attachments via ``write_item``
   ``action=import`` (local file import, never a public download);
4. hands the real item/attachment keys to ``build_issue32_e2e_fixture.py``
   so ``papers.json``/preview bind to the actual fixture library;
5. produces the Stage 1 prerequisite canonical target with the repository's
   deterministic Stage 0 helper (``contact_targets.py select``);
6. writes machine-readable setup evidence (dynamic keys, fixture run id,
   input hashes).

It never writes fixture SQLite, never copies a user Zotero profile, and
refuses the production Zotero ports 23119/23120.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
ITEMS_CONFIG_SCHEMA_VERSION = 1
PRODUCTION_ZOTERO_PORTS = ("23119", "23120")
MCP_PROTOCOL_VERSION = "2024-11-05"
SYNTHETIC_ITEM_COUNT = 2
STAGE0_SELECTION_NOTE = "I want to study adaptive and nonlinear extensions of this processing framework."
HELPER_ID = "tests/runtime/prepare_issue40_runtime_fixture.py"


class SetupError(RuntimeError):
    pass


class ZoteroFixtureMcpClient:
    """Minimal MCP JSON-RPC client for the disposable Zotero fixture.

    The HTTP transport is injectable so deterministic tests can exercise the
    full setup orchestration without a running fixture.
    """

    def __init__(self, mcp_url: str, *, transport=None, protocol_version: str = MCP_PROTOCOL_VERSION):
        if not mcp_url:
            raise SetupError("ZOTERO_MCP_URL is required for the runtime fixture setup")
        self.mcp_url = self._normalize_endpoint(mcp_url)
        self.protocol_version = protocol_version
        self._transport = transport or self._http_post
        self._session_id: str | None = None
        self._next_id = 0
        self.initialized = False

    @staticmethod
    def _normalize_endpoint(url: str) -> str:
        url = url.rstrip("/")
        return url if url.endswith("/mcp") else f"{url}/mcp"

    def _http_post(self, body: bytes) -> bytes:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        request = urllib.request.Request(self.mcp_url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    self._session_id = session.strip()
                return raw
        except urllib.error.HTTPError as exc:
            raise SetupError(f"fixture MCP request failed with HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')}") from exc
        except urllib.error.URLError as exc:
            raise SetupError(f"fixture MCP endpoint unreachable at {self.mcp_url}: {exc.reason}") from exc

    def _payload(self) -> dict:
        self._next_id += 1
        return {"jsonrpc": "2.0", "id": self._next_id}

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        payload = self._payload()
        payload["method"] = method
        if params is not None:
            payload["params"] = params
        raw = self._transport(json.dumps(payload).encode("utf-8"))
        try:
            response = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SetupError(f"fixture MCP returned a non-JSON response for {method}: {exc}") from exc
        if not isinstance(response, dict):
            raise SetupError(f"fixture MCP response for {method} is not an object")
        if "error" in response:
            raise SetupError(f"fixture MCP error for {method}: {response['error']}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise SetupError(f"fixture MCP response for {method} has no result object")
        return result

    def initialize(self) -> dict:
        result = self._rpc("initialize", {
            "protocolVersion": self.protocol_version,
            "capabilities": {},
            "clientInfo": {"name": HELPER_ID, "version": "1"},
        })
        self._notify("notifications/initialized")
        self.initialized = True
        return result

    def _notify(self, method: str, params: dict | None = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._transport(json.dumps(payload).encode("utf-8"))

    def call_tool(self, name: str, arguments: dict) -> dict:
        if not self.initialized:
            raise SetupError("fixture MCP session is not initialized")
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content")
        if not isinstance(content, list) or not content:
            raise SetupError(f"tool {name} returned no content")
        text = content[0].get("text") if isinstance(content[0], dict) else None
        if not isinstance(text, str) or not text.strip():
            raise SetupError(f"tool {name} returned no text content")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SetupError(f"tool {name} returned non-JSON content: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise SetupError(f"tool {name} reported failure: {payload.get('error') or payload}")
        return payload.get("data", {})


def _validate_urls(zotero_http_url: str, zotero_mcp_url: str) -> None:
    if not zotero_http_url or not zotero_mcp_url:
        raise SetupError("both --zotero-http-url and --zotero-mcp-url are required")
    for name, url in (("zotero-http-url", zotero_http_url), ("zotero-mcp-url", zotero_mcp_url)):
        if not url.startswith(("http://", "https://")):
            raise SetupError(f"{name} must be an http(s) URL: {url}")
        for port in PRODUCTION_ZOTERO_PORTS:
            suffix = f":{port}"
            rest = url.split("://", 1)[1]
            if rest.split("/", 1)[0].endswith(suffix):
                raise SetupError(
                    f"{name} uses production Zotero port {port}; the runtime fixture "
                    "must run on a disposable fixture port")
        if url.rstrip("/") != url and not url.endswith("/mcp"):
            raise SetupError(f"{name} has an unexpected trailing slash: {url}")


def resolve_stage0_helper(consumer_root: Path | None) -> Path:
    """Resolve the installed deterministic Stage 0 helper (contact_targets.py)."""
    candidates = []
    if consumer_root:
        candidates.append(Path(consumer_root) / ".agents/skills/professor-contact/scripts/contact_targets.py")
    candidates.append(RUNTIME_DIR.parents[1] / "scripts" / "contact_targets.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise SetupError(
        "installed contact_targets.py not found; pass --consumer-root pointing at the clean consumer")


def synthetic_item_payloads() -> list[dict]:
    """Frozen synthetic journal items, in frozen creation order."""
    return [
        {
            "action": "create",
            "itemType": "journalArticle",
            "fields": {
                "title": "Adaptive Processing in Synthetic Systems",
                "abstractNote": "A deterministic synthetic paper about adaptive and nonlinear processing.",
                "date": "2024",
                "publicationTitle": "Journal of Synthetic Runtime Fixtures",
                "language": "en",
            },
            "creators": [
                {"creatorType": "author", "firstName": "Example", "lastName": "Professor"},
                {"creatorType": "author", "firstName": "Synthetic", "lastName": "Researcher"},
            ],
            "tags": ["professor-contact-runtime-fixture"],
        },
        {
            "action": "create",
            "itemType": "journalArticle",
            "fields": {
                "title": "Nonlinear Extensions of Synthetic Processing",
                "abstractNote": "A synthetic paper whose PDF must be collected during Stage 1.",
                "date": "2023",
                "publicationTitle": "Journal of Synthetic Runtime Fixtures",
                "language": "en",
            },
            "creators": [
                {"creatorType": "author", "firstName": "Example", "lastName": "Professor"},
                {"creatorType": "author", "firstName": "Synthetic", "lastName": "Collaborator"},
            ],
            "tags": ["professor-contact-runtime-fixture"],
        },
    ]


def assign_roles(item_keys: list[str]) -> dict[str, str]:
    """Frozen mechanical rule: sorted item keys; first is the ready paper,
    the last is the fill target.  Executors never choose roles by hand."""
    if len(item_keys) != SYNTHETIC_ITEM_COUNT:
        raise SetupError(f"expected exactly {SYNTHETIC_ITEM_COUNT} created items, got {len(item_keys)}")
    ordered = sorted(item_keys)
    return {ordered[0]: "ready", ordered[-1]: "fill"}


def prepare(*, program_root: Path, profile_root: Path, consumer_root: Path | None,
            zotero_http_url: str, zotero_mcp_url: str, professor_research_sha: str,
            fixture_run_id: str, output: Path, transport=None,
            builder_module=None, stage0_runner: str | None = None) -> dict:
    _validate_urls(zotero_http_url, zotero_mcp_url)
    if not fixture_run_id or not fixture_run_id.strip():
        raise SetupError("fixture run id is required (pass --fixture-run-id or export FIXTURE_RUN_ID)")
    if builder_module is None:
        builder_module = _load_builder_module()
    client = ZoteroFixtureMcpClient(zotero_mcp_url, transport=transport)
    server_info = client.initialize()

    created: list[dict] = []
    for payload in synthetic_item_payloads():
        data = client.call_tool("write_item", payload)
        item_key = data.get("itemKey")
        if not isinstance(item_key, str) or not item_key.strip():
            raise SetupError(f"write_item create returned no itemKey: {data}")
        created.append({"item_key": item_key, "title": payload["fields"]["title"]})

    roles = assign_roles([row["item_key"] for row in created])
    with tempfile.TemporaryDirectory(prefix="issue40-pdf-staging.") as staging:
        for row in created:
            role = roles[row["item_key"]]
            pdf_bytes = builder_module.paper_pdf_bytes(row["item_key"], role)
            staged_pdf = Path(staging) / f"{row['item_key']}.pdf"
            staged_pdf.write_bytes(pdf_bytes)
            data = client.call_tool("write_item", {
                "action": "import",
                "filePath": str(staged_pdf.resolve()),
                "parentItemKey": row["item_key"],
                "title": f"{row['title']} (deterministic fixture PDF)",
            })
            attachment_key = data.get("attachmentKey")
            if not isinstance(attachment_key, str) or not attachment_key.strip():
                raise SetupError(f"write_item import returned no attachmentKey: {data}")
            row["role"] = role
            row["attachment_key"] = attachment_key
            row["pdf_sha256"] = hashlib.sha256(pdf_bytes).hexdigest()

    item_keys = [row["item_key"] for row in created]
    ready_item_keys = sorted(key for key, role in roles.items() if role == "ready")
    fill_target = next(key for key, role in roles.items() if role == "fill")
    items_config = {
        "schema_version": ITEMS_CONFIG_SCHEMA_VERSION,
        "fixture_run_id": fixture_run_id,
        "item_keys": item_keys,
        "ready_item_keys": ready_item_keys,
        "fill_target_item_key": fill_target,
        "fill_target_pdf_status": "pending",
        "attachment_keys": {row["item_key"]: row["attachment_key"] for row in created},
    }
    manifest = builder_module.build_fixture(
        program_root, profile_root, zotero_items_config=items_config,
        consumer_root=consumer_root, professor_research_sha=professor_research_sha,
        zotero_http_url=zotero_http_url, zotero_mcp_url=zotero_mcp_url)

    stage0_script = Path(stage0_runner).resolve() if stage0_runner else resolve_stage0_helper(consumer_root)
    preview_path = Path(manifest["program_root"]) / "教授研究/X分野/Example Professor/方向预筛.json"
    stage0 = run_stage0_select(stage0_script, Path(manifest["program_root"]), preview_path,
                               fixture_run_id=fixture_run_id)

    evidence = {
        "schema_version": 1,
        "helper": HELPER_ID,
        "fixture_run_id": fixture_run_id,
        "zotero_http_url": zotero_http_url,
        "zotero_mcp_url": zotero_mcp_url,
        "professor_research_sha": professor_research_sha,
        "mcp_server_info": server_info.get("serverInfo"),
        "items": created,
        "role_assignment_rule": "sorted(item_keys): first=ready, last=fill_target",
        "item_keys": item_keys,
        "ready_item_keys": ready_item_keys,
        "fill_target_item_key": fill_target,
        "attachment_keys": items_config["attachment_keys"],
        "builder_manifest": {
            "builder": manifest["builder"],
            "builder_sha256": manifest["builder_sha256"],
            "fixture_run_id": manifest["fixture_run_id"],
            "program_root": manifest["program_root"],
            "profile_root": manifest["profile_root"],
            "item_keys": manifest["item_keys"],
            "ready_item_keys": manifest["ready_item_keys"],
            "fill_target_item_key": manifest["fill_target_item_key"],
            "fill_target_pdf_status": manifest["fill_target_pdf_status"],
        },
        "stage0": stage0,
        "input_hashes": manifest["protected_files"],
    }
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return evidence


def run_stage0_select(stage0_script: Path, program_root: Path, preview_path: Path,
                      *, fixture_run_id: str) -> dict:
    """Run the deterministic Stage 0 helper to create 套磁目标.json."""
    selection = {
        "direction_ids": ["DIR00001"],
        "notes": {"DIR00001": STAGE0_SELECTION_NOTE},
    }
    with tempfile.TemporaryDirectory(prefix="issue40-stage0.") as staging:
        selection_file = Path(staging) / "stage0-selection.json"
        selection_file.write_text(json.dumps(selection, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(stage0_script), "select",
             "--program-root", str(program_root),
             "--preview", str(preview_path),
             "--selection-file", str(selection_file)],
            capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise SetupError(
            f"Stage 0 select failed (exit {completed.returncode}): "
            f"{completed.stdout.strip()} / {completed.stderr.strip()}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SetupError(f"Stage 0 select returned non-JSON output: {exc}") from exc
    if payload.get("status") != "ok":
        raise SetupError(f"Stage 0 select did not succeed: {payload}")
    target_path = program_root / "教授研究/套磁目标.json"
    if not target_path.is_file():
        raise SetupError(f"Stage 0 select did not create {target_path}")
    return {
        "helper": stage0_script.name,
        "helper_sha256": hashlib.sha256(stage0_script.read_bytes()).hexdigest(),
        "selection": selection,
        "result": payload,
        "target_file": str(target_path),
        "selected_direction_ids": selection["direction_ids"],
        "fixture_run_id": fixture_run_id,
    }


def _load_builder_module():
    import importlib.util
    builder_path = RUNTIME_DIR / "build_issue32_e2e_fixture.py"
    spec = importlib.util.spec_from_file_location("issue40_fixture_builder", builder_path)
    if spec is None or spec.loader is None:
        raise SetupError(f"cannot load builder module: {builder_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--consumer-root", type=Path)
    parser.add_argument("--zotero-http-url", required=True)
    parser.add_argument("--zotero-mcp-url", required=True)
    parser.add_argument("--professor-research-sha", default="")
    parser.add_argument("--fixture-run-id",
                        default=os.environ.get("FIXTURE_RUN_ID", ""),
                        help="fixture run id (defaults to exported FIXTURE_RUN_ID)")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = prepare(
            program_root=args.program_root, profile_root=args.profile_root,
            consumer_root=args.consumer_root,
            zotero_http_url=args.zotero_http_url, zotero_mcp_url=args.zotero_mcp_url,
            professor_research_sha=args.professor_research_sha,
            fixture_run_id=args.fixture_run_id, output=args.output)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(Path(args.output).resolve()),
                      "fixture_run_id": evidence["fixture_run_id"],
                      "item_keys": evidence["item_keys"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
