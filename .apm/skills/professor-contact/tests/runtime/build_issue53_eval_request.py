#!/usr/bin/env python3
"""Build the minimal Codex eval request for issue #53 PC53-R1."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
from pathlib import Path


MODEL = "gpt-5.6-luna"
REASONING = "low"


class RequestBuildError(RuntimeError):
    pass


def build_request(*, consumer_root: Path, prompt_file: Path, output: Path,
                  model: str = MODEL, reasoning: str = REASONING,
                  timeout: int = 900) -> dict[str, object]:
    consumer_root = Path(consumer_root).resolve()
    if not consumer_root.is_dir():
        raise RequestBuildError(f"consumer root does not exist: {consumer_root}")
    if model != MODEL:
        raise RequestBuildError(f"PC53 requires model {MODEL}")
    if reasoning != REASONING:
        raise RequestBuildError(f"PC53 requires reasoning {REASONING}")
    if timeout <= 0:
        raise RequestBuildError("timeout must be positive")
    prompt = Path(prompt_file).read_text(encoding="utf-8")
    if not prompt.strip():
        raise RequestBuildError("prompt file is empty")

    trust_override = f'projects."{consumer_root}".trust_level="trusted"'
    config_values = [f'model_reasoning_effort="{reasoning}"', trust_override]
    # eval-server prepends ``codex exec``.  These are the only arguments and
    # per-run config values allowed by PC53-R1.
    argv = [
        "--json", "--ephemeral", "--skip-git-repo-check",
        "--sandbox", "workspace-write", "--cd", str(consumer_root),
        "--model", model,
    ]
    for value in config_values:
        argv.extend(["--config", value])
    argv.extend(["--", prompt])
    request = {"command": shlex.join(argv), "timeout": int(timeout)}

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output.parent,
        prefix=f".{output.name}.", delete=False,
    ) as handle:
        json.dump(request, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, output)
    return request


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--reasoning", default=REASONING)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request = build_request(
            consumer_root=args.consumer_root,
            prompt_file=args.prompt_file,
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
