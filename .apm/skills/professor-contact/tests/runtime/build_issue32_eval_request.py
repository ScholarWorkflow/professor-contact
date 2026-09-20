#!/usr/bin/env python3
"""Build a machine-readable Codex eval request for issue #32.

This module only constructs the request. It never invokes Codex, the eval
server, or a browser.

Every request declares the canonical case it serves through ``--case``; the
case, never the prompt text, decides what the request may inject:

``r1``, ``r2``
    the disposable-Zotero continuity cases: both fixture endpoints are required
    and localhost network access is granted.
``r3a``, ``r3b``, ``r4a``, ``r4b``
    Stage 3-5 cases: no Zotero endpoint and no network override at all, because
    the production ``stage2_zotero_rpc.py`` treats an unset or empty
    ``ZOTERO_*`` as the production ``23119/23120`` fallback.
``browser``
    the distinct explicit mode reserved for a separate browser-specific recipe;
    it is the only case that may inject Chrome/NPM wiring.

Unused optional environment is omitted, never injected as an empty string.
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


CANONICAL_CASES = ("r1", "r2", "r3a", "r3b", "r4a", "r4b")
FIXTURE_ENDPOINT_CASES = ("r1", "r2")
ISOLATED_CASES = ("r3a", "r3b", "r4a", "r4b")
BROWSER_CASE = "browser"
REQUEST_CASES = CANONICAL_CASES + (BROWSER_CASE,)


# #40's Stage 2 contract allows one analyzer to run up to three full-mode
# paper-analysis coordinators in one batch. Each coordinator may own exactly
# three analysis leaves, and Stage 2 may run up to two style-validator rounds.
# With Codex V1 semantics, completed-but-open spawned agents still count toward
# the session concurrency ceiling, so the legal single-batch topology can need
# 1 analyzer + 3 coordinators + 9 leaves + 2 validators = 15 open spawned
# threads before lifecycle cleanup. Use one slot of headroom for the acceptance
# harness. This is a test runtime prerequisite, not a production default and
# not a substitute for a separate lifecycle-management issue.
DEFAULT_MAX_CONCURRENT_AGENT_THREADS = 16


def _toml_string(value: str) -> str:
    """Encode a TOML basic string without allowing numeric env coercion."""
    return json.dumps(str(value), ensure_ascii=False)


def _toml_key_segment(value: str) -> str:
    """Return a Codex CLI-compatible bare-key MCP server id."""
    value = str(value)
    if not value or any(char not in "abcdefghijklmnopqrstuvwxyz"
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in value):
        raise RequestBuildError(
            "MCP server id cannot be represented safely in a dotted Codex config override: "
            f"{value!r}")
    return value


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


def _non_empty_names(values: dict[str, object]) -> list[str]:
    return sorted(name for name, value in values.items()
                  if isinstance(value, str) and value.strip())


def _resolve_endpoints(case: str, zotero_http_url: str,
                       zotero_mcp_url: str) -> tuple[str, str] | None:
    """Return the fixture endpoints to inject, or ``None`` when the case must not."""
    supplied = _non_empty_names({"--zotero-http-url": zotero_http_url,
                                 "--zotero-mcp-url": zotero_mcp_url})
    if case in ISOLATED_CASES:
        if supplied:
            raise RequestBuildError(
                f"case {case} does not use Zotero; refusing endpoint arguments {supplied} "
                "because an empty or unused override leaves the production "
                "23119/23120 fallback reachable")
        return None
    if len(supplied) != 2:
        missing = [name for name in ("--zotero-http-url", "--zotero-mcp-url")
                   if name not in supplied]
        raise RequestBuildError(f"case {case} requires fixture Zotero endpoints; "
                                f"missing {missing}")
    return (str(zotero_http_url), str(zotero_mcp_url))


def build_request(*, case: str, consumer_root: Path, prompt_file: Path, output: Path,
                  model: str = "gpt-5.6-luna", reasoning: str = "low",
                  zotero_http_url: str = "", zotero_mcp_url: str = "",
                  max_agent_threads: int = DEFAULT_MAX_CONCURRENT_AGENT_THREADS,
                  chrome_profile_dir: str = "", chrome_cdp_port: str = "",
                  npm_cache: str = "", timeout: int = 1800) -> dict[str, object]:
    consumer_root = Path(consumer_root).resolve()
    prompt = Path(prompt_file).read_text(encoding="utf-8")
    if not consumer_root.is_dir():
        raise RequestBuildError(f"consumer root does not exist: {consumer_root}")
    if case not in REQUEST_CASES:
        raise RequestBuildError(
            f"unknown case {case!r}; expected one of {list(REQUEST_CASES)}")
    if isinstance(max_agent_threads, bool) or not isinstance(max_agent_threads, int):
        raise RequestBuildError("max_agent_threads must be an integer")
    if max_agent_threads < 1:
        raise RequestBuildError("max_agent_threads must be >= 1")
    browser_values = {"--chrome-profile-dir": chrome_profile_dir,
                      "--chrome-cdp-port": chrome_cdp_port,
                      "--npm-cache": npm_cache}
    if case in CANONICAL_CASES:
        supplied = _non_empty_names(browser_values)
        if supplied:
            raise RequestBuildError(
                f"canonical case {case} must stay free of Chrome/NPM wiring; "
                f"refusing {supplied}; a browser-specific recipe uses case "
                f"{BROWSER_CASE!r}")
    else:
        missing = [name for name in browser_values if name not in _non_empty_names(browser_values)]
        if missing:
            raise RequestBuildError(
                f"case {BROWSER_CASE} is the explicit browser-specific mode; "
                f"missing {missing}")
    endpoints = _resolve_endpoints(case, zotero_http_url, zotero_mcp_url)

    # The eval-server passes this as a per-run config override. Without an
    # explicit trust entry, Codex does not load the clean consumer's generated
    # project configuration.
    project_trust = (
        "projects=" + "{" + _toml_string(str(consumer_root)) +
        '={trust_level="trusted"}}'
    )
    config_values = [
        f"model_reasoning_effort={_toml_string(reasoning)}",
        project_trust,
        # Canonical #40 R1-R4 acceptance must not inherit Codex V1's default
        # six-thread ceiling because that ceiling cannot represent the legal
        # Stage 2 single-batch topology. Keep this as an explicit, recorded
        # runtime override rather than mutating the generated consumer config.
        f"agents.max_concurrent_threads_per_session={max_agent_threads}",
    ]
    if endpoints is not None:
        config_values.extend([
            f"shell_environment_policy.set.ZOTERO_HTTP_URL={_toml_string(endpoints[0])}",
            f"shell_environment_policy.set.ZOTERO_MCP_URL={_toml_string(endpoints[1])}",
            # `--sandbox workspace-write` alone does not grant network access; the
            # Zotero fixture endpoints stay unreachable without this override.
            "sandbox_workspace_write.network_access=true",
        ])

    # Canonical #40/#47 R1-R4 never discover or inject Chrome/NPM state; only
    # the separately declared browser mode may, and it discovers the server id
    # from the clean consumer's generated TOML rather than guessing.
    if case == BROWSER_CASE:
        server_id = discover_chrome_server_id(consumer_root)
        server_key = _toml_key_segment(server_id)
        config_values.extend([
            f"shell_environment_policy.set.NPM_CONFIG_CACHE={_toml_string(npm_cache)}",
            f"mcp_servers.{server_key}.env.CHROME_PROFILE_DIR={_toml_string(chrome_profile_dir)}",
            f"mcp_servers.{server_key}.env.CHROME_CDP_PORT={_toml_string(chrome_cdp_port)}",
        ])

    # eval-server prepends ``codex exec``. Its request contract therefore
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
    parser.add_argument("--case", required=True, choices=REQUEST_CASES,
                        help="canonical runtime case; it alone decides Zotero, "
                             "network and Chrome/NPM injection")
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning", default="low")
    parser.add_argument("--zotero-http-url", default="")
    parser.add_argument("--zotero-mcp-url", default="")
    parser.add_argument("--max-agent-threads", type=int,
                        default=DEFAULT_MAX_CONCURRENT_AGENT_THREADS)
    parser.add_argument("--chrome-profile-dir", default="")
    parser.add_argument("--chrome-cdp-port", default="")
    parser.add_argument("--npm-cache", default="")
    parser.add_argument("--timeout", type=int, default=1800)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request = build_request(
            case=args.case,
            consumer_root=args.consumer_root, prompt_file=args.prompt_file, output=args.output,
            model=args.model, reasoning=args.reasoning, zotero_http_url=args.zotero_http_url,
            zotero_mcp_url=args.zotero_mcp_url, max_agent_threads=args.max_agent_threads,
            chrome_profile_dir=args.chrome_profile_dir,
            chrome_cdp_port=args.chrome_cdp_port, npm_cache=args.npm_cache,
            timeout=args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "case": args.case,
                      "output": str(args.output.resolve()),
                      "timeout": request["timeout"],
                      "max_agent_threads": args.max_agent_threads}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
