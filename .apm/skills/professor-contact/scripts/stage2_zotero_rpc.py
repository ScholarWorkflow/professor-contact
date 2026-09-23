#!/usr/bin/env python3
"""Stage 2 deterministic Zotero transport helper.

Routes an already-decided Stage 2 Zotero business call to the run's resolved
endpoint. Endpoint resolution is env-only and cannot be overridden from the
command line:

- ``mcp``  resolves the FULL MCP endpoint from ``ZOTERO_MCP_URL``
  (unset/empty -> production fallback ``http://127.0.0.1:23120/mcp``);
- ``http`` resolves the REST base from ``ZOTERO_HTTP_URL``
  (unset/empty -> production fallback ``http://127.0.0.1:23119``);
- ``probe`` resolves both endpoints the same way and answers the Stage 2
  connectivity question in one deterministic call: it GETs
  ``<ZOTERO_HTTP_URL>/connector/ping`` and the resolved MCP endpoint and
  prints one compact JSON verdict (``{"online": true|false, ...}``) that also
  states the exact endpoints used, so a caller never hand-writes a URL or
  port to test connectivity.

Both resolved values are normalized to drop one trailing ``/``. The CLI
exposes no URL/port/endpoint argument, so a caller can never point real
traffic at a different endpoint than the resolved one. Session creation stays
owned by ``zotero-read`` (``scripts/new-session.sh``): this helper never
initializes a session and performs no business judgement — it forwards one
call, prints the response body on stdout, and reports transport failures as a
machine-readable JSON error line on stderr with a non-zero exit code.

``http --response-meta <file>`` additionally writes ``{"total_results": …}`` to
that file, where the value is Zotero's ``Total-Results`` header as an integer or
``null`` when the header carries no usable count. stdout stays exactly the
response body, so a caller that needs to paginate reads the sidecar instead of
guessing whether one page was the whole result set.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HTTP_FALLBACK = "http://127.0.0.1:23119"
MCP_FALLBACK = "http://127.0.0.1:23120/mcp"
REQUEST_TIMEOUT = 60
PROBE_TIMEOUT = 5

EXIT_USAGE = 2
EXIT_BAD_ARGUMENTS_JSON = 3
EXIT_TRANSPORT_FAILURE = 4
EXIT_HTTP_STATUS = 5
EXIT_RESPONSE_META = 6


def _fail(code: int, kind: str, **fields: object) -> None:
    payload = {"error": kind, **fields}
    sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    raise SystemExit(code)


def resolve_endpoint(env_name: str, fallback: str) -> tuple[str, str]:
    """Resolve an endpoint from the environment only; drop one trailing slash.

    Returns ``(endpoint, source)`` with ``source`` in ``{"env", "fallback"}``
    so failures can state which endpoint was actually used.
    """
    raw = os.environ.get(env_name)
    if raw is None or raw.strip() == "":
        endpoint, source = fallback, "fallback"
    else:
        endpoint, source = raw.strip(), "env"
    endpoint = endpoint.rstrip("/")
    if not endpoint.startswith(("http://", "https://")):
        _fail(
            EXIT_USAGE,
            "invalid_endpoint",
            env=env_name,
            endpoint=endpoint,
            source=source,
            detail="resolved endpoint must be an http(s) URL",
        )
    return endpoint, source


def _reject_control_text(value: str, what: str) -> None:
    if value == "" or any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        _fail(EXIT_USAGE, "invalid_argument", what=what)


def _read_response(resp, unwrap_sse: bool) -> str:
    charset = resp.headers.get_content_charset() or "utf-8"
    body = resp.read().decode(charset, errors="replace")
    if unwrap_sse and "text/event-stream" in (resp.headers.get("Content-Type") or ""):
        payloads = [
            line[len("data:"):].lstrip()
            for line in body.splitlines()
            if line.startswith("data:")
        ]
        return "\n".join(payloads)
    return body


def _total_results(headers) -> int | None:
    raw = headers.get("Total-Results")
    if raw is None:
        return None
    text = raw.strip()
    return int(text) if text.isdigit() else None


def _write_response_meta(path: str, headers) -> None:
    """Publish the page total as a sidecar so a caller can keep paginating.

    Written before stdout and through ``os.replace`` so a caller that sees a
    completed body never reads a half-written (or stale) total.
    """
    payload = {"total_results": _total_results(headers)}
    directory = os.path.dirname(os.path.abspath(path)) or "."
    tmp = os.path.join(directory, f".{os.path.basename(path)}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        _fail(
            EXIT_RESPONSE_META,
            "response_meta_write_failed",
            path=path,
            detail=str(exc),
        )


def _request(url: str, *, method: str, headers: dict[str, str],
             data: bytes | None, unwrap_sse: bool, source: str,
             response_meta: str | None = None) -> None:
    # Proxy handlers are disabled on purpose: the resolved loopback endpoint
    # must be contacted directly, never through an ambient proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=REQUEST_TIMEOUT) as resp:
            status = resp.status
            if not 200 <= status < 300:
                _fail(
                    EXIT_HTTP_STATUS,
                    "http_status",
                    status=status,
                    endpoint=url,
                    source=source,
                    body_preview=_read_response(resp, unwrap_sse)[:500],
                )
            payload = _read_response(resp, unwrap_sse)
            if response_meta is not None:
                _write_response_meta(response_meta, resp.headers)
            sys.stdout.write(payload)
    except urllib.error.HTTPError as exc:  # non-2xx surfaces here as well
        preview = ""
        try:
            preview = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:  # noqa: BLE001 - best-effort preview only
            preview = ""
        _fail(
            EXIT_HTTP_STATUS,
            "http_status",
            status=exc.code,
            endpoint=url,
            source=source,
            body_preview=preview,
        )
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        _fail(
            EXIT_TRANSPORT_FAILURE,
            "transport_failure",
            endpoint=url,
            source=source,
            detail=str(exc),
        )


def cmd_mcp(args: argparse.Namespace) -> None:
    _reject_control_text(args.session_id, "--session-id")
    _reject_control_text(args.tool, "--tool")
    try:
        arguments = json.loads(args.arguments_json)
    except json.JSONDecodeError as exc:
        _fail(EXIT_BAD_ARGUMENTS_JSON, "invalid_arguments_json", detail=str(exc))
    if not isinstance(arguments, dict):
        _fail(
            EXIT_BAD_ARGUMENTS_JSON,
            "invalid_arguments_json",
            detail="arguments must be a JSON object",
        )
    endpoint, source = resolve_endpoint("ZOTERO_MCP_URL", MCP_FALLBACK)
    envelope = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": args.tool, "arguments": arguments},
    }
    _request(
        endpoint,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Session-Id": args.session_id,
        },
        data=(json.dumps(envelope, ensure_ascii=False) + "\n").encode("utf-8"),
        unwrap_sse=True,
        source=source,
    )


def cmd_http(args: argparse.Namespace) -> None:
    path = args.path
    _reject_control_text(path.strip(), "--path")
    if not path.startswith("/") or "://" in path:
        _fail(
            EXIT_USAGE,
            "invalid_path",
            path=path,
            detail="--path must be a relative path starting with / (no scheme, no authority)",
        )
    base, source = resolve_endpoint("ZOTERO_HTTP_URL", HTTP_FALLBACK)
    response_meta = args.response_meta
    if response_meta is not None and not response_meta.strip():
        _fail(EXIT_USAGE, "invalid_argument", what="--response-meta")
    _request(
        base + path,
        method="GET",
        headers={"Accept": "application/json"},
        data=None,
        unwrap_sse=False,
        source=source,
        response_meta=response_meta,
    )


def _probe_once(url: str) -> dict:
    """One connectivity GET; any HTTP answer proves a listener, errors don't."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url, method="GET",
                                 headers={"Accept": "application/json"})
    try:
        with opener.open(req, timeout=PROBE_TIMEOUT) as resp:
            return {"reachable": True, "status": resp.status}
    except urllib.error.HTTPError as exc:
        # A non-2xx answer (e.g. 405 for a plain GET on an MCP endpoint) still
        # proves the endpoint is served by a live listener.
        try:
            exc.read()
        except Exception:  # noqa: BLE001 - best-effort drain only
            pass
        return {"reachable": True, "status": exc.code}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        detail = getattr(exc, "reason", None) or exc
        return {"reachable": False, "status": None, "error": str(detail)}


def cmd_probe(args: argparse.Namespace) -> None:
    http_base, http_source = resolve_endpoint("ZOTERO_HTTP_URL", HTTP_FALLBACK)
    mcp_endpoint, mcp_source = resolve_endpoint("ZOTERO_MCP_URL", MCP_FALLBACK)
    http_view = {
        "endpoint": http_base + "/connector/ping",
        "source": http_source,
        **_probe_once(http_base + "/connector/ping"),
    }
    mcp_view = {
        "endpoint": mcp_endpoint,
        "source": mcp_source,
        **_probe_once(mcp_endpoint),
    }
    verdict = {
        "schema": 1,
        "kind": "probe",
        "online": bool(http_view["reachable"] and mcp_view["reachable"]),
        "http": http_view,
        "mcp": mcp_view,
    }
    sys.stdout.write(json.dumps(verdict, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stage2_zotero_rpc.py",
        description="Stage 2 Zotero transport helper (env-resolved endpoints only)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_probe = sub.add_parser(
        "probe",
        help="deterministic connectivity check on both resolved endpoints",
    )
    p_probe.set_defaults(func=cmd_probe)

    p_mcp = sub.add_parser(
        "mcp",
        help="forward one MCP tools/call to the resolved ZOTERO_MCP_URL",
    )
    p_mcp.add_argument("--session-id", required=True,
                       help="Mcp-Session-Id from zotero-read new-session.sh")
    p_mcp.add_argument("--tool", required=True, help="MCP tool name")
    p_mcp.add_argument("--arguments-json", required=True,
                       help="tool arguments as a JSON object literal")
    p_mcp.set_defaults(func=cmd_mcp)

    p_http = sub.add_parser(
        "http",
        help="GET a relative path on the resolved ZOTERO_HTTP_URL base",
    )
    p_http.add_argument("--path", required=True,
                        help="relative path starting with /, may include a query string")
    p_http.add_argument("--response-meta",
                        help="optional JSON sidecar path receiving "
                             '{"total_results": <int|null>} from Total-Results')
    p_http.set_defaults(func=cmd_http)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
