#!/usr/bin/env python3
"""Build the fixed Codex eval request for issue #57 PC57-R1 (Stage-2 routing).

The command surface is frozen by the PC57-R1 recipe.  The thread limit value
16 is retained only because PC57-R1 reproduces the exact #47 regression
environment; it is not the Stage-2 business concurrency rule (which stays
"at most 3 concurrent paper-analysis jobs") and must not be increased after a
run.  No Chrome/CDP/NPM or uv-tool (``UV_TOOL_DIR``/``XDG_DATA_HOME``/HOME)
override is ever emitted.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


MODEL = "gpt-5.6-luna"
REASONING = "low"
TIMEOUT = 900
THREAD_LIMIT = 16
PROMPT_TOKEN = "<PROGRAM_ROOT>"
PROMPT_TEMPLATE = (
    "在 <PROGRAM_ROOT> 按已安装 professor-contact 的正式 Codex 工作流执行 Stage 2，"
    "且只执行 Stage 2。\n"
    "直接消费已准备好的 Stage 1 canonical state。本轮 chatgpt_handoff=continue，"
    "paper_analysis=all，gap_scope=selected_direction，freshness_scope=shortlist，"
    "kb_import=false。\n"
    "不要进入 Stage 3；按已安装的正式工作流正常处理并结束本轮。\n"
)
PRODUCTION_ZOTERO_PORTS = {23119, 23120}


class RequestBuildError(RuntimeError):
    pass


def validate_fixture_endpoints(zotero_http_url: str, zotero_mcp_url: str) -> None:
    """Require disposable HTTP/MCP fixture endpoints; reject production ports."""
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
                f"{name} uses production Zotero port {port}; refusing PC57-R1 request")
    if not urlsplit(zotero_mcp_url.rstrip("/")).path.endswith("/mcp"):
        raise RequestBuildError("zotero_mcp_url must be the complete endpoint ending in /mcp")


def _atomic_write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, path)


def build_request(*, consumer_root: Path, program_root: Path, prompt_template: Path,
                  rendered_prompt: Path, zotero_http_url: str, zotero_mcp_url: str,
                  output: Path, model: str = MODEL, reasoning: str = REASONING,
                  timeout: int = TIMEOUT) -> dict[str, object]:
    consumer_root = Path(consumer_root).resolve()
    program_root = Path(program_root).resolve()
    prompt_template = Path(prompt_template).resolve()
    rendered_prompt = Path(rendered_prompt).resolve()
    output = Path(output).resolve()
    if not consumer_root.is_dir():
        raise RequestBuildError(f"consumer root does not exist: {consumer_root}")
    if not program_root.is_dir():
        raise RequestBuildError(f"program root does not exist: {program_root}")
    if model != MODEL:
        raise RequestBuildError(f"PC57 requires model {MODEL}")
    if reasoning != REASONING:
        raise RequestBuildError(f"PC57 requires reasoning {REASONING}")
    if timeout != TIMEOUT:
        raise RequestBuildError(f"PC57 requires timeout {TIMEOUT}")
    validate_fixture_endpoints(zotero_http_url, zotero_mcp_url)
    template = prompt_template.read_text(encoding="utf-8")
    if template != PROMPT_TEMPLATE:
        raise RequestBuildError("prompt template differs from the frozen PC57 prompt")
    if template.count(PROMPT_TOKEN) != 1:
        raise RequestBuildError("frozen PC57 prompt must contain exactly one PROGRAM_ROOT token")
    rendered = template.replace(PROMPT_TOKEN, str(program_root))
    if PROMPT_TOKEN in rendered:
        raise RequestBuildError("rendered prompt still contains the PROGRAM_ROOT token")
    rendered_prompt.parent.mkdir(parents=True, exist_ok=True)
    rendered_prompt.write_text(rendered, encoding="utf-8")

    trust_override = f'projects."{consumer_root}".trust_level="trusted"'
    argv = [
        "--json", "--ephemeral", "--skip-git-repo-check",
        "--sandbox", "workspace-write", "--cd", str(consumer_root),
        "--model", model,
        "--config", f'model_reasoning_effort="{reasoning}"',
        "--config", trust_override,
        "--config", f"agents.max_concurrent_threads_per_session={THREAD_LIMIT}",
        "--config", "sandbox_workspace_write.network_access=true",
        "--config", f'shell_environment_policy.set.ZOTERO_HTTP_URL="{zotero_http_url}"',
        "--config", f'shell_environment_policy.set.ZOTERO_MCP_URL="{zotero_mcp_url}"',
        "--", rendered,
    ]
    request = {"command": shlex.join(argv), "timeout": TIMEOUT}
    _atomic_write(output, request)
    return request


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--prompt-template", type=Path, required=True)
    parser.add_argument("--rendered-prompt", type=Path, required=True)
    parser.add_argument("--zotero-http-url", required=True)
    parser.add_argument("--zotero-mcp-url", required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--reasoning", default=REASONING)
    parser.add_argument("--timeout", type=int, default=TIMEOUT)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request = build_request(
            consumer_root=args.consumer_root,
            program_root=args.program_root,
            prompt_template=args.prompt_template,
            rendered_prompt=args.rendered_prompt,
            zotero_http_url=args.zotero_http_url,
            zotero_mcp_url=args.zotero_mcp_url,
            output=args.output,
            model=args.model,
            reasoning=args.reasoning,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": "ok", "output": str(args.output.resolve()),
        "timeout": request["timeout"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
