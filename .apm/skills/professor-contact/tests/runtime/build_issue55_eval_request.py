#!/usr/bin/env python3
"""Build the fixed Codex eval request for issue #55 PC55-R1."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
from pathlib import Path


MODEL = "gpt-5.6-luna"
REASONING = "low"
TIMEOUT = 900
PROMPT_TOKEN = "{{PROGRAM_ROOT}}"
PROMPT_TEMPLATE = (
    "在 {{PROGRAM_ROOT}} 执行已安装 professor-contact 的正式 Stage 3，且只执行 Stage 3。\n"
    "直接消费现有 Stage 2 canonical input；不要进入 Stage 4。\n"
    "完成后正常结束。\n"
)


class RequestBuildError(RuntimeError):
    pass


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
                  rendered_prompt: Path, output: Path, model: str = MODEL,
                  reasoning: str = REASONING, timeout: int = TIMEOUT) -> dict[str, object]:
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
        raise RequestBuildError(f"PC55 requires model {MODEL}")
    if reasoning != REASONING:
        raise RequestBuildError(f"PC55 requires reasoning {REASONING}")
    if timeout != TIMEOUT:
        raise RequestBuildError(f"PC55 requires timeout {TIMEOUT}")
    template = prompt_template.read_text(encoding="utf-8")
    if template != PROMPT_TEMPLATE:
        raise RequestBuildError("prompt template differs from the frozen PC55 prompt")
    rendered = template.replace(PROMPT_TOKEN, str(program_root))
    if PROMPT_TOKEN in rendered:
        raise RequestBuildError("rendered prompt still contains PROGRAM_ROOT token")
    rendered_prompt.parent.mkdir(parents=True, exist_ok=True)
    rendered_prompt.write_text(rendered, encoding="utf-8")

    trust_override = f'projects."{consumer_root}".trust_level="trusted"'
    argv = [
        "--json", "--ephemeral", "--skip-git-repo-check",
        "--sandbox", "workspace-write", "--cd", str(consumer_root),
        "--model", model,
        "--config", f'model_reasoning_effort="{reasoning}"',
        "--config", trust_override,
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
