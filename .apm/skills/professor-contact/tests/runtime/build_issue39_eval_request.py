#!/usr/bin/env python3
"""Build the minimal Codex eval request for issue #39 PC39-R1.

PC39-R1 proves one thing: the installed Stage 2 analyzer consumes runtime
injected non-default ``ZOTERO_HTTP_URL`` / ``ZOTERO_MCP_URL`` endpoints.  The
request therefore carries only model/reasoning, the exact clean-consumer trust
entry, workspace-write network access, and the two Zotero endpoints.  Chrome
MCP wiring, Chrome environment overrides, and npm cache settings belong to
other cases and must never appear here.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


PRODUCTION_ZOTERO_PORTS = {23119, 23120}


class RequestBuildError(RuntimeError):
    pass


def _toml_string(value: str) -> str:
    """Encode a TOML basic string without allowing numeric env coercion."""
    return json.dumps(str(value), ensure_ascii=False)


def validate_endpoints(zotero_http_url: str, zotero_mcp_url: str) -> None:
    """Require non-empty non-production endpoints; MCP must be complete."""
    for name, raw in (("zotero_http_url", zotero_http_url),
                      ("zotero_mcp_url", zotero_mcp_url)):
        if not isinstance(raw, str) or not raw.strip():
            raise RequestBuildError(f"{name} is required")
        parsed = urlsplit(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise RequestBuildError(f"{name} must be an absolute http(s) URL: {raw!r}")
        try:
            port = parsed.port
        except ValueError as exc:
            raise RequestBuildError(f"{name} has an invalid port: {raw!r}") from exc
        if port in PRODUCTION_ZOTERO_PORTS:
            raise RequestBuildError(
                f"{name} uses production Zotero port {port}; refusing PC39 request")
    if not urlsplit(zotero_mcp_url.rstrip("/")).path.endswith("/mcp"):
        raise RequestBuildError(
            "zotero_mcp_url must be the complete endpoint ending in /mcp")


def build_request(*, consumer_root: Path, prompt_file: Path, output: Path,
                  zotero_http_url: str, zotero_mcp_url: str,
                  model: str = "gpt-5.6-luna", reasoning: str = "low",
                  timeout: int = 1800) -> dict[str, object]:
    consumer_root = Path(consumer_root).resolve()
    if not consumer_root.is_dir():
        raise RequestBuildError(f"consumer root does not exist: {consumer_root}")
    prompt = Path(prompt_file).read_text(encoding="utf-8")
    if not prompt.strip():
        raise RequestBuildError("prompt file is empty")
    # The Chrome-scanning #32 prompt carries profile_path; PC39 must never
    # reopen that path, so a leaked profile_path fails the build closed.
    if "profile_path" in prompt:
        raise RequestBuildError("PC39 prompt must not contain profile_path")
    validate_endpoints(zotero_http_url, zotero_mcp_url)
    # Without an explicit trust entry Codex skips the clean consumer's
    # project-scoped `.codex/` layer, so the installed analyzer never loads.
    project_trust = (
        "projects=" + "{" + _toml_string(str(consumer_root)) +
        '={trust_level="trusted"}}'
    )
    config_values = [
        f"model_reasoning_effort={_toml_string(reasoning)}",
        project_trust,
        # `--sandbox workspace-write` alone does not grant network access; the
        # Zotero fixture endpoints stay unreachable without this override.
        "sandbox_workspace_write.network_access=true",
        f"shell_environment_policy.set.ZOTERO_HTTP_URL={_toml_string(zotero_http_url)}",
        f"shell_environment_policy.set.ZOTERO_MCP_URL={_toml_string(zotero_mcp_url)}",
    ]
    # eval-server prepends ``codex exec``.  Its request contract therefore
    # accepts only the arguments that follow that executable pair.
    argv = ["--json", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "workspace-write", "--cd", str(consumer_root),
            "--model", model]
    for value in config_values:
        argv.extend(["--config", value])
    argv.extend(["--", prompt])
    request = {"command": shlex.join(argv), "timeout": int(timeout)}
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                     prefix=f".{output.name}.", delete=False) as handle:
        json.dump(request, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, output)
    return request


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--zotero-http-url", required=True)
    parser.add_argument("--zotero-mcp-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning", default="low")
    parser.add_argument("--timeout", type=int, default=1800)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request = build_request(
            consumer_root=args.consumer_root, prompt_file=args.prompt_file,
            output=args.output, zotero_http_url=args.zotero_http_url,
            zotero_mcp_url=args.zotero_mcp_url, model=args.model,
            reasoning=args.reasoning, timeout=args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output.resolve()),
                      "timeout": request["timeout"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
