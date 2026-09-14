#!/usr/bin/env python3
"""Build a machine-readable Codex eval request for issue #32.

This module only constructs the request.  It never invokes Codex, the eval
server, or a browser.  Chrome's MCP server id is discovered from the clean
consumer's generated TOML configuration so the request cannot silently bind
to a guessed server name.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
import tomllib
from pathlib import Path


class RequestBuildError(RuntimeError):
    pass


def _toml_string(value: str) -> str:
    """Encode a TOML basic string without allowing numeric env coercion."""
    return json.dumps(str(value), ensure_ascii=False)


def _toml_key_segment(value: str) -> str:
    """Quote a dynamic dotted-key segment, such as an MCP server id."""
    return json.dumps(str(value), ensure_ascii=False)


def _toml_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*.toml") if path.is_file() and ".git" not in path.parts]


def discover_chrome_server_id(consumer_root: Path) -> str:
    """Return the generated MCP server id used for page-scoped Chrome work."""
    matches: list[tuple[str, dict[str, object]]] = []
    for path in _toml_files(consumer_root):
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        servers = payload.get("mcp_servers")
        if not isinstance(servers, dict):
            continue
        for server_id, config in servers.items():
            if not isinstance(config, dict):
                continue
            env = config.get("env", {})
            if not isinstance(env, dict):
                env = {}
            env_names = {str(key).lower() for key in env}
            name = str(server_id).lower()
            chrome_signal = (
                "chrome" in name or
                any("chrome" in key or "cdp" in key or "profile" in key for key in env_names)
            )
            if chrome_signal and all(str(server_id) != item[0] for item in matches):
                matches.append((str(server_id), config))
    if len(matches) == 1:
        return matches[0][0]
    page_id_matches = [
        server_id for server_id, config in matches
        if isinstance(config.get("args"), list) and "--page-id" in config["args"]
    ]
    if len(page_id_matches) == 1:
        return page_id_matches[0]
    ids = [server_id for server_id, _ in matches]
    if len(ids) != 1:
        raise RequestBuildError(
            "could not uniquely identify the page-scoped Chrome MCP server; "
            f"found {ids!r}, page-id matches={page_id_matches!r}")
    return ids[0]


def build_request(*, consumer_root: Path, prompt_file: Path, output: Path,
                  model: str = "gpt-5.6-luna", reasoning: str = "low",
                  zotero_http_url: str = "", zotero_mcp_url: str = "",
                  chrome_profile_dir: str = "", chrome_cdp_port: str = "",
                  npm_cache: str = "", timeout: int = 1800) -> dict[str, object]:
    consumer_root = Path(consumer_root).resolve()
    prompt = Path(prompt_file).read_text(encoding="utf-8")
    if not consumer_root.is_dir():
        raise RequestBuildError(f"consumer root does not exist: {consumer_root}")
    server_id = discover_chrome_server_id(consumer_root)
    server_key = _toml_key_segment(server_id)
    config_values = [
        f"model_reasoning_effort={_toml_string(reasoning)}",
        f"shell_environment_policy.set.ZOTERO_HTTP_URL={_toml_string(zotero_http_url)}",
        f"shell_environment_policy.set.ZOTERO_MCP_URL={_toml_string(zotero_mcp_url)}",
        # `--sandbox workspace-write` alone does not grant network access; the
        # Zotero fixture endpoints stay unreachable without this override.
        "sandbox_workspace_write.network_access=true",
        f"shell_environment_policy.set.NPM_CONFIG_CACHE={_toml_string(npm_cache)}",
        f"mcp_servers.{server_key}.env.CHROME_PROFILE_DIR={_toml_string(chrome_profile_dir)}",
        f"mcp_servers.{server_key}.env.CHROME_CDP_PORT={_toml_string(chrome_cdp_port)}",
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
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning", default="low")
    parser.add_argument("--zotero-http-url", default="")
    parser.add_argument("--zotero-mcp-url", default="")
    parser.add_argument("--chrome-profile-dir", default="")
    parser.add_argument("--chrome-cdp-port", default="")
    parser.add_argument("--npm-cache", default="")
    parser.add_argument("--timeout", type=int, default=1800)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request = build_request(
            consumer_root=args.consumer_root, prompt_file=args.prompt_file, output=args.output,
            model=args.model, reasoning=args.reasoning, zotero_http_url=args.zotero_http_url,
            zotero_mcp_url=args.zotero_mcp_url, chrome_profile_dir=args.chrome_profile_dir,
            chrome_cdp_port=args.chrome_cdp_port, npm_cache=args.npm_cache, timeout=args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output.resolve()),
                      "timeout": request["timeout"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
