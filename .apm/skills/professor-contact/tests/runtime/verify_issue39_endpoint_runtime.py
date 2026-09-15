#!/usr/bin/env python3
"""Offline machine verdict for the issue #39 PC39-R1 runtime evidence.

The verifier judges only structured evidence: the fixture adapter's formal
``spawnAgent`` child thread, that child's ``item/completed`` command events,
and a second JSON parse of the JSON-RPC payloads inside the child's command
output.  Assistant final text, named identity, ``paper-analysis`` completion,
and ``stage2-final`` state are never PASS evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import tomllib
from pathlib import Path


HELPER_ID = "tests/runtime/verify_issue39_endpoint_runtime.py"
SCHEMA_VERSION = 1
FIXTURE_REPOSITORY = "skills-test-fixtures"
FIXTURE_REVISION = "f412b79fde390dfcaa73fa7c4bc9bd10bd1f8972"
DEFAULT_HTTP_URL = "http://127.0.0.1:23119"
DEFAULT_MCP_URL = "http://127.0.0.1:23120/mcp"
READ_TOOLS = {"get_item_details", "get_item_abstract"}
DEFAULT_ENDPOINT_PATTERN = re.compile(
    r"https?://\S*?127\.0\.0\.1:231(19|20)\b")
MCP_MCP_PATTERN = re.compile(r"/mcp/mcp(?!/)", re.IGNORECASE)
BLOCKED = "BLOCKED_TEST_CONFIGURATION"
OBSERVABILITY = "BLOCKED_OBSERVABILITY"
FAIL_PRODUCER = "FAIL_PRODUCER"


def _load(source: Path | str | dict) -> object:
    if isinstance(source, dict):
        return source
    with Path(source).open(encoding="utf-8") as handle:
        return json.load(handle)


def _decode_json_objects(text: str) -> list[dict]:
    """Second-pass parse: pull every embedded JSON object out of raw text."""
    if not text:
        return []
    decoder = json.JSONDecoder()
    payloads: list[dict] = []
    index = 0
    while True:
        start = text.find("{", index)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text, start)
            index = start + 1 if end <= start else end
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(value, dict):
            payloads.append(value)
    return payloads


def _rpc_payloads(text: str) -> list[dict]:
    """JSON-RPC messages in raw JSON or SSE ``data:`` frames."""
    payloads = [payload for payload in _decode_json_objects(text)
                if isinstance(payload.get("jsonrpc"), str)]
    for line in (text or "").splitlines():
        candidate = line.strip()
        if not candidate.startswith("data:"):
            continue
        try:
            payload = json.loads(candidate[5:].strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("jsonrpc"), str):
            payloads.append(payload)
    return payloads


def _check(name: str, ok: bool, blocked: bool, detail: str) -> dict:
    return {"name": name, "status": ("pass" if ok else
                                     "blocked" if blocked else "fail"),
            "detail": detail}


def _request_checks(request: dict, consumer_root: str | None,
                    expected_http: str, expected_mcp: str) -> list[dict]:
    command = str(request.get("command", ""))
    argv = shlex.split(command)
    assignments = [argv[index + 1] for index, value in enumerate(argv[:-1])
                   if value == "--config"]
    checks: list[dict] = []

    forbidden_markers = ("mcp_servers", "CHROME_", "NPM_CONFIG_CACHE")
    carrying = [marker for marker in forbidden_markers if any(
        marker in assignment for assignment in assignments)]
    checks.append(_check(
        "request_free_of_chrome_mcp_npm", not carrying, True,
        "found forbidden config markers: " + json.dumps(carrying)
        if carrying else "no mcp_servers.*/CHROME_*/NPM_CONFIG_CACHE config"))

    env: dict[str, object] = {}
    trust_seen: list[str] = []
    for assignment in assignments:
        try:
            parsed = tomllib.loads(f"{assignment}\n")
        except tomllib.TOMLDecodeError:
            continue
        if "shell_environment_policy" in parsed:
            env.update(parsed["shell_environment_policy"].get("set", {}))
        if "projects" in parsed:
            trust_seen.extend(str(key) for key, value in parsed["projects"].items()
                              if isinstance(value, dict)
                              and value.get("trust_level") == "trusted")

    http_value = env.get("ZOTERO_HTTP_URL")
    mcp_value = env.get("ZOTERO_MCP_URL")
    endpoint_ok = (
        isinstance(http_value, str) and http_value.strip()
        and http_value != DEFAULT_HTTP_URL
        and isinstance(mcp_value, str) and mcp_value.strip()
        and mcp_value != DEFAULT_MCP_URL)
    mismatch = ((expected_http and http_value != expected_http)
                or (expected_mcp and mcp_value != expected_mcp))
    checks.append(_check(
        "request_nondefault_endpoints", endpoint_ok and not mismatch, True,
        f"ZOTERO_HTTP_URL={http_value!r} ZOTERO_MCP_URL={mcp_value!r} "
        f"expected={expected_http!r}/{expected_mcp!r}"))

    if consumer_root:
        resolved = str(Path(consumer_root))
        trust_ok = resolved in trust_seen
    else:
        trust_ok = bool(trust_seen)
    checks.append(_check(
        "request_trusts_exact_clean_consumer", trust_ok, True,
        f"trusted projects: {trust_seen!r}, consumer: {consumer_root!r}"))
    return checks


def _fixture_checks(items: dict, evidence: dict) -> list[dict]:
    run_ok = (isinstance(items.get("fixture_run_id"), str)
              and items.get("fixture_run_id") == evidence.get("fixture_run_id"))
    revision_ok = (items.get("fixture_revision") == FIXTURE_REVISION
                   and evidence.get("fixture_repo_sha") == FIXTURE_REVISION
                   and items.get("fixture_repository") == FIXTURE_REPOSITORY)
    clean_ok = (evidence.get("fixture_repo_dirty") == "no"
                and evidence.get("manual_patch") == "no")
    keys_ok = (isinstance(items.get("item_keys"), list)
               and all(isinstance(key, str) and key.strip()
                       for key in items["item_keys"]))
    detail = (f"run={items.get('fixture_run_id')!r}/{evidence.get('fixture_run_id')!r} "
              f"revision_ok={revision_ok} clean_ok={clean_ok} keys_ok={keys_ok}")
    return [_check("fixture_provenance_consistent",
                   run_ok and revision_ok and clean_ok and keys_ok, True, detail)]


def _child_reads(events: list[dict], child_ids: set[str], seeded: set[str]):
    """Scan formal-child command events for real MCP reads of seeded keys."""
    observed: list[str] = []
    violation_commands: list[str] = []
    zotero_traffic = False
    for event in events:
        params = event.get("message", {}).get("params", {})
        if params.get("threadId") not in child_ids:
            continue
        item = params.get("item", {})
        if item.get("type") != "commandExecution":
            continue
        command = str(item.get("command", ""))
        output = str(item.get("aggregatedOutput", ""))
        if DEFAULT_ENDPOINT_PATTERN.search(command):
            violation_commands.append(command[:400])
        if MCP_MCP_PATTERN.search(command):
            violation_commands.append(command[:400])
        payloads = _rpc_payloads(output) + [
            payload for payload in _decode_json_objects(command)
            if isinstance(payload.get("jsonrpc"), str)]
        requests: dict[object, str] = {}
        successful: set[object] = set()
        for payload in payloads:
            method = payload.get("method")
            if method == "tools/call":
                params_rpc = payload.get("params", {})
                name = params_rpc.get("name")
                key = (params_rpc.get("arguments", {}) or {}).get("itemKey")
                if name in READ_TOOLS and isinstance(key, str) and key in seeded:
                    requests[payload.get("id")] = key
            elif payload.get("id") is not None and (
                    "result" in payload or "error" in payload):
                if "result" in payload and payload["result"] is not None:
                    successful.add(payload.get("id"))
        reads = {key for rpc_id, key in requests.items() if rpc_id in successful}
        if requests or successful:
            zotero_traffic = True
        for key in reads:
            if key not in observed:
                observed.append(key)
    return observed, violation_commands, zotero_traffic


def run_verification(*, eval_response, adapter, request, zotero_items_config,
                     fixture_evidence, consumer_root: str | None = None,
                     expected_http_url: str = "", expected_mcp_url: str = "",
                     output: Path | None = None) -> dict:
    response = _load(eval_response)
    adapter_payload = _load(adapter)
    request_payload = _load(request)
    items = _load(zotero_items_config)
    evidence = _load(fixture_evidence)

    checks: list[dict] = []
    checks.extend(_request_checks(request_payload, consumer_root,
                                  expected_http_url, expected_mcp_url))
    checks.extend(_fixture_checks(items, evidence))

    delegation = adapter_payload.get("delegation", {}) if isinstance(adapter_payload, dict) else {}
    confirmed = delegation.get("state") == "confirmed"
    child_ids = delegation.get("child_thread_ids")
    child_count = delegation.get("formal_child_count")
    delegation_ok = (confirmed and isinstance(child_ids, list) and len(child_ids) >= 1
                     and isinstance(child_count, int) and child_count >= 1)
    checks.append(_check(
        "formal_analyzer_delegation_confirmed", delegation_ok, True,
        f"state={delegation.get('state')!r} formal_child_count={child_count!r} "
        f"child_thread_ids={child_ids!r}"))

    events = (response.get("output", {}).get("app_server_events", [])
              if isinstance(response, dict) else [])
    observed: list[str] = []
    violations: list[str] = []
    traffic = False
    if delegation_ok:
        seeded = {key for key in items.get("item_keys", []) if isinstance(key, str)}
        observed, violations, traffic = _child_reads(
            events, {str(child) for child in child_ids}, seeded)

    if violations:
        checks.append(_check(
            "child_never_touches_production_endpoints", False, False,
            "formal child executed commands against default endpoints or a "
            f"/mcp/mcp path: {json.dumps(violations[:3], ensure_ascii=False)}"))
    else:
        checks.append(_check(
            "child_never_touches_production_endpoints", True, False,
            "no default-endpoint or /mcp/mcp usage in formal child commands"))

    reads_ok = bool(observed)
    checks.append(_check(
        "formal_child_reads_seeded_item_via_mcp", reads_ok, False,
        f"observed={observed!r} zotero_traffic={traffic}"))

    if not delegation_ok or any(check["status"] == "blocked" for check in checks):
        status = BLOCKED
    elif violations:
        status = FAIL_PRODUCER
    elif reads_ok:
        status = "PASS"
    else:
        status = OBSERVABILITY

    verdict = {
        "schema_version": SCHEMA_VERSION,
        "verifier": HELPER_ID,
        "status": status,
        "checks": checks,
        "observed_item_keys": observed,
        "seeded_item_keys": items.get("item_keys", []),
        "formal_child_thread_ids": child_ids if delegation_ok else [],
    }
    if output is not None:
        output = Path(output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(verdict, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
            encoding="utf-8")
    return verdict


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Machine verdict for the PC39-R1 endpoint runtime evidence")
    parser.add_argument("--eval-response", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--zotero-items-config", type=Path, required=True)
    parser.add_argument("--fixture-evidence", type=Path, required=True)
    parser.add_argument("--consumer-root")
    parser.add_argument("--expected-http-url", default="")
    parser.add_argument("--expected-mcp-url", default="")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        verdict = run_verification(
            eval_response=args.eval_response, adapter=args.adapter,
            request=args.request, zotero_items_config=args.zotero_items_config,
            fixture_evidence=args.fixture_evidence,
            consumer_root=args.consumer_root,
            expected_http_url=args.expected_http_url,
            expected_mcp_url=args.expected_mcp_url,
            output=args.output)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": verdict["status"], "output": str(args.output.resolve())},
                     ensure_ascii=False))
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
