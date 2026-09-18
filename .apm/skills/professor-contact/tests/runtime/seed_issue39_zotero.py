#!/usr/bin/env python3
"""Seed the disposable PC39 Zotero fixture through the real MCP write path.

The helper creates two fixed synthetic journal articles in the current run's
disposable Zotero library via ``write_item(action=create)`` and records the
runtime-returned ``itemKey`` values.  It never touches the production Zotero
ports, never edits the Zotero database directly, and never invents keys.

``--expected-fixture-revision`` lets a follow-up recipe (issue #51) pin a
newer fixture sha explicitly; the default stays on the original #39 pin.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


HELPER_ID = "tests/runtime/seed_issue39_zotero.py"
SCHEMA_VERSION = 1
FIXTURE_REPOSITORY = "skills-test-fixtures"
FIXTURE_REVISION = "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972"
PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "pc39-zotero-seed", "version": "1"}
PRODUCTION_ZOTERO_PORTS = {23119, 23120}
LEGACY_ITEM_KEYS = {"AAAA1111", "BBBB2222"}
AUTHOR = {"creatorType": "author", "firstName": "Example", "lastName": "Professor"}
FIXED_ITEMS = (
    {
        "role": "ready",
        "fields": {
            "title": "Adaptive Processing in Synthetic Systems",
            "date": "2024",
            "publicationTitle": "Synthetic Processing Journal",
            "abstractNote": "A deterministic synthetic paper about adaptive and "
                            "nonlinear processing.",
        },
    },
    {
        "role": "fill_target",
        "fields": {
            "title": "Nonlinear Extensions of Synthetic Processing",
            "date": "2023",
            "publicationTitle": "Synthetic Processing Journal",
            "abstractNote": "A synthetic paper used to keep the runtime fill "
                            "target explicit.",
        },
    },
)


class SeedError(RuntimeError):
    """Raised when the fixture seed cannot be created safely."""


def _read_json(source: Path | str | dict) -> object:
    if isinstance(source, dict):
        return json.loads(json.dumps(source, ensure_ascii=False))
    with Path(source).open(encoding="utf-8") as handle:
        return json.load(handle)


def _validate_expected_revision(expected_revision: str) -> None:
    """Fail closed unless the expected fixture revision is a 40-hex git sha."""
    if not isinstance(expected_revision, str) \
            or not re.fullmatch(r"[0-9a-f]{40}", expected_revision):
        raise SeedError(
            "expected fixture revision must be a 40-char hex git sha, got "
            f"{expected_revision!r}")


def validate_mcp_url(zotero_mcp_url: str) -> None:
    """Require a complete disposable MCP endpoint; reject production ports."""
    if not isinstance(zotero_mcp_url, str) or not zotero_mcp_url.strip():
        raise SeedError("zotero_mcp_url is required")
    parsed = urlsplit(zotero_mcp_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SeedError(f"zotero_mcp_url must be an absolute http(s) URL: {zotero_mcp_url!r}")
    try:
        port = parsed.port
    except ValueError as exc:
        raise SeedError(f"zotero_mcp_url has an invalid port: {zotero_mcp_url!r}") from exc
    if port in PRODUCTION_ZOTERO_PORTS:
        raise SeedError(
            f"zotero_mcp_url uses production Zotero port {port}; refusing to seed")
    if not parsed.path.rstrip("/").endswith("/mcp"):
        raise SeedError("zotero_mcp_url must be the complete endpoint ending in /mcp")


def validate_fixture_evidence(source: Path | str | dict,
                              expected_revision: str = FIXTURE_REVISION) -> dict:
    """Fail closed unless the evidence belongs to the pinned clean fixture."""
    _validate_expected_revision(expected_revision)
    evidence = _read_json(source)
    if not isinstance(evidence, dict):
        raise SeedError("fixture evidence must be a JSON object")
    if evidence.get("fixture_repo_sha") != expected_revision:
        raise SeedError(
            "fixture evidence fixture_repo_sha does not match the pinned "
            f"{FIXTURE_REPOSITORY}@{expected_revision}")
    if evidence.get("fixture_repo_dirty") != "no":
        raise SeedError("fixture evidence must record fixture_repo_dirty=no")
    if evidence.get("manual_patch") != "no":
        raise SeedError("fixture evidence must record manual_patch=no")
    run_id = evidence.get("fixture_run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise SeedError("fixture evidence fixture_run_id must be a non-empty string")
    return {"revision": expected_revision, "run_id": run_id}


def _http_post(url: str, payload_bytes: bytes, headers: dict[str, str]):
    """Post one JSON-RPC payload; returns (status, response headers, text)."""
    request = urllib.request.Request(
        url, data=payload_bytes, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream", **headers})
    with urllib.request.urlopen(request, timeout=60) as response:
        return (response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read().decode("utf-8"))


def _parse_rpc_response(text: str) -> object:
    """Parse a JSON or SSE-framed JSON-RPC message."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            candidate = line.strip()
            if candidate.startswith("data:"):
                try:
                    return json.loads(candidate[5:].strip())
                except json.JSONDecodeError:
                    continue
    return None


def _rpc_result(http_post, url: str, session: dict[str, str], payload: dict,
                expect_reply: bool = True) -> object:
    status, headers, text = http_post(
        url, json.dumps(payload).encode("utf-8"),
        {"mcp-session-id": session["id"]} if session["id"] else {})
    if status >= 400:
        raise SeedError(f"MCP endpoint returned HTTP {status} for {payload.get('method')}")
    message = _parse_rpc_response(text)
    if expect_reply and not isinstance(message, dict):
        raise SeedError(f"MCP endpoint returned an unparseable response for {payload.get('method')}")
    if isinstance(message, dict) and message.get("error") is not None:
        raise SeedError(
            f"MCP call {payload.get('method')} failed: "
            f"{json.dumps(message.get('error'), ensure_ascii=False)}")
    return message


def _open_session(http_post, url: str) -> dict[str, str]:
    status, headers, text = http_post(
        url,
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": PROTOCOL_VERSION,
                               "capabilities": {},
                               "clientInfo": CLIENT_INFO}}).encode("utf-8"),
        {})
    if status >= 400:
        raise SeedError(f"MCP initialize returned HTTP {status}")
    message = _parse_rpc_response(text)
    if not isinstance(message, dict) or not isinstance(message.get("result"), dict):
        raise SeedError("MCP initialize did not return a JSON-RPC result")
    session_id = headers.get("mcp-session-id", "")
    if not session_id:
        raise SeedError("MCP initialize response did not carry mcp-session-id")
    _rpc_result(http_post, url, {"id": session_id},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                expect_reply=False)
    return {"id": session_id}


def _extract_item_key(result: object) -> str:
    """Pull the runtime-returned itemKey out of a write_item result."""
    if not isinstance(result, dict):
        raise SeedError("write_item returned no result object")
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        key = structured.get("itemKey", structured.get("key"))
        if isinstance(key, str) and key.strip():
            return key.strip()
    content = result.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict) or "text" not in block:
                continue
            try:
                payload = json.loads(block["text"])
            except (json.JSONDecodeError, TypeError):
                continue
            candidates: list[object] = [payload]
            if isinstance(payload, dict):
                candidates.extend(payload.values())
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                key = candidate.get("itemKey", candidate.get("key"))
                if isinstance(key, str) and key.strip():
                    return key.strip()
                successful = candidate.get("successful")
                if isinstance(successful, dict):
                    for row in successful.values():
                        if isinstance(row, dict) and isinstance(row.get("key"), str) \
                                and row["key"].strip():
                            return row["key"].strip()
    raise SeedError("write_item returned no itemKey; refusing to invent one")


def seed_zotero_items(*, zotero_mcp_url: str, fixture_evidence: Path | str | dict,
                      output: Path, http_post=_http_post,
                      expected_revision: str = FIXTURE_REVISION) -> dict:
    validate_mcp_url(zotero_mcp_url)
    evidence = validate_fixture_evidence(
        fixture_evidence, expected_revision=expected_revision)
    session = _open_session(http_post, zotero_mcp_url)
    item_keys: list[str] = []
    for index, item in enumerate(FIXED_ITEMS):
        message = _rpc_result(
            http_post, zotero_mcp_url, session,
            {"jsonrpc": "2.0", "id": 10 + index, "method": "tools/call",
             "params": {"name": "write_item",
                        "arguments": {"action": "create",
                                      "itemType": "journalArticle",
                                      "fields": item["fields"],
                                      "creators": [dict(AUTHOR)]}}})
        if not isinstance(message, dict) or not isinstance(message.get("result"), dict):
            raise SeedError("write_item did not return a JSON-RPC result")
        key = _extract_item_key(message["result"])
        if not isinstance(key, str) or not key.strip():
            raise SeedError("write_item returned a non-string itemKey")
        if key in LEGACY_ITEM_KEYS:
            raise SeedError(f"write_item returned a legacy fake key: {key!r}")
        item_keys.append(key.strip())
    if len(set(item_keys)) != len(FIXED_ITEMS):
        raise SeedError(f"write_item returned duplicate item keys: {item_keys!r}")
    config = {
        "schema_version": SCHEMA_VERSION,
        "fixture_repository": FIXTURE_REPOSITORY,
        "fixture_revision": evidence["revision"],
        "fixture_run_id": evidence["run_id"],
        "item_keys": item_keys,
        "ready_item_keys": [item_keys[0]],
        "fill_target_item_key": item_keys[1],
        "fill_target_pdf_status": "pending",
    }
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(config, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8")
    return {"status": "ok", "helper": HELPER_ID, "output": str(output),
            "item_keys": item_keys}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed the PC39 disposable Zotero fixture via real MCP write_item")
    parser.add_argument("--zotero-mcp-url", required=True)
    parser.add_argument("--fixture-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--expected-fixture-revision", default=FIXTURE_REVISION,
        help="expected skills-test-fixtures git sha "
             f"(default: the #39 pin {FIXTURE_REVISION})")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        status = seed_zotero_items(
            zotero_mcp_url=args.zotero_mcp_url,
            fixture_evidence=args.fixture_evidence,
            output=args.output,
            expected_revision=args.expected_fixture_revision)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(status, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
