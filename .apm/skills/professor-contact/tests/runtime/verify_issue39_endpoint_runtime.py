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
READ_TOOL_KEY_PATTERN = re.compile(
    r"\b(get_item_details|get_item_abstract)[\"' =:]+([A-Za-z0-9]{4,12})\b")
DEFAULT_ENDPOINT_PATTERN = re.compile(
    r"https?://\S*?127\.0\.0\.1:231(19|20)\b")
MCP_MCP_PATTERN = re.compile(r"/mcp/mcp(?!/)", re.IGNORECASE)
# The analyzer contract expresses production ports only as the fallback of a
# parameter expansion (`${ZOTERO_MCP_URL:-http://127.0.0.1:23120/mcp}`); the
# executed path is the resolved variable.  Such expansion literals are the
# documented contract, not endpoint violations.
FALLBACK_EXPANSION_PATTERN = re.compile(
    r"\$\{ZOTERO_(?:HTTP|MCP)_URL:-[^}]*\}")
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
    """JSON-RPC messages in raw JSON, shell-escaped JSON, or SSE frames."""
    payloads = [payload for payload in _decode_json_objects(text)
                if isinstance(payload.get("jsonrpc"), str)]
    # A JSON-RPC body embedded in a shell-quoted command line arrives
    # backslash-escaped (`-d "{\"jsonrpc\":...}"`); one level of un-escaping
    # recovers the request objects.
    unescaped = text.replace('\\"', '"')
    if unescaped != text:
        payloads.extend(payload for payload in _decode_json_objects(unescaped)
                        if isinstance(payload.get("jsonrpc"), str))
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


def _transformed_reads(text: str, seeded: set[str]) -> list[str]:
    """Read keys from jq-transformed tool outputs in command output.

    ``jq -r '... | fromjson | {item_key, op, data}'`` only emits when a real
    JSON-RPC result carried parseable item payload, so such objects are
    machine evidence of a successful read.
    """
    keys: list[str] = []
    for payload in _decode_json_objects(text):
        operation = payload.get("op")
        if operation not in READ_TOOLS:
            continue
        data = payload.get("data")
        candidates = [payload.get("item_key"), payload.get("itemKey")]
        if isinstance(data, dict):
            candidates.append(data.get("itemKey"))
        for candidate in candidates:
            if isinstance(candidate, str) and candidate in seeded and candidate not in keys:
                keys.append(candidate)
    return keys


def _command_violations(command: str) -> list[str]:
    stripped = FALLBACK_EXPANSION_PATTERN.sub("", command)
    hits: list[str] = []
    if DEFAULT_ENDPOINT_PATTERN.search(stripped):
        hits.append("default_endpoint")
    if MCP_MCP_PATTERN.search(stripped):
        hits.append("mcp_mcp_path")
    return hits


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
        resolved = str(Path(consumer_root).resolve())
        trust_ok = any(entry in (resolved, str(Path(consumer_root)))
                       for entry in trust_seen)
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


def _result_item_keys(payloads: list[dict], seeded: set[str]) -> list[str]:
    """Seeded keys carried by successful JSON-RPC result payloads."""
    keys: list[str] = []
    for payload in payloads:
        result = payload.get("result")
        if not isinstance(result, dict):
            continue
        content = result.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or "text" not in block:
                continue
            try:
                inner = json.loads(block["text"])
            except (json.JSONDecodeError, TypeError):
                inner = None
            candidates = [inner]
            if isinstance(inner, dict):
                candidates.extend(inner.values())
            for candidate in candidates:
                key = candidate.get("itemKey") if isinstance(candidate, dict) else None
                if isinstance(key, str) and key in seeded and key not in keys:
                    keys.append(key)
    return keys


def _item_payload_keys(text: str, seeded: set[str]) -> list[str]:
    """Seeded keys inside Zotero item payloads printed in command output.

    A payload is an object with ``itemKey``/``key`` plus an item signature
    (``itemType``, or ``title`` with an abstract field) — the shape Zotero MCP
    read results print after any jq transformation.
    """
    keys: list[str] = []
    for payload in _decode_json_objects(text):
        if not isinstance(payload, dict):
            continue
        key = payload.get("itemKey", payload.get("key"))
        if not isinstance(key, str) or key not in seeded or key in keys:
            continue
        has_signature = (
            isinstance(payload.get("itemType"), str)
            or (isinstance(payload.get("title"), str)
                and isinstance(payload.get("abstractNote", payload.get("abstract")), str)))
        if has_signature:
            keys.append(key)
    return keys


def _child_reads(events: list[dict], child_ids: set[str], seeded: set[str]):
    """Scan formal-child command events for real MCP reads of seeded keys."""
    observed: list[str] = []
    attempts: list[dict] = []
    traffic = False
    # Thread-level read attribution: when the child's own commands pair a read
    # tool with a seeded key (e.g. a scripted loop "get_item_details BNMWJJDG")
    # and any of its command outputs carries a successful JSON-RPC result
    # embedding that key, the key counts as read through this child.
    tool_key_pairs: set[str] = set()
    thread_result_keys: list[str] = []
    for event in events:
        message = event.get("message", {})
        # Only terminal item/completed events count; item/started snapshots of
        # the same exec id must not double-count.
        if message.get("method") != "item/completed":
            continue
        params = message.get("params", {})
        if params.get("threadId") not in child_ids:
            continue
        item = params.get("item", {})
        if item.get("type") != "commandExecution":
            continue
        command = str(item.get("command", ""))
        output = str(item.get("aggregatedOutput", ""))
        violations = _command_violations(command)
        if violations:
            attempts.append({"command": command[:400], "hits": violations})
        for match in READ_TOOL_KEY_PATTERN.finditer(command):
            if match.group(2) in seeded:
                tool_key_pairs.add(match.group(2))
        payloads = _rpc_payloads(output) + _rpc_payloads(command)
        thread_result_keys.extend(_result_item_keys([p for p in payloads
                                                     if "result" in p], seeded))
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
        reads = [key for rpc_id, key in requests.items() if rpc_id in successful]
        reads.extend(_transformed_reads(output, seeded))
        if requests or successful or reads:
            traffic = True
        if violations:
            # A command that targeted a production endpoint cannot prove a
            # read through the resolved fixture endpoint.
            continue
        # Templated loops bind itemKey to a shell variable, so the JSON-RPC
        # request never contains the literal key.  When the same command
        # references a read tool, enumerates the seeded key, and prints an
        # item payload for it, that payload is machine proof of the read.
        if any(tool in command for tool in READ_TOOLS):
            for key in _item_payload_keys(output, seeded):
                if re.search(rf"\b{re.escape(key)}\b", command) and key not in reads:
                    reads.append(key)
        for key in reads:
            if key not in observed:
                observed.append(key)
    if tool_key_pairs:
        traffic = True
        for key in thread_result_keys:
            if key in tool_key_pairs and key not in observed:
                observed.append(key)
    return observed, attempts, traffic


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
    attempts: list[dict] = []
    traffic = False
    if delegation_ok:
        seeded = {key for key in items.get("item_keys", []) if isinstance(key, str)}
        observed, attempts, traffic = _child_reads(
            events, {str(child) for child in child_ids}, seeded)

    # Production-endpoint attempts are recorded for the report.  They only
    # force FAIL_PRODUCER when no read succeeded through the resolved
    # endpoints, i.e. when Stage 2's actual item access stayed on the wrong
    # path or offline.
    reads_ok = bool(observed)
    if attempts and not reads_ok:
        checks.append(_check(
            "child_never_touches_production_endpoints", False, False,
            "formal child executed commands against default endpoints or a "
            "/mcp/mcp path and no resolved-endpoint read succeeded: "
            + json.dumps(attempts[:3], ensure_ascii=False)))
    elif attempts:
        checks.append(_check(
            "child_never_touches_production_endpoints", True, False,
            f"{len(attempts)} failed attempt(s) at production endpoints were "
            "recorded, but the seeded-item reads succeeded via the resolved "
            "endpoints"))
    else:
        checks.append(_check(
            "child_never_touches_production_endpoints", True, False,
            "no default-endpoint or /mcp/mcp usage in formal child commands"))

    checks.append(_check(
        "formal_child_reads_seeded_item_via_mcp", reads_ok, False,
        f"observed={observed!r} zotero_traffic={traffic}"))

    if not delegation_ok or any(check["status"] == "blocked" for check in checks):
        status = BLOCKED
    elif reads_ok:
        status = "PASS"
    elif attempts:
        status = FAIL_PRODUCER
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
        "production_endpoint_attempts": attempts,
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
